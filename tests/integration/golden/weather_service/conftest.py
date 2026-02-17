"""
Weather Service Integration Test Configuration

Fixtures for integration testing with real HTTP and database.
"""
import pytest
import pytest_asyncio
import httpx
import os
from typing import List

# Weather service URL
WEATHER_SERVICE_URL = os.getenv("WEATHER_SERVICE_URL", "http://localhost:8241")
WEATHER_API_BASE = f"{WEATHER_SERVICE_URL}/api/v1/weather"


@pytest.fixture
def weather_service_url():
    """Get weather service URL"""
    return WEATHER_SERVICE_URL


@pytest.fixture
def weather_api_base():
    """Get weather API base URL"""
    return WEATHER_API_BASE


@pytest.fixture
def internal_headers():
    """Headers for internal service calls (bypass auth)"""
    return {
        "X-Internal-Call": "true",
        "Content-Type": "application/json",
    }


@pytest_asyncio.fixture
async def http_client():
    """Create async HTTP client"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


@pytest.fixture
def cleanup_locations():
    """
    Fixture to track locations for cleanup.

    Usage:
        def test_something(cleanup_locations):
            # Create location
            location_id = create_location()
            cleanup_locations(location_id, user_id)
    """
    locations_to_cleanup: List[tuple] = []

    def _track(location_id: int, user_id: str):
        locations_to_cleanup.append((location_id, user_id))

    yield _track

    # Cleanup is handled by individual tests since we need async HTTP client
    # This fixture just tracks what needs cleanup
