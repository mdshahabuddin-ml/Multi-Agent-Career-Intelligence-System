"""
Social API Router - Social media management endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_active_user
from backend.models import User
from backend.services.social_account_service import SocialAccountService
from backend.social_integrations.oauth import OAuthError, SUPPORTED_PLATFORMS

router = APIRouter(prefix="/social", tags=["Social"])


def get_account_service(db: Session = Depends(get_db)) -> SocialAccountService:
    return SocialAccountService(db)


class SocialAccountConnectRequest(BaseModel):
    platform: str
    redirect_uri: Optional[str] = None
    # Complete the flow when the platform redirected back with these:
    code: Optional[str] = None
    state: Optional[str] = None


class ManualLinkedInRequest(BaseModel):
    profile_url: str


class ManualYouTubeRequest(BaseModel):
    channel_url: str


class ManualGitHubRequest(BaseModel):
    profile_url: str


@router.get("/accounts")
async def list_accounts(
    current_user: User = Depends(get_current_active_user),
    service: SocialAccountService = Depends(get_account_service),
):
    """List connected social accounts (tokens never exposed)."""
    accounts = service.list_accounts(current_user.id)
    return {"accounts": accounts, "total": len(accounts)}


@router.post("/accounts/connect", status_code=status.HTTP_201_CREATED)
async def connect_account(
    request: SocialAccountConnectRequest,
    current_user: User = Depends(get_current_active_user),
    service: SocialAccountService = Depends(get_account_service),
):
    """Begin OAuth (returns authorize URL) or complete it (with code+state)."""
    try:
        if request.code and request.state:
            account = await service.complete_connect(
                current_user.id, request.platform, request.code,
                request.state, request.redirect_uri,
            )
            return {"success": True, "account": account, "platform": request.platform}
        return service.begin_connect(current_user.id, request.platform, request.redirect_uri)
    except OAuthError as exc:
        raise HTTPException(status_code=_oauth_status(exc), detail=_oauth_detail(exc))


@router.post("/accounts/linkedin-manual", status_code=status.HTTP_201_CREATED)
async def connect_linkedin_manual(
    request: ManualLinkedInRequest,
    current_user: User = Depends(get_current_active_user),
    service: SocialAccountService = Depends(get_account_service),
):
    """Manually connect a LinkedIn profile by URL (no OAuth required)."""
    return service.manual_connect_linkedin(current_user.id, request.profile_url)


@router.post("/accounts/youtube-manual", status_code=status.HTTP_201_CREATED)
async def connect_youtube_manual(
    request: ManualYouTubeRequest,
    current_user: User = Depends(get_current_active_user),
    service: SocialAccountService = Depends(get_account_service),
):
    """Manually connect a YouTube channel by URL (no OAuth required)."""
    return service.manual_connect_youtube(current_user.id, request.channel_url)


@router.post("/accounts/github-manual", status_code=status.HTTP_201_CREATED)
async def connect_github_manual(
    request: ManualGitHubRequest,
    current_user: User = Depends(get_current_active_user),
    service: SocialAccountService = Depends(get_account_service),
):
    """Manually connect a GitHub profile by URL (no OAuth required)."""
    return service.manual_connect_github(current_user.id, request.profile_url)


@router.get("/accounts/callback")
async def oauth_callback(
    provider: str = Query(...),
    code: str = Query(...),
    state: str = Query(...),
    redirect_uri: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    service: SocialAccountService = Depends(get_account_service),
):
    """OAuth redirect target: completes the connection for the signed-in user."""
    try:
        account = await service.complete_connect(
            current_user.id, provider, code, state, redirect_uri
        )
        return {"success": True, "account": account, "platform": provider}
    except OAuthError as exc:
        raise HTTPException(status_code=_oauth_status(exc), detail=_oauth_detail(exc))


@router.post("/accounts/{account_id}/refresh")
async def refresh_account(
    account_id: str,
    current_user: User = Depends(get_current_active_user),
    service: SocialAccountService = Depends(get_account_service),
):
    """Refresh stored credentials where the platform allows it."""
    try:
        account = await service.refresh_account(
            current_user.id, _coerce_id(account_id)
        )
        return {"success": True, "account": account}
    except OAuthError as exc:
        raise HTTPException(status_code=_oauth_status(exc), detail=_oauth_detail(exc))


@router.delete("/accounts/{account_id}")
async def disconnect_account(
    account_id: str,
    current_user: User = Depends(get_current_active_user),
    service: SocialAccountService = Depends(get_account_service),
):
    """Disconnect a social account."""
    try:
        return await service.disconnect_account(current_user.id, _coerce_id(account_id))
    except OAuthError as exc:
        raise HTTPException(status_code=_oauth_status(exc), detail=_oauth_detail(exc))


def _coerce_id(account_id: str) -> int:
    try:
        return int(account_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Social account not found")


def _oauth_status(exc: OAuthError) -> int:
    reason = (exc.reason or "").lower()
    if "not found" in reason:
        return status.HTTP_404_NOT_FOUND
    if "not configured" in reason:
        return status.HTTP_503_SERVICE_UNAVAILABLE
    return status.HTTP_400_BAD_REQUEST


def _oauth_detail(exc: OAuthError) -> str:
    if exc.provider == "__account__":
        return exc.reason
    return str(exc)


@router.get("/posts")
async def list_posts(
    platform: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
):
    """List social posts."""
    return {"posts": [], "total": 0}


@router.post("/posts")
async def create_post(
    account_id: str,
    content: str,
    scheduled_at: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
):
    """Create a new social post."""
    return {
        "success": True,
        "post_id": "post_001",
        "account_id": account_id,
    }


@router.get("/posts/{post_id}")
async def get_post(
    post_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Get post details."""
    return {"post_id": post_id, "status": "draft"}


@router.get("/queue")
async def get_publishing_queue(
    current_user: User = Depends(get_current_active_user),
):
    """Get publishing queue."""
    return {"queue": [], "total": 0}
