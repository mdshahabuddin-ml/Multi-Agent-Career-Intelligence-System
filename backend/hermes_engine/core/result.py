"""
Result types for the Hermes Engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class HermesResult:
    """
    Result of a Hermes Agent task execution.
    """
    task_id: str
    success: bool = True
    output: Any = None
    error: Optional[str] = None
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize result to dictionary."""
        return {
            "task_id": self.task_id,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HermesResult":
        """Deserialize result from dictionary."""
        return cls(
            task_id=data.get("task_id", ""),
            success=data.get("success", True),
            output=data.get("output"),
            error=data.get("error"),
            agent_id=data.get("agent_id"),
            agent_name=data.get("agent_name"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class PlanResult:
    """
    Result of a planning operation.
    """
    goal: str
    subtasks: list = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    estimated_steps: int = 0
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "subtasks": self.subtasks,
            "constraints": self.constraints,
            "estimated_steps": self.estimated_steps,
            "success": self.success,
            "error": self.error,
        }


@dataclass
class ExecutionResult:
    """
    Result of a parallel execution operation.
    """
    task_id: str
    results: list = field(default_factory=list)
    total_tasks: int = 0
    completed: int = 0
    failed: int = 0
    success: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "results": self.results,
            "total_tasks": self.total_tasks,
            "completed": self.completed,
            "failed": self.failed,
            "success": self.success,
        }
