"""
Organization Service Validation Logic Golden Tests

Tests the pure validation methods in OrganizationService.
These are synchronous methods that don't require mocks.

Usage:
    pytest tests/unit/golden/organization_service/test_organization_service_validation_golden.py -v
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock

pytestmark = [pytest.mark.unit, pytest.mark.golden]


class TestCheckUserAccess:
    """
    Golden: OrganizationService.check_user_access()
    """

    def _create_service(self):
        """Create service with mock repository"""
        from microservices.organization_service.organization_service import OrganizationService
        repository = MagicMock()
        return OrganizationService(repository=repository)

    @pytest.mark.asyncio
    async def test_returns_true_for_active_member(self):
        """GOLDEN: Returns True for active member"""
        service = self._create_service()
        service.repository.get_user_organization_role = AsyncMock(
            return_value={"role": "member", "status": "active", "permissions": []}
        )

        result = await service.check_user_access("org_123", "usr_123")

        assert result is True
        service.repository.get_user_organization_role.assert_called_once_with("org_123", "usr_123")

    @pytest.mark.asyncio
    async def test_returns_false_for_no_membership(self):
        """GOLDEN: Returns False when user is not a member"""
        service = self._create_service()
        service.repository.get_user_organization_role = AsyncMock(return_value=None)

        result = await service.check_user_access("org_123", "usr_123")

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_for_suspended_member(self):
        """GOLDEN: Returns False for suspended member"""
        service = self._create_service()
        service.repository.get_user_organization_role = AsyncMock(
            return_value={"role": "member", "status": "suspended", "permissions": []}
        )

        result = await service.check_user_access("org_123", "usr_123")

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_for_pending_member(self):
        """GOLDEN: Returns False for pending member"""
        service = self._create_service()
        service.repository.get_user_organization_role = AsyncMock(
            return_value={"role": "member", "status": "pending", "permissions": []}
        )

        result = await service.check_user_access("org_123", "usr_123")

        assert result is False


class TestCheckAdminAccess:
    """
    Golden: OrganizationService.check_admin_access()
    """

    def _create_service(self):
        """Create service with mock repository"""
        from microservices.organization_service.organization_service import OrganizationService
        repository = MagicMock()
        return OrganizationService(repository=repository)

    @pytest.mark.asyncio
    async def test_returns_true_for_owner(self):
        """GOLDEN: Returns True for owner"""
        service = self._create_service()
        service.repository.get_user_organization_role = AsyncMock(
            return_value={"role": "owner", "status": "active", "permissions": []}
        )

        result = await service.check_admin_access("org_123", "usr_123")

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_true_for_admin(self):
        """GOLDEN: Returns True for admin"""
        service = self._create_service()
        service.repository.get_user_organization_role = AsyncMock(
            return_value={"role": "admin", "status": "active", "permissions": []}
        )

        result = await service.check_admin_access("org_123", "usr_123")

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_for_member(self):
        """GOLDEN: Returns False for regular member"""
        service = self._create_service()
        service.repository.get_user_organization_role = AsyncMock(
            return_value={"role": "member", "status": "active", "permissions": []}
        )

        result = await service.check_admin_access("org_123", "usr_123")

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_for_guest(self):
        """GOLDEN: Returns False for guest"""
        service = self._create_service()
        service.repository.get_user_organization_role = AsyncMock(
            return_value={"role": "guest", "status": "active", "permissions": []}
        )

        result = await service.check_admin_access("org_123", "usr_123")

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_for_inactive_admin(self):
        """GOLDEN: Returns False for inactive admin"""
        service = self._create_service()
        service.repository.get_user_organization_role = AsyncMock(
            return_value={"role": "admin", "status": "suspended", "permissions": []}
        )

        result = await service.check_admin_access("org_123", "usr_123")

        assert result is False


class TestCheckOwnerAccess:
    """
    Golden: OrganizationService.check_owner_access()
    """

    def _create_service(self):
        """Create service with mock repository"""
        from microservices.organization_service.organization_service import OrganizationService
        repository = MagicMock()
        return OrganizationService(repository=repository)

    @pytest.mark.asyncio
    async def test_returns_true_for_owner(self):
        """GOLDEN: Returns True for owner"""
        service = self._create_service()
        service.repository.get_user_organization_role = AsyncMock(
            return_value={"role": "owner", "status": "active", "permissions": []}
        )

        result = await service.check_owner_access("org_123", "usr_123")

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_for_admin(self):
        """GOLDEN: Returns False for admin (not owner)"""
        service = self._create_service()
        service.repository.get_user_organization_role = AsyncMock(
            return_value={"role": "admin", "status": "active", "permissions": []}
        )

        result = await service.check_owner_access("org_123", "usr_123")

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_for_inactive_owner(self):
        """GOLDEN: Returns False for inactive owner"""
        service = self._create_service()
        service.repository.get_user_organization_role = AsyncMock(
            return_value={"role": "owner", "status": "suspended", "permissions": []}
        )

        result = await service.check_owner_access("org_123", "usr_123")

        assert result is False


class TestCreateOrganizationValidation:
    """
    Golden: OrganizationService.create_organization() validation
    """

    def _create_service(self):
        """Create service with mock repository"""
        from microservices.organization_service.organization_service import OrganizationService
        repository = MagicMock()
        return OrganizationService(repository=repository)

    def _create_request(self, name="Test Org", billing_email="billing@example.com"):
        """Create OrganizationCreateRequest"""
        from microservices.organization_service.models import OrganizationCreateRequest
        return OrganizationCreateRequest(name=name, billing_email=billing_email)

    @pytest.mark.asyncio
    async def test_validates_empty_name(self):
        """GOLDEN: Empty name raises OrganizationValidationError"""
        from microservices.organization_service.organization_service import OrganizationValidationError

        service = self._create_service()

        # Create mock request with empty name
        request = MagicMock()
        request.name = ""
        request.billing_email = "billing@example.com"
        request.model_dump = MagicMock(return_value={})

        with pytest.raises(OrganizationValidationError) as exc_info:
            await service.create_organization(request, "usr_123")

        assert "name" in str(exc_info.value).lower() or "required" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_validates_empty_billing_email(self):
        """GOLDEN: Empty billing_email raises OrganizationValidationError"""
        from microservices.organization_service.organization_service import OrganizationValidationError

        service = self._create_service()

        # Create mock request with empty billing_email
        request = MagicMock()
        request.name = "Test Org"
        request.billing_email = ""
        request.model_dump = MagicMock(return_value={})

        with pytest.raises(OrganizationValidationError) as exc_info:
            await service.create_organization(request, "usr_123")

        assert "billing" in str(exc_info.value).lower() or "required" in str(exc_info.value).lower()


class TestAddOrganizationMemberValidation:
    """
    Golden: OrganizationService.add_organization_member() validation
    """

    def _create_service(self):
        """Create service with mock repository"""
        from microservices.organization_service.organization_service import OrganizationService
        repository = MagicMock()
        return OrganizationService(repository=repository)

    @pytest.mark.asyncio
    async def test_validates_no_user_id_or_email(self):
        """GOLDEN: Missing user_id and email raises OrganizationValidationError"""
        from microservices.organization_service.organization_service import (
            OrganizationService,
            OrganizationValidationError
        )

        service = self._create_service()
        service.repository.get_user_organization_role = AsyncMock(
            return_value={"role": "admin", "status": "active", "permissions": []}
        )

        request = MagicMock()
        request.user_id = None
        request.email = None
        request.role = "member"
        request.permissions = []

        with pytest.raises(OrganizationValidationError) as exc_info:
            await service.add_organization_member("org_123", request, "admin_usr")

        assert "user_id" in str(exc_info.value).lower() or "email" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_validates_empty_user_id_and_email(self):
        """GOLDEN: Empty user_id and email raises OrganizationValidationError"""
        from microservices.organization_service.organization_service import OrganizationValidationError

        service = self._create_service()
        service.repository.get_user_organization_role = AsyncMock(
            return_value={"role": "admin", "status": "active", "permissions": []}
        )

        request = MagicMock()
        request.user_id = ""
        request.email = ""
        request.role = "member"
        request.permissions = []

        with pytest.raises(OrganizationValidationError) as exc_info:
            await service.add_organization_member("org_123", request, "admin_usr")

        assert "user_id" in str(exc_info.value).lower() or "email" in str(exc_info.value).lower()


class TestUpdateOrganizationMemberValidation:
    """
    Golden: OrganizationService.update_organization_member() validation
    """

    def _create_service(self):
        """Create service with mock repository"""
        from microservices.organization_service.organization_service import OrganizationService
        repository = MagicMock()
        return OrganizationService(repository=repository)

    @pytest.mark.asyncio
    async def test_admin_cannot_modify_owner(self):
        """GOLDEN: Admin cannot modify owner"""
        from microservices.organization_service.organization_service import OrganizationAccessDeniedError

        service = self._create_service()

        # Requesting user is admin
        service.repository.get_user_organization_role = AsyncMock(
            side_effect=[
                {"role": "admin", "status": "active", "permissions": []},  # check_admin_access
                {"role": "owner", "status": "active", "permissions": []},  # target role
                {"role": "admin", "status": "active", "permissions": []},  # requesting role check
            ]
        )

        request = MagicMock()
        request.role = "member"
        request.model_dump = MagicMock(return_value={"role": "member"})

        with pytest.raises(OrganizationAccessDeniedError) as exc_info:
            await service.update_organization_member("org_123", "owner_usr", request, "admin_usr")

        assert "admin" in str(exc_info.value).lower() or "owner" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_admin_cannot_modify_other_admin(self):
        """GOLDEN: Admin cannot modify other admin"""
        from microservices.organization_service.organization_service import OrganizationAccessDeniedError

        service = self._create_service()

        # Requesting user is admin, target is also admin
        service.repository.get_user_organization_role = AsyncMock(
            side_effect=[
                {"role": "admin", "status": "active", "permissions": []},  # check_admin_access
                {"role": "admin", "status": "active", "permissions": []},  # target role
                {"role": "admin", "status": "active", "permissions": []},  # requesting role check
            ]
        )

        request = MagicMock()
        request.role = "member"
        request.model_dump = MagicMock(return_value={"role": "member"})

        with pytest.raises(OrganizationAccessDeniedError) as exc_info:
            await service.update_organization_member("org_123", "other_admin", request, "admin_usr")

        assert "admin" in str(exc_info.value).lower()


class TestRemoveOrganizationMemberValidation:
    """
    Golden: OrganizationService.remove_organization_member() validation
    """

    def _create_service(self):
        """Create service with mock repository"""
        from microservices.organization_service.organization_service import OrganizationService
        repository = MagicMock()
        return OrganizationService(repository=repository)

    @pytest.mark.asyncio
    async def test_admin_cannot_remove_owner(self):
        """GOLDEN: Admin cannot remove owner"""
        from microservices.organization_service.organization_service import OrganizationAccessDeniedError

        service = self._create_service()

        service.repository.get_user_organization_role = AsyncMock(
            side_effect=[
                {"role": "admin", "status": "active", "permissions": []},  # requesting role
                {"role": "owner", "status": "active", "permissions": []},  # target role
            ]
        )

        with pytest.raises(OrganizationAccessDeniedError) as exc_info:
            await service.remove_organization_member("org_123", "owner_usr", "admin_usr")

        assert "admin" in str(exc_info.value).lower() or "owner" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_member_cannot_remove_others(self):
        """GOLDEN: Member cannot remove other members"""
        from microservices.organization_service.organization_service import OrganizationAccessDeniedError

        service = self._create_service()

        service.repository.get_user_organization_role = AsyncMock(
            side_effect=[
                {"role": "member", "status": "active", "permissions": []},  # requesting role
                {"role": "member", "status": "active", "permissions": []},  # target role
            ]
        )

        with pytest.raises(OrganizationAccessDeniedError) as exc_info:
            await service.remove_organization_member("org_123", "other_member", "member_usr")

        assert "member" in str(exc_info.value).lower() or "remove" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_cannot_remove_last_owner(self):
        """GOLDEN: Cannot remove the last owner"""
        from microservices.organization_service.organization_service import OrganizationValidationError
        from microservices.organization_service.models import OrganizationRole

        service = self._create_service()

        service.repository.get_user_organization_role = AsyncMock(
            side_effect=[
                {"role": "owner", "status": "active", "permissions": []},  # requesting role (owner)
                {"role": "owner", "status": "active", "permissions": []},  # target role (also owner)
            ]
        )
        # Only one owner exists
        service.repository.get_organization_members = AsyncMock(return_value=[{"user_id": "owner_usr"}])

        with pytest.raises(OrganizationValidationError) as exc_info:
            await service.remove_organization_member("org_123", "owner_usr", "owner_usr")

        assert "last" in str(exc_info.value).lower() or "owner" in str(exc_info.value).lower()


class TestSwitchUserContextValidation:
    """
    Golden: OrganizationService.switch_user_context() validation
    """

    def _create_service(self):
        """Create service with mock repository"""
        from microservices.organization_service.organization_service import OrganizationService
        repository = MagicMock()
        return OrganizationService(repository=repository)

    @pytest.mark.asyncio
    async def test_switch_to_personal_context(self):
        """GOLDEN: Switch to personal context (no org_id) returns individual context"""
        service = self._create_service()

        result = await service.switch_user_context("usr_123", organization_id=None)

        assert result.context_type == "individual"
        assert result.organization_id is None
        assert result.organization_name is None
        assert result.user_role is None

    @pytest.mark.asyncio
    async def test_switch_fails_for_non_member(self):
        """GOLDEN: Switch fails for non-member"""
        from microservices.organization_service.organization_service import OrganizationAccessDeniedError

        service = self._create_service()
        service.repository.get_user_organization_role = AsyncMock(return_value=None)

        with pytest.raises(OrganizationAccessDeniedError) as exc_info:
            await service.switch_user_context("usr_123", organization_id="org_123")

        assert "member" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_switch_fails_for_inactive_member(self):
        """GOLDEN: Switch fails for inactive member"""
        from microservices.organization_service.organization_service import OrganizationAccessDeniedError

        service = self._create_service()
        service.repository.get_user_organization_role = AsyncMock(
            return_value={"role": "member", "status": "suspended", "permissions": []}
        )

        with pytest.raises(OrganizationAccessDeniedError) as exc_info:
            await service.switch_user_context("usr_123", organization_id="org_123")

        assert "active" in str(exc_info.value).lower()
