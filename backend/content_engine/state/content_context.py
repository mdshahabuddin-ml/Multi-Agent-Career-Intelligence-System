"""
Content Context - Context for content operations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ContentContext:
    """Context for content operations."""
    user_id: int
    platform: Optional[str] = None
    audience: Optional[str] = None
    tone: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
