from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class ClaimStatus(PyEnum):
    EXTRACTED = "extracted"
    VERIFIED = "verified"
    CONFLICTING = "conflicting"
    UNVERIFIED = "unverified"
    REJECTED = "rejected"


class ResearchClaim(Base):
    __tablename__ = "research_claims"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    research_id: Mapped[int] = mapped_column(
        ForeignKey("research.id"),
        nullable=False,
        index=True,
    )

    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("research_sources.id"),
        nullable=True,
        index=True,
    )

    claim_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    claim_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    status: Mapped[ClaimStatus] = mapped_column(
        Enum(ClaimStatus),
        default=ClaimStatus.EXTRACTED,
        nullable=False,
    )

    confidence: Mapped[float] = mapped_column(
        default=0.0,
        nullable=False,
    )

    verified_by_sources: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    conflicting_sources: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    claim_metadata: Mapped[dict | None] = mapped_column(
        JSON,
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

    research: Mapped["Research"] = relationship("Research", back_populates="claims")
    source: Mapped["ResearchSource"] = relationship("ResearchSource", back_populates="claims")
    evidence: Mapped[list["ResearchEvidence"]] = relationship("ResearchEvidence", back_populates="claim")