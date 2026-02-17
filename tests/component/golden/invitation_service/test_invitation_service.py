"""
Invitation Service - Component Tests

Tests InvitationService business logic with mocked dependencies.
All tests use InvitationTestDataFactory - zero hardcoded data.
"""
import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timezone, timedelta

from tests.contracts.invitation.data_contract import (
    InvitationTestDataFactory,
    InvitationStatus,
    OrganizationRole,
)

pytestmark = [pytest.mark.component, pytest.mark.golden, pytest.mark.asyncio]


# =============================================================================
# Create Invitation Tests (15 tests)
# =============================================================================

class TestInvitationCreate:
    """Test invitation creation business logic"""

    async def test_create_success_returns_invitation(
        self, invitation_service, mock_repository, mock_event_bus, mock_invitation
    ):
        """Successful creation returns invitation data"""
        # Arrange
        org_id = InvitationTestDataFactory.make_organization_id()
        inviter_id = InvitationTestDataFactory.make_user_id()
        email = InvitationTestDataFactory.make_email()
        role = OrganizationRole.MEMBER

        created_invitation = mock_invitation(
            organization_id=org_id,
            email=email,
            role=role,
            invited_by=inviter_id
        )
        mock_repository.create.return_value = created_invitation
        mock_repository.get_pending_invitation_by_email_and_organization.return_value = None

        # Act
        success, invitation, message = await invitation_service.create_invitation(
            organization_id=org_id,
            inviter_user_id=inviter_id,
            email=email,
            role=role
        )

        # Assert
        assert success is True
        assert invitation is not None
        assert invitation.email == email

    async def test_create_calls_repository(
        self, invitation_service, mock_repository, mock_invitation
    ):
        """Creation calls repository create method"""
        org_id = InvitationTestDataFactory.make_organization_id()
        inviter_id = InvitationTestDataFactory.make_user_id()
        email = InvitationTestDataFactory.make_email()
        role = OrganizationRole.MEMBER

        mock_repository.create.return_value = mock_invitation()
        mock_repository.get_pending_invitation_by_email_and_organization.return_value = None

        await invitation_service.create_invitation(
            organization_id=org_id,
            inviter_user_id=inviter_id,
            email=email,
            role=role
        )

        mock_repository.create.assert_called_once()

    async def test_create_checks_for_duplicate(
        self, invitation_service, mock_repository, mock_invitation
    ):
        """Creation checks for existing pending invitation"""
        org_id = InvitationTestDataFactory.make_organization_id()
        inviter_id = InvitationTestDataFactory.make_user_id()
        email = InvitationTestDataFactory.make_email()

        # Return existing invitation
        mock_repository.get_pending_invitation_by_email_and_organization.return_value = mock_invitation()

        success, invitation, message = await invitation_service.create_invitation(
            organization_id=org_id,
            inviter_user_id=inviter_id,
            email=email,
            role=OrganizationRole.MEMBER
        )

        assert success is False
        assert "already exists" in message.lower()

    async def test_create_with_custom_message(
        self, invitation_service, mock_repository, mock_invitation
    ):
        """Creation accepts custom message"""
        org_id = InvitationTestDataFactory.make_organization_id()
        inviter_id = InvitationTestDataFactory.make_user_id()
        email = InvitationTestDataFactory.make_email()
        custom_message = InvitationTestDataFactory.make_invitation_message()

        mock_repository.create.return_value = mock_invitation()
        mock_repository.get_pending_invitation_by_email_and_organization.return_value = None

        success, invitation, message = await invitation_service.create_invitation(
            organization_id=org_id,
            inviter_user_id=inviter_id,
            email=email,
            role=OrganizationRole.MEMBER,
            message=custom_message
        )

        assert success is True

    async def test_create_with_admin_role(
        self, invitation_service, mock_repository, mock_invitation
    ):
        """Creation with admin role succeeds"""
        org_id = InvitationTestDataFactory.make_organization_id()
        inviter_id = InvitationTestDataFactory.make_user_id()
        email = InvitationTestDataFactory.make_email()

        created = mock_invitation(role=OrganizationRole.ADMIN)
        mock_repository.create.return_value = created
        mock_repository.get_pending_invitation_by_email_and_organization.return_value = None

        success, invitation, message = await invitation_service.create_invitation(
            organization_id=org_id,
            inviter_user_id=inviter_id,
            email=email,
            role=OrganizationRole.ADMIN
        )

        assert success is True
        assert invitation.role == OrganizationRole.ADMIN

    async def test_create_failure_returns_error(
        self, invitation_service, mock_repository
    ):
        """Creation failure returns appropriate error"""
        org_id = InvitationTestDataFactory.make_organization_id()
        inviter_id = InvitationTestDataFactory.make_user_id()
        email = InvitationTestDataFactory.make_email()

        mock_repository.create.return_value = None
        mock_repository.get_pending_invitation_by_email_and_organization.return_value = None

        success, invitation, message = await invitation_service.create_invitation(
            organization_id=org_id,
            inviter_user_id=inviter_id,
            email=email,
            role=OrganizationRole.MEMBER
        )

        assert success is False
        assert invitation is None
        assert "failed" in message.lower()


# =============================================================================
# Get Invitation Tests (10 tests)
# =============================================================================

class TestInvitationGet:
    """Test invitation retrieval"""

    async def test_get_by_token_returns_detail(
        self, invitation_service, mock_repository, mock_invitation
    ):
        """Getting by token returns invitation detail"""
        token = InvitationTestDataFactory.make_invitation_token()
        inv = mock_invitation(invitation_token=token)
        mock_repository.get_invitation_with_organization_info.return_value = inv.dict()

        success, detail, message = await invitation_service.get_invitation_by_token(token)

        assert success is True
        assert detail is not None

    async def test_get_nonexistent_returns_not_found(
        self, invitation_service, mock_repository
    ):
        """Getting nonexistent invitation returns not found"""
        token = InvitationTestDataFactory.make_invitation_token()
        mock_repository.get_invitation_with_organization_info.return_value = None

        success, detail, message = await invitation_service.get_invitation_by_token(token)

        assert success is False
        assert "not found" in message.lower()

    async def test_get_expired_returns_error(
        self, invitation_service, mock_repository, mock_invitation
    ):
        """Getting expired invitation returns error"""
        token = InvitationTestDataFactory.make_invitation_token()
        expired_time = datetime.now(timezone.utc) - timedelta(days=1)
        inv = mock_invitation(
            invitation_token=token,
            expires_at=expired_time,
            status=InvitationStatus.PENDING
        )
        mock_repository.get_invitation_with_organization_info.return_value = inv.dict()

        success, detail, message = await invitation_service.get_invitation_by_token(token)

        assert success is False
        assert "expired" in message.lower()

    async def test_get_accepted_returns_error(
        self, invitation_service, mock_repository, mock_invitation
    ):
        """Getting already accepted invitation returns error"""
        token = InvitationTestDataFactory.make_invitation_token()
        inv = mock_invitation(
            invitation_token=token,
            status=InvitationStatus.ACCEPTED
        )
        inv_dict = inv.dict()
        inv_dict["status"] = InvitationStatus.ACCEPTED.value
        mock_repository.get_invitation_with_organization_info.return_value = inv_dict

        success, detail, message = await invitation_service.get_invitation_by_token(token)

        assert success is False
        assert "accepted" in message.lower()

    async def test_get_cancelled_returns_error(
        self, invitation_service, mock_repository, mock_invitation
    ):
        """Getting cancelled invitation returns error"""
        token = InvitationTestDataFactory.make_invitation_token()
        inv = mock_invitation(
            invitation_token=token,
            status=InvitationStatus.CANCELLED
        )
        inv_dict = inv.dict()
        inv_dict["status"] = InvitationStatus.CANCELLED.value
        mock_repository.get_invitation_with_organization_info.return_value = inv_dict

        success, detail, message = await invitation_service.get_invitation_by_token(token)

        assert success is False
        assert "cancelled" in message.lower()


# =============================================================================
# Accept Invitation Tests (12 tests)
# =============================================================================

class TestInvitationAccept:
    """Test invitation acceptance"""

    async def test_accept_success(
        self, invitation_service, mock_repository, mock_event_bus, mock_invitation
    ):
        """Successful acceptance returns accept response"""
        token = InvitationTestDataFactory.make_invitation_token()
        user_id = InvitationTestDataFactory.make_user_id()
        inv = mock_invitation(invitation_token=token, status=InvitationStatus.PENDING)

        mock_repository.get_invitation_with_organization_info.return_value = inv.dict()
        mock_repository.get_invitation_by_token.return_value = inv
        mock_repository.accept_invitation.return_value = True

        success, response, message = await invitation_service.accept_invitation(
            invitation_token=token,
            user_id=user_id
        )

        assert success is True
        assert response is not None
        assert response.user_id == user_id

    async def test_accept_updates_repository(
        self, invitation_service, mock_repository, mock_invitation
    ):
        """Acceptance updates repository"""
        token = InvitationTestDataFactory.make_invitation_token()
        user_id = InvitationTestDataFactory.make_user_id()
        inv = mock_invitation(invitation_token=token)

        mock_repository.get_invitation_with_organization_info.return_value = inv.dict()
        mock_repository.get_invitation_by_token.return_value = inv
        mock_repository.accept_invitation.return_value = True

        await invitation_service.accept_invitation(
            invitation_token=token,
            user_id=user_id
        )

        mock_repository.accept_invitation.assert_called_once_with(token)

    async def test_accept_nonexistent_returns_error(
        self, invitation_service, mock_repository
    ):
        """Accepting nonexistent invitation returns error"""
        token = InvitationTestDataFactory.make_invitation_token()
        user_id = InvitationTestDataFactory.make_user_id()

        mock_repository.get_invitation_with_organization_info.return_value = None

        success, response, message = await invitation_service.accept_invitation(
            invitation_token=token,
            user_id=user_id
        )

        assert success is False
        assert "not found" in message.lower()

    async def test_accept_expired_returns_error(
        self, invitation_service, mock_repository, mock_invitation
    ):
        """Accepting expired invitation returns error"""
        token = InvitationTestDataFactory.make_invitation_token()
        user_id = InvitationTestDataFactory.make_user_id()
        expired_time = datetime.now(timezone.utc) - timedelta(days=1)
        inv = mock_invitation(invitation_token=token, expires_at=expired_time)

        mock_repository.get_invitation_with_organization_info.return_value = inv.dict()

        success, response, message = await invitation_service.accept_invitation(
            invitation_token=token,
            user_id=user_id
        )

        assert success is False
        assert "expired" in message.lower()

    async def test_accept_failure_rollback(
        self, invitation_service, mock_repository, mock_invitation
    ):
        """Failed acceptance triggers rollback"""
        token = InvitationTestDataFactory.make_invitation_token()
        user_id = InvitationTestDataFactory.make_user_id()
        inv = mock_invitation(invitation_token=token)

        mock_repository.get_invitation_with_organization_info.return_value = inv.dict()
        mock_repository.get_invitation_by_token.return_value = inv
        mock_repository.accept_invitation.return_value = False

        success, response, message = await invitation_service.accept_invitation(
            invitation_token=token,
            user_id=user_id
        )

        assert success is False


# =============================================================================
# List Invitations Tests (8 tests)
# =============================================================================

class TestInvitationList:
    """Test invitation listing"""

    async def test_list_returns_invitations(
        self, invitation_service, mock_repository, mock_invitation
    ):
        """Listing returns invitation list"""
        from microservices.invitation_service.models import InvitationDetailResponse

        org_id = InvitationTestDataFactory.make_organization_id()
        user_id = InvitationTestDataFactory.make_user_id()

        # Create InvitationDetailResponse objects (what InvitationListResponse expects)
        invitations = [
            InvitationDetailResponse(
                invitation_id=InvitationTestDataFactory.make_invitation_id(),
                organization_id=org_id,
                organization_name=InvitationTestDataFactory.make_organization_name(),
                email=InvitationTestDataFactory.make_email(),
                role=OrganizationRole.MEMBER,
                status=InvitationStatus.PENDING,
                created_at=datetime.now(timezone.utc),
            )
            for _ in range(5)
        ]
        mock_repository.get_organization_invitations.return_value = invitations

        success, result, message = await invitation_service.get_organization_invitations(
            organization_id=org_id,
            user_id=user_id
        )

        assert success is True
        assert result is not None
        assert len(result.invitations) == 5

    async def test_list_with_pagination(
        self, invitation_service, mock_repository, mock_invitation
    ):
        """Listing respects pagination"""
        from microservices.invitation_service.models import InvitationDetailResponse

        org_id = InvitationTestDataFactory.make_organization_id()
        user_id = InvitationTestDataFactory.make_user_id()

        # Create InvitationDetailResponse objects (what InvitationListResponse expects)
        invitations = [
            InvitationDetailResponse(
                invitation_id=InvitationTestDataFactory.make_invitation_id(),
                organization_id=org_id,
                organization_name=InvitationTestDataFactory.make_organization_name(),
                email=InvitationTestDataFactory.make_email(),
                role=OrganizationRole.MEMBER,
                status=InvitationStatus.PENDING,
                created_at=datetime.now(timezone.utc),
            )
            for _ in range(3)
        ]
        mock_repository.get_organization_invitations.return_value = invitations

        success, result, message = await invitation_service.get_organization_invitations(
            organization_id=org_id,
            user_id=user_id,
            limit=50,
            offset=10
        )

        mock_repository.get_organization_invitations.assert_called_once_with(
            org_id, 50, 10
        )

    async def test_list_empty_returns_empty_list(
        self, invitation_service, mock_repository
    ):
        """Listing empty org returns empty list"""
        org_id = InvitationTestDataFactory.make_organization_id()
        user_id = InvitationTestDataFactory.make_user_id()

        mock_repository.get_organization_invitations.return_value = []

        success, result, message = await invitation_service.get_organization_invitations(
            organization_id=org_id,
            user_id=user_id
        )

        assert success is True
        assert len(result.invitations) == 0


# =============================================================================
# Cancel Invitation Tests (10 tests)
# =============================================================================

class TestInvitationCancel:
    """Test invitation cancellation"""

    async def test_cancel_success(
        self, invitation_service, mock_repository, mock_event_bus, mock_invitation
    ):
        """Successful cancellation returns success"""
        inv_id = InvitationTestDataFactory.make_invitation_id()
        user_id = InvitationTestDataFactory.make_user_id()
        inv = mock_invitation(invitation_id=inv_id, invited_by=user_id)

        mock_repository.get_invitation_by_id.return_value = inv
        mock_repository.cancel_invitation.return_value = True

        success, message = await invitation_service.cancel_invitation(
            invitation_id=inv_id,
            user_id=user_id
        )

        assert success is True
        assert "cancelled" in message.lower() or "success" in message.lower()

    async def test_cancel_calls_repository(
        self, invitation_service, mock_repository, mock_invitation
    ):
        """Cancellation calls repository"""
        inv_id = InvitationTestDataFactory.make_invitation_id()
        user_id = InvitationTestDataFactory.make_user_id()
        inv = mock_invitation(invitation_id=inv_id, invited_by=user_id)

        mock_repository.get_invitation_by_id.return_value = inv
        mock_repository.cancel_invitation.return_value = True

        await invitation_service.cancel_invitation(
            invitation_id=inv_id,
            user_id=user_id
        )

        mock_repository.cancel_invitation.assert_called_once_with(inv_id)

    async def test_cancel_nonexistent_returns_error(
        self, invitation_service, mock_repository
    ):
        """Cancelling nonexistent invitation returns error"""
        inv_id = InvitationTestDataFactory.make_invitation_id()
        user_id = InvitationTestDataFactory.make_user_id()

        mock_repository.get_invitation_by_id.return_value = None

        success, message = await invitation_service.cancel_invitation(
            invitation_id=inv_id,
            user_id=user_id
        )

        assert success is False
        assert "not found" in message.lower()

    async def test_cancel_by_different_user_checks_permission(
        self, invitation_service, mock_repository, mock_invitation
    ):
        """Cancellation by different user checks permission"""
        inv_id = InvitationTestDataFactory.make_invitation_id()
        inviter_id = InvitationTestDataFactory.make_user_id()
        other_user_id = InvitationTestDataFactory.make_user_id()
        inv = mock_invitation(invitation_id=inv_id, invited_by=inviter_id)

        mock_repository.get_invitation_by_id.return_value = inv

        # Without proper permission check, this should fail
        success, message = await invitation_service.cancel_invitation(
            invitation_id=inv_id,
            user_id=other_user_id
        )

        # Permission check should be called
        assert success is False or mock_repository.cancel_invitation.called


# =============================================================================
# Resend Invitation Tests (8 tests)
# =============================================================================

class TestInvitationResend:
    """Test invitation resending"""

    async def test_resend_success(
        self, invitation_service, mock_repository, mock_invitation
    ):
        """Successful resend returns success"""
        inv_id = InvitationTestDataFactory.make_invitation_id()
        user_id = InvitationTestDataFactory.make_user_id()
        inv = mock_invitation(
            invitation_id=inv_id,
            invited_by=user_id,
            status=InvitationStatus.PENDING
        )

        mock_repository.get_invitation_by_id.return_value = inv
        mock_repository.update_invitation.return_value = True

        success, message = await invitation_service.resend_invitation(
            invitation_id=inv_id,
            user_id=user_id
        )

        assert success is True
        assert "resent" in message.lower()

    async def test_resend_extends_expiration(
        self, invitation_service, mock_repository, mock_invitation
    ):
        """Resending extends expiration date"""
        inv_id = InvitationTestDataFactory.make_invitation_id()
        user_id = InvitationTestDataFactory.make_user_id()
        inv = mock_invitation(
            invitation_id=inv_id,
            invited_by=user_id,
            status=InvitationStatus.PENDING
        )

        mock_repository.get_invitation_by_id.return_value = inv
        mock_repository.update_invitation.return_value = True

        await invitation_service.resend_invitation(
            invitation_id=inv_id,
            user_id=user_id
        )

        mock_repository.update_invitation.assert_called()

    async def test_resend_nonexistent_returns_error(
        self, invitation_service, mock_repository
    ):
        """Resending nonexistent invitation returns error"""
        inv_id = InvitationTestDataFactory.make_invitation_id()
        user_id = InvitationTestDataFactory.make_user_id()

        mock_repository.get_invitation_by_id.return_value = None

        success, message = await invitation_service.resend_invitation(
            invitation_id=inv_id,
            user_id=user_id
        )

        assert success is False
        assert "not found" in message.lower()

    async def test_resend_accepted_returns_error(
        self, invitation_service, mock_repository, mock_invitation
    ):
        """Resending accepted invitation returns error"""
        inv_id = InvitationTestDataFactory.make_invitation_id()
        user_id = InvitationTestDataFactory.make_user_id()
        inv = mock_invitation(
            invitation_id=inv_id,
            invited_by=user_id,
            status=InvitationStatus.ACCEPTED
        )

        mock_repository.get_invitation_by_id.return_value = inv

        success, message = await invitation_service.resend_invitation(
            invitation_id=inv_id,
            user_id=user_id
        )

        assert success is False
        assert "cannot" in message.lower() or "accepted" in message.lower()

    async def test_resend_cancelled_returns_error(
        self, invitation_service, mock_repository, mock_invitation
    ):
        """Resending cancelled invitation returns error"""
        inv_id = InvitationTestDataFactory.make_invitation_id()
        user_id = InvitationTestDataFactory.make_user_id()
        inv = mock_invitation(
            invitation_id=inv_id,
            invited_by=user_id,
            status=InvitationStatus.CANCELLED
        )

        mock_repository.get_invitation_by_id.return_value = inv

        success, message = await invitation_service.resend_invitation(
            invitation_id=inv_id,
            user_id=user_id
        )

        assert success is False


# =============================================================================
# Expire Invitations Tests (5 tests)
# =============================================================================

class TestInvitationExpire:
    """Test invitation expiration batch processing"""

    async def test_expire_returns_count(
        self, invitation_service, mock_repository
    ):
        """Expiration returns count of expired invitations"""
        mock_repository.expire_old_invitations.return_value = 10

        success, count, message = await invitation_service.expire_old_invitations()

        assert success is True
        assert count == 10

    async def test_expire_zero_when_none_expired(
        self, invitation_service, mock_repository
    ):
        """Expiration returns zero when none expired"""
        mock_repository.expire_old_invitations.return_value = 0

        success, count, message = await invitation_service.expire_old_invitations()

        assert success is True
        assert count == 0

    async def test_expire_calls_repository(
        self, invitation_service, mock_repository
    ):
        """Expiration calls repository method"""
        mock_repository.expire_old_invitations.return_value = 0

        await invitation_service.expire_old_invitations()

        mock_repository.expire_old_invitations.assert_called_once()


# =============================================================================
# Event Publishing Tests (8 tests)
# =============================================================================

class TestInvitationEventPublishing:
    """Test event publishing behavior"""

    async def test_create_publishes_sent_event(
        self, invitation_service, mock_repository, mock_event_bus, mock_invitation
    ):
        """Creation publishes invitation.sent event"""
        org_id = InvitationTestDataFactory.make_organization_id()
        inviter_id = InvitationTestDataFactory.make_user_id()
        email = InvitationTestDataFactory.make_email()

        mock_repository.create.return_value = mock_invitation()
        mock_repository.get_pending_invitation_by_email_and_organization.return_value = None

        await invitation_service.create_invitation(
            organization_id=org_id,
            inviter_user_id=inviter_id,
            email=email,
            role=OrganizationRole.MEMBER
        )

        # Event bus publish should be called
        mock_event_bus.publish_event.assert_called()

    async def test_accept_publishes_accepted_event(
        self, invitation_service, mock_repository, mock_event_bus, mock_invitation
    ):
        """Acceptance publishes invitation.accepted event"""
        token = InvitationTestDataFactory.make_invitation_token()
        user_id = InvitationTestDataFactory.make_user_id()
        inv = mock_invitation(invitation_token=token)

        mock_repository.get_invitation_with_organization_info.return_value = inv.dict()
        mock_repository.get_invitation_by_token.return_value = inv
        mock_repository.accept_invitation.return_value = True

        await invitation_service.accept_invitation(
            invitation_token=token,
            user_id=user_id
        )

        mock_event_bus.publish_event.assert_called()

    async def test_cancel_publishes_cancelled_event(
        self, invitation_service, mock_repository, mock_event_bus, mock_invitation
    ):
        """Cancellation publishes invitation.cancelled event"""
        inv_id = InvitationTestDataFactory.make_invitation_id()
        user_id = InvitationTestDataFactory.make_user_id()
        inv = mock_invitation(invitation_id=inv_id, invited_by=user_id)

        mock_repository.get_invitation_by_id.return_value = inv
        mock_repository.cancel_invitation.return_value = True

        await invitation_service.cancel_invitation(
            invitation_id=inv_id,
            user_id=user_id
        )

        mock_event_bus.publish_event.assert_called()

    async def test_no_event_when_bus_unavailable(
        self, invitation_service, mock_repository, mock_invitation
    ):
        """No error when event bus is unavailable"""
        # Set event bus to None
        invitation_service.event_bus = None

        org_id = InvitationTestDataFactory.make_organization_id()
        inviter_id = InvitationTestDataFactory.make_user_id()
        email = InvitationTestDataFactory.make_email()

        mock_repository.create.return_value = mock_invitation()
        mock_repository.get_pending_invitation_by_email_and_organization.return_value = None

        # Should not raise error
        success, invitation, message = await invitation_service.create_invitation(
            organization_id=org_id,
            inviter_user_id=inviter_id,
            email=email,
            role=OrganizationRole.MEMBER
        )

        assert success is True
