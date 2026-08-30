import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from enum import Enum as PyEnum

logger = logging.getLogger(__name__)


class ResourceType(str, PyEnum):
    COURSE = "course"
    BOOK = "book"
    ARTICLE = "article"
    VIDEO = "video"
    CERTIFICATION = "certification"
    PROJECT = "project"
    PRACTICE = "practice"
    WORKSHOP = "workshop"
    BOOTCAMP = "bootcamp"
    MENTORSHIP = "mentorship"


class LearningStyle(str, PyEnum):
    VISUAL = "visual"
    READING = "reading"
    HANDS_ON = "hands_on"
    AUDIO = "audio"
    MIXED = "mixed"


class DifficultyLevel(str, PyEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class LearningResource:
    """A learning resource."""
    title: str
    resource_type: ResourceType
    provider: str
    url: Optional[str] = None
    difficulty: DifficultyLevel = DifficultyLevel.BEGINNER
    estimated_hours: int = 0
    cost: float = 0.0  # 0 for free
    rating: float = 0.0
    skills_covered: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    certification: bool = False
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "resource_type": self.resource_type.value,
            "provider": self.provider,
            "url": self.url,
            "difficulty": self.difficulty.value,
            "estimated_hours": self.estimated_hours,
            "cost": self.cost,
            "rating": self.rating,
            "skills_covered": self.skills_covered,
            "prerequisites": self.prerequisites,
            "certification": self.certification,
            "description": self.description,
        }


@dataclass
class LearningMilestone:
    """A milestone in the learning plan."""
    id: str
    title: str
    description: str
    target_skills: List[str]
    resources: List[LearningResource]
    estimated_weeks: int
    target_date: Optional[date] = None
    completion_criteria: List[str] = field(default_factory=list)
    order: int = 0
    is_completed: bool = False
    completed_date: Optional[date] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "target_skills": self.target_skills,
            "resources": [r.to_dict() for r in self.resources],
            "estimated_weeks": self.estimated_weeks,
            "target_date": self.target_date.isoformat() if self.target_date else None,
            "completion_criteria": self.completion_criteria,
            "order": self.order,
            "is_completed": self.is_completed,
            "completed_date": self.completed_date.isoformat() if self.completed_date else None,
        }


@dataclass
class LearningPhase:
    """A phase in the learning plan."""
    id: str
    name: str
    description: str
    milestones: List[LearningMilestone]
    estimated_weeks: int
    focus_areas: List[str]
    order: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "milestones": [m.to_dict() for m in self.milestones],
            "estimated_weeks": self.estimated_weeks,
            "focus_areas": self.focus_areas,
            "order": self.order,
        }


@dataclass
class LearningPlan:
    """A complete learning plan."""
    id: str
    user_id: int
    target_role: str
    target_skills: List[str]
    current_skills: List[str]
    skill_gaps: List[str]
    phases: List[LearningPhase]
    total_estimated_weeks: int
    weekly_time_commitment_hours: int
    start_date: date
    target_completion_date: Optional[date] = None
    learning_style: LearningStyle = LearningStyle.MIXED
    budget: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "target_role": self.target_role,
            "target_skills": self.target_skills,
            "current_skills": self.current_skills,
            "skill_gaps": self.skill_gaps,
            "phases": [p.to_dict() for p in self.phases],
            "total_estimated_weeks": self.total_estimated_weeks,
            "weekly_time_commitment_hours": self.weekly_time_commitment_hours,
            "start_date": self.start_date.isoformat(),
            "target_completion_date": self.target_completion_date.isoformat() if self.target_completion_date else None,
            "learning_style": self.learning_style.value,
            "budget": self.budget,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class LearningProgress:
    """Track learning progress."""
    plan_id: str
    completed_milestones: int
    total_milestones: int
    completed_hours: float
    total_estimated_hours: float
    current_phase: int
    current_milestone: int
    skills_acquired: List[str]
    last_activity_date: Optional[date] = None
    streak_days: int = 0
    completion_percentage: float = 0.0


class LearningAgent:
    """Generate personalized learning roadmaps."""

    def __init__(self):
        self.name = "learning_agent"
        self._resource_database = self._initialize_resources()

    def _initialize_resources(self) -> Dict[str, List[LearningResource]]:
        """Initialize learning resource database."""
        # In production, this would be loaded from a database
        return {
            "Python": [
                LearningResource("Python for Everybody", ResourceType.COURSE, "Coursera", "https://coursera.org/learn/python",
                    DifficultyLevel.BEGINNER, 40, 0, 4.8, ["Python", "Programming Basics"], certification=True),
                LearningResource("Automate the Boring Stuff with Python", ResourceType.BOOK, "Al Sweigart", "https://automatetheboringstuff.com",
                    DifficultyLevel.BEGINNER, 20, 0, 4.7, ["Python", "Automation"]),
                LearningResource("Effective Python", ResourceType.BOOK, "Brett Slatkin", "https://effectivepython.com",
                    DifficultyLevel.INTERMEDIATE, 15, 40, 4.8, ["Python Best Practices"]),
                LearningResource("Real Python", ResourceType.ARTICLE, "Real Python", "https://realpython.com",
                    DifficultyLevel.BEGINNER, 50, 0, 4.9, ["Python", "Web Development", "Data Science"]),
                LearningResource("Python Official Documentation", ResourceType.ARTICLE, "Python.org", "https://docs.python.org",
                    DifficultyLevel.BEGINNER, 30, 0, 4.5, ["Python", "Standard Library"]),
            ],
            "JavaScript": [
                LearningResource("JavaScript Algorithms and Data Structures", ResourceType.COURSE, "freeCodeCamp", "https://freecodecamp.org",
                    DifficultyLevel.BEGINNER, 60, 0, 4.8, ["JavaScript", "Algorithms", "Data Structures"], certification=True),
                LearningResource("You Don't Know JS", ResourceType.BOOK, "Kyle Simpson", "https://github.com/getify/You-Dont-Know-JS",
                    DifficultyLevel.INTERMEDIATE, 30, 0, 4.9, ["JavaScript Internals"]),
                LearningResource("MDN Web Docs", ResourceType.ARTICLE, "Mozilla", "https://developer.mozilla.org",
                    DifficultyLevel.BEGINNER, 40, 0, 4.8, ["JavaScript", "Web APIs", "DOM"]),
            ],
            "React": [
                LearningResource("React Official Tutorial", ResourceType.ARTICLE, "React.dev", "https://react.dev/learn",
                    DifficultyLevel.BEGINNER, 15, 0, 4.8, ["React", "Components", "Hooks"]),
                LearningResource("Epic React", ResourceType.COURSE, "Kent C. Dodds", "https://epicreact.dev",
                    DifficultyLevel.INTERMEDIATE, 40, 500, 4.9, ["React", "Testing", "Patterns"], certification=True),
                LearningResource("React Patterns", ResourceType.ARTICLE, "React Patterns", "https://reactpatterns.com",
                    DifficultyLevel.INTERMEDIATE, 10, 0, 4.7, ["React Patterns", "Best Practices"]),
            ],
            "AWS": [
                LearningResource("AWS Certified Solutions Architect Associate", ResourceType.CERTIFICATION, "AWS", "https://aws.amazon.com/certification/certified-solutions-architect-associate",
                    DifficultyLevel.INTERMEDIATE, 80, 150, 4.7, ["AWS", "Architecture", "Services"], certification=True),
                LearningResource("AWS Free Tier Labs", ResourceType.PRACTICE, "AWS", "https://aws.amazon.com/free",
                    DifficultyLevel.BEGINNER, 30, 0, 4.5, ["AWS", "Hands-on Practice"]),
                LearningResource("A Cloud Guru AWS Courses", ResourceType.COURSE, "A Cloud Guru", "https://acloudguru.com",
                    DifficultyLevel.INTERMEDIATE, 60, 300, 4.6, ["AWS", "Cloud"], certification=True),
            ],
            "Kubernetes": [
                LearningResource("Kubernetes the Hard Way", ResourceType.PROJECT, "Kelsey Hightower", "https://github.com/kelseyhightower/kubernetes-the-hard-way",
                    DifficultyLevel.ADVANCED, 40, 0, 4.9, ["Kubernetes", "Cluster Setup", "Networking"]),
                LearningResource("CKA Certification Course", ResourceType.COURSE, "Linux Foundation", "https://training.linuxfoundation.org/training/kubernetes-fundamentals",
                    DifficultyLevel.ADVANCED, 50, 300, 4.6, ["Kubernetes", "CKA Prep"], certification=True),
                LearningResource("Kubernetes Official Docs", ResourceType.ARTICLE, "Kubernetes.io", "https://kubernetes.io/docs",
                    DifficultyLevel.INTERMEDIATE, 30, 0, 4.5, ["Kubernetes", "API", "Concepts"]),
            ],
            "Machine Learning": [
                LearningResource("Machine Learning Specialization", ResourceType.COURSE, "Coursera/Andrew Ng", "https://coursera.org/specializations/machine-learning-intro",
                    DifficultyLevel.BEGINNER, 60, 0, 4.9, ["ML", "Supervised Learning", "Unsupervised Learning"], certification=True),
                LearningResource("Hands-On ML with Scikit-Learn, Keras & TensorFlow", ResourceType.BOOK, "Aurelien Geron", "https://github.com/ageron/handson-ml2",
                    DifficultyLevel.INTERMEDIATE, 50, 50, 4.8, ["ML", "Scikit-Learn", "TensorFlow", "Keras"]),
                LearningResource("Fast.ai Practical Deep Learning", ResourceType.COURSE, "fast.ai", "https://course.fast.ai",
                    DifficultyLevel.INTERMEDIATE, 60, 0, 4.9, ["Deep Learning", "PyTorch", "Computer Vision", "NLP"], certification=True),
            ],
            "Docker": [
                LearningResource("Docker Mastery", ResourceType.COURSE, "Udemy/Bret Fisher", "https://udemy.com/course/docker-mastery",
                    DifficultyLevel.BEGINNER, 25, 20, 4.7, ["Docker", "Containers", "Docker Compose"], certification=True),
                LearningResource("Docker Official Docs", ResourceType.ARTICLE, "Docker", "https://docs.docker.com",
                    DifficultyLevel.BEGINNER, 20, 0, 4.5, ["Docker", "Containerization"]),
            ],
            "SQL": [
                LearningResource("SQL for Data Science", ResourceType.COURSE, "Coursera/UC Davis", "https://coursera.org/learn/sql-for-data-science",
                    DifficultyLevel.BEGINNER, 20, 0, 4.6, ["SQL", "Data Analysis"], certification=True),
                LearningResource("SQL Zoo", ResourceType.PRACTICE, "SQL Zoo", "https://sqlzoo.net",
                    DifficultyLevel.BEGINNER, 15, 0, 4.5, ["SQL", "Practice"]),
                LearningResource("PostgreSQL Tutorial", ResourceType.ARTICLE, "PostgreSQL", "https://postgresqltutorial.com",
                    DifficultyLevel.BEGINNER, 20, 0, 4.6, ["PostgreSQL", "Advanced SQL"]),
            ],
        }

    def generate_learning_plan(
        self,
        user_id: int,
        target_role: str,
        target_skills: List[str],
        current_skills: List[str],
        skill_gaps: List[str],
        weekly_hours: int = 10,
        learning_style: LearningStyle = LearningStyle.MIXED,
        budget: float = 0.0,
        target_date: Optional[date] = None,
    ) -> LearningPlan:
        """Generate a personalized learning plan."""
        logger.info(f"Generating learning plan for user {user_id} targeting {target_role}")

        # Filter resources by budget
        available_resources = self._filter_resources_by_budget(skill_gaps, budget)

        # Create phases based on skill dependencies
        phases = self._create_phases(skill_gaps, available_resources, learning_style)

        # Calculate total time
        total_weeks = sum(p.estimated_weeks for p in phases)
        total_hours = sum(
            sum(r.estimated_hours for m in p.milestones for r in m.resources)
            for p in phases
        )

        # Adjust for weekly commitment
        adjusted_weeks = max(total_weeks, total_hours // weekly_hours)

        # Set target date if not provided
        start_date = date.today()
        if not target_date:
            target_date = start_date + timedelta(weeks=adjusted_weeks)

        return LearningPlan(
            id=f"plan_{user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            user_id=user_id,
            target_role=target_role,
            target_skills=target_skills,
            current_skills=current_skills,
            skill_gaps=skill_gaps,
            phases=phases,
            total_estimated_weeks=adjusted_weeks,
            weekly_time_commitment_hours=weekly_hours,
            start_date=start_date,
            target_completion_date=target_date,
            learning_style=learning_style,
            budget=budget,
        )

    def _filter_resources_by_budget(
        self,
        skill_gaps: List[str],
        budget: float,
    ) -> Dict[str, List[LearningResource]]:
        """Filter resources by budget constraint."""
        filtered = {}
        for skill in skill_gaps:
            resources = self._resource_database.get(skill, [])
            if budget == 0:
                resources = [r for r in resources if r.cost == 0]
            else:
                # Allow some paid resources within budget
                free_resources = [r for r in resources if r.cost == 0]
                paid_resources = sorted([r for r in resources if r.cost > 0], key=lambda x: x.cost)
                total_cost = 0
                affordable = []
                for r in paid_resources:
                    if total_cost + r.cost <= budget:
                        affordable.append(r)
                        total_cost += r.cost
                resources = free_resources + affordable
            filtered[skill] = resources
        return filtered

    def _create_phases(
        self,
        skill_gaps: List[str],
        resources: Dict[str, List[LearningResource]],
        learning_style: LearningStyle,
    ) -> List[LearningPhase]:
        """Create learning phases based on skill dependencies."""
        phases = []

        # Group skills by category/foundation level
        foundation_skills = []
        intermediate_skills = []
        advanced_skills = []

        for skill in skill_gaps:
            skill_resources = resources.get(skill, [])
            if not skill_resources:
                continue

            min_difficulty = min(r.difficulty for r in skill_resources)
            if min_difficulty == DifficultyLevel.BEGINNER:
                foundation_skills.append(skill)
            elif min_difficulty == DifficultyLevel.INTERMEDIATE:
                intermediate_skills.append(skill)
            else:
                advanced_skills.append(skill)

        # Phase 1: Foundation
        if foundation_skills:
            phases.append(self._create_phase(
                id="phase_1",
                name="Foundation",
                description="Build fundamental skills and core concepts",
                skills=foundation_skills,
                resources=resources,
                learning_style=learning_style,
                order=0,
            ))

        # Phase 2: Intermediate
        if intermediate_skills:
            phases.append(self._create_phase(
                id="phase_2",
                name="Core Competencies",
                description="Build practical skills and apply knowledge",
                skills=intermediate_skills,
                resources=resources,
                learning_style=learning_style,
                order=1,
            ))

        # Phase 3: Advanced
        if advanced_skills:
            phases.append(self._create_phase(
                id="phase_3",
                name="Advanced Mastery",
                description="Master advanced concepts and build portfolio projects",
                skills=advanced_skills,
                resources=resources,
                learning_style=learning_style,
                order=2,
            ))

        return phases

    def _create_phase(
        self,
        id: str,
        name: str,
        description: str,
        skills: List[str],
        resources: Dict[str, List[LearningResource]],
        learning_style: LearningStyle,
        order: int,
    ) -> LearningPhase:
        """Create a learning phase with milestones."""
        milestones = []
        total_weeks = 0

        for i, skill in enumerate(skills):
            skill_resources = resources.get(skill, [])
            if not skill_resources:
                continue

            # Select best resources for learning style
            selected = self._select_resources_for_style(skill_resources, learning_style)
            milestone_weeks = max(r.estimated_hours for r in selected) // 10 + 1

            milestones.append(LearningMilestone(
                id=f"{id}_milestone_{i}",
                title=f"Learn {skill}",
                description=f"Master {skill} fundamentals and apply in practice",
                target_skills=[skill],
                resources=selected,
                estimated_weeks=milestone_weeks,
                completion_criteria=[
                    f"Complete all {skill} resources",
                    f"Build a project using {skill}",
                    f"Explain {skill} concepts to someone else",
                ],
                order=i,
            ))
            total_weeks += milestone_weeks

        return LearningPhase(
            id=id,
            name=name,
            description=description,
            milestones=milestones,
            estimated_weeks=total_weeks,
            focus_areas=skills,
            order=order,
        )

    def _select_resources_for_style(
        self,
        resources: List[LearningResource],
        style: LearningStyle,
    ) -> List[LearningResource]:
        """Select best resources for learning style."""
        if style == LearningStyle.VISUAL:
            preferred = [ResourceType.VIDEO, ResourceType.COURSE]
        elif style == LearningStyle.READING:
            preferred = [ResourceType.BOOK, ResourceType.ARTICLE]
        elif style == LearningStyle.HANDS_ON:
            preferred = [ResourceType.PROJECT, ResourceType.PRACTICE, ResourceType.CERTIFICATION]
        elif style == LearningStyle.AUDIO:
            preferred = [ResourceType.VIDEO, ResourceType.COURSE]
        else:  # MIXED
            preferred = [ResourceType.COURSE, ResourceType.BOOK, ResourceType.PROJECT, ResourceType.ARTICLE]

        # Sort by preference and rating
        def score(r: LearningResource) -> float:
            pref_score = 1.0 if r.resource_type in preferred else 0.5
            return pref_score * (r.rating / 5.0)

        return sorted(resources, key=score, reverse=True)[:3]

    def get_resource_recommendations(
        self,
        skill: str,
        difficulty: Optional[DifficultyLevel] = None,
        budget: float = 0.0,
    ) -> List[LearningResource]:
        """Get resource recommendations for a skill."""
        resources = self._resource_database.get(skill, [])

        if difficulty:
            resources = [r for r in resources if r.difficulty == difficulty]

        if budget == 0:
            resources = [r for r in resources if r.cost == 0]

        return sorted(resources, key=lambda r: r.rating, reverse=True)

    def estimate_learning_time(
        self,
        skills: List[str],
        current_proficiency: Dict[str, str],
        target_proficiency: Dict[str, str],
        weekly_hours: int = 10,
    ) -> Dict[str, Any]:
        """Estimate time to learn skills."""
        proficiency_levels = {
            "beginner": 0,
            "intermediate": 1,
            "advanced": 2,
            "expert": 3,
        }

        total_weeks = 0
        skill_estimates = {}

        for skill in skills:
            current = proficiency_levels.get(current_proficiency.get(skill, "beginner"), 0)
            target = proficiency_levels.get(target_proficiency.get(skill, "intermediate"), 1)
            gap = max(0, target - current)

            # Estimate: ~8 weeks per proficiency level at 10 hrs/week
            weeks = gap * 8 * (10 / weekly_hours)
            total_weeks += weeks
            skill_estimates[skill] = weeks

        return {
            "total_weeks": total_weeks,
            "skill_estimates": skill_estimates,
            "total_hours": total_weeks * weekly_hours,
            "assumptions": "8 weeks per proficiency level at 10 hours/week",
        }

    def create_micro_learning_plan(
        self,
        skill: str,
        available_hours_per_week: int,
        duration_weeks: int = 4,
    ) -> List[LearningMilestone]:
        """Create a short-term focused learning plan."""
        resources = self._resource_database.get(skill, [])
        if not resources:
            return []

        selected = self._select_resources_for_style(resources, LearningStyle.MIXED)[:2]

        milestones = []
        hours_per_week = available_hours_per_week
        hours_per_milestone = (duration_weeks * hours_per_week) // len(selected) if selected else duration_weeks * hours_per_week

        for i, resource in enumerate(selected):
            milestones.append(LearningMilestone(
                id=f"micro_{skill}_{i}",
                title=f"{resource.title}",
                description=f"Complete {resource.resource_type.value}: {resource.title}",
                target_skills=[skill],
                resources=[resource],
                estimated_weeks=max(1, resource.estimated_hours // hours_per_week),
                completion_criteria=[
                    f"Finish {resource.title}",
                    f"Complete exercises/projects in {resource.title}",
                ],
                order=i,
            ))

        return milestones

    def get_skill_prerequisites(self, skill: str) -> List[str]:
        """Get prerequisites for a skill."""
        prereq_map = {
            "React": ["JavaScript", "HTML", "CSS"],
            "Node.js": ["JavaScript", "Async Programming"],
            "Django": ["Python", "SQL", "HTTP Basics"],
            "FastAPI": ["Python", "Async Programming", "REST APIs"],
            "Kubernetes": ["Docker", "Linux", "Networking", "YAML"],
            "Machine Learning": ["Python", "Statistics", "Linear Algebra", "Calculus"],
            "Deep Learning": ["Machine Learning", "Python", "Linear Algebra"],
            "AWS": ["Linux", "Networking", "Security Basics"],
            "Terraform": ["AWS/GCP/Azure", "Infrastructure Concepts"],
            "CI/CD": ["Git", "Linux", "Scripting", "Docker"],
            "GraphQL": ["REST APIs", "JavaScript/TypeScript", "Database Basics"],
            "TypeScript": ["JavaScript", "Static Typing Concepts"],
            "Next.js": ["React", "TypeScript", "Node.js"],
            "PostgreSQL": ["SQL", "Database Design", "Relational Theory"],
            "Redis": ["Caching Concepts", "Data Structures", "Linux"],
            "Kafka": ["Distributed Systems", "Messaging Patterns", "Java/Go"],
        }
        return prereq_map.get(skill, [])