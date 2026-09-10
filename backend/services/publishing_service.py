"""Publishing service - official-API publishing with safety rails.

- Publishes only through ``social_integrations.publisher`` (official REST
  APIs, OAuth tokens; never passwords, scraping, or browser automation).
- Validates the OAuth token first (decrypt + expiry, refresh when allowed).
- Never double-publishes: items carrying ``platform_post_id`` are returned
  as-is without any HTTP call.
- Retries only safe errors (429/5xx/timeouts, single token-refresh retry);
  attempts are bounded by MAX_PUBLISH_ATTEMPTS — never indefinite.
- Error messages never contain tokens, secrets, or request bodies.
- ``dry_run_item`` previews everything with zero network calls and zero writes.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.models.content_calendar import ContentCalendar, ContentStatus, SocialPlatform
from backend.models.social_account import SocialAccount
from backend.models.social_post import SocialPost
from backend.social_integrations import publisher
from backend.social_integrations.oauth import OAuthError
from backend.social_integrations.publisher import (
    PermanentPublishError,
    PublishError,
    TokenExpiredError,
    plan_publish,
)
from backend.social_integrations.token_crypto import TokenDecryptionError, decrypt_token

logger = logging.getLogger(__name__)

MAX_PUBLISH_ATTEMPTS = 3


class PublishingService:
    """Publish scheduled content through official platform APIs."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Account + token handling
    # ------------------------------------------------------------------
    def _account_for(
        self, user_id: int, platform: SocialPlatform
    ) -> SocialAccount:
        platform_value = platform.value if isinstance(platform, SocialPlatform) else str(platform)
        account = (
            self.db.query(SocialAccount)
            .filter(
                SocialAccount.user_id == user_id,
                SocialAccount.platform == platform_value,
                SocialAccount.enabled == True,  # noqa: E712 - SQLAlchemy expression
            )
            .order_by(SocialAccount.id)
            .first()
        )
        if not account:
            raise PermanentPublishError(
                platform_value, f"no connected {platform_value} account"
            )
        return account

    async def _fresh_access_token(self, account: SocialAccount) -> str:
        """Decrypt; refresh first when expired and refreshable."""
        from backend.services.social_account_service import SocialAccountService

        try:
            current = decrypt_token(account.access_token or "")
        except TokenDecryptionError as exc:
            raise PermanentPublishError(
                account.platform, f"{exc}; please reconnect the account"
            ) from exc
        expired = bool(
            account.token_expires_at and account.token_expires_at <= datetime.utcnow()
        )
        if not expired:
            return current
        logger.info("Access token expired for account %s; refreshing", account.id)
        from backend.services.social_account_service import SocialAccountService

        await SocialAccountService(self.db).refresh_account(account.user_id, account.id)
        self.db.refresh(account)
        try:
            return decrypt_token(account.access_token or "")
        except TokenDecryptionError as exc:
            raise PermanentPublishError(
                account.platform, f"{exc}; please reconnect the account"
            ) from exc

    # ------------------------------------------------------------------
    # Payload building (from the calendar item's formatted variants)
    # ------------------------------------------------------------------
    @staticmethod
    def _payload_for(item: ContentCalendar) -> Dict[str, Any]:
        """Build the platform payload from stored formatted content."""
        platform = item.platform.value if isinstance(item.platform, SocialPlatform) else str(item.platform)
        data = dict(item.platform_specific_data or {})
        media = list(item.media_urls or [])
        image_url = next((u for u in media if u), None)
        payload: Dict[str, Any] = {
            "text": item.content or "",
            "caption": (data.get("caption") or {}).get("text", "") if isinstance(data.get("caption"), dict) else "",
            "image_url": image_url,
            "video_url": None,
            "title": data.get("title") or (item.title or ""),
            "description": data.get("description") or item.content or "",
            "tags": list(item.hashtags or []),
            "privacy": data.get("privacy", "unlisted"),
        }
        variant_kind = str(data.get("variant_kind") or "")
        if variant_kind in ("reel", "video", "short") and image_url:
            # Video-capable variants reuse the attached media URL.
            payload["video_url"] = data.get("video_url") or (
                image_url if _looks_like_video(image_url) else None
            )
        return payload

    # ------------------------------------------------------------------
    # Dry-run (no network, no writes)
    # ------------------------------------------------------------------
    def dry_run_item(self, user_id: int, content_id: int) -> Dict[str, Any]:
        """Preview validation for one item. Pure: no HTTP, no DB writes."""
        item = self._owned_item(user_id, content_id)
        platform = item.platform.value if isinstance(item.platform, SocialPlatform) else str(item.platform)
        checks: List[Dict[str, Any]] = []
        account = (
            self.db.query(SocialAccount)
            .filter(SocialAccount.user_id == user_id, SocialAccount.platform == platform)
            .first()
        )
        checks.append({
            "name": "connected_account",
            "ok": account is not None and bool(account.enabled),
            "detail": "" if account else f"no connected {platform} account",
        })
        token_ok, token_detail = False, "no account"
        if account and account.access_token:
            try:
                decrypt_token(account.access_token)
                token_ok = True
                token_detail = ""
            except TokenDecryptionError as exc:
                token_detail = str(exc)
        checks.append({"name": "token_decryptable", "ok": token_ok, "detail": token_detail})
        if item.platform_post_id:
            checks.append({"name": "not_already_published", "ok": False,
                           "detail": f"already published as {item.platform_post_id}"})
        else:
            checks.append({"name": "not_already_published", "ok": True, "detail": ""})
        payload = self._payload_for(item)
        plan = plan_publish(platform, payload)
        proceeding = all(c["ok"] for c in checks) and plan["proceeding"]
        return {
            "proceeding": proceeding,
            "checks": checks + plan["checks"],
            "would_post": {**plan["would_post"], "platform": platform},
        }

    def _owned_item(self, user_id: int, content_id: int) -> ContentCalendar:
        item = (
            self.db.query(ContentCalendar)
            .filter(ContentCalendar.id == content_id, ContentCalendar.user_id == user_id)
            .first()
        )
        if not item:
            raise PermanentPublishError("__item__", "content not found")
        return item

    # ------------------------------------------------------------------
    # Publish paths
    # ------------------------------------------------------------------
    async def _publish_only(
        self, user_id: int, content_id: int
    ) -> Dict[str, Any]:
        """Validate + POST to the platform. Returns external ids.

        Raises PublishError / OAuthError. Makes no status decisions itself
        beyond recording; callers apply lifecycle transitions.
        """
        item = self._owned_item(user_id, content_id)
        if item.platform_post_id:
            logger.info("Item %s already published as %s; skipping HTTP", item.id, item.platform_post_id)
            return {
                "platform_post_id": item.platform_post_id,
                "platform_post_url": item.platform_post_url or "",
                "already_published": True,
            }
        account = self._account_for(user_id, item.platform)
        access_token = await self._fresh_access_token(account)
        payload = self._payload_for(item)
        platform = item.platform.value if isinstance(item.platform, SocialPlatform) else str(item.platform)
        try:
            outcome = await publisher.publish_to_platform(platform, access_token, payload)
        except TokenExpiredError:
            # Token died mid-flight: exactly one refresh-and-retry, then stop.
            logger.info("Token rejected mid-publish for account %s; refreshing once", account.id)
            from backend.services.social_account_service import SocialAccountService

            await SocialAccountService(self.db).refresh_account(user_id, account.id)
            self.db.refresh(account)
            try:
                access_token = decrypt_token(account.access_token or "")
            except TokenDecryptionError as exc:
                raise PermanentPublishError(platform, str(exc)) from exc
            outcome = await publisher.publish_to_platform(platform, access_token, payload)
        self._record_post_row(user_id, account, item)
        return {
            "platform_post_id": outcome.get("platform_post_id", ""),
            "platform_post_url": outcome.get("platform_post_url", ""),
            "already_published": False,
        }

    def _record_post_row(
        self, user_id: int, account: SocialAccount, item: ContentCalendar
    ) -> SocialPost:
        row = SocialPost(
            user_id=user_id,
            account_id=account.id,
            content_id=None,
            content_text=(item.content or "")[:2000],
            media_urls_json=list(item.media_urls or []),
            status="published",
            published_at=datetime.utcnow(),
            metadata_json={"calendar_id": item.id, "platform": account.platform},
        )
        self.db.add(row)
        return row

    def _apply_success(
        self, item: ContentCalendar, outcome: Dict[str, Any]
    ) -> ContentCalendar:
        item.status = ContentStatus.PUBLISHED
        item.published_at = datetime.utcnow()
        item.updated_at = datetime.utcnow()
        if outcome.get("platform_post_id"):
            item.platform_post_id = str(outcome["platform_post_id"])[:255]
        if outcome.get("platform_post_url"):
            item.platform_post_url = str(outcome["platform_post_url"])[:500]
        item.error_message = None
        self.db.commit()
        self.db.refresh(item)
        return item

    def _apply_failure(self, item: ContentCalendar, error: Exception) -> ContentCalendar:
        # Never include secrets: PublishError messages are pre-sanitized.
        item.status = ContentStatus.FAILED
        item.error_message = str(error)[:2000]
        item.retry_count = (item.retry_count or 0) + 1
        item.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(item)
        return item

    async def publish_item(self, user_id: int, content_id: int) -> ContentCalendar:
        """Publish one item now, recording PUBLISHED or FAILED on the row.

        Always returns the item (never raises for publish failures) so the
        outcome — including sanitized error text — is visible to the caller.
        """
        item = self._owned_item(user_id, content_id)
        try:
            outcome = await self._publish_only(user_id, content_id)
        except Exception as exc:
            return self._apply_failure(item, exc)
        return self._apply_success(item, outcome or {})

    def build_executor(self, user_id: int):
        """Sync executor closure for ContentScheduler.run (status handled there)."""

        def _execute(item: ContentCalendar) -> Dict[str, Any]:
            if item.user_id != user_id:
                raise PermanentPublishError("scheduler", "ownership mismatch")
            return _await_sync(self._publish_only(user_id, item.id))

        return _execute

    # ------------------------------------------------------------------
    # Legacy in-memory API removed: queue/published state now lives in the
    # database (ContentCalendar + SocialPost). Kept for compatibility.
    # ------------------------------------------------------------------
    async def get_queue(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Pending/scheduled items (database-backed)."""
        items = (
            self.db.query(ContentCalendar)
            .filter(ContentCalendar.status.in_([ContentStatus.PENDING, ContentStatus.SCHEDULED]))
            .order_by(ContentCalendar.scheduled_at.asc().nullsfirst(), ContentCalendar.id.asc())
            .limit(limit)
            .all()
        )
        return [{"id": i.id, "status": i.status.value, "platform": str(i.platform)} for i in items]

    async def get_published(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Published items (database-backed)."""
        items = (
            self.db.query(ContentCalendar)
            .filter(ContentCalendar.status == ContentStatus.PUBLISHED)
            .order_by(ContentCalendar.published_at.desc())
            .limit(limit)
            .all()
        )
        return [{"id": i.id, "platform_post_id": i.platform_post_id} for i in items]


def _looks_like_video(url: str) -> bool:
    lowered = (url or "").lower().split("?")[0]
    return lowered.endswith((".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"))


def _await_sync(coro):
    """Drive an awaitable to completion from sync code, any loop state."""
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)
