"""
API Test Layer Configuration

Layer 1: API Contract Tests (E2E)
- Tests run against real services
- No mocking - validates actual HTTP contracts
- Slowest layer, runs on staging/K8s

Usage:
    pytest tests/api -v                    # Run all API tests
    pytest tests/api -v -k "account"       # Run account API tests
    pytest tests/api -v --tb=short         # Short traceback
"""

import os
import sys
from typing import AsyncGenerator, Dict, Optional

import httpx
import pytest
import pytest_asyncio

# Add project root
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)


# =============================================================================
# Configuration
# =============================================================================


class APITestConfig:
    """API test configuration"""

    # Base URLs
    GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost")

    # Direct service ports (bypass gateway) - Aligned with config/ports.yaml
    SERVICE_PORTS = {
        # Identity & Access (8201-8210)
        "auth": 8201,
        "account": 8202,
        "session": 8203,
        "authorization": 8204,
        "audit": 8205,
        "notification": 8206,
        "payment": 8207,
        "wallet": 8208,
        "storage": 8209,
        "order": 8210,
        # Business Domain (8211-8230)
        "task": 8211,
        "organization": 8212,
        "invitation": 8213,
        "vault": 8214,
        "product": 8215,
        "billing": 8216,
        "calendar": 8217,
        "weather": 8218,
        "album": 8219,
        "device": 8220,
        "ota": 8221,
        "media": 8222,
        "memory": 8223,
        "location": 8224,
        "telemetry": 8225,
        "compliance": 8226,
        "document": 8227,
        "subscription": 8228,
        "credit": 8229,
        "event": 8230,
    }

    # Test mode: "gateway" or "direct"
    TEST_MODE = os.getenv("API_TEST_MODE", "direct")

    # Timeouts
    HTTP_TIMEOUT = 30.0

    @classmethod
    def get_base_url(cls, service: str) -> str:
        """Get base URL for a service"""
        if cls.TEST_MODE == "gateway":
            return cls.GATEWAY_URL
        else:
            port = cls.SERVICE_PORTS.get(service)
            if not port:
                raise ValueError(f"Unknown service: {service}")
            return f"http://localhost:{port}"


# =============================================================================
# HTTP Client Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Async HTTP client for API tests"""
    async with httpx.AsyncClient(timeout=APITestConfig.HTTP_TIMEOUT) as client:
        yield client


@pytest_asyncio.fixture
async def auth_client(
    http_client: httpx.AsyncClient,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """HTTP client with JWT authentication"""
    # Get a dev token from auth service
    auth_url = APITestConfig.get_base_url("auth")
    response = await http_client.post(
        f"{auth_url}/api/v1/auth/dev-token",
        json={
            "user_id": "api_test_user",
            "email": "api_test@example.com",
            "expires_in": 3600,
        },
    )

    if response.status_code == 200:
        token = response.json().get("token")
        http_client.headers["Authorization"] = f"Bearer {token}"

    yield http_client


# =============================================================================
# Service-Specific Client Factories
# =============================================================================


class APIClient:
    """Base API client for service testing"""

    def __init__(self, http_client: httpx.AsyncClient, service: str, api_path: str):
        self.client = http_client
        self.base_url = APITestConfig.get_base_url(service)
        self.api_path = api_path

    @property
    def url(self) -> str:
        return f"{self.base_url}{self.api_path}"

    async def get(self, path: str = "", **kwargs) -> httpx.Response:
        return await self.client.get(f"{self.url}{path}", **kwargs)

    async def post(self, path: str = "", **kwargs) -> httpx.Response:
        return await self.client.post(f"{self.url}{path}", **kwargs)

    async def put(self, path: str = "", **kwargs) -> httpx.Response:
        return await self.client.put(f"{self.url}{path}", **kwargs)

    async def delete(self, path: str = "", **kwargs) -> httpx.Response:
        return await self.client.delete(f"{self.url}{path}", **kwargs)

    async def get_raw(self, path: str = "", **kwargs) -> httpx.Response:
        """GET request to raw path (bypasses api_path)"""
        return await self.client.get(f"{self.base_url}{path}", **kwargs)


@pytest_asyncio.fixture
async def account_api(http_client: httpx.AsyncClient) -> APIClient:
    """Account service API client"""
    return APIClient(http_client, "account", "/api/v1/accounts")


@pytest_asyncio.fixture
async def billing_api(http_client: httpx.AsyncClient) -> APIClient:
    """Billing service API client"""
    return APIClient(http_client, "billing", "/api/v1/billing")


@pytest_asyncio.fixture
async def device_api(auth_client: httpx.AsyncClient) -> APIClient:
    """Device service API client (requires auth)"""
    return APIClient(auth_client, "device", "/api/v1/devices")


@pytest_asyncio.fixture
async def storage_api(http_client: httpx.AsyncClient) -> APIClient:
    """Storage service API client"""
    return APIClient(http_client, "storage", "/api/v1/storage")


@pytest_asyncio.fixture
async def memory_api(http_client: httpx.AsyncClient) -> APIClient:
    """Memory service API client"""
    return APIClient(http_client, "memory", "/api/v1/memory")


@pytest_asyncio.fixture
async def compliance_api(http_client: httpx.AsyncClient) -> APIClient:
    """Compliance service API client"""
    return APIClient(http_client, "compliance", "/api/v1/compliance")


@pytest_asyncio.fixture
async def album_api(http_client: httpx.AsyncClient) -> APIClient:
    """Album service API client"""
    return APIClient(http_client, "album", "/api/v1/albums")


@pytest_asyncio.fixture
async def session_api(http_client: httpx.AsyncClient) -> APIClient:
    """Session service API client"""
    return APIClient(http_client, "session", "/api/v1/sessions")


@pytest_asyncio.fixture
async def organization_api(http_client: httpx.AsyncClient) -> APIClient:
    """Organization service API client"""
    return APIClient(http_client, "organization", "/api/v1/organizations")


@pytest_asyncio.fixture
async def subscription_api(http_client: httpx.AsyncClient) -> APIClient:
    """Subscription service API client"""
    return APIClient(http_client, "subscription", "/api/v1/subscriptions")


@pytest_asyncio.fixture
async def payment_api(http_client: httpx.AsyncClient) -> APIClient:
    """Payment service API client"""
    return APIClient(http_client, "payment", "/api/v1/payment")


@pytest_asyncio.fixture
async def task_api(auth_client: httpx.AsyncClient) -> APIClient:
    """Task service API client (requires auth)"""
    return APIClient(auth_client, "task", "/api/v1/tasks")


@pytest_asyncio.fixture
async def event_api(http_client: httpx.AsyncClient) -> APIClient:
    """Event service API client"""
    return APIClient(http_client, "event", "/api/v1/events")


# =============================================================================
# Assertion Helpers
# =============================================================================


class APIAssertions:
    """API-specific assertion helpers"""

    @staticmethod
    def assert_success(response: httpx.Response, expected_status: int = 200):
        """Assert response is successful"""
        assert response.status_code == expected_status, (
            f"Expected {expected_status}, got {response.status_code}: {response.text}"
        )

    @staticmethod
    def assert_created(response: httpx.Response):
        """Assert resource was created"""
        assert response.status_code in [200, 201], (
            f"Expected 200/201, got {response.status_code}: {response.text}"
        )

    @staticmethod
    def assert_not_found(response: httpx.Response):
        """Assert resource not found"""
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"

    @staticmethod
    def assert_validation_error(response: httpx.Response):
        """Assert validation error"""
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"

    @staticmethod
    def assert_unauthorized(response: httpx.Response):
        """Assert unauthorized"""
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"

    @staticmethod
    def assert_has_fields(data: dict, fields: list):
        """Assert response has required fields"""
        missing = [f for f in fields if f not in data]
        assert not missing, f"Missing fields: {missing}"


@pytest.fixture
def api_assert() -> APIAssertions:
    """Provide API assertion helpers"""
    return APIAssertions()
