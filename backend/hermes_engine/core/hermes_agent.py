"""
Core Hermes Agent - Production-grade agent implementation.
"""

from __future__ import annotations

import uuid
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from enum import Enum

from .hermes_state import TaskState, state_manager
from .lifecycle import begin as _begin_task
from .lifecycle import succeed as _succeed_task
from .lifecycle import fail as _fail_task
from .lifecycle import cancel as _cancel_task
from .task import HermesTask

logger = logging.getLogger(__name__)


class AgentState(str, Enum):
    """Agent execution states."""
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING_APPROVAL = "waiting_approval"
    ERROR = "offline"
    STOPPED = "stopped"


@dataclass
class HermesAgentConfig:
    """Configuration for a Hermes Agent."""
    agent_id: str = ""
    name: str = "hermes-agent"
    description: str = ""
    model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 4096
    max_retries: int = 3
    timeout_seconds: int = 120
    system_prompt: str = ""
    tools: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.agent_id:
            self.agent_id = str(uuid.uuid4())


class HermesAgent:
    """
    Production-grade Hermes Agent with full lifecycle management.
    
    Integrates with existing agent registry and provides:
    - Task execution with retry logic
    - Memory management
    - Skill execution
    - State persistence
    - Event callbacks
    """

    def __init__(self, config: Optional[HermesAgentConfig] = None):
        self.config = config or HermesAgentConfig()
        self.agent_id = self.config.agent_id
        self.name = self.config.name
        self.state = AgentState.IDLE
        self._created_at = datetime.utcnow()
        self._last_active = datetime.utcnow()
        self._task_count = 0
        self._error_count = 0
        self._callbacks: Dict[str, List[Callable]] = {}
        self._memory: List[Dict[str, Any]] = []
        self._context: Dict[str, Any] = {}
        state_manager.register(self.agent_id)
        logger.info(f"HermesAgent '{self.name}' initialized (id={self.agent_id})")

    @property
    def is_available(self) -> bool:
        """Whether the agent can accept a new task (idle and only idle)."""
        return self.state == AgentState.IDLE

    def on(self, event: str, callback: Callable) -> None:
        """Register an event callback."""
        self._callbacks.setdefault(event, []).append(callback)

    def _emit(self, event: str, *args: Any, **kwargs: Any) -> None:
        """Emit an event to registered callbacks."""
        for cb in self._callbacks.get(event, []):
            try:
                cb(*args, **kwargs)
            except Exception as e:
                logger.error(f"Callback error for event '{event}': {e}")

    async def execute(
        self,
        task: str,
        input_data: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        task_obj: Optional[HermesTask] = None,
    ) -> Dict[str, Any]:
        """
        Execute a task with the agent.

        Args:
            task: Task description or identifier
            input_data: Input data for the task
            context: Additional context
            task_obj: Optional HermesTask whose lifecycle is driven
                (pending -> in_progress -> completed/failed/cancelled).
                When omitted, an internal task record is used.

        Returns:
            Dictionary with execution results
        """
        record = task_obj or HermesTask(description=task, input_data=input_data or {})
        task_id = record.id
        timeout = (task_obj.timeout_seconds if task_obj else None) or self.config.timeout_seconds

        self.state = AgentState.THINKING
        self._last_active = datetime.utcnow()
        self._task_count += 1

        agent_state = state_manager.register(self.agent_id)
        agent_state.update(task_id=task_id, state=TaskState.EXECUTING)
        agent_state.append_history({"event": "task_started", "task_id": task_id})

        logger.info(f"Agent '{self.name}' executing task: {task_id}")
        self._emit("task_started", {"task_id": task_id, "input": input_data})

        try:
            # Merge context
            merged_context = {**(context or {}), **self._context}

            # Drive the task lifecycle with timeout enforcement
            _begin_task(record)
            try:
                if timeout:
                    result = await asyncio.wait_for(
                        self._execute_with_retry(task, input_data or {}, merged_context),
                        timeout=timeout,
                    )
                else:
                    result = await self._execute_with_retry(task, input_data or {}, merged_context)
            except asyncio.TimeoutError as exc:
                _fail_task(record, f"Task timed out after {timeout} seconds")
                raise TimeoutError(f"Task {task_id} timed out after {timeout} seconds") from exc
            _succeed_task(record, result)

            self.state = AgentState.IDLE
            agent_state.update(state=TaskState.COMPLETED)
            agent_state.append_history({"event": "task_completed", "task_id": task_id})
            self._emit("task_completed", {"task_id": task_id, "result": result})
            logger.info(f"Agent '{self.name}' completed task: {task_id}")

            return {
                "success": True,
                "task_id": task_id,
                "result": result,
                "agent_id": self.agent_id,
                "agent_name": self.name,
            }

        except asyncio.CancelledError:
            _cancel_task(record)
            self.state = AgentState.IDLE
            agent_state.update(state=TaskState.CANCELLED)
            agent_state.append_history({"event": "task_cancelled", "task_id": task_id})
            self._emit("task_cancelled", {"task_id": task_id})
            logger.info(f"Agent '{self.name}' cancelled task: {task_id}")
            raise

        except Exception as e:
            try:
                _fail_task(record, str(e))
            except Exception:
                pass
            self.state = AgentState.ERROR
            self._error_count += 1
            agent_state.update(state=TaskState.FAILED)
            agent_state.append_history({"event": "task_failed", "task_id": task_id, "error": str(e)})
            self._emit("task_failed", {"task_id": task_id, "error": str(e)})
            logger.error(f"Agent '{self.name}' failed task {task_id}: {e}")

            return {
                "success": False,
                "task_id": task_id,
                "error": str(e),
                "agent_id": self.agent_id,
                "agent_name": self.name,
            }

    async def _execute_with_retry(
        self,
        task: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        """Execute task with retry logic."""
        last_error = None

        for attempt in range(self.config.max_retries):
            try:
                self.state = AgentState.EXECUTING
                result = await self._process_task(task, input_data, context)
                return result
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Agent '{self.name}' attempt {attempt + 1} failed: {e}"
                )
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        raise last_error or RuntimeError("Max retries exceeded")

    async def _process_task(
        self,
        task: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        """
        Process a task. Override in subclasses for custom behavior.
        
        Default implementation returns a placeholder response.
        """
        # This is where LLM calls would happen in production
        return {
            "task": task,
            "input_data": input_data,
            "status": "processed",
            "timestamp": datetime.utcnow().isoformat(),
        }

    def get_state(self) -> Dict[str, Any]:
        """Get current agent state."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "state": self.state.value,
            "task_count": self._task_count,
            "error_count": self._error_count,
            "created_at": self._created_at.isoformat(),
            "last_active": self._last_active.isoformat(),
            "config": {
                "model": self.config.model,
                "temperature": self.config.temperature,
                "max_retries": self.config.max_retries,
            },
        }

    def set_context(self, key: str, value: Any) -> None:
        """Set a context value."""
        self._context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """Get a context value."""
        return self._context.get(key, default)

    def clear_context(self) -> None:
        """Clear all context."""
        self._context.clear()

    def add_memory(self, entry: Dict[str, Any]) -> None:
        """Add an entry to agent memory."""
        entry.setdefault("timestamp", datetime.utcnow().isoformat())
        self._memory.append(entry)
        # Keep last 100 entries
        if len(self._memory) > 100:
            self._memory = self._memory[-100:]

    def get_memory(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent memory entries."""
        return self._memory[-limit:]

    def __repr__(self) -> str:
        return f"<HermesAgent id={self.agent_id} name={self.name} state={self.state.value}>"
