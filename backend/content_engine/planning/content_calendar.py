"""
Content Calendar - Calendar management for content.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional


class ContentCalendar:
    """
    Manages content scheduling and calendar.
    """

    def __init__(self):
        self._events: List[Dict[str, Any]] = []

    def add_event(
        self,
        title: str,
        date: datetime,
        content_type: str = "post",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Add a calendar event."""
        import uuid
        event_id = str(uuid.uuid4())

        self._events.append({
            "id": event_id,
            "title": title,
            "date": date.isoformat(),
            "content_type": content_type,
            "metadata": metadata or {},
        })

        return event_id

    def get_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get events within a date range."""
        events = self._events

        if start_date:
            events = [e for e in events if e["date"] >= start_date.isoformat()]
        if end_date:
            events = [e for e in events if e["date"] <= end_date.isoformat()]

        return events

    def remove_event(self, event_id: str) -> bool:
        """Remove a calendar event."""
        for i, event in enumerate(self._events):
            if event["id"] == event_id:
                self._events.pop(i)
                return True
        return False
