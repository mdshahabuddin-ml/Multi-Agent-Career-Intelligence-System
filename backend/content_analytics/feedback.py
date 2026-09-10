"""
Feedback stage: Performance Analysis → per-post + portfolio feedback.

Deterministic, rule-based (no LLM) so feedback is explainable and stable.
Thresholds are deliberately conservative and documented below.

Verdicts:
- ``unmeasured`` — no supported metric from the official API (e.g. a
  LinkedIn post whose counts are not visible, or twitter/tiktok which have
  no wired metrics API). Feedback explains *why* instead of guessing.
- ``strong`` — engagement_rate >= 5% OR top-quartile interactions.
- ``steady`` — engagement_rate >= 1% with measurable reach.
- ``needs_attention`` — measurable but below 1%, or measurable with
  reach but zero interactions.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.content_analytics.schemas import PortfolioFeedback, PostFeedback

STRONG_RATE = 5.0
STEADY_RATE = 1.0


def _num(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def feedback_for_post(row: Dict[str, Any], median_interactions: float = 0.0) -> PostFeedback:
    """Build feedback for one latest-snapshot row (see analysis.analyse_performance)."""
    content_id = int(row.get("content_id", 0))
    platform = str(row.get("platform", "unknown"))
    rate = _num(row.get("engagement_rate"))
    likes = _num(row.get("likes")) or 0.0
    comments = _num(row.get("comments")) or 0.0
    shares = _num(row.get("shares")) or 0.0
    impressions = _num(row.get("impressions"))
    reach = _num(row.get("reach"))
    views = _num(row.get("views"))
    supported: List[str] = list(row.get("supported_metrics") or [])
    unsupported: List[str] = list(row.get("unsupported_metrics") or [])

    measured = any(row.get(k) is not None for k in ("views", "impressions", "likes", "comments", "shares"))
    if not measured:
        why = (
            f"No engagement metric is exposed by the {platform} official API for this post"
            + (f" (unsupported here: {', '.join(unsupported)})" if unsupported else "")
            + ". Publishing status is still tracked; check performance natively."
        )
        return PostFeedback(
            content_id=content_id,
            platform=platform,
            verdict="unmeasured",
            strengths=["Published successfully — distribution happened."],
            risks=[why],
            next_experiment=f"Refresh this post later or compare publishing status across {platform} posts.",
            engagement_rate=None,
        )

    interactions = likes + comments + shares
    strengths: List[str] = []
    risks: List[str] = []
    if rate is not None and rate >= STRONG_RATE:
        verdict = "strong"
        strengths.append(f"High engagement rate ({rate}%) — format and topic resonate.")
    elif rate is not None and rate >= STEADY_RATE:
        verdict = "steady"
        strengths.append(f"Healthy engagement rate ({rate}%).")
    else:
        verdict = "needs_attention"
        if rate is not None:
            risks.append(f"Low engagement rate ({rate}%) — hook, creative, or targeting needs work.")
        else:
            risks.append("Engagement rate unavailable (no supported denominator) — compare raw interactions.")

    audience = impressions or reach or views
    if audience and audience > 0:
        if interactions == 0:
            risks.append(f"Reach ({int(audience)}) with zero interactions — strengthen the call to action.")
        elif comments == 0 and likes > 0:
            risks.append("Likes without comments — add a question or prompt to spark replies.")
        if shares and shares > 0:
            strengths.append(f"Shared {int(shares)}× — content travels beyond followers.")
    else:
        risks.append("No reach/impressions from the official API — cannot judge distribution; use native analytics.")

    if interactions >= median_interactions and median_interactions > 0 and verdict != "strong":
        strengths.append("Above-median interactions for your recent posts.")

    if "impressions" in unsupported and "reach" in unsupported and "views" in unsupported:
        risks.append(f"{platform} exposes no distribution metric here — measure success via interactions only.")

    experiment: Optional[str]
    if verdict == "strong":
        experiment = "Replicate the hook + format this week with a follow-up angle on the same topic."
    elif verdict == "steady":
        experiment = "Keep the format; test one variable (hook first line, thumbnail, or posting time)."
    else:
        experiment = "Rewrite the hook, tighten the first 2 lines, and retry the topic in a different format."
    if supported and len(supported) <= 2:
        experiment += f" Note: only {', '.join(supported)} are measurable via the {platform} official API."

    return PostFeedback(
        content_id=content_id,
        platform=platform,
        verdict=verdict,
        strengths=strengths,
        risks=risks,
        next_experiment=experiment,
        engagement_rate=rate,
    )


def feedback_for_portfolio(rows: List[Dict[str, Any]]) -> PortfolioFeedback:
    """Aggregate per-post feedback into portfolio-level strengths/risks."""
    interactions = [
        ((_num(r.get("likes")) or 0.0) + (_num(r.get("comments")) or 0.0) + (_num(r.get("shares")) or 0.0))
        for r in rows
        if any(r.get(k) is not None for k in ("likes", "comments", "shares"))
    ]
    interactions_sorted = sorted(interactions)
    median = interactions_sorted[len(interactions_sorted) // 2] if interactions_sorted else 0.0

    per_post = [feedback_for_post(r, median_interactions=median) for r in rows]
    strong = sum(1 for p in per_post if p.verdict == "strong")
    attention = sum(1 for p in per_post if p.verdict == "needs_attention")
    unmeasured = sum(1 for p in per_post if p.verdict == "unmeasured")

    strengths: List[str] = []
    risks: List[str] = []
    if strong:
        strengths.append(f"{strong} post(s) with strong engagement — double down on those formats.")
    if attention:
        risks.append(f"{attention} post(s) need attention — rework hooks before repeating topics.")
    if unmeasured:
        risks.append(
            f"{unmeasured} post(s) are unmeasured via official APIs — "
            "use native platform analytics for those before judging them."
        )
    if not per_post:
        overall = "No published posts in scope yet — publish first, then refresh analytics."
    elif strong and not attention:
        overall = "Portfolio is healthy — protect what works and scale cadence carefully."
    elif attention > strong:
        overall = "More strugglers than winners — prioritise creative iteration over volume."
    else:
        overall = "Mixed portfolio — replicate winners, fix one variable per struggler."

    return PortfolioFeedback(overall=overall, strengths=strengths, risks=risks, per_post=per_post)
