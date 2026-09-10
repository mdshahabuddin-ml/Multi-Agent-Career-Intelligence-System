"""
Career context adapter - read-only bridge from Career Intelligence data
to Hermes agent memory.

Lets Hermes safely read a user's existing career material (profile, resume
summary, projects, skills, certifications, achievements, research, learning
plans) without duplicating agents or touching career data.

Privacy rules enforced here:
- SELECTs only; the adapter never adds, modifies, or deletes career rows.
- Every query is scoped to the requesting ``user_id`` (ownership).
- Only display-safe fields are exposed (safelisted per section below).
  Never exposed: passwords/hashes, emails, resume file paths and raw text
  (may contain addresses/phone numbers), tokens, billing/organization data,
  full research reports.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.models.achievement import Achievement
from backend.models.certification import Certification
from backend.models.learning_plan import LearningPlan
from backend.models.profile import Profile
from backend.models.project import Project
from backend.models.experience import Experience
from backend.models.research import Research
from backend.models.resume import Resume
from backend.models.skill import Skill
from backend.models.user import User

logger = logging.getLogger(__name__)

MEMORY_CATEGORY = "career_context"
MEMORY_NAMESPACE = "career"


def _iso(value: Any) -> Optional[str]:
    """Serialize dates/datetimes, passing everything else through."""
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _enum(value: Any) -> Any:
    """Unwrap enums to plain values."""
    return value.value if isinstance(value, Enum) else value


class CareerContextProvider:
    """
    Read-only provider of career context for Hermes agents.

    Usage:
        provider = CareerContextProvider(db)
        snapshot = provider.snapshot(user_id)          # plain dict
        keys = provider.sync_to_user_memory(mem, user_id)  # Hermes memory only
    """

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------
    def snapshot(self, user_id: int) -> Dict[str, Any]:
        """Aggregate the user's career material into a plain dict.

        Raises ValueError when the user does not exist. Performs only
        SELECT queries scoped to ``user_id``.
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        profile = self.db.query(Profile).filter(Profile.user_id == user_id).first()

        return {
            "user": {"full_name": user.full_name},
            "profile": self._profile_section(profile),
            "skills": self._skills_section(profile),
            "experience": self._experience_section(profile),
            "projects": self._projects_section(profile),
            "resume": self._resume_section(user_id),
            "certifications": self._certifications_section(user_id),
            "achievements": self._achievements_section(user_id),
            "research": self._research_section(user_id),
            "learning": self._learning_section(user_id),
        }

    def _profile_section(self, profile: Optional[Profile]) -> Optional[Dict[str, Any]]:
        if not profile:
            return None
        return {
            "headline": profile.headline,
            "target_role": profile.target_role,
            "location": profile.location,
            "bio": profile.bio,
            "years_of_experience": profile.years_of_experience,
        }

    def _skills_section(self, profile: Optional[Profile]) -> List[Dict[str, Any]]:
        if not profile:
            return []
        skills = (
            self.db.query(Skill)
            .filter(Skill.profile_id == profile.id)
            .order_by(Skill.id)
            .all()
        )
        return [
            {"name": s.name, "category": s.category, "proficiency": _enum(s.proficiency)}
            for s in skills
            if s.name
        ]

    def _experience_section(self, profile: Optional[Profile]) -> List[Dict[str, Any]]:
        if not profile:
            return []
        rows = (
            self.db.query(Experience)
            .filter(Experience.profile_id == profile.id)
            .order_by(Experience.id)
            .all()
        )
        return [
            {
                "company": e.company,
                "role": e.role,
                "description": e.description,
                "start_date": _iso(e.start_date),
                "end_date": _iso(e.end_date),
            }
            for e in rows
        ]

    def _projects_section(self, profile: Optional[Profile]) -> List[Dict[str, Any]]:
        if not profile:
            return []
        rows = (
            self.db.query(Project)
            .filter(Project.profile_id == profile.id)
            .order_by(Project.id)
            .all()
        )
        return [
            {
                "name": p.name,
                "description": p.description,
                "technologies": p.technologies,
                "url": p.url,
            }
            for p in rows
        ]

    def _resume_section(self, user_id: int) -> Optional[Dict[str, Any]]:
        resume = (
            self.db.query(Resume)
            .filter(Resume.user_id == user_id)
            .order_by(Resume.is_primary.desc(), Resume.id.desc())
            .first()
        )
        if not resume:
            return None
        return {
            "filename": resume.original_filename,
            "status": _enum(resume.status),
            "skills": list(resume.extracted_skills or []),
            "ats_score": resume.ats_score,
        }

    def _certifications_section(self, user_id: int) -> List[Dict[str, Any]]:
        rows = (
            self.db.query(Certification)
            .filter(Certification.user_id == user_id)
            .order_by(Certification.id)
            .all()
        )
        return [
            {
                "name": c.name,
                "issuer": c.issuer,
                "issue_date": _iso(c.issue_date),
                "credential_url": c.credential_url,
            }
            for c in rows
        ]

    def _achievements_section(self, user_id: int) -> List[Dict[str, Any]]:
        rows = (
            self.db.query(Achievement)
            .filter(Achievement.user_id == user_id)
            .order_by(Achievement.id)
            .all()
        )
        return [
            {
                "title": a.title,
                "description": a.description,
                "category": a.category,
                "achieved_date": _iso(a.achieved_date),
                "url": a.url,
            }
            for a in rows
        ]

    def _research_section(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        rows = (
            self.db.query(Research)
            .filter(Research.user_id == user_id)
            .order_by(Research.id.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "query": r.query,
                "type": _enum(r.research_type),
                "status": _enum(r.status),
                "summary": r.executive_summary,
                "key_findings": list(r.key_findings or []),
                "recommendations": list(r.recommendations or []),
                "confidence": r.confidence_score,
            }
            for r in rows
        ]

    def _learning_section(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        rows = (
            self.db.query(LearningPlan)
            .filter(LearningPlan.user_id == user_id)
            .order_by(LearningPlan.id.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "title": p.title,
                "target_role": p.target_role,
                "skill_gaps": p.skill_gaps,
                "status": _enum(p.status),
                "progress": p.progress_percentage,
            }
            for p in rows
        ]

    # ------------------------------------------------------------------
    # Hermes memory sync (writes Hermes memory only, never career data)
    # ------------------------------------------------------------------
    def sync_to_user_memory(
        self,
        memory,
        user_id: int,
        namespace: str = MEMORY_NAMESPACE,
    ) -> List[str]:
        """Store a snapshot under namespaced keys in a Hermes UserMemory.

        Only writes to the passed Hermes memory object (``store`` calls);
        career tables are only read. Returns the stored key list.
        """
        snapshot = self.snapshot(user_id)
        user_key = str(user_id)
        stored: List[str] = []
        for section, value in snapshot.items():
            key = f"{namespace}.{section}"
            memory.store(user_key, key, value, category=MEMORY_CATEGORY)
            stored.append(key)
        logger.info("Synced %d career sections to Hermes memory for user %s", len(stored), user_id)
        return stored
