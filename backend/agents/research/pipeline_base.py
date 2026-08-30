import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

if TYPE_CHECKING:
    from backend.agents.research.task_decomposer import DecompositionResult
    from backend.agents.research.source_manager import SourceCollection
    from backend.agents.research.evidence_agent import Evidence
    from backend.agents.research.evidence_ranker import EvidenceRankingResult
    from backend.agents.research.verification_agent import VerificationResult
    from backend.agents.research.analysis_agent import AnalysisResult
    from backend.agents.research.synthesis_agent import SynthesisResult
    from backend.agents.research.confidence_scorer import ConfidenceScoreResult
    from backend.agents.research.report_agent import ResearchReport
    from backend.models import ResearchType

logger = logging.getLogger(__name__)


class PipelinePhase(str, Enum):
    DECOMPOSING = "decomposing"
    RESEARCHING = "researching"
    MANAGING_SOURCES = "managing_sources"
    EXTRACTING_CLAIMS = "extracting_claims"
    COLLECTING_EVIDENCE = "collecting_evidence"
    RANKING_EVIDENCE = "ranking_evidence"
    VERIFYING = "verifying"
    ANALYZING = "analyzing"
    SYNTHESIZING = "synthesizing"
    SCORING_CONFIDENCE = "scoring_confidence"
    BUILDING_REPORT = "building_report"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PipelineState:
    """State of the research pipeline."""
    research_id: int
    query: str
    research_type: "ResearchType"
    phase: PipelinePhase = PipelinePhase.DECOMPOSING
    progress: int = 0

    # Phase outputs
    decomposition: Optional["DecompositionResult"] = None
    subtask_results: List[Dict[str, Any]] = field(default_factory=list)
    source_collection: Optional["SourceCollection"] = None
    claims: List[str] = field(default_factory=list)
    evidence: List["Evidence"] = field(default_factory=list)
    ranked_evidence: List["EvidenceRankingResult"] = field(default_factory=list)
    verification_results: List["VerificationResult"] = field(default_factory=list)
    analysis_result: Optional["AnalysisResult"] = None
    synthesis_result: Optional["SynthesisResult"] = None
    confidence_result: Optional["ConfidenceScoreResult"] = None
    report: Optional["ResearchReport"] = None

    # Errors
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    # Timing
    started_at: datetime = field(default_factory=datetime.utcnow)
    phase_started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class PhaseExecutor(ABC):
    """Base class for pipeline phase executors."""

    @abstractmethod
    async def execute(self, state: PipelineState, db_session) -> PipelineState:
        """Execute the phase."""
        pass

    @abstractmethod
    def get_phase(self) -> PipelinePhase:
        """Get the phase this executor handles."""
        pass