"""
Memory Manager - orchestrates memory operations for agents.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .storage import MemoryStorage
from .retriever import MemoryRetriever


class MemoryManager:
    """
    High-level interface for agent memory operations.

    Coordinates storage and retrieval of memories, providing
    a unified API for agents to store experiences, retrieve
    relevant context, and manage their knowledge.
    """

    def __init__(self, storage: Optional[MemoryStorage] = None):
        self._storage = storage or MemoryStorage()
        self._retriever = MemoryRetriever(self._storage)

    async def store(
        self,
        agent_id: str,
        content: Any,
        category: str = "general",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Store a memory entry for an agent.

        Args:
            agent_id: The ID of the agent storing the memory.
            content: The memory content (str, dict, or any serializable data).
            category: Category label for organizing memories.
            metadata: Optional metadata to attach to the memory.

        Returns:
            The ID of the stored memory entry.
        """
        return await self._storage.store(
            agent_id=agent_id,
            content=content,
            category=category,
            metadata=metadata or {},
        )

    async def retrieve(
        self,
        agent_id: str,
        query: str,
        limit: int = 10,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories for a query.

        Args:
            agent_id: The ID of the agent requesting memories.
            query: The search query.
            limit: Maximum number of results.
            category: Optional category filter.

        Returns:
            List of memory entries sorted by relevance.
        """
        return await self._retriever.retrieve(
            agent_id=agent_id,
            query=query,
            limit=limit,
            category=category,
        )

    async def get_recent(
        self,
        agent_id: str,
        limit: int = 10,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get the most recent memories for an agent."""
        return await self._storage.get_recent(
            agent_id=agent_id,
            limit=limit,
            category=category,
        )

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory entry by ID."""
        return await self._storage.delete(memory_id)

    async def clear_agent(self, agent_id: str) -> int:
        """Clear all memories for an agent. Returns count of deleted entries."""
        return await self._storage.clear_agent(agent_id)

    def get_stats(self, agent_id: str) -> Dict[str, Any]:
        """Get memory statistics for an agent."""
        return self._storage.get_stats(agent_id)
