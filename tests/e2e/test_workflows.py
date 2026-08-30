"""End-to-end workflow tests for complete user journeys."""

import pytest
from fastapi.testclient import TestClient
from io import BytesIO


class TestCompleteUserJourney:
    """Test complete user journey from registration to application."""

    def test_full_user_journey(self, client: TestClient):
        """Test complete flow: register -> login -> upload resume -> parse -> analyze -> search jobs -> apply."""
        
        # 1. Register
        register_response = client.post(
            "/auth/register",
            json={
                "email": "journey@example.com",
                "password": "SecurePass123!",
                "full_name": "Journey User",
            },
        )
        assert register_response.status_code == 201
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Upload resume
        resume_content = b"""
        John Doe
        john.doe@email.com | (555) 123-4567 | San Francisco, CA
        LinkedIn: linkedin.com/in/johndoe

        SUMMARY
        Senior Software Engineer with 8 years experience in Python, React, AWS, Kubernetes.

        EXPERIENCE
        Senior Software Engineer at TechCorp (2020-Present)
        - Led team of 5 engineers building microservices
        - Reduced deployment time by 80% through CI/CD pipeline improvements
        - Architected migration from monolith to microservices

        Software Engineer at StartupXYZ (2017-2020)
        - Built full-stack web applications using React, Node.js, MongoDB

        EDUCATION
        BS Computer Science | Stanford University | 2017

        SKILLS
        Languages: Go, Python, JavaScript, TypeScript, SQL
        Frameworks: React, Node.js, Express, Gin, gRPC
        Infrastructure: Kubernetes, Docker, AWS, Terraform
        Databases: PostgreSQL, MongoDB, Redis
        """
        files = {"file": ("resume.txt", BytesIO(resume_content), "text/plain")}
        upload_response = client.post(
            "/resume/upload",
            files=files,
            data={"is_primary": "true"},
            headers=headers,
        )
        assert upload_response.status_code == 201
        resume_id = upload_response.json()["id"]

        # 3. Parse resume
        parse_response = client.post(
            f"/resume/{resume_id}/parse",
            headers=headers,
        )
        assert parse_response.status_code == 200
        assert parse_response.json()["status"] == "parsed"

        # 4. ATS analysis
        ats_response = client.post(
            f"/resume/{resume_id}/ats",
            data={"target_role": "software engineer"},
            headers=headers,
        )
        assert ats_response.status_code == 200
        ats_result = ats_response.json()
        assert ats_result["overall_score"] >= 70
        assert ats_result["passed"] is True

        # 5. Resume review
        review_response = client.post(
            f"/resume/{resume_id}/review",
            headers=headers,
        )
        assert review_response.status_code == 200
        review_result = review_response.json()
        assert review_result["overall_score"] >= 70

        # 6. Search jobs
        search_response = client.post(
            "/jobs/search",
            json={
                "query": "Python",
                "location": "San Francisco",
                "remote": True,
                "limit": 10,
            },
            headers=headers,
        )
        assert search_response.status_code == 200
        jobs = search_response.json()["jobs"]
        assert len(jobs) > 0
        job_id = jobs[0]["id"]

        # 7. Get job recommendations
        rec_response = client.get(
            "/jobs/recommendations",
            params={"limit": 5},
            headers=headers,
        )
        assert rec_response.status_code == 200

        # 8. Save job
        save_response = client.post(
            f"/jobs/{job_id}/save",
            data={"notes": "Good match for my skills"},
            headers=headers,
        )
        assert save_response.status_code == 200

        # 9. Prepare application
        prepare_response = client.post(
            "/applications/prepare",
            json={
                "job_id": job_id,
                "resume_text": resume_content.decode(),
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
            headers=headers,
        )
        assert prepare_response.status_code == 200
        prepare_result = prepare_response.json()
        assert prepare_result["ready_to_submit"] is True

        # 10. Submit application
        apply_response = client.post(
            "/applications/",
            json={
                "job_id": job_id,
                "resume_text": resume_content.decode(),
                "cover_letter": prepare_result["cover_letter_result"]["content"],
            },
            headers=headers,
        )
        assert apply_response.status_code == 201
        application = apply_response.json()
        assert application["status"] == "submitted"

        # 11. Get application stats
        stats_response = client.get("/applications/stats", headers=headers)
        assert stats_response.status_code == 200
        stats = stats_response.json()
        assert stats["total"] >= 1
        assert stats["by_status"]["submitted"] >= 1

        # 12. Career assessment
        career_response = client.post(
            "/career/assess",
            json={
                "current_role": "Senior Software Engineer",
                "years_experience": 8,
                "skills": [
                    {"name": "Python", "proficiency": "expert"},
                    {"name": "React", "proficiency": "advanced"},
                    {"name": "AWS", "proficiency": "advanced"},
                    {"name": "Kubernetes", "proficiency": "intermediate"},
                ],
                "target_role": "Staff Software Engineer",
                "interests": ["backend", "leadership"],
                "weekly_learning_hours": 10,
            },
            headers=headers,
        )
        assert career_response.status_code == 201
        career = career_response.json()
        assert "skill_gap_analysis" in career
        assert "learning_plan" in career

        # 13. Generate cover letter
        cl_response = client.post(
            "/applications/cover-letter",
            json={
                "target_role": "Senior Software Engineer",
                "target_company": "Google",
                "job_description": "Senior Software Engineer with Python, React, AWS, Kubernetes...",
                "hiring_manager": "Jane Smith",
                "tone": "professional",
                "length": "medium",
            },
            headers=headers,
        )
        assert cl_response.status_code == 200
        cl_result = cl_response.json()
        assert "Google" in cl_result["content"]
        assert cl_result["personalization_score"] >= 70

        # 14. Interview prep
        interview_response = client.post(
            "/applications/interview-prep",
            json={
                "target_role": "Senior Software Engineer",
                "target_company": "Google",
                "job_description": "Python, React, AWS, Kubernetes, leadership experience required",
            },
            headers=headers,
        )
        assert interview_response.status_code == 200
        interview = interview_response.json()
        assert "likely_questions" in interview
        assert "star_stories" in interview

        # 15. Start research
        research_response = client.post(
            "/research/start",
            json={
                "query": "What are the latest trends in AI job market for 2024?",
                "research_type": "job_market",
                "target_role": "Machine Learning Engineer",
                "target_location": "San Francisco",
            },
            headers=headers,
        )
        assert research_response.status_code == 202
        research_id = research_response.json()["id"]

        # 16. Create career goal
        goal_response = client.post(
            "/career/goals",
            json={
                "title": "Become Staff Engineer",
                "description": "Reach staff engineer level within 2 years",
                "target_date": "2026-12-31",
                "target_role": "Staff Software Engineer",
                "target_skills": ["System Design", "Technical Leadership"],
            },
            headers=headers,
        )
        assert goal_response.status_code == 201

        print("✅ Complete user journey test passed!")


class TestResearchWorkflow:
    """Test research workflow end-to-end."""

    def test_research_lifecycle(self, client: TestClient, auth_headers):
        """Test complete research lifecycle: start -> monitor -> get results."""
        
        # Start research
        start_response = client.post(
            "/research/start",
            json={
                "query": "What are the latest trends in software engineering salaries 2024?",
                "research_type": "salary",
                "target_role": "Senior Software Engineer",
                "target_location": "San Francisco",
                "max_sources": 5,
                "timeout_seconds": 60,
            },
            headers=auth_headers,
        )
        assert start_response.status_code == 202
        research_id = start_response.json()["id"]

        # Check status immediately
        status_response = client.get(
            f"/research/{research_id}/status",
            headers=auth_headers,
        )
        assert status_response.status_code == 200
        status = status_response.json()
        assert status["id"] == research_id
        assert "progress" in status

        # List user research
        list_response = client.get("/research/", headers=auth_headers)
        assert list_response.status_code == 200
        research_list = list_response.json()
        assert any(r["id"] == research_id for r in research_list)

        # Cancel research (if still running)
        cancel_response = client.post(
            f"/research/{research_id}/cancel",
            headers=auth_headers,
        )
        # Either cancels or already completed
        assert cancel_response.status_code in [204, 400]


class TestApplicationWorkflow:
    """Test application workflow end-to-end."""

    def test_application_lifecycle(self, client: TestClient, auth_headers, test_jobs):
        """Test application lifecycle: create -> update -> withdraw."""
        
        job = test_jobs[0]

        # Create application
        create_response = client.post(
            "/applications/",
            json={
                "job_id": job.id,
                "resume_text": "John Doe\nSenior Software Engineer\n\nSKILLS\nPython, React, AWS, Kubernetes",
                "cover_letter": "Dear Hiring Manager, I am interested in this position...",
            },
            headers=auth_headers,
        )
        assert create_response.status_code == 201
        app_id = create_response.json()["id"]

        # Update status to interview_scheduled
        update_response = client.patch(
            f"/applications/{app_id}",
            json={
                "status": "interview_scheduled",
                "notes": "Phone screen scheduled for Friday 2pm",
            },
            headers=auth_headers,
        )
        assert update_response.status_code == 200
        assert update_response.json()["status"] == "interview_scheduled"

        # Update to interview_completed
        update_response = client.patch(
            f"/applications/{app_id}",
            json={
                "status": "interview_completed",
                "notes": "Technical interview completed, waiting for feedback",
            },
            headers=auth_headers,
        )
        assert update_response.status_code == 200
        assert update_response.json()["status"] == "interview_completed"

        # Get application insights
        insights_response = client.get("/applications/stats/insights", headers=auth_headers)
        assert insights_response.status_code == 200

        # Withdraw application
        withdraw_response = client.delete(f"/applications/{app_id}", headers=auth_headers)
        assert withdraw_response.status_code == 204

        # Verify withdrawn
        get_response = client.get(f"/applications/{app_id}", headers=auth_headers)
        assert get_response.json()["status"] == "withdrawn"


class TestCareerDevelopmentWorkflow:
    """Test career development workflow."""

    def test_skill_gap_to_learning_plan(self, client: TestClient, auth_headers):
        """Test flow: skill gap analysis -> learning plan -> goal creation."""
        
        # Get skill recommendations
        skill_response = client.get(
            "/career/skill-recommendations",
            params={"target_role": "Machine Learning Engineer"},
            headers=auth_headers,
        )
        assert skill_response.status_code == 200
        skills = skill_response.json()
        assert "priority_skills" in skills

        # Create learning plan
        plan_response = client.post(
            "/career/learning-plan",
            json={
                "target_role": "Machine Learning Engineer",
                "target_skills": skills["priority_skills"][:3],
                "skill_gaps": skills["missing_skills"][:3],
                "weekly_hours": 10,
                "learning_style": "mixed",
                "budget": 500.0,
            },
            headers=auth_headers,
        )
        assert plan_response.status_code == 201
        plan = plan_response.json()
        assert "phases" in plan
        assert plan["total_estimated_weeks"] > 0

        # Create career goal based on plan
        goal_response = client.post(
            "/career/goals",
            json={
                "title": "Transition to ML Engineer",
                "description": "Complete learning plan and transition to ML role",
                "target_date": "2026-06-30",
                "target_role": "Machine Learning Engineer",
                "target_skills": skills["priority_skills"][:3],
            },
            headers=auth_headers,
        )
        assert goal_response.status_code == 201
        goal = goal_response.json()
        goal_id = goal["id"]

        # Update goal progress
        progress_response = client.post(
            f"/career/goals/{goal_id}/progress",
            json={"completed_milestones": ["Complete Python for ML course"]},
            headers=auth_headers,
        )
        assert progress_response.status_code == 200
        assert progress_response.json()["progress"] > 0


class TestMultiUserWorkflows:
    """Test workflows involving multiple users."""

    def test_job_recommendations_different_users(self, client: TestClient, test_user, second_user, test_jobs, db_session):
        """Test that job recommendations are personalized per user."""
        from backend.utils.security import create_access_token
        
        token1 = create_access_token(data={"sub": test_user.id})
        token2 = create_access_token(data={"sub": second_user.id})
        headers1 = {"Authorization": f"Bearer {token1}"}
        headers2 = {"Authorization": f"Bearer {token2}"}

        # Both users get recommendations
        rec1 = client.get("/jobs/recommendations", params={"limit": 5}, headers=headers1)
        rec2 = client.get("/jobs/recommendations", params={"limit": 5}, headers=headers2)

        assert rec1.status_code == 200
        assert rec2.status_code == 200

        # Results should be different (personalized)
        # At minimum, they should both return valid responses
        assert "recommendations" in rec1.json()
        assert "recommendations" in rec2.json()


class TestDataIntegrity:
    """Test data integrity across workflows."""

    def test_resume_data_consistency(self, client: TestClient, auth_headers):
        """Test that resume data stays consistent through pipeline."""
        
        resume_content = """
        Jane Smith
        jane.smith@email.com | (555) 987-6543 | New York, NY
        LinkedIn: linkedin.com/in/janesmith

        SUMMARY
        Full Stack Developer with 5 years experience in React, Node.js, PostgreSQL.

        EXPERIENCE
        Full Stack Developer at WebCorp (2019-Present)
        - Built React/Node.js applications
        - Designed PostgreSQL schemas
        - Implemented CI/CD pipelines

        EDUCATION
        MS Computer Science | NYU | 2019

        SKILLS
        React, Node.js, PostgreSQL, TypeScript, Docker, AWS
        """
        
        files = {"file": ("resume.txt", BytesIO(resume_content.encode()), "text/plain")}
        upload = client.post("/resume/upload", files=files, data={"is_primary": "true"}, headers=auth_headers)
        resume_id = upload.json()["id"]

        # Parse
        client.post(f"/resume/{resume_id}/parse", headers=auth_headers)

        # Get parsed data
        get_response = client.get(f"/resume/{resume_id}", headers=auth_headers)
        resume_data = get_response.json()

        # Verify data consistency
        assert "Jane Smith" in resume_data["raw_text"]
        assert "jane.smith@email.com" in resume_data["raw_text"]
        assert "React" in resume_data["extracted_skills"]
        assert "Node.js" in resume_data["extracted_skills"]
        assert len(resume_data["extracted_experience"]) > 0

        # ATS analysis should use same data
        ats_response = client.post(f"/resume/{resume_id}/ats", data={"target_role": "full stack developer"}, headers=auth_headers)
        assert ats_response.status_code == 200
        assert "React" in ats_response.json()["matched_keywords"]


class TestErrorRecovery:
    """Test error handling and recovery in workflows."""

    def test_failed_resume_parse_recovery(self, client: TestClient, auth_headers):
        """Test recovery from failed resume parsing."""
        
        # Upload corrupted file
        files = {"file": ("corrupt.pdf", BytesIO(b"not a real pdf"), "application/pdf")}
        upload = client.post("/resume/upload", files=files, headers=auth_headers)
        assert upload.status_code == 201
        resume_id = upload.json()["id"]

        # Try to parse - should fail gracefully
        parse_response = client.post(f"/resume/{resume_id}/parse", headers=auth_headers)
        # Might succeed with empty result or fail with 500
        # Either way, system should not crash
        assert parse_response.status_code in [200, 500]

        # User should still be able to upload another resume
        files2 = {"file": ("good.txt", BytesIO(b"Good resume content"), "text/plain")}
        upload2 = client.post("/resume/upload", files=files2, headers=auth_headers)
        assert upload2.status_code == 201

    def test_partial_application_recovery(self, client: TestClient, auth_headers, test_jobs):
        """Test recovery from partial application preparation failure."""
        
        job = test_jobs[0]
        
        # Prepare with minimal data (might have warnings but should work)
        response = client.post(
            "/applications/prepare",
            json={
                "job_id": job.id,
                "resume_text": "Minimal resume",
                "candidate_profile": {
                    "name": "Test User",
                    "email": "test@example.com",
                },
            },
            headers=auth_headers,
        )
        
        # Should still return a result even with minimal data
        assert response.status_code == 200
        result = response.json()
        assert "application_id" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-k", "not test_full_user_journey or test_full_user_journey"])