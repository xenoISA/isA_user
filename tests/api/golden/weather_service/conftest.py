"""
Weather Service API Test Configuration

Fixtures for API testing with JWT authentication.
"""
import pytest
import pytest_asyncio
import httpx
import os

# Service URLs
WEATHER_SERVICE_URL = os.getenv("WEATHER_SERVICE_URL", "http://localhost:8241")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8202")
WEATHER_API_BASE = f"{WEATHER_SERVICE_URL}/api/v1/weather"


@pytest.fixture
def weather_service_url():
    """Get weather service URL"""
    return WEATHER_SERVICE_URL


@pytest.fixture
def weather_api_base():
    """Get weather API base URL"""
    return WEATHER_API_BASE


@pytest_asyncio.fixture
async def http_client():
    """Create async HTTP client"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


@pytest_asyncio.fixture
async def auth_token(http_client):
    """
    Get JWT auth token for testing.

    Note: This requires auth_service to be running.
    Returns None if auth service is not available.
    """
    try:
        # Try to get a test token from auth service
        response = await http_client.post(
            f"{AUTH_SERVICE_URL}/api/v1/auth/token",
            json={
                "grant_type": "client_credentials",
                "client_id": "test_client",
                "client_secret": "test_secret",
            }
        )

        if response.status_code == 200:
            return response.json().get("access_token")

        # Fallback: try device auth flow
        response = await http_client.post(
            f"{AUTH_SERVICE_URL}/api/v1/auth/device/token",
            json={"device_id": "test_device_api_tests"}
        )

        if response.status_code == 200:
            return response.json().get("access_token")

    except Exception:
        pass

    return None


@pytest.fixture
def auth_headers(auth_token):
    """Get authorization headers with JWT token"""
    if auth_token:
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
        }
    return {"Content-Type": "application/json"}


class WeatherAPIClient:
    """Helper client for weather API calls with authentication"""

    def __init__(self, http_client: httpx.AsyncClient, auth_headers: dict):
        self.client = http_client
        self.base_url = WEATHER_API_BASE
        self.headers = auth_headers

    async def get(self, path: str, params: dict = None):
        """GET request with auth"""
        url = f"{self.base_url}{path}"
        return await self.client.get(url, params=params, headers=self.headers)

    async def post(self, path: str, json: dict = None):
        """POST request with auth"""
        url = f"{self.base_url}{path}"
        return await self.client.post(url, json=json, headers=self.headers)

    async def put(self, path: str, json: dict = None):
        """PUT request with auth"""
        url = f"{self.base_url}{path}"
        return await self.client.put(url, json=json, headers=self.headers)

    async def delete(self, path: str, params: dict = None):
        """DELETE request with auth"""
        url = f"{self.base_url}{path}"
        return await self.client.delete(url, params=params, headers=self.headers)


@pytest_asyncio.fixture
async def weather_api(http_client, auth_headers):
    """Create weather API client with authentication"""
    return WeatherAPIClient(http_client, auth_headers)
