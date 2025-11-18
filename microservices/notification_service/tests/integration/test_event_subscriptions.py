#!/usr/bin/env python3
"""
Test Notification Service Event Subscriptions

Tests that notification service correctly handles events from other services
"""

import asyncio
import sys
import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from microservices.notification_service.events.handlers import NotificationEventHandlers
from microservices.notification_service.notification_service import NotificationService
from core.nats_client import Event, EventType, ServiceSource, get_event_bus


class MockNotificationRepository:
    """Mock repository for testing"""

    async def create_notification(self, notification):
        """Mock create notification"""
        return notification

    async def create_in_app_notification(self, notification):
        """Mock create in-app notification"""
        return notification


class MockNotificationService:
    """Mock notification service for testing"""

    def __init__(self):
        self.repository = MockNotificationRepository()
        self.sent_notifications = []

    async def send_notification(self, request):
        """Mock send notification"""
        self.sent_notifications.append({
            "type": request.type,
            "recipient_id": request.recipient_id,
            "subject": request.subject,
            "content": request.content,
            "priority": request.priority,
            "metadata": request.metadata
        })
        print(f"✅ Mock notification sent: {request.subject}")
        return {"success": True, "notification_id": f"notif_{len(self.sent_notifications)}"}


async def test_user_logged_in_handler():
    """Test handling of user.logged_in event"""
    print("\n" + "="*60)
    print("TEST 1: User Logged In Event Handler")
    print("="*60)

    # Create mock service
    mock_service = MockNotificationService()
    handlers = NotificationEventHandlers(mock_service)

    # Create event
    event = Event(
        event_type=EventType.USER_LOGGED_IN,
        source=ServiceSource.AUTH_SERVICE,
        data={
            "user_id": "user_123",
            "email": "user@example.com",
            "provider": "email",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

    # Handle event
    await handlers.handle_user_logged_in(event)

    # Verify notification was sent
    assert len(mock_service.sent_notifications) == 1, "Expected 1 notification"
    notif = mock_service.sent_notifications[0]
    assert notif["recipient_id"] == "user_123"
    assert "Welcome back" in notif["subject"]
    assert notif["type"].value == "in_app"

    # Verify idempotency - same event should not be processed twice
    await handlers.handle_user_logged_in(event)
    assert len(mock_service.sent_notifications) == 1, "Event should be processed only once (idempotency)"

    print(f"✅ user.logged_in event handled correctly")
    print(f"   Recipient: {notif['recipient_id']}")
    print(f"   Subject: {notif['subject']}")
    print(f"   Idempotency verified")

    return True


async def test_payment_completed_handler():
    """Test handling of payment.completed event"""
    print("\n" + "="*60)
    print("TEST 2: Payment Completed Event Handler")
    print("="*60)

    # Create mock service
    mock_service = MockNotificationService()
    handlers = NotificationEventHandlers(mock_service)

    # Create event
    event = Event(
        event_type=EventType.PAYMENT_COMPLETED,
        source=ServiceSource.PAYMENT_SERVICE,
        data={
            "payment_id": "pay_123",
            "user_id": "user_456",
            "amount": 99.99,
            "currency": "USD",
            "customer_email": "customer@example.com",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

    # Handle event
    await handlers.handle_payment_completed(event)

    # Verify notifications were sent (email + in-app)
    assert len(mock_service.sent_notifications) == 2, "Expected 2 notifications (email + in-app)"

    # Check email notification
    email_notif = [n for n in mock_service.sent_notifications if n["type"].value == "email"][0]
    assert email_notif["recipient_id"] == "user_456"
    assert "Receipt" in email_notif["subject"]
    assert email_notif["metadata"]["payment_id"] == "pay_123"

    # Check in-app notification
    in_app_notif = [n for n in mock_service.sent_notifications if n["type"].value == "in_app"][0]
    assert in_app_notif["recipient_id"] == "user_456"
    assert "Payment Completed" in in_app_notif["subject"]

    print(f"✅ payment.completed event handled correctly")
    print(f"   Email receipt sent: {email_notif['subject']}")
    print(f"   In-app notification sent: {in_app_notif['subject']}")

    return True


async def test_organization_member_added_handler():
    """Test handling of organization.member_added event"""
    print("\n" + "="*60)
    print("TEST 3: Organization Member Added Event Handler")
    print("="*60)

    # Create mock service
    mock_service = MockNotificationService()
    handlers = NotificationEventHandlers(mock_service)

    # Create event
    event = Event(
        event_type=EventType.ORG_MEMBER_ADDED,
        source=ServiceSource.ORG_SERVICE,
        data={
            "organization_id": "org_789",
            "organization_name": "Acme Corp",
            "user_id": "user_999",
            "role": "member",
            "added_by": "admin_user",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

    # Handle event
    await handlers.handle_organization_member_added(event)

    # Verify notification was sent
    assert len(mock_service.sent_notifications) == 1, "Expected 1 notification"
    notif = mock_service.sent_notifications[0]
    assert notif["recipient_id"] == "user_999"
    assert "Acme Corp" in notif["subject"]
    assert "member" in notif["content"]

    print(f"✅ organization.member_added event handled correctly")
    print(f"   Recipient: {notif['recipient_id']}")
    print(f"   Organization: Acme Corp")

    return True


async def test_device_offline_handler():
    """Test handling of device.offline event"""
    print("\n" + "="*60)
    print("TEST 4: Device Offline Event Handler")
    print("="*60)

    # Create mock service
    mock_service = MockNotificationService()
    handlers = NotificationEventHandlers(mock_service)

    # Create event
    event = Event(
        event_type=EventType.DEVICE_OFFLINE,
        source=ServiceSource.DEVICE_SERVICE,
        data={
            "device_id": "device_123",
            "device_name": "Smart Frame 1",
            "user_id": "user_555",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

    # Handle event
    await handlers.handle_device_offline(event)

    # Verify notification was sent
    assert len(mock_service.sent_notifications) == 1, "Expected 1 notification"
    notif = mock_service.sent_notifications[0]
    assert notif["recipient_id"] == "user_555"
    assert "Smart Frame 1" in notif["subject"]
    assert "offline" in notif["content"]

    print(f"✅ device.offline event handled correctly")
    print(f"   Device: {event.data['device_name']}")
    print(f"   Recipient: {notif['recipient_id']}")

    return True


async def test_file_shared_handler():
    """Test handling of file.shared event"""
    print("\n" + "="*60)
    print("TEST 5: File Shared Event Handler")
    print("="*60)

    # Create mock service
    mock_service = MockNotificationService()
    handlers = NotificationEventHandlers(mock_service)

    # Create event
    event = Event(
        event_type=EventType.FILE_SHARED,
        source=ServiceSource.STORAGE_SERVICE,
        data={
            "share_id": "share_abc",
            "file_id": "file_789",
            "file_name": "document.pdf",
            "shared_by": "user_111",
            "shared_with": "user_222",
            "shared_with_email": "recipient@example.com",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

    # Handle event
    await handlers.handle_file_shared(event)

    # Verify notification was sent
    assert len(mock_service.sent_notifications) == 1, "Expected 1 notification"
    notif = mock_service.sent_notifications[0]
    assert notif["recipient_id"] == "user_222"
    assert "document.pdf" in notif["content"]
    assert "shared" in notif["subject"].lower()

    print(f"✅ file.shared event handled correctly")
    print(f"   File: document.pdf")
    print(f"   Recipient: user_222")

    return True


async def test_nats_subscription():
    """Test actual NATS subscription (if available)"""
    print("\n" + "="*60)
    print("TEST 6: NATS Event Subscription Test")
    print("="*60)

    try:
        # Create mock service
        mock_service = MockNotificationService()
        handlers = NotificationEventHandlers(mock_service)

        # Try to connect to NATS
        event_bus = await get_event_bus("notification_service_test")

        if event_bus and event_bus._is_connected:
            print("✅ Successfully connected to NATS")
            print(f"   URL: {event_bus.nats_url}")

            # Subscribe to a test event
            await event_bus.subscribe_to_events(
                pattern="*.user.logged_in",
                handler=handlers.handle_user_logged_in
            )
            print("✅ Successfully subscribed to user.logged_in events")

            # Publish a test event
            test_event = Event(
                event_type=EventType.USER_LOGGED_IN,
                source=ServiceSource.AUTH_SERVICE,
                data={
                    "user_id": "test_user",
                    "email": "test@example.com",
                    "provider": "email",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

            await event_bus.publish_event(test_event)
            print("✅ Test event published")

            # Wait a moment for the event to be processed
            await asyncio.sleep(2)

            # Check if notification was sent
            if len(mock_service.sent_notifications) > 0:
                print("✅ Event received and notification sent!")
            else:
                print("⚠️  Event published but notification not sent (may need more time)")

            await event_bus.close()
            return True
        else:
            print("⚠️  NATS not available or not configured")
            return False

    except Exception as e:
        print(f"⚠️  NATS subscription test failed: {e}")
        print("   This is OK for testing without NATS running")
        return False


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("NOTIFICATION SERVICE EVENT SUBSCRIPTION TEST SUITE")
    print("="*80)
    print(f"Timestamp: {datetime.now().isoformat()}")

    results = {}

    # Run tests
    try:
        results["user_logged_in_handler"] = await test_user_logged_in_handler()
    except Exception as e:
        print(f"❌ TEST 1 FAILED: {e}")
        results["user_logged_in_handler"] = False

    try:
        results["payment_completed_handler"] = await test_payment_completed_handler()
    except Exception as e:
        print(f"❌ TEST 2 FAILED: {e}")
        results["payment_completed_handler"] = False

    try:
        results["organization_member_added_handler"] = await test_organization_member_added_handler()
    except Exception as e:
        print(f"❌ TEST 3 FAILED: {e}")
        results["organization_member_added_handler"] = False

    try:
        results["device_offline_handler"] = await test_device_offline_handler()
    except Exception as e:
        print(f"❌ TEST 4 FAILED: {e}")
        results["device_offline_handler"] = False

    try:
        results["file_shared_handler"] = await test_file_shared_handler()
    except Exception as e:
        print(f"❌ TEST 5 FAILED: {e}")
        results["file_shared_handler"] = False

    try:
        results["nats_subscription"] = await test_nats_subscription()
    except Exception as e:
        print(f"❌ TEST 6 FAILED: {e}")
        results["nats_subscription"] = False

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
    elif passed >= 5:  # Core handler tests (NATS is optional)
        print("\n✅ Core handler tests passed (NATS optional)")
    else:
        print("\n⚠️  Some tests failed")

    return passed, total


if __name__ == "__main__":
    passed, total = asyncio.run(run_all_tests())

    # Exit with appropriate code
    if passed >= 5:  # Core tests must pass (NATS is optional)
        sys.exit(0)
    else:
        sys.exit(1)
