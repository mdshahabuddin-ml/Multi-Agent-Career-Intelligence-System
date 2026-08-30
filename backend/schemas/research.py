from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field


class ResearchType(str, Enum):
    JOB_MARKET = "job_market"
    COMPANY = "company"
    TECHNOLOGY = "technology"
    CAREER_PATH = "career_path"
    SKILL_ANALYSIS = "skill_analysis"
    SALARY = "salary"
    INTERVIEW_PREP = "interview_prep"
    GENERAL = "general"


class ResearchStatus(str, Enum):
    CREATED = "created"
    PLANNING = "planning"
    RESEARCHING = "researching"
    COLLECTING_EVIDENCE = "collecting_evidence"
    VERIFYING = "verifying"
    ANALYZING = "analyzing"
    SYNTHESIZING = "synthesizing"
    COMPLETED = "completed"
    FAILED = "failed"


class ResearchStartRequest(BaseModel):
    query: str = Field(..., min_length=5, max_length=500)
    research_type: ResearchType = ResearchType.GENERAL
    target_role: Optional[str] = None
    target_company: Optional[str] = None
    target_location: Optional[str] = None
    max_sources: int = Field(10, ge=1, le=50)
    timeout_seconds: int = Field(300, ge=30, le=1800)


class ResearchStartResponse(BaseModel):
    id: int
    query: str
    research_type: ResearchType
    status: ResearchStatus
    message: str


class ResearchStatusResponse(BaseModel):
    id: int
    query: str
    status: ResearchStatus
    progress: int
    source_count: int
    verified_claim_count: int
    confidence_score: Optional[float] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class ResearchListResponse(BaseModel):
    id: int
    query: str
    research_type: ResearchType
    status: ResearchStatus
    source_count: int
    verified_claim_count: int
    confidence_score: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ResearchReportResponse(BaseModel):
    id: int
    query: str
    research_type: ResearchType
    executive_summary: str
    key_findings: List[str]
    recommendations: List[str]
    confidence_score: float
    source_count: int
    verified_claim_count: int
    completed_at: datetime


class ResearchSourceResponse(BaseModel):
    index: int
    title: str
    url: str
    source_type: str
    domain: str
    author: Optional[str] = None
    published_date: Optional[str] = None
    credibility: float
    relevance: float
    snippet: str


class ResearchCitationResponse(BaseModel):
    source_index: int
    source_title: str
    source_url: str
    source_type: str
    supporting_claims: List[str]
    citation_format: str