#!/usr/bin/env python3
"""
Test Notification Service Event Publishing

Tests that notification service correctly publishes NOTIFICATION_SENT events
"""

import asyncio
import sys
import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from microservices.notification_service.notification_service import NotificationService
from microservices.notification_service.models import (
    Notification, NotificationStatus, NotificationType, NotificationPriority, RecipientType
)
from core.nats_client import Event, EventType, ServiceSource


class MockEventBus:
    """Mock event bus for testing"""

    def __init__(self):
        self.published_events = []

    async def publish_event(self, event):
        """Mock publish event"""
        self.published_events.append(event)
        return True

    def get_published_events(self, event_type=None):
        """Get published events, optionally filtered by type"""
        if event_type:
            # Event object has 'type' attribute, not 'event_type'
            event_type_value = event_type.value if hasattr(event_type, 'value') else event_type
            return [e for e in self.published_events if e.type == event_type_value]
        return self.published_events

    def clear(self):
        """Clear published events"""
        self.published_events = []


async def test_notification_sent_event_email():
    """Test NOTIFICATION_SENT event is published for email notifications"""
    print("\n" + "="*60)
    print("TEST 1: NOTIFICATION_SENT Event for Email")
    print("="*60)

    # Create mock event bus
    mock_event_bus = MockEventBus()

    # Create notification service with mock event bus
    service = NotificationService(event_bus=mock_event_bus)

    # Create a mock notification
    notification = Notification(
        notification_id="ntf_email_123",
        type=NotificationType.EMAIL,
        priority=NotificationPriority.NORMAL,
        recipient_type=RecipientType.EMAIL,
        recipient_email="user@example.com",
        recipient_id="user_123",
        subject="Test Email",
        content="This is a test email notification",
        status=NotificationStatus.SENT
    )

    print(f"📧 Publishing NOTIFICATION_SENT event for email: {notification.notification_id}")

    # Publish the event
    await service._publish_notification_sent_event(notification)

    # Verify event was published
    events = mock_event_bus.get_published_events(EventType.NOTIFICATION_SENT)

    print(f"✅ Published {len(events)} events")
    assert len(events) == 1, f"Expected 1 event, got {len(events)}"

    # Verify event details
    event = events[0]
    assert event.type == EventType.NOTIFICATION_SENT.value, \
        f"Expected notification.sent, got {event.type}"
    assert event.source == ServiceSource.NOTIFICATION_SERVICE.value, \
        f"Expected notification_service, got {event.source}"
    assert event.data["notification_id"] == "ntf_email_123", \
        f"Expected ntf_email_123, got {event.data['notification_id']}"
    assert event.data["notification_type"] == "email", \
        f"Expected email, got {event.data['notification_type']}"
    assert event.data["recipient_email"] == "user@example.com", \
        f"Expected user@example.com, got {event.data['recipient_email']}"
    assert event.data["status"] == "sent", \
        f"Expected sent, got {event.data['status']}"

    print("✅ Event data validated:")
    print(f"   - notification_id: {event.data['notification_id']}")
    print(f"   - type: {event.data['notification_type']}")
    print(f"   - recipient: {event.data['recipient_email']}")
    print(f"   - status: {event.data['status']}")

    print("✅ TEST PASSED: Email notification event published successfully")
    return True


async def test_notification_sent_event_in_app():
    """Test NOTIFICATION_SENT event is published for in-app notifications"""
    print("\n" + "="*60)
    print("TEST 2: NOTIFICATION_SENT Event for In-App Notification")
    print("="*60)

    # Create mock event bus
    mock_event_bus = MockEventBus()

    # Create notification service with mock event bus
    service = NotificationService(event_bus=mock_event_bus)

    # Create a mock in-app notification
    notification = Notification(
        notification_id="ntf_inapp_456",
        type=NotificationType.IN_APP,
        priority=NotificationPriority.HIGH,
        recipient_type=RecipientType.USER,
        recipient_id="user_456",
        subject="New Message",
        content="You have a new message from John",
        status=NotificationStatus.DELIVERED
    )

    print(f"📱 Publishing NOTIFICATION_SENT event for in-app: {notification.notification_id}")

    # Publish the event
    await service._publish_notification_sent_event(notification)

    # Verify event was published
    events = mock_event_bus.get_published_events(EventType.NOTIFICATION_SENT)

    print(f"✅ Published {len(events)} events")
    assert len(events) == 1, f"Expected 1 event, got {len(events)}"

    # Verify event details
    event = events[0]
    assert event.data["notification_type"] == "in_app", \
        f"Expected in_app, got {event.data['notification_type']}"
    assert event.data["priority"] == "high", \
        f"Expected high, got {event.data['priority']}"
    assert event.data["status"] == "delivered", \
        f"Expected delivered, got {event.data['status']}"

    print("✅ Event data validated:")
    print(f"   - notification_id: {event.data['notification_id']}")
    print(f"   - type: {event.data['notification_type']}")
    print(f"   - recipient_id: {event.data['recipient_id']}")
    print(f"   - priority: {event.data['priority']}")

    print("✅ TEST PASSED: In-app notification event published successfully")
    return True


async def test_notification_sent_event_push():
    """Test NOTIFICATION_SENT event is published for push notifications"""
    print("\n" + "="*60)
    print("TEST 3: NOTIFICATION_SENT Event for Push Notification")
    print("="*60)

    # Create mock event bus
    mock_event_bus = MockEventBus()

    # Create notification service with mock event bus
    service = NotificationService(event_bus=mock_event_bus)

    # Create a mock push notification
    notification = Notification(
        notification_id="ntf_push_789",
        type=NotificationType.PUSH,
        priority=NotificationPriority.URGENT,
        recipient_type=RecipientType.USER,
        recipient_id="user_789",
        subject="Urgent Alert",
        content="Your device is offline",
        status=NotificationStatus.DELIVERED
    )

    print(f"📲 Publishing NOTIFICATION_SENT event for push: {notification.notification_id}")

    # Publish the event
    await service._publish_notification_sent_event(notification)

    # Verify event was published
    events = mock_event_bus.get_published_events(EventType.NOTIFICATION_SENT)

    print(f"✅ Published {len(events)} events")
    assert len(events) == 1, f"Expected 1 event, got {len(events)}"

    # Verify event details
    event = events[0]
    assert event.data["notification_type"] == "push", \
        f"Expected push, got {event.data['notification_type']}"
    assert event.data["priority"] == "urgent", \
        f"Expected urgent, got {event.data['priority']}"

    print("✅ Event data validated:")
    print(f"   - notification_id: {event.data['notification_id']}")
    print(f"   - type: {event.data['notification_type']}")
    print(f"   - priority: {event.data['priority']}")

    print("✅ TEST PASSED: Push notification event published successfully")
    return True


async def test_notification_sent_event_webhook():
    """Test NOTIFICATION_SENT event is published for webhook notifications"""
    print("\n" + "="*60)
    print("TEST 4: NOTIFICATION_SENT Event for Webhook")
    print("="*60)

    # Create mock event bus
    mock_event_bus = MockEventBus()

    # Create notification service with mock event bus
    service = NotificationService(event_bus=mock_event_bus)

    # Create a mock webhook notification
    notification = Notification(
        notification_id="ntf_webhook_101",
        type=NotificationType.WEBHOOK,
        priority=NotificationPriority.NORMAL,
        recipient_type=RecipientType.USER,
        subject="Webhook Event",
        content="Data update notification",
        status=NotificationStatus.DELIVERED
    )

    print(f"🔗 Publishing NOTIFICATION_SENT event for webhook: {notification.notification_id}")

    # Publish the event
    await service._publish_notification_sent_event(notification)

    # Verify event was published
    events = mock_event_bus.get_published_events(EventType.NOTIFICATION_SENT)

    print(f"✅ Published {len(events)} events")
    assert len(events) == 1, f"Expected 1 event, got {len(events)}"

    # Verify event details
    event = events[0]
    assert event.data["notification_type"] == "webhook", \
        f"Expected webhook, got {event.data['notification_type']}"

    print("✅ Event data validated")
    print("✅ TEST PASSED: Webhook notification event published successfully")
    return True


async def test_no_event_bus():
    """Test that service handles missing event bus gracefully"""
    print("\n" + "="*60)
    print("TEST 5: Graceful Handling of Missing Event Bus")
    print("="*60)

    # Create notification service WITHOUT event bus
    service = NotificationService(event_bus=None)

    # Create a mock notification
    notification = Notification(
        notification_id="ntf_no_bus_001",
        type=NotificationType.EMAIL,
        priority=NotificationPriority.NORMAL,
        recipient_type=RecipientType.EMAIL,
        recipient_email="user@example.com",
        subject="Test",
        content="Test content",
        status=NotificationStatus.SENT
    )

    print(f"🚫 Attempting to publish event without event bus")

    # Try to publish the event - should not raise an error
    await service._publish_notification_sent_event(notification)

    print("✅ Handled missing event bus gracefully (no exception raised)")
    print("✅ TEST PASSED: Service degrades gracefully without event bus")
    return True


async def test_multiple_notifications_published():
    """Test publishing events for multiple notifications"""
    print("\n" + "="*60)
    print("TEST 6: Multiple Notification Events")
    print("="*60)

    # Create mock event bus
    mock_event_bus = MockEventBus()

    # Create notification service with mock event bus
    service = NotificationService(event_bus=mock_event_bus)

    # Create multiple notifications
    notifications = [
        Notification(
            notification_id=f"ntf_{i}",
            type=NotificationType.EMAIL,
            priority=NotificationPriority.NORMAL,
            recipient_type=RecipientType.EMAIL,
            recipient_email=f"user{i}@example.com",
            subject=f"Test {i}",
            content=f"Content {i}",
            status=NotificationStatus.SENT
        )
        for i in range(5)
    ]

    print(f"📤 Publishing events for {len(notifications)} notifications")

    # Publish events for all notifications
    for notification in notifications:
        await service._publish_notification_sent_event(notification)

    # Verify all events were published
    events = mock_event_bus.get_published_events(EventType.NOTIFICATION_SENT)

    print(f"✅ Published {len(events)} events")
    assert len(events) == 5, f"Expected 5 events, got {len(events)}"

    # Verify each event has unique notification_id
    notification_ids = [e.data["notification_id"] for e in events]
    assert len(set(notification_ids)) == 5, "Expected 5 unique notification IDs"

    print("✅ All events published with unique IDs")
    print("✅ TEST PASSED: Multiple notifications published successfully")
    return True


async def test_event_data_completeness():
    """Test that all required fields are present in event data"""
    print("\n" + "="*60)
    print("TEST 7: Event Data Completeness")
    print("="*60)

    # Create mock event bus
    mock_event_bus = MockEventBus()

    # Create notification service with mock event bus
    service = NotificationService(event_bus=mock_event_bus)

    # Create a notification
    notification = Notification(
        notification_id="ntf_complete_001",
        type=NotificationType.EMAIL,
        priority=NotificationPriority.NORMAL,
        recipient_type=RecipientType.EMAIL,
        recipient_email="user@example.com",
        recipient_id="user_123",
        subject="Complete Test",
        content="Testing completeness",
        status=NotificationStatus.SENT
    )

    # Publish the event
    await service._publish_notification_sent_event(notification)

    # Get the event
    events = mock_event_bus.get_published_events(EventType.NOTIFICATION_SENT)
    event = events[0]

    # Verify all required fields are present
    required_fields = [
        "notification_id",
        "notification_type",
        "recipient_id",
        "recipient_email",
        "status",
        "subject",
        "priority",
        "timestamp"
    ]

    print(f"🔍 Verifying {len(required_fields)} required fields")

    for field in required_fields:
        assert field in event.data, f"Missing required field: {field}"
        print(f"   ✓ {field}: {event.data[field]}")

    print("✅ All required fields present")
    print("✅ TEST PASSED: Event data is complete")
    return True


async def run_all_tests():
    """Run all notification service event publishing tests"""
    print("\n" + "🔔" * 30)
    print("NOTIFICATION SERVICE EVENT PUBLISHING TESTS")
    print("🔔" * 30)

    tests = [
        ("Email Notification Event", test_notification_sent_event_email),
        ("In-App Notification Event", test_notification_sent_event_in_app),
        ("Push Notification Event", test_notification_sent_event_push),
        ("Webhook Notification Event", test_notification_sent_event_webhook),
        ("Missing Event Bus Handling", test_no_event_bus),
        ("Multiple Notifications", test_multiple_notifications_published),
        ("Event Data Completeness", test_event_data_completeness),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, "PASSED" if result else "FAILED"))
        except Exception as e:
            print(f"❌ TEST FAILED: {test_name}")
            print(f"   Error: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append((test_name, "FAILED"))

    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(1 for _, status in results if status == "PASSED")
    total = len(results)

    for test_name, status in results:
        emoji = "✅" if status == "PASSED" else "❌"
        print(f"{emoji} {test_name}: {status}")

    print(f"\n📊 Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        return True
    else:
        print("⚠️  SOME TESTS FAILED")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
