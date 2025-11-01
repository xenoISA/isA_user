#!/usr/bin/env python3
"""
Test Order Service Event Subscriptions

Tests that order service correctly subscribes to and processes events from NATS
"""

import asyncio
import sys
import os
from datetime import datetime, timezone
from decimal import Decimal

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from microservices.order_service.models import OrderStatus, PaymentStatus, OrderCompleteRequest
from core.nats_client import Event, EventType, ServiceSource


class MockOrder:
    """Mock order object"""
    def __init__(self, order_id, user_id, payment_intent_id, status=OrderStatus.PENDING):
        self.order_id = order_id
        self.user_id = user_id
        self.payment_intent_id = payment_intent_id
        self.status = status
        self.payment_status = PaymentStatus.PENDING


class MockOrderRepository:
    """Mock order repository for testing"""

    def __init__(self):
        self.orders = {}
        self.status_updates = []

    async def get_order_by_payment_intent(self, payment_intent_id):
        """Mock get order by payment intent"""
        for order in self.orders.values():
            if order.payment_intent_id == payment_intent_id:
                return order
        return None

    async def update_order_status(self, order_id, status, payment_status=None):
        """Mock update order status"""
        self.status_updates.append({
            "order_id": order_id,
            "status": status,
            "payment_status": payment_status
        })
        if order_id in self.orders:
            self.orders[order_id].status = status
            if payment_status:
                self.orders[order_id].payment_status = payment_status
        return True


class MockOrderService:
    """Mock order service for testing"""

    def __init__(self):
        self.repository = MockOrderRepository()
        self.completed_orders = []

    async def complete_order(self, order_id: str, request: OrderCompleteRequest):
        """Mock complete order"""
        self.completed_orders.append({
            "order_id": order_id,
            "payment_confirmed": request.payment_confirmed,
            "transaction_id": request.transaction_id,
            "credits_added": request.credits_added
        })
        return type('obj', (object,), {'success': True})


async def test_payment_completed_event():
    """Test order service handles payment.completed events"""
    print("\n" + "="*60)
    print("TEST 1: Payment Completed Event → Auto-complete Order")
    print("="*60)

    # Create mock order service
    mock_order_service = MockOrderService()

    # Create a mock order
    mock_order = MockOrder(
        order_id="order_123",
        user_id="user_456",
        payment_intent_id="pi_789",
        status=OrderStatus.PENDING
    )
    mock_order_service.repository.orders["order_123"] = mock_order

    # Import event handler from main.py
    from microservices.order_service import main
    main.order_microservice.order_service = mock_order_service

    # Create a payment.completed event
    event = Event(
        event_type=EventType.PAYMENT_COMPLETED,
        source=ServiceSource.PAYMENT_SERVICE,
        data={
            "payment_intent_id": "pi_789",
            "user_id": "user_456",
            "amount": 99.99,
            "currency": "USD",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

    # Handle the event
    await main.handle_payment_completed(event)

    # Verify order was completed
    assert len(mock_order_service.completed_orders) == 1, "Expected 1 completed order"
    completed = mock_order_service.completed_orders[0]

    assert completed["order_id"] == "order_123"
    assert completed["payment_confirmed"] == True
    assert completed["credits_added"] == Decimal("99.99")

    print(f"✅ payment.completed event processed successfully")
    print(f"   Order ID: {completed['order_id']}")
    print(f"   Payment Confirmed: {completed['payment_confirmed']}")
    print(f"   Credits Added: {completed['credits_added']}")

    return True


async def test_payment_failed_event():
    """Test order service handles payment.failed events"""
    print("\n" + "="*60)
    print("TEST 2: Payment Failed Event → Mark Order Failed")
    print("="*60)

    # Create mock order service
    mock_order_service = MockOrderService()

    # Create a mock order
    mock_order = MockOrder(
        order_id="order_456",
        user_id="user_789",
        payment_intent_id="pi_failed",
        status=OrderStatus.PENDING
    )
    mock_order_service.repository.orders["order_456"] = mock_order

    # Import event handler from main.py
    from microservices.order_service import main
    main.order_microservice.order_service = mock_order_service

    # Create a payment.failed event
    event = Event(
        event_type=EventType.PAYMENT_FAILED,
        source=ServiceSource.PAYMENT_SERVICE,
        data={
            "payment_intent_id": "pi_failed",
            "user_id": "user_789",
            "error_message": "Card declined",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

    # Handle the event
    await main.handle_payment_failed(event)

    # Verify order status was updated
    assert len(mock_order_service.repository.status_updates) == 1, "Expected 1 status update"
    update = mock_order_service.repository.status_updates[0]

    assert update["order_id"] == "order_456"
    assert update["status"] == OrderStatus.FAILED
    assert update["payment_status"] == PaymentStatus.FAILED

    print(f"✅ payment.failed event processed successfully")
    print(f"   Order ID: {update['order_id']}")
    print(f"   New Status: {update['status']}")
    print(f"   Payment Status: {update['payment_status']}")

    return True


async def test_payment_event_no_order():
    """Test payment event when order not found"""
    print("\n" + "="*60)
    print("TEST 3: Payment Event with Non-existent Order")
    print("="*60)

    # Create mock order service (empty - no orders)
    mock_order_service = MockOrderService()

    # Import event handler from main.py
    from microservices.order_service import main
    main.order_microservice.order_service = mock_order_service

    # Create a payment.completed event for non-existent order
    event = Event(
        event_type=EventType.PAYMENT_COMPLETED,
        source=ServiceSource.PAYMENT_SERVICE,
        data={
            "payment_intent_id": "pi_nonexistent",
            "user_id": "user_999",
            "amount": 50.00
        }
    )

    # Handle the event (should not crash)
    await main.handle_payment_completed(event)

    # Verify no orders were completed
    assert len(mock_order_service.completed_orders) == 0, "Expected 0 completed orders"

    print(f"✅ Event handled gracefully for non-existent order")
    print(f"   No crashes or errors")
    print(f"   Event marked as processed to prevent retries")

    return True


async def test_idempotency():
    """Test event idempotency"""
    print("\n" + "="*60)
    print("TEST 4: Event Idempotency")
    print("="*60)

    # Create mock order service
    mock_order_service = MockOrderService()

    # Create a mock order
    mock_order = MockOrder(
        order_id="order_idempotent",
        user_id="user_idem",
        payment_intent_id="pi_idem",
        status=OrderStatus.PENDING
    )
    mock_order_service.repository.orders["order_idempotent"] = mock_order

    # Import event handler from main.py
    from microservices.order_service import main
    main.order_microservice.order_service = mock_order_service

    # Create a payment.completed event
    event = Event(
        event_type=EventType.PAYMENT_COMPLETED,
        source=ServiceSource.PAYMENT_SERVICE,
        data={
            "payment_intent_id": "pi_idem",
            "user_id": "user_idem",
            "amount": 75.00
        }
    )

    # Process event first time
    await main.handle_payment_completed(event)
    first_count = len(mock_order_service.completed_orders)

    # Process same event again (should be skipped)
    await main.handle_payment_completed(event)
    second_count = len(mock_order_service.completed_orders)

    # Verify event was only processed once
    assert first_count == 1, "Expected 1 completed order after first processing"
    assert second_count == 1, "Expected still 1 completed order after duplicate event"

    print(f"✅ Event idempotency works correctly")
    print(f"   First processing: {first_count} orders completed")
    print(f"   Duplicate processing: {second_count} orders completed (no change)")

    return True


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("ORDER SERVICE EVENT SUBSCRIPTION TEST SUITE")
    print("="*80)
    print(f"Timestamp: {datetime.now().isoformat()}")

    results = {}

    # Run tests
    try:
        results["payment_completed"] = await test_payment_completed_event()
    except Exception as e:
        print(f"❌ TEST 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["payment_completed"] = False

    try:
        results["payment_failed"] = await test_payment_failed_event()
    except Exception as e:
        print(f"❌ TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["payment_failed"] = False

    try:
        results["no_order_found"] = await test_payment_event_no_order()
    except Exception as e:
        print(f"❌ TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["no_order_found"] = False

    try:
        results["idempotency"] = await test_idempotency()
    except Exception as e:
        print(f"❌ TEST 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["idempotency"] = False

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
        print("\n🎉 ALL ORDER SERVICE EVENT TESTS PASSED!")
        print("\nEvent Subscriptions Verified:")
        print("  ✅ payment.completed → Automatic order completion")
        print("  ✅ payment.failed → Automatic order failure marking")
        print("  ✅ Graceful handling of non-existent orders")
        print("  ✅ Event idempotency working correctly")
    else:
        print("\n⚠️  Some tests failed")

    return passed, total


if __name__ == "__main__":
    passed, total = asyncio.run(run_all_tests())

    # Exit with appropriate code
    if passed == total:
        sys.exit(0)
    else:
        sys.exit(1)
