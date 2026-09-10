"""
Feedback Collector - gathers and analyzes agent performance feedback.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional


class FeedbackEntry:
    """A single feedback entry."""

    def __init__(
        self,
        agent_id: str,
        task_id: str,
        rating: int,
        comment: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.id = f"{agent_id}_{task_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        self.agent_id = agent_id
        self.task_id = task_id
        self.rating = max(1, min(5, rating))
        self.comment = comment
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()


class FeedbackCollector:
    """
    Collects and analyzes feedback on agent performance.

    Stores feedback entries and provides analytics for
    continuous improvement of agent behavior.
    """

    def __init__(self) -> None:
        self._entries: List[FeedbackEntry] = []

    def submit(
        self,
        agent_id: str,
        task_id: str,
        rating: int,
        comment: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FeedbackEntry:
        """Submit a feedback entry."""
        entry = FeedbackEntry(
            agent_id=agent_id,
            task_id=task_id,
            rating=rating,
            comment=comment,
            metadata=metadata,
        )
        self._entries.append(entry)
        return entry

    def get_agent_feedback(
        self, agent_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get feedback for a specific agent."""
        agent_entries = [
            e for e in self._entries if e.agent_id == agent_id
        ]
        return [
            {
                "id": e.id,
                "task_id": e.task_id,
                "rating": e.rating,
                "comment": e.comment,
                "created_at": e.created_at.isoformat(),
            }
            for e in agent_entries[-limit:]
        ]

    def get_average_rating(self, agent_id: str) -> float:
        """Get the average rating for an agent."""
        agent_entries = [
            e for e in self._entries if e.agent_id == agent_id
        ]
        if not agent_entries:
            return 0.0
        return sum(e.rating for e in agent_entries) / len(agent_entries)

    def get_stats(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Get feedback statistics."""
        entries = self._entries
        if agent_id:
            entries = [e for e in entries if e.agent_id == agent_id]

        if not entries:
            return {"total": 0, "average_rating": 0.0}

        return {
            "total": len(entries),
            "average_rating": sum(e.rating for e in entries) / len(entries),
            "rating_distribution": {
                i: sum(1 for e in entries if e.rating == i)
                for i in range(1, 6)
            },
        }
