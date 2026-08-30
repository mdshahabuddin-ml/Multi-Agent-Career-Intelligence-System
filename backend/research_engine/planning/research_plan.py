from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum as PyEnum

from backend.research_engine.state.research_context import ResearchPlan, ResearchTask
from backend.research_engine.planning.task_decomposer import TaskDecomposer, DecompositionStrategy, DecompositionRule


class PlanStatus(str, PyEnum):
    """Status of a research plan."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PlanExecutionState:
    """Execution state of a research plan."""
    plan_id: str
    status: PlanStatus = PlanStatus.DRAFT
    current_task_index: int = 0
    completed_tasks: List[str] = field(default_factory=list)
    failed_tasks: List[str] = field(default_factory=list)
    task_results: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    error: Optional[str] = None


class ResearchPlanManager:
    """Manage research plans and their execution."""

    def __init__(self, decomposer: Optional[TaskDecomposer] = None):
        self.decomposer = decomposer or TaskDecomposer()
        self._plans: Dict[str, ResearchPlan] = {}
        self._executions: Dict[str, PlanExecutionState] = {}

    def create_plan(
        self,
        research_id: int,
        query: str,
        research_type: str,
        max_sources: int = 10,
        timeout_seconds: int = 300,
        target_role: Optional[str] = None,
        target_company: Optional[str] = None,
        target_location: Optional[str] = None,
        strategy: DecompositionStrategy = DecompositionStrategy.PARALLEL,
        custom_rules: Optional[List[DecompositionRule]] = None,
    ) -> ResearchPlan:
        """Create a new research plan."""
        from backend.research_engine.state.research_context import ResearchType

        plan = self.decomposer.decompose(
            query=query,
            research_type=ResearchType(research_type),
            target_role=target_role,
            target_company=target_company,
            target_location=target_location,
            max_sources=max_sources,
            timeout_seconds=timeout_seconds,
            strategy=strategy,
        )
        plan.research_id = research_id

        # Store plan
        self._plans[plan.id] = plan

        # Create execution state
        self._executions[plan.id] = PlanExecutionState(plan_id=plan.id)

        return plan

    def get_plan(self, plan_id: str) -> Optional[ResearchPlan]:
        """Get a plan by ID."""
        return self._plans.get(plan_id)

    def get_execution(self, plan_id: str) -> Optional[PlanExecutionState]:
        """Get execution state for a plan."""
        return self._executions.get(plan_id)

    def start_execution(self, plan_id: str) -> bool:
        """Start plan execution."""
        execution = self._executions.get(plan_id)
        if not execution or execution.status != PlanStatus.DRAFT:
            return False

        execution.status = PlanStatus.ACTIVE
        execution.started_at = datetime.utcnow()
        execution.current_task_index = 0
        return True

    def pause_execution(self, plan_id: str) -> bool:
        """Pause plan execution."""
        execution = self._executions.get(plan_id)
        if not execution or execution.status != PlanStatus.ACTIVE:
            return False

        execution.status = PlanStatus.PAUSED
        execution.paused_at = datetime.utcnow()
        return True

    def resume_execution(self, plan_id: str) -> bool:
        """Resume paused plan execution."""
        execution = self._executions.get(plan_id)
        if not execution or execution.status != PlanStatus.PAUSED:
            return False

        execution.status = PlanStatus.ACTIVE
        execution.paused_at = None
        return True

    def complete_task(self, plan_id: str, task_id: str, result: Dict[str, Any]) -> bool:
        """Mark a task as completed with result."""
        execution = self._executions.get(plan_id)
        plan = self._plans.get(plan_id)

        if not execution or not plan:
            return False

        if task_id not in [t.id for t in plan.tasks]:
            return False

        execution.completed_tasks.append(task_id)
        execution.task_results[task_id] = result
        execution.current_task_index += 1

        # Check if all tasks completed
        if len(execution.completed_tasks) == len(plan.tasks):
            execution.status = PlanStatus.COMPLETED
            execution.completed_at = datetime.utcnow()

        return True

    def fail_task(self, plan_id: str, task_id: str, error: str) -> bool:
        """Mark a task as failed."""
        execution = self._executions.get(plan_id)
        plan = self._plans.get(plan_id)

        if not execution or not plan:
            return False

        execution.failed_tasks.append(task_id)
        execution.task_results[task_id] = {"error": error}

        # Check if should fail entire plan
        if len(execution.failed_tasks) > len(plan.tasks) * 0.5:
            execution.status = PlanStatus.FAILED
            execution.error = f"Too many failed tasks: {error}"

        return True

    def get_next_task(self, plan_id: str) -> Optional[ResearchTask]:
        """Get the next task to execute."""
        execution = self._executions.get(plan_id)
        plan = self._plans.get(plan_id)

        if not execution or not plan:
            return None

        if execution.status != PlanStatus.ACTIVE:
            return None

        if execution.current_task_index >= len(plan.tasks):
            return None

        task = plan.tasks[execution.current_task_index]

        # Skip already completed/failed tasks
        if task.id in execution.completed_tasks or task.id in execution.failed_tasks:
            execution.current_task_index += 1
            return self.get_next_task(plan_id)

        return task

    def get_progress(self, plan_id: str) -> Dict[str, Any]:
        """Get plan execution progress."""
        execution = self._executions.get(plan_id)
        plan = self._plans.get(plan_id)

        if not execution or not plan:
            return {"error": "Plan not found"}

        total = len(plan.tasks)
        completed = len(execution.completed_tasks)
        failed = len(execution.failed_tasks)
        remaining = total - completed - failed

        return {
            "plan_id": plan_id,
            "status": execution.status.value,
            "total_tasks": total,
            "completed_tasks": completed,
            "failed_tasks": failed,
            "remaining_tasks": remaining,
            "progress_percentage": round((completed / total * 100) if total > 0 else 0, 1),
            "current_task": execution.current_task_index,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
        }

    def add_custom_rule(self, rule: DecompositionRule):
        """Add a custom decomposition rule."""
        self.decomposer.rules.append(rule)

    def remove_custom_rule(self, agent_type: str, research_type: str) -> bool:
        """Remove a custom decomposition rule."""
        initial_len = len(self.decomposer.rules)
        self.decomposer.rules = [
            r for r in self.decomposer.rules
            if not (r.agent_type == agent_type and r.research_type.value == research_type)
        ]
        return len(self.decomposer.rules) < initial_len

    def list_plans(self) -> List[Dict[str, Any]]:
        """List all plans."""
        return [
            {
                "id": p.id,
                "research_id": p.research_id,
                "query": p.query,
                "research_type": p.research_type.value,
                "task_count": len(p.tasks),
                "status": self._executions.get(p.id, PlanExecutionState(p.id)).status.value,
            }
            for p in self._plans.values()
        ]