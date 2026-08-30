from datetime import datetime, date
from enum import Enum as PyEnum

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class LearningResourceType(PyEnum):
    COURSE = "course"
    BOOK = "book"
    ARTICLE = "article"
    VIDEO = "video"
    CERTIFICATION = "certification"
    PROJECT = "project"
    PRACTICE = "practice"


class LearningStatus(PyEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class LearningPlan(Base):
    __tablename__ = "learning_plans"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    target_role: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    skill_gaps: Mapped[list[dict] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    estimated_weeks: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    resources: Mapped[list[dict] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    milestones: Mapped[list[dict] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    status: Mapped[LearningStatus] = mapped_column(
        Enum(LearningStatus),
        default=LearningStatus.NOT_STARTED,
        nullable=False,
    )

    progress_percentage: Mapped[float] = mapped_column(
        default=0.0,
        nullable=False,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    target_completion_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="learning_plans")