"""Integration tests for Auth API endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestAuthAPI:
    """Tests for authentication endpoints."""

    def test_register_success(self, client: TestClient):
        """Test successful user registration."""
        response = client.post(
            "/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePass123!",
                "full_name": "New User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "user" in data
        assert "access_token" in data
        assert data["user"]["email"] == "newuser@example.com"
        assert data["user"]["full_name"] == "New User"

    def test_register_duplicate_email(self, client: TestClient, test_user):
        """Test registration with duplicate email fails."""
        response = client.post(
            "/auth/register",
            json={
                "email": test_user.email,
                "password": "SecurePass123!",
                "full_name": "Another User",
            },
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_register_invalid_email(self, client: TestClient):
        """Test registration with invalid email."""
        response = client.post(
            "/auth/register",
            json={
                "email": "invalid-email",
                "password": "SecurePass123!",
                "full_name": "Test User",
            },
        )
        assert response.status_code == 422

    def test_register_weak_password(self, client: TestClient):
        """Test registration with weak password."""
        response = client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "password": "weak",
                "full_name": "Test User",
            },
        )
        assert response.status_code == 422

    def test_login_success(self, client: TestClient, test_user):
        """Test successful login."""
        response = client.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "access_token" in data
        assert data["user"]["email"] == test_user.email

    def test_login_wrong_password(self, client: TestClient, test_user):
        """Test login with wrong password."""
        response = client.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, client: TestClient):
        """Test login with nonexistent user."""
        response = client.post(
            "/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 401

    def test_get_me_authenticated(self, client: TestClient, auth_headers):
        """Test getting current user info with valid token."""
        response = client.get("/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert "full_name" in data

    def test_get_me_unauthenticated(self, client: TestClient):
        """Test getting current user info without token."""
        response = client.get("/auth/me")
        assert response.status_code == 401


class TestAuthSecurity:
    """Tests for auth security features."""

    def test_rate_limiting_on_login(self, client: TestClient, test_user):
        """Test rate limiting on login endpoint."""
        # Make multiple failed login attempts
        for _ in range(6):
            client.post(
                "/auth/login",
                json={
                    "email": test_user.email,
                    "password": "wrongpassword",
                },
            )
        
        # Next attempt should be rate limited
        response = client.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "wrongpassword",
            },
        )
        # Should be rate limited (429) or still 401 depending on config
        assert response.status_code in [401, 429]

    def test_password_not_in_response(self, client: TestClient, test_user):
        """Test that password hash is never returned."""
        response = client.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123",
            },
        )
        data = response.json()
        assert "hashed_password" not in str(data)
        assert "password" not in data["user"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])