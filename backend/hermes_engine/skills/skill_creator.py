"""
Skill Creator - Creates skills dynamically.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional


class SkillCreator:
    """
    Creates skills dynamically from templates or code.
    """

    def __init__(self):
        self._templates: Dict[str, Dict[str, Any]] = {}

    def create_from_template(
        self,
        template_name: str,
        name: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a skill from a template."""
        template = self._templates.get(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")

        return {
            "name": name,
            "description": template.get("description", ""),
            "parameters": {**template.get("parameters", {}), **(params or {})},
            "handler": template.get("handler"),
            "tags": template.get("tags", []),
        }

    def create_from_function(
        self,
        name: str,
        func: Callable,
        description: str = "",
    ) -> Dict[str, Any]:
        """Create a skill from a function."""
        return {
            "name": name,
            "description": description,
            "handler": func,
            "parameters": {},
            "tags": [],
        }

    def add_template(
        self,
        name: str,
        template: Dict[str, Any],
    ) -> None:
        """Add a skill template."""
        self._templates[name] = template

    def list_templates(self) -> list:
        """List available templates."""
        return list(self._templates.keys())
