"""Tests for social OAuth connection + token management (no publishing)."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from backend.config import settings
from backend.models.social_account import SocialAccount
from backend.services.social_account_service import SocialAccountService
from backend.social_integrations import oauth
from backend.social_integrations.oauth import OAuthError
from backend.social_integrations.token_crypto import decrypt_token, encrypt_token


@pytest.fixture
def creds(monkeypatch):
    monkeypatch.setattr(settings, "LINKEDIN_CLIENT_ID", "li-id")
    monkeypatch.setattr(settings, "LINKEDIN_CLIENT_SECRET", "li-secret")
    monkeypatch.setattr(settings, "FACEBOOK_APP_ID", "fb-id")
    monkeypatch.setattr(settings, "FACEBOOK_APP_SECRET", "fb-secret")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "go-id")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "go-secret")
    monkeypatch.setattr(settings, "FRONTEND_URL", "http://localhost:5173")


TOKENS = {"access_token": "access-123", "refresh_token": "refresh-123", "expires_in": 3600}
PROFILE = {"platform_user_id": "p-1", "display_name": "Test Person", "raw": {"id": "p-1"}}


def _service(db_session, **overrides):
    return SocialAccountService(db_session)


class TestAuthorizeUrls:
    @pytest.mark.parametrize("platform,host", [
        ("linkedin", "linkedin.com"),
        ("instagram", "facebook.com"),
        ("facebook", "facebook.com"),
        ("youtube", "accounts.google.com"),
    ])
    def test_official_hosts_and_no_secrets(self, platform, host):
        url = oauth.build_authorize_url(
            platform, client_id="cid", redirect_uri="http://localhost:5173/social/callback",
            state="state-123",
        )
        assert host in url
        assert "client_id=cid" in url
        assert "state=state-123" in url
        assert "secret" not in url.lower()

    def test_unknown_platform_rejected(self):
        with pytest.raises(OAuthError):
            oauth.build_authorize_url("myspace", "cid", "http://x/", "s")


class TestTokenCrypto:
    def test_round_trip(self):
        stored = encrypt_token("super-secret-token")
        assert stored.startswith("fernet:")
        assert decrypt_token(stored) == "super-secret-token"

    def test_legacy_plaintext_rejected(self):
        with pytest.raises(ValueError):
            decrypt_token("plain-old-token")


class TestConnectFlow:
    def test_begin_returns_url_and_state(self, db_session, test_user, creds):
        service = _service(db_session)
        result = service.begin_connect(test_user.id, "linkedin")
        assert result["authorization_url"].startswith("https://www.linkedin.com")
        assert result["state"]

    def test_begin_unknown_platform(self, db_session, test_user, creds):
        with pytest.raises(OAuthError):
            _service(db_session).begin_connect(test_user.id, "myspace")

    def test_begin_requires_configured_credentials(self, db_session, test_user):
        with pytest.raises(OAuthError):
            _service(db_session).begin_connect(test_user.id, "linkedin")

    @pytest.mark.asyncio
    async def test_complete_persists_encrypted(self, db_session, test_user, creds):
        service = _service(db_session)
        begun = service.begin_connect(test_user.id, "linkedin")
        with patch.object(oauth, "exchange_code", new=AsyncMock(return_value=dict(TOKENS))), \
             patch.object(oauth, "fetch_profile", new=AsyncMock(return_value=dict(PROFILE))):
            account = await service.complete_connect(
                test_user.id, "linkedin", "authcode-1", begun["state"])
        assert account["platform"] == "linkedin"
        assert account["account_id"] == "p-1"
        assert "access_token" not in account and "refresh_token" not in account
        row = db_session.query(SocialAccount).filter_by(id=account["id"]).first()
        assert row.access_token.startswith("fernet:")
        assert decrypt_token(row.access_token) == "access-123"
        assert decrypt_token(row.refresh_token) == "refresh-123"
        assert row.token_expires_at is not None and row.token_expires_at > datetime.utcnow()

    @pytest.mark.asyncio
    async def test_reconnect_updates_without_duplicates(self, db_session, test_user, creds):
        service = _service(db_session)
        begun = service.begin_connect(test_user.id, "linkedin")
        new_tokens = dict(TOKENS, access_token="access-456")
        with patch.object(oauth, "exchange_code", new=AsyncMock(return_value=new_tokens)), \
             patch.object(oauth, "fetch_profile", new=AsyncMock(return_value=dict(PROFILE))):
            first = await service.complete_connect(test_user.id, "linkedin", "c1", begun["state"])
            begun2 = service.begin_connect(test_user.id, "linkedin")
            second = await service.complete_connect(test_user.id, "linkedin", "c2", begun2["state"])
        assert first["id"] == second["id"]
        assert db_session.query(SocialAccount).count() == 1

    @pytest.mark.asyncio
    async def test_tampered_state_rejected(self, db_session, test_user, creds):
        service = _service(db_session)
        begun = service.begin_connect(test_user.id, "linkedin")
        with pytest.raises(OAuthError):
            await service.complete_connect(test_user.id, "linkedin", "c", begun["state"] + "x")

    @pytest.mark.asyncio
    async def test_cross_user_state_rejected(self, db_session, test_user, second_user, creds):
        service = _service(db_session)
        begun = service.begin_connect(test_user.id, "linkedin")
        with pytest.raises(OAuthError):
            await service.complete_connect(second_user.id, "linkedin", "c", begun["state"])

    @pytest.mark.asyncio
    async def test_cross_platform_state_rejected(self, db_session, test_user, creds):
        service = _service(db_session)
        begun = service.begin_connect(test_user.id, "linkedin")
        with pytest.raises(OAuthError):
            await service.complete_connect(test_user.id, "youtube", "c", begun["state"])


class TestRefreshDisconnectList:
    async def _connected(self, db_session, test_user, creds):
        service = _service(db_session)
        begun = service.begin_connect(test_user.id, "youtube")
        with patch.object(oauth, "exchange_code", new=AsyncMock(return_value=dict(TOKENS))), \
             patch.object(oauth, "fetch_profile", new=AsyncMock(return_value=dict(PROFILE))):
            return service, await service.complete_connect(
                test_user.id, "youtube", "c", begun["state"])

    @pytest.mark.asyncio
    async def test_refresh_updates_tokens(self, db_session, test_user, creds):
        service, account = await self._connected(db_session, test_user, creds)
        fresh = dict(TOKENS, access_token="access-789", expires_in=7200)
        with patch.object(oauth, "refresh_access_token", new=AsyncMock(return_value=fresh)):
            updated = await service.refresh_account(test_user.id, account["id"])
        assert updated["id"] == account["id"]
        row = db_session.query(SocialAccount).filter_by(id=account["id"]).first()
        assert decrypt_token(row.access_token) == "access-789"

    @pytest.mark.asyncio
    async def test_ownership_enforced(self, db_session, test_user, second_user, creds):
        service, account = await self._connected(db_session, test_user, creds)
        with pytest.raises(OAuthError):
            await service.refresh_account(second_user.id, account["id"])
        with pytest.raises(OAuthError):
            await service.disconnect_account(second_user.id, account["id"])
        # Owner's row untouched.
        assert db_session.query(SocialAccount).filter_by(id=account["id"]).first() is not None

    @pytest.mark.asyncio
    async def test_disconnect_deletes(self, db_session, test_user, creds):
        service, account = await self._connected(db_session, test_user, creds)
        with patch.object(SocialAccountService, "_revoke_remote", new=AsyncMock(return_value=None)):
            result = await service.disconnect_account(test_user.id, account["id"])
        assert result["success"] is True
        assert db_session.query(SocialAccount).filter_by(id=account["id"]).first() is None

    def test_list_redacted(self, db_session, test_user):
        db_session.add(SocialAccount(
            user_id=test_user.id, platform="linkedin", account_id="p-9",
            account_name="Someone", access_token=encrypt_token("tok"),
        ))
        db_session.commit()
        accounts = _service(db_session).list_accounts(test_user.id)
        assert len(accounts) == 1
        assert "access_token" not in accounts[0] and "refresh_token" not in accounts[0]
        assert accounts[0]["account_id"] == "p-9"


class TestSocialAPI:
    def test_connect_initiation(self, client, auth_headers, creds):
        response = client.post(
            "/api/social/accounts/connect", headers=auth_headers,
            json={"platform": "linkedin"},
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["authorization_url"].startswith("https://www.linkedin.com")
        assert body["state"]

    def test_connect_unknown_platform(self, client, auth_headers, creds):
        response = client.post(
            "/api/social/accounts/connect", headers=auth_headers,
            json={"platform": "myspace"},
        )
        assert response.status_code == 400

    def test_connect_requires_config(self, client, auth_headers):
        response = client.post(
            "/api/social/accounts/connect", headers=auth_headers,
            json={"platform": "linkedin"},
        )
        assert response.status_code == 503

    def test_disconnect_missing_is_404(self, client, auth_headers):
        response = client.delete("/api/social/accounts/999999", headers=auth_headers)
        assert response.status_code == 404

    def test_requires_auth(self, client):
        assert client.get("/api/social/accounts").status_code in (401, 403)
