"""
Performance Analysis stage: Published Content + Analytics → aggregates.

Pure functions (no DB, no HTTP) so they are deterministic and unit-testable.
Rules:
- Unsupported metrics are ``None`` and are EXCLUDED from totals/averages —
  never treated as 0. A post with no supported measurements at all counts
  as ``unmeasured`` (publishing status is still tracked).
- ``engagement_rate`` per snapshot = (likes + comments + shares + saves) /
  impressions, falling back to / reach, then / views. Result is a percent.
- Rankings use engagement_rate first, then absolute likes+comments+shares.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.content_analytics.schemas import PerformanceSummary, PlatformBreakdown


def _num(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    return num


def compute_engagement_rate(snapshot: Dict[str, Any]) -> Optional[float]:
    """Compute engagement rate from supported inputs only. None when impossible."""
    likes = _num(snapshot.get("likes")) or 0.0
    comments = _num(snapshot.get("comments")) or 0.0
    shares = _num(snapshot.get("shares")) or 0.0
    saves = _num(snapshot.get("saves")) or 0.0
    has_any_engagement_input = any(
        snapshot.get(k) is not None for k in ("likes", "comments", "shares", "saves")
    )
    if not has_any_engagement_input:
        return None
    interactions = likes + comments + shares + saves
    for denominator_key in ("impressions", "reach", "views"):
        denominator = _num(snapshot.get(denominator_key))
        if denominator and denominator > 0:
            return round((interactions / denominator) * 100.0, 2)
    return None


def compute_ctr(snapshot: Dict[str, Any]) -> Optional[float]:
    clicks = _num(snapshot.get("clicks"))
    impressions = _num(snapshot.get("impressions"))
    if clicks is None or not impressions:
        return None
    return round((clicks / impressions) * 100.0, 2)


def _is_measured(snapshot: Dict[str, Any]) -> bool:
    return any(
        snapshot.get(k) is not None
        for k in ("views", "impressions", "likes", "comments", "shares", "saves", "clicks", "reach")
    )


def _sum(values: List[Optional[float]]) -> Optional[int]:
    real = [v for v in values if v is not None]
    if not real:
        return None
    return int(sum(real))


def _avg(values: List[Optional[float]]) -> Optional[float]:
    real = [v for v in values if v is not None]
    if not real:
        return None
    return round(sum(real) / len(real), 2)


def _breakdown(rows: List[Dict[str, Any]]) -> PlatformBreakdown:
    measured = [r for r in rows if r.get("_measured")]
    return PlatformBreakdown(
        posts=len(rows),
        views=_sum([r.get("views") for r in measured]),
        impressions=_sum([r.get("impressions") for r in measured]),
        likes=_sum([r.get("likes") for r in measured]),
        comments=_sum([r.get("comments") for r in measured]),
        shares=_sum([r.get("shares") for r in measured]),
        avg_engagement_rate=_avg([r.get("engagement_rate") for r in measured if r.get("engagement_rate") is not None]),
        measured_posts=len(measured),
    )


def analyse_performance(
    latest_snapshots: List[Dict[str, Any]],
    total_published: int,
    window_days: int = 30,
    top_n: int = 5,
) -> PerformanceSummary:
    """Aggregate latest-snapshot-per-post rows into a PerformanceSummary.

    Each row must contain: content_id, platform, content_type (+title),
    and snapshot metrics (or None when unmeasured).
    """
    for row in latest_snapshots:
        row["_measured"] = _is_measured(row)
        if row.get("engagement_rate") is None and row["_measured"]:
            row["engagement_rate"] = compute_engagement_rate(row)

    measured = [r for r in latest_snapshots if r.get("_measured")]
    by_platform: Dict[str, List[Dict[str, Any]]] = {}
    by_type: Dict[str, List[Dict[str, Any]]] = {}
    for row in latest_snapshots:
        by_platform.setdefault(str(row.get("platform", "unknown")), []).append(row)
        by_type.setdefault(str(row.get("content_type", "post")), []).append(row)

    def _rank_key(row: Dict[str, Any]) -> tuple:
        rate = row.get("engagement_rate")
        interactions = sum(_num(row.get(k)) or 0.0 for k in ("likes", "comments", "shares"))
        return (rate is not None, rate or -1.0, interactions)

    ranked = sorted(measured, key=_rank_key, reverse=True)

    def _card(row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "content_id": row.get("content_id"),
            "title": row.get("title", ""),
            "platform": row.get("platform"),
            "content_type": row.get("content_type"),
            "engagement_rate": row.get("engagement_rate"),
            "likes": row.get("likes"),
            "comments": row.get("comments"),
            "shares": row.get("shares"),
            "impressions": row.get("impressions"),
            "views": row.get("views"),
        }

    return PerformanceSummary(
        total_published=total_published,
        measured_posts=len(measured),
        unmeasured_posts=total_published - len(measured),
        totals={
            "views": _sum([r.get("views") for r in measured]),
            "impressions": _sum([r.get("impressions") for r in measured]),
            "likes": _sum([r.get("likes") for r in measured]),
            "comments": _sum([r.get("comments") for r in measured]),
            "shares": _sum([r.get("shares") for r in measured]),
        },
        avg_engagement_rate=_avg([r.get("engagement_rate") for r in measured if r.get("engagement_rate") is not None]),
        by_platform={k: _breakdown(v) for k, v in by_platform.items()},
        by_content_type={k: _breakdown(v) for k, v in by_type.items()},
        top_posts=[_card(r) for r in ranked[:top_n]],
        bottom_posts=[_card(r) for r in ranked[-top_n:]][::-1] if ranked else [],
        window_days=window_days,
    )
