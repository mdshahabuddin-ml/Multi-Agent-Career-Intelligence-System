from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"),
        nullable=True,
        index=True,
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

    profile: Mapped["Profile"] = relationship(
        "Profile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    resumes: Mapped[list["Resume"]] = relationship(
        "Resume",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    applications: Mapped[list["Application"]] = relationship(
        "Application",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    research_tasks: Mapped[list["Research"]] = relationship(
        "Research",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    interviews: Mapped[list["Interview"]] = relationship(
        "Interview",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    learning_plans: Mapped[list["LearningPlan"]] = relationship(
        "LearningPlan",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    notifications: Mapped[list["Notification"]] = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    preferences: Mapped["UserPreference"] = relationship(
        "UserPreference",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    behavior_logs: Mapped[list["UserBehaviorLog"]] = relationship(
        "UserBehaviorLog",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    interactions: Mapped[list["UserInteraction"]] = relationship(
        "UserInteraction",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    personalization_profile: Mapped["PersonalizationProfile"] = relationship(
        "PersonalizationProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="users",
    )