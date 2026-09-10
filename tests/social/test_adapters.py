"""
Tests for social adapters.
"""

import pytest
from backend.hermes_engine.gateway.adapters.telegram import TelegramAdapter
from backend.hermes_engine.gateway.adapters.discord import DiscordAdapter
from backend.hermes_engine.gateway.adapters.slack import SlackAdapter


class TestTelegramAdapter:
    @pytest.mark.asyncio
    async def test_send_message(self):
        adapter = TelegramAdapter()
        result = await adapter.send_message("123456", "Hello")
        assert result["status"] == "sent"


class TestDiscordAdapter:
    @pytest.mark.asyncio
    async def test_send_message(self):
        adapter = DiscordAdapter()
        result = await adapter.send_message("channel123", "Hello")
        assert result["status"] == "sent"


class TestSlackAdapter:
    @pytest.mark.asyncio
    async def test_send_message(self):
        adapter = SlackAdapter()
        result = await adapter.send_message("#general", "Hello")
        assert result["status"] == "sent"
