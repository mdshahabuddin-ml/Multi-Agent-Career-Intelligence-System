"""Integration tests for Career API endpoints."""

import pytest
from datetime import date, datetime
from fastapi.testclient import TestClient


class TestCareerAPI:
    """Tests for career intelligence endpoints."""

    def test_assess_career(self, client: TestClient, auth_headers, test_profile, test_skills, test_projects, test_experience):
        """Test comprehensive career assessment."""
        response = client.post(
            "/career/assess",
            json={
                "current_role": "Software Engineer",
                "years_experience": 5,
                "skills": [
                    {"name": "Python", "proficiency": "advanced"},
                    {"name": "React", "proficiency": "advanced"},
                    {"name": "AWS", "proficiency": "intermediate"},
                ],
                "target_role": "Senior Software Engineer",
                "interests": ["backend", "leadership"],
                "weekly_learning_hours": 10,
                "learning_budget": 500.0,
                "learning_style": "mixed",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        result = response.json()
        assert "overall_score" in result
        assert "strengths" in result
        assert "areas_for_improvement" in result
        assert "next_actions" in result
        assert "skill_gap_analysis" in result
        assert "career_trajectory" in result
        assert "learning_plan" in result
        assert "advice" in result
        assert 0 <= result["overall_score"] <= 100

    def test_create_career_goal(self, client: TestClient, auth_headers):
        """Test creating a career goal."""
        response = client.post(
            "/career/goals",
            json={
                "title": "Become Staff Engineer",
                "description": "Reach staff engineer level within 2 years",
                "target_date": "2026-12-31",
                "target_role": "Staff Engineer",
                "target_skills": ["System Design", "Technical Leadership", "Architecture"],
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        result = response.json()
        assert "id" in result
        assert result["title"] == "Become Staff Engineer"
        assert result["target_role"] == "Staff Engineer"
        assert "milestones" in result
        assert result["progress"] == 0.0

    def test_list_career_goals(self, client: TestClient, auth_headers, test_user, db_session):
        """Test listing career goals."""
        from backend.models import LearningPlan
        
        goal = LearningPlan(
            user_id=test_user.id,
            target_role="Staff Engineer",
            title="Become Staff Engineer",
            description="Reach staff level",
            target_completion_date=date(2026, 12, 31),
            status="active",
            progress_percentage=25.0,
            milestones=[{"title": "Learn System Design", "completed": False}],
            skill_gaps=["System Design", "Architecture"],
        )
        db_session.add(goal)
        db_session.commit()

        response = client.get("/career/goals", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_update_goal_progress(self, client: TestClient, auth_headers, test_user, db_session):
        """Test updating career goal progress."""
        from backend.models import LearningPlan
        
        goal = LearningPlan(
            user_id=test_user.id,
            target_role="Staff Engineer",
            title="Become Staff Engineer",
            description="Reach staff level",
            target_completion_date=date(2026, 12, 31),
            status="active",
            progress_percentage=0.0,
            milestones=[
                {"title": "Learn System Design", "completed": False},
                {"title": "Lead Major Project", "completed": False},
            ],
            skill_gaps=["System Design", "Architecture"],
        )
        db_session.add(goal)
        db_session.commit()
        db_session.refresh(goal)

        response = client.post(
            f"/career/goals/{goal.id}/progress",
            json={"completed_milestones": ["Learn System Design"]},
            headers=auth_headers,
        )

        assert response.status_code == 200
        result = response.json()
        assert result["progress"] > 0

    def test_job_search_strategy(self, client: TestClient, auth_headers):
        """Test getting personalized job search strategy."""
        response = client.get(
            "/career/job-search-strategy",
            params={"target_role": "Senior Software Engineer"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        result = response.json()
        assert "target_roles" in result
        assert "key_skills_to_highlight" in result
        assert "skill_gaps_to_address" in result
        assert "networking_strategy" in result
        assert "application_timeline" in result
        assert "salary_expectations" in result
        assert "preparation_checklist" in result

    def test_skill_recommendations(self, client: TestClient, auth_headers):
        """Test getting skill recommendations for target role."""
        response = client.get(
            "/career/skill-recommendations",
            params={"target_role": "Machine Learning Engineer"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        result = response.json()
        assert "missing_skills" in result
        assert "proficiency_gaps" in result
        assert "priority_skills" in result
        assert "learning_resources" in result

    def test_career_path_options(self, client: TestClient, auth_headers):
        """Test getting career path options."""
        response = client.get(
            "/career/path-options",
            params={"current_role": "Software Engineer"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        result = response.json()
        assert "recommended_path" in result
        assert "alternative_paths" in result
        assert "decision_factors" in result

    def test_learning_resources(self, client: TestClient, auth_headers):
        """Test getting learning resources for a skill."""
        response = client.get(
            "/career/learning-resources",
            params={"skill": "Kubernetes", "difficulty": "intermediate", "budget": 200},
            headers=auth_headers,
        )

        assert response.status_code == 200
        result = response.json()
        assert "skill" in result
        assert "resources" in result
        assert isinstance(result["resources"], list)

    def test_create_learning_plan(self, client: TestClient, auth_headers):
        """Test creating a learning plan."""
        response = client.post(
            "/career/learning-plan",
            json={
                "target_role": "Senior Software Engineer",
                "target_skills": ["System Design", "Kubernetes", "Architecture"],
                "skill_gaps": ["System Design", "Kubernetes"],
                "weekly_hours": 10,
                "learning_style": "mixed",
                "budget": 500.0,
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        result = response.json()
        assert "id" in result
        assert result["target_role"] == "Senior Software Engineer"
        assert "phases" in result
        assert "total_estimated_weeks" in result
        assert result["weekly_time_commitment_hours"] == 10

    def test_career_insights(self, client: TestClient, auth_headers, test_profile, test_skills):
        """Test getting career insights and analytics."""
        response = client.get("/career/insights", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert "total_skills" in result
        assert "skill_categories" in result
        assert "top_skills" in result
        assert "experience_level" in result
        assert "market_demand" in result
        assert "salary_estimate" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])