"""
Content Service - Content management operations.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ContentService:
    """
    Service for content management.
    """

    def __init__(self):
        self._content: Dict[str, Dict[str, Any]] = {}

    async def create(
        self,
        title: str,
        content_type: str = "post",
        body: str = "",
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a content item."""
        import uuid
        content_id = str(uuid.uuid4())

        self._content[content_id] = {
            "id": content_id,
            "title": title,
            "content_type": content_type,
            "body": body,
            "user_id": user_id,
            "status": "draft",
        }

        return {"content_id": content_id, "title": title}

    async def get(self, content_id: str) -> Optional[Dict[str, Any]]:
        """Get content by ID."""
        return self._content.get(content_id)

    async def list_content(
        self,
        user_id: Optional[int] = None,
        content_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List content items."""
        items = list(self._content.values())

        if user_id:
            items = [i for i in items if i.get("user_id") == user_id]
        if content_type:
            items = [i for i in items if i.get("content_type") == content_type]

        return items[:limit]

    async def update(
        self,
        content_id: str,
        updates: Dict[str, Any],
    ) -> bool:
        """Update content."""
        if content_id in self._content:
            self._content[content_id].update(updates)
            return True
        return False

    async def delete(self, content_id: str) -> bool:
        """Delete content."""
        return self._content.pop(content_id, None) is not None
