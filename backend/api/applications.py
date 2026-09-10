from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form, Query
from sqlalchemy.orm import Session

from backend.api import auth
from backend.database import get_db
from backend.schemas.application import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationUpdate,
    ApplicationListResponse,
    ApplicationStatsResponse,
    ApplicationPrepareRequest,
    ApplicationPrepareResponse,
    ATSAnalysisRequest,
    ATSAnalysisResponse,
    ResumeReviewRequest,
    ResumeReviewResponse,
    CoverLetterRequest,
    CoverLetterResponse,
    ApplicationAnswersRequest,
    ApplicationAnswersResponse,
    InterviewPrepRequest,
    InterviewPrepResponse,
    ResumeOptimizationRequest,
    ResumeOptimizationResponse,
    CoverLetterOptimizationRequest,
    CoverLetterOptimizationResponse,
)
from backend.services.application_service import ApplicationService

router = APIRouter(prefix="/applications", tags=["Applications"])


def get_application_service(db: Session = Depends(get_db)) -> ApplicationService:
    return ApplicationService(db)


# ==========================================
# Application Workflow
# ==========================================

@router.post("/prepare", response_model=ApplicationPrepareResponse)
async def prepare_application(
    request: ApplicationPrepareRequest,
    current_user = Depends(auth.get_current_active_user),
    application_service: ApplicationService = Depends(get_application_service),
):
    """Prepare complete application package for a job."""
    result = await application_service.prepare_application(
        user_id=current_user.id,
        job_id=request.job_id,
        resume_text=request.resume_text,
        candidate_profile=request.candidate_profile,
        job_description=request.job_description,
        cover_letter_tone=request.cover_letter_tone,
        cover_letter_length=request.cover_letter_length,
    )
    return ApplicationPrepareResponse(
        application_id=result.application_id,
        resume_ats_result=result.resume_ats_result.to_dict() if result.resume_ats_result else None,
        resume_review_result=result.resume_review_result.to_dict() if result.resume_review_result else None,
        cover_letter_result=result.cover_letter_result.to_dict() if result.cover_letter_result else None,
        answers_result=result.answers_result.to_dict() if result.answers_result else None,
        ready_to_submit=result.ready_to_submit,
        checklist=result.checklist,
        next_steps=result.next_steps,
    )


# ==========================================
# ATS Analysis
# ==========================================

@router.post("/ats/analyze", response_model=ATSAnalysisResponse)
async def analyze_resume_ats(
    request: ATSAnalysisRequest,
    current_user = Depends(auth.get_current_active_user),
    application_service: ApplicationService = Depends(get_application_service),
):
    """Analyze resume for ATS compatibility."""
    result = application_service.analyze_resume_ats(
        resume_text=request.resume_text,
        target_role=request.target_role,
        job_description=request.job_description,
    )
    return ATSAnalysisResponse(
        overall_score=result.overall_score,
        passed=result.passed,
        issues=[i.to_dict() for i in result.issues],
        keyword_match_score=result.keyword_match_score,
        format_score=result.format_score,
        section_score=result.section_score,
        content_score=result.content_score,
        missing_keywords=result.missing_keywords,
        matched_keywords=result.matched_keywords,
        recommendations=result.recommendations,
    )


# ==========================================
# Resume Review
# ==========================================

@router.post("/resume/review", response_model=ResumeReviewResponse)
async def review_resume(
    request: ResumeReviewRequest,
    current_user = Depends(auth.get_current_active_user),
    application_service: ApplicationService = Depends(get_application_service),
):
    """Review resume content quality."""
    result = application_service.review_resume(
        resume_text=request.resume_text,
        target_role=request.target_role,
    )
    return ResumeReviewResponse(
        overall_score=result.overall_score,
        grade=result.grade,
        section_reviews={k: v.to_dict() for k, v in result.section_reviews.items()},
        top_priorities=result.top_priorities,
        strengths=result.strengths,
        overall_feedback=result.overall_feedback,
        improvement_plan=result.improvement_plan,
    )


@router.post("/resume/optimize", response_model=ResumeOptimizationResponse)
async def optimize_resume(
    request: ResumeOptimizationRequest,
    current_user = Depends(auth.get_current_active_user),
    application_service: ApplicationService = Depends(get_application_service),
):
    """Get comprehensive resume optimization suggestions."""
    result = application_service.optimize_resume(
        resume_text=request.resume_text,
        target_role=request.target_role,
        job_description=request.job_description,
    )
    return ResumeOptimizationResponse(**result)


# ==========================================
# Cover Letter
# ==========================================

@router.post("/cover-letter", response_model=CoverLetterResponse)
async def generate_cover_letter(
    request: CoverLetterRequest,
    current_user = Depends(auth.get_current_active_user),
    application_service: ApplicationService = Depends(get_application_service),
):
    """Generate a cover letter for a specific application."""
    result = application_service.generate_cover_letter(
        user_id=current_user.id,
        target_role=request.target_role,
        target_company=request.target_company,
        job_description=request.job_description,
        hiring_manager=request.hiring_manager,
        tone=request.tone,
        length=request.length,
    )
    return CoverLetterResponse(
        content=result.content,
        word_count=result.word_count,
        tone=result.tone.value,
        length=result.length.value,
        key_points_covered=result.key_points_covered,
        personalization_score=result.personalization_score,
        suggestions=result.suggestions,
    )


@router.post("/cover-letter/optimize", response_model=CoverLetterOptimizationResponse)
async def optimize_cover_letter(
    request: CoverLetterOptimizationRequest,
    current_user = Depends(auth.get_current_active_user),
    application_service: ApplicationService = Depends(get_application_service),
):
    """Get optimization suggestions for cover letter."""
    result = application_service.optimize_cover_letter(
        cover_letter=request.cover_letter,
        target_role=request.target_role,
        target_company=request.target_company,
    )
    return CoverLetterOptimizationResponse(**result)


# ==========================================
# Application Answers
# ==========================================

@router.post("/answers", response_model=ApplicationAnswersResponse)
async def generate_answers(
    request: ApplicationAnswersRequest,
    current_user = Depends(auth.get_current_active_user),
    application_service: ApplicationService = Depends(get_application_service),
):
    """Generate answers for application questions."""
    result = application_service.generate_application_answers(
        user_id=current_user.id,
        questions=request.questions,
        target_role=request.target_role,
        target_company=request.target_company,
    )
    return ApplicationAnswersResponse(
        answers=[a.to_dict() for a in result.answers],
        overall_confidence=result.overall_confidence,
        total_word_count=result.total_word_count,
        missing_required=result.missing_required,
        review_notes=result.review_notes,
    )


# ==========================================
# Interview Preparation
# ==========================================

@router.post("/interview-prep", response_model=InterviewPrepResponse)
async def prepare_interview(
    request: InterviewPrepRequest,
    current_user = Depends(auth.get_current_active_user),
    application_service: ApplicationService = Depends(get_application_service),
):
    """Generate interview preparation materials."""
    result = application_service.prepare_for_interview(
        user_id=current_user.id,
        target_role=request.target_role,
        target_company=request.target_company,
        job_description=request.job_description,
    )
    return InterviewPrepResponse(**result)


# ==========================================
# Application CRUD
# ==========================================

@router.post("/", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(
    request: ApplicationCreate,
    current_user = Depends(auth.get_current_active_user),
    application_service: ApplicationService = Depends(get_application_service),
):
    """Submit application to a job."""
    try:
        application = application_service.apply_to_job(
            user_id=current_user.id,
            job_id=request.job_id,
            resume_text=request.resume_text,
            cover_letter=request.cover_letter,
            answers=request.answers,
        )
        return ApplicationResponse.model_validate(application)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[ApplicationListResponse])
async def list_applications(
    status: Optional[str] = Query(None),
    current_user = Depends(auth.get_current_active_user),
    application_service: ApplicationService = Depends(get_application_service),
):
    """List user's applications."""
    apps = application_service.get_user_applications(current_user.id)

    if status:
        def _status_value(s):
            return s.value if hasattr(s, "value") else str(s)
        apps = [a for a in apps if _status_value(a.status) == status]

    return [
        ApplicationListResponse(
            id=a.id,
            job_id=a.job_id,
            job_title=a.job.title if a.job else "Unknown",
            company_name=a.job.company.name if a.job and a.job.company else "Unknown",
            status=a.status.value if hasattr(a.status, "value") else str(a.status),
            applied_date=a.applied_date,
            response_date=a.response_date,
            interview_date=a.interview_date,
        )
        for a in apps
    ]


# ==========================================
# Application Stats & Insights
# ==========================================

@router.get("/stats", response_model=ApplicationStatsResponse)
async def get_application_stats(
    current_user = Depends(auth.get_current_active_user),
    application_service: ApplicationService = Depends(get_application_service),
):
    """Get application statistics."""
    stats = application_service.get_application_stats(current_user.id)
    return ApplicationStatsResponse(**stats)


@router.get("/stats/insights", response_model=Dict[str, Any])
async def get_application_insights(
    current_user = Depends(auth.get_current_active_user),
    application_service: ApplicationService = Depends(get_application_service),
):
    """Get application insights and analytics."""
    return application_service.get_application_insights(current_user.id)


@router.get("/{application_id}", response_model=ApplicationResponse)
async def get_application(
    application_id: int,
    current_user = Depends(auth.get_current_active_user),
    application_service: ApplicationService = Depends(get_application_service),
):
    """Get application details."""
    application = application_service.get_application(application_id, current_user.id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    return ApplicationResponse.model_validate(application)


@router.put("/{application_id}", response_model=ApplicationResponse)
async def update_application(
    application_id: int,
    request: ApplicationUpdate,
    current_user = Depends(auth.get_current_active_user),
    application_service: ApplicationService = Depends(get_application_service),
):
    """Update application details."""
    application = application_service.get_application(application_id, current_user.id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    from backend.models.application import ApplicationStatus
    db = application_service.db
    if request.status:
        try:
            application.status = ApplicationStatus(request.status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")
    if request.notes is not None:
        application.notes = request.notes
    db.commit()
    db.refresh(application)
    return ApplicationResponse.model_validate(application)


@router.patch("/{application_id}/status", response_model=ApplicationResponse)
async def update_application_status(
    application_id: int,
    body: dict,
    current_user = Depends(auth.get_current_active_user),
    application_service: ApplicationService = Depends(get_application_service),
):
    """Update application status."""
    application = application_service.get_application(application_id, current_user.id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    new_status = body.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="Status is required")

    from backend.models.application import ApplicationStatus
    try:
        status_enum = ApplicationStatus(new_status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {new_status}")
    application.status = status_enum
    from datetime import date as date_type
    if new_status == "submitted" and not application.applied_date:
        application.applied_date = date_type.today()
    elif new_status == "interview_scheduled":
        interview_date = body.get("interview_date")
        if interview_date:
            application.interview_date = interview_date
    elif new_status in ("rejected", "offer_received"):
        application.response_date = date_type.today()

    notes = body.get("notes")
    if notes is not None:
        application.notes = notes

    db = application_service.db
    db.commit()
    db.refresh(application)
    return ApplicationResponse.model_validate(application)


@router.delete("/{application_id}", status_code=204)
async def delete_application(
    application_id: int,
    current_user = Depends(auth.get_current_active_user),
    application_service: ApplicationService = Depends(get_application_service),
):
    """Delete an application."""
    application = application_service.get_application(application_id, current_user.id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    db = application_service.db
    db.delete(application)
    db.commit()
    return None


# ==========================================
# Resume Upload
# ==========================================

@router.post("/resume/upload")
async def upload_resume(
    file: UploadFile = File(...),
    current_user = Depends(auth.get_current_active_user),
    application_service: ApplicationService = Depends(get_application_service),
):
    """Upload and parse resume file."""
    # This would integrate with resume parsing service
    # For now, return placeholder
    return {
        "message": "Resume upload endpoint - integrate with resume parsing service",
        "filename": file.filename,
    }


# ==========================================
# Schemas
# ==========================================

from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class ApplicationStatusEnum(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEW_COMPLETED = "interview_completed"
    OFFER_RECEIVED = "offer_received"
    OFFER_ACCEPTED = "offer_accepted"
    OFFER_DECLINED = "offer_declined"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class ApplicationPrepareRequest(BaseModel):
    job_id: int
    resume_text: str
    candidate_profile: Dict[str, Any]
    job_description: Optional[str] = None
    cover_letter_tone: str = "professional"
    cover_letter_length: str = "medium"


class ApplicationPrepareResponse(BaseModel):
    application_id: str
    resume_ats_result: Optional[Dict[str, Any]] = None
    resume_review_result: Optional[Dict[str, Any]] = None
    cover_letter_result: Optional[Dict[str, Any]] = None
    answers_result: Optional[Dict[str, Any]] = None
    ready_to_submit: bool
    checklist: List[Dict[str, Any]]
    next_steps: List[str]


class ATSAnalysisRequest(BaseModel):
    resume_text: str
    target_role: Optional[str] = None
    job_description: Optional[str] = None


class ATSAnalysisResponse(BaseModel):
    overall_score: float
    passed: bool
    issues: List[Dict[str, Any]]
    keyword_match_score: float
    format_score: float
    section_score: float
    content_score: float
    missing_keywords: List[str]
    matched_keywords: List[str]
    recommendations: List[str]


class ResumeReviewRequest(BaseModel):
    resume_text: str
    target_role: Optional[str] = None


class ResumeReviewResponse(BaseModel):
    overall_score: float
    grade: str
    section_reviews: Dict[str, Dict[str, Any]]
    top_priorities: List[str]
    strengths: List[str]
    overall_feedback: str
    improvement_plan: List[Dict[str, Any]]


class ResumeOptimizationRequest(BaseModel):
    resume_text: str
    target_role: Optional[str] = None
    job_description: Optional[str] = None


class ResumeOptimizationResponse(BaseModel):
    ats_score: float
    ats_passed: bool
    review_score: float
    review_grade: str
    ats_issues: List[Dict[str, Any]]
    review_issues: List[Dict[str, Any]]
    missing_keywords: List[str]
    recommendations: List[str]
    improvement_plan: List[Dict[str, Any]]


class CoverLetterRequest(BaseModel):
    target_role: str
    target_company: str
    job_description: Optional[str] = None
    hiring_manager: Optional[str] = None
    tone: str = "professional"
    length: str = "medium"


class CoverLetterResponse(BaseModel):
    content: str
    word_count: int
    tone: str
    length: str
    key_points_covered: List[str]
    personalization_score: float
    suggestions: List[str]


class CoverLetterOptimizationRequest(BaseModel):
    cover_letter: str
    target_role: str
    target_company: str


class CoverLetterOptimizationResponse(BaseModel):
    word_count: int
    suggestions: List[str]
    company_mentions: int


class ApplicationAnswersRequest(BaseModel):
    questions: List[str]
    target_role: Optional[str] = None
    target_company: Optional[str] = None


class ApplicationAnswersResponse(BaseModel):
    answers: List[Dict[str, Any]]
    overall_confidence: float
    total_word_count: int
    missing_required: List[str]
    review_notes: List[str]


class InterviewPrepRequest(BaseModel):
    target_role: str
    target_company: str
    job_description: Optional[str] = None


class InterviewPrepResponse(BaseModel):
    likely_questions: List[Dict[str, Any]]
    star_stories: List[Dict[str, str]]
    company_research: List[str]
    technical_preparation: Dict[str, Any]
    questions_to_ask: List[str]


class ApplicationCreate(BaseModel):
    job_id: int
    resume_text: str
    cover_letter: Optional[str] = None
    answers: Optional[Dict[str, str]] = None


class ApplicationUpdate(BaseModel):
    status: str
    notes: Optional[str] = None


class ApplicationListResponse(BaseModel):
    id: int
    job_id: int
    job_title: str
    company_name: str
    status: str
    applied_date: Optional[date] = None
    response_date: Optional[date] = None
    interview_date: Optional[date] = None


class ApplicationResponse(BaseModel):
    id: int
    user_id: int
    job_id: int
    resume_id: Optional[int] = None
    cover_letter: Optional[str] = None
    status: str
    applied_date: Optional[date] = None
    response_date: Optional[date] = None
    interview_date: Optional[date] = None
    notes: Optional[str] = None
    application_answers: Optional[Dict[str, str]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ApplicationStatsResponse(BaseModel):
    total: int
    by_status: Dict[str, int]
    response_rate: float
    interview_rate: float
    offer_rate: float