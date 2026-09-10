"""
Skill Service - Skill management operations.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class SkillService:
    """
    Service for skill management.
    """

    def __init__(self):
        self._skills: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        name: str,
        handler: Callable,
        description: str = "",
    ) -> None:
        """Register a skill."""
        self._skills[name] = {
            "name": name,
            "handler": handler,
            "description": description,
            "execution_count": 0,
        }

    async def execute(
        self,
        name: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute a skill."""
        skill = self._skills.get(name)
        if not skill:
            raise KeyError(f"Skill '{name}' not found")

        skill["execution_count"] += 1
        return await skill["handler"](**(params or {}))

    def list_skills(self) -> List[Dict[str, Any]]:
        """List all skills."""
        return [
            {"name": s["name"], "description": s["description"], "execution_count": s["execution_count"]}
            for s in self._skills.values()
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get skill statistics."""
        return {"total": len(self._skills)}
