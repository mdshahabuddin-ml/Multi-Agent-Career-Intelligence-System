"""
MCP Registry - Registry of MCP tools.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class MCPRegistry:
    """
    Registry of available MCP tools and resources.
    """

    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        name: str,
        description: str = "",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Register a tool."""
        self._tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters or {},
        }

    def unregister(self, name: str) -> bool:
        """Unregister a tool."""
        return self._tools.pop(name, None) is not None

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools."""
        return list(self._tools.values())

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search tools."""
        query_lower = query.lower()
        return [
            t for t in self._tools.values()
            if query_lower in t["name"].lower() or query_lower in t["description"].lower()
        ]
