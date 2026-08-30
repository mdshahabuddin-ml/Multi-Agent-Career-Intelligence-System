from typing import Optional, List

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status, Form
from sqlalchemy.orm import Session

from backend.api import auth
from backend.database import get_db
from backend.schemas.resume import (
    ResumeResponse,
    ResumeUploadResponse,
    ResumeParseResponse,
    ResumeATSResponse,
    ResumeReviewResponse,
    ResumeListResponse,
)
from backend.services.resume_service import ResumeService

router = APIRouter(prefix="/resume", tags=["Resume"])


def get_resume_service(db: Session = Depends(get_db)) -> ResumeService:
    return ResumeService(db)


@router.post("/upload", response_model=ResumeUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    is_primary: bool = Form(False),
    current_user = Depends(auth.get_current_active_user),
    resume_service: ResumeService = Depends(get_resume_service),
):
    """Upload a resume file."""
    resume = await resume_service.upload_resume(
        user_id=current_user.id,
        file=file,
        is_primary=is_primary,
    )
    return ResumeUploadResponse(
        id=resume.id,
        filename=resume.original_filename,
        status=resume.status.value,
        message="Resume uploaded successfully. Use /parse to extract content.",
    )


@router.post("/{resume_id}/parse", response_model=ResumeParseResponse)
async def parse_resume(
    resume_id: int,
    current_user = Depends(auth.get_current_active_user),
    resume_service: ResumeService = Depends(get_resume_service),
):
    """Parse uploaded resume and extract structured data."""
    resume = await resume_service.get_resume(resume_id, current_user.id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    resume = await resume_service.parse_resume(resume_id)

    return ResumeParseResponse(
        id=resume.id,
        status=resume.status.value,
        sections=list((resume.sections or {}).keys()),
        skills_count=len(resume.extracted_skills or []),
        projects_count=len(resume.extracted_projects or []),
        experience_entries=len(resume.extracted_experience or []),
        years_of_experience=resume.parsed_data.get("experience", {}).get("years_of_experience", 0) if resume.parsed_data else 0,
    )


@router.post("/{resume_id}/ats", response_model=ResumeATSResponse)
async def analyze_resume_ats(
    resume_id: int,
    target_role: Optional[str] = Form(None),
    target_keywords: Optional[str] = Form(None),
    current_user = Depends(auth.get_current_active_user),
    resume_service: ResumeService = Depends(get_resume_service),
):
    """Analyze resume for ATS compatibility."""
    resume = await resume_service.get_resume(resume_id, current_user.id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    keywords = []
    if target_keywords:
        keywords = [k.strip() for k in target_keywords.split(",") if k.strip()]

    result = await resume_service.analyze_resume_ats(
        resume_id=resume_id,
        target_role=target_role,
        target_keywords=keywords,
    )

    return ResumeATSResponse(
        overall_score=result["overall_score"],
        breakdown=result["breakdown"],
        recommendations=result["recommendations"],
        target_role=result.get("target_role"),
        word_count=result.get("word_count"),
    )


@router.post("/{resume_id}/review", response_model=ResumeReviewResponse)
async def review_resume(
    resume_id: int,
    current_user = Depends(auth.get_current_active_user),
    resume_service: ResumeService = Depends(get_resume_service),
):
    """Comprehensive resume content review."""
    resume = await resume_service.get_resume(resume_id, current_user.id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    result = await resume_service.review_resume(resume_id)

    return ResumeReviewResponse(
        content=result["content"],
        experience=result["experience"],
        skills=result["skills"],
        projects=result["projects"],
        overall=result["overall"],
        word_count=result["word_count"],
    )


@router.get("/", response_model=List[ResumeListResponse])
async def list_resumes(
    current_user = Depends(auth.get_current_active_user),
    resume_service: ResumeService = Depends(get_resume_service),
):
    """List all resumes for current user."""
    resumes = await resume_service.get_user_resumes(current_user.id)
    return [
        ResumeListResponse(
            id=r.id,
            original_filename=r.original_filename,
            file_size=r.file_size,
            status=r.status.value,
            is_primary=r.is_primary,
            ats_score=r.ats_score,
            created_at=r.created_at,
        )
        for r in resumes
    ]


@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume(
    resume_id: int,
    current_user = Depends(auth.get_current_active_user),
    resume_service: ResumeService = Depends(get_resume_service),
):
    """Get resume details."""
    resume = await resume_service.get_resume(resume_id, current_user.id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    return ResumeResponse.model_validate(resume)


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    resume_id: int,
    current_user = Depends(auth.get_current_active_user),
    resume_service: ResumeService = Depends(get_resume_service),
):
    """Delete a resume."""
    success = await resume_service.delete_resume(resume_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Resume not found")


@router.post("/{resume_id}/primary", response_model=ResumeResponse)
async def set_primary_resume(
    resume_id: int,
    current_user = Depends(auth.get_current_active_user),
    resume_service: ResumeService = Depends(get_resume_service),
):
    """Set resume as primary."""
    resume = await resume_service.set_primary_resume(resume_id, current_user.id)
    return ResumeResponse.model_validate(resume)