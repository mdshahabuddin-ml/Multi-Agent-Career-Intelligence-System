from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, List

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class NotificationChannel(str, PyEnum):
    EMAIL = "email"
    PUSH = "push"
    IN_APP = "in_app"
    SMS = "sms"
    WEBHOOK = "webhook"


class NotificationFrequency(str, PyEnum):
    REAL_TIME = "real_time"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    NEVER = "never"


class JobAlertFrequency(str, PyEnum):
    REAL_TIME = "real_time"
    DAILY = "daily"
    WEEKLY = "weekly"
    NEVER = "never"


class ThemeMode(str, PyEnum):
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


class ContentDensity(str, PyEnum):
    COMPACT = "compact"
    COMFORTABLE = "comfortable"
    SPACIOUS = "spacious"


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), unique=True, nullable=False, index=True
    )

    # Job Preferences
    preferred_job_types: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    preferred_locations: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    preferred_remote_types: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    min_salary: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    preferred_industries: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    excluded_companies: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    excluded_keywords: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    salary_currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    job_alert_frequency: Mapped[JobAlertFrequency] = mapped_column(
        default=JobAlertFrequency.DAILY, nullable=False
    )
    job_alert_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Notification Preferences
    email_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    in_app_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notification_channels: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    notification_frequency: Mapped[NotificationFrequency] = mapped_column(
        default=NotificationFrequency.DAILY, nullable=False
    )
    quiet_hours_start: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)  # HH:MM
    quiet_hours_end: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)

    # Content & UI Preferences
    theme_mode: Mapped[ThemeMode] = mapped_column(default=ThemeMode.SYSTEM, nullable=False)
    content_density: Mapped[ContentDensity] = mapped_column(default=ContentDensity.COMFORTABLE, nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    date_format: Mapped[str] = mapped_column(String(20), default="YYYY-MM-DD", nullable=False)
    time_format: Mapped[str] = mapped_column(String(10), default="24h", nullable=False)
    show_salary_estimates: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_save_drafts: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    compact_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Privacy & Data
    profile_visibility: Mapped[str] = mapped_column(String(20), default="private", nullable=False)  # private, connections, public
    data_sharing_consent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    analytics_opt_out: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    marketing_emails: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    third_party_integrations: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Learning & Career Preferences
    learning_style: Mapped[str] = mapped_column(String(20), default="mixed", nullable=False)  # visual, reading, hands-on, mixed
    skill_gap_priority: Mapped[str] = mapped_column(String(20), default="market_demand", nullable=False)  # market_demand, interest, career_goal
    preferred_learning_platforms: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    weekly_learning_hours: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Recommendation Weights
    rec_weight_skills_match: Mapped[float] = mapped_column(Float, default=0.35, nullable=False)
    rec_weight_salary: Mapped[float] = mapped_column(Float, default=0.25, nullable=False)
    rec_weight_location: Mapped[float] = mapped_column(Float, default=0.20, nullable=False)
    rec_weight_company_culture: Mapped[float] = mapped_column(Float, default=0.10, nullable=False)
    rec_weight_growth_potential: Mapped[float] = mapped_column(Float, default=0.10, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="preferences")


class UserBehaviorLog(Base):
    __tablename__ = "user_behavior_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # page_view, click, search, apply, save, etc.
    event_category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # job, company, research, learning, profile
    event_action: Mapped[str] = mapped_column(String(100), nullable=False)
    event_label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    event_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Context
    page_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    referrer: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    device_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # desktop, mobile, tablet
    browser: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Entity references
    entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # job, company, course, research
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Metadata
    event_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user: Mapped["User"] = relationship("User", back_populates="behavior_logs")


class UserInteraction(Base):
    __tablename__ = "user_interactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    interaction_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # view, click, save, apply, share, rate, feedback
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # job, company, course, article, research
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Interaction details
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    scroll_depth: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0.0 to 1.0
    click_position: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Feedback
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-5
    feedback_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_positive: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Context
    source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # search, recommendation, direct, email
    context: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="interactions")


class PersonalizationProfile(Base):
    __tablename__ = "personalization_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False, index=True)

    # Computed preferences from behavior
    inferred_skills: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    inferred_interests: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    inferred_seniority: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    inferred_job_functions: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    inferred_industries: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    inferred_work_style: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # remote-first, hybrid, office, flexible

    # Engagement scores
    job_search_engagement: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    learning_engagement: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    research_engagement: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    community_engagement: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Preference vectors for ML
    skill_vector: Mapped[Optional[List[float]]] = mapped_column(JSON, nullable=True)
    company_vector: Mapped[Optional[List[float]]] = mapped_column(JSON, nullable=True)
    role_vector: Mapped[Optional[List[float]]] = mapped_column(JSON, nullable=True)

    # Model metadata
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    model_version: Mapped[str] = mapped_column(String(20), default="1.0", nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Feature flags
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    manual_override: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="personalization_profile")


# Add relationship to User model
# This would be added to the User model:
# preferences: Mapped["UserPreference"] = relationship("UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")
# behavior_logs: Mapped[list["UserBehaviorLog"]] = relationship("UserBehaviorLog", back_populates="user", cascade="all, delete-orphan")
# interactions: Mapped[list["UserInteraction"]] = relationship("UserInteraction", back_populates="user", cascade="all, delete-orphan")
# personalization_profile: Mapped["PersonalizationProfile"] = relationship("PersonalizationProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")