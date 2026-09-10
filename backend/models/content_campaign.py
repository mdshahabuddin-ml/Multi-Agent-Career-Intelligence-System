"""
Content Campaign model - Stores content campaigns.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, ForeignKey, JSON, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class ContentCampaign(Base):
    """Stores content campaigns."""
    __tablename__ = "content_campaigns"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    campaign_type: Mapped[str] = mapped_column(String(50), default="content")
    status: Mapped[str] = mapped_column(String(20), default="draft")
    start_date: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    target_platforms_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    goals_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    content_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
