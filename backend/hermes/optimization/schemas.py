"""
Hermes content-optimization schemas.

Explainability contract: every ``ContentRecommendation`` MUST carry
``rationale`` (human-readable why), ``evidence`` (post ids + measured
values + sample size) and ``confidence`` (derived from sample size).
A recommendation without evidence is a bug — the loop refuses to emit it.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

Area = Literal[
    "topic_selection",
    "content_format",
    "posting_strategy",
    "platform_adaptation",
    "content_quality",
]

RiskLevel = Literal["low", "medium", "high"]

Confidence = Literal["high", "medium", "low"]


class RecommendationEvidence(BaseModel):
    """Measured facts behind a recommendation (never guesses)."""

    post_ids: List[int] = Field(default_factory=list)
    metric_values: Dict[str, Any] = Field(default_factory=dict)
    sample_size: int = 0
    measured_posts: int = 0
    unmeasured_posts: int = 0
    window_days: int = 30


class ContentRecommendation(BaseModel):
    """One explainable, risk-gated content recommendation."""

    area: Area
    suggestion: str
    rationale: str
    evidence: RecommendationEvidence
    confidence: Confidence = "low"
    risk_level: RiskLevel = "low"
    requires_approval: bool = False
    auto_applied: bool = False
    approval_action: Optional[str] = None


class TopicPerformance(BaseModel):
    """Aggregated measured performance for one normalized topic."""

    topic: str
    posts: int = 0
    measured_posts: int = 0
    avg_engagement_rate: Optional[float] = None
    total_interactions: int = 0
    post_ids: List[int] = Field(default_factory=list)
    platforms: List[str] = Field(default_factory=list)


class LoopRunSummary(BaseModel):
    """What the loop did — safe actions applied, risky ones queued."""

    posts_analysed: int = 0
    measured_posts: int = 0
    unmeasured_posts: int = 0
    recommendations_total: int = 0
    auto_applied: int = 0
    queued_for_approval: int = 0
    generated_at: Optional[datetime] = None


class OptimizationReport(BaseModel):
    """Full feedback-loop output: 5 areas + risk handling + summary."""

    recommendations: List[ContentRecommendation] = Field(default_factory=list)
    topics: List[TopicPerformance] = Field(default_factory=list)
    approvals: List[ContentRecommendation] = Field(default_factory=list)
    applied: List[ContentRecommendation] = Field(default_factory=list)
    summary: LoopRunSummary = Field(default_factory=LoopRunSummary)

    def for_area(self, area: Area) -> List[ContentRecommendation]:
        return [r for r in self.recommendations if r.area == area]
