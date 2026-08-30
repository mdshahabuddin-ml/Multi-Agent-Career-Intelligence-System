from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum as PyEnum
import logging
import math

from backend.research_engine.state.research_context import ResearchClaim, ResearchEvidence, ResearchSourceType

logger = logging.getLogger(__name__)


class ScoringMethod(str, PyEnum):
    """Confidence scoring methods."""
    BAYESIAN = "bayesian"
    WEIGHTED_AVERAGE = "weighted_average"
    Dempster_SHAfer = "dempster_shafer"
    ENSEMBLE = "ensemble"


@dataclass
class ConfidenceFactors:
    """Factors contributing to confidence score."""
    source_credibility: float = 0.0
    evidence_relevance: float = 0.0
    evidence_quality: float = 0.0
    source_agreement: float = 0.0
    evidence_diversity: float = 0.0
    recency: float = 0.0
    cross_verification: float = 0.0
    claim_specificity: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "source_credibility": self.source_credibility,
            "evidence_relevance": self.evidence_relevance,
            "evidence_quality": self.evidence_quality,
            "source_agreement": self.source_agreement,
            "evidence_diversity": self.evidence_diversity,
            "recency": self.recency,
            "cross_verification": self.cross_verification,
            "claim_specificity": self.claim_specificity,
        }


@dataclass
class ConfidenceScore:
    """Confidence score with breakdown."""
    claim_id: str
    overall_confidence: float
    factors: ConfidenceFactors
    method: ScoringMethod
    calibrated: bool = False
    calibration_details: Optional[Dict[str, Any]] = None
    scored_at: datetime = field(default_factory=datetime.utcnow)


class ConfidenceScorer:
    """Calculate confidence scores for claims."""

    def __init__(
        self,
        method: ScoringMethod = ScoringMethod.ENSEMBLE,
        calibrate: bool = True,
    ):
        self.method = method
        self.calibrate = calibrate

        # Default weights for weighted average
        self.weights = {
            "source_credibility": 0.20,
            "evidence_relevance": 0.20,
            "evidence_quality": 0.15,
            "source_agreement": 0.20,
            "evidence_diversity": 0.10,
            "recency": 0.05,
            "cross_verification": 0.05,
            "claim_specificity": 0.05,
        }

    def score_claim(
        self,
        claim: "ResearchClaim",
        evidence: List["ResearchEvidence"],
        sources: Optional[List["SourceMetadata"]] = None,
    ) -> ConfidenceScore:
        """Calculate confidence score for a claim."""
        factors = self._extract_factors(claim, evidence, sources)

        if self.method == ScoringMethod.BAYESIAN:
            confidence = self._bayesian_score(factors, evidence)
        elif self.method == ScoringMethod.WEIGHTED_AVERAGE:
            confidence = self._weighted_average(factors)
        elif self.method == ScoringMethod.Dempster_SHAfer:
            confidence = self._dempster_shafer(factors, evidence)
        else:  # ENSEMBLE
            confidence = self._ensemble_score(factors, evidence)

        # Calibrate if enabled
        if self.calibrate:
            confidence = self._calibrate(confidence, factors, evidence)

        return ConfidenceScore(
            claim_id=claim.id,
            overall_confidence=round(confidence, 3),
            factors=factors,
            method=self.method,
            calibrated=self.calibrate,
        )

    def _extract_factors(
        self,
        claim: "ResearchClaim",
        evidence: List["ResearchEvidence"],
        sources: Optional[List["SourceMetadata"]] = None,
    ) -> ConfidenceFactors:
        """Extract confidence factors from claim and evidence."""
        factors = ConfidenceFactors()

        if not evidence:
            return factors

        # Source credibility
        credibilities = [e.metadata.get("source_credibility", 0.5) for e in evidence]
        factors.source_credibility = sum(credibilities) / len(credibilities)

        # Evidence relevance
        relevances = [e.relevance_score for e in evidence]
        factors.evidence_relevance = sum(relevances) / len(relevances)

        # Evidence quality (confidence scores)
        qualities = [e.confidence_score for e in evidence]
        factors.evidence_quality = sum(qualities) / len(qualities)

        # Source agreement
        supporting = sum(1 for e in evidence if e.supports_claim)
        total = len(evidence)
        factors.source_agreement = supporting / total if total > 0 else 0

        # Evidence diversity
        types = set(e.evidence_type for e in evidence)
        source_types = set(e.metadata.get("source_type", "web") for e in evidence)
        factors.evidence_diversity = (len(types) + len(source_types)) / 14  # 7 types + 7 source types

        # Recency
        if sources:
            recency_scores = []
            for s in sources:
                if s.published_date:
                    try:
                        from datetime import datetime, timezone
                        pub_date = s.published_date
                        if pub_date.tzinfo is None:
                            pub_date = pub_date.replace(tzinfo=timezone.utc)
                        days_old = (datetime.now(timezone.utc) - pub_date).days
                        if days_old < 30:
                            recency_scores.append(1.0)
                        elif days_old < 90:
                            recency_scores.append(0.8)
                        elif days_old < 365:
                            recency_scores.append(0.5)
                        else:
                            recency_scores.append(0.2)
                    except Exception:
                        recency_scores.append(0.5)
            factors.recency = sum(recency_scores) / len(recency_scores) if recency_scores else 0.5
        else:
            factors.recency = 0.5

        # Cross verification (placeholder)
        factors.cross_verification = 0.5

        # Claim specificity
        factors.claim_specificity = self._calculate_claim_specificity(claim.text)

        return factors

    def _calculate_claim_specificity(self, claim_text: str) -> float:
        """Calculate how specific vs vague a claim is."""
        # Vague indicators
        vague_words = {"many", "some", "several", "various", "often", "usually", "generally", "typically"}
        # Specific indicators
        specific_words = {"%", "percent", "exactly", "precisely", "specifically", "detailed", "exact"}

        text_lower = claim_text.lower()
        words = set(text_lower.split())

        vague_count = len(vague_words & words)
        specific_count = len(specific_words & words)

        # Check for numbers
        has_numbers = bool(re.search(r'\d+', claim_text))

        if has_numbers and specific_count > 0:
            return 0.9
        elif has_numbers:
            return 0.7
        elif specific_count > vague_count:
            return 0.6
        elif vague_count > 0:
            return 0.3
        return 0.5

    def _bayesian_score(self, factors: ConfidenceFactors, evidence: List["ResearchEvidence"]) -> float:
        """Bayesian-inspired confidence scoring."""
        # Prior probability
        prior = 0.5

        # Likelihood ratios from each factor
        likelihoods = [
            factors.source_credibility,
            factors.evidence_relevance,
            factors.evidence_quality,
            factors.source_agreement,
            factors.evidence_diversity,
            factors.recency,
            factors.cross_verification,
            factors.claim_specificity,
        ]

        # Update posterior (simplified)
        posterior = prior
        for likelihood in likelihoods:
            # Convert to likelihood ratio
            lr = likelihood / (1 - likelihood) if likelihood < 1 else 10
            posterior = (posterior * lr) / (posterior * lr + (1 - posterior))

        return posterior

    def _weighted_average(self, factors: ConfidenceFactors) -> float:
        """Weighted average of factors."""
        score = 0.0
        for factor, weight in self.weights.items():
            value = getattr(factors, factor, 0.5)
            score += value * weight
        return min(score, 1.0)

    def _dempster_shafer(self, factors: ConfidenceFactors, evidence: List["ResearchEvidence"]) -> float:
        """Dempster-Shafer theory based scoring (simplified)."""
        # Mass functions for each piece of evidence
        masses = []
        for e in evidence:
            # Support mass
            support = e.confidence_score * e.relevance_score
            # Conflict mass (if contradicts)
            conflict = 0 if e.supports_claim else support * 0.5
            # Uncertainty mass
            uncertainty = 1 - support - conflict

            masses.append({"support": support, "conflict": conflict, "uncertainty": uncertainty})

        # Combine using Dempster's rule (simplified)
        if not masses:
            return 0.5

        combined_support = 1.0
        combined_conflict = 1.0
        for m in masses:
            combined_support *= m["support"]
            combined_conflict *= m["conflict"]

        # Normalize
        total = combined_support + combined_conflict
        if total == 0:
            return 0.5

        return combined_support / total

    def _ensemble_score(self, factors: ConfidenceFactors, evidence: List["ResearchEvidence"]) -> float:
        """Ensemble of multiple scoring methods."""
        bayesian = self._bayesian_score(factors, evidence)
        weighted = self._weighted_average(factors)
        ds = self._dempster_shafer(factors, evidence)

        # Weighted ensemble
        return (bayesian * 0.4 + weighted * 0.4 + ds * 0.2)

    def _calibrate(self, confidence: float, factors: ConfidenceFactors, evidence: List["ResearchEvidence"]) -> float:
        """Calibrate confidence score based on empirical data."""
        # Simple calibration: adjust for overconfidence
        # In production, this would use a calibration model trained on historical data

        # Penalize low diversity
        if factors.evidence_diversity < 0.3:
            confidence *= 0.9

        # Penalize low agreement with many sources
        if len(evidence) > 5 and factors.source_agreement < 0.5:
            confidence *= 0.85

        # Boost for high specificity with numbers
        if factors.claim_specificity > 0.8 and factors.evidence_relevance > 0.7:
            confidence = min(confidence * 1.05, 1.0)

        # Ensure bounds
        return max(0.0, min(1.0, confidence))

    def score_batch(
        self,
        claims: List["ResearchClaim"],
        evidence_map: Dict[str, List["ResearchEvidence"]],
        sources_map: Optional[Dict[int, List["SourceMetadata"]]] = None,
    ) -> List[ConfidenceScore]:
        """Score multiple claims."""
        results = []
        for claim in claims:
            evidence = evidence_map.get(claim.id, [])
            sources = sources_map.get(claim.id, None) if sources_map else None
            score = self.score_claim(claim, evidence, sources)
            results.append(score)
        return results

    def get_confidence_interval(
        self,
        score: ConfidenceScore,
        confidence_level: float = 0.95,
    ) -> tuple:
        """Get confidence interval for a score (bootstrap approximation)."""
        # Simplified: use standard error approximation
        n = max(1, len(score.factors.__dict__))  # Number of factors
        se = math.sqrt(score.overall_confidence * (1 - score.overall_confidence) / n)

        z = 1.96 if confidence_level == 0.95 else 1.645
        margin = z * se

        return (
            max(0, score.overall_confidence - margin),
            min(1, score.overall_confidence + margin),
        )


import math
import re