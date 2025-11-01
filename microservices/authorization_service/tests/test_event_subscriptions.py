#!/usr/bin/env python3
"""
Test Authorization Service Event Subscriptions

Tests that authorization service correctly handles events from other services
"""

import asyncio
import sys
import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from microservices.authorization_service.events.handlers import AuthorizationEventHandlers
from microservices.authorization_service.authorization_service import AuthorizationService
from microservices.authorization_service.models import (
    ResourceType, AccessLevel, PermissionSource, UserPermissionRecord
)
from core.nats_client import Event, EventType, ServiceSource


class MockAuthorizationRepository:
    """Mock repository for testing"""

    def __init__(self):
        self.permissions = {}
        self.revoked_permissions = []
        self.granted_permissions = []

    async def list_user_permissions(self, user_id, resource_type=None):
        """Mock list user permissions"""
        if user_id not in self.permissions:
            return []

        perms = self.permissions[user_id]
        if resource_type:
            return [p for p in perms if p.resource_type == resource_type]
        return perms

    async def revoke_user_permission(self, user_id, resource_type, resource_name):
        """Mock revoke user permission"""
        self.revoked_permissions.append({
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_name": resource_name
        })

        # Remove from permissions
        if user_id in self.permissions:
            self.permissions[user_id] = [
                p for p in self.permissions[user_id]
                if not (p.resource_type == resource_type and p.resource_name == resource_name)
            ]
        return True

    async def grant_user_permission(self, permission):
        """Mock grant user permission"""
        self.granted_permissions.append(permission)

        # Add to permissions
        if permission.user_id not in self.permissions:
            self.permissions[permission.user_id] = []
        self.permissions[permission.user_id].append(permission)
        return permission

    async def get_user_permission(self, user_id, resource_type, resource_name):
        """Mock get user permission"""
        if user_id not in self.permissions:
            return None

        for perm in self.permissions[user_id]:
            if perm.resource_type == resource_type and perm.resource_name == resource_name:
                return perm
        return None

    async def list_organization_permissions(self, organization_id):
        """Mock list organization permissions"""
        # Return some mock organization permissions
        from microservices.authorization_service.models import OrganizationPermission
        return [
            OrganizationPermission(
                organization_id=organization_id,
                resource_type=ResourceType.FILE_STORAGE,
                resource_name="shared_storage",
                access_level=AccessLevel.READ_WRITE,
                org_plan_required="team",
                is_enabled=True,
                created_by_user_id="admin"
            ),
            OrganizationPermission(
                organization_id=organization_id,
                resource_type=ResourceType.AI_MODEL,
                resource_name="shared_ai_models",
                access_level=AccessLevel.READ_ONLY,
                org_plan_required="team",
                is_enabled=True,
                created_by_user_id="admin"
            )
        ]


class MockAuthorizationService:
    """Mock authorization service for testing"""

    def __init__(self):
        self.repository = MockAuthorizationRepository()


async def test_user_deleted_event():
    """Test handling of user.deleted event - should cleanup all user permissions"""
    print("\n" + "="*60)
    print("TEST 1: User Deleted Event Handler")
    print("="*60)

    # Create mock service and handlers
    mock_service = MockAuthorizationService()
    handlers = AuthorizationEventHandlers(mock_service)

    # Setup: Add some permissions for the user
    user_id = "user_123"
    mock_service.repository.permissions[user_id] = [
        UserPermissionRecord(
            user_id=user_id,
            resource_type=ResourceType.FILE_STORAGE,
            resource_name="personal_storage",
            access_level=AccessLevel.READ_WRITE,
            permission_source=PermissionSource.ADMIN_GRANT,
            granted_by_user_id="admin",
            is_active=True
        ),
        UserPermissionRecord(
            user_id=user_id,
            resource_type=ResourceType.AI_MODEL,
            resource_name="gpt4_access",
            access_level=AccessLevel.READ_WRITE,
            permission_source=PermissionSource.ADMIN_GRANT,
            granted_by_user_id="admin",
            is_active=True
        ),
        UserPermissionRecord(
            user_id=user_id,
            resource_type=ResourceType.DATABASE,
            resource_name="user_database",
            access_level=AccessLevel.READ_ONLY,
            permission_source=PermissionSource.ORGANIZATION,
            granted_by_user_id="org_admin",
            is_active=True
        )
    ]

    print(f"📋 Initial permissions for user {user_id}: {len(mock_service.repository.permissions[user_id])}")

    # Create user.deleted event
    event_data = {
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat()
    }

    # Handle event
    print(f"🔥 Triggering user.deleted event for user: {user_id}")
    await handlers.handle_user_deleted(event_data)

    # Verify all permissions were revoked
    print(f"✅ Revoked permissions: {len(mock_service.repository.revoked_permissions)}")
    print(f"✅ Remaining permissions: {len(mock_service.repository.permissions.get(user_id, []))}")

    assert len(mock_service.repository.revoked_permissions) == 3, \
        f"Expected 3 permissions revoked, got {len(mock_service.repository.revoked_permissions)}"
    assert len(mock_service.repository.permissions.get(user_id, [])) == 0, \
        f"Expected 0 remaining permissions, got {len(mock_service.repository.permissions.get(user_id, []))}"

    print("✅ TEST PASSED: All user permissions cleaned up successfully")
    return True


async def test_org_member_added_event():
    """Test handling of organization.member_added event - should auto-grant organization permissions"""
    print("\n" + "="*60)
    print("TEST 2: Organization Member Added Event Handler")
    print("="*60)

    # Create mock service and handlers
    mock_service = MockAuthorizationService()
    handlers = AuthorizationEventHandlers(mock_service)

    # Create organization.member_added event
    organization_id = "org_456"
    user_id = "user_789"
    event_data = {
        "organization_id": organization_id,
        "user_id": user_id,
        "role": "member",
        "added_by": "org_admin",
        "timestamp": datetime.utcnow().isoformat()
    }

    print(f"👥 Adding user {user_id} to organization {organization_id}")
    print(f"📋 Organization has {len(await mock_service.repository.list_organization_permissions(organization_id))} configured permissions")

    # Handle event
    await handlers.handle_org_member_added(event_data)

    # Verify permissions were granted
    granted_count = len(mock_service.repository.granted_permissions)
    user_permissions = mock_service.repository.permissions.get(user_id, [])

    print(f"✅ Granted {granted_count} permissions to user")
    print(f"✅ User now has {len(user_permissions)} total permissions")

    # Verify correct permissions were granted
    assert granted_count == 2, f"Expected 2 permissions granted, got {granted_count}"
    assert len(user_permissions) == 2, f"Expected 2 user permissions, got {len(user_permissions)}"

    # Verify permission details
    for perm in user_permissions:
        assert perm.permission_source == PermissionSource.ORGANIZATION, \
            f"Expected ORGANIZATION source, got {perm.permission_source}"
        assert perm.organization_id == organization_id, \
            f"Expected org_id {organization_id}, got {perm.organization_id}"
        print(f"   - {perm.resource_type.value}:{perm.resource_name} ({perm.access_level.value})")

    print("✅ TEST PASSED: Organization permissions auto-granted successfully")
    return True


async def test_org_member_removed_event():
    """Test handling of organization.member_removed event - should revoke organization permissions"""
    print("\n" + "="*60)
    print("TEST 3: Organization Member Removed Event Handler")
    print("="*60)

    # Create mock service and handlers
    mock_service = MockAuthorizationService()
    handlers = AuthorizationEventHandlers(mock_service)

    # Setup: Add organization-sourced permissions for the user
    organization_id = "org_456"
    user_id = "user_789"
    mock_service.repository.permissions[user_id] = [
        UserPermissionRecord(
            user_id=user_id,
            resource_type=ResourceType.FILE_STORAGE,
            resource_name="shared_storage",
            access_level=AccessLevel.READ_WRITE,
            permission_source=PermissionSource.ORGANIZATION,
            granted_by_user_id="org_admin",
            organization_id=organization_id,
            is_active=True
        ),
        UserPermissionRecord(
            user_id=user_id,
            resource_type=ResourceType.AI_MODEL,
            resource_name="shared_ai_models",
            access_level=AccessLevel.READ_ONLY,
            permission_source=PermissionSource.ORGANIZATION,
            granted_by_user_id="org_admin",
            organization_id=organization_id,
            is_active=True
        ),
        UserPermissionRecord(
            user_id=user_id,
            resource_type=ResourceType.DATABASE,
            resource_name="personal_database",
            access_level=AccessLevel.OWNER,
            permission_source=PermissionSource.ADMIN_GRANT,  # Not from organization
            granted_by_user_id="admin",
            is_active=True
        )
    ]

    initial_count = len(mock_service.repository.permissions[user_id])
    print(f"📋 User has {initial_count} permissions (2 from organization, 1 personal)")

    # Create organization.member_removed event
    event_data = {
        "organization_id": organization_id,
        "user_id": user_id,
        "removed_by": "org_admin",
        "timestamp": datetime.utcnow().isoformat()
    }

    print(f"🚫 Removing user {user_id} from organization {organization_id}")

    # Handle event
    await handlers.handle_org_member_removed(event_data)

    # Verify organization permissions were revoked
    revoked_count = len(mock_service.repository.revoked_permissions)
    remaining_permissions = mock_service.repository.permissions.get(user_id, [])

    print(f"✅ Revoked {revoked_count} organization permissions")
    print(f"✅ User still has {len(remaining_permissions)} personal permissions")

    # Should have revoked 2 organization permissions
    assert revoked_count == 2, f"Expected 2 permissions revoked, got {revoked_count}"

    # Should still have 1 personal permission
    assert len(remaining_permissions) == 1, \
        f"Expected 1 remaining permission, got {len(remaining_permissions)}"
    assert remaining_permissions[0].permission_source == PermissionSource.ADMIN_GRANT, \
        "Remaining permission should be admin-granted, not organization"

    print("✅ TEST PASSED: Organization permissions revoked, personal permissions retained")
    return True


async def test_duplicate_permission_grant():
    """Test that duplicate permissions are not granted when user is added to organization"""
    print("\n" + "="*60)
    print("TEST 4: Duplicate Permission Prevention")
    print("="*60)

    # Create mock service and handlers
    mock_service = MockAuthorizationService()
    handlers = AuthorizationEventHandlers(mock_service)

    # Setup: User already has one of the organization permissions
    organization_id = "org_456"
    user_id = "user_789"
    mock_service.repository.permissions[user_id] = [
        UserPermissionRecord(
            user_id=user_id,
            resource_type=ResourceType.FILE_STORAGE,
            resource_name="shared_storage",
            access_level=AccessLevel.READ_WRITE,
            permission_source=PermissionSource.ADMIN_GRANT,  # Already granted by admin
            granted_by_user_id="admin",
            is_active=True
        )
    ]

    print(f"📋 User already has 1 permission (shared_storage - FILE_STORAGE)")

    # Create organization.member_added event
    event_data = {
        "organization_id": organization_id,
        "user_id": user_id,
        "role": "member",
        "added_by": "org_admin",
        "timestamp": datetime.utcnow().isoformat()
    }

    # Handle event
    await handlers.handle_org_member_added(event_data)

    # Verify only NEW permissions were granted
    granted_count = len(mock_service.repository.granted_permissions)
    user_permissions = mock_service.repository.permissions.get(user_id, [])

    print(f"✅ Granted {granted_count} new permissions (skipped duplicate)")
    print(f"✅ User now has {len(user_permissions)} total permissions")

    # Should only grant 1 new permission (shared_devices), skipping shared_storage
    assert granted_count == 1, f"Expected 1 new permission granted, got {granted_count}"
    assert len(user_permissions) == 2, f"Expected 2 total permissions, got {len(user_permissions)}"

    print("✅ TEST PASSED: Duplicate permissions prevented successfully")
    return True


async def test_missing_event_data():
    """Test that handlers gracefully handle missing event data"""
    print("\n" + "="*60)
    print("TEST 5: Missing Event Data Handling")
    print("="*60)

    # Create mock service and handlers
    mock_service = MockAuthorizationService()
    handlers = AuthorizationEventHandlers(mock_service)

    # Test user.deleted with missing user_id
    print("🧪 Testing user.deleted with missing user_id")
    await handlers.handle_user_deleted({})
    assert len(mock_service.repository.revoked_permissions) == 0, \
        "Should not revoke anything when user_id is missing"
    print("✅ Handled missing user_id gracefully")

    # Test org.member_added with missing organization_id
    print("🧪 Testing org.member_added with missing organization_id")
    await handlers.handle_org_member_added({"user_id": "user_123"})
    assert len(mock_service.repository.granted_permissions) == 0, \
        "Should not grant anything when organization_id is missing"
    print("✅ Handled missing organization_id gracefully")

    # Test org.member_removed with missing user_id
    print("🧪 Testing org.member_removed with missing user_id")
    await handlers.handle_org_member_removed({"organization_id": "org_456"})
    assert len(mock_service.repository.revoked_permissions) == 0, \
        "Should not revoke anything when user_id is missing"
    print("✅ Handled missing user_id gracefully")

    print("✅ TEST PASSED: All edge cases handled gracefully")
    return True


async def run_all_tests():
    """Run all authorization service event subscription tests"""
    print("\n" + "🔒" * 30)
    print("AUTHORIZATION SERVICE EVENT SUBSCRIPTION TESTS")
    print("🔒" * 30)

    tests = [
        ("User Deleted Event", test_user_deleted_event),
        ("Organization Member Added Event", test_org_member_added_event),
        ("Organization Member Removed Event", test_org_member_removed_event),
        ("Duplicate Permission Prevention", test_duplicate_permission_grant),
        ("Missing Event Data Handling", test_missing_event_data),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, "PASSED" if result else "FAILED"))
        except Exception as e:
            print(f"❌ TEST FAILED: {test_name}")
            print(f"   Error: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append((test_name, "FAILED"))

    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(1 for _, status in results if status == "PASSED")
    total = len(results)

    for test_name, status in results:
        emoji = "✅" if status == "PASSED" else "❌"
        print(f"{emoji} {test_name}: {status}")

    print(f"\n📊 Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        return True
    else:
        print("⚠️  SOME TESTS FAILED")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
