from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class JobSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)
    location: Optional[str] = None
    remote: Optional[bool] = None
    limit: int = Field(50, ge=1, le=200)
    sources: Optional[List[str]] = None


class JobSearchResponse(BaseModel):
    jobs_found: int
    jobs: List["JobListResponse"]


class JobListResponse(BaseModel):
    id: int
    title: str
    company_name: Optional[str] = None
    location: Optional[str] = None
    is_remote: bool
    remote_type: Optional[str] = None
    salary_yearly_min: Optional[int] = None
    salary_yearly_max: Optional[int] = None
    salary_currency: str
    experience_level: Optional[str] = None
    employment_type: Optional[str] = None
    source: str
    quality_score: float
    posted_date: Optional[datetime] = None
    skills: Optional[List[str]] = None

    model_config = {"from_attributes": True}

    @classmethod
    def model_validate(cls, obj):
        if hasattr(obj, 'company') and obj.company:
            data = obj.__dict__.copy()
            data['company_name'] = obj.company.name
            return cls(**data)
        return super().model_validate(obj)


class JobResponse(BaseModel):
    id: int
    title: str
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    location: Optional[str] = None
    is_remote: bool
    remote_type: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    responsibilities: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: str
    salary_period: Optional[str] = None
    salary_yearly_min: Optional[int] = None
    salary_yearly_max: Optional[int] = None
    experience_level: Optional[str] = None
    employment_type: Optional[str] = None
    source: str
    source_url: Optional[str] = None
    source_job_id: Optional[str] = None
    posted_date: Optional[datetime] = None
    expires_date: Optional[datetime] = None
    application_url: Optional[str] = None
    application_email: Optional[str] = None
    skills: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    quality_score: float
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def model_validate(cls, obj):
        if hasattr(obj, 'company') and obj.company:
            data = obj.__dict__.copy()
            data['company_name'] = obj.company.name
            return cls(**data)
        return super().model_validate(obj)


class JobRecommendationResponse(BaseModel):
    job_id: int
    title: str
    company: str
    location: str
    is_remote: bool
    remote_type: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    experience_level: Optional[str] = None
    employment_type: Optional[str] = None
    match_score: float
    tier: str
    highlights: List[str]
    concerns: List[str]
    action_items: List[str]
    matching_skills: List[Dict[str, Any]]
    missing_skills: List[str]
    posted_date: Optional[datetime] = None
    application_url: Optional[str] = None


class JobRecommendationsResponse(BaseModel):
    recommendations: List[JobRecommendationResponse]
    total: int


class JobStatsResponse(BaseModel):
    total_jobs: int
    remote_jobs: int
    remote_percentage: float
    by_source: Dict[str, int]
    by_experience_level: Dict[str, int]
    top_skills: Dict[str, int]


class SavedJobResponse(BaseModel):
    application_id: int
    job_id: int
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    is_remote: Optional[bool] = None
    status: str
    saved_date: datetime
    applied_date: Optional[datetime] = None
    match_score: Optional[float] = None