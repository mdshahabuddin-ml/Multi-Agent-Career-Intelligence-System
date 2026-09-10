"""
Telegram adapter.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class TelegramAdapter:
    """Telegram bot adapter."""

    def __init__(self, token: str = ""):
        self._token = token

    async def send_message(self, chat_id: str, text: str) -> Dict[str, Any]:
        """Send a message to Telegram."""
        return {"chat_id": chat_id, "text": text, "status": "sent"}

    async def get_updates(self) -> list:
        """Get updates from Telegram."""
        return []
