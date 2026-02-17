"""
API Test Fixtures for Campaign Service

Provides fixtures for API testing with real HTTP requests.
"""

import pytest
import httpx
import os
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional

import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from tests.contracts.campaign.data_contract import CampaignTestDataFactory


# ====================
# Test Configuration
# ====================


class APITestConfig:
    """Configuration for API tests"""

    SERVICE_HOST = os.getenv("CAMPAIGN_SERVICE_HOST", "localhost")
    SERVICE_PORT = int(os.getenv("CAMPAIGN_SERVICE_PORT", "8251"))
    BASE_URL = f"http://{SERVICE_HOST}:{SERVICE_PORT}"

    # Auth
    AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8201")
    TEST_USER_ID = "usr_api_test"
    TEST_ORG_ID = "org_api_test"

    # Timeouts
    HTTP_TIMEOUT = 30


@pytest.fixture(scope="session")
def api_config():
    """Provide API test configuration"""
    return APITestConfig()


# ====================
# HTTP Client
# ====================


@pytest.fixture
async def http_client(api_config):
    """Provide async HTTP client"""
    async with httpx.AsyncClient(
        base_url=api_config.BASE_URL,
        timeout=api_config.HTTP_TIMEOUT,
    ) as client:
        yield client


@pytest.fixture
async def auth_headers(api_config):
    """Provide authorization headers for API requests"""
    # In real tests, this would obtain a JWT token
    # For now, return a mock header
    return {
        "Authorization": "Bearer mock_jwt_token",
        "X-Organization-ID": api_config.TEST_ORG_ID,
        "X-User-ID": api_config.TEST_USER_ID,
    }


# ====================
# Factory
# ====================


@pytest.fixture
def factory():
    """Provide CampaignTestDataFactory"""
    return CampaignTestDataFactory


# ====================
# API Response Helpers
# ====================


class APIResponseHelper:
    """Helper for validating API responses"""

    @staticmethod
    def assert_success(response: httpx.Response, expected_status: int = 200):
        """Assert response is successful"""
        assert response.status_code == expected_status, (
            f"Expected {expected_status}, got {response.status_code}: {response.text}"
        )

    @staticmethod
    def assert_error(
        response: httpx.Response, expected_status: int, error_code: Optional[str] = None
    ):
        """Assert response is an error"""
        assert response.status_code == expected_status, (
            f"Expected {expected_status}, got {response.status_code}: {response.text}"
        )
        if error_code:
            data = response.json()
            assert data.get("error", {}).get("code") == error_code

    @staticmethod
    def get_campaign_id(response: httpx.Response) -> str:
        """Extract campaign_id from response"""
        data = response.json()
        return data.get("campaign", {}).get("campaign_id")


@pytest.fixture
def api_helper():
    """Provide API response helper"""
    return APIResponseHelper()


# ====================
# Test Data Cleanup
# ====================


class APITestCleaner:
    """Cleanup utility for API-created test data"""

    def __init__(self):
        self.created_campaign_ids = []

    def track(self, campaign_id: str):
        """Track campaign for cleanup"""
        self.created_campaign_ids.append(campaign_id)

    async def cleanup(self, client: httpx.AsyncClient, headers: dict):
        """Delete all tracked campaigns"""
        for campaign_id in self.created_campaign_ids:
            try:
                await client.delete(
                    f"/api/v1/campaigns/{campaign_id}",
                    headers=headers,
                )
            except Exception:
                pass
        self.created_campaign_ids.clear()


@pytest.fixture
def cleaner():
    """Provide test data cleaner"""
    return APITestCleaner()
