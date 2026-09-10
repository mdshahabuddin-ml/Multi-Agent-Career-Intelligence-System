"""
Memory Retriever - relevance-based retrieval of agent memories.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .storage import MemoryStorage


class MemoryRetriever:
    """
    Retrieves memories based on relevance scoring.

    Uses a combination of text matching, recency weighting,
    and category relevance to rank memories for a given query.
    """

    def __init__(self, storage: MemoryStorage):
        self._storage = storage
        self._recency_weight = 0.3
        self._relevance_weight = 0.7

    def _score_relevance(self, content: str, query: str) -> float:
        """Compute a simple relevance score between content and query."""
        content_lower = content.lower()
        query_lower = query.lower()

        query_words = query_lower.split()
        if not query_words:
            return 0.0

        matches = sum(1 for word in query_words if word in content_lower)
        return matches / len(query_words)

    def _score_recency(self, created_at: str) -> float:
        """Compute a recency score. More recent = higher score."""
        from datetime import datetime

        try:
            created = datetime.fromisoformat(created_at)
            now = datetime.utcnow()
            age_hours = max((now - created).total_seconds() / 3600, 0.01)
            return 1.0 / (1.0 + age_hours * 0.1)
        except (ValueError, TypeError):
            return 0.5

    async def retrieve(
        self,
        agent_id: str,
        query: str,
        limit: int = 10,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve and rank memories by relevance.

        Args:
            agent_id: The agent to retrieve memories for.
            query: The search query.
            limit: Maximum results to return.
            category: Optional category filter.

        Returns:
            Ranked list of memory entries.
        """
        candidates = await self._storage.search(
            agent_id=agent_id,
            query=query,
            limit=50,
            category=category,
        )

        scored = []
        for memory in candidates:
            content_str = str(memory.get("content", ""))
            relevance = self._score_relevance(content_str, query)
            recency = self._score_recency(memory.get("created_at", ""))
            score = (
                self._relevance_weight * relevance
                + self._recency_weight * recency
            )
            scored.append((score, memory))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [memory for _, memory in scored[:limit]]
