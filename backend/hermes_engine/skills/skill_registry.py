"""
Skill Registry - Catalog of available skills.
"""

from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Optional


class SkillRegistry:
    """
    Thread-safe registry of available skills.
    """

    def __init__(self):
        self._skills: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def register(
        self,
        name: str,
        handler: Callable,
        description: str = "",
        parameters: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> None:
        """Register a skill."""
        with self._lock:
            if name in self._skills:
                raise ValueError(f"Skill '{name}' already registered")

            self._skills[name] = {
                "name": name,
                "handler": handler,
                "description": description,
                "parameters": parameters or {},
                "tags": tags or [],
            }

    def unregister(self, name: str) -> bool:
        """Unregister a skill."""
        with self._lock:
            return self._skills.pop(name, None) is not None

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """Get skill by name."""
        return self._skills.get(name)

    def has(self, name: str) -> bool:
        """Check if skill exists."""
        return name in self._skills

    def list_all(self, tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all skills."""
        skills = []
        for skill in self._skills.values():
            if tag and tag not in skill["tags"]:
                continue
            skills.append({
                "name": skill["name"],
                "description": skill["description"],
                "tags": skill["tags"],
            })
        return skills

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search skills."""
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
