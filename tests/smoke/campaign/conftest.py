"""
Smoke Test Fixtures for Campaign Service

Provides fixtures for smoke testing.
"""

import pytest
import httpx
import os
from datetime import datetime, timezone, timedelta

import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from tests.contracts.campaign.data_contract import CampaignTestDataFactory


# ====================
# Test Configuration
# ====================


class SmokeTestConfig:
    """Configuration for smoke tests"""

    SERVICE_HOST = os.getenv("CAMPAIGN_SERVICE_HOST", "localhost")
    SERVICE_PORT = int(os.getenv("CAMPAIGN_SERVICE_PORT", "8240"))
    BASE_URL = f"http://{SERVICE_HOST}:{SERVICE_PORT}"

    # External Services
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "50061"))
    NATS_HOST = os.getenv("NATS_HOST", "localhost")
    NATS_PORT = int(os.getenv("NATS_PORT", "50056"))
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CONSUL_HOST = os.getenv("CONSUL_HOST", "localhost")
    CONSUL_PORT = int(os.getenv("CONSUL_PORT", "8500"))

    # Timeouts
    HTTP_TIMEOUT = 30
    HEALTH_CHECK_TIMEOUT = 5


@pytest.fixture(scope="session")
def smoke_config():
    """Provide smoke test configuration"""
    return SmokeTestConfig()


# ====================
# HTTP Client
# ====================


@pytest.fixture
async def http_client(smoke_config):
    """Provide async HTTP client"""
    async with httpx.AsyncClient(
        base_url=smoke_config.BASE_URL,
        timeout=smoke_config.HTTP_TIMEOUT,
    ) as client:
        yield client


@pytest.fixture
def auth_headers(smoke_config):
    """Provide authorization headers"""
    return {
        "Authorization": "Bearer smoke_test_token",
        "X-Organization-ID": "org_smoke_test",
        "X-User-ID": "usr_smoke_test",
    }


# ====================
# Factory
# ====================


@pytest.fixture
def factory():
    """Provide CampaignTestDataFactory"""
    return CampaignTestDataFactory
