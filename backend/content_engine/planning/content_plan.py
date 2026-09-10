"""
Content Plan - Content planning utilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ContentPlan:
    """A plan for content creation."""
    id: str
    title: str
    description: str = ""
    content_type: str = "post"
    platforms: List[str] = field(default_factory=list)
    target_audience: str = ""
    keywords: List[str] = field(default_factory=list)
    schedule_date: Optional[datetime] = None
    status: str = "draft"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "content_type": self.content_type,
            "platforms": self.platforms,
            "status": self.status,
        }
