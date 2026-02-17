"""
Device Service Component Golden Tests

These tests document CURRENT DeviceService behavior with mocked deps.
Uses proper dependency injection - no patching needed!

Golden tests capture behavior as-is for regression detection.
"""
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from microservices.device_service.device_service import DeviceService
from microservices.device_service.models import DeviceStatus, DeviceType, ConnectivityType
from .mocks import (
    MockDeviceRepository,
    MockEventBus,
    MockTelemetryClient,
    MockMQTTCommandClient,
)

pytestmark = [pytest.mark.component, pytest.mark.golden, pytest.mark.asyncio]


# ======================
# Fixtures
# ======================

@pytest_asyncio.fixture
async def mock_repo():
    """Provide MockDeviceRepository"""
    return MockDeviceRepository()


@pytest_asyncio.fixture
async def mock_event_bus():
    """Provide MockEventBus"""
    return MockEventBus()


@pytest_asyncio.fixture
async def mock_telemetry_client():
    """Provide MockTelemetryClient"""
    return MockTelemetryClient()


@pytest_asyncio.fixture
async def mock_mqtt_client():
    """Provide MockMQTTCommandClient"""
    return MockMQTTCommandClient()


@pytest_asyncio.fixture
async def device_service(mock_repo, mock_event_bus, mock_mqtt_client):
    """Create DeviceService with mocked dependencies"""
    service = DeviceService(
        repository=mock_repo,
        event_bus=mock_event_bus,
        mqtt_client=mock_mqtt_client,
    )
    return service


# ======================
# Device Registration Tests
# ======================

async def test_register_device_success(device_service, mock_repo, mock_event_bus):
    """Test successful device registration"""
    # Given
    user_id = "user_123"
    device_data = {
        "device_name": "Smart Sensor 001",
        "device_type": DeviceType.SENSOR,
        "manufacturer": "IoT Corp",
        "model": "SS-2024",
        "serial_number": "SN123456789",
        "firmware_version": "1.0.0",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "connectivity_type": ConnectivityType.WIFI,
    }

    # When
    result = await device_service.register_device(user_id, device_data)

    # Then
    assert result is not None
    assert result.user_id == user_id
    assert result.device_name == "Smart Sensor 001"
    assert result.device_type == DeviceType.SENSOR
    assert result.status == DeviceStatus.PENDING
    assert mock_repo.call_count["create_device"] == 1
    assert mock_event_bus.call_count["publish_event"] >= 1  # device.registered event


async def test_register_device_with_organization(device_service, mock_repo):
    """Test device registration with organization"""
    # Given
    user_id = "user_123"
    device_data = {
        "device_name": "Office Sensor",
        "device_type": DeviceType.SENSOR,
        "organization_id": "org_456",
        "manufacturer": "IoT Corp",
        "model": "SS-2024",
        "serial_number": "SN123456790",
        "firmware_version": "1.0.0",
        "connectivity_type": ConnectivityType.WIFI,
    }

    # When
    result = await device_service.register_device(user_id, device_data)

    # Then
    assert result is not None
    assert result.organization_id == "org_456"


async def test_register_smart_frame(device_service, mock_repo):
    """Test smart frame registration"""
    # Given
    user_id = "user_123"
    device_data = {
        "device_name": "EmoFrame 001",
        "device_type": DeviceType.SMART_FRAME,
        "manufacturer": "EmoFrame Inc",
        "model": "EF-2024",
        "serial_number": "EF123456789",
        "firmware_version": "1.0.0",
        "mac_address": "11:22:33:44:55:66",
        "connectivity_type": ConnectivityType.WIFI,
    }

    # When
    result = await device_service.register_device(user_id, device_data)

    # Then
    assert result is not None
    assert result.device_type == DeviceType.SMART_FRAME
    assert result.status == DeviceStatus.PENDING


# ======================
# Device Retrieval Tests
# ======================

async def test_get_device_by_id_success(device_service, mock_repo):
    """Test getting device by ID"""
    # Given - create a device first
    user_id = "user_123"
    device_data = {
        "device_name": "Test Device",
        "device_type": DeviceType.SENSOR,
        "manufacturer": "Test Corp",
        "model": "T-001",
        "serial_number": "SN_TEST001",
        "firmware_version": "1.0.0",
        "connectivity_type": ConnectivityType.WIFI,
    }
    created_device = await device_service.register_device(user_id, device_data)

    # When
    result = await device_service.get_device(created_device.device_id)

    # Then
    assert result is not None
    assert result.device_id == created_device.device_id
    assert result.device_name == "Test Device"


async def test_get_device_by_id_not_found(device_service, mock_repo):
    """Test getting non-existent device"""
    # When
    result = await device_service.get_device("nonexistent_device")

    # Then
    assert result is None


async def test_list_user_devices(device_service, mock_repo):
    """Test listing devices for a user"""
    # Given - create multiple devices
    user_id = "user_123"
    for i in range(3):
        await device_service.register_device(user_id, {
            "device_name": f"Device {i}",
            "device_type": DeviceType.SENSOR,
            "manufacturer": "Test Corp",
            "model": f"T-{i:03d}",
            "serial_number": f"SN_{i:03d}",
            "firmware_version": "1.0.0",
            "connectivity_type": ConnectivityType.WIFI,
        })

    # When
    devices = await device_service.list_user_devices(user_id)

    # Then
    assert len(devices) == 3
    assert all(d.user_id == user_id for d in devices)


async def test_list_user_devices_filtered_by_type(device_service, mock_repo):
    """Test listing devices filtered by type"""
    # Given - create devices of different types
    user_id = "user_123"
    await device_service.register_device(user_id, {
        "device_name": "Sensor 1",
        "device_type": DeviceType.SENSOR,
        "manufacturer": "Test Corp",
        "model": "S-001",
        "serial_number": "SN_S001",
        "firmware_version": "1.0.0",
        "connectivity_type": ConnectivityType.WIFI,
    })
    await device_service.register_device(user_id, {
        "device_name": "Frame 1",
        "device_type": DeviceType.SMART_FRAME,
        "manufacturer": "Frame Corp",
        "model": "F-001",
        "serial_number": "SN_F001",
        "firmware_version": "1.0.0",
        "connectivity_type": ConnectivityType.WIFI,
    })

    # When
    sensors = await device_service.list_user_devices(user_id, device_type=DeviceType.SENSOR)

    # Then
    assert len(sensors) == 1
    assert sensors[0].device_type == DeviceType.SENSOR


# ======================
# Device Update Tests
# ======================

async def test_update_device_status(device_service, mock_repo):
    """Test updating device status"""
    # Given
    user_id = "user_123"
    device_data = {
        "device_name": "Test Device",
        "device_type": DeviceType.SENSOR,
        "manufacturer": "Test Corp",
        "model": "T-001",
        "serial_number": "SN_TEST",
        "firmware_version": "1.0.0",
        "connectivity_type": ConnectivityType.WIFI,
    }
    device = await device_service.register_device(user_id, device_data)

    # When
    success = await device_service.update_device_status(device.device_id, DeviceStatus.ACTIVE)

    # Then
    assert success is True
    updated_device = await device_service.get_device(device.device_id)
    assert updated_device.status == DeviceStatus.ACTIVE


async def test_update_device_info(device_service, mock_repo):
    """Test updating device information"""
    # Given
    user_id = "user_123"
    device_data = {
        "device_name": "Old Name",
        "device_type": DeviceType.SENSOR,
        "manufacturer": "Test Corp",
        "model": "T-001",
        "serial_number": "SN_OLD",
        "firmware_version": "1.0.0",
        "connectivity_type": ConnectivityType.WIFI,
    }
    device = await device_service.register_device(user_id, device_data)

    # When
    result = await device_service.update_device(device.device_id, {
        "device_name": "New Name",
        "firmware_version": "2.0.0",
    })

    # Then
    assert result is not None
    assert result.device_name == "New Name"
    assert result.firmware_version == "2.0.0"


# ======================
# Device Deletion Tests
# ======================

async def test_decommission_device(device_service, mock_repo, mock_event_bus):
    """Test decommissioning a device"""
    # Given
    user_id = "user_123"
    device_data = {
        "device_name": "Device to Remove",
        "device_type": DeviceType.SENSOR,
        "manufacturer": "Test Corp",
        "model": "T-001",
        "serial_number": "SN_DEL",
        "firmware_version": "1.0.0",
        "connectivity_type": ConnectivityType.WIFI,
    }
    device = await device_service.register_device(user_id, device_data)

    # When
    success = await device_service.decommission_device(device.device_id)

    # Then
    assert success is True
    # Device should be deleted
    result = await device_service.get_device(device.device_id)
    assert result is None


# ======================
# Device Group Tests
# ======================

async def test_create_device_group(device_service, mock_repo):
    """Test creating a device group"""
    # Given
    user_id = "user_123"
    group_data = {
        "group_name": "Office Devices",
        "description": "All office sensors",
        "device_ids": [],
    }

    # When
    result = await device_service.create_device_group(user_id, group_data)

    # Then
    assert result is not None
    assert result.group_name == "Office Devices"
    assert result.user_id == user_id


async def test_get_device_group(device_service, mock_repo):
    """Test getting a device group"""
    # Given
    user_id = "user_123"
    group_data = {
        "group_name": "Test Group",
        "description": "Test group",
    }
    created_group = await device_service.create_device_group(user_id, group_data)

    # When
    result = await device_service.get_device_group(created_group.group_id)

    # Then
    assert result is not None
    assert result.group_id == created_group.group_id
    assert result.group_name == "Test Group"


# ======================
# Device Command Tests
# ======================

async def test_send_command(device_service, mock_repo, mock_mqtt_client):
    """Test sending command to device"""
    # Given
    user_id = "user_123"
    device_data = {
        "device_name": "Controllable Device",
        "device_type": DeviceType.SENSOR,
        "manufacturer": "Test Corp",
        "model": "T-001",
        "serial_number": "SN_CMD",
        "firmware_version": "1.0.0",
        "connectivity_type": ConnectivityType.WIFI,
    }
    device = await device_service.register_device(user_id, device_data)

    # Update device to active status
    await device_service.update_device_status(device.device_id, DeviceStatus.ACTIVE)

    command_data = {
        "command": "reboot",
        "parameters": {"force": True},
        "timeout": 30,
    }

    # When
    result = await device_service.send_command(device.device_id, user_id, command_data)

    # Then
    assert result is not None
    assert result.get("success") is True
    assert "command_id" in result


async def test_send_command_to_inactive_device(device_service, mock_repo):
    """Test sending command to inactive device"""
    # Given
    user_id = "user_123"
    device_data = {
        "device_name": "Inactive Device",
        "device_type": DeviceType.SENSOR,
        "manufacturer": "Test Corp",
        "model": "T-001",
        "serial_number": "SN_INACTIVE",
        "firmware_version": "1.0.0",
        "connectivity_type": ConnectivityType.WIFI,
    }
    device = await device_service.register_device(user_id, device_data)
    # Device remains in PENDING status

    command_data = {
        "command": "reboot",
        "parameters": {},
    }

    # When
    result = await device_service.send_command(device.device_id, user_id, command_data)

    # Then
    # Should still create command record, but might not send via MQTT
    assert result is not None


# ======================
# Device Health Tests
# ======================

async def test_get_device_health(device_service, mock_repo, mock_telemetry_client):
    """Test getting device health status"""
    # Given
    user_id = "user_123"
    device_data = {
        "device_name": "Healthy Device",
        "device_type": DeviceType.SENSOR,
        "manufacturer": "Test Corp",
        "model": "T-001",
        "serial_number": "SN_HEALTH",
        "firmware_version": "1.0.0",
        "connectivity_type": ConnectivityType.WIFI,
    }
    device = await device_service.register_device(user_id, device_data)
    await device_service.update_device_status(device.device_id, DeviceStatus.ACTIVE)

    # When
    # Note: This depends on how DeviceService integrates telemetry client
    # For now, we just test that the method exists
    health = await device_service.get_device_health(device.device_id)

    # Then
    assert health is not None
    # Exact structure depends on implementation


# ======================
# Device Stats Tests
# ======================

async def test_get_device_stats(device_service, mock_repo):
    """Test getting device statistics"""
    # Given
    user_id = "user_123"
    # Create multiple devices with different statuses
    for i in range(3):
        device = await device_service.register_device(user_id, {
            "device_name": f"Device {i}",
            "device_type": DeviceType.SENSOR,
            "manufacturer": "Test Corp",
            "model": f"T-{i:03d}",
            "serial_number": f"SN_STATS_{i}",
            "firmware_version": "1.0.0",
            "connectivity_type": ConnectivityType.WIFI,
        })
        if i < 2:
            await device_service.update_device_status(device.device_id, DeviceStatus.ACTIVE)

    # When
    stats = await device_service.get_device_stats(user_id)

    # Then
    assert stats is not None
    assert stats.total_devices == 3
    assert stats.active_devices == 2
    assert stats.inactive_devices == 0  # Changed from 1 to 0 - devices start as PENDING


# ======================
# Event Publishing Tests
# ======================

async def test_device_registered_event_published(device_service, mock_event_bus):
    """Test that device.registered event is published"""
    # Given
    user_id = "user_123"
    device_data = {
        "device_name": "Event Test Device",
        "device_type": DeviceType.SENSOR,
        "manufacturer": "Test Corp",
        "model": "T-001",
        "serial_number": "SN_EVENT",
        "firmware_version": "1.0.0",
        "connectivity_type": ConnectivityType.WIFI,
    }

    # When
    await device_service.register_device(user_id, device_data)

    # Then
    assert len(mock_event_bus.published_events) >= 1
    # Check that a device.registered event was published
    # Event objects have a .type attribute (e.g., "device.registered")
    event_types = [getattr(e, 'type', str(e)) for e in mock_event_bus.published_events]
    assert any("device.registered" in str(event_type).lower() or "registered" in str(event_type).lower() for event_type in event_types)


async def test_device_status_updated_event_published(device_service, mock_event_bus):
    """Test that device status update publishes event"""
    # Given
    user_id = "user_123"
    device_data = {
        "device_name": "Status Test Device",
        "device_type": DeviceType.SENSOR,
        "manufacturer": "Test Corp",
        "model": "T-001",
        "serial_number": "SN_STATUS",
        "firmware_version": "1.0.0",
        "connectivity_type": ConnectivityType.WIFI,
    }
    device = await device_service.register_device(user_id, device_data)

    # Clear previous events
    mock_event_bus.published_events.clear()

    # When
    await device_service.update_device_status(device.device_id, DeviceStatus.ACTIVE)

    # Then
    # Should publish device.status_updated event
    assert len(mock_event_bus.published_events) >= 1
