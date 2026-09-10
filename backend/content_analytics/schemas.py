"""
Pydantic schemas for the isolated content-analytics layer.

Convention: remote metrics use ``Optional[int]`` where ``None`` means
"unsupported by this platform's official API" (see capabilities.py).
This is load-bearing — ``None`` must never be coerced to 0 when
computing rates or rankings; unsupported inputs are excluded.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MetricSnapshot(BaseModel):
    """One official-API snapshot for a published post.

    ``supported_metrics`` / ``unsupported_metrics`` come from the
    capability matrix so clients can render "—" instead of 0.
    """

    content_id: int
    platform: str
    platform_post_id: str
    views: Optional[int] = None
    impressions: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    saves: Optional[int] = None
    clicks: Optional[int] = None
    reach: Optional[int] = None
    engagement_rate: Optional[float] = None
    click_through_rate: Optional[float] = None
    supported_metrics: List[str] = Field(default_factory=list)
    unsupported_metrics: List[str] = Field(default_factory=list)
    fetched_at: Optional[datetime] = None
    snapshot_id: Optional[int] = None


class PublishedContentItem(BaseModel):
    """Published (or attempted) content with its latest snapshot summary."""

    content_id: int
    title: str
    platform: str
    content_type: str
    status: str
    platform_post_id: Optional[str] = None
    platform_post_url: Optional[str] = None
    published_at: Optional[datetime] = None
    scheduled_at: Optional[datetime] = None
    latest_snapshot: Optional[MetricSnapshot] = None
    snapshot_count: int = 0


class PlatformBreakdown(BaseModel):
    posts: int = 0
    views: Optional[int] = None
    impressions: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    avg_engagement_rate: Optional[float] = None
    # How many posts actually contributed measurable data.
    measured_posts: int = 0


class PerformanceSummary(BaseModel):
    """Performance Analysis stage output."""

    total_published: int
    measured_posts: int
    unmeasured_posts: int
    totals: Dict[str, Optional[int]] = Field(default_factory=dict)
    avg_engagement_rate: Optional[float] = None
    by_platform: Dict[str, PlatformBreakdown] = Field(default_factory=dict)
    by_content_type: Dict[str, PlatformBreakdown] = Field(default_factory=dict)
    top_posts: List[Dict[str, Any]] = Field(default_factory=list)
    bottom_posts: List[Dict[str, Any]] = Field(default_factory=list)
    window_days: int = 30


class PostFeedback(BaseModel):
    """Feedback stage output for one post."""

    content_id: int
    platform: str
    verdict: str = Field(description="strong | steady | needs_attention | unmeasured")
    strengths: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    next_experiment: Optional[str] = None
    engagement_rate: Optional[float] = None


class PortfolioFeedback(BaseModel):
    overall: str = ""
    strengths: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    per_post: List[PostFeedback] = Field(default_factory=list)


class OptimizationSuggestion(BaseModel):
    area: str = Field(description="platform | format | cadence | measurement | creative")
    suggestion: str
    rationale: str
    priority: str = Field(default="medium", description="high | medium | low")


class OptimizationPlan(BaseModel):
    """Future Content Optimization stage output."""

    suggestions: List[OptimizationSuggestion] = Field(default_factory=list)
    best_platform: Optional[str] = None
    best_content_type: Optional[str] = None
    generated_at: Optional[datetime] = None


class RefreshRequest(BaseModel):
    content_ids: Optional[List[int]] = None
    max_items: int = Field(default=20, ge=1, le=100)
