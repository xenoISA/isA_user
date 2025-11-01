"""
Invitation Service Event Publishing Tests

Tests that Invitation Service correctly publishes events for all invitation operations
"""
import asyncio
import sys
import os
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from core.nats_client import Event, EventType, ServiceSource
from microservices.invitation_service.invitation_service import InvitationService
from microservices.invitation_service.models import (
    InvitationStatus, OrganizationRole, InvitationResponse
)


class MockEventBus:
    """Mock event bus for testing"""

    def __init__(self):
        self.published_events = []

    async def publish_event(self, event: Event):
        """Mock publish event"""
        self.published_events.append(event)
        print(f"✅ Event captured: {event.type}")
        print(f"   Data: {event.data}")


class MockInvitationRepository:
    """Mock Invitation Repository for testing"""

    def __init__(self):
        self.invitations = {}

    async def create_invitation(self, organization_id, email, role, invited_by):
        """Mock create invitation"""
        invitation = InvitationResponse(
            invitation_id="inv_123",
            organization_id=organization_id,
            email=email,
            role=role,
            status=InvitationStatus.PENDING,
            invited_by=invited_by,
            invitation_token="token_abc123",
            expires_at=datetime.now(timezone.utc),
            accepted_at=None,
            created_at=datetime.now(timezone.utc),
            updated_at=None
        )
        self.invitations[invitation.invitation_id] = invitation
        return invitation

    async def get_pending_invitation_by_email_and_organization(self, email, organization_id):
        """Mock get pending invitation"""
        return None

    async def get_invitation_by_token(self, token):
        """Mock get invitation by token"""
        # Return a mock invitation
        class MockInvitation:
            def __init__(self):
                self.invitation_id = "inv_123"
                self.organization_id = "org_456"
                self.email = "user@example.com"
                self.role = OrganizationRole.MEMBER
                self.status = InvitationStatus.PENDING
                self.invited_by = "user_789"
        return MockInvitation()

    async def get_invitation_with_organization_info(self, token):
        """Mock get invitation with org info"""
        from datetime import timedelta
        # Return invitation that expires in future (not expired)
        future_time = datetime.now(timezone.utc) + timedelta(days=7)
        return {
            'invitation_id': 'inv_123',
            'organization_id': 'org_456',
            'organization_name': 'Test Org',
            'email': 'user@example.com',
            'role': 'member',
            'status': 'pending',
            'invited_by': 'user_789',
            'expires_at': future_time.isoformat(),
            'created_at': datetime.now(timezone.utc).isoformat()
        }

    async def accept_invitation(self, token):
        """Mock accept invitation"""
        return True

    async def get_invitation_by_id(self, invitation_id):
        """Mock get invitation by id"""
        class MockInvitation:
            def __init__(self):
                self.invitation_id = invitation_id
                self.organization_id = "org_456"
                self.email = "user@example.com"
                self.role = OrganizationRole.MEMBER
                self.status = InvitationStatus.PENDING
                self.invited_by = "user_789"
        return MockInvitation()

    async def cancel_invitation(self, invitation_id):
        """Mock cancel invitation"""
        return True

    async def update_invitation(self, invitation_id, data):
        """Mock update invitation"""
        return True


async def test_invitation_sent_event():
    """Test that invitation.sent event is published when creating an invitation"""
    print("\n" + "="*80)
    print("TEST: Invitation Sent Event Publishing")
    print("="*80)

    # Setup
    mock_event_bus = MockEventBus()
    invitation_service = InvitationService(event_bus=mock_event_bus)
    invitation_service.repository = MockInvitationRepository()

    # Mock the validation methods
    async def mock_verify_org(*args, **kwargs):
        return True
    async def mock_verify_perms(*args, **kwargs):
        return True
    async def mock_check_membership(*args, **kwargs):
        return False
    async def mock_send_email(*args, **kwargs):
        return True

    invitation_service._verify_organization_exists = mock_verify_org
    invitation_service._verify_inviter_permissions = mock_verify_perms
    invitation_service._check_user_membership = mock_check_membership
    invitation_service._send_invitation_email = mock_send_email

    # Create invitation
    success, invitation, message = await invitation_service.create_invitation(
        organization_id="org_456",
        inviter_user_id="user_789",
        email="newuser@example.com",
        role=OrganizationRole.MEMBER,
        message="Join our team!"
    )

    # Verify event was published
    assert success is True, "Invitation creation should succeed"
    assert len(mock_event_bus.published_events) == 1, "Expected 1 event to be published"

    event = mock_event_bus.published_events[0]
    assert event.type == EventType.INVITATION_SENT.value, f"Expected {EventType.INVITATION_SENT.value}"
    assert event.source == ServiceSource.INVITATION_SERVICE.value
    assert event.data["organization_id"] == "org_456"
    assert event.data["email"] == "newuser@example.com"
    assert event.data["role"] == OrganizationRole.MEMBER.value

    print("✅ TEST PASSED: invitation.sent event published correctly")
    return True


async def test_invitation_accepted_event():
    """Test that invitation.accepted event is published when accepting an invitation"""
    print("\n" + "="*80)
    print("TEST: Invitation Accepted Event Publishing")
    print("="*80)

    # Setup
    mock_event_bus = MockEventBus()
    invitation_service = InvitationService(event_bus=mock_event_bus)
    invitation_service.repository = MockInvitationRepository()

    # Mock the validation methods
    async def mock_verify_email(*args, **kwargs):
        return True
    async def mock_add_to_org(*args, **kwargs):
        return True

    invitation_service._verify_user_email_match = mock_verify_email
    invitation_service._add_user_to_organization = mock_add_to_org

    # Accept invitation
    success, accept_response, message = await invitation_service.accept_invitation(
        invitation_token="token_abc123",
        user_id="user_123"
    )

    # Verify event was published
    assert success is True, "Invitation acceptance should succeed"
    assert len(mock_event_bus.published_events) == 1, "Expected 1 event to be published"

    event = mock_event_bus.published_events[0]
    assert event.type == EventType.INVITATION_ACCEPTED.value
    assert event.source == ServiceSource.INVITATION_SERVICE.value
    assert event.data["user_id"] == "user_123"
    assert "organization_id" in event.data

    print("✅ TEST PASSED: invitation.accepted event published correctly")
    return True


async def test_invitation_expired_event():
    """Test that invitation.expired event is published when invitation expires"""
    print("\n" + "="*80)
    print("TEST: Invitation Expired Event Publishing")
    print("="*80)

    # Setup
    mock_event_bus = MockEventBus()
    invitation_service = InvitationService(event_bus=mock_event_bus)

    # Mock repository with expired invitation
    class ExpiredInvitationRepo(MockInvitationRepository):
        async def get_invitation_with_organization_info(self, token):
            # Return an expired invitation
            from datetime import timedelta
            expired_time = datetime.now(timezone.utc) - timedelta(days=10)
            return {
                'invitation_id': 'inv_expired',
                'organization_id': 'org_456',
                'organization_name': 'Test Org',
                'email': 'expired@example.com',
                'role': 'member',
                'status': 'pending',
                'invited_by': 'user_789',
                'expires_at': expired_time.isoformat(),
                'created_at': datetime.now(timezone.utc).isoformat()
            }

    invitation_service.repository = ExpiredInvitationRepo()

    # Try to get expired invitation
    success, invitation_detail, message = await invitation_service.get_invitation_by_token("token_expired")

    # Verify event was published
    assert success is False, "Getting expired invitation should fail"
    assert "expired" in message.lower(), "Message should indicate expiration"
    assert len(mock_event_bus.published_events) == 1, "Expected 1 event to be published"

    event = mock_event_bus.published_events[0]
    assert event.type == EventType.INVITATION_EXPIRED.value
    assert event.source == ServiceSource.INVITATION_SERVICE.value
    assert event.data["invitation_id"] == "inv_expired"
    assert event.data["email"] == "expired@example.com"

    print("✅ TEST PASSED: invitation.expired event published correctly")
    return True


async def test_invitation_cancelled_event():
    """Test that invitation.cancelled event is published when cancelling an invitation"""
    print("\n" + "="*80)
    print("TEST: Invitation Cancelled Event Publishing")
    print("="*80)

    # Setup
    mock_event_bus = MockEventBus()
    invitation_service = InvitationService(event_bus=mock_event_bus)
    invitation_service.repository = MockInvitationRepository()

    # Mock the verification method
    async def mock_verify_perms(*args, **kwargs):
        return True

    invitation_service._verify_inviter_permissions = mock_verify_perms

    # Cancel invitation
    success, message = await invitation_service.cancel_invitation(
        invitation_id="inv_123",
        user_id="user_789"
    )

    # Verify event was published
    assert success is True, "Invitation cancellation should succeed"
    assert len(mock_event_bus.published_events) == 1, "Expected 1 event to be published"

    event = mock_event_bus.published_events[0]
    assert event.type == EventType.INVITATION_CANCELLED.value
    assert event.source == ServiceSource.INVITATION_SERVICE.value
    assert event.data["invitation_id"] == "inv_123"
    assert event.data["cancelled_by"] == "user_789"

    print("✅ TEST PASSED: invitation.cancelled event published correctly")
    return True


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("INVITATION SERVICE EVENT PUBLISHING TEST SUITE")
    print("="*80)

    tests = [
        ("Invitation Sent Event", test_invitation_sent_event),
        ("Invitation Accepted Event", test_invitation_accepted_event),
        ("Invitation Expired Event", test_invitation_expired_event),
        ("Invitation Cancelled Event", test_invitation_cancelled_event),
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
