"""
Message Router - Routes messages between agents and services.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class MessageRouter:
    """
    Routes messages between components.
    """

    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._message_log: List[Dict[str, Any]] = []

    def register(self, message_type: str, handler: Callable) -> None:
        """Register a handler for a message type."""
        self._handlers[message_type] = handler

    def unregister(self, message_type: str) -> bool:
        """Unregister a handler."""
        return self._handlers.pop(message_type, None) is not None

    async def route(self, message: Dict[str, Any]) -> Any:
        """Route a message."""
        msg_type = message.get("type", "unknown")
        handler = self._handlers.get(msg_type)

        self._message_log.append(message)

        if handler:
            return await handler(message)
        else:
            logger.warning(f"No handler for message type: {msg_type}")
            return None

    def get_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get message log."""
        return self._message_log[-limit:]
