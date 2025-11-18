"""
Organization Service Event Subscription Tests

Tests that Organization Service correctly handles events from other services
"""
import asyncio
import sys
import os
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from microservices.organization_service.events import OrganizationEventHandler


class SimpleMember:
    """Simple member object for testing"""
    def __init__(self, user_id, role):
        self.user_id = user_id
        self.role = role


class MockOrganizationRepository:
    """Mock Organization Repository for testing"""

    def __init__(self):
        self.organizations = {}
        self.members = {}
        self.removed_users = []

    async def remove_user_from_all_organizations(self, user_id: str) -> int:
        """Mock remove user from all organizations"""
        count = 0
        for org_id, members_list in list(self.members.items()):
            if user_id in [m.user_id for m in members_list]:
                # Remove user from this organization
                self.members[org_id] = [m for m in members_list if m.user_id != user_id]
                count += 1

        self.removed_users.append(user_id)
        return count


async def test_user_deleted_event():
    """Test that user.deleted event removes user from all organizations"""
    print("\n" + "="*80)
    print("TEST: Handle user.deleted Event")
    print("="*80)

    # Setup
    mock_repo = MockOrganizationRepository()
    event_handler = OrganizationEventHandler(mock_repo)

    # Prepare test data - user is member of 3 organizations
    mock_repo.members = {
        "org_1": [
            SimpleMember("user_123", "member"),
            SimpleMember("user_456", "admin")
        ],
        "org_2": [
            SimpleMember("user_123", "owner")
        ],
        "org_3": [
            SimpleMember("user_123", "member"),
            SimpleMember("user_789", "admin")
        ]
    }

    # Create user.deleted event
    event_data = {
        "event_type": "user.deleted",
        "user_id": "user_123",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Handle event
    await event_handler.handle_user_deleted(event_data)

    # Verify user was removed from all organizations
    assert "user_123" in mock_repo.removed_users, "User should be marked as removed"

    # Verify user was removed from all 3 organizations
    for org_id, members_list in mock_repo.members.items():
        user_ids = [m.user_id for m in members_list]
        assert "user_123" not in user_ids, f"User should be removed from {org_id}"

    # Verify other users remain
    assert len(mock_repo.members["org_1"]) == 1, "org_1 should still have 1 member"
    assert mock_repo.members["org_1"][0].user_id == "user_456", "user_456 should remain in org_1"
    assert len(mock_repo.members["org_2"]) == 0, "org_2 should have no members"
    assert len(mock_repo.members["org_3"]) == 1, "org_3 should still have 1 member"
    assert mock_repo.members["org_3"][0].user_id == "user_789", "user_789 should remain in org_3"

    print("✅ TEST PASSED: user.deleted event handled correctly")
    print(f"   User removed from 3 organizations")
    return True


async def test_user_deleted_event_no_memberships():
    """Test that user.deleted event handles user with no memberships gracefully"""
    print("\n" + "="*80)
    print("TEST: Handle user.deleted Event (No Memberships)")
    print("="*80)

    # Setup
    mock_repo = MockOrganizationRepository()
    event_handler = OrganizationEventHandler(mock_repo)

    # Prepare test data - user is not a member of any organization
    mock_repo.members = {
        "org_1": [
            SimpleMember("user_456", "admin")
        ]
    }

    # Create user.deleted event
    event_data = {
        "event_type": "user.deleted",
        "user_id": "user_999",  # User not in any organization
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Handle event (should not crash)
    await event_handler.handle_user_deleted(event_data)

    # Verify no changes to existing organizations
    assert len(mock_repo.members["org_1"]) == 1, "org_1 should still have 1 member"
    assert mock_repo.members["org_1"][0].user_id == "user_456", "user_456 should remain"

    print("✅ TEST PASSED: user.deleted event handled gracefully for user with no memberships")
    return True


async def run_all_tests():
    """Run all event subscription tests"""
    print("\n" + "="*80)
    print("ORGANIZATION SERVICE EVENT SUBSCRIPTION TESTS")
    print("="*80)

    tests = [
        ("user.deleted Handler", test_user_deleted_event),
        ("user.deleted Handler (No Memberships)", test_user_deleted_event_no_memberships)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, "PASSED", None))
        except Exception as e:
            results.append((test_name, "FAILED", str(e)))
            print(f"❌ TEST FAILED: {test_name}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for _, status, _ in results if status == "PASSED")
    failed = sum(1 for _, status, _ in results if status == "FAILED")

    for test_name, status, error in results:
        symbol = "✅" if status == "PASSED" else "❌"
        print(f"{symbol} {test_name}: {status}")
        if error:
            print(f"   Error: {error}")

    print(f"\nTotal: {len(results)} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed == 0:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n❌ {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
