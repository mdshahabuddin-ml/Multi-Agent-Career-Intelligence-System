"""
Conversation Memory - Manages conversation context.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Optional


class ConversationMemory:
    """
    Manages conversation context for agent interactions.
    """

    def __init__(self, max_size: int = 100):
        self._max_size = max_size
        self._conversations: Dict[str, deque] = {}

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a message to a conversation."""
        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = deque(maxlen=self._max_size)

        self._conversations[conversation_id].append({
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
        })

    def get_history(
        self,
        conversation_id: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get conversation history."""
        messages = self._conversations.get(conversation_id, deque())
        return list(messages)[-limit:]

    def get_context(
        self,
        conversation_id: str,
        max_tokens: int = 2000,
    ) -> str:
        """Get conversation context as a string."""
        history = self.get_history(conversation_id)
        context_parts = []
        total_tokens = 0

        for msg in reversed(history):
            text = f"{msg['role']}: {msg['content']}"
            # Rough token estimate
            tokens = len(text.split())
            if total_tokens + tokens > max_tokens:
                break
            context_parts.insert(0, text)
            total_tokens += tokens

        return "\n".join(context_parts)

    def clear(self, conversation_id: str) -> None:
        """Clear a conversation."""
        self._conversations.pop(conversation_id, None)

    def get_conversations(self) -> List[str]:
        """Get all conversation IDs."""
        return list(self._conversations.keys())
