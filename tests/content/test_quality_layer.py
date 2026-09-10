"""Tests for the content quality and fact-validation layer.

Covers existence re-validation, numeric-claim support, personal/sensitive
data screening, quality signals, platform-fit checks, draft lifecycle
statuses, and the human-approval gate.
"""

import pytest

from backend.content_engine.quality.pipeline_verifier import (
    PipelineVerifier,
    validate_platform_fit,
)
from backend.models.content_pipeline_run import ContentKind, PipelineStage, PipelineSource
from backend.providers.llm.base import LLMConfig
from backend.providers.llm.mock import MockProvider
from backend.providers.search.mock import MockSearchProvider
from backend.services.career_content_service import CareerContentService

CLEAN_DRAFT = (
    "I shipped the billing API at Acme Corp with our backend team after months "
    "of focused Python engineering work. Biggest lesson: small slices beat big "
    "bang releases every single time for the whole crew.\n\nWhat did shipping "
    "teach you this year?\n\n#Backend #Python"
)


def _mock_llm(text=CLEAN_DRAFT):
    return MockProvider(LLMConfig(model="mock"), responses=[text])


def _service(db_session):
    return CareerContentService(
        db_session, llm_provider=_mock_llm(), search_provider=MockSearchProvider()
    )


class TestExistenceGuard:
    @pytest.mark.asyncio
    async def test_guard_passes_with_terms(self, db_session, test_user):
        service = _service(db_session)
        report = await service.router.route({
            "type": "career_content.guard", "source": "certification",
            "source_id": 1, "user_id": test_user.id,
            "required_terms": ["AWS Architect"],
        })
        assert report["exists"] is True

    @pytest.mark.asyncio
    async def test_guard_fails_closed_without_terms(self, db_session, test_user):
        service = _service(db_session)
        report = await service.router.route({
            "type": "career_content.guard", "source": "certification",
            "source_id": 999, "user_id": test_user.id, "required_terms": [],
        })
        assert report["exists"] is False
        assert "not owned" in report["message"]

    @pytest.mark.asyncio
    async def test_guard_skips_general_sources(self, db_session, test_user):
        service = _service(db_session)
        report = await service.router.route({
            "type": "career_content.guard", "source": "profile",
            "source_id": None, "user_id": test_user.id, "required_terms": [],
        })
        assert report == {"exists": True, "skipped": True}


class TestNumericClaims:
    @pytest.mark.asyncio
    async def test_supported_number_passes(self):
        verifier = PipelineVerifier()
        brief = {"skills": ["Python"], "highlight": "Grew API traffic 300 percent in 2024"}
        result = await verifier.verify(
            "Proud that we grew API traffic 300 percent in 2024 with our Python backend team working together.",
            brief=brief,
        )
        assert not any("numeric claims" in i for i in result["issues"])

    @pytest.mark.asyncio
    async def test_invented_metric_flagged(self):
        verifier = PipelineVerifier()
        result = await verifier.verify(
            "Proud that we grew revenue 900 percent with our Python backend team working together daily.",
            brief={"skills": ["Python"]},
        )
        assert any("numeric claims" in i for i in result["issues"])

    @pytest.mark.asyncio
    async def test_template_numbers_not_penalized(self):
        verifier = PipelineVerifier()
        draft = ("Hook for our Python journey in under 60 seconds of talking with friends "
                 "about backend work and lessons learned together.")
        result = await verifier.verify(
            draft, brief={"skills": ["Python"]}, kind_template="fit ~60 seconds (~130 words)",
        )
        assert not any("numeric claims" in i for i in result["issues"])


class TestSensitiveData:
    @pytest.mark.asyncio
    async def test_foreign_email_flagged(self):
        verifier = PipelineVerifier()
        result = await verifier.verify(
            CLEAN_DRAFT + " Contact me at jane.doe@example.com for details.",
            brief={"skills": ["Python"]},
        )
        assert any("personal contact" in i for i in result["issues"])

    @pytest.mark.asyncio
    async def test_foreign_phone_flagged(self):
        verifier = PipelineVerifier()
        result = await verifier.verify(
            CLEAN_DRAFT + " Call +1-555-123-4567 to collaborate with our team.",
            brief={"skills": ["Python"]},
        )
        assert any("personal contact" in i for i in result["issues"])

    @pytest.mark.asyncio
    async def test_secret_leakage_flagged(self):
        verifier = PipelineVerifier()
        result = await verifier.verify(
            CLEAN_DRAFT + " Deploy with api_key: sk-live-9f8e7d6c5b4a39482716 later today.",
            brief={"skills": ["Python"]},
        )
        assert any("secret" in i for i in result["issues"])

    @pytest.mark.asyncio
    async def test_clean_draft_passes(self):
        verifier = PipelineVerifier()
        result = await verifier.verify(CLEAN_DRAFT, brief={"skills": ["Python"]})
        assert result["passed"] is True


class TestQualitySignals:
    @pytest.mark.asyncio
    async def test_shouting_and_punctuation_flagged(self):
        verifier = PipelineVerifier()
        draft = ("AMAZING NEWS EVERYONE I AM THRILLED TO ANNOUNCE THIS TODAY!!!!!! "
                 "So grateful!!!!!! Truly blessed!!!!!! Wow wow wow!!!!!!")
        result = await verifier.verify(draft, brief={"skills": ["Python"]})
        assert any("SHOUTING" in i or "SHOUT" in i or "shouting" in i for i in result["issues"])
        assert any("exclamation" in i for i in result["issues"])

    @pytest.mark.asyncio
    async def test_duplicated_sentences_flagged(self):
        verifier = PipelineVerifier()
        sentence = "We shipped the billing API after months of careful Python work together"
        result = await verifier.verify(
            f"{sentence}. Some filler transition here now. {sentence}.",
            brief={"skills": ["Python"]},
        )
        assert any("duplicated" in i for i in result["issues"])


class TestPlatformFit:
    def test_fit_report(self):
        report = validate_platform_fit("x" * 500, ["linkedin", "twitter"], {"linkedin": 3000, "twitter": 280})
        assert report["linkedin"]["fits"] is True
        assert report["twitter"]["fits"] is False
        assert report["twitter"]["over_by"] == 220

    @pytest.mark.asyncio
    async def test_heavy_overflow_flagged(self):
        verifier = PipelineVerifier()
        result = await verifier.verify(
            "Python backend work " * 60,
            brief={"skills": ["Python"]},
            platforms=["twitter"],
            platform_limits={"twitter": 280},
        )
        assert any("exceeds twitter" in i for i in result["issues"])


class TestDraftLifecycle:
    def test_status_members(self):
        assert PipelineStage.DRAFT.value == "draft"
        assert PipelineStage.REVIEW_REQUIRED is PipelineStage.PENDING_REVIEW
        assert PipelineStage.APPROVED.value == "approved"
        assert PipelineStage.REJECTED.value == "rejected"

    @pytest.mark.asyncio
    async def test_run_records_guard_and_stays_draft(self, db_session, test_user):
        from backend.models.profile import Profile

        db_session.add(Profile(
            user_id=test_user.id, headline="Backend Engineer",
            bio="Ships Python APIs.", years_of_experience=5,
        ))
        db_session.commit()
        service = _service(db_session)
        run = await service.run_pipeline(
            user_id=test_user.id, source=PipelineSource.PROFILE,
            content_kind=ContentKind.LINKEDIN_POST, platforms=["linkedin"],
        )
        assert run.status.value == "pending_review"
        verification = run.stage_results["verification"]
        assert verification["guard"]["exists"] is True
        assert run.stage_results["topic_selection"]["selected"]["topic"]

    @pytest.mark.asyncio
    async def test_pii_issue_surfaced_not_silent(self, db_session, test_user):
        from backend.models.profile import Profile

        db_session.add(Profile(
            user_id=test_user.id, headline="Backend Engineer",
            bio="Ships Python APIs.", years_of_experience=5,
        ))
        db_session.commit()
        text = CLEAN_DRAFT + " Contact me at jane.doe@example.com for details."
        service = CareerContentService(
            db_session, llm_provider=_mock_llm(text), search_provider=MockSearchProvider()
        )
        run = await service.run_pipeline(
            user_id=test_user.id, source=PipelineSource.PROFILE,
            content_kind=ContentKind.LINKEDIN_POST, platforms=["linkedin"],
        )
        issues = run.stage_results["verification"]["issues"]
        assert any("personal contact" in i for i in issues)

    @pytest.mark.asyncio
    async def test_approval_gate_blocks_failed_runs(self, db_session, test_user):
        from backend.models.profile import Profile

        db_session.add(Profile(user_id=test_user.id, headline="Engineer"))
        db_session.commit()
        service = CareerContentService(
            db_session,
            llm_provider=_mock_llm("short"),
            search_provider=MockSearchProvider(),
        )
        run = await service.run_pipeline(
            user_id=test_user.id, source=PipelineSource.PROFILE,
            content_kind=ContentKind.LINKEDIN_POST, platforms=["linkedin"],
        )
        assert run.status.value == "failed"
        with pytest.raises(ValueError):
            service.approve_run(run.id, test_user.id)
