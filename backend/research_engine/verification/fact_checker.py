from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum as PyEnum
import logging
import re

from backend.research_engine.state.research_context import ResearchClaim, ResearchEvidence

logger = logging.getLogger(__name__)


class ClaimStatus(str, PyEnum):
    """Status of a claim after verification."""
    VERIFIED = "verified"
    LIKELY = "likely"
    UNCERTAIN = "uncertain"
    CONFLICTING = "conflicting"
    REJECTED = "rejected"


class VerificationMethod(str, PyEnum):
    """Methods used for verification."""
    SOURCE_AGREEMENT = "source_agreement"
    CREDIBILITY_WEIGHTED = "credibility_weighted"
    EVIDENCE_QUALITY = "evidence_quality"
    CROSS_REFERENCE = "cross_reference"
    EXTERNAL_API = "external_api"


@dataclass
class VerificationResult:
    """Result of fact-checking a claim."""
    claim_id: str
    claim_text: str
    status: ClaimStatus
    confidence: float
    method: VerificationMethod
    supporting_evidence_count: int
    conflicting_evidence_count: int
    total_evidence_count: int
    source_agreement_score: float
    credibility_weighted_score: float
    details: Dict[str, Any]
    verified_at: datetime = field(default_factory=datetime.utcnow)


class FactChecker:
    """Verify claims using multiple verification methods."""

    def __init__(self):
        self.min_sources_for_verified = 2
        self.min_agreement_for_verified = 0.7
        self.confidence_threshold_verified = 0.75
        self.confidence_threshold_likely = 0.5
        self.confidence_threshold_rejected = 0.3

    def verify_claim(
        self,
        claim: "ResearchClaim",
        evidence: List["ResearchEvidence"],
    ) -> VerificationResult:
        """Verify a single claim using multiple methods."""
        logger.info(f"Verifying claim: {claim.text[:50]}...")

        # Method 1: Source Agreement
        agreement_result = self._check_source_agreement(claim, evidence)

        # Method 2: Credibility Weighted
        credibility_result = self._check_credibility_weighted(claim, evidence)

        # Method 3: Evidence Quality
        quality_result = self._check_evidence_quality(claim, evidence)

        # Method 4: Cross Reference (if external sources available)
        cross_ref_result = self._check_cross_reference(claim, evidence)

        # Combine results
        final_status, final_confidence = self._combine_results(
            agreement_result, credibility_result, quality_result, cross_ref_result
        )

        return VerificationResult(
            claim_id=claim.id,
            claim_text=claim.text,
            status=final_status,
            confidence=final_confidence,
            method=VerificationMethod.CREDIBILITY_WEIGHTED,
            supporting_evidence_count=agreement_result["supporting"],
            conflicting_evidence_count=agreement_result["conflicting"],
            total_evidence_count=len(evidence),
            source_agreement_score=agreement_result["score"],
            credibility_weighted_score=credibility_result["score"],
            details={
                "source_agreement": agreement_result,
                "credibility_weighted": credibility_result,
                "evidence_quality": quality_result,
                "cross_reference": cross_ref_result,
            },
        )

    def _check_source_agreement(
        self,
        claim: "ResearchClaim",
        evidence: List["ResearchEvidence"],
    ) -> Dict[str, Any]:
        """Check agreement among sources."""
        if not evidence:
            return {"score": 0.0, "supporting": 0, "conflicting": 0, "details": "No evidence"}

        supporting = sum(1 for e in evidence if e.supports_claim)
        conflicting = sum(1 for e in evidence if not e.supports_claim)

        agreement_score = supporting / len(evidence) if evidence else 0

        return {
            "score": agreement_score,
            "supporting": supporting,
            "conflicting": conflicting,
            "details": f"{supporting} supporting, {conflicting} conflicting out of {len(evidence)}",
        }

    def _check_credibility_weighted(
        self,
        claim: "ResearchClaim",
        evidence: List["ResearchEvidence"],
    ) -> Dict[str, Any]:
        """Weight evidence by source credibility."""
        if not evidence:
            return {"score": 0.0, "weighted_support": 0.0, "details": "No evidence"}

        total_credibility = sum(e.metadata.get("source_credibility", 0.5) for e in evidence)
        if total_credibility == 0:
            return {"score": 0.0, "weighted_support": 0.0, "details": "Zero credibility"}

        weighted_support = sum(
            e.metadata.get("source_credibility", 0.5) for e in evidence if e.supports_claim
        )
        weighted_conflict = sum(
            e.metadata.get("source_credibility", 0.5) for e in evidence if not e.supports_claim
        )

        score = weighted_support / total_credibility if total_credibility > 0 else 0

        return {
            "score": score,
            "weighted_support": weighted_support,
            "weighted_conflict": weighted_conflict,
            "total_credibility": total_credibility,
            "details": f"Weighted support: {weighted_support:.2f}, conflict: {weighted_conflict:.2f}",
        }

    def _check_evidence_quality(
        self,
        claim: "ResearchClaim",
        evidence: List["ResearchEvidence"],
    ) -> Dict[str, Any]:
        """Assess quality of evidence."""
        if not evidence:
            return {"score": 0.0, "details": "No evidence"}

        # Average relevance and confidence
        avg_relevance = sum(e.relevance_score for e in evidence) / len(evidence)
        avg_confidence = sum(e.confidence_score for e in evidence) / len(evidence)

        # Evidence type diversity
        types = set(e.evidence_type for e in evidence)
        type_diversity = len(types) / 7  # 7 possible types

        # High-quality evidence types present
        high_quality_types = {"statistic", "expert_opinion", "direct_quote", "report"}
        hq_present = len(set(e.evidence_type for e in evidence) & high_quality_types)

        score = (
            avg_relevance * 0.3 +
            avg_confidence * 0.3 +
            type_diversity * 0.2 +
            min(hq_present / 3, 1.0) * 0.2
        )

        return {
            "score": score,
            "avg_relevance": avg_relevance,
            "avg_confidence": avg_confidence,
            "type_diversity": type_diversity,
            "high_quality_types_present": hq_present,
            "details": f"Avg relevance: {avg_relevance:.2f}, confidence: {avg_confidence:.2f}",
        }

    def _check_cross_reference(
        self,
        claim: "ResearchClaim",
        evidence: List["ResearchEvidence"],
    ) -> Dict[str, Any]:
        """Cross-reference with external knowledge (placeholder)."""
        # In production, this would query fact-checking APIs
        # For now, return neutral result
        return {
            "score": 0.5,
            "verified_externally": False,
            "details": "External verification not implemented",
        }

    def _combine_results(
        self,
        agreement: Dict[str, Any],
        credibility: Dict[str, Any],
        quality: Dict[str, Any],
        cross_ref: Dict[str, Any],
    ) -> tuple:
        """Combine verification results into final status and confidence."""
        # Weighted combination
        weights = {
            "agreement": 0.30,
            "credibility": 0.35,
            "quality": 0.25,
            "cross_ref": 0.10,
        }

        combined_score = (
            agreement["score"] * weights["agreement"] +
            credibility["score"] * weights["credibility"] +
            quality["score"] * weights["quality"] +
            cross_ref["score"] * weights["cross_ref"]
        )

        # Determine status based on score and supporting evidence
        supporting = agreement.get("supporting", 0)
        conflicting = agreement.get("conflicting", 0)

        if combined_score >= self.confidence_threshold_verified and supporting >= self.min_sources_for_verified:
            if agreement["score"] >= self.min_agreement_for_verified:
                return ClaimStatus.VERIFIED, combined_score

        if combined_score >= self.confidence_threshold_likely and supporting >= 1:
            return ClaimStatus.LIKELY, combined_score

        if combined_score <= self.confidence_threshold_rejected or conflicting > supporting:
            return ClaimStatus.REJECTED, combined_score

        if conflicting > 0 and supporting > 0:
            return ClaimStatus.CONFLICTING, combined_score

        return ClaimStatus.UNCERTAIN, combined_score

    def verify_batch(
        self,
        claims: List["ResearchClaim"],
        evidence_map: Dict[str, List["ResearchEvidence"]],
    ) -> List[VerificationResult]:
        """Verify multiple claims."""
        results = []
        for claim in claims:
            evidence = evidence_map.get(claim.id, [])
            result = self.verify_claim(claim, evidence)
            results.append(result)
        return results