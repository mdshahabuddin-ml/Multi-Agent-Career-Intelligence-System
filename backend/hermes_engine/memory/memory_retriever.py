"""
Memory Retriever - Retrieves relevant memories.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class MemoryRetriever:
    """
    Retrieves memories based on relevance scoring.
    """

    def __init__(self):
        self._recency_weight = 0.3
        self._relevance_weight = 0.7

    def retrieve(
        self,
        memories: List[Dict[str, Any]],
        query: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve and rank memories by relevance.
        """
        scored = []
        query_lower = query.lower()
        query_words = query_lower.split()

        for memory in memories:
            content = str(memory.get("content", "")).lower()
            relevance = sum(1 for w in query_words if w in content)
            if query_words:
                relevance /= len(query_words)

            # Simple recency score
            recency = 0.5  # Default

            score = (
                self._relevance_weight * relevance
                + self._recency_weight * recency
            )
            scored.append((score, memory))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:limit]]
