"""
Social Post model - Tracks social media posts.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, ForeignKey, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class SocialPost(Base):
    """Tracks social media posts."""
    __tablename__ = "social_posts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("social_accounts.id"), index=True)
    content_id: Mapped[Optional[int]] = mapped_column(ForeignKey("content.id"), nullable=True)
    platform_post_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    content_text: Mapped[str] = mapped_column(Text, default="")
    media_urls_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    likes_count: Mapped[int] = mapped_column(Integer, default=0)
    comments_count: Mapped[int] = mapped_column(Integer, default=0)
    shares_count: Mapped[int] = mapped_column(Integer, default=0)
    impressions_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
