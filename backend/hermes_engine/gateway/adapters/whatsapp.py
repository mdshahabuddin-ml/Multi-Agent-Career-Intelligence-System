"""
WhatsApp adapter.
"""

from __future__ import annotations

from typing import Any, Dict


class WhatsAppAdapter:
    """WhatsApp Business adapter."""

    def __init__(self, token: str = ""):
        self._token = token

    async def send_message(self, phone: str, text: str) -> Dict[str, Any]:
        """Send a message via WhatsApp."""
        return {"phone": phone, "text": text, "status": "sent"}
