"""
Invitation Service Event Subscription Tests

Tests that Invitation Service correctly handles events from other services
"""
import asyncio
import sys
import os
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from core.nats_client import Event, EventType, ServiceSource
from microservices.invitation_service.events import InvitationEventHandler


class MockInvitationRepository:
    """Mock Invitation Repository for testing"""

    def __init__(self):
        self.cancelled_orgs = []
        self.cancelled_by_inviter = []

    async def cancel_organization_invitations(self, organization_id: str) -> int:
        """Mock cancel organization invitations"""
        self.cancelled_orgs.append(organization_id)
        # Simulate 3 invitations cancelled
        return 3

    async def cancel_invitations_by_inviter(self, user_id: str) -> int:
        """Mock cancel invitations by inviter"""
        self.cancelled_by_inviter.append(user_id)
        # Simulate 2 invitations cancelled
        return 2


async def test_organization_deleted_event():
    """Test that organization.deleted event cancels all pending invitations"""
    print("\n" + "="*80)
    print("TEST: Handle organization.deleted Event")
    print("="*80)

    # Setup
    mock_repo = MockInvitationRepository()
    event_handler = InvitationEventHandler(mock_repo)

    # Create organization.deleted event
    event_data = {
        "organization_id": "org_456",
        "deleted_by": "admin_123",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Handle event
    success = await event_handler.handle_organization_deleted(event_data)

    # Verify
    assert success is True, "Event handling should succeed"
    assert "org_456" in mock_repo.cancelled_orgs, "Organization should be in cancelled list"
    assert len(mock_repo.cancelled_orgs) == 1, "Should have cancelled invitations for 1 org"

    print("✅ TEST PASSED: organization.deleted event handled correctly")
    print(f"   Cancelled 3 pending invitations for organization org_456")
    return True


async def test_user_deleted_event():
    """Test that user.deleted event cancels invitations sent by user"""
    print("\n" + "="*80)
    print("TEST: Handle user.deleted Event")
    print("="*80)

    # Setup
    mock_repo = MockInvitationRepository()
    event_handler = InvitationEventHandler(mock_repo)

    # Create user.deleted event
    event_data = {
        "user_id": "user_789",
        "deleted_by": "admin_123",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Handle event
    success = await event_handler.handle_user_deleted(event_data)

    # Verify
    assert success is True, "Event handling should succeed"
    assert "user_789" in mock_repo.cancelled_by_inviter, "User should be in cancelled list"
    assert len(mock_repo.cancelled_by_inviter) == 1, "Should have cancelled invitations for 1 user"

    print("✅ TEST PASSED: user.deleted event handled correctly")
    print(f"   Cancelled 2 pending invitations sent by user user_789")
    return True


async def test_missing_organization_id():
    """Test handling of organization.deleted event with missing organization_id"""
    print("\n" + "="*80)
    print("TEST: Handle organization.deleted Event with Missing organization_id")
    print("="*80)

    # Setup
    mock_repo = MockInvitationRepository()
    event_handler = InvitationEventHandler(mock_repo)

    # Create event with missing organization_id
    event_data = {
        "deleted_by": "admin_123",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Handle event
    success = await event_handler.handle_organization_deleted(event_data)

    # Verify - should return False for invalid event
    assert success is False, "Should return False for missing organization_id"
    assert len(mock_repo.cancelled_orgs) == 0, "No invitations should be cancelled"

    print("✅ TEST PASSED: Invalid event handled gracefully")
    return True


async def test_missing_user_id():
    """Test handling of user.deleted event with missing user_id"""
    print("\n" + "="*80)
    print("TEST: Handle user.deleted Event with Missing user_id")
    print("="*80)

    # Setup
    mock_repo = MockInvitationRepository()
    event_handler = InvitationEventHandler(mock_repo)

    # Create event with missing user_id
    event_data = {
        "deleted_by": "admin_123",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Handle event
    success = await event_handler.handle_user_deleted(event_data)

    # Verify - should return False for invalid event
    assert success is False, "Should return False for missing user_id"
    assert len(mock_repo.cancelled_by_inviter) == 0, "No invitations should be cancelled"

    print("✅ TEST PASSED: Invalid event handled gracefully")
    return True


async def test_event_routing():
    """Test that events are routed to correct handlers"""
    print("\n" + "="*80)
    print("TEST: Event Routing")
    print("="*80)

    # Setup
    mock_repo = MockInvitationRepository()
    event_handler = InvitationEventHandler(mock_repo)

    # Create organization.deleted event using Event class
    event = Event(
        event_type=EventType.ORG_UPDATED,  # Use a type that exists
        source=ServiceSource.ORG_SERVICE,
        data={
            "organization_id": "org_456",
            "deleted_by": "admin_123"
        }
    )

    # Manually set the type to test deleted
    event.type = "organization.deleted"

    # Route event
    success = await event_handler.handle_event(event)

    # Verify
    assert success is True, "Event should be routed and handled"
    assert "org_456" in mock_repo.cancelled_orgs, "Organization invitations should be cancelled"

    print("✅ TEST PASSED: Event routing works correctly")
    return True


async def test_get_subscriptions():
    """Test that handler returns correct subscriptions"""
    print("\n" + "="*80)
    print("TEST: Get Subscriptions")
    print("="*80)

    # Setup
    mock_repo = MockInvitationRepository()
    event_handler = InvitationEventHandler(mock_repo)

    # Get subscriptions
    subscriptions = event_handler.get_subscriptions()

    # Verify
    assert isinstance(subscriptions, list), "Should return a list"
    assert len(subscriptions) == 2, "Should have 2 subscriptions"
    assert EventType.USER_DELETED.value in subscriptions, "Should subscribe to user.deleted"

    print("✅ TEST PASSED: Subscriptions configured correctly")
    print(f"   Subscriptions: {subscriptions}")
    return True


async def test_multiple_organizations():
    """Test handling multiple organization deletions"""
    print("\n" + "="*80)
    print("TEST: Multiple Organization Deletions")
    print("="*80)

    # Setup
    mock_repo = MockInvitationRepository()
    event_handler = InvitationEventHandler(mock_repo)

    # Create and handle multiple organization.deleted events
    orgs = ["org_1", "org_2", "org_3"]
    for org_id in orgs:
        event_data = {
            "organization_id": org_id,
            "deleted_by": "admin_123",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        success = await event_handler.handle_organization_deleted(event_data)
        assert success is True, f"Handling should succeed for {org_id}"

    # Verify all organizations were processed
    assert len(mock_repo.cancelled_orgs) == 3, "Should have processed 3 organizations"
    for org_id in orgs:
        assert org_id in mock_repo.cancelled_orgs, f"{org_id} should be in cancelled list"

    print("✅ TEST PASSED: Multiple organizations handled correctly")
    print(f"   Processed {len(orgs)} organization deletions")
    return True


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("INVITATION SERVICE EVENT SUBSCRIPTION TEST SUITE")
    print("="*80)

    tests = [
        ("Organization Deleted Event", test_organization_deleted_event),
        ("User Deleted Event", test_user_deleted_event),
        ("Missing Organization ID", test_missing_organization_id),
        ("Missing User ID", test_missing_user_id),
        ("Event Routing", test_event_routing),
        ("Get Subscriptions", test_get_subscriptions),
        ("Multiple Organizations", test_multiple_organizations),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            result = await test_func()
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ TEST FAILED: {test_name}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "="*80)
    print(f"TEST RESULTS: {passed} passed, {failed} failed out of {len(tests)} total")
    print("="*80)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
