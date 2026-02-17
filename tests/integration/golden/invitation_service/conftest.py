"""
Invitation Service - Integration Test Configuration

Provides HTTP client and cleanup utilities for integration testing.
"""
import pytest
import pytest_asyncio
import httpx
from typing import List

INVITATION_SERVICE_URL = "http://localhost:8213"
API_BASE = f"{INVITATION_SERVICE_URL}/api/v1/invitations"


@pytest.fixture
def service_url():
    """Provide invitation service URL"""
    return INVITATION_SERVICE_URL


@pytest.fixture
def api_base():
    """Provide API base URL"""
    return API_BASE


@pytest.fixture
def internal_headers():
    """Headers for internal service calls (bypass auth)"""
    return {
        "X-Internal-Call": "true",
        "X-User-Id": "test_user_integration",
        "Content-Type": "application/json",
    }


@pytest_asyncio.fixture
async def http_client():
    """Provide async HTTP client"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


@pytest.fixture
def cleanup_invitations():
    """Factory for tracking and cleaning up test invitations"""
    created_ids: List[str] = []

    def track(invitation_id: str):
        created_ids.append(invitation_id)
        return invitation_id

    yield track

    # Cleanup would happen here if we had a direct DB connection
    # For now, invitations are cleaned via API or expire naturally


@pytest_asyncio.fixture
async def invitation_api(http_client, internal_headers):
    """Provide API helper for invitation service"""
    class InvitationAPI:
        def __init__(self, client, headers):
            self.client = client
            self.headers = headers
            self.base_url = API_BASE

        async def post(self, path: str, json: dict):
            return await self.client.post(
                f"{self.base_url}{path}",
                json=json,
                headers=self.headers
            )

        async def get(self, path: str):
            return await self.client.get(
                f"{self.base_url}{path}",
                headers=self.headers
            )

        async def put(self, path: str, json: dict):
            return await self.client.put(
                f"{self.base_url}{path}",
                json=json,
                headers=self.headers
            )

        async def delete(self, path: str):
            return await self.client.delete(
                f"{self.base_url}{path}",
                headers=self.headers
            )

    return InvitationAPI(http_client, internal_headers)
