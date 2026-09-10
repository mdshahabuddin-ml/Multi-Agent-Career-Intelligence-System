"""
Sample historical content-performance data for the Hermes optimization loop.

Deterministic fixture (10 posts, 4 platforms, mixed measurability):
- Winning topics: ``resume`` (IG reels) and ``python`` (YT + IG).
- Struggler: ``system-design`` deep dive (0.33%) + zero-interaction YT post.
- Unmeasured: LinkedIn limited-visibility post + Twitter (no metrics API).
- ``None`` = official-API-unsupported (never zero-filled).

Each row matches ``ContentAnalyticsService.latest_per_post`` shape plus
``hashtags`` / ``published_at`` enrichment used by the Hermes loop.
"""

from __future__ import annotations

from typing import Any, Dict, List


def _row(content_id: int, title: str, platform: str, content_type: str,
         hashtags: List[str], published_at: str, **metrics: Any) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "content_id": content_id,
        "title": title,
        "platform": platform,
        "content_type": content_type,
        "status": "published",
        "hashtags": hashtags,
        "published_at": published_at,
        "engagement_rate": None,
        "views": None,
        "impressions": None,
        "likes": None,
        "comments": None,
        "shares": None,
        "saves": None,
        "clicks": None,
        "reach": None,
    }
    base.update(metrics)
    return base


SAMPLE_HISTORY: List[Dict[str, Any]] = [
    _row(1, "Python async await tutorial", "youtube", "video",
         ["python", "async"], "2026-08-20T10:00:00",
         views=5000, likes=300, comments=40),
    _row(2, "Python dataclasses guide", "youtube", "video",
         ["python"], "2026-08-22T10:00:00",
         views=3000, likes=120, comments=10),
    _row(3, "Resume tips that actually work", "instagram", "reel",
         ["resume", "career"], "2026-08-24T18:00:00",
         impressions=8000, reach=6500, likes=500, comments=60, shares=40, saves=30),
    _row(4, "Resume tips part 2", "instagram", "post",
         ["resume"], "2026-08-26T18:00:00",
         impressions=4000, reach=3200, likes=120, comments=5, shares=2, saves=3),
    _row(5, "System design basics", "facebook", "post",
         ["system-design"], "2026-08-27T12:00:00",
         impressions=2000, reach=1600, likes=30, comments=2, shares=1),
    _row(6, "System design deep dive", "facebook", "post",
         ["system-design"], "2026-08-28T12:00:00",
         impressions=1500, reach=1200, likes=5, comments=0, shares=0),
    _row(7, "Open to work post", "linkedin", "post",
         [], "2026-08-29T09:00:00"),
    _row(8, "Kubernetes networking explained", "youtube", "video",
         ["kubernetes"], "2026-08-30T10:00:00",
         views=800, likes=0, comments=0),
    _row(9, "Python async mistakes to avoid", "instagram", "reel",
         ["python", "async"], "2026-09-01T18:00:00",
         impressions=6000, reach=5000, likes=200, comments=8, shares=5, saves=4),
    _row(10, "Weekend hot take", "twitter", "post",
          [], "2026-09-02T15:00:00"),
]


def sample_history() -> List[Dict[str, Any]]:
    """Fresh deep-ish copy so tests cannot mutate the shared fixture."""
    return [dict(row) for row in SAMPLE_HISTORY]
