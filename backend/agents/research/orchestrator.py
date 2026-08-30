import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from backend.agents.research.research_supervisor import (
    ResearchSupervisor, ResearchPlanner, ResearchAgent,
    WebResearcher, NewsResearcher, JobMarketResearcher,
    CompanyResearcher, AcademicResearcher, ResearchTask, ResearchPlan
)
from backend.agents.research.task_decomposer import TaskDecomposer, Subtask, SubtaskType, DecompositionResult
from backend.agents.research.source_manager import SourceManager, SourceCollection, ManagedSource
from backend.agents.research.evidence_agent import EvidenceAgent, Evidence
from backend.agents.research.evidence_ranker import EvidenceRanker, EvidenceRankingResult
from backend.agents.research.verification_agent import VerificationAgent, VerificationResult, SourceValidator
from backend.agents.research.analysis_agent import AnalysisAgent, AnalysisResult
from backend.agents.research.synthesis_agent import SynthesisAgent, SynthesisResult
from backend.agents.research.confidence_scorer import ConfidenceScorer, ConfidenceScoreResult
from backend.agents.research.report_agent import ReportAgent, ResearchReport
from backend.agents.research.llm_executors import (
    LLMVerificationExecutor, LLMAnalysisExecutor, LLMSynthesisExecutor,
    create_llm_enhanced_orchestrator,
)
from backend.agents.research.pipeline_base import PipelinePhase, PipelineState, PhaseExecutor
from backend.agents.research.error_handling import (
    ErrorHandler, PipelineError, ErrorSeverity, ErrorCategory,
    NetworkError, SourceError, LLMError, ValidationError, TimeoutError,
    EmptyResultsError, DuplicateError, ConflictError, DatabaseError,
    search_circuit_breaker, llm_circuit_breaker, database_circuit_breaker,
    with_error_handling,
)
from backend.models import Research, ResearchStatus, ResearchType, ResearchSource, ResearchClaim, ResearchEvidence

logger = logging.getLogger(__name__)


class DecompositionExecutor(PhaseExecutor):
    """Execute query decomposition phase."""

    def __init__(self):
        self.decomposer = TaskDecomposer()
        self.error_handler = ErrorHandler(max_retries=2)

    def get_phase(self) -> PipelinePhase:
        return PipelinePhase.DECOMPOSING

    @with_error_handling("DECOMPOSING")
    async def execute(self, state: PipelineState, db_session) -> PipelineState:
        logger.info(f"Research {state.research_id}: Decomposing query")
        state.phase = PipelinePhase.DECOMPOSING
        state.progress = 5

        # Get research from DB for additional params
        research = db_session.query(Research).filter(Research.id == state.research_id).first()
        if not research:
            raise DatabaseError("Research not found", phase="DECOMPOSING")

        decomposition = await self.decomposer.decompose(
            query=state.query,
            research_type=state.research_type.value,
            target_role=research.target_role,
            target_company=research.target_company,
            target_location=research.target_location,
        )

        if not decomposition.subtasks:
            raise EmptyResultsError("No subtasks generated from decomposition", phase="DECOMPOSING")

        state.decomposition = decomposition
        state.progress = 10
        logger.info(f"Research {state.research_id}: Decomposed into {len(decomposition.subtasks)} subtasks")
        return state


class ResearchExecutor(PhaseExecutor):
    """Execute parallel research phase using supervisor's agents."""

    def __init__(self):
        self.supervisor = ResearchSupervisor()
        self.error_handler = ErrorHandler(max_retries=3)

    def get_phase(self) -> PipelinePhase:
        return PipelinePhase.RESEARCHING

    @with_error_handling("RESEARCHING")
    async def execute(self, state: PipelineState, db_session) -> PipelineState:
        logger.info(f"Research {state.research_id}: Executing parallel research")
        state.phase = PipelinePhase.RESEARCHING
        state.progress = 20

        if not state.decomposition or not state.decomposition.subtasks:
            raise EmptyResultsError("No subtasks to execute", phase="RESEARCHING")

        # Group subtasks by type for parallel execution
        subtasks_by_type = {}
        for subtask in state.decomposition.subtasks:
            if subtask.type not in subtasks_by_type:
                subtasks_by_type[subtask.type] = []
            subtasks_by_type[subtask.type].append(subtask)

        # Execute each type in parallel
        all_sources = []
        failed_subtasks = 0
        
        for stype, subtasks in subtasks_by_type.items():
            agent = self.supervisor.agents.get(
                stype.value.replace("_search", "").replace("_analysis", "").replace("_research", "")
            )
            if not agent:
                logger.warning(f"No agent for type: {stype}")
                failed_subtasks += len(subtasks)
                continue

            # Execute subtasks for this type
            for subtask in subtasks:
                try:
                    task = ResearchTask(
                        id=subtask.id,
                        description=subtask.description,
                        agent_type=stype.value.replace("_search", "").replace("_analysis", "").replace("_research", ""),
                        query=subtask.query,
                        priority=subtask.priority,
                    )
                    # Use circuit breaker for search
                    async def execute_with_breaker():
                        return await agent.execute(task)
                    
                    result = await search_circuit_breaker.acall(execute_with_breaker)
                    
                    if result.get("sources"):
                        all_sources.extend(result["sources"])
                    state.subtask_results.append({
                        "subtask_id": subtask.id,
                        "type": stype.value,
                        "query": subtask.query,
                        "result": result,
                    })
                except Exception as e:
                    failed_subtasks += 1
                    logger.error(f"Subtask {subtask.id} failed: {e}")
                    state.subtask_results.append({
                        "subtask_id": subtask.id,
                        "type": stype.value,
                        "error": str(e),
                    })

        if failed_subtasks == len(state.decomposition.subtasks):
            raise SourceError("All subtasks failed", phase="RESEARCHING")

        if not all_sources:
            state.warnings.append("No sources collected from any subtask")

        # Store sources in state for next phase
        state.source_collection = SourceCollection(
            sources=[],
            total_count=len(all_sources),
            unique_domains=0,
            source_types={},
            avg_credibility=0.0,
            avg_relevance=0.0,
            duplicates_removed=0,
        )
        state.metadata = getattr(state, 'metadata', {})
        state.metadata['raw_sources'] = all_sources

        state.progress = 35
        logger.info(f"Research {state.research_id}: Collected {len(all_sources)} raw sources ({failed_subtasks} failed)")
        return state


class SourceManagementExecutor(PhaseExecutor):
    """Execute source management phase."""

    def __init__(self):
        self.source_manager = SourceManager()
        self.error_handler = ErrorHandler(max_retries=2)

    def get_phase(self) -> PipelinePhase:
        return PipelinePhase.MANAGING_SOURCES

    @with_error_handling("MANAGING_SOURCES")
    async def execute(self, state: PipelineState, db_session) -> PipelineState:
        logger.info(f"Research {state.research_id}: Managing sources")
        state.phase = PipelinePhase.MANAGING_SOURCES
        state.progress = 40

        raw_sources = getattr(state, 'metadata', {}).get('raw_sources', [])
        if not raw_sources:
            state.warnings.append("No sources to manage")
            state.source_collection = SourceCollection(
                sources=[], total_count=0, unique_domains=0,
                source_types={}, avg_credibility=0.0, avg_relevance=0.0, duplicates_removed=0
            )
            state.progress = 45
            return state

        collection = await self.source_manager.process_sources(
            sources=raw_sources,
            query=state.query,
            max_sources=50,
        )

        if collection.total_count == 0:
            raise SourceError("No valid sources after deduplication and validation", phase="MANAGING_SOURCES")

        state.source_collection = collection
        state.progress = 45
        logger.info(f"Research {state.research_id}: Managed {collection.total_count} sources ({collection.duplicates_removed} duplicates removed)")
        return state


class ClaimExtractionExecutor(PhaseExecutor):
    """Execute claim extraction phase."""

    def __init__(self):
        self.error_handler = ErrorHandler(max_retries=2)

    def get_phase(self) -> PipelinePhase:
        return PipelinePhase.EXTRACTING_CLAIMS

    @with_error_handling("EXTRACTING_CLAIMS")
    async def execute(self, state: PipelineState, db_session) -> PipelineState:
        logger.info(f"Research {state.research_id}: Extracting claims")
        state.phase = PipelinePhase.EXTRACTING_CLAIMS
        state.progress = 50

        if not state.source_collection or not state.source_collection.sources:
            state.warnings.append("No sources for claim extraction")
            state.progress = 55
            return state

        # Extract claims from sources
        claims = self._extract_claims(state.source_collection.sources)
        
        if not claims:
            raise EmptyResultsError("No claims extracted from sources", phase="EXTRACTING_CLAIMS")
        
        state.claims = claims[:20]  # Limit claims

        state.progress = 55
        logger.info(f"Research {state.research_id}: Extracted {len(state.claims)} claims")
        return state

    def _extract_claims(self, sources: List[ManagedSource]) -> List[str]:
        """Extract key claims from sources."""
        claims = []
        import re

        for source in sources:
            snippet = source.snippet
            if not snippet:
                continue

            sentences = re.split(r'[.!?]+', snippet)
            for sent in sentences:
                sent = sent.strip()
                if len(sent) > 30 and len(sent) < 500:
                    if any(kw in sent.lower() for kw in [
                        "is", "are", "shows", "indicates", "found", "reveals",
                        "reports", "says", "stated", "according to", "study shows",
                        "data shows", "research finds", "analysis reveals"
                    ]):
                        claims.append(sent)

        # Deduplicate
        unique_claims = []
        seen = set()
        for claim in claims:
            key = claim.lower()[:100]
            if key not in seen:
                seen.add(key)
                unique_claims.append(claim)
        return unique_claims


class EvidenceCollectionExecutor(PhaseExecutor):
    """Execute evidence collection phase."""

    def __init__(self):
        self.evidence_agent = EvidenceAgent()
        self.error_handler = ErrorHandler(max_retries=2)

    def get_phase(self) -> PipelinePhase:
        return PipelinePhase.COLLECTING_EVIDENCE

    @with_error_handling("COLLECTING_EVIDENCE")
    async def execute(self, state: PipelineState, db_session) -> PipelineState:
        logger.info(f"Research {state.research_id}: Collecting evidence")
        state.phase = PipelinePhase.COLLECTING_EVIDENCE
        state.progress = 60

        if not state.claims:
            state.warnings.append("No claims to collect evidence for")
            state.progress = 65
            return state

        if not state.source_collection or not state.source_collection.sources:
            state.warnings.append("No sources for evidence collection")
            state.progress = 65
            return state

        # Convert sources to dict format
        source_dicts = [
            {
                "url": s.url,
                "title": s.title,
                "snippet": s.snippet,
                "source_type": s.source_type,
                "credibility": s.credibility,
                "relevance": s.relevance,
                "author": s.author,
                "published_date": s.published_date,
                "metadata": s.metadata,
            }
            for s in state.source_collection.sources
        ]

        evidence = await self.evidence_agent.collect_evidence(source_dicts, state.claims)
        
        if not evidence:
            state.warnings.append("No evidence collected for any claim")

        state.evidence = evidence
        state.progress = 65
        logger.info(f"Research {state.research_id}: Collected {len(evidence)} pieces of evidence")
        return state


class EvidenceRankingExecutor(PhaseExecutor):
    """Execute evidence ranking phase."""

    def __init__(self):
        self.evidence_ranker = EvidenceRanker()
        self.error_handler = ErrorHandler(max_retries=2)

    def get_phase(self) -> PipelinePhase:
        return PipelinePhase.RANKING_EVIDENCE

    @with_error_handling("RANKING_EVIDENCE")
    async def execute(self, state: PipelineState, db_session) -> PipelineState:
        logger.info(f"Research {state.research_id}: Ranking evidence")
        state.phase = PipelinePhase.RANKING_EVIDENCE
        state.progress = 70

        if not state.evidence or not state.claims:
            state.warnings.append("No evidence or claims to rank")
            state.progress = 72
            return state

        # Convert evidence to dict format
        evidence_dicts = [e.__dict__ for e in state.evidence]

        # Convert sources to dict format
        source_dicts = [
            {
                "url": s.url,
                "title": s.title,
                "snippet": s.snippet,
                "source_type": s.source_type,
                "credibility": s.credibility,
                "relevance": s.relevance,
                "domain": s.domain,
                "author": s.author,
                "published_date": s.published_date,
                "metadata": s.metadata,
            }
            for s in state.source_collection.sources
        ]

        ranked = await self.evidence_ranker.rank_evidence(
            evidence_list=evidence_dicts,
            claims=state.claims,
            sources=source_dicts,
            max_per_claim=10,
        )

        state.ranked_evidence = ranked
        state.progress = 72
        logger.info(f"Research {state.research_id}: Ranked evidence for {len(ranked)} claims")
        return state


class VerificationExecutor(PhaseExecutor):
    """Execute claim verification phase."""

    def __init__(self):
        self.verification_agent = VerificationAgent()
        self.source_validator = SourceValidator()
        self.error_handler = ErrorHandler(max_retries=2)

    def get_phase(self) -> PipelinePhase:
        return PipelinePhase.VERIFYING

    @with_error_handling("VERIFYING")
    async def execute(self, state: PipelineState, db_session) -> PipelineState:
        logger.info(f"Research {state.research_id}: Verifying claims")
        state.phase = PipelinePhase.VERIFYING
        state.progress = 75

        if not state.claims or not state.evidence:
            state.warnings.append("No claims or evidence to verify")
            state.progress = 78
            return state

        # Convert evidence to dict format
        evidence_dicts = [e.__dict__ for e in state.evidence]

        verification_results = await self.verification_agent.verify_claims(
            claims=state.claims,
            evidence=evidence_dicts,
        )

        if not verification_results:
            raise ValidationError("Verification produced no results", phase="VERIFYING")

        state.verification_results = verification_results
        state.progress = 78
        logger.info(f"Research {state.research_id}: Verified {len(verification_results)} claims")
        return state


class AnalysisExecutor(PhaseExecutor):
    """Execute analysis phase."""

    def __init__(self):
        self.analysis_agent = AnalysisAgent()
        self.error_handler = ErrorHandler(max_retries=2)

    def get_phase(self) -> PipelinePhase:
        return PipelinePhase.ANALYZING

    @with_error_handling("ANALYZING")
    async def execute(self, state: PipelineState, db_session) -> PipelineState:
        logger.info(f"Research {state.research_id}: Analyzing findings")
        state.phase = PipelinePhase.ANALYZING
        state.progress = 80

        if not state.verification_results:
            state.warnings.append("No verification results to analyze")
            state.progress = 82
            return state

        # Convert to dict formats
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

        analysis_result = await self.analysis_agent.analyze(
            research_id=state.research_id,
            claims=claims_dict,
            evidence=evidence_dicts,
            verification_results=verification_dicts,
            sources=source_dicts,
        )

        if not analysis_result:
            raise ValidationError("Analysis produced no results", phase="ANALYZING")

        state.analysis_result = analysis_result
        state.progress = 82
        logger.info(f"Research {state.research_id}: Analysis complete")
        return state


class SynthesisExecutor(PhaseExecutor):
    """Execute synthesis phase."""

    def __init__(self):
        self.synthesis_agent = SynthesisAgent()
        self.error_handler = ErrorHandler(max_retries=2)

    def get_phase(self) -> PipelinePhase:
        return PipelinePhase.SYNTHESIZING

    @with_error_handling("SYNTHESIZING")
    async def execute(self, state: PipelineState, db_session) -> PipelineState:
        logger.info(f"Research {state.research_id}: Synthesizing findings")
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

        synthesis_result = await self.synthesis_agent.synthesize(
            research_id=state.research_id,
            query=state.query,
            research_type=state.research_type.value,
            analysis_result=state.analysis_result.__dict__,
            verification_results=[v.__dict__ for v in state.verification_results],
            sources=source_dicts,
        )

        if not synthesis_result:
            raise ValidationError("Synthesis produced no results", phase="SYNTHESIZING")

        state.synthesis_result = synthesis_result
        state.progress = 87
        logger.info(f"Research {state.research_id}: Synthesis complete")
        return state


class ConfidenceScoringExecutor(PhaseExecutor):
    """Execute confidence scoring phase."""

    def __init__(self):
        self.confidence_scorer = ConfidenceScorer()
        self.error_handler = ErrorHandler(max_retries=2)

    def get_phase(self) -> PipelinePhase:
        return PipelinePhase.SCORING_CONFIDENCE

    @with_error_handling("SCORING_CONFIDENCE")
    async def execute(self, state: PipelineState, db_session) -> PipelineState:
        logger.info(f"Research {state.research_id}: Scoring confidence")
        state.phase = PipelinePhase.SCORING_CONFIDENCE
        state.progress = 90

        if not state.synthesis_result or not state.verification_results:
            state.warnings.append("Missing synthesis or verification for confidence scoring")
            state.progress = 92
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
                "metadata": s.metadata,
            }
            for s in state.source_collection.sources
        ] if state.source_collection else []

        evidence_dicts = [e.__dict__ for e in state.evidence]
        ranked_dicts = [r.__dict__ for r in state.ranked_evidence] if state.ranked_evidence else None

        confidence_result = await self.confidence_scorer.score_research(
            research_id=state.research_id,
            query=state.query,
            sources=source_dicts,
            evidence=evidence_dicts,
            verification_results=[v.__dict__ for v in state.verification_results],
            analysis_result=state.analysis_result.__dict__ if state.analysis_result else {},
            synthesis_result=state.synthesis_result.__dict__,
            ranked_evidence=ranked_dicts,
        )

        if not confidence_result:
            raise ValidationError("Confidence scoring produced no results", phase="SCORING_CONFIDENCE")

        state.confidence_result = confidence_result
        state.warnings.extend(confidence_result.warnings)
        state.progress = 92
        logger.info(f"Research {state.research_id}: Confidence scored at {confidence_result.confidence_percentage}% ({confidence_result.confidence_level})")
        return state


class ReportBuildingExecutor(PhaseExecutor):
    """Execute report building phase."""

    def __init__(self):
        self.report_agent = ReportAgent()
        self.error_handler = ErrorHandler(max_retries=2)

    def get_phase(self) -> PipelinePhase:
        return PipelinePhase.BUILDING_REPORT

    @with_error_handling("BUILDING_REPORT")
    async def execute(self, state: PipelineState, db_session) -> PipelineState:
        logger.info(f"Research {state.research_id}: Building report")
        state.phase = PipelinePhase.BUILDING_REPORT
        state.progress = 95

        if not state.synthesis_result or not state.verification_results:
            raise ValidationError("Missing synthesis or verification for report", phase="BUILDING_REPORT")

        source_dicts = [
            {
                "url": s.url,
                "title": s.title,
                "snippet": s.snippet,
                "source_type": s.source_type,
                "credibility": s.credibility,
                "relevance": s.relevance,
                "domain": s.domain,
                "author": s.author,
                "published_date": s.published_date,
            }
            for s in state.source_collection.sources
        ] if state.source_collection else []

        report = await self.report_agent.generate_report(
            research_id=state.research_id,
            query=state.query,
            research_type=state.research_type.value,
            synthesis_result=state.synthesis_result.__dict__,
            sources=source_dicts,
            verification_results=[v.__dict__ for v in state.verification_results],
        )

        state.report = report
        state.phase = PipelinePhase.COMPLETED
        state.progress = 100
        state.completed_at = datetime.utcnow()
        logger.info(f"Research {state.research_id}: Report built successfully")
        return state


class ResearchOrchestrator:
    """Orchestrate the full multi-agent research pipeline."""

    def __init__(self, use_llm: bool = True):
        self.name = "research_orchestrator"
        self.use_llm = use_llm
        self.executors: List[PhaseExecutor] = create_llm_enhanced_orchestrator(use_llm=use_llm)
        self.phase_map = {e.get_phase(): e for e in self.executors}

    async def execute_pipeline(
        self,
        research: Research,
        db_session,
        progress_callback: Optional[Callable[[PipelineState], None]] = None,
    ) -> PipelineState:
        """Execute the complete research pipeline."""
        logger.info(f"Starting pipeline for research #{research.id}: {research.query}")

        state = PipelineState(
            research_id=research.id,
            query=research.query,
            research_type=research.research_type,
        )

        try:
            for executor in self.executors:
                if state.phase == PipelinePhase.FAILED:
                    break

                # Execute phase
                state = await executor.execute(state, db_session)

                # Call progress callback
                if progress_callback:
                    try:
                        progress_callback(state)
                    except Exception as e:
                        logger.warning(f"Progress callback failed: {e}")

                # Check for errors
                if state.error:
                    state.phase = PipelinePhase.FAILED
                    break

                # Small delay between phases
                await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"Pipeline failed for research #{research.id}: {e}")
            state.error = str(e)
            state.phase = PipelinePhase.FAILED

        return state

    async def execute_single_phase(
        self,
        phase: PipelinePhase,
        state: PipelineState,
        db_session,
    ) -> PipelineState:
        """Execute a single pipeline phase."""
        executor = self.phase_map.get(phase)
        if not executor:
            state.error = f"No executor for phase: {phase}"
            state.phase = PipelinePhase.FAILED
            return state

        return await executor.execute(state, db_session)

    def get_pipeline_status(self, state: PipelineState) -> Dict[str, Any]:
        """Get current pipeline status."""
        return {
            "research_id": state.research_id,
            "query": state.query,
            "phase": state.phase.value,
            "progress": state.progress,
            "error": state.error,
            "warnings": state.warnings,
            "started_at": state.started_at.isoformat(),
            "completed_at": state.completed_at.isoformat() if state.completed_at else None,
            "stats": {
                "subtasks": len(state.decomposition.subtasks) if state.decomposition else 0,
                "sources": state.source_collection.total_count if state.source_collection else 0,
                "claims": len(state.claims),
                "evidence": len(state.evidence),
                "verified_claims": sum(1 for v in state.verification_results if v.status in ["verified", "likely"]),
                "confidence": state.confidence_result.confidence_percentage if state.confidence_result else 0,
            },
        }