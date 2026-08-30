from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum as PyEnum
import logging

from backend.research_engine.state.research_context import ResearchEvidence

logger = logging.getLogger(__name__)


class RankingStrategy(str, PyEnum):
    """Evidence ranking strategies."""
    RELEVANCE = "relevance"  # By relevance to claim
    CONFIDENCE = "confidence"  # By confidence score
    CREDIBILITY = "credibility"  # By source credibility
    RECENCY = "recency"  # By publication date
    COMPOSITE = "composite"  # Weighted combination
    EVIDENCE_TYPE = "evidence_type"  # Prioritize certain evidence types


EVIDENCE_TYPE_WEIGHTS = {
    "direct_quote": 1.0,
    "statistic": 0.95,
    "expert_opinion": 0.9,
    "case_study": 0.85,
    "survey_result": 0.85,
    "report": 0.8,
    "other": 0.7,
}


SOURCE_TYPE_WEIGHTS = {
    "academic": 1.0,
    "government": 0.95,
    "company": 0.85,
    "job_board": 0.85,
    "news": 0.8,
    "web": 0.75,
    "social": 0.6,
    "other": 0.7,
}


@dataclass
class RankedEvidence:
    """Evidence with ranking score."""
    evidence: "ResearchEvidence"
    score: float
    rank: int
    ranking_factors: Dict[str, float]


class EvidenceRanker:
    """Rank evidence by various criteria."""

    def __init__(
        self,
        strategy: RankingStrategy = RankingStrategy.COMPOSITE,
        custom_weights: Optional[Dict[str, float]] = None,
    ):
        self.strategy = strategy
        self.custom_weights = custom_weights or {}

        # Default weights for composite strategy
        self.weights = {
            "relevance": 0.30,
            "confidence": 0.25,
            "credibility": 0.20,
            "evidence_type": 0.15,
            "source_type": 0.10,
        }
        self.weights.update(self.custom_weights)

    def rank(
        self,
        evidence_list: List["ResearchEvidence"],
        claim_text: Optional[str] = None,
    ) -> List[RankedEvidence]:
        """Rank a list of evidence."""
        if not evidence_list:
            return []

        ranked = []

        for i, evidence in enumerate(evidence_list):
            score = self._calculate_score(evidence, claim_text)
            factors = self._get_ranking_factors(evidence)

            ranked.append(RankedEvidence(
                evidence=evidence,
                score=score,
                rank=0,  # Will be set after sorting
                ranking_factors=factors,
            ))

        # Sort by score descending
        ranked.sort(key=lambda x: x.score, reverse=True)

        # Assign ranks
        for i, item in enumerate(ranked):
            item.rank = i + 1

        return ranked

    def _calculate_score(self, evidence: "ResearchEvidence", claim_text: Optional[str] = None) -> float:
        """Calculate composite ranking score."""
        if self.strategy == RankingStrategy.RELEVANCE:
            return evidence.relevance_score
        elif self.strategy == RankingStrategy.CONFIDENCE:
            return evidence.confidence_score
        elif self.strategy == RankingStrategy.CREDIBILITY:
            return evidence.metadata.get("source_credibility", 0.5)
        elif self.strategy == RankingStrategy.EVIDENCE_TYPE:
            return EVIDENCE_TYPE_WEIGHTS.get(evidence.evidence_type, 0.7)
        elif self.strategy == RankingStrategy.RECENCY:
            # Would need publication date
            return 0.5

        # Composite strategy
        score = 0.0

        # Relevance weight
        score += evidence.relevance_score * self.weights.get("relevance", 0.30)

        # Confidence weight
        score += evidence.confidence_score * self.weights.get("confidence", 0.25)

        # Source credibility
        credibility = evidence.metadata.get("source_credibility", 0.5)
        score += credibility * self.weights.get("credibility", 0.20)

        # Evidence type weight
        type_weight = EVIDENCE_TYPE_WEIGHTS.get(evidence.evidence_type, 0.7)
        score += type_weight * self.weights.get("evidence_type", 0.15)

        # Source type weight
        source_type = evidence.metadata.get("source_type", "web")
        source_weight = SOURCE_TYPE_WEIGHTS.get(source_type, 0.7)
        score += source_weight * self.weights.get("source_type", 0.10)

        return min(score, 1.0)

    def _get_ranking_factors(self, evidence: "ResearchEvidence") -> Dict[str, float]:
        """Get individual ranking factors for transparency."""
        return {
            "relevance": evidence.relevance_score,
            "confidence": evidence.confidence_score,
            "credibility": evidence.metadata.get("source_credibility", 0.5),
            "evidence_type_weight": EVIDENCE_TYPE_WEIGHTS.get(evidence.evidence_type, 0.7),
            "source_type_weight": SOURCE_TYPE_WEIGHTS.get(evidence.metadata.get("source_type", "web"), 0.7),
        }

    def get_top_evidence(
        self,
        evidence_list: List["ResearchEvidence"],
        limit: int = 5,
        claim_text: Optional[str] = None,
    ) -> List["ResearchEvidence"]:
        """Get top N evidence items."""
        ranked = self.rank(evidence_list, claim_text)
        return [r.evidence for r in ranked[:limit]]

    def group_by_type(self, evidence_list: List["ResearchEvidence"]) -> Dict[str, List["ResearchEvidence"]]:
        """Group evidence by type."""
        groups = {}
        for evidence in evidence_list:
            etype = evidence.evidence_type
            if etype not in groups:
                groups[etype] = []
            groups[etype].append(evidence)
        return groups

    def get_evidence_summary(self, evidence_list: List["ResearchEvidence"]) -> Dict[str, Any]:
        """Get summary statistics for evidence."""
        if not evidence_list:
            return {
                "total": 0,
                "by_type": {},
                "avg_relevance": 0,
                "avg_confidence": 0,
                "top_types": [],
            }

        by_type = {}
        total_relevance = 0
        total_confidence = 0

        for e in evidence_list:
            etype = e.evidence_type
            by_type[etype] = by_type.get(etype, 0) + 1
            total_relevance += e.relevance_score
            total_confidence += e.confidence_score

        # Top types by count
        top_types = sorted(by_type.items(), key=lambda x: x[1], reverse=True)[:3]

        return {
            "total": len(evidence_list),
            "by_type": by_type,
            "avg_relevance": round(total_relevance / len(evidence_list), 3),
            "avg_confidence": round(total_confidence / len(evidence_list), 3),
            "top_types": [{"type": t, "count": c} for t, c in top_types],
        }