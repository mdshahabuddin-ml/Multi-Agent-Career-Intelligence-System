from typing import List, Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum as PyEnum
from abc import ABC, abstractmethod
import uuid
import asyncio
import logging

logger = logging.getLogger(__name__)


class InterventionType(str, PyEnum):
    """Types of human interventions."""
    APPROVAL = "approval"           # Approve/reject a decision
    INPUT = "input"                 # Provide input or clarification
    CORRECTION = "correction"       # Correct agent output
    GUIDANCE = "guidance"           # Provide guidance on approach
    ESCALATION = "escalation"       # Escalate to human expert
    FEEDBACK = "feedback"           # Provide feedback on quality


class InterventionPriority(str, PyEnum):
    """Priority of human intervention."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class InterventionStatus(str, PyEnum):
    """Status of human intervention."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


@dataclass
class HumanIntervention:
    """A request for human intervention."""
    intervention_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    intervention_type: InterventionType = InterventionType.APPROVAL
    priority: InterventionPriority = InterventionPriority.NORMAL
    status: InterventionStatus = InterventionStatus.PENDING
    agent_id: str = ""
    workflow_id: Optional[str] = None
    step_id: Optional[str] = None
    execution_id: Optional[str] = None
    title: str = ""
    description: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    question: str = ""
    options: List[Dict[str, Any]] = field(default_factory=list)  # For approval/choice
    required_fields: List[str] = field(default_factory=list)     # For input
    timeout_seconds: int = 3600  # 1 hour default
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    resolution: Optional[Dict[str, Any]] = None
    assigned_human: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "intervention_id": self.intervention_id,
            "intervention_type": self.intervention_type.value,
            "priority": self.priority.value,
            "status": self.status.value,
            "agent_id": self.agent_id,
            "workflow_id": self.workflow_id,
            "step_id": self.step_id,
            "execution_id": self.execution_id,
            "title": self.title,
            "description": self.description,
            "context": self.context,
            "question": self.question,
            "options": self.options,
            "required_fields": self.required_fields,
            "timeout_seconds": self.timeout_seconds,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution": self.resolution,
            "assigned_human": self.assigned_human,
            "metadata": self.metadata,
        }


@dataclass
class HumanFeedback:
    """Feedback from human on agent output."""
    feedback_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    intervention_id: Optional[str] = None
    agent_id: str = ""
    human_id: str = ""
    rating: Optional[int] = None  # 1-5
    feedback_text: str = ""
    corrections: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class HumanInterface(ABC):
    """Abstract interface for human interaction."""
    
    @abstractmethod
    async def request_intervention(self, intervention: HumanIntervention) -> Dict[str, Any]:
        """Request human intervention and wait for response."""
        pass
    
    @abstractmethod
    async def submit_feedback(self, feedback: HumanFeedback) -> None:
        """Submit human feedback."""
        pass
    
    @abstractmethod
    async def get_pending_interventions(self, human_id: str) -> List[HumanIntervention]:
        """Get pending interventions for a human."""
        pass


class ConsoleHumanInterface(HumanInterface):
    """Console-based human interface for development/testing."""
    
    def __init__(self):
        self._pending: Dict[str, HumanIntervention] = {}
        self._futures: Dict[str, asyncio.Future] = {}
    
    async def request_intervention(self, intervention: HumanIntervention) -> Dict[str, Any]:
        """Request intervention via console."""
        self._pending[intervention.intervention_id] = intervention
        future = asyncio.Future()
        self._futures[intervention.intervention_id] = future
        
        # Print to console
        print(f"\n{'='*60}")
        print(f"HUMAN INTERVENTION REQUIRED")
        print(f"{'='*60}")
        print(f"ID: {intervention.intervention_id}")
        print(f"Type: {intervention.intervention_type.value}")
        print(f"Priority: {intervention.priority.value}")
        print(f"Agent: {intervention.agent_id}")
        print(f"Title: {intervention.title}")
        print(f"Description: {intervention.description}")
        print(f"Question: {intervention.question}")
        if intervention.options:
            print("Options:")
            for i, opt in enumerate(intervention.options):
                print(f"  {i+1}. {opt.get('label', opt)}")
        print(f"{'='*60}\n")
        
        # Set timeout
        async def timeout_handler():
            await asyncio.sleep(intervention.timeout_seconds)
            if not future.done():
                future.set_exception(asyncio.TimeoutError("Intervention timed out"))
        
        asyncio.create_task(timeout_handler())
        
        try:
            result = await future
            return result
        except asyncio.TimeoutError:
            intervention.status = InterventionStatus.TIMED_OUT
            raise
    
    async def submit_feedback(self, feedback: HumanFeedback) -> None:
        """Submit feedback (console just logs)."""
        print(f"\nFeedback received from {feedback.human_id} for agent {feedback.agent_id}")
        print(f"Rating: {feedback.rating}")
        print(f"Text: {feedback.feedback_text}")
        if feedback.corrections:
            print(f"Corrections: {feedback.corrections}")
    
    async def get_pending_interventions(self, human_id: str) -> List[HumanIntervention]:
        """Get pending interventions."""
        return list(self._pending.values())
    
    def resolve_intervention(self, intervention_id: str, resolution: Dict[str, Any]) -> bool:
        """Resolve an intervention (for testing)."""
        if intervention_id in self._futures:
            future = self._futures.pop(intervention_id)
            if not future.done():
                future.set_result(resolution)
            if intervention_id in self._pending:
                intervention = self._pending.pop(intervention_id)
                intervention.status = InterventionStatus.RESOLVED
                intervention.resolution = resolution
                intervention.resolved_at = datetime.utcnow()
            return True
        return False


class WebHumanInterface(HumanInterface):
    """Web-based human interface (placeholder for integration)."""
    
    def __init__(self, api_base: str = "/api/human-loop"):
        self.api_base = api_base
        self._callbacks: Dict[str, Callable] = {}
    
    async def request_intervention(self, intervention: HumanIntervention) -> Dict[str, Any]:
        """Request intervention via web API (would integrate with frontend)."""
        # In production, this would:
        # 1. Store intervention in database
        # 2. Send notification (WebSocket, email, push)
        # 3. Wait for human response via web UI
        # 4. Return resolution
        
        # For now, simulate with a future
        future = asyncio.Future()
        self._callbacks[intervention.intervention_id] = future
        
        # Simulate webhook/notification
        logger.info(f"Web intervention requested: {intervention.intervention_id}")
        
        try:
            return await asyncio.wait_for(future, timeout=intervention.timeout_seconds)
        except asyncio.TimeoutError:
            intervention.status = InterventionStatus.TIMED_OUT
            raise
    
    async def submit_feedback(self, feedback: HumanFeedback) -> None:
        """Submit feedback via web API."""
        logger.info(f"Web feedback submitted: {feedback.feedback_id}")
    
    async def get_pending_interventions(self, human_id: str) -> List[HumanIntervention]:
        """Get pending interventions from database."""
        # Would query database
        return []
    
    def resolve_intervention(self, intervention_id: str, resolution: Dict[str, Any]) -> bool:
        """Resolve intervention from web callback."""
        if intervention_id in self._callbacks:
            future = self._callbacks.pop(intervention_id)
            if not future.done():
                future.set_result(resolution)
            return True
        return False


class HumanLoopManager:
    """Manages human-in-the-loop interventions."""
    
    def __init__(self, interface: HumanInterface):
        self.interface = interface
        self._interventions: Dict[str, HumanIntervention] = {}
        self._human_assignments: Dict[str, List[str]] = {}  # human_id -> intervention_ids
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start background tasks."""
        self._cleanup_task = asyncio.create_task(self._cleanup_timed_out())
    
    async def stop(self):
        """Stop background tasks."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
    
    async def _cleanup_timed_out(self):
        """Clean up timed out interventions."""
        while True:
            try:
                await asyncio.sleep(60)
                now = datetime.utcnow()
                for intervention in list(self._interventions.values()):
                    if (intervention.status == InterventionStatus.PENDING and
                        intervention.created_at + timedelta(seconds=intervention.timeout_seconds) < now):
                        intervention.status = InterventionStatus.TIMED_OUT
                        logger.warning(f"Intervention {intervention.intervention_id} timed out")
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
    
    async def request_intervention(
        self,
        agent_id: str,
        intervention_type: InterventionType,
        title: str,
        description: str,
        question: str,
        priority: InterventionPriority = InterventionPriority.NORMAL,
        context: Optional[Dict[str, Any]] = None,
        options: Optional[List[Dict[str, Any]]] = None,
        required_fields: Optional[List[str]] = None,
        timeout_seconds: int = 3600,
        workflow_id: Optional[str] = None,
        step_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        assigned_human: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Request human intervention."""
        intervention = HumanIntervention(
            intervention_type=intervention_type,
            priority=priority,
            agent_id=agent_id,
            workflow_id=workflow_id,
            step_id=step_id,
            execution_id=execution_id,
            title=title,
            description=description,
            context=context or {},
            question=question,
            options=options or [],
            required_fields=required_fields or [],
            timeout_seconds=timeout_seconds,
            assigned_human=assigned_human,
        )
        
        self._interventions[intervention.intervention_id] = intervention
        
        if assigned_human:
            self._human_assignments.setdefault(assigned_human, []).append(intervention.intervention_id)
        
        logger.info(f"Requested human intervention: {intervention.intervention_id} ({intervention_type.value})")
        
        try:
            resolution = await self.interface.request_intervention(intervention)
            
            intervention.status = InterventionStatus.RESOLVED
            intervention.resolution = resolution
            intervention.resolved_at = datetime.utcnow()
            
            return resolution
            
        except asyncio.TimeoutError:
            intervention.status = InterventionStatus.TIMED_OUT
            raise
        except Exception as e:
            intervention.status = InterventionStatus.CANCELLED
            raise
    
    async def request_approval(
        self,
        agent_id: str,
        title: str,
        description: str,
        question: str,
        options: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Request approval (yes/no or multiple choice)."""
        default_options = [
            {"label": "Approve", "value": "approve", "type": "success"},
            {"label": "Reject", "value": "reject", "type": "danger"},
        ]
        return await self.request_intervention(
            agent_id=agent_id,
            intervention_type=InterventionType.APPROVAL,
            title=title,
            description=description,
            question=question,
            options=options or default_options,
            **kwargs
        )
    
    async def request_input(
        self,
        agent_id: str,
        title: str,
        description: str,
        question: str,
        required_fields: List[str],
        **kwargs
    ) -> Dict[str, Any]:
        """Request structured input from human."""
        return await self.request_intervention(
            agent_id=agent_id,
            intervention_type=InterventionType.INPUT,
            title=title,
            description=description,
            question=question,
            required_fields=required_fields,
            **kwargs
        )
    
    async def request_correction(
        self,
        agent_id: str,
        title: str,
        description: str,
        current_output: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Request correction of agent output."""
        return await self.request_intervention(
            agent_id=agent_id,
            intervention_type=InterventionType.CORRECTION,
            title=title,
            description=description,
            question="Please correct the output below",
            context={"current_output": current_output},
            required_fields=list(current_output.keys()),
            **kwargs
        )
    
    async def request_guidance(
        self,
        agent_id: str,
        title: str,
        description: str,
        question: str,
        options: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Request guidance on approach."""
        return await self.request_intervention(
            agent_id=agent_id,
            intervention_type=InterventionType.GUIDANCE,
            title=title,
            description=description,
            question=question,
            options=options,
            **kwargs
        )
    
    async def submit_feedback(
        self,
        human_id: str,
        agent_id: str,
        feedback_text: str,
        rating: Optional[int] = None,
        corrections: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        intervention_id: Optional[str] = None,
    ) -> HumanFeedback:
        """Submit human feedback."""
        feedback = HumanFeedback(
            intervention_id=intervention_id,
            agent_id=agent_id,
            human_id=human_id,
            rating=rating,
            feedback_text=feedback_text,
            corrections=corrections or {},
            tags=tags or [],
        )
        
        await self.interface.submit_feedback(feedback)
        logger.info(f"Feedback submitted: {feedback.feedback_id}")
        return feedback
    
    async def get_pending_for_human(self, human_id: str) -> List[HumanIntervention]:
        """Get pending interventions for a human."""
        return await self.interface.get_pending_interventions(human_id)
    
    def get_intervention(self, intervention_id: str) -> Optional[HumanIntervention]:
        """Get intervention by ID."""
        return self._interventions.get(intervention_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get intervention statistics."""
        total = len(self._interventions)
        by_status = {}
        by_type = {}
        by_priority = {}
        
        for i in self._interventions.values():
            by_status[i.status.value] = by_status.get(i.status.value, 0) + 1
            by_type[i.intervention_type.value] = by_type.get(i.intervention_type.value, 0) + 1
            by_priority[i.priority.value] = by_priority.get(i.priority.value, 0) + 1
        
        return {
            "total": total,
            "by_status": by_status,
            "by_type": by_type,
            "by_priority": by_priority,
        }


# Global instances
console_interface = ConsoleHumanInterface()
web_interface = WebHumanInterface()
human_loop_manager = HumanLoopManager(console_interface)