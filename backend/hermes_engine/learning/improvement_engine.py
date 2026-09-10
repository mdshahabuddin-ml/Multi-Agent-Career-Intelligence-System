"""
Improvement Engine - Generates improvement suggestions.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional


class ImprovementEngine:
    """
    Generates improvement suggestions based on performance data.
    """

    def __init__(self):
        self._suggestions: List[Dict[str, Any]] = []

    def analyze(
        self,
        agent_id: str,
        performance_stats: Dict[str, Any],
        feedback_stats: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Analyze and generate suggestions."""
        suggestions = []

        avg_rating = feedback_stats.get("average_rating", 0)
        if avg_rating < 3.0 and avg_rating > 0:
            suggestions.append({
                "agent_id": agent_id,
                "category": "quality",
                "priority": "high",
                "description": f"Average rating is low ({avg_rating:.1f}/5)",
            })

        failed = performance_stats.get("failed", 0)
        total = performance_stats.get("total", 0)
        if total > 0 and failed / total > 0.2:
            suggestions.append({
                "agent_id": agent_id,
                "category": "reliability",
                "priority": "high",
                "description": f"High failure rate: {failed}/{total} tasks failed",
            })

        self._suggestions.extend(suggestions)
        return suggestions

    def get_suggestions(
        self,
        agent_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get improvement suggestions."""
        if agent_id:
            return [s for s in self._suggestions if s["agent_id"] == agent_id]
        return list(self._suggestions)
