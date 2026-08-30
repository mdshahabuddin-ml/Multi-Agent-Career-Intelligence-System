import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """Result of research analysis."""
    research_id: int
    patterns: List[Dict[str, Any]]
    insights: List[Dict[str, Any]]
    trends: List[Dict[str, Any]]
    comparisons: List[Dict[str, Any]]
    gaps: List[str]
    confidence: float
    analyzed_at: datetime = field(default_factory=datetime.utcnow)


class AnalysisAgent:
    """Analyze research findings for patterns, trends, and insights."""

    def __init__(self):
        self.name = "analysis_agent"

    async def analyze(
        self,
        research_id: int,
        claims: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
        verification_results: List[Dict[str, Any]],
        sources: List[Dict[str, Any]],
    ) -> AnalysisResult:
        """Analyze all research findings."""
        logger.info(f"Analyzing research #{research_id}")

        # Extract verified claims
        verified_claims = [
            v for v in verification_results
            if v.get("status") in ["verified", "likely"]
        ]

        # Pattern detection
        patterns = self._detect_patterns(verified_claims, evidence)

        # Insight generation
        insights = self._generate_insights(verified_claims, evidence, sources)

        # Trend analysis
        trends = self._analyze_trends(verified_claims, sources)

        # Comparisons
        comparisons = self._compare_sources(sources)

        # Identify gaps
        gaps = self._identify_gaps(verified_claims, evidence)

        # Overall confidence
        confidence = self._calculate_confidence(verification_results)

        return AnalysisResult(
            research_id=research_id,
            patterns=patterns,
            insights=insights,
            trends=trends,
            comparisons=comparisons,
            gaps=gaps,
            confidence=confidence,
        )

    def _detect_patterns(
        self,
        claims: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Detect patterns in claims and evidence."""
        patterns = []

        # Claim frequency patterns
        claim_texts = [c.get("claim_text", "") for c in claims]
        word_freq = Counter()
        for text in claim_texts:
            words = text.lower().split()
            word_freq.update([w for w in words if len(w) > 4])

        common_terms = word_freq.most_common(10)
        if common_terms:
            patterns.append({
                "type": "term_frequency",
                "description": "Most common terms in verified claims",
                "data": [{"term": t, "count": c} for t, c in common_terms],
            })

        # Evidence type patterns
        evidence_types = [e.get("evidence_type", "other") for e in evidence]
        type_counts = Counter(evidence_types)
        if type_counts:
            patterns.append({
                "type": "evidence_distribution",
                "description": "Distribution of evidence types",
                "data": [{"type": t, "count": c} for t, c in type_counts.items()],
            })

        # Source type patterns
        source_types = [e.get("source_type", "web") for e in evidence]
        source_counts = Counter(source_types)
        if source_counts:
            patterns.append({
                "type": "source_distribution",
                "description": "Distribution of source types",
                "data": [{"source": s, "count": c} for s, c in source_counts.items()],
            })

        return patterns

    def _generate_insights(
        self,
        claims: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
        sources: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate actionable insights."""
        insights = []

        # Insight 1: Claim coverage
        if claims:
            high_conf_claims = [c for c in claims if c.get("confidence", 0) > 0.7]
            insights.append({
                "type": "coverage",
                "title": "High Confidence Findings",
                "description": f"{len(high_conf_claims)} out of {len(claims)} claims have high confidence (>70%)",
                "actionable": True,
                "priority": "high" if len(high_conf_claims) > len(claims) * 0.5 else "medium",
            })

        # Insight 2: Evidence quality
        if evidence:
            high_qual = [e for e in evidence if e.get("confidence_score", 0) > 0.8]
            insights.append({
                "type": "evidence_quality",
                "title": "Evidence Quality",
                "description": f"{len(high_qual)} out of {len(evidence)} pieces of evidence have high confidence",
                "actionable": True,
                "priority": "high" if len(high_qual) < len(evidence) * 0.3 else "medium",
            })

        # Insight 3: Source diversity
        if sources:
            source_types = set(s.get("source_type", "web") for s in sources)
            insights.append({
                "type": "source_diversity",
                "title": "Source Diversity",
                "description": f"Research draws from {len(source_types)} source types: {', '.join(source_types)}",
                "actionable": len(source_types) < 3,
                "priority": "medium" if len(source_types) < 3 else "low",
            })

        # Insight 4: Recency
        recent_sources = 0
        for s in sources:
            pub_date = s.get("published_date")
            if pub_date:
                try:
                    from datetime import datetime
                    pub_dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                    if (datetime.utcnow() - pub_dt.replace(tzinfo=None)).days < 90:
                        recent_sources += 1
                except Exception:
                    pass

        if sources:
            insights.append({
                "type": "recency",
                "title": "Information Recency",
                "description": f"{recent_sources} out of {len(sources)} sources are from the last 90 days",
                "actionable": recent_sources < len(sources) * 0.3,
                "priority": "high" if recent_sources < len(sources) * 0.3 else "low",
            })

        return insights

    def _analyze_trends(
        self,
        claims: List[Dict[str, Any]],
        sources: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Analyze trends over time."""
        trends = []

        # Group sources by time period
        time_buckets = defaultdict(list)
        for s in sources:
            pub_date = s.get("published_date")
            if pub_date:
                try:
                    from datetime import datetime
                    pub_dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                    month_key = pub_dt.strftime("%Y-%m")
                    time_buckets[month_key].append(s)
                except Exception:
                    pass

        # Trend: source volume over time
        if len(time_buckets) > 1:
            sorted_months = sorted(time_buckets.keys())
            trend_data = [{"period": m, "source_count": len(time_buckets[m])} for m in sorted_months]

            trends.append({
                "type": "temporal_volume",
                "description": "Research activity over time",
                "data": trend_data,
            })

        return trends

    def _compare_sources(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Compare sources for agreement/conflict."""
        comparisons = []

        # Group by source type
        by_type = defaultdict(list)
        for s in sources:
            by_type[s.get("source_type", "web")].append(s)

        for source_type, srcs in by_type.items():
            if len(srcs) > 1:
                avg_cred = sum(s.get("credibility", 0) for s in srcs) / len(srcs)
                comparisons.append({
                    "type": "source_type_consistency",
                    "source_type": source_type,
                    "source_count": len(srcs),
                    "avg_credibility": round(avg_cred, 2),
                    "consistency": "high" if avg_cred > 0.7 else "medium" if avg_cred > 0.5 else "low",
                })

        return comparisons

    def _identify_gaps(
        self,
        claims: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
    ) -> List[str]:
        """Identify research gaps."""
        gaps = []

        # Claims with low evidence
        low_evidence_claims = [c for c in claims if c.get("supporting_sources", 0) < 2]
        if low_evidence_claims:
            gaps.append(f"{len(low_evidence_claims)} claims have fewer than 2 supporting sources")

        # Missing evidence types
        evidence_types = set(e.get("evidence_type", "other") for e in evidence)
        important_types = {"statistic", "expert_opinion", "case_study"}
        missing_types = important_types - evidence_types
        if missing_types:
            gaps.append(f"Missing evidence types: {', '.join(missing_types)}")

        # Conflicting claims
        conflicting = [c for c in claims if c.get("status") == "conflicting"]
        if conflicting:
            gaps.append(f"{len(conflicting)} claims have conflicting evidence")

        return gaps

    def _calculate_confidence(self, verification_results: List[Dict[str, Any]]) -> float:
        """Calculate overall research confidence."""
        if not verification_results:
            return 0.0

        verified = sum(1 for v in verification_results if v.get("status") == "verified")
        likely = sum(1 for v in verification_results if v.get("status") == "likely")
        total = len(verification_results)

        confidence = (verified * 1.0 + likely * 0.7) / total
        return round(confidence, 2)