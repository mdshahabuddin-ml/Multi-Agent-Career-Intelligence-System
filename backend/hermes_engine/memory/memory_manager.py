"""
Memory Manager - Orchestrates memory operations for agents.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    High-level interface for agent memory operations.
    """

    def __init__(self, storage_path: Optional[str] = None):
        self._storage_path = storage_path or "data/hermes/memory"
        self._memories: Dict[str, List[Dict[str, Any]]] = {}

    async def store(
        self,
        agent_id: str,
        content: Any,
        category: str = "general",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Store a memory entry.
        
        Returns:
            Memory entry ID
        """
        import uuid
        from datetime import datetime

        memory_id = str(uuid.uuid4())
        entry = {
            "id": memory_id,
            "agent_id": agent_id,
            "content": content,
            "category": category,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
        }

        self._memories.setdefault(agent_id, []).append(entry)
        logger.info(f"Stored memory {memory_id} for agent {agent_id}")
        return memory_id

    async def retrieve(
        self,
        agent_id: str,
        query: str = "",
        limit: int = 10,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve memories for an agent."""
        memories = self._memories.get(agent_id, [])

        if category:
            memories = [m for m in memories if m.get("category") == category]

        if query:
            query_lower = query.lower()
            memories = [
                m for m in memories
                if query_lower in str(m.get("content", "")).lower()
            ]

        return memories[-limit:]

    async def delete(self, memory_id: str, agent_id: str) -> bool:
        """Delete a memory entry."""
        memories = self._memories.get(agent_id, [])
        for i, m in enumerate(memories):
            if m.get("id") == memory_id:
                memories.pop(i)
                return True
        return False

    async def clear_agent(self, agent_id: str) -> int:
        """Clear all memories for an agent."""
        count = len(self._memories.get(agent_id, []))
        self._memories.pop(agent_id, None)
        return count

    def get_stats(self, agent_id: str) -> Dict[str, Any]:
        """Get memory statistics for an agent."""
        memories = self._memories.get(agent_id, [])
        categories: Dict[str, int] = {}
        for m in memories:
            cat = m.get("category", "general")
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "total": len(memories),
            "categories": categories,
        }
