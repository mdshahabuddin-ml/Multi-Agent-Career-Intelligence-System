"""
Agent state management for tracking agent status and context.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .task import Task


@dataclass
class AgentState:
    """
    Mutable state container for an Agent.

    Tracks the agent's current task, accumulated context,
    and any intermediate results.
    """

    agent_id: str
    current_task: Optional["Task"] = None
    context: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def update(self, **kwargs: Any) -> None:
        """Update state fields and mark as updated."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.utcnow()

    def add_to_context(self, key: str, value: Any) -> None:
        """Add a key-value pair to the context dictionary."""
        self.context[key] = value
        self.updated_at = datetime.utcnow()

    def get_from_context(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from the context dictionary."""
        return self.context.get(key, default)

    def append_history(self, entry: Dict[str, Any]) -> None:
        """Append an entry to the state history."""
        entry.setdefault("timestamp", datetime.utcnow().isoformat())
        self.history.append(entry)
        self.updated_at = datetime.utcnow()

    def clear_context(self) -> None:
        """Clear all context data."""
        self.context.clear()
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize state to a dictionary."""
        return {
            "agent_id": self.agent_id,
            "current_task_id": self.current_task.id if self.current_task else None,
            "context": self.context,
            "history_length": len(self.history),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class StateManager:
    """
    Thread-safe manager for multiple agent states.

    Provides centralized state storage and retrieval for
    multi-agent orchestration scenarios.
    """

    def __init__(self) -> None:
        self._states: Dict[str, AgentState] = {}
        self._lock = threading.Lock()

    def register(self, agent_id: str) -> AgentState:
        """Register a new agent and return its state."""
        with self._lock:
            if agent_id in self._states:
                return self._states[agent_id]
            state = AgentState(agent_id=agent_id)
            self._states[agent_id] = state
            return state

    def get(self, agent_id: str) -> Optional[AgentState]:
        """Get the state for an agent by ID."""
        return self._states.get(agent_id)

    def remove(self, agent_id: str) -> bool:
        """Remove an agent's state. Returns True if removed."""
        with self._lock:
            return self._states.pop(agent_id, None) is not None

    def get_all(self) -> Dict[str, AgentState]:
        """Get all registered states."""
        return dict(self._states)

    def clear(self) -> None:
        """Remove all registered states."""
        with self._lock:
            self._states.clear()
