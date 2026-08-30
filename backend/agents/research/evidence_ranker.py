import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import math

logger = logging.getLogger(__name__)


@dataclass
class RankedEvidence:
    """Evidence with ranking scores."""
    evidence_id: str
    claim_id: str
    source_url: str
    source_title: str
    source_type: str
    evidence_text: str
    evidence_type: str  # direct_quote, statistic, expert_opinion, case_study, survey, report
    supports_claim: bool
    relevance_score: float  # 0-1
    confidence_score: float  # 0-1
    citation_context: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Ranking scores
    quality_score: float = 0.0      # Evidence quality (type, source)
    authority_score: float = 0.0    # Source authority
    recency_score: float = 0.0      # How recent
    specificity_score: float = 0.0  # How specific to claim
    corroboration_score: float = 0.0  # Agreement with other evidence
    final_score: float = 0.0        # Weighted combination
    rank: int = 0                   # Final rank position


@dataclass
class EvidenceRankingResult:
    """Result of evidence ranking."""
    claim_id: str
    claim_text: str
    ranked_evidence: List[RankedEvidence]
    top_evidence: List[RankedEvidence]  # Top N
    evidence_summary: Dict[str, Any]
    ranked_at: datetime = field(default_factory=datetime.utcnow)


class EvidenceRanker:
    """Rank evidence by quality, authority, recency, specificity, and corroboration."""

    def __init__(self):
        self.name = "evidence_ranker"

        # Evidence type quality weights
        self.type_weights = {
            "statistic": 1.0,
            "expert_opinion": 0.9,
            "direct_quote": 0.85,
            "report": 0.8,
            "case_study": 0.75,
            "survey_result": 0.7,
            "other": 0.5,
        }

        # Source type authority weights
        self.source_authority = {
            "academic": 1.0,
            "job_market": 0.9,
            "company": 0.8,
            "news": 0.7,
            "web": 0.5,
        }

    async def rank_evidence(
        self,
        evidence_list: List[Dict[str, Any]],
        claims: List[str],
        sources: List[Dict[str, Any]],
        max_per_claim: int = 10,
    ) -> List[EvidenceRankingResult]:
        """Rank evidence for all claims."""
        logger.info(f"Ranking evidence for {len(claims)} claims")

        # Build source lookup
        source_lookup = {s.get("url", ""): s for s in sources}

        results = []
        for i, claim in enumerate(claims):
            claim_id = f"claim_{i}"

            # Filter evidence for this claim
            claim_evidence = [
                e for e in evidence_list
                if e.get("claim_id") == claim_id
            ]

            if not claim_evidence:
                results.append(EvidenceRankingResult(
                    claim_id=claim_id,
                    claim_text=claim,
                    ranked_evidence=[],
                    top_evidence=[],
                    evidence_summary={"total": 0, "supporting": 0, "conflicting": 0},
                ))
                continue

            # Convert to RankedEvidence
            ranked = await self._rank_claim_evidence(
                claim_id, claim, claim_evidence, source_lookup
            )

            # Sort by final score
            ranked.sort(key=lambda e: e.final_score, reverse=True)

            # Assign ranks
            for rank, ev in enumerate(ranked, 1):
                ev.rank = rank

            # Get top evidence
            top_evidence = ranked[:max_per_claim]

            # Create summary
            supporting = sum(1 for e in ranked if e.supports_claim)
            conflicting = sum(1 for e in ranked if not e.supports_claim)

            evidence_summary = {
                "total": len(ranked),
                "supporting": supporting,
                "conflicting": conflicting,
                "avg_quality": sum(e.quality_score for e in ranked) / len(ranked) if ranked else 0,
                "avg_authority": sum(e.authority_score for e in ranked) / len(ranked) if ranked else 0,
                "types": list(set(e.evidence_type for e in ranked)),
                "source_types": list(set(e.source_type for e in ranked)),
            }

            results.append(EvidenceRankingResult(
                claim_id=claim_id,
                claim_text=claim,
                ranked_evidence=ranked,
                top_evidence=top_evidence,
                evidence_summary=evidence_summary,
            ))

        return results

    async def _rank_claim_evidence(
        self,
        claim_id: str,
        claim: str,
        evidence: List[Dict[str, Any]],
        source_lookup: Dict[str, Dict[str, Any]],
    ) -> List[RankedEvidence]:
        """Rank evidence for a single claim."""
        ranked = []
        claim_keywords = set(claim.lower().split())

        for ev in evidence:
            # Get source info
            source_url = ev.get("source_url", "")
            source = source_lookup.get(source_url, {})

            # Create RankedEvidence
            ranked_ev = RankedEvidence(
                evidence_id=ev.get("id", f"ev_{len(ranked)}"),
                claim_id=claim_id,
                source_url=source_url,
                source_title=ev.get("source_title", "Unknown"),
                source_type=ev.get("source_type", "web"),
                evidence_text=ev.get("evidence_text", ""),
                evidence_type=ev.get("evidence_type", "other"),
                supports_claim=ev.get("supports_claim", True),
                relevance_score=ev.get("relevance_score", 0.5),
                confidence_score=ev.get("confidence_score", 0.5),
                citation_context=ev.get("citation_context"),
                metadata=ev.get("metadata", {}),
            )

            # Calculate individual scores
            ranked_ev.quality_score = self._calculate_quality_score(ranked_ev)
            ranked_ev.authority_score = self._calculate_authority_score(ranked_ev, source)
            ranked_ev.recency_score = self._calculate_recency_score(source)
            ranked_ev.specificity_score = self._calculate_specificity_score(ranked_ev, claim_keywords)
            ranked_ev.corroboration_score = 0.0  # Will calculate after all

            ranked.append(ranked_ev)

        # Calculate corroboration (cross-evidence agreement)
        self._calculate_corroboration(ranked)

        # Calculate final weighted score
        for ev in ranked:
            ev.final_score = self._calculate_final_score(ev)

        return ranked

    def _calculate_quality_score(self, evidence: RankedEvidence) -> float:
        """Calculate evidence quality based on type."""
        return self.type_weights.get(evidence.evidence_type, 0.5)

    def _calculate_authority_score(
        self,
        evidence: RankedEvidence,
        source: Dict[str, Any],
    ) -> float:
        """Calculate source authority score."""
        base = self.source_authority.get(evidence.source_type, 0.5)

        # Adjust by source credibility
        credibility = source.get("credibility", evidence.confidence_score)
        domain_cred = source.get("domain_credibility", 0.5)

        return round((base + credibility + domain_cred) / 3, 3)

    def _calculate_recency_score(self, source: Dict[str, Any]) -> float:
        """Calculate recency score."""
        pub_date = source.get("published_date")
        if not pub_date:
            return 0.5

        try:
            from datetime import datetime, timezone
            pub_dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
            if pub_dt.tzinfo is None:
                pub_dt = pub_dt.replace(tzinfo=timezone.utc)

            now = datetime.now(timezone.utc)
            days_old = (now - pub_dt).days

            if days_old < 7:
                return 1.0
            elif days_old < 30:
                return 0.9
            elif days_old < 90:
                return 0.7
            elif days_old < 180:
                return 0.5
            elif days_old < 365:
                return 0.3
            else:
                return 0.1
        except Exception:
            return 0.5

    def _calculate_specificity_score(
        self,
        evidence: RankedEvidence,
        claim_keywords: set,
    ) -> float:
        """Calculate how specific evidence is to the claim."""
        ev_text = evidence.evidence_text.lower()
        ev_keywords = set(ev_text.split())

        # Keyword overlap
        overlap = claim_keywords & ev_keywords
        if not claim_keywords:
            return 0.5

        overlap_ratio = len(overlap) / len(claim_keywords)

        # Evidence length factor (more specific = longer relevant excerpt)
        length_factor = min(len(evidence.evidence_text) / 500, 1.0)

        # Evidence type factor (statistics and quotes are more specific)
        type_factor = {
            "statistic": 1.0,
            "direct_quote": 0.95,
            "expert_opinion": 0.85,
            "report": 0.8,
            "case_study": 0.75,
            "survey_result": 0.8,
            "other": 0.6,
        }.get(evidence.evidence_type, 0.6)

        return round(overlap_ratio * 0.5 + length_factor * 0.2 + type_factor * 0.3, 3)

    def _calculate_corroboration(self, evidence_list: List[RankedEvidence]) -> None:
        """Calculate corroboration score based on agreement with other evidence."""
        if len(evidence_list) <= 1:
            for ev in evidence_list:
                ev.corroboration_score = 0.5  # Neutral
            return

        # Group by supports_claim
        supporting = [e for e in evidence_list if e.supports_claim]
        conflicting = [e for e in evidence_list if not e.supports_claim]

        # More supporting evidence = higher corroboration for supporting
        # More conflicting = lower corroboration for supporting
        support_ratio = len(supporting) / len(evidence_list)

        for ev in evidence_list:
            if ev.supports_claim:
                # High support ratio = high corroboration
                ev.corroboration_score = min(0.3 + support_ratio * 0.7, 1.0)
            else:
                # High conflict ratio = high corroboration for conflicting
                conflict_ratio = len(conflicting) / len(evidence_list)
                ev.corroboration_score = min(0.3 + conflict_ratio * 0.7, 1.0)

    def _calculate_final_score(self, evidence: RankedEvidence) -> float:
        """Calculate final weighted ranking score."""
        weights = {
            "quality": 0.20,
            "authority": 0.25,
            "recency": 0.15,
            "specificity": 0.20,
            "corroboration": 0.10,
            "relevance": 0.10,  # Original relevance
        }

        score = (
            evidence.quality_score * weights["quality"] +
            evidence.authority_score * weights["authority"] +
            evidence.recency_score * weights["recency"] +
            evidence.specificity_score * weights["specificity"] +
            evidence.corroboration_score * weights["corroboration"] +
            evidence.relevance_score * weights["relevance"]
        )

        # Boost if supports claim
        if evidence.supports_claim:
            score *= 1.1

        return round(min(score, 1.0), 3)

    async def get_best_evidence_for_claim(
        self,
        ranking_results: List[EvidenceRankingResult],
        claim_id: str,
        count: int = 3,
    ) -> List[RankedEvidence]:
        """Get best evidence for a specific claim."""
        for result in ranking_results:
            if result.claim_id == claim_id:
                return result.top_evidence[:count]
        return []

    async def get_evidence_stats(
        self,
        ranking_results: List[EvidenceRankingResult],
    ) -> Dict[str, Any]:
        """Get statistics across all ranked evidence."""
        all_evidence = []
        for result in ranking_results:
            all_evidence.extend(result.ranked_evidence)

        if not all_evidence:
            return {"total_evidence": 0}

        return {
            "total_evidence": len(all_evidence),
            "by_type": self._count_by_field(all_evidence, "evidence_type"),
            "by_source_type": self._count_by_field(all_evidence, "source_type"),
            "avg_final_score": sum(e.final_score for e in all_evidence) / len(all_evidence),
            "supporting_count": sum(1 for e in all_evidence if e.supports_claim),
            "conflicting_count": sum(1 for e in all_evidence if not e.supports_claim),
            "top_evidence_types": self._get_top_types(all_evidence),
        }

    def _count_by_field(self, evidence: List[RankedEvidence], field: str) -> Dict[str, int]:
        """Count evidence by field value."""
        counts = defaultdict(int)
        for e in evidence:
            val = getattr(e, field, "unknown")
            counts[val] += 1
        return dict(counts)

    def _get_top_types(self, evidence: List[RankedEvidence], top: int = 5) -> List[Dict[str, Any]]:
        """Get top evidence types by average score."""
        type_scores = defaultdict(list)
        for e in evidence:
            type_scores[e.evidence_type].append(e.final_score)

        avg_scores = {
            t: sum(s) / len(s) for t, s in type_scores.items()
        }

        sorted_types = sorted(avg_scores.items(), key=lambda x: x[1], reverse=True)
        return [
            {"type": t, "avg_score": round(s, 3), "count": len(type_scores[t])}
            for t, s in sorted_types[:top]
        ]