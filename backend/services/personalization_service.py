import logging
import json
import math
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc

from backend.models.preference import (
    UserPreference, UserBehaviorLog, UserInteraction, PersonalizationProfile
)
from backend.models.user import User
from backend.models.job import Job
from backend.models.company import Company
from backend.models.skill import Skill
from backend.schemas.preference import (
    UserPreferenceCreate, UserPreferenceUpdate,
    UserPreferenceResponse, UserBehaviorLogCreate,
    UserInteractionCreate, PersonalizationProfileResponse
)

logger = logging.getLogger(__name__)


class PersonalizationService:
    """Service for managing user preferences and personalization."""

    def __init__(self, db: Session):
        self.db = db

    # ============= User Preferences =============

    def get_preferences(self, user_id: int) -> Optional[UserPreference]:
        """Get user preferences."""
        return self.db.query(UserPreference).filter(
            UserPreference.user_id == user_id
        ).first()

    def create_preferences(self, user_id: int, preferences: UserPreferenceCreate) -> UserPreference:
        """Create user preferences."""
        existing = self.get_preferences(user_id)
        if existing:
            raise ValueError("Preferences already exist for this user")

        pref = UserPreference(user_id=user_id)
        self._update_preference_fields(pref, preferences)
        self.db.add(pref)
        self.db.commit()
        self.db.refresh(pref)
        return pref

    def update_preferences(self, user_id: int, preferences: UserPreferenceUpdate) -> Optional[UserPreference]:
        """Update user preferences."""
        pref = self.get_preferences(user_id)
        if not pref:
            return None

        self._update_preference_fields(pref, preferences)
        pref.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(pref)
        return pref

    def _update_preference_fields(self, pref: UserPreference, data: Any) -> None:
        """Update preference fields from schema."""
        if data.job_preferences:
            for k, v in data.job_preferences.dict().items():
                setattr(pref, k, v)
        if data.notification_preferences:
            for k, v in data.notification_preferences.dict().items():
                setattr(pref, k, v)
        if data.content_ui_preferences:
            for k, v in data.content_ui_preferences.dict().items():
                setattr(pref, k, v)
        if data.privacy_preferences:
            for k, v in data.privacy_preferences.dict().items():
                setattr(pref, k, v)
        if data.learning_preferences:
            for k, v in data.learning_preferences.dict().items():
                setattr(pref, k, v)
        if data.recommendation_weights:
            for k, v in data.recommendation_weights.dict().items():
                setattr(pref, k, v)

    def delete_preferences(self, user_id: int) -> bool:
        """Delete user preferences."""
        pref = self.get_preferences(user_id)
        if not pref:
            return False
        self.db.delete(pref)
        self.db.commit()
        return True

    def export_preferences(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Export user preferences as JSON."""
        pref = self.get_preferences(user_id)
        if not pref:
            return None

        return {
            "preferences": UserPreferenceResponse.from_entity(pref).dict(),
            "exported_at": datetime.utcnow().isoformat(),
            "version": "1.0"
        }

    def import_preferences(self, user_id: int, data: Dict[str, Any]) -> UserPreference:
        """Import user preferences from JSON."""
        existing = self.get_preferences(user_id)
        if existing:
            self.db.delete(existing)

        pref_data = data.get("preferences", data)
        pref = UserPreference(user_id=user_id)
        self._update_preference_fields(pref, UserPreferenceCreate(**pref_data))
        self.db.add(pref)
        self.db.commit()
        self.db.refresh(pref)
        return pref

    # ============= Behavior Logging =============

    def log_behavior(self, user_id: int, log: UserBehaviorLogCreate) -> UserBehaviorLog:
        """Log user behavior event."""
        behavior = UserBehaviorLog(
            user_id=user_id,
            **log.dict()
        )
        self.db.add(behavior)
        self.db.commit()
        self.db.refresh(behavior)
        return behavior

    def log_behavior_batch(self, user_id: int, logs: List[UserBehaviorLogCreate]) -> List[UserBehaviorLog]:
        """Log multiple behavior events in batch."""
        behaviors = [
            UserBehaviorLog(user_id=user_id, **log.dict())
            for log in logs
        ]
        self.db.bulk_save_objects(behaviors)
        self.db.commit()
        return behaviors

    def get_behavior_logs(
        self,
        user_id: int,
        event_type: Optional[str] = None,
        event_category: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[UserBehaviorLog]:
        """Get user behavior logs with filters."""
        query = self.db.query(UserBehaviorLog).filter(UserBehaviorLog.user_id == user_id)

        if event_type:
            query = query.filter(UserBehaviorLog.event_type == event_type)
        if event_category:
            query = query.filter(UserBehaviorLog.event_category == event_category)
        if start_date:
            query = query.filter(UserBehaviorLog.created_at >= start_date)
        if end_date:
            query = query.filter(UserBehaviorLog.created_at <= end_date)

        return query.order_by(desc(UserBehaviorLog.created_at)).limit(limit).all()

    # ============= User Interactions =============

    def record_interaction(self, user_id: int, interaction: UserInteractionCreate) -> UserInteraction:
        """Record user interaction with an entity."""
        inter = UserInteraction(user_id=user_id, **interaction.dict())
        self.db.add(inter)
        self.db.commit()
        self.db.refresh(inter)
        return inter

    def get_interactions(
        self,
        user_id: int,
        interaction_type: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        limit: int = 50
    ) -> List[UserInteraction]:
        """Get user interactions with filters."""
        query = self.db.query(UserInteraction).filter(UserInteraction.user_id == user_id)

        if interaction_type:
            query = query.filter(UserInteraction.interaction_type == interaction_type)
        if entity_type:
            query = query.filter(UserInteraction.entity_type == entity_type)
        if entity_id:
            query = query.filter(UserInteraction.entity_id == entity_id)

        return query.order_by(desc(UserInteraction.created_at)).limit(limit).all()

    def get_interaction_stats(self, user_id: int) -> Dict[str, Any]:
        """Get interaction statistics for a user."""
        stats = self.db.query(
            UserInteraction.interaction_type,
            UserInteraction.entity_type,
            func.count(UserInteraction.id)
        ).filter(UserInteraction.user_id == user_id).group_by(
            UserInteraction.interaction_type,
            UserInteraction.entity_type
        ).all()

        result = defaultdict(lambda: defaultdict(int))
        for interaction_type, entity_type, count in stats:
            result[interaction_type][entity_type] = count

        total = sum(sum(v.values()) for v in result.values())
        return {
            "total_interactions": total,
            "by_type_and_entity": dict(result),
            "most_interacted_entity": max(result.items(), key=lambda x: sum(x[1].values()))[0] if result else None
        }

    # ============= Personalization Profile =============

    def get_personalization_profile(self, user_id: int) -> Optional[PersonalizationProfile]:
        """Get user's personalization profile."""
        return self.db.query(PersonalizationProfile).filter(
            PersonalizationProfile.user_id == user_id
        ).first()

    def update_personalization_profile(
        self,
        user_id: int,
        updates: Dict[str, Any]
    ) -> Optional[PersonalizationProfile]:
        """Update personalization profile."""
        profile = self.get_personalization_profile(user_id)
        if not profile:
            profile = PersonalizationProfile(user_id=user_id)
            self.db.add(profile)

        for key, value in updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)

        profile.last_updated = datetime.utcnow()
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def rebuild_personalization_profile(self, user_id: int) -> PersonalizationProfile:
        """Rebuild personalization profile from user behavior."""
        profile = self.get_personalization_profile(user_id)
        if not profile:
            profile = PersonalizationProfile(user_id=user_id)
            self.db.add(profile)

        # Analyze behavior logs
        behaviors = self.get_behavior_logs(user_id, limit=5000)
        interactions = self.get_interactions(user_id, limit=5000)

        # Infer skills from interactions
        skill_counter = Counter()
        interest_counter = Counter()
        industry_counter = Counter()
        job_function_counter = Counter()

        for inter in interactions:
            if inter.entity_type == "job" and inter.interaction_type in ["view", "save", "apply"]:
                job = self.db.query(Job).filter(Job.id == inter.entity_id).first()
                if job:
                    if job.skills:
                        skill_counter.update(job.skills)
                    if job.title:
                        # Extract job function from title
                        pass

        for behavior in behaviors:
            if behavior.event_type == "search" and behavior.metadata:
                query = behavior.metadata.get("query", "")
                if query:
                    interest_counter[query] += 1

        # Update profile
        profile.inferred_skills = [s for s, _ in skill_counter.most_common(20)]
        profile.inferred_interests = [i for i, _ in interest_counter.most_common(20)]
        profile.inferred_industries = [i for i, _ in industry_counter.most_common(10)]

        # Calculate engagement scores
        profile.job_search_engagement = self._calculate_engagement(behaviors, "job")
        profile.learning_engagement = self._calculate_engagement(behaviors, "learning")
        profile.research_engagement = self._calculate_engagement(behaviors, "research")

        profile.last_updated = datetime.utcnow()
        profile.confidence_score = min(1.0, len(behaviors) / 1000.0)
        profile.model_version = "1.0"

        self.db.commit()
        self.db.refresh(profile)
        return profile

    def _calculate_engagement(self, behaviors: List[UserBehaviorLog], category: str) -> float:
        """Calculate engagement score for a category."""
        category_behaviors = [b for b in behaviors if b.event_category == category]
        if not category_behaviors:
            return 0.0

        # Weight by recency and frequency
        now = datetime.utcnow()
        total_weight = 0.0
        for b in category_behaviors:
            days_ago = (now - b.created_at).days
            recency_weight = math.exp(-days_ago / 30.0)  # Exponential decay
            total_weight += recency_weight

        # Normalize (assuming max ~100 weighted events per month)
        return min(1.0, total_weight / 100.0)

    # ============= Recommendations =============

    def get_personalized_job_recommendations(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get personalized job recommendations."""
        preferences = self.get_preferences(user_id)
        profile = self.get_personalization_profile(user_id)

        # Build query based on preferences
        query = self.db.query(Job).filter(Job.is_active == True)

        if preferences:
            # Location filter
            if preferences.preferred_locations:
                location_filters = [
                    Job.location.ilike(f"%{loc}%") for loc in preferences.preferred_locations
                ]
                query = query.filter(or_(*location_filters))

            # Remote type filter
            if preferences.preferred_remote_types:
                if "remote" in preferences.preferred_remote_types:
                    query = query.filter(Job.is_remote == True)
                if "hybrid" in preferences.preferred_remote_types:
                    query = query.filter(Job.remote_type == "hybrid")
                if "onsite" in preferences.preferred_remote_types:
                    query = query.filter(Job.remote_type == "on_site")

            # Salary filter
            if preferences.min_salary:
                query = query.filter(
                    or_(Job.salary_yearly_min >= preferences.min_salary,
                        Job.salary_yearly_max >= preferences.min_salary)
                )

            # Excluded companies
            if preferences.excluded_companies:
                company_ids = self.db.query(Company.id).filter(
                    Company.name.in_(preferences.excluded_companies)
                ).subquery()
                query = query.filter(~Job.company_id.in_(company_ids))

            # Excluded keywords
            if preferences.excluded_keywords:
                for keyword in preferences.excluded_keywords:
                    query = query.filter(
                        ~Job.title.ilike(f"%{keyword}%"),
                        ~Job.description.ilike(f"%{keyword}%")
                    )

        # Apply personalization profile
        if profile and profile.inferred_skills:
            for skill in profile.inferred_skills[:10]:
                query = query.filter(Job.skills.op("@>")([skill]))

        # Order by relevance (using quality_score and recency)
        query = query.order_by(desc(Job.quality_score), desc(Job.posted_date))

        jobs = query.offset(offset).limit(limit).all()

        return [self._job_to_recommendation(job, profile, preferences) for job in jobs]

    def _job_to_recommendation(
        self,
        job: Job,
        profile: Optional[PersonalizationProfile],
        preferences: Optional[UserPreference]
    ) -> Dict[str, Any]:
        """Convert job to recommendation with personalization score."""
        score = 0.5  # Base score
        reasons = []

        if profile and profile.inferred_skills and job.skills:
            matching_skills = set(profile.inferred_skills) & set(job.skills or [])
            if matching_skills:
                skill_score = len(matching_skills) / max(len(job.skills or []), 1)
                score += 0.3 * skill_score
                reasons.append(f"Matches {len(matching_skills)} of your skills")

        if preferences:
            if preferences.preferred_locations and job.location:
                if any(loc.lower() in job.location.lower() for loc in preferences.preferred_locations):
                    score += 0.2
                    reasons.append("Matches preferred location")

            if preferences.preferred_remote_types and job.is_remote:
                if "remote" in preferences.preferred_remote_types:
                    score += 0.15
                    reasons.append("Remote position")

            if preferences.min_salary and job.salary_yearly_min:
                if job.salary_yearly_min >= preferences.min_salary:
                    score += 0.15
                    reasons.append("Meets salary expectations")

        # Add company culture match if available
        if job.company and profile:
            score += 0.1  # Placeholder for culture match

        return {
            "job_id": job.id,
            "title": job.title,
            "company": job.company.name if job.company else None,
            "location": job.location,
            "is_remote": job.is_remote,
            "remote_type": job.remote_type,
            "salary_min": job.salary_yearly_min,
            "salary_max": job.salary_yearly_max,
            "personalization_score": min(1.0, score),
            "match_reasons": reasons,
            "skills_match": list(matching_skills) if profile and profile.inferred_skills else [],
        }

    def get_personalized_learning_recommendations(
        self,
        user_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get personalized learning recommendations."""
        preferences = self.get_preferences(user_id)
        profile = self.get_personalization_profile(user_id)

        # This would integrate with a course catalog
        # For now, return skill-based recommendations
        recommendations = []

        if profile and profile.inferred_skills:
            for skill in profile.inferred_skills[:5]:
                recommendations.append({
                    "skill": skill,
                    "type": "skill_gap",
                    "priority": "high",
                    "reason": f"High demand skill in your field"
                })

        if preferences:
            learning = UserPreferenceResponse.from_entity(preferences).learning_preferences
            if learning.preferred_learning_platforms:
                for platform in learning.preferred_learning_platforms:
                    recommendations.append({
                        "platform": platform,
                        "type": "platform_preference",
                        "priority": "medium",
                        "reason": f"Your preferred learning platform"
                    })

        return recommendations[:limit]

    # ============= Adaptive UI =============

    def get_adaptive_ui_config(self, user_id: int) -> Dict[str, Any]:
        """Get adaptive UI configuration based on preferences and behavior."""
        preferences = self.get_preferences(user_id)
        profile = self.get_personalization_profile(user_id)

        config = {
            "theme": "system",
            "density": "comfortable",
            "compact_mode": False,
            "show_salary_estimates": True,
            "language": "en",
            "dashboard_layout": self._get_dashboard_layout(profile),
            "default_filters": self._get_default_filters(preferences),
            "recommendation_widgets": self._get_recommendation_widgets(profile),
        }
        if preferences:
            ui = UserPreferenceResponse.from_entity(preferences).content_ui_preferences
            config.update(
                theme=ui.theme_mode.value,
                density=ui.content_density.value,
                compact_mode=ui.compact_mode,
                show_salary_estimates=ui.show_salary_estimates,
                language=ui.language,
            )

        return config

    def _get_dashboard_layout(self, profile: Optional[PersonalizationProfile]) -> List[str]:
        """Determine dashboard widget layout based on engagement."""
        if not profile:
            return ["jobs", "learning", "research", "applications"]

        layout = []
        if profile.job_search_engagement > 0.5:
            layout.append("jobs")
        if profile.learning_engagement > 0.3:
            layout.append("learning")
        if profile.research_engagement > 0.3:
            layout.append("research")
        if profile.community_engagement > 0.2:
            layout.append("network")

        return layout or ["jobs", "learning", "research", "applications"]

    def _get_default_filters(self, preferences: Optional[UserPreference]) -> Dict[str, Any]:
        """Get default search filters from preferences."""
        if not preferences:
            return {}

        job = UserPreferenceResponse.from_entity(preferences).job_preferences
        return {
            "locations": job.preferred_locations,
            "remote_types": job.preferred_remote_types,
            "min_salary": job.min_salary,
            "job_types": job.preferred_job_types,
            "industries": job.preferred_industries,
        }

    def _get_recommendation_widgets(self, profile: Optional[PersonalizationProfile]) -> List[Dict[str, Any]]:
        """Get recommendation widget configuration."""
        widgets = []

        if profile:
            if profile.inferred_skills:
                widgets.append({
                    "type": "skill_based_jobs",
                    "title": "Jobs Matching Your Skills",
                    "skills": profile.inferred_skills[:5]
                })

            if profile.inferred_interests:
                widgets.append({
                    "type": "interest_based_content",
                    "title": "Based on Your Interests",
                    "interests": profile.inferred_interests[:5]
                })

        widgets.append({
            "type": "trending_in_field",
            "title": "Trending in Your Field"
        })

        return widgets