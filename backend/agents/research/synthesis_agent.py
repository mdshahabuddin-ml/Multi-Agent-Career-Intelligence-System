import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SynthesisResult:
    """Result of research synthesis."""
    research_id: int
    executive_summary: str
    key_findings: List[str]
    detailed_findings: List[Dict[str, Any]]
    recommendations: List[str]
    methodology: str
    limitations: List[str]
    confidence: float
    synthesized_at: datetime = field(default_factory=datetime.utcnow)


class SynthesisAgent:
    """Synthesize research findings into coherent narrative."""

    def __init__(self):
        self.name = "synthesis_agent"

    async def synthesize(
        self,
        research_id: int,
        query: str,
        research_type: str,
        analysis_result: Dict[str, Any],
        verification_results: List[Dict[str, Any]],
        sources: List[Dict[str, Any]],
    ) -> SynthesisResult:
        """Synthesize all research into final output."""
        logger.info(f"Synthesizing research #{research_id}")

        # Generate executive summary
        executive_summary = self._generate_executive_summary(
            query, research_type, analysis_result, verification_results
        )

        # Extract key findings
        key_findings = self._extract_key_findings(
            analysis_result, verification_results
        )

        # Detailed findings
        detailed_findings = self._create_detailed_findings(
            analysis_result, verification_results, sources
        )

        # Recommendations
        recommendations = self._generate_recommendations(
            analysis_result, verification_results, research_type
        )

        # Methodology
        methodology = self._describe_methodology(
            verification_results, sources
        )

        # Limitations
        limitations = self._identify_limitations(
            analysis_result, verification_results, sources
        )

        # Overall confidence
        confidence = analysis_result.get("confidence", 0.5)

        return SynthesisResult(
            research_id=research_id,
            executive_summary=executive_summary,
            key_findings=key_findings,
            detailed_findings=detailed_findings,
            recommendations=recommendations,
            methodology=methodology,
            limitations=limitations,
            confidence=confidence,
        )

    def _generate_executive_summary(
        self,
        query: str,
        research_type: str,
        analysis_result: Dict[str, Any],
        verification_results: List[Dict[str, Any]],
    ) -> str:
        """Generate executive summary."""
        total_claims = len(verification_results)
        verified = sum(1 for v in verification_results if v.get("status") == "verified")
        likely = sum(1 for v in verification_results if v.get("status") == "likely")
        conflicting = sum(1 for v in verification_results if v.get("status") == "conflicting")

        summary_parts = [
            f"This research investigated: '{query}'",
            f"Research type: {research_type.replace('_', ' ').title()}",
            f"Analyzed {total_claims} key claims from multiple sources.",
        ]

        if verified > 0:
            summary_parts.append(f"{verified} claims were verified with high confidence.")
        if likely > 0:
            summary_parts.append(f"{likely} claims are likely true based on available evidence.")
        if conflicting > 0:
            summary_parts.append(f"{conflicting} claims have conflicting evidence and require further investigation.")

        # Add key insight
        insights = analysis_result.get("insights", [])
        high_priority = [i for i in insights if i.get("priority") == "high"]
        if high_priority:
            summary_parts.append(f"Key insight: {high_priority[0].get('description', '')}")

        return " ".join(summary_parts)

    def _extract_key_findings(
        self,
        analysis_result: Dict[str, Any],
        verification_results: List[Dict[str, Any]],
    ) -> List[str]:
        """Extract key findings from analysis."""
        findings = []

        # From verified claims
        verified_claims = [
            v for v in verification_results
            if v.get("status") in ["verified", "likely"]
        ]
        for claim in verified_claims[:5]:
            findings.append(claim.get("claim_text", ""))

        # From insights
        insights = analysis_result.get("insights", [])
        for insight in insights[:3]:
            if insight.get("actionable"):
                findings.append(f"Insight: {insight.get('description', '')}")

        # From patterns
        patterns = analysis_result.get("patterns", [])
        for pattern in patterns[:2]:
            if pattern.get("type") == "term_frequency":
                top_terms = [t["term"] for t in pattern.get("data", [])[:5]]
                findings.append(f"Key themes identified: {', '.join(top_terms)}")

        return findings[:8]  # Limit to 8 key findings

    def _create_detailed_findings(
        self,
        analysis_result: Dict[str, Any],
        verification_results: List[Dict[str, Any]],
        sources: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Create detailed findings with evidence."""
        detailed = []

        # Group by status
        status_groups = {
            "verified": [],
            "likely": [],
            "conflicting": [],
            "uncertain": [],
            "rejected": [],
        }

        for v in verification_results:
            status = v.get("status", "uncertain")
            if status in status_groups:
                status_groups[status].append(v)

        for status, claims in status_groups.items():
            if not claims:
                continue

            for claim in claims:
                # Find supporting evidence
                claim_evidence = [
                    e for e in sources
                    if any(kw in e.get("snippet", "").lower()
                           for kw in claim.get("claim_text", "").lower().split() if len(kw) > 4)
                ]

                detailed.append({
                    "claim": claim.get("claim_text", ""),
                    "status": status,
                    "confidence": claim.get("confidence", 0),
                    "supporting_sources": claim.get("supporting_sources", 0),
                    "conflicting_sources": claim.get("conflicting_sources", 0),
                    "evidence_count": len(claim_evidence),
                    "key_evidence": claim_evidence[:3],
                })

        return detailed

    def _generate_recommendations(
        self,
        analysis_result: Dict[str, Any],
        verification_results: List[Dict[str, Any]],
        research_type: str,
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # From analysis insights
        insights = analysis_result.get("insights", [])
        for insight in insights:
            if insight.get("actionable") and insight.get("priority") in ["high", "medium"]:
                recommendations.append(f"{insight.get('title', '')}: {insight.get('description', '')}")

        # From gaps
        gaps = analysis_result.get("gaps", [])
        for gap in gaps[:3]:
            recommendations.append(f"Address gap: {gap}")

        # Research-type specific recommendations
        type_recs = {
            "job_market": [
                "Monitor job postings weekly for emerging skill requirements",
                "Set up job alerts for target roles and companies",
                "Track salary trends quarterly",
            ],
            "company": [
                "Follow company news and earnings reports",
                "Connect with current employees on LinkedIn",
                "Review Glassdoor/Blind for culture insights",
            ],
            "technology": [
                "Follow key technology blogs and newsletters",
                "Experiment with new tools in side projects",
                "Join relevant developer communities",
            ],
            "career_path": [
                "Create a skill development roadmap",
                "Seek mentorship from target role holders",
                "Build portfolio projects demonstrating target skills",
            ],
            "skill_analysis": [
                "Prioritize learning high-demand skills",
                "Obtain relevant certifications",
                "Contribute to open source projects",
            ],
        }

        for rec in type_recs.get(research_type, []):
            recommendations.append(rec)

        # General recommendations
        recommendations.extend([
            "Regularly update this research as market conditions change",
            "Cross-reference findings with primary sources when possible",
            "Share findings with mentors or peers for validation",
        ])

        # Deduplicate and limit
        seen = set()
        unique = []
        for r in recommendations:
            if r not in seen:
                seen.add(r)
                unique.append(r)

        return unique[:10]

    def _describe_methodology(
        self,
        verification_results: List[Dict[str, Any]],
        sources: List[Dict[str, Any]],
    ) -> str:
        """Describe research methodology."""
        parts = [
            "This research employed a multi-agent approach with specialized agents for web search, "
            "news monitoring, job market analysis, company research, and academic literature review.",
        ]

        source_types = set(s.get("source_type", "web") for s in sources)
        parts.append(f"Sources included: {', '.join(source_types)}.")

        parts.append(
            f"Claims were extracted from source content and verified using a multi-criteria approach: "
            f"source credibility, evidence relevance, cross-source agreement, and evidence type quality. "
            f"{len(verification_results)} claims were evaluated."
        )

        parts.append(
            "Claims were classified as: Verified (multiple high-credibility sources agree), "
            "Likely (single credible source), Conflicting (sources disagree), "
            "Uncertain (insufficient evidence), or Rejected (evidence contradicts)."
        )

        return " ".join(parts)

    def _identify_limitations(
        self,
        analysis_result: Dict[str, Any],
        verification_results: List[Dict[str, Any]],
        sources: List[Dict[str, Any]],
    ) -> List[str]:
        """Identify research limitations."""
        limitations = []

        # Source limitations
        if len(sources) < 5:
            limitations.append("Limited number of sources may not capture full picture")

        source_types = set(s.get("source_type", "web") for s in sources)
        if len(source_types) < 3:
            limitations.append("Limited source type diversity may introduce bias")

        # Recency
        recent_count = 0
        for s in sources:
            pub_date = s.get("published_date")
            if pub_date:
                try:
                    from datetime import datetime
                    pub_dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                    if (datetime.utcnow() - pub_dt.replace(tzinfo=None)).days < 90:
                        recent_count += 1
                except Exception:
                    pass

        if sources and recent_count < len(sources) * 0.3:
            limitations.append("Many sources are older than 90 days; findings may be outdated")

        # Verification limitations
        uncertain = sum(1 for v in verification_results if v.get("status") == "uncertain")
        if uncertain > len(verification_results) * 0.3:
            limitations.append("High proportion of uncertain claims limits confidence")

        conflicting = sum(1 for v in verification_results if v.get("status") == "conflicting")
        if conflicting > 0:
            limitations.append(f"{conflicting} claims have conflicting evidence requiring manual review")

        # General limitations
        limitations.extend([
            "Research based on publicly available sources; proprietary data not included",
            "Automated extraction may miss nuanced context",
            "Salary and market data may vary by location and company size",
            "Findings represent snapshot in time; continuous monitoring recommended",
        ])

        return limitations[:7]