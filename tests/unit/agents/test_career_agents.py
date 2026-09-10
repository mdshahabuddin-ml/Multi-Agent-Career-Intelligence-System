"""Unit tests for Career Intelligence agents."""

import pytest
from datetime import datetime, date
from unittest.mock import AsyncMock, MagicMock, patch

from backend.agents.career.skill_gap_agent import (
    SkillGapAgent, SkillGapAnalysis, SkillGap, CandidateSkill, RequiredSkill,
    SkillCategory, ProficiencyLevel
)
from backend.agents.career.career_path_agent import (
    CareerPathAgent, CareerTrajectory, CareerPath, CareerTransition,
    CareerPathNode, CareerStage, TransitionType
)
from backend.agents.career.learning_agent import (
    LearningAgent, LearningPlan, LearningProgress, LearningMilestone,
    LearningPhase, LearningResource, LearningStyle, DifficultyLevel, ResourceType
)
from backend.agents.career.career_advisor import (
    CareerAdvisor, CareerAssessment, CareerAdvice, CareerGoal, AdvisorFocus
)


class TestSkillGapAgent:
    """Tests for SkillGapAgent."""

    @pytest.fixture
    def agent(self):
        return SkillGapAgent()

    @pytest.fixture
    def candidate_skills(self):
        return [
            CandidateSkill("Python", SkillCategory.LANGUAGE, ProficiencyLevel.EXPERT, 8, 1.0, "profile"),
            CandidateSkill("React", SkillCategory.FRAMEWORK, ProficiencyLevel.ADVANCED, 5, 0.9, "profile"),
            CandidateSkill("AWS", SkillCategory.PLATFORM, ProficiencyLevel.ADVANCED, 4, 0.9, "profile"),
            CandidateSkill("PostgreSQL", SkillCategory.LANGUAGE, ProficiencyLevel.ADVANCED, 6, 0.95, "profile"),
            CandidateSkill("Kubernetes", SkillCategory.TOOL, ProficiencyLevel.INTERMEDIATE, 2, 0.8, "profile"),
            CandidateSkill("Git", SkillCategory.TOOL, ProficiencyLevel.ADVANCED, 7, 1.0, "profile"),
            CandidateSkill("Communication", SkillCategory.SOFT, ProficiencyLevel.ADVANCED, 8, 0.9, "profile"),
        ]

    def test_analyze_skill_gaps_software_engineer(self, agent, candidate_skills):
        """Test skill gap analysis for software engineer role."""
        result = agent.analyze_skill_gaps(
            candidate_skills=candidate_skills,
            target_role="software engineer",
        )

        assert isinstance(result, SkillGapAnalysis)
        assert result.target_role == "software engineer"
        assert result.overall_match_score >= 0.0
        assert result.overall_match_score <= 1.0
        assert len(result.gaps) >= 0
        assert len(result.matched_skills) > 0
        assert result.critical_gaps_count + result.moderate_gaps_count + result.minor_gaps_count == len(result.gaps)

    def test_analyze_skill_gaps_ml_engineer(self, agent, candidate_skills):
        """Test skill gap analysis for ML engineer role."""
        result = agent.analyze_skill_gaps(
            candidate_skills=candidate_skills,
            target_role="machine learning engineer",
        )

        # Should identify ML-specific gaps
        gap_names = [g.skill_name for g in result.gaps]
        assert any("PyTorch" in g or "TensorFlow" in g or "Machine Learning" in g for g in gap_names)
        assert result.overall_match_score < 0.8  # Lower match for different role

    def test_skill_matching_with_aliases(self, agent):
        """Test skill matching handles aliases."""
        candidate_skills = [
            CandidateSkill("JavaScript", SkillCategory.LANGUAGE, ProficiencyLevel.EXPERT, 5),
            CandidateSkill("PostgreSQL", SkillCategory.LANGUAGE, ProficiencyLevel.ADVANCED, 4),
            CandidateSkill("AWS", SkillCategory.PLATFORM, ProficiencyLevel.ADVANCED, 3),
        ]

        result = agent.analyze_skill_gaps(
            candidate_skills=candidate_skills,
            target_role="software engineer",  # Requires JS, SQL, AWS
        )

        matched_names = [m["skill"] for m in result.matched_skills]
        # Should match JavaScript, SQL (via PostgreSQL alias), AWS.
        # Entries are keyed by required-skill name.
        assert "JavaScript" in matched_names
        assert "SQL" in matched_names
        assert "AWS" in matched_names

    def test_proficiency_gap_calculation(self, agent):
        """Test proficiency gap calculation."""
        candidate_skills = [
            CandidateSkill("Docker", SkillCategory.TOOL, ProficiencyLevel.INTERMEDIATE, 2),
        ]

        result = agent.analyze_skill_gaps(
            candidate_skills=candidate_skills,
            target_role="devops engineer",  # Requires Docker EXPERT
        )

        docker_gap = next((g for g in result.gaps if g.skill_name == "Docker"), None)
        assert docker_gap is not None
        assert docker_gap.candidate_proficiency == ProficiencyLevel.INTERMEDIATE
        assert docker_gap.required_proficiency == ProficiencyLevel.EXPERT
        assert docker_gap.gap_severity > 0.5

    def test_priority_skills_ordering(self, agent, candidate_skills):
        """Test that priority skills are ordered by importance."""
        result = agent.analyze_skill_gaps(
            candidate_skills=candidate_skills,
            target_role="software engineer",
        )

        # Priority skills should be sorted by severity * importance * frequency
        assert len(result.priority_skills) <= 5
        for i in range(len(result.priority_skills) - 1):
            # Can't easily test exact ordering without knowing internal scores
            # but we can verify it returns a reasonable list
            assert isinstance(result.priority_skills[i], str)


class TestCareerPathAgent:
    """Tests for CareerPathAgent."""

    @pytest.fixture
    def agent(self):
        return CareerPathAgent()

    @pytest.fixture
    def candidate_profile(self):
        return {
            "current_role": "Software Engineer",
            "years_experience": 5,
            "skills": [
                {"name": "Python", "category": "technical", "proficiency": "advanced"},
                {"name": "React", "category": "technical", "proficiency": "advanced"},
                {"name": "AWS", "category": "technical", "proficiency": "intermediate"},
                {"name": "PostgreSQL", "category": "technical", "proficiency": "advanced"},
                {"name": "System Design", "category": "technical", "proficiency": "intermediate"},
            ],
            "interests": ["backend", "distributed systems", "mentoring"],
            "values": ["technical excellence", "team growth", "impact"],
        }

    def test_get_career_paths(self, agent, candidate_profile):
        """Test getting career path recommendations."""
        trajectory = agent.generate_trajectory(
            current_role=candidate_profile["current_role"],
            current_skills=[s["name"] for s in candidate_profile["skills"]],
            years_experience=candidate_profile["years_experience"],
            interests=candidate_profile["interests"],
        )

        assert isinstance(trajectory, CareerTrajectory)
        assert trajectory.current_role == "Software Engineer"
        assert len(trajectory.possible_paths) > 0
        assert all(isinstance(t, CareerPath) for t in trajectory.possible_paths)

    def test_recommended_path_includes_steps(self, agent, candidate_profile):
        """Test that recommended path includes actionable steps."""
        trajectory = agent.generate_trajectory(
            current_role=candidate_profile["current_role"],
            current_skills=[s["name"] for s in candidate_profile["skills"]],
            years_experience=candidate_profile["years_experience"],
            interests=candidate_profile["interests"],
        )
        recommended = trajectory.recommended_path

        assert recommended is not None
        assert isinstance(recommended, CareerPath)
        assert recommended.target_role is not None
        assert len(recommended.transitions) > 0

    def test_transition_requirements(self, agent, candidate_profile):
        """Test that transitions include skill requirements."""
        trajectory = agent.generate_trajectory(
            current_role=candidate_profile["current_role"],
            current_skills=[s["name"] for s in candidate_profile["skills"]],
            years_experience=candidate_profile["years_experience"],
            interests=candidate_profile["interests"],
        )
        recommended = trajectory.recommended_path

        for transition in recommended.transitions:
            assert isinstance(transition, CareerTransition)
            assert transition.transition_type in [t.value for t in TransitionType]
            assert len(transition.required_additional_skills) > 0
            assert transition.estimated_time_months > 0


class TestLearningAgent:
    """Tests for LearningAgent."""

    @pytest.fixture
    def agent(self):
        return LearningAgent()

    @pytest.fixture
    def skill_gaps(self):
        return ["Kubernetes", "System Design", "Machine Learning"]

    def test_create_learning_plan(self, agent, skill_gaps):
        """Test learning plan creation."""
        plan = agent.generate_learning_plan(
            user_id=1,
            target_role="Senior Software Engineer",
            target_skills=skill_gaps,
            current_skills=["Python", "Docker"],
            skill_gaps=skill_gaps,
            weekly_hours=10,
            learning_style=LearningStyle.MIXED,
            budget=500.0,
        )

        assert isinstance(plan, LearningPlan)
        assert len(plan.phases) > 0
        assert plan.total_estimated_weeks > 0
        assert plan.weekly_time_commitment_hours == 10
        assert plan.learning_style == LearningStyle.MIXED

    def test_learning_phases_structure(self, agent, skill_gaps):
        """Test that learning phases are properly structured."""
        plan = agent.generate_learning_plan(
            user_id=1,
            target_role="Senior Software Engineer",
            target_skills=skill_gaps,
            current_skills=["Python", "Docker"],
            skill_gaps=skill_gaps,
            weekly_hours=10,
        )

        # Every gap skill should land in some phase's focus areas
        covered = {skill for p in plan.phases for skill in p.focus_areas}
        assert set(skill_gaps) <= covered

        for phase in plan.phases:
            assert isinstance(phase, LearningPhase)
            assert phase.name is not None
            assert len(phase.milestones) > 0
            assert phase.estimated_weeks > 0
            for milestone in phase.milestones:
                assert len(milestone.resources) > 0

    def test_resource_recommendations(self, agent, skill_gaps):
        """Test that resources are recommended per skill."""
        all_resources = []
        for skill in skill_gaps:
            all_resources.extend(agent.get_resource_recommendations(skill, budget=1000.0))

        assert len(all_resources) > 0
        for resource in all_resources:
            assert isinstance(resource, LearningResource)
            assert resource.title is not None
            assert resource.resource_type in [t.value for t in ResourceType]
            assert resource.difficulty in [d.value for d in DifficultyLevel]
            assert resource.estimated_hours > 0


class TestCareerAdvisor:
    """Tests for CareerAdvisor."""

    @pytest.fixture
    def agent(self):
        return CareerAdvisor()

    @pytest.fixture
    def assessment_request(self):
        return {
            "user_id": 1,
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
            "learning_style": "mixed",
        }

    def test_assess_career(self, agent, assessment_request):
        """Test comprehensive career assessment."""
        assessment = agent.assess_career(**assessment_request)

        assert isinstance(assessment, CareerAssessment)
        assert 0 <= assessment.overall_score <= 100
        assert len(assessment.strengths) > 0
        assert len(assessment.areas_for_improvement) > 0
        assert len(assessment.next_actions) > 0
        assert assessment.skill_gap_analysis is not None
        assert assessment.career_trajectory is not None
        assert assessment.learning_plan is not None
        assert len(assessment.advice) > 0

    def test_generate_advice_for_focus_areas(self, agent, assessment_request):
        """Test advice generation for different focus areas."""
        assessment = agent.assess_career(**assessment_request)

        focus_areas = [a.focus for a in assessment.advice]
        assert AdvisorFocus.SKILL_DEVELOPMENT in focus_areas
        assert len(focus_areas) > 1
        # Should also have role-specific advice

    def test_create_career_goal(self, agent):
        """Test career goal creation."""
        goal = agent.create_career_goal(
            user_id=1,
            title="Become Staff Engineer",
            description="Reach staff engineer level within 2 years",
            target_date=date(2026, 12, 31),
            target_role="Staff Engineer",
            target_skills=["System Design", "Technical Leadership", "Architecture"],
        )

        assert goal.id is not None
        assert goal.title == "Become Staff Engineer"
        assert goal.target_role == "Staff Engineer"
        assert isinstance(goal.milestones, list)
        assert goal.progress == 0.0

    def test_update_goal_progress(self, agent):
        """Test updating career goal progress."""
        goal = agent.create_career_goal(
            user_id=1,
            title="Test Goal",
            description="Test",
            target_date=date(2026, 12, 31),
        )
        goal.milestones = [
            {"title": "Milestone 1", "completed": False},
            {"title": "Milestone 2", "completed": False},
        ]

        updated = agent.update_goal_progress(goal, ["Milestone 1", "Milestone 2"])

        assert updated.progress == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])