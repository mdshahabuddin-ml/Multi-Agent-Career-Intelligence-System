import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from backend.agents.jobs.requirement_extractor import RequirementExtractor, ExtractedRequirements
from backend.agents.jobs.job_normalizer import NormalizedJob
from backend.models import Skill

logger = logging.getLogger(__name__)


@dataclass
class JobMatch:
    """Result of job-candidate matching."""
    job_id: int
    job_title: str
    company: str
    match_score: float
    skill_match: Dict[str, Any]
    experience_match: Dict[str, Any]
    location_match: Dict[str, Any]
    salary_match: Dict[str, Any]
    missing_skills: List[str]
    matching_skills: List[str]
    recommendations: List[str]


class JobMatchingAgent:
    """Match jobs against candidate profiles."""

    def __init__(self):
        self.name = "job_matching_agent"
        self.requirement_extractor = RequirementExtractor()

    def match_job_to_candidate(
        self,
        job: NormalizedJob,
        candidate_skills: List[Dict[str, Any]],
        candidate_experience_years: int,
        candidate_location: str,
        candidate_remote_preference: bool,
        candidate_salary_min: Optional[int] = None,
        job_requirements: Optional[ExtractedRequirements] = None,
    ) -> JobMatch:
        """Match a single job to a candidate profile."""
        logger.info(f"Matching job: {job.title}")

        if job_requirements is None:
            job_requirements = self.requirement_extractor.extract(job)

        # Skill matching
        skill_result = self._match_skills(
            job_requirements.required_skills,
            job_requirements.preferred_skills,
            candidate_skills,
        )

        # Experience matching
        exp_result = self._match_experience(
            job_requirements.experience_years,
            candidate_experience_years,
        )

        # Location matching
        loc_result = self._match_location(
            job,
            candidate_location,
            candidate_remote_preference,
        )

        # Salary matching
        salary_result = self._match_salary(
            job,
            candidate_salary_min,
        )

        # Calculate overall match score
        weights = {
            "skills": 0.50,
            "experience": 0.20,
            "location": 0.15,
            "salary": 0.15,
        }

        match_score = (
            skill_result["score"] * weights["skills"] +
            exp_result["score"] * weights["experience"] +
            loc_result["score"] * weights["location"] +
            salary_result["score"] * weights["salary"]
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            skill_result, exp_result, loc_result, salary_result
        )

        return JobMatch(
            job_id=0,  # Will be set by caller
            job_title=job.title,
            company=job.company_name,
            match_score=round(match_score, 1),
            skill_match=skill_result,
            experience_match=exp_result,
            location_match=loc_result,
            salary_match=salary_result,
            missing_skills=skill_result["missing_required"],
            matching_skills=skill_result["matching"],
            recommendations=recommendations,
        )

    def _match_skills(
        self,
        required: List[Dict[str, Any]],
        preferred: List[Dict[str, Any]],
        candidate_skills: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Match candidate skills to job requirements."""
        candidate_skill_names = {s["name"].lower(): s for s in candidate_skills}

        matching = []
        missing_required = []
        missing_preferred = []

        # Check required skills
        for req in required:
            req_name = req["name"].lower()
            if req_name in candidate_skill_names:
                matching.append({
                    "skill": req["name"],
                    "required": True,
                    "candidate_proficiency": candidate_skill_names[req_name].get("proficiency"),
                })
            else:
                missing_required.append(req["name"])

        # Check preferred skills
        for pref in preferred:
            pref_name = pref["name"].lower()
            if pref_name in candidate_skill_names:
                matching.append({
                    "skill": pref["name"],
                    "required": False,
                    "candidate_proficiency": candidate_skill_names[pref_name].get("proficiency"),
                })
            else:
                missing_preferred.append(pref["name"])

        # Score: required skills weighted more
        total_required = len(required)
        matched_required = total_required - len(missing_required)
        required_score = (matched_required / total_required * 100) if total_required > 0 else 100

        total_preferred = len(preferred)
        matched_preferred = total_preferred - len(missing_preferred)
        preferred_score = (matched_preferred / total_preferred * 100) if total_preferred > 0 else 100

        # Weighted skill score (required 70%, preferred 30%)
        skill_score = required_score * 0.7 + preferred_score * 0.3

        return {
            "score": round(skill_score, 1),
            "matching": matching,
            "missing_required": missing_required,
            "missing_preferred": missing_preferred,
            "required_matched": matched_required,
            "required_total": total_required,
            "preferred_matched": matched_preferred,
            "preferred_total": total_preferred,
        }

    def _match_experience(
        self,
        required_years: Optional[int],
        candidate_years: int,
    ) -> Dict[str, Any]:
        """Match candidate experience to job requirements."""
        if required_years is None:
            return {
                "score": 100,
                "required_years": None,
                "candidate_years": candidate_years,
                "gap": 0,
                "status": "not_specified",
            }

        gap = candidate_years - required_years

        if gap >= 0:
            # Candidate meets or exceeds requirement
            if gap <= 2:
                score = 100  # Close match
            elif gap <= 5:
                score = 90   # Overqualified but good
            else:
                score = 75   # Significantly overqualified
            status = "exceeds"
        else:
            # Candidate has less experience
            gap_abs = abs(gap)
            if gap_abs <= 1:
                score = 80   # Close
            elif gap_abs <= 2:
                score = 60   # Somewhat lacking
            elif gap_abs <= 3:
                score = 40   # Lacking
            else:
                score = 20   # Significantly lacking
            status = "below"

        return {
            "score": score,
            "required_years": required_years,
            "candidate_years": candidate_years,
            "gap": gap,
            "status": status,
        }

    def _match_location(
        self,
        job: NormalizedJob,
        candidate_location: str,
        candidate_remote: bool,
    ) -> Dict[str, Any]:
        """Match job location to candidate preferences."""
        if job.is_remote and candidate_remote:
            return {
                "score": 100,
                "job_location": job.normalized_location,
                "candidate_location": candidate_location,
                "remote_compatible": True,
                "status": "remote_match",
            }

        if not job.is_remote and not candidate_remote:
            # Both on-site - check location proximity
            from difflib import SequenceMatcher
            similarity = SequenceMatcher(None, job.normalized_location.lower(), candidate_location.lower()).ratio()
            score = int(similarity * 100)
            return {
                "score": score,
                "job_location": job.normalized_location,
                "candidate_location": candidate_location,
                "remote_compatible": False,
                "status": "onsite_match" if score > 70 else "location_mismatch",
            }

        if job.is_remote and not candidate_remote:
            return {
                "score": 50,
                "job_location": job.normalized_location,
                "candidate_location": candidate_location,
                "remote_compatible": True,
                "status": "candidate_prefers_onsite",
            }

        # Candidate wants remote but job is on-site
        return {
            "score": 30,
            "job_location": job.normalized_location,
            "candidate_location": candidate_location,
            "remote_compatible": False,
            "status": "candidate_wants_remote",
        }

    def _match_salary(
        self,
        job: NormalizedJob,
        candidate_min: Optional[int],
    ) -> Dict[str, Any]:
        """Match job salary to candidate expectations."""
        if not job.salary_yearly_min and not job.salary_yearly_max:
            return {
                "score": 100,
                "job_min": None,
                "job_max": None,
                "candidate_min": candidate_min,
                "status": "not_specified",
            }

        job_min = job.salary_yearly_min or 0
        job_max = job.salary_yearly_max or job_min

        if candidate_min is None:
            return {
                "score": 80,
                "job_min": job_min,
                "job_max": job_max,
                "candidate_min": None,
                "status": "no_preference",
            }

        if job_max >= candidate_min:
            if job_min >= candidate_min:
                score = 100  # Entire range above expectation
            else:
                score = 85   # Range overlaps
            status = "meets_expectations"
        else:
            # Job max below candidate min
            gap_pct = (candidate_min - job_max) / candidate_min * 100
            if gap_pct <= 10:
                score = 60
            elif gap_pct <= 20:
                score = 40
            else:
                score = 20
            status = "below_expectations"

        return {
            "score": score,
            "job_min": job_min,
            "job_max": job_max,
            "candidate_min": candidate_min,
            "status": status,
        }

    def _generate_recommendations(
        self,
        skill_result: Dict,
        exp_result: Dict,
        loc_result: Dict,
        salary_result: Dict,
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        if skill_result["missing_required"]:
            top_missing = skill_result["missing_required"][:3]
            recommendations.append(f"Learn required skills: {', '.join(top_missing)}")

        if skill_result["missing_preferred"]:
            top_missing = skill_result["missing_preferred"][:2]
            recommendations.append(f"Consider adding preferred skills: {', '.join(top_missing)}")

        if exp_result["status"] == "below":
            recommendations.append(f"Job requires {exp_result['required_years']} years experience (you have {exp_result['candidate_years']})")

        if loc_result["status"] in ["candidate_wants_remote", "location_mismatch"]:
            recommendations.append("Location mismatch - consider remote positions or relocation")

        if salary_result["status"] == "below_expectations":
            recommendations.append("Salary may be below your expectations")

        if not recommendations:
            recommendations.append("Strong match! Consider applying.")

        return recommendations

    def match_batch(
        self,
        jobs: List[NormalizedJob],
        candidate_skills: List[Dict[str, Any]],
        candidate_experience_years: int,
        candidate_location: str,
        candidate_remote_preference: bool,
        candidate_salary_min: Optional[int] = None,
    ) -> List[JobMatch]:
        """Match multiple jobs to a candidate."""
        matches = []
        for job in jobs:
            match = self.match_job_to_candidate(
                job=job,
                candidate_skills=candidate_skills,
                candidate_experience_years=candidate_experience_years,
                candidate_location=candidate_location,
                candidate_remote_preference=candidate_remote_preference,
                candidate_salary_min=candidate_salary_min,
            )
            matches.append(match)

        # Sort by match score descending
        matches.sort(key=lambda m: m.match_score, reverse=True)
        return matches