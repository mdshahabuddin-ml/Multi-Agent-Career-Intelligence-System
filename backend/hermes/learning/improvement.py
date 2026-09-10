"""
Improvement Tracker - tracks and suggests agent improvements based on feedback.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional


class ImprovementSuggestion:
    """A suggested improvement for an agent."""

    def __init__(
        self,
        agent_id: str,
        category: str,
        description: str,
        priority: int = 0,
        based_on: Optional[List[str]] = None,
    ):
        self.agent_id = agent_id
        self.category = category
        self.description = description
        self.priority = priority
        self.based_on = based_on or []
        self.created_at = datetime.utcnow()
        self.implemented = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "category": self.category,
            "description": self.description,
            "priority": self.priority,
            "based_on": self.based_on,
            "created_at": self.created_at.isoformat(),
            "implemented": self.implemented,
        }


class ImprovementTracker:
    """
    Tracks agent improvements and generates suggestions.

    Analyzes feedback patterns and task results to suggest
    actionable improvements for agent performance.
    """

    def __init__(self) -> None:
        self._suggestions: List[ImprovementSuggestion] = []
        self._implemented: List[Dict[str, Any]] = []

    def analyze_and_suggest(
        self,
        agent_id: str,
        feedback_stats: Dict[str, Any],
        task_history: List[Dict[str, Any]],
    ) -> List[ImprovementSuggestion]:
        """
        Analyze feedback and task history to generate improvement suggestions.

        Args:
            agent_id: The agent to analyze.
            feedback_stats: Feedback statistics from FeedbackCollector.
            task_history: Recent task execution history.

        Returns:
            List of improvement suggestions.
        """
        suggestions = []

        avg_rating = feedback_stats.get("average_rating", 0)
        if avg_rating < 3.0 and avg_rating > 0:
            suggestions.append(
                ImprovementSuggestion(
                    agent_id=agent_id,
                    category="quality",
                    description=(
                        f"Average rating is low ({avg_rating:.1f}/5). "
                        "Consider refining task processing logic."
                    ),
                    priority=2,
                )
            )

        failed_tasks = [
            t for t in task_history if not t.get("success", True)
        ]
        if len(failed_tasks) > 3:
            suggestions.append(
                ImprovementSuggestion(
                    agent_id=agent_id,
                    category="reliability",
                    description=(
                        f"{len(failed_tasks)} recent task failures detected. "
                        "Review error handling and add retry logic."
                    ),
                    priority=3,
                )
            )

        self._suggestions.extend(suggestions)
        return suggestions

    def get_suggestions(
        self,
        agent_id: Optional[str] = None,
        include_implemented: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get improvement suggestions."""
        filtered = self._suggestions
        if agent_id:
            filtered = [s for s in filtered if s.agent_id == agent_id]
        if not include_implemented:
            filtered = [s for s in filtered if not s.implemented]
        return [s.to_dict() for s in filtered]

    def mark_implemented(
        self,
        agent_id: str,
        category: str,
        notes: str = "",
    ) -> bool:
        """Mark a suggestion as implemented."""
        for suggestion in self._suggestions:
            if (
                suggestion.agent_id == agent_id
                and suggestion.category == category
                and not suggestion.implemented
            ):
                suggestion.implemented = True
                self._implemented.append({
                    "agent_id": agent_id,
                    "category": category,
                    "notes": notes,
                    "implemented_at": datetime.utcnow().isoformat(),
                })
                return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get improvement tracking statistics."""
        return {
            "total_suggestions": len(self._suggestions),
            "implemented": len(self._implemented),
            "pending": len([s for s in self._suggestions if not s.implemented]),
        }
