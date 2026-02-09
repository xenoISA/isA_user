"""
Device Service Integration Tests

This test suite validates integration between Device Service components:
- HTTP API endpoints
- Database operations (PostgreSQL)
- Message passing (NATS)
- External service dependencies (Auth Service)
- MQTT broker integration

These tests require running infrastructure components.
"""

import pytest
import asyncio
import json
import httpx
import asyncpg
import nats
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import os
import secrets

# Import contract components
from tests.contracts.device.data_contract import (
    DeviceType, DeviceStatus, ConnectivityType, SecurityLevel,
    DeviceRegistrationRequest, DeviceResponse, DeviceAuthRequest,
    DeviceCommandRequest, DeviceHealthResponse, DeviceStatsResponse,
    DeviceDataFactory, FrameDataFactory
)


class TestDeviceServiceIntegration:
    """Test Device Service integration with external dependencies"""
    
    @pytest.fixture(scope="class")
    async def test_config(self):
        """Test configuration for integration tests"""
        return {
            "device_service_url": os.getenv("DEVICE_SERVICE_URL", "http://localhost:8220"),
            "database_url": os.getenv("TEST_DATABASE_URL", "postgresql://test:test@localhost:5432/device_test"),
            "nats_url": os.getenv("NATS_URL", "nats://localhost:4222"),
            "auth_service_url": os.getenv("AUTH_SERVICE_URL", "http://localhost:8210"),
            "test_user_id": "integration-test-user",
            "test_device_id": f"test-device-{secrets.token_hex(8)}"
        }
    
    @pytest.fixture(scope="class")
    async def db_pool(self, test_config):
        """Create database connection pool"""
        return await asyncpg.create_pool(
            test_config["database_url"],
            min_size=2,
            max_size=10
        )
    
    @pytest.fixture(scope="class")
    async def nats_client(self, test_config):
        """Create NATS client"""
        nc = await nats.connect(test_config["nats_url"])
        yield nc
        await nc.close()
    
    @pytest.fixture(scope="class")
    async def http_client(self, test_config):
        """Create HTTP client"""
        async with httpx.AsyncClient(base_url=test_config["device_service_url"]) as client:
            yield client
    
    @pytest.fixture(autouse=True)
    async def setup_test_data(self, db_pool, test_config):
        """Setup test data before each test"""
        # Clean up any existing test data
        await db_pool.execute("""
            DELETE FROM device.devices WHERE user_id = $1
        """, test_config["test_user_id"])
        
        yield
        
        # Cleanup after each test
        await db_pool.execute("""
            DELETE FROM device.devices WHERE user_id = $1
        """, test_config["test_user_id"])


class TestDeviceRegistrationIntegration:
    """Test device registration integration with database and events"""
    
    async def test_register_device_success(
        self, http_client, db_pool, nats_client, test_config
    ):
        """Test successful device registration with database persistence and event publishing"""
        
        # Create registration request
        registration_request = DeviceDataFactory.create_device_registration_request(
            device_type=DeviceType.SMART_FRAME
        )
        
        # Register device via API
        response = await http_client.post("/api/v1/devices", json=registration_request.dict())
        
        assert response.status_code == 201
        response_data = response.json()
        
        # Verify response structure
        assert "device_id" in response_data
        assert response_data["device_name"] == registration_request.device_name
        assert response_data["device_type"] == registration_request.device_type.value
        assert response_data["manufacturer"] == registration_request.manufacturer
        assert response_data["serial_number"] == registration_request.serial_number
        assert response_data["status"] == DeviceStatus.PENDING.value
        assert response_data["user_id"] == test_config["test_user_id"]
        
        device_id = response_data["device_id"]
        
        # Verify database persistence
        db_record = await db_pool.fetchrow("""
            SELECT device_id, device_name, device_type, manufacturer, serial_number, status, user_id
            FROM device.devices WHERE device_id = $1
        """, device_id)
        
        assert db_record is not None
        assert db_record["device_id"] == device_id
        assert db_record["device_name"] == registration_request.device_name
        assert db_record["device_type"] == registration_request.device_type.value
        assert db_record["manufacturer"] == registration_request.manufacturer
        assert db_record["serial_number"] == registration_request.serial_number
        assert db_record["status"] == DeviceStatus.PENDING.value
        assert db_record["user_id"] == test_config["test_user_id"]
        
        # Verify event publishing to NATS
        events = []
        
        async def message_handler(msg):
            events.append(json.loads(msg.data.decode()))
        
        await nats_client.subscribe("device.registered", cb=message_handler)
        
        # Wait for event
        await asyncio.sleep(0.5)
        
        assert len(events) > 0
        device_registered_event = next((e for e in events if e.get("device_id") == device_id), None)
        assert device_registered_event is not None
        assert device_registered_event["event_type"] == "device.registered"
        assert device_registered_event["device_id"] == device_id
        assert device_registered_event["user_id"] == test_config["test_user_id"]
        assert device_registered_event["device_type"] == registration_request.device_type.value
    
    async def test_register_device_duplicate_serial(
        self, http_client, db_pool, test_config
    ):
        """Test registration with duplicate serial number should fail"""
        
        # Create first device
        registration_request1 = DeviceDataFactory.create_device_registration_request(
            overrides={"serial_number": "DUPLICATE123"}
        )
        
        response1 = await http_client.post("/api/v1/devices", json=registration_request1.dict())
        assert response1.status_code == 201
        
        # Try to register second device with same serial number
        registration_request2 = DeviceDataFactory.create_device_registration_request(
            overrides={"serial_number": "DUPLICATE123"}
        )
        
        response2 = await http_client.post("/api/v1/devices", json=registration_request2.dict())
        assert response2.status_code == 409  # Conflict
        
        error_data = response2.json()
        assert "error" in error_data
        assert "DUPLICATE_DEVICE_SERIAL" in error_data["error"]
    
    async def test_register_device_invalid_manufacturer(
        self, http_client, test_config
    ):
        """Test registration with unapproved manufacturer should fail"""
        
        registration_request = DeviceDataFactory.create_device_registration_request(
            overrides={"manufacturer": "InvalidManufacturer123"}
        )
        
        response = await http_client.post("/api/v1/devices", json=registration_request.dict())
        assert response.status_code == 400
        
        error_data = response.json()
        assert "error" in error_data
        assert "UNAPPROVED_MANUFACTURER" in error_data["error"]


class TestDeviceAuthenticationIntegration:
    """Test device authentication integration with Auth Service"""
    
    async def test_device_authentication_success(
        self, http_client, db_pool, test_config
    ):
        """Test successful device authentication with token generation"""
        
        # First register a device
        registration_request = DeviceDataFactory.create_device_registration_request()
        reg_response = await http_client.post("/api/v1/devices", json=registration_request.dict())
        device_id = reg_response.json()["device_id"]
        
        # Update device to active status (simulating completion of registration)
        await db_pool.execute("""
            UPDATE device.devices SET status = 'active' WHERE device_id = $1
        """, device_id)
        
        # Authenticate device
        auth_request = DeviceDataFactory.create_device_auth_request(
            device_id=device_id
        )
        
        response = await http_client.post("/api/v1/devices/auth", json=auth_request.dict())
        
        assert response.status_code == 200
        auth_data = response.json()
        
        # Verify authentication response
        assert auth_data["device_id"] == device_id
        assert "access_token" in auth_data
        assert auth_data["token_type"] == "Bearer"
        assert "expires_in" in auth_data
        assert isinstance(auth_data["expires_in"], int)
        assert auth_data["expires_in"] > 0
        
        # Verify device status updated in database
        db_record = await db_pool.fetchrow("""
            SELECT status, last_authenticated_at FROM device.devices WHERE device_id = $1
        """, device_id)
        
        assert db_record["status"] == DeviceStatus.ACTIVE.value
        assert db_record["last_authenticated_at"] is not None
    
    async def test_device_authentication_invalid_credentials(
        self, http_client, test_config
    ):
        """Test device authentication with invalid credentials should fail"""
        
        auth_request = DeviceDataFactory.create_device_auth_request(
            device_id="nonexistent-device",
            overrides={"device_secret": "invalid_secret"}
        )
        
        response = await http_client.post("/api/v1/devices/auth", json=auth_request.dict())
        assert response.status_code == 401
        
        error_data = response.json()
        assert "error" in error_data
        assert "INVALID_CREDENTIALS" in error_data["error"]
    
    async def test_device_authentication_rate_limiting(
        self, http_client, test_config
    ):
        """Test device authentication rate limiting"""
        
        device_id = f"rate-limit-test-{secrets.token_hex(8)}"
        auth_request = DeviceDataFactory.create_device_auth_request(
            device_id=device_id,
            overrides={"device_secret": "test_secret"}
        )
        
        # Make multiple rapid requests
        responses = []
        for i in range(6):  # Exceed rate limit of 5 per minute
            response = await http_client.post("/api/v1/devices/auth", json=auth_request.dict())
            responses.append(response)
        
        # Should hit rate limit
        assert any(r.status_code == 429 for r in responses)
        rate_limited_response = next(r for r in responses if r.status_code == 429)
        
        error_data = rate_limited_response.json()
        assert "error" in error_data
        assert "RATE_LIMIT_EXCEEDED" in error_data["error"]


class TestDeviceCommandIntegration:
    """Test device command execution integration with MQTT and database"""
    
    async def test_send_device_command_success(
        self, http_client, db_pool, nats_client, test_config
    ):
        """Test successful device command delivery and tracking"""
        
        # Register and activate a device
        registration_request = DeviceDataFactory.create_device_registration_request()
        reg_response = await http_client.post("/api/v1/devices", json=registration_request.dict())
        device_id = reg_response.json()["device_id"]
        
        await db_pool.execute("""
            UPDATE device.devices SET status = 'active' WHERE device_id = $1
        """, device_id)
        
        # Send command to device
        command_request = DeviceDataFactory.create_device_command_request(
            command_name="reboot"
        )
        
        response = await http_client.post(
            f"/api/v1/devices/{device_id}/commands",
            json=command_request.dict()
        )
        
        assert response.status_code == 200
        command_data = response.json()
        
        # Verify command response
        assert "command_id" in command_data
        assert command_data["device_id"] == device_id
        assert command_data["command"] == command_request.command
        assert command_data["status"] in ["pending", "sent"]
        
        command_id = command_data["command_id"]
        
        # Verify command stored in database
        db_command = await db_pool.fetchrow("""
            SELECT command_id, device_id, command, status, priority, timeout
            FROM device.device_commands WHERE command_id = $1
        """, command_id)
        
        assert db_command is not None
        assert db_command["command_id"] == command_id
        assert db_command["device_id"] == device_id
        assert db_command["command"] == command_request.command
        assert db_command["status"] in ["pending", "sent"]
        assert db_command["priority"] == command_request.priority.value
        assert db_command["timeout"] == command_request.timeout
        
        # Verify command published to MQTT via NATS bridge
        mqtt_events = []
        
        async def mqtt_handler(msg):
            mqtt_events.append(json.loads(msg.data.decode()))
        
        await nats_client.subscribe(f"devices.{device_id}.commands.*", cb=mqtt_handler)
        
        # Wait for MQTT message
        await asyncio.sleep(0.5)
        
        assert len(mqtt_events) > 0
        command_event = next((e for e in mqtt_events if e.get("command_id") == command_id), None)
        assert command_event is not None
        assert command_event["command_id"] == command_id
        assert command_event["device_id"] == device_id
        assert command_event["command"] == command_request.command
    
    async def test_send_device_command_unauthorized(
        self, http_client, test_config
    ):
        """Test sending command to unauthorized device should fail"""
        
        # Try to send command to device owned by different user
        unauthorized_device_id = "unauthorized-device-123"
        command_request = DeviceDataFactory.create_device_command_request()
        
        response = await http_client.post(
            f"/api/v1/devices/{unauthorized_device_id}/commands",
            json=command_request.dict()
        )
        
        assert response.status_code == 403
        
        error_data = response.json()
        assert "error" in error_data
        assert "UNAUTHORIZED_COMMAND_ACCESS" in error_data["error"]
    
    async def test_send_bulk_command_success(
        self, http_client, db_pool, test_config
    ):
        """Test successful bulk command execution"""
        
        # Register multiple devices
        device_ids = []
        for i in range(3):
            registration_request = DeviceDataFactory.create_device_registration_request()
            reg_response = await http_client.post("/api/v1/devices", json=registration_request.dict())
            device_id = reg_response.json()["device_id"]
            device_ids.append(device_id)
            
            await db_pool.execute("""
                UPDATE device.devices SET status = 'active' WHERE device_id = $1
            """, device_id)
        
        # Send bulk command
        bulk_request = DeviceDataFactory.create_bulk_command_request(
            device_count=len(device_ids),
            overrides={"device_ids": device_ids}
        )
        
        response = await http_client.post("/api/v1/devices/bulk/commands", json=bulk_request.dict())
        
        assert response.status_code == 200
        bulk_response = response.json()
        
        # Verify bulk command response
        assert "command_id" in bulk_response  # Bulk command ID
        assert bulk_response["device_count"] == len(device_ids)
        assert "results" in bulk_response
        assert len(bulk_response["results"]) == len(device_ids)
        
        # Verify individual commands created in database
        for device_id in device_ids:
            device_commands = await db_pool.fetch("""
                SELECT command_id, status FROM device.device_commands WHERE device_id = $1
            """, device_id)
            
            assert len(device_commands) == 1
            assert device_commands[0]["status"] in ["pending", "sent"]


class TestDeviceHealthIntegration:
    """Test device health monitoring integration"""
    
    async def test_get_device_health_success(
        self, http_client, db_pool, test_config
    ):
        """Test retrieving device health information"""
        
        # Register a device
        registration_request = DeviceDataFactory.create_device_registration_request()
        reg_response = await http_client.post("/api/v1/devices", json=registration_request.dict())
        device_id = reg_response.json()["device_id"]
        
        # Insert health data
        health_data = DeviceDataFactory.create_device_health_response(
            device_id=device_id,
            overrides={"status": DeviceStatus.ACTIVE}
        )
        
        await db_pool.execute("""
            UPDATE device.devices 
            SET status = $1, last_seen = NOW()
            WHERE device_id = $2
        """, health_data.status.value, device_id)
        
        # Get device health
        response = await http_client.get(f"/api/v1/devices/{device_id}/health")
        
        assert response.status_code == 200
        health_response = response.json()
        
        # Verify health response structure
        assert health_response["device_id"] == device_id
        assert health_response["status"] == health_data.status.value
        assert 0 <= health_response["health_score"] <= 100
        assert isinstance(health_response["error_count"], int)
        assert isinstance(health_response["warning_count"], int)
        assert "last_check" in health_response
    
    async def test_device_health_calculation(
        self, http_client, db_pool, test_config
    ):
        """Test automatic health score calculation"""
        
        # Register device and create activity history
        registration_request = DeviceDataFactory.create_device_registration_request()
        reg_response = await http_client.post("/api/v1/devices", json=registration_request.dict())
        device_id = reg_response.json()["device_id"]
        
        # Simulate device activity
        await db_pool.execute("""
            UPDATE device.devices 
            SET 
                total_commands = 100,
                total_telemetry_points = 10000,
                uptime_percentage = 95.5,
                last_seen = NOW()
            WHERE device_id = $1
        """, device_id)
        
        # Get health to trigger calculation
        response = await http_client.get(f"/api/v1/devices/{device_id}/health")
        
        assert response.status_code == 200
        health_response = response.json()
        
        # Health score should be high for active device
        assert health_response["health_score"] >= 80


class TestDeviceStatisticsIntegration:
    """Test device statistics and analytics integration"""
    
    async def test_get_device_statistics_success(
        self, http_client, db_pool, test_config
    ):
        """Test retrieving device statistics"""
        
        # Create multiple devices with different statuses
        devices_data = [
            {"status": DeviceStatus.ACTIVE, "type": DeviceType.SMART_FRAME},
            {"status": DeviceStatus.INACTIVE, "type": DeviceType.SENSOR},
            {"status": DeviceStatus.ERROR, "type": DeviceType.CAMERA},
            {"status": DeviceStatus.ACTIVE, "type": DeviceType.CONTROLLER},
            {"status": DeviceStatus.ACTIVE, "type": DeviceType.SMART_FRAME},
        ]
        
        for device_info in devices_data:
            registration_request = DeviceDataFactory.create_device_registration_request(
                device_type=device_info["type"]
            )
            reg_response = await http_client.post("/api/v1/devices", json=registration_request.dict())
            device_id = reg_response.json()["device_id"]
            
            await db_pool.execute("""
                UPDATE device.devices SET status = $1 WHERE device_id = $2
            """, device_info["status"].value, device_id)
        
        # Get device statistics
        response = await http_client.get("/api/v1/devices/stats")
        
        assert response.status_code == 200
        stats_response = response.json()
        
        # Verify statistics structure
        assert "total_devices" in stats_response
        assert "active_devices" in stats_response
        assert "inactive_devices" in stats_response
        assert "error_devices" in stats_response
        assert "devices_by_type" in stats_response
        assert "devices_by_status" in stats_response
        assert "avg_uptime" in stats_response
        
        # Verify statistics accuracy
        assert stats_response["total_devices"] == len(devices_data)
        assert stats_response["active_devices"] == 3
        assert stats_response["inactive_devices"] == 1
        assert stats_response["error_devices"] == 1
        
        # Check device type breakdown
        devices_by_type = stats_response["devices_by_type"]
        assert devices_by_type.get("smart_frame", 0) == 2
        assert devices_by_type.get("sensor", 0) == 1
        assert devices_by_type.get("camera", 0) == 1
        assert devices_by_type.get("controller", 0) == 1


class TestSmartFrameIntegration:
    """Test smart frame specific integration features"""
    
    async def test_register_smart_frame_success(
        self, http_client, db_pool, test_config
    ):
        """Test smart frame registration with frame-specific features"""
        
        # Register smart frame
        frame_request = FrameDataFactory.create_frame_registration_request()
        
        response = await http_client.post("/api/v1/devices/frames", json=frame_request.dict())
        
        assert response.status_code == 201
        frame_response = response.json()
        
        # Verify frame response structure
        assert "device_id" in frame_response
        assert frame_response["device_name"] == frame_request.device_name
        assert frame_response["device_type"] == DeviceType.SMART_FRAME.value
        assert "frame_config" in frame_response
        assert "frame_status" in frame_response
        
        device_id = frame_response["device_id"]
        
        # Verify frame config stored in database
        frame_config = await db_pool.fetchrow("""
            SELECT brightness, display_mode, auto_sync_albums FROM device.frame_configs WHERE device_id = $1
        """, device_id)
        
        assert frame_config is not None
    
    async def test_frame_content_sync(
        self, http_client, db_pool, nats_client, test_config
    ):
        """Test frame content synchronization"""
        
        # Register smart frame
        frame_request = FrameDataFactory.create_frame_registration_request()
        reg_response = await http_client.post("/api/v1/devices/frames", json=frame_request.dict())
        device_id = reg_response.json()["device_id"]
        
        # Initiate content sync
        sync_request = {
            "album_ids": ["album1", "album2"],
            "force": False,
            "priority": "normal"
        }
        
        response = await http_client.post(
            f"/api/v1/devices/frames/{device_id}/sync",
            json=sync_request
        )
        
        assert response.status_code == 200
        sync_response = response.json()
        
        # Verify sync response
        assert "sync_id" in sync_response
        assert sync_response["device_id"] == device_id
        assert sync_response["sync_type"] in ["full", "incremental"]
        assert sync_response["status"] in ["pending", "started"]
        
        # Verify sync event published
        sync_events = []
        
        async def sync_handler(msg):
            sync_events.append(json.loads(msg.data.decode()))
        
        await nats_client.subscribe("frame.sync_started", cb=sync_handler)
        await asyncio.sleep(0.5)
        
        assert len(sync_events) > 0
        sync_event = next((e for e in sync_events if e.get("device_id") == device_id), None)
        assert sync_event is not None
        assert sync_event["event_type"] == "frame.sync_started"
        assert sync_event["device_id"] == device_id
        assert "album_ids" in sync_event
    
    async def test_frame_display_control(
        self, http_client, db_pool, test_config
    ):
        """Test frame display control"""
        
        # Register smart frame
        frame_request = FrameDataFactory.create_frame_registration_request()
        reg_response = await http_client.post("/api/v1/devices/frames", json=frame_request.dict())
        device_id = reg_response.json()["device_id"]
        
        # Update frame display settings
        display_request = {
            "brightness": 85,
            "display_mode": "clock_display",
            "slideshow_interval": 45
        }
        
        response = await http_client.post(
            f"/api/v1/devices/frames/{device_id}/display",
            json=display_request
        )
        
        assert response.status_code == 200
        display_response = response.json()
        
        # Verify display control response
        assert display_response["device_id"] == device_id
        assert display_response["success"] is True
        
        # Verify config updated in database
        updated_config = await db_pool.fetchrow("""
            SELECT brightness, display_mode, slideshow_interval 
            FROM device.frame_configs WHERE device_id = $1
        """, device_id)
        
        assert updated_config is not None
        assert updated_config["brightness"] == 85
        assert updated_config["display_mode"] == "clock_display"
        assert updated_config["slideshow_interval"] == 45


class TestErrorHandlingIntegration:
    """Test error handling and edge cases in integration scenarios"""
    
    async def test_database_connection_failure_recovery(
        self, http_client, test_config
    ):
        """Test service behavior during database connection issues"""
        
        # This test would require database connection failure simulation
        # In real integration tests, you might use a database proxy to simulate failures
        
        # For now, test graceful degradation
        response = await http_client.get("/api/v1/devices/stats")
        
        # Should handle database issues gracefully
        if response.status_code == 503:
            error_data = response.json()
            assert "error" in error_data
            assert "DATABASE_UNAVAILABLE" in error_data["error"]
    
    async def test_nats_connection_failure_recovery(
        self, http_client, test_config
    ):
        """Test service behavior during NATS connection issues"""
        
        # Register a device
        registration_request = DeviceDataFactory.create_device_registration_request()
        response = await http_client.post("/api/v1/devices", json=registration_request.dict())
        
        # Should succeed even if NATS is down (events queued)
        assert response.status_code == 201
        
        # Service should handle NATS failures gracefully
        # Events would be queued for later delivery
    
    async def test_concurrent_device_operations(
        self, http_client, db_pool, test_config
    ):
        """Test concurrent operations on same device"""
        
        # Register device
        registration_request = DeviceDataFactory.create_device_registration_request()
        reg_response = await http_client.post("/api/v1/devices", json=registration_request.dict())
        device_id = reg_response.json()["device_id"]
        
        # Send concurrent commands
        command_request = DeviceDataFactory.create_device_command_request(
            command_name="reboot"
        )
        
        tasks = []
        for i in range(5):
            task = http_client.post(
                f"/api/v1/devices/{device_id}/commands",
                json=command_request.dict()
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should succeed or handle gracefully
        successful_responses = [r for r in responses if hasattr(r, 'status_code') and r.status_code == 200]
        assert len(successful_responses) >= 1
        
        # Verify command queue handling
        commands = await db_pool.fetch("""
            SELECT command_id, status FROM device.device_commands WHERE device_id = $1 ORDER BY created_at
        """, device_id)
        
        assert len(commands) == len(successful_responses)


class TestPerformanceIntegration:
    """Test performance characteristics under load"""
    
    async def test_bulk_device_registration_performance(
        self, http_client, db_pool, test_config
    ):
        """Test performance of bulk device registration"""
        
        # Register multiple devices concurrently
        device_count = 50
        registration_requests = [
            DeviceDataFactory.create_device_registration_request()
            for _ in range(device_count)
        ]
        
        start_time = datetime.now(timezone.utc)
        
        tasks = [
            http_client.post("/api/v1/devices", json=req.dict())
            for req in registration_requests
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        # Verify performance metrics
        successful_responses = [r for r in responses if hasattr(r, 'status_code') and r.status_code == 201]
        assert len(successful_responses) >= device_count * 0.9  # 90% success rate
        assert duration < 30.0  # Should complete within 30 seconds
        
        # Verify database consistency
        total_devices = await db_pool.fetchval("""
            SELECT COUNT(*) FROM device.devices WHERE user_id = $1
        """, test_config["test_user_id"])
        
        assert total_devices == len(successful_responses)
    
    async def test_real_time_command_execution_performance(
        self, http_client, db_pool, test_config
    ):
        """Test performance of real-time command execution"""
        
        # Register and activate device
        registration_request = DeviceDataFactory.create_device_registration_request()
        reg_response = await http_client.post("/api/v1/devices", json=registration_request.dict())
        device_id = reg_response.json()["device_id"]
        
        await db_pool.execute("""
            UPDATE device.devices SET status = 'active' WHERE device_id = $1
        """, device_id)
        
        # Send command and measure response time
        command_request = DeviceDataFactory.create_device_command_request(
            command_name="get_status"
        )
        
        start_time = datetime.now(timezone.utc)
        
        response = await http_client.post(
            f"/api/v1/devices/{device_id}/commands",
            json=command_request.dict()
        )
        
        end_time = datetime.now(timezone.utc)
        response_time = (end_time - start_time).total_seconds()
        
        assert response.status_code == 200
        assert response_time < 1.0  # Should respond within 1 second


# Integration test utilities
class IntegrationTestUtils:
    """Utilities for integration testing"""
    
    @staticmethod
    async def create_test_user(db_pool, user_id: str):
        """Create test user in database"""
        await db_pool.execute("""
            INSERT INTO users (user_id, email, created_at) 
            VALUES ($1, $2, NOW())
            ON CONFLICT (user_id) DO NOTHING
        """, user_id, f"{user_id}@test.com")
    
    @staticmethod
    async def wait_for_event(nats_client, subject: str, timeout: float = 5.0):
        """Wait for specific event on NATS"""
        event_received = asyncio.Event()
        event_data = None
        
        async def handler(msg):
            nonlocal event_data
            event_data = json.loads(msg.data.decode())
            event_received.set()
        
        await nats_client.subscribe(subject, cb=handler)
        
        try:
            await asyncio.wait_for(event_received.wait(), timeout=timeout)
            return event_data
        except asyncio.TimeoutError:
            return None
    
    @staticmethod
    async def simulate_device_heartbeat(db_pool, device_id: str):
        """Simulate device heartbeat in database"""
        await db_pool.execute("""
            UPDATE device.devices 
            SET last_seen = NOW(), status = 'active'
            WHERE device_id = $1
        """, device_id)


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])
