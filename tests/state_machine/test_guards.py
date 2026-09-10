"""
Tests for central guards.

Message assertions pin the EXACT legacy strings: the publish/schedule/
review endpoints return these details to clients, so any wording change
is a contract break and must fail here first.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from backend.models.content_calendar import (
    ContentCalendar,
    ContentStatus,
    ContentType,
    SocialPlatform,
)
from backend.models.content_pipeline_run import (
    ContentKind,
    ContentPipelineRun,
    PipelineSource,
    PipelineStage,
)
from backend.state_machine.guards import (
    TransitionNotAllowed,
    allowed_targets,
    require_editable,
    require_publishable,
    require_regenerable,
    require_retryable,
    require_review_decision,
    require_schedulable,
    require_transition,
    to_http_status,
)


class TestGuardBasics:
    def test_error_is_value_error_compatible(self):
        # Existing callers catch ValueError/SchedulingError — must keep working.
        assert issubclass(TransitionNotAllowed, ValueError)
        exc = TransitionNotAllowed("content", "draft", "published", "nope")
        assert isinstance(exc, ValueError)
        assert str(exc) == "nope"
        assert (exc.machine, exc.current, exc.target) == ("content", "draft", "published")

    def test_require_transition(self):
        assert require_transition("content", "draft", "scheduled") == "draft"
        with pytest.raises(TransitionNotAllowed):
            require_transition("content", "draft", "published")

    def test_to_http_status_is_400(self):
        exc = TransitionNotAllowed("content", "draft", "published", "nope")
        assert to_http_status(exc) == 400

    def test_allowed_targets_alias(self):
        assert allowed_targets("content", "failed") == frozenset({"retry", "scheduled"})

    def test_raw_strings_and_enums_agree(self):
        assert require_schedulable(ContentStatus.DRAFT) == require_schedulable("draft") == "draft"


class TestScheduleAndRetryGuards:
    @pytest.mark.parametrize("status", ["pending", "draft", "retry", "scheduled",
                                        ContentStatus.PENDING, ContentStatus.SCHEDULED])
    def test_schedulable_accepts(self, status):
        require_schedulable(status)

    @pytest.mark.parametrize("status", ["published", "failed", "cancelled"])
    def test_schedulable_rejects_with_legacy_message(self, status):
        with pytest.raises(TransitionNotAllowed, match=r"^Cannot schedule content with status="):
            require_schedulable(status)
        with pytest.raises(ValueError):  # legacy handler compatibility
            require_schedulable(status)

    def test_retryable_accepts_failed(self):
        assert require_retryable("failed") == "failed"
        assert require_retryable(ContentStatus.FAILED) == "failed"

    def test_retryable_rejects_with_legacy_message(self):
        with pytest.raises(TransitionNotAllowed,
                           match=r"^Only FAILED content can be retried \(status=scheduled\)$"):
            require_retryable("scheduled")


class TestPublishGuard:
    def test_unlinked_schedulable_passes(self):
        assert require_publishable(item_status="scheduled") == "scheduled"
        assert require_publishable(item_status=ContentStatus.RETRY) == "retry"

    @pytest.mark.parametrize("status", ["draft", "pending", "published", "failed", "cancelled"])
    def test_unlinked_blocks_with_legacy_message(self, status):
        with pytest.raises(TransitionNotAllowed) as exc_info:
            require_publishable(item_status=status)
        assert str(exc_info.value) == f"Schedule the content first (status={status})"

    def test_linked_approved_passes(self):
        assert require_publishable(run_status="approved") == "approved"
        assert require_publishable(run_status=PipelineStage.APPROVED) == "approved"

    @pytest.mark.parametrize("status", ["pending_review", "rejected", "failed", "draft"])
    def test_linked_unapproved_blocks_with_legacy_message(self, status):
        with pytest.raises(TransitionNotAllowed) as exc_info:
            require_publishable(run_status=status)
        assert str(exc_info.value) == f"Only APPROVED content can be published (run status={status})"


class TestReviewGuards:
    def test_decision_requires_pending_review(self):
        assert require_review_decision("pending_review") == "pending_review"
        with pytest.raises(TransitionNotAllowed) as exc_info:
            require_review_decision("approved")
        assert str(exc_info.value) == "Run is not awaiting review (status=approved)"

    def test_editable_states(self):
        assert require_editable("pending_review") == "pending_review"
        assert require_editable("failed") == "failed"
        with pytest.raises(TransitionNotAllowed) as exc_info:
            require_editable("approved")
        assert str(exc_info.value) == "Run cannot be edited (status=approved; approved runs are final)"
        with pytest.raises(TransitionNotAllowed) as exc_info:
            require_editable("rejected")
        assert str(exc_info.value) == "Run cannot be edited (status=rejected)"

    def test_regenerable_states(self):
        for ok in ("pending_review", "failed", "rejected"):
            assert require_regenerable(ok) == ok
        with pytest.raises(TransitionNotAllowed) as exc_info:
            require_regenerable("approved")
        assert str(exc_info.value) == (
            "Run cannot be regenerated (status=approved; approved runs are final)")


def _calendar_item(db_session, user_id, **kwargs):
    params = dict(user_id=user_id, title="t", content="c",
                  content_type=ContentType.POST, platform=SocialPlatform.FACEBOOK)
    params.update(kwargs)
    item = ContentCalendar(**params)
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


def _pipeline_run(db_session, user_id, status):
    run = ContentPipelineRun(
        user_id=user_id, source=PipelineSource.PROFILE, content_kind=ContentKind.EDUCATIONAL,
        platforms=["facebook"], status=status, current_stage=status.value,
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    return run


class TestApiGateDelegation:
    """The content_calendar publish gate delegates with an unchanged contract."""

    def test_draft_refused_400_not_500(self, db_session, test_user):
        from backend.api.content_calendar import _require_publishable

        item = _calendar_item(db_session, test_user.id, status=ContentStatus.DRAFT)
        with pytest.raises(HTTPException) as exc_info:
            _require_publishable(db_session, test_user.id, item)
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Schedule the content first (status=draft)"

    def test_scheduled_passes(self, db_session, test_user):
        from backend.api.content_calendar import _require_publishable

        item = _calendar_item(db_session, test_user.id, status=ContentStatus.SCHEDULED)
        assert _require_publishable(db_session, test_user.id, item) is None

    def test_missing_run_is_404(self, db_session, test_user):
        from backend.api.content_calendar import _require_publishable

        item = _calendar_item(db_session, test_user.id,
                              status=ContentStatus.SCHEDULED, pipeline_run_id=999999)
        with pytest.raises(HTTPException) as exc_info:
            _require_publishable(db_session, test_user.id, item)
        assert exc_info.value.status_code == 404

    def test_unapproved_run_refused(self, db_session, test_user):
        from backend.api.content_calendar import _require_publishable

        run = _pipeline_run(db_session, test_user.id, PipelineStage.PENDING_REVIEW)
        item = _calendar_item(db_session, test_user.id,
                              status=ContentStatus.SCHEDULED, pipeline_run_id=run.id)
        with pytest.raises(HTTPException) as exc_info:
            _require_publishable(db_session, test_user.id, item)
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == (
            "Only APPROVED content can be published (run status=pending_review)")

    def test_approved_run_passes(self, db_session, test_user):
        from backend.api.content_calendar import _require_publishable

        run = _pipeline_run(db_session, test_user.id, PipelineStage.APPROVED)
        item = _calendar_item(db_session, test_user.id,
                              status=ContentStatus.SCHEDULED, pipeline_run_id=run.id)
        assert _require_publishable(db_session, test_user.id, item) is None
