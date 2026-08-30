from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class ResearchStatus(PyEnum):
    CREATED = "created"
    PLANNING = "planning"
    RESEARCHING = "researching"
    COLLECTING_EVIDENCE = "collecting_evidence"
    VERIFYING = "verifying"
    ANALYZING = "analyzing"
    SYNTHESIZING = "synthesizing"
    COMPLETED = "completed"
    FAILED = "failed"


class ResearchType(PyEnum):
    JOB_MARKET = "job_market"
    COMPANY = "company"
    TECHNOLOGY = "technology"
    CAREER_PATH = "career_path"
    SKILL_ANALYSIS = "skill_analysis"
    SALARY = "salary"
    INTERVIEW_PREP = "interview_prep"
    GENERAL = "general"


class Research(Base):
    __tablename__ = "research"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    query: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    research_type: Mapped[ResearchType] = mapped_column(
        Enum(ResearchType),
        default=ResearchType.GENERAL,
        nullable=False,
    )

    status: Mapped[ResearchStatus] = mapped_column(
        Enum(ResearchStatus),
        default=ResearchStatus.CREATED,
        nullable=False,
        index=True,
    )

    research_plan: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    target_role: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    target_company: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    target_location: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    max_sources: Mapped[int] = mapped_column(
        Integer,
        default=10,
        nullable=False,
    )

    timeout_seconds: Mapped[int] = mapped_column(
        Integer,
        default=300,
        nullable=False,
    )

    report: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    executive_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    key_findings: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    recommendations: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    confidence_score: Mapped[float | None] = mapped_column(
        nullable=True,
    )

    source_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    verified_claim_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    progress: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    report_data: Mapped[dict | None] = mapped_column(
        JSON,
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

    user: Mapped["User"] = relationship("User", back_populates="research_tasks")
    sources: Mapped[list["ResearchSource"]] = relationship("ResearchSource", back_populates="research")
    claims: Mapped[list["ResearchClaim"]] = relationship("ResearchClaim", back_populates="research")
    evidence: Mapped[list["ResearchEvidence"]] = relationship("ResearchEvidence", back_populates="research")