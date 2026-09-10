"""Tests for the Career-to-Content pipeline (backend stages 1-7)."""

import pytest

from backend.content_engine.generation import career_templates
from backend.content_engine.generation.llm_generator import CareerContentGenerator
from backend.content_engine.quality.pipeline_verifier import PipelineVerifier
from backend.content_engine.transformation.platform_formatter import PlatformFormatter
from backend.models.achievement import Achievement
from backend.models.certification import Certification
from backend.models.content_pipeline_run import ContentKind, PipelineSource
from backend.models.profile import Profile
from backend.providers.llm.base import LLMConfig
from backend.providers.llm.mock import MockProvider
from backend.providers.search.mock import MockSearchProvider
from backend.services.career_content_service import CareerContentService


def _mock_llm(
    text="Reflections on shipping our Python API for Acme Corp with the backend team after months of focused engineering work."
):
    return MockProvider(LLMConfig(model="mock"), responses=[text])


def _make_profile(db_session, user):
    profile = Profile(
        user_id=user.id,
        headline="Backend Engineer",
        target_role="Senior Backend Engineer",
        location="Remote",
        bio="Backend engineer shipping Python APIs.",
        years_of_experience=5,
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return profile


class TestCareerTemplates:
    def test_all_kinds_have_prompts(self):
        brief = {"headline": "Backend Engineer", "skills": ["Python"], "highlight": "Shipped X"}
        for kind in ContentKind:
            system, user = career_templates.build_prompt(kind, brief)
            assert system and user
            assert "ONLY the facts" in system

    def test_short_video_script_schema(self):
        system, _ = career_templates.build_prompt(
            ContentKind.SHORT_VIDEO_SCRIPT, {"highlight": "Won hackathon"}
        )
        for section in ("HOOK", "BEATS", "CTA"):
            assert section in system


class TestPipelineVerifier:
    @pytest.mark.asyncio
    async def test_passes_grounded_draft(self):
        verifier = PipelineVerifier()
        result = await verifier.verify(
            "I shipped our Python API at Acme Corp with the backend team after months of hard work together.",
            brief={"skills": ["Python"], "highlight": "Shipped Python API at Acme Corp"},
        )
        assert result["passed"] is True
        assert result["score"] >= 0.6

    @pytest.mark.asyncio
    async def test_rejects_stub_leakage(self):
        verifier = PipelineVerifier()
        result = await verifier.verify(
            "Generated content for: my career update post",
            brief={"skills": ["Python"]},
        )
        assert result["passed"] is False
        assert result["issues"]

    @pytest.mark.asyncio
    async def test_rejects_empty_draft(self):
        verifier = PipelineVerifier()
        result = await verifier.verify("", brief={"skills": ["Python"]})
        assert result["passed"] is False


class TestPlatformFormatterExtension:
    def test_existing_limits_unchanged(self):
        formatter = PlatformFormatter()
        assert formatter.format("x" * 2000, "linkedin") == "x" * 2000
        assert len(formatter.format("x" * 4000, "linkedin")) == 3000
        assert formatter.format("x" * 300, "twitter").endswith("...")

    def test_youtube_and_shorts_limits(self):
        formatter = PlatformFormatter()
        assert len(formatter.format("y" * 6000, "youtube")) <= 5000
        assert len(formatter.format("s" * 3000, "short")) <= 2200
        assert formatter.youtube_title("t" * 150).endswith("...")
        assert len(formatter.youtube_title("t" * 150)) <= 100


class TestCareerContentService:
    def test_build_brief_from_profile(self, db_session, test_user):
        _make_profile(db_session, test_user)
        service = CareerContentService(db_session, llm_provider=_mock_llm())
        brief = service.build_brief(test_user.id, PipelineSource.PROFILE)
        assert brief["name"]
        assert isinstance(brief["skills"], list)

    def test_build_brief_from_certification(self, db_session, test_user):
        cert = Certification(user_id=test_user.id, name="AWS Architect", issuer="AWS")
        db_session.add(cert)
        db_session.commit()
        service = CareerContentService(db_session, llm_provider=_mock_llm())
        brief = service.build_brief(test_user.id, PipelineSource.CERTIFICATION, cert.id)
        assert "AWS Architect" in brief["highlight"]

    def test_build_brief_from_achievement(self, db_session, test_user):
        item = Achievement(user_id=test_user.id, title="Hackathon winner", description="Built X")
        db_session.add(item)
        db_session.commit()
        service = CareerContentService(db_session, llm_provider=_mock_llm())
        brief = service.build_brief(test_user.id, PipelineSource.ACHIEVEMENT, item.id)
        assert "Hackathon winner" in brief["highlight"]

    @pytest.mark.asyncio
    async def test_full_run_to_review(self, db_session, test_user):
        _make_profile(db_session, test_user)
        service = CareerContentService(
            db_session, llm_provider=_mock_llm(), search_provider=MockSearchProvider()
        )
        run = await service.run_pipeline(
            user_id=test_user.id,
            source=PipelineSource.PROFILE,
            content_kind=ContentKind.LINKEDIN_POST,
            platforms=["linkedin"],
        )
        assert run.status.value == "pending_review"
        assert run.quality_score is not None
        assert "linkedin" in (run.stage_results.get("formatting", {}).get("variants", {}))

    @pytest.mark.asyncio
    async def test_approve_and_reject_gates(self, db_session, test_user):
        _make_profile(db_session, test_user)
        service = CareerContentService(
            db_session, llm_provider=_mock_llm(), search_provider=MockSearchProvider()
        )
        run = await service.run_pipeline(
            user_id=test_user.id,
            source=PipelineSource.PROFILE,
            content_kind=ContentKind.EDUCATIONAL,
            platforms=["linkedin"],
        )
        approved = service.approve_run(run.id, test_user.id, notes="Looks good")
        assert approved.status.value == "approved"
        assert approved.reviewed_by == test_user.id
        with pytest.raises(ValueError):
            service.reject_run(run.id, test_user.id)

    def test_reject_requires_review_state(self, db_session, test_user):
        service = CareerContentService(db_session, llm_provider=_mock_llm())
        with pytest.raises(ValueError):
            service.reject_run(999999, test_user.id)


class TestCareerContentAPI:
    def test_meta(self, client, auth_headers):
        response = client.get("/api/career-content/meta", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert "linkedin_post" in body["content_kinds"]
        assert "linkedin" in body["platforms"]

    def test_run_list_and_review_flow(self, client, auth_headers, db_session, test_user):
        _make_profile(db_session, test_user)
        create = client.post(
            "/api/career-content/pipeline/runs",
            headers=auth_headers,
            json={"source": "profile", "content_kind": "linkedin_post", "platforms": ["linkedin"]},
        )
        assert create.status_code == 201, create.text
        run_id = create.json()["id"]
        # Keyless environments resolve generation to the Mock provider whose
        # canned output is intentionally junk: the quality gate must fail
        # the run instead of letting it reach human review.
        assert create.json()["status"] == "failed"
        assert create.json()["error_message"]

        listed = client.get("/api/career-content/pipeline/runs", headers=auth_headers)
        assert listed.status_code == 200
        assert any(r["id"] == run_id for r in listed.json()["runs"])

        detail = client.get(f"/api/career-content/pipeline/runs/{run_id}", headers=auth_headers)
        assert detail.status_code == 200
        assert detail.json()["stage_results"]["generation"]

        # Approval gate must refuse runs that are not awaiting review.
        blocked = client.post(
            f"/api/career-content/pipeline/runs/{run_id}/approve",
            headers=auth_headers,
            json={"notes": "Ship it"},
        )
        assert blocked.status_code == 400

    def test_rejects_unknown_platform(self, client, auth_headers):
        response = client.post(
            "/api/career-content/pipeline/runs",
            headers=auth_headers,
            json={"source": "profile", "content_kind": "linkedin_post", "platforms": ["myspace"]},
        )
        assert response.status_code == 400

    def test_requires_auth(self, client):
        response = client.get("/api/career-content/meta")
        assert response.status_code in (401, 403)
