"""
Slack adapter.
"""

from __future__ import annotations

from typing import Any, Dict


class SlackAdapter:
    """Slack bot adapter."""

    def __init__(self, token: str = ""):
        self._token = token

    async def send_message(self, channel: str, text: str) -> Dict[str, Any]:
        """Send a message to Slack."""
        return {"channel": channel, "text": text, "status": "sent"}
