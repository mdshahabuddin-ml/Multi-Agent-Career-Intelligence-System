"""
Task definitions for the Hermes Engine.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from .hermes_state import TaskState


class TaskType(str, Enum):
    """Task types."""
    GENERIC = "generic"
    RESEARCH = "research"
    ANALYSIS = "analysis"
    CONTENT = "content"
    AUTOMATION = "automation"
    SCHEDULED = "scheduled"


class TaskPriority(int, Enum):
    """Task priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


@dataclass
class HermesTask:
    """
    A unit of work to be executed by a Hermes Agent.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: TaskType = TaskType.GENERIC
    description: str = ""
    input_data: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    status: str = "pending"
    assigned_agent: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_task_id: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    timeout_seconds: int = 300
    max_retries: int = 3

    def start(self) -> None:
        """Mark task as started."""
        self.status = "in_progress"
        self.started_at = datetime.utcnow()

    def complete(self, output: Any = None) -> None:
        """Mark task as completed."""
        self.status = "completed"
        self.completed_at = datetime.utcnow()
        if output is not None:
            self.metadata["output"] = output

    def fail(self, error: str) -> None:
        """Mark task as failed."""
        self.status = "failed"
        self.completed_at = datetime.utcnow()
        self.metadata["error"] = error

    def cancel(self) -> None:
        """Mark task as cancelled."""
        self.status = "cancelled"
        self.completed_at = datetime.utcnow()

    @property
    def state(self) -> "TaskState":
        """Map the status string onto the TaskState enum."""
        mapping = {
            "pending": TaskState.PENDING,
            "in_progress": TaskState.EXECUTING,
            "completed": TaskState.COMPLETED,
            "failed": TaskState.FAILED,
            "cancelled": TaskState.CANCELLED,
        }
        return mapping.get(self.status, TaskState.PENDING)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HermesTask":
        """Deserialize a task from a dictionary (round-trips to_dict)."""
        try:
            task_type = TaskType(data.get("type", TaskType.GENERIC.value))
        except ValueError:
            task_type = TaskType.GENERIC
        try:
            priority = TaskPriority(data.get("priority", TaskPriority.NORMAL.value))
        except ValueError:
            priority = TaskPriority.NORMAL

        def _parse_dt(value: Any) -> Optional[datetime]:
            if not value:
                return None
            if isinstance(value, datetime):
                return value
            try:
                return datetime.fromisoformat(value)
            except (ValueError, TypeError):
                return None

        return cls(
            id=data.get("id") or str(uuid.uuid4()),
            type=task_type,
            description=data.get("description", ""),
            input_data=data.get("input_data", {}),
            priority=priority,
            status=data.get("status", "pending"),
            assigned_agent=data.get("assigned_agent"),
            created_at=_parse_dt(data.get("created_at")) or datetime.utcnow(),
            started_at=_parse_dt(data.get("started_at")),
            completed_at=_parse_dt(data.get("completed_at")),
            metadata=data.get("metadata", {}),
            parent_task_id=data.get("parent_task_id"),
            dependencies=data.get("dependencies", []),
            tags=data.get("tags", []),
            timeout_seconds=data.get("timeout_seconds", 300),
            max_retries=data.get("max_retries", 3),
        )
    @property
    def duration_seconds(self) -> Optional[float]:
        """Get task duration in seconds."""
        if self.started_at is None:
            return None
        end = self.completed_at or datetime.utcnow()
        return (end - self.started_at).total_seconds()

    @property
    def is_terminal(self) -> bool:
        """Check if task is in a terminal state."""
        return self.status in ("completed", "failed", "cancelled")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize task to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "description": self.description,
            "input_data": self.input_data,
            "priority": self.priority.value,
            "status": self.status,
            "assigned_agent": self.assigned_agent,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata,
            "parent_task_id": self.parent_task_id,
            "dependencies": self.dependencies,
            "tags": self.tags,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
        }
