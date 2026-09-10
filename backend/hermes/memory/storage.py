"""
Memory Storage - persistent storage backend for agent memories.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class MemoryStorage:
    """
    File-system based storage for agent memories.

    Stores memory entries as JSON files organized by agent ID
    and category. Provides basic CRUD operations and querying.
    """

    def __init__(self, base_path: Optional[str] = None):
        if base_path is None:
            base_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data",
                "hermes",
                "memory",
            )
        self._base_path = Path(base_path)
        self._base_path.mkdir(parents=True, exist_ok=True)
        self._index: Dict[str, Dict[str, Any]] = {}
        self._load_index()

    def _agent_dir(self, agent_id: str) -> Path:
        """Get or create the directory for an agent's memories."""
        agent_dir = self._base_path / agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)
        return agent_dir

    def _index_path(self) -> Path:
        return self._base_path / "_index.json"

    def _load_index(self) -> None:
        """Load the memory index from disk."""
        idx_path = self._index_path()
        if idx_path.exists():
            try:
                with open(idx_path, "r") as f:
                    self._index = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._index = {}

    def _save_index(self) -> None:
        """Persist the memory index to disk."""
        with open(self._index_path(), "w") as f:
            json.dump(self._index, f, indent=2, default=str)

    async def store(
        self,
        agent_id: str,
        content: Any,
        category: str = "general",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store a memory entry and return its ID."""
        memory_id = str(uuid.uuid4())
        agent_dir = self._agent_dir(agent_id)
        file_path = agent_dir / f"{memory_id}.json"

        entry = {
            "id": memory_id,
            "agent_id": agent_id,
            "content": content,
            "category": category,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
        }

        with open(file_path, "w") as f:
            json.dump(entry, f, indent=2, default=str)

        self._index[memory_id] = {
            "agent_id": agent_id,
            "category": category,
            "file_path": str(file_path),
            "created_at": entry["created_at"],
        }
        self._save_index()

        return memory_id

    async def get(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single memory entry by ID."""
        info = self._index.get(memory_id)
        if not info:
            return None

        file_path = Path(info["file_path"])
        if not file_path.exists():
            return None

        with open(file_path, "r") as f:
            return json.load(f)

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory entry. Returns True if deleted."""
        info = self._index.pop(memory_id, None)
        if not info:
            return False

        file_path = Path(info["file_path"])
        if file_path.exists():
            file_path.unlink()

        self._save_index()
        return True

    async def get_recent(
        self,
        agent_id: str,
        limit: int = 10,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get the most recent memories for an agent."""
        entries = []
        for mid, info in self._index.items():
            if info["agent_id"] != agent_id:
                continue
            if category and info["category"] != category:
                continue
            entries.append((info["created_at"], mid))

        entries.sort(key=lambda x: x[0], reverse=True)
        results = []
        for _, mid in entries[:limit]:
            memory = await self.get(mid)
            if memory:
                results.append(memory)
        return results

    async def search(
        self,
        agent_id: str,
        query: str,
        limit: int = 10,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Simple text-based search across agent memories."""
        query_lower = query.lower()
        candidates = []

        for mid, info in self._index.items():
            if info["agent_id"] != agent_id:
                continue
            if category and info["category"] != category:
                continue
            candidates.append(mid)

        results = []
        for mid in candidates:
            memory = await self.get(mid)
            if not memory:
                continue

            content_str = json.dumps(memory.get("content", "")).lower()
            if query_lower in content_str:
                results.append(memory)
                if len(results) >= limit:
                    break

        return results

    async def clear_agent(self, agent_id: str) -> int:
        """Clear all memories for an agent. Returns count deleted."""
        to_delete = [
            mid for mid, info in self._index.items()
            if info["agent_id"] == agent_id
        ]

        for mid in to_delete:
            await self.delete(mid)

        return len(to_delete)

    def get_stats(self, agent_id: str) -> Dict[str, Any]:
        """Get memory statistics for an agent."""
        categories: Dict[str, int] = {}
        total = 0

        for info in self._index.values():
            if info["agent_id"] != agent_id:
                continue
            total += 1
            cat = info["category"]
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "total": total,
            "categories": categories,
        }
