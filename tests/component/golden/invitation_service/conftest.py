"""
Invitation Service - Component Test Configuration

Provides mocked dependencies for testing service business logic.
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone, timedelta

from tests.contracts.invitation.data_contract import (
    InvitationTestDataFactory,
    InvitationStatus,
    OrganizationRole,
)


class MockInvitationRepository:
    """Mock repository for invitation data access"""

    def __init__(self):
        self.invitations = {}
        # Main method name matches actual repository
        self.create_invitation = AsyncMock()
        self.get_invitation_by_id = AsyncMock()
        self.get_invitation_by_token = AsyncMock()
        self.get_invitation_with_organization_info = AsyncMock()
        self.get_pending_invitation_by_email_and_organization = AsyncMock()
        self.get_organization_invitations = AsyncMock()
        self.update_invitation = AsyncMock()
        self.accept_invitation = AsyncMock()
        self.cancel_invitation = AsyncMock()
        self.expire_old_invitations = AsyncMock()
        self.delete_invitation = AsyncMock()
        self.get_invitation_stats = AsyncMock()
        self.cancel_organization_invitations = AsyncMock()
        self.cancel_invitations_by_inviter = AsyncMock()

        # Default return values
        self.create_invitation.return_value = None
        self.get_invitation_by_id.return_value = None
        self.get_invitation_by_token.return_value = None
        self.get_pending_invitation_by_email_and_organization.return_value = None
        self.get_organization_invitations.return_value = []
        self.update_invitation.return_value = True
        self.accept_invitation.return_value = True
        self.cancel_invitation.return_value = True
        self.expire_old_invitations.return_value = 0

        # Alias for backward compatibility with tests
        self.create = self.create_invitation

    def reset_mocks(self):
        """Reset all mocks to default state"""
        self.create_invitation.reset_mock()
        self.get_invitation_by_id.reset_mock()
        self.get_invitation_by_token.reset_mock()
        self.get_invitation_with_organization_info.reset_mock()
        self.get_pending_invitation_by_email_and_organization.reset_mock()
        self.get_organization_invitations.reset_mock()
        self.update_invitation.reset_mock()
        self.accept_invitation.reset_mock()
        self.cancel_invitation.reset_mock()
        self.expire_old_invitations.reset_mock()


class MockEventBus:
    """Mock event bus for NATS publishing"""

    def __init__(self):
        self.publish_event = AsyncMock()
        self.subscribe = AsyncMock()
        self.close = AsyncMock()
        self.published_events = []

    async def publish_event_tracking(self, event):
        """Publish and track events"""
        self.published_events.append(event)
        return await self.publish_event(event)

    def get_published_events(self):
        """Get list of published events"""
        return self.published_events

    def clear_events(self):
        """Clear published events"""
        self.published_events = []

    def reset_mocks(self):
        """Reset all mocks"""
        self.publish_event.reset_mock()
        self.subscribe.reset_mock()
        self.close.reset_mock()
        self.published_events = []


class MockOrganizationClient:
    """Mock client for organization service"""

    def __init__(self):
        self.get_organization_info = AsyncMock()
        self.can_user_invite = AsyncMock()
        self.is_user_member = AsyncMock()
        self.add_member_to_organization = AsyncMock()
        self.close = AsyncMock()

        # Default return values
        self.get_organization_info.return_value = {
            "organization_id": InvitationTestDataFactory.make_organization_id(),
            "name": InvitationTestDataFactory.make_organization_name(),
        }
        self.can_user_invite.return_value = True
        self.is_user_member.return_value = False
        self.add_member_to_organization.return_value = True

    def reset_mocks(self):
        """Reset all mocks"""
        self.get_organization_info.reset_mock()
        self.can_user_invite.reset_mock()
        self.is_user_member.reset_mock()
        self.add_member_to_organization.reset_mock()


class MockInvitationResponse:
    """Mock invitation response object"""

    def __init__(self, **kwargs):
        self.invitation_id = kwargs.get("invitation_id", InvitationTestDataFactory.make_invitation_id())
        self.organization_id = kwargs.get("organization_id", InvitationTestDataFactory.make_organization_id())
        self.email = kwargs.get("email", InvitationTestDataFactory.make_email())
        self.role = kwargs.get("role", OrganizationRole.MEMBER)
        self.status = kwargs.get("status", InvitationStatus.PENDING)
        self.invited_by = kwargs.get("invited_by", InvitationTestDataFactory.make_user_id())
        self.invitation_token = kwargs.get("invitation_token", InvitationTestDataFactory.make_invitation_token())
        self.expires_at = kwargs.get("expires_at", datetime.now(timezone.utc) + timedelta(days=7))
        self.accepted_at = kwargs.get("accepted_at", None)
        self.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
        self.updated_at = kwargs.get("updated_at", datetime.now(timezone.utc))

    def dict(self):
        """Convert to dictionary"""
        return {
            "invitation_id": self.invitation_id,
            "organization_id": self.organization_id,
            "email": self.email,
            "role": self.role.value if hasattr(self.role, 'value') else self.role,
            "status": self.status.value if hasattr(self.status, 'value') else self.status,
            "invited_by": self.invited_by,
            "invitation_token": self.invitation_token,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@pytest.fixture
def mock_repository():
    """Provide mock repository"""
    return MockInvitationRepository()


@pytest.fixture
def mock_event_bus():
    """Provide mock event bus"""
    return MockEventBus()


@pytest.fixture
def mock_organization_client():
    """Provide mock organization client"""
    return MockOrganizationClient()


@pytest.fixture
def mock_invitation():
    """Provide factory for mock invitation responses"""
    def _create(**kwargs):
        return MockInvitationResponse(**kwargs)
    return _create


@pytest_asyncio.fixture
async def invitation_service(mock_repository, mock_event_bus, mock_organization_client):
    """
    Create InvitationService with mocked dependencies.

    Note: Uses the real service class but with mocked repository, event bus,
    and mocked internal helper methods to avoid real HTTP calls.
    """
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../.."))

    from microservices.invitation_service.invitation_service import InvitationService

    service = InvitationService(event_bus=mock_event_bus)
    service.repository = mock_repository

    # Mock internal helper methods that make HTTP calls to external services
    # These methods use httpx.AsyncClient internally, so we mock them directly
    service._verify_organization_exists = AsyncMock(return_value=True)
    service._verify_inviter_permissions = AsyncMock(return_value=True)
    service._check_user_membership = AsyncMock(return_value=False)
    service._verify_user_email_match = AsyncMock(return_value=True)
    service._add_user_to_organization = AsyncMock(return_value=True)
    service._send_invitation_email = AsyncMock(return_value=True)

    return service
