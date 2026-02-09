"""
Session Service - Component Test Configuration

Service-specific fixtures with mocked dependencies.
"""
import pytest
import pytest_asyncio
from .mocks import (
    MockSessionRepository,
    MockSessionMessageRepository,
    MockEventBus,
    MockAccountClient,
)


@pytest.fixture
def mock_session_repository():
    """Provide MockSessionRepository"""
    return MockSessionRepository()


@pytest.fixture
def mock_message_repository():
    """Provide MockSessionMessageRepository"""
    return MockSessionMessageRepository()


@pytest.fixture
def mock_event_bus():
    """Provide MockEventBus"""
    return MockEventBus()


@pytest.fixture
def mock_account_client():
    """Provide MockAccountClient"""
    return MockAccountClient()


@pytest_asyncio.fixture
async def session_service(
    mock_session_repository,
    mock_message_repository,
    mock_event_bus,
    mock_account_client
):
    """Create SessionService with mocked dependencies"""
    from microservices.session_service.session_service import SessionService

    service = SessionService(
        session_repo=mock_session_repository,
        message_repo=mock_message_repository,
        event_bus=mock_event_bus,
        account_client=mock_account_client,
    )

    return service


@pytest_asyncio.fixture
async def session_service_no_event_bus(
    mock_session_repository,
    mock_message_repository,
    mock_account_client
):
    """Create SessionService without event bus for testing fallback behavior"""
    from microservices.session_service.session_service import SessionService

    service = SessionService(
        session_repo=mock_session_repository,
        message_repo=mock_message_repository,
        event_bus=None,
        account_client=mock_account_client,
    )

    return service
