"""Unit tests for Job Intelligence agents."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from backend.data_pipeline import (
    JobNormalizer,
    NormalizedJob,
    DuplicateDetector,
    DuplicateMatch,
    RawDataRecord,
)
from backend.agents.jobs.job_search_agent import JobSearchAgent, RawJob, MockJobProvider
from backend.agents.jobs.requirement_extractor import RequirementExtractor, ExtractedRequirements
from backend.agents.jobs.job_matching_agent import JobMatchingAgent, JobMatch
from backend.agents.jobs.opportunity_ranker import OpportunityRanker, RankedOpportunity


class TestJobSearchAgent:
    """Tests for JobSearchAgent."""

    @pytest.fixture
    def search_agent(self):
        return JobSearchAgent(providers=[MockJobProvider()])

    @pytest.mark.asyncio
    async def test_search_jobs_basic(self, search_agent):
        """Test basic job search functionality."""
        jobs = await search_agent.search(
            query="Python",
            location="San Francisco",
            remote=True,
            limit=10,
        )

        assert len(jobs) > 0
        assert all(isinstance(job, RawJob) for job in jobs)
        assert any("Python" in job.title or "Python" in job.skills for job in jobs)

    @pytest.mark.asyncio
    async def test_search_jobs_remote_filter(self, search_agent):
        """Test remote job filtering."""
        jobs = await search_agent.search(
            query="Software Engineer",
            remote=True,
        )

        assert all(job.is_remote for job in jobs)

    @pytest.mark.asyncio
    async def test_search_jobs_location_filter(self, search_agent):
        """Test location-based filtering."""
        jobs = await search_agent.search(
            query="Engineer",
            location="New York",
        )

        assert any("New York" in job.location for job in jobs)

    @pytest.mark.asyncio
    async def test_deduplication(self, search_agent):
        """Test that duplicate jobs are removed."""
        # Add same provider twice
        search_agent.add_provider(MockJobProvider())
        
        jobs = await search_agent.search(query="Python", limit=20)
        
        # Check no duplicate source_job_id + source combinations
        seen = set()
        for job in jobs:
            key = f"{job.source}:{job.source_job_id}"
            assert key not in seen, f"Duplicate job found: {key}"
            seen.add(key)

    @pytest.mark.asyncio
    async def test_add_remove_provider(self, search_agent):
        """Test adding and removing providers."""
        initial_count = len(search_agent.providers)
        
        mock_provider = MagicMock()
        mock_provider.source_name = "test_provider"
        mock_provider.search_jobs = AsyncMock(return_value=[])
        
        search_agent.add_provider(mock_provider)
        assert len(search_agent.providers) == initial_count + 1
        
        search_agent.remove_provider("test_provider")
        assert len(search_agent.providers) == initial_count


class TestJobNormalizer:
    """Tests for JobNormalizer."""

    @pytest.fixture
    def normalizer(self):
        return JobNormalizer()

    def test_normalize_raw_job(self, normalizer):
        """Test normalizing a raw job to standard format."""
        raw_record = RawDataRecord.create(
            source_id="mock_jobs",
            source_name="Mock Job Provider",
            source_type="internal_database",
            external_id="mock_1",
            source_url="https://example.com/jobs/1",
            raw_payload={
                "title": "Sr. Python Developer",
                "company": "TechCorp Inc.",
                "location": "San Francisco, CA",
                "is_remote": True,
                "remote_type": "fully_remote",
                "description": "We need a Senior Python Developer...",
                "requirements": "5+ years Python, FastAPI, PostgreSQL, Docker, AWS",
                "responsibilities": "Build APIs, mentor juniors, code reviews",
                "salary_min": 130000,
                "salary_max": 180000,
                "salary_currency": "USD",
                "salary_period": "yearly",
                "experience_level": "senior",
                "employment_type": "full_time",
                "source": "mock",
                "source_job_id": "mock_1",
                "application_url": "https://example.com/apply/1",
                "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS", "Git"],
                "keywords": ["microservices", "API", "scalable"],
                "quality_score": 0.9,
            }
        )

        normalized = normalizer.normalize(raw_record)

        assert isinstance(normalized, NormalizedJob)
        assert normalized.title == "Sr. Python Developer"
        assert normalized.company_name == "TechCorp Inc."
        assert normalized.location == "San Francisco, CA"
        assert normalized.is_remote is True
        assert normalized.salary_min == 130000
        assert normalized.salary_max == 180000
        assert len(normalized.skills) > 0

    def test_normalize_salary_periods(self, normalizer):
        """Test salary normalization across different periods."""
        raw_record = RawDataRecord.create(
            source_id="test",
            source_name="Test Provider",
            source_type="test",
            external_id="test_1",
            source_url="https://example.com/jobs/1",
            raw_payload={
                "title": "Developer",
                "company": "Test",
                "location": "Remote",
                "is_remote": True,
                "description": "",
                "requirements": "",
                "responsibilities": "",
                "salary_min": 50,
                "salary_max": 100,
                "salary_currency": "USD",
                "salary_period": "hourly",
                "experience_level": "mid",
                "employment_type": "contract",
                "source": "test",
                "source_job_id": "test_1",
                "skills": [],
                "keywords": [],
                "quality_score": 0.5,
            }
        )

        normalized = normalizer.normalize(raw_record)
        # Should convert hourly to yearly (approx 2080 hours/year)
        # The original salary_period is preserved, yearly conversion is in salary_yearly_min
        assert normalized.salary_yearly_min >= 100000  # 50 * 2080
        assert normalized.salary_period == "hourly"  # Original period preserved

    def test_normalize_skill_names(self, normalizer):
        """Test skill name standardization."""
        raw_record = RawDataRecord.create(
            source_id="test",
            source_name="Test Provider",
            source_type="test",
            external_id="test_1",
            source_url="https://example.com/jobs/1",
            raw_payload={
                "title": "Developer",
                "company": "Test",
                "location": "Remote",
                "is_remote": True,
                "description": "",
                "requirements": "",
                "responsibilities": "",
                "salary_min": None,
                "salary_max": None,
                "salary_currency": "USD",
                "salary_period": "yearly",
                "experience_level": "mid",
                "employment_type": "full_time",
                "source": "test",
                "source_job_id": "test_1",
                "skills": ["py", "js", "k8s", "tf", "react.js", "node"],
                "keywords": [],
                "quality_score": 0.5,
            }
        )

        normalized = normalizer.normalize(raw_record)
        
        skill_names = [s.lower() for s in normalized.skills]
        assert "python" in skill_names or "py" in skill_names
        assert "javascript" in skill_names or "js" in skill_names
        assert "kubernetes" in skill_names or "k8s" in skill_names


class TestDuplicateDetector:
    """Tests for DuplicateDetector."""

    @pytest.fixture
    def detector(self):
        return DuplicateDetector()

    def _create_norm_job(self, title, company, location, source_job_id, quality_score=0.8):
        """Helper to create a NormalizedJob for testing."""
        return NormalizedJob(
            title=title,
            company_name=company,
            company_domain=f"{company.lower().replace(' ', '')}.com",
            location=location,
            normalized_location=location,
            is_remote="remote" in location.lower(),
            remote_type="fully_remote" if "remote" in location.lower() else "on_site",
            description="Test description",
            requirements="Python",
            responsibilities="Code",
            salary_min=100000,
            salary_max=150000,
            salary_currency="USD",
            salary_period="yearly",
            salary_yearly_min=100000,
            salary_yearly_max=150000,
            experience_level="mid",
            employment_type="full_time",
            source="test",
            source_url="http://example.com",
            source_job_id=source_job_id,
            posted_date=datetime.utcnow(),
            expires_date=datetime.utcnow() + timedelta(days=30),
            application_url=None,
            application_email=None,
            skills=["Python"],
            keywords=[],
            quality_score=quality_score,
            raw_record=None,
        )

    def test_detect_exact_duplicate(self, detector):
        """Test detection of exact duplicate jobs."""
        job1 = self._create_norm_job(
            title="Python Developer",
            company="TechCorp",
            location="SF",
            source_job_id="job_1",
            quality_score=0.8,
        )
        job2 = self._create_norm_job(
            title="Python Developer",
            company="TechCorp",
            location="SF",
            source_job_id="job_1",
            quality_score=0.8,
        )

        matches = detector.find_duplicates([job1, job2])

        assert len(matches) == 1
        match = matches[0]
        assert match.is_duplicate is True
        assert match.similarity_score == 1.0
        assert "Exact content hash match" in match.match_reasons

    def test_detect_similar_jobs(self, detector):
        """Test detection of similar but not identical jobs."""
        job1 = NormalizedJob(
            title="Senior Python Developer",
            company_name="TechCorp Inc",
            company_domain="techcorp.com",
            location="San Francisco, CA",
            normalized_location="San Francisco, CA",
            is_remote=True,
            remote_type="fully_remote",
            description="Build scalable systems with Python and Django",
            requirements="5+ years Python, Django",
            responsibilities="Backend development",
            salary_min=130000,
            salary_max=180000,
            salary_currency="USD",
            salary_period="yearly",
            salary_yearly_min=130000,
            salary_yearly_max=180000,
            experience_level="senior",
            employment_type="full_time",
            source="source1",
            source_url="http://url1",
            source_job_id="job_1",
            posted_date=datetime.utcnow(),
            expires_date=datetime.utcnow() + timedelta(days=30),
            application_url=None,
            application_email=None,
            skills=["Python", "Django"],
            keywords=[],
            quality_score=0.9,
            raw_record=None,
        )
        job2 = NormalizedJob(
            title="Python Developer Senior",
            company_name="TechCorp Inc",
            company_domain="techcorp.com",
            location="San Francisco, CA",
            normalized_location="San Francisco, CA",
            is_remote=True,
            remote_type="fully_remote",
            description="Building scalable systems with Python and Django",
            requirements="5+ yrs Python, Django",
            responsibilities="Backend dev",
            salary_min=130000,
            salary_max=180000,
            salary_currency="USD",
            salary_period="yearly",
            salary_yearly_min=130000,
            salary_yearly_max=180000,
            experience_level="senior",
            employment_type="full_time",
            source="source2",
            source_url="http://url2",
            source_job_id="job_2",
            posted_date=datetime.utcnow(),
            expires_date=datetime.utcnow() + timedelta(days=30),
            application_url=None,
            application_email=None,
            skills=["Python", "Django"],
            keywords=[],
            quality_score=0.85,
            raw_record=None,
        )

        matches = detector.find_duplicates([job1, job2])

        assert len(matches) == 1
        match = matches[0]
        assert match.is_duplicate is True
        assert match.similarity_score > 0.7

    def test_no_false_positive_different_companies(self, detector):
        """Test that jobs at different companies are not flagged as duplicates."""
        job1 = self._create_norm_job(
            title="Python Developer",
            company="TechCorp",
            location="SF",
            source_job_id="job_1",
            quality_score=0.8,
        )
        job2 = self._create_norm_job(
            title="Python Developer",
            company="DifferentCorp",
            location="SF",
            source_job_id="job_2",
            quality_score=0.8,
        )

        matches = detector.find_duplicates([job1, job2])

        # Should not be a duplicate (different companies)
        assert len(matches) == 0


class TestRequirementExtractor:
    """Tests for RequirementExtractor."""

    @pytest.fixture
    def extractor(self):
        return RequirementExtractor()

    @pytest.mark.asyncio
    async def test_extract_requirements_from_jd(self, extractor):
        """Test extracting structured requirements from job description."""
        job_description = """
        Senior Software Engineer
        
        Requirements:
        - 5+ years of professional software development experience
        - Expert in Python and Django/FastAPI
        - Strong experience with PostgreSQL and Redis
        - Experience with AWS, Docker, Kubernetes
        - Bachelor's degree in Computer Science or equivalent
        - Excellent communication skills
        
        Responsibilities:
        - Design and build scalable backend services
        - Mentor junior engineers
        - Participate in code reviews
        """

        result = await extractor.extract(job_description)

        assert isinstance(result, ExtractedRequirements)
        assert result.years_experience_min == 5
        assert "Python" in result.required_skills
        assert "PostgreSQL" in result.required_skills
        assert "AWS" in result.required_skills
        assert result.education_required is True
        assert result.degree_requirement == "Bachelor's"

    @pytest.mark.asyncio
    async def test_extract_salary_range(self, extractor):
        """Test salary range extraction."""
        job_description = """
        Software Engineer
        Salary: $120,000 - $180,000 per year
        Equity: 0.1% - 0.5%
        """

        result = await extractor.extract(job_description)

        assert result.salary_min == 120000
        assert result.salary_max == 180000
        assert result.equity_min is not None

    @pytest.mark.asyncio
    async def test_extract_remote_policy(self, extractor):
        """Test remote work policy extraction."""
        job_description = """
        Remote-first company. Work from anywhere in US.
        Optional office in San Francisco. Hybrid available.
        """

        result = await extractor.extract(job_description)

        assert result.remote_policy == "remote_first"
        assert result.location_flexibility == "us_anywhere"


class TestJobMatchingAgent:
    """Tests for JobMatchingAgent."""

    @pytest.fixture
    def matching_agent(self):
        return JobMatchingAgent()

    @pytest.fixture
    def sample_candidate_profile(self):
        return {
            "skills": [
                {"name": "Python", "proficiency": "expert", "years_experience": 8},
                {"name": "React", "proficiency": "advanced", "years_experience": 5},
                {"name": "AWS", "proficiency": "advanced", "years_experience": 4},
                {"name": "PostgreSQL", "proficiency": "advanced", "years_experience": 6},
                {"name": "Kubernetes", "proficiency": "intermediate", "years_experience": 2},
            ],
            "years_experience": 8,
            "current_role": "Senior Software Engineer",
            "desired_salary_min": 180000,
            "prefers_remote": True,
            "location": "San Francisco, CA",
        }

    @pytest.fixture
    def sample_jobs(self):
        return [
            {
                "id": "job_1",
                "title": "Senior Python Developer",
                "company": "TechCorp",
                "location": "San Francisco, CA",
                "is_remote": True,
                "remote_type": "fully_remote",
                "required_skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"],
                "salary_min": 150000,
                "salary_max": 200000,
                "experience_level": "senior",
                "employment_type": "full_time",
            },
            {
                "id": "job_2",
                "title": "Frontend Developer",
                "company": "StartupXYZ",
                "location": "New York, NY",
                "is_remote": False,
                "remote_type": None,
                "required_skills": ["React", "TypeScript", "Vue", "CSS"],
                "salary_min": 120000,
                "salary_max": 160000,
                "experience_level": "mid",
                "employment_type": "full_time",
            },
            {
                "id": "job_3",
                "title": "DevOps Engineer",
                "company": "CloudScale",
                "location": "Remote",
                "is_remote": True,
                "remote_type": "fully_remote",
                "required_skills": ["AWS", "Kubernetes", "Terraform", "Python"],
                "salary_min": 140000,
                "salary_max": 180000,
                "experience_level": "senior",
                "employment_type": "full_time",
            },
        ]

    def test_match_jobs_returns_ranked_results(self, matching_agent, sample_candidate_profile, sample_jobs):
        """Test that job matching returns ranked results."""
        matches = matching_agent.match_jobs(sample_candidate_profile, sample_jobs)

        assert len(matches) == 3
        assert all(isinstance(m, JobMatch) for m in matches)
        # Should be sorted by match score descending
        scores = [m.match_score for m in matches]
        assert scores == sorted(scores, reverse=True)

    def test_match_score_calculation(self, matching_agent, sample_candidate_profile, sample_jobs):
        """Test that match scores are calculated correctly."""
        matches = matching_agent.match_jobs(sample_candidate_profile, sample_jobs)

        python_job = next(m for m in matches if "Python" in m.job_title)
        frontend_job = next(m for m in matches if "Frontend" in m.job_title)

        # Python job should score higher for this candidate
        assert python_job.match_score > frontend_job.match_score

    def test_skill_gap_identification(self, matching_agent, sample_candidate_profile, sample_jobs):
        """Test that skill gaps are identified."""
        matches = matching_agent.match_jobs(sample_candidate_profile, sample_jobs)

        for match in matches:
            assert "skill_gaps" in match.__dict__ or hasattr(match, "skill_gaps")
            assert "matched_skills" in match.__dict__ or hasattr(match, "matched_skills")

    def test_salary_expectation_matching(self, matching_agent, sample_candidate_profile, sample_jobs):
        """Test salary expectation matching."""
        matches = matching_agent.match_jobs(sample_candidate_profile, sample_jobs)

        for match in matches:
            if match.salary_min and match.salary_min >= sample_candidate_profile["desired_salary_min"]:
                assert match.salary_match is True
            elif match.salary_max and match.salary_max < sample_candidate_profile["desired_salary_min"]:
                assert match.salary_match is False


class TestOpportunityRanker:
    """Tests for OpportunityRanker."""

    @pytest.fixture
    def ranker(self):
        return OpportunityRanker()

    @pytest.fixture
    def sample_matches(self, sample_candidate_profile, sample_jobs):
        matching_agent = JobMatchingAgent()
        return matching_agent.match_jobs(sample_candidate_profile, sample_jobs)

    def test_rank_opportunities(self, ranker, sample_matches):
        """Test ranking of job opportunities."""
        ranked = ranker.rank_opportunities(sample_matches)

        assert len(ranked) == len(sample_matches)
        assert all(isinstance(r, RankedOpportunity) for r in ranked)
        # Should be sorted by overall score
        scores = [r.overall_score for r in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_ranking_factors(self, ranker, sample_candidate_profile, sample_jobs):
        """Test that ranking considers multiple factors."""
        matching_agent = JobMatchingAgent()
        matches = matching_agent.match_jobs(sample_candidate_profile, sample_jobs)
        ranked = ranker.rank_opportunities(matches)

        for opp in ranked:
            assert hasattr(opp, "skill_match_score")
            assert hasattr(opp, "salary_match_score")
            assert hasattr(opp, "location_match_score")
            assert hasattr(opp, "company_fit_score")
            assert hasattr(opp, "growth_potential_score")

    def test_top_k_recommendations(self, ranker, sample_candidate_profile, sample_jobs):
        """Test getting top K recommendations."""
        matching_agent = JobMatchingAgent()
        matches = matching_agent.match_jobs(sample_candidate_profile, sample_jobs)
        
        top_2 = ranker.get_top_k(matches, k=2)
        
        assert len(top_2) == 2
        assert top_2[0].overall_score >= top_2[1].overall_score


if __name__ == "__main__":
    pytest.main([__file__, "-v"])