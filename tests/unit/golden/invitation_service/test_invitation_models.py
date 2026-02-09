"""
Invitation Service - Unit Tests: Models & Validation

Tests for:
- Pydantic model validation
- TestDataFactory methods
- Request builders
- Enum validation

No I/O, no mocks, no fixtures needed.
All tests use InvitationTestDataFactory - zero hardcoded data.
"""
import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from tests.contracts.invitation.data_contract import (
    InvitationTestDataFactory,
    InvitationCreateRequestContract,
    InvitationAcceptRequestContract,
    InvitationResendRequestContract,
    InvitationCancelRequestContract,
    InvitationListParamsContract,
    InvitationResponseContract,
    InvitationDetailResponseContract,
    InvitationListResponseContract,
    AcceptInvitationResponseContract,
    InvitationCreateResponseContract,
    InvitationStatsResponseContract,
    ErrorResponseContract,
    InvitationCreateRequestBuilder,
    InvitationAcceptRequestBuilder,
    InvitationListParamsBuilder,
    InvitationStatus,
    OrganizationRole,
)

pytestmark = [pytest.mark.unit, pytest.mark.golden]


# =============================================================================
# TestDataFactory ID Generation Tests (8 tests)
# =============================================================================

class TestInvitationTestDataFactoryIds:
    """Test ID generation methods"""

    def test_make_invitation_id_format(self):
        """make_invitation_id returns correctly formatted ID"""
        invitation_id = InvitationTestDataFactory.make_invitation_id()
        assert invitation_id.startswith("inv_")
        assert len(invitation_id) > 8

    def test_make_invitation_id_uniqueness(self):
        """make_invitation_id generates unique IDs"""
        ids = [InvitationTestDataFactory.make_invitation_id() for _ in range(100)]
        assert len(set(ids)) == 100

    def test_make_organization_id_format(self):
        """make_organization_id returns correctly formatted ID"""
        org_id = InvitationTestDataFactory.make_organization_id()
        assert org_id.startswith("org_")
        assert len(org_id) > 8

    def test_make_organization_id_uniqueness(self):
        """make_organization_id generates unique IDs"""
        ids = [InvitationTestDataFactory.make_organization_id() for _ in range(100)]
        assert len(set(ids)) == 100

    def test_make_user_id_format(self):
        """make_user_id returns correctly formatted ID"""
        user_id = InvitationTestDataFactory.make_user_id()
        assert user_id.startswith("user_")
        assert len(user_id) > 8

    def test_make_user_id_uniqueness(self):
        """make_user_id generates unique IDs"""
        ids = [InvitationTestDataFactory.make_user_id() for _ in range(100)]
        assert len(set(ids)) == 100

    def test_make_uuid_format(self):
        """make_uuid returns valid UUID string"""
        uuid_str = InvitationTestDataFactory.make_uuid()
        assert len(uuid_str) == 36
        assert uuid_str.count('-') == 4

    def test_make_correlation_id_format(self):
        """make_correlation_id returns correctly formatted ID"""
        corr_id = InvitationTestDataFactory.make_correlation_id()
        assert corr_id.startswith("corr_")


# =============================================================================
# TestDataFactory String Generation Tests (8 tests)
# =============================================================================

class TestInvitationTestDataFactoryStrings:
    """Test string generation methods"""

    def test_make_email_valid_format(self):
        """make_email generates valid email format"""
        email = InvitationTestDataFactory.make_email()
        assert "@" in email
        assert "." in email.split("@")[1]

    def test_make_email_uniqueness(self):
        """make_email generates unique emails"""
        emails = [InvitationTestDataFactory.make_email() for _ in range(100)]
        assert len(set(emails)) == 100

    def test_make_email_with_custom_domain(self):
        """make_email accepts custom domain"""
        email = InvitationTestDataFactory.make_email(domain="custom.org")
        assert email.endswith("@custom.org")

    def test_make_organization_name_non_empty(self):
        """make_organization_name generates non-empty names"""
        name = InvitationTestDataFactory.make_organization_name()
        assert len(name) > 0

    def test_make_organization_name_uniqueness(self):
        """make_organization_name generates unique names"""
        names = [InvitationTestDataFactory.make_organization_name() for _ in range(100)]
        assert len(set(names)) == 100

    def test_make_invitation_token_length(self):
        """make_invitation_token generates token of correct length"""
        token = InvitationTestDataFactory.make_invitation_token()
        assert len(token) >= 32  # URL-safe base64

    def test_make_invitation_token_uniqueness(self):
        """make_invitation_token generates unique tokens"""
        tokens = [InvitationTestDataFactory.make_invitation_token() for _ in range(100)]
        assert len(set(tokens)) == 100

    def test_make_invitation_message_content(self):
        """make_invitation_message generates readable message"""
        message = InvitationTestDataFactory.make_invitation_message()
        assert len(message) > 0
        assert len(message) <= 500


# =============================================================================
# TestDataFactory Timestamp Generation Tests (6 tests)
# =============================================================================

class TestInvitationTestDataFactoryTimestamps:
    """Test timestamp generation methods"""

    def test_make_timestamp_utc(self):
        """make_timestamp returns UTC datetime"""
        ts = InvitationTestDataFactory.make_timestamp()
        assert ts.tzinfo == timezone.utc

    def test_make_past_timestamp_in_past(self):
        """make_past_timestamp returns past datetime"""
        ts = InvitationTestDataFactory.make_past_timestamp()
        assert ts < datetime.now(timezone.utc)

    def test_make_future_timestamp_in_future(self):
        """make_future_timestamp returns future datetime"""
        ts = InvitationTestDataFactory.make_future_timestamp()
        assert ts > datetime.now(timezone.utc)

    def test_make_expires_at_in_future(self):
        """make_expires_at returns future datetime"""
        expires = InvitationTestDataFactory.make_expires_at()
        assert expires > datetime.now(timezone.utc)

    def test_make_expires_at_custom_days(self):
        """make_expires_at accepts custom days parameter"""
        expires = InvitationTestDataFactory.make_expires_at(days=14)
        expected_min = datetime.now(timezone.utc) + timedelta(days=13)
        expected_max = datetime.now(timezone.utc) + timedelta(days=15)
        assert expected_min < expires < expected_max

    def test_make_expired_timestamp_in_past(self):
        """make_expired_timestamp returns past datetime"""
        expired = InvitationTestDataFactory.make_expired_timestamp()
        assert expired < datetime.now(timezone.utc)


# =============================================================================
# TestDataFactory Request Generation Tests (10 tests)
# =============================================================================

class TestInvitationTestDataFactoryRequests:
    """Test request generation methods"""

    def test_make_create_request_valid(self):
        """make_create_request generates valid request"""
        request = InvitationTestDataFactory.make_create_request()
        assert isinstance(request, InvitationCreateRequestContract)
        assert request.email is not None
        assert "@" in request.email

    def test_make_create_request_with_overrides(self):
        """make_create_request accepts overrides"""
        custom_email = "custom@example.com"
        request = InvitationTestDataFactory.make_create_request(email=custom_email)
        assert request.email == custom_email

    def test_make_create_request_with_role_override(self):
        """make_create_request accepts role override"""
        request = InvitationTestDataFactory.make_create_request(role=OrganizationRole.ADMIN)
        assert request.role == OrganizationRole.ADMIN

    def test_make_create_request_with_message(self):
        """make_create_request accepts message override"""
        custom_message = "Welcome to our team!"
        request = InvitationTestDataFactory.make_create_request(message=custom_message)
        assert request.message == custom_message

    def test_make_accept_request_valid(self):
        """make_accept_request generates valid request"""
        request = InvitationTestDataFactory.make_accept_request()
        assert isinstance(request, InvitationAcceptRequestContract)
        assert request.invitation_token is not None

    def test_make_accept_request_with_overrides(self):
        """make_accept_request accepts overrides"""
        # Token must be at least 32 characters per contract
        custom_token = InvitationTestDataFactory.make_invitation_token()
        request = InvitationTestDataFactory.make_accept_request(invitation_token=custom_token)
        assert request.invitation_token == custom_token

    def test_make_list_params_defaults(self):
        """make_list_params generates valid defaults"""
        params = InvitationTestDataFactory.make_list_params()
        assert isinstance(params, InvitationListParamsContract)
        assert params.limit == 100
        assert params.offset == 0

    def test_make_list_params_with_overrides(self):
        """make_list_params accepts overrides"""
        params = InvitationTestDataFactory.make_list_params(limit=50, offset=10)
        assert params.limit == 50
        assert params.offset == 10

    def test_make_resend_request_valid(self):
        """make_resend_request generates valid request"""
        request = InvitationTestDataFactory.make_resend_request()
        assert isinstance(request, InvitationResendRequestContract)
        assert request.invitation_id is not None

    def test_make_cancel_request_valid(self):
        """make_cancel_request generates valid request"""
        request = InvitationTestDataFactory.make_cancel_request()
        assert isinstance(request, InvitationCancelRequestContract)
        assert request.invitation_id is not None


# =============================================================================
# TestDataFactory Response Generation Tests (8 tests)
# =============================================================================

class TestInvitationTestDataFactoryResponses:
    """Test response generation methods"""

    def test_make_invitation_response_valid(self):
        """make_invitation_response generates valid response data"""
        data = InvitationTestDataFactory.make_invitation_response()
        assert "invitation_id" in data
        assert "organization_id" in data
        assert "email" in data
        assert "status" in data

    def test_make_invitation_response_with_overrides(self):
        """make_invitation_response accepts overrides"""
        custom_email = "test@example.com"
        data = InvitationTestDataFactory.make_invitation_response(email=custom_email)
        assert data["email"] == custom_email

    def test_make_invitation_detail_response_valid(self):
        """make_invitation_detail_response includes organization info"""
        data = InvitationTestDataFactory.make_invitation_detail_response()
        assert "invitation_id" in data
        assert "organization_name" in data
        assert "inviter_name" in data

    def test_make_list_response_default_count(self):
        """make_list_response generates default count"""
        data = InvitationTestDataFactory.make_list_response()
        assert "invitations" in data
        assert "total" in data
        assert len(data["invitations"]) == data["total"]

    def test_make_list_response_custom_count(self):
        """make_list_response accepts custom count"""
        data = InvitationTestDataFactory.make_list_response(count=10)
        assert len(data["invitations"]) == 10
        assert data["total"] == 10

    def test_make_accept_response_valid(self):
        """make_accept_response generates valid response"""
        data = InvitationTestDataFactory.make_accept_response()
        assert "invitation_id" in data
        assert "organization_id" in data
        assert "user_id" in data
        assert "accepted_at" in data

    def test_make_stats_response_valid(self):
        """make_stats_response generates valid stats"""
        data = InvitationTestDataFactory.make_stats_response()
        assert "total_invitations" in data
        assert "pending_invitations" in data
        assert "accepted_invitations" in data

    def test_make_error_response_valid(self):
        """make_error_response generates valid error"""
        data = InvitationTestDataFactory.make_error_response()
        assert data["success"] is False
        assert "error" in data
        assert "message" in data


# =============================================================================
# TestDataFactory Invalid Data Generation Tests (12 tests)
# =============================================================================

class TestInvitationTestDataFactoryInvalid:
    """Test invalid data generation methods"""

    def test_make_invalid_email_no_at(self):
        """make_invalid_email generates email without @"""
        email = InvitationTestDataFactory.make_invalid_email()
        assert "@" not in email

    def test_make_invalid_invitation_id(self):
        """make_invalid_invitation_id generates wrong format"""
        inv_id = InvitationTestDataFactory.make_invalid_invitation_id()
        assert not inv_id.startswith("inv_")

    def test_make_invalid_organization_id(self):
        """make_invalid_organization_id generates wrong format"""
        org_id = InvitationTestDataFactory.make_invalid_organization_id()
        assert not org_id.startswith("org_")

    def test_make_invalid_token_empty(self):
        """make_invalid_token_empty generates empty string"""
        token = InvitationTestDataFactory.make_invalid_token_empty()
        assert token == ""

    def test_make_invalid_token_short(self):
        """make_invalid_token_short generates short token"""
        token = InvitationTestDataFactory.make_invalid_token_short()
        assert len(token) < 10

    def test_make_invalid_role(self):
        """make_invalid_role generates invalid role value"""
        role = InvitationTestDataFactory.make_invalid_role()
        valid_roles = [r.value for r in OrganizationRole]
        assert role not in valid_roles

    def test_make_invalid_status(self):
        """make_invalid_status generates invalid status value"""
        status = InvitationTestDataFactory.make_invalid_status()
        valid_statuses = [s.value for s in InvitationStatus]
        assert status not in valid_statuses

    def test_make_invalid_message_too_long(self):
        """make_invalid_message_too_long exceeds max length"""
        message = InvitationTestDataFactory.make_invalid_message_too_long()
        assert len(message) > 500

    def test_make_invalid_limit_zero(self):
        """make_invalid_limit_zero returns zero"""
        limit = InvitationTestDataFactory.make_invalid_limit_zero()
        assert limit == 0

    def test_make_invalid_limit_negative(self):
        """make_invalid_limit_negative returns negative"""
        limit = InvitationTestDataFactory.make_invalid_limit_negative()
        assert limit < 0

    def test_make_invalid_limit_too_large(self):
        """make_invalid_limit_too_large exceeds max"""
        limit = InvitationTestDataFactory.make_invalid_limit_too_large()
        assert limit > 1000

    def test_make_invalid_offset_negative(self):
        """make_invalid_offset_negative returns negative"""
        offset = InvitationTestDataFactory.make_invalid_offset_negative()
        assert offset < 0


# =============================================================================
# Request Contract Validation Tests (15 tests)
# =============================================================================

class TestInvitationCreateRequestValidation:
    """Test creation request validation"""

    def test_valid_request_passes(self):
        """Valid request passes validation"""
        request = InvitationTestDataFactory.make_create_request()
        assert request.email is not None
        assert request.role is not None

    def test_invalid_email_raises_error(self):
        """Invalid email raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            InvitationCreateRequestContract(
                email=InvitationTestDataFactory.make_invalid_email(),
                role=OrganizationRole.MEMBER
            )
        assert "email" in str(exc_info.value).lower()

    def test_message_max_length_accepted(self):
        """Message at max length is accepted"""
        max_message = "x" * 500
        request = InvitationCreateRequestContract(
            email=InvitationTestDataFactory.make_email(),
            role=OrganizationRole.MEMBER,
            message=max_message
        )
        assert len(request.message) == 500

    def test_message_too_long_raises_error(self):
        """Message exceeding max length raises ValidationError"""
        with pytest.raises(ValidationError):
            InvitationCreateRequestContract(
                email=InvitationTestDataFactory.make_email(),
                role=OrganizationRole.MEMBER,
                message="x" * 501
            )

    def test_default_role_is_member(self):
        """Default role is MEMBER"""
        request = InvitationCreateRequestContract(
            email=InvitationTestDataFactory.make_email()
        )
        assert request.role == OrganizationRole.MEMBER

    def test_all_roles_accepted(self):
        """All valid roles are accepted"""
        for role in OrganizationRole:
            request = InvitationCreateRequestContract(
                email=InvitationTestDataFactory.make_email(),
                role=role
            )
            assert request.role == role

    def test_email_normalized_to_lowercase(self):
        """Email is normalized to lowercase"""
        request = InvitationCreateRequestContract(
            email="TEST@EXAMPLE.COM",
            role=OrganizationRole.MEMBER
        )
        assert request.email == "test@example.com"


class TestInvitationAcceptRequestValidation:
    """Test accept request validation"""

    def test_valid_request_passes(self):
        """Valid request passes validation"""
        request = InvitationTestDataFactory.make_accept_request()
        assert request.invitation_token is not None

    def test_empty_token_raises_error(self):
        """Empty token raises ValidationError"""
        with pytest.raises(ValidationError):
            InvitationAcceptRequestContract(invitation_token="")

    def test_user_id_optional(self):
        """user_id is optional"""
        request = InvitationAcceptRequestContract(
            invitation_token=InvitationTestDataFactory.make_invitation_token()
        )
        assert request.user_id is None

    def test_user_id_accepted(self):
        """user_id is accepted when provided"""
        user_id = InvitationTestDataFactory.make_user_id()
        request = InvitationAcceptRequestContract(
            invitation_token=InvitationTestDataFactory.make_invitation_token(),
            user_id=user_id
        )
        assert request.user_id == user_id


class TestInvitationListParamsValidation:
    """Test list params validation"""

    def test_valid_params_passes(self):
        """Valid params pass validation"""
        params = InvitationTestDataFactory.make_list_params()
        assert params.limit > 0
        assert params.offset >= 0

    def test_limit_min_boundary(self):
        """Limit at minimum (1) is accepted"""
        org_id = InvitationTestDataFactory.make_organization_id()
        params = InvitationListParamsContract(organization_id=org_id, limit=1)
        assert params.limit == 1

    def test_limit_max_boundary(self):
        """Limit at maximum (1000) is accepted"""
        org_id = InvitationTestDataFactory.make_organization_id()
        params = InvitationListParamsContract(organization_id=org_id, limit=1000)
        assert params.limit == 1000

    def test_limit_over_max_raises_error(self):
        """Limit over maximum raises ValidationError"""
        org_id = InvitationTestDataFactory.make_organization_id()
        with pytest.raises(ValidationError):
            InvitationListParamsContract(organization_id=org_id, limit=1001)

    def test_offset_zero_accepted(self):
        """Offset at zero is accepted"""
        org_id = InvitationTestDataFactory.make_organization_id()
        params = InvitationListParamsContract(organization_id=org_id, offset=0)
        assert params.offset == 0


# =============================================================================
# Builder Tests (12 tests)
# =============================================================================

class TestInvitationCreateRequestBuilder:
    """Test invitation create request builder"""

    def test_builder_default_build(self):
        """Builder creates valid request with defaults"""
        request = InvitationCreateRequestBuilder().build()
        assert isinstance(request, InvitationCreateRequestContract)
        assert request.email is not None

    def test_builder_with_email(self):
        """Builder accepts custom email"""
        custom_email = "custom@example.com"
        request = InvitationCreateRequestBuilder().with_email(custom_email).build()
        assert request.email == custom_email

    def test_builder_with_role(self):
        """Builder accepts custom role"""
        request = InvitationCreateRequestBuilder().with_role(OrganizationRole.ADMIN).build()
        assert request.role == OrganizationRole.ADMIN

    def test_builder_with_message(self):
        """Builder accepts custom message"""
        custom_message = "Welcome!"
        request = InvitationCreateRequestBuilder().with_message(custom_message).build()
        assert request.message == custom_message

    def test_builder_chaining(self):
        """Builder supports method chaining"""
        request = (
            InvitationCreateRequestBuilder()
            .with_email("test@example.com")
            .with_role(OrganizationRole.VIEWER)
            .with_message("Hello")
            .build()
        )
        assert request.email == "test@example.com"
        assert request.role == OrganizationRole.VIEWER
        assert request.message == "Hello"

    def test_builder_build_dict(self):
        """Builder can build as dictionary"""
        data = InvitationCreateRequestBuilder().build_dict()
        assert isinstance(data, dict)
        assert "email" in data
        assert "role" in data


class TestInvitationAcceptRequestBuilder:
    """Test invitation accept request builder"""

    def test_builder_default_build(self):
        """Builder creates valid request with defaults"""
        request = InvitationAcceptRequestBuilder().build()
        assert isinstance(request, InvitationAcceptRequestContract)
        assert request.invitation_token is not None

    def test_builder_with_token(self):
        """Builder accepts custom token"""
        # Token must be at least 32 characters per contract
        custom_token = InvitationTestDataFactory.make_invitation_token()
        request = InvitationAcceptRequestBuilder().with_token(custom_token).build()
        assert request.invitation_token == custom_token

    def test_builder_with_user_id(self):
        """Builder accepts user_id"""
        user_id = InvitationTestDataFactory.make_user_id()
        request = InvitationAcceptRequestBuilder().with_user_id(user_id).build()
        assert request.user_id == user_id

    def test_builder_build_dict(self):
        """Builder can build as dictionary"""
        data = InvitationAcceptRequestBuilder().build_dict()
        assert isinstance(data, dict)
        assert "invitation_token" in data


class TestInvitationListParamsBuilder:
    """Test invitation list params builder"""

    def test_builder_default_build(self):
        """Builder creates valid params with defaults"""
        params = InvitationListParamsBuilder().build()
        assert isinstance(params, InvitationListParamsContract)

    def test_builder_with_pagination(self):
        """Builder accepts pagination settings"""
        params = InvitationListParamsBuilder().with_pagination(50, 100).build()
        assert params.limit == 50
        assert params.offset == 100


# =============================================================================
# Response Contract Tests (10 tests)
# =============================================================================

class TestInvitationResponseContract:
    """Test invitation response contract validation"""

    def test_valid_response_accepted(self):
        """Valid response data creates contract"""
        data = InvitationTestDataFactory.make_invitation_response()
        response = InvitationResponseContract(**data)
        assert response.invitation_id is not None

    def test_status_enum_parsed(self):
        """Status is parsed as enum"""
        data = InvitationTestDataFactory.make_invitation_response()
        response = InvitationResponseContract(**data)
        assert isinstance(response.status, InvitationStatus)

    def test_role_enum_parsed(self):
        """Role is parsed as enum"""
        data = InvitationTestDataFactory.make_invitation_response()
        response = InvitationResponseContract(**data)
        assert isinstance(response.role, OrganizationRole)


class TestInvitationDetailResponseContract:
    """Test invitation detail response contract"""

    def test_valid_detail_response_accepted(self):
        """Valid detail response creates contract"""
        data = InvitationTestDataFactory.make_invitation_detail_response()
        response = InvitationDetailResponseContract(**data)
        assert response.organization_name is not None

    def test_optional_fields_accepted(self):
        """Optional fields can be None"""
        data = InvitationTestDataFactory.make_invitation_detail_response()
        data["organization_domain"] = None
        data["inviter_name"] = None
        response = InvitationDetailResponseContract(**data)
        assert response.organization_domain is None


class TestInvitationListResponseContract:
    """Test invitation list response contract"""

    def test_valid_list_response_accepted(self):
        """Valid list response creates contract"""
        data = InvitationTestDataFactory.make_list_response()
        response = InvitationListResponseContract(**data)
        assert response.total >= 0

    def test_empty_list_accepted(self):
        """Empty invitation list is accepted"""
        data = InvitationTestDataFactory.make_list_response(count=0)
        response = InvitationListResponseContract(**data)
        assert len(response.invitations) == 0
        assert response.total == 0


class TestAcceptInvitationResponseContract:
    """Test accept invitation response contract"""

    def test_valid_accept_response_accepted(self):
        """Valid accept response creates contract"""
        data = InvitationTestDataFactory.make_accept_response()
        response = AcceptInvitationResponseContract(**data)
        assert response.user_id is not None
        assert response.accepted_at is not None


class TestErrorResponseContract:
    """Test error response contract"""

    def test_valid_error_response_accepted(self):
        """Valid error response creates contract"""
        data = InvitationTestDataFactory.make_error_response()
        response = ErrorResponseContract(**data)
        assert response.success is False
        assert response.error is not None


# =============================================================================
# Enum Tests (6 tests)
# =============================================================================

class TestInvitationStatus:
    """Test InvitationStatus enum"""

    def test_pending_value(self):
        """PENDING has correct value"""
        assert InvitationStatus.PENDING.value == "pending"

    def test_accepted_value(self):
        """ACCEPTED has correct value"""
        assert InvitationStatus.ACCEPTED.value == "accepted"

    def test_expired_value(self):
        """EXPIRED has correct value"""
        assert InvitationStatus.EXPIRED.value == "expired"

    def test_cancelled_value(self):
        """CANCELLED has correct value"""
        assert InvitationStatus.CANCELLED.value == "cancelled"


class TestOrganizationRole:
    """Test OrganizationRole enum"""

    def test_all_roles_exist(self):
        """All expected roles exist"""
        assert OrganizationRole.OWNER.value == "owner"
        assert OrganizationRole.ADMIN.value == "admin"
        assert OrganizationRole.MEMBER.value == "member"
        assert OrganizationRole.VIEWER.value == "viewer"
        assert OrganizationRole.GUEST.value == "guest"

    def test_role_count(self):
        """Correct number of roles"""
        assert len(OrganizationRole) == 5
