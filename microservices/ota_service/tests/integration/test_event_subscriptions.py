"""
OTA Service Event Subscription Tests

Tests that OTA Service correctly handles incoming events:
- device.deleted: Cancel all pending updates for the deleted device
"""
import asyncio
import sys
import os
from datetime import datetime, timezone
from typing import List, Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from core.nats_client import Event, EventType, ServiceSource
from microservices.ota_service.events.handlers import OTAEventHandler


class MockOTARepository:
    """Mock OTA repository for testing event handlers"""

    def __init__(self):
        self.updates = {}
        self.update_counter = 1

    def add_update(self, device_id: str, firmware_id: str, status: str = "created") -> str:
        """Helper to add an update for testing"""
        update_id = f"update_{self.update_counter}"
        self.update_counter += 1

        self.updates[update_id] = {
            "update_id": update_id,
            "device_id": device_id,
            "firmware_id": firmware_id,
            "status": status
        }
        return update_id

    async def cancel_device_updates(self, device_id: str) -> int:
        """Cancel all pending/in-progress updates for a device"""
        count = 0
        for update in self.updates.values():
            if update["device_id"] == device_id and update["status"] in ["created", "scheduled", "in_progress"]:
                update["status"] = "cancelled"
                count += 1
        return count

    def get_updates_by_device(self, device_id: str) -> List[Dict[str, Any]]:
        """Get all updates for a device"""
        return [update for update in self.updates.values() if update["device_id"] == device_id]

    def get_cancelled_count(self, device_id: str) -> int:
        """Get count of cancelled updates for a device"""
        return len([
            update for update in self.updates.values()
            if update["device_id"] == device_id and update["status"] == "cancelled"
        ])


async def test_handle_device_deleted():
    """Test handling device.deleted event cancels all device's updates"""
    print("\n📝 Testing device.deleted event handler...")

    mock_repository = MockOTARepository()
    event_handler = OTAEventHandler(mock_repository)

    # Create some updates for the device
    mock_repository.add_update("device123", "fw_1", "created")
    mock_repository.add_update("device123", "fw_2", "scheduled")
    mock_repository.add_update("device123", "fw_3", "in_progress")
    mock_repository.add_update("device123", "fw_4", "completed")  # Should not be cancelled
    mock_repository.add_update("device456", "fw_5", "created")  # Different device

    # Create device.deleted event
    event_data = {
        "device_id": "device123",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Handle the event
    result = await event_handler.handle_device_deleted(event_data)

    # Verify success
    assert result is True, "Handler should return True on success"

    # Check that only pending/scheduled/in-progress updates were cancelled
    cancelled_count = mock_repository.get_cancelled_count("device123")
    assert cancelled_count == 3, f"Should cancel 3 updates, cancelled {cancelled_count}"

    # Verify completed update was not cancelled
    device_updates = mock_repository.get_updates_by_device("device123")
    completed_updates = [u for u in device_updates if u["status"] == "completed"]
    assert len(completed_updates) == 1, "Completed update should not be cancelled"

    # Verify other device's updates were not affected
    other_device_updates = mock_repository.get_updates_by_device("device456")
    assert len(other_device_updates) == 1, "Other device should still have 1 update"
    assert other_device_updates[0]["status"] == "created", "Other device's update should still be created"

    print("✅ TEST PASSED: device.deleted event handled correctly")
    return True


async def test_handle_device_deleted_no_updates():
    """Test handling device.deleted event when device has no updates"""
    print("\n📝 Testing device.deleted with no updates...")

    mock_repository = MockOTARepository()
    event_handler = OTAEventHandler(mock_repository)

    event_data = {
        "device_id": "device_with_no_updates",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Handle the event
    result = await event_handler.handle_device_deleted(event_data)

    # Should succeed even with no updates
    assert result is True, "Handler should return True even with no updates"
    assert mock_repository.get_cancelled_count("device_with_no_updates") == 0, "No updates should be cancelled"

    print("✅ TEST PASSED: device.deleted with no updates handled correctly")
    return True


async def test_handle_device_deleted_missing_device_id():
    """Test handling device.deleted event with missing device_id"""
    print("\n📝 Testing device.deleted with missing device_id...")

    mock_repository = MockOTARepository()
    event_handler = OTAEventHandler(mock_repository)

    event_data = {
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Handle the event
    result = await event_handler.handle_device_deleted(event_data)

    # Should return False for invalid data
    assert result is False, "Handler should return False for missing device_id"

    print("✅ TEST PASSED: device.deleted with missing device_id handled correctly")
    return True


async def test_handle_event_routing():
    """Test that handle_event correctly routes to device.deleted handler"""
    print("\n📝 Testing event routing...")

    mock_repository = MockOTARepository()
    event_handler = OTAEventHandler(mock_repository)

    # Create an update
    mock_repository.add_update("device123", "fw_1", "created")

    # Create mock event object
    class MockEvent:
        def __init__(self):
            self.type = "device.deleted"
            self.source = ServiceSource.DEVICE_SERVICE.value
            self.data = {
                "device_id": "device123",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    event = MockEvent()

    # Handle the event
    result = await event_handler.handle_event(event)

    # Verify it was routed correctly
    assert result is True, "Event should be routed and handled successfully"
    assert mock_repository.get_cancelled_count("device123") == 1, "Update should be cancelled"

    print("✅ TEST PASSED: event routing works correctly")
    return True


async def test_handle_unknown_event():
    """Test handling unknown event type"""
    print("\n📝 Testing unknown event handling...")

    mock_repository = MockOTARepository()
    event_handler = OTAEventHandler(mock_repository)

    # Create mock event object with unknown type
    class MockEvent:
        def __init__(self):
            self.type = "unknown.event"
            self.source = ServiceSource.DEVICE_SERVICE.value
            self.data = {}

    event = MockEvent()

    # Handle the event
    result = await event_handler.handle_event(event)

    # Should return False for unknown event
    assert result is False, "Handler should return False for unknown event type"

    print("✅ TEST PASSED: unknown event handled correctly")
    return True


async def test_get_subscriptions():
    """Test that handler returns correct subscription list"""
    print("\n📝 Testing subscription list...")

    mock_repository = MockOTARepository()
    event_handler = OTAEventHandler(mock_repository)

    subscriptions = event_handler.get_subscriptions()

    # Should subscribe to device.deleted
    assert "device.deleted" in subscriptions, "Should subscribe to device.deleted"
    assert len(subscriptions) == 1, f"Should have 1 subscription, got {len(subscriptions)}"

    print("✅ TEST PASSED: subscription list is correct")
    return True


async def test_handle_device_deleted_multiple_devices():
    """Test handling device.deleted for multiple devices"""
    print("\n📝 Testing device.deleted for multiple devices...")

    mock_repository = MockOTARepository()
    event_handler = OTAEventHandler(mock_repository)

    # Create updates for multiple devices
    mock_repository.add_update("device1", "fw_1", "created")
    mock_repository.add_update("device1", "fw_2", "created")
    mock_repository.add_update("device2", "fw_3", "created")
    mock_repository.add_update("device3", "fw_4", "created")

    # Delete device1
    event_data = {
        "device_id": "device1",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    result = await event_handler.handle_device_deleted(event_data)
    assert result is True, "Should handle device1 deletion"
    assert mock_repository.get_cancelled_count("device1") == 2, "Should cancel 2 updates for device1"

    # Verify other devices' updates are not affected
    assert mock_repository.get_cancelled_count("device2") == 0, "Device2 updates should not be cancelled"
    assert mock_repository.get_cancelled_count("device3") == 0, "Device3 updates should not be cancelled"

    # Delete device2
    event_data = {
        "device_id": "device2",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    result = await event_handler.handle_device_deleted(event_data)
    assert result is True, "Should handle device2 deletion"
    assert mock_repository.get_cancelled_count("device2") == 1, "Should cancel 1 update for device2"

    # Verify device3's updates are still not affected
    assert mock_repository.get_cancelled_count("device3") == 0, "Device3 updates should still not be cancelled"

    print("✅ TEST PASSED: multiple device deletions handled correctly")
    return True


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("OTA SERVICE EVENT SUBSCRIPTION TEST SUITE")
    print("="*80)

    tests = [
        ("Device Deleted Event Handler", test_handle_device_deleted),
        ("Device Deleted With No Updates", test_handle_device_deleted_no_updates),
        ("Device Deleted Missing Device ID", test_handle_device_deleted_missing_device_id),
        ("Event Routing", test_handle_event_routing),
        ("Unknown Event Handling", test_handle_unknown_event),
        ("Subscription List", test_get_subscriptions),
        ("Multiple Device Deletions", test_handle_device_deleted_multiple_devices),
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
