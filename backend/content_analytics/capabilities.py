"""
Official-API capability matrix for content analytics.

Every entry documents *which official endpoint* a metric comes from.
If a platform has no official endpoint for a metric it is marked
``supported=False`` and the analytics layer MUST return ``None`` for it
— never scrape, never guess, never store a fabricated zero as a real
measurement (the DB row keeps 0 only because the legacy
``content_analytics`` columns are NOT NULL; the API layer converts back
to ``None`` — see ``service.to_public_snapshot``).

Tracked metrics (user request):
- publishing_status : always available locally (reflects the official
  publish outcome recorded in ``content_calendar``). Not a platform metric.
- views / impressions
- likes / reactions  (reactions are normalised to ``likes``)
- comments
- shares
- engagement metrics (engagement_rate, computed only from supported inputs)

Platform notes (official docs, 2024-2026):
- YouTube Data API v3 ``videos.list(part=statistics)`` returns
  viewCount / likeCount / commentCount. Impressions, reach, shares,
  saves, clicks require the separate YouTube Analytics API and are NOT
  tracked here → unsupported.
- Instagram Graph API: ``GET /{ig-media-id}?fields=like_count,comments_count``
  plus ``GET /{ig-media-id}/insights?metric=impressions,reach,shares,saves``.
  ``plays``/views exist for Reels via ``plays`` metric where the app has
  permission; coverage varies → ``views`` marked conditional.
- Facebook Graph API: ``GET /{page-post-id}?fields=likes.summary(true),
  comments.summary(true),shares`` plus
  ``GET /{post-id}/insights?metric=post_impressions,post_impressions_unique``.
  Saves/clicks/watch-time are not exposed for plain feed posts → unsupported.
- LinkedIn: organic post analytics via ``/v2/socialActions/{urn}`` likes /
  comments summaries have narrow visibility (UGC, member perms). No public
  impressions endpoint for member shares without Marketing API access.
  → likes/comments/shares are conditional; views/impressions unsupported.
- twitter / tiktok: this codebase has no OAuth provider for them
  (see ``backend/social_integrations/oauth.py`` SUPPORTED_PLATFORMS), so no
  official token exists to query → all remote metrics unsupported. Only
  local publishing status is tracked.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

# Metrics the product tracks (publishing_status is local, the rest remote).
TRACKED_METRICS: List[str] = [
    "publishing_status",
    "views",
    "impressions",
    "likes",
    "comments",
    "shares",
    "saves",
    "clicks",
    "reach",
    "engagement_rate",
]

SUPPORTED_PLATFORMS: List[str] = ["youtube", "instagram", "facebook", "linkedin"]


@dataclass(frozen=True)
class MetricCapability:
    """One metric's official-API provenance on one platform."""

    supported: bool
    source: str = ""
    # True when support depends on media kind / permissions / API version.
    conditional: bool = False
    note: str = ""


@dataclass(frozen=True)
class PlatformCapabilities:
    platform: str
    metrics: Dict[str, MetricCapability] = field(default_factory=dict)
    publish_status_source: str = "content_calendar (official publish outcome)"


def _m(supported: bool, source: str = "", conditional: bool = False, note: str = "") -> MetricCapability:
    return MetricCapability(supported=supported, source=source, conditional=conditional, note=note)


YT_STATS = "YouTube Data API v3 videos.list(part=statistics)"
IG_MEDIA = "Instagram Graph API /{ig-media-id}?fields=like_count,comments_count"
IG_INSIGHTS = "Instagram Graph API /{ig-media-id}/insights"
FB_POST = "Facebook Graph API /{post-id}?fields=likes,comments,shares"
FB_INSIGHTS = "Facebook Graph API /{post-id}/insights"
LI_ACTIONS = "LinkedIn REST /v2/socialActions (limited organic coverage)"

PLATFORM_CAPABILITIES: Dict[str, PlatformCapabilities] = {
    "youtube": PlatformCapabilities(
        platform="youtube",
        metrics={
            "views": _m(True, YT_STATS),
            "impressions": _m(False, note="Requires YouTube Analytics API, not Data API v3 — not tracked."),
            "likes": _m(True, YT_STATS, note="likeCount; reactions normalised to likes."),
            "comments": _m(True, YT_STATS),
            "shares": _m(False, note="Not exposed by Data API v3 videos.list."),
            "saves": _m(False, note="Not exposed by Data API v3."),
            "clicks": _m(False, note="Not exposed by Data API v3."),
            "reach": _m(False, note="Requires YouTube Analytics API — not tracked."),
            "engagement_rate": _m(True, "computed from supported inputs (likes+comments)/views"),
        },
    ),
    "instagram": PlatformCapabilities(
        platform="instagram",
        metrics={
            "views": _m(True, IG_INSIGHTS, conditional=True, note="Reels 'plays' where permitted; varies by app review."),
            "impressions": _m(True, IG_INSIGHTS),
            "likes": _m(True, IG_MEDIA),
            "comments": _m(True, IG_MEDIA),
            "shares": _m(True, IG_INSIGHTS),
            "saves": _m(True, IG_INSIGHTS),
            "clicks": _m(False, note="Not exposed for IG media insights."),
            "reach": _m(True, IG_INSIGHTS),
            "engagement_rate": _m(True, "computed from supported inputs"),
        },
    ),
    "facebook": PlatformCapabilities(
        platform="facebook",
        metrics={
            "views": _m(False, note="Video views need video insights; plain feed posts unsupported."),
            "impressions": _m(True, FB_INSIGHTS, note="post_impressions."),
            "likes": _m(True, FB_POST, note="likes.summary(true); reactions normalised to likes."),
            "comments": _m(True, FB_POST, note="comments.summary(true)."),
            "shares": _m(True, FB_POST, note="'shares' field when present."),
            "saves": _m(False, note="Not exposed for Page posts."),
            "clicks": _m(False, note="post_consumptions not tracked here to avoid permission drift."),
            "reach": _m(True, FB_INSIGHTS, note="post_impressions_unique."),
            "engagement_rate": _m(True, "computed from supported inputs"),
        },
    ),
    "linkedin": PlatformCapabilities(
        platform="linkedin",
        metrics={
            "views": _m(False, note="No member-share impressions endpoint without Marketing API."),
            "impressions": _m(False, note="No member-share impressions endpoint without Marketing API."),
            "likes": _m(True, LI_ACTIONS, conditional=True, note="socialActions likes summary; narrow visibility."),
            "comments": _m(True, LI_ACTIONS, conditional=True, note="socialActions comments summary; narrow visibility."),
            "shares": _m(True, LI_ACTIONS, conditional=True, note="Reshare count where visible."),
            "saves": _m(False, note="Not exposed."),
            "clicks": _m(False, note="Not exposed for member shares."),
            "reach": _m(False, note="Not exposed for member shares."),
            "engagement_rate": _m(True, "computed only when a supported denominator exists", conditional=True),
        },
    ),
}


def _norm(platform: str) -> str:
    return (platform or "").strip().lower()


def get_capabilities(platform: str) -> PlatformCapabilities | None:
    """Return the capability record for a platform (None = no official access)."""
    return PLATFORM_CAPABILITIES.get(_norm(platform))


def is_metric_supported(platform: str, metric: str) -> bool:
    """True only when the official API exposes this metric on this platform."""
    caps = get_capabilities(platform)
    if caps is None:
        return metric == "publishing_status"
    if metric == "publishing_status":
        return True
    cap = caps.metrics.get(metric)
    return bool(cap and cap.supported)


def supported_metrics_for(platform: str) -> List[str]:
    caps = get_capabilities(platform)
    if caps is None:
        return ["publishing_status"]
    return ["publishing_status"] + [k for k, v in caps.metrics.items() if v.supported]


def unsupported_metrics_for(platform: str) -> List[str]:
    supported = set(supported_metrics_for(platform))
    return [m for m in TRACKED_METRICS if m not in supported]
