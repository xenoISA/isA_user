"""
Credit Service API Test Configuration

Fixtures for testing credit_service HTTP endpoints using FastAPI TestClient approach.
"""
import os
import sys
import uuid
from typing import AsyncGenerator

import httpx
import pytest
import pytest_asyncio

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from tests.api.conftest import APIClient, APIAssertions


# =============================================================================
# Configuration
# =============================================================================

CREDIT_SERVICE_PORT = 8229
CREDIT_BASE_URL = os.getenv("CREDIT_SERVICE_URL", f"http://localhost:{CREDIT_SERVICE_PORT}")


# =============================================================================
# Credit Service API Client
# =============================================================================

@pytest_asyncio.fixture
async def credit_api() -> AsyncGenerator[APIClient, None]:
    """
    Credit service API client fixture.

    Provides HTTPx async client configured for credit_service endpoints.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        api_client = APIClient(
            http_client=client,
            service="credit",
            api_path="/api/v1/credits"
        )
        # Override base URL if needed
        api_client.base_url = CREDIT_BASE_URL
        yield api_client


@pytest_asyncio.fixture
async def http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Raw HTTP client for credit service tests"""
    async with httpx.AsyncClient(
        timeout=30.0,
        base_url=CREDIT_BASE_URL
    ) as client:
        yield client


# =============================================================================
# Test Data Helpers
# =============================================================================

def unique_user_id() -> str:
    """Generate unique user ID for API tests"""
    return f"api_test_user_{uuid.uuid4().hex[:16]}"


def unique_campaign_id() -> str:
    """Generate unique campaign ID for API tests"""
    return f"api_test_camp_{uuid.uuid4().hex[:16]}"


def unique_account_id() -> str:
    """Generate unique account ID for API tests"""
    return f"api_test_acc_{uuid.uuid4().hex[:16]}"
