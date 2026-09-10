"""Content pipeline run - DB-backed tracking for the Career-to-Content pipeline.

Persists every stage (intake -> research -> generation -> fact/quality check
-> formatting -> human approval) so runs survive restarts, unlike the
in-memory hermes_engine state.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import JSON, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class PipelineStage(str, PyEnum):
    DRAFT = "draft"
    INTAKE = "intake"
    TOPIC_SELECTION = "topic_selection"
    RESEARCH = "research"
    # REVIEW_REQUIRED is the canonical pre-publish gate. It aliases
    # PENDING_REVIEW so existing rows and API payloads keep working.
    PENDING_REVIEW = "pending_review"
    REVIEW_REQUIRED = "pending_review"
    GENERATION = "generation"
    VERIFICATION = "verification"
    FORMATTING = "formatting"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"


class ContentKind(str, PyEnum):
    LINKEDIN_POST = "linkedin_post"
    EDUCATIONAL = "educational"
    PROJECT_POST = "project_post"
    ACHIEVEMENT_POST = "achievement_post"
    CERTIFICATION_POST = "certification_post"
    CAREER_POST = "career_post"
    SHORT_VIDEO_SCRIPT = "short_video_script"


class PipelineSource(str, PyEnum):
    RESUME = "resume"
    PROFILE = "profile"
    PROJECT = "project"
    CERTIFICATION = "certification"
    ACHIEVEMENT = "achievement"
    RESEARCH = "research"
    LEARNING = "learning"


class ContentPipelineRun(Base):
    """One Career-to-Content pipeline execution."""

    __tablename__ = "content_pipeline_runs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    # What career material seeded this run
    source: Mapped[PipelineSource] = mapped_column(Enum(PipelineSource), nullable=False)
    source_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # What to produce, and for which platforms
    content_kind: Mapped[ContentKind] = mapped_column(Enum(ContentKind), nullable=False)
    platforms: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # Lifecycle
    status: Mapped[PipelineStage] = mapped_column(
        Enum(PipelineStage), default=PipelineStage.INTAKE, nullable=False, index=True
    )
    current_stage: Mapped[str] = mapped_column(String(50), default=PipelineStage.INTAKE.value)

    # Stage outputs (brief, research, draft, verification, formatted variants)
    stage_results: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Human approval audit
    reviewed_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="content_pipeline_runs")
