#!/usr/bin/env python3
"""
Test Billing Service Event Subscriptions

Tests that billing service correctly subscribes to and processes events from NATS
"""

import asyncio
import sys
import os
from datetime import datetime, timezone
from decimal import Decimal

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from microservices.billing_service.event_handlers import BillingEventHandlers
from microservices.billing_service.billing_service import BillingService
from microservices.billing_service.models import ProcessBillingResponse
from core.nats_client import Event, EventType, ServiceSource


class MockBillingService:
    """Mock billing service for testing"""

    def __init__(self):
        self.recorded_usage = []

    async def record_usage_and_bill(self, request):
        """Mock record usage and bill"""
        self.recorded_usage.append({
            "user_id": request.user_id,
            "product_id": request.product_id,
            "service_type": request.service_type,
            "usage_amount": request.usage_amount,
            "session_id": request.session_id,
            "usage_details": request.usage_details
        })
        return ProcessBillingResponse(
            success=True,
            message="Usage recorded successfully"
        )


async def test_session_tokens_used_event():
    """Test billing service handles session.tokens_used events"""
    print("\n" + "="*60)
    print("TEST 1: Session Tokens Used Event")
    print("="*60)

    # Create mock billing service
    mock_billing = MockBillingService()

    # Create event handlers
    handlers = BillingEventHandlers(mock_billing)

    # Create a session.tokens_used event
    event = Event(
        event_type=EventType.SESSION_TOKENS_USED,
        source=ServiceSource.SESSION_SERVICE,
        data={
            "session_id": "session_123",
            "user_id": "user_456",
            "message_id": "msg_789",
            "tokens_used": 1500,
            "cost_usd": 0.15,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

    # Handle the event
    await handlers.handle_session_tokens_used(event)

    # Verify usage was recorded
    assert len(mock_billing.recorded_usage) == 1, "Expected 1 usage record"
    usage = mock_billing.recorded_usage[0]

    assert usage["user_id"] == "user_456"
    assert usage["product_id"] == "ai_tokens"
    assert usage["usage_amount"] == Decimal("1500")
    assert usage["session_id"] == "session_123"
    assert usage["usage_details"]["tokens_used"] == 1500
    assert usage["usage_details"]["cost_usd"] == 0.15

    print(f"✅ session.tokens_used event processed successfully")
    print(f"   User ID: {usage['user_id']}")
    print(f"   Tokens: {usage['usage_amount']}")
    print(f"   Cost: ${usage['usage_details']['cost_usd']}")

    return True


async def test_order_completed_event():
    """Test billing service handles order.completed events"""
    print("\n" + "="*60)
    print("TEST 2: Order Completed Event")
    print("="*60)

    # Create mock billing service
    mock_billing = MockBillingService()

    # Create event handlers
    handlers = BillingEventHandlers(mock_billing)

    # Create an order.completed event
    event = Event(
        event_type=EventType.ORDER_COMPLETED,
        source=ServiceSource.ORDER_SERVICE,
        data={
            "order_id": "order_abc123",
            "user_id": "user_789",
            "order_type": "CREDIT_PURCHASE",
            "total_amount": 99.99,
            "currency": "USD",
            "transaction_id": "txn_xyz789",
            "payment_confirmed": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

    # Handle the event
    await handlers.handle_order_completed(event)

    # Verify revenue was recorded
    assert len(mock_billing.recorded_usage) == 1, "Expected 1 usage record"
    usage = mock_billing.recorded_usage[0]

    assert usage["user_id"] == "user_789"
    assert usage["product_id"] == "order_CREDIT_PURCHASE"
    assert usage["usage_amount"] == Decimal("99.99")
    assert usage["session_id"] == "order_abc123"
    assert usage["usage_details"]["order_id"] == "order_abc123"
    assert usage["usage_details"]["total_amount"] == 99.99
    assert usage["usage_details"]["payment_confirmed"] == True

    print(f"✅ order.completed event processed successfully")
    print(f"   User ID: {usage['user_id']}")
    print(f"   Order ID: {usage['usage_details']['order_id']}")
    print(f"   Amount: ${usage['usage_amount']}")

    return True


async def test_session_ended_event():
    """Test billing service handles session.ended events (logging only)"""
    print("\n" + "="*60)
    print("TEST 3: Session Ended Event")
    print("="*60)

    # Create mock billing service
    mock_billing = MockBillingService()

    # Create event handlers
    handlers = BillingEventHandlers(mock_billing)

    # Create a session.ended event
    event = Event(
        event_type=EventType.SESSION_ENDED,
        source=ServiceSource.SESSION_SERVICE,
        data={
            "session_id": "session_999",
            "user_id": "user_888",
            "total_messages": 25,
            "total_tokens": 5000,
            "total_cost": 0.50,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

    # Handle the event
    await handlers.handle_session_ended(event)

    # Verify no usage was recorded (this is just logging)
    assert len(mock_billing.recorded_usage) == 0, "session.ended should not record usage (already tracked via tokens_used)"

    print(f"✅ session.ended event processed successfully (logging only)")
    print(f"   Session ID: session_999")
    print(f"   Total tokens: 5000")
    print(f"   Total cost: $0.50")

    return True


async def test_idempotency():
    """Test billing service handles duplicate events (idempotency)"""
    print("\n" + "="*60)
    print("TEST 4: Idempotency - Duplicate Event Handling")
    print("="*60)

    # Create mock billing service
    mock_billing = MockBillingService()

    # Create event handlers
    handlers = BillingEventHandlers(mock_billing)

    # Create a session.tokens_used event
    event = Event(
        event_type=EventType.SESSION_TOKENS_USED,
        source=ServiceSource.SESSION_SERVICE,
        data={
            "session_id": "session_duplicate",
            "user_id": "user_duplicate",
            "message_id": "msg_duplicate",
            "tokens_used": 100,
            "cost_usd": 0.01,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

    # Handle the event first time
    await handlers.handle_session_tokens_used(event)

    # Verify usage was recorded
    assert len(mock_billing.recorded_usage) == 1, "Expected 1 usage record after first event"

    # Handle the SAME event again (duplicate)
    await handlers.handle_session_tokens_used(event)

    # Verify usage was NOT recorded again (idempotency)
    assert len(mock_billing.recorded_usage) == 1, "Expected still only 1 usage record after duplicate event (idempotency)"

    print(f"✅ Duplicate event handled correctly (idempotency)")
    print(f"   First event: Recorded")
    print(f"   Duplicate event: Skipped (idempotent)")
    print(f"   Total records: {len(mock_billing.recorded_usage)}")

    return True


async def test_zero_tokens_skipped():
    """Test billing service skips zero-token events"""
    print("\n" + "="*60)
    print("TEST 5: Zero Tokens Skipped")
    print("="*60)

    # Create mock billing service
    mock_billing = MockBillingService()

    # Create event handlers
    handlers = BillingEventHandlers(mock_billing)

    # Create a session.tokens_used event with zero tokens
    event = Event(
        event_type=EventType.SESSION_TOKENS_USED,
        source=ServiceSource.SESSION_SERVICE,
        data={
            "session_id": "session_zero",
            "user_id": "user_zero",
            "message_id": "msg_zero",
            "tokens_used": 0,  # Zero tokens
            "cost_usd": 0.0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

    # Handle the event
    await handlers.handle_session_tokens_used(event)

    # Verify usage was NOT recorded (zero tokens)
    assert len(mock_billing.recorded_usage) == 0, "Expected zero-token event to be skipped"

    print(f"✅ Zero-token event skipped correctly")
    print(f"   Tokens: 0")
    print(f"   Status: Skipped (no billing for zero tokens)")

    return True


async def test_event_handler_map():
    """Test event handler map returns correct handlers"""
    print("\n" + "="*60)
    print("TEST 6: Event Handler Map")
    print("="*60)

    # Create mock billing service
    mock_billing = MockBillingService()

    # Create event handlers
    handlers = BillingEventHandlers(mock_billing)

    # Get handler map
    handler_map = handlers.get_event_handler_map()

    # Verify all expected event types are mapped
    expected_events = [
        "session.tokens_used",
        "order.completed",
        "session.ended"
    ]

    for event_type in expected_events:
        assert event_type in handler_map, f"Expected {event_type} in handler map"
        assert callable(handler_map[event_type]), f"Handler for {event_type} should be callable"

    print(f"✅ Event handler map configured correctly")
    print(f"   Registered event types: {len(handler_map)}")
    for event_type in expected_events:
        print(f"   - {event_type}")

    return True


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("BILLING SERVICE EVENT SUBSCRIPTION TEST SUITE")
    print("="*80)
    print(f"Timestamp: {datetime.now().isoformat()}")

    results = {}

    # Run tests
    try:
        results["session_tokens_used_event"] = await test_session_tokens_used_event()
    except Exception as e:
        print(f"❌ TEST 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["session_tokens_used_event"] = False

    try:
        results["order_completed_event"] = await test_order_completed_event()
    except Exception as e:
        print(f"❌ TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["order_completed_event"] = False

    try:
        results["session_ended_event"] = await test_session_ended_event()
    except Exception as e:
        print(f"❌ TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["session_ended_event"] = False

    try:
        results["idempotency"] = await test_idempotency()
    except Exception as e:
        print(f"❌ TEST 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["idempotency"] = False

    try:
        results["zero_tokens_skipped"] = await test_zero_tokens_skipped()
    except Exception as e:
        print(f"❌ TEST 5 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["zero_tokens_skipped"] = False

    try:
        results["event_handler_map"] = await test_event_handler_map()
    except Exception as e:
        print(f"❌ TEST 6 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["event_handler_map"] = False

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
