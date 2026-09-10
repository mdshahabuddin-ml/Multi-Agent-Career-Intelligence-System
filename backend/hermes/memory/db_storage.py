"""
DB-backed memory storage for Hermes agents.

Persists to the EXISTING ``hermes_memory`` table (previously unwired —
nothing else referenced it). Implements the SAME async interface as
``MemoryStorage`` (file backend), so ``MemoryManager(storage=...)``
accepts either backend with zero manager changes:

    from backend.hermes.memory import MemoryManager
    from backend.hermes.memory.db_storage import DbMemoryStorage

    manager = MemoryManager(storage=DbMemoryStorage(db, user_id))

Scoping: every row is owned by (user_id, agent_id). Memory IDs are
``str(row.id)`` to match the file backend's opaque string IDs.

Non-string content is JSON-serialized with a ``{"_serialized": "json"}``
marker merged into metadata so ``get`` round-trips the original type.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.models.hermes_memory import HermesMemory

logger = logging.getLogger(__name__)

_SERIALIZED_MARKER = "_serialized"
_JSON_MARKER = "json"


def _serialize(content: Any) -> tuple[str, bool]:
    if isinstance(content, str):
        return content, False
    return json.dumps(content, default=str), True


def _deserialize(text: str, metadata: Optional[Dict[str, Any]]) -> Any:
    if isinstance(metadata, dict) and metadata.get(_SERIALIZED_MARKER) == _JSON_MARKER:
        try:
            return json.loads(text)
        except (TypeError, ValueError):
            return text
    return text


def _row_to_dict(row: HermesMemory) -> Dict[str, Any]:
    metadata = dict(row.metadata_json or {})
    metadata.pop(_SERIALIZED_MARKER, None)
    return {
        "id": str(row.id),
        "agent_id": row.agent_id,
        "content": _deserialize(row.content, row.metadata_json),
        "category": row.category,
        "metadata": metadata,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


class DbMemoryStorage:
    """SQLAlchemy-backed drop-in replacement for ``MemoryStorage``."""

    def __init__(self, db: Session, user_id: int):
        self._db = db
        self._user_id = user_id

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _base_query(self, agent_id: str, category: Optional[str] = None):
        query = self._db.query(HermesMemory).filter(
            HermesMemory.user_id == self._user_id,
            HermesMemory.agent_id == agent_id,
        )
        if category:
            query = query.filter(HermesMemory.category == category)
        return query

    @staticmethod
    def _coerce_id(memory_id: str) -> Optional[int]:
        try:
            return int(str(memory_id))
        except (TypeError, ValueError):
            return None

    # ------------------------------------------------------------------
    # Interface (mirrors MemoryStorage)
    # ------------------------------------------------------------------
    async def store(
        self,
        agent_id: str,
        content: Any,
        category: str = "general",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store a memory entry and return its ID."""
        text, was_json = _serialize(content)
        stored_metadata = dict(metadata or {})
        if was_json:
            stored_metadata[_SERIALIZED_MARKER] = _JSON_MARKER
        row = HermesMemory(
            agent_id=agent_id,
            user_id=self._user_id,
            category=category or "general",
            content=text,
            metadata_json=stored_metadata or None,
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return str(row.id)

    async def get(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single memory entry by ID (None when absent/foreign)."""
        row_id = self._coerce_id(memory_id)
        if row_id is None:
            return None
        row = (
            self._db.query(HermesMemory)
            .filter(HermesMemory.id == row_id, HermesMemory.user_id == self._user_id)
            .first()
        )
        return _row_to_dict(row) if row else None

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory entry. Returns True if deleted."""
        row_id = self._coerce_id(memory_id)
        if row_id is None:
            return False
        row = (
            self._db.query(HermesMemory)
            .filter(HermesMemory.id == row_id, HermesMemory.user_id == self._user_id)
            .first()
        )
        if not row:
            return False
        self._db.delete(row)
        self._db.commit()
        return True

    async def get_recent(
        self,
        agent_id: str,
        limit: int = 10,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get the most recent memories for an agent."""
        rows = (
            self._base_query(agent_id, category)
            .order_by(HermesMemory.id.desc())
            .limit(max(1, limit))
            .all()
        )
        return [_row_to_dict(r) for r in rows]

    async def search(
        self,
        agent_id: str,
        query: str,
        limit: int = 10,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Substring search across an agent's memories (same semantics as file backend)."""
        needle = (query or "").lower()
        if not needle:
            return []
        rows = (
            self._base_query(agent_id, category)
            .order_by(HermesMemory.id.desc())
            .all()
        )
        results = []
        for row in rows:
            haystack = json.dumps(_deserialize(row.content, row.metadata_json), default=str).lower()
            if needle in haystack:
                results.append(_row_to_dict(row))
                if len(results) >= max(1, limit):
                    break
        return results

    async def clear_agent(self, agent_id: str) -> int:
        """Clear all memories for an agent. Returns count deleted."""
        rows = self._base_query(agent_id).all()
        count = len(rows)
        for row in rows:
            self._db.delete(row)
        if count:
            self._db.commit()
        return count

    def get_stats(self, agent_id: str) -> Dict[str, Any]:
        """Get memory statistics for an agent."""
        rows = self._base_query(agent_id).all()
        categories: Dict[str, int] = {}
        for row in rows:
            categories[row.category] = categories.get(row.category, 0) + 1
        return {
            "total": len(rows),
            "categories": categories,
            "backend": "db",
            "stored_at": datetime.utcnow().isoformat(),
        }
