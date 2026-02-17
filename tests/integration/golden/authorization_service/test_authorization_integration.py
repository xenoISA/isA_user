"""
Authorization Service Integration Tests

Tests the AuthorizationService layer with mocked dependencies (repository, event_bus).
These are NOT HTTP tests - they test the service business logic layer directly.

Purpose:
- Test AuthorizationService business logic with mocked repository
- Test event publishing integration
- Test validation and error handling
- Test subscription and organization permission flows

According to TDD_CONTRACT.md:
- Service layer tests use mocked repository (no real DB)
- Service layer tests use mocked event bus (no real NATS)
- Use AuthorizationTestDataFactory from data contracts (no hardcoded data)
- Target 25-35 tests with comprehensive coverage

Usage:
    pytest tests/integration/golden/authorization_service/test_authorization_integration.py -v
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock, patch

# Import from centralized data contracts
from tests.contracts.authorization.data_contract import (
    AuthorizationTestDataFactory,
    ResourceType,
    AccessLevel,
    PermissionSource,
    SubscriptionTier,
    OrganizationPlan,
)

# Import service layer to test
from microservices.authorization_service.authorization_service import AuthorizationService
from microservices.authorization_service.models import (
    ResourceAccessRequest,
    ResourceAccessResponse,
    GrantPermissionRequest,
    RevokePermissionRequest,
    ResourcePermission,
    UserPermissionRecord,
    OrganizationPermission,
    ExternalServiceUser,
    ExternalServiceOrganization,
    UserPermissionSummary,
    ResourceType as ModelResourceType,
    AccessLevel as ModelAccessLevel,
    PermissionSource as ModelPermissionSource,
    SubscriptionTier as ModelSubscriptionTier,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_repository():
    """
    Mock repository for testing service layer.

    This replaces the real AuthorizationRepository with an AsyncMock,
    allowing us to test business logic without database I/O.
    """
    return AsyncMock()


@pytest.fixture
def mock_event_bus():
    """
    Mock event bus for testing event publishing.

    This replaces the real NATS connection with an AsyncMock,
    allowing us to verify events are published correctly.
    """
    mock = AsyncMock()
    mock.publish_event = AsyncMock()
    return mock


@pytest.fixture
def auth_service(mock_repository, mock_event_bus):
    """
    Create AuthorizationService with mocked dependencies.

    This is the service under test - we test its business logic
    while mocking all I/O dependencies.
    """
    service = AuthorizationService(
        repository=mock_repository,
        event_bus=mock_event_bus,
        config=None,
    )
    return service


@pytest.fixture
def sample_user():
    """
    Create sample user for testing using data contract factory.
    """
    return ExternalServiceUser(
        user_id=AuthorizationTestDataFactory.make_user_id(),
        email=AuthorizationTestDataFactory.make_email(),
        subscription_status="pro",
        is_active=True,
        organization_id=None,
    )


@pytest.fixture
def sample_resource_permission():
    """
    Create sample resource permission for testing.
    """
    return ResourcePermission(
        resource_type=ModelResourceType.API_ENDPOINT,
        resource_name=AuthorizationTestDataFactory.make_api_endpoint_name(),
        resource_category="utilities",
        subscription_tier_required=ModelSubscriptionTier.PRO,
        access_level=ModelAccessLevel.READ_WRITE,
        description="Test API endpoint",
        is_enabled=True,
    )


@pytest.fixture
def sample_user_permission():
    """
    Create sample user permission record.
    """
    return UserPermissionRecord(
        user_id=AuthorizationTestDataFactory.make_user_id(),
        resource_type=ModelResourceType.API_ENDPOINT,
        resource_name=AuthorizationTestDataFactory.make_api_endpoint_name(),
        access_level=ModelAccessLevel.READ_WRITE,
        permission_source=ModelPermissionSource.ADMIN_GRANT,
        granted_by_user_id=AuthorizationTestDataFactory.make_admin_id(),
        is_active=True,
    )


# ============================================================================
# Test Access Check Integration
# ============================================================================


class TestAccessCheckIntegration:
    """Integration tests for access check flow"""

    async def test_subscription_access_granted(
        self, auth_service, mock_repository, sample_user
    ):
        """Test access granted via subscription tier"""
        # Setup
        resource_name = AuthorizationTestDataFactory.make_api_endpoint_name()
        mock_repository.get_user_info.return_value = sample_user
        mock_repository.get_user_permission.return_value = None
        mock_repository.get_resource_permission.return_value = ResourcePermission(
            resource_type=ModelResourceType.API_ENDPOINT,
            resource_name=resource_name,
            resource_category="utilities",
            subscription_tier_required=ModelSubscriptionTier.PRO,
            access_level=ModelAccessLevel.READ_WRITE,
            is_enabled=True,
        )

        # Act
        request = ResourceAccessRequest(
            user_id=sample_user.user_id,
            resource_type=ModelResourceType.API_ENDPOINT,
            resource_name=resource_name,
            required_access_level=ModelAccessLevel.READ_ONLY,
        )
        result = await auth_service.check_resource_access(request)

        # Assert
        assert result.has_access is True
        assert result.permission_source == ModelPermissionSource.SUBSCRIPTION
        assert result.subscription_tier == "pro"

    async def test_subscription_access_denied_insufficient_tier(
        self, auth_service, mock_repository
    ):
        """Test access denied when subscription tier is insufficient"""
        # Setup - free user trying to access pro resource
        free_user = ExternalServiceUser(
            user_id=AuthorizationTestDataFactory.make_user_id(),
            email=AuthorizationTestDataFactory.make_email(),
            subscription_status="free",
            is_active=True,
            organization_id=None,
        )
        resource_name = AuthorizationTestDataFactory.make_api_endpoint_name()
        mock_repository.get_user_info.return_value = free_user
        mock_repository.get_user_permission.return_value = None
        mock_repository.get_resource_permission.return_value = ResourcePermission(
            resource_type=ModelResourceType.API_ENDPOINT,
            resource_name=resource_name,
            resource_category="utilities",
            subscription_tier_required=ModelSubscriptionTier.PRO,
            access_level=ModelAccessLevel.READ_WRITE,
            is_enabled=True,
        )

        # Act
        request = ResourceAccessRequest(
            user_id=free_user.user_id,
            resource_type=ModelResourceType.API_ENDPOINT,
            resource_name=resource_name,
            required_access_level=ModelAccessLevel.READ_ONLY,
        )
        result = await auth_service.check_resource_access(request)

        # Assert
        assert result.has_access is False
        assert "insufficient" in result.reason.lower()

    async def test_admin_permission_overrides_subscription(
        self, auth_service, mock_repository
    ):
        """Test admin-granted permission takes priority"""
        # Setup - admin grant
        user = ExternalServiceUser(
            user_id=AuthorizationTestDataFactory.make_user_id(),
            email=AuthorizationTestDataFactory.make_email(),
            subscription_status="free",
            is_active=True,
            organization_id=None,
        )
        resource_name = AuthorizationTestDataFactory.make_api_endpoint_name()
        mock_repository.get_user_info.return_value = user
        mock_repository.get_user_permission.return_value = UserPermissionRecord(
            user_id=user.user_id,
            resource_type=ModelResourceType.API_ENDPOINT,
            resource_name=resource_name,
            access_level=ModelAccessLevel.ADMIN,
            permission_source=ModelPermissionSource.ADMIN_GRANT,
            granted_by_user_id=AuthorizationTestDataFactory.make_admin_id(),
            is_active=True,
        )

        # Act
        request = ResourceAccessRequest(
            user_id=user.user_id,
            resource_type=ModelResourceType.API_ENDPOINT,
            resource_name=resource_name,
            required_access_level=ModelAccessLevel.READ_WRITE,
        )
        result = await auth_service.check_resource_access(request)

        # Assert
        assert result.has_access is True
        assert result.permission_source == ModelPermissionSource.ADMIN_GRANT
        assert result.user_access_level == ModelAccessLevel.ADMIN

    async def test_inactive_user_denied(self, auth_service, mock_repository):
        """Test inactive users are denied access"""
        # Setup
        inactive_user = ExternalServiceUser(
            user_id=AuthorizationTestDataFactory.make_user_id(),
            email=AuthorizationTestDataFactory.make_email(),
            subscription_status="pro",
            is_active=False,
            organization_id=None,
        )
        mock_repository.get_user_info.return_value = inactive_user

        # Act
        request = ResourceAccessRequest(
            user_id=inactive_user.user_id,
            resource_type=ModelResourceType.API_ENDPOINT,
            resource_name=AuthorizationTestDataFactory.make_api_endpoint_name(),
            required_access_level=ModelAccessLevel.READ_ONLY,
        )
        result = await auth_service.check_resource_access(request)

        # Assert
        assert result.has_access is False
        assert "inactive" in result.reason.lower()

    async def test_nonexistent_user_denied(self, auth_service, mock_repository):
        """Test access denied for non-existent user"""
        # Setup
        mock_repository.get_user_info.return_value = None

        # Act
        request = ResourceAccessRequest(
            user_id=AuthorizationTestDataFactory.make_nonexistent_user_id(),
            resource_type=ModelResourceType.API_ENDPOINT,
            resource_name=AuthorizationTestDataFactory.make_api_endpoint_name(),
            required_access_level=ModelAccessLevel.READ_ONLY,
        )
        result = await auth_service.check_resource_access(request)

        # Assert
        assert result.has_access is False
        assert "not found" in result.reason.lower()

    async def test_unconfigured_resource_denied(
        self, auth_service, mock_repository, sample_user
    ):
        """Test access denied for unconfigured resource"""
        # Setup
        mock_repository.get_user_info.return_value = sample_user
        mock_repository.get_user_permission.return_value = None
        mock_repository.get_resource_permission.return_value = None

        # Act
        request = ResourceAccessRequest(
            user_id=sample_user.user_id,
            resource_type=ModelResourceType.DATABASE,
            resource_name="unconfigured_db",
            required_access_level=ModelAccessLevel.READ_ONLY,
        )
        result = await auth_service.check_resource_access(request)

        # Assert
        assert result.has_access is False
        # No resource config means insufficient permissions
        assert "insufficient" in result.reason.lower()


# ============================================================================
# Test Permission Grant Integration
# ============================================================================


class TestPermissionGrantIntegration:
    """Integration tests for permission grant flow"""

    async def test_grant_permission_success(
        self, auth_service, mock_repository, mock_event_bus
    ):
        """Test successful permission grant"""
        # Setup
        user_id = AuthorizationTestDataFactory.make_user_id()
        mock_repository.get_user_info.return_value = ExternalServiceUser(
            user_id=user_id,
            email=AuthorizationTestDataFactory.make_email(),
            subscription_status="free",
            is_active=True,
            organization_id=None,
        )
        mock_repository.grant_user_permission.return_value = True
        mock_repository.log_permission_action.return_value = True

        # Act
        request = GrantPermissionRequest(
            user_id=user_id,
            resource_type=ModelResourceType.MCP_TOOL,
            resource_name=AuthorizationTestDataFactory.make_mcp_tool_name(),
            access_level=ModelAccessLevel.READ_WRITE,
            permission_source=ModelPermissionSource.ADMIN_GRANT,
            granted_by_user_id=AuthorizationTestDataFactory.make_admin_id(),
            reason="Test grant",
        )
        result = await auth_service.grant_resource_permission(request)

        # Assert
        assert result is True
        mock_repository.grant_user_permission.assert_called_once()
        mock_event_bus.publish_event.assert_called_once()

    async def test_grant_permission_nonexistent_user_fails(
        self, auth_service, mock_repository
    ):
        """Test grant fails for non-existent user"""
        # Setup
        mock_repository.get_user_info.return_value = None

        # Act
        request = GrantPermissionRequest(
            user_id=AuthorizationTestDataFactory.make_nonexistent_user_id(),
            resource_type=ModelResourceType.MCP_TOOL,
            resource_name=AuthorizationTestDataFactory.make_mcp_tool_name(),
            access_level=ModelAccessLevel.READ_WRITE,
            permission_source=ModelPermissionSource.ADMIN_GRANT,
            granted_by_user_id=AuthorizationTestDataFactory.make_admin_id(),
        )
        result = await auth_service.grant_resource_permission(request)

        # Assert
        assert result is False
        mock_repository.grant_user_permission.assert_not_called()

    async def test_grant_permission_publishes_event(
        self, auth_service, mock_repository, mock_event_bus
    ):
        """Test grant publishes permission.granted event"""
        # Setup
        user_id = AuthorizationTestDataFactory.make_user_id()
        mock_repository.get_user_info.return_value = ExternalServiceUser(
            user_id=user_id,
            email=AuthorizationTestDataFactory.make_email(),
            subscription_status="free",
            is_active=True,
            organization_id=None,
        )
        mock_repository.grant_user_permission.return_value = True
        mock_repository.log_permission_action.return_value = True

        # Act
        request = GrantPermissionRequest(
            user_id=user_id,
            resource_type=ModelResourceType.AI_MODEL,
            resource_name=AuthorizationTestDataFactory.make_ai_model_name(),
            access_level=ModelAccessLevel.READ_ONLY,
            permission_source=ModelPermissionSource.ADMIN_GRANT,
            granted_by_user_id=AuthorizationTestDataFactory.make_admin_id(),
        )
        await auth_service.grant_resource_permission(request)

        # Assert
        mock_event_bus.publish_event.assert_called_once()
        event = mock_event_bus.publish_event.call_args[0][0]
        assert "permission.granted" in str(event.type).lower()


# ============================================================================
# Test Permission Revoke Integration
# ============================================================================


class TestPermissionRevokeIntegration:
    """Integration tests for permission revoke flow"""

    async def test_revoke_permission_success(
        self, auth_service, mock_repository, mock_event_bus
    ):
        """Test successful permission revoke"""
        # Setup
        user_id = AuthorizationTestDataFactory.make_user_id()
        resource_name = AuthorizationTestDataFactory.make_api_endpoint_name()
        mock_repository.get_user_permission.return_value = UserPermissionRecord(
            user_id=user_id,
            resource_type=ModelResourceType.API_ENDPOINT,
            resource_name=resource_name,
            access_level=ModelAccessLevel.READ_WRITE,
            permission_source=ModelPermissionSource.ADMIN_GRANT,
            is_active=True,
        )
        mock_repository.revoke_user_permission.return_value = True
        mock_repository.log_permission_action.return_value = True

        # Act
        request = RevokePermissionRequest(
            user_id=user_id,
            resource_type=ModelResourceType.API_ENDPOINT,
            resource_name=resource_name,
            revoked_by_user_id=AuthorizationTestDataFactory.make_admin_id(),
            reason="Access review",
        )
        result = await auth_service.revoke_resource_permission(request)

        # Assert
        assert result is True
        mock_repository.revoke_user_permission.assert_called_once()
        mock_event_bus.publish_event.assert_called_once()

    async def test_revoke_nonexistent_permission_returns_false(
        self, auth_service, mock_repository
    ):
        """Test revoke returns false for non-existent permission"""
        # Setup
        mock_repository.revoke_user_permission.return_value = False

        # Act
        request = RevokePermissionRequest(
            user_id=AuthorizationTestDataFactory.make_user_id(),
            resource_type=ModelResourceType.API_ENDPOINT,
            resource_name="nonexistent_resource",
            revoked_by_user_id=AuthorizationTestDataFactory.make_admin_id(),
        )
        result = await auth_service.revoke_resource_permission(request)

        # Assert
        assert result is False

    async def test_revoke_permission_publishes_event(
        self, auth_service, mock_repository, mock_event_bus
    ):
        """Test revoke publishes permission.revoked event"""
        # Setup
        user_id = AuthorizationTestDataFactory.make_user_id()
        resource_name = AuthorizationTestDataFactory.make_api_endpoint_name()
        mock_repository.get_user_permission.return_value = UserPermissionRecord(
            user_id=user_id,
            resource_type=ModelResourceType.API_ENDPOINT,
            resource_name=resource_name,
            access_level=ModelAccessLevel.READ_WRITE,
            permission_source=ModelPermissionSource.ADMIN_GRANT,
            is_active=True,
        )
        mock_repository.revoke_user_permission.return_value = True
        mock_repository.log_permission_action.return_value = True

        # Act
        request = RevokePermissionRequest(
            user_id=user_id,
            resource_type=ModelResourceType.API_ENDPOINT,
            resource_name=resource_name,
            revoked_by_user_id=AuthorizationTestDataFactory.make_admin_id(),
        )
        await auth_service.revoke_resource_permission(request)

        # Assert
        mock_event_bus.publish_event.assert_called_once()
        event = mock_event_bus.publish_event.call_args[0][0]
        assert "permission.revoked" in str(event.type).lower()


# ============================================================================
# Test Organization Permission Integration
# ============================================================================


class TestOrganizationPermissionIntegration:
    """Integration tests for organization-based permissions"""

    async def test_organization_access_for_member(
        self, auth_service, mock_repository
    ):
        """Test organization member gets org-level access"""
        # Setup
        org_id = AuthorizationTestDataFactory.make_organization_id()
        user = ExternalServiceUser(
            user_id=AuthorizationTestDataFactory.make_user_id(),
            email=AuthorizationTestDataFactory.make_email(),
            subscription_status="free",
            is_active=True,
            organization_id=org_id,
        )
        resource_name = AuthorizationTestDataFactory.make_api_endpoint_name()

        mock_repository.get_user_info.return_value = user
        mock_repository.get_user_permission.return_value = None
        mock_repository.get_organization_info.return_value = ExternalServiceOrganization(
            organization_id=org_id,
            plan="enterprise",
            is_active=True,
            member_count=10,
        )
        mock_repository.is_user_organization_member.return_value = True
        mock_repository.get_organization_permission.return_value = OrganizationPermission(
            organization_id=org_id,
            resource_type=ModelResourceType.API_ENDPOINT,
            resource_name=resource_name,
            access_level=ModelAccessLevel.READ_WRITE,
            org_plan_required="startup",
            is_enabled=True,
        )

        # Act
        request = ResourceAccessRequest(
            user_id=user.user_id,
            resource_type=ModelResourceType.API_ENDPOINT,
            resource_name=resource_name,
            required_access_level=ModelAccessLevel.READ_ONLY,
            organization_id=org_id,
        )
        result = await auth_service.check_resource_access(request)

        # Assert
        assert result.has_access is True
        assert result.permission_source == ModelPermissionSource.ORGANIZATION

    async def test_organization_access_denied_for_nonmember(
        self, auth_service, mock_repository
    ):
        """Test non-member doesn't get organization access"""
        # Setup
        org_id = AuthorizationTestDataFactory.make_organization_id()
        user = ExternalServiceUser(
            user_id=AuthorizationTestDataFactory.make_user_id(),
            email=AuthorizationTestDataFactory.make_email(),
            subscription_status="free",
            is_active=True,
            organization_id=None,  # Not in organization
        )
        resource_name = AuthorizationTestDataFactory.make_api_endpoint_name()

        mock_repository.get_user_info.return_value = user
        mock_repository.get_user_permission.return_value = None
        mock_repository.is_user_organization_member.return_value = False
        mock_repository.get_resource_permission.return_value = None

        # Act
        request = ResourceAccessRequest(
            user_id=user.user_id,
            resource_type=ModelResourceType.API_ENDPOINT,
            resource_name=resource_name,
            required_access_level=ModelAccessLevel.READ_ONLY,
            organization_id=org_id,
        )
        result = await auth_service.check_resource_access(request)

        # Assert
        assert result.has_access is False


# ============================================================================
# Test Event Publishing Integration
# ============================================================================


class TestEventPublishingIntegration:
    """Integration tests for event publishing"""

    async def test_access_denied_publishes_event(
        self, auth_service, mock_repository, mock_event_bus
    ):
        """Test access denial publishes access.denied event"""
        # Setup
        user = ExternalServiceUser(
            user_id=AuthorizationTestDataFactory.make_user_id(),
            email=AuthorizationTestDataFactory.make_email(),
            subscription_status="free",
            is_active=True,
            organization_id=None,
        )
        mock_repository.get_user_info.return_value = user
        mock_repository.get_user_permission.return_value = None
        mock_repository.get_resource_permission.return_value = None

        # Act
        request = ResourceAccessRequest(
            user_id=user.user_id,
            resource_type=ModelResourceType.DATABASE,
            resource_name="restricted_db",
            required_access_level=ModelAccessLevel.ADMIN,
        )
        await auth_service.check_resource_access(request)

        # Assert
        mock_event_bus.publish_event.assert_called_once()
        event = mock_event_bus.publish_event.call_args[0][0]
        assert "access.denied" in str(event.type).lower()

    async def test_service_works_without_event_bus(self, mock_repository):
        """Test service works gracefully without event bus"""
        # Create service without event bus
        service = AuthorizationService(
            repository=mock_repository,
            event_bus=None,
            config=None,
        )

        user = ExternalServiceUser(
            user_id=AuthorizationTestDataFactory.make_user_id(),
            email=AuthorizationTestDataFactory.make_email(),
            subscription_status="pro",
            is_active=True,
            organization_id=None,
        )
        mock_repository.get_user_info.return_value = user
        mock_repository.get_user_permission.return_value = None
        mock_repository.get_resource_permission.return_value = None

        # Act - should not raise
        request = ResourceAccessRequest(
            user_id=user.user_id,
            resource_type=ModelResourceType.MCP_TOOL,
            resource_name="test_tool",
            required_access_level=ModelAccessLevel.READ_ONLY,
        )
        result = await service.check_resource_access(request)

        # Assert
        assert result is not None
        assert result.has_access is False


# ============================================================================
# Test Permission Summary Integration
# ============================================================================


class TestPermissionSummaryIntegration:
    """Integration tests for permission summary"""

    async def test_get_user_permission_summary(
        self, auth_service, mock_repository
    ):
        """Test getting user permission summary"""
        # Setup
        user_id = AuthorizationTestDataFactory.make_user_id()
        mock_repository.get_user_permission_summary.return_value = UserPermissionSummary(
            user_id=user_id,
            subscription_tier="pro",
            organization_id=None,
            organization_plan=None,
            total_permissions=10,
            permissions_by_type={"api_endpoint": 5, "mcp_tool": 5},
            permissions_by_source={"subscription": 8, "admin_grant": 2},
            permissions_by_level={"read_only": 4, "read_write": 6},
            expires_soon_count=1,
            last_access_check=None,
        )

        # Act
        result = await auth_service.get_user_permission_summary(user_id)

        # Assert
        assert result is not None
        assert result.user_id == user_id
        assert result.total_permissions == 10
        mock_repository.get_user_permission_summary.assert_called_once_with(user_id)


# ============================================================================
# Test Accessible Resources Integration
# ============================================================================


class TestAccessibleResourcesIntegration:
    """Integration tests for listing accessible resources"""

    async def test_list_user_accessible_resources(
        self, auth_service, mock_repository
    ):
        """Test listing user's accessible resources"""
        # Setup
        user_id = AuthorizationTestDataFactory.make_user_id()
        mock_repository.list_user_permissions.return_value = [
            UserPermissionRecord(
                user_id=user_id,
                resource_type=ModelResourceType.API_ENDPOINT,
                resource_name="/api/data",
                access_level=ModelAccessLevel.READ_WRITE,
                permission_source=ModelPermissionSource.SUBSCRIPTION,
                is_active=True,
            ),
            UserPermissionRecord(
                user_id=user_id,
                resource_type=ModelResourceType.MCP_TOOL,
                resource_name="weather_api",
                access_level=ModelAccessLevel.READ_ONLY,
                permission_source=ModelPermissionSource.ADMIN_GRANT,
                is_active=True,
            ),
        ]

        # Act
        result = await auth_service.list_user_accessible_resources(user_id)

        # Assert
        assert result is not None
        mock_repository.list_user_permissions.assert_called_once_with(user_id, None)


# ============================================================================
# Test Error Handling Integration
# ============================================================================


class TestErrorHandlingIntegration:
    """Integration tests for error handling"""

    async def test_repository_error_returns_safe_denial(
        self, auth_service, mock_repository
    ):
        """Test repository error returns safe denial"""
        # Setup
        mock_repository.get_user_info.side_effect = Exception("Database error")

        # Act
        request = ResourceAccessRequest(
            user_id=AuthorizationTestDataFactory.make_user_id(),
            resource_type=ModelResourceType.API_ENDPOINT,
            resource_name="/api/test",
            required_access_level=ModelAccessLevel.READ_ONLY,
        )
        result = await auth_service.check_resource_access(request)

        # Assert - should fail safely, not raise
        assert result.has_access is False
        assert "error" in result.reason.lower() or "failed" in result.reason.lower()

    async def test_grant_with_repository_error(
        self, auth_service, mock_repository
    ):
        """Test grant handles repository error gracefully"""
        # Setup
        user_id = AuthorizationTestDataFactory.make_user_id()
        mock_repository.get_user_info.return_value = ExternalServiceUser(
            user_id=user_id,
            email=AuthorizationTestDataFactory.make_email(),
            subscription_status="free",
            is_active=True,
            organization_id=None,
        )
        mock_repository.grant_user_permission.side_effect = Exception("Database error")

        # Act
        request = GrantPermissionRequest(
            user_id=user_id,
            resource_type=ModelResourceType.API_ENDPOINT,
            resource_name="/api/test",
            access_level=ModelAccessLevel.READ_WRITE,
            permission_source=ModelPermissionSource.ADMIN_GRANT,
            granted_by_user_id=AuthorizationTestDataFactory.make_admin_id(),
        )

        # Should not raise, returns False
        result = await auth_service.grant_resource_permission(request)
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
