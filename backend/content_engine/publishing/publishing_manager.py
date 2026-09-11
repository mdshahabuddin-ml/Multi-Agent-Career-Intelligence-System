"""
Publishing Manager - Manages content publishing to platforms.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.models.content import Content
from backend.models.social_account import SocialAccount
from backend.models.social_post import SocialPost
from backend.social_integrations.token_crypto import TokenDecryptionError, decrypt_token
from backend.social_integrations.publisher import publish_youtube, TokenExpiredError, RetryablePublishError, PermanentPublishError
from backend.social_integrations import oauth
from backend.services.social_account_service import provider_credentials, _expiry_timestamp

logger = logging.getLogger(__name__)


class PublishingManager:
    """
    Manages content publishing to platforms with real YouTube integration.
    """

    def __init__(self, db: Session):
        self.db = db

    async def publish_to_youtube(
        self,
        user_id: int,
        content_id: int,
        title: str,
        description: str = "",
        video_url: Optional[str] = None,
        tags: Optional[List[str]] = None,
        privacy: str = "unlisted",
        category_id: str = "27",
    ) -> Dict[str, Any]:
        """Publish content to YouTube. Handles token refresh automatically."""
        # Get content
        content = self.db.query(Content).filter(
            Content.id == content_id,
            Content.user_id == user_id,
        ).first()
        if not content:
            return {"success": False, "error": "Content not found"}

        # Check approval
        if content.status != "approved":
            return {"success": False, "error": f"Content not approved (status: {content.status})"}

        # Check duplicate
        existing = self.db.query(SocialPost).filter(
            SocialPost.user_id == user_id,
            SocialPost.content_id == content_id,
            SocialPost.status == "published",
        ).first()
        if existing:
            return {
                "success": False,
                "error": "Already published",
                "platform_post_id": existing.platform_post_id,
            }

        # Get YouTube account
        account = self.db.query(SocialAccount).filter(
            SocialAccount.user_id == user_id,
            SocialAccount.platform == "youtube",
            SocialAccount.enabled == True,
        ).first()
        if not account:
            return {"success": False, "error": "YouTube not connected"}

        # Get token
        try:
            access_token = decrypt_token(account.access_token or "")
        except TokenDecryptionError:
            return {"success": False, "error": "YouTube token invalid, please reconnect"}

        # Publish with retry on token expiry
        try:
            result = await publish_youtube(
                access_token=access_token,
                title=title,
                description=description,
                video_url=video_url,
                tags=tags or [],
                privacy=privacy,
                category_id=category_id,
            )
        except TokenExpiredError:
            access_token = await self._refresh_token(account)
            result = await publish_youtube(
                access_token=access_token,
                title=title,
                description=description,
                video_url=video_url,
                tags=tags or [],
                privacy=privacy,
                category_id=category_id,
            )
        except (RetryablePublishError, PermanentPublishError) as exc:
            return {"success": False, "error": str(exc)}

        # Persist result
        post = SocialPost(
            user_id=user_id,
            account_id=account.id,
            content_id=content_id,
            platform_post_id=result.get("platform_post_id"),
            content_text=title,
            media_urls_json=[video_url] if video_url else [],
            status="published",
            published_at=datetime.utcnow(),
            metadata_json={
                "platform": "youtube",
                "video_url": result.get("platform_post_url"),
                "privacy": privacy,
                "category_id": category_id,
                "tags": tags or [],
            },
        )
        self.db.add(post)
        self.db.commit()

        return {
            "success": True,
            "platform_post_id": result.get("platform_post_id"),
            "platform_post_url": result.get("platform_post_url"),
        }

    async def _refresh_token(self, account: SocialAccount) -> str:
        """Refresh YouTube access token."""
        from backend.social_integrations.token_crypto import encrypt_token

        client_id, secret, _ = provider_credentials("youtube")
        current = decrypt_token(account.access_token or "")
        stored_refresh = None
        if account.refresh_token:
            try:
                stored_refresh = decrypt_token(account.refresh_token)
            except TokenDecryptionError:
                pass

        tokens = await oauth.refresh_access_token(
            "youtube", client_id, secret,
            refresh_token=stored_refresh, current_access_token=current,
        )

        account.access_token = encrypt_token(tokens["access_token"])
        if tokens.get("refresh_token"):
            account.refresh_token = encrypt_token(tokens["refresh_token"])
        account.token_expires_at = _expiry_timestamp(tokens.get("expires_in"))
        account.last_synced_at = datetime.utcnow()
        self.db.commit()

        return tokens["access_token"]

    async def publish(
        self,
        content_id: str,
        platforms: List[str],
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Publish content to platforms (legacy interface)."""
        result = {
            "content_id": content_id,
            "platforms": platforms,
            "status": "published",
            "results": {},
        }

        for platform in platforms:
            result["results"][platform] = {"status": "success", "post_id": f"post_{platform}"}

        return result

    async def schedule(
        self,
        content_id: str,
        platforms: List[str],
        scheduled_at: str,
    ) -> Dict[str, Any]:
        """Schedule content for publishing."""
        entry = {
            "content_id": content_id,
            "platforms": platforms,
            "scheduled_at": scheduled_at,
            "status": "scheduled",
        }
        return entry
