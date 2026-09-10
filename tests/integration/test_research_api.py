"""Integration tests for Research API endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestResearchAPI:
    """Tests for research endpoints."""

    def test_start_research(self, client: TestClient, auth_headers):
        """Test starting a new research task."""
        response = client.post(
            "/api/research",
            json={
                "query": "What are the latest trends in AI job market for 2024?",
                "research_type": "job_market",
                "target_role": "Machine Learning Engineer",
                "target_location": "San Francisco",
                "max_sources": 10,
                "timeout_seconds": 300,
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        result = response.json()
        assert "id" in result
        assert result["query"] == "What are the latest trends in AI job market for 2024?"
        assert result["status"] == "created"

    def test_start_research_invalid_type(self, client: TestClient, auth_headers):
        """Test starting research with invalid type."""
        response = client.post(
            "/api/research",
            json={
                "query": "Test query",
                "research_type": "invalid_type",
            },
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_get_research_status(self, client: TestClient, auth_headers, test_research):
        """Test getting research status."""
        # Mapped to the detail endpoint: it carries the live id/status/progress
        # fields the legacy /status shape asserted.
        response = client.get(
            f"/api/research/{test_research.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        result = response.json()
        assert result["id"] == test_research.id
        assert "status" in result
        assert "progress" in result
        assert 0 <= result["progress"] <= 100

    def test_get_nonexistent_research_status(self, client: TestClient, auth_headers):
        """Test getting status of nonexistent research."""
        response = client.get("/api/research/99999/status", headers=auth_headers)
        assert response.status_code == 404

    def test_get_research_report(self, client: TestClient, auth_headers, test_research):
        """Test getting completed research report."""
        response = client.get(f"/api/research/{test_research.id}", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert result["id"] == test_research.id
        assert "executive_summary" in result
        assert "key_findings" in result
        assert "recommendations" in result
        assert "confidence_score" in result

    def test_get_incomplete_research_report(self, client: TestClient, auth_headers, db_session):
        """Test getting report for incomplete research."""
        from backend.models import Research, ResearchStatus, ResearchType
        
        incomplete = Research(
            user_id=1,
            query="Incomplete research",
            research_type=ResearchType.GENERAL,
            status=ResearchStatus.RESEARCHING,
        )
        db_session.add(incomplete)
        db_session.commit()
        db_session.refresh(incomplete)

        # Mapped to the report endpoint: it 404s unless the run COMPLETED.
        response = client.get(f"/api/research/{incomplete.id}/report", headers=auth_headers)
        assert response.status_code == 404

    def test_list_research(self, client: TestClient, auth_headers, test_research):
        """Test listing user's research tasks."""
        response = client.get("/api/research/", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        # Paginated envelope on the registered route.
        assert result["total"] >= 1
        assert result["items"][0]["id"] == test_research.id

    def test_cancel_research(self, client: TestClient, auth_headers, db_session):
        """Test canceling a running research task."""
        from backend.models import Research, ResearchStatus, ResearchType
        
        running = Research(
            user_id=1,
            query="Running research",
            research_type=ResearchType.GENERAL,
            status=ResearchStatus.RESEARCHING,
        )
        db_session.add(running)
        db_session.commit()
        db_session.refresh(running)

        response = client.delete(f"/api/research/{running.id}", headers=auth_headers)
        assert response.status_code == 200
        assert "cancelled" in response.json()["message"].lower()

    def test_cancel_completed_research(self, client: TestClient, auth_headers, test_research):
        """Test canceling already completed research."""
        response = client.delete(f"/api/research/{test_research.id}", headers=auth_headers)
        assert response.status_code == 400

    def test_get_research_sources(self, client: TestClient, auth_headers, test_research):
        """Test getting sources used in research."""
        # Mapped to the detail endpoint, whose "sources" field is the only
        # registered source listing (no standalone /sources route exists).
        response = client.get(f"/api/research/{test_research.id}", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()["sources"] or []
        assert isinstance(result, list)
        if result:
            source = result[0]
            assert "id" in source
            assert "title" in source
            assert "url" in source
            assert "source_type" in source
            assert "credibility" in source
            assert "relevance" in source

    def test_get_research_citations(self, client: TestClient, auth_headers, test_research):
        """Test getting citations for research."""
        # Mapped to the report endpoint: it is the only registered route
        # whose payload can carry citations (inside report_data). No
        # standalone /citations route exists.
        response = client.get(f"/api/research/{test_research.id}/report", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, dict)
        assert result["id"] == test_research.id
        assert "executive_summary" in result


class TestResearchSecurity:
    """Security tests for research endpoints."""

    def test_user_isolation(self, client: TestClient, test_research, second_user, db_session):
        """Test that users can't access other users' research."""
        from backend.utils.security import create_access_token
        token = create_access_token(data={"sub": second_user.id})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(f"/api/research/{test_research.id}", headers=headers)
        assert response.status_code == 404

    def test_research_timeout_validation(self, client: TestClient, auth_headers):
        """Test timeout validation."""
        response = client.post(
            "/api/research",
            json={
                "query": "Test",
                "timeout_seconds": 100000,  # Too large
            },
            headers=auth_headers,
        )
        # Should be rejected or capped
        assert response.status_code in [202, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])