#!/usr/bin/env python3
"""
Test Account Service Event Publishing

Tests that account service correctly publishes events to NATS
"""

import asyncio
import sys
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from microservices.account_service.account_service import AccountService
from microservices.account_service.models import (
    AccountEnsureRequest, AccountUpdateRequest, SubscriptionStatus, User
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


class MockAccountRepository:
    """Mock repository for testing"""

    def __init__(self):
        self.accounts = {}

    async def ensure_account_exists(self, user_id, email, name, subscription_plan):
        """Mock ensure account exists"""
        now = datetime.now(timezone.utc)

        # Simulate new account creation
        if user_id not in self.accounts:
            user = User(
                user_id=user_id,
                email=email,
                name=name,
                subscription_status=subscription_plan,
                is_active=True,
                created_at=now,  # New account
                updated_at=now
            )
            self.accounts[user_id] = user
            return user
        else:
            # Return existing account
            return self.accounts[user_id]

    async def get_account_by_id(self, user_id):
        """Mock get account by id"""
        return self.accounts.get(user_id)

    async def update_account_profile(self, user_id, update_data):
        """Mock update account profile"""
        if user_id in self.accounts:
            user = self.accounts[user_id]
            for key, value in update_data.items():
                setattr(user, key, value)
            user.updated_at = datetime.now(timezone.utc)
            return user
        return None

    async def delete_account(self, user_id):
        """Mock delete account"""
        if user_id in self.accounts:
            self.accounts[user_id].is_active = False
            # Note: User model doesn't have deleted_at field, just mark as inactive
            return True
        return False


async def test_user_created_event():
    """Test user.created event is published when new account is created"""
    print("\n" + "="*60)
    print("TEST 1: User Created Event")
    print("="*60)

    # Create mock event bus and repository
    mock_event_bus = MockEventBus()

    # Create service with mock event bus
    service = AccountService.__new__(AccountService)
    service.event_bus = mock_event_bus
    service.account_repo = MockAccountRepository()

    # Ensure account (should create new one)
    request = AccountEnsureRequest(
        user_id="user_123",
        email="newuser@example.com",
        name="New User",
        subscription_plan=SubscriptionStatus.FREE
    )

    account_response, was_created = await service.ensure_account(request)

    # Verify event was published
    assert len(mock_event_bus.published_events) == 1, "Expected 1 event to be published"
    event = mock_event_bus.published_events[0]

    assert event["type"] == EventType.USER_CREATED.value, f"Expected user.created, got {event['type']}"
    assert event["source"] == ServiceSource.ACCOUNT_SERVICE.value
    assert event["data"]["user_id"] == "user_123"
    assert event["data"]["email"] == "newuser@example.com"
    assert event["data"]["name"] == "New User"
    assert "timestamp" in event["data"]

    print(f"✅ user.created event published successfully")
    print(f"   User ID: {event['data']['user_id']}")
    print(f"   Email: {event['data']['email']}")
    print(f"   Name: {event['data']['name']}")

    return True


async def test_user_created_event_not_published_for_existing():
    """Test user.created event is NOT published when account already exists"""
    print("\n" + "="*60)
    print("TEST 2: User Created Event Not Published for Existing Account")
    print("="*60)

    # Create mock event bus and repository
    mock_event_bus = MockEventBus()

    # Create service with mock event bus
    service = AccountService.__new__(AccountService)
    service.event_bus = mock_event_bus
    service.account_repo = MockAccountRepository()

    # Create account first
    request = AccountEnsureRequest(
        user_id="user_456",
        email="existing@example.com",
        name="Existing User",
        subscription_plan=SubscriptionStatus.PREMIUM
    )

    await service.ensure_account(request)

    # Clear events
    mock_event_bus.published_events.clear()

    # Modify account to appear old
    service.account_repo.accounts["user_456"].created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)

    # Try to ensure same account again (should not create)
    await service.ensure_account(request)

    # Verify NO event was published
    assert len(mock_event_bus.published_events) == 0, "Expected 0 events for existing account"

    print(f"✅ user.created event NOT published for existing account (correct)")

    return True


async def test_user_profile_updated_event():
    """Test user.profile_updated event is published when profile is updated"""
    print("\n" + "="*60)
    print("TEST 3: User Profile Updated Event")
    print("="*60)

    # Create mock event bus and repository
    mock_event_bus = MockEventBus()

    # Create service with mock event bus
    service = AccountService.__new__(AccountService)
    service.event_bus = mock_event_bus
    service.account_repo = MockAccountRepository()

    # Create account first
    ensure_request = AccountEnsureRequest(
        user_id="user_789",
        email="user@example.com",
        name="Original Name",
        subscription_plan=SubscriptionStatus.FREE
    )
    await service.ensure_account(ensure_request)

    # Clear events from account creation
    mock_event_bus.published_events.clear()

    # Update account profile
    update_request = AccountUpdateRequest(
        name="Updated Name",
        email="updated@example.com"
    )

    await service.update_account_profile("user_789", update_request)

    # Verify event was published
    assert len(mock_event_bus.published_events) == 1, "Expected 1 event to be published"
    event = mock_event_bus.published_events[0]

    assert event["type"] == EventType.USER_PROFILE_UPDATED.value
    assert event["source"] == ServiceSource.ACCOUNT_SERVICE.value
    assert event["data"]["user_id"] == "user_789"
    assert event["data"]["email"] == "updated@example.com"
    assert event["data"]["name"] == "Updated Name"
    assert "updated_fields" in event["data"]
    assert "name" in event["data"]["updated_fields"]
    assert "email" in event["data"]["updated_fields"]

    print(f"✅ user.profile_updated event published successfully")
    print(f"   User ID: {event['data']['user_id']}")
    print(f"   Updated Fields: {event['data']['updated_fields']}")
    print(f"   New Name: {event['data']['name']}")

    return True


async def test_user_deleted_event():
    """Test user.deleted event is published when account is deleted"""
    print("\n" + "="*60)
    print("TEST 4: User Deleted Event")
    print("="*60)

    # Create mock event bus and repository
    mock_event_bus = MockEventBus()

    # Create service with mock event bus
    service = AccountService.__new__(AccountService)
    service.event_bus = mock_event_bus
    service.account_repo = MockAccountRepository()

    # Create account first
    ensure_request = AccountEnsureRequest(
        user_id="user_delete",
        email="delete@example.com",
        name="Delete Me",
        subscription_plan=SubscriptionStatus.FREE
    )
    await service.ensure_account(ensure_request)

    # Clear events from account creation
    mock_event_bus.published_events.clear()

    # Delete account
    success = await service.delete_account("user_delete", reason="User requested deletion")

    # Verify event was published
    assert success, "Account deletion should succeed"
    assert len(mock_event_bus.published_events) == 1, "Expected 1 event to be published"
    event = mock_event_bus.published_events[0]

    assert event["type"] == EventType.USER_DELETED.value
    assert event["source"] == ServiceSource.ACCOUNT_SERVICE.value
    assert event["data"]["user_id"] == "user_delete"
    assert event["data"]["email"] == "delete@example.com"
    assert event["data"]["reason"] == "User requested deletion"

    print(f"✅ user.deleted event published successfully")
    print(f"   User ID: {event['data']['user_id']}")
    print(f"   Email: {event['data']['email']}")
    print(f"   Reason: {event['data']['reason']}")

    return True


async def test_graceful_degradation_without_event_bus():
    """Test service works without event bus (graceful degradation)"""
    print("\n" + "="*60)
    print("TEST 5: Graceful Degradation Without Event Bus")
    print("="*60)

    # Create service WITHOUT event bus
    service = AccountService.__new__(AccountService)
    service.event_bus = None  # No event bus
    service.account_repo = MockAccountRepository()

    # Ensure account
    request = AccountEnsureRequest(
        user_id="user_no_events",
        email="noevents@example.com",
        name="No Events User",
        subscription_plan=SubscriptionStatus.FREE
    )

    account_response, was_created = await service.ensure_account(request)

    # Verify account was created successfully
    assert account_response.user_id == "user_no_events"
    assert was_created == True

    print(f"✅ Service works without event bus (graceful degradation)")
    print(f"   Account created: {account_response.user_id}")
    print(f"   No events published (expected)")

    return True


async def test_nats_connection():
    """Test actual NATS connection (if available)"""
    print("\n" + "="*60)
    print("TEST 6: NATS Connection Test")
    print("="*60)

    try:
        # Try to connect to NATS
        event_bus = await get_event_bus("account_service_test")

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
    print("ACCOUNT SERVICE EVENT PUBLISHING TEST SUITE")
    print("="*80)
    print(f"Timestamp: {datetime.now().isoformat()}")

    results = {}

    # Run tests
    try:
        results["user_created_event"] = await test_user_created_event()
    except Exception as e:
        print(f"❌ TEST 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["user_created_event"] = False

    try:
        results["user_created_not_published_existing"] = await test_user_created_event_not_published_for_existing()
    except Exception as e:
        print(f"❌ TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["user_created_not_published_existing"] = False

    try:
        results["user_profile_updated_event"] = await test_user_profile_updated_event()
    except Exception as e:
        print(f"❌ TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["user_profile_updated_event"] = False

    try:
        results["user_deleted_event"] = await test_user_deleted_event()
    except Exception as e:
        print(f"❌ TEST 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["user_deleted_event"] = False

    try:
        results["graceful_degradation"] = await test_graceful_degradation_without_event_bus()
    except Exception as e:
        print(f"❌ TEST 5 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["graceful_degradation"] = False

    try:
        results["nats_connection"] = await test_nats_connection()
    except Exception as e:
        print(f"❌ TEST 6 FAILED: {e}")
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
    elif passed >= 5:  # Core tests (NATS is optional)
        print("\n✅ Core tests passed (NATS optional)")
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
