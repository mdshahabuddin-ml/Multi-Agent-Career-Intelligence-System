from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class ResumeStatus(PyEnum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    FAILED = "failed"


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    file_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    status: Mapped[ResumeStatus] = mapped_column(
        Enum(ResumeStatus),
        default=ResumeStatus.UPLOADED,
        nullable=False,
    )

    raw_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    parsed_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    sections: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    extracted_skills: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    extracted_projects: Mapped[list[dict] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    extracted_experience: Mapped[list[dict] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    extracted_education: Mapped[list[dict] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    ats_score: Mapped[float | None] = mapped_column(
        nullable=True,
    )

    ats_feedback: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
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

    user: Mapped["User"] = relationship("User", back_populates="resumes")