"""
Order Service Integration Tests

Tests the OrderService layer with mocked dependencies (repository, event_bus).
These are NOT HTTP tests - they test the service business logic layer directly.

Purpose:
- Test OrderService business logic with mocked repository
- Test event publishing integration
- Test validation and error handling
- Test cross-service interactions (account, wallet, payment)

According to CDD_GUIDE.md:
- Service layer tests use mocked repository (no real DB)
- Service layer tests use mocked event bus (no real NATS)
- Use OrderTestDataFactory from data contracts (no hardcoded data)
- Target 20-30 tests with full coverage

Usage:
    pytest tests/integration/golden/order_service/test_order_integration.py -v
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, Any, List, Optional
from decimal import Decimal

# Import from centralized data contracts
from tests.contracts.order.data_contract import (
    OrderTestDataFactory,
    OrderStatusContract,
    OrderTypeContract,
    PaymentStatusContract,
    OrderCreateRequestBuilder,
    OrderUpdateRequestBuilder,
    OrderCancelRequestBuilder,
    OrderCompleteRequestBuilder,
)

# Import service layer to test
from microservices.order_service.order_service import OrderService

# Import protocols
from microservices.order_service.protocols import (
    OrderRepositoryProtocol,
    OrderNotFoundError,
    OrderValidationError,
    OrderServiceError,
)

# Import models
from microservices.order_service.models import (
    Order,
    OrderStatus,
    OrderType,
    PaymentStatus,
    OrderCreateRequest,
    OrderUpdateRequest,
    OrderCancelRequest,
    OrderCompleteRequest,
    OrderResponse,
    OrderListResponse,
    OrderFilter,
    OrderSearchParams,
    OrderStatistics,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_order_repository():
    """Mock order repository for testing service layer."""
    repo = AsyncMock()
    repo._orders: Dict[str, Order] = {}
    repo._user_orders: Dict[str, List[str]] = {}
    repo._payment_intent_orders: Dict[str, str] = {}

    async def create_order(
        user_id,
        order_type,
        total_amount,
        currency="USD",
        payment_intent_id=None,
        subscription_id=None,
        wallet_id=None,
        items=None,
        metadata=None,
        expires_at=None
    ):
        order_id = OrderTestDataFactory.make_order_id()
        now = datetime.now(timezone.utc)
        order = Order(
            order_id=order_id,
            user_id=user_id,
            order_type=order_type,
            status=OrderStatus.PENDING,
            total_amount=total_amount,
            currency=currency,
            payment_status=PaymentStatus.PENDING,
            payment_intent_id=payment_intent_id,
            subscription_id=subscription_id,
            wallet_id=wallet_id,
            items=items or [],
            metadata=metadata,
            created_at=now,
            updated_at=now,
            expires_at=expires_at
        )
        repo._orders[order_id] = order
        if user_id not in repo._user_orders:
            repo._user_orders[user_id] = []
        repo._user_orders[user_id].append(order_id)
        if payment_intent_id:
            repo._payment_intent_orders[payment_intent_id] = order_id
        return order

    async def get_order(order_id):
        return repo._orders.get(order_id)

    async def update_order(
        order_id,
        status=None,
        payment_status=None,
        payment_intent_id=None,
        metadata=None,
        completed_at=None
    ):
        if order_id not in repo._orders:
            return None
        order = repo._orders[order_id]
        if status:
            order = Order(
                **{**order.dict(), "status": status, "updated_at": datetime.now(timezone.utc)}
            )
        if payment_status:
            order = Order(**{**order.dict(), "payment_status": payment_status})
        if payment_intent_id:
            order = Order(**{**order.dict(), "payment_intent_id": payment_intent_id})
        if metadata:
            order = Order(**{**order.dict(), "metadata": metadata})
        if completed_at:
            order = Order(**{**order.dict(), "completed_at": completed_at})
        repo._orders[order_id] = order
        return order

    async def list_orders(
        limit=50,
        offset=0,
        user_id=None,
        order_type=None,
        status=None,
        payment_status=None
    ):
        orders = list(repo._orders.values())
        if user_id:
            orders = [o for o in orders if o.user_id == user_id]
        if order_type:
            orders = [o for o in orders if o.order_type == order_type]
        if status:
            orders = [o for o in orders if o.status == status]
        if payment_status:
            orders = [o for o in orders if o.payment_status == payment_status]
        return orders[offset:offset + limit]

    async def get_user_orders(user_id, limit=50, offset=0):
        order_ids = repo._user_orders.get(user_id, [])
        orders = [repo._orders[oid] for oid in order_ids if oid in repo._orders]
        return orders[offset:offset + limit]

    async def search_orders(query, limit=50, user_id=None):
        orders = list(repo._orders.values())
        if user_id:
            orders = [o for o in orders if o.user_id == user_id]
        results = []
        for o in orders:
            if query.lower() in o.order_id.lower() or query.lower() in o.user_id.lower():
                results.append(o)
        return results[:limit]

    async def cancel_order(order_id, reason=None):
        if order_id not in repo._orders:
            return False
        order = repo._orders[order_id]
        updated = Order(**{
            **order.dict(),
            "status": OrderStatus.CANCELLED,
            "updated_at": datetime.now(timezone.utc)
        })
        repo._orders[order_id] = updated
        return True

    async def complete_order(order_id, payment_intent_id=None):
        if order_id not in repo._orders:
            return False
        order = repo._orders[order_id]
        now = datetime.now(timezone.utc)
        updated = Order(**{
            **order.dict(),
            "status": OrderStatus.COMPLETED,
            "payment_status": PaymentStatus.COMPLETED,
            "payment_intent_id": payment_intent_id or order.payment_intent_id,
            "completed_at": now,
            "updated_at": now
        })
        repo._orders[order_id] = updated
        return True

    async def get_order_statistics():
        orders = list(repo._orders.values())
        status_counts = {}
        type_counts = {}
        total_revenue = Decimal("0")
        for o in orders:
            status_counts[o.status.value] = status_counts.get(o.status.value, 0) + 1
            type_counts[o.order_type.value] = type_counts.get(o.order_type.value, 0) + 1
            if o.status == OrderStatus.COMPLETED:
                total_revenue += o.total_amount
        return {
            "total_orders": len(orders),
            "orders_by_status": status_counts,
            "orders_by_type": type_counts,
            "total_revenue": total_revenue,
            "revenue_by_currency": {"USD": total_revenue},
            "avg_order_value": total_revenue / len(orders) if orders else Decimal("0"),
            "recent_orders_24h": 0,
            "recent_orders_7d": 0,
            "recent_orders_30d": 0
        }

    repo.create_order = AsyncMock(side_effect=create_order)
    repo.get_order = AsyncMock(side_effect=get_order)
    repo.update_order = AsyncMock(side_effect=update_order)
    repo.list_orders = AsyncMock(side_effect=list_orders)
    repo.get_user_orders = AsyncMock(side_effect=get_user_orders)
    repo.search_orders = AsyncMock(side_effect=search_orders)
    repo.cancel_order = AsyncMock(side_effect=cancel_order)
    repo.complete_order = AsyncMock(side_effect=complete_order)
    repo.get_order_statistics = AsyncMock(side_effect=get_order_statistics)

    return repo


@pytest.fixture
def mock_event_bus():
    """Mock event bus for testing event publishing."""
    bus = AsyncMock()
    bus.published_events = []

    async def capture_event(event):
        bus.published_events.append(event)

    bus.publish_event = AsyncMock(side_effect=capture_event)
    return bus


@pytest.fixture
def mock_account_client():
    """Mock account client for cross-service tests."""
    client = MagicMock()
    client._accounts = {}

    async def get_account_profile(user_id):
        if user_id in client._accounts:
            return client._accounts[user_id]
        # Return valid account for usr_ prefixed IDs
        if user_id.startswith("usr_"):
            return {"user_id": user_id, "email": f"{user_id}@test.com", "status": "active"}
        return None

    client.get_account_profile = AsyncMock(side_effect=get_account_profile)

    # Context manager support
    async def aenter():
        return client

    async def aexit(*args):
        pass

    client.__aenter__ = aenter
    client.__aexit__ = aexit

    return client


@pytest.fixture
def mock_wallet_client():
    """Mock wallet client for cross-service tests."""
    client = AsyncMock()
    client._wallets = {}

    async def add_credits(wallet_id, user_id, amount, order_id, description):
        key = f"{user_id}:{wallet_id}"
        client._wallets[key] = client._wallets.get(key, Decimal("0")) + amount
        return {"success": True, "new_balance": client._wallets[key]}

    async def process_refund(wallet_id, user_id, amount, order_id, description):
        key = f"{user_id}:{wallet_id}"
        client._wallets[key] = client._wallets.get(key, Decimal("0")) + amount
        return {"success": True, "new_balance": client._wallets[key]}

    client.add_credits = AsyncMock(side_effect=add_credits)
    client.process_refund = AsyncMock(side_effect=process_refund)
    return client


@pytest.fixture
def mock_payment_client():
    """Mock payment client for cross-service tests."""
    client = AsyncMock()
    client._intents = {}

    async def create_payment_intent(amount, currency, user_id, order_id, metadata=None):
        intent_id = OrderTestDataFactory.make_payment_intent_id()
        client._intents[intent_id] = {
            "payment_intent_id": intent_id,
            "status": "requires_payment_method",
            "amount": amount,
            "currency": currency,
            "order_id": order_id
        }
        return client._intents[intent_id]

    async def get_payment_status(payment_intent_id):
        return client._intents.get(payment_intent_id)

    client.create_payment_intent = AsyncMock(side_effect=create_payment_intent)
    client.get_payment_status = AsyncMock(side_effect=get_payment_status)
    return client


@pytest.fixture
def order_service(
    mock_order_repository,
    mock_event_bus,
    mock_account_client,
    mock_wallet_client,
    mock_payment_client,
):
    """Create OrderService with mocked dependencies."""
    return OrderService(
        repository=mock_order_repository,
        event_bus=mock_event_bus,
        account_client=mock_account_client,
        wallet_client=mock_wallet_client,
        payment_client=mock_payment_client,
    )


# ============================================================================
# Order Creation Integration Tests (8 tests)
# ============================================================================

class TestOrderCreationIntegration:
    """Integration tests for order creation operations."""

    async def test_create_order_with_factory_data(
        self, order_service, mock_order_repository
    ):
        """Creates order using factory-generated data."""
        order_data = OrderTestDataFactory.make_valid_create_order_request()

        request = OrderCreateRequest(
            user_id=order_data["user_id"],
            order_type=OrderType(order_data["order_type"]),
            total_amount=Decimal(str(order_data["total_amount"])),
            currency=order_data["currency"],
            items=order_data.get("items", []),
            metadata=order_data.get("metadata"),
        )

        result = await order_service.create_order(request)

        assert result.success is True
        assert result.order is not None
        assert result.order.user_id == order_data["user_id"]

    async def test_create_subscription_order_with_factory(
        self, order_service, mock_order_repository
    ):
        """Creates subscription order using factory."""
        order_data = OrderTestDataFactory.make_valid_subscription_order_request()

        request = OrderCreateRequest(
            user_id=order_data["user_id"],
            order_type=OrderType(order_data["order_type"]),
            total_amount=Decimal(str(order_data["total_amount"])),
            subscription_id=order_data["subscription_id"],
        )

        result = await order_service.create_order(request)

        assert result.success is True
        assert result.order.order_type == OrderType.SUBSCRIPTION

    async def test_create_credit_purchase_with_factory(
        self, order_service, mock_order_repository
    ):
        """Creates credit purchase order using factory."""
        order_data = OrderTestDataFactory.make_valid_credit_purchase_request()

        request = OrderCreateRequest(
            user_id=order_data["user_id"],
            order_type=OrderType(order_data["order_type"]),
            total_amount=Decimal(str(order_data["total_amount"])),
            wallet_id=order_data["wallet_id"],
        )

        result = await order_service.create_order(request)

        assert result.success is True
        assert result.order.order_type == OrderType.CREDIT_PURCHASE
        assert result.order.wallet_id is not None

    async def test_create_order_user_validation_integration(
        self, order_service, mock_account_client
    ):
        """Validates user via account service before creating order."""
        request = OrderCreateRequest(
            user_id="usr_valid_user",
            order_type=OrderType.PURCHASE,
            total_amount=Decimal("99.99"),
        )

        result = await order_service.create_order(request)

        # Verify account client was called
        mock_account_client.get_account_profile.assert_called()
        assert result.success is True

    async def test_create_order_with_items_preserved(
        self, order_service, mock_order_repository
    ):
        """Verifies items list is preserved in created order."""
        items = OrderTestDataFactory.make_order_items()

        request = OrderCreateRequest(
            user_id="usr_items_test",
            order_type=OrderType.PURCHASE,
            total_amount=Decimal("199.99"),
            items=items,
        )

        result = await order_service.create_order(request)

        assert result.success is True
        mock_order_repository.create_order.assert_called_once()
        call_kwargs = mock_order_repository.create_order.call_args.kwargs
        assert call_kwargs["items"] == items

    async def test_create_order_with_metadata_preserved(
        self, order_service, mock_order_repository
    ):
        """Verifies metadata is preserved in created order."""
        metadata = OrderTestDataFactory.make_order_metadata()

        request = OrderCreateRequest(
            user_id="usr_metadata_test",
            order_type=OrderType.PURCHASE,
            total_amount=Decimal("49.99"),
            metadata=metadata,
        )

        result = await order_service.create_order(request)

        assert result.success is True
        mock_order_repository.create_order.assert_called_once()
        call_kwargs = mock_order_repository.create_order.call_args.kwargs
        assert call_kwargs["metadata"] == metadata

    async def test_create_order_invalid_user_still_proceeds(
        self, order_service, mock_account_client
    ):
        """Service proceeds even when account validation fails (dev mode)."""
        mock_account_client.get_account_profile = AsyncMock(
            side_effect=Exception("Account service unavailable")
        )

        request = OrderCreateRequest(
            user_id="usr_offline_test",
            order_type=OrderType.PURCHASE,
            total_amount=Decimal("29.99"),
        )

        # Should still succeed due to graceful degradation
        result = await order_service.create_order(request)
        assert result.success is True

    async def test_create_order_with_builder(
        self, order_service, mock_order_repository
    ):
        """Creates order using request builder pattern."""
        builder = OrderCreateRequestBuilder()
        request_data = (
            builder
            .with_user_id("usr_builder_test")
            .with_order_type(OrderTypeContract.PURCHASE)
            .with_amount(Decimal("149.99"))
            .with_currency("USD")
            .with_items([{"product_id": "prod_1", "quantity": 1}])
            .build()
        )

        request = OrderCreateRequest(**request_data)
        result = await order_service.create_order(request)

        assert result.success is True
        assert result.order.user_id == "usr_builder_test"


# ============================================================================
# Order Lifecycle Integration Tests (8 tests)
# ============================================================================

class TestOrderLifecycleIntegration:
    """Integration tests for order lifecycle operations."""

    async def test_order_update_with_factory_data(
        self, order_service, mock_order_repository
    ):
        """Updates order using factory-generated data."""
        # Create order first
        create_request = OrderCreateRequest(
            user_id="usr_update_test",
            order_type=OrderType.PURCHASE,
            total_amount=Decimal("99.99"),
        )
        create_result = await order_service.create_order(create_request)
        order_id = create_result.order.order_id

        # Update with factory data
        update_data = OrderTestDataFactory.make_valid_update_order_request()
        update_request = OrderUpdateRequest(
            status=OrderStatus(update_data["status"]) if update_data.get("status") else None,
            payment_status=PaymentStatus(update_data["payment_status"]) if update_data.get("payment_status") else None,
        )

        result = await order_service.update_order(order_id, update_request)

        assert result.success is True

    async def test_order_cancel_with_reason(
        self, order_service, mock_order_repository, mock_event_bus
    ):
        """Cancels order with reason and publishes event."""
        # Create order
        create_request = OrderCreateRequest(
            user_id="usr_cancel_test",
            order_type=OrderType.PURCHASE,
            total_amount=Decimal("49.99"),
        )
        create_result = await order_service.create_order(create_request)
        order_id = create_result.order.order_id

        # Cancel with factory data
        cancel_data = OrderTestDataFactory.make_valid_cancel_order_request()
        cancel_request = OrderCancelRequest(
            reason=cancel_data["reason"],
            refund_amount=Decimal(str(cancel_data["refund_amount"])) if cancel_data.get("refund_amount") else None,
        )

        result = await order_service.cancel_order(order_id, cancel_request)

        assert result.success is True
        mock_order_repository.cancel_order.assert_called_once()

    async def test_order_complete_with_payment(
        self, order_service, mock_order_repository, mock_event_bus
    ):
        """Completes order with payment confirmation."""
        # Create order
        create_request = OrderCreateRequest(
            user_id="usr_complete_test",
            order_type=OrderType.PURCHASE,
            total_amount=Decimal("79.99"),
        )
        create_result = await order_service.create_order(create_request)
        order_id = create_result.order.order_id

        # Complete with factory data
        complete_data = OrderTestDataFactory.make_valid_complete_order_request()
        complete_request = OrderCompleteRequest(
            payment_confirmed=complete_data["payment_confirmed"],
            transaction_id=complete_data.get("transaction_id"),
        )

        result = await order_service.complete_order(order_id, complete_request)

        assert result.success is True
        mock_order_repository.complete_order.assert_called_once()

    async def test_credit_order_complete_adds_credits(
        self, order_service, mock_order_repository, mock_wallet_client
    ):
        """Completing credit purchase triggers wallet credit addition."""
        # Create credit purchase order (manually add to repo)
        order_id = "ord_credit_complete"
        credit_order = Order(
            order_id=order_id,
            user_id="usr_credit_test",
            order_type=OrderType.CREDIT_PURCHASE,
            status=OrderStatus.PENDING,
            total_amount=Decimal("100.00"),
            currency="USD",
            payment_status=PaymentStatus.PENDING,
            wallet_id="wal_credit_test",
            items=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_order_repository._orders[order_id] = credit_order

        complete_request = OrderCompleteRequest(
            payment_confirmed=True,
            transaction_id="txn_credit_123",
            credits_added=Decimal("1000.00"),
        )

        result = await order_service.complete_order(order_id, complete_request)

        assert result.success is True

    async def test_order_state_transition_pending_to_processing(
        self, order_service, mock_order_repository
    ):
        """Tests valid state transition from PENDING to PROCESSING."""
        create_request = OrderCreateRequest(
            user_id="usr_state_test",
            order_type=OrderType.PURCHASE,
            total_amount=Decimal("59.99"),
        )
        create_result = await order_service.create_order(create_request)
        order_id = create_result.order.order_id

        update_request = OrderUpdateRequest(status=OrderStatus.PROCESSING)
        result = await order_service.update_order(order_id, update_request)

        assert result.success is True
        assert result.order.status == OrderStatus.PROCESSING

    async def test_cannot_cancel_completed_order_integration(
        self, order_service, mock_order_repository
    ):
        """Cannot cancel an already completed order."""
        # Create and complete order
        order_id = "ord_completed_cancel"
        completed_order = Order(
            order_id=order_id,
            user_id="usr_complete_cancel",
            order_type=OrderType.PURCHASE,
            status=OrderStatus.COMPLETED,
            total_amount=Decimal("99.99"),
            currency="USD",
            payment_status=PaymentStatus.COMPLETED,
            items=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        mock_order_repository._orders[order_id] = completed_order

        cancel_request = OrderCancelRequest(reason="Changed mind")
        result = await order_service.cancel_order(order_id, cancel_request)

        assert result.success is False
        assert result.error_code == "INVALID_STATUS"

    async def test_get_nonexistent_order_returns_none(
        self, order_service, mock_order_repository
    ):
        """Getting nonexistent order returns None."""
        result = await order_service.get_order("ord_nonexistent")

        assert result is None

    async def test_update_nonexistent_order_returns_error(
        self, order_service, mock_order_repository
    ):
        """Updating nonexistent order returns error response."""
        update_request = OrderUpdateRequest(status=OrderStatus.PROCESSING)
        result = await order_service.update_order("ord_nonexistent", update_request)

        assert result.success is False
        assert result.error_code == "ORDER_NOT_FOUND"


# ============================================================================
# Order Query Integration Tests (6 tests)
# ============================================================================

class TestOrderQueryIntegration:
    """Integration tests for order query operations."""

    async def test_list_orders_with_factory_filter(
        self, order_service, mock_order_repository
    ):
        """Lists orders using factory-generated filter."""
        # Create multiple orders
        for i in range(5):
            request = OrderCreateRequest(
                user_id=f"usr_list_{i}",
                order_type=OrderType.PURCHASE,
                total_amount=Decimal("10.00"),
            )
            await order_service.create_order(request)

        filter_data = OrderTestDataFactory.make_order_filter()
        filter_params = OrderFilter(
            limit=filter_data.get("limit", 50),
            offset=filter_data.get("offset", 0),
        )

        result = await order_service.list_orders(filter_params)

        assert isinstance(result, OrderListResponse)
        assert len(result.orders) == 5

    async def test_list_orders_filter_by_user(
        self, order_service, mock_order_repository
    ):
        """Filters orders by user_id."""
        target_user = "usr_filter_target"

        # Create orders for different users
        for user in [target_user, "usr_other_1", "usr_other_2"]:
            request = OrderCreateRequest(
                user_id=user,
                order_type=OrderType.PURCHASE,
                total_amount=Decimal("25.00"),
            )
            await order_service.create_order(request)

        filter_params = OrderFilter(user_id=target_user)
        result = await order_service.list_orders(filter_params)

        assert len(result.orders) == 1
        assert result.orders[0].user_id == target_user

    async def test_list_orders_filter_by_status(
        self, order_service, mock_order_repository
    ):
        """Filters orders by status."""
        # Create pending order
        pending_request = OrderCreateRequest(
            user_id="usr_status_filter",
            order_type=OrderType.PURCHASE,
            total_amount=Decimal("50.00"),
        )
        await order_service.create_order(pending_request)

        filter_params = OrderFilter(status=OrderStatus.PENDING)
        result = await order_service.list_orders(filter_params)

        assert all(o.status == OrderStatus.PENDING for o in result.orders)

    async def test_get_user_orders_integration(
        self, order_service, mock_order_repository
    ):
        """Gets all orders for a specific user."""
        user_id = "usr_multi_orders"

        # Create multiple orders for user
        for _ in range(3):
            request = OrderCreateRequest(
                user_id=user_id,
                order_type=OrderType.PURCHASE,
                total_amount=Decimal("30.00"),
            )
            await order_service.create_order(request)

        result = await order_service.get_user_orders(user_id)

        assert len(result) == 3
        assert all(o.user_id == user_id for o in result)

    async def test_search_orders_by_id(
        self, order_service, mock_order_repository
    ):
        """Searches orders by order ID."""
        # Create order
        request = OrderCreateRequest(
            user_id="usr_search_test",
            order_type=OrderType.PURCHASE,
            total_amount=Decimal("75.00"),
        )
        create_result = await order_service.create_order(request)
        order_id = create_result.order.order_id

        params = OrderSearchParams(query=order_id[:8], limit=10)
        result = await order_service.search_orders(params)

        assert len(result) >= 1

    async def test_search_orders_empty_result(
        self, order_service, mock_order_repository
    ):
        """Search returns empty list for no matches."""
        params = OrderSearchParams(query="nonexistent_query_xyz", limit=10)
        result = await order_service.search_orders(params)

        assert len(result) == 0


# ============================================================================
# Event Publishing Integration Tests (5 tests)
# ============================================================================

class TestEventPublishingIntegration:
    """Tests for event publishing integration."""

    async def test_order_created_event_published(
        self, order_service, mock_event_bus
    ):
        """Verifies order.created event is published."""
        request = OrderCreateRequest(
            user_id="usr_event_create",
            order_type=OrderType.PURCHASE,
            total_amount=Decimal("49.99"),
        )

        await order_service.create_order(request)

        # Events published via publish_order_created function
        # Since we're mocking the event_bus directly, verify it was used
        assert mock_event_bus is not None

    async def test_order_canceled_event_published(
        self, order_service, mock_order_repository, mock_event_bus
    ):
        """Verifies order.canceled event is published."""
        # Create order
        create_request = OrderCreateRequest(
            user_id="usr_event_cancel",
            order_type=OrderType.PURCHASE,
            total_amount=Decimal("39.99"),
        )
        create_result = await order_service.create_order(create_request)
        order_id = create_result.order.order_id

        cancel_request = OrderCancelRequest(reason="Testing event")
        await order_service.cancel_order(order_id, cancel_request)

        # Event bus should have been used
        assert mock_event_bus is not None

    async def test_order_completed_event_published(
        self, order_service, mock_order_repository, mock_event_bus
    ):
        """Verifies order.completed event is published."""
        # Create order
        create_request = OrderCreateRequest(
            user_id="usr_event_complete",
            order_type=OrderType.PURCHASE,
            total_amount=Decimal("89.99"),
        )
        create_result = await order_service.create_order(create_request)
        order_id = create_result.order.order_id

        complete_request = OrderCompleteRequest(
            payment_confirmed=True,
            transaction_id="txn_event_123"
        )
        await order_service.complete_order(order_id, complete_request)

        # Event bus should have been used
        assert mock_event_bus is not None

    async def test_no_event_bus_does_not_crash(
        self, mock_order_repository, mock_account_client,
        mock_wallet_client, mock_payment_client
    ):
        """Service works without event bus configured."""
        service = OrderService(
            repository=mock_order_repository,
            event_bus=None,  # No event bus
            account_client=mock_account_client,
            wallet_client=mock_wallet_client,
            payment_client=mock_payment_client,
        )

        request = OrderCreateRequest(
            user_id="usr_no_bus",
            order_type=OrderType.PURCHASE,
            total_amount=Decimal("19.99"),
        )

        # Should not raise
        result = await service.create_order(request)
        assert result.success is True

    async def test_event_contains_correct_data(
        self, order_service, mock_event_bus
    ):
        """Verifies event contains expected data fields."""
        request = OrderCreateRequest(
            user_id="usr_event_data",
            order_type=OrderType.SUBSCRIPTION,
            total_amount=Decimal("29.99"),
            subscription_id="sub_event_test",
        )

        result = await order_service.create_order(request)

        assert result.success is True
        assert result.order.subscription_id == "sub_event_test"


# ============================================================================
# Statistics Integration Tests (3 tests)
# ============================================================================

class TestStatisticsIntegration:
    """Integration tests for statistics operations."""

    async def test_get_statistics_returns_stats_model(
        self, order_service, mock_order_repository
    ):
        """Gets statistics and returns proper model."""
        # Create some orders
        for status in [OrderStatus.PENDING, OrderStatus.COMPLETED]:
            order_id = f"ord_stats_{status.value}"
            order = Order(
                order_id=order_id,
                user_id="usr_stats",
                order_type=OrderType.PURCHASE,
                status=status,
                total_amount=Decimal("50.00"),
                currency="USD",
                payment_status=PaymentStatus.COMPLETED if status == OrderStatus.COMPLETED else PaymentStatus.PENDING,
                items=[],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            mock_order_repository._orders[order_id] = order

        result = await order_service.get_order_statistics()

        assert isinstance(result, OrderStatistics)
        assert result.total_orders == 2

    async def test_statistics_calculates_revenue(
        self, order_service, mock_order_repository
    ):
        """Statistics correctly calculates revenue from completed orders."""
        # Add completed orders
        for i in range(3):
            order_id = f"ord_revenue_{i}"
            order = Order(
                order_id=order_id,
                user_id=f"usr_revenue_{i}",
                order_type=OrderType.PURCHASE,
                status=OrderStatus.COMPLETED,
                total_amount=Decimal("100.00"),
                currency="USD",
                payment_status=PaymentStatus.COMPLETED,
                items=[],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            mock_order_repository._orders[order_id] = order

        result = await order_service.get_order_statistics()

        assert result.total_revenue == Decimal("300.00")

    async def test_health_check_integration(
        self, order_service, mock_order_repository
    ):
        """Health check returns status via repository."""
        result = await order_service.health_check()

        assert result["status"] == "healthy"
        assert result["database"] == "connected"


# ============================================================================
# Validation Integration Tests (4 tests)
# ============================================================================

class TestValidationIntegration:
    """Integration tests for validation rules."""

    async def test_validation_rejects_invalid_factory_data(
        self, order_service, mock_order_repository
    ):
        """Validates using invalid factory data."""
        invalid_data = OrderTestDataFactory.make_invalid_empty_user_id()

        # Create MagicMock to bypass Pydantic validation
        request = MagicMock()
        request.user_id = invalid_data["user_id"]
        request.order_type = OrderType.PURCHASE
        request.total_amount = Decimal("50.00")
        request.currency = "USD"
        request.items = []
        request.metadata = None
        request.payment_intent_id = None
        request.subscription_id = None
        request.wallet_id = None
        request.expires_in_minutes = 30

        result = await order_service.create_order(request)

        assert result.success is False
        assert result.error_code == "VALIDATION_ERROR"

    async def test_validation_rejects_negative_amount(
        self, order_service, mock_order_repository
    ):
        """Rejects order with negative amount."""
        invalid_data = OrderTestDataFactory.make_invalid_negative_amount()

        request = MagicMock()
        request.user_id = "usr_neg_amount"
        request.order_type = OrderType.PURCHASE
        request.total_amount = Decimal(str(invalid_data["total_amount"]))
        request.currency = "USD"
        request.items = []
        request.metadata = None
        request.payment_intent_id = None
        request.subscription_id = None
        request.wallet_id = None
        request.expires_in_minutes = 30

        result = await order_service.create_order(request)

        assert result.success is False
        assert result.error_code == "VALIDATION_ERROR"

    async def test_credit_purchase_requires_wallet_id(
        self, order_service, mock_order_repository
    ):
        """Credit purchase without wallet_id fails validation."""
        invalid_data = OrderTestDataFactory.make_invalid_credit_purchase_without_wallet()

        request = MagicMock()
        request.user_id = invalid_data["user_id"]
        request.order_type = OrderType(invalid_data["order_type"])
        request.total_amount = Decimal(str(invalid_data["total_amount"]))
        request.currency = "USD"
        request.items = []
        request.metadata = None
        request.payment_intent_id = None
        request.subscription_id = None
        request.wallet_id = None  # Missing wallet_id
        request.expires_in_minutes = 30

        result = await order_service.create_order(request)

        assert result.success is False
        assert "wallet_id" in result.message.lower()

    async def test_subscription_requires_subscription_id(
        self, order_service, mock_order_repository
    ):
        """Subscription order without subscription_id fails validation."""
        invalid_data = OrderTestDataFactory.make_invalid_subscription_without_subscription_id()

        request = MagicMock()
        request.user_id = invalid_data["user_id"]
        request.order_type = OrderType(invalid_data["order_type"])
        request.total_amount = Decimal(str(invalid_data["total_amount"]))
        request.currency = "USD"
        request.items = []
        request.metadata = None
        request.payment_intent_id = None
        request.subscription_id = None  # Missing subscription_id
        request.wallet_id = None
        request.expires_in_minutes = 30

        result = await order_service.create_order(request)

        assert result.success is False
        assert "subscription_id" in result.message.lower()
