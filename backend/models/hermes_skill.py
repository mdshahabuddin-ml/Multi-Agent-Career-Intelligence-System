"""
Hermes Skill model - Stores agent skill definitions.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, ForeignKey, JSON, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class HermesSkill(Base):
    """Stores agent skill definitions."""
    __tablename__ = "hermes_skills"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    module_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    function_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # Owner + provenance for restart rehydration (Step B). Nullable so
    # pre-existing rows keep working; NULL-owner rows never rehydrate
    # (fail closed) until re-promoted with an owner.
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    template: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    parameters_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    tags_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    execution_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)


class HermesSkillExecution(Base):
    """Tracks skill execution history."""
    __tablename__ = "hermes_skill_executions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("hermes_skills.id"), index=True)
    agent_id: Mapped[str] = mapped_column(String(100), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    duration_ms: Mapped[Optional[float]] = mapped_column(nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    input_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    output_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
