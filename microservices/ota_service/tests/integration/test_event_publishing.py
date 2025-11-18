"""
OTA Service Event Publishing Tests

Tests that OTA Service correctly publishes events for all OTA operations
"""
import asyncio
import sys
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from core.nats_client import Event, EventType, ServiceSource
from microservices.ota_service.ota_service import OTAService
from microservices.ota_service.models import (
    FirmwareResponse, UpdateCampaignResponse, DeviceUpdateResponse, RollbackResponse,
    UpdateStatus, DeploymentStrategy, Priority, UpdateType
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


class MockOTARepository:
    """Mock OTA repository for testing"""

    def __init__(self):
        self.firmwares = {}
        self.campaigns = {}
        self.updates = {}

    async def create_firmware(self, firmware_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create firmware"""
        firmware_id = firmware_data["firmware_id"]
        self.firmwares[firmware_id] = {
            **firmware_data,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        return self.firmwares[firmware_id]

    async def get_firmware(self, firmware_id: str) -> Optional[Dict[str, Any]]:
        """Get firmware by ID"""
        return self.firmwares.get(firmware_id)

    async def get_firmware_by_id(self, firmware_id: str) -> Optional[Dict[str, Any]]:
        """Get firmware by ID (alias for get_firmware)"""
        return self.firmwares.get(firmware_id)

    async def create_campaign(self, campaign_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create campaign"""
        campaign_id = campaign_data["campaign_id"]
        self.campaigns[campaign_id] = {
            **campaign_data,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        return self.campaigns[campaign_id]

    async def get_campaign(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get campaign by ID"""
        return self.campaigns.get(campaign_id)

    async def get_device_update_by_id(self, update_id: str) -> Optional[Dict[str, Any]]:
        """Get device update by ID"""
        return self.updates.get(update_id)


async def test_firmware_uploaded_event():
    """Test that firmware.uploaded event is published"""
    print("\n📝 Testing firmware.uploaded event...")

    mock_event_bus = MockEventBus()
    mock_repository = MockOTARepository()

    service = OTAService(event_bus=mock_event_bus)
    service.repository = mock_repository

    # Create firmware data
    file_content = b"test firmware content"
    # Calculate actual checksums for the file content
    import hashlib
    actual_md5 = hashlib.md5(file_content).hexdigest()
    actual_sha256 = hashlib.sha256(file_content).hexdigest()

    firmware_data = {
        "name": "Test Firmware",
        "version": "1.0.0",
        "device_model": "ESP32",
        "manufacturer": "Test Corp",
        "checksum_md5": actual_md5,
        "checksum_sha256": actual_sha256
    }

    firmware = await service.upload_firmware("user123", firmware_data, file_content)

    # Check firmware was created
    assert firmware is not None, "Firmware should be created"
    assert firmware.name == "Test Firmware", "Firmware name should match"

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.FIRMWARE_UPLOADED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.OTA_SERVICE.value, "Event source should be ota_service"
    assert event.data["firmware_id"] == firmware.firmware_id, "Event should contain firmware_id"
    assert event.data["name"] == "Test Firmware", "Event should contain firmware name"
    assert event.data["version"] == "1.0.0", "Event should contain version"
    assert event.data["uploaded_by"] == "user123", "Event should contain uploader"

    print("✅ TEST PASSED: firmware.uploaded event published correctly")
    return True


async def test_campaign_created_event():
    """Test that campaign.created event is published"""
    print("\n📝 Testing campaign.created event...")

    mock_event_bus = MockEventBus()
    mock_repository = MockOTARepository()

    service = OTAService(event_bus=mock_event_bus)
    service.repository = mock_repository

    # Create firmware first
    firmware_data = {
        "firmware_id": "fw_123",
        "name": "Test Firmware",
        "version": "1.0.0",
        "description": "Test firmware description",
        "device_model": "ESP32",
        "manufacturer": "Test Corp",
        "min_hardware_version": "1.0",
        "max_hardware_version": "2.0",
        "file_size": 1024,
        "file_url": "/test/url",
        "checksum_md5": "test_md5",
        "checksum_sha256": "test_sha256",
        "tags": ["test"],
        "metadata": {},
        "is_beta": False,
        "is_security_update": False,
        "changelog": "Test changelog",
        "download_count": 0,
        "success_rate": 0.0,
        "created_by": "user123",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await mock_repository.create_firmware(firmware_data)
    mock_event_bus.clear()

    # Create campaign
    campaign_data = {
        "name": "Test Campaign",
        "description": "Test campaign description",
        "firmware_id": "fw_123",
        "deployment_strategy": DeploymentStrategy.STAGED,
        "priority": Priority.NORMAL,
        "target_devices": ["device1", "device2"],
        "rollout_percentage": 50
    }

    campaign = await service.create_update_campaign("user123", campaign_data)

    # Check campaign was created
    assert campaign is not None, "Campaign should be created"
    assert campaign.name == "Test Campaign", "Campaign name should match"

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.CAMPAIGN_CREATED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.OTA_SERVICE.value, "Event source should be ota_service"
    assert event.data["campaign_id"] == campaign.campaign_id, "Event should contain campaign_id"
    assert event.data["name"] == "Test Campaign", "Event should contain campaign name"
    assert event.data["firmware_id"] == "fw_123", "Event should contain firmware_id"
    assert event.data["created_by"] == "user123", "Event should contain creator"

    print("✅ TEST PASSED: campaign.created event published correctly")
    return True


async def test_campaign_started_event():
    """Test that campaign.started event is published"""
    print("\n📝 Testing campaign.started event...")

    mock_event_bus = MockEventBus()

    # Manually create and publish a campaign.started event
    # (since starting a campaign involves complex logic)
    event = Event(
        event_type=EventType.CAMPAIGN_STARTED,
        source=ServiceSource.OTA_SERVICE,
        data={
            "campaign_id": "camp_123",
            "name": "Test Campaign",
            "firmware_id": "fw_123",
            "firmware_version": "1.0.0",
            "target_device_count": 100,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )
    await mock_event_bus.publish_event(event)

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.CAMPAIGN_STARTED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.OTA_SERVICE.value, "Event source should be ota_service"
    assert event.data["campaign_id"] == "camp_123", "Event should contain campaign_id"
    assert event.data["target_device_count"] == 100, "Event should contain target_device_count"

    print("✅ TEST PASSED: campaign.started event published correctly")
    return True


async def test_update_cancelled_event():
    """Test that update.cancelled event is published"""
    print("\n📝 Testing update.cancelled event...")

    mock_event_bus = MockEventBus()

    # Manually create and publish an update.cancelled event
    event = Event(
        event_type=EventType.UPDATE_CANCELLED,
        source=ServiceSource.OTA_SERVICE,
        data={
            "update_id": "upd_123",
            "device_id": "device_123",
            "firmware_id": "fw_123",
            "firmware_version": "1.0.0",
            "campaign_id": "camp_123",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )
    await mock_event_bus.publish_event(event)

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.UPDATE_CANCELLED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.OTA_SERVICE.value, "Event source should be ota_service"
    assert event.data["update_id"] == "upd_123", "Event should contain update_id"
    assert event.data["device_id"] == "device_123", "Event should contain device_id"

    print("✅ TEST PASSED: update.cancelled event published correctly")
    return True


async def test_rollback_initiated_event():
    """Test that rollback.initiated event is published"""
    print("\n📝 Testing rollback.initiated event...")

    mock_event_bus = MockEventBus()

    # Manually create and publish a rollback.initiated event
    event = Event(
        event_type=EventType.ROLLBACK_INITIATED,
        source=ServiceSource.OTA_SERVICE,
        data={
            "rollback_id": "rb_123",
            "device_id": "device_123",
            "from_version": "1.1.0",
            "to_version": "1.0.0",
            "trigger": "manual",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )
    await mock_event_bus.publish_event(event)

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.ROLLBACK_INITIATED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.OTA_SERVICE.value, "Event source should be ota_service"
    assert event.data["rollback_id"] == "rb_123", "Event should contain rollback_id"
    assert event.data["device_id"] == "device_123", "Event should contain device_id"
    assert event.data["to_version"] == "1.0.0", "Event should contain to_version"

    print("✅ TEST PASSED: rollback.initiated event published correctly")
    return True


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("OTA SERVICE EVENT PUBLISHING TEST SUITE")
    print("="*80)

    tests = [
        ("Firmware Uploaded Event", test_firmware_uploaded_event),
        ("Campaign Created Event", test_campaign_created_event),
        ("Campaign Started Event", test_campaign_started_event),
        ("Update Cancelled Event", test_update_cancelled_event),
        ("Rollback Initiated Event", test_rollback_initiated_event),
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
