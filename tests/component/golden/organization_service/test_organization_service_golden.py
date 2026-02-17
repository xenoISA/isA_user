"""
Organization Service Component Golden Tests

These tests document CURRENT OrganizationService behavior with mocked deps.
Uses proper dependency injection - no patching needed!

Usage:
    pytest tests/component/golden/organization_service -v
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from .mocks import MockOrganizationRepository, MockEventBus

pytestmark = [pytest.mark.component, pytest.mark.golden, pytest.mark.asyncio]


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_repo():
    """Create a fresh MockOrganizationRepository"""
    return MockOrganizationRepository()


@pytest.fixture
def mock_repo_with_org():
    """Create MockOrganizationRepository with existing organization and owner"""
    repo = MockOrganizationRepository()
    repo.set_organization(
        organization_id="org_test_123",
        name="Test Organization",
        billing_email="billing@example.com",
        plan="free",
        status="active",
        member_count=2,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc)
    )
    repo.set_member(
        organization_id="org_test_123",
        user_id="usr_owner",
        role="owner",
        status="active"
    )
    repo.set_member(
        organization_id="org_test_123",
        user_id="usr_member",
        role="member",
        status="active"
    )
    return repo


@pytest.fixture
def mock_event_bus():
    """Create a fresh MockEventBus"""
    return MockEventBus()


# =============================================================================
# OrganizationService.create_organization() Tests
# =============================================================================

class TestOrganizationServiceCreateGolden:
    """Golden: OrganizationService.create_organization() current behavior"""

    async def test_create_organization_returns_response(self, mock_repo, mock_event_bus):
        """GOLDEN: create_organization creates org and returns OrganizationResponse"""
        from microservices.organization_service.organization_service import OrganizationService
        from microservices.organization_service.models import (
            OrganizationCreateRequest,
            OrganizationResponse
        )

        service = OrganizationService(
            repository=mock_repo,
            event_bus=mock_event_bus
        )
        request = OrganizationCreateRequest(
            name="New Organization",
            billing_email="billing@neworg.com"
        )

        result = await service.create_organization(request, "usr_owner_123")

        assert isinstance(result, OrganizationResponse)
        assert result.name == "New Organization"
        assert result.billing_email == "billing@neworg.com"
        assert result.status.value == "active"

        # Verify repository was called
        mock_repo.assert_called("create_organization")

    async def test_create_organization_publishes_event(self, mock_repo, mock_event_bus):
        """GOLDEN: create_organization publishes organization.created event"""
        from microservices.organization_service.organization_service import OrganizationService
        from microservices.organization_service.models import OrganizationCreateRequest

        service = OrganizationService(
            repository=mock_repo,
            event_bus=mock_event_bus
        )
        request = OrganizationCreateRequest(
            name="Test Org",
            billing_email="test@example.com"
        )

        await service.create_organization(request, "usr_123")

        mock_event_bus.assert_published("organization.created")

    async def test_create_organization_validates_empty_name(self, mock_repo):
        """GOLDEN: create_organization rejects empty name"""
        from microservices.organization_service.organization_service import (
            OrganizationService,
            OrganizationValidationError
        )

        service = OrganizationService(repository=mock_repo)

        request = MagicMock()
        request.name = ""
        request.billing_email = "billing@example.com"
        request.model_dump = MagicMock(return_value={})

        with pytest.raises(OrganizationValidationError):
            await service.create_organization(request, "usr_123")

    async def test_create_organization_validates_empty_billing_email(self, mock_repo):
        """GOLDEN: create_organization rejects empty billing_email"""
        from microservices.organization_service.organization_service import (
            OrganizationService,
            OrganizationValidationError
        )

        service = OrganizationService(repository=mock_repo)

        request = MagicMock()
        request.name = "Test Org"
        request.billing_email = ""
        request.model_dump = MagicMock(return_value={})

        with pytest.raises(OrganizationValidationError):
            await service.create_organization(request, "usr_123")


# =============================================================================
# OrganizationService.get_organization() Tests
# =============================================================================

class TestOrganizationServiceGetGolden:
    """Golden: OrganizationService.get_organization() current behavior"""

    async def test_get_organization_returns_response(self, mock_repo_with_org):
        """GOLDEN: get_organization returns OrganizationResponse"""
        from microservices.organization_service.organization_service import OrganizationService
        from microservices.organization_service.models import OrganizationResponse

        service = OrganizationService(repository=mock_repo_with_org)
        result = await service.get_organization("org_test_123", user_id="usr_owner")

        assert isinstance(result, OrganizationResponse)
        assert result.organization_id == "org_test_123"
        assert result.name == "Test Organization"

    async def test_get_organization_raises_not_found(self, mock_repo):
        """GOLDEN: get_organization raises OrganizationNotFoundError when not found"""
        from microservices.organization_service.organization_service import (
            OrganizationService,
            OrganizationNotFoundError
        )

        service = OrganizationService(repository=mock_repo)

        # Use internal-service to bypass access check and verify NotFoundError
        with pytest.raises(OrganizationNotFoundError):
            await service.get_organization("org_nonexistent", user_id="internal-service")

    async def test_get_organization_internal_service_bypass(self, mock_repo_with_org):
        """GOLDEN: Internal service calls bypass access checks"""
        from microservices.organization_service.organization_service import OrganizationService

        service = OrganizationService(repository=mock_repo_with_org)

        # Using internal-service user_id should bypass access checks
        result = await service.get_organization("org_test_123", user_id="internal-service")

        assert result.organization_id == "org_test_123"


# =============================================================================
# OrganizationService.update_organization() Tests
# =============================================================================

class TestOrganizationServiceUpdateGolden:
    """Golden: OrganizationService.update_organization() current behavior"""

    async def test_update_organization_returns_updated(self, mock_repo_with_org, mock_event_bus):
        """GOLDEN: update_organization returns updated OrganizationResponse"""
        from microservices.organization_service.organization_service import OrganizationService
        from microservices.organization_service.models import (
            OrganizationUpdateRequest,
            OrganizationResponse
        )

        service = OrganizationService(
            repository=mock_repo_with_org,
            event_bus=mock_event_bus
        )
        request = OrganizationUpdateRequest(name="Updated Name")
        result = await service.update_organization("org_test_123", request, "usr_owner")

        assert isinstance(result, OrganizationResponse)
        assert result.name == "Updated Name"
        mock_repo_with_org.assert_called("update_organization")

    async def test_update_organization_non_admin_denied(self, mock_repo_with_org):
        """GOLDEN: update_organization raises AccessDenied for non-admin"""
        from microservices.organization_service.organization_service import (
            OrganizationService,
            OrganizationAccessDeniedError
        )
        from microservices.organization_service.models import OrganizationUpdateRequest

        service = OrganizationService(repository=mock_repo_with_org)
        request = OrganizationUpdateRequest(name="New Name")

        with pytest.raises(OrganizationAccessDeniedError):
            await service.update_organization("org_test_123", request, "usr_member")


# =============================================================================
# OrganizationService.delete_organization() Tests
# =============================================================================

class TestOrganizationServiceDeleteGolden:
    """Golden: OrganizationService.delete_organization() current behavior"""

    async def test_delete_organization_owner_succeeds(self, mock_repo_with_org, mock_event_bus):
        """GOLDEN: delete_organization by owner returns True"""
        from microservices.organization_service.organization_service import OrganizationService

        service = OrganizationService(
            repository=mock_repo_with_org,
            event_bus=mock_event_bus
        )

        result = await service.delete_organization("org_test_123", "usr_owner")

        assert result is True
        mock_repo_with_org.assert_called("delete_organization")

    async def test_delete_organization_non_owner_denied(self, mock_repo_with_org):
        """GOLDEN: delete_organization by non-owner raises AccessDenied"""
        from microservices.organization_service.organization_service import (
            OrganizationService,
            OrganizationAccessDeniedError
        )

        service = OrganizationService(repository=mock_repo_with_org)

        with pytest.raises(OrganizationAccessDeniedError):
            await service.delete_organization("org_test_123", "usr_member")

    async def test_delete_organization_publishes_event(self, mock_repo_with_org, mock_event_bus):
        """GOLDEN: delete_organization publishes organization.deleted event"""
        from microservices.organization_service.organization_service import OrganizationService

        service = OrganizationService(
            repository=mock_repo_with_org,
            event_bus=mock_event_bus
        )

        await service.delete_organization("org_test_123", "usr_owner")

        mock_event_bus.assert_published("organization.deleted")


# =============================================================================
# OrganizationService.add_organization_member() Tests
# =============================================================================

class TestOrganizationServiceAddMemberGolden:
    """Golden: OrganizationService.add_organization_member() current behavior"""

    async def test_add_member_returns_response(self, mock_repo_with_org, mock_event_bus):
        """GOLDEN: add_organization_member returns OrganizationMemberResponse"""
        from microservices.organization_service.organization_service import OrganizationService
        from microservices.organization_service.models import (
            OrganizationMemberAddRequest,
            OrganizationMemberResponse,
            OrganizationRole
        )

        service = OrganizationService(
            repository=mock_repo_with_org,
            event_bus=mock_event_bus
        )
        request = OrganizationMemberAddRequest(user_id="usr_new")

        result = await service.add_organization_member("org_test_123", request, "usr_owner")

        assert isinstance(result, OrganizationMemberResponse)
        assert result.user_id == "usr_new"
        assert result.role == OrganizationRole.MEMBER

    async def test_add_member_non_admin_denied(self, mock_repo_with_org):
        """GOLDEN: add_organization_member by non-admin raises AccessDenied"""
        from microservices.organization_service.organization_service import (
            OrganizationService,
            OrganizationAccessDeniedError
        )
        from microservices.organization_service.models import OrganizationMemberAddRequest

        service = OrganizationService(repository=mock_repo_with_org)
        request = OrganizationMemberAddRequest(user_id="usr_new")

        with pytest.raises(OrganizationAccessDeniedError):
            await service.add_organization_member("org_test_123", request, "usr_member")

    async def test_add_member_validates_user_id(self, mock_repo_with_org):
        """GOLDEN: add_organization_member validates user_id is provided"""
        from microservices.organization_service.organization_service import (
            OrganizationService,
            OrganizationValidationError
        )

        service = OrganizationService(repository=mock_repo_with_org)

        request = MagicMock()
        request.user_id = None
        request.email = None
        request.role = "member"
        request.permissions = []

        with pytest.raises(OrganizationValidationError):
            await service.add_organization_member("org_test_123", request, "usr_owner")


# =============================================================================
# OrganizationService.remove_organization_member() Tests
# =============================================================================

class TestOrganizationServiceRemoveMemberGolden:
    """Golden: OrganizationService.remove_organization_member() current behavior"""

    async def test_remove_member_owner_succeeds(self, mock_repo_with_org, mock_event_bus):
        """GOLDEN: Owner can remove members"""
        from microservices.organization_service.organization_service import OrganizationService

        service = OrganizationService(
            repository=mock_repo_with_org,
            event_bus=mock_event_bus
        )

        result = await service.remove_organization_member(
            "org_test_123", "usr_member", "usr_owner"
        )

        assert result is True

    async def test_remove_member_self_removal_succeeds(self, mock_repo_with_org, mock_event_bus):
        """GOLDEN: Member can remove themselves"""
        from microservices.organization_service.organization_service import OrganizationService

        service = OrganizationService(
            repository=mock_repo_with_org,
            event_bus=mock_event_bus
        )

        result = await service.remove_organization_member(
            "org_test_123", "usr_member", "usr_member"
        )

        assert result is True

    async def test_remove_member_non_self_denied(self, mock_repo_with_org):
        """GOLDEN: Member cannot remove other members"""
        from microservices.organization_service.organization_service import (
            OrganizationService,
            OrganizationAccessDeniedError
        )

        # Add another member
        mock_repo_with_org.set_member(
            organization_id="org_test_123",
            user_id="usr_another",
            role="member",
            status="active"
        )

        service = OrganizationService(repository=mock_repo_with_org)

        with pytest.raises(OrganizationAccessDeniedError):
            await service.remove_organization_member(
                "org_test_123", "usr_another", "usr_member"
            )


# =============================================================================
# OrganizationService.switch_user_context() Tests
# =============================================================================

class TestOrganizationServiceContextGolden:
    """Golden: OrganizationService.switch_user_context() current behavior"""

    async def test_switch_to_organization_context(self, mock_repo_with_org):
        """GOLDEN: switch_user_context returns organization context"""
        from microservices.organization_service.organization_service import OrganizationService
        from microservices.organization_service.models import OrganizationContextResponse

        service = OrganizationService(repository=mock_repo_with_org)

        result = await service.switch_user_context("usr_owner", organization_id="org_test_123")

        assert isinstance(result, OrganizationContextResponse)
        assert result.context_type == "organization"
        assert result.organization_id == "org_test_123"
        assert result.organization_name == "Test Organization"

    async def test_switch_to_personal_context(self, mock_repo):
        """GOLDEN: switch_user_context with None returns individual context"""
        from microservices.organization_service.organization_service import OrganizationService
        from microservices.organization_service.models import OrganizationContextResponse

        service = OrganizationService(repository=mock_repo)

        result = await service.switch_user_context("usr_123", organization_id=None)

        assert isinstance(result, OrganizationContextResponse)
        assert result.context_type == "individual"
        assert result.organization_id is None

    async def test_switch_non_member_denied(self, mock_repo_with_org):
        """GOLDEN: switch_user_context by non-member raises AccessDenied"""
        from microservices.organization_service.organization_service import (
            OrganizationService,
            OrganizationAccessDeniedError
        )

        service = OrganizationService(repository=mock_repo_with_org)

        with pytest.raises(OrganizationAccessDeniedError):
            await service.switch_user_context("usr_nonmember", organization_id="org_test_123")


# =============================================================================
# OrganizationService.get_organization_stats() Tests
# =============================================================================

class TestOrganizationServiceStatsGolden:
    """Golden: OrganizationService.get_organization_stats() current behavior"""

    async def test_get_stats_returns_response(self, mock_repo_with_org):
        """GOLDEN: get_organization_stats returns OrganizationStatsResponse"""
        from microservices.organization_service.organization_service import OrganizationService
        from microservices.organization_service.models import OrganizationStatsResponse

        service = OrganizationService(repository=mock_repo_with_org)

        result = await service.get_organization_stats("org_test_123", "usr_owner")

        assert isinstance(result, OrganizationStatsResponse)
        assert result.organization_id == "org_test_123"
        assert result.name == "Test Organization"


# =============================================================================
# OrganizationService.get_organization_members() Tests
# =============================================================================

class TestOrganizationServiceMembersListGolden:
    """Golden: OrganizationService.get_organization_members() current behavior"""

    async def test_get_members_returns_list(self, mock_repo_with_org):
        """GOLDEN: get_organization_members returns OrganizationMemberListResponse"""
        from microservices.organization_service.organization_service import OrganizationService
        from microservices.organization_service.models import OrganizationMemberListResponse

        service = OrganizationService(repository=mock_repo_with_org)

        result = await service.get_organization_members("org_test_123", "usr_owner")

        assert isinstance(result, OrganizationMemberListResponse)
        assert len(result.members) == 2
        assert result.total == 2

    async def test_get_members_non_member_denied(self, mock_repo_with_org):
        """GOLDEN: get_organization_members by non-member raises AccessDenied"""
        from microservices.organization_service.organization_service import (
            OrganizationService,
            OrganizationAccessDeniedError
        )

        service = OrganizationService(repository=mock_repo_with_org)

        with pytest.raises(OrganizationAccessDeniedError):
            await service.get_organization_members("org_test_123", "usr_nonmember")


# =============================================================================
# OrganizationService.get_user_organizations() Tests
# =============================================================================

class TestOrganizationServiceUserOrgsGolden:
    """Golden: OrganizationService.get_user_organizations() current behavior"""

    async def test_get_user_organizations_returns_list(self, mock_repo_with_org):
        """GOLDEN: get_user_organizations returns OrganizationListResponse"""
        from microservices.organization_service.organization_service import OrganizationService
        from microservices.organization_service.models import OrganizationListResponse

        service = OrganizationService(repository=mock_repo_with_org)

        result = await service.get_user_organizations("usr_owner")

        assert isinstance(result, OrganizationListResponse)
        assert len(result.organizations) == 1
        assert result.organizations[0].organization_id == "org_test_123"

    async def test_get_user_organizations_empty(self, mock_repo):
        """GOLDEN: get_user_organizations returns empty list for user without orgs"""
        from microservices.organization_service.organization_service import OrganizationService

        service = OrganizationService(repository=mock_repo)

        result = await service.get_user_organizations("usr_no_orgs")

        assert len(result.organizations) == 0
        assert result.total == 0
