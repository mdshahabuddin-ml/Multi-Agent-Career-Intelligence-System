"""
Memory Service - Memory operations for agents.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MemoryService:
    """
    Service for agent memory operations.
    """

    def __init__(self):
        self._memories: Dict[int, List[Dict[str, Any]]] = {}

    async def store(
        self,
        user_id: int,
        content: Any,
        category: str = "general",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store a memory."""
        import uuid
        memory_id = str(uuid.uuid4())

        self._memories.setdefault(user_id, []).append({
            "id": memory_id,
            "content": content,
            "category": category,
            "metadata": metadata or {},
        })

        return memory_id

    async def retrieve(
        self,
        user_id: int,
        query: str = "",
        limit: int = 10,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve memories."""
        memories = self._memories.get(user_id, [])

        if category:
            memories = [m for m in memories if m.get("category") == category]

        return memories[-limit:]

    async def delete(self, user_id: int, memory_id: str) -> bool:
        """Delete a memory."""
        memories = self._memories.get(user_id, [])
        for i, m in enumerate(memories):
            if m.get("id") == memory_id:
                memories.pop(i)
                return True
        return False

    async def get_stats(self, user_id: int) -> Dict[str, Any]:
        """Get memory statistics."""
        memories = self._memories.get(user_id, [])
        return {"total": len(memories)}
