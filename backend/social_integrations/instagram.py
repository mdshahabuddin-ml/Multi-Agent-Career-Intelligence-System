"""
Instagram Integration.
"""

from __future__ import annotations

from typing import Any, Dict
from .base import BaseIntegration


class InstagramIntegration(BaseIntegration):
    """Instagram API integration."""

    def __init__(self, access_token: str = ""):
        super().__init__("instagram", access_token)

    async def connect(self) -> bool:
        self._connected = True
        return True

    async def disconnect(self) -> bool:
        self._connected = False
        return True

    async def post(self, content: str, image_url: str = "", **kwargs: Any) -> Dict[str, Any]:
        return {"platform": "instagram", "status": "posted", "content": content}

    async def get_profile(self) -> Dict[str, Any]:
        return {"platform": "instagram", "username": "user"}

    async def get_media(self, limit: int = 10) -> list:
        return []
