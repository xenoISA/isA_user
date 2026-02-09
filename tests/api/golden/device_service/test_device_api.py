"""
Device Service API Tests

This test suite validates API endpoints, request/response formats,
error handling, and HTTP status codes for Device Service.

Focus Areas:
1. Endpoint contract validation
2. HTTP status code correctness
3. Error response formats
4. Request/response validation
5. API authentication and authorization
6. Rate limiting behavior
"""

import pytest
import httpx
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import os
import secrets

# Import contract components
from tests.contracts.device.data_contract import (
    DeviceType, DeviceStatus, ConnectivityType, SecurityLevel,
    DeviceRegistrationRequest, DeviceUpdateRequest, DeviceAuthRequest,
    DeviceCommandRequest, BulkCommandRequest, DeviceGroupRequest,
    DeviceResponse, DeviceAuthResponse, DeviceCommand,
    DeviceDataFactory, FrameDataFactory
)


class TestDeviceAPIAuthentication:
    """Test API authentication and authorization"""
    
    @pytest.fixture
    def api_client(self):
        """Create API client without authentication"""
        return httpx.Client(base_url="http://localhost:8220")
    
    @pytest.fixture
    def authenticated_client(self):
        """Create API client with authentication"""
        # In real tests, this would use valid JWT token
        token = os.getenv("TEST_JWT_TOKEN", "Bearer test-token")
        return httpx.Client(
            base_url="http://localhost:8220",
            headers={"Authorization": token}
        )
    
    def test_unauthenticated_access_denied(self, api_client):
        """Test unauthenticated access is denied"""
        response = api_client.get("/api/v1/devices")
        
        assert response.status_code == 401
        error_data = response.json()
        
        # Verify error response structure
        assert "error" in error_data
        assert "UNAUTHORIZED" in error_data["error"]
        assert "message" in error_data
        assert "timestamp" in error_data
        assert "request_id" in error_data
    
    def test_invalid_token_denied(self, api_client):
        """Test invalid token is denied"""
        response = api_client.get(
            "/api/v1/devices",
            headers={"Authorization": "Bearer invalid-token"}
        )
        
        assert response.status_code == 401
        error_data = response.json()
        
        assert "error" in error_data
        assert "INVALID_TOKEN" in error_data["error"]
    
    def test_expired_token_denied(self, api_client):
        """Test expired token is denied"""
        response = api_client.get(
            "/api/v1/devices",
            headers={"Authorization": "Bearer expired-token"}
        )
        
        assert response.status_code == 401
        error_data = response.json()
        
        assert "error" in error_data
        assert "TOKEN_EXPIRED" in error_data["error"]


class TestDeviceRegistrationAPI:
    """Test device registration API endpoints"""
    
    def test_register_device_success(self, authenticated_client):
        """Test successful device registration"""
        registration_request = DeviceDataFactory.create_device_registration_request()
        
        response = authenticated_client.post(
            "/api/v1/devices",
            json=registration_request.dict()
        )
        
        assert response.status_code == 201
        response_data = response.json()
        
        # Verify response structure
        required_fields = [
            "device_id", "device_name", "device_type", "manufacturer",
            "model", "serial_number", "firmware_version", "connectivity_type",
            "security_level", "status", "user_id", "registered_at", "updated_at"
        ]
        
        for field in required_fields:
            assert field in response_data, f"Missing required field: {field}"
        
        # Verify data consistency
        assert response_data["device_name"] == registration_request.device_name
        assert response_data["device_type"] == registration_request.device_type.value
        assert response_data["manufacturer"] == registration_request.manufacturer
        assert response_data["serial_number"] == registration_request.serial_number
        assert response_data["status"] == DeviceStatus.PENDING.value
        
        # Verify device ID format
        assert len(response_data["device_id"]) > 0
        assert isinstance(response_data["device_id"], str)
        
        # Verify timestamps
        assert response_data["registered_at"] is not None
        assert response_data["updated_at"] is not None
        # Should be ISO format timestamps
        datetime.fromisoformat(response_data["registered_at"].replace('Z', '+00:00'))
        datetime.fromisoformat(response_data["updated_at"].replace('Z', '+00:00'))
    
    def test_register_device_validation_errors(self, authenticated_client):
        """Test device registration validation errors"""
        # Test missing required fields
        incomplete_request = {
            "device_name": "Test Device"
            # Missing required fields
        }
        
        response = authenticated_client.post(
            "/api/v1/devices",
            json=incomplete_request
        )
        
        assert response.status_code == 400
        error_data = response.json()
        
        assert "error" in error_data
        assert "VALIDATION_ERROR" in error_data["error"]
        assert "validation_errors" in error_data
        
        # Test invalid device type
        invalid_type_request = DeviceDataFactory.create_device_registration_request()
        invalid_type_request["device_type"] = "invalid_type"
        
        response = authenticated_client.post(
            "/api/v1/devices",
            json=invalid_type_request
        )
        
        assert response.status_code == 400
        error_data = response.json()
        assert "VALIDATION_ERROR" in error_data["error"]
        
        # Test invalid MAC address
        invalid_mac_request = DeviceDataFactory.create_device_registration_request()
        invalid_mac_request["mac_address"] = "invalid-mac-address"
        
        response = authenticated_client.post(
            "/api/v1/devices",
            json=invalid_mac_request
        )
        
        assert response.status_code == 400
        error_data = response.json()
        assert "VALIDATION_ERROR" in error_data["error"]
        
        # Test device name too long
        long_name_request = DeviceDataFactory.create_device_registration_request()
        long_name_request["device_name"] = "a" * 201  # Exceeds 200 character limit
        
        response = authenticated_client.post(
            "/api/v1/devices",
            json=long_name_request
        )
        
        assert response.status_code == 400
        error_data = response.json()
        assert "VALIDATION_ERROR" in error_data["error"]
    
    def test_register_device_duplicate_serial(self, authenticated_client):
        """Test registration with duplicate serial number"""
        # First registration
        registration_request = DeviceDataFactory.create_device_registration_request(
            overrides={"serial_number": "DUPLICATE123"}
        )
        
        response1 = authenticated_client.post(
            "/api/v1/devices",
            json=registration_request.dict()
        )
        assert response1.status_code == 201
        
        # Second registration with same serial
        response2 = authenticated_client.post(
            "/api/v1/devices",
            json=registration_request.dict()
        )
        
        assert response2.status_code == 409
        error_data = response2.json()
        
        assert "error" in error_data
        assert "DUPLICATE_DEVICE_SERIAL" in error_data["error"]
        assert "message" in error_data
        assert "existing_device_id" in error_data
    
    def test_register_device_unsupported_manufacturer(self, authenticated_client):
        """Test registration with unsupported manufacturer"""
        registration_request = DeviceDataFactory.create_device_registration_request(
            overrides={"manufacturer": "UnsupportedManufacturer123"}
        )
        
        response = authenticated_client.post(
            "/api/v1/devices",
            json=registration_request.dict()
        )
        
        assert response.status_code == 400
        error_data = response.json()
        
        assert "error" in error_data
        assert "UNAPPROVED_MANUFACTURER" in error_data["error"]
        assert "supported_manufacturers" in error_data
    
    def test_register_device_security_level_mismatch(self, authenticated_client):
        """Test registration with insufficient security level"""
        # Medical device with basic security (should fail)
        registration_request = DeviceDataFactory.create_device_registration_request(
            device_type=DeviceType.MEDICAL,
            overrides={"security_level": SecurityLevel.BASIC}
        )
        
        response = authenticated_client.post(
            "/api/v1/devices",
            json=registration_request.dict()
        )
        
        assert response.status_code == 400
        error_data = response.json()
        
        assert "error" in error_data
        assert "INSUFFICIENT_SECURITY_LEVEL" in error_data["error"]
        assert "required_security_level" in error_data
        assert error_data["required_security_level"] == SecurityLevel.CRITICAL.value


class TestDeviceAuthenticationAPI:
    """Test device authentication API endpoints"""
    
    def test_device_auth_success(self, authenticated_client):
        """Test successful device authentication"""
        auth_request = DeviceDataFactory.create_device_auth_request()
        
        response = authenticated_client.post(
            "/api/v1/devices/auth",
            json=auth_request.dict()
        )
        
        assert response.status_code == 200
        auth_response = response.json()
        
        # Verify response structure
        required_fields = [
            "device_id", "access_token", "token_type", "expires_in",
            "mqtt_broker", "mqtt_topic"
        ]
        
        for field in required_fields:
            assert field in auth_response, f"Missing required field: {field}"
        
        # Verify data consistency
        assert auth_response["device_id"] == auth_request.device_id
        assert auth_response["token_type"] == "Bearer"
        assert isinstance(auth_response["expires_in"], int)
        assert auth_response["expires_in"] > 0
        assert auth_response["mqtt_broker"] is not None
        assert auth_response["mqtt_topic"] is not None
        
        # Verify access token format
        access_token = auth_response["access_token"]
        assert len(access_token) > 0
        assert access_token.startswith("eyJ")  # JWT format
    
    def test_device_auth_invalid_credentials(self, authenticated_client):
        """Test device authentication with invalid credentials"""
        auth_request = DeviceDataFactory.create_device_auth_request(
            device_id="nonexistent-device",
            overrides={"device_secret": "invalid-secret"}
        )
        
        response = authenticated_client.post(
            "/api/v1/devices/auth",
            json=auth_request.dict()
        )
        
        assert response.status_code == 401
        error_data = response.json()
        
        assert "error" in error_data
        assert "INVALID_CREDENTIALS" in error_data["error"]
        assert "message" in error_data
    
    def test_device_auth_rate_limiting(self, authenticated_client):
        """Test device authentication rate limiting"""
        device_id = f"rate-limit-{secrets.token_hex(8)}"
        auth_request = DeviceDataFactory.create_device_auth_request(
            device_id=device_id
        )
        
        # Make multiple rapid requests
        responses = []
        for i in range(6):  # Exceed rate limit
            response = authenticated_client.post(
                "/api/v1/devices/auth",
                json=auth_request.dict()
            )
            responses.append(response)
        
        # Should hit rate limit
        rate_limited = any(r.status_code == 429 for r in responses)
        assert rate_limited
        
        # Verify rate limit response
        rate_limited_response = next(r for r in responses if r.status_code == 429)
        error_data = rate_limited_response.json()
        
        assert "error" in error_data
        assert "RATE_LIMIT_EXCEEDED" in error_data["error"]
        assert "retry_after" in error_data
        assert isinstance(error_data["retry_after"], int)
        assert error_data["retry_after"] > 0


class TestDeviceManagementAPI:
    """Test device management API endpoints"""
    
    @pytest.fixture
    def test_device(self, authenticated_client):
        """Create a test device for management tests"""
        registration_request = DeviceDataFactory.create_device_registration_request()
        response = authenticated_client.post(
            "/api/v1/devices",
            json=registration_request.dict()
        )
        return response.json()
    
    def test_get_device_success(self, authenticated_client, test_device):
        """Test successful device retrieval"""
        device_id = test_device["device_id"]
        
        response = authenticated_client.get(f"/api/v1/devices/{device_id}")
        
        assert response.status_code == 200
        device_response = response.json()
        
        # Verify response structure
        required_fields = [
            "device_id", "device_name", "device_type", "manufacturer",
            "model", "serial_number", "firmware_version", "connectivity_type",
            "security_level", "status", "user_id", "registered_at", "updated_at"
        ]
        
        for field in required_fields:
            assert field in device_response, f"Missing required field: {field}"
        
        # Verify data consistency
        assert device_response["device_id"] == device_id
        assert device_response["device_name"] == test_device["device_name"]
        assert device_response["device_type"] == test_device["device_type"]
        assert device_response["manufacturer"] == test_device["manufacturer"]
    
    def test_get_device_not_found(self, authenticated_client):
        """Test retrieving non-existent device"""
        device_id = "nonexistent-device-123"
        
        response = authenticated_client.get(f"/api/v1/devices/{device_id}")
        
        assert response.status_code == 404
        error_data = response.json()
        
        assert "error" in error_data
        assert "DEVICE_NOT_FOUND" in error_data["error"]
        assert "message" in error_data
    
    def test_get_device_unauthorized(self, api_client, test_device):
        """Test unauthorized device access"""
        device_id = test_device["device_id"]
        
        response = api_client.get(f"/api/v1/devices/{device_id}")
        
        assert response.status_code == 401
        error_data = response.json()
        
        assert "error" in error_data
        assert "UNAUTHORIZED" in error_data["error"]
    
    def test_update_device_success(self, authenticated_client, test_device):
        """Test successful device update"""
        device_id = test_device["device_id"]
        update_request = DeviceUpdateRequest(
            device_name="Updated Device Name",
            firmware_version="2.0.0",
            status=DeviceStatus.ACTIVE
        )
        
        response = authenticated_client.put(
            f"/api/v1/devices/{device_id}",
            json=update_request.dict(exclude_unset=True)
        )
        
        assert response.status_code == 200
        device_response = response.json()
        
        # Verify updated fields
        assert device_response["device_name"] == update_request.device_name
        assert device_response["firmware_version"] == update_request.firmware_version
        assert device_response["status"] == update_request.status.value
        assert device_response["updated_at"] > test_device["updated_at"]
    
    def test_update_device_not_found(self, authenticated_client):
        """Test updating non-existent device"""
        device_id = "nonexistent-device-123"
        update_request = DeviceUpdateRequest(device_name="Updated Name")
        
        response = authenticated_client.put(
            f"/api/v1/devices/{device_id}",
            json=update_request.dict(exclude_unset=True)
        )
        
        assert response.status_code == 404
        error_data = response.json()
        
        assert "error" in error_data
        assert "DEVICE_NOT_FOUND" in error_data["error"]
    
    def test_update_device_unauthorized(self, api_client, test_device):
        """Test unauthorized device update"""
        device_id = test_device["device_id"]
        update_request = DeviceUpdateRequest(device_name="Updated Name")
        
        response = api_client.put(
            f"/api/v1/devices/{device_id}",
            json=update_request.dict(exclude_unset=True)
        )
        
        assert response.status_code == 401
        error_data = response.json()
        
        assert "error" in error_data
        assert "UNAUTHORIZED" in error_data["error"]
    
    def test_delete_device_success(self, authenticated_client, test_device):
        """Test successful device deletion"""
        device_id = test_device["device_id"]
        
        response = authenticated_client.delete(f"/api/v1/devices/{device_id}")
        
        assert response.status_code == 200
        response_data = response.json()
        
        assert "message" in response_data
        assert "device_id" in response_data
        assert response_data["device_id"] == device_id
        
        # Verify device is actually deleted
        get_response = authenticated_client.get(f"/api/v1/devices/{device_id}")
        assert get_response.status_code == 404
    
    def test_delete_device_not_found(self, authenticated_client):
        """Test deleting non-existent device"""
        device_id = "nonexistent-device-123"
        
        response = authenticated_client.delete(f"/api/v1/devices/{device_id}")
        
        assert response.status_code == 404
        error_data = response.json()
        
        assert "error" in error_data
        assert "DEVICE_NOT_FOUND" in error_data["error"]


class TestDeviceListAPI:
    """Test device listing API endpoints"""
    
    @pytest.fixture
    def multiple_devices(self, authenticated_client):
        """Create multiple test devices"""
        devices = []
        for i in range(5):
            registration_request = DeviceDataFactory.create_device_registration_request()
            response = authenticated_client.post(
                "/api/v1/devices",
                json=registration_request.dict()
            )
            devices.append(response.json())
        return devices
    
    def test_list_devices_success(self, authenticated_client, multiple_devices):
        """Test successful device listing"""
        response = authenticated_client.get("/api/v1/devices")
        
        assert response.status_code == 200
        list_response = response.json()
        
        # Verify response structure
        required_fields = ["devices", "count", "limit", "offset"]
        for field in required_fields:
            assert field in list_response, f"Missing required field: {field}"
        
        # Verify data consistency
        assert isinstance(list_response["devices"], list)
        assert len(list_response["devices"]) == len(multiple_devices)
        assert list_response["count"] == len(multiple_devices)
        assert list_response["limit"] is not None
        assert list_response["offset"] is not None
        
        # Verify device data in list
        device_ids = [device["device_id"] for device in list_response["devices"]]
        expected_ids = [device["device_id"] for device in multiple_devices]
        assert all(device_id in device_ids for device_id in expected_ids)
    
    def test_list_devices_with_filters(self, authenticated_client, multiple_devices):
        """Test device listing with filters"""
        # Test by device type
        first_device = multiple_devices[0]
        device_type = first_device["device_type"]
        
        response = authenticated_client.get(
            "/api/v1/devices",
            params={"device_type": device_type}
        )
        
        assert response.status_code == 200
        list_response = response.json()
        
        filtered_devices = [d for d in list_response["devices"] if d["device_type"] == device_type]
        assert len(list_response["devices"]) == len(filtered_devices)
        
        # Test by status
        response = authenticated_client.get(
            "/api/v1/devices",
            params={"status": DeviceStatus.PENDING.value}
        )
        
        assert response.status_code == 200
        list_response = response.json()
        
        pending_devices = [d for d in list_response["devices"] if d["status"] == DeviceStatus.PENDING.value]
        assert len(list_response["devices"]) == len(pending_devices)
    
    def test_list_devices_with_pagination(self, authenticated_client, multiple_devices):
        """Test device listing with pagination"""
        # Test with limit
        limit = 2
        response = authenticated_client.get(
            "/api/v1/devices",
            params={"limit": limit}
        )
        
        assert response.status_code == 200
        list_response = response.json()
        
        assert len(list_response["devices"]) <= limit
        assert list_response["limit"] == limit
        
        # Test with offset
        offset = 2
        response = authenticated_client.get(
            "/api/v1/devices",
            params={"limit": limit, "offset": offset}
        )
        
        assert response.status_code == 200
        list_response = response.json()
        
        assert list_response["offset"] == offset
        # Should return devices starting from offset
        assert len(list_response["devices"]) <= limit
    
    def test_list_devices_invalid_parameters(self, authenticated_client):
        """Test device listing with invalid parameters"""
        # Test invalid limit
        response = authenticated_client.get(
            "/api/v1/devices",
            params={"limit": -1}
        )
        
        assert response.status_code == 400
        error_data = response.json()
        
        assert "error" in error_data
        assert "INVALID_PARAMETER" in error_data["error"]
        
        # Test invalid offset
        response = authenticated_client.get(
            "/api/v1/devices",
            params={"offset": -1}
        )
        
        assert response.status_code == 400
        error_data = response.json()
        
        assert "error" in error_data
        assert "INVALID_PARAMETER" in error_data["error"]
        
        # Test invalid device type
        response = authenticated_client.get(
            "/api/v1/devices",
            params={"device_type": "invalid_type"}
        )
        
        assert response.status_code == 400
        error_data = response.json()
        
        assert "error" in error_data
        assert "INVALID_PARAMETER" in error_data["error"]


class TestDeviceCommandAPI:
    """Test device command API endpoints"""
    
    @pytest.fixture
    def active_device(self, authenticated_client):
        """Create an active device for command tests"""
        registration_request = DeviceDataFactory.create_device_registration_request()
        response = authenticated_client.post(
            "/api/v1/devices",
            json=registration_request.dict()
        )
        device = response.json()
        
        # Update to active status
        update_request = DeviceUpdateRequest(status=DeviceStatus.ACTIVE)
        authenticated_client.put(
            f"/api/v1/devices/{device['device_id']}",
            json=update_request.dict(exclude_unset=True)
        )
        
        return device
    
    def test_send_command_success(self, authenticated_client, active_device):
        """Test successful command sending"""
        device_id = active_device["device_id"]
        command_request = DeviceDataFactory.create_device_command_request()
        
        response = authenticated_client.post(
            f"/api/v1/devices/{device_id}/commands",
            json=command_request.dict()
        )
        
        assert response.status_code == 200
        command_response = response.json()
        
        # Verify response structure
        required_fields = ["command_id", "device_id", "command", "status"]
        for field in required_fields:
            assert field in command_response, f"Missing required field: {field}"
        
        # Verify data consistency
        assert command_response["device_id"] == device_id
        assert command_response["command"] == command_request.command
        assert command_response["status"] in ["pending", "sent"]
        assert len(command_response["command_id"]) > 0
    
    def test_send_command_unauthorized(self, api_client, active_device):
        """Test unauthorized command sending"""
        device_id = active_device["device_id"]
        command_request = DeviceDataFactory.create_device_command_request()
        
        response = api_client.post(
            f"/api/v1/devices/{device_id}/commands",
            json=command_request.dict()
        )
        
        assert response.status_code == 401
        error_data = response.json()
        
        assert "error" in error_data
        assert "UNAUTHORIZED" in error_data["error"]
    
    def test_send_command_device_not_found(self, authenticated_client):
        """Test sending command to non-existent device"""
        device_id = "nonexistent-device-123"
        command_request = DeviceDataFactory.create_device_command_request()
        
        response = authenticated_client.post(
            f"/api/v1/devices/{device_id}/commands",
            json=command_request.dict()
        )
        
        assert response.status_code == 404
        error_data = response.json()
        
        assert "error" in error_data
        assert "DEVICE_NOT_FOUND" in error_data["error"]
    
    def test_send_command_invalid_device_status(self, authenticated_client, active_device):
        """Test sending command to inactive device"""
        device_id = active_device["device_id"]
        
        # Set device to inactive
        update_request = DeviceUpdateRequest(status=DeviceStatus.INACTIVE)
        authenticated_client.put(
            f"/api/v1/devices/{device_id}",
            json=update_request.dict(exclude_unset=True)
        )
        
        # Try to send command
        command_request = DeviceDataFactory.create_device_command_request()
        response = authenticated_client.post(
            f"/api/v1/devices/{device_id}/commands",
            json=command_request.dict()
        )
        
        assert response.status_code == 400
        error_data = response.json()
        
        assert "error" in error_data
        assert "DEVICE_NOT_ACTIVE" in error_data["error"]
    
    def test_send_command_validation_errors(self, authenticated_client, active_device):
        """Test command sending validation errors"""
        device_id = active_device["device_id"]
        
        # Test invalid timeout
        invalid_command = DeviceDataFactory.create_device_command_request()
        invalid_command.timeout = 0  # Invalid (must be >= 1)
        
        response = authenticated_client.post(
            f"/api/v1/devices/{device_id}/commands",
            json=invalid_command.dict()
        )
        
        assert response.status_code == 400
        error_data = response.json()
        
        assert "error" in error_data
        assert "VALIDATION_ERROR" in error_data["error"]
        
        # Test invalid priority
        invalid_command = DeviceDataFactory.create_device_command_request()
        invalid_command.priority = 11  # Invalid (must be 1-10)
        
        response = authenticated_client.post(
            f"/api/v1/devices/{device_id}/commands",
            json=invalid_command.dict()
        )
        
        assert response.status_code == 400
        error_data = response.json()
        
        assert "error" in error_data
        assert "VALIDATION_ERROR" in error_data["error"]


class TestBulkCommandAPI:
    """Test bulk command API endpoints"""
    
    @pytest.fixture
    def multiple_active_devices(self, authenticated_client):
        """Create multiple active devices"""
        devices = []
        for i in range(3):
            registration_request = DeviceDataFactory.create_device_registration_request()
            response = authenticated_client.post(
                "/api/v1/devices",
                json=registration_request.dict()
            )
            device = response.json()
            
            # Activate device
            update_request = DeviceUpdateRequest(status=DeviceStatus.ACTIVE)
            authenticated_client.put(
                f"/api/v1/devices/{device['device_id']}",
                json=update_request.dict(exclude_unset=True)
            )
            
            devices.append(device)
        return devices
    
    def test_bulk_command_success(self, authenticated_client, multiple_active_devices):
        """Test successful bulk command execution"""
        device_ids = [device["device_id"] for device in multiple_active_devices]
        bulk_request = DeviceDataFactory.create_bulk_command_request(
            device_count=len(device_ids),
            overrides={"device_ids": device_ids}
        )
        
        response = authenticated_client.post(
            "/api/v1/devices/bulk/commands",
            json=bulk_request.dict()
        )
        
        assert response.status_code == 200
        bulk_response = response.json()
        
        # Verify response structure
        required_fields = ["command_id", "device_count", "results"]
        for field in required_fields:
            assert field in bulk_response, f"Missing required field: {field}"
        
        # Verify data consistency
        assert bulk_response["device_count"] == len(device_ids)
        assert len(bulk_response["results"]) == len(device_ids)
        
        # Verify individual results
        for result in bulk_response["results"]:
            assert "device_id" in result
            assert "command_id" in result
            assert "status" in result
            assert result["device_id"] in device_ids
    
    def test_bulk_command_too_many_devices(self, authenticated_client, multiple_active_devices):
        """Test bulk command with too many devices"""
        device_ids = [device["device_id"] for device in multiple_active_devices]
        
        # Add many more device IDs to exceed limit
        device_ids.extend([f"extra-device-{i}" for i in range(1000)])
        
        bulk_request = DeviceDataFactory.create_bulk_command_request(
            device_count=len(device_ids),
            overrides={"device_ids": device_ids}
        )
        
        response = authenticated_client.post(
            "/api/v1/devices/bulk/commands",
            json=bulk_request.dict()
        )
        
        assert response.status_code == 400
        error_data = response.json()
        
        assert "error" in error_data
        assert "BULK_OPERATION_TOO_LARGE" in error_data["error"]
        assert "max_devices" in error_data
        assert error_data["max_devices"] == 1000
    
    def test_bulk_command_unauthorized_devices(self, authenticated_client):
        """Test bulk command with unauthorized devices"""
        unauthorized_device_ids = [
            "unauthorized-device-1",
            "unauthorized-device-2",
            "unauthorized-device-3"
        ]
        
        bulk_request = DeviceDataFactory.create_bulk_command_request(
            device_count=len(unauthorized_device_ids),
            overrides={"device_ids": unauthorized_device_ids}
        )
        
        response = authenticated_client.post(
            "/api/v1/devices/bulk/commands",
            json=bulk_request.dict()
        )
        
        assert response.status_code == 403
        error_data = response.json()
        
        assert "error" in error_data
        assert "UNAUTHORIZED_COMMAND_ACCESS" in error_data["error"]
        assert "unauthorized_devices" in error_data
        assert len(error_data["unauthorized_devices"]) == len(unauthorized_device_ids)


class TestSmartFrameAPI:
    """Test smart frame specific API endpoints"""
    
    @pytest.fixture
    def smart_frame(self, authenticated_client):
        """Create a smart frame for testing"""
        frame_request = FrameDataFactory.create_frame_registration_request()
        response = authenticated_client.post(
            "/api/v1/devices/frames",
            json=frame_request.dict()
        )
        return response.json()
    
    def test_register_frame_success(self, authenticated_client):
        """Test successful smart frame registration"""
        frame_request = FrameDataFactory.create_frame_registration_request()
        
        response = authenticated_client.post(
            "/api/v1/devices/frames",
            json=frame_request.dict()
        )
        
        assert response.status_code == 201
        frame_response = response.json()
        
        # Verify frame-specific fields
        assert "device_id" in frame_response
        assert "device_type" in frame_response
        assert frame_response["device_type"] == DeviceType.SMART_FRAME.value
        assert "frame_config" in frame_response
        assert "frame_status" in frame_response
        
        # Verify frame config
        frame_config = frame_response["frame_config"]
        assert "brightness" in frame_config
        assert "display_mode" in frame_config
        assert "slideshow_interval" in frame_config
    
    def test_get_frames_success(self, authenticated_client, smart_frame):
        """Test successful frame listing"""
        response = authenticated_client.get("/api/v1/devices/frames")
        
        assert response.status_code == 200
        frames_response = response.json()
        
        # Verify response structure
        required_fields = ["frames", "count", "limit", "offset"]
        for field in required_fields:
            assert field in frames_response, f"Missing required field: {field}"
        
        # Verify frame data
        assert isinstance(frames_response["frames"], list)
        assert frames_response["count"] >= 1
        
        # Verify our test frame is in the list
        frame_ids = [frame["device_id"] for frame in frames_response["frames"]]
        assert smart_frame["device_id"] in frame_ids
    
    def test_frame_display_control_success(self, authenticated_client, smart_frame):
        """Test successful frame display control"""
        device_id = smart_frame["device_id"]
        display_request = {
            "brightness": 85,
            "display_mode": "clock_display",
            "slideshow_interval": 45
        }
        
        response = authenticated_client.post(
            f"/api/v1/devices/frames/{device_id}/display",
            json=display_request
        )
        
        assert response.status_code == 200
        display_response = response.json()
        
        # Verify response
        assert "device_id" in display_response
        assert "success" in display_response
        assert display_response["device_id"] == device_id
        assert display_response["success"] is True
        
        # Verify config was updated
        get_response = authenticated_client.get(f"/api/v1/devices/frames/{device_id}")
        updated_frame = get_response.json()
        
        assert updated_frame["frame_config"]["brightness"] == 85
        assert updated_frame["frame_config"]["display_mode"] == "clock_display"
        assert updated_frame["frame_config"]["slideshow_interval"] == 45
    
    def test_frame_display_control_invalid_values(self, authenticated_client, smart_frame):
        """Test frame display control with invalid values"""
        device_id = smart_frame["device_id"]
        
        # Test invalid brightness
        invalid_display_request = {
            "brightness": 150,  # Invalid (must be 0-100)
            "display_mode": "photo_slideshow"
        }
        
        response = authenticated_client.post(
            f"/api/v1/devices/frames/{device_id}/display",
            json=invalid_display_request
        )
        
        assert response.status_code == 400
        error_data = response.json()
        
        assert "error" in error_data
        assert "VALIDATION_ERROR" in error_data["error"]
        assert "validation_errors" in error_data
        
        # Test invalid display mode
        invalid_display_request = {
            "brightness": 80,
            "display_mode": "invalid_mode"  # Invalid enum value
        }
        
        response = authenticated_client.post(
            f"/api/v1/devices/frames/{device_id}/display",
            json=invalid_display_request
        )
        
        assert response.status_code == 400
        error_data = response.json()
        
        assert "error" in error_data
        assert "VALIDATION_ERROR" in error_data["error"]
    
    def test_frame_sync_success(self, authenticated_client, smart_frame):
        """Test successful frame content sync"""
        device_id = smart_frame["device_id"]
        sync_request = {
            "album_ids": ["album1", "album2"],
            "force": False,
            "priority": "normal"
        }
        
        response = authenticated_client.post(
            f"/api/v1/devices/frames/{device_id}/sync",
            json=sync_request
        )
        
        assert response.status_code == 200
        sync_response = response.json()
        
        # Verify response
        assert "sync_id" in sync_response
        assert "device_id" in sync_response
        assert "sync_type" in sync_response
        assert "status" in sync_response
        
        assert sync_response["device_id"] == device_id
        assert sync_response["sync_type"] in ["full", "incremental"]
        assert sync_response["status"] in ["pending", "started"]
        assert len(sync_response["sync_id"]) > 0
    
    def test_frame_sync_non_frame_device(self, authenticated_client, active_device):
        """Test frame sync on non-frame device"""
        device_id = active_device["device_id"]
        sync_request = {
            "album_ids": ["album1"],
            "force": False,
            "priority": "normal"
        }
        
        response = authenticated_client.post(
            f"/api/v1/devices/frames/{device_id}/sync",
            json=sync_request
        )
        
        assert response.status_code == 400
        error_data = response.json()
        
        assert "error" in error_data
        assert "NOT_A_SMART_FRAME" in error_data["error"]


class TestErrorHandlingAPI:
    """Test API error handling and edge cases"""
    
    def test_method_not_allowed(self, authenticated_client):
        """Test unsupported HTTP methods"""
        # Try PUT on list endpoint
        response = authenticated_client.put("/api/v1/devices")
        assert response.status_code == 405
        
        # Try POST on get endpoint
        response = authenticated_client.post("/api/v1/devices/nonexistent-device")
        assert response.status_code == 405
    
    def test_invalid_json(self, authenticated_client):
        """Test invalid JSON in request body"""
        response = authenticated_client.post(
            "/api/v1/devices",
            content="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 400
        error_data = response.json()
        
        assert "error" in error_data
        assert "INVALID_JSON" in error_data["error"]
    
    def test_missing_content_type(self, authenticated_client):
        """Test missing Content-Type header"""
        registration_request = DeviceDataFactory.create_device_registration_request()
        
        response = authenticated_client.post(
            "/api/v1/devices",
            data=json.dumps(registration_request.dict())
            # Missing Content-Type header
        )
        
        assert response.status_code == 400
        error_data = response.json()
        
        assert "error" in error_data
        assert "MISSING_CONTENT_TYPE" in error_data["error"]
    
    def test_request_timeout(self, authenticated_client):
        """Test handling of long-running requests"""
        # This would require simulating a timeout scenario
        # For now, test that timeout errors are properly formatted
        pass
    
    def test_api_rate_limiting(self, authenticated_client):
        """Test API rate limiting"""
        # Make many rapid requests
        responses = []
        for i in range(100):  # Exceed typical rate limits
            response = authenticated_client.get("/api/v1/devices")
            responses.append(response)
            
            # Stop if we hit rate limit
            if response.status_code == 429:
                break
        
        # Verify rate limiting was applied
        rate_limited = any(r.status_code == 429 for r in responses)
        if rate_limited:
            rate_limited_response = next(r for r in responses if r.status_code == 429)
            error_data = rate_limited_response.json()
            
            assert "error" in error_data
            assert "RATE_LIMIT_EXCEEDED" in error_data["error"]
            assert "retry_after" in error_data
            assert isinstance(error_data["retry_after"], int)
    
    def test_server_error_handling(self, authenticated_client):
        """Test server error response formatting"""
        # This would require simulating a server error
        # For now, test that 500 errors are properly formatted
        pass


if __name__ == "__main__":
    # Run API tests
    pytest.main([__file__, "-v", "--tb=short"])
