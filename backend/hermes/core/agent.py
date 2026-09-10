"""
Base Agent class and configuration for the Hermes framework.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Sequence

from .state import AgentState
from .task import Task, TaskResult


@dataclass
class AgentConfig:
    """Configuration for an Agent instance."""

    name: str
    description: str = ""
    model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 4096
    tools: List[str] = field(default_factory=list)
    system_prompt: str = ""
    max_retries: int = 3
    timeout_seconds: int = 120
    metadata: Dict[str, Any] = field(default_factory=dict)


class Agent:
    """
    Base Agent class that all specialized agents inherit from.

    An Agent is an autonomous unit capable of:
    - Receiving and processing tasks
    - Maintaining state across interactions
    - Using tools and skills to accomplish goals
    - Reporting results and requesting assistance
    """

    def __init__(self, config: AgentConfig):
        self.id: str = str(uuid.uuid4())
        self.config = config
        self.state = AgentState(agent_id=self.id)
        self._task_history: List[TaskResult] = []
        self._created_at = datetime.utcnow()
        self._callbacks: Dict[str, List[Callable]] = {}

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def is_busy(self) -> bool:
        return self.state.current_task is not None

    def on(self, event: str, callback: Callable) -> None:
        """Register an event callback."""
        self._callbacks.setdefault(event, []).append(callback)

    def _emit(self, event: str, *args: Any, **kwargs: Any) -> None:
        """Emit an event to registered callbacks."""
        for cb in self._callbacks.get(event, []):
            cb(*args, **kwargs)

    async def execute(self, task: Task) -> TaskResult:
        """
        Execute a task and return the result.

        Subclasses should override `_process_task` to implement
        agent-specific logic.
        """
        self.state.current_task = task
        self._emit("task_started", task)

        try:
            result = await self._process_task(task)
            self._task_history.append(result)
            self._emit("task_completed", result)
            return result
        except Exception as exc:
            result = TaskResult(
                task_id=task.id,
                success=False,
                error=str(exc),
            )
            self._task_history.append(result)
            self._emit("task_failed", result)
            return result
        finally:
            self.state.current_task = None

    async def _process_task(self, task: Task) -> TaskResult:
        """
        Process a task. Must be implemented by subclasses.

        Args:
            task: The task to process.

        Returns:
            TaskResult with the outcome of processing.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _process_task"
        )

    def get_history(self) -> List[TaskResult]:
        """Return the history of task results."""
        return list(self._task_history)

    def get_state(self) -> Dict[str, Any]:
        """Return the current agent state as a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "is_busy": self.is_busy,
            "tasks_completed": len(self._task_history),
            "created_at": self._created_at.isoformat(),
            "state": self.state.to_dict(),
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id} name={self.name}>"
