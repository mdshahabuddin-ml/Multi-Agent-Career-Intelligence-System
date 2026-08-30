from typing import List, Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum as PyEnum
import uuid
import asyncio
import logging
from abc import ABC, abstractmethod

from backend.agents.communication.protocol import (
    AgentMessage, MessageType, MessagePriority, message_bus,
    create_request, create_response, create_handoff, create_notification
)
from backend.agents.memory.shared_memory import (
    SharedMemory, MemoryEntry, MemoryScope, MemoryType,
    ConversationContext, shared_memory
)

logger = logging.getLogger(__name__)


class OrchestrationState(str, PyEnum):
    """States in orchestration workflow."""
    PENDING = "pending"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REQUIRES_HUMAN = "requires_human"


class AgentRole(str, PyEnum):
    """Roles in orchestration."""
    COORDINATOR = "coordinator"
    WORKER = "worker"
    SPECIALIST = "specialist"
    REVIEWER = "reviewer"
    HUMAN = "human"


@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    step_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    assigned_role: AgentRole = AgentRole.WORKER
    assigned_agent: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)  # step_ids
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 300
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Workflow:
    """A multi-agent workflow definition."""
    workflow_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    steps: List[WorkflowStep] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowExecution:
    """Runtime execution of a workflow."""
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str = ""
    state: OrchestrationState = OrchestrationState.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    current_step: Optional[str] = None
    step_results: Dict[str, Any] = field(default_factory=dict)
    step_states: Dict[str, OrchestrationState] = field(default_factory=dict)
    assigned_agents: Dict[str, str] = field(default_factory=dict)  # step_id -> agent_id
    context: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseOrchestrator(ABC):
    """Abstract base class for workflow orchestrators."""
    
    def __init__(self, orchestrator_id: str):
        self.orchestrator_id = orchestrator_id
        self._workflows: Dict[str, Workflow] = {}
        self._executions: Dict[str, WorkflowExecution] = {}
        self._agent_registry: Dict[str, AgentRole] = {}
        self._message_handlers: Dict[MessageType, Callable] = {}
        self._running = False
    
    def register_workflow(self, workflow: Workflow) -> None:
        """Register a workflow."""
        self._workflows[workflow.workflow_id] = workflow
        logger.info(f"Registered workflow: {workflow.name} ({workflow.workflow_id})")
    
    def register_agent(self, agent_id: str, role: AgentRole) -> None:
        """Register an agent with a role."""
        self._agent_registry[agent_id] = role
        message_bus.register_agent(agent_id)
    
    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent."""
        self._agent_registry.pop(agent_id, None)
        message_bus.unregister_agent(agent_id)
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get workflow by ID."""
        return self._workflows.get(workflow_id)
    
    def list_workflows(self) -> List[Workflow]:
        """List all registered workflows."""
        return list(self._workflows.values())
    
    async def execute_workflow(
        self,
        workflow_id: str,
        initial_context: Dict[str, Any],
        assigned_agents: Optional[Dict[str, str]] = None,
    ) -> WorkflowExecution:
        """Execute a workflow."""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        execution = WorkflowExecution(
            workflow_id=workflow_id,
            state=OrchestrationState.RUNNING,
            started_at=datetime.utcnow(),
            context=initial_context.copy(),
            assigned_agents=assigned_agents or {},
        )
        
        self._executions[execution.execution_id] = execution
        
        try:
            await self._run_workflow(execution, workflow)
            execution.state = OrchestrationState.COMPLETED
            execution.completed_at = datetime.utcnow()
        except Exception as e:
            execution.state = OrchestrationState.FAILED
            execution.error = str(e)
            execution.completed_at = datetime.utcnow()
            logger.error(f"Workflow execution failed: {e}")
        
        return execution
    
    @abstractmethod
    async def _run_workflow(self, execution: WorkflowExecution, workflow: Workflow) -> None:
        """Run the workflow - implemented by subclasses."""
        pass
    
    async def _execute_step(
        self,
        execution: WorkflowExecution,
        step: WorkflowStep,
    ) -> Any:
        """Execute a single workflow step."""
        agent_id = execution.assigned_agents.get(step.step_id) or step.assigned_agent
        
        if not agent_id:
            # Find agent by role
            for aid, role in self._agent_registry.items():
                if role == step.assigned_role:
                    agent_id = aid
                    break
        
        if not agent_id:
            raise ValueError(f"No agent available for step {step.step_id} (role: {step.assigned_role})")
        
        execution.current_step = step.step_id
        execution.step_states[step.step_id] = OrchestrationState.RUNNING
        
        # Prepare input from context and dependencies
        step_input = execution.context.copy()
        for dep_id in step.dependencies:
            if dep_id in execution.step_results:
                step_input[f"dep_{dep_id}"] = execution.step_results[dep_id]
        
        # Send handoff message to agent
        handoff = create_handoff(
            sender_id=self.orchestrator_id,
            recipient_id=agent_id,
            task=step.name,
            context={
                "step_id": step.step_id,
                "execution_id": execution.execution_id,
                "input": step_input,
                "timeout": step.timeout_seconds,
            },
        )
        
        await message_bus.send(handoff)
        
        # Wait for response (with timeout)
        try:
            result = await asyncio.wait_for(
                self._wait_for_step_result(execution.execution_id, step.step_id),
                timeout=step.timeout_seconds,
            )
            
            execution.step_results[step.step_id] = result
            execution.step_states[step.step_id] = OrchestrationState.COMPLETED
            execution.context[f"step_{step.step_id}_result"] = result
            
            return result
            
        except asyncio.TimeoutError:
            execution.step_states[step.step_id] = OrchestrationState.FAILED
            raise TimeoutError(f"Step {step.step_id} timed out after {step.timeout_seconds}s")
    
    async def _wait_for_step_result(
        self,
        execution_id: str,
        step_id: str,
    ) -> Any:
        """Wait for step result from agent."""
        future = asyncio.Future()
        
        async def handler(message: AgentMessage):
            if (message.conversation_id == execution_id and 
                message.metadata.get("step_id") == step_id and
                message.message_type in [MessageType.RESPONSE, MessageType.RESULT]):
                if not future.done():
                    if message.payload.get("success", True):
                        future.set_result(message.payload.get("result"))
                    else:
                        future.set_exception(Exception(message.payload.get("error", "Step failed")))
        
        message_bus.subscribe(self.orchestrator_id, MessageType.RESPONSE, handler)
        message_bus.subscribe(self.orchestrator_id, MessageType.RESULT, handler)
        
        try:
            return await future
        finally:
            # Note: In production, you'd want to properly unsubscribe
            pass


class SequentialOrchestrator(BaseOrchestrator):
    """Orchestrator that executes steps sequentially."""
    
    async def _run_workflow(self, execution: WorkflowExecution, workflow: Workflow) -> None:
        """Run workflow steps in sequence."""
        # Sort steps by dependencies (topological sort)
        sorted_steps = self._topological_sort(workflow.steps)
        
        for step in sorted_steps:
            # Check if dependencies are met
            for dep_id in step.dependencies:
                if dep_id not in execution.step_results:
                    raise ValueError(f"Dependency {dep_id} not satisfied for step {step.step_id}")
            
            await self._execute_step(execution, step)
    
    def _topological_sort(self, steps: List[WorkflowStep]) -> List[WorkflowStep]:
        """Sort steps by dependencies."""
        step_map = {s.step_id: s for s in steps}
        visited = set()
        result = []
        
        def visit(step_id: str):
            if step_id in visited:
                return
            visited.add(step_id)
            step = step_map[step_id]
            for dep_id in step.dependencies:
                visit(dep_id)
            result.append(step)
        
        for step in steps:
            visit(step.step_id)
        
        return result


class ParallelOrchestrator(BaseOrchestrator):
    """Orchestrator that executes independent steps in parallel."""
    
    async def _run_workflow(self, execution: WorkflowExecution, workflow: Workflow) -> None:
        """Run workflow with parallel execution where possible."""
        step_map = {s.step_id: s for s in workflow.steps}
        completed = set()
        execution.step_states = {s.step_id: OrchestrationState.PENDING for s in workflow.steps}
        
        while len(completed) < len(workflow.steps):
            # Find steps that can run (dependencies met)
            ready = [
                s for s in workflow.steps
                if s.step_id not in completed
                and all(d in completed for d in s.dependencies)
            ]
            
            if not ready:
                if len(completed) < len(workflow.steps):
                    raise ValueError("Circular dependency or deadlock detected")
                break
            
            # Execute ready steps in parallel
            tasks = [self._execute_step(execution, step) for step in ready]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for step, result in zip(ready, results):
                if isinstance(result, Exception):
                    raise result
                completed.add(step.step_id)


class HumanInTheLoopOrchestrator(SequentialOrchestrator):
    """Orchestrator with human-in-the-loop checkpoints."""
    
    def __init__(self, orchestrator_id: str, human_interface: Callable):
        super().__init__(orchestrator_id)
        self.human_interface = human_interface
    
    async def _execute_step(self, execution: WorkflowExecution, step: WorkflowStep) -> Any:
        # Check if step requires human review
        if step.metadata.get("requires_human_review", False):
            execution.state = OrchestrationState.REQUIRES_HUMAN
            
            # Request human input
            human_input = await self.human_interface({
                "execution_id": execution.execution_id,
                "step_id": step.step_id,
                "step_name": step.name,
                "context": execution.context,
                "question": step.metadata.get("human_question", "Please review and approve"),
            })
            
            if not human_input.get("approved", False):
                execution.state = OrchestrationState.FAILED
                execution.error = f"Human rejected step {step.step_id}: {human_input.get('reason', 'No reason given')}"
                raise ValueError(execution.error)
            
            execution.state = OrchestrationState.RUNNING
        
        return await super()._execute_step(execution, step)


# Convenience functions for common workflows
def create_research_workflow() -> Workflow:
    """Create a standard research workflow."""
    return Workflow(
        name="Research Workflow",
        description="Multi-agent research with planning, collection, verification, and synthesis",
        steps=[
            WorkflowStep(
                step_id="plan",
                name="Research Planning",
                description="Create research plan from query",
                assigned_role=AgentRole.COORDINATOR,
                input_schema={"query": "str", "max_sources": "int"},
                output_schema={"plan": "dict", "sub_queries": "list"},
            ),
            WorkflowStep(
                step_id="collect",
                name="Evidence Collection",
                description="Collect evidence from multiple sources",
                assigned_role=AgentRole.SPECIALIST,
                dependencies=["plan"],
                input_schema={"plan": "dict", "sub_queries": "list"},
                output_schema={"sources": "list", "evidence": "list"},
            ),
            WorkflowStep(
                step_id="verify",
                name="Fact Verification",
                description="Verify claims against sources",
                assigned_role=AgentRole.REVIEWER,
                dependencies=["collect"],
                input_schema={"sources": "list", "evidence": "list"},
                output_schema={"verified_claims": "list", "confidence_scores": "dict"},
            ),
            WorkflowStep(
                step_id="analyze",
                name="Analysis",
                description="Analyze findings and extract insights",
                assigned_role=AgentRole.SPECIALIST,
                dependencies=["verify"],
                input_schema={"verified_claims": "list", "confidence_scores": "dict"},
                output_schema={"insights": "list", "patterns": "list"},
            ),
            WorkflowStep(
                step_id="synthesize",
                name="Report Synthesis",
                description="Generate final research report",
                assigned_role=AgentRole.COORDINATOR,
                dependencies=["analyze"],
                input_schema={"insights": "list", "patterns": "list", "sources": "list"},
                output_schema={"report": "str", "executive_summary": "str", "recommendations": "list"},
                metadata={"requires_human_review": True, "human_question": "Review and approve final report"},
            ),
        ],
    )


def create_job_matching_workflow() -> Workflow:
    """Create a job matching workflow."""
    return Workflow(
        name="Job Matching Workflow",
        description="Match candidates to jobs with ranking and recommendations",
        steps=[
            WorkflowStep(
                step_id="parse_profile",
                name="Parse Candidate Profile",
                description="Extract skills, experience, preferences from resume/profile",
                assigned_role=AgentRole.SPECIALIST,
                input_schema={"resume": "str", "profile": "dict"},
                output_schema={"skills": "list", "experience": "dict", "preferences": "dict"},
            ),
            WorkflowStep(
                step_id="search_jobs",
                name="Search Jobs",
                description="Search for relevant job postings",
                assigned_role=AgentRole.SPECIALIST,
                dependencies=["parse_profile"],
                input_schema={"skills": "list", "preferences": "dict"},
                output_schema={"jobs": "list"},
            ),
            WorkflowStep(
                step_id="match",
                name="Match Jobs to Candidate",
                description="Score and match jobs to candidate profile",
                assigned_role=AgentRole.SPECIALIST,
                dependencies=["search_jobs", "parse_profile"],
                input_schema={"jobs": "list", "candidate_profile": "dict"},
                output_schema={"matches": "list"},
            ),
            WorkflowStep(
                step_id="rank",
                name="Rank Opportunities",
                description="Rank matched opportunities by fit",
                assigned_role=AgentRole.SPECIALIST,
                dependencies=["match"],
                input_schema={"matches": "list", "candidate_profile": "dict"},
                output_schema={"ranked_opportunities": "list"},
            ),
            WorkflowStep(
                step_id="recommend",
                name="Generate Recommendations",
                description="Generate personalized recommendations with reasoning",
                assigned_role=AgentRole.COORDINATOR,
                dependencies=["rank"],
                input_schema={"ranked_opportunities": "list", "candidate_profile": "dict"},
                output_schema={"recommendations": "list", "reasoning": "dict"},
                metadata={"requires_human_review": False},
            ),
        ],
    )