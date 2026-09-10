"""
Hermes State Management - Thread-safe state for agents and tasks.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum


class TaskState(str, Enum):
    """Task execution states."""
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class HermesState:
    """
    Thread-safe state container for Hermes agents and tasks.
    """
    agent_id: str
    task_id: Optional[str] = None
    state: TaskState = TaskState.PENDING
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def update(self, **kwargs: Any) -> None:
        """Thread-safe state update."""
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            self.updated_at = datetime.utcnow()

    def add_context(self, key: str, value: Any) -> None:
        """Thread-safe context addition."""
        with self._lock:
            self.context[key] = value
            self.updated_at = datetime.utcnow()

    def get_context(self, key: str, default: Any = None) -> Any:
        """Thread-safe context retrieval."""
        with self._lock:
            return self.context.get(key, default)

    def append_history(self, entry: Dict[str, Any]) -> None:
        """Thread-safe history append."""
        with self._lock:
            entry.setdefault("timestamp", datetime.utcnow().isoformat())
            self.history.append(entry)
            self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize state to dictionary."""
        with self._lock:
            return {
                "agent_id": self.agent_id,
                "task_id": self.task_id,
                "state": self.state.value,
                "context": dict(self.context),
                "metadata": dict(self.metadata),
                "history_length": len(self.history),
                "created_at": self.created_at.isoformat(),
                "updated_at": self.updated_at.isoformat(),
            }


class StateManager:
    """
    Thread-safe manager for multiple agent states.
    """

    def __init__(self) -> None:
        self._states: Dict[str, HermesState] = {}
        self._lock = threading.Lock()

    def register(self, agent_id: str) -> HermesState:
        """Register a new agent state."""
        with self._lock:
            if agent_id in self._states:
                return self._states[agent_id]
            state = HermesState(agent_id=agent_id)
            self._states[agent_id] = state
            return state

    def get(self, agent_id: str) -> Optional[HermesState]:
        """Get agent state by ID."""
        return self._states.get(agent_id)

    def remove(self, agent_id: str) -> bool:
        """Remove an agent state."""
        with self._lock:
            return self._states.pop(agent_id, None) is not None

    def get_all(self) -> Dict[str, HermesState]:
        """Get all registered states."""
        return dict(self._states)

    def clear(self) -> None:
        """Remove all states."""
        with self._lock:
            self._states.clear()


# Global state manager instance
state_manager = StateManager()
