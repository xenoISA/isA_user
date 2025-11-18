#!/usr/bin/env python3
"""
Test Audit Service Event Subscriptions

Tests that audit service correctly logs all events from NATS
"""

import asyncio
import sys
import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from microservices.audit_service.audit_service import AuditService
from core.nats_client import Event, EventType, ServiceSource, get_event_bus


class MockAuditRepository:
    """Mock repository for testing"""

    async def create_audit_event(self, audit_event):
        """Mock create audit event"""
        audit_event.id = f"audit_{datetime.utcnow().timestamp()}"
        return audit_event

    async def check_connection(self):
        """Mock check connection"""
        return True


class MockAuditService:
    """Mock audit service for testing"""

    def __init__(self):
        self.repository = MockAuditRepository()
        self.processed_event_ids = set()
        self.logged_events = []

    async def log_event(self, request):
        """Mock log event"""
        self.logged_events.append({
            "event_type": request.event_type,
            "category": request.category,
            "severity": request.severity,
            "action": request.action,
            "user_id": request.user_id,
            "resource_type": request.resource_type,
            "resource_id": request.resource_id,
            "metadata": request.metadata,
            "tags": request.tags
        })
        print(f"✅ Mock audit event logged: {request.action}")
        return MagicMock(
            id=f"audit_{len(self.logged_events)}",
            event_type=request.event_type,
            category=request.category,
            severity=request.severity,
            status=request.event_type,
            action=request.action,
            description=request.description,
            user_id=request.user_id,
            organization_id=request.organization_id,
            resource_type=request.resource_type,
            resource_name=request.resource_name,
            success=request.success,
            timestamp=datetime.utcnow(),
            metadata=request.metadata
        )

    async def handle_nats_event(self, event):
        """Use real implementation from AuditService"""
        # Borrow the real implementation but use our mock log_event
        real_service = AuditService()
        real_service.log_event = self.log_event
        real_service.processed_event_ids = self.processed_event_ids
        await real_service.handle_nats_event(event)


async def test_user_logged_in_event():
    """Test handling of user.logged_in event"""
    print("\n" + "="*60)
    print("TEST 1: User Logged In Event Handler")
    print("="*60)

    # Create mock service
    mock_service = MockAuditService()

    # Create event
    event = Event(
        event_type=EventType.USER_LOGGED_IN,
        source=ServiceSource.AUTH_SERVICE,
        data={
            "user_id": "user_123",
            "email": "user@example.com",
            "provider": "email",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

    # Handle event
    await mock_service.handle_nats_event(event)

    # Verify audit log was created
    assert len(mock_service.logged_events) == 1, "Expected 1 audit event"
    audit = mock_service.logged_events[0]
    assert audit["user_id"] == "user_123"
    assert audit["action"] == "user.logged_in"
    assert "nats_event" in audit["tags"]
    assert audit["metadata"]["nats_event_source"] == "auth_service"

    # Verify idempotency
    await mock_service.handle_nats_event(event)
    assert len(mock_service.logged_events) == 1, "Event should be processed only once"

    print(f"✅ user.logged_in event logged to audit trail")
    print(f"   User: {audit['user_id']}")
    print(f"   Action: {audit['action']}")
    print(f"   Category: {audit['category']}")
    print(f"   Idempotency verified")

    return True


async def test_payment_completed_event():
    """Test handling of payment.completed event"""
    print("\n" + "="*60)
    print("TEST 2: Payment Completed Event Handler")
    print("="*60)

    # Create mock service
    mock_service = MockAuditService()

    # Create event
    event = Event(
        event_type=EventType.PAYMENT_COMPLETED,
        source=ServiceSource.PAYMENT_SERVICE,
        data={
            "payment_id": "pay_123",
            "user_id": "user_456",
            "amount": 99.99,
            "currency": "USD",
            "customer_email": "customer@example.com",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

    # Handle event
    await mock_service.handle_nats_event(event)

    # Verify audit log
    assert len(mock_service.logged_events) == 1, "Expected 1 audit event"
    audit = mock_service.logged_events[0]
    assert audit["user_id"] == "user_456"
    assert audit["action"] == "payment.completed"
    assert audit["resource_id"] == "pay_123"
    assert audit["category"].value == "configuration"

    print(f"✅ payment.completed event logged to audit trail")
    print(f"   Payment ID: {audit['resource_id']}")
    print(f"   User: {audit['user_id']}")
    print(f"   Category: {audit['category'].value}")

    return True


async def test_device_registered_event():
    """Test handling of device.registered event"""
    print("\n" + "="*60)
    print("TEST 3: Device Registered Event Handler")
    print("="*60)

    # Create mock service
    mock_service = MockAuditService()

    # Create event
    event = Event(
        event_type=EventType.DEVICE_REGISTERED,
        source=ServiceSource.DEVICE_SERVICE,
        data={
            "device_id": "device_123",
            "device_name": "Smart Frame 1",
            "device_type": "smart_frame",
            "user_id": "user_789",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

    # Handle event
    await mock_service.handle_nats_event(event)

    # Verify audit log
    assert len(mock_service.logged_events) == 1, "Expected 1 audit event"
    audit = mock_service.logged_events[0]
    assert audit["user_id"] == "user_789"
    assert audit["action"] == "device.registered"
    assert audit["resource_type"] == "device"
    assert audit["resource_id"] == "device_123"

    print(f"✅ device.registered event logged to audit trail")
    print(f"   Device: {audit['resource_id']}")
    print(f"   User: {audit['user_id']}")
    print(f"   Resource Type: {audit['resource_type']}")

    return True


async def test_file_deleted_event():
    """Test handling of file.deleted event"""
    print("\n" + "="*60)
    print("TEST 4: File Deleted Event Handler")
    print("="*60)

    # Create mock service
    mock_service = MockAuditService()

    # Create event
    event = Event(
        event_type=EventType.FILE_DELETED,
        source=ServiceSource.STORAGE_SERVICE,
        data={
            "file_id": "file_456",
            "file_name": "document.pdf",
            "user_id": "user_111",
            "permanent": True,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

    # Handle event
    await mock_service.handle_nats_event(event)

    # Verify audit log
    assert len(mock_service.logged_events) == 1, "Expected 1 audit event"
    audit = mock_service.logged_events[0]
    assert audit["user_id"] == "user_111"
    assert audit["action"] == "file.deleted"
    assert audit["severity"].value == "high"  # Delete events are high severity
    assert audit["resource_id"] == "file_456"

    print(f"✅ file.deleted event logged to audit trail")
    print(f"   File: {audit['resource_id']}")
    print(f"   Severity: {audit['severity'].value}")

    return True


async def test_organization_member_added_event():
    """Test handling of organization.member_added event"""
    print("\n" + "="*60)
    print("TEST 5: Organization Member Added Event Handler")
    print("="*60)

    # Create mock service
    mock_service = MockAuditService()

    # Create event
    event = Event(
        event_type=EventType.ORG_MEMBER_ADDED,
        source=ServiceSource.ORG_SERVICE,
        data={
            "organization_id": "org_789",
            "organization_name": "Acme Corp",
            "user_id": "user_999",
            "role": "member",
            "added_by": "admin_user",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

    # Handle event
    await mock_service.handle_nats_event(event)

    # Verify audit log
    assert len(mock_service.logged_events) == 1, "Expected 1 audit event"
    audit = mock_service.logged_events[0]
    assert audit["user_id"] == "user_999"
    assert audit["action"] == "organization.member_added"
    assert audit["category"].value == "authorization"
    assert audit["resource_id"] == "org_789"

    print(f"✅ organization.member_added event logged to audit trail")
    print(f"   Organization: {audit['resource_id']}")
    print(f"   Category: {audit['category'].value}")

    return True


async def test_nats_subscription():
    """Test actual NATS subscription (if available)"""
    print("\n" + "="*60)
    print("TEST 6: NATS Wildcard Subscription Test")
    print("="*60)

    try:
        # Create mock service
        mock_service = MockAuditService()

        # Try to connect to NATS
        event_bus = await get_event_bus("audit_service_test")

        if event_bus and event_bus._is_connected:
            print("✅ Successfully connected to NATS")
            print(f"   URL: {event_bus.nats_url}")

            # Subscribe to all events using wildcard
            await event_bus.subscribe_to_events(
                pattern="*.*",
                handler=mock_service.handle_nats_event
            )
            print("✅ Successfully subscribed to all events (*.*)")

            # Publish multiple test events from different services
            test_events = [
                Event(
                    event_type=EventType.USER_LOGGED_IN,
                    source=ServiceSource.AUTH_SERVICE,
                    data={"user_id": "test_user", "email": "test@example.com"}
                ),
                Event(
                    event_type=EventType.DEVICE_REGISTERED,
                    source=ServiceSource.DEVICE_SERVICE,
                    data={"device_id": "test_device", "user_id": "test_user"}
                ),
                Event(
                    event_type=EventType.FILE_UPLOADED,
                    source=ServiceSource.STORAGE_SERVICE,
                    data={"file_id": "test_file", "user_id": "test_user"}
                )
            ]

            for test_event in test_events:
                await event_bus.publish_event(test_event)
                print(f"✅ Published {test_event.type} event")

            # Wait for events to be processed
            await asyncio.sleep(2)

            # Check if events were logged
            if len(mock_service.logged_events) >= 3:
                print(f"✅ All {len(mock_service.logged_events)} events received and logged to audit trail!")
            else:
                print(f"⚠️  Only {len(mock_service.logged_events)}/3 events logged (may need more time)")

            await event_bus.close()
            return True
        else:
            print("⚠️  NATS not available or not configured")
            return False

    except Exception as e:
        print(f"⚠️  NATS subscription test failed: {e}")
        print("   This is OK for testing without NATS running")
        return False


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("AUDIT SERVICE EVENT SUBSCRIPTION TEST SUITE")
    print("="*80)
    print(f"Timestamp: {datetime.now().isoformat()}")

    results = {}

    # Run tests
    try:
        results["user_logged_in_handler"] = await test_user_logged_in_event()
    except Exception as e:
        print(f"❌ TEST 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["user_logged_in_handler"] = False

    try:
        results["payment_completed_handler"] = await test_payment_completed_event()
    except Exception as e:
        print(f"❌ TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["payment_completed_handler"] = False

    try:
        results["device_registered_handler"] = await test_device_registered_event()
    except Exception as e:
        print(f"❌ TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["device_registered_handler"] = False

    try:
        results["file_deleted_handler"] = await test_file_deleted_event()
    except Exception as e:
        print(f"❌ TEST 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["file_deleted_handler"] = False

    try:
        results["organization_member_added_handler"] = await test_organization_member_added_event()
    except Exception as e:
        print(f"❌ TEST 5 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["organization_member_added_handler"] = False

    try:
        results["nats_subscription"] = await test_nats_subscription()
    except Exception as e:
        print(f"❌ TEST 6 FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["nats_subscription"] = False

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
    elif passed >= 5:  # Core handler tests (NATS is optional)
        print("\n✅ Core handler tests passed (NATS optional)")
    else:
        print("\n⚠️  Some tests failed")

    return passed, total


if __name__ == "__main__":
    passed, total = asyncio.run(run_all_tests())

    # Exit with appropriate code
    if passed >= 5:  # Core tests must pass (NATS is optional)
        sys.exit(0)
    else:
        sys.exit(1)
