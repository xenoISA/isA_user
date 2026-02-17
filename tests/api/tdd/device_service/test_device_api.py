"""
Device Service API Contract Tests (Layer 1)

RED PHASE: Define what the Device API should return before implementation.
These tests define the HTTP contracts for the Device service.

Usage:
    pytest tests/api/services/device -v                    # Run all device API tests
    pytest tests/api/services/device -v -k "register"      # Run registration tests
    pytest tests/api/services/device -v --tb=short         # Short traceback
"""
import pytest
import uuid

pytestmark = [pytest.mark.api, pytest.mark.asyncio]


# =============================================================================
# Helper Functions
# =============================================================================

def make_device_registration(**overrides):
    """Create device registration payload with defaults"""
    defaults = {
        "device_name": f"Test Device {uuid.uuid4().hex[:8]}",
        "device_type": "sensor",
        "manufacturer": "Test Corp",
        "model": "TEST-001",
        "serial_number": f"SN_{uuid.uuid4().hex[:12].upper()}",
        "firmware_version": "1.0.0",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "connectivity_type": "wifi",
        "security_level": "standard",
        "location": {"latitude": 37.7749, "longitude": -122.4194},
        "metadata": {},
        "tags": ["api-test"],
    }
    defaults.update(overrides)
    return defaults


# =============================================================================
# Device Registration Tests
# =============================================================================

class TestDeviceRegistrationEndpoint:
    """
    POST /api/v1/devices

    Register a new device with the system.
    """

    async def test_register_sensor_device(self, device_api, api_assert):
        """RED: Should register a new sensor device"""
        registration = make_device_registration(
            device_type="sensor",
            device_name="Temperature Sensor"
        )

        response = await device_api.post("", json=registration)

        api_assert.assert_created(response)
        data = response.json()

        # Contract: Response must have these fields
        api_assert.assert_has_fields(data, [
            "device_id", "device_name", "device_type", "status",
            "manufacturer", "model", "serial_number", "firmware_version",
            "registered_at", "user_id"
        ])

        assert data["device_name"] == "Temperature Sensor"
        assert data["device_type"] == "sensor"
        assert data["status"] == "pending"

    async def test_register_smart_frame_device(self, device_api, api_assert):
        """RED: Should register a smart frame device"""
        registration = make_device_registration(
            device_type="smart_frame",
            device_name="EmoFrame 001",
            manufacturer="EmoFrame Inc"
        )

        response = await device_api.post("", json=registration)

        api_assert.assert_created(response)
        data = response.json()

        assert data["device_type"] == "smart_frame"
        assert data["manufacturer"] == "EmoFrame Inc"

    async def test_register_validates_required_fields(self, device_api, api_assert):
        """RED: Missing required fields should return 422"""
        # Missing device_name
        response = await device_api.post("", json={
            "device_type": "sensor",
            "manufacturer": "Test",
            "model": "TEST-001"
        })
        api_assert.assert_validation_error(response)

        # Missing device_type
        response = await device_api.post("", json={
            "device_name": "Test Device",
            "manufacturer": "Test",
            "model": "TEST-001"
        })
        api_assert.assert_validation_error(response)

    async def test_register_validates_mac_address_format(self, device_api, api_assert):
        """RED: Invalid MAC address format should return 422"""
        registration = make_device_registration(
            mac_address="invalid-mac"
        )

        response = await device_api.post("", json=registration)
        api_assert.assert_validation_error(response)

    async def test_register_validates_device_type_enum(self, device_api, api_assert):
        """RED: Invalid device type should return 422"""
        registration = make_device_registration(
            device_type="invalid_type"
        )

        response = await device_api.post("", json=registration)
        api_assert.assert_validation_error(response)


# =============================================================================
# Device Detail Tests
# =============================================================================

class TestDeviceDetailEndpoint:
    """
    GET/PUT/DELETE /api/v1/devices/{device_id}

    Device CRUD operations.
    """

    async def test_get_device_returns_full_details(self, device_api, api_assert):
        """RED: Get device should return complete device data"""
        # Create device first
        registration = make_device_registration(
            device_name="Detail Test Device"
        )
        create_response = await device_api.post("", json=registration)
        device_id = create_response.json()["device_id"]

        # Get device
        response = await device_api.get(f"/{device_id}")

        api_assert.assert_success(response)
        data = response.json()

        # Contract: Device detail response fields
        api_assert.assert_has_fields(data, [
            "device_id", "device_name", "device_type", "status",
            "manufacturer", "model", "serial_number", "firmware_version",
            "mac_address", "connectivity_type", "security_level",
            "registered_at", "updated_at", "user_id"
        ])

        assert data["device_id"] == device_id
        assert data["device_name"] == "Detail Test Device"

    async def test_get_device_not_found(self, device_api, api_assert):
        """RED: Non-existent device should return 404"""
        response = await device_api.get("/dev_nonexistent_12345")
        api_assert.assert_not_found(response)

    async def test_update_device_name(self, device_api, api_assert):
        """RED: Should update device name"""
        # Create device
        registration = make_device_registration(
            device_name="Original Name"
        )
        create_response = await device_api.post("", json=registration)
        device_id = create_response.json()["device_id"]

        # Update name
        response = await device_api.put(f"/{device_id}", json={
            "device_name": "Updated Name"
        })

        api_assert.assert_success(response)
        data = response.json()

        assert data["device_name"] == "Updated Name"

    async def test_update_device_status(self, device_api, api_assert):
        """RED: Should update device status"""
        # Create device
        registration = make_device_registration()
        create_response = await device_api.post("", json=registration)
        device_id = create_response.json()["device_id"]

        # Update status to active
        response = await device_api.put(f"/{device_id}", json={
            "status": "active"
        })

        api_assert.assert_success(response)
        data = response.json()

        assert data["status"] == "active"

    async def test_update_device_firmware_version(self, device_api, api_assert):
        """RED: Should update firmware version"""
        # Create device
        registration = make_device_registration(
            firmware_version="1.0.0"
        )
        create_response = await device_api.post("", json=registration)
        device_id = create_response.json()["device_id"]

        # Update firmware
        response = await device_api.put(f"/{device_id}", json={
            "firmware_version": "2.0.0"
        })

        api_assert.assert_success(response)
        data = response.json()

        assert data["firmware_version"] == "2.0.0"

    async def test_update_device_not_found(self, device_api, api_assert):
        """RED: Updating non-existent device should return 404"""
        response = await device_api.put("/dev_nonexistent_12345", json={
            "device_name": "New Name"
        })
        api_assert.assert_not_found(response)

    async def test_delete_device_success(self, device_api, api_assert):
        """RED: Delete should decommission the device"""
        # Create device
        registration = make_device_registration(
            device_name="To Be Deleted"
        )
        create_response = await device_api.post("", json=registration)
        device_id = create_response.json()["device_id"]

        # Delete device
        response = await device_api.delete(f"/{device_id}")
        api_assert.assert_success(response)

        # Verify deleted (should return 404 or decommissioned status)
        get_response = await device_api.get(f"/{device_id}")
        if get_response.status_code == 200:
            assert get_response.json()["status"] == "decommissioned"
        else:
            assert get_response.status_code == 404


# =============================================================================
# Device List Tests
# =============================================================================

class TestDeviceListEndpoint:
    """
    GET /api/v1/devices

    List devices with filtering and pagination.
    """

    async def test_list_devices_returns_paginated_response(self, device_api, api_assert):
        """RED: List should return paginated device list"""
        response = await device_api.get("")

        api_assert.assert_success(response)
        data = response.json()

        # Contract: Paginated response structure
        api_assert.assert_has_fields(data, [
            "devices", "count", "limit", "offset"
        ])

        assert isinstance(data["devices"], list)
        assert isinstance(data["count"], int)
        assert data["count"] >= 0

    async def test_list_devices_pagination(self, device_api, api_assert):
        """RED: Pagination parameters should work correctly"""
        response = await device_api.get("", params={
            "limit": 10,
            "offset": 0
        })

        api_assert.assert_success(response)
        data = response.json()

        assert data["limit"] == 10
        assert data["offset"] == 0
        assert len(data["devices"]) <= 10

    async def test_list_devices_filter_by_type(self, device_api, api_assert):
        """RED: Should filter devices by type"""
        # Create a sensor device
        sensor_reg = make_device_registration(device_type="sensor")
        await device_api.post("", json=sensor_reg)

        # Filter by sensor type
        response = await device_api.get("", params={
            "device_type": "sensor"
        })

        api_assert.assert_success(response)
        data = response.json()

        # All returned devices should be sensors
        for device in data["devices"]:
            assert device["device_type"] == "sensor"

    async def test_list_devices_filter_by_status(self, device_api, api_assert):
        """RED: Should filter devices by status"""
        response = await device_api.get("", params={
            "status": "active"
        })

        api_assert.assert_success(response)
        data = response.json()

        # All returned devices should be active
        for device in data["devices"]:
            assert device["status"] == "active"

    async def test_list_devices_filter_by_connectivity(self, device_api, api_assert):
        """RED: Should filter devices by connectivity type"""
        response = await device_api.get("", params={
            "connectivity": "wifi"
        })

        api_assert.assert_success(response)


# =============================================================================
# Device Commands Tests
# =============================================================================

class TestDeviceCommandsEndpoint:
    """
    POST /api/v1/devices/{device_id}/commands

    Send commands to devices.
    """

    async def test_send_command_to_active_device(self, device_api, api_assert):
        """RED: Should send command to active device"""
        # Create and activate device
        registration = make_device_registration()
        create_response = await device_api.post("", json=registration)
        device_id = create_response.json()["device_id"]

        # Activate device
        await device_api.put(f"/{device_id}", json={"status": "active"})

        # Send command
        command = {
            "command": "reboot",
            "parameters": {"force": False},
            "timeout": 30,
            "priority": 5
        }

        response = await device_api.post(f"/{device_id}/commands", json=command)

        api_assert.assert_success(response)
        data = response.json()

        # Should have command_id or success indicator
        assert "command_id" in data or "success" in data

    async def test_send_command_validates_required_fields(self, device_api, api_assert):
        """RED: Missing command name should return 422"""
        # Create device
        registration = make_device_registration()
        create_response = await device_api.post("", json=registration)
        device_id = create_response.json()["device_id"]

        # Missing command field
        response = await device_api.post(f"/{device_id}/commands", json={
            "parameters": {}
        })

        api_assert.assert_validation_error(response)

    async def test_send_command_to_nonexistent_device(self, device_api, api_assert):
        """RED: Command to non-existent device should return 404"""
        command = {
            "command": "reboot",
            "parameters": {},
            "timeout": 30
        }

        response = await device_api.post("/dev_nonexistent_12345/commands", json=command)
        # Could be 404 or 500 depending on implementation
        assert response.status_code in [404, 500]


# =============================================================================
# Device Groups Tests
# =============================================================================

class TestDeviceGroupsEndpoint:
    """
    POST /api/v1/groups
    GET /api/v1/groups/{group_id}

    Device group management.
    """

    async def test_create_device_group(self, device_api, http_client, api_assert):
        """RED: Should create a new device group"""
        from tests.api.conftest import APITestConfig

        base_url = APITestConfig.get_base_url("device")
        group_data = {
            "group_name": f"Test Group {uuid.uuid4().hex[:8]}",
            "description": "API test device group",
            "tags": ["test"],
            "metadata": {}
        }

        response = await http_client.post(
            f"{base_url}/api/v1/groups",
            json=group_data,
            headers={"X-Internal-Call": "true"}
        )

        api_assert.assert_created(response)
        data = response.json()

        # Contract: Group response fields
        api_assert.assert_has_fields(data, [
            "group_id", "group_name", "description", "user_id",
            "device_count", "created_at"
        ])

        assert data["group_name"] == group_data["group_name"]
        assert data["device_count"] == 0

    async def test_create_group_validates_required_fields(self, device_api, http_client, api_assert):
        """RED: Missing group_name should return 422"""
        from tests.api.conftest import APITestConfig

        base_url = APITestConfig.get_base_url("device")

        # Missing group_name
        response = await http_client.post(
            f"{base_url}/api/v1/groups",
            json={"description": "No name"},
            headers={"X-Internal-Call": "true"}
        )

        api_assert.assert_validation_error(response)


# =============================================================================
# Device Stats Tests
# =============================================================================

class TestDeviceStatsEndpoint:
    """
    GET /api/v1/devices/stats

    Get device statistics.
    """

    async def test_get_device_stats_returns_counts(self, device_api, api_assert):
        """RED: Stats should return device counts and metrics"""
        response = await device_api.get("/stats")

        api_assert.assert_success(response)
        data = response.json()

        # Contract: Stats response fields
        api_assert.assert_has_fields(data, [
            "total_devices",
            "active_devices",
            "inactive_devices"
        ])

        assert isinstance(data["total_devices"], int)
        assert isinstance(data["active_devices"], int)
        assert data["total_devices"] >= 0


# =============================================================================
# Device Health Tests
# =============================================================================

class TestDeviceHealthEndpoints:
    """
    GET /health
    GET /health/detailed

    Service health check endpoints.
    """

    async def test_health_check(self, http_client, api_assert):
        """RED: Health check should return service status"""
        from tests.api.conftest import APITestConfig

        base_url = APITestConfig.get_base_url("device")
        response = await http_client.get(f"{base_url}/health")

        api_assert.assert_success(response)
        data = response.json()

        assert "status" in data
        assert data["status"] == "healthy"

    async def test_health_detailed(self, http_client, api_assert):
        """RED: Detailed health should include component status"""
        from tests.api.conftest import APITestConfig

        base_url = APITestConfig.get_base_url("device")
        response = await http_client.get(f"{base_url}/health/detailed")

        api_assert.assert_success(response)
        data = response.json()

        assert "status" in data
        assert "components" in data or "service" in data


# =============================================================================
# Error Contract Tests
# =============================================================================

class TestDeviceErrorContracts:
    """
    Test error response contracts for Device API.
    """

    async def test_404_response_format(self, device_api):
        """RED: 404 errors should have consistent format"""
        response = await device_api.get("/dev_nonexistent_12345")

        assert response.status_code == 404
        data = response.json()

        # Should have detail message
        assert "detail" in data or "message" in data or "error" in data

    async def test_422_response_format(self, device_api):
        """RED: 422 validation errors should have detail array"""
        response = await device_api.post("", json={
            "device_type": "sensor"
            # Missing required fields
        })

        assert response.status_code == 422
        data = response.json()

        # FastAPI returns detail with validation errors
        assert "detail" in data


# =============================================================================
# Device Authentication Tests
# =============================================================================

class TestDeviceAuthenticationEndpoint:
    """
    POST /api/v1/devices/auth

    Device authentication for MQTT/API access.
    """

    async def test_device_auth_requires_credentials(self, device_api, http_client, api_assert):
        """RED: Device auth should validate credentials"""
        from tests.api.conftest import APITestConfig

        base_url = APITestConfig.get_base_url("device")

        # Missing device_secret
        response = await http_client.post(
            f"{base_url}/api/v1/devices/auth",
            json={"device_id": "dev_test_123"}
        )

        api_assert.assert_validation_error(response)
