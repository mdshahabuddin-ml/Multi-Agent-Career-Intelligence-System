from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum as PyEnum
import logging

from backend.research_engine.state.research_context import (
    ResearchClaim, ResearchEvidence, SourceMetadata
)

logger = logging.getLogger(__name__)


class SynthesisStrategy(str, PyEnum):
    """Synthesis strategies."""
    THEMATIC = "thematic"  # Group by themes
    CHRONOLOGICAL = "chronological"  # Order by time
    ARGUMENTATIVE = "argumentative"  # Build argument
    COMPARATIVE = "comparative"  # Compare viewpoints
    COMPREHENSIVE = "comprehensive"  # Full synthesis


@dataclass
class SynthesizedSection:
    """A section of the synthesis."""
    title: str
    content: str
    supporting_claims: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    confidence: float = 0.0
    order: int = 0


@dataclass
class SynthesisResult:
    """Complete synthesis result."""
    query: str
    research_type: str
    executive_summary: str
    sections: List[SynthesizedSection]
    key_findings: List[str]
    recommendations: List[str]
    methodology: str
    limitations: List[str]
    confidence: float
    word_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)


class ResearchSynthesizer:
    """Synthesize research findings into coherent narrative."""

    def __init__(self, strategy: SynthesisStrategy = SynthesisStrategy.COMPREHENSIVE):
        self.strategy = strategy

    async def synthesize(
        self,
        query: str,
        research_type: str,
        claims: List[ResearchClaim],
        evidence: List[ResearchEvidence],
        verification_results: List[Dict[str, Any]],
        sources: List[SourceMetadata],
        analysis_result: Optional[Dict[str, Any]] = None,
    ) -> SynthesisResult:
        """Synthesize research findings."""
        logger.info(f"Synthesizing research for: {query}")

        # Filter verified claims
        verified_claims = self._get_verified_claims(claims, verification_results)

        # Generate sections based on strategy
        if self.strategy == SynthesisStrategy.THEMATIC:
            sections = await self._synthesize_thematic(verified_claims, evidence, sources)
        elif self.strategy == SynthesisStrategy.CHRONOLOGICAL:
            sections = await self._synthesize_chronological(verified_claims, evidence, sources)
        elif self.strategy == SynthesisStrategy.ARGUMENTATIVE:
            sections = await self._synthesize_argumentative(verified_claims, evidence, sources)
        elif self.strategy == SynthesisStrategy.COMPARATIVE:
            sections = await self._synthesize_comparative(verified_claims, evidence, sources)
        else:  # COMPREHENSIVE
            sections = await self._synthesize_comprehensive(verified_claims, evidence, sources, analysis_result)

        # Generate executive summary
        executive_summary = self._generate_executive_summary(
            query, research_type, sections, verification_results
        )

        # Extract key findings
        key_findings = self._extract_key_findings(sections, verification_results)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            query, research_type, sections, analysis_result
        )

        # Methodology
        methodology = self._describe_methodology(verification_results, sources)

        # Limitations
        limitations = self._identify_limitations(verification_results, sources)

        # Overall confidence
        confidence = self._calculate_overall_confidence(verification_results)

        # Word count
        section_contents = [s.content for s in sections]
        word_count = self._count_words(executive_summary, section_contents, key_findings, recommendations)

        return SynthesisResult(
            query=query,
            research_type=research_type,
            executive_summary=executive_summary,
            sections=sections,
            key_findings=key_findings,
            recommendations=recommendations,
            methodology=methodology,
            limitations=limitations,
            confidence=confidence,
            word_count=word_count,
        )

    def _get_verified_claims(
        self,
        claims: List[ResearchClaim],
        verification_results: List[Dict[str, Any]],
    ) -> List[ResearchClaim]:
        """Get claims that are verified or likely."""
        verified_statuses = {"verified", "likely"}
        verified_ids = {
            v["claim_id"] for v in verification_results
            if v.get("status") in verified_statuses
        }
        return [c for c in claims if c.id in verified_ids]

    async def _synthesize_thematic(
        self,
        claims: List[ResearchClaim],
        evidence: List[ResearchEvidence],
        sources: List[SourceMetadata],
    ) -> List[SynthesizedSection]:
        """Synthesize by themes."""
        # Group claims by theme (using keywords)
        themes = self._extract_themes(claims)
        sections = []

        for i, (theme, theme_claims) in enumerate(themes.items()):
            content = self._synthesize_theme(theme, theme_claims, evidence, sources)
            confidence = sum(c.confidence for c in theme_claims) / len(theme_claims) if theme_claims else 0

            sections.append(SynthesizedSection(
                title=theme.replace("_", " ").title(),
                content=content,
                supporting_claims=[c.id for c in theme_claims],
                evidence_refs=self._get_evidence_refs(theme_claims, evidence),
                confidence=confidence,
                order=i,
            ))

        return sections

    async def _synthesize_chronological(
        self,
        claims: List[ResearchClaim],
        evidence: List[ResearchEvidence],
        sources: List[SourceMetadata],
    ) -> List[SynthesizedSection]:
        """Synthesize chronologically by source date."""
        # Group by time periods
        sections = []
        # Simplified - would need date extraction from claims
        return sections

    async def _synthesize_argumentative(
        self,
        claims: List[ResearchClaim],
        evidence: List[ResearchEvidence],
        sources: List[SourceMetadata],
    ) -> List[SynthesizedSection]:
        """Synthesize as argument (thesis, evidence, counter-evidence, conclusion)."""
        sections = [
            SynthesizedSection(
                title="Thesis",
                content=self._build_thesis(claims),
                confidence=0.8,
                order=0,
            ),
            SynthesizedSection(
                title="Supporting Evidence",
                content=self._build_supporting_evidence(claims, evidence),
                confidence=0.85,
                order=1,
            ),
            SynthesizedSection(
                title="Counter-Evidence & Limitations",
                content=self._build_counter_evidence(claims, evidence),
                confidence=0.7,
                order=2,
            ),
            SynthesizedSection(
                title="Conclusion",
                content=self._build_conclusion(claims),
                confidence=0.8,
                order=3,
            ),
        ]
        return sections

    async def _synthesize_comparative(
        self,
        claims: List[ResearchClaim],
        evidence: List[ResearchEvidence],
        sources: List[SourceMetadata],
    ) -> List[SynthesizedSection]:
        """Synthesize by comparing viewpoints."""
        sections = []
        return sections

    async def _synthesize_comprehensive(
        self,
        claims: List[ResearchClaim],
        evidence: List[ResearchEvidence],
        sources: List[SourceMetadata],
        analysis_result: Optional[Dict[str, Any]] = None,
    ) -> List[SynthesizedSection]:
        """Comprehensive synthesis with multiple angles."""
        sections = []

        # 1. Overview
        sections.append(SynthesizedSection(
            title="Overview",
            content=self._build_overview(claims, analysis_result),
            confidence=0.85,
            order=0,
        ))

        # 2. Thematic sections
        themes = self._extract_themes(claims)
        for i, (theme, theme_claims) in enumerate(themes.items()):
            sections.append(SynthesizedSection(
                title=theme.replace("_", " ").title(),
                content=self._synthesize_theme(theme, theme_claims, evidence, sources),
                supporting_claims=[c.id for c in theme_claims],
                confidence=sum(c.confidence for c in theme_claims) / len(theme_claims) if theme_claims else 0,
                order=i + 1,
            ))

        # 3. Evidence quality assessment
        if evidence:
            sections.append(SynthesizedSection(
                title="Evidence Assessment",
                content=self._build_evidence_assessment(evidence),
                confidence=0.9,
                order=len(sections),
            ))

        return sections

    def _extract_themes(self, claims: List[ResearchClaim]) -> Dict[str, List[ResearchClaim]]:
        """Extract themes from claims using keyword clustering."""
        themes = {}

        for claim in claims:
            # Simple theme extraction from claim text
            theme = self._classify_claim_theme(claim.text)
            if theme not in themes:
                themes[theme] = []
            themes[theme].append(claim)

        return themes

    def _classify_claim_theme(self, text: str) -> str:
        """Classify claim into a theme."""
        text_lower = text.lower()

        theme_keywords = {
            "market_trends": ["market", "trend", "demand", "growth", "adoption", "market size"],
            "salary_compensation": ["salary", "compensation", "pay", "wage", "income", "benefits", "bonus"],
            "skills_technologies": ["skill", "technology", "tool", "framework", "language", "platform", "python", "javascript", "aws", "cloud"],
            "career_progression": ["career", "promotion", "advancement", "progression", "senior", "lead", "manager"],
            "company_culture": ["culture", "environment", "work-life", "remote", "hybrid", "values", "mission"],
            "hiring_recruitment": ["hiring", "recruit", "interview", "candidate", "position", "opening", "role"],
            "education_learning": ["education", "learning", "certification", "course", "training", "degree", "bootcamp"],
        }

        for theme, keywords in theme_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return theme

        return "general_findings"

    def _synthesize_theme(
        self,
        theme: str,
        claims: List[ResearchClaim],
        evidence: List[ResearchEvidence],
        sources: List[SourceMetadata],
    ) -> str:
        """Synthesize content for a theme."""
        if not claims:
            return "No findings for this theme."

        # Sort claims by confidence
        sorted_claims = sorted(claims, key=lambda c: c.confidence, reverse=True)

        parts = [f"Analysis of {theme.replace('_', ' ')} reveals several key findings:"]

        for i, claim in enumerate(sorted_claims[:5], 1):
            # Find supporting evidence
            claim_evidence = [
                e for e in evidence
                if claim.id in e.claim_id or any(kw in e.text.lower() for kw in claim.text.lower().split() if len(kw) > 4)
            ]

            parts.append(f"{i}. {claim.text}")

            if claim_evidence:
                # Add top evidence
                top_evidence = sorted(claim_evidence, key=lambda e: e.relevance_score * e.confidence_score, reverse=True)[:2]
                for ev in top_evidence:
                    parts.append(f"   - Evidence: {ev.text[:150]}... (confidence: {ev.confidence_score:.0%})")

        if len(claims) > 5:
            parts.append(f"\nPlus {len(claims) - 5} additional findings.")

        return "\n".join(parts)

    def _build_overview(self, claims: List[ResearchClaim], analysis_result: Optional[Dict]) -> str:
        """Build overview section."""
        total_claims = len(claims)
        verified = sum(1 for c in claims if c.status == "verified")
        likely = sum(1 for c in claims if c.status == "likely")

        parts = [
            f"This research analyzed {total_claims} key claims from multiple sources.",
        ]

        if verified:
            parts.append(f"{verified} claims were verified with high confidence.")
        if likely:
            parts.append(f"{likely} claims are likely true based on available evidence.")

        if analysis_result:
            insights = analysis_result.get("insights", [])
            high_priority = [i for i in insights if i.get("priority") == "high"]
            if high_priority:
                parts.append(f"Key insight: {high_priority[0].get('description', '')}")

        return " ".join(parts)

    def _build_evidence_assessment(self, evidence: List[ResearchEvidence]) -> str:
        """Build evidence assessment section."""
        if not evidence:
            return "No evidence collected."

        by_type = {}
        for e in evidence:
            by_type[e.evidence_type] = by_type.get(e.evidence_type, 0) + 1

        avg_relevance = sum(e.relevance_score for e in evidence) / len(evidence)
        avg_confidence = sum(e.confidence_score for e in evidence) / len(evidence)

        parts = [
            f"Collected {len(evidence)} pieces of evidence across {len(by_type)} evidence types.",
            f"Average relevance: {avg_relevance:.0%}, Average confidence: {avg_confidence:.0%}.",
            "Evidence types: " + ", ".join(f"{t} ({c})" for t, c in by_type.items()),
        ]

        return " ".join(parts)

    def _build_thesis(self, claims: List[ResearchClaim]) -> str:
        """Build thesis statement."""
        if not claims:
            return "No clear thesis could be established."

        top_claim = max(claims, key=lambda c: c.confidence)
        return f"Based on the research, the central finding is: {top_claim.text}"

    def _build_supporting_evidence(self, claims: List[ResearchClaim], evidence: List[ResearchEvidence]) -> str:
        """Build supporting evidence section."""
        if not evidence:
            return "Limited supporting evidence available."

        verified_claims = [c for c in claims if c.status == "verified"]
        parts = [f"Found {len(verified_claims)} verified claims supported by {len(evidence)} pieces of evidence:"]

        for claim in verified_claims[:5]:
            parts.append(f"- {claim.text}")

        return "\n".join(parts)

    def _build_counter_evidence(self, claims: List[ResearchClaim], evidence: List[ResearchEvidence]) -> str:
        """Build counter-evidence section."""
        conflicting = [c for c in claims if c.status == "conflicting"]
        rejected = [c for c in claims if c.status == "rejected"]

        if not conflicting and not rejected:
            return "No significant counter-evidence found."

        parts = ["Some claims have conflicting evidence or were not supported:"]

        for claim in (conflicting + rejected)[:5]:
            parts.append(f"- {claim.text} (Status: {claim.status})")

        return "\n".join(parts)

    def _build_conclusion(self, claims: List[ResearchClaim]) -> str:
        """Build conclusion."""
        verified = sum(1 for c in claims if c.status == "verified")
        total = len(claims)

        if verified / total > 0.7:
            return "The research strongly supports the main findings with high confidence."
        elif verified / total > 0.4:
            return "The research provides moderate support for the findings, with some areas requiring further investigation."
        else:
            return "The research findings are preliminary and require further validation."

    def _generate_executive_summary(
        self,
        query: str,
        research_type: str,
        sections: List[SynthesizedSection],
        verification_results: List[Dict[str, Any]],
    ) -> str:
        """Generate executive summary."""
        total_claims = sum(len(section.supporting_claims) for section in sections)
        verified = sum(1 for v in verification_results if v.get("status") == "verified")
        likely = sum(1 for v in verification_results if v.get("status") == "likely")
        conflicting = sum(1 for v in verification_results if v.get("status") == "conflicting")

        parts = [
            f"This research investigated: '{query}'",
            f"Research type: {research_type.replace('_', ' ').title()}",
            f"Analyzed {total_claims} key claims from multiple sources.",
        ]

        if verified > 0:
            parts.append(f"{verified} claims were verified with high confidence.")
        if likely > 0:
            parts.append(f"{likely} claims are likely true based on available evidence.")
        if conflicting > 0:
            parts.append(f"{conflicting} claims have conflicting evidence and require further investigation.")

        # Add top finding
        if sections:
            top_section = max(sections, key=lambda s: s.confidence)
            parts.append(f"Primary finding: {top_section.title} - {top_section.content[:200]}...")

        return " ".join(parts)

    def _extract_key_findings(
        self,
        sections: List[SynthesizedSection],
        verification_results: List[Dict[str, Any]],
    ) -> List[str]:
        """Extract key findings from sections."""
        findings = []

        # From verified claims
        verified_claims = [v for v in verification_results if v.get("status") == "verified"]
        for claim in verified_claims[:5]:
            findings.append(claim.get("claim_text", ""))

        # From section content
        for section in sections[:3]:
            # Extract first sentence of each section
            first_sentence = section.content.split(".")[0]
            if first_sentence and len(first_sentence) > 20:
                findings.append(f"{section.title}: {first_sentence}.")

        return findings[:8]

    def _generate_recommendations(
        self,
        query: str,
        research_type: str,
        sections: List[SynthesizedSection],
        analysis_result: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Generate recommendations."""
        recommendations = []

        # From analysis insights
        if analysis_result:
            insights = analysis_result.get("insights", [])
            for insight in insights:
                if insight.get("actionable") and insight.get("priority") in ["high", "medium"]:
                    recommendations.append(f"{insight.get('title', '')}: {insight.get('description', '')}")

        # From gaps
        if analysis_result:
            gaps = analysis_result.get("gaps", [])
            for gap in gaps[:3]:
                recommendations.append(f"Address gap: {gap}")

        # Research-type specific
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

        # General
        recommendations.extend([
            "Regularly update this research as market conditions change",
            "Cross-reference findings with primary sources when possible",
            "Share findings with mentors or peers for validation",
        ])

        # Deduplicate
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
        sources: List[SourceMetadata],
    ) -> str:
        """Describe research methodology."""
        parts = [
            "This research employed a multi-agent approach with specialized agents for web search, "
            "news monitoring, job market analysis, company research, and academic literature review.",
        ]

        source_types = set(s.source_type for s in sources)
        parts.append(f"Sources included: {', '.join(t.value for t in source_types)}.")

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
        verification_results: List[Dict[str, Any]],
        sources: List[SourceMetadata],
    ) -> List[str]:
        """Identify research limitations."""
        limitations = []

        if len(sources) < 5:
            limitations.append("Limited number of sources may not capture full picture")

        source_types = set(s.source_type for s in sources)
        if len(source_types) < 3:
            limitations.append("Limited source type diversity may introduce bias")

        # Recency
        recent_count = 0
        for s in sources:
            if s.published_date:
                try:
                    from datetime import datetime, timezone
                    pub_date = s.published_date
                    if pub_date.tzinfo is None:
                        pub_date = pub_date.replace(tzinfo=timezone.utc)
                    if (datetime.now(timezone.utc) - pub_date).days < 90:
                        recent_count += 1
                except Exception:
                    pass

        if sources and recent_count < len(sources) * 0.3:
            limitations.append("Many sources are older than 90 days; findings may be outdated")

        uncertain = sum(1 for v in verification_results if v.get("status") == "uncertain")
        if uncertain > len(verification_results) * 0.3:
            limitations.append("High proportion of uncertain claims limits confidence")

        conflicting = sum(1 for v in verification_results if v.get("status") == "conflicting")
        if conflicting > 0:
            limitations.append(f"{conflicting} claims have conflicting evidence requiring manual review")

        limitations.extend([
            "Research based on publicly available sources; proprietary data not included",
            "Automated extraction may miss nuanced context",
            "Salary and market data may vary by location and company size",
            "Findings represent snapshot in time; continuous monitoring recommended",
        ])

        return limitations[:7]

    def _calculate_overall_confidence(self, verification_results: List[Dict[str, Any]]) -> float:
        """Calculate overall research confidence."""
        if not verification_results:
            return 0.0

        verified = sum(1 for v in verification_results if v.get("status") == "verified")
        likely = sum(1 for v in verification_results if v.get("status") == "likely")
        total = len(verification_results)

        confidence = (verified * 1.0 + likely * 0.7) / total
        return round(confidence, 2)

    def _get_evidence_refs(self, claims: List[ResearchClaim], evidence: List[ResearchEvidence]) -> List[str]:
        """Get evidence reference IDs for claims."""
        refs = []
        for claim in claims:
            claim_evidence = [e for e in evidence if e.claim_id == claim.id]
            refs.extend([e.id for e in claim_evidence])
        return refs

    def _count_words(self, *texts: str) -> int:
        """Count total words."""
        count = 0
        for text in texts:
            if text:
                if isinstance(text, list):
                    for t in text:
                        count += len(t.split())
                else:
                    count += len(text.split())
        return count


import re