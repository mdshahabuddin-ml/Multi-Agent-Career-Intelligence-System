"""Tests for Phase 3: Content Blueprint generation.

Verifies that:
- ContentBlueprintGenerator produces structured blueprints
- Blueprints are grounded in the customer's question
- Unrelated/random topics are NOT produced
- Blueprint validation rejects empty/incomplete blueprints
- Blueprints persist in Content.metadata_json
- Different questions produce different blueprints
"""

import pytest
from backend.models.content import Content
from backend.models.profile import Profile
from backend.models.skill import Skill
from backend.hermes_engine.models.content_blueprint import ContentBlueprint
from backend.hermes_engine.skills.content_blueprint_generator import ContentBlueprintGenerator


# ── Helpers ──────────────────────────────────────────────────


def _make_content(db, user_id, title, body, original_question=None):
    content = Content(
        user_id=user_id,
        title=title,
        body=body,
        original_question=original_question,
        status="approved",
        content_type="post",
        tags_json=[],
    )
    db.add(content)
    db.commit()
    db.refresh(content)
    return content


def _make_profile(db, user_id, target_role="Data Scientist", headline="Analyst"):
    profile = Profile(
        user_id=user_id,
        headline=headline,
        target_role=target_role,
        location="Remote",
        bio="Professional",
        years_of_experience=3,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def _make_skill(db, profile_id, name):
    skill = Skill(profile_id=profile_id, name=name, category="technical", proficiency="advanced")
    db.add(skill)
    db.commit()
    return skill


# ── Validation Tests ────────────────────────────────────────


class TestBlueprintValidation:
    def test_valid_blueprint_passes(self):
        bp = ContentBlueprint(
            original_question="What skills for data science?",
            target_topic="Data Science Skills",
            target_audience="Aspiring Data Scientists",
            career_goal="Become a Data Scientist",
            current_skills=["Python", "SQL"],
            learning_objectives=["Learn Python", "Master statistics", "Build ML models", "Create portfolio"],
            key_concepts=["Python", "Statistics", "Machine Learning", "Data Visualization", "SQL"],
            topic_sequence=["Python Fundamentals", "Statistics", "Machine Learning", "Data Visualization", "Portfolio"],
            subtopics={"Foundations": ["Python", "SQL"], "Core": ["Statistics", "ML"]},
            expected_outcome="Gain data science skills",
            difficulty_level="intermediate",
            estimated_duration="8 weeks",
        )
        errors = bp.validate()
        assert errors == []

    def test_empty_blueprint_fails(self):
        bp = ContentBlueprint()
        errors = bp.validate()
        assert len(errors) > 0
        assert any("original_question" in e for e in errors)

    def test_missing_concepts_fails(self):
        bp = ContentBlueprint(
            original_question="What skills for data science?",
            target_topic="Data Science",
            target_audience="Beginners",
            learning_objectives=["Learn A", "Learn B"],
            key_concepts=["only one"],
            topic_sequence=["A", "B"],
            subtopics={"A": ["a1"]},
            expected_outcome="Something",
            difficulty_level="beginner",
            estimated_duration="4 weeks",
        )
        errors = bp.validate()
        assert any("key_concepts" in e for e in errors)

    def test_unrelated_topic_detected(self):
        bp = ContentBlueprint(
            original_question="What skills should I learn to become a Data Scientist?",
            target_topic="French Cooking",
            target_audience="Aspiring Data Scientists",
            key_concepts=["A", "B", "C", "D"],
            topic_sequence=["A", "B", "C"],
            learning_objectives=["Learn A", "Learn B"],
            subtopics={"A": ["a1"]},
            expected_outcome="Something",
            difficulty_level="intermediate",
            estimated_duration="8 weeks",
        )
        errors = bp.validate()
        assert any("unrelated" in e.lower() for e in errors)

    def test_serialization_roundtrip(self):
        bp = ContentBlueprint(
            original_question="Test question",
            target_topic="Test Topic",
            target_audience="Testers",
            key_concepts=["A", "B", "C"],
            topic_sequence=["A", "B"],
            learning_objectives=["Learn A", "Learn B"],
            subtopics={"A": ["a1"]},
            expected_outcome="Outcome",
            difficulty_level="beginner",
            estimated_duration="4 weeks",
        )
        data = bp.to_dict()
        bp2 = ContentBlueprint.from_dict(data)
        assert bp2.original_question == bp.original_question
        assert bp2.target_topic == bp.target_topic
        assert bp2.key_concepts == bp.key_concepts

    def test_from_dict_empty(self):
        bp = ContentBlueprint.from_dict({})
        assert bp.original_question == ""
        assert bp.key_concepts == []


# ── Scenario Tests ──────────────────────────────────────────


class TestBlueprintScenarios:
    """Test that blueprints change according to the question."""

    def test_scenario_a_data_scientist(self, db_session, test_user):
        """Scenario A: 'What skills should I learn to become a Data Scientist in 2026?'"""
        content = _make_content(
            db_session, test_user.id,
            title="Data Scientist Skills 2026",
            body="A guide to data science skills.",
            original_question="What skills should I learn to become a Data Scientist in 2026?",
        )
        generator = ContentBlueprintGenerator(db_session)
        bp = generator.generate(content.id, test_user.id)

        # Must be grounded in data science
        assert bp.original_question == "What skills should I learn to become a Data Scientist in 2026?"
        assert "data scien" in bp.target_topic.lower() or "data" in bp.target_topic.lower()
        # Should have data science concepts
        concepts_lower = " ".join(bp.key_concepts).lower()
        assert any(kw in concepts_lower for kw in ["python", "machine learn", "statistic", "data", "sql"])
        # Should NOT have unrelated topics
        assert "cooking" not in concepts_lower
        assert "marketing" not in concepts_lower
        assert "french" not in concepts_lower
        # Validate structure
        errors = bp.validate()
        assert errors == [], f"Validation failed: {errors}"

    def test_scenario_b_swe_interview(self, db_session, test_user):
        """Scenario B: 'How can I prepare for a software engineering interview?'"""
        content = _make_content(
            db_session, test_user.id,
            title="SWE Interview Prep",
            body="How to prepare for software engineering interviews.",
            original_question="How can I prepare for a software engineering interview?",
        )
        generator = ContentBlueprintGenerator(db_session)
        bp = generator.generate(content.id, test_user.id)

        # Must be grounded in interview prep
        assert "interview" in bp.original_question.lower()
        topic_lower = bp.target_topic.lower()
        assert any(kw in topic_lower for kw in ["interview", "software", "engineering", "technical"])
        # Should have interview-relevant concepts
        concepts_lower = " ".join(bp.key_concepts).lower()
        assert any(kw in concepts_lower for kw in [
            "interview", "algorithm", "data structure", "system design",
            "behavioral", "coding", "resume",
        ])
        # Should NOT have data science topics
        assert "machine learn" not in concepts_lower
        assert "neural network" not in concepts_lower
        errors = bp.validate()
        assert errors == [], f"Validation failed: {errors}"

    def test_scenario_c_cybersecurity(self, db_session, test_user):
        """Scenario C: 'What should I learn to become a cybersecurity analyst?'"""
        content = _make_content(
            db_session, test_user.id,
            title="Cybersecurity Analyst Path",
            body="Career path to cybersecurity analysis.",
            original_question="What should I learn to become a cybersecurity analyst?",
        )
        generator = ContentBlueprintGenerator(db_session)
        bp = generator.generate(content.id, test_user.id)

        # Must be grounded in cybersecurity
        assert "cyber" in bp.original_question.lower()
        topic_lower = bp.target_topic.lower()
        assert any(kw in topic_lower for kw in ["cyber", "security", "information"])
        # Should have security-relevant concepts
        concepts_lower = " ".join(bp.key_concepts).lower()
        assert any(kw in concepts_lower for kw in [
            "security", "network", "vulnerability", "cryptograph",
            "penetration", "incident", "threat", "ethical",
        ])
        # Should NOT have data science or cooking topics
        assert "machine learn" not in concepts_lower
        assert "cooking" not in concepts_lower
        errors = bp.validate()
        assert errors == [], f"Validation failed: {errors}"

    def test_different_questions_different_blueprints(self, db_session, test_user):
        """Verify that different questions produce structurally different blueprints."""
        content_a = _make_content(
            db_session, test_user.id,
            title="Data Science",
            body="Body A",
            original_question="What skills should I learn to become a Data Scientist in 2026?",
        )
        content_b = _make_content(
            db_session, test_user.id,
            title="Cybersecurity",
            body="Body B",
            original_question="What should I learn to become a cybersecurity analyst?",
        )
        generator = ContentBlueprintGenerator(db_session)
        bp_a = generator.generate(content_a.id, test_user.id)
        bp_b = generator.generate(content_b.id, test_user.id)

        # Topics must be different
        assert bp_a.target_topic != bp_b.target_topic
        # Concepts must have different focus
        assert set(bp_a.key_concepts) != set(bp_b.key_concepts)
        # Sequences must be different
        assert bp_a.topic_sequence != bp_b.topic_sequence


# ── Storage Tests ────────────────────────────────────────────


class TestBlueprintStorage:
    def test_blueprint_stored_in_metadata(self, db_session, test_user):
        content = _make_content(
            db_session, test_user.id,
            title="Test",
            body="Body",
            original_question="What skills for data science?",
        )
        generator = ContentBlueprintGenerator(db_session)
        bp = generator.generate(content.id, test_user.id)

        # Simulate storage (as the API endpoint does)
        meta = content.metadata_json or {}
        meta["blueprint"] = bp.to_dict()
        content.metadata_json = meta
        db_session.commit()
        db_session.refresh(content)

        # Verify stored
        stored = content.metadata_json.get("blueprint")
        assert stored is not None
        assert stored["original_question"] == bp.original_question
        assert stored["target_topic"] == bp.target_topic

    def test_blueprint_retrievable(self, db_session, test_user):
        content = _make_content(
            db_session, test_user.id,
            title="Test",
            body="Body",
            original_question="What skills for data science?",
        )
        generator = ContentBlueprintGenerator(db_session)
        bp = generator.generate(content.id, test_user.id)

        meta = content.metadata_json or {}
        meta["blueprint"] = bp.to_dict()
        content.metadata_json = meta
        db_session.commit()
        db_session.refresh(content)

        # Retrieve and deserialize
        retrieved = ContentBlueprint.from_dict(content.metadata_json["blueprint"])
        assert retrieved.target_topic == bp.target_topic
        assert len(retrieved.key_concepts) == len(bp.key_concepts)


# ── Career Context Integration ──────────────────────────────


class TestBlueprintWithCareerContext:
    def test_career_context_influences_skills(self, db_session, test_user):
        """When career context has skills, they appear in current_skills."""
        profile = _make_profile(db_session, test_user.id, target_role="Senior Data Scientist")
        _make_skill(db_session, profile.id, "Python")
        _make_skill(db_session, profile.id, "TensorFlow")

        content = _make_content(
            db_session, test_user.id,
            title="Advanced DS",
            body="Body",
            original_question="What advanced data science skills should I learn?",
        )
        generator = ContentBlueprintGenerator(db_session)
        bp = generator.generate(content.id, test_user.id)

        # Career context skills should appear
        assert "Python" in bp.current_skills or "TensorFlow" in bp.current_skills

    def test_no_profile_still_generates_blueprint(self, db_session, test_user):
        """Blueprint generation works even without a profile."""
        content = _make_content(
            db_session, test_user.id,
            title="No Profile Content",
            body="Body",
            original_question="What skills for cloud computing?",
        )
        generator = ContentBlueprintGenerator(db_session)
        bp = generator.generate(content.id, test_user.id)

        assert bp.target_topic != ""
        assert len(bp.key_concepts) >= 3
        errors = bp.validate()
        assert errors == []
