"""
Tests for social integrations.
"""

import pytest
import asyncio
from backend.social_integrations.base import BaseIntegration
from backend.social_integrations.oauth_manager import OAuthManager
from backend.social_integrations.token_manager import TokenManager
from backend.social_integrations.instagram import InstagramIntegration
from backend.social_integrations.linkedin import LinkedInIntegration


@pytest.fixture
def oauth_manager():
    return OAuthManager()


@pytest.fixture
def token_manager():
    return TokenManager()


class TestOAuthManager:
    def test_register_provider(self, oauth_manager):
        oauth_manager.register_provider(
            "linkedin",
            "client_id",
            "client_secret",
            "https://auth.linkedin.com",
            "https://api.linkedin.com/oauth/token",
        )
        url = oauth_manager.get_auth_url("linkedin", "http://localhost/callback")
        assert "client_id" in url


class TestTokenManager:
    def test_store_and_get(self, token_manager):
        token_manager.store("linkedin", "user1", "token123")
        token = token_manager.get("linkedin", "user1")
        assert token == "token123"

    def test_revoke(self, token_manager):
        token_manager.store("linkedin", "user1", "token123")
        revoked = token_manager.revoke("linkedin", "user1")
        assert revoked


class TestInstagramIntegration:
    @pytest.mark.asyncio
    async def test_connect(self):
        integration = InstagramIntegration()
        connected = await integration.connect()
        assert connected

    @pytest.mark.asyncio
    async def test_post(self):
        integration = InstagramIntegration()
        await integration.connect()
        result = await integration.post("Hello Instagram")
        assert result["status"] == "posted"


class TestLinkedInIntegration:
    @pytest.mark.asyncio
    async def test_connect(self):
        integration = LinkedInIntegration()
        connected = await integration.connect()
        assert connected

    @pytest.mark.asyncio
    async def test_post(self):
        integration = LinkedInIntegration()
        await integration.connect()
        result = await integration.post("Hello LinkedIn")
        assert result["status"] == "posted"
