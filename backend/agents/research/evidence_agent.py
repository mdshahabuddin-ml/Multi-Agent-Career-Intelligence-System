import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Evidence:
    """Evidence piece for a claim."""
    id: str
    claim_id: str
    source_url: str
    source_title: str
    source_type: str
    evidence_text: str
    evidence_type: str  # direct_quote, statistic, expert_opinion, case_study, survey, report
    supports_claim: bool
    relevance_score: float
    confidence_score: float
    citation_context: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


class EvidenceAgent:
    """Collect evidence for research claims."""

    def __init__(self):
        self.name = "evidence_agent"

    async def collect_evidence(
        self,
        sources: List[Dict[str, Any]],
        claims: List[str],
    ) -> List[Evidence]:
        """Collect evidence from sources for given claims."""
        logger.info(f"Collecting evidence for {len(claims)} claims from {len(sources)} sources")

        all_evidence = []

        for i, claim in enumerate(claims):
            claim_evidence = await self._extract_evidence_for_claim(claim, sources, i)
            all_evidence.extend(claim_evidence)

        logger.info(f"Collected {len(all_evidence)} pieces of evidence")
        return all_evidence

    async def _extract_evidence_for_claim(
        self,
        claim: str,
        sources: List[Dict[str, Any]],
        claim_index: int,
    ) -> List[Evidence]:
        """Extract evidence from sources for a specific claim."""
        evidence_list = []
        claim_lower = claim.lower()

        for source in sources:
            # Check if source is relevant to claim
            source_text = " ".join(filter(None, [
                source.get("title", ""),
                source.get("snippet", ""),
                source.get("content", ""),
            ])).lower()

            # Simple relevance check - keyword overlap
            claim_keywords = set(claim_lower.split())
            source_keywords = set(source_text.split())
            overlap = claim_keywords & source_keywords
            relevance = len(overlap) / len(claim_keywords) if claim_keywords else 0

            if relevance > 0.1:  # Minimum relevance threshold
                # Extract relevant snippet
                evidence_text = self._extract_relevant_snippet(claim, source.get("snippet", ""))

                evidence = Evidence(
                    id=f"ev_{claim_index}_{source.get('url', 'unknown')[:20]}",
                    claim_id=f"claim_{claim_index}",
                    source_url=source.get("url", ""),
                    source_title=source.get("title", "Unknown"),
                    source_type=source.get("source_type", "web"),
                    evidence_text=evidence_text,
                    evidence_type=self._classify_evidence_type(evidence_text),
                    supports_claim=True,  # Would need NLP to determine
                    relevance_score=min(relevance * 1.5, 1.0),
                    confidence_score=source.get("credibility", 0.7),
                    citation_context=f"From {source.get('title', 'source')}",
                    metadata={
                        "source_credibility": source.get("credibility", 0.7),
                        "source_relevance": source.get("relevance", 0.7),
                    },
                )
                evidence_list.append(evidence)

        # Sort by relevance and confidence
        evidence_list.sort(key=lambda e: e.relevance_score * e.confidence_score, reverse=True)
        return evidence_list[:5]  # Top 5 per claim

    def _extract_relevant_snippet(self, claim: str, source_text: str) -> str:
        """Extract the most relevant snippet from source text for the claim."""
        if not source_text:
            return ""

        # Simple approach: return first 300 chars that contain claim keywords
        claim_keywords = claim.lower().split()
        sentences = source_text.split(". ")

        relevant_sentences = []
        for sent in sentences:
            sent_lower = sent.lower()
            if any(kw in sent_lower for kw in claim_keywords if len(kw) > 3):
                relevant_sentences.append(sent)

        if relevant_sentences:
            return ". ".join(relevant_sentences[:3]) + "."
        return source_text[:300] + "..." if len(source_text) > 300 else source_text

    def _classify_evidence_type(self, text: str) -> str:
        """Classify the type of evidence."""
        text_lower = text.lower()

        if any(kw in text_lower for kw in ["%", "percent", "statistic", "data shows", "survey"]):
            return "statistic"
        elif any(kw in text_lower for kw in ["expert", "according to", "said", "stated", "believes"]):
            return "expert_opinion"
        elif any(kw in text_lower for kw in ["case study", "example", "instance"]):
            return "case_study"
        elif any(kw in text_lower for kw in ["survey", "poll", "respondents"]):
            return "survey_result"
        elif any(kw in text_lower for kw in ["report", "study", "analysis", "findings"]):
            return "report"
        elif '"' in text or "'" in text:
            return "direct_quote"
        return "other"