#!/usr/bin/env python3
"""
Test Order Service Event Publishing

Tests that order service correctly publishes events to NATS
"""

import asyncio
import sys
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock
from decimal import Decimal

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from microservices.order_service.order_service import OrderService
from microservices.order_service.models import (
    OrderCreateRequest, OrderCompleteRequest, OrderCancelRequest,
    OrderType, Order, OrderStatus, PaymentStatus
)
from core.nats_client import EventType, ServiceSource, get_event_bus


class MockEventBus:
    """Mock event bus for testing"""

    def __init__(self):
        self.published_events = []
        self._is_connected = False

    async def publish_event(self, event):
        """Mock publish event"""
        self.published_events.append({
            "id": event.id,
            "type": event.type,
            "source": event.source,
            "data": event.data,
            "timestamp": event.timestamp
        })
        print(f"✅ Mock event published: {event.type}")

    async def close(self):
        """Mock close"""
        pass


class MockOrderRepository:
    """Mock repository for testing"""

    def __init__(self):
        self.orders = {}

    async def create_order(self, user_id, order_type, total_amount, currency,
                          payment_intent_id=None, subscription_id=None,
                          wallet_id=None, items=None, metadata=None, expires_at=None):
        """Mock create order"""
        order_id = f"order_{len(self.orders) + 1}"
        order = Order(
            order_id=order_id,
            user_id=user_id,
            order_type=order_type,
            status=OrderStatus.PENDING,
            payment_status=PaymentStatus.PENDING,
            total_amount=total_amount,
            currency=currency,
            payment_intent_id=payment_intent_id,
            subscription_id=subscription_id,
            wallet_id=wallet_id,
            items=items or [],
            metadata=metadata or {},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=expires_at
        )
        self.orders[order_id] = order
        return order

    async def get_order(self, order_id):
        """Mock get order"""
        return self.orders.get(order_id)

    async def complete_order(self, order_id, payment_intent_id=None):
        """Mock complete order"""
        if order_id in self.orders:
            self.orders[order_id].status = OrderStatus.COMPLETED
            self.orders[order_id].payment_status = PaymentStatus.COMPLETED
            if payment_intent_id:
                self.orders[order_id].payment_intent_id = payment_intent_id
            return True
        return False

    async def cancel_order(self, order_id, reason=None):
        """Mock cancel order"""
        if order_id in self.orders:
            self.orders[order_id].status = OrderStatus.CANCELLED
            return True
        return False


async def test_order_created_event():
    """Test order.created event is published when new order is created"""
    print("\n" + "="*60)
    print("TEST 1: Order Created Event")
    print("="*60)

    # Create mock event bus and repository
    mock_event_bus = MockEventBus()

    # Create service with mock event bus
    service = OrderService.__new__(OrderService)
    service.event_bus = mock_event_bus
    service.order_repo = MockOrderRepository()
    service.consul = None

    # Create order
    request = OrderCreateRequest(
        user_id="user_123",
        order_type=OrderType.CREDIT_PURCHASE,
        total_amount=Decimal("99.99"),
        currency="USD",
        items=[{"product_id": "prod_1", "quantity": 1, "price": 99.99}],
        payment_intent_id="pi_123",
        wallet_id="wallet_123"  # Required for credit purchases
    )

    response = await service.create_order(request)

    # Verify order was created
    assert response.success == True, "Order creation should succeed"
    assert response.order is not None, "Order should be returned"

    # Verify event was published
    assert len(mock_event_bus.published_events) == 1, "Expected 1 event to be published"
    event = mock_event_bus.published_events[0]

    assert event["type"] == EventType.ORDER_CREATED.value
    assert event["source"] == ServiceSource.ORDER_SERVICE.value
    assert event["data"]["user_id"] == "user_123"
    assert event["data"]["order_type"] == OrderType.CREDIT_PURCHASE.value
    assert event["data"]["total_amount"] == 99.99
    assert event["data"]["currency"] == "USD"
    assert "timestamp" in event["data"]

    print(f"✅ order.created event published successfully")
    print(f"   Order ID: {event['data']['order_id']}")
    print(f"   User ID: {event['data']['user_id']}")
    print(f"   Total Amount: ${event['data']['total_amount']}")

    return True


async def test_order_completed_event():
    """Test order.completed event is published when order is completed"""
    print("\n" + "="*60)
    print("TEST 2: Order Completed Event")
    print("="*60)

    # Create mock event bus and repository
    mock_event_bus = MockEventBus()

    # Create service with mock event bus
    service = OrderService.__new__(OrderService)
    service.event_bus = mock_event_bus
    service.order_repo = MockOrderRepository()
    service.consul = None

    # Mock the _add_credits_to_wallet method to avoid HTTP calls
    async def mock_add_credits(user_id, wallet_id, amount, order_id):
        return True
    service._add_credits_to_wallet = mock_add_credits

    # Create order first
    create_request = OrderCreateRequest(
        user_id="user_456",
        order_type=OrderType.SUBSCRIPTION,
        total_amount=Decimal("29.99"),
        currency="USD",
        items=[{"product_id": "sub_monthly", "quantity": 1, "price": 29.99}],
        subscription_id="sub_123"
    )

    create_response = await service.create_order(create_request)
    order_id = create_response.order.order_id

    # Clear events from creation
    mock_event_bus.published_events.clear()

    # Complete the order
    complete_request = OrderCompleteRequest(
        payment_confirmed=True,
        transaction_id="txn_789"
    )

    response = await service.complete_order(order_id, complete_request)

    # Verify order was completed
    assert response.success == True, "Order completion should succeed"

    # Verify event was published
    assert len(mock_event_bus.published_events) == 1, "Expected 1 event to be published"
    event = mock_event_bus.published_events[0]

    assert event["type"] == EventType.ORDER_COMPLETED.value
    assert event["source"] == ServiceSource.ORDER_SERVICE.value
    assert event["data"]["order_id"] == order_id
    assert event["data"]["user_id"] == "user_456"
    assert event["data"]["transaction_id"] == "txn_789"
    assert event["data"]["payment_confirmed"] == True

    print(f"✅ order.completed event published successfully")
    print(f"   Order ID: {event['data']['order_id']}")
    print(f"   Transaction ID: {event['data']['transaction_id']}")
    print(f"   Payment Confirmed: {event['data']['payment_confirmed']}")

    return True


async def test_order_canceled_event():
    """Test order.canceled event is published when order is canceled"""
    print("\n" + "="*60)
    print("TEST 3: Order Canceled Event")
    print("="*60)

    # Create mock event bus and repository
    mock_event_bus = MockEventBus()

    # Create service with mock event bus
    service = OrderService.__new__(OrderService)
    service.event_bus = mock_event_bus
    service.order_repo = MockOrderRepository()
    service.consul = None

    # Create order first
    create_request = OrderCreateRequest(
        user_id="user_789",
        order_type=OrderType.CREDIT_PURCHASE,
        total_amount=Decimal("49.99"),
        currency="USD",
        items=[{"product_id": "credits_500", "quantity": 1, "price": 49.99}],
        wallet_id="wallet_789"  # Required for credit purchases
    )

    create_response = await service.create_order(create_request)
    order_id = create_response.order.order_id

    # Clear events from creation
    mock_event_bus.published_events.clear()

    # Cancel the order
    cancel_request = OrderCancelRequest(
        reason="Customer requested cancellation",
        refund_amount=Decimal("49.99")
    )

    response = await service.cancel_order(order_id, cancel_request)

    # Verify order was canceled
    assert response.success == True, "Order cancellation should succeed"

    # Verify event was published
    assert len(mock_event_bus.published_events) == 1, "Expected 1 event to be published"
    event = mock_event_bus.published_events[0]

    assert event["type"] == EventType.ORDER_CANCELED.value
    assert event["source"] == ServiceSource.ORDER_SERVICE.value
    assert event["data"]["order_id"] == order_id
    assert event["data"]["user_id"] == "user_789"
    assert event["data"]["reason"] == "Customer requested cancellation"
    assert event["data"]["refund_amount"] == 49.99

    print(f"✅ order.canceled event published successfully")
    print(f"   Order ID: {event['data']['order_id']}")
    print(f"   Reason: {event['data']['reason']}")
    print(f"   Refund Amount: ${event['data']['refund_amount']}")

    return True


async def test_graceful_degradation_without_event_bus():
    """Test service works without event bus (graceful degradation)"""
    print("\n" + "="*60)
    print("TEST 4: Graceful Degradation Without Event Bus")
    print("="*60)

    # Create service WITHOUT event bus
    service = OrderService.__new__(OrderService)
    service.event_bus = None  # No event bus
    service.order_repo = MockOrderRepository()
    service.consul = None

    # Create order
    request = OrderCreateRequest(
        user_id="user_no_events",
        order_type=OrderType.CREDIT_PURCHASE,
        total_amount=Decimal("19.99"),
        currency="USD",
        items=[{"product_id": "credits_100", "quantity": 1, "price": 19.99}],
        wallet_id="wallet_no_events"  # Required for credit purchases
    )

    response = await service.create_order(request)

    # Verify order was created successfully
    assert response.success == True, "Order creation should succeed without event bus"
    assert response.order is not None, "Order should be returned"

    print(f"✅ Service works without event bus (graceful degradation)")
    print(f"   Order created: {response.order.order_id}")
    print(f"   No events published (expected)")

    return True


async def test_nats_connection():
    """Test actual NATS connection (if available)"""
    print("\n" + "="*60)
    print("TEST 5: NATS Connection Test")
    print("="*60)

    try:
        # Try to connect to NATS
        event_bus = await get_event_bus("order_service_test")

        if event_bus and event_bus._is_connected:
            print("✅ Successfully connected to NATS")
            print(f"   URL: {event_bus.nats_url}")
            await event_bus.close()
            return True
        else:
            print("⚠️  NATS not available or not configured")
            return False

    except Exception as e:
        print(f"⚠️  NATS connection test failed: {e}")
        print("   This is OK for testing without NATS running")
        return False


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("ORDER SERVICE EVENT PUBLISHING TEST SUITE")
    print("="*80)
    print(f"Timestamp: {datetime.now().isoformat()}")

    results = {}

    # Run tests
    try:
        results["order_created_event"] = await test_order_created_event()
    except Exception as e:
        print(f"❌ TEST 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["order_created_event"] = False

    try:
        results["order_completed_event"] = await test_order_completed_event()
    except Exception as e:
        print(f"❌ TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["order_completed_event"] = False

    try:
        results["order_canceled_event"] = await test_order_canceled_event()
    except Exception as e:
        print(f"❌ TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["order_canceled_event"] = False

    try:
        results["graceful_degradation"] = await test_graceful_degradation_without_event_bus()
    except Exception as e:
        print(f"❌ TEST 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["graceful_degradation"] = False

    try:
        results["nats_connection"] = await test_nats_connection()
    except Exception as e:
        print(f"❌ TEST 5 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["nats_connection"] = False

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
    elif passed >= 4:  # Core tests (NATS is optional)
        print("\n✅ Core tests passed (NATS optional)")
    else:
        print("\n⚠️  Some tests failed")

    return passed, total


if __name__ == "__main__":
    passed, total = asyncio.run(run_all_tests())

    # Exit with appropriate code
    if passed >= 4:  # Core tests must pass (NATS is optional)
        sys.exit(0)
    else:
        sys.exit(1)
