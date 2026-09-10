"""
Automation model - Stores automation schedules.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, ForeignKey, JSON, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Automation(Base):
    """Stores automation definitions."""
    __tablename__ = "automations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    automation_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")
    automation_type: Mapped[str] = mapped_column(String(50), default="custom")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    schedule_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    trigger_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    execution_count: Mapped[int] = mapped_column(Integer, default=0)
    last_executed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)


class AutomationExecution(Base):
    """Tracks automation execution history."""
    __tablename__ = "automation_executions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    automation_id: Mapped[str] = mapped_column(ForeignKey("automations.automation_id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="running")
    input_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    output_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[Optional[float]] = mapped_column(nullable=True)
    started_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
