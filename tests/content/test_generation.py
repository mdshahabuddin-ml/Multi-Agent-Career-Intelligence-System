"""
Tests for content engine.
"""

import pytest
from backend.content_engine.state.content_state import ContentState
from backend.content_engine.planning.content_calendar import ContentCalendar
from backend.content_engine.generation.text_generator import TextGenerator
from backend.content_engine.quality.content_validator import ContentValidator


class TestContentState:
    def test_creation(self):
        state = ContentState(content_id="1", user_id=1)
        assert state.content_id == "1"
        assert state.status == "draft"


class TestContentCalendar:
    def test_add_event(self):
        from datetime import datetime
        calendar = ContentCalendar()
        event_id = calendar.add_event("Test", datetime.now())
        assert event_id is not None


class TestTextGenerator:
    @pytest.mark.asyncio
    async def test_generate(self):
        generator = TextGenerator()
        result = await generator.generate("Hello world")
        assert "Hello world" in result


class TestContentValidator:
    def test_validate(self):
        validator = ContentValidator()
        result = validator.validate("Test content")
        assert result["valid"] is True
