"""
Compliance API Golden Test Configuration

Service-specific fixtures for API golden tests with authentication.
Requires: PostgreSQL + NATS + Auth Service + Compliance Service running

Usage:
    pytest tests/api/golden/compliance_service -v
"""

import pytest
import pytest_asyncio
import httpx
from typing import List
import os

# Service configuration
COMPLIANCE_URL = os.getenv("COMPLIANCE_SERVICE_URL", "http://localhost:8226")
AUTH_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8210")
API_BASE = f"{COMPLIANCE_URL}/api/v1/compliance"
TIMEOUT = 30.0


# =============================================================================
# HTTP Client Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def http_client():
    """Async HTTP client for API calls"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        yield client


@pytest.fixture
def internal_headers():
    """Headers for internal service calls"""
    return {
        "X-Internal-Service": "api_test_runner",
        "X-Correlation-ID": "api-test-correlation-123",
        "Content-Type": "application/json",
    }


@pytest_asyncio.fixture
async def auth_token(http_client):
    """Get authentication token for API tests"""
    try:
        response = await http_client.post(
            f"{AUTH_URL}/api/v1/auth/internal",
            json={
                "service": "test_runner",
                "scope": ["compliance:read", "compliance:write"],
            },
        )
        if response.status_code == 200:
            return response.json().get("access_token")
    except Exception:
        pass
    return None


@pytest.fixture
def auth_headers(auth_token, internal_headers):
    """Headers with authentication"""
    headers = internal_headers.copy()
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    return headers


# =============================================================================
# Cleanup Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def cleanup_policies(http_client, auth_headers):
    """Track and cleanup policies created during tests"""
    created_ids: List[str] = []

    def track(policy_id: str) -> str:
        created_ids.append(policy_id)
        return policy_id

    yield track

    for policy_id in created_ids:
        try:
            await http_client.delete(
                f"{API_BASE}/policies/{policy_id}",
                headers=auth_headers
            )
        except Exception:
            pass


# =============================================================================
# Service URL Fixtures
# =============================================================================

@pytest.fixture
def compliance_url():
    """Get compliance service URL"""
    return COMPLIANCE_URL


@pytest.fixture
def compliance_api_base():
    """Get compliance API base URL"""
    return API_BASE


# =============================================================================
# Pytest Configuration
# =============================================================================

def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line("markers", "api: marks tests as API tests")
    config.addinivalue_line("markers", "golden: marks tests as golden/characterization tests")
    config.addinivalue_line("markers", "auth_required: marks tests that require authentication")
