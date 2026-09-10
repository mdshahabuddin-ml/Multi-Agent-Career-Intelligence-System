from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, List

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class SocialPlatform(str, PyEnum):
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    TIKTOK = "tiktok"


class ContentStatus(str, PyEnum):
    DRAFT = "draft"
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RETRY = "retry"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ContentType(str, PyEnum):
    POST = "post"
    STORY = "story"
    REEL = "reel"
    VIDEO = "video"
    SHORT = "short"
    ARTICLE = "article"
    THREAD = "thread"


class ContentCalendar(Base):
    __tablename__ = "content_calendar"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    # Optional link to the approved pipeline run this item was scheduled from.
    # Items scheduled through the approval flow always carry this link, which
    # is how "only APPROVED content can be scheduled" is enforced.
    pipeline_run_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("content_pipeline_runs.id"), nullable=True, index=True
    )

    # Content details
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[ContentType] = mapped_column(Enum(ContentType), default=ContentType.POST, nullable=False)

    # Platform targeting
    platform: Mapped[SocialPlatform] = mapped_column(Enum(SocialPlatform), nullable=False, index=True)
    platform_specific_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Media attachments
    media_urls: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Scheduling
    status: Mapped[ContentStatus] = mapped_column(Enum(ContentStatus), default=ContentStatus.DRAFT, nullable=False, index=True)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Recurring schedule
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recurrence_rule: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # RRULE format

    # Hashtags & mentions
    hashtags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    mentions: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)

    # SEO / metadata
    meta_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    meta_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Analytics (populated after publishing)
    platform_post_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    platform_post_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="content_calendar")
    analytics: Mapped[list["ContentAnalytics"]] = relationship("ContentAnalytics", back_populates="content", cascade="all, delete-orphan")


class ContentAnalytics(Base):
    __tablename__ = "content_analytics"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("content_calendar.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    # Platform metrics
    platform: Mapped[SocialPlatform] = mapped_column(Enum(SocialPlatform), nullable=False)
    platform_post_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Engagement metrics
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    likes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    shares: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    saves: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reach: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Video specific
    watch_time_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    average_watch_time: Mapped[float] = mapped_column(default=0.0, nullable=False)
    completion_rate: Mapped[float] = mapped_column(default=0.0, nullable=False)

    # Calculated rates
    engagement_rate: Mapped[float] = mapped_column(default=0.0, nullable=False)
    click_through_rate: Mapped[float] = mapped_column(default=0.0, nullable=False)

    # Raw platform data
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    content: Mapped["ContentCalendar"] = relationship("ContentCalendar", back_populates="analytics")
    user: Mapped["User"] = relationship("User")