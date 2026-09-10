"""
Planner Agent - decomposes high-level goals into actionable task plans.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..core.agent import Agent, AgentConfig
from ..core.task import Task, TaskResult


class PlannerAgent(Agent):
    """
    An agent specialized in breaking down complex goals into
    structured, executable task plans.

    The Planner Agent analyzes goals, identifies required subtasks,
    determines dependencies, and produces ordered execution plans.
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                name="planner",
                description="Decomposes goals into executable task plans",
                model="gpt-4",
                tools=["task_creation", "dependency_analysis"],
                system_prompt=(
                    "You are a planning agent. Break down complex goals "
                    "into smaller, actionable subtasks with clear dependencies."
                ),
            )
        super().__init__(config)

    async def _process_task(self, task: Task) -> TaskResult:
        """Process a planning task by creating a structured plan."""
        goal = task.input_data.get("goal", task.description)
        constraints = task.input_data.get("constraints", {})
        available_agents = task.input_data.get("available_agents", [])

        plan = await self._create_plan(goal, constraints, available_agents)

        return TaskResult(
            task_id=task.id,
            success=True,
            output=plan,
            metadata={"plan_length": len(plan.get("subtasks", []))},
        )

    async def _create_plan(
        self,
        goal: str,
        constraints: Dict[str, Any],
        available_agents: List[str],
    ) -> Dict[str, Any]:
        """
        Create a structured execution plan for a goal.

        Args:
            goal: The high-level goal to achieve.
            constraints: Limitations and requirements.
            available_agents: List of agent IDs that can execute subtasks.

        Returns:
            A plan dictionary with subtasks, dependencies, and assignments.
        """
        # This is a template implementation.
        # In production, this would use an LLM to analyze the goal
        # and generate an optimal plan.
        subtasks = []
        for i, agent_id in enumerate(available_agents):
            subtasks.append({
                "id": f"subtask_{i}",
                "description": f"Task segment {i + 1} for goal: {goal}",
                "assigned_agent": agent_id,
                "depends_on": [f"subtask_{j}"] if i > 0 else [],
                "status": "pending",
            })

        return {
            "goal": goal,
            "subtasks": subtasks,
            "constraints": constraints,
            "estimated_steps": len(subtasks),
        }

    async def replan(
        self,
        original_plan: Dict[str, Any],
        completed_subtasks: List[str],
        failure_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Revise a plan based on progress and failures.

        Args:
            original_plan: The current plan.
            completed_subtasks: IDs of completed subtasks.
            failure_info: Details about any failures.

        Returns:
            An updated plan.
        """
        remaining = [
            st for st in original_plan.get("subtasks", [])
            if st["id"] not in completed_subtasks
        ]

        if failure_info:
            for st in remaining:
                if st["id"] == failure_info.get("failed_subtask_id"):
                    st["status"] = "needs_revision"
                    st["error"] = failure_info.get("error", "")

        return {
            **original_plan,
            "subtasks": remaining,
            "revised": True,
            "completed": completed_subtasks,
        }
