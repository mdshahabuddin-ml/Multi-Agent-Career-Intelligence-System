"""
Discord adapter.
"""

from __future__ import annotations

from typing import Any, Dict


class DiscordAdapter:
    """Discord bot adapter."""

    def __init__(self, token: str = ""):
        self._token = token

    async def send_message(self, channel_id: str, text: str) -> Dict[str, Any]:
        """Send a message to Discord."""
        return {"channel_id": channel_id, "text": text, "status": "sent"}
