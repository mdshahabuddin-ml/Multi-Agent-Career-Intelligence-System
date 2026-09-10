"""Tests for official-API publishing (all HTTP mocked; no network).

Covers per-platform success shapes, 401-refresh-once, retryable vs
permanent errors, duplicate suppression, dry-run purity, max attempts,
and secret hygiene in logged errors. Publishing dispatch itself is
exercised through the real service + scheduler with fakes.
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from backend.models.content_calendar import ContentCalendar, ContentStatus, SocialPlatform
from backend.models.social_account import SocialAccount
from backend.services.content_scheduler import ContentScheduler
from backend.services.publishing_service import PublishingService
from backend.services.social_account_service import SocialAccountService
from backend.social_integrations import publisher
from backend.social_integrations.publisher import (
    PermanentPublishError,
    RetryablePublishError,
    TokenExpiredError,
    plan_publish,
)
from backend.social_integrations.token_crypto import encrypt_token

FUTURE = datetime.utcnow() + timedelta(days=30)


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, headers=None, text=""):
        self.status_code = status_code
        self._json = json_data
        self.headers = headers or {}
        self.text = text

    def json(self):
        if self._json is None:
            raise ValueError("no json body")
        return self._json


class FakeAsyncClient:
    """Canned per-(method, url-substring) responses; records requests."""

    canned = {}
    seen = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    @classmethod
    def reset(cls):
        cls.canned = {}
        cls.seen = []

    @classmethod
    def on(cls, method, url_part, response):
        cls.canned.setdefault((method.upper(), url_part), []).append(response)

    async def _handle(self, method, url, **kwargs):
        FakeAsyncClient.seen.append({"method": method, "url": url, "kwargs": kwargs})
        for (m, part), queue in list(FakeAsyncClient.canned.items()):
            if m == method and part in url and queue:
                return queue.pop(0)
        raise AssertionError(f"unexpected HTTP call: {method} {url}")

    async def get(self, url, **kwargs):
        return await self._handle("GET", url, **kwargs)

    async def post(self, url, **kwargs):
        return await self._handle("POST", url, **kwargs)

    async def put(self, url, **kwargs):
        return await self._handle("PUT", url, **kwargs)

    async def request(self, method, url, **kwargs):
        return await self._handle(method.upper(), url, **kwargs)


@pytest.fixture
def fake_http(monkeypatch):
    FakeAsyncClient.reset()
    monkeypatch.setattr(publisher.httpx, "AsyncClient", FakeAsyncClient)
    return FakeAsyncClient


@pytest.fixture
def account(db_session, test_user):
    row = SocialAccount(
        user_id=test_user.id, platform="linkedin", account_id="person-1",
        account_name="Test Person", access_token=encrypt_token("tok-live-1"),
        refresh_token=encrypt_token("tok-refresh-1"),
        token_expires_at=FUTURE, enabled=True,
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


def _item(db_session, test_user, platform="linkedin", status=ContentStatus.SCHEDULED,
          text="Hello world from the test suite"):
    row = ContentCalendar(
        user_id=test_user.id, title="T", content=text, platform=platform,
        status=status, scheduled_at=datetime.utcnow() - timedelta(minutes=1),
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


class TestLinkedInPublish:
    @pytest.mark.asyncio
    async def test_text_post_success(self, fake_http):
        fake_http.on("GET", "userinfo", FakeResponse(200, {"sub": "person-1", "name": "T"}))
        fake_http.on("POST", "ugcPosts", FakeResponse(201, {}, {"x-restli-id": "urn:li:share:abc"}))
        outcome = await publisher.publish_linkedin("tok", "Hello LinkedIn")
        assert outcome["platform_post_id"] == "urn:li:share:abc"
        auth_headers = [r["kwargs"].get("headers", {}).get("Authorization")
                        for r in fake_http.seen if r["method"] == "POST"]
        assert auth_headers and all(h == "Bearer tok" for h in auth_headers)

    @pytest.mark.asyncio
    async def test_expired_token_signalled(self, fake_http):
        fake_http.on("GET", "userinfo", FakeResponse(200, {"sub": "person-1"}))
        fake_http.on("POST", "ugcPosts", FakeResponse(401, {"message": "Expired"}))
        with pytest.raises(TokenExpiredError):
            await publisher.publish_linkedin("tok", "Hello")

    def test_dry_run_shape(self):
        plan = plan_publish("linkedin", {"text": "Hello world"})
        assert plan["proceeding"] is True
        assert any(c["name"] == "within_limit" and c["ok"] for c in plan["checks"])
        bad = plan_publish("instagram", {"text": "no media here"})
        assert bad["proceeding"] is False


class TestInstagramFacebook:
    @pytest.mark.asyncio
    async def test_photo_success(self, fake_http):
        fake_http.on("GET", "me/accounts", FakeResponse(200, {"data": [
            {"id": "page-1", "access_token": "page-tok",
             "instagram_business_account": {"id": "ig-1"}}]}))
        fake_http.on("POST", "/media", FakeResponse(200, {"id": "container-1"}))
        fake_http.on("POST", "media_publish", FakeResponse(200, {"id": "media-9"}))
        outcome = await publisher.publish_instagram(
            "user-tok", "Nice photo", image_url="https://example.com/a.jpg")
        assert outcome["platform_post_id"] == "media-9"

    @pytest.mark.asyncio
    async def test_reel_container_error_permanent(self, fake_http):
        fake_http.on("GET", "me/accounts", FakeResponse(200, {"data": [
            {"id": "page-1", "access_token": "page-tok",
             "instagram_business_account": {"id": "ig-1"}}]}))
        fake_http.on("POST", "/media", FakeResponse(400, {"error": {"message": "bad video"}}))
        with pytest.raises(PermanentPublishError):
            await publisher.publish_instagram("user-tok", "Reel", video_url="https://example.com/v.mp4")

    @pytest.mark.asyncio
    async def test_facebook_feed_success(self, fake_http):
        fake_http.on("GET", "me/accounts", FakeResponse(200, {"data": [
            {"id": "page-7", "name": "P", "access_token": "page-tok"}]}))
        fake_http.on("POST", "/feed", FakeResponse(200, {"id": "page-7_123"}))
        outcome = await publisher.publish_facebook("user-tok", "Hello page")
        assert outcome["platform_post_id"] == "page-7_123"

    @pytest.mark.asyncio
    async def test_rate_limit_retryable(self, fake_http):
        fake_http.on("GET", "me/accounts", FakeResponse(200, {"data": [
            {"id": "page-7", "access_token": "page-tok"}]}))
        fake_http.on("POST", "/feed", FakeResponse(429, {"error": {"message": "throttled"}}))
        with pytest.raises(RetryablePublishError):
            await publisher.publish_facebook("user-tok", "Hello")


class TestYouTubePublish:
    @pytest.mark.asyncio
    async def test_resumable_upload_ids(self, fake_http):
        FakeAsyncClient.on("POST", "upload/youtube", FakeResponse(
            200, {}, {"location": "https://upload.example/session/1"}))
        FakeAsyncClient.on("PUT", "upload.example", FakeResponse(200, {"id": "vid-1"}))
        outcome = await publisher.publish_youtube("tok", "My title", "Desc", video_bytes=b"0" * 100)
        assert outcome["platform_post_id"] == "vid-1"
        assert outcome["platform_post_url"] == "https://www.youtube.com/watch?v=vid-1"


class TestServiceFlow:
    @pytest.mark.asyncio
    async def test_publish_item_success(self, db_session, test_user, account, fake_http):
        item = _item(db_session, test_user)
        fake_http.on("GET", "userinfo", FakeResponse(200, {"sub": "person-1"}))
        fake_http.on("POST", "ugcPosts", FakeResponse(201, {}, {"x-restli-id": "urn:li:share:z"}))
        service = PublishingService(db_session)
        result = await service.publish_item(test_user.id, item.id)
        assert result.status == ContentStatus.PUBLISHED
        assert result.platform_post_id == "urn:li:share:z"
        assert result.published_at is not None

    @pytest.mark.asyncio
    async def test_midflight_401_refreshes_once(self, db_session, test_user, account,
                                               fake_http, monkeypatch):
        import backend.config as config_module
        monkeypatch.setattr(config_module.settings, "LINKEDIN_CLIENT_ID", "cid")
        monkeypatch.setattr(config_module.settings, "LINKEDIN_CLIENT_SECRET", "csec")
        item = _item(db_session, test_user)
        fake_http.on("GET", "userinfo", FakeResponse(200, {"sub": "person-1"}))
        fake_http.on("POST", "ugcPosts", FakeResponse(401, {"message": "expired"}))
        fake_http.on("POST", "accessToken", FakeResponse(200, {
            "access_token": "tok-live-2", "expires_in": 3600}))
        fake_http.on("GET", "userinfo", FakeResponse(200, {"sub": "person-1"}))
        fake_http.on("POST", "ugcPosts", FakeResponse(201, {}, {"x-restli-id": "urn:li:share:r2"}))
        service = PublishingService(db_session)
        result = await service.publish_item(test_user.id, item.id)
        assert result.status == ContentStatus.PUBLISHED
        assert result.platform_post_id == "urn:li:share:r2"

    @pytest.mark.asyncio
    async def test_duplicate_skips_http(self, db_session, test_user, account, fake_http):
        item = _item(db_session, test_user)
        item.platform_post_id = "urn:li:share:old"
        db_session.commit()
        service = PublishingService(db_session)
        outcome = await service._publish_only(test_user.id, item.id)
        assert outcome["already_published"] is True
        assert FakeAsyncClient.seen == []

    @pytest.mark.asyncio
    async def test_retryable_marks_failed(self, db_session, test_user, account, fake_http):
        item = _item(db_session, test_user)
        fake_http.on("GET", "userinfo", FakeResponse(200, {"sub": "person-1"}))
        fake_http.on("POST", "ugcPosts", FakeResponse(503, {"message": "down"}))
        service = PublishingService(db_session)
        result = await service.publish_item(test_user.id, item.id)
        assert result.status == ContentStatus.FAILED
        assert result.retry_count == 1

    @pytest.mark.asyncio
    async def test_secrets_never_logged(self, db_session, test_user, account, fake_http):
        item = _item(db_session, test_user)
        fake_http.on("GET", "userinfo", FakeResponse(200, {"sub": "person-1"}))
        fake_http.on("POST", "ugcPosts", FakeResponse(400, {"error": {"message": "nope"}}))
        service = PublishingService(db_session)
        result = await service.publish_item(test_user.id, item.id)
        assert "tok-live-1" not in (result.error_message or "")

    @pytest.mark.asyncio
    async def test_no_account_is_permanent(self, db_session, test_user):
        item = _item(db_session, test_user)
        service = PublishingService(db_session)
        result = await service.publish_item(test_user.id, item.id)
        assert result.status == ContentStatus.FAILED
        assert "no connected" in (result.error_message or "")

    def test_dry_run_pure(self, db_session, test_user, account, fake_http):
        item = _item(db_session, test_user)
        service = PublishingService(db_session)
        report = service.dry_run_item(test_user.id, item.id)
        assert report["proceeding"] is True
        assert FakeAsyncClient.seen == []
        assert report["would_post"]["platform"] == "linkedin"

    def test_max_attempts_skips(self, db_session, test_user):
        item = _item(db_session, test_user)
        item.retry_count = 3
        db_session.commit()
        summary = ContentScheduler(db_session).run(test_user.id, lambda i: {"platform_post_id": "x"})
        assert summary["skipped"] == 1
        assert summary["published"] == 0
        db_session.refresh(item)
        assert item.status == ContentStatus.SCHEDULED


class TestPublishEndpoints:
    def _scheduled_item(self, db_session, test_user, run_id=None):
        item = ContentCalendar(
            user_id=test_user.id, title="T", content="Hello world",
            platform="linkedin", status=ContentStatus.SCHEDULED,
            scheduled_at=datetime.utcnow() - timedelta(minutes=1),
            pipeline_run_id=run_id,
        )
        db_session.add(item)
        db_session.commit()
        db_session.refresh(item)
        return item

    def _account(self, db_session, test_user):
        db_session.add(SocialAccount(
            user_id=test_user.id, platform="linkedin", account_id="person-1",
            access_token=encrypt_token("tok-live-1"),
            refresh_token=encrypt_token("tok-refresh-1"),
            token_expires_at=datetime.utcnow() + timedelta(days=30)))
        db_session.commit()

    def test_publish_scheduled_item(self, client, auth_headers, db_session, test_user):
        item = self._scheduled_item(db_session, test_user)
        self._account(db_session, test_user)
        body = {"source": "profile", "content_kind": "linkedin_post", "platforms": ["linkedin"]}
        with _patched_linkedin_success():
            response = client.post(f"/api/content-calendar/{item.id}/publish",
                                   headers=auth_headers)
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "published"
        assert response.json()["platform_post_id"] == "urn:li:share:z"

    def test_publish_draft_refused(self, client, auth_headers, db_session, test_user):
        item = ContentCalendar(
            user_id=test_user.id, title="T", content="Hello",
            platform="linkedin", status=ContentStatus.DRAFT)
        db_session.add(item)
        db_session.commit()
        response = client.post(f"/api/content-calendar/{item.id}/publish", headers=auth_headers)
        assert response.status_code == 400

    def test_publish_missing_is_404(self, client, auth_headers):
        response = client.post("/api/content-calendar/999999/publish", headers=auth_headers)
        assert response.status_code == 404

    def test_dry_run_endpoint(self, client, auth_headers, db_session, test_user):
        item = self._scheduled_item(db_session, test_user)
        self._account(db_session, test_user)
        response = client.post(f"/api/content-calendar/{item.id}/publish/dry-run",
                               headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["proceeding"] is True
        db_session.refresh(item)
        assert item.status == ContentStatus.SCHEDULED  # unchanged


from contextlib import contextmanager


@contextmanager
def _patched_linkedin_success():
    from backend.social_integrations import publisher as publisher_module
    FakeAsyncClient.reset()
    FakeAsyncClient.on("GET", "userinfo", FakeResponse(200, {"sub": "person-1"}))
    FakeAsyncClient.on("POST", "ugcPosts", FakeResponse(201, {}, {"x-restli-id": "urn:li:share:z"}))
    with patch.object(publisher_module.httpx, "AsyncClient", FakeAsyncClient):
        yield
