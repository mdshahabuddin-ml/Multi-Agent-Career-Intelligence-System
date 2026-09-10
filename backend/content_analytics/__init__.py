"""
Content Analytics — isolated analytics layer for published social content.

Pipeline:
    Published Content
      → Analytics (official-API snapshots)
      → Performance Analysis (aggregates, rankings, trends)
      → Feedback (strengths / risks per post + portfolio)
      → Future Content Optimization (what to publish next)

Isolation contract (do not break):
- NEVER imports from ``backend.services.career_service`` or
  ``backend.api.career`` and NEVER reads/writes career tables
  (``learning_plans``, skills, etc.).
- Reads only content tables: ``content_calendar`` (publishing status),
  ``content_analytics`` (snapshots), ``social_accounts`` (OAuth token),
  ``social_posts`` (best-effort mirror).
- Writes only to ``content_analytics`` (plus best-effort ``social_posts``
  counters). Career analytics are untouched.
- Tracks ONLY data available through official platform APIs
  (see ``capabilities.py``). Anything an official API does not expose is
  surfaced as ``None`` (unsupported) — never scraped, never fabricated
  as zero.

Official API sources:
- YouTube: Data API v3 ``videos.list(part=statistics)``
- Instagram: Graph API ``/{media-id}`` + ``/{media-id}/insights``
- Facebook: Graph API ``/{post-id}`` + ``/{post-id}/insights``
- LinkedIn: REST ``/v2/socialActions`` (limited organic coverage)
"""

from backend.content_analytics.capabilities import (
    PLATFORM_CAPABILITIES,
    SUPPORTED_PLATFORMS,
    TRACKED_METRICS,
    get_capabilities,
    is_metric_supported,
    supported_metrics_for,
    unsupported_metrics_for,
)

__all__ = [
    "PLATFORM_CAPABILITIES",
    "SUPPORTED_PLATFORMS",
    "TRACKED_METRICS",
    "get_capabilities",
    "is_metric_supported",
    "supported_metrics_for",
    "unsupported_metrics_for",
]

__version__ = "0.1.0"
