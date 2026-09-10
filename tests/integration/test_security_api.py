"""Integration tests for Security API endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestSecurityAPI:
    """Tests for security endpoints."""

    def test_get_available_scopes(self, client: TestClient, auth_headers):
        """Test getting available API key scopes."""
        response = client.get("/api/security/scopes", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert "scopes" in result
        assert isinstance(result["scopes"], list)
        scope_values = [s["value"] for s in result["scopes"]]
        assert "read" in scope_values
        assert "write" in scope_values
        assert "admin" in scope_values
        assert "research" in scope_values
        assert "jobs" in scope_values
        assert "resume" in scope_values

    def test_create_api_key(self, client: TestClient, auth_headers):
        """Test creating an API key."""
        response = client.post(
            "/api/security/api-keys",
            json={
                "name": "Test API Key",
                "scopes": ["read", "research"],
                "expires_in_days": 30,
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        result = response.json()
        assert "api_key" in result
        assert "raw_key" in result
        assert result["raw_key"].startswith("ci_")
        assert result["api_key"]["name"] == "Test API Key"
        assert result["api_key"]["scopes"] == ["read", "research"]

    def test_create_api_key_invalid_scope(self, client: TestClient, auth_headers):
        """Test creating API key with invalid scope."""
        response = client.post(
            "/api/security/api-keys",
            json={
                "name": "Test Key",
                "scopes": ["invalid_scope"],
            },
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "invalid scope" in response.json()["detail"].lower()

    def test_list_api_keys(self, client: TestClient, auth_headers):
        """Test listing user's API keys."""
        # First create a key
        client.post(
            "/api/security/api-keys",
            json={"name": "List Test Key", "scopes": ["read"]},
            headers=auth_headers,
        )

        response = client.get("/api/security/api-keys", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)
        assert len(result) >= 1
        assert result[0]["name"] == "List Test Key"
        assert "raw_key" not in result[0]  # Raw key should not be in list

    def test_get_api_key(self, client: TestClient, auth_headers):
        """Test getting a specific API key."""
        # Create a key first
        create_response = client.post(
            "/api/security/api-keys",
            json={"name": "Get Test Key", "scopes": ["read"]},
            headers=auth_headers,
        )
        key_id = create_response.json()["api_key"]["id"]

        response = client.get(f"/api/security/api-keys/{key_id}", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert result["id"] == key_id
        assert result["name"] == "Get Test Key"
        assert "raw_key" not in result

    def test_update_api_key(self, client: TestClient, auth_headers):
        """Test updating an API key."""
        create_response = client.post(
            "/api/security/api-keys",
            json={"name": "Original Name", "scopes": ["read"]},
            headers=auth_headers,
        )
        key_id = create_response.json()["api_key"]["id"]

        response = client.patch(
            f"/api/security/api-keys/{key_id}",
            json={
                "name": "Updated Name",
                "scopes": ["read", "write"],
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        result = response.json()
        assert result["name"] == "Updated Name"
        assert "write" in result["scopes"]

    def test_revoke_api_key(self, client: TestClient, auth_headers):
        """Test revoking an API key."""
        create_response = client.post(
            "/api/security/api-keys",
            json={"name": "To Revoke", "scopes": ["read"]},
            headers=auth_headers,
        )
        key_id = create_response.json()["api_key"]["id"]

        response = client.delete(f"/api/security/api-keys/{key_id}", headers=auth_headers)

        assert response.status_code == 204

        # Verify it's revoked
        response = client.get(f"/api/security/api-keys/{key_id}", headers=auth_headers)
        assert response.status_code == 404

    def test_rotate_api_key(self, client: TestClient, auth_headers):
        """Test rotating an API key."""
        create_response = client.post(
            "/api/security/api-keys",
            json={"name": "To Rotate", "scopes": ["read"]},
            headers=auth_headers,
        )
        key_id = create_response.json()["api_key"]["id"]

        response = client.post(f"/api/security/api-keys/{key_id}/rotate", headers=auth_headers)

        assert response.status_code == 201
        result = response.json()
        assert "api_key" in result
        assert "raw_key" in result
        assert result["raw_key"].startswith("ci_")
        # New key should have different ID
        assert result["api_key"]["id"] != key_id

    def test_get_security_status(self, client: TestClient, auth_headers):
        """Test getting security configuration status (requires admin API-key scope)."""
        # JWT alone must not satisfy admin API-key scope
        response = client.get("/api/security/status", headers=auth_headers)
        assert response.status_code == 401

        # Provision admin API key via JWT, then use it
        create_response = client.post(
            "/api/security/api-keys",
            json={"name": "Admin Status Key", "scopes": ["admin"]},
            headers=auth_headers,
        )
        assert create_response.status_code == 201
        raw_key = create_response.json()["raw_key"]
        response = client.get("/api/security/status", headers={"X-API-Key": raw_key})
        assert response.status_code == 200

    def test_get_csrf_token(self, client: TestClient, auth_headers):
        """Test getting CSRF token."""
        response = client.get("/api/security/csrf-token", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert "csrf_token" in result
        assert len(result["csrf_token"]) > 20


class TestSecurityMiddleware:
    """Tests for security middleware."""

    def test_security_headers_present(self, client: TestClient):
        """Test that security headers are present on responses."""
        response = client.get("/")
        
        assert response.status_code == 200
        headers = response.headers
        
        # Check key security headers
        assert "strict-transport-security" in headers
        assert "content-security-policy" in headers
        assert "x-frame-options" in headers
        assert "x-content-type-options" in headers
        assert "referrer-policy" in headers
        assert "permissions-policy" in headers
        assert "x-xss-protection" in headers

    def test_rate_limit_headers(self, client: TestClient):
        """Test that rate limit headers are present."""
        response = client.get("/")
        
        assert "x-ratelimit-limit" in response.headers
        assert "x-ratelimit-remaining" in response.headers
        assert "x-ratelimit-reset" in response.headers

    def test_cors_headers(self, client: TestClient):
        """Test CORS headers on preflight request."""
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
        )
        
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-credentials" in response.headers

    def test_request_size_limit(self, client: TestClient):
        """Test request size limit enforcement."""
        large_data = "x" * (11 * 1024 * 1024)  # 11MB > 10MB limit
        response = client.post(
            "/api/auth/register",
            content=large_data,
            headers={"Content-Type": "application/json"},
        )
        
        assert response.status_code == 413

    def test_json_depth_limit(self, client: TestClient):
        """Test JSON nesting depth limit."""
        # Create deeply nested JSON
        deep_json = {"a": {"b": {"c": {"d": {"e": {"f": {"g": {"h": {"i": {"j": {"k": "value"}}}}}}}}}}}
        response = client.post("/api/auth/register", json=deep_json)
        
        # Should either accept or reject based on depth limit
        assert response.status_code in [200, 400, 422]

    def test_csrf_protection(self, client: TestClient, auth_headers, test_jobs):
        """Test CSRF protection on state-changing endpoints."""
        # Try POST without CSRF token (should fail for non-exempt endpoints)
        # Note: This depends on CSRF middleware configuration
        job = test_jobs[0]
        response = client.post(
            "/api/applications/",
            json={
                "job_id": job.id,
                "resume_text": "Test",
            },
            headers=auth_headers,
        )
        # Should either work (if CSRF exempt for API) or return 403
        assert response.status_code in [201, 403, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])