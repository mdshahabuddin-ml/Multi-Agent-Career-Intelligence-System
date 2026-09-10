"""
Execution Plan - Structured execution plan management.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum


class PlanStatus(str, Enum):
    """Plan execution status."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PlanStep:
    """A single step in an execution plan."""
    id: str
    description: str
    agent_id: Optional[str] = None
    status: str = "pending"
    depends_on: List[str] = field(default_factory=list)
    result: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    def complete(self, result: Optional[Dict[str, Any]] = None) -> None:
        """Mark step as completed."""
        self.status = "completed"
        self.result = result
        self.completed_at = datetime.utcnow()

    def fail(self, error: str) -> None:
        """Mark step as failed."""
        self.status = "failed"
        self.result = {"error": error}
        self.completed_at = datetime.utcnow()


@dataclass
class ExecutionPlan:
    """
    A structured plan for task execution.
    """
    id: str
    goal: str
    steps: List[PlanStep] = field(default_factory=list)
    status: PlanStatus = PlanStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_step(self, step: PlanStep) -> None:
        """Add a step to the plan."""
        self.steps.append(step)
        self.updated_at = datetime.utcnow()

    def get_next_step(self) -> Optional[PlanStep]:
        """Get the next executable step."""
        for step in self.steps:
            if step.status == "pending":
                # Check if dependencies are met
                deps_met = all(
                    self._get_step(dep_id) and self._get_step(dep_id).status == "completed"
                    for dep_id in step.depends_on
                )
                if deps_met:
                    return step
        return None

    def _get_step(self, step_id: str) -> Optional[PlanStep]:
        """Get a step by ID."""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    @property
    def progress(self) -> float:
        """Calculate plan progress (0-100)."""
        if not self.steps:
            return 0.0
        completed = sum(1 for s in self.steps if s.status == "completed")
        return (completed / len(self.steps)) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Serialize plan to dictionary."""
        return {
            "id": self.id,
            "goal": self.goal,
            "steps": [
                {
                    "id": s.id,
                    "description": s.description,
                    "agent_id": s.agent_id,
                    "status": s.status,
                    "depends_on": s.depends_on,
                }
                for s in self.steps
            ],
            "status": self.status.value,
            "progress": self.progress,
            "created_at": self.created_at.isoformat(),
        }
