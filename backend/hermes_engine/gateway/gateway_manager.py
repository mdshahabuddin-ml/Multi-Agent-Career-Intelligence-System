"""
Gateway Manager - Manages external service integrations.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class GatewayManager:
    """
    Manages gateway routing and external integrations.
    """

    def __init__(self):
        self._routes: Dict[str, Dict[str, Any]] = {}
        self._middleware: List[Callable] = []

    def register_route(
        self,
        path: str,
        handler: Callable,
        methods: Optional[List[str]] = None,
    ) -> None:
        """Register a route."""
        self._routes[path] = {
            "handler": handler,
            "methods": methods or ["GET"],
        }

    def unregister_route(self, path: str) -> bool:
        """Unregister a route."""
        return self._routes.pop(path, None) is not None

    def add_middleware(self, middleware: Callable) -> None:
        """Add middleware."""
        self._middleware.append(middleware)

    async def route(
        self,
        path: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Route a request."""
        route_info = self._routes.get(path)
        if not route_info:
            return {"error": f"No route for {method} {path}"}

        if method not in route_info["methods"]:
            return {"error": f"Method {method} not allowed"}

        handler = route_info["handler"]
        try:
            result = await handler(path=path, method=method, data=data)
            return result if isinstance(result, dict) else {"result": result}
        except Exception as e:
            return {"error": str(e)}

    def list_routes(self) -> List[Dict[str, Any]]:
        """List all routes."""
        return [
            {"path": path, "methods": info["methods"]}
            for path, info in self._routes.items()
        ]
