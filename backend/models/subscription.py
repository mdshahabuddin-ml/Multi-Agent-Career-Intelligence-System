from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, JSON, Enum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base
from backend.models.enums import (
    SubscriptionTier,
    SubscriptionStatus,
    BillingInterval,
    UserType,
    CompanyRole,
)


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # Stripe info
    stripe_customer_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True, index=True)
    stripe_price_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Subscription details
    tier: Mapped[SubscriptionTier] = mapped_column(Enum(SubscriptionTier), default=SubscriptionTier.FREE, nullable=False, index=True)
    status: Mapped[SubscriptionStatus] = mapped_column(Enum(SubscriptionStatus), default=SubscriptionStatus.INCOMPLETE, nullable=False)
    interval: Mapped[BillingInterval] = mapped_column(Enum(BillingInterval), default=BillingInterval.MONTHLY, nullable=False)

    # Period
    current_period_start: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    current_period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    canceled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    trial_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Usage tracking (reset each period)
    research_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    content_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    api_calls_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    job_posts_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    candidate_searches_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Metadata
    subscription_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="subscription")

    __table_args__ = (
        Index('ix_user_sub_status_tier', 'status', 'tier'),
        Index('ix_user_sub_period_end', 'current_period_end'),
    )


from backend.models.company import Company


class CompanyMember(Base):
    __tablename__ = "company_members"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    # Role & permissions
    role: Mapped[CompanyRole] = mapped_column(Enum(CompanyRole), default=CompanyRole.MEMBER, nullable=False)
    permissions: Mapped[Dict[str, bool]] = mapped_column(JSON, nullable=False, default=dict)

    # Invitation
    invited_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    invited_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    joined_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)

    # Metadata
    member_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="members")
    user: Mapped["User"] = relationship("User", foreign_keys="CompanyMember.user_id", back_populates="company_memberships")
    inviter: Mapped[Optional["User"]] = relationship("User", foreign_keys="CompanyMember.invited_by")

    __table_args__ = (
        Index('ix_company_member_company_user', 'company_id', 'user_id', unique=True),
        Index('ix_company_member_status', 'status'),
    )


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # User type
    user_type: Mapped[UserType] = mapped_column(Enum(UserType), default=UserType.INDIVIDUAL, nullable=False, index=True)

    # Profile info
    headline: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)

    # Career info
    current_role: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    current_company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    years_experience: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    skills: Mapped[List[str]] = mapped_column(JSON, nullable=True, default=list)
    target_role: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    desired_salary_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    desired_salary_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Creator info
    brand_voice: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    content_niches: Mapped[List[str]] = mapped_column(JSON, nullable=True, default=list)
    social_accounts: Mapped[Optional[Dict[str, str]]] = mapped_column(JSON, nullable=True)

    # Preferences
    email_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    weekly_digest: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    marketing_emails: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Privacy
    profile_visibility: Mapped[str] = mapped_column(String(50), default="public", nullable=False)
    show_salary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    open_to_work: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    open_to_hire: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="user_profile", uselist=False)