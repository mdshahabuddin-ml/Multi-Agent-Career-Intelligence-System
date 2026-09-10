"""
Tests for Hermes browser module.
"""

import pytest
import asyncio
from backend.hermes_engine.browser.browser_manager import BrowserManager
from backend.hermes_engine.browser.web_navigator import WebNavigator
from backend.hermes_engine.browser.browser_session import BrowserSession


@pytest.fixture
def browser_manager():
    return BrowserManager()


@pytest.fixture
def web_navigator():
    return WebNavigator()


@pytest.fixture
def browser_session():
    return BrowserSession()


class TestBrowserManager:
    @pytest.mark.asyncio
    async def test_navigate(self, browser_manager):
        result = await browser_manager.navigate("https://example.com")
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_click(self, browser_manager):
        result = await browser_manager.click("button.submit")
        assert result is True


class TestWebNavigator:
    @pytest.mark.asyncio
    async def test_goto(self, web_navigator):
        result = await web_navigator.goto("https://example.com")
        assert result["status"] == "ok"


class TestBrowserSession:
    def test_set_cookie(self, browser_session):
        browser_session.set_cookie("session", "abc123")
        assert browser_session.get_cookie("session") == "abc123"

    def test_set_header(self, browser_session):
        browser_session.set_header("Authorization", "Bearer token")
        assert "Authorization" in browser_session.get_headers()
