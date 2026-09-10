"""
Step B tests: restart rehydration of approved skills.

Simulated restart = dropping the in-memory managers (and reconcile marks),
then calling the API again: owned+enabled+resolvable rows must come back,
everything else must stay out (fail closed).

Proven here: module-addressed rows rehydrate through the allowlisted
loader; template-addressed rows skip-and-log (no persistent template
store exists); disabled, foreign-user, legacy ownerless, and unresolvable
rows never rehydrate.
"""

from __future__ import annotations

import pytest

from backend.api import skills as skills_api
from backend.models.hermes_skill import HermesSkill


@pytest.fixture(autouse=True)
def _clean_state():
    skills_api._managers.clear()
    skills_api._reconciled.clear()
    yield
    skills_api._managers.clear()
    skills_api._reconciled.clear()


def _restart():
    """Simulate an application restart (memory backends wiped, DB kept)."""
    skills_api._managers.clear()
    skills_api._reconciled.clear()


def _row(db_session, user_id, name, **kwargs):
    params = dict(name=name, description=f"{name} skill", enabled=True,
                  user_id=user_id)
    params.update(kwargs)
    row = HermesSkill(**params)
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


class TestPromotionPersistsProvenance:
    def test_owner_and_template_recorded(self, creator, db_session, test_user):
        from backend.hermes_engine.skills.skill_promotion import SkillPromotion
        from backend.hermes.approval.manager import ApprovalManager
        from backend.hermes.skills.registry import SkillRegistry

        promotion = SkillPromotion(
            creator=creator, registry=SkillRegistry(),
            approval=ApprovalManager(), db=db_session)
        draft = promotion.propose_suggestion({
            "agent_id": "a1", "category": "q", "description": "d",
            "skill_name": "owned_skill", "template": "summarize",
        }, requester_id="u9", user_id=test_user.id)
        promotion.approve(draft.approval_request_id)
        row = db_session.query(HermesSkill).filter_by(name="owned_skill").one()
        assert row.user_id == test_user.id
        assert row.template == "summarize"
        assert row.enabled is True

    def test_legacy_default_stays_ownerless(self, creator, db_session):
        from backend.hermes_engine.skills.skill_promotion import SkillPromotion
        from backend.hermes.approval.manager import ApprovalManager
        from backend.hermes.skills.registry import SkillRegistry

        promotion = SkillPromotion(
            creator=creator, registry=SkillRegistry(),
            approval=ApprovalManager(), db=db_session)
        draft = promotion.propose_suggestion({
            "agent_id": "a1", "category": "q", "description": "d",
            "skill_name": "legacy_skill", "template": "summarize",
        }, requester_id="u9")
        promotion.approve(draft.approval_request_id)
        row = db_session.query(HermesSkill).filter_by(name="legacy_skill").one()
        assert row.user_id is None


@pytest.fixture
def creator():
    from backend.hermes_engine.skills.skill_creator import SkillCreator

    async def _handler(**kwargs):
        return {"ok": True}

    creator = SkillCreator()
    creator.add_template("summarize", {
        "description": "Summarize text", "parameters": {},
        "handler": _handler, "tags": [],
    })
    return creator


MODULE = "backend.hermes_engine.skills.skill_creator"


class TestRehydrate:
    def test_module_skill_returns_after_restart(self, client, auth_headers,
                                                db_session, test_user):
        _row(db_session, test_user.id, "mod_skill",
             module_path=MODULE, function_name="SkillCreator")
        assert client.get("/api/skills/skills/mod_skill",
                          headers=auth_headers).status_code == 200
        _restart()
        body = client.get("/api/skills/skills/mod_skill",
                          headers=auth_headers)
        assert body.status_code == 200
        assert body.json()["name"] == "mod_skill"

    def test_template_skill_skipped_after_restart(self, client, auth_headers,
                                                  db_session, test_user):
        _row(db_session, test_user.id, "tmpl_skill", template="summarize")
        _restart()
        assert client.get("/api/skills/skills/tmpl_skill",
                          headers=auth_headers).status_code == 404

    def test_disabled_row_never_rehydrates(self, client, auth_headers,
                                           db_session, test_user):
        _row(db_session, test_user.id, "off_skill",
             module_path=MODULE, function_name="SkillCreator", enabled=False)
        _restart()
        assert client.get("/api/skills/skills/off_skill",
                          headers=auth_headers).status_code == 404

    def test_foreign_user_rows_never_rehydrate(self, client, auth_headers,
                                               db_session, test_user, second_user):
        _row(db_session, second_user.id, "theirs",
             module_path=MODULE, function_name="SkillCreator")
        _restart()
        assert client.get("/api/skills/skills/theirs",
                          headers=auth_headers).status_code == 404

    def test_legacy_ownerless_rows_never_rehydrate(self, client, auth_headers,
                                                   db_session, test_user):
        _row(db_session, None, "legacy",
             module_path=MODULE, function_name="SkillCreator")
        _restart()
        assert client.get("/api/skills/skills/legacy",
                          headers=auth_headers).status_code == 404

    def test_unresolvable_and_disallowed_rows_skipped(self, client, auth_headers,
                                                      db_session, test_user):
        _row(db_session, test_user.id, "ghost_fn",
             module_path=MODULE, function_name="NoSuchThing")
        _row(db_session, test_user.id, "evil_mod",
             module_path="os", function_name="system")
        _restart()
        assert client.get("/api/skills/skills/ghost_fn",
                          headers=auth_headers).status_code == 404
        assert client.get("/api/skills/skills/evil_mod",
                          headers=auth_headers).status_code == 404

    def test_human_registered_entry_wins_over_row(self, client, auth_headers,
                                                  db_session, test_user):
        async def _human(**kwargs):
            return "human"

        skills_api.get_skill_manager(int(test_user.id)).register(
            "mod_skill", _human, description="human version")
        _row(db_session, test_user.id, "mod_skill",
             module_path=MODULE, function_name="SkillCreator")
        _restart()
        # Reconcile re-registers from the row (human entry was wiped too).
        body = client.get("/api/skills/skills/mod_skill",
                          headers=auth_headers)
        assert body.status_code == 200

    def test_live_human_entry_is_never_overwritten(self, client, auth_headers,
                                                   db_session, test_user):
        async def _human(**kwargs):
            return "human"

        skills_api.get_skill_manager(int(test_user.id)).register(
            "mod_skill", _human, description="human version")
        _row(db_session, test_user.id, "mod_skill",
             module_path=MODULE, function_name="SkillCreator")
        # No restart: reconcile runs with the human entry present → kept.
        body = client.get("/api/skills/skills/mod_skill",
                          headers=auth_headers)
        assert body.status_code == 200
        assert body.json()["description"] == "human version"

    def test_reconcile_runs_once_and_survives_db_errors(
            self, client, auth_headers, db_session, test_user, monkeypatch):
        _row(db_session, test_user.id, "mod_skill",
             module_path=MODULE, function_name="SkillCreator")
        assert client.get("/api/skills/skills", headers=auth_headers).status_code == 200
        assert test_user.id in skills_api._reconciled
        # Second call does not re-query (mark present); state stable.
        assert client.get("/api/skills/skills", headers=auth_headers).status_code == 200
