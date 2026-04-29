from typing import AsyncGenerator

import httpx
import pytest

from tests.smoke.conftest import resolve_base_url, resolve_service_url

# Service Configuration
CREDIT_BASE_URL = resolve_base_url("credit_service", "CREDIT_BASE_URL")
CREDIT_API_V1 = f"{CREDIT_BASE_URL}/api/v1/credits"
CREDIT_HEALTH_URL = resolve_service_url("credit_service", "/health", "CREDIT_BASE_URL")
TIMEOUT = 10.0


@pytest.fixture
async def http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """
    Async HTTP client for smoke tests.

    Provides an httpx.AsyncClient configured for testing the live credit service.
    Automatically closes the client after tests complete.
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        yield client


@pytest.fixture
def credit_base_url() -> str:
    """Base URL for credit service"""
    return CREDIT_BASE_URL


@pytest.fixture
def credit_api_v1() -> str:
    """API v1 base path for credit service"""
    return CREDIT_API_V1


@pytest.fixture
def credit_health_url() -> str:
    """Health route for direct or gateway smoke mode."""
    return CREDIT_HEALTH_URL
