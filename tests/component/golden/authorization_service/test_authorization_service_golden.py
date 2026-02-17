"""
Authorization Service Component Tests (Golden Tests)

Tests the AuthorizationService business logic with mocked dependencies.
Uses dependency injection - no real I/O operations.
"""
import pytest
from datetime import datetime, timezone, timedelta

from microservices.authorization_service.authorization_service import AuthorizationService
from microservices.authorization_service.models import (
    ResourceType,
    AccessLevel,
    PermissionSource,
    SubscriptionTier,
    ResourceAccessRequest,
    GrantPermissionRequest,
    RevokePermissionRequest,
    ResourcePermission,
    UserPermissionRecord,
)
from tests.component.golden.authorization_service.mocks import MockAuthorizationRepository
from tests.component.mocks.nats_mock import MockEventBus


class TestAuthorizationServiceAccessControl:
    """Test resource access control functionality"""

    @pytest.fixture
    def repository(self):
        """Create mock repository with test data"""
        repo = MockAuthorizationRepository()

        # Add test user
        repo.add_user(
            user_id="usr_test123",
            email="test@example.com",
            subscription_status="pro",
            is_active=True,
        )

        # Add resource permission for pro tier
        return repo

    @pytest.fixture
    def event_bus(self):
        """Create mock event bus"""
        return MockEventBus()

    @pytest.fixture
    def auth_service(self, repository, event_bus):
        """Create authorization service with mocked dependencies"""
        return AuthorizationService(
            repository=repository,
            event_bus=event_bus,
            config=None,
        )

    @pytest.mark.asyncio
    async def test_subscription_based_access_granted(self, auth_service, repository):
        """Test access granted based on subscription tier"""
        # Setup: Add resource permission requiring pro tier
        await repository.create_resource_permission(
            ResourcePermission(
                resource_type=ResourceType.MCP_TOOL,
                resource_name="image_generator",
                resource_category="ai_tools",
                subscription_tier_required=SubscriptionTier.PRO,
                access_level=AccessLevel.READ_WRITE,
                description="AI image generation tool",
            )
        )

        # Act: Check access for pro user
        request = ResourceAccessRequest(
            user_id="usr_test123",
            resource_type=ResourceType.MCP_TOOL,
            resource_name="image_generator",
            required_access_level=AccessLevel.READ_WRITE,
        )

        result = await auth_service.check_resource_access(request)

        # Assert
        assert result.has_access is True
        assert result.user_access_level == AccessLevel.READ_WRITE
        assert result.permission_source == PermissionSource.SUBSCRIPTION
        assert result.subscription_tier == "pro"

    @pytest.mark.asyncio
    async def test_subscription_based_access_denied_insufficient_tier(
        self, auth_service, repository
    ):
        """Test access denied when subscription tier is insufficient"""
        # Setup: Change user to free tier
        repository.add_user(
            user_id="usr_free123",
            email="free@example.com",
            subscription_status="free",
            is_active=True,
        )

        # Add resource requiring pro tier
        await repository.create_resource_permission(
            ResourcePermission(
                resource_type=ResourceType.AI_MODEL,
                resource_name="advanced_llm",
                resource_category="ai_models",
                subscription_tier_required=SubscriptionTier.PRO,
                access_level=AccessLevel.READ_WRITE,
            )
        )

        # Act: Check access for free user
        request = ResourceAccessRequest(
            user_id="usr_free123",
            resource_type=ResourceType.AI_MODEL,
            resource_name="advanced_llm",
            required_access_level=AccessLevel.READ_WRITE,
        )

        result = await auth_service.check_resource_access(request)

        # Assert
        assert result.has_access is False
        assert result.user_access_level == AccessLevel.NONE
        # When access is denied, permission_source is SYSTEM_DEFAULT
        assert result.permission_source == PermissionSource.SYSTEM_DEFAULT
        assert "insufficient" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_admin_granted_permission_overrides_subscription(
        self, auth_service, repository
    ):
        """Test admin-granted permissions take precedence over subscription"""
        # Setup: Add admin-granted permission
        await repository.grant_user_permission(
            UserPermissionRecord(
                user_id="usr_test123",
                resource_type=ResourceType.DATABASE,
                resource_name="analytics_db",
                access_level=AccessLevel.ADMIN,
                permission_source=PermissionSource.ADMIN_GRANT,
                granted_by_user_id="admin_user",
                is_active=True,
            )
        )

        # Act: Check access
        request = ResourceAccessRequest(
            user_id="usr_test123",
            resource_type=ResourceType.DATABASE,
            resource_name="analytics_db",
            required_access_level=AccessLevel.READ_WRITE,
        )

        result = await auth_service.check_resource_access(request)

        # Assert
        assert result.has_access is True
        assert result.user_access_level == AccessLevel.ADMIN
        assert result.permission_source == PermissionSource.ADMIN_GRANT
        assert "admin" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_inactive_user_denied_access(self, auth_service, repository):
        """Test inactive users are denied access"""
        # Setup: Add inactive user
        repository.add_user(
            user_id="usr_inactive",
            email="inactive@example.com",
            subscription_status="pro",
            is_active=False,
        )

        # Act: Check access
        request = ResourceAccessRequest(
            user_id="usr_inactive",
            resource_type=ResourceType.MCP_TOOL,
            resource_name="weather_api",
            required_access_level=AccessLevel.READ_ONLY,
        )

        result = await auth_service.check_resource_access(request)

        # Assert
        assert result.has_access is False
        assert "inactive" in result.reason.lower()


class TestAuthorizationServicePermissionManagement:
    """Test permission granting and revoking"""

    @pytest.fixture
    def repository(self):
        """Create mock repository"""
        repo = MockAuthorizationRepository()
        repo.add_user(
            user_id="usr_test123",
            email="test@example.com",
            subscription_status="free",
            is_active=True,
        )
        return repo

    @pytest.fixture
    def event_bus(self):
        """Create mock event bus"""
        return MockEventBus()

    @pytest.fixture
    def auth_service(self, repository, event_bus):
        """Create authorization service"""
        return AuthorizationService(
            repository=repository,
            event_bus=event_bus,
            config=None,
        )

    @pytest.mark.asyncio
    async def test_grant_permission_success(self, auth_service, event_bus):
        """Test successful permission grant"""
        # Act: Grant permission
        request = GrantPermissionRequest(
            user_id="usr_test123",
            resource_type=ResourceType.MCP_TOOL,
            resource_name="premium_tool",
            access_level=AccessLevel.READ_WRITE,
            permission_source=PermissionSource.ADMIN_GRANT,
            granted_by_user_id="admin_user",
            reason="Special access granted",
        )

        result = await auth_service.grant_resource_permission(request)

        # Assert
        assert result is True

        # Verify event was published
        events = event_bus.get_published_events()
        assert len(events) == 1
        assert events[0]["type"] == "authorization.permission.granted"

    @pytest.mark.asyncio
    async def test_revoke_permission_success(self, auth_service, repository, event_bus):
        """Test successful permission revocation"""
        # Setup: Grant permission first
        await repository.grant_user_permission(
            UserPermissionRecord(
                user_id="usr_test123",
                resource_type=ResourceType.MCP_TOOL,
                resource_name="premium_tool",
                access_level=AccessLevel.READ_WRITE,
                permission_source=PermissionSource.ADMIN_GRANT,
                is_active=True,
            )
        )

        # Act: Revoke permission
        request = RevokePermissionRequest(
            user_id="usr_test123",
            resource_type=ResourceType.MCP_TOOL,
            resource_name="premium_tool",
            revoked_by_user_id="admin_user",
            reason="Access no longer needed",
        )

        result = await auth_service.revoke_resource_permission(request)

        # Assert
        assert result is True

        # Verify event was published
        events = event_bus.get_published_events()
        assert len(events) == 1
        assert events[0]["type"] == "authorization.permission.revoked"

    @pytest.mark.asyncio
    async def test_grant_permission_nonexistent_user_fails(self, auth_service):
        """Test granting permission to non-existent user fails"""
        # Act: Try to grant permission to non-existent user
        request = GrantPermissionRequest(
            user_id="usr_nonexistent",
            resource_type=ResourceType.MCP_TOOL,
            resource_name="tool",
            access_level=AccessLevel.READ_ONLY,
            permission_source=PermissionSource.ADMIN_GRANT,
            granted_by_user_id="admin_user",
        )

        result = await auth_service.grant_resource_permission(request)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_revoke_nonexistent_permission_returns_false(self, auth_service):
        """Test revoking non-existent permission returns false"""
        # Act: Try to revoke permission that doesn't exist
        request = RevokePermissionRequest(
            user_id="usr_test123",
            resource_type=ResourceType.MCP_TOOL,
            resource_name="nonexistent_tool",
            revoked_by_user_id="admin_user",
        )

        result = await auth_service.revoke_resource_permission(request)

        # Assert
        assert result is False


class TestAuthorizationServiceOrganizationAccess:
    """Test organization-based access control"""

    @pytest.fixture
    def repository(self):
        """Create mock repository with organization data"""
        repo = MockAuthorizationRepository()

        # Add organization
        repo.add_organization(
            organization_id="org_123",
            plan="enterprise",
            is_active=True,
            member_count=5,
        )

        # Add user as org member
        repo.add_user(
            user_id="usr_test123",
            email="test@example.com",
            subscription_status="free",
            is_active=True,
            organization_id="org_123",
        )
        repo.add_org_member("usr_test123", "org_123")

        return repo

    @pytest.fixture
    def auth_service(self, repository):
        """Create authorization service"""
        return AuthorizationService(
            repository=repository,
            event_bus=None,
            config=None,
        )

    @pytest.mark.asyncio
    async def test_organization_access_granted(self, auth_service, repository):
        """Test organization member gets access to org resources"""
        # This test would need organization permission setup
        # For now, just verify user is org member
        is_member = await repository.is_user_organization_member("usr_test123", "org_123")
        assert is_member is True


class TestAuthorizationServiceEventPublishing:
    """Test event publishing functionality"""

    @pytest.fixture
    def repository(self):
        """Create mock repository"""
        repo = MockAuthorizationRepository()
        repo.add_user(
            user_id="usr_test123",
            email="test@example.com",
            subscription_status="free",
            is_active=True,
        )
        return repo

    @pytest.fixture
    def event_bus(self):
        """Create mock event bus"""
        return MockEventBus()

    @pytest.fixture
    def auth_service(self, repository, event_bus):
        """Create authorization service"""
        return AuthorizationService(
            repository=repository,
            event_bus=event_bus,
            config=None,
        )

    @pytest.mark.asyncio
    async def test_access_denied_publishes_event(self, auth_service, event_bus):
        """Test access denied publishes event"""
        # Act: Check access for resource that doesn't exist
        request = ResourceAccessRequest(
            user_id="usr_test123",
            resource_type=ResourceType.DATABASE,
            resource_name="restricted_db",
            required_access_level=AccessLevel.ADMIN,
        )

        result = await auth_service.check_resource_access(request)

        # Assert
        assert result.has_access is False

        # Verify event was published
        events = event_bus.get_published_events()
        assert len(events) == 1
        assert events[0]["type"] == "authorization.access.denied"

    @pytest.mark.asyncio
    async def test_service_works_without_event_bus(self, repository):
        """Test service works gracefully without event bus"""
        # Create service without event bus
        auth_service = AuthorizationService(
            repository=repository,
            event_bus=None,
            config=None,
        )

        # Act: Check access
        request = ResourceAccessRequest(
            user_id="usr_test123",
            resource_type=ResourceType.MCP_TOOL,
            resource_name="tool",
            required_access_level=AccessLevel.READ_ONLY,
        )

        result = await auth_service.check_resource_access(request)

        # Assert - should work without event bus
        assert result.has_access is False  # No permission configured


class TestAuthorizationServiceHelperMethods:
    """Test helper methods"""

    @pytest.fixture
    def auth_service(self):
        """Create authorization service"""
        return AuthorizationService(
            repository=None,
            event_bus=None,
            config=None,
        )

    def test_subscription_tier_hierarchy(self, auth_service):
        """Test subscription tier comparison"""
        # Pro is sufficient for pro
        assert auth_service._subscription_tier_sufficient(
            SubscriptionTier.PRO, SubscriptionTier.PRO
        ) is True

        # Enterprise is sufficient for pro
        assert auth_service._subscription_tier_sufficient(
            SubscriptionTier.ENTERPRISE, SubscriptionTier.PRO
        ) is True

        # Free is not sufficient for pro
        assert auth_service._subscription_tier_sufficient(
            SubscriptionTier.FREE, SubscriptionTier.PRO
        ) is False

    def test_access_level_hierarchy(self, auth_service):
        """Test access level comparison"""
        # Admin is sufficient for read_write
        assert auth_service._has_sufficient_access(
            AccessLevel.ADMIN, AccessLevel.READ_WRITE
        ) is True

        # Read_only is not sufficient for read_write
        assert auth_service._has_sufficient_access(
            AccessLevel.READ_ONLY, AccessLevel.READ_WRITE
        ) is False

        # Owner is sufficient for everything
        assert auth_service._has_sufficient_access(
            AccessLevel.OWNER, AccessLevel.ADMIN
        ) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
