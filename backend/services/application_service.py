import logging
from typing import List, Dict, Any, Optional
from datetime import date, datetime

from sqlalchemy.orm import Session
from fastapi import HTTPException

from backend.agents.application import (
    ApplicationAgent,
    ApplicationWorkflowResult,
    ATSAnalysisResult,
    ResumeReviewResult,
    CoverLetterResult,
    ApplicationAnswersResult,
    CoverLetterContext,
    CoverLetterTone,
    CoverLetterLength,
)
from backend.models import User, Application as ApplicationModel, Job
from backend.models.application import ApplicationStatus
from backend.database import get_db

logger = logging.getLogger(__name__)


class ApplicationService:
    """Service for application management and workflow orchestration."""

    def __init__(self, db: Session):
        self.db = db
        self.application_agent = ApplicationAgent()

    async def prepare_application(
        self,
        user_id: int,
        job_id: int,
        resume_text: str,
        candidate_profile: Dict[str, Any],
        job_description: Optional[str] = None,
        cover_letter_tone: str = "professional",
        cover_letter_length: str = "medium",
    ) -> ApplicationWorkflowResult:
        """Prepare complete application package for a job."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError("Job not found")

        result = await self.application_agent.prepare_application(
            user_id=user_id,
            job_id=job_id,
            company=job.company.name if job.company else "Unknown",
            role=job.title,
            resume_text=resume_text,
            candidate_profile=candidate_profile,
            job_description=job_description,
            target_role=job.title,
            target_company=job.company.name if job.company else None,
            cover_letter_tone=cover_letter_tone,
            cover_letter_length=cover_letter_length,
        )

        return result

    def analyze_resume_ats(
        self,
        resume_text: str,
        target_role: Optional[str] = None,
        job_description: Optional[str] = None,
    ) -> ATSAnalysisResult:
        """Analyze resume for ATS compatibility."""
        from backend.agents.application import ATSResumeAgent
        ats_agent = ATSResumeAgent()
        return ats_agent.analyze(
            resume_text=resume_text,
            target_role=target_role,
            job_description=job_description,
        )

    def review_resume(
        self,
        resume_text: str,
        target_role: Optional[str] = None,
    ) -> ResumeReviewResult:
        """Review resume content quality."""
        from backend.agents.application import ResumeReviewerAgent
        reviewer = ResumeReviewerAgent()
        return reviewer.review(
            resume_text=resume_text,
            target_role=target_role,
        )

    def generate_cover_letter(
        self,
        user_id: int,
        target_role: str,
        target_company: str,
        job_description: Optional[str] = None,
        hiring_manager: Optional[str] = None,
        tone: str = "professional",
        length: str = "medium",
    ) -> CoverLetterResult:
        """Generate a cover letter for a specific application."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        candidate_profile = self._get_candidate_profile(user_id)

        cl_context = CoverLetterContext(
            candidate_name=candidate_profile.get("name", user.full_name or "Candidate"),
            candidate_email=candidate_profile.get("email", user.email),
            candidate_phone=candidate_profile.get("phone", ""),
            candidate_location=candidate_profile.get("location", ""),
            target_role=target_role,
            target_company=target_company,
            hiring_manager=hiring_manager,
            job_description=job_description,
            key_skills=candidate_profile.get("key_skills", []),
            key_achievements=candidate_profile.get("achievements", []),
            years_experience=candidate_profile.get("years_experience", 0),
            current_role=candidate_profile.get("current_role", ""),
            tone=CoverLetterTone(tone),
            length=CoverLetterLength(length),
            linkedin_url=candidate_profile.get("linkedin_url"),
            portfolio_url=candidate_profile.get("portfolio_url"),
        )

        from backend.agents.application import CoverLetterAgent
        cover_letter_agent = CoverLetterAgent()
        return cover_letter_agent.generate(cl_context)

    def generate_application_answers(
        self,
        user_id: int,
        questions: List[str],
        target_role: Optional[str] = None,
        target_company: Optional[str] = None,
    ) -> ApplicationAnswersResult:
        """Generate answers for application questions."""
        candidate_profile = self._get_candidate_profile(user_id)

        from backend.agents.application import ApplicationAnswerAgent, ApplicationQuestion
        answer_agent = ApplicationAnswerAgent()
        # Backward-compatible: API contract passes List[str]; agent expects List[ApplicationQuestion]
        normalized: List[Any] = []
        for q in questions:
            if isinstance(q, str):
                normalized.append(
                    ApplicationQuestion(
                        question=q,
                        question_type=answer_agent._classify_question(q),
                    )
                )
            else:
                normalized.append(q)
        return answer_agent.generate_answers(
            questions=normalized,
            candidate_profile=candidate_profile,
            target_role=target_role,
            target_company=target_company,
        )

    def optimize_cover_letter(
        self,
        cover_letter: str,
        target_role: str,
        target_company: str,
    ) -> Dict[str, Any]:
        """Provide optimization suggestions for a cover letter (delegates to ApplicationAgent)."""
        return self.application_agent.optimize_cover_letter(
            cover_letter=cover_letter,
            target_role=target_role,
            target_company=target_company,
        )

    def optimize_resume(
        self,
        resume_text: str,
        target_role: Optional[str] = None,
        job_description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Provide comprehensive resume optimization suggestions."""
        from backend.agents.application import ApplicationAgent
        agent = ApplicationAgent()
        return agent.optimize_resume(
            resume_text=resume_text,
            target_role=target_role,
            job_description=job_description,
        )

    def prepare_for_interview(
        self,
        user_id: int,
        target_role: str,
        target_company: str,
        job_description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Prepare interview preparation materials."""
        candidate_profile = self._get_candidate_profile(user_id)

        from backend.agents.application import ApplicationAgent
        agent = ApplicationAgent()
        return agent.prepare_for_interview(
            candidate_profile=candidate_profile,
            target_role=target_role,
            target_company=target_company,
            job_description=job_description,
        )

    def apply_to_job(
        self,
        user_id: int,
        job_id: int,
        resume_text: str,
        cover_letter: Optional[str] = None,
        answers: Optional[Dict[str, str]] = None,
    ) -> ApplicationModel:
        """Submit application to a job."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        job = self.db.query(Job).filter(Job.id == job_id).first() if job_id else None

        if job_id and not job:
            raise HTTPException(status_code=404, detail=f"Job with id {job_id} not found")

        # Check if already applied
        if job:
            existing = self.db.query(ApplicationModel).filter(
                ApplicationModel.user_id == user_id,
                ApplicationModel.job_id == job_id,
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail="Already applied to this job")

        application = ApplicationModel(
            user_id=user_id,
            job_id=job_id,
            cover_letter=cover_letter,
            status=ApplicationStatus.DRAFT,
            applied_date=date.today(),
            application_answers=answers or {},
        )

        self.db.add(application)
        self.db.commit()
        self.db.refresh(application)

        return application

    def get_user_applications(self, user_id: int) -> List[ApplicationModel]:
        """Get all applications for a user."""
        return self.db.query(ApplicationModel).filter(
            ApplicationModel.user_id == user_id
        ).order_by(ApplicationModel.created_at.desc()).all()

    def get_application(self, application_id: int, user_id: int) -> Optional[ApplicationModel]:
        """Get specific application."""
        return self.db.query(ApplicationModel).filter(
            ApplicationModel.id == application_id,
            ApplicationModel.user_id == user_id,
        ).first()

    def update_application_status(
        self,
        application_id: int,
        user_id: int,
        status: str,
        notes: Optional[str] = None,
    ) -> Optional[ApplicationModel]:
        """Update application status."""
        app = self.get_application(application_id, user_id)
        if not app:
            return None

        try:
            status_enum = ApplicationStatus(status)
        except ValueError:
            raise ValueError(f"Invalid status: {status}")
        app.status = status_enum
        if notes:
            app.notes = notes
        if status == "interview_scheduled":
            app.interview_date = date.today()

        self.db.commit()
        self.db.refresh(app)
        return app

    def withdraw_application(self, application_id: int, user_id: int) -> bool:
        """Withdraw an application."""
        app = self.get_application(application_id, user_id)
        if not app:
            return False

        app.status = ApplicationStatus.WITHDRAWN
        self.db.commit()
        return True

    def get_application_stats(self, user_id: int) -> Dict[str, Any]:
        """Get application statistics for user."""
        apps = self.get_user_applications(user_id)

        stats = {
            "total": len(apps),
            "by_status": {},
            "response_rate": 0,
            "interview_rate": 0,
            "offer_rate": 0,
        }

        for app in apps:
            status = app.status.value if hasattr(app.status, "value") else str(app.status)
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

        if stats["total"] > 0:
            responded = stats["by_status"].get("under_review", 0) + \
                       stats["by_status"].get("interview_scheduled", 0) + \
                       stats["by_status"].get("interview_completed", 0) + \
                       stats["by_status"].get("offer_received", 0) + \
                       stats["by_status"].get("rejected", 0)
            stats["response_rate"] = round(responded / stats["total"] * 100, 1)

            interviews = stats["by_status"].get("interview_scheduled", 0) + \
                        stats["by_status"].get("interview_completed", 0)
            stats["interview_rate"] = round(interviews / stats["total"] * 100, 1)

            offers = stats["by_status"].get("offer_received", 0) + \
                    stats["by_status"].get("offer_accepted", 0)
            stats["offer_rate"] = round(offers / stats["total"] * 100, 1)

        return stats

    def _get_candidate_profile(self, user_id: int) -> Dict[str, Any]:
        """Build candidate profile from user data."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {}

        # Get skills
        from backend.models import Skill, Profile
        skills = self.db.query(Skill).filter(Skill.profile_id == user_id).all()
        profile = self.db.query(Profile).filter(Profile.user_id == user_id).first()

        return {
            "name": user.full_name,
            "email": user.email,
            "phone": getattr(user, 'phone', ''),
            "location": profile.location if profile else "",
            "linkedin_url": getattr(user, 'linkedin_url', None),
            "portfolio_url": getattr(user, 'portfolio_url', None),
            "current_role": profile.target_role if profile else "",
            "target_role": profile.target_role if profile else "",
            "years_experience": profile.years_of_experience if profile else 0,
            "key_skills": [s.name for s in skills],
            "achievements": [],  # Would come from resume/projects
            "notice_period": "2 weeks",
            "summary": profile.bio if profile else "",
        }

    def get_application_insights(self, user_id: int) -> Dict[str, Any]:
        """Get application insights and analytics for user."""
        stats = self.get_application_stats(user_id)
        apps = self.get_user_applications(user_id)

        timeline = []
        for app in apps:
            timeline.append({
                "id": app.id,
                "status": app.status.value if hasattr(app.status, "value") else str(app.status),
                "applied_date": app.applied_date.isoformat() if app.applied_date else None,
                "interview_date": app.interview_date.isoformat() if app.interview_date else None,
            })

        return {
            **stats,
            "timeline": timeline,
            "tips": self._generate_tips(stats),
        }

    def _generate_tips(self, stats: Dict[str, Any]) -> list:
        """Generate actionable tips based on application stats."""
        tips = []
        total = stats.get("total", 0)
        if total == 0:
            tips.append("Start applying to jobs to see insights here.")
        else:
            if stats.get("response_rate", 0) < 30:
                tips.append("Low response rate. Consider tailoring your resume for each application.")
            if stats.get("interview_rate", 0) < 20:
                tips.append("Low interview rate. Strengthen your cover letter and qualifications.")
            if stats.get("offer_rate", 0) < 10 and total > 5:
                tips.append("Consider negotiating offers and expanding your job search.")
        return tips