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


# Common aliases / alternate spellings for skill names. Keys are matched
# case-insensitively after stripping whitespace; values are the canonical
# keys used in the resource database below.
SKILL_ALIASES = {
    "js": "JavaScript",
    "javascript/typescript": "JavaScript",
    "ts": "TypeScript",
    "typescript/javascript": "TypeScript",
    "k8s": "Kubernetes",
    "ml": "Machine Learning",
    "machine-learning": "Machine Learning",
    "ai/ml": "Machine Learning",
    "dl": "Deep Learning",
    "deep-learning": "Deep Learning",
    "deep learning (pytorch, tensorflow)": "Deep Learning",
    "rest api": "REST APIs",
    "rest-api": "REST APIs",
    "restful apis": "REST APIs",
    "apis": "REST APIs",
    "api design": "REST APIs",
    "software testing": "Testing",
    "qa": "Testing",
    "quality assurance": "Testing",
    "unit testing": "Testing",
    "system-design": "System Design",
    "systems design": "System Design",
    "architecture": "System Design",
    "soft skills": "Communication",
    "team communication": "Communication",
    "executive communication": "Communication",
    "technical communication": "Communication",
    "ci cd": "CI/CD",
    "cicd": "CI/CD",
    "continuous integration": "CI/CD",
    "css3": "CSS",
    "html5": "HTML",
    "postgres": "SQL",
    "postgresql": "SQL",
    "mysql": "SQL",
    "databases": "SQL",
    "database basics": "SQL",
    "git/github": "Git",
    "github": "Git",
    "version control": "Git",
    "containers": "Docker",
    "containerization": "Docker",
    "cloud": "AWS",
    "frontend": "React",
    "front-end": "React",
    "backend": "Python",
    "back-end": "Python",
    "programming": "Python",
    "programming basics": "Python",
    "data structures": "Python",
    "algorithms": "Python",
    "basic algorithms": "Python",
    "debugging": "Testing",
    "linux/unix": "Linux",
    "unix": "Linux",
    "command line": "Linux",
    "shell": "Scripting",
    "bash": "Scripting",
    "data analysis": "Pandas",
    "statistics & probability": "Statistics",
    "probability": "Statistics",
    "math": "Statistics",
    "visualization": "Data Visualization",
    "dashboarding": "Data Visualization",
    "observability": "Monitoring",
    "logging": "Monitoring",
    "networking": "System Design",
    "distributed systems": "System Design",
    "microservices": "System Design",
    "web apis": "REST APIs",
    "dom": "JavaScript",
    "web performance optimization": "Web Performance",
    "performance": "Web Performance",
    "state management": "Redux",
}


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
            "Git": [
                LearningResource("Pro Git Book", ResourceType.BOOK, "Scott Chacon & Ben Straub", "https://git-scm.com/book/en/v2",
                    DifficultyLevel.BEGINNER, 20, 0, 4.9, ["Git", "Version Control"]),
                LearningResource("Git & GitHub for Beginners", ResourceType.COURSE, "freeCodeCamp", "https://www.freecodecamp.org/news/git-and-github-for-beginners/",
                    DifficultyLevel.BEGINNER, 8, 0, 4.8, ["Git", "GitHub"], certification=True),
                LearningResource("Learn Git Branching", ResourceType.PRACTICE, "Pcottle", "https://learngitbranching.js.org",
                    DifficultyLevel.BEGINNER, 10, 0, 4.9, ["Git", "Branching"]),
            ],
            "REST APIs": [
                LearningResource("FastAPI Official Tutorial", ResourceType.ARTICLE, "FastAPI", "https://fastapi.tiangolo.com/tutorial/",
                    DifficultyLevel.BEGINNER, 15, 0, 4.9, ["REST APIs", "FastAPI", "Python"]),
                LearningResource("REST API Tutorial (freeCodeCamp)", ResourceType.ARTICLE, "freeCodeCamp", "https://www.freecodecamp.org/news/rest-api-tutorial/",
                    DifficultyLevel.BEGINNER, 6, 0, 4.7, ["REST APIs", "HTTP", "JSON"]),
                LearningResource("RESTful API Design Guide", ResourceType.ARTICLE, "RESTfulAPI.net", "https://restfulapi.net",
                    DifficultyLevel.BEGINNER, 12, 0, 4.6, ["REST APIs", "HTTP", "API Design"]),
            ],
            "Testing": [
                LearningResource("Quality Assurance Certification", ResourceType.COURSE, "freeCodeCamp", "https://www.freecodecamp.org/learn/quality-assurance/",
                    DifficultyLevel.BEGINNER, 40, 0, 4.7, ["Testing", "QA", "Automation"], certification=True),
                LearningResource("Martin Fowler on Testing", ResourceType.ARTICLE, "martinfowler.com", "https://martinfowler.com/tags/testing.html",
                    DifficultyLevel.INTERMEDIATE, 10, 0, 4.8, ["Testing", "TDD", "Test Design"]),
                LearningResource("ISTQB Foundation Syllabus", ResourceType.ARTICLE, "ISTQB", "https://www.istqb.org/certification-paths/istqb-foundation-level/",
                    DifficultyLevel.BEGINNER, 20, 0, 4.5, ["Testing", "Test Design", "Certification"]),
            ],
            "System Design": [
                LearningResource("System Design Primer", ResourceType.PROJECT, "donnemartin (GitHub)", "https://github.com/donnemartin/system-design-primer",
                    DifficultyLevel.BEGINNER, 30, 0, 4.9, ["System Design", "Scalability", "Architecture"]),
                LearningResource("System Design 101", ResourceType.ARTICLE, "ByteByteGo", "https://bytebytego.com/guides/system-design-101",
                    DifficultyLevel.BEGINNER, 12, 0, 4.7, ["System Design", "Architecture"]),
                LearningResource("Designing Data-Intensive Applications", ResourceType.BOOK, "Martin Kleppmann", "https://dataintensive.net",
                    DifficultyLevel.INTERMEDIATE, 40, 50, 4.9, ["System Design", "Databases", "Distributed Systems"]),
            ],
            "Communication": [
                LearningResource("Business Communication Skills", ResourceType.COURSE, "Alison", "https://alison.com/course/business-communication-skills",
                    DifficultyLevel.BEGINNER, 10, 0, 4.5, ["Communication", "Business Writing"], certification=True),
                LearningResource("Toastmasters International", ResourceType.PRACTICE, "Toastmasters", "https://www.toastmasters.org",
                    DifficultyLevel.BEGINNER, 20, 0, 4.7, ["Communication", "Public Speaking"]),
                LearningResource("Crucial Conversations", ResourceType.BOOK, "Patterson, Grenny et al.", "https://www.cruciallearning.com/books/",
                    DifficultyLevel.INTERMEDIATE, 12, 25, 4.8, ["Communication", "Difficult Conversations"]),
            ],
            "TypeScript": [
                LearningResource("TypeScript Handbook", ResourceType.ARTICLE, "Microsoft", "https://www.typescriptlang.org/docs/handbook/intro.html",
                    DifficultyLevel.BEGINNER, 20, 0, 4.9, ["TypeScript", "Types"]),
                LearningResource("Total TypeScript Free Tutorials", ResourceType.VIDEO, "Matt Pocock", "https://www.totaltypescript.com/tutorials",
                    DifficultyLevel.BEGINNER, 10, 0, 4.8, ["TypeScript", "Practice"]),
            ],
            "CSS": [
                LearningResource("Learn CSS", ResourceType.COURSE, "Google/web.dev", "https://web.dev/learn/css",
                    DifficultyLevel.BEGINNER, 25, 0, 4.9, ["CSS", "Layout", "Responsive Design"], certification=True),
                LearningResource("CSS-Tricks Almanac", ResourceType.ARTICLE, "CSS-Tricks", "https://css-tricks.com/almanac/",
                    DifficultyLevel.BEGINNER, 20, 0, 4.8, ["CSS", "Reference"]),
                LearningResource("Flexbox Froggy", ResourceType.PRACTICE, "Codepip", "https://flexboxfroggy.com",
                    DifficultyLevel.BEGINNER, 5, 0, 4.8, ["CSS", "Flexbox"]),
            ],
            "HTML": [
                LearningResource("MDN HTML Basics", ResourceType.ARTICLE, "Mozilla", "https://developer.mozilla.org/en-US/docs/Learn/Getting_started_with_the_web/HTML_basics",
                    DifficultyLevel.BEGINNER, 10, 0, 4.9, ["HTML", "Web Basics", "Semantics"]),
                LearningResource("HTML Full Course", ResourceType.VIDEO, "freeCodeCamp", "https://www.freecodecamp.org/news/html-crash-course/",
                    DifficultyLevel.BEGINNER, 8, 0, 4.7, ["HTML", "Forms", "Semantics"]),
            ],
            "Redux": [
                LearningResource("Redux Essentials Tutorial", ResourceType.ARTICLE, "Redux", "https://redux.js.org/tutorials/essentials/part-1-overview-concepts",
                    DifficultyLevel.BEGINNER, 15, 0, 4.8, ["Redux", "State Management"]),
                LearningResource("Redux Toolkit Quick Start", ResourceType.ARTICLE, "Redux", "https://redux-toolkit.js.org/tutorials/quick-start",
                    DifficultyLevel.BEGINNER, 8, 0, 4.7, ["Redux Toolkit", "React"]),
            ],
            "Web Performance": [
                LearningResource("Learn Performance", ResourceType.COURSE, "Google/web.dev", "https://web.dev/learn/performance",
                    DifficultyLevel.BEGINNER, 15, 0, 4.8, ["Web Performance", "Core Web Vitals"]),
                LearningResource("High Performance Browser Networking", ResourceType.BOOK, "Ilya Grigorik", "https://hpbn.co",
                    DifficultyLevel.INTERMEDIATE, 30, 0, 4.8, ["Web Performance", "Networking"]),
            ],
            "Linux": [
                LearningResource("Introduction to Linux", ResourceType.COURSE, "Linux Foundation", "https://training.linuxfoundation.org/training/introduction-to-linux/",
                    DifficultyLevel.BEGINNER, 40, 0, 4.8, ["Linux", "Command Line"], certification=True),
                LearningResource("OverTheWire: Bandit", ResourceType.PRACTICE, "OverTheWire", "https://overthewire.org/wargames/bandit/",
                    DifficultyLevel.BEGINNER, 15, 0, 4.8, ["Linux", "Shell"]),
            ],
            "Scripting": [
                LearningResource("Bash Scripting Tutorial", ResourceType.ARTICLE, "ryanstutorials", "https://ryanstutorials.net/bash-scripting-tutorial/",
                    DifficultyLevel.BEGINNER, 10, 0, 4.6, ["Scripting", "Bash"]),
                LearningResource("Automate the Boring Stuff with Python", ResourceType.BOOK, "Al Sweigart", "https://automatetheboringstuff.com",
                    DifficultyLevel.INTERMEDIATE, 20, 0, 4.7, ["Scripting", "Python", "Automation"]),
            ],
            "Terraform": [
                LearningResource("Terraform Official Tutorials", ResourceType.ARTICLE, "HashiCorp", "https://developer.hashicorp.com/terraform/tutorials",
                    DifficultyLevel.BEGINNER, 20, 0, 4.8, ["Terraform", "IaC"]),
                LearningResource("Terraform Up & Running", ResourceType.BOOK, "Yevgeniy Brikman", "https://www.terraformupandrunning.com",
                    DifficultyLevel.INTERMEDIATE, 25, 35, 4.7, ["Terraform", "AWS"]),
            ],
            "CI/CD": [
                LearningResource("GitHub Actions Documentation", ResourceType.ARTICLE, "GitHub", "https://docs.github.com/en/actions",
                    DifficultyLevel.BEGINNER, 15, 0, 4.8, ["CI/CD", "GitHub Actions"]),
                LearningResource("Jenkins User Handbook", ResourceType.ARTICLE, "Jenkins", "https://www.jenkins.io/doc/book/",
                    DifficultyLevel.BEGINNER, 20, 0, 4.6, ["CI/CD", "Jenkins", "Pipelines"]),
            ],
            "Monitoring": [
                LearningResource("Grafana Tutorials", ResourceType.COURSE, "Grafana Labs", "https://grafana.com/tutorials/",
                    DifficultyLevel.BEGINNER, 10, 0, 4.6, ["Monitoring", "Grafana", "Dashboards"]),
                LearningResource("Prometheus Documentation", ResourceType.ARTICLE, "Prometheus", "https://prometheus.io/docs/introduction/overview/",
                    DifficultyLevel.INTERMEDIATE, 15, 0, 4.7, ["Monitoring", "Prometheus", "Metrics"]),
            ],
            "PyTorch": [
                LearningResource("PyTorch Official Tutorials", ResourceType.ARTICLE, "PyTorch", "https://pytorch.org/tutorials",
                    DifficultyLevel.BEGINNER, 25, 0, 4.8, ["PyTorch", "Deep Learning", "Tensors"]),
                LearningResource("Intro to Deep Learning with PyTorch", ResourceType.COURSE, "Udacity", "https://www.udacity.com/course/deep-learning-pytorch--ud188",
                    DifficultyLevel.BEGINNER, 40, 0, 4.7, ["PyTorch", "Neural Networks"], certification=True),
            ],
            "TensorFlow": [
                LearningResource("TensorFlow Official Guide", ResourceType.ARTICLE, "TensorFlow", "https://www.tensorflow.org/learn",
                    DifficultyLevel.BEGINNER, 25, 0, 4.7, ["TensorFlow", "ML", "Keras"]),
                LearningResource("TensorFlow in Practice", ResourceType.COURSE, "DeepLearning.AI/Coursera", "https://www.coursera.org/professional-certificates/tensorflow-in-practice",
                    DifficultyLevel.BEGINNER, 60, 0, 4.8, ["TensorFlow", "Deep Learning"], certification=True),
            ],
            "Deep Learning": [
                LearningResource("Deep Learning Specialization", ResourceType.COURSE, "Coursera/Andrew Ng", "https://www.coursera.org/specializations/deep-learning",
                    DifficultyLevel.BEGINNER, 80, 0, 4.9, ["Deep Learning", "Neural Networks"], certification=True),
                LearningResource("Dive into Deep Learning", ResourceType.BOOK, "Aston Zhang et al.", "https://d2l.ai",
                    DifficultyLevel.INTERMEDIATE, 50, 0, 4.8, ["Deep Learning", "PyTorch", "TensorFlow"]),
            ],
            "MLOps": [
                LearningResource("Machine Learning Engineering for Production (MLOps)", ResourceType.COURSE, "DeepLearning.AI/Coursera", "https://www.coursera.org/specializations/machine-learning-engineering-for-production-mlops",
                    DifficultyLevel.BEGINNER, 60, 0, 4.7, ["MLOps", "Deployment", "Pipelines"], certification=True),
                LearningResource("Made With ML", ResourceType.ARTICLE, "Goku Mohandas", "https://madewithml.com",
                    DifficultyLevel.BEGINNER, 20, 0, 4.8, ["MLOps", "ML Pipelines"]),
            ],
            "Statistics": [
                LearningResource("Statistics with Python", ResourceType.COURSE, "Coursera/U-Michigan", "https://www.coursera.org/specializations/statistics-with-python",
                    DifficultyLevel.BEGINNER, 40, 0, 4.7, ["Statistics", "Python", "Probability"], certification=True),
                LearningResource("Seeing Theory", ResourceType.ARTICLE, "Brown University", "https://seeing-theory.brown.edu",
                    DifficultyLevel.BEGINNER, 10, 0, 4.8, ["Statistics", "Probability", "Visualization"]),
            ],
            "R": [
                LearningResource("R for Data Science", ResourceType.BOOK, "Hadley Wickham", "https://r4ds.hadley.nz",
                    DifficultyLevel.BEGINNER, 30, 0, 4.9, ["R", "Data Science", "Tidyverse"]),
                LearningResource("Swirl: Learn R in R", ResourceType.PRACTICE, "swirlstats", "https://swirlstats.com",
                    DifficultyLevel.BEGINNER, 15, 0, 4.6, ["R", "Programming"]),
            ],
            "Pandas": [
                LearningResource("Pandas Official User Guide", ResourceType.ARTICLE, "pandas", "https://pandas.pydata.org/docs/user_guide/index.html",
                    DifficultyLevel.BEGINNER, 20, 0, 4.8, ["Pandas", "Data Analysis"]),
                LearningResource("Pandas Exercises", ResourceType.PRACTICE, "guipsamora (GitHub)", "https://github.com/guipsamora/pandas_exercises",
                    DifficultyLevel.BEGINNER, 15, 0, 4.7, ["Pandas", "Practice"]),
            ],
            "Data Visualization": [
                LearningResource("Data Visualization with Python", ResourceType.VIDEO, "freeCodeCamp", "https://www.freecodecamp.org/news/data-visualization-with-python/",
                    DifficultyLevel.BEGINNER, 12, 0, 4.7, ["Data Visualization", "Matplotlib", "Seaborn"]),
                LearningResource("Storytelling with Data", ResourceType.BOOK, "Cole Nussbaumer Knaflic", "https://www.storytellingwithdata.com/books",
                    DifficultyLevel.BEGINNER, 15, 30, 4.8, ["Data Visualization", "Storytelling"]),
            ],
            "Tableau": [
                LearningResource("Tableau Training Videos", ResourceType.VIDEO, "Tableau", "https://www.tableau.com/learn/training",
                    DifficultyLevel.BEGINNER, 20, 0, 4.6, ["Tableau", "Dashboards"]),
                LearningResource("Tableau Public Resources", ResourceType.PRACTICE, "Tableau", "https://public.tableau.com/s/resources",
                    DifficultyLevel.BEGINNER, 15, 0, 4.5, ["Tableau", "Practice"]),
            ],
        }

    def _normalize_skill_key(self, skill: str) -> Optional[str]:
        """Map a free-form skill name to its canonical database key.

        Matching is case-insensitive and alias-aware ("rest api" ->
        "REST APIs"). Returns None when the skill has no curated entry.
        """
        if not skill:
            return None
        cleaned = skill.strip()
        if not cleaned:
            return None
        if cleaned in self._resource_database:
            return cleaned
        lowered = cleaned.lower()
        if lowered in SKILL_ALIASES:
            return SKILL_ALIASES[lowered]
        for key in self._resource_database:
            if key.lower() == lowered:
                return key
        return None

    def _fallback_resources(self, skill: str) -> List[LearningResource]:
        """Generate useful starter resources for skills without a curated entry.

        Guarantees the learning-resources endpoint never returns an empty
        list for a valid skill query.
        """
        query = "+".join(skill.strip().split())
        slug = "-".join(skill.strip().lower().split())
        # Keep slugs URL-safe for the GitHub topics link.
        slug = "".join(c if (c.isalnum() or c == "-") else "-" for c in slug)
        while "--" in slug:
            slug = slug.replace("--", "-")
        return [
            LearningResource(
                f"{skill} Complete Course", ResourceType.COURSE, "Coursera",
                f"https://www.coursera.org/search?query={query}",
                DifficultyLevel.BEGINNER, 20, 0, 4.5, [skill],
            ),
            LearningResource(
                f"Learn {skill} (freeCodeCamp)", ResourceType.ARTICLE, "freeCodeCamp",
                f"https://www.freecodecamp.org/news/search/?query={query}",
                DifficultyLevel.BEGINNER, 10, 0, 4.5, [skill],
            ),
            LearningResource(
                f"{skill} Projects & Examples", ResourceType.PRACTICE, "GitHub",
                f"https://github.com/topics/{slug}",
                DifficultyLevel.BEGINNER, 15, 0, 4.5, [skill],
            ),
        ]

    def _get_resources_for_skill(self, skill: str) -> List[LearningResource]:
        """Return curated resources for a skill, or a generated fallback."""
        key = self._normalize_skill_key(skill)
        if key is not None:
            return list(self._resource_database.get(key, []))
        return self._fallback_resources(skill.strip())

    def _coerce_difficulty(self, difficulty: Any) -> Optional[DifficultyLevel]:
        """Coerce a raw difficulty value (enum or string) to DifficultyLevel.

        Returns None when no usable value was provided so callers can skip
        the filter instead of matching nothing.
        """
        if difficulty is None:
            return None
        if isinstance(difficulty, DifficultyLevel):
            return difficulty
        try:
            return DifficultyLevel(str(difficulty).strip().lower())
        except ValueError:
            return None

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
            resources = self._get_resources_for_skill(skill)
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
        resources = self._get_resources_for_skill(skill)

        level = self._coerce_difficulty(difficulty)
        if level is not None:
            resources = [r for r in resources if r.difficulty == level]

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
        resources = self._get_resources_for_skill(skill)
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