"""Tests for platform-specific draft formatting (no publishing)."""

import pytest

from backend.content_engine.transformation.platform_drafts import (
    PlatformDraftBuilder,
    parse_script_sections,
    strip_lead,
)
from backend.models.content_pipeline_run import ContentKind, PipelineSource
from backend.providers.llm.base import LLMConfig
from backend.providers.llm.mock import MockProvider
from backend.providers.search.mock import MockSearchProvider
from backend.services.career_content_service import CareerContentService

POST_DRAFT = (
    "I shipped the billing API at Acme Corp with our backend team after months "
    "of focused Python engineering work. Biggest lesson: small slices beat big "
    "bang releases every single time.\n\nWhat did shipping teach you?\n\n"
    "#Backend #Python #Engineering"
)

SCRIPT_DRAFT = """HOOK (0-3s):
I shipped production code in my first ninety days as a backend engineer
BEATS:
1. VO: I joined Acme Corp as a backend engineer on the billing team
ON-SCREEN: First ninety days
2. VO: I owned one small billing endpoint end to end with tests
ON-SCREEN: Own one thing
CTA (final 3s):
VO: Follow for weekly backend lessons from the trenches
ON-SCREEN: Follow for more
#Backend #Python #Engineering"""


def _clean(word):
    return word.strip("#.,!?\"'").lower()


def _vocab(text):
    return {_clean(w) for w in text.split() if len(_clean(w)) > 3}


class TestScriptParsing:
    def test_structured_script(self):
        parsed = parse_script_sections(SCRIPT_DRAFT)
        assert "ninety days" in parsed["hook"]
        assert len(parsed["beats"]) == 2
        assert parsed["beats"][0]["vo"].startswith("I joined Acme")
        assert parsed["beats"][0]["on_screen"] == "First ninety days"
        assert "Follow" in parsed["cta"]
        assert parsed["has_structure"] is True

    def test_unstructured_fallback(self):
        parsed = parse_script_sections("Just a plain post without markers here.")
        assert parsed["hook"] == "Just a plain post without markers here."
        assert parsed["beats"] == []
        assert parsed["has_structure"] is False


class TestPlatformShapes:
    def setup_method(self):
        self.builder = PlatformDraftBuilder()

    def test_linkedin_post(self):
        variants = self.builder.build(POST_DRAFT, "linkedin_post", ["linkedin"])
        post = variants["linkedin"]
        assert post["kind"] == "post"
        assert len(post["text"]) <= 3000
        assert post["hashtags"] == ["#Backend", "#Python", "#Engineering"]
        assert post["caption"]["text"]

    def test_instagram_reel(self):
        variants = self.builder.build(SCRIPT_DRAFT, "short_video_script", ["instagram"])
        reel = variants["instagram"]
        assert reel["kind"] == "reel"
        assert len(reel["caption"]["text"]) <= 2200
        assert len(reel["script"]["beats"]) == 2

    def test_instagram_post_has_no_script(self):
        variants = self.builder.build(POST_DRAFT, "linkedin_post", ["instagram"])
        assert variants["instagram"]["kind"] == "post"
        assert variants["instagram"]["script"] is None

    def test_facebook_variants(self):
        variants = self.builder.build(SCRIPT_DRAFT, "short_video_script", ["facebook"])
        assert variants["facebook"]["kind"] == "video"
        assert variants["facebook"]["description"]
        post = self.builder.build(POST_DRAFT, "linkedin_post", ["facebook"])["facebook"]
        assert post["kind"] == "post"
        assert post["description"]

    def test_youtube_shapes(self):
        variants = self.builder.build(
            SCRIPT_DRAFT, "short_video_script", ["youtube", "youtube_shorts"], extra_tags=["Python"]
        )
        video = variants["youtube"]
        assert video["kind"] == "video"
        assert len(video["title"]) <= 100
        assert len(video["description"]) <= 5000
        assert len(video["tags"]) <= 15
        assert "Python" in video["tags"]
        assert variants["youtube_shorts"]["kind"] == "short"

    def test_no_new_claims(self):
        variants = self.builder.build(SCRIPT_DRAFT, "short_video_script",
                                      ["linkedin", "instagram", "facebook", "youtube"])
        vocab = _vocab(SCRIPT_DRAFT)
        for platform, variant in variants.items():
            blob = " ".join([
                variant["text"],
                variant["caption"]["text"],
                variant.get("title", ""),
                variant.get("description", ""),
            ])
            for word in blob.split():
                cleaned = _clean(word)
                if len(cleaned) > 4 and cleaned not in {"follow"}:
                    assert cleaned in vocab, (platform, word)


class TestFormattingStage:
    @pytest.mark.asyncio
    async def test_run_produces_platform_drafts_and_stays_draft(self, db_session, test_user):
        from backend.models.profile import Profile
        from backend.models.social_post import SocialPost

        db_session.add(Profile(
            user_id=test_user.id, headline="Backend Engineer",
            bio="Ships Python APIs.", years_of_experience=5,
        ))
        db_session.commit()
        posts_before = db_session.query(SocialPost).count()

        service = CareerContentService(
            db_session,
            llm_provider=MockProvider(LLMConfig(model="mock"), responses=[POST_DRAFT]),
            search_provider=MockSearchProvider(),
        )
        run = await service.run_pipeline(
            user_id=test_user.id, source=PipelineSource.PROFILE,
            content_kind=ContentKind.LINKEDIN_POST, platforms=["linkedin", "instagram", "youtube"],
        )
        assert run.status.value == "pending_review"
        variants = run.stage_results["formatting"]["variants"]
        assert set(variants) == {"linkedin", "instagram", "youtube"}
        assert variants["linkedin"]["kind"] == "post"
        assert variants["instagram"]["caption"]["text"]
        assert len(variants["youtube"]["title"]) <= 100
        # Draft only: nothing published.
        assert db_session.query(SocialPost).count() == posts_before
