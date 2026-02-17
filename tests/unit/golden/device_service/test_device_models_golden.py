"""
Device Models Golden Tests

🔒 GOLDEN: These tests document CURRENT behavior of device models.
   DO NOT MODIFY unless behavior intentionally changes.

Purpose:
- Protect against accidental regressions
- Document what code currently does
- All tests should PASS (they describe existing behavior)

Usage:
    pytest tests/unit/golden -v
"""
import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from microservices.device_service.models import (
    DeviceType,
    DeviceStatus,
    ConnectivityType,
    SecurityLevel,
    DeviceRegistrationRequest,
    DeviceUpdateRequest,
    DeviceAuthRequest,
    DeviceCommandRequest,
    BulkCommandRequest,
    DeviceGroupRequest,
    DeviceResponse,
    DeviceAuthResponse,
    DeviceGroupResponse,
    DeviceStatsResponse,
    DeviceHealthResponse,
    FrameDisplayMode,
    FrameOrientation,
    FrameConfig,
    DisplayCommand,
    FrameStatus,
    FrameRegistrationRequest,
    UpdateFrameConfigRequest,
    FrameCommandRequest,
    FrameResponse,
    DevicePairingRequest,
    DevicePairingResponse,
)

pytestmark = [pytest.mark.unit, pytest.mark.golden]


# =============================================================================
# DeviceType Enum - Current Behavior
# =============================================================================

class TestDeviceTypeEnum:
    """Characterization: DeviceType enum current behavior"""

    def test_all_device_types_defined(self):
        """CHAR: All expected device types are defined"""
        expected_types = {
            "sensor", "actuator", "gateway", "smart_home",
            "industrial", "medical", "automotive", "wearable",
            "camera", "controller", "smart_frame"
        }
        actual_types = {dt.value for dt in DeviceType}
        assert actual_types == expected_types

    def test_device_type_values(self):
        """CHAR: Device type values are correct"""
        assert DeviceType.SMART_FRAME.value == "smart_frame"
        assert DeviceType.CAMERA.value == "camera"
        assert DeviceType.SENSOR.value == "sensor"


# =============================================================================
# DeviceStatus Enum - Current Behavior
# =============================================================================

class TestDeviceStatusEnum:
    """Characterization: DeviceStatus enum current behavior"""

    def test_all_status_values(self):
        """CHAR: All expected statuses are defined"""
        expected_statuses = {
            "pending", "active", "inactive", "maintenance",
            "error", "decommissioned"
        }
        actual_statuses = {ds.value for ds in DeviceStatus}
        assert actual_statuses == expected_statuses


# =============================================================================
# DeviceRegistrationRequest - Current Behavior
# =============================================================================

class TestDeviceRegistrationRequestChar:
    """Characterization: DeviceRegistrationRequest current behavior"""

    def test_accepts_valid_minimal_request(self):
        """CHAR: Valid minimal request is accepted"""
        req = DeviceRegistrationRequest(
            device_name="Test Device",
            device_type=DeviceType.SMART_FRAME,
            manufacturer="Test Manufacturer",
            model="Test Model",
            serial_number="SN123456",
            firmware_version="1.0.0",
            connectivity_type=ConnectivityType.WIFI
        )
        assert req.device_name == "Test Device"
        assert req.device_type == DeviceType.SMART_FRAME

    def test_accepts_full_request_with_all_fields(self):
        """CHAR: Valid request with all fields is accepted"""
        req = DeviceRegistrationRequest(
            device_name="Full Device",
            device_type=DeviceType.SMART_FRAME,
            manufacturer="Manufacturer",
            model="Model X",
            serial_number="SN789",
            firmware_version="2.0.0",
            hardware_version="1.1.0",
            mac_address="AA:BB:CC:DD:EE:FF",
            connectivity_type=ConnectivityType.WIFI,
            security_level=SecurityLevel.HIGH,
            location={"latitude": 37.7749, "longitude": -122.4194},
            metadata={"key": "value"},
            group_id="group_123",
            tags=["test", "device"]
        )
        assert req.security_level == SecurityLevel.HIGH
        assert req.location["latitude"] == 37.7749
        assert req.tags == ["test", "device"]

    def test_requires_device_name(self):
        """CHAR: device_name is required"""
        with pytest.raises(ValidationError):
            DeviceRegistrationRequest(
                device_type=DeviceType.SMART_FRAME,
                manufacturer="Test",
                model="Test",
                serial_number="SN123",
                firmware_version="1.0",
                connectivity_type=ConnectivityType.WIFI
            )

    def test_device_name_min_length_1(self):
        """CHAR: device_name minimum length is 1"""
        req = DeviceRegistrationRequest(
            device_name="A",
            device_type=DeviceType.SMART_FRAME,
            manufacturer="Test",
            model="Test",
            serial_number="SN123",
            firmware_version="1.0",
            connectivity_type=ConnectivityType.WIFI
        )
        assert req.device_name == "A"

    def test_device_name_max_length_200(self):
        """CHAR: device_name maximum length is 200"""
        req = DeviceRegistrationRequest(
            device_name="X" * 200,
            device_type=DeviceType.SMART_FRAME,
            manufacturer="Test",
            model="Test",
            serial_number="SN123",
            firmware_version="1.0",
            connectivity_type=ConnectivityType.WIFI
        )
        assert len(req.device_name) == 200

    def test_device_name_over_200_raises_error(self):
        """CHAR: device_name over 200 characters raises error"""
        with pytest.raises(ValidationError):
            DeviceRegistrationRequest(
                device_name="X" * 201,
                device_type=DeviceType.SMART_FRAME,
                manufacturer="Test",
                model="Test",
                serial_number="SN123",
                firmware_version="1.0",
                connectivity_type=ConnectivityType.WIFI
            )

    def test_mac_address_pattern_validation(self):
        """CHAR: MAC address pattern validation"""
        # Valid MAC addresses
        valid_macs = [
            "AA:BB:CC:DD:EE:FF",
            "aa:bb:cc:dd:ee:ff",
            "A1:B2:C3:D4:E5:F6"
        ]
        
        for mac in valid_macs:
            req = DeviceRegistrationRequest(
                device_name="Test",
                device_type=DeviceType.SMART_FRAME,
                manufacturer="Test",
                model="Test",
                serial_number="SN123",
                firmware_version="1.0",
                connectivity_type=ConnectivityType.WIFI,
                mac_address=mac
            )
            assert req.mac_address == mac

    def test_invalid_mac_address_raises_error(self):
        """CHAR: Invalid MAC address raises error"""
        # Pattern allows both : and - separators: ^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$
        invalid_macs = [
            "invalid",
            "GG:HH:II:JJ:KK:LL",  # Invalid hex
            "AABBCCDDEEFF",        # No separators
        ]

        for mac in invalid_macs:
            with pytest.raises(ValidationError):
                DeviceRegistrationRequest(
                    device_name="Test",
                    device_type=DeviceType.SMART_FRAME,
                    manufacturer="Test",
                    model="Test",
                    serial_number="SN123",
                    firmware_version="1.0",
                    connectivity_type=ConnectivityType.WIFI,
                    mac_address=mac
                )


# =============================================================================
# DeviceUpdateRequest - Current Behavior
# =============================================================================

class TestDeviceUpdateRequestChar:
    """Characterization: DeviceUpdateRequest current behavior"""

    def test_all_fields_optional(self):
        """CHAR: All fields are optional"""
        req = DeviceUpdateRequest()
        assert req.device_name is None
        assert req.status is None
        assert req.firmware_version is None

    def test_device_name_validation_when_provided(self):
        """CHAR: device_name validated when provided"""
        req = DeviceUpdateRequest(device_name="Updated Name")
        assert req.device_name == "Updated Name"

        with pytest.raises(ValidationError):
            DeviceUpdateRequest(device_name="")  # Too short

        with pytest.raises(ValidationError):
            DeviceUpdateRequest(device_name="X" * 201)  # Too long

    def test_status_must_be_valid_enum(self):
        """CHAR: status must be valid DeviceStatus"""
        req = DeviceUpdateRequest(status=DeviceStatus.ACTIVE)
        assert req.status == DeviceStatus.ACTIVE

        # Can also be None
        req_none = DeviceUpdateRequest()
        assert req_none.status is None


# =============================================================================
# DeviceCommandRequest - Current Behavior
# =============================================================================

class TestDeviceCommandRequestChar:
    """Characterization: DeviceCommandRequest current behavior"""

    def test_accepts_valid_command(self):
        """CHAR: Valid command is accepted"""
        req = DeviceCommandRequest(
            command="reboot",
            parameters={"delay": 5},
            timeout=30,
            priority=1,
            require_ack=True
        )
        assert req.command == "reboot"
        assert req.parameters["delay"] == 5
        assert req.timeout == 30

    def test_command_min_length_1(self):
        """CHAR: command minimum length is 1"""
        req = DeviceCommandRequest(command="X")
        assert req.command == "X"

    def test_command_max_length_100(self):
        """CHAR: command maximum length is 100"""
        req = DeviceCommandRequest(command="X" * 100)
        assert len(req.command) == 100

    def test_timeout_min_1_max_300(self):
        """CHAR: timeout range is 1-300"""
        req = DeviceCommandRequest(command="test", timeout=1)
        assert req.timeout == 1

        req = DeviceCommandRequest(command="test", timeout=300)
        assert req.timeout == 300

        with pytest.raises(ValidationError):
            DeviceCommandRequest(command="test", timeout=0)

        with pytest.raises(ValidationError):
            DeviceCommandRequest(command="test", timeout=301)

    def test_priority_min_1_max_10(self):
        """CHAR: priority range is 1-10"""
        req = DeviceCommandRequest(command="test", priority=1)
        assert req.priority == 1

        req = DeviceCommandRequest(command="test", priority=10)
        assert req.priority == 10

        with pytest.raises(ValidationError):
            DeviceCommandRequest(command="test", priority=0)

        with pytest.raises(ValidationError):
            DeviceCommandRequest(command="test", priority=11)


# =============================================================================
# FrameConfig - Current Behavior
# =============================================================================

class TestFrameConfigChar:
    """Characterization: FrameConfig current behavior"""

    def test_accepts_minimal_config(self):
        """CHAR: Minimal config with only required fields"""
        config = FrameConfig(device_id="frame_123")
        assert config.device_id == "frame_123"
        assert config.brightness == 80  # Default
        assert config.auto_brightness is True  # Default

    def test_brightness_range_0_to_100(self):
        """CHAR: brightness range is 0-100"""
        config = FrameConfig(device_id="frame_123", brightness=0)
        assert config.brightness == 0

        config = FrameConfig(device_id="frame_123", brightness=100)
        assert config.brightness == 100

        with pytest.raises(ValidationError):
            FrameConfig(device_id="frame_123", brightness=-1)

        with pytest.raises(ValidationError):
            FrameConfig(device_id="frame_123", brightness=101)

    def test_contrast_range_0_to_200(self):
        """CHAR: contrast range is 0-200"""
        config = FrameConfig(device_id="frame_123", contrast=0)
        assert config.contrast == 0

        config = FrameConfig(device_id="frame_123", contrast=200)
        assert config.contrast == 200

        with pytest.raises(ValidationError):
            FrameConfig(device_id="frame_123", contrast=-1)

        with pytest.raises(ValidationError):
            FrameConfig(device_id="frame_123", contrast=201)

    def test_slideshow_interval_range_5_to_3600(self):
        """CHAR: slideshow_interval range is 5-3600"""
        config = FrameConfig(device_id="frame_123", slideshow_interval=5)
        assert config.slideshow_interval == 5

        config = FrameConfig(device_id="frame_123", slideshow_interval=3600)
        assert config.slideshow_interval == 3600

        with pytest.raises(ValidationError):
            FrameConfig(device_id="frame_123", slideshow_interval=4)

        with pytest.raises(ValidationError):
            FrameConfig(device_id="frame_123", slideshow_interval=3601)


# =============================================================================
# DeviceResponse - Current Behavior
# =============================================================================

class TestDeviceResponseChar:
    """Characterization: DeviceResponse current behavior"""

    def test_all_fields_initialized(self):
        """CHAR: All fields have proper defaults"""
        device = DeviceResponse(
            device_id="dev_123",
            device_name="Test Device",
            device_type=DeviceType.SMART_FRAME,
            manufacturer="Test",
            model="Test",
            serial_number="SN123",
            firmware_version="1.0",
            hardware_version=None,
            mac_address=None,
            connectivity_type=ConnectivityType.WIFI,
            security_level=SecurityLevel.STANDARD,
            status=DeviceStatus.ACTIVE,
            location=None,
            metadata=None,
            group_id=None,
            tags=[],  # Required: List[str], not Optional
            last_seen=None,
            registered_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            user_id="user_123",
            organization_id=None
        )

        assert device.total_commands == 0  # Default
        assert device.total_telemetry_points == 0  # Default
        assert device.uptime_percentage == 0.0  # Default

    def test_optional_fields_can_be_none(self):
        """CHAR: Optional fields can be None, but tags must be List"""
        device = DeviceResponse(
            device_id="dev_123",
            device_name="Test",
            device_type=DeviceType.SMART_FRAME,
            manufacturer="Test",
            model="Test",
            serial_number="SN123",
            firmware_version="1.0",
            connectivity_type=ConnectivityType.WIFI,
            security_level=SecurityLevel.STANDARD,
            status=DeviceStatus.ACTIVE,
            registered_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            user_id="user_123",
            hardware_version=None,
            mac_address=None,
            location=None,
            metadata=None,
            group_id=None,
            tags=[],  # Must be List, not None
            last_seen=None,
            organization_id=None
        )

        assert device.hardware_version is None
        assert device.mac_address is None
        assert device.location is None
        assert device.tags == []  # Empty list, not None


# =============================================================================
# DevicePairingRequest - Current Behavior
# =============================================================================

class TestDevicePairingRequestChar:
    """Characterization: DevicePairingRequest current behavior"""

    def test_accepts_valid_pairing_request(self):
        """CHAR: Valid pairing request is accepted"""
        req = DevicePairingRequest(
            pairing_token="token_123456",
            user_id="user_123"
        )
        assert req.pairing_token == "token_123456"
        assert req.user_id == "user_123"

    def test_requires_pairing_token(self):
        """CHAR: pairing_token is required"""
        with pytest.raises(ValidationError):
            DevicePairingRequest(user_id="user_123")

    def test_requires_user_id(self):
        """CHAR: user_id is required"""
        with pytest.raises(ValidationError):
            DevicePairingRequest(pairing_token="token_123")


# =============================================================================
# BulkCommandRequest - Current Behavior
# =============================================================================

class TestBulkCommandRequestChar:
    """Characterization: BulkCommandRequest current behavior"""

    def test_accepts_valid_bulk_request(self):
        """CHAR: Valid bulk request is accepted"""
        req = BulkCommandRequest(
            device_ids=["dev_1", "dev_2"],
            command_name="reboot",
            parameters={"delay": 5},
            timeout=30,
            priority=5,
            require_ack=True
        )
        assert len(req.device_ids) == 2
        assert req.command_name == "reboot"
        assert req.parameters["delay"] == 5

    def test_device_ids_can_be_empty_list(self):
        """CHAR: device_ids accepts empty list (no min_length validation)"""
        # Model allows empty list - no validator rejecting it
        req = BulkCommandRequest(
            command_name="test",
            device_ids=[]
        )
        assert req.device_ids == []

    def test_requires_command_name(self):
        """CHAR: command_name is required"""
        with pytest.raises(ValidationError):
            BulkCommandRequest(
                device_ids=["dev_1"],
                command_name=""
            )

    def test_device_ids_must_be_list(self):
        """CHAR: device_ids must be a list"""
        req = BulkCommandRequest(
            device_ids=["dev_1", "dev_2"],
            command_name="test"
        )
        assert isinstance(req.device_ids, list)
        assert len(req.device_ids) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
