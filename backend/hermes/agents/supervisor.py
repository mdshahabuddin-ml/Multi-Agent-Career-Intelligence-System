"""
Supervisor Agent - orchestrates and monitors sub-agent execution.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from ..core.agent import Agent, AgentConfig
from ..core.task import Task, TaskResult, TaskStatus


class SupervisorAgent(Agent):
    """
    An agent that coordinates the work of multiple sub-agents.

    The Supervisor assigns tasks, monitors progress, handles failures,
    and aggregates results from sub-agents.
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                name="supervisor",
                description="Coordinates sub-agent execution and monitors progress",
                model="gpt-4",
                tools=["task_assignment", "progress_tracking", "error_handling"],
                system_prompt=(
                    "You are a supervisor agent. Coordinate the work of "
                    "multiple sub-agents to achieve complex goals efficiently."
                ),
            )
        super().__init__(config)
        self._sub_agents: Dict[str, Agent] = {}
        self._task_assignments: Dict[str, str] = {}  # task_id -> agent_id
        self._results: Dict[str, TaskResult] = {}

    def register_sub_agent(self, agent: Agent) -> None:
        """Register a sub-agent for task delegation."""
        self._sub_agents[agent.id] = agent
        self.state.add_to_context(
            f"sub_agent_{agent.id}", agent.name
        )

    def unregister_sub_agent(self, agent_id: str) -> bool:
        """Remove a sub-agent from the pool."""
        return self._sub_agents.pop(agent_id, None) is not None

    def get_sub_agents(self) -> List[Dict[str, Any]]:
        """Get info about all registered sub-agents."""
        return [
            {
                "id": agent.id,
                "name": agent.name,
                "is_busy": agent.is_busy,
            }
            for agent in self._sub_agents.values()
        ]

    async def _process_task(self, task: Task) -> TaskResult:
        """Process a supervision task by delegating to sub-agents."""
        subtasks = task.input_data.get("subtasks", [])

        if not subtasks:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="No subtasks provided for supervision",
            )

        results = []
        for subtask_def in subtasks:
            agent_id = subtask_def.get("assigned_agent")
            agent = self._sub_agents.get(agent_id)

            if agent is None:
                results.append({
                    "subtask_id": subtask_def.get("id"),
                    "success": False,
                    "error": f"Agent {agent_id} not found",
                })
                continue

            sub_task = Task(
                type=subtask_def.get("type", "subtask"),
                description=subtask_def.get("description", ""),
                input_data=subtask_def.get("input_data", {}),
            )

            self._task_assignments[sub_task.id] = agent_id
            result = await agent.execute(sub_task)
            self._results[sub_task.id] = result
            results.append(result.to_dict())

        all_success = all(r.get("success", False) for r in results)

        return TaskResult(
            task_id=task.id,
            success=all_success,
            output={"subtask_results": results},
            metadata={"subtask_count": len(results)},
        )

    async def execute_parallel(
        self, tasks: List[Task]
    ) -> List[TaskResult]:
        """Execute multiple tasks in parallel across available agents."""
        available = [
            agent for agent in self._sub_agents.values()
            if not agent.is_busy
        ]

        if not available:
            return [
                TaskResult(
                    task_id=t.id,
                    success=False,
                    error="No available sub-agents",
                )
                for t in tasks
            ]

        coros = []
        for task in tasks:
            agent = available[task.priority % len(available)]
            coros.append(agent.execute(task))

        return list(await asyncio.gather(*coros, return_exceptions=False))

    def get_progress(self) -> Dict[str, Any]:
        """Get the current progress of supervised tasks."""
        total = len(self._results)
        completed = sum(
            1 for r in self._results.values()
            if r.success
        )
        failed = sum(
            1 for r in self._results.values()
            if not r.success
        )
        return {
            "total_tasks": total,
            "completed": completed,
            "failed": failed,
            "in_progress": len(self._task_assignments) - total,
        }
