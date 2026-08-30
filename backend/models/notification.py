from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class NotificationType(PyEnum):
    JOB_MATCH = "job_match"
    APPLICATION_UPDATE = "application_update"
    INTERVIEW_REMINDER = "interview_reminder"
    RESEARCH_COMPLETE = "research_complete"
    RESUME_ANALYSIS = "resume_analysis"
    SKILL_GAP_ALERT = "skill_gap_alert"
    LEARNING_MILESTONE = "learning_milestone"
    SYSTEM = "system"


class NotificationPriority(PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType),
        default=NotificationType.SYSTEM,
        nullable=False,
    )

    priority: Mapped[NotificationPriority] = mapped_column(
        Enum(NotificationPriority),
        default=NotificationPriority.MEDIUM,
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    action_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    action_label: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    notification_metadata: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    read_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="notifications")