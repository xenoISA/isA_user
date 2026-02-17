"""
Organization Service Integration Tests

Tests the OrganizationService layer with mocked dependencies.
These are NOT HTTP tests - they test the service business logic layer directly.

Purpose:
- Test OrganizationService business logic with mocked repository
- Test event publishing integration
- Test validation and error handling
- Test cross-service interactions

Usage:
    pytest tests/integration/golden/organization_service/test_organization_integration.py -v
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, MagicMock
from typing import Dict, Any
from decimal import Decimal

# Import from centralized data contracts
from tests.contracts.organization.data_contract import (
    OrganizationTestDataFactory,
    OrganizationCreateRequestContract,
    OrganizationMemberAddRequestContract,
)

# Import service layer to test
from microservices.organization_service.organization_service import (
    OrganizationService,
    OrganizationNotFoundError,
    OrganizationAccessDeniedError,
    OrganizationValidationError,
    OrganizationServiceError,
)

# Import models
from microservices.organization_service.models import (
    OrganizationCreateRequest,
    OrganizationUpdateRequest,
    OrganizationMemberAddRequest,
    OrganizationResponse,
    OrganizationMemberResponse,
    OrganizationPlan,
    OrganizationStatus,
    OrganizationRole,
    MemberStatus,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_repository():
    """Mock repository for testing service layer."""
    return AsyncMock()


@pytest.fixture
def mock_event_bus():
    """Mock event bus for testing event publishing."""
    mock = Mock()
    mock.publish_event = AsyncMock()
    return mock


@pytest.fixture
def organization_service(mock_repository, mock_event_bus):
    """Create OrganizationService with mocked dependencies."""
    return OrganizationService(
        repository=mock_repository,
        event_bus=mock_event_bus,
    )


@pytest.fixture
def sample_organization():
    """Create sample organization using data contract factory."""
    return OrganizationResponse(
        organization_id=OrganizationTestDataFactory.make_organization_id(),
        name=OrganizationTestDataFactory.make_organization_name(),
        billing_email=OrganizationTestDataFactory.make_email(),
        plan=OrganizationPlan.FREE,
        status=OrganizationStatus.ACTIVE,
        member_count=1,
        credits_pool=Decimal("0"),
        settings={},
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_member():
    """Create sample member response."""
    return OrganizationMemberResponse(
        user_id=OrganizationTestDataFactory.make_user_id(),
        organization_id=OrganizationTestDataFactory.make_organization_id(),
        role=OrganizationRole.MEMBER,
        status=MemberStatus.ACTIVE,
        permissions=[],
        joined_at=datetime.now(timezone.utc),
    )


# ============================================================================
# TEST CLASS 1: Organization Creation Tests
# ============================================================================

class TestOrganizationCreation:
    """Test organization creation operations."""

    async def test_create_organization_success(
        self, organization_service, mock_repository, mock_event_bus
    ):
        """Test that create_organization creates a new organization."""
        # GIVEN: Valid create request using data contract
        create_contract = OrganizationTestDataFactory.make_create_request()
        valid_data = create_contract.model_dump()
        request = OrganizationCreateRequest(
            name=valid_data["name"],
            billing_email=valid_data["billing_email"],
        )
        owner_user_id = OrganizationTestDataFactory.make_user_id()

        # Set up mock response
        created_org = OrganizationResponse(
            organization_id=OrganizationTestDataFactory.make_organization_id(),
            name=valid_data["name"],
            billing_email=valid_data["billing_email"],
            plan=OrganizationPlan(valid_data.get("plan", "free")),
            status=OrganizationStatus.ACTIVE,
            member_count=1,
            credits_pool=Decimal("0"),
            settings={},
            created_at=datetime.now(timezone.utc),
        )
        mock_repository.create_organization.return_value = created_org

        # WHEN: Creating organization
        result = await organization_service.create_organization(request, owner_user_id)

        # THEN: Organization is created
        assert result.name == valid_data["name"]
        assert result.billing_email == valid_data["billing_email"]
        mock_repository.create_organization.assert_called_once()
        mock_event_bus.publish_event.assert_called_once()

    async def test_create_organization_validates_empty_name(
        self, organization_service
    ):
        """Test that create_organization rejects empty name."""
        # GIVEN: Request with empty name
        request = MagicMock()
        request.name = ""
        request.billing_email = "test@example.com"
        request.model_dump = MagicMock(return_value={})

        # WHEN/THEN: Validation error raised
        with pytest.raises(OrganizationValidationError) as exc_info:
            await organization_service.create_organization(
                request, "usr_123"
            )
        assert "name" in str(exc_info.value).lower() or "required" in str(exc_info.value).lower()

    async def test_create_organization_validates_empty_billing_email(
        self, organization_service
    ):
        """Test that create_organization rejects empty billing_email."""
        # GIVEN: Request with empty billing_email
        request = MagicMock()
        request.name = "Test Org"
        request.billing_email = ""
        request.model_dump = MagicMock(return_value={})

        # WHEN/THEN: Validation error raised
        with pytest.raises(OrganizationValidationError) as exc_info:
            await organization_service.create_organization(
                request, "usr_123"
            )
        assert "billing" in str(exc_info.value).lower() or "required" in str(exc_info.value).lower()


# ============================================================================
# TEST CLASS 2: Organization Retrieval Tests
# ============================================================================

class TestOrganizationRetrieval:
    """Test organization retrieval operations."""

    async def test_get_organization_success(
        self, organization_service, mock_repository, sample_organization
    ):
        """Test that get_organization returns organization for authorized user."""
        # GIVEN: Existing organization
        mock_repository.get_organization.return_value = sample_organization
        mock_repository.get_user_organization_role.return_value = {
            "role": "member",
            "status": "active",
            "permissions": []
        }

        # WHEN: Getting organization
        result = await organization_service.get_organization(
            sample_organization.organization_id,
            user_id="usr_member"
        )

        # THEN: Organization returned
        assert result.organization_id == sample_organization.organization_id

    async def test_get_organization_not_found(
        self, organization_service, mock_repository
    ):
        """Test that get_organization raises NotFoundError for non-existent org."""
        # GIVEN: Non-existent organization
        mock_repository.get_organization.return_value = None

        # WHEN/THEN: NotFoundError raised
        with pytest.raises(OrganizationNotFoundError):
            await organization_service.get_organization(
                "org_nonexistent",
                user_id="internal-service"
            )

    async def test_get_organization_access_denied(
        self, organization_service, mock_repository, sample_organization
    ):
        """Test that get_organization raises AccessDenied for unauthorized user."""
        # GIVEN: Organization exists but user is not a member
        mock_repository.get_organization.return_value = sample_organization
        mock_repository.get_user_organization_role.return_value = None

        # WHEN/THEN: AccessDenied raised
        with pytest.raises(OrganizationAccessDeniedError):
            await organization_service.get_organization(
                sample_organization.organization_id,
                user_id="usr_unauthorized"
            )


# ============================================================================
# TEST CLASS 3: Member Management Tests
# ============================================================================

class TestMemberManagement:
    """Test member management operations."""

    async def test_add_member_success(
        self, organization_service, mock_repository, mock_event_bus, sample_member
    ):
        """Test that add_organization_member adds member successfully."""
        # GIVEN: Admin user adding new member
        mock_repository.get_user_organization_role.return_value = {
            "role": "admin",
            "status": "active",
            "permissions": []
        }
        mock_repository.add_organization_member.return_value = sample_member

        request = OrganizationMemberAddRequest(
            user_id=OrganizationTestDataFactory.make_user_id()
        )

        # WHEN: Adding member
        result = await organization_service.add_organization_member(
            "org_test",
            request,
            "usr_admin"
        )

        # THEN: Member added
        assert result.user_id == sample_member.user_id
        mock_repository.add_organization_member.assert_called_once()

    async def test_add_member_non_admin_denied(
        self, organization_service, mock_repository
    ):
        """Test that add_organization_member rejects non-admin users."""
        # GIVEN: Non-admin user
        mock_repository.get_user_organization_role.return_value = {
            "role": "member",
            "status": "active",
            "permissions": []
        }

        request = OrganizationMemberAddRequest(user_id="usr_new")

        # WHEN/THEN: AccessDenied raised
        with pytest.raises(OrganizationAccessDeniedError):
            await organization_service.add_organization_member(
                "org_test",
                request,
                "usr_member"
            )

    async def test_add_member_validates_user_id(
        self, organization_service, mock_repository
    ):
        """Test that add_organization_member validates user_id is provided."""
        # GIVEN: Admin user with invalid request
        mock_repository.get_user_organization_role.return_value = {
            "role": "admin",
            "status": "active",
            "permissions": []
        }

        request = MagicMock()
        request.user_id = None
        request.email = None
        request.role = "member"
        request.permissions = []

        # WHEN/THEN: Validation error raised
        with pytest.raises(OrganizationValidationError):
            await organization_service.add_organization_member(
                "org_test",
                request,
                "usr_admin"
            )


# ============================================================================
# TEST CLASS 4: Member Removal Tests
# ============================================================================

class TestMemberRemoval:
    """Test member removal operations."""

    async def test_remove_member_owner_success(
        self, organization_service, mock_repository, mock_event_bus
    ):
        """Test that owner can remove members."""
        # GIVEN: Owner removing a member
        mock_repository.get_user_organization_role.side_effect = [
            {"role": "owner", "status": "active", "permissions": []},  # requesting
            {"role": "member", "status": "active", "permissions": []},  # target
        ]
        mock_repository.remove_organization_member.return_value = True

        # WHEN: Removing member
        result = await organization_service.remove_organization_member(
            "org_test",
            "usr_member",
            "usr_owner"
        )

        # THEN: Member removed
        assert result is True

    async def test_remove_member_self_removal_success(
        self, organization_service, mock_repository, mock_event_bus
    ):
        """Test that member can remove themselves."""
        # GIVEN: Member removing themselves
        mock_repository.get_user_organization_role.side_effect = [
            {"role": "member", "status": "active", "permissions": []},  # requesting
            {"role": "member", "status": "active", "permissions": []},  # target
        ]
        mock_repository.remove_organization_member.return_value = True

        # WHEN: Self removal
        result = await organization_service.remove_organization_member(
            "org_test",
            "usr_member",
            "usr_member"
        )

        # THEN: Removed successfully
        assert result is True

    async def test_remove_member_cannot_remove_others(
        self, organization_service, mock_repository
    ):
        """Test that member cannot remove other members."""
        # GIVEN: Member trying to remove another member
        mock_repository.get_user_organization_role.side_effect = [
            {"role": "member", "status": "active", "permissions": []},  # requesting
            {"role": "member", "status": "active", "permissions": []},  # target
        ]

        # WHEN/THEN: AccessDenied raised
        with pytest.raises(OrganizationAccessDeniedError):
            await organization_service.remove_organization_member(
                "org_test",
                "usr_other",
                "usr_member"
            )

    async def test_remove_last_owner_prevented(
        self, organization_service, mock_repository
    ):
        """Test that last owner cannot be removed."""
        # GIVEN: Only one owner exists
        mock_repository.get_user_organization_role.side_effect = [
            {"role": "owner", "status": "active", "permissions": []},  # requesting
            {"role": "owner", "status": "active", "permissions": []},  # target
        ]
        mock_repository.get_organization_members.return_value = [
            {"user_id": "usr_owner"}  # Only one owner
        ]

        # WHEN/THEN: ValidationError raised
        with pytest.raises(OrganizationValidationError) as exc_info:
            await organization_service.remove_organization_member(
                "org_test",
                "usr_owner",
                "usr_owner"
            )
        assert "last" in str(exc_info.value).lower() or "owner" in str(exc_info.value).lower()


# ============================================================================
# TEST CLASS 5: Context Switching Tests
# ============================================================================

class TestContextSwitching:
    """Test context switching operations."""

    async def test_switch_to_organization_context(
        self, organization_service, mock_repository, sample_organization
    ):
        """Test switching to organization context."""
        # GIVEN: User is member of organization
        mock_repository.get_user_organization_role.return_value = {
            "role": "member",
            "status": "active",
            "permissions": ["read"]
        }
        mock_repository.get_organization.return_value = sample_organization

        # WHEN: Switching context
        result = await organization_service.switch_user_context(
            "usr_member",
            organization_id=sample_organization.organization_id
        )

        # THEN: Organization context returned
        assert result.context_type == "organization"
        assert result.organization_id == sample_organization.organization_id

    async def test_switch_to_personal_context(
        self, organization_service
    ):
        """Test switching to personal context."""
        # WHEN: Switching to personal context
        result = await organization_service.switch_user_context(
            "usr_123",
            organization_id=None
        )

        # THEN: Individual context returned
        assert result.context_type == "individual"
        assert result.organization_id is None

    async def test_switch_context_non_member_denied(
        self, organization_service, mock_repository
    ):
        """Test that non-members cannot switch to organization context."""
        # GIVEN: User is not a member
        mock_repository.get_user_organization_role.return_value = None

        # WHEN/THEN: AccessDenied raised
        with pytest.raises(OrganizationAccessDeniedError):
            await organization_service.switch_user_context(
                "usr_nonmember",
                organization_id="org_test"
            )

    async def test_switch_context_inactive_member_denied(
        self, organization_service, mock_repository
    ):
        """Test that inactive members cannot switch to organization context."""
        # GIVEN: User is suspended
        mock_repository.get_user_organization_role.return_value = {
            "role": "member",
            "status": "suspended",
            "permissions": []
        }

        # WHEN/THEN: AccessDenied raised
        with pytest.raises(OrganizationAccessDeniedError):
            await organization_service.switch_user_context(
                "usr_suspended",
                organization_id="org_test"
            )


# ============================================================================
# TEST CLASS 6: Organization Deletion Tests
# ============================================================================

class TestOrganizationDeletion:
    """Test organization deletion operations."""

    async def test_delete_organization_owner_success(
        self, organization_service, mock_repository, mock_event_bus, sample_organization
    ):
        """Test that owner can delete organization."""
        # GIVEN: Owner deleting organization
        mock_repository.get_user_organization_role.return_value = {
            "role": "owner",
            "status": "active",
            "permissions": []
        }
        mock_repository.get_organization.return_value = sample_organization
        mock_repository.delete_organization.return_value = True

        # WHEN: Deleting organization
        result = await organization_service.delete_organization(
            sample_organization.organization_id,
            "usr_owner"
        )

        # THEN: Organization deleted
        assert result is True
        mock_event_bus.publish_event.assert_called_once()

    async def test_delete_organization_non_owner_denied(
        self, organization_service, mock_repository, sample_organization
    ):
        """Test that non-owner cannot delete organization."""
        # GIVEN: Admin trying to delete
        mock_repository.get_user_organization_role.return_value = {
            "role": "admin",
            "status": "active",
            "permissions": []
        }
        mock_repository.get_organization.return_value = sample_organization

        # WHEN/THEN: AccessDenied raised
        with pytest.raises(OrganizationAccessDeniedError):
            await organization_service.delete_organization(
                sample_organization.organization_id,
                "usr_admin"
            )
