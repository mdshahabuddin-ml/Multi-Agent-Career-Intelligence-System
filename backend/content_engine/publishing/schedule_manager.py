"""
Schedule Manager - Manages publishing schedules.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional


class ScheduleManager:
    """
    Manages publishing schedules.
    """

    def __init__(self):
        self._schedules: List[Dict[str, Any]] = []

    def add_schedule(
        self,
        content_id: str,
        platform: str,
        scheduled_at: datetime,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Add a schedule."""
        import uuid
        schedule_id = str(uuid.uuid4())

        self._schedules.append({
            "id": schedule_id,
            "content_id": content_id,
            "platform": platform,
            "scheduled_at": scheduled_at.isoformat(),
            "metadata": metadata or {},
        })

        return schedule_id

    def get_schedules(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get schedules within a date range."""
        return self._schedules

    def remove_schedule(self, schedule_id: str) -> bool:
        """Remove a schedule."""
        for i, schedule in enumerate(self._schedules):
            if schedule["id"] == schedule_id:
                self._schedules.pop(i)
                return True
        return False
