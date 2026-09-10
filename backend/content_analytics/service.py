"""
ContentAnalyticsService — Published Content → Analytics orchestration.

Isolation: imports ONLY content/social models + official-API providers.
Never touches career tables or career services.

DB mapping note: the legacy ``content_analytics`` columns are NOT NULL
integers, so unsupported metrics persist as 0. The service converts back
to ``None`` on read via the capability matrix (``to_public_snapshot``),
so API consumers always see ``None`` = unsupported, never a fake zero.
``raw_data`` preserves the audit trail (supported/unsupported lists +
provider payload summary).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.content_analytics.analysis import compute_ctr, compute_engagement_rate
from backend.content_analytics.capabilities import (
    is_metric_supported,
    supported_metrics_for,
    unsupported_metrics_for,
)
from backend.content_analytics.providers import (
    AnalyticsAuthError,
    AnalyticsError,
    AnalyticsUnsupportedError,
    fetch_metrics,
)
from backend.content_analytics.schemas import MetricSnapshot, PublishedContentItem
from backend.models.content_calendar import ContentAnalytics, ContentCalendar, ContentStatus, SocialPlatform
from backend.observability import span
from backend.observability.conventions import (
    ATTR_FLOW,
    ATTR_LAYER,
    ATTR_PLATFORM,
    LAYER_SOCIAL,
    SPAN_KIND_TOOL,
)

logger = logging.getLogger(__name__)

REMOTE_METRICS = ("views", "impressions", "likes", "comments", "shares", "saves", "clicks", "reach")


def _platform_str(value: Any) -> str:
    return value.value if isinstance(value, SocialPlatform) else str(value or "").lower()


def _status_str(value: Any) -> str:
    return value.value if isinstance(value, ContentStatus) else str(value or "")


class ContentAnalyticsService:
    """Fetch official-API snapshots and serve the analytics pipeline stages."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Published Content stage (publishing status — always local)
    # ------------------------------------------------------------------
    def list_published(
        self,
        user_id: int,
        platform: Optional[str] = None,
        limit: int = 50,
        include_failed: bool = True,
    ) -> List[ContentCalendar]:
        """Published (and attempted) content ordered by recency.

        Includes PUBLISHED plus FAILED/CANCELLED so publishing status —
        including failures — stays visible. Drafts/scheduled items are not
        analytics subjects yet.
        """
        statuses = [ContentStatus.PUBLISHED]
        if include_failed:
            statuses += [ContentStatus.FAILED, ContentStatus.CANCELLED]
        query = self.db.query(ContentCalendar).filter(
            ContentCalendar.user_id == user_id,
            ContentCalendar.status.in_(statuses),
        )
        if platform:
            try:
                query = query.filter(ContentCalendar.platform == SocialPlatform(platform.lower()))
            except ValueError:
                return []
        return (
            query.order_by(ContentCalendar.published_at.desc().nullslast(), ContentCalendar.id.desc())
            .limit(max(1, min(limit, 200)))
            .all()
        )

    def get_owned(self, user_id: int, content_id: int) -> Optional[ContentCalendar]:
        return (
            self.db.query(ContentCalendar)
            .filter(ContentCalendar.id == content_id, ContentCalendar.user_id == user_id)
            .first()
        )

    # ------------------------------------------------------------------
    # Token handling (official OAuth tokens only)
    # ------------------------------------------------------------------
    def _access_token_for(self, user_id: int, platform: str) -> str:
        """Decrypt the stored OAuth token, refreshing once when expired."""
        from backend.models.social_account import SocialAccount

        account = (
            self.db.query(SocialAccount)
            .filter(
                SocialAccount.user_id == user_id,
                SocialAccount.platform == platform.lower(),
                SocialAccount.enabled == True,  # noqa: E712 - SQLAlchemy expression
            )
            .order_by(SocialAccount.id)
            .first()
        )
        if not account or not account.access_token:
            raise AnalyticsUnsupportedError(platform, f"no connected {platform} account — tracking publishing status only")
        from backend.social_integrations.token_crypto import TokenDecryptionError, decrypt_token

        try:
            current = decrypt_token(account.access_token)
        except TokenDecryptionError as exc:
            raise AnalyticsUnsupportedError(platform, f"{exc}; please reconnect the account") from exc
        expired = bool(account.token_expires_at and account.token_expires_at <= datetime.now(timezone.utc).replace(tzinfo=None))
        if expired:
            # Best-effort single refresh; failure degrades to status-only, never scrapes.
            try:
                from backend.services.social_account_service import SocialAccountService
                import asyncio

                async def _refresh() -> None:
                    await SocialAccountService(self.db).refresh_account(user_id, account.id)

                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None
                if loop and loop.is_running():
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                        pool.submit(asyncio.run, _refresh()).result()
                else:
                    asyncio.run(_refresh())
                self.db.refresh(account)
                current = decrypt_token(account.access_token or "")
            except Exception as exc:  # noqa: BLE001 - degrade gracefully
                logger.info("Analytics token refresh failed for %s: %s", platform, exc)
        return current

    # ------------------------------------------------------------------
    # Analytics stage (official-API snapshots → ContentAnalytics rows)
    # ------------------------------------------------------------------
    async def refresh_snapshot(self, user_id: int, content_id: int) -> MetricSnapshot:
        """Fetch one post's official metrics and persist a snapshot row."""
        item = self.get_owned(user_id, content_id)
        if not item:
            raise AnalyticsError("content", "content not found")
        platform = _platform_str(item.platform)
        if _status_str(item.status) != ContentStatus.PUBLISHED.value:
            raise AnalyticsUnsupportedError(platform, f"content status is {_status_str(item.status)} — publish first")
        if not item.platform_post_id:
            raise AnalyticsUnsupportedError(platform, "post has no platform_post_id (publish record incomplete)")

        access_token = self._access_token_for(user_id, platform)
        # Observability span (no-op unless OTEL_ENABLED=true); never affects logic.
        async with span("content_analytics.refresh_snapshot", kind=SPAN_KIND_TOOL, attributes={
            ATTR_LAYER: LAYER_SOCIAL, ATTR_FLOW: "analytics_refresh",
            ATTR_PLATFORM: platform, "content_id": content_id,
        }):
            try:
                fetched = await fetch_metrics(platform, access_token, item.platform_post_id)
            except AnalyticsAuthError:
                # Exactly one refresh-and-retry, mirroring publishing_service.
                logger.info("Analytics token rejected for %s; refreshing once", platform)
                try:
                    from backend.services.social_account_service import SocialAccountService
                    from backend.models.social_account import SocialAccount

                    account = (
                        self.db.query(SocialAccount)
                        .filter(SocialAccount.user_id == user_id, SocialAccount.platform == platform.lower())
                        .order_by(SocialAccount.id)
                        .first()
                    )
                    if account:
                        await SocialAccountService(self.db).refresh_account(user_id, account.id)
                        self.db.refresh(account)
                        from backend.social_integrations.token_crypto import decrypt_token

                        access_token = decrypt_token(account.access_token or "")
                        fetched = await fetch_metrics(platform, access_token, item.platform_post_id)
                    else:
                        raise
                except AnalyticsError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    raise AnalyticsAuthError(platform, f"token refresh failed: {exc}") from exc

        return self._persist_snapshot(item, fetched)

    async def refresh_bulk(self, user_id: int, content_ids: Optional[List[int]] = None,
                           max_items: int = 20) -> Dict[str, Any]:
        """Refresh up to ``max_items`` published posts; per-post errors never abort the batch."""
        if content_ids:
            items = [self.get_owned(user_id, cid) for cid in content_ids[:max_items]]
            items = [i for i in items if i is not None]
        else:
            items = self.list_published(user_id, limit=max_items, include_failed=False)
        refreshed: List[MetricSnapshot] = []
        failed: List[Dict[str, str]] = []
        for item in items:
            try:
                refreshed.append(await self.refresh_snapshot(user_id, item.id))
            except AnalyticsError as exc:
                failed.append({"content_id": str(item.id), "error": str(exc)})
            except Exception as exc:  # noqa: BLE001 - batch must not abort
                failed.append({"content_id": str(item.id), "error": f"unexpected: {exc}"})
        return {"refreshed": refreshed, "failed": failed,
                "refreshed_count": len(refreshed), "failed_count": len(failed)}

    def _persist_snapshot(self, item: ContentCalendar, fetched: Dict[str, Any]) -> MetricSnapshot:
        platform = _platform_str(item.platform)
        engagement = compute_engagement_rate(fetched)
        ctr = compute_ctr(fetched)
        row = ContentAnalytics(
            content_id=item.id,
            user_id=item.user_id,
            platform=item.platform if isinstance(item.platform, SocialPlatform) else SocialPlatform(platform),
            platform_post_id=item.platform_post_id or fetched.get("platform_post_id", ""),
            # Legacy NOT NULL columns: unsupported (None) persists as 0; read path restores None.
            views=fetched.get("views") or 0,
            likes=fetched.get("likes") or 0,
            comments=fetched.get("comments") or 0,
            shares=fetched.get("shares") or 0,
            saves=fetched.get("saves") or 0,
            clicks=fetched.get("clicks") or 0,
            impressions=fetched.get("impressions") or 0,
            reach=fetched.get("reach") or 0,
            watch_time_seconds=0,
            average_watch_time=0.0,
            completion_rate=0.0,
            engagement_rate=engagement or 0.0,
            click_through_rate=ctr or 0.0,
            raw_data={
                "source": "official_api",
                "supported_metrics": fetched.get("supported_metrics", []),
                "unsupported_metrics": fetched.get("unsupported_metrics", []),
                "provider": fetched.get("raw", {}),
            },
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self.to_public_snapshot(row)

    # ------------------------------------------------------------------
    # Read paths (DB → public schemas, unsupported restored to None)
    # ------------------------------------------------------------------
    def to_public_snapshot(self, row: ContentAnalytics) -> MetricSnapshot:
        platform = _platform_str(row.platform)

        def _pub(field: str, stored: Any) -> Optional[int]:
            if not is_metric_supported(platform, field):
                return None
            try:
                return int(stored)
            except (TypeError, ValueError):
                return None

        def _pub_float(field: str, stored: Any) -> Optional[float]:
            if not is_metric_supported(platform, field):
                return None
            try:
                return float(stored)
            except (TypeError, ValueError):
                return None

        return MetricSnapshot(
            content_id=row.content_id,
            platform=platform,
            platform_post_id=row.platform_post_id,
            views=_pub("views", row.views),
            impressions=_pub("impressions", row.impressions),
            likes=_pub("likes", row.likes),
            comments=_pub("comments", row.comments),
            shares=_pub("shares", row.shares),
            saves=_pub("saves", row.saves),
            clicks=_pub("clicks", row.clicks),
            reach=_pub("reach", row.reach),
            engagement_rate=_pub_float("engagement_rate", row.engagement_rate),
            click_through_rate=_pub_float("engagement_rate", row.click_through_rate)
            if is_metric_supported(platform, "clicks") and is_metric_supported(platform, "impressions")
            else None,
            supported_metrics=supported_metrics_for(platform),
            unsupported_metrics=unsupported_metrics_for(platform),
            fetched_at=row.recorded_at,
            snapshot_id=row.id,
        )

    def list_snapshots(self, user_id: int, content_id: int, limit: int = 30) -> List[MetricSnapshot]:
        item = self.get_owned(user_id, content_id)
        if not item:
            raise AnalyticsError("content", "content not found")
        rows = (
            self.db.query(ContentAnalytics)
            .filter(ContentAnalytics.content_id == content_id, ContentAnalytics.user_id == user_id)
            .order_by(ContentAnalytics.recorded_at.desc())
            .limit(max(1, min(limit, 100)))
            .all()
        )
        return [self.to_public_snapshot(r) for r in rows]

    def latest_per_post(self, user_id: int, platform: Optional[str] = None,
                        window_days: int = 30) -> List[Dict[str, Any]]:
        """Latest snapshot per published post + content metadata for analysis stages."""
        from datetime import timedelta

        items = self.list_published(user_id, platform=platform, limit=200, include_failed=False)
        if window_days and window_days > 0:
            cutoff = datetime.utcnow() - timedelta(days=window_days)
            items = [i for i in items if not i.published_at or i.published_at >= cutoff]
        rows: List[Dict[str, Any]] = []
        for item in items:
            plat = _platform_str(item.platform)
            latest = (
                self.db.query(ContentAnalytics)
                .filter(ContentAnalytics.content_id == item.id, ContentAnalytics.user_id == user_id)
                .order_by(ContentAnalytics.recorded_at.desc())
                .first()
            )
            snap = self.to_public_snapshot(latest) if latest else None
            row: Dict[str, Any] = {
                "content_id": item.id,
                "title": item.title,
                "platform": plat,
                "content_type": item.content_type.value if hasattr(item.content_type, "value") else str(item.content_type),
                "status": _status_str(item.status),
                "supported_metrics": supported_metrics_for(plat),
                "unsupported_metrics": unsupported_metrics_for(plat),
                "views": snap.views if snap else None,
                "impressions": snap.impressions if snap else None,
                "likes": snap.likes if snap else None,
                "comments": snap.comments if snap else None,
                "shares": snap.shares if snap else None,
                "saves": snap.saves if snap else None,
                "clicks": snap.clicks if snap else None,
                "reach": snap.reach if snap else None,
                "engagement_rate": snap.engagement_rate if snap else None,
            }
            rows.append(row)
        return rows

    def published_with_status(self, user_id: int, platform: Optional[str] = None,
                              limit: int = 50) -> List[PublishedContentItem]:
        """Published Content stage: status + latest snapshot summary per post."""
        items = self.list_published(user_id, platform=platform, limit=limit, include_failed=True)
        out: List[PublishedContentItem] = []
        for item in items:
            latest = (
                self.db.query(ContentAnalytics)
                .filter(ContentAnalytics.content_id == item.id, ContentAnalytics.user_id == user_id)
                .order_by(ContentAnalytics.recorded_at.desc())
                .first()
            )
            count = (
                self.db.query(ContentAnalytics)
                .filter(ContentAnalytics.content_id == item.id, ContentAnalytics.user_id == user_id)
                .count()
            )
            out.append(PublishedContentItem(
                content_id=item.id,
                title=item.title,
                platform=_platform_str(item.platform),
                content_type=item.content_type.value if hasattr(item.content_type, "value") else str(item.content_type),
                status=_status_str(item.status),
                platform_post_id=item.platform_post_id,
                platform_post_url=item.platform_post_url,
                published_at=item.published_at,
                scheduled_at=item.scheduled_at,
                latest_snapshot=self.to_public_snapshot(latest) if latest else None,
                snapshot_count=count,
            ))
        return out
