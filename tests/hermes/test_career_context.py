"""Tests for the read-only Career -> Hermes context adapter."""

import json

import pytest

from backend.hermes_engine.memory.career_context import (
    MEMORY_CATEGORY,
    CareerContextProvider,
)
from backend.hermes_engine.memory.user_memory import UserMemory
from backend.models.certification import Certification
from backend.models.profile import Profile
from backend.models.skill import Skill

FORBIDDEN_MARKERS = (
    "hashed_password",
    "file_path",
    "raw_text",
    "access_token",
    "refresh_token",
    "token_expires",
    "organization_id",
    "billing",
    "invoice",
)


@pytest.fixture
def seeded_user(db_session, test_user):
    profile = Profile(
        user_id=test_user.id,
        headline="Backend Engineer",
        target_role="Senior Backend Engineer",
        location="Remote",
        bio="Ships Python APIs.",
        years_of_experience=5,
    )
    db_session.add(profile)
    db_session.flush()
    db_session.add(Skill(profile_id=profile.id, name="Python", proficiency="expert"))
    db_session.add(Certification(user_id=test_user.id, name="AWS Architect", issuer="AWS"))
    db_session.commit()
    return test_user


def _dump(snapshot):
    return json.dumps(snapshot, default=str)


class TestCareerContextSnapshot:
    def test_sections_present(self, db_session, seeded_user):
        snapshot = CareerContextProvider(db_session).snapshot(seeded_user.id)
        assert snapshot["profile"]["headline"] == "Backend Engineer"
        assert snapshot["skills"] == [
            {"name": "Python", "category": None, "proficiency": "expert"}
        ]
        assert snapshot["certifications"][0]["name"] == "AWS Architect"
        assert snapshot["user"] == {"full_name": "Test User"}

    def test_unknown_user_rejected(self, db_session):
        with pytest.raises(ValueError):
            CareerContextProvider(db_session).snapshot(999999)

    def test_no_sensitive_data_exposed(self, db_session, seeded_user, test_user):
        snapshot = CareerContextProvider(db_session).snapshot(seeded_user.id)
        dumped = _dump(snapshot).lower()
        assert test_user.email.lower() not in dumped
        for marker in FORBIDDEN_MARKERS:
            assert marker not in dumped

    def test_ownership_scoping(self, db_session, seeded_user, second_user):
        snapshot = CareerContextProvider(db_session).snapshot(second_user.id)
        assert snapshot["profile"] is None
        assert snapshot["skills"] == []
        assert snapshot["certifications"] == []

    def test_sync_writes_only_hermes_memory(self, db_session, seeded_user):
        from backend.models.profile import Profile as P
        from backend.models.skill import Skill as S
        from backend.models.certification import Certification as C

        before = (
            db_session.query(P).count(),
            db_session.query(S).count(),
            db_session.query(C).count(),
        )
        memory = UserMemory()
        keys = CareerContextProvider(db_session).sync_to_user_memory(memory, seeded_user.id)
        after = (
            db_session.query(P).count(),
            db_session.query(S).count(),
            db_session.query(C).count(),
        )
        assert before == after
        assert len(keys) == 10
        assert all(k.startswith("career.") for k in keys)
        assert memory.retrieve(str(seeded_user.id), "career.profile")["headline"] == "Backend Engineer"
        assert memory.get_all(str(seeded_user.id), category=MEMORY_CATEGORY)["career.skills"][0]["name"] == "Python"
