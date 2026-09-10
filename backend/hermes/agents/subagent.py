"""
Sub-Agent - a specialized worker agent that executes specific tasks.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from ..core.agent import Agent, AgentConfig
from ..core.task import Task, TaskResult


class SubAgent(Agent):
    """
    A lightweight worker agent designed for specific task types.

    Sub-agents are created by Supervisor agents to execute
    individual subtasks within a larger plan.
    """

    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        handler: Optional[Callable] = None,
    ):
        if config is None:
            config = AgentConfig(
                name="subagent",
                description="Executes assigned subtasks",
                model="gpt-3.5-turbo",
            )
        super().__init__(config)
        self._handler = handler

    async def _process_task(self, task: Task) -> TaskResult:
        """Process a task using the assigned handler or default logic."""
        if self._handler:
            try:
                result = await self._handler(task)
                return TaskResult(
                    task_id=task.id,
                    success=True,
                    output=result,
                )
            except Exception as exc:
                return TaskResult(
                    task_id=task.id,
                    success=False,
                    error=str(exc),
                )

        # Default: pass through the input as output
        return TaskResult(
            task_id=task.id,
            success=True,
            output=task.input_data,
            metadata={"note": "No handler assigned; input passed through"},
        )

    @classmethod
    def create(
        cls,
        name: str,
        handler: Callable,
        model: str = "gpt-3.5-turbo",
        tools: Optional[list] = None,
    ) -> SubAgent:
        """
        Factory method to create a SubAgent with a specific handler.

        Args:
            name: Name for the agent.
            handler: Async callable to handle tasks.
            model: LLM model to use.
            tools: List of tool names.

        Returns:
            A configured SubAgent instance.
        """
        config = AgentConfig(
            name=name,
            description=f"Worker agent: {name}",
            model=model,
            tools=tools or [],
        )
        return cls(config=config, handler=handler)
