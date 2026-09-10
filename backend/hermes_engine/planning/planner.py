"""
Planner - Task decomposition and execution planning.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from ..core.task import HermesTask, TaskType, TaskPriority
from ..core.result import PlanResult
from .execution_plan import ExecutionPlan, PlanStep, PlanStatus
from .task_decomposer import TaskDecomposer


class TaskPlanner:
    """
    Decomposes high-level goals into executable task plans.
    """

    def __init__(self):
        self._templates: Dict[str, Dict[str, Any]] = {}

    def create_plan(
        self,
        goal: str,
        constraints: Optional[Dict[str, Any]] = None,
        available_agents: Optional[List[str]] = None,
    ) -> PlanResult:
        """
        Create an execution plan for a goal.
        
        Args:
            goal: High-level goal to achieve
            constraints: Limitations and requirements
            available_agents: List of available agent IDs
            
        Returns:
            PlanResult with subtasks and assignments
        """
        subtasks = []
        agents = available_agents or []

        for i, agent_id in enumerate(agents):
            subtasks.append({
                "id": f"subtask_{i}",
                "description": f"Step {i + 1} for: {goal}",
                "assigned_agent": agent_id,
                "depends_on": [f"subtask_{j}"] if i > 0 else [],
                "status": "pending",
            })

        return PlanResult(
            goal=goal,
            subtasks=subtasks,
            constraints=constraints or {},
            estimated_steps=len(subtasks),
        )

    def replan(
        self,
        original_plan: PlanResult,
        completed_subtasks: List[str],
        failure_info: Optional[Dict[str, Any]] = None,
    ) -> PlanResult:
        """
        Revise a plan based on progress and failures.
        """
        remaining = [
            st for st in original_plan.subtasks
            if st["id"] not in completed_subtasks
        ]

        if failure_info:
            for st in remaining:
                if st["id"] == failure_info.get("failed_subtask_id"):
                    st["status"] = "needs_revision"
                    st["error"] = failure_info.get("error", "")

        return PlanResult(
            goal=original_plan.goal,
            subtasks=remaining,
            constraints=original_plan.constraints,
            estimated_steps=len(remaining),
        )

    def add_template(self, name: str, template: Dict[str, Any]) -> None:
        """Add a plan template."""
        self._templates[name] = template

    def get_template(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a plan template by name."""
        return self._templates.get(name)

    def build_execution_plan(
        self,
        goal: str,
        subtasks: Optional[List[HermesTask]] = None,
        agent_ids: Optional[List[str]] = None,
    ) -> ExecutionPlan:
        """
        Build a dependency-aware ExecutionPlan for a goal.

        Uses the provided subtasks, or decomposes the goal via
        TaskDecomposer when none are given. Steps run in order: each
        step depends on the previous one (plus any declared dependency
        that matches a known step), so ExecutionPlan.get_next_step()
        yields a valid execution order.
        """
        import uuid

        if subtasks is None:
            subtasks = TaskDecomposer().decompose(goal)

        plan = ExecutionPlan(
            id=f"plan_{uuid.uuid4().hex[:8]}",
            goal=goal,
            status=PlanStatus.ACTIVE,
        )
        known_ids = {t.id for t in subtasks}
        previous_id: Optional[str] = None
        agents = agent_ids or []

        for i, subtask in enumerate(subtasks):
            depends_on = [d for d in (subtask.dependencies or []) if d in known_ids]
            if previous_id is not None and previous_id not in depends_on:
                depends_on = [previous_id] + depends_on
            plan.add_step(PlanStep(
                id=subtask.id,
                description=subtask.description or f"Step {i + 1} for: {goal}",
                agent_id=subtask.assigned_agent or (agents[i % len(agents)] if agents else None),
                depends_on=depends_on,
            ))
            previous_id = subtask.id

        return plan
