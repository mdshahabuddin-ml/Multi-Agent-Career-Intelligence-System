"""Official OAuth 2.0 flows for social publishing platforms.

Supports LinkedIn, Instagram, Facebook (both via Meta Graph OAuth), and
YouTube (via Google OAuth). Only the authorization-code flow is used:
users approve access in the platform's own browser UI — this codebase
never asks for, accepts, or handles social-media passwords, and never
scrapes websites.

Covered here: authorize-URL building (state + PKCE), code exchange,
token refresh, and profile fetch. Publishing is intentionally absent.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from base64 import urlsafe_b64encode
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)

HTTP_TIMEOUT_SECONDS = 20.0
GRAPH_VERSION = "v18.0"


class OAuthError(ValueError):
    """OAuth failure (provider, reason, HTTP status). No secrets included."""

    def __init__(self, provider: str, reason: str, status: Optional[int] = None):
        self.provider = provider
        self.reason = reason
        self.status = status
        super().__init__(f"[{provider}] OAuth failed: {reason}" + (f" (HTTP {status})" if status else ""))


@dataclass(frozen=True)
class ProviderSpec:
    """Official endpoints and scopes for one platform."""

    name: str
    authorize_url: str
    token_url: str
    token_method: str = "POST"  # LinkedIn/Google POST form; Meta Graph GET
    profile_url: str = ""
    scopes: List[str] = field(default_factory=list)
    pkce: bool = False  # include code_challenge (LinkedIn, Google)


PROVIDERS: Dict[str, ProviderSpec] = {
    "linkedin": ProviderSpec(
        name="linkedin",
        authorize_url="https://www.linkedin.com/oauth/v2/authorization",
        token_url="https://www.linkedin.com/oauth/v2/accessToken",
        profile_url="https://api.linkedin.com/v2/userinfo",
        scopes=["openid", "profile", "email", "w_member_social"],
        pkce=True,
    ),
    "instagram": ProviderSpec(
        name="instagram",
        authorize_url=f"https://www.facebook.com/{GRAPH_VERSION}/dialog/oauth",
        token_url=f"https://graph.facebook.com/{GRAPH_VERSION}/oauth/access_token",
        token_method="GET",
        profile_url=f"https://graph.facebook.com/{GRAPH_VERSION}/me",
        scopes=["instagram_basic", "instagram_content_publish", "pages_show_list", "pages_read_engagement"],
    ),
    "facebook": ProviderSpec(
        name="facebook",
        authorize_url=f"https://www.facebook.com/{GRAPH_VERSION}/dialog/oauth",
        token_url=f"https://graph.facebook.com/{GRAPH_VERSION}/oauth/access_token",
        token_method="GET",
        profile_url=f"https://graph.facebook.com/{GRAPH_VERSION}/me",
        scopes=["pages_show_list", "pages_manage_posts", "pages_read_engagement"],
    ),
    "youtube": ProviderSpec(
        name="youtube",
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        profile_url="https://www.googleapis.com/oauth2/v3/userinfo",
        scopes=[
            "openid", "email", "profile",
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.readonly",
        ],
        pkce=True,
    ),
}

SUPPORTED_PLATFORMS = tuple(PROVIDERS)


def get_provider(platform: str) -> ProviderSpec:
    """Return the spec for a platform or raise OAuthError."""
    try:
        return PROVIDERS[platform]
    except KeyError:
        raise OAuthError(platform, f"unsupported platform (expected one of {', '.join(PROVIDERS)})") from None


def generate_pkce_pair() -> Dict[str, str]:
    """Generate a PKCE verifier/challenge (RFC 7636, S256)."""
    verifier = urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode("ascii")
    challenge = urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")
    return {"verifier": verifier, "challenge": challenge}


def build_authorize_url(
    platform: str,
    client_id: str,
    redirect_uri: str,
    state: str,
    code_challenge: Optional[str] = None,
    scopes: Optional[List[str]] = None,
) -> str:
    """Build the platform authorization URL (user visits this in a browser)."""
    spec = get_provider(platform)
    params: Dict[str, str] = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": " ".join(scopes if scopes is not None else spec.scopes),
    }
    if spec.pkce and code_challenge:
        params["code_challenge"] = code_challenge
        params["code_challenge_method"] = "S256"
    if platform == "youtube":
        params["access_type"] = "offline"  # request a refresh token
        params["prompt"] = "consent"
    return f"{spec.authorize_url}?{urlencode(params)}"


def _provider_error(provider: str, payload: Any, status: Optional[int]) -> OAuthError:
    """Extract a safe error reason from a provider error payload."""
    reason = "token request rejected"
    if isinstance(payload, dict):
        err = payload.get("error")
        if isinstance(err, dict):
            reason = str(err.get("message") or err.get("type") or reason)
        elif err:
            reason = str(err)
        desc = payload.get("error_description")
        if desc:
            reason = f"{reason}: {desc}"
    return OAuthError(provider, reason[:300], status)


async def exchange_code(
    platform: str,
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    code_verifier: Optional[str] = None,
) -> Dict[str, Any]:
    """Exchange an authorization code for tokens.

    Returns normalized ``{"access_token", "refresh_token" or None,
    "expires_in" or None, "raw"}``. Secrets are only ever sent to the
    platform's official token endpoint over HTTPS.
    """
    spec = get_provider(platform)
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        if spec.token_method == "GET":  # Meta Graph style
            response = await client.get(spec.token_url, params={
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "client_secret": client_secret,
                "code": code,
            })
        else:
            form: Dict[str, str] = {
                "grant_type": "authorization_code",
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
            }
            if spec.pkce and code_verifier:
                form["code_verifier"] = code_verifier
            response = await client.post(spec.token_url, data=form)
    if response.status_code >= 400:
        try:
            payload = response.json()
        except ValueError:
            payload = None
        raise _provider_error(platform, payload, response.status_code)
    return _normalize_token_response(platform, response.json())


def _normalize_token_response(platform: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize provider token payloads to a common shape."""
    if not isinstance(data, dict) or not data.get("access_token"):
        raise OAuthError(platform, "token response missing access_token")
    expires_in = data.get("expires_in")
    try:
        expires_in = int(expires_in) if expires_in is not None else None
    except (TypeError, ValueError):
        expires_in = None
    return {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token"),
        "expires_in": expires_in,
        "raw": data,
    }


async def exchange_for_long_lived_meta_token(
    access_token: str, client_id: str, client_secret: str
) -> Dict[str, Any]:
    """Exchange a short-lived Meta token for a ~60-day one (Instagram/Facebook)."""
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        response = await client.get(
            f"https://graph.facebook.com/{GRAPH_VERSION}/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": client_id,
                "client_secret": client_secret,
                "fb_exchange_token": access_token,
            },
        )
    if response.status_code >= 400:
        try:
            payload = response.json()
        except ValueError:
            payload = None
        raise _provider_error("meta", payload, response.status_code)
    return _normalize_token_response("meta", response.json())


async def refresh_access_token(
    platform: str,
    client_id: str,
    client_secret: str,
    refresh_token: Optional[str] = None,
    current_access_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Refresh credentials where the platform allows it.

    LinkedIn/Google use the OAuth refresh_token grant; Meta re-exchanges
    the long-lived token. Raises OAuthError when refresh is unsupported.
    """
    spec = get_provider(platform)
    if platform in ("instagram", "facebook"):
        # Meta has no refresh grant: re-exchange a long-lived token.
        token = current_access_token
        if not token:
            raise OAuthError(platform, "no current access token to re-exchange")
        long_lived = await exchange_for_long_lived_meta_token(token, client_id, client_secret)
        long_lived["refresh_token"] = None
        return long_lived
    if not refresh_token:
        raise OAuthError(platform, "no refresh token available")
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        response = await client.post(spec.token_url, data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        })
    if response.status_code >= 400:
        try:
            payload = response.json()
        except ValueError:
            payload = None
        raise _provider_error(platform, payload, response.status_code)
    normalized = _normalize_token_response(platform, response.json())
    if not normalized["refresh_token"]:
        normalized["refresh_token"] = refresh_token  # providers often omit rotation
    return normalized


async def fetch_profile(platform: str, access_token: str) -> Dict[str, Any]:
    """Fetch the connected identity; normalized to id/display_name/raw."""
    spec = get_provider(platform)
    headers = {"Authorization": f"Bearer {access_token}"}
    params: Dict[str, str] = {}
    if platform in ("instagram", "facebook"):
        params = {"fields": "id,name", "access_token": access_token}
        headers = {}
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        response = await client.get(spec.profile_url, headers=headers, params=params or None)
    if response.status_code >= 400:
        try:
            payload = response.json()
        except ValueError:
            payload = None
        raise _provider_error(platform, payload, response.status_code)
    data = response.json()
    user_id = str(data.get("sub") or data.get("id") or "")
    if not user_id:
        raise OAuthError(platform, "profile response missing user id")
    return {
        "platform_user_id": user_id,
        "display_name": data.get("name") or "",
        "raw": data,
    }
