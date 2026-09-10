"""Career-to-Content pipeline endpoints (backend stages 1-7).

Run the pipeline (intake -> research -> generation -> fact/quality check ->
platform formatting -> human approval) and review the results. Scheduling,
social publishing, and analytics collection are deferred stages.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_active_user
from backend.models import User
from backend.models.content_pipeline_run import ContentKind, PipelineSource
from backend.services.career_content_service import SUPPORTED_PLATFORMS, CareerContentService

router = APIRouter(prefix="/career-content", tags=["Career-to-Content"])


class PipelineRunRequest(BaseModel):
    source: PipelineSource
    source_id: Optional[int] = None
    content_kind: ContentKind
    platforms: List[str] = Field(default_factory=lambda: ["linkedin"])
    topic: Optional[str] = Field(
        default=None,
        description="Optional caller-supplied topic; otherwise auto-selected from the brief.",
    )


class ReviewRequest(BaseModel):
    notes: Optional[str] = None


class EditDraftRequest(BaseModel):
    text: str = Field(..., min_length=1)


class RegenerateRequest(BaseModel):
    topic: Optional[str] = None
    content_kind: Optional[ContentKind] = None


def _run_error(exc: ValueError) -> HTTPException:
    """Map run errors: missing run -> 404, wrong state/bad input -> 400."""
    if str(exc) == "Pipeline run not found":
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


def _serialize(run) -> Dict[str, Any]:
    return {
        "id": run.id,
        "source": run.source.value,
        "source_id": run.source_id,
        "content_kind": run.content_kind.value,
        "platforms": run.platforms,
        "status": run.status.value,
        "current_stage": run.current_stage,
        "stage_results": run.stage_results or {},
        "quality_score": run.quality_score,
        "error_message": run.error_message,
        "reviewed_by": run.reviewed_by,
        "review_notes": run.review_notes,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "updated_at": run.updated_at.isoformat() if run.updated_at else None,
    }


@router.post("/pipeline/runs", status_code=status.HTTP_201_CREATED)
async def run_pipeline(
    request: PipelineRunRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Run the Career-to-Content pipeline through human review."""
    service = CareerContentService(db)
    try:
        run = await service.run_pipeline(
            user_id=current_user.id,
            source=request.source,
            content_kind=request.content_kind,
            platforms=request.platforms,
            source_id=request.source_id,
            topic=request.topic,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return _serialize(run)


@router.get("/pipeline/runs")
async def list_runs(
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List the current user's pipeline runs (newest first)."""
    service = CareerContentService(db)
    return {"runs": [_serialize(r) for r in service.list_runs(current_user.id, limit=limit)]}


@router.get("/pipeline/runs/{run_id}")
async def get_run(
    run_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get a single pipeline run with all stage outputs."""
    service = CareerContentService(db)
    try:
        return _serialize(service.get_run(run_id, current_user.id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/pipeline/runs/{run_id}/approve")
async def approve_run(
    run_id: int,
    request: ReviewRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Human approval gate: approve a run awaiting review."""
    service = CareerContentService(db)
    try:
        run = service.approve_run(run_id, current_user.id, notes=request.notes)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return _serialize(run)


@router.post("/pipeline/runs/{run_id}/reject")
async def reject_run(
    run_id: int,
    request: ReviewRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Human approval gate: reject a run awaiting review."""
    service = CareerContentService(db)
    try:
        run = service.reject_run(run_id, current_user.id, notes=request.notes)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return _serialize(run)


@router.post("/pipeline/runs/{run_id}/edit")
async def edit_draft(
    run_id: int,
    request: EditDraftRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Human edit of a draft awaiting review (or failed); re-verified on save."""
    service = CareerContentService(db)
    try:
        run = await service.edit_draft(run_id, current_user.id, request.text)
    except ValueError as exc:
        raise _run_error(exc)
    return _serialize(run)


@router.post("/pipeline/runs/{run_id}/regenerate")
async def regenerate_draft(
    run_id: int,
    request: RegenerateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Regenerate a draft for a run awaiting review, failed, or rejected."""
    service = CareerContentService(db)
    try:
        run = await service.regenerate_draft(
            run_id, current_user.id,
            topic=request.topic, content_kind=request.content_kind,
        )
    except ValueError as exc:
        raise _run_error(exc)
    return _serialize(run)


@router.get("/meta")
async def pipeline_meta(current_user: User = Depends(get_current_active_user)):
    """Advertise supported sources, kinds, and platforms."""
    return {
        "sources": [s.value for s in PipelineSource],
        "content_kinds": [k.value for k in ContentKind],
        "platforms": list(SUPPORTED_PLATFORMS),
    }
