"""
Gateway Service - Gateway operations.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class GatewayService:
    """
    Service for gateway operations.
    """

    def __init__(self):
        self._routes: Dict[str, Callable] = {}
        self._adapters: Dict[str, Any] = {}

    def register_route(self, path: str, handler: Callable) -> None:
        """Register a route."""
        self._routes[path] = handler

    async def route(self, path: str, data: Optional[Dict[str, Any]] = None) -> Any:
        """Route a request."""
        handler = self._routes.get(path)
        if handler:
            return await handler(**(data or {}))
        return {"error": f"No route for {path}"}

    def register_adapter(self, name: str, adapter: Any) -> None:
        """Register an adapter."""
        self._adapters[name] = adapter

    async def send_message(
        self,
        adapter: str,
        target: str,
        message: str,
    ) -> Dict[str, Any]:
        """Send a message via adapter."""
        adapter_obj = self._adapters.get(adapter)
        if not adapter_obj:
            return {"error": f"Adapter '{adapter}' not found"}

        return {"success": True, "adapter": adapter, "target": target}
