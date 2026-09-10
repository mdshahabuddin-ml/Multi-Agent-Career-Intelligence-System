"""
Skill Registry - catalog of available skills for agent use.
"""

from __future__ import annotations

import threading
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional


class SkillDisabledError(Exception):
    """Raised when execution of a disabled skill is attempted."""


class SkillRegistry:
    """
    Thread-safe registry of available skills.

    Stores skill metadata and handlers, providing lookup,
    search, and enumeration capabilities.
    """

    def __init__(self) -> None:
        self._skills: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def register(
        self,
        name: str,
        handler: Callable,
        description: str = "",
        parameters: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        enabled: bool = True,
    ) -> None:
        """Register a skill. Raises ValueError if name already exists."""
        with self._lock:
            if name in self._skills:
                raise ValueError(f"Skill '{name}' is already registered")

            self._skills[name] = {
                "name": name,
                "handler": handler,
                "description": description,
                "parameters": parameters or {},
                "tags": tags or [],
                "registered_at": datetime.utcnow().isoformat(),
                "execution_count": 0,
                "error_count": 0,
                "enabled": enabled,
            }

    def unregister(self, name: str) -> bool:
        """Remove a skill. Returns True if existed."""
        with self._lock:
            return self._skills.pop(name, None) is not None

    def set_enabled(self, name: str, enabled: bool) -> bool:
        """Enable/disable a skill (kill-switch). Returns False if unknown."""
        with self._lock:
            skill = self._skills.get(name)
            if not skill:
                return False
            skill["enabled"] = bool(enabled)
            return True

    def is_enabled(self, name: str) -> bool:
        """Current enabled state; unknown skills report False (never run)."""
        skill = self._skills.get(name)
        return bool(skill and skill.get("enabled", True))

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """Get skill metadata by name."""
        return self._skills.get(name)

    def has(self, name: str) -> bool:
        """Check if a skill is registered."""
        return name in self._skills

    def list_all(self, tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all skills, optionally filtered by tag."""
        results = []
        for skill in self._skills.values():
            if tag and tag not in skill["tags"]:
                continue
            results.append({
                "name": skill["name"],
                "description": skill["description"],
                "parameters": skill["parameters"],
                "tags": skill["tags"],
                "execution_count": skill["execution_count"],
                "error_count": skill["error_count"],
                "enabled": skill.get("enabled", True),
            })
        return results

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
                    "tags": skill["tags"],
                })
        return results

    def record_execution(self, name: str, success: bool) -> None:
        """Record an execution attempt for statistics."""
        with self._lock:
            skill = self._skills.get(name)
            if skill:
                skill["execution_count"] += 1
                if not success:
                    skill["error_count"] += 1

    def get_names(self) -> List[str]:
        """Get all registered skill names."""
        return list(self._skills.keys())
