import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceBreakdown:
    """Detailed confidence breakdown."""
    source_quality: float      # Average source credibility
    evidence_strength: float   # Evidence quality and quantity
    claim_verification: float  # Verification results
    cross_validation: float    # Cross-source agreement
    recency: float             # Information recency
    coverage: float            # Topic coverage completeness
    consistency: float         # Internal consistency
    overall: float             # Weighted overall score


@dataclass
class ConfidenceScoreResult:
    """Result of confidence scoring."""
    research_id: int
    query: str
    breakdown: ConfidenceBreakdown
    confidence_level: str      # very_high, high, medium, low, very_low
    confidence_percentage: int # 0-100
    factors: List[Dict[str, Any]]  # Contributing factors
    warnings: List[str]        # Confidence-reducing factors
    scored_at: datetime = field(default_factory=datetime.utcnow)


class ConfidenceScorer:
    """Score overall research confidence with detailed breakdown."""

    def __init__(self):
        self.name = "confidence_scorer"

        # Weights for each dimension
        self.weights = {
            "source_quality": 0.20,
            "evidence_strength": 0.20,
            "claim_verification": 0.25,
            "cross_validation": 0.15,
            "recency": 0.10,
            "coverage": 0.05,
            "consistency": 0.05,
        }

        # Confidence level thresholds
        self.levels = {
            "very_high": 0.85,
            "high": 0.70,
            "medium": 0.50,
            "low": 0.30,
            "very_low": 0.0,
        }

    async def score_research(
        self,
        research_id: int,
        query: str,
        sources: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
        verification_results: List[Dict[str, Any]],
        analysis_result: Dict[str, Any],
        synthesis_result: Dict[str, Any],
        ranked_evidence: Optional[List[Dict[str, Any]]] = None,
    ) -> ConfidenceScoreResult:
        """Score overall research confidence."""
        logger.info(f"Scoring confidence for research #{research_id}")

        # Calculate each dimension
        source_quality = self._score_source_quality(sources)
        evidence_strength = self._score_evidence_strength(evidence, ranked_evidence)
        claim_verification = self._score_claim_verification(verification_results)
        cross_validation = self._score_cross_validation(verification_results, sources)
        recency = self._score_recency(sources)
        coverage = self._score_coverage(analysis_result, synthesis_result, query)
        consistency = self._score_consistency(verification_results, evidence)

        # Calculate weighted overall
        breakdown = ConfidenceBreakdown(
            source_quality=source_quality,
            evidence_strength=evidence_strength,
            claim_verification=claim_verification,
            cross_validation=cross_validation,
            recency=recency,
            coverage=coverage,
            consistency=consistency,
            overall=0.0,  # Will calculate below
        )

        breakdown.overall = self._calculate_overall(breakdown)

        # Determine level and percentage
        confidence_level = self._get_confidence_level(breakdown.overall)
        confidence_percentage = round(breakdown.overall * 100)

        # Identify factors and warnings
        factors = self._identify_factors(breakdown, sources, verification_results, evidence)
        warnings = self._identify_warnings(breakdown, sources, verification_results, evidence)

        return ConfidenceScoreResult(
            research_id=research_id,
            query=query,
            breakdown=breakdown,
            confidence_level=confidence_level,
            confidence_percentage=confidence_percentage,
            factors=factors,
            warnings=warnings,
        )

    def _score_source_quality(self, sources: List[Dict[str, Any]]) -> float:
        """Score based on source credibility and diversity."""
        if not sources:
            return 0.0

        # Average credibility
        credibilities = [s.get("credibility", 0.5) for s in sources]
        avg_cred = statistics.mean(credibilities)

        # Domain diversity
        domains = set(s.get("domain", "") for s in sources if s.get("domain"))
        domain_diversity = min(len(domains) / 10, 1.0)  # Max 10 domains

        # Source type diversity
        types = set(s.get("source_type", "web") for s in sources)
        type_diversity = min(len(types) / 5, 1.0)  # Max 5 types

        # Combine
        score = avg_cred * 0.6 + domain_diversity * 0.2 + type_diversity * 0.2
        return round(min(score, 1.0), 3)

    def _score_evidence_strength(
        self,
        evidence: List[Dict[str, Any]],
        ranked_evidence: Optional[List[Dict[str, Any]]],
    ) -> float:
        """Score based on evidence quality and quantity."""
        if not evidence:
            return 0.0

        # Quantity factor (more evidence = better, up to a point)
        count = len(evidence)
        quantity_factor = min(count / 20, 1.0)  # Saturates at 20 pieces

        # Quality factor from evidence confidence
        confidences = [e.get("confidence_score", 0.5) for e in evidence]
        avg_confidence = statistics.mean(confidences) if confidences else 0.5

        # Relevance factor
        relevances = [e.get("relevance_score", 0.5) for e in evidence]
        avg_relevance = statistics.mean(relevances) if relevances else 0.5

        # Evidence type diversity
        types = set(e.get("evidence_type", "other") for e in evidence)
        important_types = {"statistic", "expert_opinion", "direct_quote", "report"}
        type_coverage = len(types & important_types) / len(important_types)

        # If ranked evidence available, use ranking scores
        if ranked_evidence:
            ranked_scores = [e.get("final_score", 0.5) for e in ranked_evidence]
            if ranked_scores:
                avg_confidence = statistics.mean(ranked_scores)

        score = (
            quantity_factor * 0.2 +
            avg_confidence * 0.4 +
            avg_relevance * 0.2 +
            type_coverage * 0.2
        )
        return round(min(score, 1.0), 3)

    def _score_claim_verification(self, verification_results: List[Dict[str, Any]]) -> float:
        """Score based on claim verification results."""
        if not verification_results:
            return 0.3  # Neutral if no verification

        statuses = [v.get("status", "uncertain") for v in verification_results]
        confidences = [v.get("confidence", 0.5) for v in verification_results]

        # Count by status
        verified = sum(1 for s in statuses if s == "verified")
        likely = sum(1 for s in statuses if s == "likely")
        conflicting = sum(1 for s in statuses if s == "conflicting")
        uncertain = sum(1 for s in statuses if s == "uncertain")
        rejected = sum(1 for s in statuses if s == "rejected")
        total = len(statuses)

        # Weight by status
        status_score = (
            verified * 1.0 +
            likely * 0.7 +
            uncertain * 0.3 +
            conflicting * 0.2 +
            rejected * 0.0
        ) / total

        # Average confidence of verified/likely claims
        high_conf_claims = [
            c for s, c in zip(statuses, confidences)
            if s in ["verified", "likely"]
        ]
        avg_high_conf = statistics.mean(high_conf_claims) if high_conf_claims else 0.5

        # Penalty for conflicting claims
        conflict_penalty = conflicting / total * 0.3

        score = status_score * 0.7 + avg_high_conf * 0.3 - conflict_penalty
        return round(max(0.0, min(score, 1.0)), 3)

    def _score_cross_validation(
        self,
        verification_results: List[Dict[str, Any]],
        sources: List[Dict[str, Any]],
    ) -> float:
        """Score based on cross-source validation."""
        if not verification_results or not sources:
            return 0.3

        # Check how many claims have multiple supporting sources
        multi_source_claims = 0
        for v in verification_results:
            supporting = v.get("supporting_sources", 0)
            if supporting >= 2:
                multi_source_claims += 1
            elif supporting == 1:
                multi_source_claims += 0.5

        multi_source_ratio = multi_source_claims / len(verification_results)

        # Source agreement: check if different source types agree
        source_types = set(s.get("source_type", "web") for s in sources)
        type_agreement = min(len(source_types) / 3, 1.0)  # Better with 3+ types

        score = multi_source_ratio * 0.7 + type_agreement * 0.3
        return round(min(score, 1.0), 3)

    def _score_recency(self, sources: List[Dict[str, Any]]) -> float:
        """Score based on information recency."""
        if not sources:
            return 0.5

        recent_count = 0
        for s in sources:
            pub_date = s.get("published_date")
            if pub_date:
                try:
                    from datetime import datetime, timezone
                    pub_dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                    if pub_dt.tzinfo is None:
                        pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                    now = datetime.now(timezone.utc)
                    days_old = (now - pub_dt).days
                    if days_old < 90:
                        recent_count += 1
                except Exception:
                    pass

        if not sources:
            return 0.5

        recent_ratio = recent_count / len(sources)

        # Weight: more recent = higher score
        if recent_ratio > 0.7:
            return 1.0
        elif recent_ratio > 0.5:
            return 0.8
        elif recent_ratio > 0.3:
            return 0.6
        elif recent_ratio > 0.1:
            return 0.4
        else:
            return 0.2

    def _score_coverage(
        self,
        analysis_result: Dict[str, Any],
        synthesis_result: Dict[str, Any],
        query: str,
    ) -> float:
        """Score based on topic coverage completeness."""
        score = 0.5  # Base

        # Key findings count
        key_findings = synthesis_result.get("key_findings", [])
        if key_findings:
            score += min(len(key_findings) / 10, 0.2)

        # Detailed findings
        detailed = synthesis_result.get("detailed_findings", [])
        if detailed:
            score += min(len(detailed) / 15, 0.15)

        # Recommendations
        recommendations = synthesis_result.get("recommendations", [])
        if recommendations:
            score += min(len(recommendations) / 10, 0.1)

        # Insights from analysis
        insights = analysis_result.get("insights", [])
        if insights:
            score += min(len(insights) / 5, 0.15)

        # Gaps (negative factor)
        gaps = analysis_result.get("gaps", [])
        if gaps:
            score -= min(len(gaps) / 10, 0.2)

        return round(max(0.0, min(score, 1.0)), 3)

    def _score_consistency(
        self,
        verification_results: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
    ) -> float:
        """Score internal consistency."""
        if not verification_results:
            return 0.5

        # Check for contradictory claims
        statuses = [v.get("status", "uncertain") for v in verification_results]
        conflicting = sum(1 for s in statuses if s == "conflicting")

        if not verification_results:
            return 0.5

        conflict_ratio = conflicting / len(verification_results)

        # Evidence consistency: check if evidence for same claim agrees
        evidence_consistency = 0.8  # Default
        if evidence:
            # Group by claim
            by_claim = defaultdict(list)
            for e in evidence:
                by_claim[e.get("claim_id", "unknown")].append(e.get("supports_claim", True))

            # Check agreement within each claim
            agreement_scores = []
            for claim_id, supports in by_claim.items():
                if len(supports) > 1:
                    agreement = sum(supports) / len(supports)
                    agreement_scores.append(max(agreement, 1 - agreement))
                else:
                    agreement_scores.append(0.5)

            if agreement_scores:
                evidence_consistency = statistics.mean(agreement_scores)

        score = (1 - conflict_ratio) * 0.6 + evidence_consistency * 0.4
        return round(max(0.0, min(score, 1.0)), 3)

    def _calculate_overall(self, breakdown: ConfidenceBreakdown) -> float:
        """Calculate weighted overall confidence."""
        overall = (
            breakdown.source_quality * self.weights["source_quality"] +
            breakdown.evidence_strength * self.weights["evidence_strength"] +
            breakdown.claim_verification * self.weights["claim_verification"] +
            breakdown.cross_validation * self.weights["cross_validation"] +
            breakdown.recency * self.weights["recency"] +
            breakdown.coverage * self.weights["coverage"] +
            breakdown.consistency * self.weights["consistency"]
        )
        return round(min(overall, 1.0), 3)

    def _get_confidence_level(self, score: float) -> str:
        """Get confidence level label."""
        for level, threshold in sorted(self.levels.items(), key=lambda x: x[1], reverse=True):
            if score >= threshold:
                return level
        return "very_low"

    def _identify_factors(
        self,
        breakdown: ConfidenceBreakdown,
        sources: List[Dict[str, Any]],
        verification_results: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Identify positive contributing factors."""
        factors = []

        if breakdown.source_quality > 0.7:
            factors.append({
                "factor": "high_source_quality",
                "description": f"Sources have high average credibility ({breakdown.source_quality:.0%})",
                "impact": "positive",
                "score": breakdown.source_quality,
            })

        if breakdown.evidence_strength > 0.7:
            factors.append({
                "factor": "strong_evidence",
                "description": f"Strong evidence base with {len(evidence)} pieces",
                "impact": "positive",
                "score": breakdown.evidence_strength,
            })

        if breakdown.claim_verification > 0.7:
            verified = sum(1 for v in verification_results if v.get("status") == "verified")
            factors.append({
                "factor": "verified_claims",
                "description": f"{verified} claims verified with high confidence",
                "impact": "positive",
                "score": breakdown.claim_verification,
            })

        if breakdown.cross_validation > 0.7:
            factors.append({
                "factor": "cross_validated",
                "description": "Claims supported by multiple independent sources",
                "impact": "positive",
                "score": breakdown.cross_validation,
            })

        if breakdown.recency > 0.7:
            factors.append({
                "factor": "current_information",
                "description": "Majority of sources are recent (< 90 days)",
                "impact": "positive",
                "score": breakdown.recency,
            })

        return factors

    def _identify_warnings(
        self,
        breakdown: ConfidenceBreakdown,
        sources: List[Dict[str, Any]],
        verification_results: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
    ) -> List[str]:
        """Identify confidence-reducing warnings."""
        warnings = []

        if breakdown.source_quality < 0.5:
            warnings.append("Low average source credibility - consider adding more authoritative sources")

        if breakdown.evidence_strength < 0.4:
            warnings.append("Insufficient evidence quantity or quality for strong conclusions")

        if breakdown.claim_verification < 0.5:
            warnings.append("Many claims could not be verified - findings may be speculative")

        if breakdown.cross_validation < 0.4:
            warnings.append("Limited cross-source validation - claims rely on single sources")

        if breakdown.recency < 0.4:
            warnings.append("Information may be outdated - most sources older than 90 days")

        if breakdown.coverage < 0.4:
            warnings.append("Incomplete topic coverage - key aspects may be missing")

        if breakdown.consistency < 0.5:
            conflicting = sum(1 for v in verification_results if v.get("status") == "conflicting")
            if conflicting > 0:
                warnings.append(f"{conflicting} claims have conflicting evidence")

        # Source diversity warnings
        if sources:
            domains = set(s.get("domain", "") for s in sources if s.get("domain"))
            if len(domains) < 3:
                warnings.append("Low source domain diversity - potential bias")

            types = set(s.get("source_type", "web") for s in sources)
            if len(types) < 2:
                warnings.append("Single source type - limited perspective")

        return warnings

    async def score_claim_confidence(
        self,
        claim: str,
        claim_evidence: List[Dict[str, Any]],
        verification_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Score confidence for a single claim."""
        if not claim_evidence:
            return {
                "claim": claim,
                "confidence": 0.1,
                "level": "very_low",
                "reason": "No evidence",
            }

        # Use verification result if available
        if verification_result:
            return {
                "claim": claim,
                "confidence": verification_result.get("confidence", 0.5),
                "level": self._get_confidence_level(verification_result.get("confidence", 0.5)),
                "status": verification_result.get("status", "uncertain"),
                "supporting_sources": verification_result.get("supporting_sources", 0),
                "conflicting_sources": verification_result.get("conflicting_sources", 0),
            }

        # Calculate from evidence
        avg_conf = statistics.mean([e.get("confidence_score", 0.5) for e in claim_evidence])
        avg_rel = statistics.mean([e.get("relevance_score", 0.5) for e in claim_evidence])
        supporting = sum(1 for e in claim_evidence if e.get("supports_claim", True))

        confidence = avg_conf * 0.5 + avg_rel * 0.3 + min(supporting / 3, 1.0) * 0.2

        return {
            "claim": claim,
            "confidence": round(confidence, 3),
            "level": self._get_confidence_level(confidence),
            "supporting_evidence": supporting,
            "total_evidence": len(claim_evidence),
        }