from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class EvidenceType(PyEnum):
    DIRECT_QUOTE = "direct_quote"
    STATISTIC = "statistic"
    EXPERT_OPINION = "expert_opinion"
    CASE_STUDY = "case_study"
    SURVEY_RESULT = "survey_result"
    REPORT = "report"
    OTHER = "other"


class ResearchEvidence(Base):
    __tablename__ = "research_evidence"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    research_id: Mapped[int] = mapped_column(
        ForeignKey("research.id"),
        nullable=False,
        index=True,
    )

    claim_id: Mapped[int | None] = mapped_column(
        ForeignKey("research_claims.id"),
        nullable=True,
        index=True,
    )

    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("research_sources.id"),
        nullable=True,
        index=True,
    )

    evidence_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    evidence_type: Mapped[EvidenceType] = mapped_column(
        Enum(EvidenceType),
        default=EvidenceType.OTHER,
        nullable=False,
    )

    supports_claim: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    relevance_score: Mapped[float] = mapped_column(
        default=0.0,
        nullable=False,
    )

    confidence_score: Mapped[float] = mapped_column(
        default=0.0,
        nullable=False,
    )

    citation_context: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    evidence_metadata: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    research: Mapped["Research"] = relationship("Research", back_populates="evidence")
    claim: Mapped["ResearchClaim"] = relationship("ResearchClaim", back_populates="evidence")
    source: Mapped["ResearchSource"] = relationship("ResearchSource", back_populates="evidence")