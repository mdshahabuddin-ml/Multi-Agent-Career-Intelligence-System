"""Content scheduler (scheduling only — no publishing).

Owns the scheduling state machine for calendar items:

    PENDING → SCHEDULED → (dispatcher, later) → PUBLISHED / FAILED
    FAILED → RETRY → SCHEDULED ...

Rules enforced here:
- Only APPROVED pipeline runs can seed scheduled items (checked at
  schedule time for linked items; legacy unlinked items keep working).
- Rejected runs, drafts, and failed verification can never be scheduled.
- No duplicate active items for the same (run, platform).
- Scheduling is idempotent: repeating the same assignment is a no-op.
- Publishing itself is out of scope: ``run()`` executes an injected
  executor callable (a mock in tests); ``run_dry()`` changes nothing.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.models.content_calendar import ContentCalendar, ContentStatus, SocialPlatform
from backend.models.content_pipeline_run import ContentPipelineRun, PipelineStage

logger = logging.getLogger(__name__)

# An item in one of these states already covers (run, platform).
ACTIVE_STATUSES = (
    ContentStatus.PENDING,
    ContentStatus.SCHEDULED,
    ContentStatus.RETRY,
    ContentStatus.PUBLISHED,
    ContentStatus.DRAFT,
)

# States from which a date/time may be (re)assigned. SCHEDULED is included
# so replays and reschedules stay idempotent-safe single-row updates.
SCHEDULABLE_STATUSES = (
    ContentStatus.PENDING,
    ContentStatus.DRAFT,
    ContentStatus.RETRY,
    ContentStatus.SCHEDULED,
)


class SchedulingError(ValueError):
    """Scheduling rule violation (caller maps to 4xx)."""


class DuplicateScheduleError(SchedulingError):
    """An active item already covers this (run, platform)."""


class ContentScheduler:
    """Schedule approved content; dry-run or mock-executor dispatch."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _item(self, user_id: int, content_id: int) -> ContentCalendar:
        item = (
            self.db.query(ContentCalendar)
            .filter(ContentCalendar.id == content_id, ContentCalendar.user_id == user_id)
            .first()
        )
        if not item:
            raise SchedulingError("Content not found")
        return item

    def _approved_run(self, user_id: int, run_id: int) -> ContentPipelineRun:
        run = (
            self.db.query(ContentPipelineRun)
            .filter(ContentPipelineRun.id == run_id, ContentPipelineRun.user_id == user_id)
            .first()
        )
        if not run:
            raise SchedulingError("Pipeline run not found")
        status = run.status.value if isinstance(run.status, PipelineStage) else str(run.status)
        if status != PipelineStage.APPROVED.value:
            raise SchedulingError(
                f"Only APPROVED content can be scheduled (run status={status})"
            )
        return run

    def _existing_cover(
        self, user_id: int, run_id: int, platform: SocialPlatform
    ) -> Optional[ContentCalendar]:
        return (
            self.db.query(ContentCalendar)
            .filter(
                ContentCalendar.user_id == user_id,
                ContentCalendar.pipeline_run_id == run_id,
                ContentCalendar.platform == platform,
                ContentCalendar.status.in_(ACTIVE_STATUSES),
            )
            .first()
        )

    @staticmethod
    def _snapshot_from_run(run: ContentPipelineRun, platform: SocialPlatform) -> Dict[str, Any]:
        """Extract title/content/hashtags for one platform from a run."""
        results = run.stage_results or {}
        variants = results.get("formatting", {}).get("variants", {})
        variant = variants.get(platform.value if isinstance(platform, SocialPlatform) else platform, {})
        topic = results.get("topic_selection", {}).get("selected", {}).get("topic")
        kind = run.content_kind.value if hasattr(run.content_kind, "value") else str(run.content_kind)
        text = (variant.get("text") if isinstance(variant, dict) else "") or ""
        caption = variant.get("caption", {}) if isinstance(variant, dict) else {}
        hashtags = list(variant.get("hashtags", []) if isinstance(variant, dict) else [])
        title = (variant.get("title") if isinstance(variant, dict) else None) or topic or f"{kind}"
        return {
            "title": str(title)[:255],
            "content": text,
            "platform_specific_data": {
                "caption": caption,
                "variant_kind": (variant.get("kind") if isinstance(variant, dict) else None),
                "pipeline_run_id": run.id,
                "content_kind": kind,
            },
            "hashtags": hashtags,
        }

    # ------------------------------------------------------------------
    # Schedule from an approved run (the sanctioned path)
    # ------------------------------------------------------------------
    def schedule_from_run(
        self,
        user_id: int,
        run_id: int,
        platform: SocialPlatform,
        scheduled_at: Optional[datetime] = None,
    ) -> ContentCalendar:
        """Create a PENDING (no time) or SCHEDULED calendar item from a run."""
        run = self._approved_run(user_id, run_id)
        if self._existing_cover(user_id, run_id, platform):
            raise DuplicateScheduleError(
                f"Run {run_id} already has an active {platform.value} schedule"
            )
        snapshot = self._snapshot_from_run(run, platform)
        item = ContentCalendar(
            user_id=user_id,
            pipeline_run_id=run_id,
            title=snapshot["title"],
            content=snapshot["content"],
            content_type="post",
            platform=platform,
            platform_specific_data=snapshot["platform_specific_data"],
            hashtags=snapshot["hashtags"],
            status=ContentStatus.SCHEDULED if scheduled_at else ContentStatus.PENDING,
            scheduled_at=scheduled_at,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        logger.info("Scheduled run %s -> %s item %s", run_id, platform.value, item.id)
        return item

    # ------------------------------------------------------------------
    # Assign / reassign a slot (idempotent)
    # ------------------------------------------------------------------
    def assign_slot(
        self, user_id: int, content_id: int, scheduled_at: datetime
    ) -> ContentCalendar:
        """Move a PENDING/DRAFT/RETRY item to SCHEDULED at the given time."""
        item = self._item(user_id, content_id)
        status = item.status
        status_value = status.value if isinstance(status, ContentStatus) else str(status)
        allowed = {s.value for s in SCHEDULABLE_STATUSES}
        if status_value not in allowed:
            raise SchedulingError(f"Cannot schedule content with status={status_value}")
        if item.pipeline_run_id is not None:
            self._approved_run(user_id, item.pipeline_run_id)
        if item.scheduled_at == scheduled_at:
            return item  # idempotent replay: same slot, no state change
        item.scheduled_at = scheduled_at
        item.status = ContentStatus.SCHEDULED
        item.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(item)
        return item

    # ------------------------------------------------------------------
    # Retry a failed item
    # ------------------------------------------------------------------
    def request_retry(
        self, user_id: int, content_id: int, scheduled_at: Optional[datetime] = None
    ) -> ContentCalendar:
        """Move a FAILED item to RETRY (or straight to SCHEDULED with a time)."""
        item = self._item(user_id, content_id)
        status_value = item.status.value if isinstance(item.status, ContentStatus) else str(item.status)
        if status_value != ContentStatus.FAILED.value:
            raise SchedulingError(f"Only FAILED content can be retried (status={status_value})")
        if item.pipeline_run_id is not None:
            self._approved_run(user_id, item.pipeline_run_id)
        item.retry_count = (item.retry_count or 0) + 1
        item.error_message = None
        if scheduled_at is not None:
            item.scheduled_at = scheduled_at
            item.status = ContentStatus.SCHEDULED
        else:
            item.status = ContentStatus.RETRY
        item.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(item)
        return item

    # ------------------------------------------------------------------
    # Due selection + dry-run + mock-executor dispatch
    # ------------------------------------------------------------------
    def due_items(self, user_id: int, now: Optional[datetime] = None) -> List[ContentCalendar]:
        """Items ready for dispatch: SCHEDULED due, or RETRY awaiting a slot."""
        now = now or datetime.utcnow()
        return (
            self.db.query(ContentCalendar)
            .filter(
                ContentCalendar.user_id == user_id,
                ContentCalendar.status.in_([ContentStatus.SCHEDULED, ContentStatus.RETRY]),
            )
            .filter(
                (ContentCalendar.status == ContentStatus.RETRY)
                | (ContentCalendar.scheduled_at <= now)
            )
            .order_by(ContentCalendar.scheduled_at.asc().nullsfirst(), ContentCalendar.id.asc())
            .all()
        )

    def run_dry(self, user_id: int, now: Optional[datetime] = None) -> Dict[str, Any]:
        """Report what WOULD be dispatched without changing anything."""
        due = self.due_items(user_id, now)
        return {
            "due": [
                {"id": item.id, "platform": item.platform.value, "scheduled_at": (
                    item.scheduled_at.isoformat() if item.scheduled_at else None
                )}
                for item in due
            ],
            "actions": [
                f"publish item {item.id} to {item.platform.value} (dry-run)"
                for item in due
            ],
            "changed": 0,
        }

    def run(
        self,
        user_id: int,
        executor: Callable[[ContentCalendar], Dict[str, Any]],
        now: Optional[datetime] = None,
        max_attempts: int = 3,
    ) -> Dict[str, Any]:
        """Dispatch due items through an injected executor (mock in tests).

        The executor performs the platform call; on success the item is
        marked PUBLISHED (recording platform_post_id/url when returned),
        on exception FAILED with the error recorded. No network I/O happens
        here — without a real executor this must not be used in production.
        Items at or above ``max_attempts`` are skipped (never retried
        indefinitely); only an explicit human retry re-queues them.
        """
        due = self.due_items(user_id, now)
        published, failed, skipped = 0, 0, 0
        for item in due:
            if (item.retry_count or 0) >= max_attempts:
                skipped += 1
                continue
            try:
                outcome = executor(item) or {}
            except Exception as exc:
                item.status = ContentStatus.FAILED
                item.error_message = str(exc)[:2000]
                item.retry_count = (item.retry_count or 0) + 1
                item.updated_at = datetime.utcnow()
                failed += 1
                continue
            item.status = ContentStatus.PUBLISHED
            item.published_at = datetime.utcnow()
            item.updated_at = datetime.utcnow()
            if isinstance(outcome, dict):
                if outcome.get("platform_post_id"):
                    item.platform_post_id = str(outcome["platform_post_id"])[:255]
                if outcome.get("platform_post_url"):
                    item.platform_post_url = str(outcome["platform_post_url"])[:500]
            published += 1
        self.db.commit()
        return {"due": len(due), "published": published, "failed": failed, "skipped": skipped}
