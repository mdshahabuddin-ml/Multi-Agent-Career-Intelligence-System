import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from backend.agents.jobs.job_matching_agent import JobMatch
from backend.agents.jobs.job_normalizer import NormalizedJob

logger = logging.getLogger(__name__)


@dataclass
class RankedOpportunity:
    """A ranked job opportunity with detailed scoring."""
    job_match: JobMatch
    rank: int
    composite_score: float
    tier: str  # "excellent", "good", "fair", "poor"
    highlights: List[str]
    concerns: List[str]
    action_items: List[str]


class OpportunityRanker:
    """Rank job opportunities based on multiple factors."""

    def __init__(self):
        self.name = "opportunity_ranker"

    def rank_opportunities(
        self,
        matches: List[JobMatch],
        candidate_profile: Optional[Dict[str, Any]] = None,
    ) -> List[RankedOpportunity]:
        """Rank a list of job matches."""
        logger.info(f"Ranking {len(matches)} job opportunities")

        ranked = []
        for i, match in enumerate(matches):
            ranked_opp = self._rank_single(match, candidate_profile)
            ranked_opp.rank = i + 1
            ranked.append(ranked_opp)

        # Assign tiers based on composite score
        self._assign_tiers(ranked)

        return ranked

    def _rank_single(
        self,
        match: JobMatch,
        candidate_profile: Optional[Dict[str, Any]] = None,
    ) -> RankedOpportunity:
        """Rank a single job match with detailed analysis."""

        # Base score from matching
        base_score = match.match_score

        # Boost factors
        boost = 0
        highlights = []
        concerns = []

        # Skill match boost
        skill_score = match.skill_match.get("score", 0)
        if skill_score >= 90:
            boost += 5
            highlights.append(f"Excellent skill match ({skill_score}%)")
        elif skill_score >= 70:
            boost += 2
            highlights.append(f"Good skill match ({skill_score}%)")
        elif skill_score < 50:
            concerns.append(f"Skill gap: {len(match.missing_skills)} required skills missing")

        # Experience match
        exp_status = match.experience_match.get("status", "")
        if exp_status == "exceeds":
            boost += 3
            highlights.append("Experience exceeds requirements")
        elif exp_status == "below":
            gap = abs(match.experience_match.get("gap", 0))
            if gap <= 1:
                concerns.append(f"Slightly below required experience ({gap} year gap)")
            else:
                concerns.append(f"Below required experience ({gap} year gap)")

        # Location match
        loc_status = match.location_match.get("status", "")
        if loc_status == "remote_match":
            boost += 3
            highlights.append("Remote-friendly position")
        elif loc_status == "candidate_wants_remote":
            concerns.append("On-site role but you prefer remote")
        elif loc_status == "location_mismatch":
            concerns.append("Location may require relocation")

        # Salary match
        sal_status = match.salary_match.get("status", "")
        if sal_status == "meets_expectations":
            boost += 2
            highlights.append("Salary meets expectations")
        elif sal_status == "below_expectations":
            concerns.append("Salary may be below expectations")

        # Recency boost
        # (would need posted_date from job)
        # For now, assume recent

        # Quality score boost
        if hasattr(match, 'quality_score') and match.quality_score > 0.8:
            boost += 2
            highlights.append("High quality job posting")

        composite_score = min(100, base_score + boost)

        # Tier assignment (will be finalized in _assign_tiers)
        tier = self._determine_tier(composite_score)

        # Action items
        action_items = self._generate_action_items(match, concerns)

        return RankedOpportunity(
            job_match=match,
            rank=0,  # Will be set after sorting
            composite_score=round(composite_score, 1),
            tier=tier,
            highlights=highlights,
            concerns=concerns,
            action_items=action_items,
        )

    def _determine_tier(self, score: float) -> str:
        """Determine tier based on score."""
        if score >= 85:
            return "excellent"
        elif score >= 70:
            return "good"
        elif score >= 55:
            return "fair"
        else:
            return "poor"

    def _assign_tiers(self, ranked: List[RankedOpportunity]):
        """Finalize tiers based on relative ranking."""
        if not ranked:
            return

        scores = [r.composite_score for r in ranked]
        max_score = max(scores)
        min_score = min(scores)
        range_score = max_score - min_score

        if range_score == 0:
            for r in ranked:
                r.tier = "good"
            return

        # Assign tiers based on percentile
        for r in ranked:
            percentile = (r.composite_score - min_score) / range_score
            if percentile >= 0.8:
                r.tier = "excellent"
            elif percentile >= 0.6:
                r.tier = "good"
            elif percentile >= 0.4:
                r.tier = "fair"
            else:
                r.tier = "poor"

    def _generate_action_items(
        self,
        match: JobMatch,
        concerns: List[str],
    ) -> List[str]:
        """Generate actionable items for the candidate."""
        actions = []

        # Skill-based actions
        if match.missing_skills:
            top_skills = match.missing_skills[:3]
            actions.append(f"Priority: Learn {', '.join(top_skills)}")

        if match.skill_match.get("missing_preferred"):
            actions.append(f"Bonus: Add {', '.join(match.skill_match['missing_preferred'][:2])}")

        # Experience actions
        if match.experience_match.get("status") == "below":
            gap = abs(match.experience_match.get("gap", 0))
            if gap <= 2:
                actions.append(f"Highlight transferable experience to bridge {gap} year gap")
            else:
                actions.append("Emphasize relevant projects and achievements to compensate for experience gap")

        # Location actions
        if match.location_match.get("status") == "candidate_wants_remote":
            actions.append("Mention remote work flexibility in cover letter")

        # Salary actions
        if match.salary_match.get("status") == "below_expectations":
            actions.append("Research market rate; be prepared to negotiate")

        # Application actions
        actions.append("Tailor resume to highlight matching skills")
        actions.append("Prepare specific examples for required skills in interview")

        return actions[:5]  # Limit to top 5

    def filter_by_tier(
        self,
        ranked: List[RankedOpportunity],
        min_tier: str = "fair",
    ) -> List[RankedOpportunity]:
        """Filter opportunities by minimum tier."""
        tier_order = {"poor": 0, "fair": 1, "good": 2, "excellent": 3}
        min_level = tier_order.get(min_tier, 1)
        return [r for r in ranked if tier_order.get(r.tier, 0) >= min_level]

    def get_top_opportunities(
        self,
        ranked: List[RankedOpportunity],
        limit: int = 10,
    ) -> List[RankedOpportunity]:
        """Get top N opportunities."""
        return ranked[:limit]

    def get_summary_stats(self, ranked: List[RankedOpportunity]) -> Dict[str, Any]:
        """Get summary statistics for ranked opportunities."""
        if not ranked:
            return {
                "total": 0,
                "by_tier": {},
                "avg_score": 0,
                "top_match": None,
            }

        by_tier = {}
        for r in ranked:
            by_tier[r.tier] = by_tier.get(r.tier, 0) + 1

        return {
            "total": len(ranked),
            "by_tier": by_tier,
            "avg_score": round(sum(r.composite_score for r in ranked) / len(ranked), 1),
            "top_match": {
                "title": ranked[0].job_match.job_title,
                "company": ranked[0].job_match.company,
                "score": ranked[0].composite_score,
                "tier": ranked[0].tier,
            } if ranked else None,
        }