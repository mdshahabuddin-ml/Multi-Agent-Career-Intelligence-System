from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Query, Form
from sqlalchemy.orm import Session

from backend.api import auth
from backend.database import get_db
from backend.schemas.job import (
    JobSearchRequest,
    JobSearchResponse,
    JobResponse,
    JobListResponse,
    JobRecommendationResponse,
    JobRecommendationsResponse,
    JobStatsResponse,
    SavedJobResponse,
)
from backend.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def get_job_service(db: Session = Depends(get_db)) -> JobService:
    return JobService(db)


@router.post("/search", response_model=JobSearchResponse)
async def search_jobs(
    request: JobSearchRequest,
    job_service: JobService = Depends(get_job_service),
):
    """Search and save jobs from external sources."""
    jobs = await job_service.search_and_save_jobs(
        query=request.query,
        location=request.location,
        remote=request.remote,
        limit=request.limit,
        sources=request.sources,
    )
    return JobSearchResponse(
        jobs_found=len(jobs),
        jobs=[JobListResponse.model_validate(j) for j in jobs],
    )


@router.get("/search", response_model=JobSearchResponse)
async def search_jobs_get(
    query: str = Query(..., description="Search query"),
    location: Optional[str] = Query(None),
    remote: Optional[bool] = Query(None),
    experience_level: Optional[str] = Query(None),
    employment_type: Optional[str] = Query(None),
    salary_min: Optional[int] = Query(None),
    skills: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    job_service: JobService = Depends(get_job_service),
):
    """Search saved jobs with filters."""
    skill_list = skills.split(",") if skills else None
    jobs = job_service.get_jobs(
        query=query,
        location=location,
        remote=remote,
        experience_level=experience_level,
        employment_type=employment_type,
        salary_min=salary_min,
        skills=skill_list,
        source=source,
        limit=limit,
        offset=offset,
    )
    total = job_service.get_job_count(query=query, location=location, remote=remote)
    return JobSearchResponse(
        jobs_found=total,
        jobs=[JobListResponse.model_validate(j) for j in jobs],
    )


@router.get("/recommendations", response_model=JobRecommendationsResponse)
async def get_recommendations(
    limit: int = Query(20, le=50),
    current_user = Depends(auth.get_current_active_user),
    job_service: JobService = Depends(get_job_service),
):
    """Get personalized job recommendations for current user."""
    recommendations = await job_service.get_personalized_recommendations(
        user_id=current_user.id,
        limit=limit,
    )
    return JobRecommendationsResponse(
        recommendations=[JobRecommendationResponse(**r) for r in recommendations],
        total=len(recommendations),
    )


@router.get("/stats", response_model=JobStatsResponse)
async def get_job_stats(
    job_service: JobService = Depends(get_job_service),
):
    """Get job market statistics."""
    stats = job_service.get_job_stats()
    return JobStatsResponse(**stats)


@router.get("/", response_model=List[JobListResponse])
async def list_jobs(
    query: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    remote: Optional[bool] = Query(None),
    experience_level: Optional[str] = Query(None),
    employment_type: Optional[str] = Query(None),
    salary_min: Optional[int] = Query(None),
    skills: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    job_service: JobService = Depends(get_job_service),
):
    """List jobs with filters."""
    skill_list = skills.split(",") if skills else None
    jobs = job_service.get_jobs(
        query=query,
        location=location,
        remote=remote,
        experience_level=experience_level,
        employment_type=employment_type,
        salary_min=salary_min,
        skills=skill_list,
        source=source,
        limit=limit,
        offset=offset,
    )
    return [JobListResponse.model_validate(j) for j in jobs]


@router.get("/saved", response_model=List[SavedJobResponse])
async def get_saved_jobs(
    current_user = Depends(auth.get_current_active_user),
    job_service: JobService = Depends(get_job_service),
):
    """Get user's saved jobs."""
    saved = job_service.get_saved_jobs(current_user.id)
    return [SavedJobResponse(**s) for s in saved]


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    job_service: JobService = Depends(get_job_service),
):
    """Get job details."""
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse.model_validate(job)


@router.post("/{job_id}/save", response_model=SavedJobResponse)
async def save_job(
    job_id: int,
    notes: Optional[str] = Form(None),
    current_user = Depends(auth.get_current_active_user),
    job_service: JobService = Depends(get_job_service),
):
    """Save a job for later."""
    application = job_service.save_job_for_user(
        user_id=current_user.id,
        job_id=job_id,
        notes=notes,
    )
    return SavedJobResponse(
        application_id=application.id,
        job_id=job_id,
        status=application.status,
        saved_date=application.created_at,
    )