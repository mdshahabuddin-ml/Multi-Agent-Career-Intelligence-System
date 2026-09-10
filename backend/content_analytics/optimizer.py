"""
Future Content Optimization stage: Feedback → what to publish next.

Produces prioritized, actionable suggestions grounded ONLY in measured
data (unsupported metrics never drive a recommendation). Every suggestion
carries a rationale naming the evidence. When evidence is thin, the plan
says so and recommends measurement first instead of guessing.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.content_analytics.schemas import (
    OptimizationPlan,
    OptimizationSuggestion,
    PerformanceSummary,
)


def _pick_best(mapping: Dict[str, Any], key: str = "avg_engagement_rate") -> Optional[str]:
    best: Optional[str] = None
    best_val: Optional[float] = None
    for name, breakdown in mapping.items():
        val = getattr(breakdown, key, None)
        if val is None:
            continue
        # Require at least one measured post behind the average.
        if getattr(breakdown, "measured_posts", 0) <= 0:
            continue
        if best_val is None or val > best_val:
            best, best_val = name, val
    return best


def build_optimization_plan(
    performance: PerformanceSummary,
    unmeasured_platforms: List[str] | None = None,
) -> OptimizationPlan:
    """Turn a PerformanceSummary into a prioritized optimization plan."""
    suggestions: List[OptimizationSuggestion] = []
    unmeasured_platforms = unmeasured_platforms or []

    best_platform = _pick_best(performance.by_platform)
    best_type = _pick_best(performance.by_content_type)

    if performance.measured_posts == 0:
        suggestions.append(OptimizationSuggestion(
            area="measurement",
            suggestion="Refresh analytics for published posts before changing strategy.",
            rationale="No post has a supported metric from an official API yet, so any creative advice would be a guess.",
            priority="high",
        ))
        return OptimizationPlan(
            suggestions=suggestions,
            best_platform=None,
            best_content_type=None,
            generated_at=datetime.now(timezone.utc),
        )

    if best_platform:
        top = performance.by_platform[best_platform]
        suggestions.append(OptimizationSuggestion(
            area="platform",
            suggestion=f"Prioritise {best_platform} for the next 3–5 posts.",
            rationale=f"Highest average engagement rate ({top.avg_engagement_rate}%) across {top.measured_posts} measured post(s).",
            priority="high",
        ))
    else:
        suggestions.append(OptimizationSuggestion(
            area="measurement",
            suggestion="Hold platform mix steady until engagement rates are comparable.",
            rationale="No platform has a supported engagement denominator yet — volume without measurement hides winners.",
            priority="medium",
        ))

    if best_type:
        top = performance.by_content_type[best_type]
        suggestions.append(OptimizationSuggestion(
            area="format",
            suggestion=f"Produce more '{best_type}' content; it leads on engagement.",
            rationale=f"'{best_type}' averages {top.avg_engagement_rate}% engagement over {top.measured_posts} measured post(s).",
            priority="high",
        ))

    if performance.bottom_posts:
        worst = performance.bottom_posts[0]
        if worst.get("engagement_rate") is not None and worst["engagement_rate"] < 1.0:
            suggestions.append(OptimizationSuggestion(
                area="creative",
                suggestion=f"Rework '{worst.get('title', 'lowest post')}' angle before repeating it (post {worst.get('content_id')}).",
                rationale=f"Lowest engagement at {worst.get('engagement_rate')}% — test a new hook and creative, not just reposting.",
                priority="medium",
            ))

    if performance.top_posts:
        winner = performance.top_posts[0]
        suggestions.append(OptimizationSuggestion(
            area="creative",
            suggestion=f"Create a follow-up to '{winner.get('title', 'top post')}' (post {winner.get('content_id')}).",
            rationale=f"Top performer at {winner.get('engagement_rate')}% — same topic, new angle compounds winners.",
            priority="medium",
        ))

    # Cadence guidance from sample size, not from thin air.
    if performance.total_published < 5:
        suggestions.append(OptimizationSuggestion(
            area="cadence",
            suggestion="Publish at least weekly until 8–10 measured posts exist.",
            rationale=f"Only {performance.total_published} published post(s) in scope — patterns before that are noise.",
            priority="low",
        ))
    elif performance.unmeasured_posts > performance.measured_posts:
        suggestions.append(OptimizationSuggestion(
            area="measurement",
            suggestion="Close the measurement gap: refresh analytics for unmeasured posts.",
            rationale=f"{performance.unmeasured_posts} of {performance.total_published} posts lack official-API metrics.",
            priority="high",
        ))

    for platform in sorted(set(unmeasured_platforms)):
        suggestions.append(OptimizationSuggestion(
            area="measurement",
            suggestion=f"Judge {platform} inside its native analytics, not here.",
            rationale=f"{platform} exposes no comparable metric via its official API in this integration — don't rank it against measured platforms.",
            priority="low",
        ))

    return OptimizationPlan(
        suggestions=suggestions,
        best_platform=best_platform,
        best_content_type=best_type,
        generated_at=datetime.now(timezone.utc),
    )
