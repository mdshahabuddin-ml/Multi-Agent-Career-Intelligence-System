"""
Facebook Integration.
"""

from __future__ import annotations

from typing import Any, Dict
from .base import BaseIntegration


class FacebookIntegration(BaseIntegration):
    """Facebook API integration."""

    def __init__(self, access_token: str = ""):
        super().__init__("facebook", access_token)

    async def connect(self) -> bool:
        self._connected = True
        return True

    async def disconnect(self) -> bool:
        self._connected = False
        return True

    async def post(self, content: str, **kwargs: Any) -> Dict[str, Any]:
        return {"platform": "facebook", "status": "posted", "content": content}

    async def get_profile(self) -> Dict[str, Any]:
        return {"platform": "facebook", "name": "User"}
