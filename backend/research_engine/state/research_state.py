from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from uuid import uuid4


class ResearchState(str, PyEnum):
    """Research workflow states."""
    CREATED = "created"
    PLANNING = "planning"
    RESEARCHING = "researching"
    COLLECTING_EVIDENCE = "collecting_evidence"
    VERIFYING = "verifying"
    ANALYZING = "analyzing"
    SYNTHESIZING = "synthesizing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ResearchPhase(str, PyEnum):
    """Detailed research phases for progress tracking."""
    INITIALIZING = "initializing"
    TASK_DECOMPOSITION = "task_decomposition"
    SOURCE_DISCOVERY = "source_discovery"
    CONTENT_EXTRACTION = "content_extraction"
    CLAIM_EXTRACTION = "claim_extraction"
    EVIDENCE_COLLECTION = "evidence_collection"
    SOURCE_VALIDATION = "source_validation"
    CLAIM_VERIFICATION = "claim_verification"
    FACT_CHECKING = "fact_checking"
    PATTERN_ANALYSIS = "pattern_analysis"
    TREND_ANALYSIS = "trend_analysis"
    INSIGHT_GENERATION = "insight_generation"
    SYNTHESIS = "synthesis"
    REPORT_GENERATION = "report_generation"
    FINALIZING = "finalizing"


@dataclass
class ResearchContext:
    """Context passed between research phases."""
    research_id: int
    user_id: int
    query: str
    research_type: str
    target_role: Optional[str] = None
    target_company: Optional[str] = None
    target_location: Optional[str] = None
    max_sources: int = 10
    timeout_seconds: int = 300
    started_at: datetime = field(default_factory=datetime.utcnow)
    current_phase: ResearchPhase = ResearchPhase.INITIALIZING
    completed_phases: List[ResearchPhase] = field(default_factory=list)
    phase_start_times: Dict[str, datetime] = field(default_factory=dict)
    phase_end_times: Dict[str, datetime] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def start_phase(self, phase: ResearchPhase):
        """Mark phase as started."""
        self.current_phase = phase
        self.phase_start_times[phase.value] = datetime.utcnow()

    def complete_phase(self, phase: ResearchPhase):
        """Mark phase as completed."""
        if phase not in self.completed_phases:
            self.completed_phases.append(phase)
        self.phase_end_times[phase.value] = datetime.utcnow()

    def get_phase_duration(self, phase: ResearchPhase) -> Optional[float]:
        """Get duration of a phase in seconds."""
        start = self.phase_start_times.get(phase.value)
        end = self.phase_end_times.get(phase.value)
        if start and end:
            return (end - start).total_seconds()
        return None

    def get_total_duration(self) -> float:
        """Get total elapsed time in seconds."""
        return (datetime.utcnow() - self.started_at).total_seconds()

    def add_error(self, error: str):
        """Add an error."""
        self.errors.append(f"[{datetime.utcnow().isoformat()}] {error}")

    def add_warning(self, warning: str):
        """Add a warning."""
        self.warnings.append(f"[{datetime.utcnow().isoformat()}] {warning}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "research_id": self.research_id,
            "user_id": self.user_id,
            "query": self.query,
            "research_type": self.research_type,
            "target_role": self.target_role,
            "target_company": self.target_company,
            "target_location": self.target_location,
            "max_sources": self.max_sources,
            "timeout_seconds": self.timeout_seconds,
            "started_at": self.started_at.isoformat(),
            "current_phase": self.current_phase.value,
            "completed_phases": [p.value for p in self.completed_phases],
            "errors": self.errors,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResearchContext":
        """Create from dictionary."""
        context = cls(
            research_id=data["research_id"],
            user_id=data["user_id"],
            query=data["query"],
            research_type=data["research_type"],
            target_role=data.get("target_role"),
            target_company=data.get("target_company"),
            target_location=data.get("target_location"),
            max_sources=data.get("max_sources", 10),
            timeout_seconds=data.get("timeout_seconds", 300),
        )
        if "started_at" in data:
            context.started_at = datetime.fromisoformat(data["started_at"])
        if "current_phase" in data:
            context.current_phase = ResearchPhase(data["current_phase"])
        if "completed_phases" in data:
            context.completed_phases = [ResearchPhase(p) for p in data["completed_phases"]]
        if "errors" in data:
            context.errors = data["errors"]
        if "warnings" in data:
            context.warnings = data["warnings"]
        if "metadata" in data:
            context.metadata = data["metadata"]
        return context


@dataclass
class ResearchStateSnapshot:
    """Snapshot of research state for checkpointing."""
    context: ResearchContext
    plan: Optional["ResearchPlan"] = None
    sources: List[Dict[str, Any]] = field(default_factory=list)
    claims: List[str] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    verification_results: List[Dict[str, Any]] = field(default_factory=list)
    analysis_result: Optional[Dict[str, Any]] = None
    synthesis_result: Optional[Dict[str, Any]] = None
    report: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context": self.context.to_dict(),
            "plan": self.plan.to_dict() if self.plan else None,
            "sources": self.sources,
            "claims": self.claims,
            "evidence": self.evidence,
            "verification_results": self.verification_results,
            "analysis_result": self.analysis_result,
            "synthesis_result": self.synthesis_result,
            "report": self.report,
            "timestamp": self.timestamp.isoformat(),
        }


class StateManager:
    """Manage research state persistence."""

    def __init__(self, storage_backend: str = "memory"):
        self.storage_backend = storage_backend
        self._states: Dict[int, ResearchStateSnapshot] = {}

    async def save_state(self, snapshot: ResearchStateSnapshot):
        """Save research state snapshot."""
        self._states[snapshot.context.research_id] = snapshot

    async def load_state(self, research_id: int) -> Optional[ResearchStateSnapshot]:
        """Load research state snapshot."""
        return self._states.get(research_id)

    async def delete_state(self, research_id: int):
        """Delete research state."""
        self._states.pop(research_id, None)

    async def list_states(self) -> List[Dict[str, Any]]:
        """List all saved states."""
        return [
            {
                "research_id": rid,
                "query": snap.context.query,
                "phase": snap.context.current_phase.value,
                "timestamp": snap.timestamp.isoformat(),
            }
            for rid, snap in self._states.items()
        ]