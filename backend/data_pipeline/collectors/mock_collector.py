"""
Mock collector for development and testing.
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from backend.data_pipeline.collectors.base_collector import BaseCollector, RawDataRecord, CollectorHealth


class MockJobCollector(BaseCollector):
    """Mock job collector for development/testing."""
    
    MOCK_JOBS = [
        {
            "title": "Senior Python Developer",
            "company": "TechCorp",
            "location": "San Francisco, CA",
            "is_remote": True,
            "remote_type": "fully_remote",
            "description": "We are looking for a Senior Python Developer to join our team and build scalable backend services.",
            "requirements": "5+ years Python, FastAPI, PostgreSQL, Docker, AWS",
            "responsibilities": "Build scalable APIs, mentor junior developers, code reviews",
            "salary_min": 130000,
            "salary_max": 180000,
            "salary_currency": "USD",
            "salary_period": "yearly",
            "experience_level": "senior",
            "employment_type": "full_time",
            "source_job_id": "mock_1",
            "source_url": "https://example.com/jobs/1",
            "application_url": "https://example.com/apply/1",
            "application_email": "jobs@techcorp.com",
            "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS", "Git"],
            "keywords": ["microservices", "API", "scalable", "mentoring"],
            "quality_score": 0.9,
            "source": "mock",
        },
        {
            "title": "Full Stack Developer (React/Node)",
            "company": "StartupXYZ",
            "location": "New York, NY",
            "is_remote": True,
            "remote_type": "hybrid",
            "description": "Join our fast-growing startup as a Full Stack Developer building user-facing features.",
            "requirements": "3+ years React, Node.js, TypeScript, MongoDB",
            "responsibilities": "Build features end-to-end, collaborate with design team",
            "salary_min": 100000,
            "salary_max": 140000,
            "salary_currency": "USD",
            "salary_period": "yearly",
            "experience_level": "mid",
            "employment_type": "full_time",
            "source_job_id": "mock_2",
            "source_url": "https://example.com/jobs/2",
            "application_url": "https://example.com/apply/2",
            "application_email": "hiring@startupxyz.com",
            "skills": ["React", "Node.js", "TypeScript", "MongoDB", "GraphQL"],
            "keywords": ["startup", "full-stack", "typescript", "mongodb"],
            "quality_score": 0.85,
            "source": "mock",
        },
        {
            "title": "Machine Learning Engineer",
            "company": "AI Innovations Inc",
            "location": "Boston, MA",
            "is_remote": False,
            "remote_type": None,
            "description": "Work on cutting-edge ML models for production systems.",
            "requirements": "MS/PhD in CS, 3+ years ML, Python, PyTorch, TensorFlow, MLOps",
            "responsibilities": "Design ML pipelines, deploy models, optimize performance",
            "salary_min": 140000,
            "salary_max": 200000,
            "salary_currency": "USD",
            "salary_period": "yearly",
            "experience_level": "senior",
            "employment_type": "full_time",
            "source_job_id": "mock_3",
            "source_url": "https://example.com/jobs/3",
            "application_url": "https://example.com/apply/3",
            "application_email": "ml-jobs@aiinnovations.com",
            "skills": ["Python", "PyTorch", "TensorFlow", "MLOps", "Kubernetes", "ML"],
            "keywords": ["machine learning", "deep learning", "production", "mlops"],
            "quality_score": 0.95,
            "source": "mock",
        },
        {
            "title": "DevOps Engineer",
            "company": "CloudScale",
            "location": "Austin, TX",
            "is_remote": True,
            "remote_type": "fully_remote",
            "description": "Build and maintain cloud infrastructure for high-scale applications.",
            "requirements": "4+ years AWS, Terraform, Kubernetes, CI/CD, Python/Go",
            "responsibilities": "Infrastructure as code, monitoring, incident response",
            "salary_min": 120000,
            "salary_max": 160000,
            "salary_currency": "USD",
            "salary_period": "yearly",
            "experience_level": "senior",
            "employment_type": "full_time",
            "source_job_id": "mock_4",
            "source_url": "https://example.com/jobs/4",
            "application_url": "https://example.com/apply/4",
            "application_email": "devops@cloudscale.io",
            "skills": ["AWS", "Terraform", "Kubernetes", "Docker", "Python", "CI/CD"],
            "keywords": ["devops", "cloud", "infrastructure", "automation"],
            "quality_score": 0.88,
            "source": "mock",
        },
        {
            "title": "Frontend Developer (Vue.js)",
            "company": "DesignFirst",
            "location": "Remote",
            "is_remote": True,
            "remote_type": "fully_remote",
            "description": "Create beautiful, performant user interfaces for our design-focused platform.",
            "requirements": "3+ years Vue.js, Vuex, TypeScript, Tailwind, Testing",
            "responsibilities": "Build components, optimize performance, write tests",
            "salary_min": 90000,
            "salary_max": 130000,
            "salary_currency": "USD",
            "salary_period": "yearly",
            "experience_level": "mid",
            "employment_type": "full_time",
            "source_job_id": "mock_5",
            "source_url": "https://example.com/jobs/5",
            "application_url": "https://example.com/apply/5",
            "application_email": "frontend@designfirst.com",
            "skills": ["Vue.js", "Vuex", "TypeScript", "Tailwind", "Jest", "CSS"],
            "keywords": ["frontend", "vue", "ui", "performance"],
            "quality_score": 0.82,
            "source": "mock",
        },
    ]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._source_name = "mock_jobs"
        self._source_type = "internal_database"
        self._delay = self.config.get("delay", 0.1)
        self._failure_rate = self.config.get("failure_rate", 0.0)
    
    @property
    def source_name(self) -> str:
        return self._source_name
    
    @property
    def source_type(self) -> str:
        return self._source_type

    async def fetch(self, query: str = "", location: Optional[str] = None, 
                    remote: Optional[bool] = None, limit: int = 50, **kwargs) -> List[Dict[str, Any]]:
        """Return mock job data for testing."""
        await asyncio.sleep(self._delay)
        
        # Simulate random failures for testing
        if self._failure_rate > 0 and random.random() < self._failure_rate:
            raise ConnectionError("Simulated collector failure")
        
        filtered = []
        query_lower = query.lower()
        
        for job in self.MOCK_JOBS:
            # Filter by query
            if query_lower and not (
                query_lower in job["title"].lower() or
                query_lower in job["description"].lower() or
                any(query_lower in s.lower() for s in job["skills"])
            ):
                continue
            
            # Filter by location
            if location and location.lower() not in job["location"].lower():
                continue
            
            # Filter by remote
            if remote is not None and job["is_remote"] != remote:
                continue
            
            # Add posted/expires dates
            job_copy = job.copy()
            job_copy["posted_date"] = (datetime.utcnow() - timedelta(days=random.randint(1, 30))).isoformat()
            job_copy["expires_date"] = (datetime.utcnow() + timedelta(days=random.randint(20, 60))).isoformat()
            
            filtered.append(job_copy)
            
            if len(filtered) >= limit:
                break
        
        return filtered

    async def parse(self, raw_data: List[Dict[str, Any]]) -> List[RawDataRecord]:
        """Parse raw mock data into RawDataRecord objects."""
        records = []
        for job in raw_data:
            record = RawDataRecord.create(
                source_id="mock_jobs",
                source_name="mock",
                source_type="internal_database",
                external_id=job["source_job_id"],
                source_url=job["source_url"],
                raw_payload=job,
                metadata={"mock": True}
            )
            records.append(record)
        return records

    async def health_check(self) -> CollectorHealth:
        """Mock collector is always healthy."""
        return CollectorHealth.HEALTHY