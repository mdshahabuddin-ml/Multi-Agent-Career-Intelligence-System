"""
Campaign Planner - Campaign planning utilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Campaign:
    """A content campaign."""
    id: str
    name: str
    description: str = ""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    platforms: List[str] = field(default_factory=list)
    goals: Dict[str, Any] = field(default_factory=dict)
    status: str = "draft"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "platforms": self.platforms,
            "status": self.status,
        }
