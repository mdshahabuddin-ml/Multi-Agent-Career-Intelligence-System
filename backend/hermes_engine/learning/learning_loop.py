"""
Learning Loop - Continuous learning system.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class LearningLoop:
    """
    Continuous learning loop for agent improvement.
    """

    def __init__(self):
        self._iterations: int = 0
        self._learnings: list = []

    async def run_iteration(
        self,
        agent_id: str,
        performance_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Run a learning iteration."""
        self._iterations += 1

        learning = {
            "agent_id": agent_id,
            "iteration": self._iterations,
            "performance": performance_data,
        }
        self._learnings.append(learning)

        return {
            "iteration": self._iterations,
            "status": "completed",
        }

    def get_learnings(self, limit: int = 10) -> list:
        """Get recent learnings."""
        return self._learnings[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get learning loop statistics."""
        return {
            "total_iterations": self._iterations,
            "total_learnings": len(self._learnings),
        }
