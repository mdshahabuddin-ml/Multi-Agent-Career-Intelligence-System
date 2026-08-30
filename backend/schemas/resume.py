from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field
from pydantic import EmailStr


class ResumeUploadResponse(BaseModel):
    id: int
    filename: str
    status: str
    message: str


class ResumeParseResponse(BaseModel):
    id: int
    status: str
    sections: List[str]
    skills_count: int
    projects_count: int
    experience_entries: int
    years_of_experience: int


class ResumeATSResponse(BaseModel):
    overall_score: float
    breakdown: Dict[str, Any]
    recommendations: List[str]
    target_role: Optional[str] = None
    word_count: Optional[int] = None


class ResumeReviewResponse(BaseModel):
    content: Dict[str, Any]
    experience: Dict[str, Any]
    skills: Dict[str, Any]
    projects: Dict[str, Any]
    overall: Dict[str, Any]
    word_count: int


class ResumeListResponse(BaseModel):
    id: int
    original_filename: str
    file_size: int
    status: str
    is_primary: bool
    ats_score: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ResumeResponse(BaseModel):
    id: int
    user_id: int
    filename: str
    original_filename: str
    file_path: str
    file_size: int
    mime_type: str
    status: str
    raw_text: Optional[str] = None
    parsed_data: Optional[Dict[str, Any]] = None
    sections: Optional[Dict[str, Any]] = None
    extracted_skills: Optional[List[str]] = None
    extracted_projects: Optional[List[Dict[str, Any]]] = None
    extracted_experience: Optional[List[Dict[str, Any]]] = None
    extracted_education: Optional[List[Dict[str, Any]]] = None
    ats_score: Optional[float] = None
    ats_feedback: Optional[Dict[str, Any]] = None
    is_primary: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}