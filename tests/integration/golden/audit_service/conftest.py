"""
Audit Service Integration Test Configuration

Provides fixtures for integration testing:
- http_client: Async HTTP client for making requests
- internal_headers: Headers to bypass authentication
- cleanup_events: Fixture to cleanup test data
"""
import pytest
import pytest_asyncio
import httpx
from typing import List

AUDIT_SERVICE_URL = "http://localhost:8204"


@pytest_asyncio.fixture
async def http_client():
    """Create async HTTP client"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


@pytest.fixture
def internal_headers():
    """Headers to bypass authentication for internal calls"""
    return {
        "X-Internal-Call": "true",
        "Content-Type": "application/json",
    }


@pytest.fixture
def cleanup_events():
    """Factory fixture for cleanup - events are auto-cleaned by retention"""
    created_ids: List[str] = []

    def _register(event_id: str):
        created_ids.append(event_id)
        return event_id

    yield _register

    # Note: Audit events don't have a delete endpoint typically
    # They are managed by data retention policies


@pytest.fixture
def audit_api_base():
    """Base URL for audit API"""
    return f"{AUDIT_SERVICE_URL}/api/v1/audit"


@pytest.fixture
def health_url():
    """Health check URL"""
    return f"{AUDIT_SERVICE_URL}/health"
