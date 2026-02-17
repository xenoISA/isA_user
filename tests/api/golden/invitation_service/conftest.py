"""
Invitation Service - API Test Configuration

Provides authenticated HTTP client for API testing.
"""
import pytest
import pytest_asyncio
import httpx
import os

INVITATION_SERVICE_URL = "http://localhost:8213"
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8202")
API_BASE = f"{INVITATION_SERVICE_URL}/api/v1/invitations"


@pytest.fixture
def service_url():
    """Provide invitation service URL"""
    return INVITATION_SERVICE_URL


@pytest.fixture
def api_base():
    """Provide API base URL"""
    return API_BASE


@pytest_asyncio.fixture
async def http_client():
    """Provide async HTTP client"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


@pytest_asyncio.fixture
async def auth_token(http_client):
    """Get valid JWT token from auth service"""
    # Try to get a test token
    try:
        response = await http_client.post(
            f"{AUTH_SERVICE_URL}/api/v1/auth/login",
            json={
                "email": os.getenv("TEST_USER_EMAIL", "test@example.com"),
                "password": os.getenv("TEST_USER_PASSWORD", "testpassword")
            }
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
    except Exception:
        pass

    # Return None if we can't get a token
    return None


@pytest.fixture
def auth_headers(auth_token):
    """Provide authenticated headers"""
    if auth_token:
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
        }
    # Fallback to internal headers for testing
    return {
        "X-Internal-Call": "true",
        "X-User-Id": "api_test_user",
        "Content-Type": "application/json",
    }


@pytest_asyncio.fixture
async def invitation_api(http_client, auth_headers):
    """Provide authenticated API helper"""
    class InvitationAPI:
        def __init__(self, client, headers):
            self.client = client
            self.headers = headers
            self.base_url = API_BASE

        async def post(self, path: str, json: dict = None):
            return await self.client.post(
                f"{self.base_url}{path}",
                json=json,
                headers=self.headers
            )

        async def get(self, path: str, params: dict = None):
            return await self.client.get(
                f"{self.base_url}{path}",
                params=params,
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

    return InvitationAPI(http_client, auth_headers)
