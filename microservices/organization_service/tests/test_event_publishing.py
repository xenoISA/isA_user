#!/usr/bin/env python3
"""
Test Organization Service Event Publishing

Tests that organization service publishes events correctly to NATS
"""

import asyncio
import sys
import os
from datetime import datetime
import uuid

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from microservices.organization_service.organization_service import OrganizationService
from microservices.organization_service.family_sharing_service import FamilySharingService
from microservices.organization_service.models import (
    OrganizationCreateRequest, OrganizationMemberAddRequest, OrganizationRole
)
from microservices.organization_service.family_sharing_models import (
    CreateSharingRequest, SharingResourceType, SharingPermissionLevel
)
from core.nats_client import get_event_bus, Event


class MockEventBus:
    """Mock event bus to capture published events"""

    def __init__(self):
        self.published_events = []
        self._is_connected = True

    async def publish_event(self, event: Event) -> bool:
        """Capture published events"""
        self.published_events.append({
            "id": event.id,
            "type": event.type,
            "source": event.source,
            "data": event.data,
            "metadata": event.metadata,
            "timestamp": event.timestamp
        })
        print(f"✅ Event captured: {event.type}")
        print(f"   Data: {event.data}")
        return True

    async def close(self):
        """Mock close"""
        pass


class MockOrganizationRepository:
    """Mock repository for testing"""

    async def create_organization(self, org_data, owner_id):
        """Mock create organization"""
        from microservices.organization_service.models import OrganizationResponse
        return OrganizationResponse(
            organization_id=str(uuid.uuid4()),
            name=org_data.get("name"),
            billing_email=org_data.get("billing_email"),
            plan="free",
            status="active",
            owner_user_id=owner_id,
            member_count=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

    async def add_organization_member(self, org_id, user_id, role, permissions):
        """Mock add member"""
        from microservices.organization_service.models import OrganizationMemberResponse, MemberStatus
        return OrganizationMemberResponse(
            organization_id=org_id,
            user_id=user_id,
            role=role,
            status=MemberStatus.ACTIVE,
            permissions=permissions or [],
            joined_at=datetime.utcnow()
        )

    async def remove_organization_member(self, org_id, user_id):
        """Mock remove member"""
        return True

    async def get_user_organization_role(self, org_id, user_id):
        """Mock get role - owner can remove members, target user is a member"""
        if user_id == "admin_user":
            return {"role": "owner", "status": "active"}
        else:
            return {"role": "member", "status": "active"}


class MockFamilySharingRepository:
    """Mock family sharing repository"""

    async def create_sharing(self, sharing_data):
        """Mock create sharing with all required fields"""
        # Add missing fields for SharingResourceResponse
        sharing_data["created_at"] = datetime.utcnow()
        sharing_data["updated_at"] = datetime.utcnow()
        return sharing_data

    async def _check_organization_admin_permission(self, org_id, user_id):
        """Mock admin check"""
        return True

    async def check_organization_admin(self, org_id, user_id):
        """Mock admin check"""
        return True

    async def get_organization_members(self, organization_id, **kwargs):
        """Mock get organization members"""
        return []  # Return empty list for testing (no members to grant permissions to)

    async def create_member_permission(self, permission_data):
        """Mock create member permission"""
        return permission_data


async def test_organization_created_event():
    """Test that creating organization publishes organization.created event"""
    print("\n" + "="*60)
    print("TEST 1: Organization Created Event Publishing")
    print("="*60)

    # Create mock event bus
    mock_bus = MockEventBus()

    # Create organization service with mock event bus and repository
    org_service = OrganizationService(event_bus=mock_bus)
    org_service.repository = MockOrganizationRepository()

    # Create organization
    request = OrganizationCreateRequest(
        name="Test Org",
        billing_email="test@example.com",
        plan="free"
    )

    organization = await org_service.create_organization(request, "user_123")

    # Verify event was published
    assert len(mock_bus.published_events) == 1, "Expected 1 event to be published"

    event = mock_bus.published_events[0]
    assert event["type"] == "organization.created", f"Expected organization.created, got {event['type']}"
    assert event["source"] == "organization_service"
    assert event["data"]["organization_name"] == "Test Org"
    assert event["data"]["owner_user_id"] == "user_123"
    assert event["data"]["billing_email"] == "test@example.com"

    print(f"✅ organization.created event published correctly")
    print(f"   Event ID: {event['id']}")
    print(f"   Organization: {event['data']['organization_name']}")
    print(f"   Owner: {event['data']['owner_user_id']}")

    return True


async def test_member_added_event():
    """Test that adding member publishes organization.member_added event"""
    print("\n" + "="*60)
    print("TEST 2: Organization Member Added Event Publishing")
    print("="*60)

    # Create mock event bus
    mock_bus = MockEventBus()

    # Create organization service
    org_service = OrganizationService(event_bus=mock_bus)
    org_service.repository = MockOrganizationRepository()

    # Add member
    request = OrganizationMemberAddRequest(
        user_id="user_456",
        role=OrganizationRole.MEMBER,
        permissions=["read"]
    )

    member = await org_service.add_organization_member("org_123", request, "admin_user")

    # Verify event
    assert len(mock_bus.published_events) == 1
    event = mock_bus.published_events[0]
    assert event["type"] == "organization.member_added"
    assert event["data"]["user_id"] == "user_456"
    assert event["data"]["organization_id"] == "org_123"
    assert event["data"]["added_by"] == "admin_user"

    print(f"✅ organization.member_added event published correctly")
    print(f"   Member: {event['data']['user_id']}")
    print(f"   Role: {event['data']['role']}")

    return True


async def test_member_removed_event():
    """Test that removing member publishes organization.member_removed event"""
    print("\n" + "="*60)
    print("TEST 3: Organization Member Removed Event Publishing")
    print("="*60)

    # Create mock event bus
    mock_bus = MockEventBus()

    # Create organization service
    org_service = OrganizationService(event_bus=mock_bus)
    org_service.repository = MockOrganizationRepository()

    # Remove member
    success = await org_service.remove_organization_member("org_123", "user_456", "admin_user")

    # Verify event
    assert success
    assert len(mock_bus.published_events) == 1
    event = mock_bus.published_events[0]
    assert event["type"] == "organization.member_removed"
    assert event["data"]["user_id"] == "user_456"
    assert event["data"]["removed_by"] == "admin_user"

    print(f"✅ organization.member_removed event published correctly")
    print(f"   Member removed: {event['data']['user_id']}")

    return True


async def test_family_resource_shared_event():
    """Test that creating sharing publishes family.resource_shared event"""
    print("\n" + "="*60)
    print("TEST 4: Family Resource Shared Event Publishing")
    print("="*60)

    # Create mock event bus
    mock_bus = MockEventBus()

    # Create family sharing service
    sharing_service = FamilySharingService(
        repository=MockFamilySharingRepository(),
        event_bus=mock_bus
    )

    # Mock the _check_organization_admin_permission method
    async def mock_check_admin(org_id, user_id):
        return True

    sharing_service._check_organization_admin_permission = mock_check_admin

    # Create sharing
    request = CreateSharingRequest(
        resource_type=SharingResourceType.STORAGE,
        resource_id="storage_123",
        resource_name="Family Photos",
        share_with_all_members=True,
        default_permission=SharingPermissionLevel.READ_WRITE
    )

    sharing = await sharing_service.create_sharing("org_123", request, "user_123")

    # Verify event
    assert len(mock_bus.published_events) == 1
    event = mock_bus.published_events[0]
    assert event["type"] == "family.resource_shared"
    assert event["source"] == "organization_service"
    assert event["data"]["resource_type"] == "storage"
    assert event["data"]["resource_name"] == "Family Photos"
    assert event["data"]["created_by"] == "user_123"

    print(f"✅ family.resource_shared event published correctly")
    print(f"   Resource: {event['data']['resource_name']}")
    print(f"   Type: {event['data']['resource_type']}")

    return True


async def test_nats_connection():
    """Test actual NATS connection (if available)"""
    print("\n" + "="*60)
    print("TEST 5: NATS Connection Test")
    print("="*60)

    try:
        # Try to connect to NATS
        event_bus = await get_event_bus("organization_service_test")

        if event_bus and event_bus._is_connected:
            print("✅ Successfully connected to NATS")
            print(f"   URL: {event_bus.nats_url}")

            # Test publishing an organization event
            from core.nats_client import Event, EventType, ServiceSource
            test_event = Event(
                event_type=EventType.ORG_CREATED,
                source=ServiceSource.ORG_SERVICE,
                data={
                    "organization_id": "test_123",
                    "organization_name": "Test Org",
                    "owner_user_id": "user_123",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

            success = await event_bus.publish_event(test_event)

            if success:
                print("✅ Test organization event published to NATS successfully")
            else:
                print("⚠️  Event publish returned False")

            await event_bus.close()
            return True
        else:
            print("⚠️  NATS not available or not configured")
            return False

    except Exception as e:
        print(f"⚠️  NATS connection failed: {e}")
        print("   This is OK for testing without NATS running")
        return False


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("ORGANIZATION SERVICE EVENT PUBLISHING TEST SUITE")
    print("="*80)
    print(f"Timestamp: {datetime.now().isoformat()}")

    results = {}

    # Run tests
    try:
        results["organization_created_event"] = await test_organization_created_event()
    except Exception as e:
        print(f"❌ TEST 1 FAILED: {e}")
        results["organization_created_event"] = False

    try:
        results["member_added_event"] = await test_member_added_event()
    except Exception as e:
        print(f"❌ TEST 2 FAILED: {e}")
        results["member_added_event"] = False

    try:
        results["member_removed_event"] = await test_member_removed_event()
    except Exception as e:
        print(f"❌ TEST 3 FAILED: {e}")
        results["member_removed_event"] = False

    try:
        results["family_resource_shared_event"] = await test_family_resource_shared_event()
    except Exception as e:
        print(f"❌ TEST 4 FAILED: {e}")
        results["family_resource_shared_event"] = False

    try:
        results["nats_connection"] = await test_nats_connection()
    except Exception as e:
        print(f"❌ TEST 5 FAILED: {e}")
        results["nats_connection"] = False

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
    elif passed >= 4:  # Core tests (NATS is optional)
        print("\n✅ Core functionality tests passed (NATS optional)")
    else:
        print("\n⚠️  Some tests failed")

    return passed, total


if __name__ == "__main__":
    passed, total = asyncio.run(run_all_tests())

    # Exit with appropriate code
    if passed >= 4:  # Core tests must pass (NATS is optional)
        sys.exit(0)
    else:
        sys.exit(1)
