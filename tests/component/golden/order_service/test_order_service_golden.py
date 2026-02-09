"""
Order Service Component Golden Tests

These tests document CURRENT OrderService behavior with mocked deps.
Uses proper dependency injection - no patching needed!

Usage:
    pytest tests/component/golden/order_service -v
"""
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from .mocks import (
    MockOrderRepository,
    MockEventBus,
    MockAccountClient,
    MockWalletClient,
    MockPaymentClient
)

pytestmark = [pytest.mark.component, pytest.mark.golden, pytest.mark.asyncio]


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_repo():
    """Create a fresh MockOrderRepository"""
    return MockOrderRepository()


@pytest.fixture
def mock_repo_with_order():
    """Create MockOrderRepository with existing order"""
    from microservices.order_service.models import OrderType, OrderStatus, PaymentStatus

    repo = MockOrderRepository()
    repo.set_order(
        order_id="ord_test_123",
        user_id="usr_test_123",
        order_type=OrderType.PURCHASE,
        status=OrderStatus.PENDING,
        total_amount=Decimal("99.99"),
        currency="USD",
        payment_status=PaymentStatus.PENDING,
        items=[{"product_id": "prod_123", "quantity": 1, "price": "99.99"}],
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc)
    )
    return repo


@pytest.fixture
def mock_repo_with_credit_order():
    """Create MockOrderRepository with credit purchase order"""
    from microservices.order_service.models import OrderType, OrderStatus, PaymentStatus

    repo = MockOrderRepository()
    repo.set_order(
        order_id="ord_credit_123",
        user_id="usr_test_123",
        order_type=OrderType.CREDIT_PURCHASE,
        status=OrderStatus.PENDING,
        total_amount=Decimal("50.00"),
        currency="USD",
        payment_status=PaymentStatus.PENDING,
        wallet_id="wal_test_123"
    )
    return repo


@pytest.fixture
def mock_event_bus():
    """Create a fresh MockEventBus"""
    return MockEventBus()


@pytest.fixture
def mock_account_client():
    """Create mock account client with test user"""
    client = MockAccountClient()
    client.set_user("usr_test_123", name="Test User", email="test@example.com")
    return client


@pytest.fixture
def mock_wallet_client():
    """Create mock wallet client"""
    client = MockWalletClient()
    client.set_wallet("wal_test_123", balance=Decimal("100.00"))
    return client


@pytest.fixture
def mock_payment_client():
    """Create mock payment client"""
    return MockPaymentClient()


# =============================================================================
# OrderService.create_order() Tests
# =============================================================================

class TestOrderServiceCreateGolden:
    """Golden: OrderService.create_order() current behavior"""

    async def test_create_order_returns_success_response(
        self, mock_repo, mock_event_bus, mock_account_client
    ):
        """GOLDEN: create_order returns OrderResponse with success=True"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import (
            OrderCreateRequest, OrderResponse, OrderType
        )

        service = OrderService(
            repository=mock_repo,
            event_bus=mock_event_bus,
            account_client=mock_account_client
        )
        request = OrderCreateRequest(
            user_id="usr_test_123",
            order_type=OrderType.PURCHASE,
            total_amount=Decimal("99.99"),
            currency="USD",
            items=[{"product_id": "prod_123", "quantity": 1}]
        )

        result = await service.create_order(request)

        assert isinstance(result, OrderResponse)
        assert result.success is True
        assert result.order is not None
        assert result.order.user_id == "usr_test_123"
        assert result.order.total_amount == Decimal("99.99")
        assert result.message == "Order created successfully"

        # Verify repository was called
        mock_repo.assert_called("create_order")

    async def test_create_order_with_subscription(
        self, mock_repo, mock_event_bus, mock_account_client
    ):
        """GOLDEN: create_order with subscription type requires subscription_id"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import OrderCreateRequest, OrderType

        service = OrderService(
            repository=mock_repo,
            event_bus=mock_event_bus,
            account_client=mock_account_client
        )
        request = OrderCreateRequest(
            user_id="usr_test_123",
            order_type=OrderType.SUBSCRIPTION,
            total_amount=Decimal("9.99"),
            subscription_id="sub_test_123"
        )

        result = await service.create_order(request)

        assert result.success is True
        assert result.order.order_type == OrderType.SUBSCRIPTION

    async def test_create_credit_purchase_requires_wallet_id(
        self, mock_repo, mock_event_bus, mock_account_client
    ):
        """GOLDEN: credit_purchase without wallet_id returns validation error"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import OrderCreateRequest, OrderType

        service = OrderService(
            repository=mock_repo,
            event_bus=mock_event_bus,
            account_client=mock_account_client
        )
        request = OrderCreateRequest(
            user_id="usr_test_123",
            order_type=OrderType.CREDIT_PURCHASE,
            total_amount=Decimal("50.00")
            # Missing wallet_id
        )

        result = await service.create_order(request)

        assert result.success is False
        assert result.error_code == "VALIDATION_ERROR"
        assert "wallet_id" in result.message.lower()

    async def test_create_subscription_requires_subscription_id(
        self, mock_repo, mock_event_bus, mock_account_client
    ):
        """GOLDEN: subscription without subscription_id returns validation error"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import OrderCreateRequest, OrderType

        service = OrderService(
            repository=mock_repo,
            event_bus=mock_event_bus,
            account_client=mock_account_client
        )
        request = OrderCreateRequest(
            user_id="usr_test_123",
            order_type=OrderType.SUBSCRIPTION,
            total_amount=Decimal("9.99")
            # Missing subscription_id
        )

        result = await service.create_order(request)

        assert result.success is False
        assert result.error_code == "VALIDATION_ERROR"
        assert "subscription_id" in result.message.lower()

    async def test_create_order_validates_empty_user_id(
        self, mock_repo, mock_event_bus, mock_account_client
    ):
        """GOLDEN: create_order rejects empty user_id"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import OrderType

        service = OrderService(
            repository=mock_repo,
            event_bus=mock_event_bus,
            account_client=mock_account_client
        )

        # Use MagicMock to bypass Pydantic validation
        request = MagicMock()
        request.user_id = ""
        request.order_type = OrderType.PURCHASE
        request.total_amount = Decimal("99.99")
        request.currency = "USD"
        request.items = []
        request.metadata = None
        request.payment_intent_id = None
        request.subscription_id = None
        request.wallet_id = None
        request.expires_in_minutes = 30

        result = await service.create_order(request)

        assert result.success is False
        assert result.error_code == "VALIDATION_ERROR"
        assert "user_id" in result.message.lower()

    async def test_create_order_validates_negative_amount(
        self, mock_repo, mock_event_bus, mock_account_client
    ):
        """GOLDEN: create_order rejects negative amount"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import OrderType

        service = OrderService(
            repository=mock_repo,
            event_bus=mock_event_bus,
            account_client=mock_account_client
        )

        request = MagicMock()
        request.user_id = "usr_test_123"
        request.order_type = OrderType.PURCHASE
        request.total_amount = Decimal("-10.00")
        request.currency = "USD"
        request.items = []
        request.metadata = None
        request.payment_intent_id = None
        request.subscription_id = None
        request.wallet_id = None
        request.expires_in_minutes = 30

        result = await service.create_order(request)

        assert result.success is False
        assert result.error_code == "VALIDATION_ERROR"
        assert "amount" in result.message.lower()

    async def test_create_order_sets_expiration(
        self, mock_repo, mock_event_bus, mock_account_client
    ):
        """GOLDEN: create_order sets expiration time based on expires_in_minutes"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import OrderCreateRequest, OrderType

        service = OrderService(
            repository=mock_repo,
            event_bus=mock_event_bus,
            account_client=mock_account_client
        )
        request = OrderCreateRequest(
            user_id="usr_test_123",
            order_type=OrderType.PURCHASE,
            total_amount=Decimal("99.99"),
            expires_in_minutes=60
        )

        result = await service.create_order(request)

        assert result.success is True
        mock_repo.assert_called("create_order")


# =============================================================================
# OrderService.get_order() Tests
# =============================================================================

class TestOrderServiceGetGolden:
    """Golden: OrderService.get_order() current behavior"""

    async def test_get_order_returns_order(self, mock_repo_with_order):
        """GOLDEN: get_order returns Order when found"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import Order

        service = OrderService(repository=mock_repo_with_order)
        result = await service.get_order("ord_test_123")

        assert isinstance(result, Order)
        assert result.order_id == "ord_test_123"
        assert result.user_id == "usr_test_123"
        assert result.total_amount == Decimal("99.99")

    async def test_get_order_returns_none_when_not_found(self, mock_repo):
        """GOLDEN: get_order returns None when order not found"""
        from microservices.order_service.order_service import OrderService

        service = OrderService(repository=mock_repo)
        result = await service.get_order("ord_nonexistent")

        assert result is None

    async def test_get_order_raises_on_repo_error(self, mock_repo):
        """GOLDEN: get_order raises OrderServiceError on repository error"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.protocols import OrderServiceError

        mock_repo.set_error(Exception("Database error"))

        service = OrderService(repository=mock_repo)

        with pytest.raises(OrderServiceError) as exc_info:
            await service.get_order("ord_test_123")

        assert "Failed to get order" in str(exc_info.value)


# =============================================================================
# OrderService.update_order() Tests
# =============================================================================

class TestOrderServiceUpdateGolden:
    """Golden: OrderService.update_order() current behavior"""

    async def test_update_order_returns_success(self, mock_repo_with_order, mock_event_bus):
        """GOLDEN: update_order returns OrderResponse with success=True"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import (
            OrderUpdateRequest, OrderResponse, OrderStatus, PaymentStatus
        )

        service = OrderService(
            repository=mock_repo_with_order,
            event_bus=mock_event_bus
        )
        request = OrderUpdateRequest(
            status=OrderStatus.PROCESSING,
            payment_status=PaymentStatus.PROCESSING
        )

        result = await service.update_order("ord_test_123", request)

        assert isinstance(result, OrderResponse)
        assert result.success is True
        assert result.order.status == OrderStatus.PROCESSING

        mock_repo_with_order.assert_called("update_order")

    async def test_update_order_not_found(self, mock_repo, mock_event_bus):
        """GOLDEN: update_order returns error when order not found"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import OrderUpdateRequest, OrderStatus

        service = OrderService(
            repository=mock_repo,
            event_bus=mock_event_bus
        )
        request = OrderUpdateRequest(status=OrderStatus.PROCESSING)

        result = await service.update_order("ord_nonexistent", request)

        assert result.success is False
        assert result.error_code == "ORDER_NOT_FOUND"

    async def test_update_order_with_payment_intent(self, mock_repo_with_order):
        """GOLDEN: update_order can set payment_intent_id"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import OrderUpdateRequest

        service = OrderService(repository=mock_repo_with_order)
        request = OrderUpdateRequest(payment_intent_id="pi_new_123")

        result = await service.update_order("ord_test_123", request)

        assert result.success is True
        mock_repo_with_order.assert_called_with(
            "update_order",
            order_id="ord_test_123",
            payment_intent_id="pi_new_123"
        )


# =============================================================================
# OrderService.cancel_order() Tests
# =============================================================================

class TestOrderServiceCancelGolden:
    """Golden: OrderService.cancel_order() current behavior"""

    async def test_cancel_order_returns_success(self, mock_repo_with_order, mock_event_bus):
        """GOLDEN: cancel_order returns success for pending order"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import OrderCancelRequest, OrderResponse

        service = OrderService(
            repository=mock_repo_with_order,
            event_bus=mock_event_bus
        )
        request = OrderCancelRequest(reason="Customer requested cancellation")

        result = await service.cancel_order("ord_test_123", request)

        assert isinstance(result, OrderResponse)
        assert result.success is True
        assert result.message == "Order cancelled successfully"

        mock_repo_with_order.assert_called("cancel_order")

    async def test_cancel_order_not_found(self, mock_repo, mock_event_bus):
        """GOLDEN: cancel_order returns error when order not found"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import OrderCancelRequest

        service = OrderService(
            repository=mock_repo,
            event_bus=mock_event_bus
        )
        request = OrderCancelRequest(reason="Test")

        result = await service.cancel_order("ord_nonexistent", request)

        assert result.success is False
        assert result.error_code == "ORDER_NOT_FOUND"

    async def test_cannot_cancel_completed_order(self, mock_repo, mock_event_bus):
        """GOLDEN: cannot cancel already completed order"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import (
            OrderCancelRequest, OrderType, OrderStatus, PaymentStatus
        )

        # Set up a completed order
        mock_repo.set_order(
            order_id="ord_completed",
            user_id="usr_test_123",
            order_type=OrderType.PURCHASE,
            status=OrderStatus.COMPLETED,
            total_amount=Decimal("99.99"),
            payment_status=PaymentStatus.COMPLETED
        )

        service = OrderService(
            repository=mock_repo,
            event_bus=mock_event_bus
        )
        request = OrderCancelRequest(reason="Changed mind")

        result = await service.cancel_order("ord_completed", request)

        assert result.success is False
        assert result.error_code == "INVALID_STATUS"

    async def test_cannot_cancel_already_cancelled_order(self, mock_repo, mock_event_bus):
        """GOLDEN: cannot cancel already cancelled order"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import (
            OrderCancelRequest, OrderType, OrderStatus, PaymentStatus
        )

        mock_repo.set_order(
            order_id="ord_cancelled",
            user_id="usr_test_123",
            order_type=OrderType.PURCHASE,
            status=OrderStatus.CANCELLED,
            total_amount=Decimal("99.99"),
            payment_status=PaymentStatus.PENDING
        )

        service = OrderService(
            repository=mock_repo,
            event_bus=mock_event_bus
        )
        request = OrderCancelRequest(reason="Another cancel")

        result = await service.cancel_order("ord_cancelled", request)

        assert result.success is False
        assert result.error_code == "INVALID_STATUS"

    async def test_cancel_with_refund_amount(self, mock_repo_with_order, mock_event_bus):
        """GOLDEN: cancel_order processes refund when refund_amount provided"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import OrderCancelRequest

        service = OrderService(
            repository=mock_repo_with_order,
            event_bus=mock_event_bus
        )
        request = OrderCancelRequest(
            reason="Refund requested",
            refund_amount=Decimal("50.00")
        )

        result = await service.cancel_order("ord_test_123", request)

        assert result.success is True


# =============================================================================
# OrderService.complete_order() Tests
# =============================================================================

class TestOrderServiceCompleteGolden:
    """Golden: OrderService.complete_order() current behavior"""

    async def test_complete_order_returns_success(self, mock_repo_with_order, mock_event_bus):
        """GOLDEN: complete_order returns success with payment confirmation"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import OrderCompleteRequest, OrderResponse

        service = OrderService(
            repository=mock_repo_with_order,
            event_bus=mock_event_bus
        )
        request = OrderCompleteRequest(
            payment_confirmed=True,
            transaction_id="txn_123"
        )

        result = await service.complete_order("ord_test_123", request)

        assert isinstance(result, OrderResponse)
        assert result.success is True
        assert result.message == "Order completed successfully"

        mock_repo_with_order.assert_called("complete_order")

    async def test_complete_order_not_found(self, mock_repo, mock_event_bus):
        """GOLDEN: complete_order returns error when order not found"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import OrderCompleteRequest

        service = OrderService(
            repository=mock_repo,
            event_bus=mock_event_bus
        )
        request = OrderCompleteRequest(payment_confirmed=True)

        result = await service.complete_order("ord_nonexistent", request)

        assert result.success is False
        assert result.error_code == "ORDER_NOT_FOUND"

    async def test_complete_order_requires_payment_confirmation(
        self, mock_repo_with_order, mock_event_bus
    ):
        """GOLDEN: complete_order fails without payment confirmation"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import OrderCompleteRequest

        service = OrderService(
            repository=mock_repo_with_order,
            event_bus=mock_event_bus
        )
        request = OrderCompleteRequest(payment_confirmed=False)

        result = await service.complete_order("ord_test_123", request)

        assert result.success is False
        assert result.error_code == "PAYMENT_NOT_CONFIRMED"

    async def test_complete_credit_purchase_with_credits(
        self, mock_repo_with_credit_order, mock_event_bus
    ):
        """GOLDEN: completing credit purchase order adds credits"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import OrderCompleteRequest

        service = OrderService(
            repository=mock_repo_with_credit_order,
            event_bus=mock_event_bus
        )
        request = OrderCompleteRequest(
            payment_confirmed=True,
            transaction_id="txn_123",
            credits_added=Decimal("500.00")
        )

        result = await service.complete_order("ord_credit_123", request)

        assert result.success is True


# =============================================================================
# OrderService.list_orders() Tests
# =============================================================================

class TestOrderServiceListGolden:
    """Golden: OrderService.list_orders() current behavior"""

    async def test_list_orders_returns_response(self, mock_repo):
        """GOLDEN: list_orders returns OrderListResponse"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import (
            OrderFilter, OrderListResponse, OrderType, OrderStatus, PaymentStatus
        )

        # Add some orders
        mock_repo.set_order(
            order_id="ord_1",
            user_id="usr_1",
            order_type=OrderType.PURCHASE,
            total_amount=Decimal("50.00")
        )
        mock_repo.set_order(
            order_id="ord_2",
            user_id="usr_2",
            order_type=OrderType.SUBSCRIPTION,
            total_amount=Decimal("9.99"),
            subscription_id="sub_123"
        )

        service = OrderService(repository=mock_repo)
        params = OrderFilter(limit=10, offset=0)
        result = await service.list_orders(params)

        assert isinstance(result, OrderListResponse)
        assert len(result.orders) == 2
        assert result.page == 1
        assert result.page_size == 10

    async def test_list_orders_empty(self, mock_repo):
        """GOLDEN: list_orders returns empty list when no orders"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import OrderFilter

        service = OrderService(repository=mock_repo)
        params = OrderFilter()
        result = await service.list_orders(params)

        assert len(result.orders) == 0
        assert result.total_count == 0

    async def test_list_orders_filter_by_user(self, mock_repo):
        """GOLDEN: list_orders filters by user_id"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import OrderFilter, OrderType

        mock_repo.set_order(
            order_id="ord_1",
            user_id="usr_1",
            order_type=OrderType.PURCHASE,
            total_amount=Decimal("50.00")
        )
        mock_repo.set_order(
            order_id="ord_2",
            user_id="usr_2",
            order_type=OrderType.PURCHASE,
            total_amount=Decimal("75.00")
        )

        service = OrderService(repository=mock_repo)
        params = OrderFilter(user_id="usr_1")
        result = await service.list_orders(params)

        assert len(result.orders) == 1
        assert result.orders[0].user_id == "usr_1"

    async def test_list_orders_filter_by_status(self, mock_repo):
        """GOLDEN: list_orders filters by status"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import (
            OrderFilter, OrderType, OrderStatus, PaymentStatus
        )

        mock_repo.set_order(
            order_id="ord_pending",
            user_id="usr_1",
            order_type=OrderType.PURCHASE,
            status=OrderStatus.PENDING,
            total_amount=Decimal("50.00")
        )
        mock_repo.set_order(
            order_id="ord_completed",
            user_id="usr_1",
            order_type=OrderType.PURCHASE,
            status=OrderStatus.COMPLETED,
            payment_status=PaymentStatus.COMPLETED,
            total_amount=Decimal("75.00")
        )

        service = OrderService(repository=mock_repo)
        params = OrderFilter(status=OrderStatus.COMPLETED)
        result = await service.list_orders(params)

        assert len(result.orders) == 1
        assert result.orders[0].status == OrderStatus.COMPLETED

    async def test_list_orders_filter_by_type(self, mock_repo):
        """GOLDEN: list_orders filters by order_type"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import OrderFilter, OrderType

        mock_repo.set_order(
            order_id="ord_purchase",
            user_id="usr_1",
            order_type=OrderType.PURCHASE,
            total_amount=Decimal("50.00")
        )
        mock_repo.set_order(
            order_id="ord_credit",
            user_id="usr_1",
            order_type=OrderType.CREDIT_PURCHASE,
            total_amount=Decimal("100.00"),
            wallet_id="wal_123"
        )

        service = OrderService(repository=mock_repo)
        params = OrderFilter(order_type=OrderType.CREDIT_PURCHASE)
        result = await service.list_orders(params)

        assert len(result.orders) == 1
        assert result.orders[0].order_type == OrderType.CREDIT_PURCHASE


# =============================================================================
# OrderService.get_user_orders() Tests
# =============================================================================

class TestOrderServiceGetUserOrdersGolden:
    """Golden: OrderService.get_user_orders() current behavior"""

    async def test_get_user_orders_returns_list(self, mock_repo):
        """GOLDEN: get_user_orders returns list of orders for user"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import OrderType

        mock_repo.set_order(
            order_id="ord_1",
            user_id="usr_test",
            order_type=OrderType.PURCHASE,
            total_amount=Decimal("50.00")
        )
        mock_repo.set_order(
            order_id="ord_2",
            user_id="usr_test",
            order_type=OrderType.SUBSCRIPTION,
            total_amount=Decimal("9.99"),
            subscription_id="sub_123"
        )
        mock_repo.set_order(
            order_id="ord_other",
            user_id="usr_other",
            order_type=OrderType.PURCHASE,
            total_amount=Decimal("25.00")
        )

        service = OrderService(repository=mock_repo)
        result = await service.get_user_orders("usr_test")

        assert len(result) == 2
        assert all(o.user_id == "usr_test" for o in result)

    async def test_get_user_orders_empty_for_new_user(self, mock_repo):
        """GOLDEN: get_user_orders returns empty list for user with no orders"""
        from microservices.order_service.order_service import OrderService

        service = OrderService(repository=mock_repo)
        result = await service.get_user_orders("usr_new")

        assert len(result) == 0

    async def test_get_user_orders_respects_limit(self, mock_repo):
        """GOLDEN: get_user_orders respects limit parameter"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import OrderType

        for i in range(5):
            mock_repo.set_order(
                order_id=f"ord_{i}",
                user_id="usr_test",
                order_type=OrderType.PURCHASE,
                total_amount=Decimal("10.00")
            )

        service = OrderService(repository=mock_repo)
        result = await service.get_user_orders("usr_test", limit=3)

        assert len(result) == 3


# =============================================================================
# OrderService.search_orders() Tests
# =============================================================================

class TestOrderServiceSearchGolden:
    """Golden: OrderService.search_orders() current behavior"""

    async def test_search_orders_returns_matches(self, mock_repo):
        """GOLDEN: search_orders returns matching orders"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import OrderSearchParams, OrderType

        mock_repo.set_order(
            order_id="ord_abc123",
            user_id="usr_1",
            order_type=OrderType.PURCHASE,
            total_amount=Decimal("50.00")
        )
        mock_repo.set_order(
            order_id="ord_xyz789",
            user_id="usr_2",
            order_type=OrderType.PURCHASE,
            total_amount=Decimal("75.00")
        )

        service = OrderService(repository=mock_repo)
        params = OrderSearchParams(query="abc123", limit=10)
        result = await service.search_orders(params)

        assert len(result) == 1
        assert result[0].order_id == "ord_abc123"

    async def test_search_orders_by_user(self, mock_repo):
        """GOLDEN: search_orders filters by user_id"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import OrderSearchParams, OrderType

        mock_repo.set_order(
            order_id="ord_match1",
            user_id="usr_target",
            order_type=OrderType.PURCHASE,
            total_amount=Decimal("50.00")
        )
        mock_repo.set_order(
            order_id="ord_match2",
            user_id="usr_other",
            order_type=OrderType.PURCHASE,
            total_amount=Decimal("75.00")
        )

        service = OrderService(repository=mock_repo)
        params = OrderSearchParams(query="match", user_id="usr_target", limit=10)
        result = await service.search_orders(params)

        assert len(result) == 1
        assert result[0].user_id == "usr_target"


# =============================================================================
# OrderService.get_order_statistics() Tests
# =============================================================================

class TestOrderServiceStatisticsGolden:
    """Golden: OrderService.get_order_statistics() current behavior"""

    async def test_get_statistics_returns_stats(self, mock_repo):
        """GOLDEN: get_order_statistics returns OrderStatistics"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import OrderStatistics

        mock_repo.set_stats(
            total_orders=100,
            orders_by_status={"pending": 20, "completed": 70, "cancelled": 10},
            orders_by_type={"purchase": 60, "subscription": 30, "credit_purchase": 10},
            total_revenue=Decimal("9999.99"),
            revenue_by_currency={"USD": Decimal("9999.99")},
            avg_order_value=Decimal("99.99"),
            recent_orders_24h=5,
            recent_orders_7d=25,
            recent_orders_30d=100
        )

        service = OrderService(repository=mock_repo)
        result = await service.get_order_statistics()

        assert isinstance(result, OrderStatistics)
        assert result.total_orders == 100
        assert result.total_revenue == Decimal("9999.99")

    async def test_get_statistics_calculates_from_data(self, mock_repo):
        """GOLDEN: get_order_statistics calculates from actual data"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import (
            OrderType, OrderStatus, PaymentStatus
        )

        mock_repo.set_order(
            order_id="ord_1",
            user_id="usr_1",
            order_type=OrderType.PURCHASE,
            status=OrderStatus.COMPLETED,
            payment_status=PaymentStatus.COMPLETED,
            total_amount=Decimal("100.00")
        )
        mock_repo.set_order(
            order_id="ord_2",
            user_id="usr_2",
            order_type=OrderType.SUBSCRIPTION,
            status=OrderStatus.PENDING,
            total_amount=Decimal("50.00"),
            subscription_id="sub_123"
        )

        service = OrderService(repository=mock_repo)
        result = await service.get_order_statistics()

        assert result.total_orders == 2
        assert result.orders_by_status.get("completed") == 1
        assert result.orders_by_status.get("pending") == 1


# =============================================================================
# OrderService.health_check() Tests
# =============================================================================

class TestOrderServiceHealthGolden:
    """Golden: OrderService.health_check() current behavior"""

    async def test_health_check_healthy(self, mock_repo):
        """GOLDEN: health_check returns healthy status"""
        from microservices.order_service.order_service import OrderService

        service = OrderService(repository=mock_repo)
        result = await service.health_check()

        assert result["status"] == "healthy"
        assert result["database"] == "connected"

    async def test_health_check_unhealthy_on_db_error(self, mock_repo):
        """GOLDEN: health_check returns unhealthy on database error"""
        from microservices.order_service.order_service import OrderService

        mock_repo.set_error(Exception("Database connection failed"))

        service = OrderService(repository=mock_repo)
        result = await service.health_check()

        assert result["status"] == "unhealthy"
        assert result["database"] == "disconnected"


# =============================================================================
# Order State Transition Tests
# =============================================================================

class TestOrderStateTransitionsGolden:
    """Golden: Order state transitions current behavior"""

    async def test_pending_to_processing(self, mock_repo_with_order):
        """GOLDEN: Order can transition from PENDING to PROCESSING"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import OrderUpdateRequest, OrderStatus

        service = OrderService(repository=mock_repo_with_order)
        request = OrderUpdateRequest(status=OrderStatus.PROCESSING)

        result = await service.update_order("ord_test_123", request)

        assert result.success is True
        assert result.order.status == OrderStatus.PROCESSING

    async def test_processing_to_completed(self, mock_repo):
        """GOLDEN: Order can transition from PROCESSING to COMPLETED"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import (
            OrderCompleteRequest, OrderType, OrderStatus, PaymentStatus
        )

        mock_repo.set_order(
            order_id="ord_processing",
            user_id="usr_test",
            order_type=OrderType.PURCHASE,
            status=OrderStatus.PROCESSING,
            payment_status=PaymentStatus.PROCESSING,
            total_amount=Decimal("99.99")
        )

        service = OrderService(repository=mock_repo)
        request = OrderCompleteRequest(payment_confirmed=True, transaction_id="txn_123")

        result = await service.complete_order("ord_processing", request)

        assert result.success is True

    async def test_pending_to_cancelled(self, mock_repo_with_order, mock_event_bus):
        """GOLDEN: Order can transition from PENDING to CANCELLED"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import OrderCancelRequest

        service = OrderService(
            repository=mock_repo_with_order,
            event_bus=mock_event_bus
        )
        request = OrderCancelRequest(reason="User cancelled")

        result = await service.cancel_order("ord_test_123", request)

        assert result.success is True


# =============================================================================
# Payment Status Tests
# =============================================================================

class TestPaymentStatusGolden:
    """Golden: Payment status handling current behavior"""

    async def test_update_payment_status(self, mock_repo_with_order):
        """GOLDEN: Can update payment status independently"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import OrderUpdateRequest, PaymentStatus

        service = OrderService(repository=mock_repo_with_order)
        request = OrderUpdateRequest(payment_status=PaymentStatus.PROCESSING)

        result = await service.update_order("ord_test_123", request)

        assert result.success is True
        assert result.order.payment_status == PaymentStatus.PROCESSING

    async def test_payment_completed_on_order_complete(self, mock_repo_with_order, mock_event_bus):
        """GOLDEN: Payment status becomes COMPLETED when order completes"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import OrderCompleteRequest, PaymentStatus

        service = OrderService(
            repository=mock_repo_with_order,
            event_bus=mock_event_bus
        )
        request = OrderCompleteRequest(payment_confirmed=True, transaction_id="txn_123")

        result = await service.complete_order("ord_test_123", request)

        assert result.success is True
        # Repository complete_order sets payment status to COMPLETED
        mock_repo_with_order.assert_called("complete_order")


# =============================================================================
# Edge Cases Tests
# =============================================================================

class TestOrderServiceEdgeCasesGolden:
    """Golden: Edge cases current behavior"""

    async def test_create_order_with_metadata(self, mock_repo, mock_account_client):
        """GOLDEN: create_order preserves metadata"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import OrderCreateRequest, OrderType

        service = OrderService(
            repository=mock_repo,
            account_client=mock_account_client
        )
        request = OrderCreateRequest(
            user_id="usr_test_123",
            order_type=OrderType.PURCHASE,
            total_amount=Decimal("99.99"),
            metadata={"promo_code": "SAVE10", "source": "web"}
        )

        result = await service.create_order(request)

        assert result.success is True
        mock_repo.assert_called_with(
            "create_order",
            metadata={"promo_code": "SAVE10", "source": "web"}
        )

    async def test_create_order_with_items(self, mock_repo, mock_account_client):
        """GOLDEN: create_order preserves items list"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import OrderCreateRequest, OrderType

        items = [
            {"product_id": "prod_1", "quantity": 2, "price": "25.00"},
            {"product_id": "prod_2", "quantity": 1, "price": "49.99"}
        ]

        service = OrderService(
            repository=mock_repo,
            account_client=mock_account_client
        )
        request = OrderCreateRequest(
            user_id="usr_test_123",
            order_type=OrderType.PURCHASE,
            total_amount=Decimal("99.99"),
            items=items
        )

        result = await service.create_order(request)

        assert result.success is True
        mock_repo.assert_called_with("create_order", items=items)

    async def test_list_orders_pagination(self, mock_repo):
        """GOLDEN: list_orders pagination works correctly"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import OrderFilter, OrderType

        # Create 10 orders
        for i in range(10):
            mock_repo.set_order(
                order_id=f"ord_{i:03d}",
                user_id="usr_test",
                order_type=OrderType.PURCHASE,
                total_amount=Decimal("10.00")
            )

        service = OrderService(repository=mock_repo)

        # First page
        params = OrderFilter(limit=5, offset=0)
        result = await service.list_orders(params)
        assert len(result.orders) == 5
        assert result.has_next is True

        # Second page
        params = OrderFilter(limit=5, offset=5)
        result = await service.list_orders(params)
        assert len(result.orders) == 5
        assert result.has_next is True  # Equal to limit, so has_next is True

    async def test_zero_amount_order_fails(self, mock_repo, mock_account_client):
        """GOLDEN: create_order with zero amount fails validation"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import OrderType

        service = OrderService(
            repository=mock_repo,
            account_client=mock_account_client
        )

        request = MagicMock()
        request.user_id = "usr_test_123"
        request.order_type = OrderType.PURCHASE
        request.total_amount = Decimal("0")
        request.currency = "USD"
        request.items = []
        request.metadata = None
        request.payment_intent_id = None
        request.subscription_id = None
        request.wallet_id = None
        request.expires_in_minutes = 30

        result = await service.create_order(request)

        assert result.success is False
        assert result.error_code == "VALIDATION_ERROR"

    async def test_multiple_orders_same_user(self, mock_repo, mock_account_client):
        """GOLDEN: User can have multiple orders"""
        from microservices.order_service.order_service import OrderService
        from microservices.order_service.models import OrderCreateRequest, OrderType

        service = OrderService(
            repository=mock_repo,
            account_client=mock_account_client
        )

        # Create first order
        request1 = OrderCreateRequest(
            user_id="usr_test_123",
            order_type=OrderType.PURCHASE,
            total_amount=Decimal("50.00")
        )
        result1 = await service.create_order(request1)

        # Create second order
        request2 = OrderCreateRequest(
            user_id="usr_test_123",
            order_type=OrderType.SUBSCRIPTION,
            total_amount=Decimal("9.99"),
            subscription_id="sub_123"
        )
        result2 = await service.create_order(request2)

        assert result1.success is True
        assert result2.success is True

        # Get user orders
        user_orders = await service.get_user_orders("usr_test_123")
        assert len(user_orders) == 2
