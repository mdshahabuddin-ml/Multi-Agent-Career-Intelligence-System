"""Unit tests for Research Intelligence agents."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from backend.agents.research.research_supervisor import (
    ResearchSupervisor, ResearchPlanner, ResearchAgent,
    WebResearcher, NewsResearcher, JobMarketResearcher, CompanyResearcher, AcademicResearcher,
    ResearchTask, ResearchPlan, ResearchPhase
)
from backend.agents.research.evidence_agent import EvidenceAgent, Evidence
from backend.agents.research.verification_agent import VerificationAgent, VerificationResult
from backend.agents.research.analysis_agent import AnalysisAgent, AnalysisResult
from backend.agents.research.synthesis_agent import SynthesisAgent, SynthesisResult
from backend.agents.research.report_agent import ReportAgent, ResearchReport


class TestResearchSupervisor:
    """Tests for ResearchSupervisor orchestration."""

    @pytest.fixture
    def supervisor(self):
        return ResearchSupervisor()

    @pytest.fixture
    def mock_research(self):
        research = MagicMock()
        research.id = 1
        research.query = "AI job market trends 2024"
        research.research_type = "job_market"
        research.target_role = "Machine Learning Engineer"
        research.target_company = None
        research.target_location = "San Francisco"
        research.max_sources = 10
        research.timeout_seconds = 300
        research.status = "created"
        research.research_plan = None
        research.sources = []
        research.source_count = 0
        return research

    @pytest.mark.asyncio
    async def test_execute_research_creates_plan(self, supervisor, mock_research):
        """Test that research execution creates a plan."""
        mock_db = MagicMock()

        with patch.object(supervisor.planner, 'create_plan', new_callable=AsyncMock) as mock_create_plan:
            mock_plan = ResearchPlan(
                research_id=1,
                query="AI job market trends 2024",
                research_type="job_market",
                tasks=[
                    ResearchTask(
                        id="task_1_0",
                        description="Analyze job market trends",
                        agent_type="job_market",
                        query="AI job market trends 2024 job market trends 2024",
                        priority=1,
                    ),
                ],
            )
            mock_create_plan.return_value = mock_plan

            with patch.object(supervisor.agents["job_market"], 'execute', new_callable=AsyncMock) as mock_execute:
                mock_execute.return_value = {
                    "agent": "job_market_researcher",
                    "sources": [{"title": "AI Job Report", "url": "https://example.com", "source_type": "job_market"}],
                }

                result = await supervisor.execute_research(mock_research, mock_db)

        assert result.research_plan is not None
        assert len(result.research_plan["tasks"]) > 0
        assert result.source_count >= 0

    @pytest.mark.asyncio
    async def test_execute_research_handles_agent_failure(self, supervisor, mock_research):
        """Test handling of agent execution failures."""
        mock_db = MagicMock()

        with patch.object(supervisor.planner, 'create_plan', new_callable=AsyncMock) as mock_create_plan:
            mock_plan = ResearchPlan(
                research_id=1,
                query="Test query",
                research_type="general",
                tasks=[
                    ResearchTask(
                        id="task_1",
                        description="Test task",
                        agent_type="nonexistent",
                        query="test",
                        priority=1,
                    ),
                ],
            )
            mock_create_plan.return_value = mock_plan

            result = await supervisor.execute_research(mock_research, mock_db)

        # Should handle missing agent gracefully
        assert result.status in ["collecting_evidence", "failed"]


class TestResearchPlanner:
    """Tests for ResearchPlanner."""

    @pytest.fixture
    def planner(self):
        return ResearchPlanner()

    @pytest.mark.asyncio
    async def test_create_plan_job_market(self, planner):
        """Test plan creation for job market research."""
        plan = await planner.create_plan(
            research_id=1,
            query="Python developer job market",
            research_type="job_market",
            target_role="Python Developer",
            target_location="San Francisco",
        )

        assert isinstance(plan, ResearchPlan)
        assert len(plan.tasks) >= 3
        agent_types = [t.agent_type for t in plan.tasks]
        assert "job_market" in agent_types
        assert "web" in agent_types
        assert "news" in agent_types

    @pytest.mark.asyncio
    async def test_create_plan_company_research(self, planner):
        """Test plan creation for company research."""
        plan = await planner.create_plan(
            research_id=2,
            query="Google company culture",
            research_type="company",
            target_company="Google",
        )

        assert isinstance(plan, ResearchPlan)
        agent_types = [t.agent_type for t in plan.tasks]
        assert "company" in agent_types
        assert "web" in agent_types

    @pytest.mark.asyncio
    async def test_create_plan_technology_research(self, planner):
        """Test plan creation for technology research."""
        plan = await planner.create_plan(
            research_id=3,
            query="Kubernetes trends 2024",
            research_type="technology",
        )

        agent_types = [t.agent_type for t in plan.tasks]
        assert "web" in agent_types
        assert "academic" in agent_types
        assert "news" in agent_types


class TestResearchAgents:
    """Tests for individual research agents."""

    @pytest.fixture
    def web_researcher(self):
        return WebResearcher()

    @pytest.fixture
    def news_researcher(self):
        return NewsResearcher()

    @pytest.fixture
    def job_market_researcher(self):
        return JobMarketResearcher()

    @pytest.fixture
    def company_researcher(self):
        return CompanyResearcher()

    @pytest.fixture
    def academic_researcher(self):
        return AcademicResearcher()

    @pytest.mark.asyncio
    async def test_web_researcher_returns_sources(self, web_researcher):
        """Test web researcher returns structured sources."""
        task = ResearchTask(
            id="test_1",
            description="Test web search",
            agent_type="web",
            query="Python job market",
            priority=1,
        )

        result = await web_researcher.execute(task)

        assert "sources" in result
        assert len(result["sources"]) > 0
        source = result["sources"][0]
        assert "title" in source
        assert "url" in source
        assert "snippet" in source
        assert "source_type" in source
        assert source["source_type"] == "web"
        assert "credibility" in source
        assert "relevance" in source

    @pytest.mark.asyncio
    async def test_news_researcher_includes_date(self, news_researcher):
        """Test news researcher includes publication date."""
        task = ResearchTask(
            id="test_2",
            description="Test news search",
            agent_type="news",
            query="AI hiring news",
            priority=1,
        )

        result = await news_researcher.execute(task)

        source = result["sources"][0]
        assert "published_date" in source
        assert source["source_type"] == "news"

    @pytest.mark.asyncio
    async def test_job_market_researcher_high_credibility(self, job_market_researcher):
        """Test job market researcher returns high credibility sources."""
        task = ResearchTask(
            id="test_3",
            description="Test job market search",
            agent_type="job_market",
            query="Software engineer salaries",
            priority=1,
        )

        result = await job_market_researcher.execute(task)

        source = result["sources"][0]
        assert source["credibility"] >= 0.8
        assert source["relevance"] >= 0.8
        assert source["source_type"] == "job_market"

    @pytest.mark.asyncio
    async def test_company_researcher_includes_culture(self, company_researcher):
        """Test company researcher includes culture info."""
        task = ResearchTask(
            id="test_4",
            description="Test company research",
            agent_type="company",
            query="Google culture",
            priority=1,
        )

        result = await company_researcher.execute(task)

        source = result["sources"][0]
        assert "culture" in source["snippet"].lower()
        assert source["source_type"] == "company"

    @pytest.mark.asyncio
    async def test_academic_researcher_includes_authors(self, academic_researcher):
        """Test academic researcher includes author information."""
        task = ResearchTask(
            id="test_5",
            description="Test academic search",
            agent_type="academic",
            query="Machine learning optimization",
            priority=1,
        )

        result = await academic_researcher.execute(task)

        source = result["sources"][0]
        assert "authors" in source
        assert len(source["authors"]) > 0
        assert source["source_type"] == "academic"
        assert source["credibility"] >= 0.9


class TestEvidenceAgent:
    """Tests for EvidenceAgent."""

    @pytest.fixture
    def evidence_agent(self):
        return EvidenceAgent()

    @pytest.mark.asyncio
    async def test_collect_evidence_for_claims(self, evidence_agent):
        """Test evidence collection for claims."""
        sources = [
            {"title": "AI Report 2024", "url": "https://example.com/1", "snippet": "AI jobs growing 40% YoY", "source_type": "job_market"},
            {"title": "Tech Salaries", "url": "https://example.com/2", "snippet": "ML engineers earn $150-250k", "source_type": "web"},
        ]
        claims = [
            "AI job market is growing rapidly",
            "Machine learning engineers command high salaries",
        ]

        evidence = await evidence_agent.collect_evidence(sources, claims)

        assert len(evidence) == len(claims)
        for e in evidence:
            assert isinstance(e, Evidence)
            assert e.claim_text in claims
            assert len(e.supporting_sources) > 0

    @pytest.mark.asyncio
    async def test_evidence_relevance_scoring(self, evidence_agent):
        """Test that evidence is relevance-scored."""
        sources = [
            {"title": "Report", "snippet": "Python is popular for AI", "source_type": "web"},
        ]
        claims = ["Python is widely used in AI development"]

        evidence = await evidence_agent.collect_evidence(sources, claims)

        assert evidence[0].relevance_score >= 0.0
        assert evidence[0].relevance_score <= 1.0


class TestVerificationAgent:
    """Tests for VerificationAgent."""

    @pytest.fixture
    def verification_agent(self):
        return VerificationAgent()

    @pytest.mark.asyncio
    async def test_verify_supported_claim(self, verification_agent):
        """Test verification of a well-supported claim."""
        claims = ["Python is the most popular language for machine learning"]
        evidence = [
            Evidence(
                claim_text="Python is the most popular language for machine learning",
                supporting_sources=[
                    {"title": "Stack Overflow Survey 2024", "snippet": "Python #1 for ML", "credibility": 0.9},
                    {"title": "Kaggle Survey", "snippet": "85% use Python for ML", "credibility": 0.85},
                ],
                relevance_score=0.95,
            ),
        ]

        results = await verification_agent.verify_claims(claims, evidence)

        assert len(results) == 1
        assert isinstance(results[0], VerificationResult)
        assert results[0].status in ["verified", "likely"]
        assert results[0].confidence >= 0.7

    @pytest.mark.asyncio
    async def test_verify_unsupported_claim(self, verification_agent):
        """Test verification of unsupported claim."""
        claims = ["COBOL is the most popular language for AI in 2024"]
        evidence = [
            Evidence(
                claim_text="COBOL is the most popular language for AI in 2024",
                supporting_sources=[],
                relevance_score=0.1,
            ),
        ]

        results = await verification_agent.verify_claims(claims, evidence)

        assert results[0].status in ["unverified", "contradicted"]
        assert results[0].confidence < 0.5


class TestAnalysisAgent:
    """Tests for AnalysisAgent."""

    @pytest.fixture
    def analysis_agent(self):
        return AnalysisAgent()

    @pytest.mark.asyncio
    async def test_analyze_identifies_themes(self, analysis_agent):
        """Test that analysis identifies key themes."""
        sources = [
            {"title": "Report 1", "snippet": "AI jobs growing rapidly", "source_type": "job_market"},
            {"title": "Report 2", "snippet": "Python dominate ML landscape", "source_type": "web"},
            {"title": "Report 3", "snippet": "Remote work standard for tech", "source_type": "news"},
        ]
        claims = ["AI jobs growing", "Python popular for ML", "Remote work common"]
        verification_results = [
            VerificationResult(claim_text=c, status="verified", confidence=0.9, supporting_evidence=[])
            for c in claims
        ]

        result = await analysis_agent.analyze(
            research_id=1,
            claims=[{"claim_text": c, "claim_id": f"claim_{i}"} for i, c in enumerate(claims)],
            evidence=[],
            verification_results=[v.__dict__ for v in verification_results],
            sources=sources,
        )

        assert isinstance(result, AnalysisResult)
        assert len(result.key_themes) > 0
        assert len(result.trends) > 0
        assert len(result.insights) > 0


class TestSynthesisAgent:
    """Tests for SynthesisAgent."""

    @pytest.fixture
    def synthesis_agent(self):
        return SynthesisAgent()

    @pytest.mark.asyncio
    async def test_synthesize_creates_report_structure(self, synthesis_agent):
        """Test synthesis creates structured report."""
        analysis_result = AnalysisResult(
            key_themes=["AI Growth", "Python Dominance", "Remote Work"],
            trends=[{"theme": "AI", "direction": "up", "magnitude": "high"}],
            insights=["AI job market expanding 40% YoY"],
            contradictions=[],
            confidence=0.88,
        )
        verification_results = []
        sources = [{"title": "Test", "url": "https://example.com"}]

        result = await synthesis_agent.synthesize(
            research_id=1,
            query="AI job market trends",
            research_type="job_market",
            analysis_result=analysis_result.__dict__,
            verification_results=verification_results,
            sources=sources,
        )

        assert isinstance(result, SynthesisResult)
        assert result.executive_summary is not None
        assert len(result.key_findings) > 0
        assert len(result.recommendations) > 0
        assert result.confidence >= 0.0


class TestReportAgent:
    """Tests for ReportAgent."""

    @pytest.fixture
    def report_agent(self):
        return ReportAgent()

    @pytest.mark.asyncio
    async def test_generate_report_formats(self, report_agent):
        """Test report generation in multiple formats."""
        synthesis_result = SynthesisResult(
            executive_summary="Test summary",
            key_findings=["Finding 1", "Finding 2"],
            recommendations=["Rec 1", "Rec 2"],
            confidence=0.85,
        )
        sources = [{"title": "Source 1", "url": "https://example.com"}]
        verification_results = []

        report = await report_agent.generate_report(
            research_id=1,
            query="Test query",
            research_type="general",
            synthesis_result=synthesis_result.__dict__,
            sources=sources,
            verification_results=verification_results,
        )

        assert isinstance(report, ResearchReport)
        assert report.markdown is not None
        assert "# " in report.markdown  # Has headers
        
        # Test format exports
        html = await report_agent.export_html(report)
        assert "<html>" in html.lower() or "<h1>" in html.lower()

        markdown = await report_agent.export_markdown(report)
        assert "# " in markdown


if __name__ == "__main__":
    pytest.main([__file__, "-v"])