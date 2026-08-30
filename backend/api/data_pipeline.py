from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.database import get_db
from backend.api import auth
from backend.config import settings
from backend.data_pipeline import (
    IngestionPipeline,
    SourceRegistry,
    SourceConfig,
    SourceType,
    SourceProviderType,
    MockJobCollector,
    MockCompanyCollector,
    MockNewsCollector,
    MockResearchCollector,
    MockSkillCollector,
    MockCourseCollector,
    MockMarketTrendCollector,
    JobNormalizer,
    CompanyNormalizer,
    NewsNormalizer,
    ResearchNormalizer,
    SkillNormalizer,
    CourseNormalizer,
    MarketTrendNormalizer,
    DuplicateDetector,
    DataQualityScorer,
)
from backend.data_pipeline.sources.source_registry import DataSource

router = APIRouter(prefix="/api/data-pipeline", tags=["Data Pipeline"])


def get_source_registry(db: Session = Depends(get_db)) -> SourceRegistry:
    """Get source registry with DB session."""
    registry = SourceRegistry(db_session=db)
    registry.create_default_sources()
    return registry


class SourceConfigRequest(BaseModel):
    """Request model for source configuration."""
    source_id: str
    name: str
    source_type: str
    provider_type: str
    domain: str
    enabled: bool = True
    priority: int = 1
    update_frequency: str = "daily"
    reliability_score: float = 0.5
    rate_limit: int = 60
    timeout_seconds: int = 30
    api_key_env: Optional[str] = None
    base_url: Optional[str] = None
    custom_headers: Dict[str, str] = {}
    parameters: Dict[str, Any] = {}
    terms_url: Optional[str] = None
    metadata: Dict[str, Any] = {}


class PipelineRunRequest(BaseModel):
    """Request model for running pipeline."""
    source_id: str
    collector_kwargs: Dict[str, Any] = {}
    limit: Optional[int] = None


class SourceStatusResponse(BaseModel):
    """Response model for source status."""
    source_id: str
    name: str
    source_type: str
    provider_type: str
    domain: str
    enabled: bool
    priority: int
    update_frequency: str
    reliability_score: float
    rate_limit: int
    timeout_seconds: int
    last_success: Optional[str]
    last_failure: Optional[str]
    consecutive_failures: int


@router.get("/status")
async def get_pipeline_status(
    current_user = Depends(auth.get_current_active_user),
    registry: SourceRegistry = Depends(get_source_registry),
):
    """Get overall data pipeline status."""
    stats = registry.get_stats()
    sources = registry.list_all()
    
    return {
        "mock_data_mode": settings.MOCK_DATA,
        "pipeline_enabled": settings.DATA_PIPELINE_ENABLED,
        "total_sources": stats["total"],
        "enabled_sources": stats["enabled"],
        "disabled_sources": stats["disabled"],
        "sources_by_type": stats["by_type"],
        "sources": [
            SourceStatusResponse(
                source_id=s.source_id,
                name=s.name,
                source_type=s.source_type.value,
                provider_type=s.provider_type.value,
                domain=s.domain,
                enabled=s.enabled,
                priority=s.priority,
                update_frequency=s.update_frequency,
                reliability_score=s.reliability_score,
                rate_limit=s.rate_limit,
                timeout_seconds=s.timeout_seconds,
                last_success=s.last_success.isoformat() if s.last_success else None,
                last_failure=s.last_failure.isoformat() if s.last_failure else None,
                consecutive_failures=s.consecutive_failures,
            )
            for s in sources
        ],
    }


@router.get("/sources")
async def list_sources(
    source_type: Optional[str] = Query(None),
    enabled_only: bool = Query(True),
    current_user = Depends(auth.get_current_active_user),
    registry: SourceRegistry = Depends(get_source_registry),
):
    """List all configured data sources."""
    source_type_enum = None
    if source_type:
        try:
            source_type_enum = SourceType(source_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid source_type: {source_type}"
            )
    
    if enabled_only:
        sources = registry.list_enabled(source_type_enum)
    else:
        sources = registry.list_all()
        if source_type_enum:
            sources = [s for s in sources if s.source_type == source_type_enum]
    
    return [
        SourceStatusResponse(
            source_id=s.source_id,
            name=s.name,
            source_type=s.source_type.value,
            provider_type=s.provider_type.value,
            domain=s.domain,
            enabled=s.enabled,
            priority=s.priority,
            update_frequency=s.update_frequency,
            reliability_score=s.reliability_score,
            rate_limit=s.rate_limit,
            timeout_seconds=s.timeout_seconds,
            last_success=s.last_success.isoformat() if s.last_success else None,
            last_failure=s.last_failure.isoformat() if s.last_failure else None,
            consecutive_failures=s.consecutive_failures,
        )
        for s in sources
    ]


@router.post("/sources")
async def create_source(
    config: SourceConfigRequest,
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new data source configuration."""
    registry = SourceRegistry(db_session=db)
    
    try:
        source_type = SourceType(config.source_type)
        provider_type = SourceProviderType(config.provider_type)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid enum value: {e}"
        )
    
    source_config = SourceConfig(
        source_id=config.source_id,
        name=config.name,
        source_type=source_type,
        provider_type=provider_type,
        domain=config.domain,
        enabled=config.enabled,
        priority=config.priority,
        update_frequency=config.update_frequency,
        reliability_score=config.reliability_score,
        rate_limit=config.rate_limit,
        timeout_seconds=config.timeout_seconds,
        api_key_env=config.api_key_env,
        base_url=config.base_url,
        custom_headers=config.custom_headers,
        parameters=config.parameters,
        terms_url=config.terms_url,
        metadata=config.metadata,
    )
    
    registry.register(source_config, persist=True)
    
    return {"message": "Source created successfully", "source_id": config.source_id}


@router.delete("/sources/{source_id}")
async def delete_source(
    source_id: str,
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a data source configuration."""
    registry = SourceRegistry(db_session=db)
    success = registry.unregister(source_id, persist=True)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source not found: {source_id}"
        )
    
    return {"message": "Source deleted successfully"}


@router.post("/run")
async def run_pipeline(
    request: PipelineRunRequest,
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Run the ingestion pipeline for a source."""
    # Initialize pipeline with all components
    pipeline = IngestionPipeline(db_session=db)
    
    # Register mock collectors if in mock mode
    if settings.MOCK_DATA:
        collectors = {
            "mock_jobs": MockJobCollector(),
            "mock_companies": MockCompanyCollector(),
            "mock_news": MockNewsCollector(),
            "mock_research": MockResearchCollector(),
            "mock_skills": MockSkillCollector(),
            "mock_courses": MockCourseCollector(),
            "mock_market_trends": MockMarketTrendCollector(),
        }
        for name, collector in collectors.items():
            pipeline.register_collector(collector)
    
    # Check if source exists
    registry = SourceRegistry(db_session=db)
    source_config = registry.get(request.source_id)
    if not source_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source not found: {request.source_id}"
        )
    
    if not source_config.enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Source is disabled: {request.source_id}"
        )
    
    # Run pipeline
    result = await pipeline.run(
        source_id=request.source_id,
        collector_kwargs=request.collector_kwargs,
        limit=request.limit,
    )
    
    # Update source registry status
    registry.update_status(request.source_id, result.overall_success)
    
    return result.to_dict()


@router.get("/runs/{run_id}")
async def get_pipeline_run(
    run_id: str,
    current_user = Depends(auth.get_current_active_user),
):
    """Get pipeline run details (would query from run history store)."""
    # In a real implementation, this would query a pipeline_runs table
    # For now, return a placeholder
    return {
        "run_id": run_id,
        "message": "Run history not yet implemented. Use /run to execute pipeline.",
    }


@router.get("/metrics")
async def get_pipeline_metrics(
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get data pipeline metrics."""
    from backend.models import Job, Company
    from sqlalchemy import func
    from datetime import datetime, timedelta
    
    # Get job stats
    total_jobs = db.query(func.count(Job.id)).filter(Job.is_active == True).scalar() or 0
    recent_jobs = db.query(func.count(Job.id)).filter(
        Job.is_active == True,
        Job.created_at >= datetime.utcnow() - timedelta(days=7)
    ).scalar() or 0
    
    # Get company stats
    total_companies = db.query(func.count(Company.id)).filter(Company.is_active == True).scalar() or 0
    
    # Get source distribution
    sources = db.query(Job.source, func.count(Job.id)).filter(
        Job.is_active == True
    ).group_by(Job.source).all()
    by_source = {s: c for s, c in sources}
    
    # Quality stats
    avg_quality = db.query(func.avg(Job.quality_score)).filter(
        Job.is_active == True
    ).scalar() or 0.0
    
    return {
        "jobs": {
            "total": total_jobs,
            "last_7_days": recent_jobs,
            "avg_quality_score": round(float(avg_quality), 3),
            "by_source": by_source,
        },
        "companies": {
            "total": total_companies,
        },
        "pipeline": {
            "mock_mode": settings.MOCK_DATA,
            "enabled": settings.DATA_PIPELINE_ENABLED,
        },
    }


@router.get("/sources/{source_id}/health")
async def check_source_health(
    source_id: str,
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Check health of a specific source."""
    registry = SourceRegistry(db_session=db)
    source_config = registry.get(source_id)
    
    if not source_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source not found: {source_id}"
        )
    
    # Get appropriate collector
    collectors = {}
    if settings.MOCK_DATA:
        collectors = {
            "mock_jobs": MockJobCollector(),
            "mock_companies": MockCompanyCollector(),
            "mock_news": MockNewsCollector(),
            "mock_research": MockResearchCollector(),
            "mock_skills": MockSkillCollector(),
            "mock_courses": MockCourseCollector(),
            "mock_market_trends": MockMarketTrendCollector(),
        }
    
    collector = collectors.get(source_id)
    if not collector:
        return {
            "source_id": source_id,
            "healthy": False,
            "message": "No collector registered for this source",
        }
    
    health = await collector.health_check()
    
    return {
        "source_id": source_id,
        "healthy": health.value == "healthy",
        "status": health.value,
        "last_success": source_config.last_success.isoformat() if source_config.last_success else None,
        "last_failure": source_config.last_failure.isoformat() if source_config.last_failure else None,
        "consecutive_failures": source_config.consecutive_failures,
    }


@router.post("/sources/{source_id}/toggle")
async def toggle_source(
    source_id: str,
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Enable or disable a source."""
    registry = SourceRegistry(db_session=db)
    source = db.query(DataSource).filter(DataSource.source_id == source_id).first()
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source not found: {source_id}"
        )
    
    source.enabled = not source.enabled
    source.updated_at = datetime.utcnow()
    db.commit()
    
    # Update cache
    registry._cache[source_id] = source.to_config()
    
    return {
        "source_id": source_id,
        "enabled": source.enabled,
        "message": f"Source {'enabled' if source.enabled else 'disabled'} successfully",
    }