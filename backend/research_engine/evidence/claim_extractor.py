from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4
import re
import logging

from backend.research_engine.state.research_context import SourceMetadata, ResearchClaim, ResearchEvidence

logger = logging.getLogger(__name__)


@dataclass
class ExtractedClaim:
    """A claim extracted from source content."""
    text: str
    claim_type: str  # fact, statistic, opinion, prediction, recommendation
    confidence: float
    source_id: str
    source_title: str
    source_url: str
    evidence_snippet: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class ClaimExtractor:
    """Extract claims from source content."""

    def __init__(self):
        self.claim_patterns = {
            "fact": [
                r"(?:is|are|was|were|has|have|had)\s+(?:a|an|the)?\s*\w+",
                r"(?:shows|indicates|demonstrates|proves|reveals)\s+that",
                r"(?:according to|based on|data shows|research shows)\s+",
            ],
            "statistic": [
                r"\d+(?:\.\d+)?%\s*(?:of|increase|decrease|growth)",
                r"\$\d+(?:,\d{3})*(?:\.\d+)?\s*(?:billion|million|thousand|k|M|B)",
                r"\d+(?:,\d{3})*(?:\.\d+)?\s*(?:jobs|positions|workers|employees)",
                r"(?:average|median|mean)\s+(?:salary|pay|compensation)\s+(?:is|of)\s*\$?",
                r"(?:increased|decreased|grew|fell)\s+by\s+\d+(?:\.\d+)?%",
            ],
            "opinion": [
                r"(?:believes|thinks|suggests|argues|contends|maintains)\s+that",
                r"(?:experts?|analysts?|researchers?)\s+(?:say|believe|argue|suggest)",
                r"(?:in my opinion|it is (?:my|our) (?:view|opinion|belief))\s+that",
            ],
            "prediction": [
                r"(?:will|is expected to|is projected to|is forecast to|is predicted to)\s+\w+",
                r"(?:by\s+20\d{2}|in\s+the\s+next\s+\d+\s+years?)\s*,?\s*(?:will|expected)",
                r"(?:trend|forecast|projection)\s+(?:shows|indicates|suggests)\s+",
            ],
            "recommendation": [
                r"(?:recommend|suggest|advise|urge)\s+(?:that|ing)\s+",
                r"(?:should|must|need to|ought to)\s+\w+",
                r"(?:best practice|recommended approach|advised)\s+(?:is|to)\s+",
            ],
        }

    def extract_claims(
        self,
        sources: List[SourceMetadata],
        min_confidence: float = 0.3,
    ) -> List[ExtractedClaim]:
        """Extract claims from a list of sources."""
        all_claims = []

        for source in sources:
            content = self._get_source_content(source)
            if not content:
                continue

            claims = self._extract_from_content(content, source)
            all_claims.extend(claims)

        # Filter by confidence
        filtered = [c for c in all_claims if c.confidence >= min_confidence]

        # Deduplicate similar claims
        deduplicated = self._deduplicate_claims(filtered)

        logger.info(f"Extracted {len(deduplicated)} claims from {len(sources)} sources")
        return deduplicated

    def _get_source_content(self, source: SourceMetadata) -> str:
        """Get content from source metadata."""
        # In production, this would fetch from storage
        # For now, use snippet
        return source.custom_metadata.get("content", source.custom_metadata.get("snippet", ""))

    def _extract_from_content(
        self,
        content: str,
        source: SourceMetadata,
    ) -> List[ExtractedClaim]:
        """Extract claims from text content."""
        claims = []

        # Split into sentences
        sentences = re.split(r'[.!?]+', content)

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20 or len(sentence) > 500:
                continue

            # Classify claim type
            claim_type, confidence = self._classify_claim(sentence)

            if confidence >= 0.3:
                # Extract evidence snippet (surrounding context)
                evidence_snippet = self._extract_evidence_snippet(content, sentence)

                claim = ExtractedClaim(
                    text=sentence,
                    claim_type=claim_type,
                    confidence=confidence,
                    source_id=source.url,
                    source_title=source.title,
                    source_url=source.url,
                    evidence_snippet=evidence_snippet,
                    metadata={
                        "source_type": source.source_type.value,
                        "source_credibility": source.credibility_score,
                        "source_relevance": source.relevance_score,
                    },
                )
                claims.append(claim)

        return claims

    def _classify_claim(self, sentence: str) -> tuple[str, float]:
        """Classify claim type and confidence."""
        sentence_lower = sentence.lower()
        best_type = "fact"
        best_confidence = 0.3

        for claim_type, patterns in self.claim_patterns.items():
            for pattern in patterns:
                if re.search(pattern, sentence_lower, re.IGNORECASE):
                    # Calculate confidence based on pattern strength and sentence quality
                    confidence = 0.5

                    # Boost for specific indicators
                    if claim_type == "statistic" and re.search(r"\d+(?:\.\d+)?%", sentence):
                        confidence = 0.8
                    elif claim_type == "prediction" and re.search(r"(?:20\d{2}|next \d+ years)", sentence_lower):
                        confidence = 0.7
                    elif claim_type == "recommendation" and re.search(r"(?:should|must|recommend)", sentence_lower):
                        confidence = 0.7

                    # Length penalty
                    if len(sentence) > 300:
                        confidence *= 0.8

                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_type = claim_type

        return best_type, best_confidence

    def _extract_evidence_snippet(self, content: str, target_sentence: str, context_chars: int = 200) -> str:
        """Extract surrounding context for a sentence."""
        idx = content.find(target_sentence)
        if idx == -1:
            return target_sentence[:200]

        start = max(0, idx - context_chars)
        end = min(len(content), idx + len(target_sentence) + context_chars)
        return content[start:end].strip()

    def _deduplicate_claims(self, claims: List[ExtractedClaim]) -> List[ExtractedClaim]:
        """Remove duplicate or very similar claims."""
        unique = []
        seen_texts = set()

        for claim in claims:
            # Normalize for comparison
            normalized = re.sub(r'\s+', ' ', claim.text.lower()).strip()
            normalized = re.sub(r'[^\w\s]', '', normalized)

            # Check similarity with existing
            is_duplicate = False
            for seen in seen_texts:
                similarity = self._text_similarity(normalized, seen)
                if similarity > 0.85:
                    is_duplicate = True
                    break

            if not is_duplicate:
                seen_texts.add(normalized)
                unique.append(claim)

        return unique

    def _text_similarity(self, a: str, b: str) -> float:
        """Calculate text similarity using Jaccard index."""
        words_a = set(a.split())
        words_b = set(b.split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)

    def convert_to_research_claims(
        self,
        extracted: List[ExtractedClaim],
    ) -> List[ResearchClaim]:
        """Convert extracted claims to ResearchClaim objects."""
        research_claims = []
        for ext in extracted:
            claim = ResearchClaim(
                id=str(uuid4()),
                text=ext.text,
                claim_type=ext.claim_type,
                source_ids=[ext.source_id],
                confidence=ext.confidence,
                status="extracted",
                metadata={
                    **ext.metadata,
                    "source_title": ext.source_title,
                    "source_url": ext.source_url,
                    "evidence_snippet": ext.evidence_snippet,
                },
            )
            research_claims.append(claim)
        return research_claims