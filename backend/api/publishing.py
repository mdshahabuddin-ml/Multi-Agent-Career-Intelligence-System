"""
Publishing API Router - Content publishing to social platforms.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_active_user
from backend.models import User
from backend.models.content import Content
from backend.models.social_account import SocialAccount
from backend.models.social_post import SocialPost
from backend.social_integrations.token_crypto import TokenDecryptionError, decrypt_token
from backend.social_integrations.publisher import (
    publish_youtube,
    TokenExpiredError,
    RetryablePublishError,
    PermanentPublishError,
)
from backend.social_integrations import oauth
from backend.services.social_account_service import SocialAccountService, provider_credentials

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/publishing", tags=["Publishing"])


class YouTubePublishRequest(BaseModel):
    content_id: int
    title: str
    description: str = ""
    video_url: Optional[str] = None
    tags: Optional[List[str]] = None
    privacy: str = "unlisted"
    category_id: str = "27"
    scheduled_at: Optional[str] = None


class PublishResponse(BaseModel):
    success: bool
    platform_post_id: Optional[str] = None
    platform_post_url: Optional[str] = None
    status: str
    message: str = ""


def _get_youtube_account(db: Session, user_id: int) -> SocialAccount:
    """Get the user's YouTube social account with OAuth tokens."""
    account = (
        db.query(SocialAccount)
        .filter(
            SocialAccount.user_id == user_id,
            SocialAccount.platform == "youtube",
            SocialAccount.enabled == True,
        )
        .first()
    )
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="YouTube account not connected. Please connect YouTube first.",
        )
    return account


def _get_decrypted_token(account: SocialAccount, token_type: str = "access") -> str:
    """Decrypt stored token. Never logs or returns raw token material."""
    try:
        if token_type == "refresh" and account.refresh_token:
            return decrypt_token(account.refresh_token)
        return decrypt_token(account.access_token or "")
    except TokenDecryptionError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"YouTube token invalid: {exc}. Please reconnect YouTube.",
        )


def _is_duplicate(db: Session, user_id: int, content_id: int) -> Optional[SocialPost]:
    """Check if content already published to YouTube."""
    return (
        db.query(SocialPost)
        .filter(
            SocialPost.user_id == user_id,
            SocialPost.content_id == content_id,
            SocialPost.status == "published",
        )
        .first()
    )


async def _refresh_youtube_token(
    db: Session, account: SocialAccount
) -> str:
    """Refresh YouTube access token and return new token."""
    client_id, secret, _ = provider_credentials("youtube")
    try:
        current = decrypt_token(account.access_token or "")
    except TokenDecryptionError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Cannot refresh: {exc}",
        )

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

    from backend.social_integrations.token_crypto import encrypt_token
    from backend.services.social_account_service import _expiry_timestamp

    account.access_token = encrypt_token(tokens["access_token"])
    if tokens.get("refresh_token"):
        account.refresh_token = encrypt_token(tokens["refresh_token"])
    account.token_expires_at = _expiry_timestamp(tokens.get("expires_in"))
    account.last_synced_at = datetime.utcnow()
    db.commit()

    return tokens["access_token"]


@router.post("/youtube", response_model=PublishResponse)
async def publish_to_youtube(
    request: YouTubePublishRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Publish approved content to YouTube via the official Data API v3.

    Flow: verify content → check approval → check duplicate → get token →
    refresh if needed → upload via publish_youtube() → persist result.
    """
    # 1. Verify content exists and belongs to user
    content = db.query(Content).filter(
        Content.id == request.content_id,
        Content.user_id == current_user.id,
    ).first()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found",
        )

    # 2. Verify content is approved
    if content.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Content must be approved before publishing. Current status: {content.status}",
        )

    # 3. Duplicate protection
    existing = _is_duplicate(db, current_user.id, request.content_id)
    if existing:
        return PublishResponse(
            success=False,
            platform_post_id=existing.platform_post_id,
            status="already_published",
            message=f"Content already published to YouTube as video {existing.platform_post_id}",
        )

    # 4. Get YouTube account
    account = _get_youtube_account(db, current_user.id)

    # 5. Get access token
    access_token = _get_decrypted_token(account, "access")

    # 6. Upload to YouTube
    try:
        result = await publish_youtube(
            access_token=access_token,
            title=request.title,
            description=request.description,
            video_url=request.video_url,
            tags=request.tags or [],
            privacy=request.privacy,
            category_id=request.category_id,
        )
    except TokenExpiredError:
        # Token expired — refresh once and retry
        logger.info("YouTube token expired, refreshing for user %s", current_user.id)
        access_token = await _refresh_youtube_token(db, account)
        try:
            result = await publish_youtube(
                access_token=access_token,
                title=request.title,
                description=request.description,
                video_url=request.video_url,
                tags=request.tags or [],
                privacy=request.privacy,
                category_id=request.category_id,
            )
        except PermanentPublishError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"YouTube upload failed after refresh: {exc}",
            )
    except RetryablePublishError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"YouTube API transient error (retry later): {exc}",
        )
    except PermanentPublishError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"YouTube upload failed: {exc}",
        )

    # 7. Persist result
    post = SocialPost(
        user_id=current_user.id,
        account_id=account.id,
        content_id=request.content_id,
        platform_post_id=result.get("platform_post_id"),
        content_text=request.title,
        media_urls_json=[request.video_url] if request.video_url else [],
        status="published",
        published_at=datetime.utcnow(),
        metadata_json={
            "platform": "youtube",
            "video_url": result.get("platform_post_url"),
            "privacy": request.privacy,
            "category_id": request.category_id,
            "tags": request.tags or [],
        },
    )
    db.add(post)
    db.commit()
    db.refresh(post)

    logger.info(
        "Published content %s to YouTube as %s for user %s",
        request.content_id, result.get("platform_post_id"), current_user.id,
    )

    return PublishResponse(
        success=True,
        platform_post_id=result.get("platform_post_id"),
        platform_post_url=result.get("platform_post_url"),
        status="published",
        message="Published successfully to YouTube",
    )


@router.get("/youtube/status/{content_id}")
async def get_publish_status(
    content_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get publishing status for a content item on YouTube."""
    posts = (
        db.query(SocialPost)
        .filter(
            SocialPost.user_id == current_user.id,
            SocialPost.content_id == content_id,
        )
        .all()
    )
    return {
        "content_id": content_id,
        "platforms": [
            {
                "platform": p.metadata_json.get("platform", "unknown") if p.metadata_json else "unknown",
                "status": p.status,
                "platform_post_id": p.platform_post_id,
                "video_url": p.metadata_json.get("video_url") if p.metadata_json else None,
                "published_at": p.published_at.isoformat() if p.published_at else None,
            }
            for p in posts
        ],
    }


@router.get("/youtube/queue")
async def get_publish_queue(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get scheduled YouTube publishes."""
    posts = (
        db.query(SocialPost)
        .filter(
            SocialPost.user_id == current_user.id,
            SocialPost.status == "scheduled",
        )
        .order_by(SocialPost.scheduled_at)
        .all()
    )
    return {
        "queue": [
            {
                "id": p.id,
                "content_id": p.content_id,
                "status": p.status,
                "scheduled_at": p.scheduled_at.isoformat() if p.scheduled_at else None,
                "metadata": p.metadata_json,
            }
            for p in posts
        ],
        "total": len(posts),
    }
