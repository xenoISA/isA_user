"""
Root conftest.py - Global fixtures and configuration for all test layers.

Test Layers (Top-Down TDD):
    - api/        : API contract tests (E2E, real services)
    - integration/: Service integration tests (real DB, mocked external)
    - component/  : Component tests (mocked dependencies)
    - unit/       : Unit tests (pure functions, no I/O)
    - eval/       : DeepEval LLM quality tests
"""
import asyncio
import os
import sys
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Generator, List, Optional

import pytest

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Import shared fixtures from tests/fixtures
from tests.fixtures import (
    # Common
    make_user_id,
    make_device_id,
    make_org_id,
    make_email,
    make_timestamp,
    # Generators
    random_string,
    random_email,
    random_phone,
    random_user_ids,
    random_amount,
    # Account fixtures
    make_account,
    make_account_ensure_request,
    make_account_update_request,
    make_preferences_update,
    # Album fixtures
    make_album_id,
    make_photo_id,
    make_album,
    make_album_create_request,
    make_album_update_request,
    make_add_photos_request,
    make_remove_photos_request,
    make_album_photo,
)

# Legacy alias
make_user = make_account


# =============================================================================
# Test Configuration
# =============================================================================

class TestConfig:
    """Centralized test configuration"""

    # Service URLs (port registry)
    # Authoritative source: deployment/k8s/build-all-images.sh
    SERVICES = {
        "auth_service": 8201,
        "account_service": 8202,
        "session_service": 8203,
        "authorization_service": 8204,
        "audit_service": 8205,
        "notification_service": 8206,
        "payment_service": 8207,
        "wallet_service": 8208,
        "storage_service": 8209,
        "order_service": 8210,
        "task_service": 8211,
        "organization_service": 8212,
        "invitation_service": 8213,
        "vault_service": 8214,
        "product_service": 8215,
        "billing_service": 8216,
        "calendar_service": 8217,
        "weather_service": 8218,
        "album_service": 8219,
        "device_service": 8220,
        "ota_service": 8221,
        "media_service": 8222,
        "memory_service": 8223,
        "location_service": 8224,
        "telemetry_service": 8225,
        "compliance_service": 8226,
        "document_service": 8227,
        "subscription_service": 8228,
        "event_service": 8230,
    }

    # Infrastructure
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
    NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6334"))

    # Timeouts
    HTTP_TIMEOUT = 30
    EVENT_WAIT_TIMEOUT = 10
    DB_TIMEOUT = 10

    @classmethod
    def get_service_url(cls, service_name: str) -> str:
        port = cls.SERVICES.get(service_name)
        if not port:
            raise ValueError(f"Unknown service: {service_name}")
        return f"http://localhost:{port}"


@pytest.fixture(scope="session")
def test_config() -> TestConfig:
    """Provide test configuration"""
    return TestConfig()


# =============================================================================
# Event Loop Configuration
# =============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Test Data Generators
# =============================================================================

class TestDataGenerator:
    """Generate unique test data"""

    _counter = 0

    @classmethod
    def _next_id(cls) -> str:
        cls._counter += 1
        return f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{cls._counter:04d}"

    @classmethod
    def user_id(cls) -> str:
        return f"usr_test_{cls._next_id()}"

    @classmethod
    def device_id(cls) -> str:
        return f"dev_test_{cls._next_id()}"

    @classmethod
    def org_id(cls) -> str:
        return f"org_test_{cls._next_id()}"

    @classmethod
    def email(cls) -> str:
        return f"test_{cls._next_id()}@example.com"

    @classmethod
    def serial_number(cls) -> str:
        return f"SN-TEST-{cls._next_id().upper()}"

    @classmethod
    def billing_id(cls) -> str:
        return f"bill_test_{cls._next_id()}"


@pytest.fixture
def generate() -> TestDataGenerator:
    """Provide test data generator"""
    return TestDataGenerator()


# =============================================================================
# Sample Data Fixtures
# =============================================================================

@pytest.fixture
def sample_user(generate: TestDataGenerator) -> Dict[str, Any]:
    """Generate a sample user dict"""
    return {
        "user_id": generate.user_id(),
        "email": generate.email(),
        "name": "Test User",
        "subscription_plan": "free",
        "is_active": True,
    }


@pytest.fixture
def sample_device(generate: TestDataGenerator, sample_user: Dict) -> Dict[str, Any]:
    """Generate a sample device dict"""
    return {
        "device_id": generate.device_id(),
        "device_name": "Test Device",
        "device_type": "smart_frame",
        "serial_number": generate.serial_number(),
        "owner_user_id": sample_user["user_id"],
        "status": "active",
    }


@pytest.fixture
def sample_billing_request(sample_user: Dict) -> Dict[str, Any]:
    """Generate a sample billing request"""
    return {
        "user_id": sample_user["user_id"],
        "product_id": "gpt-4",
        "usage_amount": 100,
    }


# =============================================================================
# Assertion Helpers
# =============================================================================

class AssertionHelpers:
    """Custom assertion helpers for tests"""

    @staticmethod
    def assert_http_success(response, expected_status: int = 200):
        """Assert HTTP response is successful"""
        assert response.status_code == expected_status, \
            f"Expected {expected_status}, got {response.status_code}: {response.text}"

    @staticmethod
    def assert_has_fields(data: Dict, fields: List[str]):
        """Assert dict has required fields"""
        missing = [f for f in fields if f not in data]
        assert not missing, f"Missing fields: {missing}"

    @staticmethod
    def assert_event_published(events: List[Dict], event_type: str, **kwargs):
        """Assert an event was published with expected data"""
        matching = [e for e in events if e.get("type") == event_type]
        assert matching, f"Event '{event_type}' not found in {events}"

        if kwargs:
            for event in matching:
                if all(event.get("data", {}).get(k) == v for k, v in kwargs.items()):
                    return event
            assert False, f"No event matched criteria: {kwargs}"

        return matching[0]


@pytest.fixture
def assertions() -> AssertionHelpers:
    """Provide assertion helpers"""
    return AssertionHelpers()


# =============================================================================
# Skip Markers Based on Environment
# =============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers and skip logic"""
    # Add marker descriptions
    config.addinivalue_line("markers", "api: API contract tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "component: Component tests")
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "eval: DeepEval tests")


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on markers and environment"""

    # Check available infrastructure
    skip_db = pytest.mark.skip(reason="PostgreSQL not available")
    skip_nats = pytest.mark.skip(reason="NATS not available")
    skip_ai = pytest.mark.skip(reason="AI model access not configured")

    for item in items:
        # Skip DB tests if running in --unit-only mode
        if "requires_db" in item.keywords and os.getenv("SKIP_DB_TESTS"):
            item.add_marker(skip_db)

        # Skip NATS tests if not available
        if "requires_nats" in item.keywords and os.getenv("SKIP_NATS_TESTS"):
            item.add_marker(skip_nats)

        # Skip AI tests if no API key
        if "requires_ai" in item.keywords and not os.getenv("OPENAI_API_KEY"):
            item.add_marker(skip_ai)


# =============================================================================
# Logging Configuration
# =============================================================================

@pytest.fixture(autouse=True)
def test_logger(request):
    """Log test start/end for debugging"""
    test_name = request.node.name
    print(f"\n{'='*60}")
    print(f"Starting: {test_name}")
    print(f"{'='*60}")

    yield

    print(f"\n{'='*60}")
    print(f"Finished: {test_name}")
    print(f"{'='*60}")
