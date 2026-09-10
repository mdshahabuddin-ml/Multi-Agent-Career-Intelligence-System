"""
Content model - Stores content items.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, ForeignKey, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Content(Base):
    """Stores content items."""
    __tablename__ = "content"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    campaign_id: Mapped[Optional[int]] = mapped_column(ForeignKey("content_campaigns.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    content_type: Mapped[str] = mapped_column(String(50), default="post")
    body: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    quality_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
