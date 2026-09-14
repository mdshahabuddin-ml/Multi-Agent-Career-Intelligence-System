"""Tests for Phase 2: Content → Hermes Context resolution.

Verifies that:
- ContentContextResolver resolves original question + career context
- Original question is the PRIMARY intent in resolved context
- Career context includes profile, skills, experience, learning goals
- User isolation is enforced
- Video pipeline receives context end-to-end
"""

import pytest
from datetime import date, datetime

from backend.models.content import Content
from backend.models.profile import Profile
from backend.models.skill import Skill
from backend.models.experience import Experience
from backend.models.learning_plan import LearningPlan
from backend.models.user import User
from backend.hermes_engine.memory.content_context import ContentContextResolver


# ── Helpers ──────────────────────────────────────────────────


def _make_content(db, user_id, title, body, original_question=None, status="approved"):
    content = Content(
        user_id=user_id,
        title=title,
        body=body,
        original_question=original_question,
        status=status,
        content_type="post",
        tags_json=["data-science", "career"],
    )
    db.add(content)
    db.commit()
    db.refresh(content)
    return content


def _make_profile(db, user_id, target_role="Data Scientist", headline="Data Analyst"):
    profile = Profile(
        user_id=user_id,
        headline=headline,
        target_role=target_role,
        location="Remote",
        bio="Data professional with 3 years experience.",
        years_of_experience=3,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def _make_skill(db, profile_id, name, proficiency="advanced"):
    skill = Skill(profile_id=profile_id, name=name, category="technical", proficiency=proficiency)
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


def _make_experience(db, profile_id, company, role):
    exp = Experience(profile_id=profile_id, company=company, role=role, description=f"Worked as {role}")
    db.add(exp)
    db.commit()
    db.refresh(exp)
    return exp


def _make_learning_plan(db, user_id, title, target_role="Data Scientist"):
    plan = LearningPlan(user_id=user_id, title=title, target_role=target_role, skill_gaps=["ML", "Python"])
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


# ── Tests ────────────────────────────────────────────────────


class TestContentContextResolver:
    """Unit tests for ContentContextResolver."""

    def test_resolves_original_question(self, db_session, test_user):
        content = _make_content(
            db_session, test_user.id,
            title="What Skills Should You Learn to Become a Data Scientist in 2026?",
            body="Data science continues to evolve.",
            original_question="What skills should I learn to become a Data Scientist in 2026?",
        )
        resolver = ContentContextResolver(db_session)
        ctx = resolver.resolve(content.id, test_user.id)

        assert ctx["content"]["original_question"] == "What skills should I learn to become a Data Scientist in 2026?"
        assert ctx["content"]["title"] == "What Skills Should You Learn to Become a Data Scientist in 2026?"
        assert ctx["content"]["body"] == "Data science continues to evolve."
        assert ctx["content"]["content_id"] == content.id

    def test_resolves_content_without_original_question(self, db_session, test_user):
        content = _make_content(
            db_session, test_user.id,
            title="Data Science Career Guide",
            body="A comprehensive guide.",
            original_question=None,
        )
        resolver = ContentContextResolver(db_session)
        ctx = resolver.resolve(content.id, test_user.id)

        assert ctx["content"]["original_question"] is None
        assert ctx["content"]["title"] == "Data Science Career Guide"

    def test_includes_career_context(self, db_session, test_user):
        profile = _make_profile(db_session, test_user.id, target_role="Senior Data Scientist")
        _make_skill(db_session, profile.id, "Python", "expert")
        _make_skill(db_session, profile.id, "Machine Learning", "advanced")
        _make_experience(db_session, profile.id, "DataCorp", "Data Analyst")
        _make_learning_plan(db_session, test_user.id, "ML Bootcamp", "Senior Data Scientist")

        content = _make_content(
            db_session, test_user.id,
            title="Data Science Skills",
            body="Learn data science.",
            original_question="What skills for data science?",
        )
        resolver = ContentContextResolver(db_session)
        ctx = resolver.resolve(content.id, test_user.id)

        career = ctx["career"]
        assert career["target_role"] == "Senior Data Scientist"
        assert "Python" in career["skills"]
        assert "Machine Learning" in career["skills"]
        assert len(career["recent_experience"]) > 0
        assert career["recent_experience"][0]["company"] == "DataCorp"
        assert len(career["learning_goals"]) > 0
        assert career["learning_goals"][0]["title"] == "ML Bootcamp"

    def test_isolation_cannot_access_other_users_content(self, db_session, test_user, second_user):
        content = _make_content(
            db_session, test_user.id,
            title="Private content",
            body="Secret",
            original_question="Private question?",
        )
        resolver = ContentContextResolver(db_session)
        with pytest.raises(ValueError, match="not found"):
            resolver.resolve(content.id, second_user.id)

    def test_nonexistent_content_raises(self, db_session, test_user):
        resolver = ContentContextResolver(db_session)
        with pytest.raises(ValueError, match="not found"):
            resolver.resolve(99999, test_user.id)

    def test_empty_career_context_when_no_profile(self, db_session, test_user):
        content = _make_content(
            db_session, test_user.id,
            title="No Profile Content",
            body="Body",
            original_question="Question?",
        )
        resolver = ContentContextResolver(db_session)
        ctx = resolver.resolve(content.id, test_user.id)

        career = ctx["career"]
        assert career["target_role"] == ""
        assert career["skills"] == []

    def test_get_intent_summary_uses_original_question(self, db_session, test_user):
        content = _make_content(
            db_session, test_user.id,
            title="Title Here",
            body="Body",
            original_question="What skills for data science?",
        )
        resolver = ContentContextResolver(db_session)
        ctx = resolver.resolve(content.id, test_user.id)
        intent = resolver.get_intent_summary(ctx)
        assert intent == "What skills for data science?"

    def test_get_intent_summary_falls_back_to_title(self, db_session, test_user):
        content = _make_content(
            db_session, test_user.id,
            title="Data Science Guide",
            body="Body",
            original_question=None,
        )
        resolver = ContentContextResolver(db_session)
        ctx = resolver.resolve(content.id, test_user.id)
        intent = resolver.get_intent_summary(ctx)
        assert intent == "Data Science Guide"

    def test_tags_preserved(self, db_session, test_user):
        content = _make_content(
            db_session, test_user.id,
            title="Tagged Content",
            body="Body",
            original_question="Question?",
        )
        content.tags_json = ["python", "ml", "career"]
        db_session.commit()

        resolver = ContentContextResolver(db_session)
        ctx = resolver.resolve(content.id, test_user.id)
        assert ctx["content"]["tags"] == ["python", "ml", "career"]

    def test_body_truncated_to_3000_chars(self, db_session, test_user):
        long_body = "x" * 5000
        content = _make_content(
            db_session, test_user.id,
            title="Long Body",
            body=long_body,
            original_question="Question?",
        )
        resolver = ContentContextResolver(db_session)
        ctx = resolver.resolve(content.id, test_user.id)
        assert len(ctx["content"]["body"]) <= 3000
