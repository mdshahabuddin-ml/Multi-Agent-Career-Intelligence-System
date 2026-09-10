"""Official platform publishing clients (no scraping, no passwords, no browser).

One async publish function per supported platform, all speaking only to
official REST APIs with the user's OAuth access token:

- LinkedIn: UGC Posts API (``/v2/ugcPosts``), binary image upload when needed.
- Instagram: Graph API two-step container flow (``/{ig-id}/media`` then
  ``/media_publish``); photos and Reels.
- Facebook: Graph API Page feed/photos/videos endpoints.
- YouTube: Data API v3 resumable upload session.

Error taxonomy (fail fast, retry only what is safe):
- ``TokenExpiredError`` — HTTP 401; caller may refresh once and retry once.
- ``RetryablePublishError`` — HTTP 429 / 5xx / timeouts / network errors.
- ``PermanentPublishError`` — everything else (validation, unsupported
  media, missing linkage). Never retried automatically.

Error messages contain provider, status, and reason only — never tokens,
secrets, or request bodies.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

HTTP_TIMEOUT_SECONDS = 60.0
GRAPH_VERSION = "v18.0"
LINKEDIN_VERSION = "202501"
MAX_IMAGE_BYTES = 25 * 1024 * 1024
MAX_VIDEO_BYTES = 512 * 1024 * 1024


class PublishError(Exception):
    """Base publishing failure. ``retryable`` decides automatic retry."""

    retryable = False

    def __init__(self, platform: str, reason: str, status: Optional[int] = None):
        self.platform = platform
        self.reason = reason
        self.status = status
        super().__init__(
            f"[{platform}] publish failed: {reason}" + (f" (HTTP {status})" if status else "")
        )


class TokenExpiredError(PublishError):
    """Access token rejected (HTTP 401); caller may refresh once."""

    retryable = False
    refreshable = True


class RetryablePublishError(PublishError):
    """Transient failure (rate limit, 5xx, timeout); safe to retry bounded."""

    retryable = True


class PermanentPublishError(PublishError):
    """Non-retryable failure (validation, unsupported media/linkage)."""

    retryable = False


def _classify(platform: str, status: Optional[int], reason: str) -> PublishError:
    """Map an HTTP failure onto the error taxonomy."""
    if status == 401:
        return TokenExpiredError(platform, reason or "access token rejected", status)
    if status == 429 or (status is not None and status >= 500):
        return RetryablePublishError(platform, reason or "transient platform error", status)
    return PermanentPublishError(platform, reason or "request rejected", status)


def _safe_reason(payload: Any, fallback: str = "request rejected") -> str:
    """Extract a short human reason from a provider error payload."""
    try:
        if isinstance(payload, dict):
            err = payload.get("error")
            if isinstance(err, dict):
                for key in ("message", "error_user_msg", "error_user_title", "type", "code"):
                    value = err.get(key)
                    if isinstance(value, str) and value:
                        return value[:300]
                    if isinstance(value, dict):
                        message = value.get("message")
                        if message:
                            return str(message)[:300]
                return fallback
            if isinstance(err, str) and err:
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


async def download_media(url: str, kind: str = "image") -> Dict[str, Any]:
    """Download user-provided public media for upload flows.

    Only http(s) URLs; size-capped; content-type checked. This fetches a
    caller-supplied asset for the sole purpose of uploading it to the
    user's own account — it is not web scraping.
    """
    if not url.startswith(("http://", "https://")):
        raise PermanentPublishError("media", "media URL must be http(s)")
    cap = MAX_VIDEO_BYTES if kind == "video" else MAX_IMAGE_BYTES
    try:
        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            async with client.stream("GET", url) as response:
                if response.status_code >= 400:
                    raise PermanentPublishError(
                        "media", f"media download rejected (HTTP {response.status_code})",
                        response.status_code,
                    )
                content_type = (response.headers.get("content-type", "") or "").split(";")[0].strip()
                chunks, total = [], 0
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > cap:
                        raise PermanentPublishError("media", f"media exceeds {cap // 1024 // 1024}MB cap")
                    chunks.append(chunk)
    except PermanentPublishError:
        raise
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        raise RetryablePublishError("media", f"media download failed: {type(exc).__name__}") from exc
    data = b"".join(chunks)
    if not data:
        raise PermanentPublishError("media", "downloaded media is empty")
    expected = "video/" if kind == "video" else "image/"
    if content_type and not content_type.startswith(expected):
        raise PermanentPublishError("media", f"unexpected content type {content_type or 'unknown'}")
    return {"bytes": data, "mime": content_type or ("video/mp4" if kind == "video" else "image/jpeg")}


# ----------------------------------------------------------------------
# LinkedIn
# ----------------------------------------------------------------------
def _linkedin_headers(access_token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": LINKEDIN_VERSION,
        "Content-Type": "application/json",
    }


async def _linkedin_author_urn(client: httpx.AsyncClient, access_token: str) -> str:
    """Resolve the member URN via OpenID userinfo (no scraping)."""
    response = await client.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if response.status_code >= 400:
        raise _classify("linkedin", response.status_code, await _read_error(response))
    person_id = (response.json() or {}).get("sub", "")
    if not person_id:
        raise PermanentPublishError("linkedin", "could not resolve member identity")
    return f"urn:li:person:{person_id}"


async def _linkedin_upload_image(
    client: httpx.AsyncClient, access_token: str, author_urn: str,
    image_bytes: bytes, mime: str,
) -> str:
    """Register + binary-upload an image; returns the asset URN."""
    response = await client.post(
        "https://api.linkedin.com/v2/assets?action=registerUpload",
        headers=_linkedin_headers(access_token),
        json={"registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": author_urn,
            "serviceRelationships": [{
                "relationshipType": "OWNER",
                "identifier": "urn:li:userGeneratedContent",
            }],
        }},
    )
    if response.status_code >= 400:
        raise _classify("linkedin", response.status_code, await _read_error(response))
    value = (response.json() or {}).get("value", {})
    upload_url = value.get("uploadUrl", "")
    asset = value.get("asset", "")
    if not upload_url or not asset:
        raise PermanentPublishError("linkedin", "image upload registration failed")
    put = await client.put(upload_url, headers={"Authorization": f"Bearer {access_token}",
                                                "Content-Type": mime}, content=image_bytes)
    if put.status_code >= 400:
        raise _classify("linkedin", put.status_code, await _read_error(put))
    return asset


async def publish_linkedin(
    access_token: str,
    text: str,
    image_url: Optional[str] = None,
    visibility: str = "PUBLIC",
) -> Dict[str, Any]:
    """Publish a LinkedIn text (or image) post. Returns ``{"platform_post_id"}``."""
    if not (text or "").strip() and not image_url:
        raise PermanentPublishError("linkedin", "nothing to publish (empty text, no image)")
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        author_urn = await _linkedin_author_urn(client, access_token)
        if image_url:
            media = await download_media(image_url, kind="image")
            asset = await _linkedin_upload_image(client, access_token, author_urn, media["bytes"], media["mime"])
            media_payload = [{"status": "READY", "media": asset,
                              "description": {"text": (text or "")[:2000]}}]
            category, commentary = "IMAGE", text or ""
        else:
            media_payload, category, commentary = [], "NONE", text
        response = await client.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers=_linkedin_headers(access_token),
            json={
                "author": author_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {"com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": commentary},
                    "shareMediaCategory": category,
                    **({"media": media_payload} if media_payload else {}),
                }},
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": visibility},
            },
        )
    if response.status_code >= 400:
        raise _classify("linkedin", response.status_code, await _read_error(response))
    urn = response.headers.get("x-restli-id", "")
    if not urn:
        raise PermanentPublishError("linkedin", "publish response missing post URN")
    return {"platform_post_id": urn, "platform_post_url": ""}


# ----------------------------------------------------------------------
# Meta (Instagram + Facebook share the Graph OAuth app)
# ----------------------------------------------------------------------
async def _graph(
    client: httpx.AsyncClient, method: str, path: str, token: str, **kwargs: Any
) -> httpx.Response:
    params = dict(kwargs.pop("params", {}) or {})
    params.setdefault("access_token", token)
    return await client.request(method, f"https://graph.facebook.com/{GRAPH_VERSION}{path}",
                                params=params, **kwargs)


def _graph_error(platform: str, payload: Any, status: Optional[int]) -> PublishError:
    return _classify(platform, status, _safe_reason(payload))


async def _meta_pages(client: httpx.AsyncClient, user_token: str) -> List[Dict[str, Any]]:
    """Pages the user manages (needed for Page + IG publishing)."""
    response = await _graph(client, "GET", "/me/accounts",
                            user_token, params={"fields": "id,name,access_token,instagram_business_account"})
    if response.status_code >= 400:
        raise _graph_error("meta", response.json() if _is_json(response) else None, response.status_code)
    data = response.json() or {}
    return data.get("data", []) or []


def _is_json(response: httpx.Response) -> bool:
    try:
        response.json()
        return True
    except ValueError:
        return False


async def _resolve_instagram(client: httpx.AsyncClient, user_token: str) -> Dict[str, str]:
    """Find the IG business id + owning Page token. No scraping involved."""
    for page in await _meta_pages(client, user_token):
        ig = page.get("instagram_business_account") or {}
        if ig.get("id") and page.get("access_token"):
            return {"ig_user_id": str(ig["id"]), "page_token": str(page["access_token"]),
                    "page_id": str(page.get("id", ""))}
    raise PermanentPublishError("instagram", "no Instagram business account linked to a managed Page")


async def _resolve_facebook_page(client: httpx.AsyncClient, user_token: str) -> Dict[str, str]:
    pages = await _meta_pages(client, user_token)
    for page in pages:
        if page.get("id") and page.get("access_token"):
            return {"page_id": str(page["id"]), "page_token": str(page["access_token"]),
                    "page_name": str(page.get("name", ""))}
    raise PermanentPublishError("facebook", "no manageable Facebook Page found")


async def _poll_ig_container(client: httpx.AsyncClient, container_id: str, token: str) -> None:
    """Wait for async video-container processing (transient → retryable on timeout)."""
    import asyncio

    for _ in range(24):  # ~2 minutes max
        response = await _graph(client, "GET", f"/{container_id}", token,
                                params={"fields": "status_code"})
        if response.status_code >= 400:
            raise _graph_error("instagram", response.json() if _is_json(response) else None,
                               response.status_code)
        status_code = ((response.json() or {}).get("status_code") or "").upper()
        if status_code == "FINISHED":
            return
        if status_code == "ERROR":
            raise PermanentPublishError("instagram", "media container processing failed")
        await asyncio.sleep(5)
    raise RetryablePublishError("instagram", "media container still processing")


async def publish_instagram(
    access_token: str,
    caption: str,
    image_url: Optional[str] = None,
    video_url: Optional[str] = None,
    share_to_feed: bool = True,
) -> Dict[str, Any]:
    """Publish a photo post or Reel via the two-step container flow."""
    if not image_url and not video_url:
        raise PermanentPublishError("instagram", "photo posts need image_url, reels need video_url")
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        resolved = await _resolve_instagram(client, access_token)
        ig_id, token = resolved["ig_user_id"], resolved["page_token"]
        params: Dict[str, Any] = {"caption": caption or ""}
        if video_url:
            params.update({"media_type": "REELS", "video_url": video_url,
                           "share_to_feed_timeline": share_to_feed})
        else:
            params["image_url"] = image_url
        created = await _graph(client, "POST", f"/{ig_id}/media", token, data=params)
        if created.status_code >= 400:
            raise _graph_error("instagram", created.json() if _is_json(created) else None,
                               created.status_code)
        container_id = str((created.json() or {}).get("id", ""))
        if not container_id:
            raise PermanentPublishError("instagram", "container creation returned no id")
        if video_url:
            await _poll_ig_container(client, container_id, token)
        published = await _graph(client, "POST", f"/{ig_id}/media_publish", token,
                                 data={"creation_id": container_id})
        if published.status_code >= 400:
            raise _graph_error("instagram", published.json() if _is_json(published) else None,
                               published.status_code)
        media_id = str((published.json() or {}).get("id", ""))
        if not media_id:
            raise PermanentPublishError("instagram", "publish returned no media id")
        return {"platform_post_id": media_id, "platform_post_url": ""}


async def publish_facebook(
    access_token: str,
    message: str,
    link_url: Optional[str] = None,
    image_url: Optional[str] = None,
    video_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Publish to a Page: feed post, photo, or video (URL-based upload)."""
    if not (message or "").strip() and not image_url and not video_url:
        raise PermanentPublishError("facebook", "nothing to publish")
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        page = await _resolve_facebook_page(client, access_token)
        page_id, token = page["page_id"], page["page_token"]
        if video_url:
            response = await _graph(client, "POST", f"/{page_id}/videos", token,
                                    data={"file_url": video_url, "description": message or ""})
        elif image_url:
            response = await _graph(client, "POST", f"/{page_id}/photos", token,
                                    data={"url": image_url, "caption": message or ""})
        else:
            payload: Dict[str, Any] = {"message": message}
            if link_url:
                payload["link"] = link_url
            response = await client.post(
                f"https://graph.facebook.com/{GRAPH_VERSION}/{page_id}/feed",
                params={"access_token": token}, data=payload)
        if response.status_code >= 400:
            raise _graph_error("facebook", response.json() if _is_json(response) else None,
                               response.status_code)
        data = response.json() or {}
        post_id = str(data.get("post_id") or data.get("id") or "")
        if not post_id:
            raise PermanentPublishError("facebook", "publish returned no post id")
        return {"platform_post_id": post_id, "platform_post_url": ""}


# ----------------------------------------------------------------------
# YouTube (Data API v3 resumable upload)
# ----------------------------------------------------------------------
async def publish_youtube(
    access_token: str,
    title: str,
    description: str,
    video_bytes: Optional[bytes] = None,
    video_url: Optional[str] = None,
    mime_type: str = "video/mp4",
    tags: Optional[List[str]] = None,
    privacy: str = "unlisted",
    category_id: str = "27",
) -> Dict[str, Any]:
    """Upload a Short/video. Bytes win; otherwise the public media URL is
    downloaded server-side (user-supplied asset, not scraping)."""
    title = (title or "").strip()[:100]
    if not title:
        raise PermanentPublishError("youtube", "title is required")
    if privacy not in ("public", "unlisted", "private"):
        raise PermanentPublishError("youtube", f"invalid privacy status: {privacy}")
    if video_bytes is None:
        if not video_url:
            raise PermanentPublishError("youtube", "upload needs video bytes or a media URL")
        media = await download_media(video_url, kind="video")
        video_bytes, mime_type = media["bytes"], media["mime"]
    tag_list = [t for t in (tags or []) if t][:15]
    tag_list = [t for t in tag_list if len(" ".join(tag_list)) <= 500]
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    body = {"snippet": {"title": title, "description": (description or "")[:5000],
                        "tags": tag_list, "categoryId": category_id},
            "status": {"privacyStatus": privacy, "madeForKids": False,
                       "selfDeclaredMadeForKids": False}}
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        session = await client.post(
            "https://www.googleapis.com/upload/youtube/v3/videos"
            "?uploadType=resumable&part=snippet,status",
            headers={**headers, "X-Upload-Content-Length": str(len(video_bytes)),
                     "X-Upload-Content-Type": mime_type},
            json=body)
        if session.status_code >= 400:
            raise _classify("youtube", session.status_code, await _read_error(session))
        upload_url = session.headers.get("location", "")
        if not upload_url:
            raise PermanentPublishError("youtube", "no resumable upload session returned")
        uploaded = await client.put(upload_url, headers={
            "Authorization": f"Bearer {access_token}", "Content-Length": str(len(video_bytes)),
            "Content-Type": mime_type}, content=video_bytes)
        if uploaded.status_code >= 400:
            raise _classify("youtube", uploaded.status_code, await _read_error(uploaded))
        video_id = str((uploaded.json() or {}).get("id", ""))
        if not video_id:
            raise PermanentPublishError("youtube", "upload returned no video id")
        return {"platform_post_id": video_id,
                "platform_post_url": f"https://www.youtube.com/watch?v={video_id}"}


# ----------------------------------------------------------------------
# Dispatcher + dry-run planning
# ----------------------------------------------------------------------
def _validate_common(platform: str, text: str) -> None:
    if platform not in ("linkedin", "instagram", "facebook", "youtube"):
        raise PermanentPublishError(platform, f"publishing to {platform} is not supported")


async def publish_to_platform(
    platform: str, access_token: str, payload: Dict[str, Any]
) -> Dict[str, Any]:
    """Publish pre-validated content to one platform. Returns external ids."""
    if platform == "linkedin":
        return await publish_linkedin(
            access_token, text=payload.get("text", ""),
            image_url=payload.get("image_url"),
            visibility=payload.get("visibility", "PUBLIC"),
        )
    if platform == "instagram":
        return await publish_instagram(
            access_token, caption=payload.get("caption") or payload.get("text", ""),
            image_url=payload.get("image_url"), video_url=payload.get("video_url"),
        )
    if platform == "facebook":
        return await publish_facebook(
            access_token, message=payload.get("text", ""),
            link_url=payload.get("link_url"), image_url=payload.get("image_url"),
            video_url=payload.get("video_url"),
        )
    if platform == "youtube":
        return await publish_youtube(
            access_token, title=payload.get("title", ""),
            description=payload.get("description") or payload.get("text", ""),
            video_bytes=payload.get("video_bytes"), video_url=payload.get("video_url"),
            mime_type=payload.get("mime_type", "video/mp4"),
            tags=payload.get("tags", []),
            privacy=payload.get("privacy", "unlisted"),
            category_id=payload.get("category_id", "27"),
        )
    raise PermanentPublishError(platform, f"publishing to {platform} is not supported")


def plan_publish(platform: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """DRY-RUN planner: validate shape/limits without any network calls.

    Returns ``{"proceeding", "checks": [...], "would_post": {...}}``.
    """
    checks: List[Dict[str, Any]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})

    if platform not in ("linkedin", "instagram", "facebook", "youtube"):
        check("supported_platform", False, f"unsupported: {platform}")
        return {"proceeding": False, "checks": checks, "would_post": {}}

    text = (payload.get("text") or payload.get("caption") or "").strip()
    check("non_empty", bool(text), "" if text else "nothing to publish")
    limits = {"linkedin": 3000, "instagram": 2200, "facebook": 63206, "youtube": 5000}
    limit = limits[platform]
    check("within_limit", len(text) <= limit, f"{len(text)}/{limit} chars")
    media_urls = [u for u in [payload.get("image_url"), payload.get("video_url")] if u]
    check("media_urls_valid", all(u.startswith(("http://", "https://")) for u in media_urls),
          "" if media_urls else "text-only post")
    if platform == "instagram" and not media_urls:
        check("instagram_requires_media", False, "photo/video URL required")
    else:
        check("instagram_requires_media", True, "")
    if platform == "youtube":
        title = (payload.get("title") or "").strip()
        check("youtube_title", bool(title) and len(title) <= 100,
              "" if title else "title required")
        check("youtube_media", bool(payload.get("video_url") or payload.get("video_bytes")),
              "video bytes or media URL required")
    proceeding = all(c["ok"] for c in checks)
    preview = {k: v for k, v in payload.items() if k != "video_bytes"}
    if payload.get("video_bytes"):
        preview["video_bytes"] = f"<{len(payload['video_bytes'])} bytes>"
    return {"proceeding": proceeding, "checks": checks, "would_post": preview}
