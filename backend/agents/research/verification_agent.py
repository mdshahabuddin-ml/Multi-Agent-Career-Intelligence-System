import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    """Result of claim verification."""
    claim_id: str
    claim_text: str
    status: str  # verified, likely, uncertain, conflicting, rejected
    confidence: float
    supporting_sources: int
    conflicting_sources: int
    verification_details: Dict[str, Any]
    verified_at: datetime = field(default_factory=datetime.utcnow)


class VerificationAgent:
    """Verify claims against collected evidence."""

    def __init__(self):
        self.name = "verification_agent"

    async def verify_claims(
        self,
        claims: List[str],
        evidence: List[Dict[str, Any]],
    ) -> List[VerificationResult]:
        """Verify multiple claims against evidence."""
        logger.info(f"Verifying {len(claims)} claims")

        results = []
        for i, claim in enumerate(claims):
            result = await self._verify_claim(claim, evidence, i)
            results.append(result)

        return results

    async def _verify_claim(
        self,
        claim: str,
        evidence: List[Dict[str, Any]],
        claim_index: int,
    ) -> VerificationResult:
        """Verify a single claim against evidence."""
        claim_id = f"claim_{claim_index}"

        # Filter evidence for this claim
        claim_evidence = [e for e in evidence if e.get("claim_id") == claim_id]

        if not claim_evidence:
            return VerificationResult(
                claim_id=claim_id,
                claim_text=claim,
                status="uncertain",
                confidence=0.0,
                supporting_sources=0,
                conflicting_sources=0,
                verification_details={"reason": "No evidence found"},
            )

        # Count supporting vs conflicting
        supporting = sum(1 for e in claim_evidence if e.get("supports_claim", True))
        conflicting = sum(1 for e in claim_evidence if not e.get("supports_claim", True))

        # Calculate confidence based on evidence quality
        total_evidence = len(claim_evidence)
        avg_relevance = sum(e.get("relevance_score", 0) for e in claim_evidence) / total_evidence
        avg_confidence = sum(e.get("confidence_score", 0) for e in claim_evidence) / total_evidence
        avg_credibility = sum(e.get("metadata", {}).get("source_credibility", 0) for e in claim_evidence) / total_evidence

        # Determine status
        if supporting == 0:
            status = "rejected"
            confidence = 0.1
        elif conflicting == 0 and supporting >= 2:
            status = "verified"
            confidence = min(0.6 + (avg_relevance + avg_confidence + avg_credibility) / 3 * 0.4, 0.95)
        elif conflicting == 0 and supporting == 1:
            status = "likely"
            confidence = min(0.4 + (avg_relevance + avg_confidence) / 2 * 0.4, 0.8)
        elif conflicting > 0:
            status = "conflicting"
            confidence = max(0.2, (supporting - conflicting) / total_evidence + avg_confidence * 0.3)
        else:
            status = "uncertain"
            confidence = avg_confidence * 0.5

        return VerificationResult(
            claim_id=claim_id,
            claim_text=claim,
            status=status,
            confidence=round(confidence, 2),
            supporting_sources=supporting,
            conflicting_sources=conflicting,
            verification_details={
                "total_evidence": total_evidence,
                "avg_relevance": round(avg_relevance, 2),
                "avg_confidence": round(avg_confidence, 2),
                "avg_credibility": round(avg_credibility, 2),
                "evidence_types": list(set(e.get("evidence_type", "other") for e in claim_evidence)),
            },
        )

    async def cross_verify(
        self,
        claims: List[str],
        external_sources: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Cross-verify claims against external sources."""
        logger.info(f"Cross-verifying {len(claims)} claims")

        # This would integrate with fact-checking APIs in production
        # For now, return mock results
        return {
            "cross_verified": len(claims),
            "results": [
                {
                    "claim": claim,
                    "verified": True,
                    "external_sources": 2,
                }
                for claim in claims
            ],
        }


class SourceValidator:
    """Validate source credibility and quality."""

    def __init__(self):
        self.name = "source_validator"

    async def validate_sources(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and score sources."""
        logger.info(f"Validating {len(sources)} sources")

        validated = []
        for source in sources:
            validated_source = await self._validate_source(source)
            validated.append(validated_source)

        return validated

    async def _validate_source(self, source: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a single source."""
        credibility = source.get("credibility", 0.5)
        relevance = source.get("relevance", 0.5)

        # Domain-based credibility
        url = source.get("url", "")
        domain_credibility = self._assess_domain_credibility(url)

        # Content quality indicators
        content_quality = self._assess_content_quality(source)

        # Combined score
        final_credibility = (credibility + domain_credibility + content_quality) / 3

        return {
            **source,
            "credibility": round(final_credibility, 2),
            "domain_credibility": round(domain_credibility, 2),
            "content_quality": round(content_quality, 2),
            "validation_timestamp": datetime.utcnow().isoformat(),
        }

    def _assess_domain_credibility(self, url: str) -> float:
        """Assess credibility based on domain."""
        if not url:
            return 0.3

        from urllib.parse import urlparse
        try:
            domain = urlparse(url).netloc.lower()
        except Exception:
            return 0.3

        # High credibility domains
        high_cred = [
            "arxiv.org", "pubmed.ncbi.nlm.nih.gov", "scholar.google.com",
            "github.com", "stackoverflow.com", "medium.com",
            "linkedin.com", "glassdoor.com", "indeed.com",
        ]

        # Medium credibility
        med_cred = [
            "wikipedia.org", "reddit.com", "quora.com",
        ]

        if any(d in domain for d in high_cred):
            return 0.9
        elif any(d in domain for d in med_cred):
            return 0.6
        elif domain.endswith((".edu", ".gov", ".org")):
            return 0.8
        elif domain.endswith(".com"):
            return 0.7
        return 0.5

    def _assess_content_quality(self, source: Dict[str, Any]) -> float:
        """Assess content quality."""
        score = 0.5

        # Has title
        if source.get("title") and len(source["title"]) > 10:
            score += 0.1

        # Has snippet/content
        content = source.get("snippet") or source.get("content", "")
        if content and len(content) > 100:
            score += 0.2
        elif content and len(content) > 50:
            score += 0.1

        # Has author
        if source.get("author"):
            score += 0.1

        # Has date
        if source.get("published_date"):
            score += 0.1

        return min(score, 1.0)