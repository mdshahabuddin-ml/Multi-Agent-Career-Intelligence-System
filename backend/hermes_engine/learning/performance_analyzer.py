"""
Performance Analyzer - Analyzes agent performance.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class PerformanceAnalyzer:
    """
    Analyzes agent performance metrics.
    """

    def __init__(self):
        self._metrics: List[Dict[str, Any]] = []

    def record(
        self,
        agent_id: str,
        task_id: str,
        duration_ms: float,
        success: bool,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a performance metric."""
        self._metrics.append({
            "agent_id": agent_id,
            "task_id": task_id,
            "duration_ms": duration_ms,
            "success": success,
            "metadata": metadata or {},
        })

    def get_agent_stats(self, agent_id: str) -> Dict[str, Any]:
        """Get performance stats for an agent."""
        metrics = [m for m in self._metrics if m["agent_id"] == agent_id]
        if not metrics:
            return {"total": 0}

        successful = [m for m in metrics if m["success"]]
        durations = [m["duration_ms"] for m in metrics]

        return {
            "total": len(metrics),
            "successful": len(successful),
            "failed": len(metrics) - len(successful),
            "avg_duration_ms": sum(durations) / len(durations),
            "min_duration_ms": min(durations),
            "max_duration_ms": max(durations),
        }

    def get_slowest_agents(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get slowest agents by average duration."""
        agent_durations: Dict[str, List[float]] = {}
        for m in self._metrics:
            agent_durations.setdefault(m["agent_id"], []).append(m["duration_ms"])

        stats = []
        for agent_id, durations in agent_durations.items():
            stats.append({
                "agent_id": agent_id,
                "avg_duration_ms": sum(durations) / len(durations),
                "task_count": len(durations),
            })

        return sorted(stats, key=lambda x: x["avg_duration_ms"], reverse=True)[:limit]
