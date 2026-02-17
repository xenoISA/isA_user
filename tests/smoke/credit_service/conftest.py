"""
Credit Service Smoke Test Fixtures

Provides fixtures for live service testing against deployed credit_service.
"""

import os
import pytest
import httpx
from typing import AsyncGenerator

# Service Configuration
CREDIT_BASE_URL = os.getenv("CREDIT_BASE_URL", "http://localhost:8229")
CREDIT_API_V1 = f"{CREDIT_BASE_URL}/api/v1/credits"
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
