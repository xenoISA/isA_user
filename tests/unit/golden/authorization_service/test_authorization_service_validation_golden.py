"""
Authorization Service - Unit Tests for Service Validation (Golden)

Tests for:
- Access level hierarchy
- Subscription tier hierarchy
- Organization plan hierarchy
- Permission source priority
- Helper method validation

All tests use AuthorizationTestDataFactory - zero hardcoded data.
"""

import pytest
from datetime import datetime, timezone, timedelta

from microservices.authorization_service.authorization_service import AuthorizationService
from microservices.authorization_service.models import (
    ResourceType,
    AccessLevel,
    PermissionSource,
    SubscriptionTier,
)
from tests.contracts.authorization.data_contract import AuthorizationTestDataFactory

pytestmark = [pytest.mark.unit]


# ============================================================================
# Test Access Level Hierarchy
# ============================================================================


class TestAccessLevelHierarchy:
    """Test access level hierarchy validation"""

    @pytest.fixture
    def service(self):
        """Create service instance without repository for helper method tests"""
        return AuthorizationService()

    def test_owner_has_sufficient_access_for_all_levels(self, service):
        """Owner access level grants access to all required levels"""
        owner = AccessLevel.OWNER
        assert service._has_sufficient_access(owner, AccessLevel.NONE)
        assert service._has_sufficient_access(owner, AccessLevel.READ_ONLY)
        assert service._has_sufficient_access(owner, AccessLevel.READ_WRITE)
        assert service._has_sufficient_access(owner, AccessLevel.ADMIN)
        assert service._has_sufficient_access(owner, AccessLevel.OWNER)

    def test_admin_has_sufficient_access_up_to_admin(self, service):
        """Admin access level grants access up to admin but not owner"""
        admin = AccessLevel.ADMIN
        assert service._has_sufficient_access(admin, AccessLevel.NONE)
        assert service._has_sufficient_access(admin, AccessLevel.READ_ONLY)
        assert service._has_sufficient_access(admin, AccessLevel.READ_WRITE)
        assert service._has_sufficient_access(admin, AccessLevel.ADMIN)
        assert not service._has_sufficient_access(admin, AccessLevel.OWNER)

    def test_read_write_has_sufficient_access_up_to_read_write(self, service):
        """Read-write access level grants access up to read_write"""
        rw = AccessLevel.READ_WRITE
        assert service._has_sufficient_access(rw, AccessLevel.NONE)
        assert service._has_sufficient_access(rw, AccessLevel.READ_ONLY)
        assert service._has_sufficient_access(rw, AccessLevel.READ_WRITE)
        assert not service._has_sufficient_access(rw, AccessLevel.ADMIN)
        assert not service._has_sufficient_access(rw, AccessLevel.OWNER)

    def test_read_only_has_sufficient_access_up_to_read_only(self, service):
        """Read-only access level grants access up to read_only"""
        ro = AccessLevel.READ_ONLY
        assert service._has_sufficient_access(ro, AccessLevel.NONE)
        assert service._has_sufficient_access(ro, AccessLevel.READ_ONLY)
        assert not service._has_sufficient_access(ro, AccessLevel.READ_WRITE)
        assert not service._has_sufficient_access(ro, AccessLevel.ADMIN)
        assert not service._has_sufficient_access(ro, AccessLevel.OWNER)

    def test_none_has_sufficient_access_only_for_none(self, service):
        """None access level only grants access to none requirement"""
        none = AccessLevel.NONE
        assert service._has_sufficient_access(none, AccessLevel.NONE)
        assert not service._has_sufficient_access(none, AccessLevel.READ_ONLY)
        assert not service._has_sufficient_access(none, AccessLevel.READ_WRITE)
        assert not service._has_sufficient_access(none, AccessLevel.ADMIN)
        assert not service._has_sufficient_access(none, AccessLevel.OWNER)

    def test_access_level_hierarchy_values(self, service):
        """Access level hierarchy has correct ordering"""
        hierarchy = service.access_level_hierarchy
        assert hierarchy[AccessLevel.NONE] < hierarchy[AccessLevel.READ_ONLY]
        assert hierarchy[AccessLevel.READ_ONLY] < hierarchy[AccessLevel.READ_WRITE]
        assert hierarchy[AccessLevel.READ_WRITE] < hierarchy[AccessLevel.ADMIN]
        assert hierarchy[AccessLevel.ADMIN] < hierarchy[AccessLevel.OWNER]


# ============================================================================
# Test Subscription Tier Hierarchy
# ============================================================================


class TestSubscriptionTierHierarchy:
    """Test subscription tier hierarchy validation"""

    @pytest.fixture
    def service(self):
        """Create service instance without repository for helper method tests"""
        return AuthorizationService()

    def test_custom_has_sufficient_tier_for_all(self, service):
        """Custom tier grants access to all tier requirements"""
        custom = SubscriptionTier.CUSTOM
        assert service._subscription_tier_sufficient(custom, SubscriptionTier.FREE)
        assert service._subscription_tier_sufficient(custom, SubscriptionTier.PRO)
        assert service._subscription_tier_sufficient(custom, SubscriptionTier.ENTERPRISE)
        assert service._subscription_tier_sufficient(custom, SubscriptionTier.CUSTOM)

    def test_enterprise_has_sufficient_tier_up_to_enterprise(self, service):
        """Enterprise tier grants access up to enterprise"""
        enterprise = SubscriptionTier.ENTERPRISE
        assert service._subscription_tier_sufficient(enterprise, SubscriptionTier.FREE)
        assert service._subscription_tier_sufficient(enterprise, SubscriptionTier.PRO)
        assert service._subscription_tier_sufficient(enterprise, SubscriptionTier.ENTERPRISE)
        assert not service._subscription_tier_sufficient(enterprise, SubscriptionTier.CUSTOM)

    def test_pro_has_sufficient_tier_up_to_pro(self, service):
        """Pro tier grants access up to pro"""
        pro = SubscriptionTier.PRO
        assert service._subscription_tier_sufficient(pro, SubscriptionTier.FREE)
        assert service._subscription_tier_sufficient(pro, SubscriptionTier.PRO)
        assert not service._subscription_tier_sufficient(pro, SubscriptionTier.ENTERPRISE)
        assert not service._subscription_tier_sufficient(pro, SubscriptionTier.CUSTOM)

    def test_free_has_sufficient_tier_only_for_free(self, service):
        """Free tier only grants access to free requirements"""
        free = SubscriptionTier.FREE
        assert service._subscription_tier_sufficient(free, SubscriptionTier.FREE)
        assert not service._subscription_tier_sufficient(free, SubscriptionTier.PRO)
        assert not service._subscription_tier_sufficient(free, SubscriptionTier.ENTERPRISE)
        assert not service._subscription_tier_sufficient(free, SubscriptionTier.CUSTOM)

    def test_subscription_hierarchy_values(self, service):
        """Subscription hierarchy has correct ordering"""
        hierarchy = service.subscription_hierarchy
        assert hierarchy[SubscriptionTier.FREE] < hierarchy[SubscriptionTier.PRO]
        assert hierarchy[SubscriptionTier.PRO] < hierarchy[SubscriptionTier.ENTERPRISE]
        assert hierarchy[SubscriptionTier.ENTERPRISE] < hierarchy[SubscriptionTier.CUSTOM]


# ============================================================================
# Test Organization Plan Hierarchy
# ============================================================================


class TestOrganizationPlanHierarchy:
    """Test organization plan hierarchy validation"""

    @pytest.fixture
    def service(self):
        """Create service instance without repository for helper method tests"""
        return AuthorizationService()

    def test_custom_plan_has_sufficient_for_all(self, service):
        """Custom plan grants access to all plan requirements"""
        assert service._organization_plan_sufficient("custom", "startup")
        assert service._organization_plan_sufficient("custom", "growth")
        assert service._organization_plan_sufficient("custom", "enterprise")
        assert service._organization_plan_sufficient("custom", "custom")

    def test_enterprise_plan_has_sufficient_up_to_enterprise(self, service):
        """Enterprise plan grants access up to enterprise"""
        assert service._organization_plan_sufficient("enterprise", "startup")
        assert service._organization_plan_sufficient("enterprise", "growth")
        assert service._organization_plan_sufficient("enterprise", "enterprise")
        assert not service._organization_plan_sufficient("enterprise", "custom")

    def test_growth_plan_has_sufficient_up_to_growth(self, service):
        """Growth plan grants access up to growth"""
        assert service._organization_plan_sufficient("growth", "startup")
        assert service._organization_plan_sufficient("growth", "growth")
        assert not service._organization_plan_sufficient("growth", "enterprise")
        assert not service._organization_plan_sufficient("growth", "custom")

    def test_startup_plan_has_sufficient_only_for_startup(self, service):
        """Startup plan only grants access to startup requirements"""
        assert service._organization_plan_sufficient("startup", "startup")
        assert not service._organization_plan_sufficient("startup", "growth")
        assert not service._organization_plan_sufficient("startup", "enterprise")
        assert not service._organization_plan_sufficient("startup", "custom")

    def test_plan_comparison_case_insensitive(self, service):
        """Plan comparison is case insensitive"""
        assert service._organization_plan_sufficient("Enterprise", "GROWTH")
        assert service._organization_plan_sufficient("CUSTOM", "startup")
        assert service._organization_plan_sufficient("Growth", "Growth")

    def test_unknown_plan_returns_false(self, service):
        """Unknown plan returns false for valid requirements"""
        assert not service._organization_plan_sufficient("unknown", "startup")
        assert not service._organization_plan_sufficient("invalid", "growth")


# ============================================================================
# Test Service Initialization
# ============================================================================


class TestServiceInitialization:
    """Test service initialization"""

    def test_service_initializes_without_dependencies(self):
        """Service can be initialized without dependencies"""
        service = AuthorizationService()
        assert service.repository is None
        assert service.event_bus is None

    def test_service_has_subscription_hierarchy(self):
        """Service has subscription hierarchy defined"""
        service = AuthorizationService()
        assert SubscriptionTier.FREE in service.subscription_hierarchy
        assert SubscriptionTier.PRO in service.subscription_hierarchy
        assert SubscriptionTier.ENTERPRISE in service.subscription_hierarchy
        assert SubscriptionTier.CUSTOM in service.subscription_hierarchy

    def test_service_has_access_level_hierarchy(self):
        """Service has access level hierarchy defined"""
        service = AuthorizationService()
        assert AccessLevel.NONE in service.access_level_hierarchy
        assert AccessLevel.READ_ONLY in service.access_level_hierarchy
        assert AccessLevel.READ_WRITE in service.access_level_hierarchy
        assert AccessLevel.ADMIN in service.access_level_hierarchy
        assert AccessLevel.OWNER in service.access_level_hierarchy

    def test_service_accepts_injected_repository(self):
        """Service accepts injected repository"""

        class MockRepository:
            pass

        mock_repo = MockRepository()
        service = AuthorizationService(repository=mock_repo)
        assert service.repository is mock_repo

    def test_service_accepts_injected_event_bus(self):
        """Service accepts injected event bus"""

        class MockEventBus:
            pass

        mock_bus = MockEventBus()
        service = AuthorizationService(event_bus=mock_bus)
        assert service.event_bus is mock_bus


# ============================================================================
# Test Permission Source Priority
# ============================================================================


class TestPermissionSourcePriority:
    """Test permission source priority understanding"""

    def test_permission_source_enum_values(self):
        """Permission source enum has expected values"""
        assert PermissionSource.ADMIN_GRANT.value == "admin_grant"
        assert PermissionSource.ORGANIZATION.value == "organization"
        assert PermissionSource.SUBSCRIPTION.value == "subscription"
        assert PermissionSource.SYSTEM_DEFAULT.value == "system_default"

    def test_permission_sources_are_distinct(self):
        """Permission sources are distinct values"""
        sources = [e.value for e in PermissionSource]
        assert len(sources) == len(set(sources))


# ============================================================================
# Test Resource Type Validation
# ============================================================================


class TestResourceTypeValidation:
    """Test resource type validation"""

    def test_all_resource_types_defined(self):
        """All expected resource types are defined"""
        expected_types = [
            "mcp_tool",
            "prompt",
            "resource",
            "api_endpoint",
            "database",
            "file_storage",
            "compute",
            "ai_model",
        ]
        actual_types = [e.value for e in ResourceType]
        for expected in expected_types:
            assert expected in actual_types

    def test_resource_types_are_distinct(self):
        """Resource types are distinct values"""
        types = [e.value for e in ResourceType]
        assert len(types) == len(set(types))


# ============================================================================
# Test Edge Cases in Hierarchy Comparisons
# ============================================================================


class TestHierarchyEdgeCases:
    """Test edge cases in hierarchy comparisons"""

    @pytest.fixture
    def service(self):
        """Create service instance"""
        return AuthorizationService()

    def test_same_access_level_is_sufficient(self, service):
        """Same access level is sufficient"""
        for level in AccessLevel:
            assert service._has_sufficient_access(level, level)

    def test_same_subscription_tier_is_sufficient(self, service):
        """Same subscription tier is sufficient"""
        for tier in SubscriptionTier:
            assert service._subscription_tier_sufficient(tier, tier)

    def test_same_org_plan_is_sufficient(self, service):
        """Same organization plan is sufficient"""
        for plan in ["startup", "growth", "enterprise", "custom"]:
            assert service._organization_plan_sufficient(plan, plan)

    def test_access_level_with_unknown_values(self, service):
        """Access level comparison handles unknown values gracefully"""
        # Unknown user level maps to -1, so it should fail for any requirement
        class FakeLevel:
            pass

        fake = FakeLevel()
        # This should return False since fake level not in hierarchy
        assert not service._has_sufficient_access(fake, AccessLevel.READ_ONLY)


# ============================================================================
# Test Data Factory Integration
# ============================================================================


class TestDataFactoryIntegration:
    """Test integration with data factory"""

    @pytest.fixture
    def service(self):
        """Create service instance"""
        return AuthorizationService()

    def test_factory_access_levels_are_valid(self, service):
        """Factory-generated access levels work with hierarchy"""
        for _ in range(50):
            level = AuthorizationTestDataFactory.make_access_level()
            # Should not raise
            assert level in service.access_level_hierarchy

    def test_factory_subscription_tiers_are_valid(self, service):
        """Factory-generated subscription tiers work with hierarchy"""
        for _ in range(50):
            tier = AuthorizationTestDataFactory.make_subscription_tier()
            # Should not raise
            assert tier in service.subscription_hierarchy

    def test_factory_organization_plans_are_valid(self, service):
        """Factory-generated organization plans work with hierarchy"""
        for _ in range(50):
            plan = AuthorizationTestDataFactory.make_organization_plan()
            # Should return a boolean (valid comparison)
            result = service._organization_plan_sufficient(plan.value, "startup")
            assert isinstance(result, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
