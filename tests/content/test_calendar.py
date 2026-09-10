"""
Tests for content calendar.
"""

import pytest
from backend.content_engine.planning.content_calendar import ContentCalendar
from backend.content_engine.planning.campaign_planner import Campaign


class TestContentCalendar:
    def test_add_and_get(self):
        from datetime import datetime
        calendar = ContentCalendar()
        event_id = calendar.add_event("Test Event", datetime.now())
        events = calendar.get_events()
        assert len(events) == 1

    def test_remove_event(self):
        from datetime import datetime
        calendar = ContentCalendar()
        event_id = calendar.add_event("Test Event", datetime.now())
        removed = calendar.remove_event(event_id)
        assert removed


class TestCampaign:
    def test_creation(self):
        campaign = Campaign(id="1", name="Test Campaign")
        assert campaign.name == "Test Campaign"
        assert campaign.status == "draft"
