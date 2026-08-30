from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class SourceType(PyEnum):
    WEB = "web"
    NEWS = "news"
    ACADEMIC = "academic"
    COMPANY = "company"
    JOB_BOARD = "job_board"
    SOCIAL = "social"
    GOVERNMENT = "government"
    OTHER = "other"


class ResearchSource(Base):
    __tablename__ = "research_sources"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    research_id: Mapped[int] = mapped_column(
        ForeignKey("research.id"),
        nullable=False,
        index=True,
    )

    url: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    title: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType),
        default=SourceType.WEB,
        nullable=False,
    )

    domain: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    author: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    published_date: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    retrieved_date: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    credibility_score: Mapped[float] = mapped_column(
        default=0.0,
        nullable=False,
    )

    relevance_score: Mapped[float] = mapped_column(
        default=0.0,
        nullable=False,
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    source_metadata: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    research: Mapped["Research"] = relationship("Research", back_populates="sources")
    claims: Mapped[list["ResearchClaim"]] = relationship("ResearchClaim", back_populates="source")
    evidence: Mapped[list["ResearchEvidence"]] = relationship("ResearchEvidence", back_populates="source")