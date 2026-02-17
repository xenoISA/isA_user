"""
Integration Test Fixtures for Campaign Service

Provides fixtures for integration testing with real infrastructure.
Requires: PostgreSQL, NATS, Redis, Consul to be running.
"""

import pytest
import asyncio
import os
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import AsyncGenerator

import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from tests.contracts.campaign.data_contract import (
    CampaignType,
    CampaignStatus,
    ScheduleType,
    ChannelType,
    SegmentType,
    ExecutionStatus,
    MessageStatus,
    CampaignTestDataFactory,
)


# ====================
# Test Configuration
# ====================


class IntegrationTestConfig:
    """Configuration for integration tests"""

    # Service
    SERVICE_HOST = os.getenv("CAMPAIGN_SERVICE_HOST", "localhost")
    SERVICE_PORT = int(os.getenv("CAMPAIGN_SERVICE_PORT", "8240"))
    SERVICE_URL = f"http://{SERVICE_HOST}:{SERVICE_PORT}"

    # PostgreSQL (via gRPC)
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "50061"))

    # NATS (via gRPC)
    NATS_HOST = os.getenv("NATS_HOST", "localhost")
    NATS_PORT = int(os.getenv("NATS_PORT", "50056"))

    # Redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Consul
    CONSUL_HOST = os.getenv("CONSUL_HOST", "localhost")
    CONSUL_PORT = int(os.getenv("CONSUL_PORT", "8500"))

    # Timeouts
    DB_TIMEOUT = 10
    NATS_TIMEOUT = 10
    HTTP_TIMEOUT = 30


@pytest.fixture(scope="session")
def integration_config():
    """Provide integration test configuration"""
    return IntegrationTestConfig()


# ====================
# Skip Markers
# ====================


def requires_postgres():
    """Marker for tests requiring PostgreSQL"""
    return pytest.mark.skipif(
        os.getenv("SKIP_POSTGRES_TESTS", "false").lower() == "true",
        reason="PostgreSQL not available",
    )


def requires_nats():
    """Marker for tests requiring NATS"""
    return pytest.mark.skipif(
        os.getenv("SKIP_NATS_TESTS", "false").lower() == "true",
        reason="NATS not available",
    )


def requires_redis():
    """Marker for tests requiring Redis"""
    return pytest.mark.skipif(
        os.getenv("SKIP_REDIS_TESTS", "false").lower() == "true",
        reason="Redis not available",
    )


def requires_consul():
    """Marker for tests requiring Consul"""
    return pytest.mark.skipif(
        os.getenv("SKIP_CONSUL_TESTS", "false").lower() == "true",
        reason="Consul not available",
    )


# ====================
# Factory Fixture
# ====================


@pytest.fixture
def factory():
    """Provide CampaignTestDataFactory"""
    return CampaignTestDataFactory


# ====================
# Cleanup Utilities
# ====================


class TestDataCleaner:
    """Utility for cleaning up test data"""

    def __init__(self):
        self.created_campaign_ids = []

    def track_campaign(self, campaign_id: str):
        """Track campaign for cleanup"""
        self.created_campaign_ids.append(campaign_id)

    async def cleanup(self, repository):
        """Clean up tracked test data"""
        for campaign_id in self.created_campaign_ids:
            try:
                await repository.delete_campaign(campaign_id)
            except Exception:
                pass  # Ignore cleanup errors
        self.created_campaign_ids.clear()


@pytest.fixture
def data_cleaner():
    """Provide test data cleaner"""
    return TestDataCleaner()


# ====================
# Event Loop Configuration
# ====================


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
