"""
Unit Golden Tests: OTA Service Models

Tests model validation and serialization without external dependencies.
"""
import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from microservices.ota_service.models import (
    UpdateType,
    UpdateStatus,
    DeploymentStrategy,
    Priority,
    RollbackTrigger,
    FirmwareUploadRequest,
    UpdateCampaignRequest,
    DeviceUpdateRequest,
    UpdateApprovalRequest,
    FirmwareResponse,
    UpdateCampaignResponse,
    DeviceUpdateResponse,
    UpdateStatsResponse,
    RollbackResponse,
)


class TestEnumTypes:
    """Test enum type definitions"""

    def test_update_type_values(self):
        """Test UpdateType enum values"""
        assert UpdateType.FIRMWARE == "firmware"
        assert UpdateType.SOFTWARE == "software"
        assert UpdateType.APPLICATION == "application"
        assert UpdateType.CONFIG == "config"
        assert UpdateType.BOOTLOADER == "bootloader"
        assert UpdateType.SECURITY_PATCH == "security_patch"

    def test_update_status_values(self):
        """Test UpdateStatus enum values"""
        assert UpdateStatus.CREATED == "created"
        assert UpdateStatus.SCHEDULED == "scheduled"
        assert UpdateStatus.IN_PROGRESS == "in_progress"
        assert UpdateStatus.DOWNLOADING == "downloading"
        assert UpdateStatus.VERIFYING == "verifying"
        assert UpdateStatus.INSTALLING == "installing"
        assert UpdateStatus.REBOOTING == "rebooting"
        assert UpdateStatus.COMPLETED == "completed"
        assert UpdateStatus.FAILED == "failed"
        assert UpdateStatus.CANCELLED == "cancelled"
        assert UpdateStatus.ROLLBACK == "rollback"

    def test_deployment_strategy_values(self):
        """Test DeploymentStrategy enum values"""
        assert DeploymentStrategy.IMMEDIATE == "immediate"
        assert DeploymentStrategy.SCHEDULED == "scheduled"
        assert DeploymentStrategy.STAGED == "staged"
        assert DeploymentStrategy.CANARY == "canary"
        assert DeploymentStrategy.BLUE_GREEN == "blue_green"

    def test_priority_values(self):
        """Test Priority enum values"""
        assert Priority.LOW == "low"
        assert Priority.NORMAL == "normal"
        assert Priority.HIGH == "high"
        assert Priority.CRITICAL == "critical"
        assert Priority.EMERGENCY == "emergency"

    def test_rollback_trigger_values(self):
        """Test RollbackTrigger enum values"""
        assert RollbackTrigger.MANUAL == "manual"
        assert RollbackTrigger.FAILURE_RATE == "failure_rate"
        assert RollbackTrigger.HEALTH_CHECK == "health_check"
        assert RollbackTrigger.TIMEOUT == "timeout"
        assert RollbackTrigger.ERROR_THRESHOLD == "error_threshold"


class TestFirmwareUploadRequest:
    """Test FirmwareUploadRequest model validation"""

    def test_firmware_upload_request_with_all_fields(self):
        """Test creating firmware upload request with all fields"""
        request = FirmwareUploadRequest(
            name="Device Firmware v2.5.0",
            version="2.5.0",
            description="Security update with bug fixes",
            device_model="SmartCamera X100",
            manufacturer="TechCorp",
            min_hardware_version="1.0",
            max_hardware_version="2.0",
            file_size=5242880,  # 5MB
            checksum_md5="d41d8cd98f00b204e9800998ecf8427e",
            checksum_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            tags=["stable", "security"],
            metadata={"release_notes": "Critical security patch"},
            is_beta=False,
            is_security_update=True,
            changelog="Fixed authentication vulnerability CVE-2024-1234",
        )

        assert request.name == "Device Firmware v2.5.0"
        assert request.version == "2.5.0"
        assert request.device_model == "SmartCamera X100"
        assert request.manufacturer == "TechCorp"
        assert request.file_size == 5242880
        assert len(request.checksum_md5) == 32
        assert len(request.checksum_sha256) == 64
        assert request.is_security_update is True
        assert "security" in request.tags

    def test_firmware_upload_request_with_minimal_fields(self):
        """Test creating firmware upload request with only required fields"""
        request = FirmwareUploadRequest(
            name="Basic Firmware",
            version="1.0.0",
            device_model="Device A",
            manufacturer="Manufacturer B",
            file_size=1048576,
            checksum_md5="a" * 32,
            checksum_sha256="b" * 64,
        )

        assert request.name == "Basic Firmware"
        assert request.version == "1.0.0"
        assert request.description is None
        assert request.tags == []
        assert request.metadata == {}
        assert request.is_beta is False
        assert request.is_security_update is False
        assert request.changelog is None

    def test_firmware_upload_request_validation_name_length(self):
        """Test firmware name length validation"""
        # Test empty name
        with pytest.raises(ValidationError) as exc_info:
            FirmwareUploadRequest(
                name="",
                version="1.0",
                device_model="Model",
                manufacturer="Mfr",
                file_size=1000,
                checksum_md5="a" * 32,
                checksum_sha256="b" * 64,
            )
        errors = exc_info.value.errors()
        assert any(err["loc"][0] == "name" for err in errors)

        # Test name too long
        with pytest.raises(ValidationError):
            FirmwareUploadRequest(
                name="x" * 201,
                version="1.0",
                device_model="Model",
                manufacturer="Mfr",
                file_size=1000,
                checksum_md5="a" * 32,
                checksum_sha256="b" * 64,
            )

    def test_firmware_upload_request_validation_file_size(self):
        """Test file size must be positive"""
        with pytest.raises(ValidationError) as exc_info:
            FirmwareUploadRequest(
                name="Test",
                version="1.0",
                device_model="Model",
                manufacturer="Mfr",
                file_size=0,
                checksum_md5="a" * 32,
                checksum_sha256="b" * 64,
            )
        errors = exc_info.value.errors()
        assert any(err["loc"][0] == "file_size" for err in errors)

    def test_firmware_upload_request_validation_checksum_length(self):
        """Test checksum length validation"""
        # MD5 checksum too short
        with pytest.raises(ValidationError):
            FirmwareUploadRequest(
                name="Test",
                version="1.0",
                device_model="Model",
                manufacturer="Mfr",
                file_size=1000,
                checksum_md5="short",
                checksum_sha256="b" * 64,
            )

        # SHA256 checksum too short
        with pytest.raises(ValidationError):
            FirmwareUploadRequest(
                name="Test",
                version="1.0",
                device_model="Model",
                manufacturer="Mfr",
                file_size=1000,
                checksum_md5="a" * 32,
                checksum_sha256="short",
            )


class TestUpdateCampaignRequest:
    """Test UpdateCampaignRequest model validation"""

    def test_update_campaign_request_with_all_fields(self):
        """Test creating update campaign request with all fields"""
        now = datetime.now(timezone.utc)
        scheduled_start = now + timedelta(hours=1)
        scheduled_end = now + timedelta(days=7)

        request = UpdateCampaignRequest(
            name="Security Update Campaign Q1",
            description="Critical security update for all devices",
            firmware_id="fw_12345",
            target_devices=["dev_001", "dev_002", "dev_003"],
            target_groups=["group_production", "group_beta"],
            target_filters={"region": "us-west", "version": "<2.0"},
            deployment_strategy=DeploymentStrategy.CANARY,
            priority=Priority.HIGH,
            rollout_percentage=50,
            max_concurrent_updates=100,
            batch_size=25,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
            timeout_minutes=120,
            auto_rollback=True,
            failure_threshold_percent=10,
            rollback_triggers=[
                RollbackTrigger.FAILURE_RATE,
                RollbackTrigger.ERROR_THRESHOLD,
            ],
            notify_on_start=True,
            notify_on_complete=True,
            notify_on_failure=True,
            notification_channels=["email", "slack", "webhook"],
        )

        assert request.name == "Security Update Campaign Q1"
        assert request.firmware_id == "fw_12345"
        assert len(request.target_devices) == 3
        assert len(request.target_groups) == 2
        assert request.deployment_strategy == DeploymentStrategy.CANARY
        assert request.priority == Priority.HIGH
        assert request.rollout_percentage == 50
        assert request.max_concurrent_updates == 100
        assert request.batch_size == 25
        assert request.timeout_minutes == 120
        assert request.auto_rollback is True
        assert request.failure_threshold_percent == 10
        assert len(request.rollback_triggers) == 2

    def test_update_campaign_request_with_minimal_fields(self):
        """Test creating update campaign request with minimal required fields"""
        request = UpdateCampaignRequest(
            name="Basic Campaign",
            firmware_id="fw_basic",
        )

        assert request.name == "Basic Campaign"
        assert request.firmware_id == "fw_basic"
        assert request.description is None
        assert request.target_devices == []
        assert request.target_groups == []
        assert request.target_filters == {}
        assert request.deployment_strategy == DeploymentStrategy.STAGED
        assert request.priority == Priority.NORMAL
        assert request.rollout_percentage == 100
        assert request.max_concurrent_updates == 10
        assert request.batch_size == 50
        assert request.timeout_minutes == 60
        assert request.auto_rollback is True
        assert request.failure_threshold_percent == 20
        assert RollbackTrigger.FAILURE_RATE in request.rollback_triggers

    def test_update_campaign_request_validation_rollout_percentage(self):
        """Test rollout percentage validation (1-100)"""
        # Test below minimum
        with pytest.raises(ValidationError):
            UpdateCampaignRequest(
                name="Test",
                firmware_id="fw_001",
                rollout_percentage=0,
            )

        # Test above maximum
        with pytest.raises(ValidationError):
            UpdateCampaignRequest(
                name="Test",
                firmware_id="fw_001",
                rollout_percentage=101,
            )

        # Test valid range
        request = UpdateCampaignRequest(
            name="Test",
            firmware_id="fw_001",
            rollout_percentage=75,
        )
        assert request.rollout_percentage == 75

    def test_update_campaign_request_validation_concurrent_updates(self):
        """Test max concurrent updates validation"""
        # Test below minimum
        with pytest.raises(ValidationError):
            UpdateCampaignRequest(
                name="Test",
                firmware_id="fw_001",
                max_concurrent_updates=0,
            )

        # Test above maximum
        with pytest.raises(ValidationError):
            UpdateCampaignRequest(
                name="Test",
                firmware_id="fw_001",
                max_concurrent_updates=1001,
            )

    def test_update_campaign_request_validation_timeout(self):
        """Test timeout validation (5-1440 minutes)"""
        # Test below minimum
        with pytest.raises(ValidationError):
            UpdateCampaignRequest(
                name="Test",
                firmware_id="fw_001",
                timeout_minutes=4,
            )

        # Test above maximum
        with pytest.raises(ValidationError):
            UpdateCampaignRequest(
                name="Test",
                firmware_id="fw_001",
                timeout_minutes=1441,
            )


class TestDeviceUpdateRequest:
    """Test DeviceUpdateRequest model validation"""

    def test_device_update_request_with_all_fields(self):
        """Test creating device update request with all fields"""
        request = DeviceUpdateRequest(
            firmware_id="fw_67890",
            priority=Priority.CRITICAL,
            force_update=True,
            pre_update_commands=["backup_config", "stop_services"],
            post_update_commands=["start_services", "verify_boot"],
            maintenance_window={
                "start": "02:00",
                "end": "06:00",
                "timezone": "UTC",
            },
            max_retries=5,
            timeout_minutes=90,
        )

        assert request.firmware_id == "fw_67890"
        assert request.priority == Priority.CRITICAL
        assert request.force_update is True
        assert len(request.pre_update_commands) == 2
        assert len(request.post_update_commands) == 2
        assert request.maintenance_window is not None
        assert request.max_retries == 5
        assert request.timeout_minutes == 90

    def test_device_update_request_with_minimal_fields(self):
        """Test creating device update request with minimal required fields"""
        request = DeviceUpdateRequest(
            firmware_id="fw_minimal",
        )

        assert request.firmware_id == "fw_minimal"
        assert request.priority == Priority.NORMAL
        assert request.force_update is False
        assert request.pre_update_commands == []
        assert request.post_update_commands == []
        assert request.maintenance_window is None
        assert request.max_retries == 3
        assert request.timeout_minutes == 60

    def test_device_update_request_validation_max_retries(self):
        """Test max retries validation (0-10)"""
        # Test below minimum
        with pytest.raises(ValidationError):
            DeviceUpdateRequest(
                firmware_id="fw_001",
                max_retries=-1,
            )

        # Test above maximum
        with pytest.raises(ValidationError):
            DeviceUpdateRequest(
                firmware_id="fw_001",
                max_retries=11,
            )

    def test_device_update_request_validation_timeout(self):
        """Test timeout validation (5-1440 minutes)"""
        # Test below minimum
        with pytest.raises(ValidationError):
            DeviceUpdateRequest(
                firmware_id="fw_001",
                timeout_minutes=4,
            )

        # Test above maximum
        with pytest.raises(ValidationError):
            DeviceUpdateRequest(
                firmware_id="fw_001",
                timeout_minutes=1441,
            )


class TestUpdateApprovalRequest:
    """Test UpdateApprovalRequest model validation"""

    def test_update_approval_request_approved(self):
        """Test creating approval request for approved campaign"""
        request = UpdateApprovalRequest(
            campaign_id="camp_12345",
            approved=True,
            approval_comment="Reviewed and approved for production deployment",
            conditions={"requires_backup": True, "max_downtime_minutes": 30},
        )

        assert request.campaign_id == "camp_12345"
        assert request.approved is True
        assert "Reviewed and approved" in request.approval_comment
        assert request.conditions["requires_backup"] is True

    def test_update_approval_request_rejected(self):
        """Test creating approval request for rejected campaign"""
        request = UpdateApprovalRequest(
            campaign_id="camp_67890",
            approved=False,
            approval_comment="Rejected due to incomplete testing",
        )

        assert request.campaign_id == "camp_67890"
        assert request.approved is False
        assert "Rejected" in request.approval_comment

    def test_update_approval_request_minimal(self):
        """Test creating approval request with minimal fields"""
        request = UpdateApprovalRequest(
            campaign_id="camp_minimal",
            approved=True,
        )

        assert request.campaign_id == "camp_minimal"
        assert request.approved is True
        assert request.approval_comment is None
        assert request.conditions == {}

    def test_update_approval_request_validation_comment_length(self):
        """Test approval comment length validation"""
        with pytest.raises(ValidationError):
            UpdateApprovalRequest(
                campaign_id="camp_001",
                approved=True,
                approval_comment="x" * 501,
            )


class TestFirmwareResponse:
    """Test FirmwareResponse model"""

    def test_firmware_response_creation_with_all_fields(self):
        """Test creating firmware response with all fields"""
        now = datetime.now(timezone.utc)

        response = FirmwareResponse(
            firmware_id="fw_12345",
            name="Device Firmware v3.0.0",
            version="3.0.0",
            description="Major release with new features",
            device_model="SmartHub Pro",
            manufacturer="TechCorp Industries",
            min_hardware_version="2.0",
            max_hardware_version="3.5",
            file_size=10485760,  # 10MB
            file_url="https://cdn.example.com/firmware/fw_12345.bin",
            checksum_md5="5d41402abc4b2a76b9719d911017c592",
            checksum_sha256="6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b",
            tags=["production", "feature-release"],
            metadata={"build_number": "3001", "git_commit": "abc123"},
            is_beta=False,
            is_security_update=False,
            changelog="Added new AI features, improved battery life",
            download_count=1523,
            success_rate=98.5,
            created_at=now,
            updated_at=now,
            created_by="admin_user_001",
        )

        assert response.firmware_id == "fw_12345"
        assert response.name == "Device Firmware v3.0.0"
        assert response.version == "3.0.0"
        assert response.device_model == "SmartHub Pro"
        assert response.manufacturer == "TechCorp Industries"
        assert response.file_size == 10485760
        assert response.download_count == 1523
        assert response.success_rate == 98.5
        assert "production" in response.tags
        assert response.created_by == "admin_user_001"

    def test_firmware_response_with_minimal_metadata(self):
        """Test firmware response with minimal metadata"""
        now = datetime.now(timezone.utc)

        response = FirmwareResponse(
            firmware_id="fw_min",
            name="Minimal Firmware",
            version="1.0",
            description=None,
            device_model="Device X",
            manufacturer="Mfr Y",
            min_hardware_version=None,
            max_hardware_version=None,
            file_size=1000000,
            file_url="https://example.com/fw.bin",
            checksum_md5="a" * 32,
            checksum_sha256="b" * 64,
            tags=[],
            metadata={},
            is_beta=False,
            is_security_update=False,
            changelog=None,
            download_count=0,
            success_rate=0.0,
            created_at=now,
            updated_at=now,
            created_by="user_001",
        )

        assert response.firmware_id == "fw_min"
        assert response.download_count == 0
        assert response.success_rate == 0.0
        assert len(response.tags) == 0
        assert len(response.metadata) == 0


class TestUpdateCampaignResponse:
    """Test UpdateCampaignResponse model"""

    def test_update_campaign_response_with_all_fields(self):
        """Test creating update campaign response with all fields"""
        now = datetime.now(timezone.utc)
        scheduled_start = now + timedelta(hours=2)
        scheduled_end = now + timedelta(days=7)
        actual_start = now + timedelta(hours=2, minutes=5)

        firmware = FirmwareResponse(
            firmware_id="fw_001",
            name="Test Firmware",
            version="2.0",
            description="Test",
            device_model="Model A",
            manufacturer="Mfr",
            min_hardware_version=None,
            max_hardware_version=None,
            file_size=5000000,
            file_url="https://example.com/fw.bin",
            checksum_md5="a" * 32,
            checksum_sha256="b" * 64,
            tags=[],
            metadata={},
            is_beta=False,
            is_security_update=True,
            changelog=None,
            download_count=0,
            success_rate=0.0,
            created_at=now,
            updated_at=now,
            created_by="admin",
        )

        response = UpdateCampaignResponse(
            campaign_id="camp_12345",
            name="Production Rollout Q1",
            description="Quarterly production update",
            firmware=firmware,
            status=UpdateStatus.IN_PROGRESS,
            deployment_strategy=DeploymentStrategy.STAGED,
            priority=Priority.HIGH,
            target_device_count=1000,
            targeted_devices=["dev_001", "dev_002"],
            targeted_groups=["group_prod"],
            rollout_percentage=75,
            max_concurrent_updates=50,
            batch_size=100,
            total_devices=1000,
            pending_devices=300,
            in_progress_devices=50,
            completed_devices=600,
            failed_devices=40,
            cancelled_devices=10,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
            actual_start=actual_start,
            actual_end=None,
            timeout_minutes=120,
            auto_rollback=True,
            failure_threshold_percent=15,
            rollback_triggers=[RollbackTrigger.FAILURE_RATE],
            requires_approval=True,
            approved=True,
            approved_by="approver_001",
            approval_comment="Approved for deployment",
            created_at=now,
            updated_at=now,
            created_by="creator_001",
        )

        assert response.campaign_id == "camp_12345"
        assert response.name == "Production Rollout Q1"
        assert response.status == UpdateStatus.IN_PROGRESS
        assert response.deployment_strategy == DeploymentStrategy.STAGED
        assert response.priority == Priority.HIGH
        assert response.target_device_count == 1000
        assert response.total_devices == 1000
        assert response.completed_devices == 600
        assert response.failed_devices == 40
        assert response.approved is True
        assert response.approved_by == "approver_001"

    def test_update_campaign_response_progress_calculation(self):
        """Test campaign response with progress tracking"""
        now = datetime.now(timezone.utc)

        firmware = FirmwareResponse(
            firmware_id="fw_progress",
            name="Test",
            version="1.0",
            description=None,
            device_model="Model",
            manufacturer="Mfr",
            min_hardware_version=None,
            max_hardware_version=None,
            file_size=1000000,
            file_url="https://example.com/fw.bin",
            checksum_md5="a" * 32,
            checksum_sha256="b" * 64,
            tags=[],
            metadata={},
            is_beta=False,
            is_security_update=False,
            changelog=None,
            created_at=now,
            updated_at=now,
            created_by="admin",
        )

        response = UpdateCampaignResponse(
            campaign_id="camp_progress",
            name="Progress Test",
            description=None,
            firmware=firmware,
            status=UpdateStatus.IN_PROGRESS,
            deployment_strategy=DeploymentStrategy.IMMEDIATE,
            priority=Priority.NORMAL,
            target_device_count=100,
            targeted_devices=[],
            targeted_groups=[],
            rollout_percentage=100,
            max_concurrent_updates=10,
            batch_size=50,
            total_devices=100,
            pending_devices=20,
            in_progress_devices=10,
            completed_devices=65,
            failed_devices=5,
            cancelled_devices=0,
            scheduled_start=None,
            scheduled_end=None,
            actual_start=now,
            actual_end=None,
            timeout_minutes=60,
            auto_rollback=False,
            failure_threshold_percent=20,
            rollback_triggers=[],
            created_at=now,
            updated_at=now,
            created_by="admin",
        )

        # Verify progress numbers add up
        total_accounted = (
            response.pending_devices
            + response.in_progress_devices
            + response.completed_devices
            + response.failed_devices
            + response.cancelled_devices
        )
        assert total_accounted == response.total_devices


class TestDeviceUpdateResponse:
    """Test DeviceUpdateResponse model"""

    def test_device_update_response_with_all_fields(self):
        """Test creating device update response with all fields"""
        now = datetime.now(timezone.utc)
        scheduled_at = now + timedelta(hours=1)
        started_at = now + timedelta(hours=1, minutes=5)
        timeout_at = now + timedelta(hours=2)

        firmware = FirmwareResponse(
            firmware_id="fw_001",
            name="Device Firmware",
            version="2.5.0",
            description="Update",
            device_model="Model X",
            manufacturer="TechCorp",
            min_hardware_version=None,
            max_hardware_version=None,
            file_size=8388608,
            file_url="https://example.com/fw.bin",
            checksum_md5="a" * 32,
            checksum_sha256="b" * 64,
            tags=[],
            metadata={},
            is_beta=False,
            is_security_update=False,
            changelog=None,
            created_at=now,
            updated_at=now,
            created_by="admin",
        )

        response = DeviceUpdateResponse(
            update_id="upd_12345",
            device_id="dev_67890",
            campaign_id="camp_001",
            firmware=firmware,
            status=UpdateStatus.DOWNLOADING,
            priority=Priority.HIGH,
            progress_percentage=45.5,
            current_phase="downloading",
            from_version="2.0.0",
            to_version="2.5.0",
            scheduled_at=scheduled_at,
            started_at=started_at,
            completed_at=None,
            timeout_at=timeout_at,
            error_code=None,
            error_message=None,
            retry_count=0,
            max_retries=3,
            download_size=8388608,
            download_progress=45.5,
            download_speed=1048576.0,  # 1MB/s
            signature_verified=None,
            checksum_verified=None,
            created_at=now,
            updated_at=now,
        )

        assert response.update_id == "upd_12345"
        assert response.device_id == "dev_67890"
        assert response.campaign_id == "camp_001"
        assert response.status == UpdateStatus.DOWNLOADING
        assert response.priority == Priority.HIGH
        assert response.progress_percentage == 45.5
        assert response.current_phase == "downloading"
        assert response.from_version == "2.0.0"
        assert response.to_version == "2.5.0"
        assert response.download_speed == 1048576.0

    def test_device_update_response_completed(self):
        """Test device update response for completed update"""
        now = datetime.now(timezone.utc)
        started_at = now - timedelta(minutes=30)
        completed_at = now

        firmware = FirmwareResponse(
            firmware_id="fw_complete",
            name="Firmware",
            version="3.0.0",
            description=None,
            device_model="Model",
            manufacturer="Mfr",
            min_hardware_version=None,
            max_hardware_version=None,
            file_size=5000000,
            file_url="https://example.com/fw.bin",
            checksum_md5="a" * 32,
            checksum_sha256="b" * 64,
            tags=[],
            metadata={},
            is_beta=False,
            is_security_update=False,
            changelog=None,
            created_at=now,
            updated_at=now,
            created_by="admin",
        )

        response = DeviceUpdateResponse(
            update_id="upd_complete",
            device_id="dev_001",
            campaign_id="camp_001",
            firmware=firmware,
            status=UpdateStatus.COMPLETED,
            priority=Priority.NORMAL,
            progress_percentage=100.0,
            current_phase="completed",
            from_version="2.5.0",
            to_version="3.0.0",
            scheduled_at=None,
            started_at=started_at,
            completed_at=completed_at,
            timeout_at=None,
            error_code=None,
            error_message=None,
            retry_count=0,
            max_retries=3,
            download_size=5000000,
            download_progress=100.0,
            download_speed=None,
            signature_verified=True,
            checksum_verified=True,
            created_at=now - timedelta(hours=1),
            updated_at=now,
        )

        assert response.status == UpdateStatus.COMPLETED
        assert response.progress_percentage == 100.0
        assert response.signature_verified is True
        assert response.checksum_verified is True
        assert response.completed_at is not None

    def test_device_update_response_failed_with_error(self):
        """Test device update response for failed update with error details"""
        now = datetime.now(timezone.utc)
        started_at = now - timedelta(minutes=15)

        firmware = FirmwareResponse(
            firmware_id="fw_fail",
            name="Failed Firmware",
            version="2.0.0",
            description=None,
            device_model="Model",
            manufacturer="Mfr",
            min_hardware_version=None,
            max_hardware_version=None,
            file_size=3000000,
            file_url="https://example.com/fw.bin",
            checksum_md5="a" * 32,
            checksum_sha256="b" * 64,
            tags=[],
            metadata={},
            is_beta=False,
            is_security_update=False,
            changelog=None,
            created_at=now,
            updated_at=now,
            created_by="admin",
        )

        response = DeviceUpdateResponse(
            update_id="upd_failed",
            device_id="dev_error",
            campaign_id="camp_001",
            firmware=firmware,
            status=UpdateStatus.FAILED,
            priority=Priority.NORMAL,
            progress_percentage=25.0,
            current_phase="downloading",
            from_version="1.5.0",
            to_version="2.0.0",
            scheduled_at=None,
            started_at=started_at,
            completed_at=None,
            timeout_at=None,
            error_code="ERR_CHECKSUM_MISMATCH",
            error_message="Downloaded file checksum verification failed",
            retry_count=3,
            max_retries=3,
            download_size=3000000,
            download_progress=25.0,
            download_speed=None,
            signature_verified=False,
            checksum_verified=False,
            created_at=now - timedelta(minutes=30),
            updated_at=now,
        )

        assert response.status == UpdateStatus.FAILED
        assert response.error_code == "ERR_CHECKSUM_MISMATCH"
        assert "checksum verification failed" in response.error_message
        assert response.retry_count == 3
        assert response.max_retries == 3
        assert response.checksum_verified is False


class TestUpdateStatsResponse:
    """Test UpdateStatsResponse model"""

    def test_update_stats_response_with_all_fields(self):
        """Test creating update stats response with comprehensive data"""
        response = UpdateStatsResponse(
            total_campaigns=150,
            active_campaigns=25,
            completed_campaigns=100,
            failed_campaigns=25,
            total_updates=5000,
            pending_updates=500,
            in_progress_updates=300,
            completed_updates=3800,
            failed_updates=400,
            success_rate=95.0,
            avg_update_time=45.5,
            total_data_transferred=524288000000,  # 500GB
            last_24h_updates=450,
            last_24h_failures=15,
            last_24h_data_transferred=52428800000,  # 50GB
            updates_by_device_type={
                "SmartCamera": 2000,
                "SmartHub": 1500,
                "SmartSensor": 1500,
            },
            updates_by_firmware_version={
                "1.0.0": 500,
                "2.0.0": 1800,
                "2.5.0": 2700,
            },
        )

        assert response.total_campaigns == 150
        assert response.active_campaigns == 25
        assert response.completed_campaigns == 100
        assert response.total_updates == 5000
        assert response.success_rate == 95.0
        assert response.avg_update_time == 45.5
        assert response.total_data_transferred == 524288000000
        assert response.last_24h_updates == 450
        assert len(response.updates_by_device_type) == 3
        assert len(response.updates_by_firmware_version) == 3

    def test_update_stats_response_empty_distribution(self):
        """Test update stats response with empty distribution data"""
        response = UpdateStatsResponse(
            total_campaigns=0,
            active_campaigns=0,
            completed_campaigns=0,
            failed_campaigns=0,
            total_updates=0,
            pending_updates=0,
            in_progress_updates=0,
            completed_updates=0,
            failed_updates=0,
            success_rate=0.0,
            avg_update_time=0.0,
            total_data_transferred=0,
            last_24h_updates=0,
            last_24h_failures=0,
            last_24h_data_transferred=0,
            updates_by_device_type={},
            updates_by_firmware_version={},
        )

        assert response.total_campaigns == 0
        assert response.success_rate == 0.0
        assert len(response.updates_by_device_type) == 0
        assert len(response.updates_by_firmware_version) == 0


class TestRollbackResponse:
    """Test RollbackResponse model"""

    def test_rollback_response_successful_device_rollback(self):
        """Test successful rollback response for a single device"""
        now = datetime.now(timezone.utc)
        started_at = now - timedelta(minutes=10)
        completed_at = now

        response = RollbackResponse(
            rollback_id="rb_12345",
            campaign_id="camp_001",
            device_id="dev_001",
            trigger=RollbackTrigger.MANUAL,
            reason="User requested rollback due to compatibility issues",
            from_version="2.5.0",
            to_version="2.0.0",
            status=UpdateStatus.COMPLETED,
            started_at=started_at,
            completed_at=completed_at,
            success=True,
            error_message=None,
        )

        assert response.rollback_id == "rb_12345"
        assert response.campaign_id == "camp_001"
        assert response.device_id == "dev_001"
        assert response.trigger == RollbackTrigger.MANUAL
        assert "compatibility issues" in response.reason
        assert response.from_version == "2.5.0"
        assert response.to_version == "2.0.0"
        assert response.status == UpdateStatus.COMPLETED
        assert response.success is True
        assert response.error_message is None

    def test_rollback_response_campaign_wide_rollback(self):
        """Test rollback response for entire campaign"""
        now = datetime.now(timezone.utc)
        started_at = now - timedelta(hours=2)
        completed_at = now

        response = RollbackResponse(
            rollback_id="rb_campaign_001",
            campaign_id="camp_failure",
            device_id=None,  # None indicates campaign-wide rollback
            trigger=RollbackTrigger.FAILURE_RATE,
            reason="Failure rate exceeded 20% threshold",
            from_version="3.0.0",
            to_version="2.5.0",
            status=UpdateStatus.COMPLETED,
            started_at=started_at,
            completed_at=completed_at,
            success=True,
            error_message=None,
        )

        assert response.rollback_id == "rb_campaign_001"
        assert response.device_id is None
        assert response.trigger == RollbackTrigger.FAILURE_RATE
        assert "exceeded 20% threshold" in response.reason
        assert response.success is True

    def test_rollback_response_failed_rollback(self):
        """Test rollback response for a failed rollback attempt"""
        now = datetime.now(timezone.utc)
        started_at = now - timedelta(minutes=30)

        response = RollbackResponse(
            rollback_id="rb_failed",
            campaign_id="camp_002",
            device_id="dev_error",
            trigger=RollbackTrigger.ERROR_THRESHOLD,
            reason="Error threshold exceeded",
            from_version="2.0.0",
            to_version="1.5.0",
            status=UpdateStatus.FAILED,
            started_at=started_at,
            completed_at=None,
            success=False,
            error_message="Device unreachable during rollback attempt",
        )

        assert response.rollback_id == "rb_failed"
        assert response.device_id == "dev_error"
        assert response.trigger == RollbackTrigger.ERROR_THRESHOLD
        assert response.status == UpdateStatus.FAILED
        assert response.success is False
        assert response.error_message == "Device unreachable during rollback attempt"
        assert response.completed_at is None

    def test_rollback_response_health_check_trigger(self):
        """Test rollback triggered by health check failure"""
        now = datetime.now(timezone.utc)
        started_at = now - timedelta(minutes=5)
        completed_at = now

        response = RollbackResponse(
            rollback_id="rb_health",
            campaign_id="camp_health",
            device_id="dev_health_001",
            trigger=RollbackTrigger.HEALTH_CHECK,
            reason="Post-update health check failed: service not responding",
            from_version="4.0.0",
            to_version="3.5.0",
            status=UpdateStatus.COMPLETED,
            started_at=started_at,
            completed_at=completed_at,
            success=True,
            error_message=None,
        )

        assert response.trigger == RollbackTrigger.HEALTH_CHECK
        assert "health check failed" in response.reason
        assert response.success is True

    def test_rollback_response_timeout_trigger(self):
        """Test rollback triggered by timeout"""
        now = datetime.now(timezone.utc)
        started_at = now - timedelta(hours=1)
        completed_at = now

        response = RollbackResponse(
            rollback_id="rb_timeout",
            campaign_id="camp_timeout",
            device_id="dev_timeout_001",
            trigger=RollbackTrigger.TIMEOUT,
            reason="Update operation exceeded timeout of 60 minutes",
            from_version="5.0.0",
            to_version="4.5.0",
            status=UpdateStatus.COMPLETED,
            started_at=started_at,
            completed_at=completed_at,
            success=True,
            error_message=None,
        )

        assert response.trigger == RollbackTrigger.TIMEOUT
        assert "exceeded timeout" in response.reason
        assert response.status == UpdateStatus.COMPLETED


if __name__ == "__main__":
    pytest.main([__file__])
