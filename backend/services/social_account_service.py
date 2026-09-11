"""Social account connection service (OAuth connection + token management).

Owns the full connect flow sans publishing:
begin (signed state + authorize URL) -> callback (validate, exchange,
profile, encrypted persist) -> refresh/disconnect/list. Every row is
scoped to the authenticated application user; stored tokens are always
Fernet-encrypted and API responses never include token material.
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.social_account import SocialAccount
from backend.social_integrations import oauth
from backend.social_integrations.oauth import OAuthError
from backend.social_integrations.token_crypto import TokenDecryptionError, decrypt_token, encrypt_token

logger = logging.getLogger(__name__)

STATE_SALT = "social-oauth-state"
STATE_MAX_AGE_SECONDS = 600
EXPIRY_SKEW_SECONDS = 60


def _signer() -> URLSafeTimedSerializer:
    if not settings.SECRET_KEY:
        raise OAuthError("oauth", "application SECRET_KEY is not configured")
    return URLSafeTimedSerializer(settings.SECRET_KEY, salt=STATE_SALT)


def _redirect_default() -> str:
    base = (settings.FRONTEND_URL or "http://localhost:5173").rstrip("/")
    return f"{base}/social/callback"


def provider_credentials(platform: str) -> Tuple[str, str, str]:
    """Resolve (client_id, client_secret, redirect_uri) or raise OAuthError."""
    oauth.get_provider(platform)  # validates platform name
    if platform == "linkedin":
        client_id, secret = settings.LINKEDIN_CLIENT_ID, settings.LINKEDIN_CLIENT_SECRET
        redirect = settings.LINKEDIN_REDIRECT_URI or _redirect_default()
    elif platform in ("instagram", "facebook"):
        # Instagram connects through Facebook Login; Facebook uses the same app.
        client_id = settings.FACEBOOK_APP_ID or settings.INSTAGRAM_CLIENT_ID
        secret = settings.FACEBOOK_APP_SECRET or settings.INSTAGRAM_CLIENT_SECRET
        redirect = settings.FACEBOOK_REDIRECT_URI or _redirect_default()
    elif platform == "youtube":
        client_id, secret = settings.GOOGLE_CLIENT_ID, settings.GOOGLE_CLIENT_SECRET
        redirect = settings.GOOGLE_REDIRECT_URI or _redirect_default()
    else:  # pragma: no cover - get_provider already guards
        raise OAuthError(platform, "unsupported platform")
    if not client_id or not secret:
        raise OAuthError(
            platform,
            "provider credentials are not configured on the server",
        )
    return client_id, secret, redirect


def _expiry_timestamp(expires_in: Optional[int]) -> Optional[datetime]:
    if not expires_in:
        return None
    return datetime.utcnow() + timedelta(seconds=max(0, expires_in - EXPIRY_SKEW_SECONDS))


def public_account(account: SocialAccount) -> Dict[str, Any]:
    """Redacted account view — never includes token material."""
    return {
        "id": account.id,
        "platform": account.platform,
        "account_id": account.account_id,
        "account_name": account.account_name,
        "enabled": account.enabled,
        "token_expires_at": account.token_expires_at.isoformat() if account.token_expires_at else None,
        "last_synced_at": account.last_synced_at.isoformat() if account.last_synced_at else None,
        "created_at": account.created_at.isoformat() if account.created_at else None,
    }


class SocialAccountService:
    """Connect, refresh, disconnect, and list OAuth social accounts."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Connect: begin (authorize URL + signed state)
    # ------------------------------------------------------------------
    def begin_connect(
        self, user_id: int, platform: str, redirect_uri: Optional[str] = None
    ) -> Dict[str, Any]:
        oauth.get_provider(platform)
        client_id, _, resolved_redirect = provider_credentials(platform)
        redirect_uri = redirect_uri or resolved_redirect
        pkce = oauth.generate_pkce_pair()
        state = _signer().dumps({
            "user_id": user_id,
            "platform": platform,
            "verifier": pkce["verifier"],
            "nonce": secrets.token_hex(8),
        })
        url = oauth.build_authorize_url(
            platform,
            client_id=client_id,
            redirect_uri=redirect_uri,
            state=state,
            code_challenge=pkce["challenge"],
        )
        return {"authorization_url": url, "state": state, "platform": platform}

    # ------------------------------------------------------------------
    # Manual LinkedIn connect (no OAuth required)
    # ------------------------------------------------------------------
    def manual_connect_linkedin(self, user_id: int, profile_url: str) -> Dict[str, Any]:
        """Manually connect a LinkedIn profile by URL without OAuth."""
        import re
        from urllib.parse import urlparse

        parsed = urlparse(profile_url)
        if "linkedin.com" not in parsed.netloc:
            raise OAuthError("linkedin", "Invalid LinkedIn URL")

        match = re.search(r"/in/([^/]+)", parsed.path)
        if not match:
            raise OAuthError("linkedin", "Invalid LinkedIn profile URL format")

        slug = match.group(1)
        account_id = f"linkedin_{slug}"

        existing = (
            self.db.query(SocialAccount)
            .filter(
                SocialAccount.user_id == user_id,
                SocialAccount.platform == "linkedin",
                SocialAccount.account_id == account_id,
            )
            .first()
        )
        if existing:
            existing.account_name = slug
            existing.profile_data_json = {"profile_url": profile_url, "manual": True}
            existing.enabled = True
            existing.last_synced_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing)
            return public_account(existing)

        account = SocialAccount(
            user_id=user_id,
            platform="linkedin",
            account_id=account_id,
            account_name=slug,
            profile_data_json={"profile_url": profile_url, "manual": True},
            enabled=True,
            last_synced_at=datetime.utcnow(),
        )
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        logger.info("Manually connected LinkedIn profile %s for user %s", slug, user_id)
        return public_account(account)

    # ------------------------------------------------------------------
    # Manual YouTube connect (no OAuth required)
    # ------------------------------------------------------------------
    def manual_connect_youtube(self, user_id: int, channel_url: str) -> Dict[str, Any]:
        """Manually connect a YouTube channel by URL without OAuth."""
        import re
        from urllib.parse import urlparse

        channel_url = channel_url.strip()

        if channel_url.startswith("@"):
            channel_id = channel_url[1:]
        elif "youtube.com" in channel_url or "youtu.be" in channel_url:
            parsed = urlparse(channel_url)
            channel_id = None
            if "/channel/" in parsed.path:
                match = re.search(r"/channel/([^/]+)", parsed.path)
                if match:
                    channel_id = match.group(1)
            elif "/c/" in parsed.path or "/user/" in parsed.path:
                match = re.search(r"/(?:c|user)/([^/]+)", parsed.path)
                if match:
                    channel_id = match.group(1)
            elif "/@" in parsed.path:
                match = re.search(r"/@([^/]+)", parsed.path)
                if match:
                    channel_id = match.group(1)
            elif "youtu.be" in parsed.netloc:
                channel_id = parsed.path.lstrip("/")
            if not channel_id:
                raise OAuthError("youtube", "Invalid YouTube channel URL format")
        else:
            channel_id = channel_url.lstrip("@")

        account_id = f"youtube_{channel_id}"

        existing = (
            self.db.query(SocialAccount)
            .filter(
                SocialAccount.user_id == user_id,
                SocialAccount.platform == "youtube",
                SocialAccount.account_id == account_id,
            )
            .first()
        )
        if existing:
            existing.account_name = channel_id
            existing.profile_data_json = {"channel_url": channel_url, "manual": True}
            existing.enabled = True
            existing.last_synced_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing)
            return public_account(existing)

        account = SocialAccount(
            user_id=user_id,
            platform="youtube",
            account_id=account_id,
            account_name=channel_id,
            profile_data_json={"channel_url": channel_url, "manual": True},
            enabled=True,
            last_synced_at=datetime.utcnow(),
        )
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        logger.info("Manually connected YouTube channel %s for user %s", channel_id, user_id)
        return public_account(account)

    # ------------------------------------------------------------------
    # Manual GitHub connect (no OAuth required)
    # ------------------------------------------------------------------
    def manual_connect_github(self, user_id: int, profile_url: str) -> Dict[str, Any]:
        """Manually connect a GitHub profile by URL without OAuth."""
        import re
        from urllib.parse import urlparse

        profile_url = profile_url.strip()

        if profile_url.startswith("github.com/"):
            username = profile_url.replace("github.com/", "").strip("/")
        elif "github.com" in profile_url:
            parsed = urlparse(profile_url)
            path_parts = parsed.path.strip("/").split("/")
            if not path_parts or not path_parts[0]:
                raise OAuthError("github", "Invalid GitHub profile URL")
            username = path_parts[0]
        else:
            username = profile_url.strip("/@")

        if not username or "/" in username:
            raise OAuthError("github", "Invalid GitHub username")

        account_id = f"github_{username}"

        existing = (
            self.db.query(SocialAccount)
            .filter(
                SocialAccount.user_id == user_id,
                SocialAccount.platform == "github",
                SocialAccount.account_id == account_id,
            )
            .first()
        )
        if existing:
            existing.account_name = username
            existing.profile_data_json = {"profile_url": f"https://github.com/{username}", "manual": True}
            existing.enabled = True
            existing.last_synced_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing)
            return public_account(existing)

        account = SocialAccount(
            user_id=user_id,
            platform="github",
            account_id=account_id,
            account_name=username,
            profile_data_json={"profile_url": f"https://github.com/{username}", "manual": True},
            enabled=True,
            last_synced_at=datetime.utcnow(),
        )
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        logger.info("Manually connected GitHub profile %s for user %s", username, user_id)
        return public_account(account)

    def _validate_state(self, user_id: int, platform: str, state: str) -> Dict[str, Any]:
        try:
            data = _signer().loads(state, max_age=STATE_MAX_AGE_SECONDS)
        except SignatureExpired as exc:
            raise OAuthError(platform, "authorization state expired; please reconnect") from exc
        except BadSignature as exc:
            raise OAuthError(platform, "authorization state invalid") from exc
        if not isinstance(data, dict) or data.get("user_id") != user_id or data.get("platform") != platform:
            raise OAuthError(platform, "authorization state does not match this session")
        return data

    # ------------------------------------------------------------------
    # Connect: callback (validate -> exchange -> profile -> persist)
    # ------------------------------------------------------------------
    async def complete_connect(
        self,
        user_id: int,
        platform: str,
        code: str,
        state: str,
        redirect_uri: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not code:
            raise OAuthError(platform, "missing authorization code")
        state_data = self._validate_state(user_id, platform, state)
        client_id, secret, resolved_redirect = provider_credentials(platform)
        redirect_uri = redirect_uri or resolved_redirect

        tokens = await oauth.exchange_code(
            platform, code, client_id, secret, redirect_uri,
            code_verifier=state_data.get("verifier"),
        )
        # Meta short-lived tokens are immediately upgraded server-side.
        if platform in ("instagram", "facebook"):
            try:
                tokens = await oauth.exchange_for_long_lived_meta_token(
                    tokens["access_token"], client_id, secret
                )
            except OAuthError as exc:
                logger.warning("Meta long-lived exchange failed, keeping short-lived token: %s", exc)

        profile = await oauth.fetch_profile(platform, tokens["access_token"])
        account = (
            self.db.query(SocialAccount)
            .filter(
                SocialAccount.user_id == user_id,
                SocialAccount.platform == platform,
                SocialAccount.account_id == profile["platform_user_id"],
            )
            .first()
        )
        if account is None:
            account = SocialAccount(
                user_id=user_id, platform=platform, account_id=profile["platform_user_id"]
            )
            self.db.add(account)
        account.account_name = profile.get("display_name") or account.account_name or ""
        account.access_token = encrypt_token(tokens["access_token"])
        account.refresh_token = (
            encrypt_token(tokens["refresh_token"]) if tokens.get("refresh_token") else account.refresh_token
        )
        account.token_expires_at = _expiry_timestamp(tokens.get("expires_in"))
        account.profile_data_json = profile.get("raw") or {}
        account.enabled = True
        account.last_synced_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(account)
        logger.info("Connected %s account %s for user %s", platform, account.account_id, user_id)
        return public_account(account)

    # ------------------------------------------------------------------
    # Refresh / disconnect / list (all ownership-scoped)
    # ------------------------------------------------------------------
    def _owned_account(self, user_id: int, account_id: int) -> SocialAccount:
        account = (
            self.db.query(SocialAccount)
            .filter(SocialAccount.id == account_id, SocialAccount.user_id == user_id)
            .first()
        )
        if not account:
            raise OAuthError("__account__", "social account not found")
        return account

    async def refresh_account(self, user_id: int, account_id: int) -> Dict[str, Any]:
        account = self._owned_account(user_id, account_id)
        client_id, secret, _ = provider_credentials(account.platform)
        try:
            current = decrypt_token(account.access_token or "")
        except TokenDecryptionError as exc:
            raise OAuthError(account.platform, str(exc)) from exc
        stored_refresh = None
        if account.refresh_token:
            try:
                stored_refresh = decrypt_token(account.refresh_token)
            except TokenDecryptionError as exc:
                raise OAuthError(account.platform, str(exc)) from exc
        tokens = await oauth.refresh_access_token(
            account.platform, client_id, secret,
            refresh_token=stored_refresh, current_access_token=current,
        )
        account.access_token = encrypt_token(tokens["access_token"])
        if tokens.get("refresh_token"):
            account.refresh_token = encrypt_token(tokens["refresh_token"])
        account.token_expires_at = _expiry_timestamp(tokens.get("expires_in"))
        account.last_synced_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(account)
        return public_account(account)

    async def disconnect_account(self, user_id: int, account_id: int) -> Dict[str, Any]:
        account = self._owned_account(user_id, account_id)
        # Best-effort provider-side revocation; local disconnect proceeds regardless.
        try:
            await self._revoke_remote(account)
        except Exception as exc:  # pragma: no cover - provider-dependent
            logger.warning("Remote revoke failed for account %s: %s", account.id, exc)
        self.db.delete(account)
        self.db.commit()
        return {"success": True, "message": f"Account {account_id} disconnected"}

    async def _revoke_remote(self, account: SocialAccount) -> None:
        import httpx

        try:
            current = decrypt_token(account.access_token or "")
        except TokenDecryptionError:
            return
        urls = {
            "youtube": "https://oauth2.googleapis.com/revoke",
            "instagram": None,  # Meta: no user-token revoke endpoint; app removal is user-side
            "facebook": None,
            "linkedin": None,  # LinkedIn: no programmatic revoke; removal is user-side
        }
        url = urls.get(account.platform)
        if not url:
            return
        async with httpx.AsyncClient(timeout=20.0) as client:
            await client.post(url, data={"token": current})

    def list_accounts(self, user_id: int) -> List[Dict[str, Any]]:
        accounts = (
            self.db.query(SocialAccount)
            .filter(SocialAccount.user_id == user_id)
            .order_by(SocialAccount.id)
            .all()
        )
        return [public_account(a) for a in accounts]
