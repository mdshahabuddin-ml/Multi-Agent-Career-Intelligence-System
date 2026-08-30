from typing import List, Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum as PyEnum
from abc import ABC, abstractmethod
from collections import defaultdict
import uuid
import asyncio
import logging

from backend.agents.communication.protocol import (
    AgentMessage, MessageType, MessagePriority, message_bus,
    create_request, create_response, create_notification
)
from backend.agents.memory.shared_memory import (
    shared_memory, MemoryScope, MemoryType
)
from backend.agents.orchestration.workflow_orchestrator import (
    BaseOrchestrator, SequentialOrchestrator, ParallelOrchestrator,
    HumanInTheLoopOrchestrator, Workflow, WorkflowStep, WorkflowExecution,
    AgentRole, OrchestrationState, create_research_workflow, create_job_matching_workflow
)
from backend.agents.human_loop.intervention import (
    HumanLoopManager, HumanIntervention, InterventionType, InterventionPriority,
    HumanInterface, console_interface, human_loop_manager
)

logger = logging.getLogger(__name__)


class AgentCapability(str, PyEnum):
    """Agent capabilities for routing."""
    RESEARCH = "research"
    ANALYSIS = "analysis"
    SYNTHESIS = "synthesis"
    WRITING = "writing"
    CODING = "coding"
    DATA_PROCESSING = "data_processing"
    WEB_SEARCH = "web_search"
    FACT_CHECKING = "fact_checking"
    MATCHING = "matching"
    RANKING = "ranking"
    PLANNING = "planning"
    COORDINATION = "coordination"
    REVIEW = "review"
    EXTRACTION = "extraction"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    agent_id: str
    name: str
    role: AgentRole
    capabilities: List[AgentCapability]
    description: str = ""
    max_concurrent_tasks: int = 3
    timeout_seconds: int = 300
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentStatus:
    """Current status of an agent."""
    agent_id: str
    status: str = "idle"  # idle, busy, error, offline
    current_task: Optional[str] = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    last_active: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """Abstract base class for all agents."""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.agent_id = config.agent_id
        self.status = AgentStatus(agent_id=config.agent_id)
        self._task_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        
        # Register with message bus
        message_bus.register_agent(self.agent_id)
        
        # Subscribe to relevant messages
        message_bus.subscribe(self.agent_id, MessageType.REQUEST, self._handle_request)
        message_bus.subscribe(self.agent_id, MessageType.HANDOFF, self._handle_handoff)
        message_bus.subscribe(self.agent_id, MessageType.DELEGATE, self._handle_delegate)
    
    @abstractmethod
    async def execute_task(self, task: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task - implemented by subclasses."""
        pass
    
    async def start(self):
        """Start the agent worker."""
        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info(f"Agent {self.agent_id} started")
    
    async def stop(self):
        """Stop the agent worker."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info(f"Agent {self.agent_id} stopped")
    
    async def _worker_loop(self):
        """Main worker loop."""
        while self._running:
            try:
                task_data = await asyncio.wait_for(self._task_queue.get(), timeout=1.0)
                await self._process_task(task_data)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Agent {self.agent_id} worker error: {e}")
    
    async def _process_task(self, task_data: Dict[str, Any]):
        """Process a single task."""
        task_id = task_data.get("task_id", str(uuid.uuid4()))
        task = task_data.get("task", "")
        input_data = task_data.get("input", {})
        
        self.status.status = "busy"
        self.status.current_task = task_id
        self.status.last_active = datetime.utcnow()
        
        try:
            logger.info(f"Agent {self.agent_id} processing task: {task}")
            result = await self.execute_task(task, input_data)
            
            # Send response if needed
            response_to = task_data.get("response_to")
            if response_to:
                response = create_response(
                    sender_id=self.agent_id,
                    original_message=AgentMessage(message_id=response_to, sender_id=""),
                    payload={"success": True, "result": result},
                )
                # Note: In real implementation, we'd need the original message
                await self._send_result(task_data.get("conversation_id", ""), result)
            
            self.status.tasks_completed += 1
            
        except Exception as e:
            self.status.tasks_failed += 1
            logger.error(f"Agent {self.agent_id} task {task_id} failed: {e}")
            
            if response_to := task_data.get("response_to"):
                await self._send_error(task_data.get("conversation_id", ""), str(e))
        
        finally:
            self.status.status = "idle"
            self.status.current_task = None
    
    async def _handle_request(self, message: AgentMessage):
        """Handle incoming request message."""
        await self._task_queue.put({
            "task_id": message.message_id,
            "task": message.payload.get("action", ""),
            "input": message.payload,
            "conversation_id": message.conversation_id,
            "response_to": message.message_id,
        })
    
    async def _handle_handoff(self, message: AgentMessage):
        """Handle handoff message."""
        await self._task_queue.put({
            "task_id": message.message_id,
            "task": message.payload.get("task", ""),
            "input": message.payload.get("context", {}),
            "conversation_id": message.conversation_id,
            "response_to": message.message_id,
        })
    
    async def _handle_delegate(self, message: AgentMessage):
        """Handle delegate message."""
        await self._handle_request(message)
    
    async def _send_result(self, conversation_id: str, result: Any):
        """Send result back to orchestrator."""
        notification = create_notification(
            sender_id=self.agent_id,
            event="task_completed",
            payload={"result": result, "conversation_id": conversation_id},
        )
        await message_bus.send(notification)
    
    async def _send_error(self, conversation_id: str, error: str):
        """Send error back to orchestrator."""
        notification = create_notification(
            sender_id=self.agent_id,
            event="task_failed",
            payload={"error": error, "conversation_id": conversation_id},
        )
        await message_bus.send(notification)
    
    async def delegate(
        self,
        recipient_id: str,
        task: str,
        input_data: Dict[str, Any],
        conversation_id: Optional[str] = None,
    ) -> Any:
        """Delegate task to another agent."""
        handoff = create_handoff(
            sender_id=self.agent_id,
            recipient_id=recipient_id,
            task=task,
            context=input_data,
            conversation_id=conversation_id,
        )
        await message_bus.send(handoff)
        
        # Wait for response
        future = asyncio.Future()
        
        async def handler(message: AgentMessage):
            if message.conversation_id == conversation_id and message.response_to == handoff.message_id:
                if not future.done():
                    if message.payload.get("success", True):
                        future.set_result(message.payload.get("result"))
                    else:
                        future.set_exception(Exception(message.payload.get("error", "Delegation failed")))
        
        message_bus.subscribe(self.agent_id, MessageType.RESPONSE, handler)
        
        try:
            return await asyncio.wait_for(future, timeout=300)
        finally:
            pass  # Unsubscribe in production
    
    async def remember(self, key: str, value: Any, scope: MemoryScope = MemoryScope.PRIVATE, **kwargs):
        """Store in shared memory."""
        return await shared_memory.store(self.agent_id, key, value, scope, **kwargs)
    
    async def recall(self, key: str, **kwargs):
        """Recall from shared memory."""
        return await shared_memory.get(self.agent_id, key, **kwargs)
    
    async def search_memory(self, query: str = "", **kwargs):
        """Search shared memory."""
        return await shared_memory.search(self.agent_id, query, **kwargs)


class AgentRegistry:
    """Registry for managing all agents."""
    
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._configs: Dict[str, AgentConfig] = {}
        self._orchestrators: Dict[str, BaseOrchestrator] = {}
        self._capability_index: Dict[AgentCapability, Set[str]] = defaultdict(set)
    
    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent."""
        self._agents[agent.agent_id] = agent
        self._configs[agent.agent_id] = agent.config
        
        for cap in agent.config.capabilities:
            self._capability_index[cap].add(agent.agent_id)
        
        logger.info(f"Registered agent: {agent.agent_id} ({agent.config.name})")
    
    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent."""
        if agent_id in self._agents:
            agent = self._agents.pop(agent_id)
            config = self._configs.pop(agent_id)
            
            for cap in config.capabilities:
                self._capability_index[cap].discard(agent_id)
            
            logger.info(f"Unregistered agent: {agent_id}")
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get agent by ID."""
        return self._agents.get(agent_id)
    
    def find_agents_by_capability(self, capability: AgentCapability) -> List[BaseAgent]:
        """Find agents with a capability."""
        agent_ids = self._capability_index.get(capability, set())
        return [self._agents[aid] for aid in agent_ids if aid in self._agents]
    
    def find_agents_by_role(self, role: AgentRole) -> List[BaseAgent]:
        """Find agents by role."""
        return [a for a in self._agents.values() if a.config.role == role]
    
    def get_best_agent(self, capability: AgentCapability, role: Optional[AgentRole] = None) -> Optional[BaseAgent]:
        """Get the best available agent for a capability."""
        candidates = self.find_agents_by_capability(capability)
        
        if role:
            candidates = [a for a in candidates if a.config.role == role]
        
        # Filter available agents
        available = [a for a in candidates if a.status.status == "idle"]
        
        if not available:
            return None
        
        # Return least busy agent
        return min(available, key=lambda a: a.status.tasks_completed - a.status.tasks_failed)
    
    def register_orchestrator(self, orchestrator: BaseOrchestrator) -> None:
        """Register an orchestrator."""
        self._orchestrators[orchestrator.orchestrator_id] = orchestrator
        logger.info(f"Registered orchestrator: {orchestrator.orchestrator_id}")
    
    def get_orchestrator(self, orchestrator_id: str) -> Optional[BaseOrchestrator]:
        """Get orchestrator by ID."""
        return self._orchestrators.get(orchestrator_id)
    
    def get_all_agents(self) -> List[BaseAgent]:
        """Get all registered agents."""
        return list(self._agents.values())
    
    def get_status(self) -> Dict[str, Any]:
        """Get registry status."""
        return {
            "total_agents": len(self._agents),
            "by_role": {
                role.value: len([a for a in self._agents.values() if a.config.role == role])
                for role in AgentRole
            },
            "by_capability": {
                cap.value: len(ids) for cap, ids in self._capability_index.items()
            },
            "agent_statuses": {
                aid: {
                    "status": a.status.status,
                    "current_task": a.status.current_task,
                    "tasks_completed": a.status.tasks_completed,
                    "tasks_failed": a.status.tasks_failed,
                }
                for aid, a in self._agents.items()
            },
        }


# Global agent registry
agent_registry = AgentRegistry()


async def initialize_default_agents():
    """Initialize default agents for the system."""
    # This would be called at startup to create standard agents
    # Actual agent implementations would be imported and registered here
    pass


def create_agent_config(
    agent_id: str,
    name: str,
    role: AgentRole,
    capabilities: List[AgentCapability],
    **kwargs
) -> AgentConfig:
    """Helper to create agent config."""
    return AgentConfig(
        agent_id=agent_id,
        name=name,
        role=role,
        capabilities=capabilities,
        **kwargs
    )