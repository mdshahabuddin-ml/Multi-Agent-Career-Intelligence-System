"""
Official-API analytics providers.

Each provider speaks ONLY to its platform's official REST API with the
user's OAuth access token. No scraping, no passwords, no browser
automation — same rule as ``backend/social_integrations/publisher.py``.

Return contract: ``fetch_metrics`` returns a dict with keys
views/impressions/likes/comments/shares/saves/clicks/reach where a value
is an ``int`` when the official API exposed it and ``None`` when the
official API does not expose it (see capabilities.py). ``raw`` carries
the redacted provider payload for audit; tokens are never logged.

Error taxonomy (mirrors publisher.py):
- ``AnalyticsAuthError`` (401) — caller may refresh once, retry once.
- ``AnalyticsRetryableError`` (429/5xx/timeout) — safe to retry bounded.
- ``AnalyticsNotFoundError`` (404) — post removed / bad id. Not retried.
- ``AnalyticsUnsupportedError`` — platform has no official metrics API
  (twitter/tiktok) or the post has no platform_post_id yet.
- ``AnalyticsPermanentError`` — everything else. Never retried.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

import httpx

from backend.content_analytics.capabilities import (
    is_metric_supported,
    supported_metrics_for,
    unsupported_metrics_for,
)

logger = logging.getLogger(__name__)

HTTP_TIMEOUT_SECONDS = 20.0
GRAPH_VERSION = "v18.0"


class AnalyticsError(Exception):
    retryable = False

    def __init__(self, platform: str, reason: str, status: Optional[int] = None):
        self.platform = platform
        self.reason = reason
        self.status = status
        super().__init__(
            f"[{platform}] analytics failed: {reason}" + (f" (HTTP {status})" if status else "")
        )


class AnalyticsAuthError(AnalyticsError):
    pass


class AnalyticsRetryableError(AnalyticsError):
    retryable = True


class AnalyticsNotFoundError(AnalyticsError):
    pass


class AnalyticsUnsupportedError(AnalyticsError):
    pass


class AnalyticsPermanentError(AnalyticsError):
    pass


def _classify(platform: str, status: Optional[int], reason: str) -> AnalyticsError:
    if status == 401:
        return AnalyticsAuthError(platform, reason or "access token rejected", status)
    if status == 404:
        return AnalyticsNotFoundError(platform, reason or "post not found", status)
    if status == 429 or (status is not None and status >= 500):
        return AnalyticsRetryableError(platform, reason or "transient platform error", status)
    return AnalyticsPermanentError(platform, reason or "request rejected", status)


def _safe_reason(payload: Any, fallback: str = "request rejected") -> str:
    try:
        if isinstance(payload, dict):
            err = payload.get("error")
            if isinstance(err, dict):
                for key in ("message", "error_user_msg", "type", "code"):
                    value = err.get(key)
                    if isinstance(value, str) and value:
                        return value[:300]
            elif isinstance(err, str) and err:
                return err[:300]
            for key in ("error_description", "message"):
                value = payload.get(key)
                if isinstance(value, str) and value:
                    return value[:300]
    except Exception:  # pragma: no cover - defensive
        pass
    return fallback


async def _read_error(response: httpx.Response) -> str:
    try:
        return _safe_reason(response.json())
    except ValueError:
        text = (response.text or "").strip()
        return text[:200] if text else "request rejected"


def _to_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        ivalue = int(str(value).replace(",", ""))
        return ivalue if ivalue >= 0 else None
    except (TypeError, ValueError):
        return None


def _blank_result(platform: str, platform_post_id: str) -> Dict[str, Any]:
    """All-None result skeleton — callers fill only supported metrics."""
    return {
        "platform": platform,
        "platform_post_id": platform_post_id,
        "views": None,
        "impressions": None,
        "likes": None,
        "comments": None,
        "shares": None,
        "saves": None,
        "clicks": None,
        "reach": None,
        "raw": {},
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "supported_metrics": supported_metrics_for(platform),
        "unsupported_metrics": unsupported_metrics_for(platform),
    }


# ----------------------------------------------------------------------
# YouTube — Data API v3 videos.list(part=statistics)
# ----------------------------------------------------------------------
async def fetch_youtube(
    access_token: str,
    platform_post_id: str,
    client: Optional[httpx.AsyncClient] = None,
) -> Dict[str, Any]:
    """Fetch viewCount/likeCount/commentCount. Impressions/shares unsupported."""
    result = _blank_result("youtube", platform_post_id)
    own_client = client is None
    http = client or httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS)
    try:
        response = await http.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={"part": "statistics", "id": platform_post_id},
            headers={"Authorization": f"Bearer {access_token}"},
        )
    finally:
        if own_client:
            await http.aclose()
    if response.status_code >= 400:
        raise _classify("youtube", response.status_code, await _read_error(response))
    try:
        items = (response.json() or {}).get("items", []) or []
    except ValueError:
        items = []
    if not items:
        raise AnalyticsNotFoundError("youtube", "video not found")
    stats = items[0].get("statistics", {}) or {}
    result["views"] = _to_int(stats.get("viewCount"))
    result["likes"] = _to_int(stats.get("likeCount"))
    result["comments"] = _to_int(stats.get("commentCount"))
    result["raw"] = {"statistics": {k: stats.get(k) for k in ("viewCount", "likeCount", "commentCount")}}
    return result


# ----------------------------------------------------------------------
# Instagram — Graph API media fields + insights
# ----------------------------------------------------------------------
async def fetch_instagram(
    access_token: str,
    platform_post_id: str,
    client: Optional[httpx.AsyncClient] = None,
) -> Dict[str, Any]:
    """Fetch likes/comments via media fields, impressions/reach/shares/saves via insights."""
    result = _blank_result("instagram", platform_post_id)
    own_client = client is None
    http = client or httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS)
    try:
        media = await http.get(
            f"https://graph.facebook.com/{GRAPH_VERSION}/{platform_post_id}",
            params={"fields": "like_count,comments_count", "access_token": access_token},
        )
        if media.status_code >= 400:
            raise _classify("instagram", media.status_code, await _read_error(media))
        try:
            media_data = media.json() or {}
        except ValueError:
            media_data = {}
        result["likes"] = _to_int(media_data.get("like_count"))
        result["comments"] = _to_int(media_data.get("comments_count"))

        insights = await http.get(
            f"https://graph.facebook.com/{GRAPH_VERSION}/{platform_post_id}/insights",
            params={
                "metric": "impressions,reach,shares,saves,plays",
                "access_token": access_token,
            },
        )
        if insights.status_code >= 400:
            # Media fields already succeeded — insights may be permission-gated.
            # Keep supported-but-unavailable as None instead of failing outright.
            logger.info("Instagram insights unavailable for %s: HTTP %s", platform_post_id, insights.status_code)
            result["raw"] = {"media": {"like_count": media_data.get("like_count")}}
            return result
        try:
            data = (insights.json() or {}).get("data", []) or []
        except ValueError:
            data = []
        values = {}
        for entry in data:
            name = entry.get("name", "")
            vals = entry.get("values", []) or []
            if vals:
                values[name] = _to_int(vals[-1].get("value"))
        result["impressions"] = values.get("impressions")
        result["reach"] = values.get("reach")
        result["shares"] = values.get("shares")
        result["saves"] = values.get("saves")
        if values.get("plays") is not None:
            result["views"] = values.get("plays")
        result["raw"] = {"media": {"like_count": media_data.get("like_count")}, "insights": sorted(values)}
        return result
    finally:
        if own_client:
            await http.aclose()


# ----------------------------------------------------------------------
# Facebook — Graph API post fields + insights
# ----------------------------------------------------------------------
async def fetch_facebook(
    access_token: str,
    platform_post_id: str,
    client: Optional[httpx.AsyncClient] = None,
) -> Dict[str, Any]:
    """Fetch likes/comments/shares via post fields, impressions/reach via insights."""
    result = _blank_result("facebook", platform_post_id)
    own_client = client is None
    http = client or httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS)
    try:
        post = await http.get(
            f"https://graph.facebook.com/{GRAPH_VERSION}/{platform_post_id}",
            params={
                "fields": "likes.summary(true),comments.summary(true),shares",
                "access_token": access_token,
            },
        )
        if post.status_code >= 400:
            raise _classify("facebook", post.status_code, await _read_error(post))
        try:
            post_data = post.json() or {}
        except ValueError:
            post_data = {}
        likes = (post_data.get("likes") or {}).get("summary", {}) or {}
        comments = (post_data.get("comments") or {}).get("summary", {}) or {}
        shares = post_data.get("shares", {}) or {}
        result["likes"] = _to_int(likes.get("total_count"))
        result["comments"] = _to_int(comments.get("total_count"))
        result["shares"] = _to_int(shares.get("count"))

        insights = await http.get(
            f"https://graph.facebook.com/{GRAPH_VERSION}/{platform_post_id}/insights",
            params={"metric": "post_impressions,post_impressions_unique", "access_token": access_token},
        )
        if insights.status_code < 400:
            try:
                data = (insights.json() or {}).get("data", []) or []
            except ValueError:
                data = []
            for entry in data:
                name = entry.get("name", "")
                vals = entry.get("values", []) or []
                if not vals:
                    continue
                if name == "post_impressions":
                    result["impressions"] = _to_int(vals[-1].get("value"))
                elif name == "post_impressions_unique":
                    result["reach"] = _to_int(vals[-1].get("value"))
        else:
            logger.info("Facebook insights unavailable for %s: HTTP %s", platform_post_id, insights.status_code)
        result["raw"] = {"has_insights": result["impressions"] is not None or result["reach"] is not None}
        return result
    finally:
        if own_client:
            await http.aclose()


# ----------------------------------------------------------------------
# LinkedIn — socialActions summaries (limited organic coverage)
# ----------------------------------------------------------------------
async def fetch_linkedin(
    access_token: str,
    platform_post_id: str,
    client: Optional[httpx.AsyncClient] = None,
) -> Dict[str, Any]:
    """Best-effort likes/comments via socialActions. Impressions/views unsupported.

    ``platform_post_id`` is the UGC share URN (``urn:li:share:...``).
    When the API does not expose the counts, they stay ``None``.
    """
    result = _blank_result("linkedin", platform_post_id)
    own_client = client is None
    http = client or httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS)
    headers = {"Authorization": f"Bearer {access_token}", "X-Restli-Protocol-Version": "2.0.0"}
    try:
        encoded = platform_post_id.replace(":", "%3A").replace("/", "%2F")
        likes_resp = await http.get(
            f"https://api.linkedin.com/v2/socialActions/{encoded}/likes/summary",
            headers=headers,
        )
        if likes_resp.status_code == 404:
            # Post exists but actions are not visible with this token — not an error.
            result["raw"] = {"limited_visibility": True}
            return result
        if likes_resp.status_code < 400:
            try:
                result["likes"] = _to_int((likes_resp.json() or {}).get("totalLikes"))
            except ValueError:
                pass
        elif likes_resp.status_code not in (403,):
            raise _classify("linkedin", likes_resp.status_code, await _read_error(likes_resp))

        comments_resp = await http.get(
            f"https://api.linkedin.com/v2/socialActions/{encoded}/comments/summary",
            headers=headers,
        )
        if comments_resp.status_code < 400:
            try:
                result["comments"] = _to_int((comments_resp.json() or {}).get("totalComments"))
            except ValueError:
                pass
        elif comments_resp.status_code not in (403, 404):
            raise _classify("linkedin", comments_resp.status_code, await _read_error(comments_resp))
        result["raw"] = {"likes_visible": result["likes"] is not None,
                         "comments_visible": result["comments"] is not None}
        return result
    finally:
        if own_client:
            await http.aclose()


PROVIDER_FETCHERS: Dict[str, Callable[..., Any]] = {
    "youtube": fetch_youtube,
    "instagram": fetch_instagram,
    "facebook": fetch_facebook,
    "linkedin": fetch_linkedin,
}


async def fetch_metrics(
    platform: str,
    access_token: str,
    platform_post_id: str,
    client: Optional[httpx.AsyncClient] = None,
) -> Dict[str, Any]:
    """Dispatch to the platform's official-API fetcher.

    Raises ``AnalyticsUnsupportedError`` when the platform has no official
    metrics API wired (twitter/tiktok/unknown) or the post was never
    published (no ``platform_post_id``).
    """
    normalised = (platform or "").strip().lower()
    if not platform_post_id:
        raise AnalyticsUnsupportedError(normalised or "unknown", "post has no platform_post_id (not published yet)")
    fetcher = PROVIDER_FETCHERS.get(normalised)
    if fetcher is None:
        raise AnalyticsUnsupportedError(
            normalised,
            f"no official metrics API wired for '{normalised}' — tracking publishing status only",
        )
    fetched = await fetcher(access_token, platform_post_id, client)
    # Safety net: never leak a metric the matrix says is unsupported.
    for metric in ("views", "impressions", "likes", "comments", "shares", "saves", "clicks", "reach"):
        if not is_metric_supported(normalised, metric):
            fetched[metric] = None
    return fetched
