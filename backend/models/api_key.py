"""
API Key model - Stores hashed user API keys for programmatic access.

Stores ONLY hashed_key (sha256/sha512 hex). Raw keys are returned
once at creation/rotation time and never persisted or re-exposed.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class ApiKey(Base):
    """Persisted API key record (hashed only)."""

    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)

    prefix: Mapped[str] = mapped_column(String(16), nullable=False, index=True)

    hashed_key: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, index=True
    )

    scopes: Mapped[list] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    # DB column is "metadata"; python attr avoids Base.metadata conflict.
    key_metadata: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSON, nullable=True
    )
