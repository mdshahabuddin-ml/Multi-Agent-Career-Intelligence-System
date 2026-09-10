"""
DB-backed conversation store for Hermes agents.

Persists turns to the EXISTING ``hermes_conversations`` table (previously
unwired). Scoped by (user_id, conversation_id, agent_id) so agents can
never read each other's histories.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.models.hermes_memory import HermesConversation

logger = logging.getLogger(__name__)

_ALLOWED_ROLES = frozenset({"user", "assistant", "system", "tool"})


def _row_to_turn(row: HermesConversation) -> Dict[str, Any]:
    return {
        "id": row.id,
        "conversation_id": row.conversation_id,
        "agent_id": row.agent_id,
        "role": row.role,
        "content": row.content,
        "metadata": dict(row.metadata_json or {}),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


class DbConversationStore:
    """Conversation history persisted in the existing database."""

    def __init__(self, db: Session, user_id: int):
        self._db = db
        self._user_id = user_id

    async def append(
        self,
        conversation_id: str,
        agent_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Append one turn; returns the row id. Raises ValueError on bad input."""
        if not conversation_id or not agent_id:
            raise ValueError("conversation_id and agent_id are required")
        if role not in _ALLOWED_ROLES:
            raise ValueError(f"Unknown role: {role!r} (expected one of {sorted(_ALLOWED_ROLES)})")
        if not (content or "").strip():
            raise ValueError("Conversation content must not be empty")
        row = HermesConversation(
            conversation_id=conversation_id,
            agent_id=agent_id,
            user_id=self._user_id,
            role=role,
            content=content,
            metadata_json=dict(metadata or {}) or None,
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row.id

    async def history(
        self,
        conversation_id: str,
        agent_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Oldest-first turns for one conversation (empty when absent/foreign)."""
        rows = (
            self._db.query(HermesConversation)
            .filter(
                HermesConversation.user_id == self._user_id,
                HermesConversation.conversation_id == conversation_id,
                HermesConversation.agent_id == agent_id,
            )
            .order_by(HermesConversation.id.asc())
            .limit(max(1, limit))
            .all()
        )
        return [_row_to_turn(r) for r in rows]

    async def clear(self, conversation_id: str, agent_id: str) -> int:
        """Delete one conversation's turns. Returns count deleted."""
        rows = (
            self._db.query(HermesConversation)
            .filter(
                HermesConversation.user_id == self._user_id,
                HermesConversation.conversation_id == conversation_id,
                HermesConversation.agent_id == agent_id,
            )
            .all()
        )
        count = len(rows)
        for row in rows:
            self._db.delete(row)
        if count:
            self._db.commit()
        return count
