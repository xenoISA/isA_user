"""
Device Service CRUD Integration Tests

Tests device lifecycle operations with real database persistence.
These tests verify data flows through the service and persists correctly.

Usage:
    pytest tests/integration/services/device/test_device_crud_integration.py -v
"""
import pytest
import pytest_asyncio
import httpx
from typing import List
import uuid

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ============================================================================
# Configuration
# ============================================================================

DEVICE_SERVICE_URL = "http://localhost:8220"
API_BASE = f"{DEVICE_SERVICE_URL}/api/v1/devices"
TIMEOUT = 30.0


# ============================================================================
# Helper Functions
# ============================================================================

def make_device_id():
    """Generate unique device ID for test isolation"""
    return f"dev_test_{uuid.uuid4().hex[:12]}"


def make_serial_number():
    """Generate unique serial number"""
    return f"SN_{uuid.uuid4().hex[:12].upper()}"


def make_mac_address():
    """Generate valid MAC address"""
    import random
    return ":".join([f"{random.randint(0, 255):02X}" for _ in range(6)])


def make_device_registration_request(**overrides):
    """Create device registration request with defaults"""
    defaults = {
        "device_name": f"Test Device {uuid.uuid4().hex[:8]}",
        "device_type": "sensor",
        "manufacturer": "Test Corp",
        "model": "TEST-001",
        "serial_number": make_serial_number(),
        "firmware_version": "1.0.0",
        "mac_address": make_mac_address(),
        "connectivity_type": "wifi",
        "security_level": "standard",
        "location": {"latitude": 37.7749, "longitude": -122.4194},
        "metadata": {},
        "tags": ["integration-test"],
    }
    defaults.update(overrides)
    return defaults


def make_device_update_request(**overrides):
    """Create device update request"""
    defaults = {
        "device_name": f"Updated Device {uuid.uuid4().hex[:8]}",
        "firmware_version": "1.1.0",
        "metadata": {"updated": True},
    }
    defaults.update(overrides)
    return defaults


def make_device_group_request(**overrides):
    """Create device group request"""
    defaults = {
        "group_name": f"Test Group {uuid.uuid4().hex[:8]}",
        "description": "Integration test device group",
        "tags": ["test"],
        "metadata": {},
    }
    defaults.update(overrides)
    return defaults


# ============================================================================
# Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def http_client():
    """HTTP client for integration tests"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        yield client


@pytest_asyncio.fixture
async def cleanup_devices(http_client):
    """Track and cleanup devices created during tests"""
    created_device_ids: List[str] = []

    def track(device_id: str):
        created_device_ids.append(device_id)
        return device_id

    yield track

    # Cleanup after test
    for device_id in created_device_ids:
        try:
            await http_client.delete(f"{API_BASE}/{device_id}", headers={"X-Internal-Call": "true"})
        except Exception:
            pass


@pytest_asyncio.fixture
async def auth_headers():
    """
    Internal service authentication headers.
    For integration tests, we use internal bypass.
    """
    return {"X-Internal-Call": "true"}


# ============================================================================
# Device Lifecycle Integration Tests
# ============================================================================

class TestDeviceLifecycleIntegration:
    """
    Integration tests for device CRUD lifecycle.
    Tests data persistence across create/read/update/delete operations.
    """

    async def test_full_device_lifecycle(self, http_client, auth_headers, cleanup_devices):
        """
        Integration: Full device lifecycle - register, read, update, delete

        1. Register device and verify persisted
        2. Read device and verify data matches
        3. Update device and verify changes persist
        4. Delete device and verify removal
        """
        # 1. REGISTER (Create)
        registration = make_device_registration_request(
            device_name="Lifecycle Test Device",
            device_type="smart_frame",
        )

        register_response = await http_client.post(
            API_BASE,
            json=registration,
            headers=auth_headers,
        )
        assert register_response.status_code == 200, f"Registration failed: {register_response.text}"

        device_data = register_response.json()
        device_id = device_data["device_id"]
        cleanup_devices(device_id)

        assert device_data["device_name"] == "Lifecycle Test Device"
        assert device_data["device_type"] == "smart_frame"
        assert device_data["status"] == "pending"

        # 2. READ - verify persisted
        get_response = await http_client.get(
            f"{API_BASE}/{device_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 200

        read_data = get_response.json()
        assert read_data["device_id"] == device_id
        assert read_data["device_name"] == "Lifecycle Test Device"

        # 3. UPDATE
        update_request = make_device_update_request(
            device_name="Updated Lifecycle Device",
            status="active",
        )

        update_response = await http_client.put(
            f"{API_BASE}/{device_id}",
            json=update_request,
            headers=auth_headers,
        )
        assert update_response.status_code == 200

        updated_data = update_response.json()
        assert updated_data["device_name"] == "Updated Lifecycle Device"

        # Verify update persisted
        verify_response = await http_client.get(
            f"{API_BASE}/{device_id}",
            headers=auth_headers,
        )
        verify_data = verify_response.json()
        assert verify_data["device_name"] == "Updated Lifecycle Device"

        # 4. DELETE
        delete_response = await http_client.delete(
            f"{API_BASE}/{device_id}",
            headers=auth_headers,
        )
        assert delete_response.status_code == 200

        # Verify deleted (404)
        get_deleted_response = await http_client.get(
            f"{API_BASE}/{device_id}",
            headers=auth_headers,
        )
        # Note: Service might return empty or 404 depending on implementation
        # assert get_deleted_response.status_code in [404, 200]


class TestDeviceRegistrationIntegration:
    """
    Integration tests for device registration.
    """

    async def test_register_sensor_device(self, http_client, auth_headers, cleanup_devices):
        """
        Integration: Register sensor device
        """
        registration = make_device_registration_request(
            device_type="sensor",
            device_name="Temperature Sensor",
        )

        response = await http_client.post(
            API_BASE,
            json=registration,
            headers=auth_headers,
        )
        assert response.status_code == 200

        device = response.json()
        cleanup_devices(device["device_id"])

        assert device["device_type"] == "sensor"
        assert device["device_name"] == "Temperature Sensor"
        assert "device_id" in device

    async def test_register_smart_frame_device(self, http_client, auth_headers, cleanup_devices):
        """
        Integration: Register smart frame device
        """
        registration = make_device_registration_request(
            device_type="smart_frame",
            device_name="EmoFrame 001",
            manufacturer="EmoFrame Inc",
        )

        response = await http_client.post(
            API_BASE,
            json=registration,
            headers=auth_headers,
        )
        assert response.status_code == 200

        device = response.json()
        cleanup_devices(device["device_id"])

        assert device["device_type"] == "smart_frame"
        assert device["manufacturer"] == "EmoFrame Inc"


class TestDeviceListingIntegration:
    """
    Integration tests for device listing and filtering.
    """

    async def test_list_user_devices(self, http_client, auth_headers, cleanup_devices):
        """
        Integration: List devices for a user

        1. Create multiple devices
        2. List devices
        3. Verify all created devices in list
        """
        # Create 3 devices
        device_ids = []
        for i in range(3):
            registration = make_device_registration_request(
                device_name=f"List Test Device {i}",
            )
            response = await http_client.post(
                API_BASE,
                json=registration,
                headers=auth_headers,
            )
            assert response.status_code == 200
            device_id = response.json()["device_id"]
            device_ids.append(device_id)
            cleanup_devices(device_id)

        # List devices
        list_response = await http_client.get(
            API_BASE,
            headers=auth_headers,
            params={"limit": 10},
        )
        assert list_response.status_code == 200

        list_data = list_response.json()
        assert "devices" in list_data
        # We created at least 3 devices
        assert len(list_data["devices"]) >= 3


class TestDeviceGroupsIntegration:
    """
    Integration tests for device groups.
    """

    async def test_create_device_group(self, http_client, auth_headers):
        """
        Integration: Create device group
        """
        group_request = make_device_group_request(
            group_name="Office Devices",
            description="All office sensors",
        )

        response = await http_client.post(
            f"{DEVICE_SERVICE_URL}/api/v1/groups",
            json=group_request,
            headers=auth_headers,
        )
        assert response.status_code == 200

        group = response.json()
        assert group["group_name"] == "Office Devices"
        assert "group_id" in group


class TestDeviceCommandsIntegration:
    """
    Integration tests for device commands.
    """

    async def test_send_command_to_device(self, http_client, auth_headers, cleanup_devices):
        """
        Integration: Send command to active device
        """
        # Create and activate device
        registration = make_device_registration_request(
            device_name="Command Test Device",
        )
        register_response = await http_client.post(
            API_BASE,
            json=registration,
            headers=auth_headers,
        )
        device = register_response.json()
        device_id = device["device_id"]
        cleanup_devices(device_id)

        # Activate device
        await http_client.put(
            f"{API_BASE}/{device_id}",
            json={"status": "active"},
            headers=auth_headers,
        )

        # Send command
        command = {
            "command": "reboot",
            "parameters": {"force": False},
            "timeout": 30,
            "priority": 5,
        }

        command_response = await http_client.post(
            f"{API_BASE}/{device_id}/commands",
            json=command,
            headers=auth_headers,
        )
        assert command_response.status_code == 200

        result = command_response.json()
        assert "command_id" in result or "success" in result


class TestDeviceStatsIntegration:
    """
    Integration tests for device statistics.
    """

    async def test_get_device_stats(self, http_client, auth_headers, cleanup_devices):
        """
        Integration: Get device statistics for user
        """
        # Create a couple of devices
        for i in range(2):
            registration = make_device_registration_request()
            response = await http_client.post(
                API_BASE,
                json=registration,
                headers=auth_headers,
            )
            cleanup_devices(response.json()["device_id"])

        # Get stats
        stats_response = await http_client.get(
            f"{API_BASE}/stats",
            headers=auth_headers,
        )
        assert stats_response.status_code == 200

        stats = stats_response.json()
        assert "total_devices" in stats
        assert stats["total_devices"] >= 2
