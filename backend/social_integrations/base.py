"""
Base Integration - Base class for social integrations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseIntegration(ABC):
    """Base class for social media integrations."""

    def __init__(self, platform: str, access_token: str = ""):
        self.platform = platform
        self._access_token = access_token
        self._connected = False

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the platform."""
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from the platform."""
        pass

    @abstractmethod
    async def post(self, content: str, **kwargs: Any) -> Dict[str, Any]:
        """Post content to the platform."""
        pass

    @abstractmethod
    async def get_profile(self) -> Dict[str, Any]:
        """Get user profile."""
        pass

    @property
    def is_connected(self) -> bool:
        return self._connected
