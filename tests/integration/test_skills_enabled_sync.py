"""
Step D tests: DB enabled-state synchronization at execute time.

The persisted row is authoritative: an explicit False denies execution
even when memory says enabled. Missing rows (ephemeral skills) and DB
lookup failures defer to the in-memory gate (availability preserved).
"""

from __future__ import annotations

import pytest

from backend.api import skills as skills_api
from backend.models.hermes_skill import HermesSkill


async def _add(x, y):
    return x + y


@pytest.fixture(autouse=True)
def _clean_state():
    skills_api._managers.clear()
    skills_api._reconciled.clear()
    yield
    skills_api._managers.clear()
    skills_api._reconciled.clear()


def _row(db_session, user_id, name, enabled=True):
    row = HermesSkill(name=name, description=f"{name} skill",
                      enabled=enabled, user_id=user_id)
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


class TestDbEnabledSync:
    def test_db_disabled_overrides_memory_enabled(self, client, auth_headers,
                                                  db_session, test_user):
        _row(db_session, test_user.id, "gated", enabled=False)
        skills_api.get_skill_manager(int(test_user.id)).register("gated", _add)
        response = client.post("/api/skills/skills/gated/execute",
                               json={"params": {"x": 1, "y": 1}}, headers=auth_headers)
        assert response.status_code == 403
        manager = skills_api.get_skill_manager(int(test_user.id))
        assert manager.get("gated")["execution_count"] == 0

    def test_db_enabled_plus_memory_enabled_executes(self, client, auth_headers,
                                                     db_session, test_user):
        _row(db_session, test_user.id, "live", enabled=True)
        skills_api.get_skill_manager(int(test_user.id)).register("live", _add)
        response = client.post("/api/skills/skills/live/execute",
                               json={"params": {"x": 2, "y": 3}}, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["result"] == 5

    def test_no_row_defers_to_memory(self, client, auth_headers, test_user):
        skills_api.get_skill_manager(int(test_user.id)).register("ephemeral", _add)
        response = client.post("/api/skills/skills/ephemeral/execute",
                               json={"params": {"x": 1, "y": 1}}, headers=auth_headers)
        assert response.status_code == 200

    def test_memory_disabled_still_blocks_when_db_enabled(self, client, auth_headers,
                                                          db_session, test_user):
        _row(db_session, test_user.id, "revoked", enabled=True)
        manager = skills_api.get_skill_manager(int(test_user.id))
        manager.register("revoked", _add)
        manager.set_enabled("revoked", False)
        response = client.post("/api/skills/skills/revoked/execute",
                               json={"params": {}}, headers=auth_headers)
        assert response.status_code == 403

    def test_db_lookup_failure_returns_none(self):
        class _BadDB:
            def query(self, *args, **kwargs):
                raise RuntimeError("db gone")

        assert skills_api._db_enabled(_BadDB(), 1, "x") is None

    def test_other_users_row_ignored(self, client, auth_headers,
                                     db_session, test_user, second_user):
        _row(db_session, second_user.id, "theirs", enabled=False)
        skills_api.get_skill_manager(int(test_user.id)).register("theirs", _add)
        response = client.post("/api/skills/skills/theirs/execute",
                               json={"params": {"x": 1, "y": 1}}, headers=auth_headers)
        assert response.status_code == 200
