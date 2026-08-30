import logging
import asyncio
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List
from dataclasses import dataclass
from abc import ABC, abstractmethod

import httpx

logger = logging.getLogger(__name__)


@dataclass
class RawJob:
    """Raw job data from external sources."""
    title: str
    company: str
    location: str
    is_remote: bool
    remote_type: Optional[str] = None
    description: str = ""
    requirements: Optional[str] = None
    responsibilities: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: str = "USD"
    salary_period: Optional[str] = None
    experience_level: Optional[str] = None
    employment_type: Optional[str] = None
    source: str = "unknown"
    source_url: str = ""
    source_job_id: str = ""
    posted_date: Optional[datetime] = None
    expires_date: Optional[datetime] = None
    application_url: Optional[str] = None
    application_email: Optional[str] = None
    skills: List[str] = None
    keywords: List[str] = None
    quality_score: float = 0.0

    def __post_init__(self):
        if self.skills is None:
            self.skills = []
        if self.keywords is None:
            self.keywords = []


class JobSearchProvider(ABC):
    """Abstract base class for job search providers."""

    @abstractmethod
    async def search_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        remote: Optional[bool] = None,
        limit: int = 50,
    ) -> List[RawJob]:
        pass

    @property
    @abstractmethod
    def source_name(self) -> str:
        pass


class MockJobProvider(JobSearchProvider):
    """Mock job provider for development/testing."""

    @property
    def source_name(self) -> str:
        return "mock"

    async def search_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        remote: Optional[bool] = None,
        limit: int = 50,
    ) -> List[RawJob]:
        """Return mock job data for testing."""
        await asyncio.sleep(0.1)  # Simulate API call

        mock_jobs = [
            RawJob(
                title="Senior Python Developer",
                company="TechCorp",
                location=location or "San Francisco, CA",
                is_remote=True,
                remote_type="fully_remote",
                description="We are looking for a Senior Python Developer to join our team...",
                requirements="5+ years Python, FastAPI, PostgreSQL, Docker, AWS",
                responsibilities="Build scalable APIs, mentor junior developers, code reviews",
                salary_min=130000,
                salary_max=180000,
                salary_currency="USD",
                salary_period="yearly",
                experience_level="senior",
                employment_type="full_time",
                source="mock",
                source_url="https://example.com/jobs/1",
                source_job_id="mock_1",
                posted_date=datetime.utcnow() - timedelta(days=2),
                expires_date=datetime.utcnow() + timedelta(days=30),
                application_url="https://example.com/apply/1",
                application_email="jobs@techcorp.com",
                skills=["Python", "FastAPI", "PostgreSQL", "Docker", "AWS", "Git"],
                keywords=["microservices", "API", "scalable", "mentoring"],
                quality_score=0.9,
            ),
            RawJob(
                title="Full Stack Developer (React/Node)",
                company="StartupXYZ",
                location=location or "New York, NY",
                is_remote=True,
                remote_type="hybrid",
                description="Join our fast-growing startup as a Full Stack Developer...",
                requirements="3+ years React, Node.js, TypeScript, MongoDB",
                responsibilities="Build features end-to-end, collaborate with design team",
                salary_min=100000,
                salary_max=140000,
                salary_currency="USD",
                salary_period="yearly",
                experience_level="mid",
                employment_type="full_time",
                source="mock",
                source_url="https://example.com/jobs/2",
                source_job_id="mock_2",
                posted_date=datetime.utcnow() - timedelta(days=5),
                expires_date=datetime.utcnow() + timedelta(days=25),
                application_url="https://example.com/apply/2",
                application_email="hiring@startupxyz.com",
                skills=["React", "Node.js", "TypeScript", "MongoDB", "GraphQL"],
                keywords=["startup", "full-stack", "typescript", "mongodb"],
                quality_score=0.85,
            ),
            RawJob(
                title="Machine Learning Engineer",
                company="AI Innovations Inc",
                location=location or "Boston, MA",
                is_remote=False,
                remote_type=None,
                description="Work on cutting-edge ML models for production systems...",
                requirements="MS/PhD in CS, 3+ years ML, Python, PyTorch, TensorFlow, MLOps",
                responsibilities="Design ML pipelines, deploy models, optimize performance",
                salary_min=140000,
                salary_max=200000,
                salary_currency="USD",
                salary_period="yearly",
                experience_level="senior",
                employment_type="full_time",
                source="mock",
                source_url="https://example.com/jobs/3",
                source_job_id="mock_3",
                posted_date=datetime.utcnow() - timedelta(days=1),
                expires_date=datetime.utcnow() + timedelta(days=35),
                application_url="https://example.com/apply/3",
                application_email="ml-jobs@aiinnovations.com",
                skills=["Python", "PyTorch", "TensorFlow", "MLOps", "Kubernetes", "ML"],
                keywords=["machine learning", "deep learning", "production", "mlops"],
                quality_score=0.95,
            ),
            RawJob(
                title="DevOps Engineer",
                company="CloudScale",
                location=location or "Austin, TX",
                is_remote=True,
                remote_type="fully_remote",
                description="Build and maintain cloud infrastructure...",
                requirements="4+ years AWS, Terraform, Kubernetes, CI/CD, Python/Go",
                responsibilities="Infrastructure as code, monitoring, incident response",
                salary_min=120000,
                salary_max=160000,
                salary_currency="USD",
                salary_period="yearly",
                experience_level="senior",
                employment_type="full_time",
                source="mock",
                source_url="https://example.com/jobs/4",
                source_job_id="mock_4",
                posted_date=datetime.utcnow() - timedelta(days=3),
                expires_date=datetime.utcnow() + timedelta(days=20),
                application_url="https://example.com/apply/4",
                application_email="devops@cloudscale.io",
                skills=["AWS", "Terraform", "Kubernetes", "Docker", "Python", "CI/CD"],
                keywords=["devops", "cloud", "infrastructure", "automation"],
                quality_score=0.88,
            ),
            RawJob(
                title="Frontend Developer (Vue.js)",
                company="DesignFirst",
                location=location or "Remote",
                is_remote=True,
                remote_type="fully_remote",
                description="Create beautiful, performant user interfaces...",
                requirements="3+ years Vue.js, Vuex, TypeScript, Tailwind, Testing",
                responsibilities="Build components, optimize performance, write tests",
                salary_min=90000,
                salary_max=130000,
                salary_currency="USD",
                salary_period="yearly",
                experience_level="mid",
                employment_type="full_time",
                source="mock",
                source_url="https://example.com/jobs/5",
                source_job_id="mock_5",
                posted_date=datetime.utcnow() - timedelta(days=4),
                expires_date=datetime.utcnow() + timedelta(days=30),
                application_url="https://example.com/apply/5",
                application_email="frontend@designfirst.com",
                skills=["Vue.js", "Vuex", "TypeScript", "Tailwind", "Jest", "CSS"],
                keywords=["frontend", "vue", "ui", "performance"],
                quality_score=0.82,
            ),
        ]

        # Filter by query
        filtered = []
        query_lower = query.lower()
        for job in mock_jobs:
            if (query_lower in job.title.lower() or
                query_lower in job.description.lower() or
                any(query_lower in s.lower() for s in job.skills)):
                filtered.append(job)

        return filtered[:limit]


class JobSearchAgent:
    """Agent responsible for searching jobs from multiple providers."""

    def __init__(self, providers: Optional[List[JobSearchProvider]] = None):
        self.name = "job_search_agent"
        self.providers = providers or [MockJobProvider()]

    async def search(
        self,
        query: str,
        location: Optional[str] = None,
        remote: Optional[bool] = None,
        limit: int = 50,
        providers: Optional[List[str]] = None,
    ) -> List[RawJob]:
        """Search jobs across all configured providers."""
        logger.info(f"Searching jobs: query='{query}', location='{location}', remote={remote}")

        all_jobs = []
        for provider in self.providers:
            if providers and provider.source_name not in providers:
                continue

            try:
                jobs = await provider.search_jobs(query, location, remote, limit)
                all_jobs.extend(jobs)
                logger.info(f"Provider '{provider.source_name}' returned {len(jobs)} jobs")
            except Exception as e:
                logger.error(f"Provider '{provider.source_name}' failed: {e}")

        # Deduplicate by source_job_id + source
        seen = set()
        unique_jobs = []
        for job in all_jobs:
            key = f"{job.source}:{job.source_job_id}"
            if key not in seen:
                seen.add(key)
                unique_jobs.append(job)

        logger.info(f"Total unique jobs found: {len(unique_jobs)}")
        return unique_jobs[:limit]

    def add_provider(self, provider: JobSearchProvider):
        """Add a new job search provider."""
        self.providers.append(provider)

    def remove_provider(self, source_name: str):
        """Remove a job search provider."""
        self.providers = [p for p in self.providers if p.source_name != source_name]