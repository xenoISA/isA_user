"""
Audit Service API Test Configuration

Provides fixtures for API testing with JWT authentication:
- http_client: Async HTTP client for making requests
- auth_headers: Headers with valid JWT token
- internal_headers: Headers for internal service calls
- audit_api: Configured client for audit endpoints
"""
import pytest
import pytest_asyncio
import httpx
from typing import Dict, Any, Optional

AUDIT_SERVICE_URL = "http://localhost:8204"
AUTH_SERVICE_URL = "http://localhost:8202"


@pytest_asyncio.fixture
async def http_client():
    """Create async HTTP client"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


@pytest.fixture
def internal_headers():
    """Headers for internal service calls (bypass auth)"""
    return {
        "X-Internal-Call": "true",
        "Content-Type": "application/json",
    }


@pytest_asyncio.fixture
async def auth_token(http_client) -> Optional[str]:
    """
    Get valid JWT token from auth service.

    Uses test credentials to obtain a token.
    Falls back to None if auth service unavailable.
    """
    try:
        response = await http_client.post(
            f"{AUTH_SERVICE_URL}/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpassword123"
            }
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
    except Exception:
        pass
    return None


@pytest.fixture
def auth_headers(auth_token) -> Dict[str, str]:
    """Headers with JWT authentication"""
    headers = {"Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    return headers


class AuditAPIClient:
    """Wrapper for audit API calls"""

    def __init__(self, client: httpx.AsyncClient, headers: Dict[str, str]):
        self._client = client
        self._headers = headers
        self._base_url = f"{AUDIT_SERVICE_URL}/api/v1/audit"

    async def post(self, path: str, json: Dict[str, Any]) -> httpx.Response:
        """POST request to audit API"""
        url = f"{self._base_url}{path}"
        return await self._client.post(url, json=json, headers=self._headers)

    async def get(self, path: str, params: Optional[Dict] = None) -> httpx.Response:
        """GET request to audit API"""
        url = f"{self._base_url}{path}"
        return await self._client.get(url, params=params, headers=self._headers)

    async def put(self, path: str, json: Dict[str, Any]) -> httpx.Response:
        """PUT request to audit API"""
        url = f"{self._base_url}{path}"
        return await self._client.put(url, json=json, headers=self._headers)

    async def delete(self, path: str) -> httpx.Response:
        """DELETE request to audit API"""
        url = f"{self._base_url}{path}"
        return await self._client.delete(url, headers=self._headers)


@pytest_asyncio.fixture
async def audit_api(http_client, internal_headers) -> AuditAPIClient:
    """Configured audit API client with internal headers"""
    return AuditAPIClient(http_client, internal_headers)


@pytest_asyncio.fixture
async def audit_api_with_auth(http_client, auth_headers) -> AuditAPIClient:
    """Configured audit API client with JWT auth"""
    return AuditAPIClient(http_client, auth_headers)


@pytest.fixture
def audit_base_url():
    """Base URL for audit API"""
    return f"{AUDIT_SERVICE_URL}/api/v1/audit"


@pytest.fixture
def health_url():
    """Health check URL"""
    return f"{AUDIT_SERVICE_URL}/health"
