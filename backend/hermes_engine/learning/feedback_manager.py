"""
Feedback Manager - Manages agent feedback.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional


class FeedbackManager:
    """
    Collects and analyzes feedback on agent performance.
    """

    def __init__(self):
        self._feedback: List[Dict[str, Any]] = []

    def submit(
        self,
        agent_id: str,
        task_id: str,
        rating: int,
        comment: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Submit feedback."""
        entry = {
            "agent_id": agent_id,
            "task_id": task_id,
            "rating": max(1, min(5, rating)),
            "comment": comment,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
        }
        self._feedback.append(entry)
        return entry

    def get_agent_feedback(
        self,
        agent_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get feedback for an agent."""
        return [
            f for f in self._feedback
            if f["agent_id"] == agent_id
        ][-limit:]

    def get_average_rating(self, agent_id: str) -> float:
        """Get average rating for an agent."""
        ratings = [
            f["rating"] for f in self._feedback
            if f["agent_id"] == agent_id
        ]
        return sum(ratings) / len(ratings) if ratings else 0.0

    def get_stats(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Get feedback statistics."""
        entries = self._feedback
        if agent_id:
            entries = [f for f in entries if f["agent_id"] == agent_id]

        if not entries:
            return {"total": 0, "average_rating": 0.0}

        return {
            "total": len(entries),
            "average_rating": sum(f["rating"] for f in entries) / len(entries),
        }
