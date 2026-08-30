"""Integration tests for Evaluation API endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestEvaluationAPI:
    """Tests for evaluation endpoints."""

    def test_list_benchmarks(self, client: TestClient, auth_headers):
        """Test listing benchmark test cases."""
        response = client.get("/evaluation/benchmarks", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)
        assert len(result) > 0
        for benchmark in result:
            assert "test_case_id" in benchmark
            assert "name" in benchmark
            assert "description" in benchmark
            assert "level" in benchmark
            assert "tags" in benchmark

    def test_list_benchmarks_by_category(self, client: TestClient, auth_headers):
        """Test listing benchmarks filtered by category."""
        response = client.get(
            "/evaluation/benchmarks",
            params={"category": "research"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        result = response.json()
        assert all(b["test_case_id"].startswith("research_") for b in result)

    def test_list_benchmark_categories(self, client: TestClient, auth_headers):
        """Test listing benchmark categories and evaluators."""
        response = client.get("/evaluation/benchmarks/categories", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert "categories" in result
        assert "evaluators_per_category" in result
        assert "research" in result["categories"]
        assert "rag" in result["categories"]
        assert "job_matching" in result["categories"]
        assert "resume" in result["categories"]

    def test_list_evaluators(self, client: TestClient, auth_headers):
        """Test listing available evaluators."""
        response = client.get("/evaluation/evaluators", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert "evaluators" in result
        assert "descriptions" in result
        assert "research_quality" in result["evaluators"]
        assert "rag_generation" in result["evaluators"]
        assert "job_matching" in result["evaluators"]
        assert "resume_parsing" in result["evaluators"]

    def test_run_evaluation(self, client: TestClient, auth_headers):
        """Test running evaluation on benchmarks."""
        response = client.post(
            "/evaluation/run",
            json={
                "category": "research",
                "mock_outputs": True,
            },
            headers=auth_headers,
        )

        assert response.status_code == 202
        result = response.json()
        assert "suite_name" in result
        assert "total_test_cases" in result
        assert "passed" in result
        assert "failed" in result
        assert "pass_rate" in result
        assert "avg_score" in result
        assert "metrics_summary" in result
        assert "detailed_results" in result

    def test_run_evaluation_specific_evaluators(self, client: TestClient, auth_headers):
        """Test running evaluation with specific evaluators."""
        response = client.post(
            "/evaluation/run",
            json={
                "category": "rag",
                "evaluators": ["rag_generation"],
                "mock_outputs": True,
            },
            headers=auth_headers,
        )

        assert response.status_code == 202
        result = response.json()
        assert result["total_test_cases"] > 0

    def test_run_evaluation_invalid_category(self, client: TestClient, auth_headers):
        """Test running evaluation with invalid category."""
        response = client.post(
            "/evaluation/run",
            json={
                "category": "invalid_category",
                "mock_outputs": True,
            },
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "invalid category" in response.json()["detail"].lower()

    def test_run_evaluation_async(self, client: TestClient, auth_headers):
        """Test running evaluation asynchronously."""
        response = client.post(
            "/evaluation/run/async",
            json={
                "category": "research",
                "mock_outputs": True,
            },
            headers=auth_headers,
        )

        assert response.status_code == 202
        result = response.json()
        assert "task_id" in result
        assert result["status"] == "queued"

    def test_get_evaluation_task_status(self, client: TestClient, auth_headers):
        """Test getting async evaluation task status."""
        # First start an async evaluation
        response = client.post(
            "/evaluation/run/async",
            json={"category": "research", "mock_outputs": True},
            headers=auth_headers,
        )
        task_id = response.json()["task_id"]

        # Check status
        response = client.get(f"/evaluation/tasks/{task_id}", headers=auth_headers)
        assert response.status_code == 200
        result = response.json()
        assert "task_id" in result
        assert "status" in result

    def test_run_custom_evaluation(self, client: TestClient, auth_headers):
        """Test running evaluation on custom test cases."""
        response = client.post(
            "/evaluation/custom",
            json={
                "test_cases": [
                    {
                        "test_case_id": "custom_001",
                        "name": "Custom Test",
                        "description": "A custom test case",
                        "level": "component",
                        "input_data": {"query": "Test query"},
                        "expected_output": {"answer": "Expected answer"},
                        "tags": ["custom"],
                    }
                ],
                "evaluators": ["answer_relevance"],
                "actual_outputs": {
                    "custom_001": {
                        "generated_answer": "This is a test answer that addresses the query.",
                        "retrieved_documents": [{"id": "doc1", "content": "Test content"}],
                    }
                },
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        result = response.json()
        assert "suite_name" in result
        assert result["total_test_cases"] == 1

    def test_get_evaluation_history(self, client: TestClient, auth_headers):
        """Test getting evaluation history."""
        response = client.get("/evaluation/history", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert "history" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])