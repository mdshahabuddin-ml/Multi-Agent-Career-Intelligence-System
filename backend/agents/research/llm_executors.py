import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from backend.agents.research.pipeline_base import PhaseExecutor, PipelinePhase, PipelineState
from backend.agents.research.evidence_ranker import EvidenceRanker, EvidenceRankingResult
from backend.agents.research.verification_agent import VerificationAgent, VerificationResult
from backend.agents.research.analysis_agent import AnalysisAgent, AnalysisResult
from backend.agents.research.synthesis_agent import SynthesisAgent, SynthesisResult
from backend.agents.research.confidence_scorer import ConfidenceScorer, ConfidenceScoreResult
from backend.agents.research.report_agent import ReportAgent, ResearchReport
from backend.agents.research.llm_enhanced import (
    LLMEnhancedOrchestrator,
    LLMVerificationAgent,
    LLMAnalysisAgent,
    LLMSynthesisAgent,
)
from backend.agents.research.evidence_agent import Evidence
from backend.agents.research.source_manager import ManagedSource
from backend.models import Research, ResearchStatus, ResearchType, ResearchSource, ResearchClaim, ResearchEvidence

logger = logging.getLogger(__name__)


class LLMVerificationExecutor(PhaseExecutor):
    """LLM-enhanced claim verification phase."""

    def __init__(self, use_llm: bool = True):
        self.verification_agent = VerificationAgent()
        self.llm_verification = LLMVerificationAgent() if use_llm else None
        self.use_llm = use_llm

    def get_phase(self) -> PipelinePhase:
        return PipelinePhase.VERIFYING

    async def execute(self, state: PipelineState, db_session) -> PipelineState:
        logger.info(f"Research {state.research_id}: Verifying claims (LLM: {self.use_llm})")
        state.phase = PipelinePhase.VERIFYING
        state.progress = 75

        if not state.claims or not state.evidence:
            state.warnings.append("No claims or evidence to verify")
            state.progress = 78
            return state

        evidence_dicts = [e.__dict__ for e in state.evidence]

        if self.use_llm and self.llm_verification:
            try:
                llm_results = await self.llm_verification.verify_claims_with_llm(
                    claims=state.claims,
                    evidence=evidence_dicts,
                )
                # Convert LLM results to VerificationResult objects
                verification_results = []
                for i, r in enumerate(llm_results.results):
                    verification_results.append(VerificationResult(
                        claim_id=r.claim_id if hasattr(r, 'claim_id') else f"claim_{i}",
                        claim_text=r.claim,
                        status=r.status,
                        confidence=r.confidence,
                        supporting_sources=len(r.supporting_evidence) if r.supporting_evidence else 0,
                        conflicting_sources=len(r.conflicting_evidence) if r.conflicting_evidence else 0,
                        verification_details={
                            "reasoning": r.reasoning,
                            "supporting_evidence": r.supporting_evidence,
                            "conflicting_evidence": r.conflicting_evidence,
                        },
                    ))
                logger.info(f"LLM verification completed for {len(verification_results)} claims")
            except Exception as e:
                logger.warning(f"LLM verification failed, falling back to rule-based: {e}")
                self.use_llm = False

        if not self.use_llm:
            verification_results = await self.verification_agent.verify_claims(
                claims=state.claims,
                evidence=evidence_dicts,
            )

        state.verification_results = verification_results
        state.progress = 78
        logger.info(f"Research {state.research_id}: Verified {len(verification_results)} claims")
        return state


class LLMAnalysisExecutor(PhaseExecutor):
    """LLM-enhanced analysis phase."""

    def __init__(self, use_llm: bool = True):
        self.analysis_agent = AnalysisAgent()
        self.llm_analysis = LLMAnalysisAgent() if use_llm else None
        self.use_llm = use_llm

    def get_phase(self) -> PipelinePhase:
        return PipelinePhase.ANALYZING

    async def execute(self, state: PipelineState, db_session) -> PipelineState:
        logger.info(f"Research {state.research_id}: Analyzing findings (LLM: {self.use_llm})")
        state.phase = PipelinePhase.ANALYZING
        state.progress = 80

        if not state.verification_results:
            state.warnings.append("No verification results to analyze")
            state.progress = 82
            return state

        claims_dict = [{"claim_text": c, "claim_id": f"claim_{i}"} for i, c in enumerate(state.claims)]
        evidence_dicts = [e.__dict__ for e in state.evidence]
        verification_dicts = [v.__dict__ for v in state.verification_results]
        source_dicts = [
            {
                "url": s.url,
                "title": s.title,
                "snippet": s.snippet,
                "source_type": s.source_type,
                "credibility": s.credibility,
                "relevance": s.relevance,
                "domain": s.domain,
                "published_date": s.published_date,
            }
            for s in state.source_collection.sources
        ] if state.source_collection else []

        # Run standard analysis first
        analysis_result = await self.analysis_agent.analyze(
            research_id=state.research_id,
            claims=claims_dict,
            evidence=evidence_dicts,
            verification_results=verification_dicts,
            sources=source_dicts,
        )

        # Enhance with LLM insights
        if self.use_llm and self.llm_analysis:
            try:
                llm_insights = await self.llm_analysis.generate_insights_with_llm(
                    query=state.query,
                    claims=claims_dict,
                    evidence=evidence_dicts,
                    sources=source_dicts,
                )
                # Merge LLM insights with standard analysis
                analysis_result.insights = llm_insights.insights + analysis_result.insights
                analysis_result.patterns = llm_insights.patterns + analysis_result.patterns
                analysis_result.gaps = llm_insights.gaps + analysis_result.gaps
                logger.info(f"LLM analysis enhanced with {len(llm_insights.insights)} insights")
            except Exception as e:
                logger.warning(f"LLM analysis failed: {e}")

        state.analysis_result = analysis_result
        state.progress = 82
        logger.info(f"Research {state.research_id}: Analysis complete")
        return state


class LLMSynthesisExecutor(PhaseExecutor):
    """LLM-enhanced synthesis phase."""

    def __init__(self, use_llm: bool = True):
        self.synthesis_agent = SynthesisAgent()
        self.llm_synthesis = LLMSynthesisAgent() if use_llm else None
        self.use_llm = use_llm

    def get_phase(self) -> PipelinePhase:
        return PipelinePhase.SYNTHESIZING

    async def execute(self, state: PipelineState, db_session) -> PipelineState:
        logger.info(f"Research {state.research_id}: Synthesizing findings (LLM: {self.use_llm})")
        state.phase = PipelinePhase.SYNTHESIZING
        state.progress = 85

        if not state.analysis_result or not state.verification_results:
            state.warnings.append("Missing analysis or verification for synthesis")
            state.progress = 87
            return state

        source_dicts = [
            {
                "url": s.url,
                "title": s.title,
                "snippet": s.snippet,
                "source_type": s.source_type,
                "credibility": s.credibility,
                "relevance": s.relevance,
                "domain": s.domain,
                "published_date": s.published_date,
            }
            for s in state.source_collection.sources
        ] if state.source_collection else []

        # Try LLM synthesis first
        if self.use_llm and self.llm_synthesis:
            try:
                llm_result = await self.llm_synthesis.synthesize_with_llm(
                    query=state.query,
                    research_type=state.research_type.value,
                    analysis_result=state.analysis_result.__dict__,
                    verification_results=[v.__dict__ for v in state.verification_results],
                    sources=source_dicts,
                )
                # Convert to SynthesisResult
                synthesis_result = SynthesisResult(
                    research_id=state.research_id,
                    executive_summary=llm_result.get("executive_summary", ""),
                    key_findings=llm_result.get("key_findings", []),
                    detailed_findings=llm_result.get("detailed_findings", []),
                    recommendations=llm_result.get("recommendations", []),
                    methodology=llm_result.get("methodology", ""),
                    limitations=llm_result.get("limitations", []),
                    confidence=llm_result.get("confidence", 0.5),
                )
                logger.info("LLM synthesis completed successfully")
            except Exception as e:
                logger.warning(f"LLM synthesis failed, falling back to rule-based: {e}")
                self.use_llm = False

        if not self.use_llm:
            synthesis_result = await self.synthesis_agent.synthesize(
                research_id=state.research_id,
                query=state.query,
                research_type=state.research_type.value,
                analysis_result=state.analysis_result.__dict__,
                verification_results=[v.__dict__ for v in state.verification_results],
                sources=source_dicts,
            )

        state.synthesis_result = synthesis_result
        state.progress = 87
        logger.info(f"Research {state.research_id}: Synthesis complete")
        return state


def create_llm_enhanced_orchestrator(use_llm: bool = True) -> List[PhaseExecutor]:
    """Create a pipeline with LLM-enhanced executors."""
    from backend.agents.research.orchestrator import (
        DecompositionExecutor, ResearchExecutor, SourceManagementExecutor,
        ClaimExtractionExecutor, EvidenceCollectionExecutor,
        EvidenceRankingExecutor, ConfidenceScoringExecutor, ReportBuildingExecutor,
    )

    executors = [
        DecompositionExecutor(),
        ResearchExecutor(),
        SourceManagementExecutor(),
        ClaimExtractionExecutor(),
        EvidenceCollectionExecutor(),
        EvidenceRankingExecutor(),
        LLMVerificationExecutor(use_llm=use_llm),
        LLMAnalysisExecutor(use_llm=use_llm),
        LLMSynthesisExecutor(use_llm=use_llm),
        ConfidenceScoringExecutor(),
        ReportBuildingExecutor(),
    ]

    return executors