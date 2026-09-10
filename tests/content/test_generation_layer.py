"""Tests for the Career-to-Content generation layer.

Covers topic selection, the career-post kind, captions, and the
entity-grounding gate that blocks invented achievements/certifications.
"""

import pytest

from backend.content_engine.generation import career_templates
from backend.content_engine.generation.captions import (
    CAPTION_LIMITS,
    build_caption,
    extract_hashtags,
)
from backend.content_engine.generation.topic_selector import pick_topic, suggest_topics
from backend.content_engine.quality.pipeline_verifier import PipelineVerifier
from backend.models.content_pipeline_run import ContentKind, PipelineSource
from backend.providers.llm.base import LLMConfig
from backend.providers.llm.mock import MockProvider
from backend.providers.search.mock import MockSearchProvider
from backend.services.career_content_service import CareerContentService

BRIEF = {
    "headline": "Backend Engineer",
    "name": "Test User",
    "target_role": "Senior Backend Engineer",
    "skills": ["Python", "Docker"],
    "highlight": "Shipped the billing API at Acme Corp",
    "platforms": ["linkedin", "instagram"],
    "extra": {"issuer": "AWS", "technologies": "Python, FastAPI",
              "url": "https://example.com/repo"},
}

LONG_DRAFT = (
    "I shipped the billing API at Acme Corp with our backend team after months "
    "of focused Python engineering work. Biggest lesson: small slices beat big "
    "bang releases every single time for the whole crew.\n\nWhat did shipping "
    "teach you this year?\n\n#Backend #Python #Engineering"
)


def _mock_llm(text=LONG_DRAFT):
    return MockProvider(LLMConfig(model="mock"), responses=[text])


class TestTopicSelection:
    def test_suggestions_grounded_in_brief(self):
        suggestions = suggest_topics(BRIEF)
        assert 1 <= len(suggestions) <= 5
        blob = " ".join(
            [BRIEF["highlight"], BRIEF["target_role"], *BRIEF["skills"],
             BRIEF["extra"]["issuer"]]
        ).lower()
        for suggestion in suggestions:
            assert any(
                token in suggestion["topic"].lower()
                for token in ["acme", "billing", "python", "docker",
                              "senior backend", "aws"]
            ), suggestion
            assert suggestion["source"] in {
                "highlight", "skills", "project", "certification",
                "target_role", "research",
            }

    def test_pick_auto_and_supplied(self):
        auto = pick_topic(BRIEF)
        assert auto["topic"]
        assert auto["source"] != "caller"
        assert isinstance(auto["suggestions"], list)
        supplied = pick_topic(BRIEF, requested="  My custom topic  ")
        assert supplied == {
            "topic": "My custom topic",
            "angle": "supplied",
            "source": "caller",
            "suggested_kind": None,
            "suggestions": supplied["suggestions"],
        }

    def test_empty_brief_falls_back(self):
        picked = pick_topic({})
        assert picked["topic"]
        assert picked["angle"] == "fallback"


class TestCareerPostKind:
    def test_template_registered(self):
        system, user = career_templates.build_prompt(ContentKind.CAREER_POST, BRIEF)
        assert "ONLY the facts" in system
        assert ContentKind.CAREER_POST.value == "career_post"
        assert ContentKind("career_post") is ContentKind.CAREER_POST


class TestCaptions:
    def test_within_platform_limits(self):
        for platform, limit in CAPTION_LIMITS.items():
            caption = build_caption(LONG_DRAFT, platform)
            assert len(caption["text"]) <= limit, platform
            assert caption["hashtags"] == ["#Backend", "#Python", "#Engineering"]

    def test_caption_introduces_no_new_claims(self):
        caption = build_caption(LONG_DRAFT, "instagram")

        def clean(word):
            return word.strip("#.,!?\"'").lower()

        draft_words = {clean(w) for w in LONG_DRAFT.split()}
        for word in caption["text"].split():
            cleaned = clean(word)
            if len(cleaned) > 3:
                assert cleaned in draft_words, word

    def test_hashtag_helpers(self):
        assert extract_hashtags("a #One b #one #Two") == ["#One", "#Two"]


class TestEntityGrounding:
    @pytest.mark.asyncio
    async def test_missing_entity_fails(self):
        verifier = PipelineVerifier()
        result = await verifier.verify(
            LONG_DRAFT,
            brief={"skills": ["Python"]},
            required_terms=["Certified Kubernetes Administrator"],
        )
        assert result["passed"] is False
        assert any("Certified Kubernetes Administrator" in i for i in result["issues"])

    @pytest.mark.asyncio
    async def test_present_entity_passes(self):
        verifier = PipelineVerifier()
        draft = LONG_DRAFT + " This work supported my AWS Architect certification journey."
        result = await verifier.verify(
            draft,
            brief={"skills": ["Python"]},
            required_terms=["AWS Architect"],
        )
        assert result["passed"] is True

    @pytest.mark.asyncio
    async def test_no_required_terms_unchanged(self):
        verifier = PipelineVerifier()
        result = await verifier.verify(LONG_DRAFT, brief={"skills": ["Python"]})
        assert result["passed"] is True


class TestGenerationPipeline:
    @pytest.mark.asyncio
    async def test_run_with_topic_and_captions_stays_draft(self, db_session, test_user):
        from backend.models.profile import Profile
        from backend.models.social_post import SocialPost

        db_session.add(Profile(
            user_id=test_user.id, headline="Backend Engineer",
            target_role="Senior Backend Engineer",
            bio="Ships Python APIs.", years_of_experience=5,
        ))
        db_session.commit()
        posts_before = db_session.query(SocialPost).count()

        service = CareerContentService(
            db_session, llm_provider=_mock_llm(), search_provider=MockSearchProvider()
        )
        run = await service.run_pipeline(
            user_id=test_user.id, source=PipelineSource.PROFILE,
            content_kind=ContentKind.CAREER_POST,
            platforms=["linkedin", "instagram"], topic="Shipping season",
        )
        assert run.status.value == "pending_review"
        assert run.stage_results["topic_selection"]["selected"]["topic"] == "Shipping season"
        variants = run.stage_results["formatting"]["variants"]
        assert set(variants) == {"linkedin", "instagram"}
        for variant in variants.values():
            assert variant["caption"]["text"]
            assert len(variant["caption"]["text"]) <= CAPTION_LIMITS["instagram"] + 200
        # Draft only: nothing published, no social rows created.
        assert db_session.query(SocialPost).count() == posts_before

    @pytest.mark.asyncio
    async def test_certification_run_grounds_entity(self, db_session, test_user):
        from backend.models.certification import Certification

        db_session.add(cert := Certification(
            user_id=test_user.id, name="AWS Architect", issuer="AWS"))
        db_session.commit()

        text = ("Thrilled to share I earned the AWS Architect certification from AWS "
                "after months of hands-on labs and practice exams with my study group.")
        service = CareerContentService(
            db_session, llm_provider=_mock_llm(text), search_provider=MockSearchProvider()
        )
        run = await service.run_pipeline(
            user_id=test_user.id, source=PipelineSource.CERTIFICATION, source_id=cert.id,
            content_kind=ContentKind.CERTIFICATION_POST, platforms=["linkedin"],
        )
        assert run.status.value == "pending_review"
        assert run.stage_results["verification"]["passed"] is True

    @pytest.mark.asyncio
    async def test_invented_certification_blocked(self, db_session, test_user):
        from backend.models.certification import Certification

        db_session.add(cert := Certification(
            user_id=test_user.id, name="AWS Architect", issuer="AWS"))
        db_session.commit()

        text = ("Thrilled to share I earned the Google Cloud Architect certification "
                "after months of dedicated weekend study sessions with my peers.")
        service = CareerContentService(
            db_session, llm_provider=_mock_llm(text), search_provider=MockSearchProvider()
        )
        run = await service.run_pipeline(
            user_id=test_user.id, source=PipelineSource.CERTIFICATION, source_id=cert.id,
            content_kind=ContentKind.CERTIFICATION_POST, platforms=["linkedin"],
        )
        assert run.status.value == "failed"
        assert "AWS Architect" in (run.error_message or "")
