from datetime import date, datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field


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