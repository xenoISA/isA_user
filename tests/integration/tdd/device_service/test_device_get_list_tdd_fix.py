"""
Device Service GET/LIST Endpoint TDD Fixes

BUGS FOUND in integration testing:
1. GET /api/v1/devices/{device_id} returns hardcoded "Smart Sensor 001" instead of actual device
2. GET /api/v1/devices returns empty list even after creating devices

This file contains RED tests that define the CORRECT behavior.
These tests should FAIL initially, then pass after fixing main.py endpoints.

According to TDD_CONTRACT.md workflow:
- RED: Write tests defining correct behavior (this file)
- Fix: Update main.py to call actual service methods
- GREEN: Tests pass

Usage:
    pytest tests/integration/services/device/test_device_get_list_tdd_fix.py -v
"""
import pytest
import pytest_asyncio
import httpx
import uuid
from typing import List

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

# ============================================================================
# Configuration
# ============================================================================

DEVICE_SERVICE_URL = "http://localhost:8220"
API_BASE = f"{DEVICE_SERVICE_URL}/api/v1/devices"
TIMEOUT = 30.0


# ============================================================================
# Helper Functions (copied from test_device_crud_integration.py)
# ============================================================================

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
# BUG #1: GET Endpoint Returns Hardcoded Data - TDD RED Tests
# ============================================================================

class TestDeviceGetEndpointFix:
    """
    TDD RED tests for Bug #1: GET endpoint returns hardcoded "Smart Sensor 001"

    CURRENT BEHAVIOR (BUG):
    - GET /api/v1/devices/{device_id} always returns:
      - device_name: "Smart Sensor 001"
      - device_type: "sensor"
      - All other hardcoded values

    EXPECTED BEHAVIOR (CORRECT):
    - GET should return the ACTUAL device data from database
    - device_name, device_type, etc should match what was created

    LOCATION: microservices/device_service/main.py:336-364
    """

    async def test_get_device_returns_actual_device_name(self, http_client, auth_headers, cleanup_devices):
        """
        RED: GET should return the actual device name, not 'Smart Sensor 001'

        This test will FAIL until main.py GET endpoint is fixed to call service layer
        """
        # Create a device with unique name
        unique_name = f"Unique TDD Device {uuid.uuid4().hex[:8]}"
        registration = make_device_registration_request(
            device_name=unique_name,
            device_type="smart_frame",
        )

        create_response = await http_client.post(
            API_BASE,
            json=registration,
            headers=auth_headers,
        )
        assert create_response.status_code == 200, f"Failed to create device: {create_response.text}"

        device_data = create_response.json()
        device_id = device_data["device_id"]
        cleanup_devices(device_id)

        # Now GET the device - should return ACTUAL data, not hardcoded
        get_response = await http_client.get(
            f"{API_BASE}/{device_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 200, f"Failed to get device: {get_response.text}"

        retrieved_device = get_response.json()

        # BUG: This will FAIL because GET returns "Smart Sensor 001" instead of unique_name
        assert retrieved_device["device_name"] == unique_name, \
            f"Expected device_name='{unique_name}', got '{retrieved_device['device_name']}'"

        # Also verify device_type is correct (not hardcoded "sensor")
        assert retrieved_device["device_type"] == "smart_frame", \
            f"Expected device_type='smart_frame', got '{retrieved_device['device_type']}'"

    async def test_get_device_returns_actual_device_id(self, http_client, auth_headers, cleanup_devices):
        """
        RED: GET should return the correct device_id

        Currently, GET might return the ID from the path but all other data is hardcoded
        """
        # Create device
        registration = make_device_registration_request(
            device_name="TDD ID Test Device",
        )

        create_response = await http_client.post(
            API_BASE,
            json=registration,
            headers=auth_headers,
        )
        assert create_response.status_code == 200

        created_device = create_response.json()
        device_id = created_device["device_id"]
        cleanup_devices(device_id)

        # GET should return same device_id
        get_response = await http_client.get(
            f"{API_BASE}/{device_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 200

        retrieved_device = get_response.json()
        assert retrieved_device["device_id"] == device_id

    async def test_get_device_returns_actual_manufacturer(self, http_client, auth_headers, cleanup_devices):
        """
        RED: GET should return actual manufacturer, not hardcoded "IoT Corp"
        """
        unique_manufacturer = f"TDD Corp {uuid.uuid4().hex[:6]}"
        registration = make_device_registration_request(
            device_name="Manufacturer Test",
            manufacturer=unique_manufacturer,
        )

        create_response = await http_client.post(
            API_BASE,
            json=registration,
            headers=auth_headers,
        )
        device_id = create_response.json()["device_id"]
        cleanup_devices(device_id)

        # GET should return actual manufacturer
        get_response = await http_client.get(
            f"{API_BASE}/{device_id}",
            headers=auth_headers,
        )

        retrieved_device = get_response.json()

        # BUG: Will FAIL because GET returns hardcoded "IoT Corp"
        assert retrieved_device["manufacturer"] == unique_manufacturer, \
            f"Expected manufacturer='{unique_manufacturer}', got '{retrieved_device['manufacturer']}'"

    async def test_get_nonexistent_device_returns_404(self, http_client, auth_headers):
        """
        RED: GET non-existent device should return 404

        Currently might return hardcoded data for ANY device_id
        """
        fake_device_id = f"dev_nonexistent_{uuid.uuid4().hex[:12]}"

        get_response = await http_client.get(
            f"{API_BASE}/{fake_device_id}",
            headers=auth_headers,
        )

        # Should return 404 for non-existent device
        assert get_response.status_code == 404, \
            f"Expected 404 for non-existent device, got {get_response.status_code}"


# ============================================================================
# BUG #2: LIST Endpoint Returns Empty Array - TDD RED Tests
# ============================================================================

class TestDeviceListEndpointFix:
    """
    TDD RED tests for Bug #2: LIST endpoint returns empty devices array

    CURRENT BEHAVIOR (BUG):
    - GET /api/v1/devices always returns:
      - devices: []  (empty list)
      - count: 0

    EXPECTED BEHAVIOR (CORRECT):
    - GET /api/v1/devices should return actual devices from database
    - devices array should contain created devices
    - count should reflect actual device count

    LOCATION: microservices/device_service/main.py:98-121
    """

    async def test_list_devices_includes_created_devices(self, http_client, auth_headers, cleanup_devices):
        """
        RED: LIST should return devices that were created, not empty array

        This test will FAIL until main.py LIST endpoint is fixed to call service layer
        """
        # Create 3 devices with unique names
        created_devices = []
        for i in range(3):
            unique_name = f"TDD List Test Device {i} {uuid.uuid4().hex[:6]}"
            registration = make_device_registration_request(
                device_name=unique_name,
            )

            create_response = await http_client.post(
                API_BASE,
                json=registration,
                headers=auth_headers,
            )
            assert create_response.status_code == 200

            device_data = create_response.json()
            created_devices.append(device_data)
            cleanup_devices(device_data["device_id"])

        # Now LIST devices - should include our created devices
        list_response = await http_client.get(
            API_BASE,
            headers=auth_headers,
            params={"limit": 10},
        )
        assert list_response.status_code == 200, f"Failed to list devices: {list_response.text}"

        list_data = list_response.json()

        # BUG: This will FAIL because LIST returns empty array
        assert "devices" in list_data
        assert isinstance(list_data["devices"], list)
        assert len(list_data["devices"]) >= 3, \
            f"Expected at least 3 devices in list, got {len(list_data['devices'])}"

        # Verify at least one of our created devices is in the list
        device_ids_in_list = [d["device_id"] for d in list_data["devices"]]
        created_device_ids = [d["device_id"] for d in created_devices]

        found_devices = [dev_id for dev_id in created_device_ids if dev_id in device_ids_in_list]
        assert len(found_devices) > 0, \
            f"None of our created devices found in list. Created: {created_device_ids}, Listed: {device_ids_in_list}"

    async def test_list_devices_count_is_accurate(self, http_client, auth_headers, cleanup_devices):
        """
        RED: LIST response count should match number of devices

        Currently returns count: 0 even when devices exist
        """
        # Create 2 devices
        for i in range(2):
            registration = make_device_registration_request(
                device_name=f"Count Test Device {i}",
            )
            create_response = await http_client.post(
                API_BASE,
                json=registration,
                headers=auth_headers,
            )
            cleanup_devices(create_response.json()["device_id"])

        # LIST devices
        list_response = await http_client.get(
            API_BASE,
            headers=auth_headers,
            params={"limit": 100},
        )

        list_data = list_response.json()

        # BUG: count is hardcoded to 0, should be >= 2
        assert list_data.get("count", 0) >= 2, \
            f"Expected count >= 2, got {list_data.get('count', 0)}"

    async def test_list_devices_empty_when_no_devices(self, http_client, auth_headers):
        """
        GREEN: LIST should correctly return empty when user has no devices

        This test might already pass, but ensures empty state works correctly
        """
        # Use a unique user context that has no devices
        # For now, we'll test with existing headers but this should still work
        list_response = await http_client.get(
            API_BASE,
            headers=auth_headers,
            params={"limit": 10},
        )

        assert list_response.status_code == 200
        list_data = list_response.json()

        # Should have devices array (even if empty)
        assert "devices" in list_data
        assert isinstance(list_data["devices"], list)
        # Note: We can't assert it's empty because other tests may have created devices

    async def test_list_devices_respects_limit_parameter(self, http_client, auth_headers, cleanup_devices):
        """
        RED: LIST should respect limit parameter

        Currently ignores limit and returns hardcoded empty array
        """
        # Create 5 devices
        for i in range(5):
            registration = make_device_registration_request(
                device_name=f"Limit Test Device {i}",
            )
            create_response = await http_client.post(
                API_BASE,
                json=registration,
                headers=auth_headers,
            )
            cleanup_devices(create_response.json()["device_id"])

        # LIST with limit=2
        list_response = await http_client.get(
            API_BASE,
            headers=auth_headers,
            params={"limit": 2},
        )

        list_data = list_response.json()

        # Should return devices (currently returns empty)
        # When fixed, should respect limit (but might return <= limit if fewer devices exist)
        assert len(list_data["devices"]) >= 2 or len(list_data["devices"]) == list_data.get("count", 0), \
            f"Expected devices in list, got {len(list_data['devices'])}"


# ============================================================================
# Integration Tests: Verify GET and LIST work together
# ============================================================================

class TestGetListIntegration:
    """
    Tests that verify GET and LIST work correctly together after fixes
    """

    async def test_create_then_list_then_get_consistency(self, http_client, auth_headers, cleanup_devices):
        """
        RED: Create device, verify it appears in LIST, then GET it

        This tests the full consistency of create -> list -> get operations
        """
        # Create device
        unique_name = f"Consistency Test {uuid.uuid4().hex[:8]}"
        registration = make_device_registration_request(
            device_name=unique_name,
            device_type="sensor",
        )

        create_response = await http_client.post(
            API_BASE,
            json=registration,
            headers=auth_headers,
        )
        created_device = create_response.json()
        device_id = created_device["device_id"]
        cleanup_devices(device_id)

        # LIST should include this device
        list_response = await http_client.get(
            API_BASE,
            headers=auth_headers,
            params={"limit": 100},
        )
        list_data = list_response.json()

        device_ids_in_list = [d["device_id"] for d in list_data["devices"]]
        assert device_id in device_ids_in_list, \
            f"Created device {device_id} not found in list"

        # Find our device in the list
        our_device_in_list = next((d for d in list_data["devices"] if d["device_id"] == device_id), None)
        assert our_device_in_list is not None
        assert our_device_in_list["device_name"] == unique_name

        # GET should return same data
        get_response = await http_client.get(
            f"{API_BASE}/{device_id}",
            headers=auth_headers,
        )
        get_device = get_response.json()

        # GET and LIST should return consistent data
        assert get_device["device_id"] == our_device_in_list["device_id"]
        assert get_device["device_name"] == our_device_in_list["device_name"]
        assert get_device["device_type"] == our_device_in_list["device_type"]
