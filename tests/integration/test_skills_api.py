"""
Step 4 tests: /api/skills wired to the real per-user skill backend.

Covers list/get/search/stats/execute, authentication, per-user
authorization, disabled-skill (403) and unapproved-name (404) rejection,
and proof that read operations never execute.
"""

from __future__ import annotations

import pytest

from backend.api import skills as skills_api
from backend.utils.security import create_access_token


async def _add(x, y):
    return x + y


async def _slow(**kwargs):
    import asyncio

    await asyncio.sleep(5)
    return "done"


@pytest.fixture(autouse=True)
def _clean_managers():
    skills_api._managers.clear()
    skills_api._reconciled.clear()
    yield
    skills_api._managers.clear()
    skills_api._reconciled.clear()


@pytest.fixture
def seeded_user(client, test_user):
    skills_api.get_skill_manager(int(test_user.id)).register(
        "add", _add, description="Add numbers", tags=["math"])
    return test_user


def _headers_for(user):
    return {"Authorization": f"Bearer {create_access_token(data={'sub': int(user.id)})}"}


class TestListGetSearchStats:
    def test_list_empty(self, client, auth_headers):
        response = client.get("/api/skills/skills", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == {"skills": [], "total": 0}

    def test_list_and_tag_filter(self, client, auth_headers, seeded_user):
        manager = skills_api.get_skill_manager(int(seeded_user.id))
        manager.register("echo", _add, description="Echo", tags=["misc"])
        body = client.get("/api/skills/skills", headers=auth_headers).json()
        assert body["total"] == 2
        filtered = client.get("/api/skills/skills", params={"tag": "math"},
                              headers=auth_headers).json()
        assert [s["name"] for s in filtered["skills"]] == ["add"]

    def test_get_ok(self, client, auth_headers, seeded_user):
        body = client.get("/api/skills/skills/add", headers=auth_headers).json()
        assert body["name"] == "add"
        assert body["description"] == "Add numbers"
        assert body["execution_count"] == 0

    def test_get_missing_404(self, client, auth_headers):
        response = client.get("/api/skills/skills/ghost", headers=auth_headers)
        assert response.status_code == 404

    def test_search(self, client, auth_headers, seeded_user):
        body = client.get("/api/skills/skills/search", params={"query": "add"},
                          headers=auth_headers).json()
        assert body["total"] == 1
        assert body["results"][0]["name"] == "add"
        empty = client.get("/api/skills/skills/search", params={"query": "zzz"},
                           headers=auth_headers).json()
        assert empty == {"results": [], "total": 0}

    def test_stats(self, client, auth_headers, seeded_user):
        client.post("/api/skills/skills/add/execute", json={"params": {"x": 1, "y": 2}},
                    headers=auth_headers)
        body = client.get("/api/skills/skills/stats", headers=auth_headers).json()
        assert body == {"total_skills": 1, "total_executions": 1,
                        "successful": 1, "failed": 0}


class TestExecute:
    def test_execute_ok(self, client, auth_headers, seeded_user):
        response = client.post("/api/skills/skills/add/execute",
                               json={"params": {"x": 2, "y": 3}}, headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == {"success": True, "skill": "add", "result": 5}

    def test_execute_missing_404(self, client, auth_headers):
        response = client.post("/api/skills/skills/ghost/execute",
                               json={"params": {}}, headers=auth_headers)
        assert response.status_code == 404

    def test_execute_disabled_403_and_uncounted(self, client, auth_headers, seeded_user):
        manager = skills_api.get_skill_manager(int(seeded_user.id))
        assert manager.set_enabled("add", False) is True
        response = client.post("/api/skills/skills/add/execute",
                               json={"params": {"x": 1, "y": 1}}, headers=auth_headers)
        assert response.status_code == 403
        assert manager.get("add")["execution_count"] == 0
        assert manager.get_stats()["total_executions"] == 0

    def test_execute_timeout_504(self, client, auth_headers, seeded_user):
        skills_api.get_skill_manager(int(seeded_user.id)).register("slow", _slow)
        response = client.post("/api/skills/skills/slow/execute",
                               json={"params": {}, "timeout": 0.05}, headers=auth_headers)
        assert response.status_code == 504

    def test_read_ops_never_execute(self, client, auth_headers, seeded_user):
        client.get("/api/skills/skills", headers=auth_headers)
        client.get("/api/skills/skills/add", headers=auth_headers)
        client.get("/api/skills/skills/search", params={"query": "add"},
                   headers=auth_headers)
        client.get("/api/skills/skills/stats", headers=auth_headers)
        manager = skills_api.get_skill_manager(int(seeded_user.id))
        assert manager.get("add")["execution_count"] == 0
        client.post("/api/skills/skills/add/execute", json={"params": {"x": 1, "y": 1}},
                    headers=auth_headers)
        assert manager.get("add")["execution_count"] == 1


class TestAuthAndIsolation:
    @pytest.mark.parametrize("method,url", [
        ("GET", "/api/skills/skills"),
        ("GET", "/api/skills/skills/add"),
        ("GET", "/api/skills/skills/search"),
        ("GET", "/api/skills/skills/stats"),
    ])
    def test_reads_require_auth(self, client, method, url):
        params = {"query": "x"} if url.endswith("/search") else None
        response = client.request(method, url, params=params)
        assert response.status_code in (401, 403)

    def test_execute_requires_auth(self, client):
        response = client.post("/api/skills/skills/add/execute", json={"params": {}})
        assert response.status_code in (401, 403)

    def test_users_cannot_access_each_others_skills(self, client, auth_headers,
                                                    seeded_user, second_user):
        other_headers = _headers_for(second_user)
        assert client.get("/api/skills/skills", headers=other_headers).json() == {
            "skills": [], "total": 0}
        assert client.get("/api/skills/skills/add", headers=other_headers).status_code == 404
        assert client.post("/api/skills/skills/add/execute", json={"params": {}},
                           headers=other_headers).status_code == 404
        # Owner unaffected.
        assert client.get("/api/skills/skills", headers=auth_headers).json()["total"] == 1

    def test_unapproved_name_rejected(self, client, auth_headers):
        # Never promoted/registered names exist nowhere: 404, never executed.
        assert client.post("/api/skills/skills/would-be-skill/execute",
                           json={"params": {}}, headers=auth_headers).status_code == 404
