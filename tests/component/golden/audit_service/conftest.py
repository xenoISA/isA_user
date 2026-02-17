"""
Audit Service Component Test Configuration

Provides fixtures for mocked dependencies:
- mock_repository: Mocked AuditRepositoryProtocol
- mock_event_bus: Mocked EventBusProtocol
- audit_service: AuditService with mock dependencies
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from tests.contracts.audit.data_contract import AuditTestDataFactory


class MockAuditRepository:
    """Mock implementation of AuditRepositoryProtocol"""

    def __init__(self):
        self.check_connection = AsyncMock(return_value=True)
        self.create_audit_event = AsyncMock()
        self.get_audit_events = AsyncMock(return_value=[])
        self.query_audit_events = AsyncMock(return_value=[])
        self.get_user_activities = AsyncMock(return_value=[])
        self.get_user_activity_summary = AsyncMock(return_value={})
        self.create_security_event = AsyncMock()
        self.get_security_events = AsyncMock(return_value=[])
        self.get_event_statistics = AsyncMock(return_value={})
        self.get_statistics = AsyncMock(return_value={})
        self.cleanup_old_events = AsyncMock(return_value=0)


class MockEventBus:
    """Mock implementation of EventBusProtocol"""

    def __init__(self):
        self.publish_event = AsyncMock()
        self.connect = AsyncMock()
        self.disconnect = AsyncMock()
        self.close = AsyncMock()


@pytest.fixture
def mock_repository():
    """Create mock repository"""
    return MockAuditRepository()


@pytest.fixture
def mock_event_bus():
    """Create mock event bus"""
    return MockEventBus()


@pytest_asyncio.fixture
async def audit_service(mock_repository, mock_event_bus):
    """Create AuditService with mock dependencies"""
    from microservices.audit_service.audit_service import AuditService
    service = AuditService(
        repository=mock_repository,
        event_bus=mock_event_bus,
    )
    return service


@pytest.fixture
def sample_audit_event():
    """Create sample audit event for testing"""
    return AuditTestDataFactory.make_audit_event_response()


@pytest.fixture
def sample_create_request():
    """Create sample create request for testing"""
    return AuditTestDataFactory.make_audit_event_create_request()


@pytest.fixture
def sample_query_request():
    """Create sample query request for testing"""
    return AuditTestDataFactory.make_audit_query_request()


@pytest.fixture
def sample_security_alert():
    """Create sample security alert for testing"""
    return AuditTestDataFactory.make_security_alert_request()
