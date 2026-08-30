import logging
from typing import List, Dict, Any, Optional
from datetime import date, datetime

from sqlalchemy.orm import Session

from backend.agents.career import (
    CareerAdvisor,
    CareerAssessment,
    CareerGoal,
    LearningStyle,
    AdvisorFocus,
)
from backend.models import User, Skill, LearningPlan, LearningPlan as LearningPlanModel
from backend.database import get_db

logger = logging.getLogger(__name__)


class CareerService:
    """Service for career intelligence operations."""

    def __init__(self, db: Session):
        self.db = db
        self.advisor = CareerAdvisor()

    def assess_career(
        self,
        user_id: int,
        current_role: str,
        years_experience: int,
        skills: List[Dict[str, Any]],
        target_role: Optional[str] = None,
        interests: Optional[List[str]] = None,
        weekly_learning_hours: int = 10,
        learning_budget: float = 0.0,
        learning_style: LearningStyle = LearningStyle.MIXED,
    ) -> CareerAssessment:
        """Perform comprehensive career assessment."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        assessment = self.advisor.assess_career(
            user_id=user_id,
            current_role=current_role,
            years_experience=years_experience,
            skills=skills,
            target_role=target_role,
            interests=interests,
            weekly_learning_hours=weekly_learning_hours,
            learning_budget=learning_budget,
            learning_style=learning_style,
        )

        return assessment

    def create_career_goal(
        self,
        user_id: int,
        title: str,
        description: str,
        target_date: date,
        target_role: Optional[str] = None,
        target_skills: Optional[List[str]] = None,
    ) -> CareerGoal:
        """Create a new career goal."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        goal = self.advisor.create_career_goal(
            user_id=user_id,
            title=title,
            description=description,
            target_date=target_date,
            target_role=target_role,
            target_skills=target_skills,
        )

        # Save to database
        db_goal = LearningPlanModel(
            user_id=user_id,
            target_role=target_role or "",
            skill_gaps=target_skills or [],
            title=title,
            description=description,
            estimated_weeks=0,
            resources=[],
            milestones=[],
            status="not_started",
            progress_percentage=0.0,
            target_completion_date=target_date,
        )
        self.db.add(db_goal)
        self.db.commit()
        self.db.refresh(db_goal)

        return goal

    def get_career_goals(self, user_id: int) -> List[LearningPlanModel]:
        """Get user's career goals."""
        return self.db.query(LearningPlanModel).filter(
            LearningPlanModel.user_id == user_id
        ).order_by(LearningPlanModel.created_at.desc()).all()

    def update_goal_progress(
        self,
        goal_id: int,
        user_id: int,
        completed_milestones: List[str],
    ) -> Optional[LearningPlanModel]:
        """Update career goal progress."""
        goal = self.db.query(LearningPlanModel).filter(
            LearningPlanModel.id == goal_id,
            LearningPlanModel.user_id == user_id,
        ).first()

        if not goal:
            return None

        if goal.milestones:
            completed = sum(1 for m in goal.milestones if m.get("title") in completed_milestones)
            goal.progress_percentage = completed / len(goal.milestones)

            if goal.progress_percentage >= 1.0:
                goal.status = "completed"
                goal.completed_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(goal)
        return goal

    def get_job_search_strategy(
        self,
        user_id: int,
        target_role: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get personalized job search strategy."""
        # Get latest assessment
        assessment = self._get_latest_assessment(user_id)
        if not assessment:
            # Create a quick assessment
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError("User not found")

            # Get user skills
            skills = self._get_user_skills(user_id)

            assessment = self.advisor.assess_career(
                user_id=user_id,
                current_role=target_role or "Software Engineer",
                years_experience=0,  # Would get from profile
                skills=skills,
                target_role=target_role,
            )

        return self.advisor.get_personalized_job_search_strategy(assessment)

    def get_skill_recommendations(
        self,
        user_id: int,
        target_role: str,
    ) -> Dict[str, Any]:
        """Get skill recommendations for a target role."""
        assessment = self._get_latest_assessment(user_id)
        if not assessment or not assessment.skill_gap_analysis:
            # Quick assessment
            user = self.db.query(User).filter(User.id == user_id).first()
            skills = self._get_user_skills(user_id)

            assessment = self.advisor.assess_career(
                user_id=user_id,
                current_role="Software Engineer",
                years_experience=0,
                skills=skills,
                target_role=target_role,
            )

        if not assessment.skill_gap_analysis:
            return {"missing_skills": [], "priority_skills": [], "learning_resources": {}}

        return {
            "missing_skills": [g.skill_name for g in assessment.skill_gap_analysis.gaps if g.is_missing],
            "proficiency_gaps": [
                {
                    "skill": g.skill_name,
                    "current": g.candidate_proficiency.value if g.candidate_proficiency else None,
                    "required": g.required_proficiency.value,
                    "gap_severity": g.gap_severity,
                }
                for g in assessment.skill_gap_analysis.gaps if not g.is_missing and g.gap_severity > 0.3
            ],
            "priority_skills": assessment.skill_gap_analysis.priority_skills,
            "learning_resources": {
                g.skill_name: g.learning_resources for g in assessment.skill_gap_analysis.gaps
            },
        }

    def get_career_path_options(
        self,
        user_id: int,
        current_role: str,
    ) -> Dict[str, Any]:
        """Get possible career paths from current role."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        skills = self._get_user_skills(user_id)
        trajectory = self.advisor.career_path_agent.generate_trajectory(
            current_role=current_role,
            current_skills=[s["name"] for s in skills],
            years_experience=0,  # Would get from profile
        )

        return {
            "recommended_path": trajectory.recommended_path.to_dict() if trajectory.recommended_path else None,
            "alternative_paths": [p.to_dict() for p in trajectory.alternative_paths],
            "decision_factors": trajectory.decision_factors,
        }

    def get_learning_resources(
        self,
        skill: str,
        difficulty: Optional[str] = None,
        budget: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Get learning resource recommendations for a skill."""
        resources = self.advisor.learning_agent.get_resource_recommendations(
            skill=skill,
            difficulty=difficulty,
            budget=budget,
        )

        return [
            {
                "title": r.title,
                "type": r.resource_type.value,
                "provider": r.provider,
                "url": r.url,
                "difficulty": r.difficulty.value,
                "estimated_hours": r.estimated_hours,
                "cost": r.cost,
                "rating": r.rating,
                "skills_covered": r.skills_covered,
                "certification": r.certification,
            }
            for r in resources
        ]

    def create_learning_plan(
        self,
        user_id: int,
        target_role: str,
        target_skills: List[str],
        skill_gaps: List[str],
        weekly_hours: int = 10,
        learning_style: LearningStyle = LearningStyle.MIXED,
        budget: float = 0.0,
    ) -> LearningPlan:
        """Create a learning plan and save to database."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        current_skills = [s["name"] for s in self._get_user_skills(user_id)]

        plan = self.advisor.learning_agent.generate_learning_plan(
            user_id=user_id,
            target_role=target_role,
            target_skills=target_skills,
            current_skills=current_skills,
            skill_gaps=skill_gaps,
            weekly_hours=weekly_hours,
            learning_style=learning_style,
            budget=budget,
        )

        # Save to database
        db_plan = LearningPlanModel(
            user_id=user_id,
            target_role=target_role,
            skill_gaps=skill_gaps,
            title=f"Learning Plan: {target_role}",
            description=f"Learning plan to bridge skill gaps for {target_role}",
            estimated_weeks=plan.total_estimated_weeks,
            resources=[r.to_dict() for phase in plan.phases for m in phase.milestones for r in m.resources],
            milestones=[
                {
                    "id": m.id,
                    "title": m.title,
                    "description": m.description,
                    "target_skills": m.target_skills,
                    "estimated_weeks": m.estimated_weeks,
                    "completion_criteria": m.completion_criteria,
                    "order": m.order,
                }
                for phase in plan.phases for m in phase.milestones
            ],
            status="not_started",
            progress_percentage=0.0,
        )
        self.db.add(db_plan)
        self.db.commit()
        self.db.refresh(db_plan)

        return plan

    def _get_latest_assessment(self, user_id: int) -> Optional[CareerAssessment]:
        """Get latest career assessment for user."""
        # In production, would retrieve from cache/database
        return None

    def _get_user_skills(self, user_id: int) -> List[Dict[str, Any]]:
        """Get user's skills from database."""
        skills = self.db.query(Skill).filter(Skill.profile_id == user_id).all()
        return [
            {
                "name": s.name,
                "category": s.category or "technical",
                "proficiency": s.proficiency or "intermediate",
                "years_experience": 0,
            }
            for s in skills
        ]

    def get_career_insights(self, user_id: int) -> Dict[str, Any]:
        """Get career insights and analytics."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        skills = self._get_user_skills(user_id)
        skill_names = [s["name"] for s in skills]

        return {
            "total_skills": len(skills),
            "skill_categories": self._categorize_skills(skills),
            "top_skills": skill_names[:10],
            "experience_level": self._infer_experience_level(0),  # Would use profile
            "market_demand": self._estimate_market_demand(skill_names),
            "salary_estimate": self._estimate_salary(skill_names),
        }

    def _categorize_skills(self, skills: List[Dict[str, Any]]) -> Dict[str, int]:
        """Categorize skills by type."""
        categories = {}
        for skill in skills:
            cat = skill.get("category", "technical")
            categories[cat] = categories.get(cat, 0) + 1
        return categories

    def _infer_experience_level(self, years: int) -> str:
        if years <= 1:
            return "entry"
        elif years <= 3:
            return "junior"
        elif years <= 5:
            return "mid"
        elif years <= 8:
            return "senior"
        elif years <= 12:
            return "lead"
        else:
            return "principal"

    def _estimate_market_demand(self, skills: List[str]) -> Dict[str, float]:
        """Estimate market demand for skills."""
        # In production, would query job market data
        demand_map = {
            "Python": 0.9, "JavaScript": 0.95, "React": 0.9, "AWS": 0.85,
            "Kubernetes": 0.8, "Machine Learning": 0.85, "SQL": 0.9,
            "Docker": 0.85, "TypeScript": 0.85, "Go": 0.75,
        }
        return {s: demand_map.get(s, 0.5) for s in skills}

    def _estimate_salary(self, skills: List[str]) -> Dict[str, int]:
        """Estimate salary based on skills."""
        # Simplified estimation
        base = 80000
        premium_skills = {"Machine Learning": 30000, "AWS": 20000, "Kubernetes": 25000,
                          "React": 15000, "TypeScript": 10000, "Go": 20000}
        total = base + sum(premium_skills.get(s, 5000) for s in skills)
        return {
            "min": total - 20000,
            "max": total + 20000,
            "median": total,
        }