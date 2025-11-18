#!/usr/bin/env python3
"""
Test Calendar Service Event Subscriptions

Tests that calendar service correctly handles events from other services
"""

import asyncio
import sys
import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from microservices.calendar_service.events.handlers import CalendarEventHandlers
from core.nats_client import Event, EventType, ServiceSource


class MockCalendarEvent:
    """Mock calendar event object"""

    def __init__(self, event_id, user_id):
        self.event_id = event_id
        self.user_id = user_id
        self.title = "Test Event"
        self.start_time = datetime.utcnow()
        self.end_time = datetime.utcnow()
        self.created_at = datetime.utcnow()


class MockCalendarRepository:
    """Mock repository for testing"""

    def __init__(self):
        self.calendar_data = {}
        self.deleted_users = []

    async def get_events_by_user(self, user_id):
        """Mock get events by user"""
        return self.calendar_data.get(user_id, [])

    async def delete_user_data(self, user_id):
        """Mock delete user data"""
        self.deleted_users.append(user_id)

        # Count and remove data
        events = self.calendar_data.get(user_id, [])
        deleted_count = len(events)

        if user_id in self.calendar_data:
            del self.calendar_data[user_id]

        return deleted_count


class MockCalendarService:
    """Mock calendar service for testing"""

    def __init__(self):
        self.repository = MockCalendarRepository()


async def test_user_deleted_event():
    """Test handling of user.deleted event - should cleanup all user calendar data"""
    print("\n" + "="*60)
    print("TEST 1: User Deleted Event Handler")
    print("="*60)

    # Create mock service and handlers
    mock_service = MockCalendarService()
    handlers = CalendarEventHandlers(mock_service)

    # Setup: Add calendar data for the user
    user_id = "user_123"
    mock_service.repository.calendar_data[user_id] = [
        MockCalendarEvent("evt_1", user_id),
        MockCalendarEvent("evt_2", user_id),
        MockCalendarEvent("evt_3", user_id),
    ]

    initial_events = len(mock_service.repository.calendar_data[user_id])
    print(f"📅 User has {initial_events} calendar events")

    # Create user.deleted event
    event_data = {
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat()
    }

    # Handle event
    print(f"🔥 Triggering user.deleted event for user: {user_id}")
    await handlers.handle_user_deleted(event_data)

    # Verify data was deleted
    deleted_users = mock_service.repository.deleted_users
    remaining_events = mock_service.repository.calendar_data.get(user_id, [])

    print(f"✅ Deleted data for {len(deleted_users)} user(s)")
    print(f"✅ Remaining events: {len(remaining_events)}")

    assert len(deleted_users) == 1, f"Expected 1 user deleted, got {len(deleted_users)}"
    assert deleted_users[0] == user_id, f"Expected {user_id}, got {deleted_users[0]}"
    assert len(remaining_events) == 0, f"Expected 0 events, got {len(remaining_events)}"

    print("✅ TEST PASSED: All calendar data cleaned up successfully")
    return True


async def test_user_deleted_no_data():
    """Test handling of user.deleted event when user has no calendar data"""
    print("\n" + "="*60)
    print("TEST 2: User Deleted Event with No Calendar Data")
    print("="*60)

    # Create mock service and handlers
    mock_service = MockCalendarService()
    handlers = CalendarEventHandlers(mock_service)

    # User has no calendar data
    user_id = "user_456"

    # Create user.deleted event
    event_data = {
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat()
    }

    print(f"🔥 Triggering user.deleted event for user with no data: {user_id}")

    # Handle event
    await handlers.handle_user_deleted(event_data)

    # Verify no errors occurred
    deleted_users = mock_service.repository.deleted_users

    print(f"✅ User deletion handled gracefully")
    assert len(deleted_users) == 1, f"Expected 1 user processed, got {len(deleted_users)}"

    print("✅ TEST PASSED: Handled user with no data gracefully")
    return True


async def test_missing_event_data():
    """Test that handlers gracefully handle missing event data"""
    print("\n" + "="*60)
    print("TEST 3: Missing Event Data Handling")
    print("="*60)

    # Create mock service and handlers
    mock_service = MockCalendarService()
    handlers = CalendarEventHandlers(mock_service)

    # Test user.deleted with missing user_id
    print("🧪 Testing user.deleted with missing user_id")
    await handlers.handle_user_deleted({})

    assert len(mock_service.repository.deleted_users) == 0, \
        "Should not delete anything when user_id is missing"

    print("✅ Handled missing user_id gracefully")

    # Test user.deleted with None user_id
    print("🧪 Testing user.deleted with None user_id")
    await handlers.handle_user_deleted({"user_id": None})

    assert len(mock_service.repository.deleted_users) == 0, \
        "Should not delete anything when user_id is None"

    print("✅ Handled None user_id gracefully")

    print("✅ TEST PASSED: All edge cases handled gracefully")
    return True


async def test_concurrent_user_deletions():
    """Test handling of multiple user.deleted events concurrently"""
    print("\n" + "="*60)
    print("TEST 4: Concurrent User Deletions")
    print("="*60)

    # Create mock service and handlers
    mock_service = MockCalendarService()
    handlers = CalendarEventHandlers(mock_service)

    # Setup: Create calendar data for multiple users
    users = ["user_001", "user_002", "user_003"]
    for user_id in users:
        mock_service.repository.calendar_data[user_id] = [
            MockCalendarEvent(f"{user_id}_evt_1", user_id),
            MockCalendarEvent(f"{user_id}_evt_2", user_id),
        ]

    total_initial_events = sum(
        len(events) for events in mock_service.repository.calendar_data.values()
    )
    print(f"📅 Created calendar data for {len(users)} users ({total_initial_events} total events)")

    # Create multiple user.deleted events
    events = [
        {"user_id": user_id, "timestamp": datetime.utcnow().isoformat()}
        for user_id in users
    ]

    # Handle events concurrently
    print(f"🔥 Triggering {len(events)} user.deleted events concurrently")
    await asyncio.gather(*[
        handlers.handle_user_deleted(event_data)
        for event_data in events
    ])

    # Verify all users were deleted
    deleted_users = mock_service.repository.deleted_users

    print(f"✅ Deleted data for {len(deleted_users)} users")
    assert len(deleted_users) == 3, f"Expected 3 users deleted, got {len(deleted_users)}"

    print("✅ TEST PASSED: Concurrent deletions handled successfully")
    return True


async def test_large_user_data():
    """Test deletion of large amounts of user data"""
    print("\n" + "="*60)
    print("TEST 5: Large User Data Deletion")
    print("="*60)

    # Create mock service and handlers
    mock_service = MockCalendarService()
    handlers = CalendarEventHandlers(mock_service)

    # Setup: Add many calendar events for the user
    user_id = "user_999"
    mock_service.repository.calendar_data[user_id] = [
        MockCalendarEvent(f"evt_{i}", user_id)
        for i in range(100)
    ]

    initial_count = len(mock_service.repository.calendar_data[user_id])
    print(f"📅 User has {initial_count} calendar events")

    # Create user.deleted event
    event_data = {
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat()
    }

    # Handle event
    print(f"🔥 Triggering user.deleted event for user with large dataset")
    await handlers.handle_user_deleted(event_data)

    # Verify all data was deleted
    remaining_events = mock_service.repository.calendar_data.get(user_id, [])

    print(f"✅ Deleted {initial_count} events")
    print(f"✅ Remaining events: {len(remaining_events)}")

    assert len(remaining_events) == 0, f"Expected 0 events, got {len(remaining_events)}"

    print("✅ TEST PASSED: Large dataset deleted successfully")
    return True


async def run_all_tests():
    """Run all calendar service event subscription tests"""
    print("\n" + "📅" * 30)
    print("CALENDAR SERVICE EVENT SUBSCRIPTION TESTS")
    print("📅" * 30)

    tests = [
        ("User Deleted Event", test_user_deleted_event),
        ("User Deleted with No Calendar Data", test_user_deleted_no_data),
        ("Missing Event Data Handling", test_missing_event_data),
        ("Concurrent User Deletions", test_concurrent_user_deletions),
        ("Large User Data Deletion", test_large_user_data),
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
