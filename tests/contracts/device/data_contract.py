"""
Device Service Data Contract

This module defines the complete data contract for device service operations,
including Pydantic schemas, validation rules, and test data factories.
All data structures are designed for zero-hardcoded-data testing.
"""

from pydantic import BaseModel, Field, validator, EmailStr
from typing import Optional, Dict, Any, List, Union, Literal
from datetime import datetime, timezone
from enum import Enum
import secrets
import hashlib
import json
import random
import string
import uuid

# Simple fake data generator to replace Faker dependency
class SimpleFaker:
    """Simple fake data generator using built-in Python modules"""

    def __init__(self):
        self._counter = 0

    def uuid4(self) -> str:
        """Generate a UUID4 string"""
        return str(uuid.uuid4())

    def company(self) -> str:
        """Generate a company name"""
        prefixes = ["Tech", "Smart", "Digital", "Cyber", "Neo", "Quantum", "Advanced"]
        suffixes = ["Corp", "Systems", "Devices", "Solutions", "Labs", "Industries"]
        return f"{random.choice(prefixes)}{random.choice(suffixes)}"

    def name(self) -> str:
        """Generate a person name"""
        first_names = ["John", "Jane", "Alex", "Sam", "Taylor", "Jordan", "Casey", "Morgan"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Garcia"]
        return f"{random.choice(first_names)} {random.choice(last_names)}"

    def word(self) -> str:
        """Generate a random word"""
        words = ["alpha", "beta", "gamma", "delta", "epsilon", "omega", "sigma", "theta"]
        return random.choice(words)

    def sentence(self, nb_words: int = 6) -> str:
        """Generate a sentence"""
        words = ["the", "quick", "brown", "fox", "jumps", "over", "lazy", "dog",
                 "device", "smart", "frame", "sensor", "data", "system"]
        return " ".join(random.choices(words, k=nb_words)).capitalize() + "."

    def text(self, max_nb_chars: int = 200) -> str:
        """Generate text"""
        sentences = [self.sentence() for _ in range(max_nb_chars // 30)]
        return " ".join(sentences)[:max_nb_chars]

    def city(self) -> str:
        """Generate a city name"""
        cities = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix",
                  "San Francisco", "Seattle", "Boston", "Denver", "Austin"]
        return random.choice(cities)

    def country(self) -> str:
        """Generate a country name"""
        countries = ["USA", "Canada", "UK", "Germany", "France", "Japan", "Australia"]
        return random.choice(countries)

    def address(self) -> str:
        """Generate an address"""
        return f"{random.randint(1, 9999)} {self.word().title()} Street"

    def latitude(self) -> float:
        """Generate a latitude"""
        return round(random.uniform(-90, 90), 6)

    def longitude(self) -> float:
        """Generate a longitude"""
        return round(random.uniform(-180, 180), 6)

    def ipv4(self) -> str:
        """Generate an IPv4 address"""
        return f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"

    def mac_address(self) -> str:
        """Generate a MAC address"""
        return ":".join([f"{random.randint(0, 255):02X}" for _ in range(6)])

    def user_name(self) -> str:
        """Generate a username"""
        return f"user_{secrets.token_hex(4)}"

    def email(self) -> str:
        """Generate an email address"""
        return f"{self.user_name()}@example.com"

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

    def timezone_name(self) -> str:
        """Generate a timezone name"""
        timezones = ["UTC", "America/New_York", "Europe/London", "Asia/Tokyo", "Australia/Sydney"]
        return random.choice(timezones)

    def hex(self, length: int = 8) -> str:
        """Generate a hex string"""
        return secrets.token_hex(length // 2)

    def alphanum(self, length: int = 8) -> str:
        """Generate an alphanumeric string"""
        return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))

    def words(self, nb: int = 3) -> List[str]:
        """Generate a list of random words"""
        word_list = ["alpha", "beta", "gamma", "delta", "epsilon", "omega", "sigma", "theta",
                     "smart", "device", "sensor", "frame", "camera", "home", "system"]
        return random.sample(word_list, min(nb, len(word_list)))

    def date_between(self, start_date: str = "-1y", end_date: str = "today") -> datetime:
        """Generate a date between two dates"""
        from datetime import timedelta
        now = datetime.now(timezone.utc)

        # Parse start_date
        if start_date == "today":
            start = now
        elif start_date.startswith("-"):
            # Parse relative date like "-2y", "-30d"
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

    def date_time_between(self, start_date: str = "-30d", end_date: str = "now") -> datetime:
        """Generate a datetime between two dates"""
        return self.date_between(start_date, end_date)

    def time_delta(self, days: int = 0, hours: int = 0, minutes: int = 0, seconds: int = 0) -> 'timedelta':
        """Generate a timedelta"""
        from datetime import timedelta
        return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)

    def timezone(self) -> str:
        """Generate a timezone name"""
        return self.timezone_name()


# Initialize fake data generator
fake = SimpleFaker()

# ==================
# Enums and Constants
# ==================

class DeviceType(str, Enum):
    """Device types supported by the platform"""
    SENSOR = "sensor"
    ACTUATOR = "actuator"
    GATEWAY = "gateway"
    SMART_HOME = "smart_home"
    INDUSTRIAL = "industrial"
    MEDICAL = "medical"
    AUTOMOTIVE = "automotive"
    WEARABLE = "wearable"
    CAMERA = "camera"
    CONTROLLER = "controller"
    SMART_FRAME = "smart_frame"

class DeviceStatus(str, Enum):
    """Device lifecycle status"""
    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    ERROR = "error"
    DECOMMISSIONED = "decommissioned"

class ConnectivityType(str, Enum):
    """Network connectivity types"""
    WIFI = "wifi"
    ETHERNET = "ethernet"
    CELLULAR_4G = "4g"
    CELLULAR_5G = "5g"
    BLUETOOTH = "bluetooth"
    ZIGBEE = "zigbee"
    LORA = "lora"
    NB_IOT = "nb-iot"
    MQTT = "mqtt"
    COAP = "coap"

class SecurityLevel(str, Enum):
    """Device security levels"""
    NONE = "none"
    BASIC = "basic"
    STANDARD = "standard"
    HIGH = "high"
    CRITICAL = "critical"

class FrameDisplayMode(str, Enum):
    """Smart frame display modes"""
    PHOTO_SLIDESHOW = "photo_slideshow"
    VIDEO_PLAYBACK = "video_playback"
    CLOCK_DISPLAY = "clock_display"
    WEATHER_INFO = "weather_info"
    CALENDAR_VIEW = "calendar_view"
    OFF = "off"

class FrameOrientation(str, Enum):
    """Smart frame orientation"""
    LANDSCAPE = "landscape"
    PORTRAIT = "portrait"
    AUTO = "auto"

class AuthType(str, Enum):
    """Device authentication types"""
    SECRET_KEY = "secret_key"
    CERTIFICATE = "certificate"
    TOKEN = "token"

class CommandStatus(str, Enum):
    """Command execution status"""
    PENDING = "pending"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    EXECUTED = "executed"
    FAILED = "failed"
    TIMEOUT = "timeout"

class PriorityLevel(int, Enum):
    """Command priority levels (1-10, higher is more important)"""
    LOWEST = 1
    LOW = 2
    BELOW_NORMAL = 3
    NORMAL = 4
    ABOVE_NORMAL = 5
    HIGH = 6
    HIGHER = 7
    HIGHEST = 8
    CRITICAL = 9
    EMERGENCY = 10

# ==================
# Request Schemas
# ==================

class DeviceRegistrationRequest(BaseModel):
    """Request schema for device registration"""
    device_name: str = Field(..., min_length=1, max_length=200, description="Device display name")
    device_type: DeviceType = Field(..., description="Type of device")
    manufacturer: str = Field(..., min_length=1, max_length=100, description="Device manufacturer")
    model: str = Field(..., min_length=1, max_length=100, description="Device model")
    serial_number: str = Field(..., min_length=1, max_length=100, description="Manufacturer serial number")
    firmware_version: str = Field(..., min_length=1, max_length=50, description="Current firmware version")
    hardware_version: Optional[str] = Field(None, max_length=50, description="Hardware revision")
    mac_address: Optional[str] = Field(None, description="MAC address")
    connectivity_type: ConnectivityType = Field(..., description="Primary connectivity method")
    security_level: SecurityLevel = Field(SecurityLevel.STANDARD, description="Device security level")
    location: Optional[Dict[str, Any]] = Field(None, description="Device location data")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional device metadata")
    group_id: Optional[str] = Field(None, description="Device group identifier")
    tags: List[str] = Field(default_factory=list, description="Device tags for categorization")

    @validator('serial_number')
    def validate_serial_number(cls, v):
        if not v or not v.strip():
            raise ValueError('Serial number cannot be empty')
        return v.strip().upper()

    @validator('mac_address')
    def validate_mac_address(cls, v):
        if v:
            # Remove common separators and convert to uppercase
            cleaned = v.upper().replace(":", "").replace("-", "").replace(".", "")
            # Should be exactly 12 hex characters
            if len(cleaned) != 12:
                raise ValueError('Invalid MAC address length')
            # Check all characters are hex
            if not all(c in '0123456789ABCDEF' for c in cleaned):
                raise ValueError('Invalid MAC address format')
            return v.upper()
        return v

class DeviceUpdateRequest(BaseModel):
    """Request schema for device updates"""
    device_name: Optional[str] = Field(None, min_length=1, max_length=200)
    status: Optional[DeviceStatus] = None
    firmware_version: Optional[str] = Field(None, min_length=1, max_length=50)
    hardware_version: Optional[str] = Field(None, max_length=50)
    mac_address: Optional[str] = Field(None)
    location: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    group_id: Optional[str] = None
    tags: Optional[List[str]] = None

class DeviceAuthRequest(BaseModel):
    """Request schema for device authentication"""
    device_id: str = Field(..., description="Device identifier")
    device_secret: str = Field(..., min_length=8, description="Device secret key")
    certificate: Optional[str] = Field(None, description="X.509 certificate for certificate-based auth")
    token: Optional[str] = Field(None, description="JWT or other token")
    auth_type: AuthType = Field(AuthType.SECRET_KEY, description="Authentication method")

class DeviceCommandRequest(BaseModel):
    """Request schema for device commands"""
    command: str = Field(..., min_length=1, max_length=100, description="Command name")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Command parameters")
    timeout: int = Field(30, ge=1, le=300, description="Command timeout in seconds")
    priority: PriorityLevel = Field(PriorityLevel.NORMAL, description="Command priority (1-10)")
    require_ack: bool = Field(True, description="Whether command acknowledgment is required")

class BulkCommandRequest(BaseModel):
    """Request schema for bulk device commands"""
    device_ids: List[str] = Field(..., min_items=1, description="Target device IDs")
    command_name: str = Field(..., min_length=1, max_length=100, alias="command", description="Command name")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Command parameters")
    timeout: int = Field(30, ge=1, le=300, description="Command timeout in seconds")
    priority: PriorityLevel = Field(PriorityLevel.NORMAL, description="Command priority")
    require_ack: bool = Field(True, description="Whether acknowledgment is required")

    class Config:
        allow_population_by_field_name = True

class DeviceGroupRequest(BaseModel):
    """Request schema for device group creation"""
    group_name: str = Field(..., min_length=1, max_length=100, description="Group display name")
    description: Optional[str] = Field(None, max_length=500, description="Group description")
    parent_group_id: Optional[str] = Field(None, description="Parent group ID for hierarchy")
    tags: List[str] = Field(default_factory=list, description="Group tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Group metadata")

class DevicePairingRequest(BaseModel):
    """Request schema for device pairing"""
    pairing_token: str = Field(..., min_length=8, description="Pairing token from QR code")
    user_id: str = Field(..., description="User attempting to pair")

class FrameRegistrationRequest(BaseModel):
    """Request schema for smart frame registration"""
    device_name: str = Field(..., min_length=1, max_length=200)
    manufacturer: str = Field("Generic", max_length=100)
    model: str = Field("SmartFrame", max_length=100)
    serial_number: str = Field(..., min_length=1, max_length=100)
    mac_address: str = Field(..., description="MAC address")
    screen_size: str = Field(..., description="Screen size (e.g., '10.1 inches')")
    resolution: str = Field(..., description="Screen resolution (e.g., '1920x1080')")
    supported_formats: List[str] = Field(default_factory=lambda: ["jpg", "png", "mp4"])
    connectivity_type: ConnectivityType = Field(ConnectivityType.WIFI)
    location: Optional[Dict[str, float]] = Field(None, description="GPS coordinates")
    organization_id: Optional[str] = Field(None)
    initial_config: Optional[Dict[str, Any]] = Field(None, description="Initial frame configuration")

class UpdateFrameConfigRequest(BaseModel):
    """Request schema for frame configuration updates"""
    brightness: Optional[int] = Field(None, ge=0, le=100)
    contrast: Optional[int] = Field(None, ge=0, le=200)
    auto_brightness: Optional[bool] = None
    slideshow_interval: Optional[int] = Field(None, ge=5, le=3600)
    display_mode: Optional[FrameDisplayMode] = None
    auto_sync_albums: Optional[List[str]] = None
    sleep_schedule: Optional[Dict[str, str]] = None
    orientation: Optional[FrameOrientation] = None

# ==================
# Response Schemas
# ==================

class DeviceResponse(BaseModel):
    """Response schema for device data"""
    device_id: str = Field(..., description="Unique device identifier")
    device_name: str = Field(..., description="Device display name")
    device_type: DeviceType = Field(..., description="Device type")
    manufacturer: str = Field(..., description="Device manufacturer")
    model: str = Field(..., description="Device model")
    serial_number: str = Field(..., description="Serial number")
    firmware_version: str = Field(..., description="Firmware version")
    hardware_version: Optional[str] = Field(None, description="Hardware version")
    mac_address: Optional[str] = Field(None, description="MAC address")
    connectivity_type: ConnectivityType = Field(..., description="Connectivity type")
    security_level: SecurityLevel = Field(..., description="Security level")
    status: DeviceStatus = Field(..., description="Device status")
    location: Optional[Dict[str, Any]] = Field(None, description="Location data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Device metadata")
    group_id: Optional[str] = Field(None, description="Device group ID")
    tags: List[str] = Field(default_factory=list, description="Device tags")
    last_seen: Optional[datetime] = Field(None, description="Last activity timestamp")
    registered_at: datetime = Field(..., description="Registration timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    user_id: str = Field(..., description="Device owner")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    total_commands: int = Field(default=0, description="Total commands sent")
    total_telemetry_points: int = Field(default=0, description="Total telemetry points")
    uptime_percentage: float = Field(default=0.0, description="Uptime percentage")

class DeviceAuthResponse(BaseModel):
    """Response schema for device authentication"""
    device_id: str = Field(..., description="Device identifier")
    access_token: str = Field(..., description="Access token for device")
    token_type: str = Field("Bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    refresh_token: Optional[str] = Field(None, description="Refresh token")
    scope: Optional[str] = Field(None, description="Token scope")
    mqtt_broker: Optional[str] = Field(None, description="MQTT broker address")
    mqtt_topic: Optional[str] = Field(None, description="MQTT topic prefix")

class DeviceGroupResponse(BaseModel):
    """Response schema for device group data"""
    group_id: str = Field(..., description="Group identifier")
    user_id: str = Field(..., description="Group owner")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    group_name: str = Field(..., description="Group display name")
    description: Optional[str] = Field(None, description="Group description")
    parent_group_id: Optional[str] = Field(None, description="Parent group ID")
    device_count: int = Field(default=0, description="Number of devices in group")
    tags: List[str] = Field(default_factory=list, description="Group tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Group metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

class DeviceStatsResponse(BaseModel):
    """Response schema for device statistics"""
    total_devices: int = Field(..., description="Total device count")
    active_devices: int = Field(..., description="Active device count")
    inactive_devices: int = Field(..., description="Inactive device count")
    error_devices: int = Field(..., description="Error device count")
    devices_by_type: Dict[str, int] = Field(..., description="Devices grouped by type")
    devices_by_status: Dict[str, int] = Field(..., description="Devices grouped by status")
    devices_by_connectivity: Dict[str, int] = Field(..., description="Devices grouped by connectivity")
    avg_uptime: float = Field(..., description="Average uptime percentage")
    total_data_points: int = Field(..., description="Total telemetry data points")
    last_24h_activity: Dict[str, Any] = Field(..., description="Last 24 hours activity summary")

class DeviceHealthResponse(BaseModel):
    """Response schema for device health"""
    device_id: str = Field(..., description="Device identifier")
    status: DeviceStatus = Field(..., description="Device status")
    health_score: float = Field(..., ge=0, le=100, description="Health score (0-100)")
    cpu_usage: Optional[float] = Field(None, ge=0, le=100, description="CPU usage percentage")
    memory_usage: Optional[float] = Field(None, ge=0, le=100, description="Memory usage percentage")
    disk_usage: Optional[float] = Field(None, ge=0, le=100, description="Disk usage percentage")
    temperature: Optional[float] = Field(None, description="Temperature in Celsius")
    battery_level: Optional[float] = Field(None, ge=0, le=100, description="Battery percentage")
    signal_strength: Optional[float] = Field(None, ge=0, le=100, description="Signal strength")
    error_count: int = Field(default=0, description="Error count")
    warning_count: int = Field(default=0, description="Warning count")
    last_error: Optional[str] = Field(None, description="Last error message")
    last_check: datetime = Field(..., description="Last health check timestamp")
    diagnostics: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic data")

class DeviceListResponse(BaseModel):
    """Response schema for device listings"""
    devices: List[DeviceResponse] = Field(..., description="Device list")
    count: int = Field(..., description="Total count")
    limit: int = Field(..., description="Query limit")
    offset: int = Field(..., description="Query offset")
    filters: Optional[Dict[str, Any]] = Field(None, description="Applied filters")

class FrameConfig(BaseModel):
    """Smart frame configuration"""
    device_id: str = Field(..., description="Device ID")
    brightness: int = Field(80, ge=0, le=100, description="Brightness (0-100)")
    contrast: int = Field(100, ge=0, le=200, description="Contrast (0-200)")
    auto_brightness: bool = Field(True, description="Auto brightness")
    orientation: FrameOrientation = Field(FrameOrientation.AUTO, description="Display orientation")
    slideshow_interval: int = Field(30, ge=5, le=3600, description="Slideshow interval (seconds)")
    slideshow_transition: str = Field("fade", description="Slideshow transition effect")
    shuffle_photos: bool = Field(True, description="Shuffle photo order")
    show_metadata: bool = Field(False, description="Show photo metadata")
    sleep_schedule: Dict[str, str] = Field(default_factory=lambda: {"start": "23:00", "end": "07:00"})
    auto_sleep: bool = Field(True, description="Auto sleep")
    motion_detection: bool = Field(True, description="Motion detection")
    auto_sync_albums: List[str] = Field(default_factory=list, description="Auto-sync album IDs")
    sync_frequency: str = Field("hourly", description="Sync frequency")
    wifi_only_sync: bool = Field(True, description="WiFi only sync")
    display_mode: FrameDisplayMode = Field(FrameDisplayMode.PHOTO_SLIDESHOW, description="Display mode")
    location: Optional[Dict[str, float]] = Field(None, description="Location coordinates")
    timezone: str = Field("UTC", description="Timezone")

class FrameStatus(BaseModel):
    """Smart frame status"""
    device_id: str
    is_online: bool
    current_mode: FrameDisplayMode
    brightness_level: int
    current_photo: Optional[str] = None
    slideshow_active: bool = False
    total_photos: int = 0
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    storage_used: Optional[float] = None
    storage_total: Optional[float] = None
    temperature: Optional[float] = None
    wifi_signal: Optional[int] = None
    last_sync_time: Optional[datetime] = None
    sync_status: str = "idle"
    pending_sync_items: int = 0
    ambient_light: Optional[float] = None
    motion_detected: bool = False
    last_seen: datetime
    uptime_seconds: int = 0

class FrameResponse(BaseModel):
    """Response schema for smart frame data"""
    device_id: str
    device_name: str
    status: DeviceStatus
    frame_status: FrameStatus
    config: FrameConfig
    is_family_shared: bool = False
    sharing_info: Optional[Dict[str, Any]] = None
    registered_at: datetime
    last_seen: datetime

class FrameListResponse(BaseModel):
    """Response schema for frame listings"""
    frames: List[FrameResponse] = Field(..., description="Frame list")
    count: int = Field(..., description="Total count")
    limit: int = Field(..., description="Query limit")
    offset: int = Field(..., description="Query offset")

class DevicePairingResponse(BaseModel):
    """Response schema for device pairing"""
    success: bool = Field(..., description="Pairing success status")
    device: Optional[Dict[str, Any]] = Field(None, description="Device data if successful")
    message: Optional[str] = Field(None, description="Success message")
    error: Optional[str] = Field(None, description="Error message if failed")

# ==================
# Internal Schemas
# ==================

class DeviceCommand(BaseModel):
    """Internal command representation"""
    command_id: str
    device_id: str
    user_id: str
    command: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    timeout: int = 30
    priority: PriorityLevel = PriorityLevel.NORMAL
    require_ack: bool = True
    status: CommandStatus = CommandStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sent_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

# ==================
# Data Factory
# ==================

class DeviceDataFactory:
    """Factory for generating device test data"""
    
    @staticmethod
    def create_device_registration_request(
        device_type: Optional[DeviceType] = None,
        user_id: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None,
        **extra_overrides
    ) -> DeviceRegistrationRequest:
        """Create a device registration request with realistic data"""

        # Merge overrides from both sources
        all_overrides = {}
        if overrides:
            all_overrides.update(overrides)
        all_overrides.update(extra_overrides)

        # Generate base data
        data = {
            "device_name": f"{fake.company()} {fake.word().capitalize()} {random.choice(['Sensor', 'Camera', 'Controller', 'Frame'])}",
            "device_type": device_type or random.choice(list(DeviceType)),
            "manufacturer": fake.company(),
            "model": f"{fake.word().upper()}-{random.randint(1000, 9999)}",
            "serial_number": f"{random.randint(10000000, 99999999)}",
            "firmware_version": f"{random.randint(1, 5)}.{random.randint(0, 99)}.{random.randint(0, 999)}",
            "hardware_version": f"HW{random.choice(['A', 'B', 'C'])}{random.randint(1, 3)}",
            "mac_address": ":".join([f"{random.randint(0, 255):02X}" for _ in range(6)]),
            "connectivity_type": random.choice(list(ConnectivityType)),
            "security_level": random.choice(list(SecurityLevel)),
            "location": {
                "latitude": float(fake.latitude()),
                "longitude": float(fake.longitude()),
                "address": fake.address(),
                "city": fake.city(),
                "country": fake.country()
            },
            "metadata": {
                "installation_date": fake.date_between(start_date="-2y", end_date="today").isoformat(),
                "warranty_expires": fake.date_between(start_date="today", end_date="+5y").isoformat(),
                "support_contact": fake.email(),
                "department": random.choice(["Engineering", "Operations", "Security", "Facilities"]),
                "cost_center": f"CC-{random.randint(1000, 9999)}"
            },
            "tags": fake.words(nb=random.randint(1, 4)),
            "group_id": secrets.token_hex(16) if random.random() > 0.7 else None
        }

        # Apply overrides
        data.update(all_overrides)

        return DeviceRegistrationRequest(**data)

    @staticmethod
    def create_device_response(
        device_id: Optional[str] = None,
        user_id: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None,
        **extra_overrides
    ) -> DeviceResponse:
        """Create a device response with realistic data"""

        # Merge overrides from both sources
        all_overrides = {}
        if overrides:
            all_overrides.update(overrides)
        all_overrides.update(extra_overrides)

        now = datetime.now(timezone.utc)
        reg_time = now - fake.time_delta(days=random.randint(1, 365))

        data = {
            "device_id": device_id or secrets.token_hex(16),
            "device_name": f"{fake.company()} {fake.word().capitalize()} {random.choice(['Sensor', 'Camera', 'Controller', 'Frame'])}",
            "device_type": random.choice(list(DeviceType)),
            "manufacturer": fake.company(),
            "model": f"{fake.word().upper()}-{random.randint(1000, 9999)}",
            "serial_number": f"{random.randint(10000000, 99999999)}",
            "firmware_version": f"{random.randint(1, 5)}.{random.randint(0, 99)}.{random.randint(0, 999)}",
            "hardware_version": f"HW{random.choice(['A', 'B', 'C'])}{random.randint(1, 3)}",
            "mac_address": ":".join([f"{random.randint(0, 255):02X}" for _ in range(6)]),
            "connectivity_type": random.choice(list(ConnectivityType)),
            "security_level": random.choice(list(SecurityLevel)),
            "status": random.choice(list(DeviceStatus)),
            "location": {
                "latitude": float(fake.latitude()),
                "longitude": float(fake.longitude()),
                "address": fake.address(),
                "city": fake.city(),
                "country": fake.country()
            },
            "metadata": {
                "installation_date": fake.date_between(start_date="-2y", end_date="today").isoformat(),
                "warranty_expires": fake.date_between(start_date="today", end_date="+5y").isoformat(),
                "support_contact": fake.email(),
                "department": random.choice(["Engineering", "Operations", "Security", "Facilities"]),
                "cost_center": f"CC-{random.randint(1000, 9999)}"
            },
            "group_id": secrets.token_hex(16) if random.random() > 0.7 else None,
            "tags": fake.words(nb=random.randint(1, 4)),
            "last_seen": now - fake.time_delta(minutes=random.randint(5, 1440)) if random.random() > 0.3 else None,
            "registered_at": reg_time,
            "updated_at": reg_time + fake.time_delta(days=random.randint(0, 30)),
            "user_id": user_id or f"user_{secrets.token_hex(8)}",
            "organization_id": f"org_{secrets.token_hex(8)}" if random.random() > 0.5 else None,
            "total_commands": random.randint(0, 10000),
            "total_telemetry_points": random.randint(0, 1000000),
            "uptime_percentage": round(random.uniform(85.0, 99.9), 2)
        }

        data.update(all_overrides)

        # Register device ownership for validation tests
        try:
            from tests.contracts.device.logic_contract import register_device_ownership
            register_device_ownership(data["device_id"], data["user_id"], data.get("organization_id"))
        except ImportError:
            pass  # Logic contract not available

        return DeviceResponse(**data)

    @staticmethod
    def create_device_auth_request(
        device_id: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None,
        **extra_overrides
    ) -> DeviceAuthRequest:
        """Create a device authentication request"""

        # Merge overrides from both sources
        all_overrides = {}
        if overrides:
            all_overrides.update(overrides)
        all_overrides.update(extra_overrides)

        # Get auth_type from overrides first, otherwise random
        auth_type = all_overrides.get("auth_type", random.choice(list(AuthType)))

        data = {
            "device_id": device_id or secrets.token_hex(16),
            "device_secret": secrets.token_urlsafe(32),
            "certificate": None,  # Will be generated if auth_type is certificate
            "token": None,  # Will be generated if auth_type is token
            "auth_type": auth_type
        }

        # Add certificate for certificate auth
        if auth_type == AuthType.CERTIFICATE:
            data["certificate"] = f"-----BEGIN CERTIFICATE-----\n{secrets.token_hex(64)}\n-----END CERTIFICATE-----"

        # Add token for token auth
        if auth_type == AuthType.TOKEN:
            data["token"] = f"Bearer {secrets.token_hex(32)}"

        data.update(all_overrides)
        return DeviceAuthRequest(**data)

    @staticmethod
    def create_device_auth_response(
        device_id: Optional[str] = None,
        **overrides
    ) -> DeviceAuthResponse:
        """Create a device authentication response"""
        
        data = {
            "device_id": device_id or secrets.token_hex(16),
            "access_token": f"eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.{secrets.token_hex(32)}.signature",
            "token_type": "Bearer",
            "expires_in": random.randint(3600, 86400),
            "refresh_token": secrets.token_urlsafe(32),
            "scope": "device:all",
            "mqtt_broker": "mqtt://localhost:1883",
            "mqtt_topic": f"devices/{device_id or secrets.token_hex(16)}/"
        }
        
        data.update(overrides)
        return DeviceAuthResponse(**data)

    @staticmethod
    def create_device_command_request(
        command_name: Optional[str] = None,
        **overrides
    ) -> DeviceCommandRequest:
        """Create a device command request"""
        
        commands = [
            "reboot", "shutdown", "update_firmware", "set_brightness",
            "capture_photo", "start_recording", "stop_recording",
            "activate_alarm", "deactivate_alarm", "sync_data",
            "clear_cache", "run_diagnostics", "calibrate_sensor"
        ]
        
        data = {
            "command": command_name or random.choice(commands),
            "parameters": {
                "param1": fake.word(),
                "param2": random.randint(1, 100),
                "param3": random.choice([True, False])
            } if random.random() > 0.3 else {},
            "timeout": random.randint(10, 300),
            "priority": random.choice(list(PriorityLevel)),
            "require_ack": random.choice([True, False])
        }
        
        data.update(overrides)
        return DeviceCommandRequest(**data)

    @staticmethod
    def create_bulk_command_request(
        device_count: int = 3,
        **overrides
    ) -> BulkCommandRequest:
        """Create a bulk command request"""
        
        device_ids = [secrets.token_hex(16) for _ in range(device_count)]
        
        data = {
            "device_ids": device_ids,
            "command": random.choice([
                "reboot", "update_firmware", "sync_data", 
                "clear_cache", "run_diagnostics"
            ]),
            "parameters": {
                "batch_id": secrets.token_hex(8),
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            "timeout": random.randint(30, 300),
            "priority": random.choice(list(PriorityLevel)),
            "require_ack": True
        }
        
        data.update(overrides)
        return BulkCommandRequest(**data)

    @staticmethod
    def create_device_group_request(
        user_id: Optional[str] = None,
        **overrides
    ) -> DeviceGroupRequest:
        """Create a device group request"""
        
        data = {
            "group_name": f"{fake.word().capitalize()} {random.choice(['Sensors', 'Cameras', 'Controllers', 'Frames'])}",
            "description": fake.sentence(),
            "parent_group_id": secrets.token_hex(16) if random.random() > 0.7 else None,
            "tags": fake.words(nb=random.randint(1, 3)),
            "metadata": {
                "department": random.choice(["Engineering", "Operations", "Security"]),
                "location": fake.city(),
                "created_by": user_id or f"user_{secrets.token_hex(8)}"
            }
        }
        
        data.update(overrides)
        return DeviceGroupRequest(**data)

    @staticmethod
    def create_device_group_response(
        group_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **overrides
    ) -> DeviceGroupResponse:
        """Create a device group response"""
        
        now = datetime.now(timezone.utc)
        created_time = now - fake.time_delta(days=random.randint(1, 180))
        
        data = {
            "group_id": group_id or secrets.token_hex(16),
            "user_id": user_id or f"user_{secrets.token_hex(8)}",
            "organization_id": f"org_{secrets.token_hex(8)}" if random.random() > 0.5 else None,
            "group_name": f"{fake.word().capitalize()} {random.choice(['Sensors', 'Cameras', 'Controllers', 'Frames'])}",
            "description": fake.sentence(),
            "parent_group_id": secrets.token_hex(16) if random.random() > 0.7 else None,
            "device_count": random.randint(0, 50),
            "tags": fake.words(nb=random.randint(1, 3)),
            "metadata": {
                "department": random.choice(["Engineering", "Operations", "Security"]),
                "location": fake.city(),
                "created_by": user_id or f"user_{secrets.token_hex(8)}"
            },
            "created_at": created_time,
            "updated_at": created_time + fake.time_delta(days=random.randint(0, 30))
        }
        
        data.update(overrides)
        return DeviceGroupResponse(**data)

    @staticmethod
    def create_device_stats_response(
        user_id: Optional[str] = None,
        **overrides
    ) -> DeviceStatsResponse:
        """Create device statistics response"""
        
        total_devices = random.randint(5, 100)
        active_devices = int(total_devices * random.uniform(0.6, 0.9))
        inactive_devices = int(total_devices * random.uniform(0.05, 0.2))
        error_devices = total_devices - active_devices - inactive_devices
        
        # Device type distribution
        device_types = [dt.value for dt in DeviceType]
        devices_by_type = {}
        remaining = total_devices
        for i, device_type in enumerate(device_types[:-1]):
            count = random.randint(0, remaining // 2)
            devices_by_type[device_type] = count
            remaining -= count
        devices_by_type[device_types[-1]] = remaining
        
        # Status distribution
        devices_by_status = {
            "active": active_devices,
            "inactive": inactive_devices,
            "error": error_devices,
            "pending": 0,
            "maintenance": 0,
            "decommissioned": 0
        }
        
        # Connectivity distribution
        connectivity_types = [ct.value for ct in ConnectivityType]
        devices_by_connectivity = {}
        remaining = total_devices
        for i, conn_type in enumerate(connectivity_types[:-1]):
            count = random.randint(0, remaining // 2)
            devices_by_connectivity[conn_type] = count
            remaining -= count
        devices_by_connectivity[connectivity_types[-1]] = remaining
        
        data = {
            "total_devices": total_devices,
            "active_devices": active_devices,
            "inactive_devices": inactive_devices,
            "error_devices": error_devices,
            "devices_by_type": devices_by_type,
            "devices_by_status": devices_by_status,
            "devices_by_connectivity": devices_by_connectivity,
            "avg_uptime": round(random.uniform(85.0, 99.5), 2),
            "total_data_points": random.randint(10000, 1000000),
            "last_24h_activity": {
                "commands_sent": random.randint(50, 500),
                "telemetry_received": random.randint(1000, 10000),
                "alerts_triggered": random.randint(0, 20),
                "firmware_updates": random.randint(0, 5)
            }
        }
        
        data.update(overrides)
        return DeviceStatsResponse(**data)

    @staticmethod
    def create_device_health_response(
        device_id: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None,
        **extra_overrides
    ) -> DeviceHealthResponse:
        """Create device health response"""

        # Merge overrides from both sources
        all_overrides = {}
        if overrides:
            all_overrides.update(overrides)
        all_overrides.update(extra_overrides)

        # Get status from overrides first, otherwise random
        status = all_overrides.get("status", random.choice([DeviceStatus.ACTIVE, DeviceStatus.INACTIVE, DeviceStatus.ERROR]))

        # Adjust health score based on status (matching test expectations)
        if status == DeviceStatus.ACTIVE:
            health_score = random.uniform(80, 100)  # Healthy: >= 80
        elif status == DeviceStatus.INACTIVE:
            health_score = random.uniform(60, 79.99)  # Warning: 60-79
        else:  # ERROR, MAINTENANCE, etc.
            health_score = random.uniform(0, 59.99)  # Critical: < 60

        data = {
            "device_id": device_id or secrets.token_hex(16),
            "status": status,
            "health_score": round(health_score, 2),
            "cpu_usage": round(random.uniform(0, 100), 2) if random.random() > 0.2 else None,
            "memory_usage": round(random.uniform(0, 100), 2) if random.random() > 0.2 else None,
            "disk_usage": round(random.uniform(0, 100), 2) if random.random() > 0.2 else None,
            "temperature": round(random.uniform(20, 80), 1) if random.random() > 0.3 else None,
            "battery_level": round(random.uniform(0, 100), 1) if random.random() > 0.4 else None,
            "signal_strength": round(random.uniform(0, 100), 1) if random.random() > 0.3 else None,
            "error_count": random.randint(0, 50),
            "warning_count": random.randint(0, 20),
            "last_error": fake.sentence() if random.random() > 0.7 else None,
            "last_check": datetime.now(timezone.utc) - fake.time_delta(minutes=random.randint(1, 60)),
            "diagnostics": {
                "last_reboot": fake.date_time_between(start_date="-30d", end_date="now").isoformat(),
                "uptime_hours": random.randint(1, 8760),  # Up to 1 year
                "firmware_version": f"{random.randint(1, 5)}.{random.randint(0, 99)}.{random.randint(0, 999)}",
                "hardware_revision": f"{random.choice(['A', 'B', 'C'])}{random.randint(1, 3)}"
            }
        }

        data.update(all_overrides)
        return DeviceHealthResponse(**data)

    @staticmethod
    def create_device_list_response(
        count: int = 10,
        user_id: Optional[str] = None,
        **overrides
    ) -> DeviceListResponse:
        """Create a device list response"""
        
        devices = [
            DeviceDataFactory.create_device_response(user_id=user_id)
            for _ in range(count)
        ]
        
        data = {
            "devices": devices,
            "count": len(devices),
            "limit": count,
            "offset": 0,
            "filters": {
                "status": random.choice([None, random.choice(list(DeviceStatus))]),
                "device_type": random.choice([None, random.choice(list(DeviceType))])
            }
        }
        
        data.update(overrides)
        return DeviceListResponse(**data)

class FrameDataFactory:
    """Factory for generating smart frame test data"""
    
    @staticmethod
    def create_frame_registration_request(
        user_id: Optional[str] = None,
        **overrides
    ) -> FrameRegistrationRequest:
        """Create a frame registration request"""
        
        data = {
            "device_name": f"{fake.word().capitalize()} Smart Frame",
            "manufacturer": fake.company(),
            "model": f"SF-{random.randint(1000, 9999)}",
            "serial_number": f"SF{random.randint(100000, 999999)}",
            "mac_address": ":".join([f"{random.randint(0, 255):02X}" for _ in range(6)]),
            "screen_size": f"{random.choice([8, 10, 12, 15])}.{random.choice([0, 1, 5, 9])} inches",
            "resolution": random.choice(["1920x1080", "2560x1440", "3840x2160", "1280x800"]),
            "supported_formats": random.sample(["jpg", "png", "mp4", "avi", "mov"], random.randint(2, 4)),
            "connectivity_type": ConnectivityType.WIFI,
            "location": {
                "latitude": float(fake.latitude()),
                "longitude": float(fake.longitude())
            } if random.random() > 0.5 else None,
            "organization_id": f"org_{secrets.token_hex(8)}" if random.random() > 0.7 else None,
            "initial_config": {
                "brightness": random.randint(40, 100),
                "auto_sync": random.choice([True, False]),
                "display_mode": random.choice([dm.value for dm in FrameDisplayMode])
            }
        }
        
        data.update(overrides)
        return FrameRegistrationRequest(**data)

    @staticmethod
    def create_frame_config(
        device_id: Optional[str] = None,
        **overrides
    ) -> FrameConfig:
        """Create a frame configuration"""
        
        data = {
            "device_id": device_id or secrets.token_hex(16),
            "brightness": random.randint(20, 100),
            "contrast": random.randint(50, 150),
            "auto_brightness": random.choice([True, False]),
            "orientation": random.choice(list(FrameOrientation)),
            "slideshow_interval": random.randint(10, 300),
            "slideshow_transition": random.choice(["fade", "slide", "zoom", "flip"]),
            "shuffle_photos": random.choice([True, False]),
            "show_metadata": random.choice([True, False]),
            "sleep_schedule": {
                "start": f"{random.randint(22, 23)}:{random.randint(0, 59):02d}",
                "end": f"{random.randint(6, 8)}:{random.randint(0, 59):02d}"
            },
            "auto_sleep": random.choice([True, False]),
            "motion_detection": random.choice([True, False]),
            "auto_sync_albums": [secrets.token_hex(8) for _ in range(random.randint(0, 3))],
            "sync_frequency": random.choice(["real-time", "hourly", "daily", "weekly"]),
            "wifi_only_sync": random.choice([True, False]),
            "display_mode": random.choice(list(FrameDisplayMode)),
            "location": {
                "latitude": float(fake.latitude()),
                "longitude": float(fake.longitude())
            } if random.random() > 0.6 else None,
            "timezone": fake.timezone()
        }
        
        data.update(overrides)
        return FrameConfig(**data)

    @staticmethod
    def create_frame_status(
        device_id: Optional[str] = None,
        **overrides
    ) -> FrameStatus:
        """Create a frame status"""
        
        now = datetime.now(timezone.utc)
        
        data = {
            "device_id": device_id or secrets.token_hex(16),
            "is_online": random.choice([True, False]),
            "current_mode": random.choice(list(FrameDisplayMode)),
            "brightness_level": random.randint(0, 100),
            "current_photo": f"photo_{secrets.token_hex(8)}" if random.random() > 0.3 else None,
            "slideshow_active": random.choice([True, False]),
            "total_photos": random.randint(0, 1000),
            "cpu_usage": round(random.uniform(5, 80), 2) if random.random() > 0.2 else None,
            "memory_usage": round(random.uniform(10, 90), 2) if random.random() > 0.2 else None,
            "storage_used": round(random.uniform(1, 50), 2) if random.random() > 0.3 else None,
            "storage_total": round(random.uniform(32, 256), 2) if random.random() > 0.3 else None,
            "temperature": round(random.uniform(25, 45), 1) if random.random() > 0.4 else None,
            "wifi_signal": random.randint(-90, -30) if random.random() > 0.3 else None,
            "last_sync_time": now - fake.time_delta(hours=random.randint(0, 72)) if random.random() > 0.4 else None,
            "sync_status": random.choice(["idle", "syncing", "error", "paused"]),
            "pending_sync_items": random.randint(0, 100),
            "ambient_light": round(random.uniform(0, 1000), 2) if random.random() > 0.5 else None,
            "motion_detected": random.choice([True, False]),
            "last_seen": now - fake.time_delta(minutes=random.randint(1, 1440)),
            "uptime_seconds": random.randint(3600, 86400 * 30)  # Up to 30 days
        }
        
        data.update(overrides)
        return FrameStatus(**data)

    @staticmethod
    def create_frame_response(
        device_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **overrides
    ) -> FrameResponse:
        """Create a frame response"""
        
        now = datetime.now(timezone.utc)
        reg_time = now - fake.time_delta(days=random.randint(1, 365))
        
        data = {
            "device_id": device_id or secrets.token_hex(16),
            "device_name": f"{fake.word().capitalize()} Smart Frame",
            "status": random.choice([DeviceStatus.ACTIVE, DeviceStatus.INACTIVE, DeviceStatus.ERROR]),
            "frame_status": FrameDataFactory.create_frame_status(device_id=device_id),
            "config": FrameDataFactory.create_frame_config(device_id=device_id),
            "is_family_shared": random.choice([True, False]),
            "sharing_info": {
                "family_id": f"family_{secrets.token_hex(8)}",
                "shared_by": user_id or f"user_{secrets.token_hex(8)}",
                "shared_at": (now - fake.time_delta(days=random.randint(1, 30))).isoformat(),
                "permissions": ["view", "control"]
            } if random.random() > 0.6 else None,
            "registered_at": reg_time,
            "last_seen": now - fake.time_delta(minutes=random.randint(5, 1440))
        }
        
        data.update(overrides)
        return FrameResponse(**data)

class DeviceCommandFactory:
    """Factory for generating device command data"""
    
    @staticmethod
    def create_device_command(
        device_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **overrides
    ) -> DeviceCommand:
        """Create a device command"""
        
        now = datetime.now(timezone.utc)
        status = random.choice(list(CommandStatus))
        
        # Set timestamps based on status
        created_at = now - fake.time_delta(minutes=random.randint(1, 60))
        sent_at = None
        acknowledged_at = None
        completed_at = None
        
        if status in [CommandStatus.SENT, CommandStatus.ACKNOWLEDGED, CommandStatus.EXECUTED, CommandStatus.FAILED, CommandStatus.TIMEOUT]:
            sent_at = created_at + fake.time_delta(seconds=random.randint(1, 30))
        
        if status in [CommandStatus.ACKNOWLEDGED, CommandStatus.EXECUTED, CommandStatus.FAILED, CommandStatus.TIMEOUT]:
            acknowledged_at = sent_at + fake.time_delta(seconds=random.randint(1, 30))
        
        if status in [CommandStatus.EXECUTED, CommandStatus.FAILED, CommandStatus.TIMEOUT]:
            completed_at = acknowledged_at + fake.time_delta(seconds=random.randint(1, 120))
        
        data = {
            "command_id": secrets.token_hex(16),
            "device_id": device_id or secrets.token_hex(16),
            "user_id": user_id or f"user_{secrets.token_hex(8)}",
            "command": random.choice([
                "reboot", "shutdown", "update_firmware", "set_brightness",
                "capture_photo", "start_recording", "stop_recording",
                "activate_alarm", "deactivate_alarm", "sync_data",
                "clear_cache", "run_diagnostics", "calibrate_sensor"
            ]),
            "parameters": {
                "param1": fake.word(),
                "param2": random.randint(1, 100),
                "param3": random.choice([True, False])
            } if random.random() > 0.3 else {},
            "timeout": random.randint(10, 300),
            "priority": random.choice(list(PriorityLevel)),
            "require_ack": random.choice([True, False]),
            "status": status,
            "created_at": created_at,
            "sent_at": sent_at,
            "acknowledged_at": acknowledged_at,
            "completed_at": completed_at,
            "result": {
                "success": True,
                "message": "Command executed successfully",
                "data": {"timestamp": datetime.now(timezone.utc).isoformat()}
            } if status == CommandStatus.EXECUTED else None,
            "error_message": fake.sentence() if status in [CommandStatus.FAILED, CommandStatus.TIMEOUT] else None
        }
        
        data.update(overrides)
        return DeviceCommand(**data)

# ==================
# Request Builders
# ==================

class DeviceRequestBuilder:
    """Builder pattern for constructing device requests"""
    
    def __init__(self):
        self._data = {}
    
    def with_name(self, name: str) -> 'DeviceRequestBuilder':
        self._data["device_name"] = name
        return self
    
    def with_type(self, device_type: DeviceType) -> 'DeviceRequestBuilder':
        self._data["device_type"] = device_type
        return self
    
    def with_manufacturer(self, manufacturer: str) -> 'DeviceRequestBuilder':
        self._data["manufacturer"] = manufacturer
        return self
    
    def with_model(self, model: str) -> 'DeviceRequestBuilder':
        self._data["model"] = model
        return self
    
    def with_serial(self, serial: str) -> 'DeviceRequestBuilder':
        self._data["serial_number"] = serial
        return self
    
    def with_firmware(self, version: str) -> 'DeviceRequestBuilder':
        self._data["firmware_version"] = version
        return self
    
    def with_connectivity(self, connectivity: ConnectivityType) -> 'DeviceRequestBuilder':
        self._data["connectivity_type"] = connectivity
        return self
    
    def with_security(self, security: SecurityLevel) -> 'DeviceRequestBuilder':
        self._data["security_level"] = security
        return self
    
    def with_location(self, latitude: float, longitude: float, address: str = None) -> 'DeviceRequestBuilder':
        location = {
            "latitude": latitude,
            "longitude": longitude
        }
        if address:
            location["address"] = address
        self._data["location"] = location
        return self
    
    def with_tags(self, tags: List[str]) -> 'DeviceRequestBuilder':
        self._data["tags"] = tags
        return self
    
    def with_metadata(self, metadata: Dict[str, Any]) -> 'DeviceRequestBuilder':
        self._data["metadata"] = metadata
        return self

    def with_status(self, status: DeviceStatus) -> 'DeviceRequestBuilder':
        self._data["status"] = status
        return self

    def build_registration(self) -> DeviceRegistrationRequest:
        return DeviceRegistrationRequest(**self._data)

    def build_update(self) -> DeviceUpdateRequest:
        return DeviceUpdateRequest(**self._data)

# ==================
# Validation Helpers
# ==================

class DeviceValidators:
    """Validation helpers for device data"""

    @staticmethod
    def validate_mac_address(mac: str) -> bool:
        """Validate MAC address format.

        Supported formats:
        - 00:1B:44:11:22:33 (colon-separated)
        - 00-1B-44-11-22-33 (dash-separated)
        - 001B.4411.2233 (Cisco format)
        - 001B44112233 (no separator)
        """
        import re
        if not mac:
            return True  # Optional field

        # Remove common separators and convert to uppercase
        cleaned = mac.upper().replace(":", "").replace("-", "").replace(".", "")

        # Should be exactly 12 hex characters
        if len(cleaned) != 12:
            return False

        # Check all characters are hex
        return bool(re.match(r"^[0-9A-F]{12}$", cleaned))

    @staticmethod
    def validate_device_id(device_id: str) -> bool:
        """Validate device ID format"""
        if not device_id or len(device_id) < 8:
            return False
        # Device ID should be alphanumeric (with dashes and underscores allowed)
        cleaned = device_id.replace("-", "").replace("_", "")
        return cleaned.isalnum() and " " not in device_id

    @staticmethod
    def validate_firmware_version(version: str) -> bool:
        """Validate firmware version format (semver: major.minor.patch)"""
        import re
        if not version:
            return False
        # Require exactly 3 numeric parts (major.minor.patch) with optional suffix
        pattern = r"^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)?$"
        return bool(re.match(pattern, version))
    
    @staticmethod
    def validate_location_data(location: Dict[str, Any]) -> bool:
        """Validate location data structure"""
        if not location:
            return True  # Optional field
        
        required_keys = ["latitude", "longitude"]
        for key in required_keys:
            if key not in location:
                return False
            if not isinstance(location[key], (int, float)):
                return False
        
        lat, lon = location["latitude"], location["longitude"]
        return -90 <= lat <= 90 and -180 <= lon <= 180

# ==================
# Export All
# ==================

__all__ = [
    # Enums
    'DeviceType', 'DeviceStatus', 'ConnectivityType', 'SecurityLevel',
    'FrameDisplayMode', 'FrameOrientation', 'AuthType', 'CommandStatus', 'PriorityLevel',
    
    # Request Schemas
    'DeviceRegistrationRequest', 'DeviceUpdateRequest', 'DeviceAuthRequest',
    'DeviceCommandRequest', 'BulkCommandRequest', 'DeviceGroupRequest',
    'DevicePairingRequest', 'FrameRegistrationRequest', 'UpdateFrameConfigRequest',
    
    # Response Schemas
    'DeviceResponse', 'DeviceAuthResponse', 'DeviceGroupResponse',
    'DeviceStatsResponse', 'DeviceHealthResponse', 'DeviceListResponse',
    'FrameConfig', 'FrameStatus', 'FrameResponse', 'FrameListResponse',
    'DevicePairingResponse',
    
    # Internal Schemas
    'DeviceCommand',
    
    # Factories
    'DeviceDataFactory', 'FrameDataFactory', 'DeviceCommandFactory',
    
    # Builders
    'DeviceRequestBuilder',
    
    # Validators
    'DeviceValidators'
]
