"""
Content State - State management for content engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class ContentState:
    """State for content operations."""
    content_id: str
    user_id: int
    status: str = "draft"
    content_type: str = "post"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content_id": self.content_id,
            "user_id": self.user_id,
            "status": self.status,
            "content_type": self.content_type,
            "metadata": self.metadata,
        }
