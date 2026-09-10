"""
Skill Manager - high-level interface for skill lifecycle management.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from .registry import SkillRegistry, SkillDisabledError
from .executor import SkillExecutor


class SkillManager:
    """
    Manages the complete lifecycle of agent skills.

    Provides registration, discovery, execution, and monitoring
    of skills that agents can use to accomplish tasks.
    """

    def __init__(self) -> None:
        self._registry = SkillRegistry()
        self._executor = SkillExecutor()

    def register(
        self,
        name: str,
        handler: Callable,
        description: str = "",
        parameters: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> None:
        """
        Register a new skill.

        Args:
            name: Unique name for the skill.
            handler: Async callable that implements the skill.
            description: Human-readable description.
            parameters: JSON schema for skill parameters.
            tags: Tags for categorization and discovery.
        """
        self._registry.register(
            name=name,
            handler=handler,
            description=description,
            parameters=parameters or {},
            tags=tags or [],
        )

    def unregister(self, name: str) -> bool:
        """Remove a skill by name. Returns True if removed."""
        return self._registry.unregister(name)

    def set_enabled(self, name: str, enabled: bool) -> bool:
        """Enable/disable a skill (kill-switch). Returns False if unknown."""
        return self._registry.set_enabled(name, enabled)

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """Get skill metadata by name."""
        return self._registry.get(name)

    def list_skills(self, tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all registered skills, optionally filtered by tag."""
        return self._registry.list_all(tag=tag)

    async def execute(
        self,
        skill_name: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        """
        Execute a registered skill.

        Args:
            skill_name: Name of the skill to execute.
            params: Parameters to pass to the skill handler.
            timeout: Optional timeout in seconds.

        Returns:
            The result of the skill execution.

        Raises:
            KeyError: If the skill is not registered.
            SkillDisabledError: If the skill is registered but disabled.
                Checked on every call so revocation takes effect immediately;
                raised before any counter increments or handler invocation.
            TimeoutError: If execution exceeds the timeout.
        """
        skill = self._registry.get(skill_name)
        if not skill:
            raise KeyError(f"Skill '{skill_name}' not found")
        if not skill.get("enabled", True):
            raise SkillDisabledError(f"Skill '{skill_name}' is disabled")

        try:
            result = await self._executor.execute(
                handler=skill["handler"],
                params=params or {},
                timeout=timeout,
            )
        except Exception:
            self._registry.record_execution(skill_name, False)
            raise
        self._registry.record_execution(skill_name, True)
        return result

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search skills by name or description."""
        return self._registry.search(query)

    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        return self._executor.get_stats()
