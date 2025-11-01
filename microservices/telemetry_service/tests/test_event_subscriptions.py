"""
Telemetry Service Event Subscription Tests

Tests that Telemetry Service correctly handles incoming events:
- device.deleted: Disable alert rules for the deleted device
"""
import asyncio
import sys
import os
from datetime import datetime, timezone
from typing import List, Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from core.nats_client import Event, EventType, ServiceSource
from microservices.telemetry_service.events.handlers import TelemetryEventHandler


class MockTelemetryRepository:
    """Mock telemetry repository for testing event handlers"""

    def __init__(self):
        self.alert_rules = {}
        self.rule_counter = 1

    def add_alert_rule(self, name: str, device_ids: List[str], enabled: bool = True) -> str:
        """Helper to add an alert rule for testing"""
        rule_id = f"rule_{self.rule_counter}"
        self.rule_counter += 1

        self.alert_rules[rule_id] = {
            "rule_id": rule_id,
            "name": name,
            "device_ids": device_ids,
            "enabled": enabled,
            "metric_name": "temperature",
            "condition": ">",
            "threshold_value": "30.0"
        }
        return rule_id

    async def disable_device_alert_rules(self, device_id: str) -> int:
        """Disable all alert rules for a specific device"""
        count = 0
        for rule in self.alert_rules.values():
            if device_id in rule.get("device_ids", []) and rule.get("enabled", False):
                rule["enabled"] = False
                count += 1
        return count

    def get_rules_by_device(self, device_id: str) -> List[Dict[str, Any]]:
        """Get all rules for a device"""
        return [
            rule for rule in self.alert_rules.values()
            if device_id in rule.get("device_ids", [])
        ]

    def get_disabled_count(self, device_id: str) -> int:
        """Get count of disabled rules for a device"""
        return len([
            rule for rule in self.alert_rules.values()
            if device_id in rule.get("device_ids", []) and not rule.get("enabled", False)
        ])


async def test_handle_device_deleted():
    """Test handling device.deleted event disables device's alert rules"""
    print("\n📝 Testing device.deleted event handler...")

    mock_repository = MockTelemetryRepository()
    event_handler = TelemetryEventHandler(mock_repository)

    # Create some alert rules for the device
    mock_repository.add_alert_rule("High Temp", ["device123"], enabled=True)
    mock_repository.add_alert_rule("Low Battery", ["device123"], enabled=True)
    mock_repository.add_alert_rule("Multi Device Rule", ["device123", "device456"], enabled=True)
    mock_repository.add_alert_rule("Other Device Rule", ["device456"], enabled=True)

    # Create device.deleted event
    event_data = {
        "device_id": "device123",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Handle the event
    result = await event_handler.handle_device_deleted(event_data)

    # Verify success
    assert result is True, "Handler should return True on success"

    # Check that alert rules for device123 were disabled
    disabled_count = mock_repository.get_disabled_count("device123")
    assert disabled_count == 3, f"Should disable 3 rules, disabled {disabled_count}"

    # Verify other device's rules were not affected
    other_device_rules = mock_repository.get_rules_by_device("device456")
    enabled_for_other = [r for r in other_device_rules if r.get("enabled", False)]
    assert len(enabled_for_other) == 1, "Other device should still have 1 enabled rule"

    print("✅ TEST PASSED: device.deleted event handled correctly")
    return True


async def test_handle_device_deleted_no_rules():
    """Test handling device.deleted event when device has no alert rules"""
    print("\n📝 Testing device.deleted with no rules...")

    mock_repository = MockTelemetryRepository()
    event_handler = TelemetryEventHandler(mock_repository)

    event_data = {
        "device_id": "device_with_no_rules",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Handle the event
    result = await event_handler.handle_device_deleted(event_data)

    # Should succeed even with no rules
    assert result is True, "Handler should return True even with no rules"
    assert mock_repository.get_disabled_count("device_with_no_rules") == 0, "No rules should be disabled"

    print("✅ TEST PASSED: device.deleted with no rules handled correctly")
    return True


async def test_handle_device_deleted_missing_device_id():
    """Test handling device.deleted event with missing device_id"""
    print("\n📝 Testing device.deleted with missing device_id...")

    mock_repository = MockTelemetryRepository()
    event_handler = TelemetryEventHandler(mock_repository)

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

    mock_repository = MockTelemetryRepository()
    event_handler = TelemetryEventHandler(mock_repository)

    # Create an alert rule
    mock_repository.add_alert_rule("Test Rule", ["device123"], enabled=True)

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
    assert mock_repository.get_disabled_count("device123") == 1, "Rule should be disabled"

    print("✅ TEST PASSED: event routing works correctly")
    return True


async def test_handle_unknown_event():
    """Test handling unknown event type"""
    print("\n📝 Testing unknown event handling...")

    mock_repository = MockTelemetryRepository()
    event_handler = TelemetryEventHandler(mock_repository)

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

    mock_repository = MockTelemetryRepository()
    event_handler = TelemetryEventHandler(mock_repository)

    subscriptions = event_handler.get_subscriptions()

    # Should subscribe to device.deleted
    assert "device.deleted" in subscriptions, "Should subscribe to device.deleted"
    assert len(subscriptions) == 1, f"Should have 1 subscription, got {len(subscriptions)}"

    print("✅ TEST PASSED: subscription list is correct")
    return True


async def test_handle_device_deleted_multiple_devices():
    """Test handling device.deleted for multiple devices"""
    print("\n📝 Testing device.deleted for multiple devices...")

    mock_repository = MockTelemetryRepository()
    event_handler = TelemetryEventHandler(mock_repository)

    # Create alert rules for multiple devices
    mock_repository.add_alert_rule("Device1 Rule1", ["device1"], enabled=True)
    mock_repository.add_alert_rule("Device1 Rule2", ["device1"], enabled=True)
    mock_repository.add_alert_rule("Device2 Rule", ["device2"], enabled=True)
    mock_repository.add_alert_rule("Device3 Rule", ["device3"], enabled=True)

    # Delete device1
    event_data = {
        "device_id": "device1",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    result = await event_handler.handle_device_deleted(event_data)
    assert result is True, "Should handle device1 deletion"
    assert mock_repository.get_disabled_count("device1") == 2, "Should disable 2 rules for device1"

    # Verify other devices' rules are not affected
    assert mock_repository.get_disabled_count("device2") == 0, "Device2 rules should not be disabled"
    assert mock_repository.get_disabled_count("device3") == 0, "Device3 rules should not be disabled"

    # Delete device2
    event_data = {
        "device_id": "device2",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    result = await event_handler.handle_device_deleted(event_data)
    assert result is True, "Should handle device2 deletion"
    assert mock_repository.get_disabled_count("device2") == 1, "Should disable 1 rule for device2"

    # Verify device3's rules are still not affected
    assert mock_repository.get_disabled_count("device3") == 0, "Device3 rules should still not be disabled"

    print("✅ TEST PASSED: multiple device deletions handled correctly")
    return True


async def test_handle_device_deleted_shared_rules():
    """Test handling device.deleted when rules are shared across devices"""
    print("\n📝 Testing device.deleted with shared rules...")

    mock_repository = MockTelemetryRepository()
    event_handler = TelemetryEventHandler(mock_repository)

    # Create shared rules
    mock_repository.add_alert_rule("Shared Rule 1", ["device1", "device2", "device3"], enabled=True)
    mock_repository.add_alert_rule("Shared Rule 2", ["device1", "device2"], enabled=True)
    mock_repository.add_alert_rule("Device1 Only", ["device1"], enabled=True)

    # Delete device1
    event_data = {
        "device_id": "device1",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    result = await event_handler.handle_device_deleted(event_data)
    assert result is True, "Should handle device1 deletion"

    # All rules targeting device1 should be disabled
    disabled_count = mock_repository.get_disabled_count("device1")
    assert disabled_count == 3, f"Should disable 3 rules, disabled {disabled_count}"

    # Check that shared rules affecting device2 and device3 are also disabled
    # (This is expected behavior - if a rule targets a deleted device, it's disabled)
    device2_rules = mock_repository.get_rules_by_device("device2")
    device2_disabled = [r for r in device2_rules if not r.get("enabled", False)]
    assert len(device2_disabled) == 2, "2 shared rules should be disabled for device2"

    print("✅ TEST PASSED: device deletion with shared rules handled correctly")
    return True


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("TELEMETRY SERVICE EVENT SUBSCRIPTION TEST SUITE")
    print("="*80)

    tests = [
        ("Device Deleted Event Handler", test_handle_device_deleted),
        ("Device Deleted With No Rules", test_handle_device_deleted_no_rules),
        ("Device Deleted Missing Device ID", test_handle_device_deleted_missing_device_id),
        ("Event Routing", test_handle_event_routing),
        ("Unknown Event Handling", test_handle_unknown_event),
        ("Subscription List", test_get_subscriptions),
        ("Multiple Device Deletions", test_handle_device_deleted_multiple_devices),
        ("Device Deletion With Shared Rules", test_handle_device_deleted_shared_rules),
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
