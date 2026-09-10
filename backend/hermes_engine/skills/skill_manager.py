"""
Skill Manager - Manages agent skills lifecycle.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class SkillDisabledError(Exception):
    """Raised when execution of a disabled skill is attempted."""


class SkillManager:
    """
    Manages the complete lifecycle of agent skills.
    """

    def __init__(self):
        self._skills: Dict[str, Dict[str, Any]] = {}
        self._executions: List[Dict[str, Any]] = []

    def register(
        self,
        name: str,
        handler: Callable,
        description: str = "",
        parameters: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> None:
        """Register a skill."""
        self._skills[name] = {
            "name": name,
            "handler": handler,
            "description": description,
            "parameters": parameters or {},
            "tags": tags or [],
            "execution_count": 0,
            "error_count": 0,
            "enabled": True,
        }
        logger.info(f"Registered skill: {name}")

    def unregister(self, name: str) -> bool:
        """Unregister a skill."""
        if name in self._skills:
            del self._skills[name]
            return True
        return False

    def set_enabled(self, name: str, enabled: bool) -> bool:
        """Enable/disable a skill (kill-switch). Returns False if unknown."""
        skill = self._skills.get(name)
        if not skill:
            return False
        skill["enabled"] = bool(enabled)
        return True

    async def execute(
        self,
        name: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        """Execute a skill.

        Raises:
            KeyError: If the skill is not registered.
            SkillDisabledError: If the skill is registered but disabled.
                Checked on every call so revocation takes effect immediately;
                raised before any counter increments or handler invocation.
        """
        skill = self._skills.get(name)
        if not skill:
            raise KeyError(f"Skill '{name}' not found")
        if not skill.get("enabled", True):
            raise SkillDisabledError(f"Skill '{name}' is disabled")

        import asyncio
        import time

        start = time.monotonic()
        skill["execution_count"] += 1

        try:
            if timeout:
                result = await asyncio.wait_for(
                    skill["handler"](**(params or {})),
                    timeout=timeout,
                )
            else:
                result = await skill["handler"](**(params or {}))

            duration = (time.monotonic() - start) * 1000
            self._executions.append({
                "skill": name,
                "success": True,
                "duration_ms": duration,
            })
            return result

        except Exception as e:
            skill["error_count"] += 1
            self._executions.append({
                "skill": name,
                "success": False,
                "error": str(e),
            })
            raise

    def list_skills(self, tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all registered skills."""
        skills = []
        for skill in self._skills.values():
            if tag and tag not in skill["tags"]:
                continue
            skills.append({
                "name": skill["name"],
                "description": skill["description"],
                "tags": skill["tags"],
                "execution_count": skill["execution_count"],
                "error_count": skill["error_count"],
            })
        return skills

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search skills by name or description."""
        query_lower = query.lower()
        results = []
        for skill in self._skills.values():
            if (
                query_lower in skill["name"].lower()
                or query_lower in skill["description"].lower()
            ):
                results.append({
                    "name": skill["name"],
                    "description": skill["description"],
                })
        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        total = len(self._executions)
        successful = sum(1 for e in self._executions if e["success"])
        return {
            "total_skills": len(self._skills),
            "total_executions": total,
            "successful": successful,
            "failed": total - successful,
        }
