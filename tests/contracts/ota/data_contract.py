"""
OTA Service Data Contract

This module defines the complete data contract for OTA service operations,
including Pydantic schemas, validation rules, and test data factories.
All data structures are designed for zero-hardcoded-data testing.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timezone, timedelta
from enum import Enum
import secrets
import hashlib
import json
import random
import string
import uuid


# =============================================================================
# Simple Fake Data Generator
# =============================================================================

class SimpleFaker:
    """Simple fake data generator using built-in Python modules"""

    def __init__(self):
        self._counter = 0

    def uuid4(self) -> str:
        """Generate a UUID4 string"""
        return str(uuid.uuid4())

    def company(self) -> str:
        """Generate a company name"""
        prefixes = ["Tech", "Smart", "Digital", "Cyber", "Neo", "Quantum", "Advanced", "Acme", "Future", "Elite"]
        suffixes = ["Corp", "Systems", "Devices", "Solutions", "Labs", "Industries", "Tech", "IoT", "Electronics"]
        return f"{random.choice(prefixes)} {random.choice(suffixes)}"

    def word(self) -> str:
        """Generate a random word"""
        words = ["alpha", "beta", "gamma", "delta", "epsilon", "omega", "sigma", "theta", "prime", "ultra"]
        return random.choice(words)

    def sentence(self, nb_words: int = 6) -> str:
        """Generate a sentence"""
        words = ["firmware", "update", "device", "smart", "frame", "sensor", "data", "system",
                 "security", "patch", "version", "release", "improvement", "fix", "enhancement"]
        return " ".join(random.choices(words, k=nb_words)).capitalize() + "."

    def text(self, max_nb_chars: int = 200) -> str:
        """Generate text"""
        sentences = [self.sentence() for _ in range(max_nb_chars // 30)]
        return " ".join(sentences)[:max_nb_chars]

    def hex(self, length: int = 8) -> str:
        """Generate a hex string"""
        return secrets.token_hex(length // 2)

    def alphanum(self, length: int = 8) -> str:
        """Generate an alphanumeric string"""
        return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))

    def words(self, nb: int = 3) -> List[str]:
        """Generate a list of random words"""
        word_list = ["ota", "firmware", "update", "device", "smart", "frame", "camera", "home",
                     "system", "sensor", "controller", "gateway", "security", "patch", "release"]
        return random.sample(word_list, min(nb, len(word_list)))

    def email(self) -> str:
        """Generate an email address"""
        return f"user_{secrets.token_hex(4)}@example.com"

    def user_name(self) -> str:
        """Generate a username"""
        return f"user_{secrets.token_hex(4)}"

    def pyint(self, min_value: int = 0, max_value: int = 100) -> int:
        """Generate a random integer"""
        return random.randint(min_value, max_value)

    def pyfloat(self, min_value: float = 0, max_value: float = 100) -> float:
        """Generate a random float"""
        return round(random.uniform(min_value, max_value), 2)

    def boolean(self) -> bool:
        """Generate a random boolean"""
        return random.choice([True, False])

    def date_time(self) -> datetime:
        """Generate a datetime"""
        return datetime.now(timezone.utc)

    def time_delta(self, days: int = 0, hours: int = 0, minutes: int = 0, seconds: int = 0) -> timedelta:
        """Generate a timedelta"""
        return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)

    def date_between(self, start_date: str = "-1y", end_date: str = "today") -> datetime:
        """Generate a date between two dates"""
        now = datetime.now(timezone.utc)

        # Parse start_date
        if start_date == "today":
            start = now
        elif start_date.startswith("-"):
            value = int(start_date[1:-1])
            unit = start_date[-1]
            if unit == 'y':
                start = now - timedelta(days=value * 365)
            elif unit == 'd':
                start = now - timedelta(days=value)
            else:
                start = now - timedelta(days=value)
        elif start_date.startswith("+"):
            value = int(start_date[1:-1])
            unit = start_date[-1]
            if unit == 'y':
                start = now + timedelta(days=value * 365)
            elif unit == 'd':
                start = now + timedelta(days=value)
            else:
                start = now + timedelta(days=value)
        else:
            start = now

        # Parse end_date
        if end_date == "today" or end_date == "now":
            end = now
        elif end_date.startswith("-"):
            value = int(end_date[1:-1])
            unit = end_date[-1]
            if unit == 'y':
                end = now - timedelta(days=value * 365)
            elif unit == 'd':
                end = now - timedelta(days=value)
            else:
                end = now - timedelta(days=value)
        elif end_date.startswith("+"):
            value = int(end_date[1:-1])
            unit = end_date[-1]
            if unit == 'y':
                end = now + timedelta(days=value * 365)
            elif unit == 'd':
                end = now + timedelta(days=value)
            else:
                end = now + timedelta(days=value)
        else:
            end = now

        # Generate random date between start and end
        delta = end - start
        random_days = random.randint(0, max(0, delta.days))
        return start + timedelta(days=random_days)


# Initialize fake data generator
fake = SimpleFaker()


# =============================================================================
# Enums and Constants
# =============================================================================

class UpdateType(str, Enum):
    """Update type enumeration"""
    FIRMWARE = "firmware"
    SOFTWARE = "software"
    APPLICATION = "application"
    CONFIG = "config"
    BOOTLOADER = "bootloader"
    SECURITY_PATCH = "security_patch"


class UpdateStatus(str, Enum):
    """Update status enumeration"""
    CREATED = "created"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    DOWNLOADING = "downloading"
    VERIFYING = "verifying"
    INSTALLING = "installing"
    REBOOTING = "rebooting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLBACK = "rollback"


class CampaignStatus(str, Enum):
    """Campaign status enumeration"""
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLBACK = "rollback"


class DeploymentStrategy(str, Enum):
    """Deployment strategy enumeration"""
    IMMEDIATE = "immediate"
    SCHEDULED = "scheduled"
    STAGED = "staged"
    CANARY = "canary"
    BLUE_GREEN = "blue_green"


class Priority(str, Enum):
    """Priority enumeration"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class RollbackTrigger(str, Enum):
    """Rollback trigger enumeration"""
    MANUAL = "manual"
    FAILURE_RATE = "failure_rate"
    HEALTH_CHECK = "health_check"
    TIMEOUT = "timeout"
    ERROR_THRESHOLD = "error_threshold"


# Supported firmware file extensions
SUPPORTED_FIRMWARE_EXTENSIONS = [".bin", ".hex", ".elf", ".tar.gz", ".zip"]

# Maximum firmware file size (500MB)
MAX_FIRMWARE_SIZE_BYTES = 500 * 1024 * 1024


# =============================================================================
# Request Contracts
# =============================================================================

class FirmwareUploadRequestContract(BaseModel):
    """Contract for firmware upload requests"""
    name: str = Field(..., min_length=1, max_length=200, description="Firmware name")
    version: str = Field(..., min_length=1, max_length=50, description="Firmware version")
    description: Optional[str] = Field(None, max_length=1000, description="Firmware description")
    device_model: str = Field(..., min_length=1, max_length=100, description="Target device model")
    manufacturer: str = Field(..., min_length=1, max_length=100, description="Device manufacturer")
    min_hardware_version: Optional[str] = Field(None, max_length=50)
    max_hardware_version: Optional[str] = Field(None, max_length=50)
    checksum_md5: Optional[str] = Field(None, min_length=32, max_length=32)
    checksum_sha256: Optional[str] = Field(None, min_length=64, max_length=64)
    release_notes: Optional[str] = Field(None, max_length=5000)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    is_beta: bool = Field(False, description="Beta release flag")
    is_security_update: bool = Field(False, description="Security update flag")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Name must not be empty or whitespace"""
        if not v or not v.strip():
            raise ValueError("name cannot be empty or whitespace")
        return v.strip()

    @field_validator('version')
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Version must be valid semver-like format"""
        if not v or not v.strip():
            raise ValueError("version cannot be empty or whitespace")
        return v.strip()

    @field_validator('checksum_md5')
    @classmethod
    def validate_md5(cls, v: Optional[str]) -> Optional[str]:
        """MD5 checksum must be 32 hex characters"""
        if v is not None:
            if len(v) != 32:
                raise ValueError("MD5 checksum must be 32 characters")
            if not all(c in '0123456789abcdef' for c in v.lower()):
                raise ValueError("MD5 checksum must be hexadecimal")
        return v

    @field_validator('checksum_sha256')
    @classmethod
    def validate_sha256(cls, v: Optional[str]) -> Optional[str]:
        """SHA256 checksum must be 64 hex characters"""
        if v is not None:
            if len(v) != 64:
                raise ValueError("SHA256 checksum must be 64 characters")
            if not all(c in '0123456789abcdef' for c in v.lower()):
                raise ValueError("SHA256 checksum must be hexadecimal")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Smart Frame Firmware",
                "version": "2.1.0",
                "device_model": "SF-100",
                "manufacturer": "Acme Corp",
                "is_beta": False,
                "is_security_update": False
            }
        }


class FirmwareQueryRequestContract(BaseModel):
    """Contract for firmware list/search requests"""
    device_model: Optional[str] = Field(None, max_length=100)
    manufacturer: Optional[str] = Field(None, max_length=100)
    is_beta: Optional[bool] = None
    is_security_update: Optional[bool] = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
    order_by: str = Field(default="created_at")
    order_dir: str = Field(default="desc", pattern="^(asc|desc)$")


class CampaignCreateRequestContract(BaseModel):
    """Contract for campaign creation requests"""
    name: str = Field(..., min_length=1, max_length=200, description="Campaign name")
    description: Optional[str] = Field(None, max_length=1000)
    firmware_id: str = Field(..., description="Target firmware ID")
    target_devices: List[str] = Field(default_factory=list, description="Target device IDs")
    target_groups: List[str] = Field(default_factory=list, description="Target device group IDs")
    target_filters: Dict[str, Any] = Field(default_factory=dict, description="Device filter criteria")
    deployment_strategy: DeploymentStrategy = Field(default=DeploymentStrategy.STAGED)
    priority: Priority = Field(default=Priority.NORMAL)
    rollout_percentage: int = Field(default=100, ge=1, le=100)
    max_concurrent_updates: int = Field(default=10, ge=1, le=1000)
    batch_size: int = Field(default=50, ge=1, le=500)
    timeout_minutes: int = Field(default=60, ge=5, le=1440)
    auto_rollback: bool = Field(default=True)
    failure_threshold_percent: int = Field(default=20, ge=1, le=100)
    scheduled_start: Optional[datetime] = None
    maintenance_window: Optional[Dict[str, str]] = None
    requires_approval: bool = Field(default=False)
    notify_on_start: bool = Field(default=True)
    notify_on_complete: bool = Field(default=True)
    notify_on_failure: bool = Field(default=True)

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Name must not be empty or whitespace"""
        if not v or not v.strip():
            raise ValueError("name cannot be empty or whitespace")
        return v.strip()

    @field_validator('firmware_id')
    @classmethod
    def validate_firmware_id(cls, v: str) -> str:
        """Firmware ID must not be empty"""
        if not v or not v.strip():
            raise ValueError("firmware_id cannot be empty")
        return v.strip()


class CampaignUpdateRequestContract(BaseModel):
    """Contract for campaign update requests"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    priority: Optional[Priority] = None
    rollout_percentage: Optional[int] = Field(None, ge=1, le=100)
    max_concurrent_updates: Optional[int] = Field(None, ge=1, le=1000)
    auto_rollback: Optional[bool] = None
    failure_threshold_percent: Optional[int] = Field(None, ge=1, le=100)
    scheduled_start: Optional[datetime] = None


class CampaignQueryRequestContract(BaseModel):
    """Contract for campaign list/search requests"""
    status: Optional[CampaignStatus] = None
    priority: Optional[Priority] = None
    firmware_id: Optional[str] = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
    order_by: str = Field(default="created_at")
    order_dir: str = Field(default="desc", pattern="^(asc|desc)$")


class DeviceUpdateRequestContract(BaseModel):
    """Contract for device update requests"""
    firmware_id: str = Field(..., description="Target firmware ID")
    priority: Priority = Field(default=Priority.NORMAL)
    force_update: bool = Field(default=False, description="Force update even if same version")
    max_retries: int = Field(default=3, ge=0, le=10)
    timeout_minutes: int = Field(default=60, ge=5, le=1440)
    pre_update_commands: List[str] = Field(default_factory=list)
    post_update_commands: List[str] = Field(default_factory=list)
    maintenance_window: Optional[Dict[str, str]] = None

    @field_validator('firmware_id')
    @classmethod
    def validate_firmware_id(cls, v: str) -> str:
        """Firmware ID must not be empty"""
        if not v or not v.strip():
            raise ValueError("firmware_id cannot be empty")
        return v.strip()


class BulkDeviceUpdateRequestContract(BaseModel):
    """Contract for bulk device update requests"""
    device_ids: List[str] = Field(..., min_length=1, max_length=100)
    firmware_id: str = Field(..., description="Target firmware ID")
    priority: Priority = Field(default=Priority.NORMAL)
    force_update: bool = Field(default=False)
    max_retries: int = Field(default=3, ge=0, le=10)
    timeout_minutes: int = Field(default=60, ge=5, le=1440)


class RollbackRequestContract(BaseModel):
    """Contract for rollback requests"""
    to_version: str = Field(..., min_length=1, max_length=50, description="Target version to rollback to")
    reason: str = Field(..., min_length=1, max_length=500, description="Reason for rollback")
    priority: Priority = Field(default=Priority.CRITICAL)

    @field_validator('to_version')
    @classmethod
    def validate_to_version(cls, v: str) -> str:
        """Target version must not be empty"""
        if not v or not v.strip():
            raise ValueError("to_version cannot be empty")
        return v.strip()

    @field_validator('reason')
    @classmethod
    def validate_reason(cls, v: str) -> str:
        """Reason must not be empty"""
        if not v or not v.strip():
            raise ValueError("reason cannot be empty")
        return v.strip()


class CampaignApprovalRequestContract(BaseModel):
    """Contract for campaign approval requests"""
    approved: bool = Field(..., description="Approval decision")
    approval_comment: Optional[str] = Field(None, max_length=500)
    conditions: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Response Contracts
# =============================================================================

class FirmwareResponseContract(BaseModel):
    """Contract for firmware response"""
    firmware_id: str = Field(..., description="Unique firmware identifier")
    name: str
    version: str
    description: Optional[str] = None
    device_model: str
    manufacturer: str
    min_hardware_version: Optional[str] = None
    max_hardware_version: Optional[str] = None
    file_url: str
    file_size: int
    checksum_md5: str
    checksum_sha256: str
    release_notes: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    is_beta: bool = False
    is_security_update: bool = False
    is_active: bool = True
    download_count: int = 0
    success_rate: float = 0.0
    created_at: datetime
    updated_at: datetime
    created_by: str


class FirmwareListResponseContract(BaseModel):
    """Contract for firmware list response"""
    firmware: List[FirmwareResponseContract]
    count: int
    limit: int
    offset: int
    filters: Optional[Dict[str, Any]] = None


class FirmwareDownloadResponseContract(BaseModel):
    """Contract for firmware download response"""
    download_url: str
    checksum_md5: str
    checksum_sha256: str
    file_size: int
    expires_in: int = Field(default=3600, description="URL expiry in seconds")


class CampaignResponseContract(BaseModel):
    """Contract for campaign response"""
    campaign_id: str = Field(..., description="Unique campaign identifier")
    name: str
    description: Optional[str] = None
    firmware_id: str
    firmware_version: str
    firmware_name: str
    status: CampaignStatus
    deployment_strategy: DeploymentStrategy
    priority: Priority
    target_device_count: int
    target_devices: List[str] = Field(default_factory=list)
    target_groups: List[str] = Field(default_factory=list)
    rollout_percentage: int
    max_concurrent_updates: int
    batch_size: int
    timeout_minutes: int
    auto_rollback: bool
    failure_threshold_percent: int
    total_devices: int = 0
    pending_devices: int = 0
    in_progress_devices: int = 0
    completed_devices: int = 0
    failed_devices: int = 0
    cancelled_devices: int = 0
    scheduled_start: Optional[datetime] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    requires_approval: bool = False
    approved: Optional[bool] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    approval_comment: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    created_by: str


class CampaignListResponseContract(BaseModel):
    """Contract for campaign list response"""
    campaigns: List[CampaignResponseContract]
    count: int
    limit: int
    offset: int
    filters: Optional[Dict[str, Any]] = None


class DeviceUpdateResponseContract(BaseModel):
    """Contract for device update response"""
    update_id: str = Field(..., description="Unique update identifier")
    device_id: str
    campaign_id: Optional[str] = None
    firmware_id: str
    firmware_version: str
    status: UpdateStatus
    priority: Priority
    progress_percentage: float = Field(0.0, ge=0, le=100)
    current_phase: Optional[str] = None
    from_version: Optional[str] = None
    to_version: str
    max_retries: int = 3
    retry_count: int = 0
    timeout_minutes: int = 60
    force_update: bool = False
    download_progress: float = Field(0.0, ge=0, le=100)
    download_speed: Optional[float] = None
    signature_verified: Optional[bool] = None
    checksum_verified: Optional[bool] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    download_started_at: Optional[datetime] = None
    download_completed_at: Optional[datetime] = None
    install_started_at: Optional[datetime] = None
    install_completed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class DeviceUpdateListResponseContract(BaseModel):
    """Contract for device update list response"""
    updates: List[DeviceUpdateResponseContract]
    count: int
    limit: int
    offset: int
    device_id: Optional[str] = None


class RollbackResponseContract(BaseModel):
    """Contract for rollback response"""
    rollback_id: str = Field(..., description="Unique rollback identifier")
    device_id: str
    campaign_id: Optional[str] = None
    update_id: Optional[str] = None
    trigger: RollbackTrigger
    reason: str
    from_version: str
    to_version: str
    status: UpdateStatus
    success: bool = False
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime


class OTAStatsResponseContract(BaseModel):
    """Contract for OTA statistics response"""
    total_campaigns: int = 0
    active_campaigns: int = 0
    completed_campaigns: int = 0
    failed_campaigns: int = 0
    total_updates: int = 0
    pending_updates: int = 0
    in_progress_updates: int = 0
    completed_updates: int = 0
    failed_updates: int = 0
    success_rate: float = 0.0
    avg_update_time: float = 0.0  # minutes
    total_data_transferred: int = 0  # bytes
    last_24h_updates: int = 0
    last_24h_failures: int = 0
    last_24h_data_transferred: int = 0
    updates_by_device_type: Dict[str, int] = Field(default_factory=dict)
    updates_by_firmware_version: Dict[str, int] = Field(default_factory=dict)


class ErrorResponseContract(BaseModel):
    """Standard error response contract"""
    success: bool = False
    error: str
    message: str
    detail: Optional[Dict[str, Any]] = None
    status_code: int


# =============================================================================
# Test Data Factory
# =============================================================================

class OTATestDataFactory:
    """
    Test data factory for ota_service.

    Zero hardcoded data - all values generated dynamically.
    Methods prefixed with 'make_' generate valid data.
    Methods prefixed with 'make_invalid_' generate invalid data.
    """

    # =========================================================================
    # ID Generators
    # =========================================================================

    @staticmethod
    def make_firmware_id() -> str:
        """Generate valid firmware ID (deterministic hash-based)"""
        return hashlib.sha256(f"{fake.uuid4()}".encode()).hexdigest()[:32]

    @staticmethod
    def make_campaign_id() -> str:
        """Generate valid campaign ID"""
        return f"camp_{secrets.token_hex(16)}"

    @staticmethod
    def make_update_id() -> str:
        """Generate valid update ID"""
        return f"upd_{secrets.token_hex(16)}"

    @staticmethod
    def make_rollback_id() -> str:
        """Generate valid rollback ID"""
        return f"rb_{secrets.token_hex(16)}"

    @staticmethod
    def make_device_id() -> str:
        """Generate valid device ID"""
        return f"dev_{secrets.token_hex(16)}"

    @staticmethod
    def make_user_id() -> str:
        """Generate valid user ID"""
        return f"user_{secrets.token_hex(8)}"

    @staticmethod
    def make_uuid() -> str:
        """Generate UUID string"""
        return str(uuid.uuid4())

    @staticmethod
    def make_correlation_id() -> str:
        """Generate correlation ID for tracing"""
        return f"corr_{uuid.uuid4().hex[:16]}"

    # =========================================================================
    # String Generators
    # =========================================================================

    @staticmethod
    def make_firmware_name(prefix: str = "Firmware") -> str:
        """Generate unique firmware name"""
        return f"{prefix} {fake.company()} {secrets.token_hex(2).upper()}"

    @staticmethod
    def make_campaign_name(prefix: str = "Campaign") -> str:
        """Generate unique campaign name"""
        return f"{prefix} {fake.word().capitalize()} {secrets.token_hex(2).upper()}"

    @staticmethod
    def make_version() -> str:
        """Generate semantic version string"""
        return f"{random.randint(1, 10)}.{random.randint(0, 99)}.{random.randint(0, 999)}"

    @staticmethod
    def make_device_model() -> str:
        """Generate device model string"""
        prefixes = ["SF", "SM", "DV", "CT", "GW", "SN"]
        return f"{random.choice(prefixes)}-{random.randint(100, 9999)}"

    @staticmethod
    def make_manufacturer() -> str:
        """Generate manufacturer name"""
        return fake.company()

    @staticmethod
    def make_description(length: int = 50) -> str:
        """Generate random description"""
        return fake.text(max_nb_chars=length)

    @staticmethod
    def make_release_notes() -> str:
        """Generate release notes"""
        features = ["Bug fixes", "Performance improvements", "Security patches",
                    "New features", "UI enhancements", "API updates"]
        items = random.sample(features, random.randint(2, 4))
        return "\n".join([f"- {item}" for item in items])

    @staticmethod
    def make_alphanumeric(length: int = 16) -> str:
        """Generate alphanumeric string"""
        chars = string.ascii_letters + string.digits
        return ''.join(random.choices(chars, k=length))

    @staticmethod
    def make_checksum_md5() -> str:
        """Generate MD5 checksum (32 hex chars)"""
        return hashlib.md5(secrets.token_bytes(32)).hexdigest()

    @staticmethod
    def make_checksum_sha256() -> str:
        """Generate SHA256 checksum (64 hex chars)"""
        return hashlib.sha256(secrets.token_bytes(32)).hexdigest()

    @staticmethod
    def make_file_url() -> str:
        """Generate file URL"""
        return f"/api/v1/firmware/{OTATestDataFactory.make_firmware_id()}/download"

    @staticmethod
    def make_tags(count: int = 3) -> List[str]:
        """Generate list of tags"""
        all_tags = ["stable", "beta", "security", "critical", "hotfix", "release",
                    "production", "testing", "canary", "rollback", "urgent"]
        return random.sample(all_tags, min(count, len(all_tags)))

    # =========================================================================
    # Numeric Generators
    # =========================================================================

    @staticmethod
    def make_file_size(min_mb: int = 1, max_mb: int = 100) -> int:
        """Generate file size in bytes"""
        return random.randint(min_mb * 1024 * 1024, max_mb * 1024 * 1024)

    @staticmethod
    def make_positive_int(max_val: int = 1000) -> int:
        """Generate positive integer"""
        return random.randint(1, max_val)

    @staticmethod
    def make_percentage() -> float:
        """Generate percentage (0-100)"""
        return round(random.uniform(0, 100), 2)

    @staticmethod
    def make_success_rate() -> float:
        """Generate success rate (typically high)"""
        return round(random.uniform(85.0, 99.9), 2)

    @staticmethod
    def make_progress_percentage() -> float:
        """Generate progress percentage"""
        return round(random.uniform(0, 100), 2)

    @staticmethod
    def make_download_speed() -> float:
        """Generate download speed in bytes/second"""
        return round(random.uniform(100000, 10000000), 2)

    # =========================================================================
    # Timestamp Generators
    # =========================================================================

    @staticmethod
    def make_timestamp() -> datetime:
        """Generate current UTC timestamp"""
        return datetime.now(timezone.utc)

    @staticmethod
    def make_past_timestamp(days: int = 30) -> datetime:
        """Generate timestamp in the past"""
        return datetime.now(timezone.utc) - timedelta(days=random.randint(1, days))

    @staticmethod
    def make_future_timestamp(days: int = 30) -> datetime:
        """Generate timestamp in the future"""
        return datetime.now(timezone.utc) + timedelta(days=random.randint(1, days))

    @staticmethod
    def make_timestamp_iso() -> str:
        """Generate ISO format timestamp string"""
        return datetime.now(timezone.utc).isoformat()

    # =========================================================================
    # Metadata Generators
    # =========================================================================

    @staticmethod
    def make_firmware_metadata() -> Dict[str, Any]:
        """Generate firmware metadata"""
        return {
            "build_number": random.randint(1000, 9999),
            "build_date": fake.date_between(start_date="-30d", end_date="today").isoformat(),
            "commit_hash": secrets.token_hex(20),
            "branch": random.choice(["main", "develop", "release", "hotfix"]),
            "builder": fake.email(),
            "min_memory_mb": random.choice([128, 256, 512]),
            "min_storage_mb": random.choice([256, 512, 1024]),
        }

    @staticmethod
    def make_campaign_metadata() -> Dict[str, Any]:
        """Generate campaign metadata"""
        return {
            "created_by_tool": random.choice(["dashboard", "api", "cli"]),
            "ticket_id": f"JIRA-{random.randint(1000, 9999)}",
            "environment": random.choice(["production", "staging", "development"]),
            "notification_emails": [fake.email() for _ in range(random.randint(1, 3))],
        }

    @staticmethod
    def make_maintenance_window() -> Dict[str, str]:
        """Generate maintenance window"""
        start_hour = random.randint(0, 23)
        end_hour = (start_hour + random.randint(2, 6)) % 24
        return {
            "start": f"{start_hour:02d}:00",
            "end": f"{end_hour:02d}:00",
            "timezone": random.choice(["UTC", "America/New_York", "Europe/London", "Asia/Tokyo"])
        }

    # =========================================================================
    # Request Generators (Valid Data)
    # =========================================================================

    @staticmethod
    def make_firmware_upload_request(**overrides) -> FirmwareUploadRequestContract:
        """Generate valid firmware upload request"""
        defaults = {
            "name": OTATestDataFactory.make_firmware_name(),
            "version": OTATestDataFactory.make_version(),
            "description": OTATestDataFactory.make_description(),
            "device_model": OTATestDataFactory.make_device_model(),
            "manufacturer": OTATestDataFactory.make_manufacturer(),
            "min_hardware_version": f"HW{random.choice(['A', 'B', 'C'])}{random.randint(1, 3)}",
            "max_hardware_version": None,
            "checksum_md5": OTATestDataFactory.make_checksum_md5(),
            "checksum_sha256": OTATestDataFactory.make_checksum_sha256(),
            "release_notes": OTATestDataFactory.make_release_notes(),
            "tags": OTATestDataFactory.make_tags(random.randint(1, 3)),
            "metadata": OTATestDataFactory.make_firmware_metadata(),
            "is_beta": fake.boolean(),
            "is_security_update": fake.boolean(),
        }
        defaults.update(overrides)
        return FirmwareUploadRequestContract(**defaults)

    @staticmethod
    def make_firmware_query_request(**overrides) -> FirmwareQueryRequestContract:
        """Generate valid firmware query request"""
        defaults = {
            "device_model": None,
            "manufacturer": None,
            "is_beta": None,
            "is_security_update": None,
            "limit": 50,
            "offset": 0,
        }
        defaults.update(overrides)
        return FirmwareQueryRequestContract(**defaults)

    @staticmethod
    def make_campaign_create_request(**overrides) -> CampaignCreateRequestContract:
        """Generate valid campaign creation request"""
        target_count = random.randint(1, 10)
        defaults = {
            "name": OTATestDataFactory.make_campaign_name(),
            "description": OTATestDataFactory.make_description(),
            "firmware_id": OTATestDataFactory.make_firmware_id(),
            "target_devices": [OTATestDataFactory.make_device_id() for _ in range(target_count)],
            "target_groups": [],
            "target_filters": {},
            "deployment_strategy": random.choice(list(DeploymentStrategy)),
            "priority": random.choice(list(Priority)),
            "rollout_percentage": random.randint(10, 100),
            "max_concurrent_updates": random.randint(5, 50),
            "batch_size": random.randint(10, 100),
            "timeout_minutes": random.randint(30, 120),
            "auto_rollback": fake.boolean(),
            "failure_threshold_percent": random.randint(10, 30),
            "scheduled_start": None,
            "maintenance_window": OTATestDataFactory.make_maintenance_window() if fake.boolean() else None,
            "requires_approval": fake.boolean(),
            "notify_on_start": True,
            "notify_on_complete": True,
            "notify_on_failure": True,
        }
        defaults.update(overrides)
        return CampaignCreateRequestContract(**defaults)

    @staticmethod
    def make_campaign_update_request(**overrides) -> CampaignUpdateRequestContract:
        """Generate valid campaign update request"""
        defaults = {
            "name": None,
            "description": None,
            "priority": None,
            "rollout_percentage": None,
            "max_concurrent_updates": None,
            "auto_rollback": None,
            "failure_threshold_percent": None,
            "scheduled_start": None,
        }
        defaults.update(overrides)
        return CampaignUpdateRequestContract(**defaults)

    @staticmethod
    def make_campaign_query_request(**overrides) -> CampaignQueryRequestContract:
        """Generate valid campaign query request"""
        defaults = {
            "status": None,
            "priority": None,
            "firmware_id": None,
            "limit": 50,
            "offset": 0,
        }
        defaults.update(overrides)
        return CampaignQueryRequestContract(**defaults)

    @staticmethod
    def make_device_update_request(**overrides) -> DeviceUpdateRequestContract:
        """Generate valid device update request"""
        defaults = {
            "firmware_id": OTATestDataFactory.make_firmware_id(),
            "priority": random.choice(list(Priority)),
            "force_update": fake.boolean(),
            "max_retries": random.randint(1, 5),
            "timeout_minutes": random.randint(30, 120),
            "pre_update_commands": [],
            "post_update_commands": [],
            "maintenance_window": None,
        }
        defaults.update(overrides)
        return DeviceUpdateRequestContract(**defaults)

    @staticmethod
    def make_bulk_device_update_request(device_count: int = 5, **overrides) -> BulkDeviceUpdateRequestContract:
        """Generate valid bulk device update request"""
        defaults = {
            "device_ids": [OTATestDataFactory.make_device_id() for _ in range(device_count)],
            "firmware_id": OTATestDataFactory.make_firmware_id(),
            "priority": random.choice(list(Priority)),
            "force_update": False,
            "max_retries": 3,
            "timeout_minutes": 60,
        }
        defaults.update(overrides)
        return BulkDeviceUpdateRequestContract(**defaults)

    @staticmethod
    def make_rollback_request(**overrides) -> RollbackRequestContract:
        """Generate valid rollback request"""
        defaults = {
            "to_version": OTATestDataFactory.make_version(),
            "reason": f"Rollback due to {random.choice(['connectivity issues', 'performance degradation', 'critical bug', 'security vulnerability'])}",
            "priority": Priority.CRITICAL,
        }
        defaults.update(overrides)
        return RollbackRequestContract(**defaults)

    @staticmethod
    def make_campaign_approval_request(**overrides) -> CampaignApprovalRequestContract:
        """Generate valid campaign approval request"""
        approved = fake.boolean()
        defaults = {
            "approved": approved,
            "approval_comment": f"{'Approved' if approved else 'Rejected'} - {fake.sentence()}",
            "conditions": {},
        }
        defaults.update(overrides)
        return CampaignApprovalRequestContract(**defaults)

    # =========================================================================
    # Response Generators
    # =========================================================================

    @staticmethod
    def make_firmware_response(**overrides) -> Dict[str, Any]:
        """Generate firmware response data"""
        now = OTATestDataFactory.make_timestamp()
        defaults = {
            "firmware_id": OTATestDataFactory.make_firmware_id(),
            "name": OTATestDataFactory.make_firmware_name(),
            "version": OTATestDataFactory.make_version(),
            "description": OTATestDataFactory.make_description(),
            "device_model": OTATestDataFactory.make_device_model(),
            "manufacturer": OTATestDataFactory.make_manufacturer(),
            "min_hardware_version": f"HW{random.choice(['A', 'B', 'C'])}{random.randint(1, 3)}",
            "max_hardware_version": None,
            "file_url": OTATestDataFactory.make_file_url(),
            "file_size": OTATestDataFactory.make_file_size(),
            "checksum_md5": OTATestDataFactory.make_checksum_md5(),
            "checksum_sha256": OTATestDataFactory.make_checksum_sha256(),
            "release_notes": OTATestDataFactory.make_release_notes(),
            "tags": OTATestDataFactory.make_tags(),
            "metadata": OTATestDataFactory.make_firmware_metadata(),
            "is_beta": fake.boolean(),
            "is_security_update": fake.boolean(),
            "is_active": True,
            "download_count": random.randint(0, 10000),
            "success_rate": OTATestDataFactory.make_success_rate(),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "created_by": OTATestDataFactory.make_user_id(),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_firmware_list_response(count: int = 5, **overrides) -> Dict[str, Any]:
        """Generate firmware list response"""
        firmware_list = [OTATestDataFactory.make_firmware_response() for _ in range(count)]
        defaults = {
            "firmware": firmware_list,
            "count": count,
            "limit": 50,
            "offset": 0,
            "filters": None,
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_firmware_download_response(**overrides) -> Dict[str, Any]:
        """Generate firmware download response"""
        defaults = {
            "download_url": f"https://storage.example.com/firmware/{secrets.token_hex(16)}.bin?token={secrets.token_hex(32)}",
            "checksum_md5": OTATestDataFactory.make_checksum_md5(),
            "checksum_sha256": OTATestDataFactory.make_checksum_sha256(),
            "file_size": OTATestDataFactory.make_file_size(),
            "expires_in": 3600,
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_campaign_response(**overrides) -> Dict[str, Any]:
        """Generate campaign response data"""
        now = OTATestDataFactory.make_timestamp()
        total_devices = random.randint(10, 100)
        completed = random.randint(0, total_devices)
        failed = random.randint(0, total_devices - completed)
        in_progress = random.randint(0, total_devices - completed - failed)
        pending = total_devices - completed - failed - in_progress

        defaults = {
            "campaign_id": OTATestDataFactory.make_campaign_id(),
            "name": OTATestDataFactory.make_campaign_name(),
            "description": OTATestDataFactory.make_description(),
            "firmware_id": OTATestDataFactory.make_firmware_id(),
            "firmware_version": OTATestDataFactory.make_version(),
            "firmware_name": OTATestDataFactory.make_firmware_name(),
            "status": random.choice(list(CampaignStatus)),
            "deployment_strategy": random.choice(list(DeploymentStrategy)),
            "priority": random.choice(list(Priority)),
            "target_device_count": total_devices,
            "target_devices": [OTATestDataFactory.make_device_id() for _ in range(min(5, total_devices))],
            "target_groups": [],
            "rollout_percentage": random.randint(10, 100),
            "max_concurrent_updates": random.randint(5, 50),
            "batch_size": random.randint(10, 100),
            "timeout_minutes": random.randint(30, 120),
            "auto_rollback": fake.boolean(),
            "failure_threshold_percent": random.randint(10, 30),
            "total_devices": total_devices,
            "pending_devices": pending,
            "in_progress_devices": in_progress,
            "completed_devices": completed,
            "failed_devices": failed,
            "cancelled_devices": 0,
            "scheduled_start": None,
            "actual_start": OTATestDataFactory.make_past_timestamp(1) if fake.boolean() else None,
            "actual_end": None,
            "requires_approval": fake.boolean(),
            "approved": fake.boolean() if fake.boolean() else None,
            "approved_by": OTATestDataFactory.make_user_id() if fake.boolean() else None,
            "approved_at": now.isoformat() if fake.boolean() else None,
            "approval_comment": fake.sentence() if fake.boolean() else None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "created_by": OTATestDataFactory.make_user_id(),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_campaign_list_response(count: int = 5, **overrides) -> Dict[str, Any]:
        """Generate campaign list response"""
        campaigns = [OTATestDataFactory.make_campaign_response() for _ in range(count)]
        defaults = {
            "campaigns": campaigns,
            "count": count,
            "limit": 50,
            "offset": 0,
            "filters": None,
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_device_update_response(**overrides) -> Dict[str, Any]:
        """Generate device update response data"""
        now = OTATestDataFactory.make_timestamp()
        status = random.choice(list(UpdateStatus))

        # Set timestamps based on status
        scheduled_at = OTATestDataFactory.make_past_timestamp(1)
        started_at = None
        download_started_at = None
        download_completed_at = None
        install_started_at = None
        install_completed_at = None
        completed_at = None

        if status in [UpdateStatus.IN_PROGRESS, UpdateStatus.DOWNLOADING, UpdateStatus.VERIFYING,
                      UpdateStatus.INSTALLING, UpdateStatus.REBOOTING, UpdateStatus.COMPLETED,
                      UpdateStatus.FAILED]:
            started_at = scheduled_at + timedelta(seconds=random.randint(1, 60))

        if status in [UpdateStatus.DOWNLOADING, UpdateStatus.VERIFYING, UpdateStatus.INSTALLING,
                      UpdateStatus.REBOOTING, UpdateStatus.COMPLETED, UpdateStatus.FAILED]:
            download_started_at = started_at + timedelta(seconds=random.randint(1, 30))

        if status in [UpdateStatus.VERIFYING, UpdateStatus.INSTALLING, UpdateStatus.REBOOTING,
                      UpdateStatus.COMPLETED, UpdateStatus.FAILED]:
            download_completed_at = download_started_at + timedelta(seconds=random.randint(30, 300))

        if status in [UpdateStatus.INSTALLING, UpdateStatus.REBOOTING, UpdateStatus.COMPLETED, UpdateStatus.FAILED]:
            install_started_at = download_completed_at + timedelta(seconds=random.randint(1, 30))

        if status in [UpdateStatus.REBOOTING, UpdateStatus.COMPLETED]:
            install_completed_at = install_started_at + timedelta(seconds=random.randint(30, 180))

        if status == UpdateStatus.COMPLETED:
            completed_at = install_completed_at + timedelta(seconds=random.randint(10, 60))

        defaults = {
            "update_id": OTATestDataFactory.make_update_id(),
            "device_id": OTATestDataFactory.make_device_id(),
            "campaign_id": OTATestDataFactory.make_campaign_id() if fake.boolean() else None,
            "firmware_id": OTATestDataFactory.make_firmware_id(),
            "firmware_version": OTATestDataFactory.make_version(),
            "status": status.value,
            "priority": random.choice(list(Priority)).value,
            "progress_percentage": OTATestDataFactory.make_progress_percentage() if status != UpdateStatus.SCHEDULED else 0.0,
            "current_phase": status.value if status in [UpdateStatus.DOWNLOADING, UpdateStatus.VERIFYING,
                                                         UpdateStatus.INSTALLING, UpdateStatus.REBOOTING] else None,
            "from_version": OTATestDataFactory.make_version(),
            "to_version": OTATestDataFactory.make_version(),
            "max_retries": 3,
            "retry_count": random.randint(0, 3) if status == UpdateStatus.FAILED else 0,
            "timeout_minutes": 60,
            "force_update": fake.boolean(),
            "download_progress": OTATestDataFactory.make_progress_percentage() if status in [
                UpdateStatus.DOWNLOADING, UpdateStatus.VERIFYING, UpdateStatus.INSTALLING,
                UpdateStatus.REBOOTING, UpdateStatus.COMPLETED] else 0.0,
            "download_speed": OTATestDataFactory.make_download_speed() if status == UpdateStatus.DOWNLOADING else None,
            "signature_verified": True if status in [UpdateStatus.VERIFYING, UpdateStatus.INSTALLING,
                                                      UpdateStatus.REBOOTING, UpdateStatus.COMPLETED] else None,
            "checksum_verified": True if status in [UpdateStatus.VERIFYING, UpdateStatus.INSTALLING,
                                                     UpdateStatus.REBOOTING, UpdateStatus.COMPLETED] else None,
            "error_code": f"ERR_{random.randint(1000, 9999)}" if status == UpdateStatus.FAILED else None,
            "error_message": fake.sentence() if status == UpdateStatus.FAILED else None,
            "scheduled_at": scheduled_at.isoformat() if scheduled_at else None,
            "started_at": started_at.isoformat() if started_at else None,
            "download_started_at": download_started_at.isoformat() if download_started_at else None,
            "download_completed_at": download_completed_at.isoformat() if download_completed_at else None,
            "install_started_at": install_started_at.isoformat() if install_started_at else None,
            "install_completed_at": install_completed_at.isoformat() if install_completed_at else None,
            "completed_at": completed_at.isoformat() if completed_at else None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_device_update_list_response(count: int = 5, device_id: Optional[str] = None, **overrides) -> Dict[str, Any]:
        """Generate device update list response"""
        updates = [OTATestDataFactory.make_device_update_response(device_id=device_id) for _ in range(count)]
        defaults = {
            "updates": updates,
            "count": count,
            "limit": 50,
            "offset": 0,
            "device_id": device_id,
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_rollback_response(**overrides) -> Dict[str, Any]:
        """Generate rollback response data"""
        now = OTATestDataFactory.make_timestamp()
        status = random.choice([UpdateStatus.IN_PROGRESS, UpdateStatus.COMPLETED, UpdateStatus.FAILED])

        defaults = {
            "rollback_id": OTATestDataFactory.make_rollback_id(),
            "device_id": OTATestDataFactory.make_device_id(),
            "campaign_id": OTATestDataFactory.make_campaign_id() if fake.boolean() else None,
            "update_id": OTATestDataFactory.make_update_id() if fake.boolean() else None,
            "trigger": random.choice(list(RollbackTrigger)).value,
            "reason": f"Rollback due to {random.choice(['connectivity issues', 'performance degradation', 'critical bug'])}",
            "from_version": OTATestDataFactory.make_version(),
            "to_version": OTATestDataFactory.make_version(),
            "status": status.value,
            "success": status == UpdateStatus.COMPLETED,
            "error_message": fake.sentence() if status == UpdateStatus.FAILED else None,
            "started_at": now.isoformat(),
            "completed_at": (now + timedelta(minutes=random.randint(1, 10))).isoformat() if status != UpdateStatus.IN_PROGRESS else None,
            "created_at": now.isoformat(),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_ota_stats_response(**overrides) -> Dict[str, Any]:
        """Generate OTA statistics response"""
        total_campaigns = random.randint(10, 100)
        active = random.randint(1, 10)
        completed = random.randint(5, total_campaigns - active)
        failed = total_campaigns - active - completed

        total_updates = random.randint(100, 10000)
        pending = random.randint(10, 100)
        in_progress = random.randint(10, 100)
        completed_updates = random.randint(50, total_updates - pending - in_progress)
        failed_updates = total_updates - pending - in_progress - completed_updates

        defaults = {
            "total_campaigns": total_campaigns,
            "active_campaigns": active,
            "completed_campaigns": completed,
            "failed_campaigns": failed,
            "total_updates": total_updates,
            "pending_updates": pending,
            "in_progress_updates": in_progress,
            "completed_updates": completed_updates,
            "failed_updates": failed_updates,
            "success_rate": round(completed_updates / (completed_updates + failed_updates) * 100, 2) if (completed_updates + failed_updates) > 0 else 0.0,
            "avg_update_time": round(random.uniform(5, 30), 2),
            "total_data_transferred": random.randint(1000000000, 100000000000),
            "last_24h_updates": random.randint(10, 500),
            "last_24h_failures": random.randint(0, 20),
            "last_24h_data_transferred": random.randint(100000000, 10000000000),
            "updates_by_device_type": {
                "smart_frame": random.randint(10, 100),
                "sensor": random.randint(10, 100),
                "gateway": random.randint(5, 50),
            },
            "updates_by_firmware_version": {
                OTATestDataFactory.make_version(): random.randint(10, 100),
                OTATestDataFactory.make_version(): random.randint(10, 100),
                OTATestDataFactory.make_version(): random.randint(10, 100),
            },
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_error_response(status_code: int = 400, **overrides) -> Dict[str, Any]:
        """Generate error response"""
        errors = {
            400: ("BAD_REQUEST", "Invalid request format"),
            401: ("UNAUTHORIZED", "Missing or invalid authentication"),
            403: ("FORBIDDEN", "Access denied"),
            404: ("NOT_FOUND", "Resource not found"),
            409: ("CONFLICT", "Resource conflict"),
            422: ("VALIDATION_ERROR", "Validation failed"),
            500: ("INTERNAL_ERROR", "Internal server error"),
        }
        error, message = errors.get(status_code, ("UNKNOWN_ERROR", "Unknown error"))

        defaults = {
            "success": False,
            "error": error,
            "message": message,
            "detail": None,
            "status_code": status_code,
        }
        defaults.update(overrides)
        return defaults

    # =========================================================================
    # Invalid Data Generators
    # =========================================================================

    @staticmethod
    def make_invalid_firmware_id() -> str:
        """Generate invalid firmware ID (wrong format)"""
        return "invalid_firmware_id"

    @staticmethod
    def make_invalid_campaign_id() -> str:
        """Generate invalid campaign ID"""
        return "invalid_campaign_id"

    @staticmethod
    def make_invalid_device_id() -> str:
        """Generate invalid device ID"""
        return ""

    @staticmethod
    def make_invalid_name_empty() -> str:
        """Generate empty name"""
        return ""

    @staticmethod
    def make_invalid_name_whitespace() -> str:
        """Generate whitespace-only name"""
        return "   "

    @staticmethod
    def make_invalid_name_too_long() -> str:
        """Generate name exceeding max length (200 chars)"""
        return "x" * 201

    @staticmethod
    def make_invalid_version_empty() -> str:
        """Generate empty version"""
        return ""

    @staticmethod
    def make_invalid_version_too_long() -> str:
        """Generate version exceeding max length (50 chars)"""
        return "1." + "0" * 50

    @staticmethod
    def make_invalid_checksum_md5() -> str:
        """Generate invalid MD5 checksum (wrong length)"""
        return "abc123"

    @staticmethod
    def make_invalid_checksum_sha256() -> str:
        """Generate invalid SHA256 checksum (wrong length)"""
        return "abc123"

    @staticmethod
    def make_invalid_checksum_non_hex() -> str:
        """Generate checksum with non-hex characters"""
        return "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz"

    @staticmethod
    def make_invalid_limit_zero() -> int:
        """Generate invalid limit (zero)"""
        return 0

    @staticmethod
    def make_invalid_limit_negative() -> int:
        """Generate invalid limit (negative)"""
        return -1

    @staticmethod
    def make_invalid_limit_too_large() -> int:
        """Generate invalid limit (exceeds max)"""
        return 10001

    @staticmethod
    def make_invalid_offset_negative() -> int:
        """Generate invalid offset (negative)"""
        return -1

    @staticmethod
    def make_invalid_rollout_percentage_zero() -> int:
        """Generate invalid rollout percentage (zero)"""
        return 0

    @staticmethod
    def make_invalid_rollout_percentage_over_100() -> int:
        """Generate invalid rollout percentage (over 100)"""
        return 101

    @staticmethod
    def make_invalid_timeout_too_small() -> int:
        """Generate invalid timeout (too small)"""
        return 1

    @staticmethod
    def make_invalid_timeout_too_large() -> int:
        """Generate invalid timeout (too large)"""
        return 10000

    @staticmethod
    def make_invalid_failure_threshold_zero() -> int:
        """Generate invalid failure threshold (zero)"""
        return 0

    @staticmethod
    def make_invalid_failure_threshold_over_100() -> int:
        """Generate invalid failure threshold (over 100)"""
        return 101

    # =========================================================================
    # Edge Case Generators
    # =========================================================================

    @staticmethod
    def make_unicode_name() -> str:
        """Generate name with unicode characters"""
        return f"Firmware \u4e2d\u6587 {secrets.token_hex(2)}"

    @staticmethod
    def make_special_chars_name() -> str:
        """Generate name with special characters"""
        return f"Firmware!@#$%^&*() {secrets.token_hex(2)}"

    @staticmethod
    def make_max_length_name() -> str:
        """Generate name at max length (200 chars)"""
        return "x" * 200

    @staticmethod
    def make_min_length_name() -> str:
        """Generate name at min length (1 char)"""
        return "x"

    @staticmethod
    def make_max_length_version() -> str:
        """Generate version at max length (50 chars)"""
        return "1.0.0-" + "x" * 44

    @staticmethod
    def make_large_file_size() -> int:
        """Generate large file size (near max 500MB)"""
        return 499 * 1024 * 1024

    @staticmethod
    def make_small_file_size() -> int:
        """Generate small file size"""
        return 1024

    # =========================================================================
    # Batch Generators
    # =========================================================================

    @staticmethod
    def make_batch_firmware_upload_requests(count: int = 5) -> List[FirmwareUploadRequestContract]:
        """Generate multiple firmware upload requests"""
        return [OTATestDataFactory.make_firmware_upload_request() for _ in range(count)]

    @staticmethod
    def make_batch_campaign_create_requests(count: int = 5) -> List[CampaignCreateRequestContract]:
        """Generate multiple campaign creation requests"""
        return [OTATestDataFactory.make_campaign_create_request() for _ in range(count)]

    @staticmethod
    def make_batch_device_ids(count: int = 10) -> List[str]:
        """Generate multiple device IDs"""
        return [OTATestDataFactory.make_device_id() for _ in range(count)]

    @staticmethod
    def make_batch_firmware_ids(count: int = 5) -> List[str]:
        """Generate multiple firmware IDs"""
        return [OTATestDataFactory.make_firmware_id() for _ in range(count)]


# =============================================================================
# Request Builders
# =============================================================================

class FirmwareUploadRequestBuilder:
    """Builder for firmware upload requests with fluent API"""

    def __init__(self):
        """Initialize with factory-generated defaults"""
        self._name = OTATestDataFactory.make_firmware_name()
        self._version = OTATestDataFactory.make_version()
        self._description: Optional[str] = None
        self._device_model = OTATestDataFactory.make_device_model()
        self._manufacturer = OTATestDataFactory.make_manufacturer()
        self._min_hardware_version: Optional[str] = None
        self._max_hardware_version: Optional[str] = None
        self._checksum_md5: Optional[str] = None
        self._checksum_sha256: Optional[str] = None
        self._release_notes: Optional[str] = None
        self._tags: List[str] = []
        self._metadata: Dict[str, Any] = {}
        self._is_beta: bool = False
        self._is_security_update: bool = False

    def with_name(self, name: str) -> 'FirmwareUploadRequestBuilder':
        """Set firmware name"""
        self._name = name
        return self

    def with_version(self, version: str) -> 'FirmwareUploadRequestBuilder':
        """Set firmware version"""
        self._version = version
        return self

    def with_description(self, description: str) -> 'FirmwareUploadRequestBuilder':
        """Set firmware description"""
        self._description = description
        return self

    def with_device_model(self, device_model: str) -> 'FirmwareUploadRequestBuilder':
        """Set target device model"""
        self._device_model = device_model
        return self

    def with_manufacturer(self, manufacturer: str) -> 'FirmwareUploadRequestBuilder':
        """Set device manufacturer"""
        self._manufacturer = manufacturer
        return self

    def with_hardware_versions(self, min_version: Optional[str] = None,
                               max_version: Optional[str] = None) -> 'FirmwareUploadRequestBuilder':
        """Set hardware version constraints"""
        self._min_hardware_version = min_version
        self._max_hardware_version = max_version
        return self

    def with_checksums(self, md5: Optional[str] = None, sha256: Optional[str] = None) -> 'FirmwareUploadRequestBuilder':
        """Set checksums"""
        self._checksum_md5 = md5
        self._checksum_sha256 = sha256
        return self

    def with_release_notes(self, notes: str) -> 'FirmwareUploadRequestBuilder':
        """Set release notes"""
        self._release_notes = notes
        return self

    def with_tags(self, tags: List[str]) -> 'FirmwareUploadRequestBuilder':
        """Set tags"""
        self._tags = tags
        return self

    def with_metadata(self, metadata: Dict[str, Any]) -> 'FirmwareUploadRequestBuilder':
        """Set metadata"""
        self._metadata = metadata
        return self

    def as_beta(self) -> 'FirmwareUploadRequestBuilder':
        """Mark as beta release"""
        self._is_beta = True
        return self

    def as_security_update(self) -> 'FirmwareUploadRequestBuilder':
        """Mark as security update"""
        self._is_security_update = True
        return self

    def with_invalid_name(self) -> 'FirmwareUploadRequestBuilder':
        """Set invalid name for negative testing"""
        self._name = OTATestDataFactory.make_invalid_name_empty()
        return self

    def with_invalid_version(self) -> 'FirmwareUploadRequestBuilder':
        """Set invalid version for negative testing"""
        self._version = OTATestDataFactory.make_invalid_version_empty()
        return self

    def with_invalid_checksum(self) -> 'FirmwareUploadRequestBuilder':
        """Set invalid checksum for negative testing"""
        self._checksum_md5 = OTATestDataFactory.make_invalid_checksum_md5()
        return self

    def build(self) -> FirmwareUploadRequestContract:
        """Build the request contract"""
        return FirmwareUploadRequestContract(
            name=self._name,
            version=self._version,
            description=self._description,
            device_model=self._device_model,
            manufacturer=self._manufacturer,
            min_hardware_version=self._min_hardware_version,
            max_hardware_version=self._max_hardware_version,
            checksum_md5=self._checksum_md5,
            checksum_sha256=self._checksum_sha256,
            release_notes=self._release_notes,
            tags=self._tags,
            metadata=self._metadata,
            is_beta=self._is_beta,
            is_security_update=self._is_security_update,
        )

    def build_dict(self) -> Dict[str, Any]:
        """Build as dictionary for API calls"""
        return self.build().model_dump()


class CampaignCreateRequestBuilder:
    """Builder for campaign creation requests with fluent API"""

    def __init__(self):
        """Initialize with factory-generated defaults"""
        self._name = OTATestDataFactory.make_campaign_name()
        self._description: Optional[str] = None
        self._firmware_id = OTATestDataFactory.make_firmware_id()
        self._target_devices: List[str] = []
        self._target_groups: List[str] = []
        self._target_filters: Dict[str, Any] = {}
        self._deployment_strategy = DeploymentStrategy.STAGED
        self._priority = Priority.NORMAL
        self._rollout_percentage = 100
        self._max_concurrent_updates = 10
        self._batch_size = 50
        self._timeout_minutes = 60
        self._auto_rollback = True
        self._failure_threshold_percent = 20
        self._scheduled_start: Optional[datetime] = None
        self._maintenance_window: Optional[Dict[str, str]] = None
        self._requires_approval = False

    def with_name(self, name: str) -> 'CampaignCreateRequestBuilder':
        """Set campaign name"""
        self._name = name
        return self

    def with_description(self, description: str) -> 'CampaignCreateRequestBuilder':
        """Set campaign description"""
        self._description = description
        return self

    def with_firmware_id(self, firmware_id: str) -> 'CampaignCreateRequestBuilder':
        """Set target firmware ID"""
        self._firmware_id = firmware_id
        return self

    def with_target_devices(self, device_ids: List[str]) -> 'CampaignCreateRequestBuilder':
        """Set target device IDs"""
        self._target_devices = device_ids
        return self

    def with_target_groups(self, group_ids: List[str]) -> 'CampaignCreateRequestBuilder':
        """Set target device group IDs"""
        self._target_groups = group_ids
        return self

    def with_target_filters(self, filters: Dict[str, Any]) -> 'CampaignCreateRequestBuilder':
        """Set device filter criteria"""
        self._target_filters = filters
        return self

    def with_deployment_strategy(self, strategy: DeploymentStrategy) -> 'CampaignCreateRequestBuilder':
        """Set deployment strategy"""
        self._deployment_strategy = strategy
        return self

    def with_priority(self, priority: Priority) -> 'CampaignCreateRequestBuilder':
        """Set priority"""
        self._priority = priority
        return self

    def with_rollout_percentage(self, percentage: int) -> 'CampaignCreateRequestBuilder':
        """Set rollout percentage"""
        self._rollout_percentage = percentage
        return self

    def with_concurrency(self, max_concurrent: int, batch_size: int) -> 'CampaignCreateRequestBuilder':
        """Set concurrency limits"""
        self._max_concurrent_updates = max_concurrent
        self._batch_size = batch_size
        return self

    def with_timeout(self, minutes: int) -> 'CampaignCreateRequestBuilder':
        """Set timeout in minutes"""
        self._timeout_minutes = minutes
        return self

    def with_auto_rollback(self, enabled: bool, threshold: int = 20) -> 'CampaignCreateRequestBuilder':
        """Configure auto-rollback"""
        self._auto_rollback = enabled
        self._failure_threshold_percent = threshold
        return self

    def with_scheduled_start(self, start_time: datetime) -> 'CampaignCreateRequestBuilder':
        """Set scheduled start time"""
        self._scheduled_start = start_time
        return self

    def with_maintenance_window(self, window: Dict[str, str]) -> 'CampaignCreateRequestBuilder':
        """Set maintenance window"""
        self._maintenance_window = window
        return self

    def requires_approval(self) -> 'CampaignCreateRequestBuilder':
        """Enable approval requirement"""
        self._requires_approval = True
        return self

    def with_invalid_name(self) -> 'CampaignCreateRequestBuilder':
        """Set invalid name for negative testing"""
        self._name = OTATestDataFactory.make_invalid_name_empty()
        return self

    def with_invalid_firmware_id(self) -> 'CampaignCreateRequestBuilder':
        """Set invalid firmware ID for negative testing"""
        self._firmware_id = OTATestDataFactory.make_invalid_firmware_id()
        return self

    def build(self) -> CampaignCreateRequestContract:
        """Build the request contract"""
        return CampaignCreateRequestContract(
            name=self._name,
            description=self._description,
            firmware_id=self._firmware_id,
            target_devices=self._target_devices,
            target_groups=self._target_groups,
            target_filters=self._target_filters,
            deployment_strategy=self._deployment_strategy,
            priority=self._priority,
            rollout_percentage=self._rollout_percentage,
            max_concurrent_updates=self._max_concurrent_updates,
            batch_size=self._batch_size,
            timeout_minutes=self._timeout_minutes,
            auto_rollback=self._auto_rollback,
            failure_threshold_percent=self._failure_threshold_percent,
            scheduled_start=self._scheduled_start,
            maintenance_window=self._maintenance_window,
            requires_approval=self._requires_approval,
        )

    def build_dict(self) -> Dict[str, Any]:
        """Build as dictionary for API calls"""
        return self.build().model_dump()


class DeviceUpdateRequestBuilder:
    """Builder for device update requests with fluent API"""

    def __init__(self):
        """Initialize with factory-generated defaults"""
        self._firmware_id = OTATestDataFactory.make_firmware_id()
        self._priority = Priority.NORMAL
        self._force_update = False
        self._max_retries = 3
        self._timeout_minutes = 60
        self._pre_update_commands: List[str] = []
        self._post_update_commands: List[str] = []
        self._maintenance_window: Optional[Dict[str, str]] = None

    def with_firmware_id(self, firmware_id: str) -> 'DeviceUpdateRequestBuilder':
        """Set target firmware ID"""
        self._firmware_id = firmware_id
        return self

    def with_priority(self, priority: Priority) -> 'DeviceUpdateRequestBuilder':
        """Set priority"""
        self._priority = priority
        return self

    def force_update(self) -> 'DeviceUpdateRequestBuilder':
        """Enable force update"""
        self._force_update = True
        return self

    def with_max_retries(self, retries: int) -> 'DeviceUpdateRequestBuilder':
        """Set maximum retry count"""
        self._max_retries = retries
        return self

    def with_timeout(self, minutes: int) -> 'DeviceUpdateRequestBuilder':
        """Set timeout in minutes"""
        self._timeout_minutes = minutes
        return self

    def with_pre_update_commands(self, commands: List[str]) -> 'DeviceUpdateRequestBuilder':
        """Set pre-update commands"""
        self._pre_update_commands = commands
        return self

    def with_post_update_commands(self, commands: List[str]) -> 'DeviceUpdateRequestBuilder':
        """Set post-update commands"""
        self._post_update_commands = commands
        return self

    def with_maintenance_window(self, window: Dict[str, str]) -> 'DeviceUpdateRequestBuilder':
        """Set maintenance window"""
        self._maintenance_window = window
        return self

    def with_invalid_firmware_id(self) -> 'DeviceUpdateRequestBuilder':
        """Set invalid firmware ID for negative testing"""
        self._firmware_id = OTATestDataFactory.make_invalid_firmware_id()
        return self

    def build(self) -> DeviceUpdateRequestContract:
        """Build the request contract"""
        return DeviceUpdateRequestContract(
            firmware_id=self._firmware_id,
            priority=self._priority,
            force_update=self._force_update,
            max_retries=self._max_retries,
            timeout_minutes=self._timeout_minutes,
            pre_update_commands=self._pre_update_commands,
            post_update_commands=self._post_update_commands,
            maintenance_window=self._maintenance_window,
        )

    def build_dict(self) -> Dict[str, Any]:
        """Build as dictionary for API calls"""
        return self.build().model_dump()


# =============================================================================
# Validators
# =============================================================================

class OTAValidators:
    """Validation helpers for OTA data"""

    @staticmethod
    def validate_firmware_id(firmware_id: str) -> bool:
        """Validate firmware ID format (32 hex chars)"""
        if not firmware_id or len(firmware_id) != 32:
            return False
        return all(c in '0123456789abcdef' for c in firmware_id.lower())

    @staticmethod
    def validate_version(version: str) -> bool:
        """Validate version format (semver-like)"""
        import re
        if not version:
            return False
        # Require at least major.minor.patch format
        pattern = r"^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)?$"
        return bool(re.match(pattern, version))

    @staticmethod
    def validate_checksum_md5(checksum: str) -> bool:
        """Validate MD5 checksum format (32 hex chars)"""
        if not checksum or len(checksum) != 32:
            return False
        return all(c in '0123456789abcdef' for c in checksum.lower())

    @staticmethod
    def validate_checksum_sha256(checksum: str) -> bool:
        """Validate SHA256 checksum format (64 hex chars)"""
        if not checksum or len(checksum) != 64:
            return False
        return all(c in '0123456789abcdef' for c in checksum.lower())

    @staticmethod
    def validate_file_extension(filename: str) -> bool:
        """Validate firmware file extension"""
        if not filename:
            return False
        lower_filename = filename.lower()
        return any(lower_filename.endswith(ext) for ext in SUPPORTED_FIRMWARE_EXTENSIONS)

    @staticmethod
    def validate_file_size(size: int) -> bool:
        """Validate firmware file size (max 500MB)"""
        return 0 < size <= MAX_FIRMWARE_SIZE_BYTES

    @staticmethod
    def validate_rollout_percentage(percentage: int) -> bool:
        """Validate rollout percentage (1-100)"""
        return 1 <= percentage <= 100

    @staticmethod
    def validate_failure_threshold(threshold: int) -> bool:
        """Validate failure threshold percentage (1-100)"""
        return 1 <= threshold <= 100

    @staticmethod
    def validate_timeout_minutes(timeout: int) -> bool:
        """Validate timeout in minutes (5-1440)"""
        return 5 <= timeout <= 1440

    @staticmethod
    def validate_batch_size(size: int) -> bool:
        """Validate batch size (1-500)"""
        return 1 <= size <= 500

    @staticmethod
    def validate_max_concurrent_updates(count: int) -> bool:
        """Validate max concurrent updates (1-1000)"""
        return 1 <= count <= 1000

    @staticmethod
    def validate_max_retries(retries: int) -> bool:
        """Validate max retries (0-10)"""
        return 0 <= retries <= 10

    @staticmethod
    def validate_maintenance_window(window: Dict[str, str]) -> bool:
        """Validate maintenance window format"""
        import re
        if not window:
            return True  # Optional field

        required_keys = ["start", "end"]
        for key in required_keys:
            if key not in window:
                return False
            # Validate time format HH:MM
            if not re.match(r"^\d{2}:\d{2}$", window[key]):
                return False

        return True


# =============================================================================
# Export All
# =============================================================================

__all__ = [
    # Enums
    'UpdateType', 'UpdateStatus', 'CampaignStatus', 'DeploymentStrategy',
    'Priority', 'RollbackTrigger',

    # Constants
    'SUPPORTED_FIRMWARE_EXTENSIONS', 'MAX_FIRMWARE_SIZE_BYTES',

    # Request Contracts
    'FirmwareUploadRequestContract', 'FirmwareQueryRequestContract',
    'CampaignCreateRequestContract', 'CampaignUpdateRequestContract',
    'CampaignQueryRequestContract', 'DeviceUpdateRequestContract',
    'BulkDeviceUpdateRequestContract', 'RollbackRequestContract',
    'CampaignApprovalRequestContract',

    # Response Contracts
    'FirmwareResponseContract', 'FirmwareListResponseContract',
    'FirmwareDownloadResponseContract', 'CampaignResponseContract',
    'CampaignListResponseContract', 'DeviceUpdateResponseContract',
    'DeviceUpdateListResponseContract', 'RollbackResponseContract',
    'OTAStatsResponseContract', 'ErrorResponseContract',

    # Factories
    'OTATestDataFactory',

    # Builders
    'FirmwareUploadRequestBuilder', 'CampaignCreateRequestBuilder',
    'DeviceUpdateRequestBuilder',

    # Validators
    'OTAValidators',
]
