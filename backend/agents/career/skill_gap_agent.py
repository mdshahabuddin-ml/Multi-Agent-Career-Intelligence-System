import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum as PyEnum

from backend.models import Skill

logger = logging.getLogger(__name__)


class SkillCategory(str, PyEnum):
    TECHNICAL = "technical"
    SOFT = "soft"
    DOMAIN = "domain"
    TOOL = "tool"
    FRAMEWORK = "framework"
    LANGUAGE = "language"
    PLATFORM = "platform"
    METHODOLOGY = "methodology"


class ProficiencyLevel(str, PyEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class CandidateSkill:
    """A skill from candidate's profile."""
    name: str
    category: SkillCategory
    proficiency: ProficiencyLevel
    years_experience: float = 0
    confidence: float = 1.0
    source: str = "profile"  # profile, resume, inferred
    last_used: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category.value,
            "proficiency": self.proficiency.value,
            "years_experience": self.years_experience,
            "confidence": self.confidence,
            "source": self.source,
            "last_used": self.last_used.isoformat() if self.last_used else None,
        }


@dataclass
class RequiredSkill:
    """A skill required for a target role."""
    name: str
    category: SkillCategory
    required_proficiency: ProficiencyLevel
    importance: float = 1.0  # 0-1, how critical
    frequency_in_jobs: float = 0.0  # percentage of job postings mentioning
    alternative_names: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category.value,
            "required_proficiency": self.required_proficiency.value,
            "importance": self.importance,
            "frequency_in_jobs": self.frequency_in_jobs,
            "alternative_names": self.alternative_names,
        }


@dataclass
class SkillGap:
    """A gap between candidate skill and required skill."""
    skill_name: str
    category: SkillCategory
    candidate_proficiency: Optional[ProficiencyLevel]
    required_proficiency: ProficiencyLevel
    importance: float
    gap_severity: float  # 0-1, how severe the gap
    is_missing: bool = False  # True if candidate doesn't have skill at all
    estimated_learning_time_weeks: int = 0
    learning_resources: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_name": self.skill_name,
            "category": self.category.value,
            "candidate_proficiency": self.candidate_proficiency.value if self.candidate_proficiency else None,
            "required_proficiency": self.required_proficiency.value,
            "importance": self.importance,
            "gap_severity": self.gap_severity,
            "is_missing": self.is_missing,
            "estimated_learning_time_weeks": self.estimated_learning_time_weeks,
            "learning_resources": self.learning_resources,
        }


@dataclass
class SkillGapAnalysis:
    """Complete skill gap analysis result."""
    target_role: str
    candidate_skills: List[CandidateSkill]
    required_skills: List[RequiredSkill]
    gaps: List[SkillGap]
    matched_skills: List[Dict[str, Any]]
    overall_match_score: float  # 0-1
    critical_gaps_count: int
    moderate_gaps_count: int
    minor_gaps_count: int
    estimated_total_learning_time_weeks: int
    priority_skills: List[str]  # Top skills to learn first
    analysis_timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_role": self.target_role,
            "candidate_skills": [s.to_dict() for s in self.candidate_skills],
            "required_skills": [s.to_dict() for s in self.required_skills],
            "gaps": [g.to_dict() for g in self.gaps],
            "matched_skills": self.matched_skills,
            "overall_match_score": self.overall_match_score,
            "critical_gaps_count": self.critical_gaps_count,
            "moderate_gaps_count": self.moderate_gaps_count,
            "minor_gaps_count": self.minor_gaps_count,
            "estimated_total_learning_time_weeks": self.estimated_total_learning_time_weeks,
            "priority_skills": self.priority_skills,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
        }


class SkillGapAgent:
    """Analyze skill gaps between candidate and target role."""

    def __init__(self):
        self.name = "skill_gap_agent"
        self._role_skill_database = self._initialize_role_skills()

    def _initialize_role_skills(self) -> Dict[str, List[RequiredSkill]]:
        """Initialize database of required skills per role."""
        # This would be loaded from a database in production
        return {
            "software engineer": [
                RequiredSkill("Python", SkillCategory.LANGUAGE, ProficiencyLevel.ADVANCED, 0.9, 0.85),
                RequiredSkill("JavaScript", SkillCategory.LANGUAGE, ProficiencyLevel.INTERMEDIATE, 0.7, 0.75),
                RequiredSkill("SQL", SkillCategory.LANGUAGE, ProficiencyLevel.ADVANCED, 0.8, 0.8),
                RequiredSkill("Git", SkillCategory.TOOL, ProficiencyLevel.ADVANCED, 0.9, 0.95),
                RequiredSkill("Docker", SkillCategory.TOOL, ProficiencyLevel.INTERMEDIATE, 0.6, 0.7),
                RequiredSkill("AWS", SkillCategory.PLATFORM, ProficiencyLevel.INTERMEDIATE, 0.7, 0.65),
                RequiredSkill("REST APIs", SkillCategory.METHODOLOGY, ProficiencyLevel.ADVANCED, 0.8, 0.8),
                RequiredSkill("Testing", SkillCategory.METHODOLOGY, ProficiencyLevel.INTERMEDIATE, 0.7, 0.7),
                RequiredSkill("System Design", SkillCategory.METHODOLOGY, ProficiencyLevel.ADVANCED, 0.8, 0.6),
                RequiredSkill("Communication", SkillCategory.SOFT, ProficiencyLevel.ADVANCED, 0.8, 0.9),
            ],
            "machine learning engineer": [
                RequiredSkill("Python", SkillCategory.LANGUAGE, ProficiencyLevel.EXPERT, 0.95, 0.95),
                RequiredSkill("PyTorch", SkillCategory.FRAMEWORK, ProficiencyLevel.ADVANCED, 0.9, 0.8),
                RequiredSkill("TensorFlow", SkillCategory.FRAMEWORK, ProficiencyLevel.INTERMEDIATE, 0.7, 0.7),
                RequiredSkill("Machine Learning", SkillCategory.DOMAIN, ProficiencyLevel.EXPERT, 0.95, 0.9),
                RequiredSkill("Deep Learning", SkillCategory.DOMAIN, ProficiencyLevel.ADVANCED, 0.9, 0.8),
                RequiredSkill("MLOps", SkillCategory.METHODOLOGY, ProficiencyLevel.ADVANCED, 0.8, 0.7),
                RequiredSkill("Statistics", SkillCategory.DOMAIN, ProficiencyLevel.ADVANCED, 0.8, 0.8),
                RequiredSkill("SQL", SkillCategory.LANGUAGE, ProficiencyLevel.INTERMEDIATE, 0.6, 0.7),
                RequiredSkill("Docker", SkillCategory.TOOL, ProficiencyLevel.INTERMEDIATE, 0.6, 0.65),
                RequiredSkill("Kubernetes", SkillCategory.TOOL, ProficiencyLevel.INTERMEDIATE, 0.5, 0.5),
            ],
            "data scientist": [
                RequiredSkill("Python", SkillCategory.LANGUAGE, ProficiencyLevel.ADVANCED, 0.9, 0.9),
                RequiredSkill("R", SkillCategory.LANGUAGE, ProficiencyLevel.INTERMEDIATE, 0.5, 0.4),
                RequiredSkill("SQL", SkillCategory.LANGUAGE, ProficiencyLevel.ADVANCED, 0.8, 0.85),
                RequiredSkill("Pandas", SkillCategory.FRAMEWORK, ProficiencyLevel.ADVANCED, 0.8, 0.8),
                RequiredSkill("Machine Learning", SkillCategory.DOMAIN, ProficiencyLevel.ADVANCED, 0.9, 0.85),
                RequiredSkill("Statistics", SkillCategory.DOMAIN, ProficiencyLevel.EXPERT, 0.9, 0.9),
                RequiredSkill("Data Visualization", SkillCategory.DOMAIN, ProficiencyLevel.ADVANCED, 0.8, 0.8),
                RequiredSkill("Tableau", SkillCategory.TOOL, ProficiencyLevel.INTERMEDIATE, 0.5, 0.5),
                RequiredSkill("Communication", SkillCategory.SOFT, ProficiencyLevel.ADVANCED, 0.9, 0.95),
            ],
            "devops engineer": [
                RequiredSkill("Linux", SkillCategory.PLATFORM, ProficiencyLevel.EXPERT, 0.95, 0.95),
                RequiredSkill("Docker", SkillCategory.TOOL, ProficiencyLevel.EXPERT, 0.95, 0.95),
                RequiredSkill("Kubernetes", SkillCategory.TOOL, ProficiencyLevel.ADVANCED, 0.9, 0.85),
                RequiredSkill("Terraform", SkillCategory.TOOL, ProficiencyLevel.ADVANCED, 0.8, 0.75),
                RequiredSkill("AWS", SkillCategory.PLATFORM, ProficiencyLevel.EXPERT, 0.9, 0.9),
                RequiredSkill("CI/CD", SkillCategory.METHODOLOGY, ProficiencyLevel.EXPERT, 0.95, 0.9),
                RequiredSkill("Python", SkillCategory.LANGUAGE, ProficiencyLevel.ADVANCED, 0.8, 0.8),
                RequiredSkill("Monitoring", SkillCategory.DOMAIN, ProficiencyLevel.ADVANCED, 0.8, 0.8),
                RequiredSkill("Scripting", SkillCategory.LANGUAGE, ProficiencyLevel.ADVANCED, 0.8, 0.85),
            ],
            "frontend developer": [
                RequiredSkill("JavaScript", SkillCategory.LANGUAGE, ProficiencyLevel.EXPERT, 0.95, 0.95),
                RequiredSkill("TypeScript", SkillCategory.LANGUAGE, ProficiencyLevel.ADVANCED, 0.9, 0.85),
                RequiredSkill("React", SkillCategory.FRAMEWORK, ProficiencyLevel.EXPERT, 0.95, 0.9),
                RequiredSkill("CSS", SkillCategory.LANGUAGE, ProficiencyLevel.ADVANCED, 0.9, 0.9),
                RequiredSkill("HTML", SkillCategory.LANGUAGE, ProficiencyLevel.EXPERT, 0.95, 0.95),
                RequiredSkill("Redux", SkillCategory.FRAMEWORK, ProficiencyLevel.INTERMEDIATE, 0.6, 0.6),
                RequiredSkill("Testing", SkillCategory.METHODOLOGY, ProficiencyLevel.INTERMEDIATE, 0.7, 0.7),
                RequiredSkill("Web Performance", SkillCategory.DOMAIN, ProficiencyLevel.ADVANCED, 0.7, 0.6),
                RequiredSkill("Git", SkillCategory.TOOL, ProficiencyLevel.ADVANCED, 0.9, 0.95),
            ],
        }

    def analyze_skill_gaps(
        self,
        candidate_skills: List[CandidateSkill],
        target_role: str,
        custom_required_skills: Optional[List[RequiredSkill]] = None,
    ) -> SkillGapAnalysis:
        """Analyze skill gaps for a target role."""
        logger.info(f"Analyzing skill gaps for role: {target_role}")

        # Get required skills for target role
        target_role_lower = target_role.lower()
        required_skills = custom_required_skills or self._role_skill_database.get(
            target_role_lower,
            self._infer_required_skills(target_role)
        )

        # Normalize candidate skills for matching
        candidate_skill_map = self._normalize_candidate_skills(candidate_skills)

        # Analyze gaps
        gaps = []
        matched = []

        for req_skill in required_skills:
            match_result = self._match_skill(req_skill, candidate_skill_map)

            if match_result["matched"]:
                matched.append({
                    "skill": req_skill.name,
                    "candidate_proficiency": match_result["candidate_proficiency"].value if match_result["candidate_proficiency"] else None,
                    "required_proficiency": req_skill.required_proficiency.value,
                    "match_quality": match_result["match_quality"],
                })

                # Check if proficiency gap exists
                if match_result["candidate_proficiency"] and self._proficiency_gap(
                    match_result["candidate_proficiency"],
                    req_skill.required_proficiency
                ) > 0:
                    gap = self._create_gap(
                        req_skill,
                        match_result["candidate_proficiency"],
                        False
                    )
                    gaps.append(gap)
            else:
                # Skill completely missing
                gap = self._create_gap(req_skill, None, True)
                gaps.append(gap)

        # Calculate scores
        overall_match = self._calculate_match_score(matched, gaps, required_skills)

        # Categorize gaps
        critical = [g for g in gaps if g.gap_severity >= 0.7]
        moderate = [g for g in gaps if 0.4 <= g.gap_severity < 0.7]
        minor = [g for g in gaps if g.gap_severity < 0.4]

        # Sort gaps by severity and importance
        gaps.sort(key=lambda g: (g.gap_severity * g.importance), reverse=True)

        # Determine priority skills
        priority_skills = self._determine_priority_skills(gaps, required_skills)

        # Estimate learning time
        total_time = sum(g.estimated_learning_time_weeks for g in gaps)

        return SkillGapAnalysis(
            target_role=target_role,
            candidate_skills=candidate_skills,
            required_skills=required_skills,
            gaps=gaps,
            matched_skills=matched,
            overall_match_score=overall_match,
            critical_gaps_count=len(critical),
            moderate_gaps_count=len(moderate),
            minor_gaps_count=len(minor),
            estimated_total_learning_time_weeks=total_time,
            priority_skills=priority_skills,
        )

    def _normalize_candidate_skills(self, skills: List[CandidateSkill]) -> Dict[str, CandidateSkill]:
        """Normalize skill names for matching."""
        normalized = {}
        for skill in skills:
            key = skill.name.lower().strip()
            normalized[key] = skill
            # Also add aliases
            for alias in self._get_skill_aliases(skill.name):
                normalized[alias.lower()] = skill
        return normalized

    def _get_skill_aliases(self, skill_name: str) -> List[str]:
        """Get known aliases for a skill."""
        aliases = {
            "javascript": ["js", "ecmascript"],
            "typescript": ["ts"],
            "machine learning": ["ml"],
            "deep learning": ["dl"],
            "artificial intelligence": ["ai"],
            "continuous integration": ["ci"],
            "continuous deployment": ["cd"],
            "continuous integration/continuous deployment": ["ci/cd"],
            "amazon web services": ["aws"],
            "google cloud platform": ["gcp", "google cloud"],
            "microsoft azure": ["azure"],
            "postgresql": ["postgres", "psql"],
            "amazon dynamodb": ["dynamodb"],
            "amazon s3": ["s3"],
            "elastic search": ["elasticsearch", "es"],
            "apache kafka": ["kafka"],
            "redis": ["redis"],
            "nginx": ["nginx"],
            "apache": ["httpd"],
        }
        return aliases.get(skill_name.lower(), [])

    def _match_skill(self, req_skill: RequiredSkill, candidate_skills: Dict[str, CandidateSkill]) -> Dict[str, Any]:
        """Match required skill to candidate skills."""
        # Direct name match
        req_name = req_skill.name.lower()
        if req_name in candidate_skills:
            return {
                "matched": True,
                "candidate_skill": candidate_skills[req_name],
                "candidate_proficiency": candidate_skills[req_name].proficiency,
                "match_quality": 1.0,
            }

        # Check aliases
        for alias in req_skill.alternative_names:
            if alias.lower() in candidate_skills:
                return {
                    "matched": True,
                    "candidate_skill": candidate_skills[alias.lower()],
                    "candidate_proficiency": candidate_skills[alias.lower()].proficiency,
                    "match_quality": 0.9,
                }

        # Fuzzy match on common aliases
        for alias in self._get_skill_aliases(req_skill.name):
            if alias.lower() in candidate_skills:
                return {
                    "matched": True,
                    "candidate_skill": candidate_skills[alias.lower()],
                    "candidate_proficiency": candidate_skills[alias.lower()].proficiency,
                    "match_quality": 0.8,
                }

        return {"matched": False}

    def _proficiency_gap(self, candidate: ProficiencyLevel, required: ProficiencyLevel) -> int:
        """Calculate proficiency gap (0-3)."""
        levels = {
            ProficiencyLevel.BEGINNER: 0,
            ProficiencyLevel.INTERMEDIATE: 1,
            ProficiencyLevel.ADVANCED: 2,
            ProficiencyLevel.EXPERT: 3,
        }
        return max(0, levels[required] - levels[candidate])

    def _create_gap(
        self,
        req_skill: RequiredSkill,
        candidate_proficiency: Optional[ProficiencyLevel],
        is_missing: bool,
    ) -> SkillGap:
        """Create a skill gap object."""
        if is_missing:
            gap_severity = min(1.0, req_skill.importance * 1.2)
            candidate_prof = None
        else:
            gap_levels = self._proficiency_gap(candidate_proficiency, req_skill.required_proficiency)
            gap_severity = min(1.0, (gap_levels / 3) * req_skill.importance)

        # Estimate learning time
        proficiency_levels = {
            ProficiencyLevel.BEGINNER: 0,
            ProficiencyLevel.INTERMEDIATE: 1,
            ProficiencyLevel.ADVANCED: 2,
            ProficiencyLevel.EXPERT: 3,
        }

        if is_missing:
            target_level = proficiency_levels[req_skill.required_proficiency]
            weeks_per_level = 8  # ~8 weeks per proficiency level
            learning_time = (target_level + 1) * weeks_per_level
        else:
            current_level = proficiency_levels[candidate_proficiency]
            target_level = proficiency_levels[req_skill.required_proficiency]
            weeks_per_level = 6
            learning_time = max(0, (target_level - current_level)) * weeks_per_level

        return SkillGap(
            skill_name=req_skill.name,
            category=req_skill.category,
            candidate_proficiency=candidate_proficiency,
            required_proficiency=req_skill.required_proficiency,
            importance=req_skill.importance,
            gap_severity=round(gap_severity, 2),
            is_missing=is_missing,
            estimated_learning_time_weeks=learning_time,
            learning_resources=self._get_learning_resources(req_skill.name, req_skill.category),
        )

    def _get_learning_resources(self, skill_name: str, category: SkillCategory) -> List[Dict[str, Any]]:
        """Get learning resources for a skill."""
        # In production, this would query a learning resource database
        base_resources = [
            {"type": "course", "title": f"{skill_name} Complete Course", "provider": "Udemy/Coursera", "estimated_hours": 20},
            {"type": "documentation", "title": f"Official {skill_name} Documentation", "provider": "Official", "estimated_hours": 10},
            {"type": "practice", "title": f"{skill_name} Projects", "provider": "GitHub/LeetCode", "estimated_hours": 30},
        ]
        return base_resources

    def _calculate_match_score(
        self,
        matched: List[Dict],
        gaps: List[SkillGap],
        required_skills: List[RequiredSkill],
    ) -> float:
        """Calculate overall match score."""
        if not required_skills:
            return 1.0

        total_importance = sum(s.importance for s in required_skills)
        matched_importance = sum(
            m["match_quality"] * next(s.importance for s in required_skills if s.name == m["skill"])
            for m in matched
        )

        return round(matched_importance / total_importance if total_importance > 0 else 1.0, 2)

    def _determine_priority_skills(
        self,
        gaps: List[SkillGap],
        required_skills: List[RequiredSkill],
    ) -> List[str]:
        """Determine priority skills to learn."""
        # Sort by severity * importance * frequency
        skill_priority = {}
        for req in required_skills:
            gap = next((g for g in gaps if g.skill_name == req.name), None)
            if gap:
                score = gap.gap_severity * req.importance * req.frequency_in_jobs
                skill_priority[req.name] = score

        sorted_skills = sorted(skill_priority.items(), key=lambda x: x[1], reverse=True)
        return [s[0] for s in sorted_skills[:5]]

    def _infer_required_skills(self, target_role: str) -> List[RequiredSkill]:
        """Infer required skills for unknown role."""
        # Generic tech role skills
        return [
            RequiredSkill("Programming", SkillCategory.LANGUAGE, ProficiencyLevel.ADVANCED, 0.8, 0.8),
            RequiredSkill("Problem Solving", SkillCategory.SOFT, ProficiencyLevel.ADVANCED, 0.9, 0.9),
            RequiredSkill("Communication", SkillCategory.SOFT, ProficiencyLevel.ADVANCED, 0.8, 0.9),
            RequiredSkill("Git", SkillCategory.TOOL, ProficiencyLevel.ADVANCED, 0.8, 0.9),
        ]