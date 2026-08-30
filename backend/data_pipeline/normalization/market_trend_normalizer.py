import logging
import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum as PyEnum

from backend.data_pipeline.collectors.base_collector import RawDataRecord

logger = logging.getLogger(__name__)


class DemandSignal(str, PyEnum):
    """Types of demand signals."""
    JOB_POSTINGS = "job_postings"
    SKILL_MENTIONS = "skill_mentions"
    SALARY_TRENDS = "salary_trends"
    HIRING_VELOCITY = "hiring_velocity"
    COMPANY_GROWTH = "company_growth"
    FUNDING_ACTIVITY = "funding_activity"
    SEARCH_VOLUME = "search_volume"
    COURSE_ENROLLMENT = "course_enrollment"


class TrendDirection(str, PyEnum):
    """Trend direction."""
    RISING = "rising"
    STABLE = "stable"
    DECLINING = "declining"
    VOLATILE = "volatile"


@dataclass
class NormalizedMarketTrend:
    """Normalized market trend data."""
    skill: str
    technology: Optional[str]
    role: Optional[str]
    location: Optional[str]
    demand_signal: DemandSignal
    signal_value: float
    trend_direction: TrendDirection
    time_period: str
    period_start: datetime
    period_end: datetime
    source_count: int
    source_quality: float
    evidence: List[Dict[str, Any]]
    confidence_score: float
    calculated_at: datetime
    source: str
    source_url: str
    source_trend_id: str
    quality_score: float
    raw_record: Optional[RawDataRecord] = None


def normalize_demand_signal(signal: Optional[str]) -> DemandSignal:
    """Normalize demand signal type."""
    if not signal:
        return DemandSignal.JOB_POSTINGS
    signal_lower = signal.lower().strip()
    
    signal_map = {
        "job": DemandSignal.JOB_POSTINGS,
        "posting": DemandSignal.JOB_POSTINGS,
        "skill": DemandSignal.SKILL_MENTIONS,
        "mention": DemandSignal.SKILL_MENTIONS,
        "salary": DemandSignal.SALARY_TRENDS,
        "compensation": DemandSignal.SALARY_TRENDS,
        "hiring": DemandSignal.HIRING_VELOCITY,
        "velocity": DemandSignal.HIRING_VELOCITY,
        "company": DemandSignal.COMPANY_GROWTH,
        "growth": DemandSignal.COMPANY_GROWTH,
        "funding": DemandSignal.FUNDING_ACTIVITY,
        "investment": DemandSignal.FUNDING_ACTIVITY,
        "search": DemandSignal.SEARCH_VOLUME,
        "course": DemandSignal.COURSE_ENROLLMENT,
        "enrollment": DemandSignal.COURSE_ENROLLMENT,
    }
    
    for key, val in signal_map.items():
        if key in signal_lower:
            return val
    return DemandSignal.JOB_POSTINGS


def normalize_trend_direction(direction: Optional[str]) -> TrendDirection:
    """Normalize trend direction."""
    if not direction:
        return TrendDirection.STABLE
    direction_lower = direction.lower().strip()
    
    if direction_lower in ["rising", "increasing", "growing", "up", "positive", "bullish"]:
        return TrendDirection.RISING
    elif direction_lower in ["declining", "decreasing", "falling", "down", "negative", "bearish"]:
        return TrendDirection.DECLINING
    elif direction_lower in ["volatile", "fluctuating", "unstable"]:
        return TrendDirection.VOLATILE
    return TrendDirection.STABLE


class MarketTrendNormalizer:
    """Normalize market trend data from various sources."""

    def __init__(self):
        self.name = "market_trend_normalizer"

    def normalize(self, raw_record: RawDataRecord) -> NormalizedMarketTrend:
        """Normalize a single raw market trend record."""
        payload = raw_record.raw_payload
        logger.debug(f"Normalizing market trend: {payload.get('skill')} - {payload.get('demand_signal')}")

        skill = payload.get("skill", "").strip()
        technology = payload.get("technology", "").strip() if payload.get("technology") else None
        role = payload.get("role", "").strip() if payload.get("role") else None
        location = payload.get("location", "").strip() if payload.get("location") else None
        
        demand_signal = normalize_demand_signal(payload.get("demand_signal"))
        
        signal_value = payload.get("signal_value", 0.0)
        if isinstance(signal_value, str):
            try:
                signal_value = float(signal_value)
            except Exception:
                signal_value = 0.0
        
        trend_direction = normalize_trend_direction(payload.get("trend_direction"))
        
        time_period = payload.get("time_period", "monthly")
        
        period_start = payload.get("period_start")
        if isinstance(period_start, str):
            try:
                period_start = datetime.fromisoformat(period_start.replace("Z", "+00:00"))
            except Exception:
                period_start = datetime.utcnow()
        
        period_end = payload.get("period_end")
        if isinstance(period_end, str):
            try:
                period_end = datetime.fromisoformat(period_end.replace("Z", "+00:00"))
            except Exception:
                period_end = datetime.utcnow()
        
        source_count = payload.get("source_count", 1)
        if isinstance(source_count, str):
            try:
                source_count = int(source_count)
            except Exception:
                source_count = 1
        
        source_quality = payload.get("source_quality", 0.5)
        if isinstance(source_quality, str):
            try:
                source_quality = float(source_quality)
            except Exception:
                source_quality = 0.5
        
        evidence = payload.get("evidence") or []
        
        confidence_score = payload.get("confidence_score", 0.5)
        if isinstance(confidence_score, str):
            try:
                confidence_score = float(confidence_score)
            except Exception:
                confidence_score = 0.5
        
        calculated_at = payload.get("calculated_at")
        if isinstance(calculated_at, str):
            try:
                calculated_at = datetime.fromisoformat(calculated_at.replace("Z", "+00:00"))
            except Exception:
                calculated_at = datetime.utcnow()
        elif not calculated_at:
            calculated_at = datetime.utcnow()

        return NormalizedMarketTrend(
            skill=skill,
            technology=technology,
            role=role,
            location=location,
            demand_signal=demand_signal,
            signal_value=signal_value,
            trend_direction=trend_direction,
            time_period=time_period,
            period_start=period_start,
            period_end=period_end,
            source_count=source_count,
            source_quality=source_quality,
            evidence=evidence,
            confidence_score=confidence_score,
            calculated_at=calculated_at,
            source=raw_record.source_name,
            source_url=payload.get("source_url", ""),
            source_trend_id=payload.get("source_trend_id", raw_record.external_id),
            quality_score=payload.get("quality_score", 0.0),
            raw_record=raw_record,
        )

    def normalize_batch(self, raw_records: List[RawDataRecord]) -> List[NormalizedMarketTrend]:
        """Normalize multiple raw market trend records."""
        return [self.normalize(record) for record in raw_records]