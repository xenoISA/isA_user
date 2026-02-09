"""
Component Test Layer Configuration (Layer 3)

Structure:
    tests/component/
    ├── golden/      🔒 Characterization (never modify)
    ├── tdd/         🆕 TDD (new features)
    └── mocks/       Mock implementations

Usage:
    pytest tests/component -v
    pytest tests/component/golden -v
    pytest tests/component/tdd/account -v
"""
import os
import sys
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

# Set testing environment BEFORE any imports
os.environ["ENV"] = "testing"
os.environ["ENVIRONMENT"] = "testing"
os.environ["NATS_ENABLED"] = "false"

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Mock AsyncNATSClient and AsyncPostgresClient BEFORE any imports that might use them
import isa_common
if not hasattr(isa_common, 'AsyncNATSClient'):
    isa_common.AsyncNATSClient = MagicMock
    print("✅ Mocked AsyncNATSClient for component testing")
if not hasattr(isa_common, 'AsyncPostgresClient'):
    isa_common.AsyncPostgresClient = MagicMock
    print("✅ Mocked AsyncPostgresClient for component testing")

# Load test environment variables
from pathlib import Path
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent.parent
test_env_file = project_root / "tests" / "config" / ".env.test"
if test_env_file.exists():
    load_dotenv(test_env_file, override=True)
    print(f"✅ Loaded test environment from {test_env_file}")

from tests.component.mocks import (
    MockAsyncPostgresClient,
    MockEventBus,
    MockHttpClient,
)
from tests.component.golden.account_service.mocks import MockAccountRepository


# =============================================================================
# Pytest Configuration
# =============================================================================

def pytest_configure(config):
    """Configure custom markers"""
    config.addinivalue_line(
        "markers", "component: marks tests as component tests"
    )
    config.addinivalue_line(
        "markers", "golden: safety net tests - DO NOT MODIFY"
    )


# =============================================================================
# Database Mocks
# =============================================================================

@pytest.fixture
def mock_db() -> MockAsyncPostgresClient:
    """Mock PostgreSQL client"""
    return MockAsyncPostgresClient()


@pytest.fixture
def mock_db_with_user(mock_db: MockAsyncPostgresClient) -> MockAsyncPostgresClient:
    """Mock DB with a pre-existing user"""
    mock_db.set_row_response({
        "user_id": "usr_test_123",
        "email": "test@example.com",
        "name": "Test User",
        "is_active": True,
        "preferences": {},
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    })
    return mock_db


# =============================================================================
# Event Bus Mocks
# =============================================================================

@pytest.fixture
def mock_event_bus() -> MockEventBus:
    """Mock NATS event bus"""
    return MockEventBus()


# =============================================================================
# HTTP Client Mocks
# =============================================================================

@pytest.fixture
def mock_http_client() -> MockHttpClient:
    """Mock HTTP client for inter-service calls"""
    return MockHttpClient()


# =============================================================================
# Service Client Mocks
# =============================================================================

@pytest.fixture
def mock_subscription_client() -> AsyncMock:
    """Mock subscription service client"""
    client = AsyncMock()
    client.get_or_create_subscription = AsyncMock(return_value={
        "subscription": {
            "subscription_id": "sub_test_123",
            "user_id": "usr_test_123",
            "tier_code": "free",
            "status": "active"
        }
    })
    client.get_subscription = AsyncMock(return_value={
        "tier_code": "free",
        "status": "active"
    })
    return client


@pytest.fixture
def mock_wallet_client() -> AsyncMock:
    """Mock wallet service client"""
    client = AsyncMock()
    client.get_balance = AsyncMock(return_value={"balance": 100.0, "currency": "USD"})
    client.create_wallet = AsyncMock(return_value={"wallet_id": "wal_test_123"})
    return client


@pytest.fixture
def mock_billing_client() -> AsyncMock:
    """Mock billing service client"""
    client = AsyncMock()
    client.get_billing_summary = AsyncMock(return_value={"total_amount": 0.0})
    return client


# =============================================================================
# Config Mocks
# =============================================================================

@pytest.fixture
def mock_config() -> MagicMock:
    """Mock ConfigManager"""
    config = MagicMock()
    config.discover_service = MagicMock(return_value=("localhost", 50061))
    return config


# =============================================================================
# Account Repository Mock
# =============================================================================

@pytest.fixture
def mock_account_repository() -> MockAccountRepository:
    """Mock Account Repository with protocol implementation"""
    return MockAccountRepository()


@pytest.fixture
def mock_account_repository_with_user() -> MockAccountRepository:
    """Mock Account Repository with a pre-existing user"""
    repo = MockAccountRepository()
    repo.set_user(
        user_id="usr_test_123",
        email="test@example.com",
        name="Test User",
        is_active=True
    )
    return repo
