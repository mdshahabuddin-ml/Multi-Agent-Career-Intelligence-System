"""Tests for the human approval workflow: view/edit/approve/reject/regenerate."""

import pytest

from backend.models.content_pipeline_run import ContentKind, PipelineSource
from backend.models.profile import Profile
from backend.providers.llm.base import LLMConfig
from backend.providers.llm.mock import MockProvider
from backend.providers.search.mock import MockSearchProvider
from backend.services.career_content_service import CareerContentService

GOOD_TEXT = (
    "Edited draft: I ship Python backend APIs with my team and mentor junior "
    "engineers on testing and code review practices every single week."
)
OTHER_TEXT = (
    "Regenerated draft: our Python backend crew refactored the billing service "
    "together and cut deploy times with careful testing and thorough reviews."
)


def _mock_llm(text=GOOD_TEXT):
    return MockProvider(LLMConfig(model="mock"), responses=[text])


def _profile(db_session, test_user):
    db_session.add(Profile(
        user_id=test_user.id, headline="Backend Engineer",
        target_role="Senior Backend Engineer",
        bio="Ships Python APIs.", years_of_experience=5,
    ))
    db_session.commit()


def _service(db_session, text=GOOD_TEXT):
    return CareerContentService(
        db_session, llm_provider=_mock_llm(text), search_provider=MockSearchProvider()
    )


async def _pending_run(db_session, test_user, text=GOOD_TEXT):
    _profile(db_session, test_user)
    service = _service(db_session, text)
    run = await service.run_pipeline(
        user_id=test_user.id, source=PipelineSource.PROFILE,
        content_kind=ContentKind.LINKEDIN_POST, platforms=["linkedin"],
    )
    assert run.status.value == "pending_review"
    return service, run


class TestViewDraft:
    @pytest.mark.asyncio
    async def test_get_run_shows_draft_and_stages(self, db_session, test_user):
        service, run = await _pending_run(db_session, test_user)
        fetched = service.get_run(run.id, test_user.id)
        assert fetched.stage_results["generation"]["text"] == GOOD_TEXT
        assert set(fetched.stage_results) >= {
            "intake", "topic_selection", "research", "generation",
            "verification", "formatting",
        }

    def test_get_missing_run(self, db_session, test_user):
        with pytest.raises(ValueError, match="not found"):
            _service(db_session).get_run(999999, test_user.id)


class TestEditDraft:
    @pytest.mark.asyncio
    async def test_edit_keeps_history_and_review_state(self, db_session, test_user):
        service, run = await _pending_run(db_session, test_user)
        edited = await service.edit_draft(run.id, test_user.id, OTHER_TEXT)
        assert edited.status.value == "pending_review"
        assert edited.stage_results["generation"]["text"] == OTHER_TEXT
        history = edited.stage_results["draft_history"]
        assert len(history) == 1
        assert history[0]["text"] == GOOD_TEXT
        assert edited.stage_results["formatting"]["variants"]["linkedin"]

    @pytest.mark.asyncio
    async def test_edit_empty_rejected(self, db_session, test_user):
        service, run = await _pending_run(db_session, test_user)
        with pytest.raises(ValueError):
            await service.edit_draft(run.id, test_user.id, "   ")

    @pytest.mark.asyncio
    async def test_edit_bad_text_fails_gate(self, db_session, test_user):
        service, run = await _pending_run(db_session, test_user)
        failed = await service.edit_draft(run.id, test_user.id, "too short")
        assert failed.status.value == "failed"
        assert failed.error_message
        with pytest.raises(ValueError):
            service.approve_run(run.id, test_user.id)

    @pytest.mark.asyncio
    async def test_edit_rescues_failed_run(self, db_session, test_user):
        _profile(db_session, test_user)
        service = _service(db_session, "short")
        run = await service.run_pipeline(
            user_id=test_user.id, source=PipelineSource.PROFILE,
            content_kind=ContentKind.LINKEDIN_POST, platforms=["linkedin"],
        )
        assert run.status.value == "failed"
        rescued = await service.edit_draft(run.id, test_user.id, GOOD_TEXT)
        assert rescued.status.value == "pending_review"

    @pytest.mark.asyncio
    async def test_edit_approved_run_blocked(self, db_session, test_user):
        service, run = await _pending_run(db_session, test_user)
        service.approve_run(run.id, test_user.id)
        with pytest.raises(ValueError, match="final"):
            await service.edit_draft(run.id, test_user.id, GOOD_TEXT)


class TestRegenerate:
    @pytest.mark.asyncio
    async def test_regenerate_new_draft_and_history(self, db_session, test_user):
        _profile(db_session, test_user)
        service = _service(db_session, GOOD_TEXT)
        run = await service.run_pipeline(
            user_id=test_user.id, source=PipelineSource.PROFILE,
            content_kind=ContentKind.LINKEDIN_POST, platforms=["linkedin"],
        )
        service2 = CareerContentService(
            db_session, llm_provider=_mock_llm(OTHER_TEXT),
            search_provider=MockSearchProvider(),
        )
        # Swap generator to simulate a fresh take (same user/session).
        service.generator = service2.generator
        revived = await service.regenerate_draft(run.id, test_user.id, topic="Mentoring")
        assert revived.status.value == "pending_review"
        assert revived.stage_results["generation"]["text"] == OTHER_TEXT
        assert revived.stage_results["generation"]["origin"] == "regenerated"
        assert revived.stage_results["draft_history"][0]["text"] == GOOD_TEXT

    @pytest.mark.asyncio
    async def test_regenerate_after_reject(self, db_session, test_user):
        service, run = await _pending_run(db_session, test_user)
        service.reject_run(run.id, test_user.id, notes="try again")
        revived = await service.regenerate_draft(run.id, test_user.id)
        assert revived.status.value == "pending_review"

    @pytest.mark.asyncio
    async def test_regenerate_approved_blocked(self, db_session, test_user):
        service, run = await _pending_run(db_session, test_user)
        service.approve_run(run.id, test_user.id)
        with pytest.raises(ValueError, match="final"):
            await service.regenerate_draft(run.id, test_user.id)

    @pytest.mark.asyncio
    async def test_regenerate_bad_kind(self, db_session, test_user):
        service, run = await _pending_run(db_session, test_user)
        with pytest.raises(ValueError, match="Unsupported content kind"):
            await service.regenerate_draft(run.id, test_user.id, content_kind="poster")


class TestApprovalAudit:
    @pytest.mark.asyncio
    async def test_approve_records_audit(self, db_session, test_user):
        service, run = await _pending_run(db_session, test_user)
        approved = service.approve_run(run.id, test_user.id, notes="Ship it")
        assert approved.status.value == "approved"
        assert approved.reviewed_by == test_user.id
        assert approved.reviewed_at is not None
        assert approved.review_notes == "Ship it"


class TestApprovalAPI:
    def _run_id(self, client, auth_headers):
        create = client.post(
            "/api/career-content/pipeline/runs", headers=auth_headers,
            json={"source": "profile", "content_kind": "linkedin_post",
                  "platforms": ["linkedin"]},
        )
        assert create.status_code == 201, create.text
        return create.json()["id"]

    def test_edit_rescues_failed_run_end_to_end(self, client, auth_headers,
                                               db_session, test_user):
        from backend.models.profile import Profile as P
        db_session.add(P(user_id=test_user.id, headline="Backend Engineer",
                         bio="Ships Python APIs.", years_of_experience=5))
        db_session.commit()
        run_id = self._run_id(client, auth_headers)  # Mock LLM junk -> failed
        edited = client.post(
            f"/api/career-content/pipeline/runs/{run_id}/edit",
            headers=auth_headers, json={"text": GOOD_TEXT},
        )
        assert edited.status_code == 200, edited.text
        body = edited.json()
        assert body["status"] == "pending_review"
        assert body["stage_results"]["generation"]["text"] == GOOD_TEXT

        approved = client.post(
            f"/api/career-content/pipeline/runs/{run_id}/approve",
            headers=auth_headers, json={"notes": "good"},
        )
        assert approved.status_code == 200
        assert approved.json()["status"] == "approved"

        blocked = client.post(
            f"/api/career-content/pipeline/runs/{run_id}/edit",
            headers=auth_headers, json={"text": GOOD_TEXT},
        )
        assert blocked.status_code == 400

    def test_edit_missing_run_is_404(self, client, auth_headers):
        response = client.post(
            "/api/career-content/pipeline/runs/999999/edit",
            headers=auth_headers, json={"text": GOOD_TEXT},
        )
        assert response.status_code == 404

    def test_regenerate_missing_run_is_404(self, client, auth_headers):
        response = client.post(
            "/api/career-content/pipeline/runs/999999/regenerate",
            headers=auth_headers, json={},
        )
        assert response.status_code == 404
