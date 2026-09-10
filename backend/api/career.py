from typing import Optional, List, Dict, Any
from datetime import datetime, date

from fastapi import APIRouter, Depends, HTTPException, status, Query, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from backend.api import auth
from backend.database import get_db
from backend.services.career_service import CareerService
from backend.agents.career import (
    CareerAssessment,
    CareerGoal,
    LearningPlan,
    LearningStyle,
    AdvisorFocus,
)

router = APIRouter(prefix="/career", tags=["Career Intelligence"])


def get_career_service(db: Session = Depends(get_db)) -> CareerService:
    return CareerService(db)


# ==========================================
# Request/Response Schemas
# ==========================================

class CareerAssessmentRequest(BaseModel):
    current_role: str = Field(..., min_length=1, max_length=100)
    years_experience: int = Field(0, ge=0, le=50)
    skills: List[Dict[str, Any]] = Field(default_factory=list)
    target_role: Optional[str] = None
    interests: Optional[List[str]] = None
    weekly_learning_hours: int = Field(10, ge=1, le=40)
    learning_budget: float = Field(0.0, ge=0)
    learning_style: LearningStyle = LearningStyle.MIXED


class CareerAssessmentResponse(BaseModel):
    overall_score: float
    strengths: List[str]
    areas_for_improvement: List[str]
    next_actions: List[str]
    skill_gap_analysis: Optional[Dict[str, Any]] = None
    career_trajectory: Optional[Dict[str, Any]] = None
    learning_plan: Optional[Dict[str, Any]] = None
    advice: List[Dict[str, Any]]
    generated_at: datetime


class CareerGoalCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=10)
    target_date: date
    target_role: Optional[str] = None
    target_skills: Optional[List[str]] = None


class CareerGoalResponse(BaseModel):
    id: str
    user_id: int
    title: str
    description: str
    target_date: Optional[date] = None
    target_role: Optional[str] = None
    target_skills: List[str]
    milestones: List[Dict[str, Any]]
    is_active: bool
    progress: float
    created_at: datetime

    model_config = {"from_attributes": True}


class CareerGoalUpdate(BaseModel):
    completed_milestones: List[str]


class JobSearchStrategyResponse(BaseModel):
    target_roles: List[str]
    key_skills_to_highlight: List[str]
    skill_gaps_to_address: List[str]
    networking_strategy: List[str]
    application_timeline: str
    salary_expectations: Dict[str, Any]
    preparation_checklist: List[str]


class SkillRecommendationsResponse(BaseModel):
    missing_skills: List[str]
    proficiency_gaps: List[Dict[str, Any]]
    priority_skills: List[str]
    learning_resources: Dict[str, List[Dict[str, Any]]]


class CareerPathOptionsResponse(BaseModel):
    recommended_path: Optional[Dict[str, Any]] = None
    alternative_paths: List[Dict[str, Any]]
    decision_factors: Dict[str, float]


class LearningResourcesResponse(BaseModel):
    skill: str
    resources: List[Dict[str, Any]]


class LearningPlanCreateRequest(BaseModel):
    target_role: str
    target_skills: List[str]
    skill_gaps: List[str]
    weekly_hours: int = Field(10, ge=1, le=40)
    learning_style: LearningStyle = LearningStyle.MIXED
    budget: float = Field(0.0, ge=0)


class LearningPlanResponse(BaseModel):
    id: str
    user_id: int
    target_role: str
    target_skills: List[str]
    current_skills: List[str]
    skill_gaps: List[str]
    phases: List[Dict[str, Any]]
    total_estimated_weeks: int
    weekly_time_commitment_hours: int
    start_date: date
    target_completion_date: Optional[date]
    learning_style: LearningStyle
    budget: float


class CareerInsightsResponse(BaseModel):
    total_skills: int
    skill_categories: Dict[str, int]
    top_skills: List[str]
    experience_level: str
    market_demand: Dict[str, float]
    salary_estimate: Dict[str, int]


# ==========================================
# API Endpoints
# ==========================================

@router.post("/assess", response_model=CareerAssessmentResponse, status_code=status.HTTP_201_CREATED)
async def assess_career(
    request: CareerAssessmentRequest,
    current_user = Depends(auth.get_current_active_user),
    career_service: CareerService = Depends(get_career_service),
):
    """Perform comprehensive career assessment."""
    assessment = career_service.assess_career(
        user_id=current_user.id,
        current_role=request.current_role,
        years_experience=request.years_experience,
        skills=request.skills,
        target_role=request.target_role,
        interests=request.interests,
        weekly_learning_hours=request.weekly_learning_hours,
        learning_budget=request.learning_budget,
        learning_style=request.learning_style,
    )
    return CareerAssessmentResponse(
        overall_score=assessment.overall_score,
        strengths=assessment.strengths,
        areas_for_improvement=assessment.areas_for_improvement,
        next_actions=assessment.next_actions,
        skill_gap_analysis=assessment.skill_gap_analysis.to_dict() if assessment.skill_gap_analysis else None,
        career_trajectory=assessment.career_trajectory.to_dict() if assessment.career_trajectory else None,
        learning_plan=assessment.learning_plan.to_dict() if assessment.learning_plan else None,
        advice=[a.to_dict() for a in assessment.advice],
        generated_at=assessment.generated_at,
    )


@router.post("/goals", response_model=CareerGoalResponse, status_code=status.HTTP_201_CREATED)
async def create_career_goal(
    request: CareerGoalCreate,
    current_user = Depends(auth.get_current_active_user),
    career_service: CareerService = Depends(get_career_service),
):
    """Create a new career goal."""
    goal = career_service.create_career_goal(
        user_id=current_user.id,
        title=request.title,
        description=request.description,
        target_date=request.target_date,
        target_role=request.target_role,
        target_skills=request.target_skills,
    )
    return CareerGoalResponse(
        id=goal.id,
        user_id=goal.user_id,
        title=goal.title,
        description=goal.description,
        target_date=goal.target_date,
        target_role=goal.target_role,
        target_skills=goal.target_skills,
        milestones=goal.milestones,
        is_active=goal.is_active,
        progress=goal.progress,
        created_at=goal.created_at,
    )


@router.get("/goals", response_model=List[CareerGoalResponse])
async def list_career_goals(
    current_user = Depends(auth.get_current_active_user),
    career_service: CareerService = Depends(get_career_service),
):
    """List user's career goals."""
    goals = career_service.get_career_goals(current_user.id)
    return [
        CareerGoalResponse(
            id=str(g.id),
            user_id=g.user_id,
            title=g.title,
            description=g.description,
            target_date=g.target_completion_date,
            target_role=g.target_role,
            target_skills=g.skill_gaps,
            milestones=g.milestones,
            is_active=g.status != "completed",
            progress=g.progress_percentage,
            created_at=g.created_at,
        )
        for g in goals
    ]


@router.post("/goals/{goal_id}/progress", response_model=CareerGoalResponse)
async def update_goal_progress(
    goal_id: int,
    request: CareerGoalUpdate,
    current_user = Depends(auth.get_current_active_user),
    career_service: CareerService = Depends(get_career_service),
):
    """Update career goal progress."""
    goal = career_service.update_goal_progress(goal_id, current_user.id, request.completed_milestones)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    return CareerGoalResponse(
        id=str(goal.id),
        user_id=goal.user_id,
        title=goal.title,
        description=goal.description,
        target_date=goal.target_completion_date,
        target_role=goal.target_role,
        target_skills=goal.skill_gaps,
        milestones=goal.milestones,
        is_active=goal.status != "completed",
        progress=goal.progress_percentage,
        created_at=goal.created_at,
    )


@router.get("/job-search-strategy", response_model=JobSearchStrategyResponse)
async def get_job_search_strategy(
    target_role: Optional[str] = Query(None),
    current_user = Depends(auth.get_current_active_user),
    career_service: CareerService = Depends(get_career_service),
):
    """Get personalized job search strategy."""
    strategy = career_service.get_job_search_strategy(
        user_id=current_user.id,
        target_role=target_role,
    )
    return JobSearchStrategyResponse(**strategy)


@router.get("/skill-recommendations", response_model=SkillRecommendationsResponse)
async def get_skill_recommendations(
    target_role: str = Query(..., min_length=1),
    current_user = Depends(auth.get_current_active_user),
    career_service: CareerService = Depends(get_career_service),
):
    """Get skill recommendations for a target role."""
    recommendations = career_service.get_skill_recommendations(
        user_id=current_user.id,
        target_role=target_role,
    )
    return SkillRecommendationsResponse(**recommendations)


@router.get("/path-options", response_model=CareerPathOptionsResponse)
async def get_career_path_options(
    current_role: str = Query(..., min_length=1),
    current_user = Depends(auth.get_current_active_user),
    career_service: CareerService = Depends(get_career_service),
):
    """Get possible career paths from current role."""
    options = career_service.get_career_path_options(
        user_id=current_user.id,
        current_role=current_role,
    )
    return CareerPathOptionsResponse(**options)


@router.get("/learning-resources", response_model=LearningResourcesResponse)
async def get_learning_resources(
    skill: str = Query(..., min_length=1),
    difficulty: Optional[str] = Query(None),
    budget: float = Query(0.0, ge=0),
    current_user = Depends(auth.get_current_active_user),
    career_service: CareerService = Depends(get_career_service),
):
    """Get learning resource recommendations for a skill."""
    resources = career_service.get_learning_resources(
        skill=skill,
        difficulty=difficulty,
        budget=budget,
    )
    return LearningResourcesResponse(skill=skill, resources=resources)


@router.post("/learning-plan", response_model=LearningPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_learning_plan(
    request: LearningPlanCreateRequest,
    current_user = Depends(auth.get_current_active_user),
    career_service: CareerService = Depends(get_career_service),
):
    """Create a learning plan."""
    plan = career_service.create_learning_plan(
        user_id=current_user.id,
        target_role=request.target_role,
        target_skills=request.target_skills,
        skill_gaps=request.skill_gaps,
        weekly_hours=request.weekly_hours,
        learning_style=request.learning_style,
        budget=request.budget,
    )
    return LearningPlanResponse(
        id=plan.id,
        user_id=plan.user_id,
        target_role=plan.target_role,
        target_skills=plan.target_skills,
        current_skills=plan.current_skills,
        skill_gaps=plan.skill_gaps,
        phases=[p.to_dict() for phase in plan.phases for p in [phase]],
        total_estimated_weeks=plan.total_estimated_weeks,
        weekly_time_commitment_hours=plan.weekly_time_commitment_hours,
        start_date=plan.start_date,
        target_completion_date=plan.target_completion_date,
        learning_style=plan.learning_style,
        budget=plan.budget,
    )


@router.get("/insights", response_model=CareerInsightsResponse)
async def get_career_insights(
    current_user = Depends(auth.get_current_active_user),
    career_service: CareerService = Depends(get_career_service),
):
    """Get career insights and analytics."""
    insights = career_service.get_career_insights(current_user.id)
    return CareerInsightsResponse(**insights)


from datetime import datetime