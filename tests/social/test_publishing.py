"""
Tests for social publishing.
"""

import pytest
from backend.content_engine.publishing.publishing_manager import PublishingManager
from backend.content_engine.publishing.schedule_manager import ScheduleManager
from backend.content_engine.publishing.publishing_status import PublishingStatus


@pytest.fixture
def publishing_manager():
    return PublishingManager()


@pytest.fixture
def schedule_manager():
    return ScheduleManager()


@pytest.fixture
def publishing_status():
    return PublishingStatus()


class TestPublishingManager:
    @pytest.mark.asyncio
    async def test_publish(self, publishing_manager):
        result = await publishing_manager.publish(
            "content1",
            ["linkedin", "twitter"],
            "Hello world",
        )
        assert result["status"] == "published"


class TestScheduleManager:
    def test_add_schedule(self, schedule_manager):
        from datetime import datetime
        schedule_id = schedule_manager.add_schedule(
            "content1",
            "linkedin",
            datetime.now(),
        )
        assert schedule_id is not None


class TestPublishingStatus:
    def test_update(self, publishing_status):
        publishing_status.update("content1", "linkedin", "published", "post123")
        statuses = publishing_status.get_status("content1")
        assert len(statuses) == 1
