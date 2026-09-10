"""
Publishing Status - Tracks publishing status.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional


class PublishingStatus:
    """
    Tracks publishing status across platforms.
    """

    def __init__(self):
        self._statuses: Dict[str, Dict[str, Any]] = {}

    def update(
        self,
        content_id: str,
        platform: str,
        status: str,
        post_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update publishing status."""
        key = f"{content_id}:{platform}"
        self._statuses[key] = {
            "content_id": content_id,
            "platform": platform,
            "status": status,
            "post_id": post_id,
            "metadata": metadata or {},
            "updated_at": datetime.utcnow().isoformat(),
        }

    def get_status(self, content_id: str) -> List[Dict[str, Any]]:
        """Get status for a content item."""
        return [
            v for k, v in self._statuses.items()
            if k.startswith(f"{content_id}:")
        ]

    def get_all(self) -> List[Dict[str, Any]]:
        """Get all statuses."""
        return list(self._statuses.values())
