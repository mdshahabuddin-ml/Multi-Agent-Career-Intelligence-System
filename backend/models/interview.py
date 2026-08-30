from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Float, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class InterviewType(PyEnum):
    MOCK = "mock"
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    SYSTEM_DESIGN = "system_design"
    CASE_STUDY = "case_study"
    CODING = "coding"


class InterviewStatus(PyEnum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    application_id: Mapped[int | None] = mapped_column(
        ForeignKey("applications.id"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    interview_type: Mapped[InterviewType] = mapped_column(
        Enum(InterviewType),
        default=InterviewType.MOCK,
        nullable=False,
    )

    status: Mapped[InterviewStatus] = mapped_column(
        Enum(InterviewStatus),
        default=InterviewStatus.SCHEDULED,
        nullable=False,
    )

    target_role: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    target_company: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    questions: Mapped[list[dict] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    answers: Mapped[list[dict] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    evaluations: Mapped[list[dict] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    overall_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    feedback: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    strengths: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    weaknesses: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    improvement_areas: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    duration_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
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

    user: Mapped["User"] = relationship("User", back_populates="interviews")
    application: Mapped["Application"] = relationship("Application", back_populates="interviews")