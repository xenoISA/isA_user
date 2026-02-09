"""
Billing Service - Component Test Configuration

Service-specific fixtures with mocked dependencies.
"""
import pytest
import pytest_asyncio
from .mocks import (
    MockBillingRepository,
    MockEventBus,
    MockWalletClient,
    MockSubscriptionClient,
    MockProductClient,
)


@pytest.fixture
def mock_billing_repository():
    """Provide MockBillingRepository"""
    return MockBillingRepository()


@pytest.fixture
def mock_event_bus():
    """Provide MockEventBus"""
    return MockEventBus()


@pytest.fixture
def mock_wallet_client():
    """Provide MockWalletClient"""
    return MockWalletClient()


@pytest.fixture
def mock_subscription_client():
    """Provide MockSubscriptionClient"""
    return MockSubscriptionClient()


@pytest.fixture
def mock_product_client():
    """Provide MockProductClient"""
    return MockProductClient()


@pytest_asyncio.fixture
async def billing_service(
    mock_billing_repository,
    mock_event_bus,
    mock_wallet_client,
    mock_subscription_client,
    mock_product_client
):
    """Create BillingService with mocked dependencies"""
    from microservices.billing_service.billing_service import BillingService

    service = BillingService(
        repository=mock_billing_repository,
        event_bus=mock_event_bus,
        wallet_client=mock_wallet_client,
        subscription_client=mock_subscription_client,
        product_client=mock_product_client,
    )

    return service


@pytest_asyncio.fixture
async def billing_service_no_event_bus(
    mock_billing_repository,
    mock_wallet_client,
    mock_subscription_client,
    mock_product_client
):
    """Create BillingService without event bus for testing fallback behavior"""
    from microservices.billing_service.billing_service import BillingService

    service = BillingService(
        repository=mock_billing_repository,
        event_bus=None,
        wallet_client=mock_wallet_client,
        subscription_client=mock_subscription_client,
        product_client=mock_product_client,
    )

    return service
