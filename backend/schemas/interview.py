from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class InterviewQuestionsRequest(BaseModel):
    target_role: str
    target_company: Optional[str] = None
    job_description: Optional[str] = None
    interview_type: str = "behavioral"
    num_questions: int = Field(default=5, ge=1, le=20)


class InterviewQuestion(BaseModel):
    id: int
    question: str
    category: str
    difficulty: str
    tips: Optional[str] = None
    star_method_hint: Optional[str] = None


class InterviewQuestionsResponse(BaseModel):
    questions: List[InterviewQuestion]
    interview_type: str
    target_role: str
    target_company: Optional[str] = None


class MockInterviewStartRequest(BaseModel):
    target_role: str
    target_company: Optional[str] = None
    job_description: Optional[str] = None
    interview_type: str = "behavioral"
    num_questions: int = Field(default=5, ge=1, le=15)


class MockInterviewStartResponse(BaseModel):
    session_id: int
    title: str
    questions: List[InterviewQuestion]
    total_questions: int
    interview_type: str


class MockAnswerRequest(BaseModel):
    session_id: int
    question_id: int
    answer: str


class AnswerEvaluation(BaseModel):
    question_id: int
    score: float = Field(ge=0, le=10)
    content_score: float = Field(ge=0, le=10, description="Relevance and substance")
    communication_score: float = Field(ge=0, le=10, description="Clarity and articulation")
    confidence_score: float = Field(ge=0, le=10, description="Assertiveness and poise")
    structure_score: float = Field(ge=0, le=10, description="STAR method usage")
    clarity_score: float = Field(ge=0, le=10, description="Conciseness and focus")
    strengths: List[str]
    improvements: List[str]
    mistakes: List[str]
    sample_answer: Optional[str] = None
    feedback: str
    word_count: int
    uses_star_method: bool


class MockAnswerResponse(BaseModel):
    evaluation: AnswerEvaluation
    questions_answered: int
    total_questions: int
    is_complete: bool


class MockInterviewEndResponse(BaseModel):
    session_id: int
    overall_score: float
    avg_content_score: float
    avg_communication_score: float
    avg_confidence_score: float
    avg_structure_score: float
    avg_clarity_score: float
    strengths: List[str]
    weaknesses: List[str]
    improvement_areas: List[str]
    detailed_feedback: str
    questions_evaluated: int
    duration_minutes: int


class STARStoryRequest(BaseModel):
    experience_description: str
    target_role: Optional[str] = None
    num_stories: int = Field(default=3, ge=1, le=10)


class STARStory(BaseModel):
    situation: str
    task: str
    action: str
    result: str
    full_story: str
    applicable_questions: List[str]


class STARStoriesResponse(BaseModel):
    stories: List[STARStory]
    tips: List[str]


class InterviewFeedbackResponse(BaseModel):
    session_id: int
    title: str
    target_role: Optional[str]
    target_company: Optional[str]
    overall_score: Optional[float]
    questions: List[Dict[str, Any]]
    evaluations: List[Dict[str, Any]]
    strengths: Optional[List[str]]
    weaknesses: Optional[List[str]]
    improvement_areas: Optional[List[str]]
    feedback: Optional[str]
    duration_minutes: Optional[int]
    completed_at: Optional[datetime]


class SavedInterviewResponse(BaseModel):
    id: int
    title: str
    target_role: Optional[str]
    target_company: Optional[str]
    interview_type: str
    status: str
    overall_score: Optional[float]
    questions_count: int
    duration_minutes: Optional[int]
    created_at: datetime


class SelfIntroRequest(BaseModel):
    target_role: str
    target_company: Optional[str] = None
    experience_years: Optional[int] = None
    key_skills: Optional[List[str]] = None
    notable_achievements: Optional[List[str]] = None


class SelfIntroResponse(BaseModel):
    introductions: List[Dict[str, str]]
    tips: List[str]
    common_mistakes: List[str]
    structure_guide: str
