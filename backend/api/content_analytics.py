"""
Content Analytics API — isolated from career analytics.

Pipeline exposed here (all scoped to the authenticated user):
    GET  /content-analytics/published          Published Content + publishing status
    POST /content-analytics/refresh/{id}       Analytics (fetch official API now)
    POST /content-analytics/refresh            Analytics (bulk)
    GET  /content-analytics/posts/{id}/snapshots
    GET  /content-analytics/performance        Performance Analysis
    GET  /content-analytics/feedback           Feedback (portfolio + per-post)
    GET  /content-analytics/optimization       Future Content Optimization
    GET  /content-analytics/capabilities       Official-API capability matrix

Only official platform APIs are ever queried (see
``backend/content_analytics/capabilities.py``). Metrics a platform does
not expose are returned as ``null`` (unsupported) — never scraped.

This router never imports career modules and never touches career tables.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.api import auth
from backend.content_analytics.analysis import analyse_performance
from backend.content_analytics.capabilities import PLATFORM_CAPABILITIES, TRACKED_METRICS
from backend.content_analytics.feedback import feedback_for_portfolio
from backend.content_analytics.optimizer import build_optimization_plan
from backend.content_analytics.providers import AnalyticsError
from backend.content_analytics.schemas import (
    MetricSnapshot,
    OptimizationPlan,
    PerformanceSummary,
    PortfolioFeedback,
    PublishedContentItem,
    RefreshRequest,
)
from backend.content_analytics.service import ContentAnalyticsService
from backend.database import get_db

router = APIRouter(prefix="/content-analytics", tags=["Content Analytics"])


def get_service(db: Session = Depends(get_db)) -> ContentAnalyticsService:
    return ContentAnalyticsService(db)


def _analytics_status(exc: AnalyticsError) -> int:
    msg = str(exc).lower()
    if "not found" in msg and "content not found" in msg:
        return status.HTTP_404_NOT_FOUND
    if "publish first" in msg or "not published" in msg:
        return status.HTTP_409_CONFLICT
    if "no connected" in msg or "please reconnect" in msg:
        return status.HTTP_424_FAILED_DEPENDENCY
    return status.HTTP_502_BAD_GATEWAY


@router.get("/capabilities")
async def get_capabilities(
    current_user=Depends(auth.get_current_active_user),
):
    """Show which metrics each platform's official API supports."""
    _ = current_user
    return {
        "tracked_metrics": TRACKED_METRICS,
        "platforms": {
            name: {
                "metrics": {
                    metric: {
                        "supported": cap.supported,
                        "source": cap.source,
                        "conditional": cap.conditional,
                        "note": cap.note,
                    }
                    for metric, cap in caps.metrics.items()
                },
                "publish_status_source": caps.publish_status_source,
            }
            for name, caps in PLATFORM_CAPABILITIES.items()
        },
        "policy": "Only official APIs are queried. Unsupported metrics return null — never scraped, never zero-filled.",
    }


@router.get("/published", response_model=List[PublishedContentItem])
async def list_published_content(
    platform: Optional[str] = Query(None, description="Filter by platform"),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(auth.get_current_active_user),
    service: ContentAnalyticsService = Depends(get_service),
):
    """Published Content stage: publishing status + latest snapshot per post."""
    return service.published_with_status(current_user.id, platform=platform, limit=limit)


@router.post("/refresh/{content_id}", response_model=MetricSnapshot)
async def refresh_post_analytics(
    content_id: int,
    current_user=Depends(auth.get_current_active_user),
    service: ContentAnalyticsService = Depends(get_service),
):
    """Analytics stage: fetch this post's metrics from the official API now."""
    try:
        return await service.refresh_snapshot(current_user.id, content_id)
    except AnalyticsError as exc:
        raise HTTPException(status_code=_analytics_status(exc), detail=str(exc))


@router.post("/refresh")
async def refresh_bulk_analytics(
    request: RefreshRequest,
    current_user=Depends(auth.get_current_active_user),
    service: ContentAnalyticsService = Depends(get_service),
):
    """Analytics stage (bulk): refresh up to ``max_items`` published posts."""
    result = await service.refresh_bulk(current_user.id, content_ids=request.content_ids, max_items=request.max_items)
    return {
        "refreshed_count": result["refreshed_count"],
        "failed_count": result["failed_count"],
        "refreshed": result["refreshed"],
        "failed": result["failed"],
    }


@router.get("/posts/{content_id}/snapshots", response_model=List[MetricSnapshot])
async def list_post_snapshots(
    content_id: int,
    limit: int = Query(30, ge=1, le=100),
    current_user=Depends(auth.get_current_active_user),
    service: ContentAnalyticsService = Depends(get_service),
):
    """Snapshot history for one post (newest first)."""
    try:
        return service.list_snapshots(current_user.id, content_id, limit=limit)
    except AnalyticsError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/performance", response_model=PerformanceSummary)
async def get_performance_analysis(
    platform: Optional[str] = Query(None),
    window_days: int = Query(30, ge=1, le=365),
    current_user=Depends(auth.get_current_active_user),
    service: ContentAnalyticsService = Depends(get_service),
):
    """Performance Analysis stage: aggregates over latest snapshot per post."""
    rows = service.latest_per_post(current_user.id, platform=platform, window_days=window_days)
    total_published = len(rows)
    return analyse_performance(rows, total_published=total_published, window_days=window_days)


@router.get("/feedback", response_model=PortfolioFeedback)
async def get_content_feedback(
    platform: Optional[str] = Query(None),
    window_days: int = Query(30, ge=1, le=365),
    current_user=Depends(auth.get_current_active_user),
    service: ContentAnalyticsService = Depends(get_service),
):
    """Feedback stage: strengths / risks per post + portfolio overall."""
    rows = service.latest_per_post(current_user.id, platform=platform, window_days=window_days)
    return feedback_for_portfolio(rows)


@router.get("/optimization", response_model=OptimizationPlan)
async def get_optimization_plan(
    platform: Optional[str] = Query(None),
    window_days: int = Query(30, ge=1, le=365),
    current_user=Depends(auth.get_current_active_user),
    service: ContentAnalyticsService = Depends(get_service),
):
    """Future Content Optimization stage: what to publish next, from measured data."""
    rows = service.latest_per_post(current_user.id, platform=platform, window_days=window_days)
    performance = analyse_performance(rows, total_published=len(rows), window_days=window_days)
    # Platforms with posts but zero measured posts need native-analytics guidance.
    unmeasured: List[str] = []
    for name, breakdown in performance.by_platform.items():
        if breakdown.posts > 0 and breakdown.measured_posts == 0:
            unmeasured.append(name)
    return build_optimization_plan(performance, unmeasured_platforms=unmeasured)
