import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pydantic import BaseModel, Field

from backend.providers import get_provider_manager, LLMMessage, LLMConfig

logger = logging.getLogger(__name__)


class ExecutiveSummary(BaseModel):
    summary: str = Field(description="Concise executive summary")
    key_points: List[str] = Field(description="3-5 key points")


class KeyFindings(BaseModel):
    findings: List[str] = Field(description="List of key findings", min_items=3, max_items=8)


class Recommendations(BaseModel):
    recommendations: List[str] = Field(description="Actionable recommendations", min_items=3, max_items=10)


class AnalysisInsights(BaseModel):
    insights: List[Dict[str, Any]] = Field(description="Actionable insights with type, title, description, priority")
    patterns: List[Dict[str, Any]] = Field(description="Detected patterns")
    gaps: List[str] = Field(description="Research gaps identified")


class VerificationResult(BaseModel):
    claim: str = Field(description="The claim being verified")
    status: str = Field(description="verified, likely, uncertain, conflicting, rejected")
    confidence: float = Field(description="Confidence score 0-1", ge=0, le=1)
    reasoning: str = Field(description="Explanation for the verification decision")
    supporting_evidence: List[str] = Field(description="Evidence supporting the claim")
    conflicting_evidence: List[str] = Field(description="Evidence conflicting with the claim")


class VerificationResults(BaseModel):
    results: List[VerificationResult] = Field(description="Verification results for all claims")


class LLMEvidenceAgent:
    """LLM-enhanced evidence extraction."""

    def __init__(self, provider_manager=None):
        self.provider_manager = provider_manager or get_provider_manager()

    async def extract_evidence_with_llm(
        self,
        claim: str,
        sources: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Use LLM to extract relevant evidence for a claim."""
        source_texts = "\n\n".join([
            f"Source {i+1} ({s.get('source_type', 'web')}): {s.get('title', '')}\n{s.get('snippet', '')}"
            for i, s in enumerate(sources)
        ])

        prompt = f"""Extract evidence from the following sources that is relevant to this claim:

Claim: {claim}

Sources:
{source_texts}

For each relevant piece of evidence, provide:
1. The exact text from the source
2. Which source it came from (index)
3. Whether it supports or contradicts the claim
4. Evidence type (statistic, expert_opinion, direct_quote, case_study, survey_result, report, other)
5. Relevance score (0-1)

Return as JSON array."""

        messages = [
            LLMMessage(role="system", content="You are an expert research analyst. Extract precise evidence from sources."),
            LLMMessage(role="user", content=prompt),
        ]

        config = LLMConfig(temperature=0.1, max_tokens=2000)
        response = await self.provider_manager.generate(messages, config)

        import json
        try:
            return json.loads(response.content)
        except Exception as e:
            logger.warning(f"LLM evidence extraction failed: {e}")
            return []


class LLMAnalysisAgent:
    """LLM-enhanced analysis agent."""

    def __init__(self, provider_manager=None):
        self.provider_manager = provider_manager or get_provider_manager()

    async def generate_insights_with_llm(
        self,
        query: str,
        claims: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
        sources: List[Dict[str, Any]],
    ) -> AnalysisInsights:
        """Use LLM to generate deep insights."""
        verified_claims = [c for c in claims if c.get("status") in ["verified", "likely"]]
        claims_text = "\n".join([f"- {c.get('claim_text', '')}" for c in verified_claims])

        evidence_summary = "\n".join([
            f"- {e.get('evidence_type', 'other')}: {e.get('evidence_text', '')[:200]}"
            for e in evidence[:20]
        ])

        source_types = set(s.get("source_type", "web") for s in sources)
        recency_info = self._get_recency_info(sources)

        prompt = f"""Analyze this research and generate deep insights:

Research Query: {query}

Verified Claims:
{claims_text}

Evidence Summary:
{evidence_summary}

Source Types: {', '.join(source_types)}
Recency: {recency_info}

Generate:
1. 3-5 actionable insights with type, title, description, priority (high/medium/low), actionable (true/false)
2. Key patterns detected in the data
3. Research gaps that need further investigation

Return as structured JSON matching the AnalysisInsights schema."""

        messages = [
            LLMMessage(role="system", content="You are an expert research analyst. Provide deep, actionable insights."),
            LLMMessage(role="user", content=prompt),
        ]

        config = LLMConfig(temperature=0.3, max_tokens=3000)
        return await self.provider_manager.generate_structured(messages, AnalysisInsights, config)

    def _get_recency_info(self, sources: List[Dict[str, Any]]) -> str:
        from datetime import datetime, timezone
        recent = 0
        total = 0
        for s in sources:
            pub_date = s.get("published_date")
            if pub_date:
                total += 1
                try:
                    pub_dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                    if pub_dt.tzinfo is None:
                        pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                    if (datetime.now(timezone.utc) - pub_dt).days < 90:
                        recent += 1
                except Exception:
                    pass
        return f"{recent}/{total} sources from last 90 days" if total else "No date info"


class LLMSynthesisAgent:
    """LLM-enhanced synthesis agent."""

    def __init__(self, provider_manager=None):
        self.provider_manager = provider_manager or get_provider_manager()

    async def synthesize_with_llm(
        self,
        query: str,
        research_type: str,
        analysis_result: Dict[str, Any],
        verification_results: List[Dict[str, Any]],
        sources: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Use LLM to synthesize research into final report."""
        verified = sum(1 for v in verification_results if v.get("status") == "verified")
        likely = sum(1 for v in verification_results if v.get("status") == "likely")
        conflicting = sum(1 for v in verification_results if v.get("status") == "conflicting")
        total = len(verification_results)

        insights = analysis_result.get("insights", [])
        patterns = analysis_result.get("patterns", [])
        gaps = analysis_result.get("gaps", [])

        prompt = f"""Synthesize this research into a comprehensive report:

Research Query: {query}
Research Type: {research_type}

Verification Results:
- Verified: {verified}
- Likely: {likely}
- Conflicting: {conflicting}
- Total Claims: {total}

Key Insights:
{insights}

Patterns:
{patterns}

Gaps:
{gaps}

Source Count: {len(sources)}
Source Types: {', '.join(set(s.get('source_type', 'web') for s in sources))}

Generate:
1. Executive summary (2-3 paragraphs)
2. Key findings (5-8 bullet points)
3. Detailed findings grouped by verification status
4. Actionable recommendations (5-10)
5. Methodology description
6. Limitations (3-5)
7. Overall confidence score (0-1)

Return as structured JSON."""

        messages = [
            LLMMessage(role="system", content="You are an expert research report writer. Create comprehensive, well-structured reports."),
            LLMMessage(role="user", content=prompt),
        ]

        config = LLMConfig(temperature=0.3, max_tokens=4000)

        class SynthesisOutput(BaseModel):
            executive_summary: str
            key_findings: List[str]
            detailed_findings: List[Dict[str, Any]]
            recommendations: List[str]
            methodology: str
            limitations: List[str]
            confidence: float

        return await self.provider_manager.generate_structured(messages, SynthesisOutput, config)


class LLMVerificationAgent:
    """LLM-enhanced claim verification."""

    def __init__(self, provider_manager=None):
        self.provider_manager = provider_manager or get_provider_manager()

    async def verify_claims_with_llm(
        self,
        claims: List[str],
        evidence: List[Dict[str, Any]],
    ) -> VerificationResults:
        """Use LLM to verify claims against evidence."""
        claims_text = "\n".join([f"{i+1}. {c}" for i, c in enumerate(claims)])

        evidence_by_claim = {}
        for e in evidence:
            claim_id = e.get("claim_id", "unknown")
            if claim_id not in evidence_by_claim:
                evidence_by_claim[claim_id] = []
            evidence_by_claim[claim_id].append(e)

        prompt = f"""Verify each claim against the available evidence:

Claims:
{claims_text}

Evidence by Claim:
"""

        for i, claim in enumerate(claims):
            claim_id = f"claim_{i}"
            claim_evidence = evidence_by_claim.get(claim_id, [])
            if claim_evidence:
                prompt += f"\nClaim {i+1}: {claim}\n"
                for ev in claim_evidence:
                    prompt += f"  - [{ev.get('source_type', 'web')}] {ev.get('evidence_text', '')[:300]}\n"
            else:
                prompt += f"\nClaim {i+1}: {claim}\n  No evidence available\n"

        prompt += """
For each claim, determine:
- status: verified (multiple strong sources agree), likely (one strong source), uncertain (insufficient evidence), conflicting (sources disagree), rejected (evidence contradicts)
- confidence: 0-1
- reasoning: brief explanation
- supporting_evidence: list of supporting evidence texts
- conflicting_evidence: list of conflicting evidence texts

Return as structured JSON."""

        messages = [
            LLMMessage(role="system", content="You are an expert fact-checker. Verify claims rigorously against evidence."),
            LLMMessage(role="user", content=prompt),
        ]

        config = LLMConfig(temperature=0.1, max_tokens=3000)
        return await self.provider_manager.generate_structured(messages, VerificationResults, config)


class LLMEnhancedOrchestrator:
    """Orchestrator that uses LLM-enhanced agents where beneficial."""

    def __init__(self, provider_manager=None):
        self.provider_manager = provider_manager or get_provider_manager()
        self.llm_evidence = LLMEvidenceAgent(provider_manager)
        self.llm_analysis = LLMAnalysisAgent(provider_manager)
        self.llm_synthesis = LLMSynthesisAgent(provider_manager)
        self.llm_verification = LLMVerificationAgent(provider_manager)

    async def enhance_evidence_collection(
        self,
        claims: List[str],
        sources: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Enhance evidence collection with LLM."""
        all_evidence = []
        for i, claim in enumerate(claims):
            evidence = await self.llm_evidence.extract_evidence_with_llm(claim, sources)
            for ev in evidence:
                ev["claim_id"] = f"claim_{i}"
            all_evidence.extend(evidence)
        return all_evidence

    async def enhance_analysis(
        self,
        query: str,
        claims: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
        sources: List[Dict[str, Any]],
    ) -> AnalysisInsights:
        """Enhance analysis with LLM."""
        return await self.llm_analysis.generate_insights_with_llm(query, claims, evidence, sources)

    async def enhance_synthesis(
        self,
        query: str,
        research_type: str,
        analysis_result: Dict[str, Any],
        verification_results: List[Dict[str, Any]],
        sources: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Enhance synthesis with LLM."""
        return await self.llm_synthesis.synthesize_with_llm(
            query, research_type, analysis_result, verification_results, sources
        )

    async def enhance_verification(
        self,
        claims: List[str],
        evidence: List[Dict[str, Any]],
    ) -> VerificationResults:
        """Enhance verification with LLM."""
        return await self.llm_verification.verify_claims_with_llm(claims, evidence)