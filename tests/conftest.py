"""Pytest configuration and shared fixtures for CareerIntel AI tests."""

import asyncio
import os
import sys
from collections.abc import AsyncGenerator, Generator
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from backend.config import settings
from backend.database import Base, get_db
from backend.main import app
from backend.models import (
    User,
    Profile,
    Skill,
    Project,
    Experience,
    Resume,
    ResumeStatus,
    Job,
    Company,
    Application,
    Research,
    ResearchStatus,
    ResearchType,
    Interview,
    LearningPlan,
    Notification,
)
from backend.utils.security import create_access_token, get_password_hash


# ============================================================
# Test Database Setup (SQLite in-memory for speed)
# ============================================================

TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Create a test client with overridden database dependency."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ============================================================
# Auth Fixtures
# ============================================================

@pytest.fixture
def test_user(db_session: Session) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Test User",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_user_token(test_user: User) -> str:
    """Generate a valid JWT token for test user."""
    return create_access_token(data={"sub": test_user.id})


@pytest.fixture
def auth_headers(test_user_token: str) -> dict:
    """Authorization headers for authenticated requests."""
    return {"Authorization": f"Bearer {test_user_token}"}


@pytest.fixture
def second_user(db_session: Session) -> User:
    """Create a second test user for multi-user tests."""
    user = User(
        email="test2@example.com",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Test User 2",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ============================================================
# Model Fixtures
# ============================================================

@pytest.fixture
def test_profile(db_session: Session, test_user: User) -> Profile:
    """Create a test profile."""
    profile = Profile(
        user_id=test_user.id,
        headline="Senior Software Engineer",
        summary="Experienced developer with 8+ years in Python, React, AWS",
        location="San Francisco, CA",
        phone="+1-555-123-4567",
        linkedin_url="https://linkedin.com/in/testuser",
        github_url="https://github.com/testuser",
        portfolio_url="https://testuser.dev",
        years_experience=8,
        current_role="Senior Software Engineer",
        target_role="Staff Software Engineer",
        desired_salary_min=180000,
        desired_salary_max=250000,
        prefers_remote=True,
        willing_to_relocate=False,
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return profile


@pytest.fixture
def test_skills(db_session: Session, test_profile: Profile) -> list[Skill]:
    """Create test skills for profile."""
    skills_data = [
        {"name": "Python", "category": "technical", "proficiency": "expert", "years_experience": 8},
        {"name": "React", "category": "technical", "proficiency": "advanced", "years_experience": 5},
        {"name": "AWS", "category": "technical", "proficiency": "advanced", "years_experience": 4},
        {"name": "PostgreSQL", "category": "technical", "proficiency": "advanced", "years_experience": 6},
        {"name": "Docker", "category": "technical", "proficiency": "intermediate", "years_experience": 3},
        {"name": "Kubernetes", "category": "technical", "proficiency": "intermediate", "years_experience": 2},
        {"name": "System Design", "category": "soft", "proficiency": "advanced", "years_experience": 5},
        {"name": "Leadership", "category": "soft", "proficiency": "advanced", "years_experience": 3},
    ]
    skills = []
    for s in skills_data:
        skill = Skill(profile_id=test_profile.id, **s)
        db_session.add(skill)
        skills.append(skill)
    db_session.commit()
    for s in skills:
        db_session.refresh(s)
    return skills


@pytest.fixture
def test_projects(db_session: Session, test_profile: Profile) -> list[Project]:
    """Create test projects."""
    projects = [
        Project(
            profile_id=test_profile.id,
            name="Microservices Platform",
            description="Built a scalable microservices platform serving 10M+ requests/day",
            technologies=["Go", "Kubernetes", "gRPC", "PostgreSQL", "Redis"],
            role="Lead Engineer",
            start_date=datetime(2022, 1, 1),
            end_date=datetime(2023, 6, 1),
            url="https://github.com/testuser/microservices",
            metrics="Reduced deployment time by 80%, improved latency by 60%",
        ),
        Project(
            profile_id=test_profile.id,
            name="Real-time Collaboration Tool",
            description="Real-time document editing with WebSocket infrastructure",
            technologies=["Node.js", "WebSockets", "Redis", "React", "TypeScript"],
            role="Full Stack Developer",
            start_date=datetime(2020, 6, 1),
            end_date=datetime(2021, 12, 1),
            url="https://github.com/testuser/realtime-editor",
            metrics="Supported 50k+ concurrent users, 99.9% uptime",
        ),
    ]
    for p in projects:
        db_session.add(p)
    db_session.commit()
    for p in projects:
        db_session.refresh(p)
    return projects


@pytest.fixture
def test_experience(db_session: Session, test_profile: Profile) -> list[Experience]:
    """Create test work experience."""
    experiences = [
        Experience(
            profile_id=test_profile.id,
            title="Senior Software Engineer",
            company="TechCorp",
            location="San Francisco, CA",
            description="Lead team of 5 engineers building scalable microservices",
            start_date=datetime(2020, 1, 1),
            end_date=None,
            is_current=True,
            technologies=["Go", "Kubernetes", "PostgreSQL", "Redis", "gRPC", "AWS"],
        ),
        Experience(
            profile_id=test_profile.id,
            title="Software Engineer",
            company="StartupXYZ",
            location="San Francisco, CA",
            description="Built full-stack web applications using React, Node.js, MongoDB",
            start_date=datetime(2017, 6, 1),
            end_date=datetime(2019, 12, 31),
            is_current=False,
            technologies=["React", "Node.js", "MongoDB", "Express", "Docker"],
        ),
    ]
    for e in experiences:
        db_session.add(e)
    db_session.commit()
    for e in experiences:
        db_session.refresh(e)
    return experiences


@pytest.fixture
def test_resume(db_session: Session, test_user: User) -> Resume:
    """Create a test resume."""
    resume = Resume(
        user_id=test_user.id,
        filename="resume_test.pdf",
        original_filename="John_Doe_Resume.pdf",
        file_path="/tmp/test_resume.pdf",
        file_size=102400,
        mime_type="application/pdf",
        status=ResumeStatus.PARSED,
        is_primary=True,
        raw_text="John Doe\nSenior Software Engineer\n\nEXPERIENCE\nSenior Software Engineer at TechCorp (2020-Present)\n- Led team of 5 engineers building microservices\n- Reduced deployment time by 80%\n\nSoftware Engineer at StartupXYZ (2017-2020)\n- Built full-stack applications with React, Node.js\n\nEDUCATION\nBS Computer Science, Stanford University, 2017\n\nSKILLS\nPython, React, AWS, Kubernetes, PostgreSQL, Go",
        sections={"experience": "...", "education": "...", "skills": "..."},
        extracted_skills=["Python", "React", "AWS", "Kubernetes", "PostgreSQL", "Go"],
        extracted_projects=[{"name": "Project 1", "description": "..." }],
        extracted_experience=[{"title": "Senior Software Engineer", "company": "TechCorp"}],
        ats_score=85.0,
    )
    db_session.add(resume)
    db_session.commit()
    db_session.refresh(resume)
    return resume


@pytest.fixture
def test_company(db_session: Session) -> Company:
    """Create a test company."""
    company = Company(
        name="Google",
        description="Technology company specializing in Internet-related services",
        website="https://google.com",
        headquarters="Mountain View, CA",
        size="10000+",
        industry="Technology",
        founded_year=1998,
        culture_score=4.5,
        work_life_balance_score=4.2,
        compensation_score=4.7,
    )
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


@pytest.fixture
def test_jobs(db_session: Session, test_company: Company) -> list[Job]:
    """Create test jobs."""
    jobs = [
        Job(
            title="Senior Software Engineer",
            company_id=test_company.id,
            location="Mountain View, CA",
            is_remote=True,
            remote_type="hybrid",
            description="We are looking for a Senior Software Engineer...",
            requirements="5+ years Python, Go, Kubernetes, GCP",
            responsibilities="Build scalable systems, mentor engineers",
            salary_min=180000,
            salary_max=280000,
            salary_currency="USD",
            salary_period="yearly",
            experience_level="senior",
            employment_type="full_time",
            source="company",
            source_url="https://careers.google.com/jobs/1",
            source_job_id="google_1",
            posted_date=datetime.utcnow() - timedelta(days=2),
            expires_date=datetime.utcnow() + timedelta(days=30),
            application_url="https://careers.google.com/apply/1",
            skills=["Python", "Go", "Kubernetes", "GCP", "Distributed Systems"],
            quality_score=0.95,
            is_active=True,
        ),
        Job(
            title="Staff Software Engineer",
            company_id=test_company.id,
            location="San Francisco, CA",
            is_remote=True,
            remote_type="fully_remote",
            description="Lead technical direction for core infrastructure...",
            requirements="8+ years experience, distributed systems, leadership",
            responsibilities="Technical strategy, cross-team collaboration",
            salary_min=250000,
            salary_max=350000,
            salary_currency="USD",
            salary_period="yearly",
            experience_level="staff",
            employment_type="full_time",
            source="company",
            source_url="https://careers.google.com/jobs/2",
            source_job_id="google_2",
            posted_date=datetime.utcnow() - timedelta(days=5),
            expires_date=datetime.utcnow() + timedelta(days=60),
            application_url="https://careers.google.com/apply/2",
            skills=["Distributed Systems", "Leadership", "Go", "Kubernetes", "System Design"],
            quality_score=0.98,
            is_active=True,
        ),
    ]
    for job in jobs:
        db_session.add(job)
    db_session.commit()
    for job in jobs:
        db_session.refresh(job)
    return jobs


@pytest.fixture
def test_application(db_session: Session, test_user: User, test_jobs: list[Job]) -> Application:
    """Create a test application."""
    app = Application(
        user_id=test_user.id,
        job_id=test_jobs[0].id,
        resume_text="Test resume text",
        cover_letter="Test cover letter",
        status="submitted",
        applied_date=datetime.utcnow().date(),
        notes="Applied via referral",
    )
    db_session.add(app)
    db_session.commit()
    db_session.refresh(app)
    return app


@pytest.fixture
def test_research(db_session: Session, test_user: User) -> Research:
    """Create a test research task."""
    research = Research(
        user_id=test_user.id,
        query="What are the latest trends in AI/ML job market for 2024?",
        research_type=ResearchType.JOB_MARKET,
        target_role="Machine Learning Engineer",
        target_company=None,
        target_location="San Francisco",
        max_sources=10,
        timeout_seconds=300,
        status=ResearchStatus.COMPLETED,
        sources=[
            {"title": "AI Job Market Report 2024", "url": "https://example.com/report1", "source_type": "job_market"},
            {"title": "ML Engineer Salary Survey", "url": "https://example.com/salary", "source_type": "web"},
        ],
        executive_summary="The AI/ML job market continues to grow rapidly...",
        key_findings=["Demand for ML engineers up 40%", "Generative AI skills highly valued"],
        recommendations=["Focus on LLM/GenAI skills", "Build portfolio projects"],
        confidence_score=0.92,
        source_count=2,
        verified_claim_count=5,
        completed_at=datetime.utcnow(),
    )
    db_session.add(research)
    db_session.commit()
    db_session.refresh(research)
    return research


# ============================================================
# Mock Fixtures
# ============================================================

@pytest.fixture
def mock_openai_client() -> MagicMock:
    """Mock OpenAI client for testing LLM interactions."""
    mock = MagicMock()
    mock.chat.completions.create = AsyncMock(return_value=MagicMock(
        choices=[MagicMock(message=MagicMock(content="Mock LLM response"))]
    ))
    mock.embeddings.create = AsyncMock(return_value=MagicMock(
        data=[MagicMock(embedding=[0.1] * 1536)]
    ))
    return mock


@pytest.fixture
def mock_qdrant_client() -> MagicMock:
    """Mock Qdrant vector database client."""
    mock = MagicMock()
    mock.search = AsyncMock(return_value=[])
    mock.upsert = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_http_client() -> AsyncMock:
    """Mock HTTP client for external API calls."""
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=MagicMock(
        status_code=200,
        json=lambda: {"results": []},
        text="{}"
    ))
    mock.post = AsyncMock(return_value=MagicMock(
        status_code=200,
        json=lambda: {"success": True},
        text='{"success": true}'
    ))
    return mock


# ============================================================
# Test Data Factories
# ============================================================

class TestDataFactory:
    """Factory for creating test data objects."""

    @staticmethod
    def create_candidate_profile(
        name: str = "Test User",
        role: str = "Software Engineer",
        years_exp: int = 5,
        skills: list[str] = None
    ) -> dict:
        return {
            "name": name,
            "email": f"{name.lower().replace(' ', '.')}@example.com",
            "phone": "+1-555-000-0000",
            "location": "San Francisco, CA",
            "linkedin_url": f"https://linkedin.com/in/{name.lower().replace(' ', '')}",
            "github_url": f"https://github.com/{name.lower().replace(' ', '')}",
            "years_experience": years_exp,
            "current_role": role,
            "target_role": f"Senior {role}",
            "key_skills": skills or ["Python", "JavaScript", "React", "AWS"],
            "achievements": [
                "Led team of 5 engineers",
                "Reduced deployment time by 50%",
                "Built scalable microservices architecture"
            ],
        }

    @staticmethod
    def create_job_description(
        title: str = "Senior Software Engineer",
        company: str = "TechCorp",
        required_skills: list[str] = None
    ) -> str:
        return f"""
        {title} at {company}
        
        We are looking for a {title} to join our team.
        
        Requirements:
        - 5+ years experience
        - {' '.join(required_skills or ['Python', 'React', 'AWS'])}
        - Strong problem-solving skills
        
        Responsibilities:
        - Build scalable systems
        - Mentor junior engineers
        - Participate in code reviews
        
        Benefits:
        - Competitive salary
        - Equity
        - Health insurance
        """

    @staticmethod
    def create_resume_text(
        name: str = "John Doe",
        role: str = "Senior Software Engineer",
        years_exp: int = 8
    ) -> str:
        return f"""
        {name}
        {role} | San Francisco, CA | john.doe@email.com | (555) 123-4567
        LinkedIn: linkedin.com/in/johndoe | GitHub: github.com/johndoe
        
        SUMMARY
        {role} with {years_exp} years of experience in Python, React, AWS, and Kubernetes.
        Proven track record of building scalable systems and leading engineering teams.
        
        EXPERIENCE
        {role} at TechCorp Inc. | 2020-Present
        - Led team of 5 engineers building scalable microservices
        - Architected migration from monolith to microservices using Go and Kubernetes
        - Reduced deployment time by 80% through CI/CD pipeline improvements
        - Technologies: Go, Kubernetes, PostgreSQL, Redis, gRPC, AWS
        
        Software Engineer at StartupXYZ | 2017-2020
        - Built full-stack web applications using React, Node.js, and MongoDB
        - Implemented real-time features using WebSockets
        - Designed RESTful APIs serving 100k+ daily requests
        - Technologies: React, Node.js, MongoDB, Express, Docker
        
        EDUCATION
        BS Computer Science | Stanford University | 2017
        
        SKILLS
        Languages: Go, Python, JavaScript, TypeScript, SQL
        Frameworks: React, Node.js, Express, Gin, gRPC
        Infrastructure: Kubernetes, Docker, AWS, Terraform
        Databases: PostgreSQL, MongoDB, Redis
        """


@pytest.fixture
def test_data_factory() -> TestDataFactory:
    """Provide test data factory."""
    return TestDataFactory()


# ============================================================
# Async Helpers
# ============================================================

@pytest.fixture
def anyio_backend() -> str:
    """Use asyncio backend for anyio."""
    return "asyncio"


# ============================================================
# Cleanup
# ============================================================

@pytest.fixture(autouse=True)
def _cleanup_after_test():
    """Auto-cleanup after each test."""
    yield
    # Any cleanup code here


# ============================================================
# Pytest Configuration
# ============================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "requires_api: Tests requiring external API keys")


def pytest_collection_modifyitems(config, items):
    """Auto-mark tests based on location."""
    for item in items:
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)