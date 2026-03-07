"""
Billing Service TDD — Component Test Configuration

Reuses fixtures from golden tests.
"""
import pytest
import pytest_asyncio
from tests.component.golden.billing_service.mocks import (
    MockBillingRepository,
    MockEventBus,
    MockWalletClient,
    MockSubscriptionClient,
    MockProductClient,
)


@pytest.fixture
def mock_billing_repository():
    return MockBillingRepository()


@pytest.fixture
def mock_event_bus():
    return MockEventBus()


@pytest.fixture
def mock_wallet_client():
    return MockWalletClient()


@pytest.fixture
def mock_subscription_client():
    return MockSubscriptionClient()


@pytest.fixture
def mock_product_client():
    return MockProductClient()


@pytest_asyncio.fixture
async def billing_service(
    mock_billing_repository,
    mock_event_bus,
    mock_wallet_client,
    mock_subscription_client,
    mock_product_client,
):
    from microservices.billing_service.billing_service import BillingService

    return BillingService(
        repository=mock_billing_repository,
        event_bus=mock_event_bus,
        wallet_client=mock_wallet_client,
        subscription_client=mock_subscription_client,
        product_client=mock_product_client,
    )
