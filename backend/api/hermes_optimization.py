"""
Hermes Content-Optimization API — feedback loop over historical performance.

- ``GET /hermes/optimization/report`` — read-only analysis (no writes).
- ``POST /hermes/optimization/run`` — full loop; only low-risk advisory
  notes are recorded (returned in-response), risky items are queued as
  approval payloads. NOTHING is published, scheduled, edited or deleted.

Isolation: content tables only. Career Intelligence untouched.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.api import auth
from backend.content_analytics.service import ContentAnalyticsService
from backend.database import get_db
from backend.hermes.optimization.feedback_loop import HermesContentOptimizationLoop
from backend.hermes.optimization.schemas import OptimizationReport

router = APIRouter(prefix="/hermes/optimization", tags=["Hermes Optimization"])


def get_analytics(db: Session = Depends(get_db)) -> ContentAnalyticsService:
    return ContentAnalyticsService(db)


def _rows_for_user(service: ContentAnalyticsService, user_id: int,
                   platform: Optional[str], window_days: int) -> List[Dict[str, Any]]:
    """Latest-per-post rows enriched with hashtags/timestamps for the loop."""
    rows = service.latest_per_post(user_id, platform=platform, window_days=window_days)
    # Enrich with fields latest_per_post does not carry (hashtags, publish time).
    items = {item.id: item for item in
             service.list_published(user_id, platform=platform, limit=200, include_failed=False)}
    for row in rows:
        item = items.get(row["content_id"])
        if item is not None:
            row["hashtags"] = list(item.hashtags or [])
            row["published_at"] = item.published_at.isoformat() if item.published_at else None
    return rows


@router.get("/report", response_model=OptimizationReport)
async def get_optimization_report(
    platform: Optional[str] = Query(None),
    window_days: int = Query(30, ge=1, le=365),
    current_user=Depends(auth.get_current_active_user),
    service: ContentAnalyticsService = Depends(get_analytics),
):
    """Read-only loop analysis: 5-area recommendations with risk labels."""
    rows = _rows_for_user(service, current_user.id, platform, window_days)
    return HermesContentOptimizationLoop(window_days=window_days).analyse(rows)


@router.post("/run", response_model=OptimizationReport)
async def run_optimization_loop(
    platform: Optional[str] = Query(None),
    window_days: int = Query(30, ge=1, le=365),
    current_user=Depends(auth.get_current_active_user),
    service: ContentAnalyticsService = Depends(get_analytics),
):
    """Run the loop: safe advisory notes recorded, risky items queued.

    Response ``applied`` holds auto-recorded low-risk notes (in-response
    payloads, no external side effects); ``approvals`` holds payloads a
    human must confirm. The loop itself changes no published content.
    """
    rows = _rows_for_user(service, current_user.id, platform, window_days)
    loop = HermesContentOptimizationLoop(window_days=window_days)
    recorded: List[Dict[str, Any]] = []
    queued: List[str] = []

    async def _memory(agent_id: str, payload: Dict[str, Any]) -> str:
        recorded.append({"agent_id": agent_id, **payload})
        return f"note-{len(recorded)}"

    async def _approval(rec: Any) -> str:
        queued.append(rec.approval_action or "review")
        return f"approval-{len(queued)}"

    return await loop.run(rows, memory_store=_memory, approval_sink=_approval)
