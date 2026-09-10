"""
Pytest configuration for E2E tests
"""

import pytest
import asyncio
from typing import AsyncGenerator


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def api_base_url() -> str:
    """Base URL for API tests."""
    return "http://localhost:8000"


@pytest.fixture(scope="session")
async def test_user_credentials() -> dict:
    """Test user credentials."""
    return {
        "email": "e2e_test@careerintel.ai",
        "password": "TestPassword123!",
        "full_name": "E2E Test User"
    }


# Markers for test categorization
def pytest_configure(config):
    config.addinivalue_line("markers", "e2e: End-to-end integration test")
    config.addinivalue_line("markers", "research: Research pipeline test")
    config.addinivalue_line("markers", "career: Career analysis test")
    config.addinivalue_line("markers", "content: Content generation test")
    config.addinivalue_line("markers", "slow: Slow running test")