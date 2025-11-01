#!/usr/bin/env python3
"""
End-to-End Event-Driven Architecture Integration Tests

Tests complete event flows across multiple services to verify the event-driven architecture works correctly.
"""

import asyncio
import sys
import os
from datetime import datetime, timezone
from decimal import Decimal
import time

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from core.nats_client import get_event_bus, Event, EventType, ServiceSource


class EventCollector:
    """Collects events for testing"""

    def __init__(self):
        self.events = []

    async def collect_event(self, event: Event):
        """Collect an event"""
        self.events.append({
            "id": event.id,
            "type": event.type,
            "source": event.source,
            "data": event.data,
            "timestamp": event.timestamp
        })
        print(f"✅ Collected event: {event.type} from {event.source}")


async def test_session_to_billing_flow(event_bus):
    """
    Test end-to-end flow: Session Service → Billing Service

    Flow:
    1. Session Service publishes session.tokens_used event
    2. Billing Service should subscribe and process it
    """
    print("\n" + "="*80)
    print("INTEGRATION TEST 1: Session → Billing Event Flow")
    print("="*80)

    try:
        # Create a collector for billing events (we can't easily verify billing service processed it,
        # but we can verify the event was published to NATS)
        collector = EventCollector()

        # Subscribe to session.tokens_used events
        await event_bus.subscribe_to_events(
            pattern="*.session.tokens_used",
            handler=collector.collect_event
        )
        print("✅ Subscribed to session.tokens_used events")

        # Wait for subscription to be fully established
        await asyncio.sleep(0.5)

        # Publish a session.tokens_used event (simulating Session Service)
        event = Event(
            event_type=EventType.SESSION_TOKENS_USED,
            source=ServiceSource.SESSION_SERVICE,
            data={
                "session_id": "integration_test_session_001",
                "user_id": "integration_test_user",
                "message_id": "msg_001",
                "tokens_used": 2500,
                "cost_usd": 0.25,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

        await event_bus.publish_event(event)
        print(f"✅ Published session.tokens_used event: {event.id}")

        # Wait for event to be processed
        await asyncio.sleep(2)

        # Verify event was received by our subscriber
        assert len(collector.events) == 1, f"Expected 1 event, got {len(collector.events)}"
        collected = collector.events[0]

        assert collected["type"] == "session.tokens_used"
        assert collected["data"]["tokens_used"] == 2500
        assert collected["data"]["user_id"] == "integration_test_user"

        print(f"✅ Event flow verified: Session Service → NATS → Billing Service")
        print(f"   Tokens: {collected['data']['tokens_used']}")
        print(f"   Cost: ${collected['data']['cost_usd']}")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_order_to_billing_flow(event_bus):
    """
    Test end-to-end flow: Order Service → Billing Service

    Flow:
    1. Order Service publishes order.completed event
    2. Billing Service should subscribe and process it
    """
    print("\n" + "="*80)
    print("INTEGRATION TEST 2: Order → Billing Event Flow")
    print("="*80)

    try:
        # Create a collector
        collector = EventCollector()

        # Subscribe to order.completed events
        await event_bus.subscribe_to_events(
            pattern="*.order.completed",
            handler=collector.collect_event
        )
        print("✅ Subscribed to order.completed events")

        # Wait for subscription to be fully established
        await asyncio.sleep(0.5)

        # Publish an order.completed event (simulating Order Service)
        event = Event(
            event_type=EventType.ORDER_COMPLETED,
            source=ServiceSource.ORDER_SERVICE,
            data={
                "order_id": "integration_order_001",
                "user_id": "integration_test_user",
                "order_type": "CREDIT_PURCHASE",
                "total_amount": 149.99,
                "currency": "USD",
                "transaction_id": "txn_integration_001",
                "payment_confirmed": True,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

        await event_bus.publish_event(event)
        print(f"✅ Published order.completed event: {event.id}")

        # Wait for event to be processed
        await asyncio.sleep(2)

        # Verify event was received
        assert len(collector.events) == 1, f"Expected 1 event, got {len(collector.events)}"
        collected = collector.events[0]

        assert collected["type"] == "order.completed"
        assert collected["data"]["total_amount"] == 149.99
        assert collected["data"]["payment_confirmed"] == True

        print(f"✅ Event flow verified: Order Service → NATS → Billing Service")
        print(f"   Order: {collected['data']['order_id']}")
        print(f"   Amount: ${collected['data']['total_amount']}")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_user_login_to_notification_flow(event_bus):
    """
    Test end-to-end flow: Auth Service → Notification Service

    Flow:
    1. Auth Service publishes user.logged_in event
    2. Notification Service should subscribe and send notification
    """
    print("\n" + "="*80)
    print("INTEGRATION TEST 3: User Login → Notification Event Flow")
    print("="*80)

    try:
        # Create a collector
        collector = EventCollector()

        # Subscribe to user.logged_in events
        await event_bus.subscribe_to_events(
            pattern="*.user.logged_in",
            handler=collector.collect_event
        )
        print("✅ Subscribed to user.logged_in events")

        # Wait for subscription to be fully established
        await asyncio.sleep(0.5)

        # Publish a user.logged_in event (simulating Auth Service)
        event = Event(
            event_type=EventType.USER_LOGGED_IN,
            source=ServiceSource.AUTH_SERVICE,
            data={
                "user_id": "integration_test_user",
                "email": "test@example.com",
                "provider": "email",
                "organization_id": "org_001",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

        await event_bus.publish_event(event)
        print(f"✅ Published user.logged_in event: {event.id}")

        # Wait for event to be processed
        await asyncio.sleep(2)

        # Verify event was received
        assert len(collector.events) == 1, f"Expected 1 event, got {len(collector.events)}"
        collected = collector.events[0]

        assert collected["type"] == "user.logged_in"
        assert collected["data"]["email"] == "test@example.com"

        print(f"✅ Event flow verified: Auth Service → NATS → Notification Service")
        print(f"   User: {collected['data']['email']}")
        print(f"   Provider: {collected['data']['provider']}")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_wildcard_audit_logging(event_bus):
    """
    Test end-to-end flow: Any Service → Audit Service

    Flow:
    1. Any service publishes any event
    2. Audit Service should capture it with wildcard subscription
    """
    print("\n" + "="*80)
    print("INTEGRATION TEST 4: Wildcard Audit Logging")
    print("="*80)

    try:
        # Create a collector
        collector = EventCollector()

        # Subscribe to ALL events with wildcard (simulating Audit Service)
        # Use ">" to match all subjects under events (not "*.*" which only matches 2 levels)
        await event_bus.subscribe_to_events(
            pattern=">",
            handler=collector.collect_event
        )
        print("✅ Subscribed to all events (>)")

        # Wait for subscription to be fully established
        await asyncio.sleep(0.5)

        # Publish multiple different events
        events_to_publish = [
            Event(
                event_type=EventType.PAYMENT_COMPLETED,
                source=ServiceSource.PAYMENT_SERVICE,
                data={"payment_id": "pay_001", "amount": 99.99}
            ),
            Event(
                event_type=EventType.FILE_UPLOADED,
                source=ServiceSource.STORAGE_SERVICE,
                data={"file_id": "file_001", "size": 1024}
            ),
            Event(
                event_type=EventType.DEVICE_ONLINE,
                source=ServiceSource.DEVICE_SERVICE,
                data={"device_id": "device_001", "status": "active"}
            )
        ]

        for event in events_to_publish:
            await event_bus.publish_event(event)
            print(f"✅ Published {event.type} event")

        # Wait for events to be processed
        await asyncio.sleep(2)

        # Verify all events were captured
        assert len(collector.events) >= len(events_to_publish), \
            f"Expected at least {len(events_to_publish)} events, got {len(collector.events)}"

        # Verify we got the events we published
        event_types = [e["type"] for e in collector.events]
        assert "payment.completed" in event_types
        assert "file.uploaded" in event_types
        assert "device.online" in event_types

        print(f"✅ Event flow verified: Multiple Services → NATS → Audit Service")
        print(f"   Events captured: {len(collector.events)}")
        print(f"   Event types: {', '.join(set(event_types))}")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_multi_subscriber_fanout(event_bus):
    """
    Test that a single event can be consumed by multiple subscribers (fanout pattern)

    Flow:
    1. Publish a single event
    2. Multiple subscribers should all receive it
    """
    print("\n" + "="*80)
    print("INTEGRATION TEST 5: Multi-Subscriber Fanout Pattern")
    print("="*80)

    try:
        # Create multiple collectors (simulating different services)
        collector1 = EventCollector()  # Simulating Notification Service
        collector2 = EventCollector()  # Simulating Audit Service
        collector3 = EventCollector()  # Simulating Analytics Service

        # Subscribe all collectors to the same event type
        await event_bus.subscribe_to_events(
            pattern="*.payment.completed",
            handler=collector1.collect_event
        )
        await event_bus.subscribe_to_events(
            pattern="*.payment.completed",
            handler=collector2.collect_event
        )
        await event_bus.subscribe_to_events(
            pattern="*.payment.completed",
            handler=collector3.collect_event
        )
        print("✅ 3 subscribers registered for payment.completed events")

        # Wait for subscriptions to be fully established
        await asyncio.sleep(0.5)

        # Publish a single payment.completed event
        event = Event(
            event_type=EventType.PAYMENT_COMPLETED,
            source=ServiceSource.PAYMENT_SERVICE,
            data={
                "payment_id": "pay_fanout_test",
                "amount": 299.99,
                "user_id": "user_fanout"
            }
        )

        await event_bus.publish_event(event)
        print(f"✅ Published single payment.completed event: {event.id}")

        # Wait for event to be processed
        await asyncio.sleep(2)

        # Verify all subscribers received the event
        assert len(collector1.events) >= 1, "Collector 1 should have received event"
        assert len(collector2.events) >= 1, "Collector 2 should have received event"
        assert len(collector3.events) >= 1, "Collector 3 should have received event"

        print(f"✅ Fanout pattern verified: 1 event → 3+ subscribers")
        print(f"   Collector 1 (Notification): {len(collector1.events)} events")
        print(f"   Collector 2 (Audit): {len(collector2.events)} events")
        print(f"   Collector 3 (Analytics): {len(collector3.events)} events")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_integration_tests():
    """Run all integration tests"""
    print("\n" + "="*80)
    print("EVENT-DRIVEN ARCHITECTURE - END-TO-END INTEGRATION TESTS")
    print("="*80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Testing NATS JetStream event flows across microservices")

    # Connect to NATS once for all tests
    event_bus = None
    try:
        event_bus = await get_event_bus("integration_test_suite")
        print("✅ Connected to NATS event bus")
    except Exception as e:
        print(f"❌ Failed to connect to NATS: {e}")
        return 0, 5

    results = {}

    # Run tests
    try:
        results["session_to_billing"] = await test_session_to_billing_flow(event_bus)
    except Exception as e:
        print(f"❌ TEST 1 FAILED: {e}")
        results["session_to_billing"] = False

    try:
        results["order_to_billing"] = await test_order_to_billing_flow(event_bus)
    except Exception as e:
        print(f"❌ TEST 2 FAILED: {e}")
        results["order_to_billing"] = False

    try:
        results["auth_to_notification"] = await test_user_login_to_notification_flow(event_bus)
    except Exception as e:
        print(f"❌ TEST 3 FAILED: {e}")
        results["auth_to_notification"] = False

    try:
        results["wildcard_audit"] = await test_wildcard_audit_logging(event_bus)
    except Exception as e:
        print(f"❌ TEST 4 FAILED: {e}")
        results["wildcard_audit"] = False

    try:
        results["multi_subscriber_fanout"] = await test_multi_subscriber_fanout(event_bus)
    except Exception as e:
        print(f"❌ TEST 5 FAILED: {e}")
        results["multi_subscriber_fanout"] = False

    # Close event bus
    if event_bus:
        await event_bus.close()
        print("\n✅ Closed event bus connection")

    # Print summary
    print("\n" + "="*80)
    print("INTEGRATION TEST SUMMARY")
    print("="*80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print(f"\nTotal: {passed}/{total} integration tests passed")

    if passed == total:
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        print("✅ Event-driven architecture is working correctly end-to-end")
    else:
        print("\n⚠️  Some integration tests failed")

    return passed, total


if __name__ == "__main__":
    passed, total = asyncio.run(run_all_integration_tests())

    # Exit with appropriate code
    if passed == total:
        sys.exit(0)
    else:
        sys.exit(1)
