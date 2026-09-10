"""
Automation Manager - Orchestrates automated tasks.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class AutomationManager:
    """
    Manages automated task execution and workflows.
    """

    def __init__(self):
        self._automations: Dict[str, Dict[str, Any]] = {}
        self._schedules: Dict[str, Dict[str, Any]] = {}

    def create(
        self,
        name: str,
        handler: Callable,
        description: str = "",
        schedule: Optional[str] = None,
        trigger: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create an automation."""
        import uuid
        automation_id = str(uuid.uuid4())

        self._automations[automation_id] = {
            "id": automation_id,
            "name": name,
            "handler": handler,
            "description": description,
            "enabled": True,
            "created_at": datetime.utcnow().isoformat(),
            "execution_count": 0,
        }

        if schedule:
            self._schedules[automation_id] = {
                "cron": schedule,
                "last_run": None,
                "next_run": None,
            }

        logger.info(f"Created automation: {name} ({automation_id})")
        return automation_id

    def enable(self, automation_id: str) -> bool:
        """Enable an automation."""
        automation = self._automations.get(automation_id)
        if automation:
            automation["enabled"] = True
            return True
        return False

    def disable(self, automation_id: str) -> bool:
        """Disable an automation."""
        automation = self._automations.get(automation_id)
        if automation:
            automation["enabled"] = False
            return True
        return False

    async def execute(self, automation_id: str, data: Optional[Dict[str, Any]] = None) -> Any:
        """Execute an automation."""
        automation = self._automations.get(automation_id)
        if not automation:
            raise KeyError(f"Automation '{automation_id}' not found")

        if not automation["enabled"]:
            raise ValueError(f"Automation '{automation_id}' is disabled")

        automation["execution_count"] += 1
        return await automation["handler"](**(data or {}))

    def list_automations(self) -> List[Dict[str, Any]]:
        """List all automations."""
        return [
            {
                "id": a["id"],
                "name": a["name"],
                "description": a["description"],
                "enabled": a["enabled"],
                "execution_count": a["execution_count"],
            }
            for a in self._automations.values()
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get automation statistics."""
        return {
            "total": len(self._automations),
            "enabled": sum(1 for a in self._automations.values() if a["enabled"]),
            "disabled": sum(1 for a in self._automations.values() if not a["enabled"]),
        }
