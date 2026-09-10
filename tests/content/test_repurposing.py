"""
Tests for content repurposing.
"""

import pytest
from backend.content_engine.transformation.platform_formatter import PlatformFormatter
from backend.content_engine.transformation.tone_adapter import ToneAdapter
from backend.content_engine.transformation.content_repurposer import ContentRepurposer


class TestPlatformFormatter:
    def test_format_short(self):
        formatter = PlatformFormatter()
        result = formatter.format("Hello", "twitter")
        assert result == "Hello"

    def test_format_truncate(self):
        formatter = PlatformFormatter()
        long_text = "x" * 300
        result = formatter.format(long_text, "twitter")
        assert len(result) <= 280


class TestToneAdapter:
    def test_adapt(self):
        adapter = ToneAdapter()
        result = adapter.adapt("Hello world", "professional")
        assert result == "Hello world"


class TestContentRepurposer:
    @pytest.mark.asyncio
    async def test_repurpose(self):
        repurposer = ContentRepurposer()
        result = await repurposer.repurpose("Original content", "thread")
        assert "Repurposed" in result
