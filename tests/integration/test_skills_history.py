"""
Step C tests: execution history + counter write-back for promoted skills.

History is written only for owned persisted rows (same fail-closed rule
as rehydration); audit failures never break the execution response.
"""

from __future__ import annotations

import pytest

from backend.api import skills as skills_api
from backend.models.hermes_skill import HermesSkill, HermesSkillExecution


async def _add(x, y):
    return x + y


async def _boom(**kwargs):
    raise ValueError("handler blew up")


async def _slow(**kwargs):
    import asyncio

    await asyncio.sleep(5)
    return "done"


@pytest.fixture(autouse=True)
def _clean_state():
    skills_api._managers.clear()
    skills_api._reconciled.clear()
    yield
    skills_api._managers.clear()
    skills_api._reconciled.clear()


def _promoted_row(db_session, user_id, name, **kwargs):
    params = dict(name=name, description=f"{name} skill", enabled=True,
                  user_id=user_id)
    params.update(kwargs)
    row = HermesSkill(**params)
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


def _history(db_session, user_id, skill_name):
    row = db_session.query(HermesSkill).filter_by(name=skill_name).one()
    return (db_session.query(HermesSkillExecution)
            .filter_by(skill_id=row.id, user_id=user_id)
            .order_by(HermesSkillExecution.id.asc()).all())


class TestHistory:
    def test_success_records_history_and_counters(self, client, auth_headers,
                                                  db_session, test_user):
        _promoted_row(db_session, test_user.id, "adder")
        skills_api.get_skill_manager(int(test_user.id)).register("adder", _add)
        response = client.post("/api/skills/skills/adder/execute",
                               json={"params": {"x": 2, "y": 3}}, headers=auth_headers)
        assert response.status_code == 200
        entries = _history(db_session, test_user.id, "adder")
        assert len(entries) == 1
        assert entries[0].success is True
        assert entries[0].error_message is None
        assert entries[0].input_json == {"x": 2, "y": 3}
        assert entries[0].output_json == {"result": 5}
        row = db_session.query(HermesSkill).filter_by(name="adder").one()
        assert (row.execution_count, row.error_count) == (1, 0)

    def test_handler_failure_records_history(self, client, auth_headers,
                                             db_session, test_user):
        _promoted_row(db_session, test_user.id, "flaky")
        skills_api.get_skill_manager(int(test_user.id)).register("flaky", _boom)
        with pytest.raises(ValueError):
            client.post("/api/skills/skills/flaky/execute",
                        json={"params": {}}, headers=auth_headers)
        entries = _history(db_session, test_user.id, "flaky")
        assert len(entries) == 1
        assert entries[0].success is False
        assert "blew up" in (entries[0].error_message or "")
        row = db_session.query(HermesSkill).filter_by(name="flaky").one()
        assert (row.execution_count, row.error_count) == (0, 1)

    def test_timeout_records_history(self, client, auth_headers,
                                     db_session, test_user):
        _promoted_row(db_session, test_user.id, "slowpoke")
        skills_api.get_skill_manager(int(test_user.id)).register("slowpoke", _slow)
        response = client.post("/api/skills/skills/slowpoke/execute",
                               json={"params": {}, "timeout": 0.05}, headers=auth_headers)
        assert response.status_code == 504
        entries = _history(db_session, test_user.id, "slowpoke")
        assert len(entries) == 1 and entries[0].success is False
        row = db_session.query(HermesSkill).filter_by(name="slowpoke").one()
        assert (row.execution_count, row.error_count) == (0, 1)

    def test_no_history_without_row_or_on_rejection(self, client, auth_headers,
                                                    db_session, test_user):
        # Ephemeral (non-promoted) skill: executes, nothing persisted.
        skills_api.get_skill_manager(int(test_user.id)).register("temp", _add)
        assert client.post("/api/skills/skills/temp/execute",
                           json={"params": {"x": 1, "y": 1}},
                           headers=auth_headers).status_code == 200
        assert db_session.query(HermesSkillExecution).count() == 0
        # 404 / 403 paths write nothing either.
        assert client.post("/api/skills/skills/ghost/execute",
                           json={"params": {}}, headers=auth_headers).status_code == 404
        manager = skills_api.get_skill_manager(int(test_user.id))
        manager.set_enabled("temp", False)
        assert client.post("/api/skills/skills/temp/execute",
                           json={"params": {}}, headers=auth_headers).status_code == 403
        assert db_session.query(HermesSkillExecution).count() == 0

    def test_history_is_user_scoped(self, client, auth_headers,
                                    db_session, test_user, second_user):
        from backend.utils.security import create_access_token

        _promoted_row(db_session, test_user.id, "adder")
        skills_api.get_skill_manager(int(test_user.id)).register("adder", _add)
        other_headers = {"Authorization": f"Bearer {create_access_token(data={'sub': int(second_user.id)})}"}
        # Other user has no such skill: 404, and owner's history untouched.
        assert client.post("/api/skills/skills/adder/execute",
                           json={"params": {}}, headers=other_headers).status_code == 404
        client.post("/api/skills/skills/adder/execute",
                    json={"params": {"x": 1, "y": 1}}, headers=auth_headers)
        assert len(_history(db_session, test_user.id, "adder")) == 1
        row = db_session.query(HermesSkill).filter_by(name="adder").one()
        assert (row.execution_count, row.error_count) == (1, 0)

    def test_audit_db_failure_keeps_execution_working(self, client, auth_headers,
                                                      db_session, test_user, monkeypatch):
        _promoted_row(db_session, test_user.id, "adder")
        skills_api.get_skill_manager(int(test_user.id)).register("adder", _add)

        def _boom_commit():
            raise RuntimeError("db gone")

        monkeypatch.setattr(db_session, "commit", _boom_commit)
        response = client.post("/api/skills/skills/adder/execute",
                               json={"params": {"x": 1, "y": 1}}, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["result"] == 2
