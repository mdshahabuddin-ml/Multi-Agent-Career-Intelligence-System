import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.database import get_db, Base
from backend.models import User, Research, ResearchStatus, ResearchType
from backend.services.research_service import ResearchService
from backend.api.auth import create_access_token


# NOTE: These fixtures intentionally use an isolated in-memory database.
# A previous revision bound them to the real dev engine (backend.database
# engine + drop_all), which wiped the developer database on every run.
# Never point test fixtures at the real engine.
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

_test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_testing_mode():
    """Ensure testing mode stays enabled for security middleware.

    Root conftest already enables TESTING at import; this guard only
    re-asserts it and deliberately does NOT disable it on teardown, so
    later test modules are never affected.
    """
    from backend.security.config import security_config
    security_config.TESTING = True
    yield
    security_config.TESTING = True


@pytest.fixture(scope="session")
def db_engine():
    Base.metadata.create_all(bind=_test_engine)
    yield _test_engine
    Base.metadata.drop_all(bind=_test_engine)


@pytest.fixture
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = _TestSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    """Create a TestClient with overridden database dependency."""
    from fastapi.testclient import TestClient
    from backend.main import app
    from backend.database import get_db
    
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def test_organization(db_session):
    """Create a test organization with quotas."""
    from backend.models.organization import Organization, OrganizationPlan
    import uuid
    org = Organization(
        name="Test Organization",
        slug=f"test-org-{uuid.uuid4().hex[:8]}",
        plan=OrganizationPlan.PROFESSIONAL,
        max_members=50,
        max_jobs_per_month=1000,
        max_research_per_month=500,
        max_api_calls_per_month=100000,
    )
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org


@pytest.fixture
def test_user(db_session, test_organization, request):
    # Use test name to generate unique email
    test_name = request.node.name
    email = f"test_{test_name}@example.com"
    user = User(
        email=email,
        hashed_password="hashed_password",
        is_active=True,
        organization_id=test_organization.id,  # Assign to org for quota checks
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    token = create_access_token(data={"sub": test_user.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_search_provider():
    with patch("backend.agents.research.research_supervisor.get_search_registry") as mock_registry:
        mock_provider = AsyncMock()
        mock_provider.search.return_value = [
            MagicMock(
                url="https://example.com/job-trends",
                title="AI Engineering Job Trends 2024",
                snippet="AI engineering jobs are growing rapidly with high demand for ML skills.",
                source_type="web",
                published_date=datetime.utcnow().isoformat(),
                credibility=0.8,
                relevance=0.9,
            ),
            MagicMock(
                url="https://news.example.com/ai-hiring",
                title="Tech Companies Hiring AI Engineers",
                snippet="Major tech companies increasing AI engineering headcount.",
                source_type="news",
                published_date=datetime.utcnow().isoformat(),
                credibility=0.85,
                relevance=0.8,
            ),
        ]
        mock_registry.return_value.list_providers.return_value = ["mock"]
        mock_registry.return_value.get_provider_class.return_value = lambda: mock_provider
        yield mock_provider


class TestResearchAPI:
    """Integration tests for research API endpoints."""

    def test_create_research(self, client, auth_headers, mock_search_provider):
        """Test creating a new research task."""
        response = client.post(
            "/api/research",
            json={
                "query": "AI engineering job trends 2024",
                "research_type": "job_market",
                "target_role": "AI Engineer",
                "max_sources": 10,
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["query"] == "AI engineering job trends 2024"
        assert data["research_type"] == "job_market"
        assert data["status"] == "created"
        assert data["progress"] == 0
        assert "id" in data

    def test_list_research(self, client, auth_headers, test_user):
        """Test listing user's research tasks."""
        from backend.database import get_db
        session = next(iter(client.app.dependency_overrides[get_db]()))
        for i in range(3):
            research = Research(
                user_id=test_user.id,
                query=f"Test query {i}",
                research_type=ResearchType.GENERAL,
                status=ResearchStatus.COMPLETED if i < 2 else ResearchStatus.RESEARCHING,
            )
            session.add(research)
        session.commit()

        response = client.get("/api/research", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3
        assert data["page"] == 1
        assert data["page_size"] == 20

    def test_list_research_with_status_filter(self, client, auth_headers, test_user):
        """Test listing research with status filter."""
        from backend.database import get_db
        session = next(iter(client.app.dependency_overrides[get_db]()))
        for status in [ResearchStatus.COMPLETED, ResearchStatus.RESEARCHING, ResearchStatus.FAILED]:
            research = Research(
                user_id=test_user.id,
                query=f"Test {status}",
                research_type=ResearchType.GENERAL,
                status=status,
            )
            session.add(research)
        session.commit()

        response = client.get("/api/research?status=completed", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "completed"

    def test_get_research_status(self, client, auth_headers, test_user):
        """Test getting research status."""
        from backend.database import get_db
        session = next(iter(client.app.dependency_overrides[get_db]()))
        research = Research(
            user_id=test_user.id,
            query="Test status",
            research_type=ResearchType.JOB_MARKET,
            status=ResearchStatus.RESEARCHING,
            progress=45,
            source_count=10,
            verified_claim_count=3,
            confidence_score=0.75,
        )
        session.add(research)
        session.commit()
        session.refresh(research)

        response = client.get(f"/api/research/{research.id}/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["research_id"] == research.id
        assert data["phase"] == "researching"
        assert data["progress"] == 45
        assert data["stats"]["source_count"] == 10
        assert data["stats"]["verified_claim_count"] == 3
        assert data["stats"]["confidence_score"] == 0.75

    def test_get_research_not_found(self, client, auth_headers):
        """Test getting non-existent research."""
        response = client.get("/api/research/99999/status", headers=auth_headers)
        assert response.status_code == 404

    def test_cancel_research(self, client, auth_headers, test_user):
        """Test cancelling a running research."""
        from backend.database import get_db
        session = next(iter(client.app.dependency_overrides[get_db]()))
        research = Research(
            user_id=test_user.id,
            query="Test cancel",
            research_type=ResearchType.GENERAL,
            status=ResearchStatus.RESEARCHING,
        )
        session.add(research)
        session.commit()
        session.refresh(research)

        response = client.delete(f"/api/research/{research.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Research cancelled"

        # Verify status updated
        session.refresh(research)
        assert research.status == ResearchStatus.FAILED
        assert research.error_message == "Cancelled by user"

    def test_cancel_completed_research_fails(self, client, auth_headers, test_user):
        """Test that cancelling completed research fails."""
        from backend.database import get_db
        session = next(iter(client.app.dependency_overrides[get_db]()))
        research = Research(
            user_id=test_user.id,
            query="Test cancel completed",
            research_type=ResearchType.GENERAL,
            status=ResearchStatus.COMPLETED,
        )
        session.add(research)
        session.commit()
        session.refresh(research)

        response = client.delete(f"/api/research/{research.id}", headers=auth_headers)
        assert response.status_code == 400

    def test_export_research_report_markdown(self, client, auth_headers, test_user):
        """Test exporting research report as markdown."""
        from backend.database import get_db
        session = next(iter(client.app.dependency_overrides[get_db]()))
        research = Research(
            user_id=test_user.id,
            query="Test export",
            research_type=ResearchType.JOB_MARKET,
            status=ResearchStatus.COMPLETED,
            executive_summary="Test summary",
            key_findings=["Finding 1", "Finding 2"],
            recommendations=["Rec 1", "Rec 2"],
            report='{"title": "Test Report", "executive_summary": "Test summary", "key_findings": ["Finding 1", "Finding 2"], "recommendations": ["Rec 1", "Rec 2"], "methodology": "Test methodology", "limitations": ["Limitation 1"], "sources": [], "citations": [], "confidence": 0.85}',
        )
        session.add(research)
        session.commit()
        session.refresh(research)

        response = client.post(
            f"/api/research/{research.id}/export",
            json={"format": "markdown"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/markdown")
        content = response.text
        assert "Test Report" in content
        assert "Test summary" in content
        assert "Finding 1" in content

    def test_export_research_html(self, client, auth_headers, test_user):
        """Test exporting research report as HTML."""
        from backend.database import get_db
        session = next(iter(client.app.dependency_overrides[get_db]()))
        research = Research(
            user_id=test_user.id,
            query="Test export HTML",
            research_type=ResearchType.JOB_MARKET,
            status=ResearchStatus.COMPLETED,
            report='{"title": "HTML Test", "executive_summary": "HTML summary", "key_findings": ["HTML finding"], "recommendations": ["HTML rec"], "methodology": "HTML methodology", "limitations": ["HTML limitation"], "sources": [], "citations": [], "confidence": 0.8}',
        )
        session.add(research)
        session.commit()
        session.refresh(research)

        response = client.post(
            f"/api/research/{research.id}/export",
            json={"format": "html"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        content = response.text
        assert "<html>" in content
        assert "HTML Test" in content

    def test_get_research_report(self, client, auth_headers, test_user):
        """Test getting full research report."""
        from backend.database import get_db
        session = next(iter(client.app.dependency_overrides[get_db]()))
        research = Research(
            user_id=test_user.id,
            query="Test report",
            research_type=ResearchType.COMPANY,
            status=ResearchStatus.COMPLETED,
            executive_summary="Report summary",
            key_findings=["Key finding 1", "Key finding 2"],
            recommendations=["Recommendation 1"],
            confidence_score=0.85,
            source_count=15,
            verified_claim_count=5,
        )
        session.add(research)
        session.commit()
        session.refresh(research)

        response = client.get(f"/api/research/{research.id}/report", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == research.id
        assert data["query"] == "Test report"
        assert data["executive_summary"] == "Report summary"
        assert len(data["key_findings"]) == 2
        assert data["confidence_score"] == 0.85


class TestResearchService:
    """Tests for ResearchService."""

    @pytest.mark.asyncio
    async def test_start_research(self, db_session, test_user, mock_search_provider):
        """Test starting research via service."""
        service = ResearchService(db_session)
        research = await service.start_research(
            user_id=test_user.id,
            query="Test service research",
            research_type=ResearchType.TECHNOLOGY,
        )
        assert research.id is not None
        assert research.query == "Test service research"
        assert research.research_type == ResearchType.TECHNOLOGY
        assert research.status == ResearchStatus.CREATED

    @pytest.mark.asyncio
    async def test_research_progress_callback(self, db_session, test_user, mock_search_provider):
        """Test that progress callback is called."""
        service = ResearchService(db_session)
        progress_updates = []

        def callback(update):
            progress_updates.append(update)

        research = await service.start_research(
            user_id=test_user.id,
            query="Test progress",
            research_type=ResearchType.GENERAL,
            progress_callback=callback,
        )

        # Wait for background task to complete
        await asyncio.sleep(2)

        assert len(progress_updates) > 0
        assert progress_updates[0]["research_id"] == research.id


class TestResearchOrchestrator:
    """Tests for ResearchOrchestrator."""

    @pytest.mark.asyncio
    async def test_orchestrator_phases(self, db_session, test_user, mock_search_provider):
        """Test that all pipeline phases execute."""
        from backend.agents.research import ResearchOrchestrator

        orchestrator = ResearchOrchestrator(use_llm=False)
        research = Research(
            id=1,
            user_id=test_user.id,
            query="Test orchestrator",
            research_type=ResearchType.GENERAL,
            status=ResearchStatus.CREATED,
        )
        db_session.add(research)
        db_session.commit()

        state = await orchestrator.execute_pipeline(research, db_session)

        assert state.phase.value == "completed"
        assert state.progress == 100
        assert state.decomposition is not None
        assert len(state.decomposition.subtasks) > 0
        assert state.source_collection is not None
        assert len(state.claims) > 0
        assert len(state.evidence) > 0
        assert len(state.verification_results) > 0
        assert state.analysis_result is not None
        assert state.synthesis_result is not None
        assert state.confidence_result is not None
        assert state.report is not None


class TestErrorHandling:
    """Tests for error handling in research pipeline."""

    @pytest.mark.asyncio
    async def test_network_error_recovery(self, db_session, test_user):
        """Test recovery from network errors."""
        from backend.agents.research.error_handling import ErrorHandler, NetworkError, ErrorSeverity

        handler = ErrorHandler(max_retries=3, retry_delay=0.01)

        async def failing_operation():
            raise NetworkError("Connection timeout", severity=ErrorSeverity.MEDIUM)

        from backend.agents.research.pipeline_base import PipelineState
        from backend.agents.research import PipelinePhase

        state = PipelineState(research_id=1, query="test", research_type=ResearchType.GENERAL)
        context = handler._create_context(state, "TEST_PHASE")

        result = await handler.handle_error(NetworkError("timeout"), context)
        assert result["action"] == "retry"

    @pytest.mark.asyncio
    async def test_circuit_breaker(self, db_session):
        """Test circuit breaker prevents cascade failures."""
        from backend.agents.research.error_handling import CircuitBreaker, PipelineError, ErrorCategory, ErrorSeverity

        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1)

        async def failing_call():
            raise PipelineError("Service unavailable", category=ErrorCategory.NETWORK, severity=ErrorSeverity.HIGH)

        # First 3 calls should fail and open circuit
        for i in range(3):
            try:
                await cb.acall(failing_call)
            except PipelineError:
                pass

        assert cb.state == "open"

        # Next call should fail immediately due to open circuit
        with pytest.raises(PipelineError, match="Circuit breaker is open"):
            await cb.acall(failing_call)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])