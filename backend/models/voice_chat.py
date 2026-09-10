from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, List, Dict, Any

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class VoiceCommandType(str, PyEnum):
    """Types of voice commands supported."""
    NAVIGATE = "navigate"
    SEARCH_JOBS = "search_jobs"
    APPLY_JOB = "apply_job"
    CREATE_CONTENT = "create_content"
    SCHEDULE_CONTENT = "schedule_content"
    CHECK_APPLICATIONS = "check_applications"
    CHECK_ANALYTICS = "check_analytics"
    RESEARCH_TOPIC = "research_topic"
    ANALYZE_RESUME = "analyze_resume"
    GENERATE_COVER_LETTER = "generate_cover_letter"
    PREPARE_INTERVIEW = "prepare_interview"
    SET_REMINDER = "set_reminder"
    GET_HELP = "get_help"
    UNKNOWN = "unknown"


class VoiceCommandStatus(str, PyEnum):
    """Status of voice command processing."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class VoiceCommand(Base):
    __tablename__ = "voice_commands"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    # Audio data
    audio_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    transcript: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)

    # Parsed command
    command_type: Mapped[VoiceCommandType] = mapped_column(
        Enum(VoiceCommandType), default=VoiceCommandType.UNKNOWN, nullable=False
    )
    intent: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    entities: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float] = mapped_column(default=0.0, nullable=False)

    # Execution
    status: Mapped[VoiceCommandStatus] = mapped_column(
        Enum(VoiceCommandStatus), default=VoiceCommandStatus.PENDING, nullable=False
    )
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Response
    response_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_audio_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Metadata
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship("User")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id"), nullable=False, index=True)

    # Message content
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant, system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), default="text", nullable=False)  # text, voice, card, action

    # Context
    context: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    message_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # For voice messages
    audio_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # For action messages
    action_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    action_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship("User")
    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Context
    context: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    current_topic: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship("User")
    messages: Mapped[list["ChatMessage"]] = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")