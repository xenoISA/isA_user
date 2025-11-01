"""
Authorization Service Event Publishing Tests

Tests that Authorization Service correctly publishes events for all authorization operations
"""
import asyncio
import sys
import os
from datetime import datetime
from typing import Optional, Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from core.nats_client import Event, EventType, ServiceSource
from microservices.authorization_service.authorization_service import AuthorizationService
from microservices.authorization_service.models import (
    ResourceAccessRequest, GrantPermissionRequest, RevokePermissionRequest,
    ResourceType, AccessLevel, PermissionSource
)


class MockEventBus:
    """Mock event bus for testing"""

    def __init__(self):
        self.published_events = []

    async def publish_event(self, event: Event):
        """Mock publish event"""
        self.published_events.append(event)

    def get_events_by_type(self, event_type: str):
        """Get events by type"""
        return [e for e in self.published_events if e.type == event_type]

    def clear(self):
        """Clear published events"""
        self.published_events = []


class MockAuthorizationRepository:
    """Mock authorization repository for testing"""

    def __init__(self):
        self.user_permissions = {}
        self.users = {}

    async def get_user_info(self, user_id: str):
        """Get user info"""
        if user_id not in self.users:
            return None

        class MockUserInfo:
            def __init__(self, user_id, is_active=True):
                self.user_id = user_id
                self.is_active = is_active
                self.subscription_status = "pro"
                self.organization_id = None

        return MockUserInfo(user_id)

    async def get_user_permission(self, user_id: str, resource_type, resource_name: str):
        """Get user permission"""
        key = f"{user_id}:{resource_type.value}:{resource_name}"
        return self.user_permissions.get(key)

    async def grant_user_permission(self, permission):
        """Grant user permission"""
        key = f"{permission.user_id}:{permission.resource_type.value}:{permission.resource_name}"
        self.user_permissions[key] = permission
        return True

    async def revoke_user_permission(self, user_id: str, resource_type, resource_name: str):
        """Revoke user permission"""
        key = f"{user_id}:{resource_type.value}:{resource_name}"
        if key in self.user_permissions:
            del self.user_permissions[key]
            return True
        return False

    async def create_permission_audit_log(self, audit_log):
        """Create permission audit log"""
        return True

    async def create_access_audit_log(self, audit_log):
        """Create access audit log"""
        return True


async def test_permission_granted_event():
    """Test that authorization.permission.granted event is published"""
    print("\n📝 Testing authorization.permission.granted event...")

    mock_event_bus = MockEventBus()
    service = AuthorizationService(event_bus=mock_event_bus)

    # Replace repository with mock
    mock_repo = MockAuthorizationRepository()
    service.repository = mock_repo

    # Add a test user
    mock_repo.users["user123"] = True

    request = GrantPermissionRequest(
        user_id="user123",
        resource_type=ResourceType.FILE_STORAGE,
        resource_name="storage_456",
        access_level=AccessLevel.READ_WRITE,
        permission_source=PermissionSource.ADMIN_GRANT,
        granted_by_user_id="admin789",
        organization_id="org123",
        reason="Test permission grant"
    )

    result = await service.grant_resource_permission(request)

    # Check permission was granted
    assert result is True, "Permission grant should succeed"

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.PERMISSION_GRANTED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.AUTHORIZATION_SERVICE.value, "Event source should be authorization_service"
    assert event.data["user_id"] == "user123", "Event should contain user_id"
    assert event.data["resource_type"] == "file_storage", "Event should contain resource_type"
    assert event.data["resource_name"] == "storage_456", "Event should contain resource_name"
    assert event.data["access_level"] == "read_write", "Event should contain access_level"
    assert event.data["granted_by_user_id"] == "admin789", "Event should contain granted_by_user_id"

    print("✅ TEST PASSED: authorization.permission.granted event published correctly")
    return True


async def test_permission_revoked_event():
    """Test that authorization.permission.revoked event is published"""
    print("\n📝 Testing authorization.permission.revoked event...")

    mock_event_bus = MockEventBus()
    service = AuthorizationService(event_bus=mock_event_bus)

    # Replace repository with mock
    mock_repo = MockAuthorizationRepository()
    service.repository = mock_repo

    # Add a test user
    mock_repo.users["user123"] = True

    # Create an existing permission
    class MockPermission:
        def __init__(self):
            self.user_id = "user123"
            self.resource_type = ResourceType.DATABASE
            self.resource_name = "database_789"
            self.access_level = AccessLevel.READ_ONLY

    mock_repo.user_permissions["user123:database:database_789"] = MockPermission()

    # Clear any previous events
    mock_event_bus.clear()

    request = RevokePermissionRequest(
        user_id="user123",
        resource_type=ResourceType.DATABASE,
        resource_name="database_789",
        revoked_by_user_id="admin789",
        reason="Test permission revocation"
    )

    result = await service.revoke_resource_permission(request)

    # Check permission was revoked
    assert result is True, "Permission revocation should succeed"

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.PERMISSION_REVOKED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.AUTHORIZATION_SERVICE.value, "Event source should be authorization_service"
    assert event.data["user_id"] == "user123", "Event should contain user_id"
    assert event.data["resource_type"] == "database", "Event should contain resource_type"
    assert event.data["resource_name"] == "database_789", "Event should contain resource_name"
    assert event.data["revoked_by_user_id"] == "admin789", "Event should contain revoked_by_user_id"

    print("✅ TEST PASSED: authorization.permission.revoked event published correctly")
    return True


async def test_access_denied_event():
    """Test that authorization.access.denied event is published"""
    print("\n📝 Testing authorization.access.denied event...")

    mock_event_bus = MockEventBus()
    service = AuthorizationService(event_bus=mock_event_bus)

    # Replace repository with mock
    mock_repo = MockAuthorizationRepository()
    service.repository = mock_repo

    # Add a test user with no permissions
    mock_repo.users["user123"] = True

    # Clear any previous events
    mock_event_bus.clear()

    request = ResourceAccessRequest(
        user_id="user123",
        resource_type=ResourceType.FILE_STORAGE,
        resource_name="file_storage_bucket_1",
        required_access_level=AccessLevel.ADMIN
    )

    response = await service.check_resource_access(request)

    # Check access was denied
    assert response.has_access is False, "Access should be denied"

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.ACCESS_DENIED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.AUTHORIZATION_SERVICE.value, "Event source should be authorization_service"
    assert event.data["user_id"] == "user123", "Event should contain user_id"
    assert event.data["resource_type"] == "file_storage", "Event should contain resource_type"
    assert event.data["resource_name"] == "file_storage_bucket_1", "Event should contain resource_name"
    assert event.data["required_access_level"] == "admin", "Event should contain required_access_level"

    print("✅ TEST PASSED: authorization.access.denied event published correctly")
    return True


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("AUTHORIZATION SERVICE EVENT PUBLISHING TEST SUITE")
    print("="*80)

    tests = [
        ("Permission Granted Event", test_permission_granted_event),
        ("Permission Revoked Event", test_permission_revoked_event),
        ("Access Denied Event", test_access_denied_event),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            result = await test_func()
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ TEST FAILED: {test_name}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "="*80)
    print(f"TEST RESULTS: {passed} passed, {failed} failed out of {len(tests)} total")
    print("="*80)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
