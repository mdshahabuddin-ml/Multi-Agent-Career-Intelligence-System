"""
Trigger Manager - Manages event triggers.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class TriggerManager:
    """
    Manages event triggers for automations.
    """

    def __init__(self):
        self._triggers: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        name: str,
        event_type: str,
        handler: Callable,
        conditions: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Register a trigger."""
        self._triggers[name] = {
            "name": name,
            "event_type": event_type,
            "handler": handler,
            "conditions": conditions or {},
            "enabled": True,
            "fire_count": 0,
        }
        logger.info(f"Registered trigger: {name}")

    def unregister(self, name: str) -> bool:
        """Unregister a trigger."""
        return self._triggers.pop(name, None) is not None

    async def fire(
        self,
        event_type: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> List[Any]:
        """Fire all triggers matching an event type."""
        results = []
        for trigger in self._triggers.values():
            if trigger["event_type"] == event_type and trigger["enabled"]:
                if self._check_conditions(trigger["conditions"], data or {}):
                    try:
                        result = await trigger["handler"](**(data or {}))
                        trigger["fire_count"] += 1
                        results.append(result)
                    except Exception as e:
                        logger.error(f"Trigger '{trigger['name']}' failed: {e}")
        return results

    def _check_conditions(
        self,
        conditions: Dict[str, Any],
        data: Dict[str, Any],
    ) -> bool:
        """Check if trigger conditions are met."""
        for key, value in conditions.items():
            if data.get(key) != value:
                return False
        return True

    def list_triggers(self) -> List[Dict[str, Any]]:
        """List all triggers."""
        return [
            {
                "name": t["name"],
                "event_type": t["event_type"],
                "enabled": t["enabled"],
                "fire_count": t["fire_count"],
            }
            for t in self._triggers.values()
        ]
