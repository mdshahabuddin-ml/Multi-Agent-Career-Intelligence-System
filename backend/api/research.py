import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime
import asyncio
import json

from backend.database import get_db
from backend.models import User, Research, ResearchStatus, ResearchType
from backend.services.research_service import ResearchService
from backend.services.websocket_manager import get_ws_manager
from backend.services.rate_limit_service import create_quota_dependency
from backend.agents.research import PipelinePhase
from backend.dependencies import get_current_user
from backend.utils.security import decode_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/research", tags=["research"])


class ResearchCreate(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000, description="Research query")
    research_type: ResearchType = Field(default=ResearchType.GENERAL, description="Type of research")
    target_role: Optional[str] = Field(None, max_length=255, description="Target role for career research")
    target_company: Optional[str] = Field(None, max_length=255, description="Target company for company research")
    target_location: Optional[str] = Field(None, max_length=255, description="Target location")
    max_sources: int = Field(default=10, ge=1, le=50, description="Maximum sources to collect")
    timeout_seconds: int = Field(default=300, ge=30, le=1800, description="Timeout in seconds")
    use_llm: bool = Field(default=True, description="Use LLM-enhanced agents")


class ResearchUpdate(BaseModel):
    query: Optional[str] = Field(None, min_length=3, max_length=1000)
    research_type: Optional[ResearchType] = None
    target_role: Optional[str] = None
    target_company: Optional[str] = None
    target_location: Optional[str] = None
    max_sources: Optional[int] = Field(None, ge=1, le=50)
    timeout_seconds: Optional[int] = Field(None, ge=30, le=1800)


class ResearchResponse(BaseModel):
    id: int
    user_id: int
    query: str
    research_type: str
    status: str
    progress: int
    source_count: int
    verified_claim_count: int
    confidence_score: Optional[float]
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ResearchDetailResponse(ResearchResponse):
    executive_summary: Optional[str] = None
    key_findings: Optional[List[str]] = None
    recommendations: Optional[List[str]] = None
    sources: Optional[List[Dict[str, Any]]] = None
    claims: Optional[List[Dict[str, Any]]] = None
    evidence: Optional[List[Dict[str, Any]]] = None
    report_data: Optional[Dict[str, Any]] = None


class ResearchListResponse(BaseModel):
    items: List[ResearchResponse]
    total: int
    page: int
    page_size: int


class ProgressUpdate(BaseModel):
    research_id: int
    phase: str
    progress: int
    stats: Dict[str, Any]
    error: Optional[str] = None
    warnings: List[str] = []


class ReportExportRequest(BaseModel):
    format: str = Field(default="markdown", pattern="^(markdown|html|pdf)$")


active_connections: Dict[int, WebSocket] = {}


def get_research_service(db: Session = Depends(get_db)) -> ResearchService:
    return ResearchService(db)


@router.post("", response_model=ResearchResponse, status_code=201)
async def create_research(
    research_data: ResearchCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    service: ResearchService = Depends(get_research_service),
    quota_ok: bool = Depends(create_quota_dependency("research", 1)),
):
    """Start a new research task. Consumes 1 research quota."""
    research = await service.start_research(
        user_id=current_user.id,
        query=research_data.query,
        research_type=research_data.research_type,
        target_role=research_data.target_role,
        target_company=research_data.target_company,
        target_location=research_data.target_location,
        max_sources=research_data.max_sources,
        timeout_seconds=research_data.timeout_seconds,
    )
    return ResearchResponse.from_orm(research)


@router.get("", response_model=ResearchListResponse)
async def list_research(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[ResearchStatus] = None,
    current_user: User = Depends(get_current_user),
    service: ResearchService = Depends(get_research_service),
):
    """List user's research tasks with pagination."""
    all_research = await service.list_user_research(current_user.id)
    
    if status:
        all_research = [r for r in all_research if r.status == status]
    
    total = len(all_research)
    start = (page - 1) * page_size
    end = start + page_size
    items = all_research[start:end]
    
    return ResearchListResponse(
        items=[ResearchResponse.from_orm(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{research_id}", response_model=ResearchDetailResponse)
async def get_research(
    research_id: int,
    current_user: User = Depends(get_current_user),
    service: ResearchService = Depends(get_research_service),
):
    """Get detailed research results."""
    details = await service.get_research_details(research_id, current_user.id)
    if not details:
        raise HTTPException(status_code=404, detail="Research not found")
    return ResearchDetailResponse(**details)


@router.get("/{research_id}/status", response_model=ProgressUpdate)
async def get_research_status(
    research_id: int,
    current_user: User = Depends(get_current_user),
    service: ResearchService = Depends(get_research_service),
):
    """Get real-time research status and progress."""
    status = await service.get_research_status(research_id, current_user.id)
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])
    
    return ProgressUpdate(
        research_id=status["id"],
        phase=status["status"],
        progress=status["progress"],
        stats={
            "source_count": status["source_count"],
            "verified_claim_count": status["verified_claim_count"],
            "confidence_score": status["confidence_score"],
        },
        error=status.get("error_message"),
        warnings=[],
    )


@router.delete("/{research_id}")
async def cancel_research(
    research_id: int,
    current_user: User = Depends(get_current_user),
    service: ResearchService = Depends(get_research_service),
):
    """Cancel a running research task."""
    success = await service.cancel_research(research_id, current_user.id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot cancel - research not found or already completed")
    return {"message": "Research cancelled"}


@router.post("/{research_id}/export")
async def export_research_report(
    research_id: int,
    export_request: ReportExportRequest,
    current_user: User = Depends(get_current_user),
    service: ResearchService = Depends(get_research_service),
):
    """Export research report in specified format."""
    report = await service.export_research_report(
        research_id, current_user.id, export_request.format
    )
    if not report:
        raise HTTPException(status_code=404, detail="Research not found or not completed")
    
    media_types = {
        "markdown": "text/markdown",
        "html": "text/html",
        "pdf": "application/pdf",
    }
    
    extensions = {
        "markdown": ".md",
        "html": ".html",
        "pdf": ".pdf",
    }
    
    research = await service.get_research(research_id, current_user.id)
    filename = f"research_{research_id}_{research.query[:50]}.{export_request.format}"
    filename = filename.replace(" ", "_").replace("/", "_")
    
    return Response(
        content=report,
        media_type=media_types[export_request.format],
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/{research_id}/report", response_model=Dict[str, Any])
async def get_research_report(
    research_id: int,
    current_user: User = Depends(get_current_user),
    service: ResearchService = Depends(get_research_service),
):
    """Get full research report."""
    report = await service.get_research_report(research_id, current_user.id)
    if not report:
        raise HTTPException(status_code=404, detail="Research not found or not completed")
    return report


@router.websocket("/ws/{research_id}")
async def research_progress_ws(
    websocket: WebSocket,
    research_id: int,
    db: Session = Depends(get_db),
):
    """WebSocket for real-time research progress updates."""
    ws_manager = get_ws_manager()
    
    # Verify access
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return
    
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return
    except Exception:
        await websocket.close(code=4001, reason="Invalid token")
        return
    
    # Verify ownership
    research = db.query(Research).filter(
        Research.id == research_id,
        Research.user_id == user_id
    ).first()
    
    if not research:
        await websocket.close(code=4004, reason="Research not found")
        return
    
    await ws_manager.connect(research_id, websocket)
    
    try:
        # Send initial status
        service = ResearchService(db)
        status = await service.get_research_status(research_id, user_id)
        await websocket.send_json(ProgressUpdate(
            research_id=status["id"],
            phase=status["status"],
            progress=status["progress"],
            stats={
                "source_count": status["source_count"],
                "verified_claim_count": status["verified_claim_count"],
                "confidence_score": status["confidence_score"],
            },
            error=status.get("error_message"),
            warnings=[],
        ).model_dump())
        
        # Keep connection alive
        while True:
            await asyncio.sleep(5)
            # Check if research is still running
            status = await service.get_research_status(research_id, user_id)
            if status.get("status") in ["completed", "failed"]:
                await websocket.send_json(ProgressUpdate(
                    research_id=status["id"],
                    phase=status["status"],
                    progress=status["progress"],
                    stats={
                        "source_count": status["source_count"],
                        "verified_claim_count": status["verified_claim_count"],
                        "confidence_score": status["confidence_score"],
                    },
                    error=status.get("error_message"),
                    warnings=[],
                ).model_dump())
                break
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(research_id)