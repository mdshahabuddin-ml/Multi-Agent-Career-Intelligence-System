"""
Gateway Router - routes requests between agents and external services.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional


class GatewayRouter:
    """
    Routes requests between internal agents and external services.

    Provides a unified interface for API gateway functionality,
    including request routing, rate limiting, and response transformation.
    """

    def __init__(self) -> None:
        self._routes: Dict[str, Dict[str, Any]] = {}
        self._middleware: List[Callable] = []

    def register_route(
        self,
        path: str,
        handler: Callable,
        methods: Optional[List[str]] = None,
        middleware: Optional[List[Callable]] = None,
    ) -> None:
        """
        Register a route handler.

        Args:
            path: The route path pattern.
            handler: The handler function.
            methods: Allowed HTTP methods. Defaults to ["GET"].
            middleware: Optional middleware functions.
        """
        self._routes[path] = {
            "handler": handler,
            "methods": methods or ["GET"],
            "middleware": middleware or [],
        }

    def unregister_route(self, path: str) -> bool:
        """Remove a route. Returns True if it existed."""
        return self._routes.pop(path, None) is not None

    def add_middleware(self, middleware: Callable) -> None:
        """Add global middleware."""
        self._middleware.append(middleware)

    async def route(
        self,
        path: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Route a request to the appropriate handler.

        Args:
            path: The request path.
            method: The HTTP method.
            data: Optional request data.

        Returns:
            The response from the handler.
        """
        route_info = self._routes.get(path)
        if not route_info:
            return {"error": f"No route found for {method} {path}"}

        if method not in route_info["methods"]:
            return {"error": f"Method {method} not allowed for {path}"}

        # Apply global middleware
        for mw in self._middleware:
            result = await self._apply_middleware(mw, path, method, data)
            if result is not None:
                return result

        # Apply route-specific middleware
        for mw in route_info["middleware"]:
            result = await self._apply_middleware(mw, path, method, data)
            if result is not None:
                return result

        # Call handler
        handler = route_info["handler"]
        if callable(handler):
            result = await handler(path=path, method=method, data=data)
            return result if isinstance(result, dict) else {"result": result}

        return {"error": "Invalid handler"}

    @staticmethod
    async def _apply_middleware(
        middleware: Callable,
        path: str,
        method: str,
        data: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Apply a middleware function. Returns response if middleware short-circuits."""
        try:
            result = await middleware(path=path, method=method, data=data)
            return result
        except Exception:
            return None

    def list_routes(self) -> List[Dict[str, Any]]:
        """List all registered routes."""
        return [
            {
                "path": path,
                "methods": info["methods"],
            }
            for path, info in self._routes.items()
        ]
