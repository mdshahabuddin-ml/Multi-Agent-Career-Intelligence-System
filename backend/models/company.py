from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, JSON, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base
from backend.models.enums import SubscriptionTier


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    normalized_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    domain: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    industry: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    company_size: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    headquarters: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    founded_year: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    website: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    linkedin_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    logo_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    tech_stack: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
    )

    culture_tags: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
    )

    benefits: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
    )

    glassdoor_rating: Mapped[Optional[float]] = mapped_column(
        nullable=True,
    )

    glassdoor_reviews_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Subscription fields
    subscription_tier: Mapped[SubscriptionTier] = mapped_column(Enum(SubscriptionTier), default=SubscriptionTier.FREE, nullable=False)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True, index=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True, index=True)

    # Settings
    settings: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    branding: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Ownership
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Status
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

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

    # Relationships
    jobs: Mapped[List["Job"]] = relationship("Job", back_populates="company")
    members: Mapped[List["CompanyMember"]] = relationship("CompanyMember", back_populates="company", cascade="all, delete-orphan")
    owner: Mapped["User"] = relationship("User", foreign_keys=[owner_id], back_populates="owned_companies")