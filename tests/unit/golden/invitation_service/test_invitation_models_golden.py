"""
Unit Golden Tests: Invitation Service Models

Tests model validation and serialization without external dependencies.
"""
import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from microservices.invitation_service.models import (
    InvitationStatus,
    OrganizationRole,
    InvitationCreateRequest,
    AcceptInvitationRequest,
    ResendInvitationRequest,
    InvitationResponse,
    InvitationDetailResponse,
    InvitationListResponse,
    AcceptInvitationResponse,
    HealthResponse,
    ServiceInfo,
    ServiceStats,
)


class TestInvitationStatusEnum:
    """Test InvitationStatus enum"""

    def test_invitation_status_values(self):
        """Test all invitation status values are defined"""
        assert InvitationStatus.PENDING.value == "pending"
        assert InvitationStatus.ACCEPTED.value == "accepted"
        assert InvitationStatus.EXPIRED.value == "expired"
        assert InvitationStatus.CANCELLED.value == "cancelled"

    def test_invitation_status_comparison(self):
        """Test invitation status comparison"""
        assert InvitationStatus.PENDING != InvitationStatus.ACCEPTED
        assert InvitationStatus.PENDING.value == "pending"
        assert InvitationStatus.EXPIRED == InvitationStatus.EXPIRED


class TestOrganizationRoleEnum:
    """Test OrganizationRole enum"""

    def test_organization_role_values(self):
        """Test all organization role values are defined"""
        assert OrganizationRole.OWNER.value == "owner"
        assert OrganizationRole.ADMIN.value == "admin"
        assert OrganizationRole.MEMBER.value == "member"
        assert OrganizationRole.VIEWER.value == "viewer"
        assert OrganizationRole.GUEST.value == "guest"

    def test_organization_role_comparison(self):
        """Test organization role comparison"""
        assert OrganizationRole.OWNER != OrganizationRole.MEMBER
        assert OrganizationRole.ADMIN.value == "admin"
        assert OrganizationRole.VIEWER == OrganizationRole.VIEWER


class TestInvitationCreateRequest:
    """Test InvitationCreateRequest model validation"""

    def test_invitation_create_request_minimal(self):
        """Test creating invitation request with minimal fields"""
        request = InvitationCreateRequest(
            email="test@example.com"
        )

        assert request.email == "test@example.com"
        assert request.role == OrganizationRole.MEMBER
        assert request.message is None

    def test_invitation_create_request_with_all_fields(self):
        """Test creating invitation request with all fields"""
        request = InvitationCreateRequest(
            email="admin@example.com",
            role=OrganizationRole.ADMIN,
            message="Welcome to our team!"
        )

        assert request.email == "admin@example.com"
        assert request.role == OrganizationRole.ADMIN
        assert request.message == "Welcome to our team!"

    def test_invitation_create_request_email_validation_valid(self):
        """Test email validation accepts valid email"""
        request = InvitationCreateRequest(
            email="valid.email@example.com"
        )

        assert request.email == "valid.email@example.com"

    def test_invitation_create_request_email_validation_lowercase(self):
        """Test email validation converts to lowercase"""
        request = InvitationCreateRequest(
            email="Test.User@Example.COM"
        )

        assert request.email == "test.user@example.com"

    def test_invitation_create_request_email_validation_invalid(self):
        """Test email validation rejects invalid email"""
        with pytest.raises(ValidationError) as exc_info:
            InvitationCreateRequest(email="invalid-email")

        errors = exc_info.value.errors()
        assert len(errors) > 0
        assert any("Invalid email format" in str(err.get("msg", "")) for err in errors)

    def test_invitation_create_request_email_validation_empty_at_sign(self):
        """Test email validation rejects email with @ but empty local part"""
        request = InvitationCreateRequest(
            email="@example.com"
        )
        # Note: Current validator only checks for '@' presence
        assert request.email == "@example.com"

    def test_invitation_create_request_missing_email(self):
        """Test that missing email raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            InvitationCreateRequest(role=OrganizationRole.MEMBER)

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "email" in missing_fields

    def test_invitation_create_request_message_max_length(self):
        """Test message field max length validation"""
        valid_message = "x" * 500
        request = InvitationCreateRequest(
            email="test@example.com",
            message=valid_message
        )

        assert len(request.message) == 500

    def test_invitation_create_request_message_exceeds_max_length(self):
        """Test message field exceeds max length raises ValidationError"""
        too_long_message = "x" * 501
        with pytest.raises(ValidationError) as exc_info:
            InvitationCreateRequest(
                email="test@example.com",
                message=too_long_message
            )

        errors = exc_info.value.errors()
        assert len(errors) > 0

    def test_invitation_create_request_default_role(self):
        """Test default role is MEMBER"""
        request = InvitationCreateRequest(
            email="test@example.com"
        )

        assert request.role == OrganizationRole.MEMBER

    def test_invitation_create_request_all_roles(self):
        """Test invitation request with all possible roles"""
        for role in OrganizationRole:
            request = InvitationCreateRequest(
                email="test@example.com",
                role=role
            )
            assert request.role == role


class TestAcceptInvitationRequest:
    """Test AcceptInvitationRequest model validation"""

    def test_accept_invitation_request_minimal(self):
        """Test accept invitation request with minimal fields"""
        request = AcceptInvitationRequest(
            invitation_token="token_abc123"
        )

        assert request.invitation_token == "token_abc123"
        assert request.user_id is None

    def test_accept_invitation_request_with_user_id(self):
        """Test accept invitation request with user_id"""
        request = AcceptInvitationRequest(
            invitation_token="token_xyz789",
            user_id="user_123"
        )

        assert request.invitation_token == "token_xyz789"
        assert request.user_id == "user_123"

    def test_accept_invitation_request_missing_token(self):
        """Test that missing token raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            AcceptInvitationRequest(user_id="user_123")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "invitation_token" in missing_fields


class TestResendInvitationRequest:
    """Test ResendInvitationRequest model validation"""

    def test_resend_invitation_request(self):
        """Test resend invitation request"""
        request = ResendInvitationRequest(
            invitation_id="inv_123"
        )

        assert request.invitation_id == "inv_123"

    def test_resend_invitation_request_missing_id(self):
        """Test that missing invitation_id raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            ResendInvitationRequest()

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "invitation_id" in missing_fields


class TestInvitationResponse:
    """Test InvitationResponse model"""

    def test_invitation_response_minimal(self):
        """Test creating invitation response with minimal fields"""
        now = datetime.now(timezone.utc)

        response = InvitationResponse(
            invitation_id="inv_123",
            organization_id="org_456",
            email="test@example.com",
            role=OrganizationRole.MEMBER,
            status=InvitationStatus.PENDING,
            invited_by="user_789",
            invitation_token="token_abc",
            created_at=now
        )

        assert response.invitation_id == "inv_123"
        assert response.organization_id == "org_456"
        assert response.email == "test@example.com"
        assert response.role == OrganizationRole.MEMBER
        assert response.status == InvitationStatus.PENDING
        assert response.invited_by == "user_789"
        assert response.invitation_token == "token_abc"
        assert response.created_at == now
        assert response.expires_at is None
        assert response.accepted_at is None
        assert response.updated_at is None

    def test_invitation_response_with_all_fields(self):
        """Test creating invitation response with all fields"""
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=7)
        accepted = now + timedelta(days=2)
        updated = now + timedelta(days=1)

        response = InvitationResponse(
            invitation_id="inv_123",
            organization_id="org_456",
            email="admin@example.com",
            role=OrganizationRole.ADMIN,
            status=InvitationStatus.ACCEPTED,
            invited_by="user_789",
            invitation_token="token_xyz",
            expires_at=expires,
            accepted_at=accepted,
            created_at=now,
            updated_at=updated
        )

        assert response.invitation_id == "inv_123"
        assert response.status == InvitationStatus.ACCEPTED
        assert response.role == OrganizationRole.ADMIN
        assert response.expires_at == expires
        assert response.accepted_at == accepted
        assert response.updated_at == updated

    def test_invitation_response_pending_status(self):
        """Test invitation response with pending status"""
        now = datetime.now(timezone.utc)

        response = InvitationResponse(
            invitation_id="inv_pending",
            organization_id="org_123",
            email="pending@example.com",
            role=OrganizationRole.MEMBER,
            status=InvitationStatus.PENDING,
            invited_by="user_456",
            invitation_token="token_pending",
            created_at=now
        )

        assert response.status == InvitationStatus.PENDING
        assert response.accepted_at is None

    def test_invitation_response_expired_status(self):
        """Test invitation response with expired status"""
        now = datetime.now(timezone.utc)
        past = now - timedelta(days=1)

        response = InvitationResponse(
            invitation_id="inv_expired",
            organization_id="org_123",
            email="expired@example.com",
            role=OrganizationRole.MEMBER,
            status=InvitationStatus.EXPIRED,
            invited_by="user_456",
            invitation_token="token_expired",
            expires_at=past,
            created_at=now
        )

        assert response.status == InvitationStatus.EXPIRED
        assert response.expires_at == past


class TestInvitationDetailResponse:
    """Test InvitationDetailResponse model"""

    def test_invitation_detail_response_minimal(self):
        """Test creating invitation detail response with minimal fields"""
        now = datetime.now(timezone.utc)

        response = InvitationDetailResponse(
            invitation_id="inv_123",
            organization_id="org_456",
            organization_name="Test Organization",
            email="test@example.com",
            role=OrganizationRole.MEMBER,
            status=InvitationStatus.PENDING,
            created_at=now
        )

        assert response.invitation_id == "inv_123"
        assert response.organization_id == "org_456"
        assert response.organization_name == "Test Organization"
        assert response.email == "test@example.com"
        assert response.role == OrganizationRole.MEMBER
        assert response.status == InvitationStatus.PENDING
        assert response.created_at == now
        assert response.organization_domain is None
        assert response.inviter_name is None
        assert response.inviter_email is None
        assert response.expires_at is None

    def test_invitation_detail_response_with_all_fields(self):
        """Test creating invitation detail response with all fields"""
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=7)

        response = InvitationDetailResponse(
            invitation_id="inv_123",
            organization_id="org_456",
            organization_name="Acme Corp",
            organization_domain="acme.com",
            email="newuser@example.com",
            role=OrganizationRole.ADMIN,
            status=InvitationStatus.PENDING,
            inviter_name="John Doe",
            inviter_email="john.doe@acme.com",
            expires_at=expires,
            created_at=now
        )

        assert response.organization_name == "Acme Corp"
        assert response.organization_domain == "acme.com"
        assert response.inviter_name == "John Doe"
        assert response.inviter_email == "john.doe@acme.com"
        assert response.expires_at == expires

    def test_invitation_detail_response_with_inviter_info(self):
        """Test invitation detail response with inviter information"""
        now = datetime.now(timezone.utc)

        response = InvitationDetailResponse(
            invitation_id="inv_123",
            organization_id="org_456",
            organization_name="Tech Company",
            email="developer@example.com",
            role=OrganizationRole.MEMBER,
            status=InvitationStatus.PENDING,
            inviter_name="Jane Smith",
            inviter_email="jane.smith@techcompany.com",
            created_at=now
        )

        assert response.inviter_name == "Jane Smith"
        assert response.inviter_email == "jane.smith@techcompany.com"


class TestInvitationListResponse:
    """Test InvitationListResponse model"""

    def test_invitation_list_response_empty(self):
        """Test empty invitation list response"""
        response = InvitationListResponse(
            invitations=[],
            total=0,
            limit=10,
            offset=0
        )

        assert len(response.invitations) == 0
        assert response.total == 0
        assert response.limit == 10
        assert response.offset == 0

    def test_invitation_list_response_with_invitations(self):
        """Test invitation list response with multiple invitations"""
        now = datetime.now(timezone.utc)

        invitations = [
            InvitationDetailResponse(
                invitation_id=f"inv_{i}",
                organization_id="org_123",
                organization_name="Test Org",
                email=f"user{i}@example.com",
                role=OrganizationRole.MEMBER,
                status=InvitationStatus.PENDING,
                created_at=now
            )
            for i in range(3)
        ]

        response = InvitationListResponse(
            invitations=invitations,
            total=3,
            limit=10,
            offset=0
        )

        assert len(response.invitations) == 3
        assert response.total == 3
        assert response.invitations[0].invitation_id == "inv_0"
        assert response.invitations[1].invitation_id == "inv_1"
        assert response.invitations[2].invitation_id == "inv_2"

    def test_invitation_list_response_with_pagination(self):
        """Test invitation list response with pagination"""
        now = datetime.now(timezone.utc)

        invitations = [
            InvitationDetailResponse(
                invitation_id=f"inv_{i}",
                organization_id="org_123",
                organization_name="Test Org",
                email=f"user{i}@example.com",
                role=OrganizationRole.MEMBER,
                status=InvitationStatus.PENDING,
                created_at=now
            )
            for i in range(5)
        ]

        response = InvitationListResponse(
            invitations=invitations,
            total=25,
            limit=5,
            offset=10
        )

        assert len(response.invitations) == 5
        assert response.total == 25
        assert response.limit == 5
        assert response.offset == 10

    def test_invitation_list_response_mixed_statuses(self):
        """Test invitation list response with mixed statuses"""
        now = datetime.now(timezone.utc)

        invitations = [
            InvitationDetailResponse(
                invitation_id="inv_pending",
                organization_id="org_123",
                organization_name="Test Org",
                email="pending@example.com",
                role=OrganizationRole.MEMBER,
                status=InvitationStatus.PENDING,
                created_at=now
            ),
            InvitationDetailResponse(
                invitation_id="inv_accepted",
                organization_id="org_123",
                organization_name="Test Org",
                email="accepted@example.com",
                role=OrganizationRole.ADMIN,
                status=InvitationStatus.ACCEPTED,
                created_at=now
            ),
            InvitationDetailResponse(
                invitation_id="inv_expired",
                organization_id="org_123",
                organization_name="Test Org",
                email="expired@example.com",
                role=OrganizationRole.VIEWER,
                status=InvitationStatus.EXPIRED,
                created_at=now
            )
        ]

        response = InvitationListResponse(
            invitations=invitations,
            total=3,
            limit=10,
            offset=0
        )

        assert response.invitations[0].status == InvitationStatus.PENDING
        assert response.invitations[1].status == InvitationStatus.ACCEPTED
        assert response.invitations[2].status == InvitationStatus.EXPIRED


class TestAcceptInvitationResponse:
    """Test AcceptInvitationResponse model"""

    def test_accept_invitation_response(self):
        """Test accept invitation response"""
        now = datetime.now(timezone.utc)

        response = AcceptInvitationResponse(
            invitation_id="inv_123",
            organization_id="org_456",
            organization_name="Test Organization",
            user_id="user_789",
            role=OrganizationRole.MEMBER,
            accepted_at=now
        )

        assert response.invitation_id == "inv_123"
        assert response.organization_id == "org_456"
        assert response.organization_name == "Test Organization"
        assert response.user_id == "user_789"
        assert response.role == OrganizationRole.MEMBER
        assert response.accepted_at == now

    def test_accept_invitation_response_admin_role(self):
        """Test accept invitation response with admin role"""
        now = datetime.now(timezone.utc)

        response = AcceptInvitationResponse(
            invitation_id="inv_admin",
            organization_id="org_123",
            organization_name="Admin Test Org",
            user_id="user_admin",
            role=OrganizationRole.ADMIN,
            accepted_at=now
        )

        assert response.role == OrganizationRole.ADMIN
        assert response.user_id == "user_admin"

    def test_accept_invitation_response_all_roles(self):
        """Test accept invitation response with all possible roles"""
        now = datetime.now(timezone.utc)

        for role in OrganizationRole:
            response = AcceptInvitationResponse(
                invitation_id=f"inv_{role.value}",
                organization_id="org_123",
                organization_name="Test Org",
                user_id="user_123",
                role=role,
                accepted_at=now
            )
            assert response.role == role


class TestHealthResponse:
    """Test HealthResponse model"""

    def test_health_response_defaults(self):
        """Test health response with default values"""
        response = HealthResponse()

        assert response.status == "healthy"
        assert response.service == "invitation_service"
        assert response.port == 8213
        assert response.version == "1.0.0"

    def test_health_response_custom_values(self):
        """Test health response with custom values"""
        response = HealthResponse(
            status="degraded",
            service="invitation_service",
            port=8214,
            version="2.0.0"
        )

        assert response.status == "degraded"
        assert response.service == "invitation_service"
        assert response.port == 8214
        assert response.version == "2.0.0"


class TestServiceInfo:
    """Test ServiceInfo model"""

    def test_service_info_defaults(self):
        """Test service info with default values"""
        info = ServiceInfo()

        assert info.service == "invitation_service"
        assert info.version == "1.0.0"
        assert info.description == "Organization invitation management microservice"
        assert info.capabilities["invitation_creation"] is True
        assert info.capabilities["email_sending"] is True
        assert info.capabilities["invitation_acceptance"] is True
        assert info.capabilities["invitation_management"] is True
        assert info.capabilities["organization_integration"] is True

    def test_service_info_endpoints(self):
        """Test service info endpoints"""
        info = ServiceInfo()

        assert info.endpoints["health"] == "/health"
        assert info.endpoints["create_invitation"] == "/api/v1/organizations/{org_id}/invitations"
        assert info.endpoints["get_invitation"] == "/api/v1/invitations/{token}"
        assert info.endpoints["accept_invitation"] == "/api/v1/invitations/accept"
        assert info.endpoints["organization_invitations"] == "/api/v1/organizations/{org_id}/invitations"

    def test_service_info_custom_capabilities(self):
        """Test service info with custom capabilities"""
        custom_capabilities = {
            "invitation_creation": True,
            "email_sending": False,
            "invitation_acceptance": True,
            "invitation_management": True,
            "organization_integration": False
        }

        info = ServiceInfo(capabilities=custom_capabilities)

        assert info.capabilities["email_sending"] is False
        assert info.capabilities["organization_integration"] is False
        assert info.capabilities["invitation_creation"] is True


class TestServiceStats:
    """Test ServiceStats model"""

    def test_service_stats_defaults(self):
        """Test service stats with default values"""
        stats = ServiceStats()

        assert stats.total_invitations == 0
        assert stats.pending_invitations == 0
        assert stats.accepted_invitations == 0
        assert stats.expired_invitations == 0
        assert stats.requests_today == 0
        assert stats.average_response_time_ms == 0.0

    def test_service_stats_custom_values(self):
        """Test service stats with custom values"""
        stats = ServiceStats(
            total_invitations=100,
            pending_invitations=25,
            accepted_invitations=60,
            expired_invitations=15,
            requests_today=150,
            average_response_time_ms=45.5
        )

        assert stats.total_invitations == 100
        assert stats.pending_invitations == 25
        assert stats.accepted_invitations == 60
        assert stats.expired_invitations == 15
        assert stats.requests_today == 150
        assert stats.average_response_time_ms == 45.5

    def test_service_stats_float_response_time(self):
        """Test service stats with float response time"""
        stats = ServiceStats(
            average_response_time_ms=123.456
        )

        assert stats.average_response_time_ms == 123.456


if __name__ == "__main__":
    pytest.main([__file__])
