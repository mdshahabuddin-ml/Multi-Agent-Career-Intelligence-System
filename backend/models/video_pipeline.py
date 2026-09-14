"""
VideoPipeline model - tracks video generation from content to final MP4.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, ForeignKey, JSON, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class VideoPipeline(Base):
    """Tracks the full lifecycle: Content → Script → Scenes → Veo → MP4."""
    __tablename__ = "video_pipelines"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("content.id"), index=True)

    # Pipeline status
    status: Mapped[str] = mapped_column(String(30), default="pending")
    # pending | script_generating | script_ready | scenes_generating |
    # scenes_ready | video_generating | video_ready | failed | published

    # Approval status
    approval_status: Mapped[str] = mapped_column(String(20), default="pending")
    # pending | approved | rejected
    approved_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    rejected_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # YouTube publishing
    youtube_video_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    youtube_video_url: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    youtube_published_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    youtube_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    # pending | uploading | published | failed

    # Script stage
    script: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    script_model: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Scenes stage (JSON array of scene objects)
    scenes: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    # Each scene: {"index": 0, "description": "...", "prompt": "...", "duration": 8}

    # Video generation stage
    video_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    video_duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    video_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    aspect_ratio: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    # 16:9 (landscape) or 9:16 (vertical/Shorts)

    # Veo operation tracking
    veo_operation_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    veo_model: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    # Metadata
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)


class VideoScene(Base):
    """Individual scene within a video pipeline."""
    __tablename__ = "video_scenes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    pipeline_id: Mapped[int] = mapped_column(ForeignKey("video_pipelines.id"), index=True)
    scene_index: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str] = mapped_column(Text, default="")
    prompt: Mapped[str] = mapped_column(Text, default="")
    duration_seconds: Mapped[int] = mapped_column(Integer, default=8)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    # pending | generating | ready | failed
    video_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    veo_operation_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
