"""Integration tests for Applications API endpoints."""

import pytest
from fastapi.testclient import TestClient
from io import BytesIO


class TestApplicationsAPI:
    """Tests for application endpoints."""

    def test_prepare_application(self, client: TestClient, auth_headers):
        """Test preparing complete application package."""
        response = client.post(
            "/applications/prepare",
            json={
                "job_id": 1,
                "resume_text": "John Doe\nSenior Software Engineer\n\nEXPERIENCE\nSenior Engineer at TechCorp (2020-Present)\n- Led team of 5 engineers\n- Reduced deployment time by 80%\n\nSKILLS\nPython, React, AWS, Kubernetes",
                "candidate_profile": {
                    "name": "John Doe",
                    "email": "john.doe@email.com",
                    "phone": "(555) 123-4567",
                    "location": "San Francisco, CA",
                    "linkedin_url": "https://linkedin.com/in/johndoe",
                    "years_experience": 8,
                    "current_role": "Senior Software Engineer",
                    "key_skills": ["Python", "React", "AWS", "Kubernetes"],
                    "achievements": [
                        "Reduced deployment time by 80%",
                        "Led team of 5 engineers",
                    ],
                },
                "job_description": "We need a Senior Software Engineer with Python, React, AWS, Kubernetes...",
                "cover_letter_tone": "professional",
                "cover_letter_length": "medium",
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        result = response.json()
        assert "application_id" in result
        assert "resume_ats_result" in result
        assert "resume_review_result" in result
        assert "cover_letter_result" in result
        assert "ready_to_submit" in result
        assert "checklist" in result
        assert "next_steps" in result

    def test_ats_analysis_endpoint(self, client: TestClient, auth_headers):
        """Test standalone ATS analysis."""
        response = client.post(
            "/applications/ats/analyze",
            json={
                "resume_text": "John Doe\nSenior Software Engineer\n\nEXPERIENCE\nSenior Engineer at TechCorp (2020-Present)\n- Led team of 5 engineers\n- Reduced deployment time by 80%\n\nSKILLS\nPython, React, AWS, Kubernetes, Go, PostgreSQL",
                "target_role": "Senior Software Engineer",
                "job_description": "Looking for Python, React, AWS, Kubernetes experience",
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        result = response.json()
        assert "overall_score" in result
        assert "passed" in result
        assert "issues" in result
        assert "recommendations" in result

    def test_resume_review_endpoint(self, client: TestClient, auth_headers):
        """Test standalone resume review."""
        response = client.post(
            "/applications/resume/review",
            json={
                "resume_text": "John Doe\nSenior Software Engineer\n\nEXPERIENCE\nSenior Engineer at TechCorp (2020-Present)\n- Led team of 5 engineers\n- Reduced deployment time by 80%\n\nSKILLS\nPython, React, AWS, Kubernetes, Go, PostgreSQL",
                "target_role": "Senior Software Engineer",
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        result = response.json()
        assert "overall_score" in result
        assert "grade" in result
        assert "section_reviews" in result
        assert "top_priorities" in result

    def test_resume_optimize_endpoint(self, client: TestClient, auth_headers):
        """Test resume optimization suggestions."""
        response = client.post(
            "/applications/resume/optimize",
            json={
                "resume_text": "John Doe\nSoftware Engineer\n\nSKILLS\nPython, React",
                "target_role": "Senior Software Engineer",
                "job_description": "Need Python, React, AWS, Kubernetes, Docker, CI/CD",
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        result = response.json()
        assert "ats_score" in result
        assert "review_score" in result
        assert "missing_keywords" in result
        assert "recommendations" in result
        assert "improvement_plan" in result

    def test_cover_letter_generation(self, client: TestClient, auth_headers):
        """Test cover letter generation."""
        response = client.post(
            "/applications/cover-letter",
            json={
                "target_role": "Senior Software Engineer",
                "target_company": "Google",
                "job_description": "We need a Senior Software Engineer with Python, React, AWS, Kubernetes...",
                "hiring_manager": "Jane Smith",
                "tone": "professional",
                "length": "medium",
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        result = response.json()
        assert "content" in result
        assert "word_count" in result
        assert "tone" in result
        assert "personalization_score" in result
        assert "Google" in result["content"]
        assert "Senior Software Engineer" in result["content"]

    def test_cover_letter_optimization(self, client: TestClient, auth_headers):
        """Test cover letter optimization."""
        cover_letter = """
        Dear Hiring Manager,
        I am writing to apply for the Software Engineer position at Google.
        I have experience with Python and React.
        Sincerely,
        John Doe
        """
        response = client.post(
            "/applications/cover-letter/optimize",
            json={
                "cover_letter": cover_letter,
                "target_role": "Software Engineer",
                "target_company": "Google",
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        result = response.json()
        assert "word_count" in result
        assert "suggestions" in result
        assert len(result["suggestions"]) > 0

    def test_application_answers_generation(self, client: TestClient, auth_headers):
        """Test application answers generation."""
        response = client.post(
            "/applications/answers",
            json={
                "questions": [
                    "Tell me about a time you led a challenging project.",
                    "Why do you want to work at Google?",
                    "What are your salary expectations?",
                ],
                "target_role": "Senior Software Engineer",
                "target_company": "Google",
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        result = response.json()
        assert "answers" in result
        assert len(result["answers"]) == 3
        assert "overall_confidence" in result
        assert "review_notes" in result

        for answer in result["answers"]:
            assert "question" in answer
            assert "answer" in answer
            assert "confidence" in answer
            assert "strategy" in answer

    def test_interview_prep(self, client: TestClient, auth_headers):
        """Test interview preparation materials."""
        response = client.post(
            "/applications/interview-prep",
            json={
                "target_role": "Senior Software Engineer",
                "target_company": "Google",
                "job_description": "Python, React, AWS, Kubernetes, leadership experience required",
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        result = response.json()
        assert "likely_questions" in result
        assert "star_stories" in result
        assert "company_research" in result
        assert "technical_preparation" in result
        assert "questions_to_ask" in result
        assert len(result["likely_questions"]) > 0

    def test_create_application(self, client: TestClient, auth_headers, test_jobs):
        """Test submitting an application."""
        job = test_jobs[0]
        response = client.post(
            "/applications/",
            json={
                "job_id": job.id,
                "resume_text": "John Doe\nSenior Software Engineer\n\nSKILLS\nPython, React, AWS, Kubernetes",
                "cover_letter": "Dear Hiring Manager, I am interested in this position...",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        result = response.json()
        assert "id" in result
        assert result["job_id"] == job.id
        assert result["status"] == "submitted"

    def test_list_applications(self, client: TestClient, auth_headers, test_application):
        """Test listing user applications."""
        response = client.get("/applications/", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_list_applications_filtered(self, client: TestClient, auth_headers, test_application):
        """Test listing applications with status filter."""
        response = client.get(
            "/applications/",
            params={"status": "submitted"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        result = response.json()
        assert all(app["status"] == "submitted" for app in result)

    def test_get_application(self, client: TestClient, auth_headers, test_application):
        """Test getting application details."""
        response = client.get(f"/applications/{test_application.id}", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert result["id"] == test_application.id
        assert result["job_id"] == test_application.job_id

    def test_update_application_status(self, client: TestClient, auth_headers, test_application):
        """Test updating application status."""
        response = client.patch(
            f"/applications/{test_application.id}",
            json={
                "status": "interview_scheduled",
                "notes": "Phone screen scheduled for Friday",
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "interview_scheduled"
        assert result["notes"] == "Phone screen scheduled for Friday"

    def test_withdraw_application(self, client: TestClient, auth_headers, test_application):
        """Test withdrawing an application."""
        response = client.delete(f"/applications/{test_application.id}", headers=auth_headers)

        assert response.status_code == 204

        # Verify it's withdrawn
        response = client.get(f"/applications/{test_application.id}", headers=auth_headers)
        assert response.json()["status"] == "withdrawn"

    def test_get_application_stats(self, client: TestClient, auth_headers, test_application):
        """Test getting application statistics."""
        response = client.get("/applications/stats", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert "total" in result
        assert "by_status" in result
        assert "response_rate" in result
        assert "interview_rate" in result
        assert "offer_rate" in result

    def test_get_application_insights(self, client: TestClient, auth_headers, test_application):
        """Test getting application insights."""
        response = client.get("/applications/stats/insights", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, dict)


class TestApplicationsSecurity:
    """Security tests for applications endpoints."""

    def test_user_isolation(self, client: TestClient, test_application, second_user, db_session):
        """Test that users can't access other users' applications."""
        from backend.utils.security import create_access_token
        token = create_access_token(data={"sub": second_user.id})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(f"/applications/{test_application.id}", headers=headers)
        assert response.status_code == 404

    def test_application_status_validation(self, client: TestClient, auth_headers, test_application):
        """Test that invalid status values are rejected."""
        response = client.patch(
            f"/applications/{test_application.id}",
            json={"status": "invalid_status"},
            headers=auth_headers,
        )
        assert response.status_code in [400, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])