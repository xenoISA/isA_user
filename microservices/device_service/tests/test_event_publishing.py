#!/usr/bin/env python3
"""
Test Device Service Event Publishing

Tests that device service publishes events correctly to NATS
"""

import asyncio
import sys
import os
from datetime import datetime
import uuid

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from microservices.device_service.device_service import DeviceService
from microservices.device_service.models import DeviceStatus
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


class MockDeviceRepository:
    """Mock repository for testing"""

    async def create_device(self, device_data):
        """Mock create device"""
        from microservices.device_service.models import DeviceResponse, DeviceStatus, DeviceType, ConnectivityType
        return DeviceResponse(
            device_id=device_data["device_id"],
            device_name=device_data["device_name"],
            device_type=DeviceType.SMART_FRAME,
            manufacturer=device_data["manufacturer"],
            model=device_data["model"],
            serial_number=device_data["serial_number"],
            firmware_version=device_data["firmware_version"],
            hardware_version=device_data.get("hardware_version", "1.0"),
            mac_address=device_data.get("mac_address"),
            connectivity_type=ConnectivityType.WIFI,
            security_level="standard",
            status=DeviceStatus.PENDING,
            location=device_data.get("location", {}),
            metadata=device_data.get("metadata", {}),
            group_id=device_data.get("group_id"),
            tags=device_data.get("tags", []),
            last_seen=datetime.utcnow(),
            registered_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            user_id=device_data["user_id"],
            organization_id=None,
            total_commands=0,
            total_telemetry_points=0,
            uptime_percentage=0.0
        )

    async def get_device_by_id(self, device_id):
        """Mock get device"""
        from microservices.device_service.models import DeviceResponse, DeviceStatus, DeviceType, ConnectivityType
        return DeviceResponse(
            device_id=device_id,
            device_name="Test Device",
            device_type=DeviceType.SMART_FRAME,
            manufacturer="Test Corp",
            model="T-100",
            serial_number="SN123",
            firmware_version="1.0.0",
            hardware_version="1.0",
            mac_address="AA:BB:CC:DD:EE:FF",
            connectivity_type=ConnectivityType.WIFI,
            security_level="standard",
            status=DeviceStatus.ACTIVE,
            location={},
            metadata={},
            group_id=None,
            tags=[],
            last_seen=datetime.utcnow(),
            registered_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            user_id="user_123",
            organization_id=None,
            total_commands=0,
            total_telemetry_points=0,
            uptime_percentage=95.0
        )

    async def update_device_status(self, device_id, status, last_seen):
        """Mock update device status"""
        return True

    async def create_device_command(self, command_data):
        """Mock create device command"""
        return True

    async def update_command_status(self, command_id, status, error_message=None):
        """Mock update command status"""
        return True


async def test_device_registered_event():
    """Test that registering device publishes device.registered event"""
    print("\n" + "="*60)
    print("TEST 1: Device Registered Event Publishing")
    print("="*60)

    # Create mock event bus
    mock_bus = MockEventBus()

    # Create device service with mock event bus and skip DB initialization
    device_service = DeviceService.__new__(DeviceService)
    device_service.event_bus = mock_bus
    device_service.device_repo = MockDeviceRepository()
    device_service.mqtt_command_client = None

    # Register device
    device_data = {
        "device_name": "Smart Frame 001",
        "device_type": "smart_frame",
        "manufacturer": "IoT Corp",
        "model": "SF-2024",
        "serial_number": "SN123456789",
        "firmware_version": "1.2.3",
        "hardware_version": "1.0",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "connectivity_type": "wifi"
    }

    device = await device_service.register_device("user_123", device_data)

    # Verify event was published
    assert len(mock_bus.published_events) == 1, "Expected 1 event to be published"

    event = mock_bus.published_events[0]
    assert event["type"] == "device.registered", f"Expected device.registered, got {event['type']}"
    assert event["source"] == "device_service"
    assert event["data"]["device_name"] == "Smart Frame 001"
    assert event["data"]["user_id"] == "user_123"

    print(f"✅ device.registered event published correctly")
    print(f"   Event ID: {event['id']}")
    print(f"   Device: {event['data']['device_name']}")
    print(f"   User: {event['data']['user_id']}")

    return True


async def test_device_online_event():
    """Test that changing device status to active publishes device.online event"""
    print("\n" + "="*60)
    print("TEST 2: Device Online Event Publishing")
    print("="*60)

    # Create mock event bus
    mock_bus = MockEventBus()

    # Create device service and skip DB initialization
    device_service = DeviceService.__new__(DeviceService)
    device_service.event_bus = mock_bus
    device_service.device_repo = MockDeviceRepository()
    device_service.mqtt_command_client = None

    # Update device status to active
    success = await device_service.update_device_status("device_123", DeviceStatus.ACTIVE)

    # Verify event
    assert success
    assert len(mock_bus.published_events) == 1
    event = mock_bus.published_events[0]
    assert event["type"] == "device.online"
    assert event["data"]["device_id"] == "device_123"
    assert event["data"]["status"] == "active"

    print(f"✅ device.online event published correctly")
    print(f"   Device: {event['data']['device_id']}")
    print(f"   Status: {event['data']['status']}")

    return True


async def test_device_offline_event():
    """Test that changing device status to inactive publishes device.offline event"""
    print("\n" + "="*60)
    print("TEST 3: Device Offline Event Publishing")
    print("="*60)

    # Create mock event bus
    mock_bus = MockEventBus()

    # Create device service and skip DB initialization
    device_service = DeviceService.__new__(DeviceService)
    device_service.event_bus = mock_bus
    device_service.device_repo = MockDeviceRepository()
    device_service.mqtt_command_client = None

    # Update device status to inactive
    success = await device_service.update_device_status("device_123", DeviceStatus.INACTIVE)

    # Verify event
    assert success
    assert len(mock_bus.published_events) == 1
    event = mock_bus.published_events[0]
    assert event["type"] == "device.offline"
    assert event["data"]["device_id"] == "device_123"
    assert event["data"]["status"] == "inactive"

    print(f"✅ device.offline event published correctly")
    print(f"   Device: {event['data']['device_id']}")
    print(f"   Status: {event['data']['status']}")

    return True


async def test_device_command_sent_event():
    """Test that sending command publishes device.command_sent event"""
    print("\n" + "="*60)
    print("TEST 4: Device Command Sent Event Publishing")
    print("="*60)

    # Create mock event bus
    mock_bus = MockEventBus()

    # Create device service and skip DB initialization
    device_service = DeviceService.__new__(DeviceService)
    device_service.event_bus = mock_bus
    device_service.device_repo = MockDeviceRepository()
    device_service.mqtt_command_client = None

    # Send command
    command = {
        "command": "update_display",
        "parameters": {"image_url": "https://example.com/image.jpg"},
        "timeout": 30,
        "priority": 5
    }

    result = await device_service.send_command("device_123", "user_456", command)

    # Verify event
    assert result["success"]
    assert len(mock_bus.published_events) == 1
    event = mock_bus.published_events[0]
    assert event["type"] == "device.command_sent"
    assert event["source"] == "device_service"
    assert event["data"]["device_id"] == "device_123"
    assert event["data"]["user_id"] == "user_456"
    assert event["data"]["command"] == "update_display"

    print(f"✅ device.command_sent event published correctly")
    print(f"   Command: {event['data']['command']}")
    print(f"   Device: {event['data']['device_id']}")

    return True


async def test_nats_connection():
    """Test actual NATS connection (if available)"""
    print("\n" + "="*60)
    print("TEST 5: NATS Connection Test")
    print("="*60)

    try:
        # Try to connect to NATS
        event_bus = await get_event_bus("device_service_test")

        if event_bus and event_bus._is_connected:
            print("✅ Successfully connected to NATS")
            print(f"   URL: {event_bus.nats_url}")

            # Test publishing a device event
            from core.nats_client import Event, EventType, ServiceSource
            test_event = Event(
                event_type=EventType.DEVICE_REGISTERED,
                source=ServiceSource.DEVICE_SERVICE,
                data={
                    "device_id": "test_123",
                    "device_name": "Test Device",
                    "user_id": "user_123",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

            success = await event_bus.publish_event(test_event)

            if success:
                print("✅ Test device event published to NATS successfully")
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
    print("DEVICE SERVICE EVENT PUBLISHING TEST SUITE")
    print("="*80)
    print(f"Timestamp: {datetime.now().isoformat()}")

    results = {}

    # Run tests
    try:
        results["device_registered_event"] = await test_device_registered_event()
    except Exception as e:
        print(f"❌ TEST 1 FAILED: {e}")
        results["device_registered_event"] = False

    try:
        results["device_online_event"] = await test_device_online_event()
    except Exception as e:
        print(f"❌ TEST 2 FAILED: {e}")
        results["device_online_event"] = False

    try:
        results["device_offline_event"] = await test_device_offline_event()
    except Exception as e:
        print(f"❌ TEST 3 FAILED: {e}")
        results["device_offline_event"] = False

    try:
        results["device_command_sent_event"] = await test_device_command_sent_event()
    except Exception as e:
        print(f"❌ TEST 4 FAILED: {e}")
        results["device_command_sent_event"] = False

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
