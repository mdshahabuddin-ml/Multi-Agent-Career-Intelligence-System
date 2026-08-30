from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4
import logging

from backend.research_engine.state.research_context import (
    SourceMetadata, ResearchClaim, ResearchEvidence
)

logger = logging.getLogger(__name__)


@dataclass
class EvidenceCollectionResult:
    """Result of evidence collection."""
    claim_id: str
    evidence: List[ResearchEvidence]
    total_sources_checked: int
    sources_with_evidence: int
    collection_time_ms: int


class EvidenceCollector:
    """Collect evidence for claims from sources."""

    def __init__(self):
        self.min_relevance_threshold = 0.15
        self.max_evidence_per_claim = 10

    async def collect_for_claims(
        self,
        claims: List[ResearchClaim],
        sources: List[SourceMetadata],
    ) -> List[EvidenceCollectionResult]:
        """Collect evidence for multiple claims."""
        results = []

        for claim in claims:
            result = await self._collect_for_claim(claim, sources)
            results.append(result)

        return results

    async def _collect_for_claim(
        self,
        claim: ResearchClaim,
        sources: List[SourceMetadata],
    ) -> EvidenceCollectionResult:
        """Collect evidence for a single claim."""
        start_time = datetime.utcnow()

        evidence_list = []
        sources_checked = 0
        sources_with_evidence = 0

        # Get claim keywords for matching
        claim_keywords = self._extract_keywords(claim.text)

        for source in sources:
            sources_checked += 1

            # Get source content
            content = self._get_source_content(source)
            if not content:
                continue

            # Check relevance
            relevance = self._calculate_relevance(claim.text, claim_keywords, content, source)

            if relevance < self.min_relevance_threshold:
                continue

            sources_with_evidence += 1

            # Extract relevant snippets
            snippets = self._extract_relevant_snippets(claim.text, claim_keywords, content)

            for snippet in snippets[:3]:  # Max 3 snippets per source
                evidence = self._create_evidence(
                    claim_id=claim.id,
                    source=source,
                    snippet=snippet,
                    relevance=relevance,
                )
                evidence_list.append(evidence)

                if len(evidence_list) >= self.max_evidence_per_claim:
                    break

        # Sort by relevance and confidence
        evidence_list.sort(
            key=lambda e: e.relevance_score * e.confidence_score,
            reverse=True
        )
        evidence_list = evidence_list[:self.max_evidence_per_claim]

        elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000

        return EvidenceCollectionResult(
            claim_id=claim.id,
            evidence=evidence_list,
            total_sources_checked=sources_checked,
            sources_with_evidence=sources_with_evidence,
            collection_time_ms=int(elapsed),
        )

    def _get_source_content(self, source: SourceMetadata) -> str:
        """Get content from source."""
        return source.custom_metadata.get("content", source.custom_metadata.get("snippet", ""))

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from claim text."""
        # Simple keyword extraction
        stopwords = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "as", "is", "are", "was", "were", "be",
            "been", "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "must", "can", "this",
            "that", "these", "those", "i", "you", "he", "she", "it", "we", "they",
        }

        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [w for w in words if w not in stopwords and len(w) > 3]
        return list(set(keywords))

    def _calculate_relevance(
        self,
        claim_text: str,
        claim_keywords: List[str],
        source_content: str,
        source: SourceMetadata,
    ) -> float:
        """Calculate relevance of source to claim."""
        if not source_content:
            return 0.0

        content_lower = source_content.lower()
        claim_lower = claim_text.lower()

        # Keyword overlap
        matches = sum(1 for kw in claim_keywords if kw in content_lower)
        keyword_score = min(matches / max(len(claim_keywords), 1), 1.0) if claim_keywords else 0

        # Direct phrase match
        phrase_score = 1.0 if claim_text[:50].lower() in content_lower else 0

        # Source credibility boost
        credibility_boost = source.credibility_score * 0.2

        # Combined score
        relevance = (
            keyword_score * 0.5 +
            phrase_score * 0.3 +
            source.relevance_score * 0.2
        ) + credibility_boost

        return min(relevance, 1.0)

    def _extract_relevant_snippets(
        self,
        claim_text: str,
        claim_keywords: List[str],
        content: str,
        max_snippets: int = 3,
        snippet_length: int = 300,
    ) -> List[str]:
        """Extract relevant snippets from content."""
        snippets = []
        content_lower = content.lower()

        # Find positions of keywords
        positions = []
        for kw in claim_keywords:
            start = 0
            while True:
                idx = content_lower.find(kw.lower(), start)
                if idx == -1:
                    break
                positions.append(idx)
                start = idx + 1

        # Also check for claim phrase
        claim_start = content_lower.find(claim_text[:100].lower())
        if claim_start != -1:
            positions.append(claim_start)

        # Create snippets around positions
        for pos in sorted(set(positions)):
            start = max(0, pos - snippet_length // 2)
            end = min(len(content), pos + snippet_length // 2)
            snippet = content[start:end].strip()

            if snippet and len(snippet) > 50:
                snippets.append(snippet)

        return snippets[:max_snippets]

    def _create_evidence(
        self,
        claim_id: str,
        source: SourceMetadata,
        snippet: str,
        relevance: float,
    ) -> ResearchEvidence:
        """Create an evidence object."""
        # Determine evidence type
        evidence_type = self._classify_evidence_type(snippet)

        # Calculate confidence based on source credibility and relevance
        confidence = (source.credibility_score + relevance) / 2

        return ResearchEvidence(
            id=str(uuid4()),
            claim_id=claim_id,
            source_id=source.url,
            text=snippet,
            evidence_type=evidence_type,
            supports_claim=True,  # Would need NLP to determine stance
            relevance_score=relevance,
            confidence_score=confidence,
            citation_context=f"From {source.title or source.url}",
            metadata={
                "source_type": source.source_type.value,
                "source_credibility": source.credibility_score,
                "source_domain": source.domain,
            },
        )

    def _classify_evidence_type(self, text: str) -> str:
        """Classify the type of evidence."""
        text_lower = text.lower()

        if any(kw in text_lower for kw in ["%", "percent", "statistic", "data shows", "survey", "poll"]):
            return "statistic"
        elif any(kw in text_lower for kw in ["expert", "according to", "said", "stated", "believes", "argues"]):
            return "expert_opinion"
        elif any(kw in text_lower for kw in ["case study", "example", "instance", "demonstrates"]):
            return "case_study"
        elif any(kw in text_lower for kw in ["survey", "poll", "respondents", "participants"]):
            return "survey_result"
        elif any(kw in text_lower for kw in ["report", "study", "analysis", "findings", "research"]):
            return "report"
        elif '"' in text or "'" in text:
            return "direct_quote"
        return "other"


import re