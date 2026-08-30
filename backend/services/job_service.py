import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func

from backend.data_pipeline import (
    IngestionPipeline,
    JobNormalizer,
    DuplicateDetector,
    NormalizedJob,
)
from backend.agents.jobs import (
    RequirementExtractor,
    JobMatchingAgent,
    OpportunityRanker,
)
from backend.config import settings
from backend.models import Job, Company, User, Application, Skill, Resume
from backend.services.resume_service import ResumeService

logger = logging.getLogger(__name__)


class JobService:
    """Service for job search, matching, and recommendations."""

    def __init__(self, db: Session):
        self.db = db
        self.normalizer = JobNormalizer()
        self.deduplicator = DuplicateDetector()
        self.requirement_extractor = RequirementExtractor()
        self.matching_agent = JobMatchingAgent()
        self.ranker = OpportunityRanker()
        
        # Initialize ingestion pipeline
        self.ingestion_pipeline = IngestionPipeline(
            normalizer=self.normalizer,
            deduplicator=self.deduplicator,
            db_session=db,
        )
        
        # Register mock collector if MOCK_DATA is enabled
        if settings.MOCK_DATA:
            from backend.data_pipeline.collectors.mock_collector import MockJobCollector
            mock_collector = MockJobCollector()
            self.ingestion_pipeline.register_collector(mock_collector)

    def _get_or_create_company(self, company_name: str, domain: Optional[str]) -> Company:
        """Get existing company or create new one."""
        company = self.db.query(Company).filter(Company.normalized_name == company_name.lower()).first()
        if company:
            return company

        company = Company(
            name=company_name,
            normalized_name=company_name.lower(),
            domain=domain,
        )
        self.db.add(company)
        self.db.flush()
        return company

    def _save_normalized_job(self, norm_job: NormalizedJob, requirements: Dict) -> Job:
        """Save normalized job to database."""
        # Check if job already exists
        existing = self.db.query(Job).filter(
            Job.source == norm_job.source,
            Job.source_job_id == norm_job.source_job_id,
        ).first()

        if existing:
            # Update existing
            for key, value in norm_job.__dict__.items():
                if hasattr(existing, key) and key not in ["id", "created_at"]:
                    setattr(existing, key, value)
            existing.requirements = requirements.get("required_skills", [])
            existing.updated_at = datetime.utcnow()
            self.db.commit()
            return existing

        # Create company
        company = self._get_or_create_company(norm_job.company_name, norm_job.company_domain)

        # Create new job
        job = Job(
            title=norm_job.title,
            company_id=company.id,
            location=norm_job.location,
            is_remote=norm_job.is_remote,
            remote_type=norm_job.remote_type,
            description=norm_job.description,
            requirements=norm_job.requirements,
            responsibilities=norm_job.responsibilities,
            salary_min=norm_job.salary_min,
            salary_max=norm_job.salary_max,
            salary_currency=norm_job.salary_currency,
            salary_period=norm_job.salary_period,
            experience_level=norm_job.experience_level,
            employment_type=norm_job.employment_type,
            source=norm_job.source,
            source_url=norm_job.source_url,
            source_job_id=norm_job.source_job_id,
            posted_date=norm_job.posted_date,
            expires_date=norm_job.expires_date,
            application_url=norm_job.application_url,
            application_email=norm_job.application_email,
            skills=norm_job.skills,
            keywords=norm_job.keywords,
            quality_score=norm_job.quality_score,
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    async def search_and_save_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        remote: Optional[bool] = None,
        limit: int = 50,
        sources: Optional[List[str]] = None,
    ) -> List[Job]:
        """Search jobs from external sources and save to database using the new ingestion pipeline."""
        logger.info(f"Searching and saving jobs via pipeline: {query}")

        # Determine which source to use
        source_id = "mock_jobs" if settings.MOCK_DATA else (sources[0] if sources else "mock_jobs")
        
        # Run the ingestion pipeline
        collector_kwargs = {
            "query": query,
            "location": location,
            "remote": remote,
        }
        
        result = await self.ingestion_pipeline.run(
            source_id=source_id,
            collector_kwargs=collector_kwargs,
            limit=limit,
        )
        
        logger.info(f"Pipeline completed: {result.total_records_saved} saved, "
                   f"{result.total_duplicates_found} duplicates, "
                   f"{result.total_records_rejected} rejected")
        
        if not result.overall_success:
            logger.warning(f"Pipeline had errors: {result.error_summary}")
        
        # Return the saved jobs
        saved_jobs = self.db.query(Job).filter(
            Job.source == source_id,
            Job.title.ilike(f"%{query}%")
        ).limit(limit).all()
        
        return saved_jobs

    def get_job(self, job_id: int) -> Optional[Job]:
        """Get job by ID."""
        return self.db.query(Job).filter(Job.id == job_id).first()

    def get_jobs(
        self,
        query: Optional[str] = None,
        location: Optional[str] = None,
        remote: Optional[bool] = None,
        experience_level: Optional[str] = None,
        employment_type: Optional[str] = None,
        salary_min: Optional[int] = None,
        skills: Optional[List[str]] = None,
        company_id: Optional[int] = None,
        source: Optional[str] = None,
        is_active: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Job]:
        """Get jobs with filters."""
        q = self.db.query(Job).filter(Job.is_active == is_active)

        if query:
            q = q.filter(or_(
                Job.title.ilike(f"%{query}%"),
                Job.description.ilike(f"%{query}%"),
                Job.requirements.ilike(f"%{query}%"),
            ))

        if location:
            q = q.filter(Job.location.ilike(f"%{location}%"))

        if remote is not None:
            q = q.filter(Job.is_remote == remote)

        if experience_level:
            q = q.filter(Job.experience_level == experience_level)

        if employment_type:
            q = q.filter(Job.employment_type == employment_type)

        if salary_min:
            q = q.filter(or_(Job.salary_yearly_min >= salary_min, Job.salary_yearly_max >= salary_min))

        if skills:
            # Filter by skills (PostgreSQL JSONB contains)
            for skill in skills:
                q = q.filter(Job.skills.op("@>")([skill]))

        if company_id:
            q = q.filter(Job.company_id == company_id)

        if source:
            q = q.filter(Job.source == source)

        q = q.order_by(Job.posted_date.desc().nullslast(), Job.quality_score.desc())
        return q.offset(offset).limit(limit).all()

    def get_job_count(
        self,
        query: Optional[str] = None,
        location: Optional[str] = None,
        remote: Optional[bool] = None,
        is_active: bool = True,
    ) -> int:
        """Get total count of jobs matching filters."""
        q = self.db.query(func.count(Job.id)).filter(Job.is_active == is_active)

        if query:
            q = q.filter(or_(
                Job.title.ilike(f"%{query}%"),
                Job.description.ilike(f"%{query}%"),
            ))

        if location:
            q = q.filter(Job.location.ilike(f"%{location}%"))

        if remote is not None:
            q = q.filter(Job.is_remote == remote)

        return q.scalar() or 0

    async def get_personalized_recommendations(
        self,
        user_id: int,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get personalized job recommendations for a user."""
        logger.info(f"Generating recommendations for user {user_id}")

        # Get user profile and resume
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        profile = user.profile
        primary_resume = self.db.query(Resume).filter(
            Resume.user_id == user_id,
            Resume.is_primary == True,
        ).first()

        # Get candidate data
        candidate_skills = []
        candidate_experience = 0
        candidate_location = profile.location if profile else "Unknown"
        candidate_remote = True  # Default preference
        candidate_salary_min = None

        if primary_resume and primary_resume.parsed_data:
            parsed = primary_resume.parsed_data
            candidate_skills = [
                {"name": s, "category": "technical", "confidence": 0.8}
                for s in (primary_resume.extracted_skills or [])
            ]
            candidate_experience = parsed.get("experience", {}).get("years_of_experience", 0)

        if profile:
            candidate_experience = max(candidate_experience, profile.years_of_experience)

        # Get active jobs
        jobs = self.get_jobs(is_active=True, limit=200)

        if not jobs:
            return []

        # Normalize for matching
        norm_jobs = []
        for job in jobs:
            norm_job = NormalizedJob(
                title=job.title,
                company_name=job.company.name if job.company else "Unknown",
                company_domain=job.company.domain if job.company else None,
                location=job.location or "Unknown",
                normalized_location=job.location or "Unknown",
                is_remote=job.is_remote,
                remote_type=job.remote_type,
                description=job.description or "",
                requirements=job.requirements,
                responsibilities=job.responsibilities,
                salary_min=job.salary_min,
                salary_max=job.salary_max,
                salary_currency=job.salary_currency,
                salary_period=job.salary_period,
                salary_yearly_min=job.salary_yearly_min,
                salary_yearly_max=job.salary_yearly_max,
                experience_level=job.experience_level,
                employment_type=job.employment_type,
                source=job.source,
                source_url=job.source_url,
                source_job_id=job.source_job_id,
                posted_date=job.posted_date,
                expires_date=job.expires_date,
                application_url=job.application_url,
                application_email=job.application_email,
                skills=job.skills or [],
                keywords=job.keywords or [],
                quality_score=job.quality_score,
                raw_record=None,
            )
            norm_jobs.append(norm_job)

        # Match jobs to candidate
        matches = self.matching_agent.match_batch(
            norm_jobs=norm_jobs,
            candidate_skills=candidate_skills,
            candidate_experience_years=candidate_experience,
            candidate_location=candidate_location,
            candidate_remote_preference=candidate_remote,
            candidate_salary_min=candidate_salary_min,
        )

        # Rank opportunities
        ranked = self.ranker.rank_opportunities(matches)

        # Convert to response format
        recommendations = []
        for ranked_opp in self.ranker.get_top_opportunities(ranked, limit):
            match = ranked_opp.job_match
            job = self.get_job(match.job_id) if match.job_id else None

            recommendations.append({
                "job_id": job.id if job else match.job_id,
                "title": match.job_title,
                "company": match.company,
                "location": job.location if job else "Unknown",
                "is_remote": job.is_remote if job else False,
                "remote_type": job.remote_type if job else None,
                "salary_min": job.salary_yearly_min if job else None,
                "salary_max": job.salary_yearly_max if job else None,
                "experience_level": job.experience_level if job else None,
                "employment_type": job.employment_type if job else None,
                "match_score": ranked_opp.composite_score,
                "tier": ranked_opp.tier,
                "highlights": ranked_opp.highlights,
                "concerns": ranked_opp.concerns,
                "action_items": ranked_opp.action_items,
                "matching_skills": match.matching_skills,
                "missing_skills": match.missing_skills,
                "posted_date": job.posted_date if job else None,
                "application_url": job.application_url if job else None,
            })

        return recommendations

    def save_job_for_user(self, user_id: int, job_id: int, notes: Optional[str] = None) -> Application:
        """Save/apply to a job."""
        user = self.db.query(User).filter(User.id == user_id).first()
        job = self.db.query(Job).filter(Job.id == job_id).first()

        if not user or not job:
            raise ValueError("User or job not found")

        # Check if already applied
        existing = self.db.query(Application).filter(
            Application.user_id == user_id,
            Application.job_id == job_id,
        ).first()

        if existing:
            existing.notes = notes
            self.db.commit()
            return existing

        # Get primary resume
        primary_resume = self.db.query(Resume).filter(
            Resume.user_id == user_id,
            Resume.is_primary == True,
        ).first()

        application = Application(
            user_id=user_id,
            job_id=job_id,
            resume_id=primary_resume.id if primary_resume else None,
            status="saved",
            notes=notes,
        )
        self.db.add(application)
        self.db.commit()
        self.db.refresh(application)
        return application

    def get_saved_jobs(self, user_id: int) -> List[Dict[str, Any]]:
        """Get user's saved/applied jobs."""
        applications = self.db.query(Application).filter(
            Application.user_id == user_id,
        ).order_by(Application.created_at.desc()).all()

        result = []
        for app in applications:
            job = app.job
            result.append({
                "application_id": app.id,
                "job_id": job.id,
                "title": job.title,
                "company": job.company.name if job.company else "Unknown",
                "location": job.location,
                "is_remote": job.is_remote,
                "status": app.status,
                "saved_date": app.created_at,
                "applied_date": app.applied_date,
                "match_score": None,  # Would need to compute
            })
        return result

    def get_job_stats(self) -> Dict[str, Any]:
        """Get job statistics."""
        total = self.db.query(func.count(Job.id)).filter(Job.is_active == True).scalar() or 0
        remote = self.db.query(func.count(Job.id)).filter(Job.is_active == True, Job.is_remote == True).scalar() or 0

        # By source
        sources = self.db.query(Job.source, func.count(Job.id)).filter(Job.is_active == True).group_by(Job.source).all()
        by_source = {s: c for s, c in sources}

        # By experience level
        exp_levels = self.db.query(Job.experience_level, func.count(Job.id)).filter(Job.is_active == True).group_by(Job.experience_level).all()
        by_experience = {e: c for e, c in exp_levels if e}

        # Top skills
        all_skills = self.db.query(Job.skills).filter(Job.is_active == True).all()
        skill_counts = {}
        for (skills,) in all_skills:
            if skills:
                for skill in skills:
                    skill_counts[skill] = skill_counts.get(skill, 0) + 1
        top_skills = dict(sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:20])

        return {
            "total_jobs": total,
            "remote_jobs": remote,
            "remote_percentage": round(remote / total * 100, 1) if total > 0 else 0,
            "by_source": by_source,
            "by_experience_level": by_experience,
            "top_skills": top_skills,
        }