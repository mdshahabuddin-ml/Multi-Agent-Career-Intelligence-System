"""Tests for content scheduling (no publishing).

Rules under test: only APPROVED runs schedule; rejected/draft runs never;
no duplicate (run, platform) items; idempotent slot assignment; FAILED ->
RETRY -> SCHEDULED; dry-run changes nothing; mock-executor dispatch marks
PUBLISHED/FAILED without any network I/O.
"""

from datetime import datetime, timedelta

import pytest

from backend.models.content_calendar import ContentCalendar, ContentStatus, SocialPlatform
from backend.models.content_pipeline_run import ContentKind, PipelineSource, PipelineStage
from backend.models.profile import Profile
from backend.providers.llm.base import LLMConfig
from backend.providers.llm.mock import MockProvider
from backend.providers.search.mock import MockSearchProvider
from backend.services.career_content_service import CareerContentService
from backend.services.content_scheduler import ContentScheduler, DuplicateScheduleError

GOOD_TEXT = (
    "Scheduling check: our Python backend crew refactored the billing service "
    "together and cut deploy times with careful testing and thorough reviews."
)
FUTURE = datetime.utcnow() + timedelta(days=2)


def _service(db_session, text=GOOD_TEXT):
    return CareerContentService(
        db_session, llm_provider=MockProvider(LLMConfig(model="mock"), responses=[text]),
        search_provider=MockSearchProvider(),
    )


async def _approved_run(db_session, test_user):
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
    assert run.status.value == "approved" or run.status.value == "pending_review"
    if run.status.value != "approved":
        run = service.approve_run(run.id, test_user.id)
    return run


def _scheduler(db_session):
    return ContentScheduler(db_session)


class TestScheduleFromApproved:
    @pytest.mark.asyncio
    async def test_pending_without_time(self, db_session, test_user):
        run = await _approved_run(db_session, test_user)
        item = _scheduler(db_session).schedule_from_run(
            test_user.id, run.id, SocialPlatform.LINKEDIN)
        assert item.status == ContentStatus.PENDING
        assert item.scheduled_at is None
        assert item.pipeline_run_id == run.id
        assert item.content

    @pytest.mark.asyncio
    async def test_scheduled_with_time(self, db_session, test_user):
        run = await _approved_run(db_session, test_user)
        item = _scheduler(db_session).schedule_from_run(
            test_user.id, run.id, SocialPlatform.LINKEDIN, FUTURE)
        assert item.status == ContentStatus.SCHEDULED
        assert item.scheduled_at is not None

    @pytest.mark.asyncio
    async def test_rejected_run_never_schedules(self, db_session, test_user):
        db_session.add(Profile(user_id=test_user.id, headline="Backend Engineer",
                               bio="Ships Python APIs.", years_of_experience=5))
        db_session.commit()
        service = _service(db_session)
        run = await service.run_pipeline(
            user_id=test_user.id, source=PipelineSource.PROFILE,
            content_kind=ContentKind.LINKEDIN_POST, platforms=["linkedin"])
        assert run.status.value == "pending_review"
        service.reject_run(run.id, test_user.id)
        with pytest.raises(ValueError, match="Only APPROVED"):
            _scheduler(db_session).schedule_from_run(
                test_user.id, run.id, SocialPlatform.INSTAGRAM)

    @pytest.mark.asyncio
    async def test_duplicate_rejected(self, db_session, test_user):
        run = await _approved_run(db_session, test_user)
        scheduler = _scheduler(db_session)
        scheduler.schedule_from_run(test_user.id, run.id, SocialPlatform.LINKEDIN)
        with pytest.raises(DuplicateScheduleError):
            scheduler.schedule_from_run(test_user.id, run.id, SocialPlatform.LINKEDIN)
        # Different platform is fine.
        other = scheduler.schedule_from_run(test_user.id, run.id, SocialPlatform.INSTAGRAM)
        assert other.id is not None
        assert db_session.query(ContentCalendar).filter_by(pipeline_run_id=run.id).count() == 2

    def test_missing_run(self, db_session, test_user):
        with pytest.raises(ValueError, match="not found"):
            _scheduler(db_session).schedule_from_run(
                test_user.id, 999999, SocialPlatform.LINKEDIN)


class TestAssignSlot:
    @pytest.mark.asyncio
    async def test_pending_to_scheduled_idempotent(self, db_session, test_user):
        run = await _approved_run(db_session, test_user)
        scheduler = _scheduler(db_session)
        item = scheduler.schedule_from_run(test_user.id, run.id, SocialPlatform.LINKEDIN)
        first = scheduler.assign_slot(test_user.id, item.id, FUTURE)
        assert first.status == ContentStatus.SCHEDULED
        again = scheduler.assign_slot(test_user.id, item.id, FUTURE)
        assert again.status == ContentStatus.SCHEDULED
        assert again.retry_count == 0
        assert db_session.query(ContentCalendar).count() == 1

    def test_legacy_unlinked_draft_schedulable(self, db_session, test_user):
        item = ContentCalendar(
            user_id=test_user.id, title="Legacy", content="Old post",
            platform=SocialPlatform.LINKEDIN, status=ContentStatus.DRAFT,
        )
        db_session.add(item)
        db_session.commit()
        scheduled = _scheduler(db_session).assign_slot(test_user.id, item.id, FUTURE)
        assert scheduled.status == ContentStatus.SCHEDULED

    def test_published_slot_rejected(self, db_session, test_user):
        item = ContentCalendar(
            user_id=test_user.id, title="Out", content="Posted",
            platform=SocialPlatform.LINKEDIN, status=ContentStatus.PUBLISHED,
        )
        db_session.add(item)
        db_session.commit()
        with pytest.raises(ValueError):
            _scheduler(db_session).assign_slot(test_user.id, item.id, FUTURE)


class TestRetry:
    def _failed(self, db_session, test_user):
        item = ContentCalendar(
            user_id=test_user.id, title="Flop", content="x",
            platform=SocialPlatform.LINKEDIN, status=ContentStatus.FAILED,
            error_message="boom",
        )
        db_session.add(item)
        db_session.commit()
        return item

    def test_failed_to_retry(self, db_session, test_user):
        item = self._failed(db_session, test_user)
        retried = _scheduler(db_session).request_retry(test_user.id, item.id)
        assert retried.status == ContentStatus.RETRY
        assert retried.retry_count == 1
        assert retried.error_message is None

    def test_retry_with_slot_schedules(self, db_session, test_user):
        item = self._failed(db_session, test_user)
        scheduled = _scheduler(db_session).request_retry(test_user.id, item.id, FUTURE)
        assert scheduled.status == ContentStatus.SCHEDULED
        assert scheduled.retry_count == 1

    def test_retry_non_failed_rejected(self, db_session, test_user):
        item = ContentCalendar(
            user_id=test_user.id, title="Draft", content="x",
            platform=SocialPlatform.LINKEDIN, status=ContentStatus.DRAFT,
        )
        db_session.add(item)
        db_session.commit()
        with pytest.raises(ValueError):
            _scheduler(db_session).request_retry(test_user.id, item.id)


class TestDispatch:
    def _due_item(self, db_session, test_user, when):
        item = ContentCalendar(
            user_id=test_user.id, title="Due", content="go",
            platform=SocialPlatform.LINKEDIN, status=ContentStatus.SCHEDULED,
            scheduled_at=when,
        )
        db_session.add(item)
        db_session.commit()
        return item

    def test_dry_run_changes_nothing(self, db_session, test_user):
        past = datetime.utcnow() - timedelta(hours=1)
        item = self._due_item(db_session, test_user, past)
        report = _scheduler(db_session).run_dry(test_user.id)
        assert report["changed"] == 0
        assert [d["id"] for d in report["due"]] == [item.id]
        assert report["actions"]
        db_session.refresh(item)
        assert item.status == ContentStatus.SCHEDULED

    def test_future_not_due(self, db_session, test_user):
        self._due_item(db_session, test_user, FUTURE)
        assert _scheduler(db_session).run_dry(test_user.id)["due"] == []

    def test_mock_executor_success_and_failure(self, db_session, test_user):
        past = datetime.utcnow() - timedelta(hours=1)
        good = self._due_item(db_session, test_user, past)
        bad = self._due_item(db_session, test_user, past)

        def executor(item):
            if item.id == bad.id:
                raise RuntimeError("platform exploded")
            return {"platform_post_id": "post-123", "platform_post_url": "https://x/post-123"}

        summary = _scheduler(db_session).run(test_user.id, executor)
        assert summary == {"due": 2, "published": 1, "failed": 1, "skipped": 0}
        db_session.refresh(good)
        db_session.refresh(bad)
        assert good.status == ContentStatus.PUBLISHED
        assert good.platform_post_id == "post-123"
        assert good.published_at is not None
        assert bad.status == ContentStatus.FAILED
        assert "exploded" in (bad.error_message or "")
        assert bad.retry_count == 1


class TestSchedulingAPI:
    def _approved_id(self, client, auth_headers, db_session, test_user):
        from backend.models.profile import Profile as P
        db_session.add(P(user_id=test_user.id, headline="Backend Engineer",
                         bio="Ships Python APIs.", years_of_experience=5))
        db_session.commit()
        create = client.post(
            "/api/career-content/pipeline/runs", headers=auth_headers,
            json={"source": "profile", "content_kind": "linkedin_post",
                  "platforms": ["linkedin"]},
        )
        assert create.status_code == 201
        run_id = create.json()["id"]
        # Keyless environments resolve generation to Mock output, which the
        # quality gate rightly fails; a human edit rescues it to review.
        edited = client.post(
            f"/api/career-content/pipeline/runs/{run_id}/edit",
            headers=auth_headers, json={"text": GOOD_TEXT},
        )
        assert edited.status_code == 200
        approved = client.post(
            f"/api/career-content/pipeline/runs/{run_id}/approve",
            headers=auth_headers, json={"notes": "ok"},
        )
        assert approved.status_code == 200
        return run_id

    def test_from_approved_schedule_retry_flow(self, client, auth_headers, db_session, test_user):
        run_id = self._approved_id(client, auth_headers, db_session, test_user)
        created = client.post(
            "/api/content-calendar/from-approved", headers=auth_headers,
            json={"pipeline_run_id": run_id, "platform": "linkedin"},
        )
        assert created.status_code == 201, created.text
        assert created.json()["status"] == "pending"
        item_id = created.json()["id"]

        dup = client.post(
            "/api/content-calendar/from-approved", headers=auth_headers,
            json={"pipeline_run_id": run_id, "platform": "linkedin"},
        )
        assert dup.status_code == 409

        scheduled = client.post(
            f"/api/content-calendar/{item_id}/schedule",
            headers=auth_headers, params={"scheduled_at": FUTURE.isoformat()},
        )
        assert scheduled.status_code == 200
        assert scheduled.json()["status"] == "scheduled"

        again = client.post(
            f"/api/content-calendar/{item_id}/schedule",
            headers=auth_headers, params={"scheduled_at": FUTURE.isoformat()},
        )
        assert again.status_code == 200

    def test_rejected_run_rejected(self, client, auth_headers, db_session, test_user):
        from backend.models.profile import Profile as P
        db_session.add(P(user_id=test_user.id, headline="E", bio="Ships Python APIs."))
        db_session.commit()
        create = client.post(
            "/api/career-content/pipeline/runs", headers=auth_headers,
            json={"source": "profile", "content_kind": "linkedin_post",
                  "platforms": ["linkedin"]},
        )
        run_id = create.json()["id"]
        client.post(
            f"/api/career-content/pipeline/runs/{run_id}/edit",
            headers=auth_headers, json={"text": GOOD_TEXT})
        client.post(f"/api/career-content/pipeline/runs/{run_id}/reject",
                    headers=auth_headers, json={})
        denied = client.post(
            "/api/content-calendar/from-approved", headers=auth_headers,
            json={"pipeline_run_id": run_id, "platform": "linkedin"},
        )
        assert denied.status_code == 400

    def test_patch_published_blocked(self, client, auth_headers, db_session, test_user):
        run_id = self._approved_id(client, auth_headers, db_session, test_user)
        created = client.post(
            "/api/content-calendar/from-approved", headers=auth_headers,
            json={"pipeline_run_id": run_id, "platform": "linkedin"},
        )
        item_id = created.json()["id"]
        forced = client.patch(
            f"/api/content-calendar/{item_id}", headers=auth_headers,
            json={"status": "published"},
        )
        assert forced.status_code == 400
