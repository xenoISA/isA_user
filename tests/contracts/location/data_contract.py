"""
Location Service - Data Contract

Pydantic schemas, test data factory, and request builders.
Zero hardcoded data - all test data generated through factory methods.

Service: location_service
Port: 8224
"""

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import random
import secrets
import string
import uuid

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# ENUMS
# =============================================================================


class LocationMethod(str, Enum):
    """Location acquisition method"""
    GPS = "gps"
    WIFI = "wifi"
    CELLULAR = "cellular"
    BLUETOOTH = "bluetooth"
    MANUAL = "manual"
    HYBRID = "hybrid"


class GeofenceShapeType(str, Enum):
    """Geofence shape types"""
    CIRCLE = "circle"
    POLYGON = "polygon"
    RECTANGLE = "rectangle"


class GeofenceTriggerType(str, Enum):
    """Geofence trigger types"""
    ENTER = "enter"
    EXIT = "exit"
    DWELL = "dwell"


class PlaceCategory(str, Enum):
    """Place category types"""
    HOME = "home"
    WORK = "work"
    SCHOOL = "school"
    FAVORITE = "favorite"
    CUSTOM = "custom"


class RouteStatus(str, Enum):
    """Route status types"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# =============================================================================
# REQUEST CONTRACTS
# =============================================================================


class LocationReportRequestContract(BaseModel):
    """Contract for location report requests"""
    device_id: str = Field(..., min_length=1, max_length=100, description="Device ID")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude (-90 to 90)")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude (-180 to 180)")
    altitude: Optional[float] = Field(None, description="Altitude in meters")
    accuracy: float = Field(..., gt=0, description="Accuracy in meters (must be > 0)")
    heading: Optional[float] = Field(None, ge=0, lt=360, description="Heading in degrees (0-360)")
    speed: Optional[float] = Field(None, ge=0, description="Speed in m/s")
    address: Optional[str] = Field(None, max_length=500, description="Street address")
    city: Optional[str] = Field(None, max_length=100, description="City name")
    state: Optional[str] = Field(None, max_length=100, description="State/province")
    country: Optional[str] = Field(None, max_length=100, description="Country")
    postal_code: Optional[str] = Field(None, max_length=20, description="Postal code")
    location_method: LocationMethod = Field(default=LocationMethod.GPS)
    battery_level: Optional[float] = Field(None, ge=0, le=100, description="Battery level 0-100")
    timestamp: Optional[datetime] = Field(None, description="Location timestamp")
    source: str = Field(default="device", max_length=50)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @field_validator('device_id')
    @classmethod
    def validate_device_id(cls, v: str) -> str:
        """Device ID must not be empty or whitespace"""
        if not v or not v.strip():
            raise ValueError("device_id cannot be empty or whitespace")
        return v.strip()

    @field_validator('metadata')
    @classmethod
    def validate_metadata(cls, v: Optional[Dict]) -> Dict:
        """Ensure metadata is a dict"""
        return v or {}


class LocationBatchRequestContract(BaseModel):
    """Contract for batch location report requests"""
    locations: List[LocationReportRequestContract] = Field(
        ..., min_length=1, max_length=1000, description="List of locations (1-1000)"
    )
    compression: Optional[str] = Field(None, description="Compression type: gzip, lz4")
    batch_id: Optional[str] = Field(None, description="Optional batch identifier")


class GeofenceCreateRequestContract(BaseModel):
    """Contract for geofence creation requests"""
    name: str = Field(..., min_length=1, max_length=200, description="Geofence name")
    description: Optional[str] = Field(None, max_length=1000, description="Description")
    shape_type: GeofenceShapeType = Field(..., description="Shape type")
    center_lat: float = Field(..., ge=-90, le=90, description="Center latitude")
    center_lon: float = Field(..., ge=-180, le=180, description="Center longitude")
    radius: Optional[float] = Field(None, gt=0, description="Radius in meters (for circle)")
    polygon_coordinates: Optional[List[Tuple[float, float]]] = Field(
        None, description="Polygon vertices [(lat, lon), ...]"
    )
    trigger_on_enter: bool = Field(default=True, description="Trigger on enter")
    trigger_on_exit: bool = Field(default=True, description="Trigger on exit")
    trigger_on_dwell: bool = Field(default=False, description="Trigger on dwell")
    dwell_time_seconds: Optional[int] = Field(None, ge=60, description="Dwell time (min 60s)")
    target_devices: List[str] = Field(default_factory=list, description="Target device IDs")
    target_groups: List[str] = Field(default_factory=list, description="Target group IDs")
    active_days: Optional[List[str]] = Field(None, description='["monday", "tuesday", ...]')
    active_hours: Optional[Dict[str, str]] = Field(None, description='{"start": "09:00", "end": "18:00"}')
    notification_channels: List[str] = Field(default_factory=list)
    notification_template: Optional[str] = Field(None)
    tags: List[str] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Name must not be empty or whitespace"""
        if not v or not v.strip():
            raise ValueError("name cannot be empty or whitespace")
        return v.strip()

    @field_validator('polygon_coordinates')
    @classmethod
    def validate_polygon(cls, v, info):
        """Polygon must have at least 3 coordinates"""
        if info.data.get('shape_type') == GeofenceShapeType.POLYGON:
            if not v or len(v) < 3:
                raise ValueError("Polygon must have at least 3 coordinates")
        return v


class GeofenceUpdateRequestContract(BaseModel):
    """Contract for geofence update requests"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    trigger_on_enter: Optional[bool] = None
    trigger_on_exit: Optional[bool] = None
    trigger_on_dwell: Optional[bool] = None
    dwell_time_seconds: Optional[int] = Field(None, ge=60)
    target_devices: Optional[List[str]] = None
    target_groups: Optional[List[str]] = None
    active_days: Optional[List[str]] = None
    active_hours: Optional[Dict[str, str]] = None
    notification_channels: Optional[List[str]] = None
    notification_template: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class PlaceCreateRequestContract(BaseModel):
    """Contract for place creation requests"""
    name: str = Field(..., min_length=1, max_length=200, description="Place name")
    category: PlaceCategory = Field(..., description="Place category")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude")
    address: Optional[str] = Field(None, max_length=500, description="Address")
    radius: float = Field(default=100.0, gt=0, le=1000, description="Recognition radius (meters)")
    icon: Optional[str] = Field(None, max_length=50, description="Icon identifier")
    color: Optional[str] = Field(None, max_length=20, description="Color code")
    tags: List[str] = Field(default_factory=list)

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Name must not be empty or whitespace"""
        if not v or not v.strip():
            raise ValueError("name cannot be empty or whitespace")
        return v.strip()


class PlaceUpdateRequestContract(BaseModel):
    """Contract for place update requests"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    category: Optional[PlaceCategory] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    address: Optional[str] = Field(None, max_length=500)
    radius: Optional[float] = Field(None, gt=0, le=1000)
    icon: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=20)
    tags: Optional[List[str]] = None


class NearbySearchRequestContract(BaseModel):
    """Contract for nearby device search requests"""
    latitude: float = Field(..., ge=-90, le=90, description="Search center latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Search center longitude")
    radius_meters: float = Field(..., gt=0, le=50000, description="Search radius (max 50km)")
    device_types: Optional[List[str]] = Field(None, description="Filter by device types")
    time_window_minutes: int = Field(default=30, ge=1, le=1440, description="Max age in minutes")
    limit: int = Field(default=50, ge=1, le=500, description="Max results")


class RadiusSearchRequestContract(BaseModel):
    """Contract for radius search requests"""
    center_lat: float = Field(..., ge=-90, le=90)
    center_lon: float = Field(..., ge=-180, le=180)
    radius_meters: float = Field(..., gt=0, le=100000, description="Max 100km")
    start_time: datetime = Field(..., description="Search start time")
    end_time: datetime = Field(..., description="Search end time")
    device_ids: Optional[List[str]] = Field(None, description="Filter by device IDs")
    limit: int = Field(default=100, ge=1, le=1000)


class PolygonSearchRequestContract(BaseModel):
    """Contract for polygon search requests"""
    polygon_coordinates: List[Tuple[float, float]] = Field(
        ..., min_length=3, description="Polygon vertices [(lat, lon), ...]"
    )
    start_time: datetime = Field(...)
    end_time: datetime = Field(...)
    device_ids: Optional[List[str]] = None
    limit: int = Field(default=100, ge=1, le=1000)


class DistanceRequestContract(BaseModel):
    """Contract for distance calculation requests"""
    from_lat: float = Field(..., ge=-90, le=90)
    from_lon: float = Field(..., ge=-180, le=180)
    to_lat: float = Field(..., ge=-90, le=90)
    to_lon: float = Field(..., ge=-180, le=180)


# =============================================================================
# RESPONSE CONTRACTS
# =============================================================================


class LocationResponseContract(BaseModel):
    """Location response contract"""
    location_id: str
    device_id: str
    user_id: str
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    accuracy: float
    heading: Optional[float] = None
    speed: Optional[float] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    location_method: str
    battery_level: Optional[float] = None
    source: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime
    created_at: datetime


class GeofenceResponseContract(BaseModel):
    """Geofence response contract"""
    geofence_id: str
    name: str
    description: Optional[str] = None
    user_id: str
    organization_id: Optional[str] = None
    shape_type: str
    center_lat: float
    center_lon: float
    radius: Optional[float] = None
    polygon_coordinates: Optional[List[Tuple[float, float]]] = None
    active: bool
    trigger_on_enter: bool
    trigger_on_exit: bool
    trigger_on_dwell: bool
    dwell_time_seconds: Optional[int] = None
    target_devices: List[str]
    target_groups: List[str]
    active_days: Optional[List[str]] = None
    active_hours: Optional[Dict[str, str]] = None
    notification_channels: List[str]
    notification_template: Optional[str] = None
    total_triggers: int
    last_triggered: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    tags: List[str]
    metadata: Dict[str, Any]


class PlaceResponseContract(BaseModel):
    """Place response contract"""
    place_id: str
    user_id: str
    name: str
    category: str
    latitude: float
    longitude: float
    address: Optional[str] = None
    radius: float
    icon: Optional[str] = None
    color: Optional[str] = None
    visit_count: int
    total_time_spent: int
    last_visit: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    tags: List[str]


class LocationOperationResultContract(BaseModel):
    """Location operation result contract"""
    success: bool
    location_id: Optional[str] = None
    geofence_id: Optional[str] = None
    place_id: Optional[str] = None
    route_id: Optional[str] = None
    operation: str
    message: str
    data: Optional[Dict[str, Any]] = None
    affected_count: int = 0


class DistanceResponseContract(BaseModel):
    """Distance calculation response contract"""
    from_lat: float
    from_lon: float
    to_lat: float
    to_lon: float
    distance_meters: float
    distance_km: float


class NearbyDeviceResponseContract(BaseModel):
    """Nearby device response contract"""
    device_id: str
    device_name: Optional[str] = None
    device_type: Optional[str] = None
    user_id: str
    latitude: float
    longitude: float
    timestamp: datetime
    accuracy: float
    distance: float  # Distance from search point in meters


class LocationListResponseContract(BaseModel):
    """Location list response contract"""
    locations: List[LocationResponseContract]
    count: int


class GeofenceListResponseContract(BaseModel):
    """Geofence list response contract"""
    geofences: List[GeofenceResponseContract]
    count: int


class PlaceListResponseContract(BaseModel):
    """Place list response contract"""
    places: List[PlaceResponseContract]
    count: int


class ErrorResponseContract(BaseModel):
    """Standard error response contract"""
    success: bool = False
    error: str
    message: str
    detail: Optional[Dict[str, Any]] = None
    status_code: int


# =============================================================================
# TEST DATA FACTORY - ZERO HARDCODED DATA
# =============================================================================


class LocationTestDataFactory:
    """
    Test data factory for location_service.

    Zero hardcoded data - all values generated dynamically.
    Methods prefixed with 'make_' generate valid data.
    Methods prefixed with 'make_invalid_' generate invalid data.
    """

    # =========================================================================
    # ID Generators
    # =========================================================================

    @staticmethod
    def make_location_id() -> str:
        """Generate valid location ID"""
        return f"loc_{uuid.uuid4().hex}"

    @staticmethod
    def make_geofence_id() -> str:
        """Generate valid geofence ID"""
        return f"geo_{uuid.uuid4().hex}"

    @staticmethod
    def make_place_id() -> str:
        """Generate valid place ID"""
        return f"plc_{uuid.uuid4().hex}"

    @staticmethod
    def make_route_id() -> str:
        """Generate valid route ID"""
        return f"route_{uuid.uuid4().hex}"

    @staticmethod
    def make_device_id() -> str:
        """Generate valid device ID"""
        return f"dev_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_user_id() -> str:
        """Generate valid user ID"""
        return f"usr_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_uuid() -> str:
        """Generate UUID string"""
        return str(uuid.uuid4())

    @staticmethod
    def make_correlation_id() -> str:
        """Generate correlation ID for tracing"""
        return f"corr_{uuid.uuid4().hex[:16]}"

    # =========================================================================
    # Geographic Coordinate Generators
    # =========================================================================

    @staticmethod
    def make_latitude() -> float:
        """Generate valid latitude (-90 to 90)"""
        return round(random.uniform(-90.0, 90.0), 6)

    @staticmethod
    def make_longitude() -> float:
        """Generate valid longitude (-180 to 180)"""
        return round(random.uniform(-180.0, 180.0), 6)

    @staticmethod
    def make_coordinates() -> Tuple[float, float]:
        """Generate valid (latitude, longitude) tuple"""
        return (LocationTestDataFactory.make_latitude(), LocationTestDataFactory.make_longitude())

    @staticmethod
    def make_san_francisco_coordinates() -> Tuple[float, float]:
        """Generate coordinates near San Francisco"""
        base_lat, base_lon = 37.7749, -122.4194
        lat = base_lat + random.uniform(-0.1, 0.1)
        lon = base_lon + random.uniform(-0.1, 0.1)
        return (round(lat, 6), round(lon, 6))

    @staticmethod
    def make_new_york_coordinates() -> Tuple[float, float]:
        """Generate coordinates near New York"""
        base_lat, base_lon = 40.7128, -74.0060
        lat = base_lat + random.uniform(-0.1, 0.1)
        lon = base_lon + random.uniform(-0.1, 0.1)
        return (round(lat, 6), round(lon, 6))

    @staticmethod
    def make_altitude() -> float:
        """Generate realistic altitude in meters"""
        return round(random.uniform(0, 3000), 1)

    @staticmethod
    def make_accuracy() -> float:
        """Generate valid accuracy in meters (positive)"""
        return round(random.uniform(1.0, 100.0), 1)

    @staticmethod
    def make_heading() -> float:
        """Generate valid heading (0-360 degrees)"""
        return round(random.uniform(0, 359.99), 1)

    @staticmethod
    def make_speed() -> float:
        """Generate valid speed in m/s"""
        return round(random.uniform(0, 30), 2)

    @staticmethod
    def make_battery_level() -> float:
        """Generate valid battery level (0-100)"""
        return round(random.uniform(0, 100), 1)

    @staticmethod
    def make_radius(min_val: float = 50, max_val: float = 5000) -> float:
        """Generate valid radius in meters"""
        return round(random.uniform(min_val, max_val), 1)

    @staticmethod
    def make_polygon_coordinates(num_points: int = 4) -> List[Tuple[float, float]]:
        """Generate valid polygon coordinates (minimum 3 points)"""
        base_lat, base_lon = LocationTestDataFactory.make_san_francisco_coordinates()
        points = []
        for i in range(num_points):
            angle = (2 * 3.14159 * i) / num_points
            lat = base_lat + 0.01 * (1 + random.uniform(-0.2, 0.2)) * (1 if angle < 3.14159 else -1)
            lon = base_lon + 0.01 * (1 + random.uniform(-0.2, 0.2)) * (1 if angle < 1.5708 or angle > 4.7124 else -1)
            points.append((round(lat, 6), round(lon, 6)))
        return points

    # =========================================================================
    # String Generators
    # =========================================================================

    @staticmethod
    def make_name(prefix: str = "Test") -> str:
        """Generate unique name"""
        return f"{prefix} {secrets.token_hex(4)}"

    @staticmethod
    def make_geofence_name() -> str:
        """Generate unique geofence name"""
        names = ["Home Zone", "Work Area", "School Perimeter", "Safety Zone", "Custom Area"]
        return f"{random.choice(names)} {secrets.token_hex(3)}"

    @staticmethod
    def make_place_name() -> str:
        """Generate unique place name"""
        return f"Place {secrets.token_hex(4)}"

    @staticmethod
    def make_description(length: int = 50) -> str:
        """Generate random description"""
        words = ["location", "tracking", "geofence", "area", "zone", "boundary", "perimeter"]
        return " ".join(random.choices(words, k=min(length // 8, 10)))

    @staticmethod
    def make_address() -> str:
        """Generate fake address"""
        num = random.randint(100, 9999)
        streets = ["Main St", "Oak Ave", "Park Blvd", "Market St", "Broadway"]
        return f"{num} {random.choice(streets)}"

    @staticmethod
    def make_city() -> str:
        """Generate city name"""
        cities = ["San Francisco", "New York", "Los Angeles", "Chicago", "Seattle"]
        return random.choice(cities)

    @staticmethod
    def make_state() -> str:
        """Generate state name"""
        states = ["CA", "NY", "WA", "TX", "IL"]
        return random.choice(states)

    @staticmethod
    def make_country() -> str:
        """Generate country name"""
        return "USA"

    @staticmethod
    def make_postal_code() -> str:
        """Generate postal code"""
        return f"{random.randint(10000, 99999)}"

    @staticmethod
    def make_alphanumeric(length: int = 16) -> str:
        """Generate alphanumeric string"""
        chars = string.ascii_letters + string.digits
        return ''.join(random.choices(chars, k=length))

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

    @staticmethod
    def make_time_range(hours: int = 24) -> Tuple[datetime, datetime]:
        """Generate start and end time range"""
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=hours)
        return (start, end)

    # =========================================================================
    # Numeric Generators
    # =========================================================================

    @staticmethod
    def make_positive_int(max_val: int = 1000) -> int:
        """Generate positive integer"""
        return random.randint(1, max_val)

    @staticmethod
    def make_dwell_time_seconds() -> int:
        """Generate valid dwell time (minimum 60 seconds)"""
        return random.randint(60, 3600)

    @staticmethod
    def make_time_window_minutes() -> int:
        """Generate valid time window (1-1440 minutes)"""
        return random.randint(1, 1440)

    @staticmethod
    def make_limit(default: int = 100, max_val: int = 1000) -> int:
        """Generate valid limit"""
        return random.randint(1, max_val)

    @staticmethod
    def make_offset() -> int:
        """Generate valid offset"""
        return random.randint(0, 100)

    # =========================================================================
    # Request Generators (Valid Data)
    # =========================================================================

    @staticmethod
    def make_location_report_request(**overrides) -> LocationReportRequestContract:
        """Generate valid location report request"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        defaults = {
            "device_id": LocationTestDataFactory.make_device_id(),
            "latitude": lat,
            "longitude": lon,
            "accuracy": LocationTestDataFactory.make_accuracy(),
            "altitude": LocationTestDataFactory.make_altitude(),
            "heading": LocationTestDataFactory.make_heading(),
            "speed": LocationTestDataFactory.make_speed(),
            "location_method": LocationMethod.GPS,
            "battery_level": LocationTestDataFactory.make_battery_level(),
            "source": "device",
            "metadata": {},
        }
        defaults.update(overrides)
        return LocationReportRequestContract(**defaults)

    @staticmethod
    def make_batch_location_request(count: int = 5, **overrides) -> LocationBatchRequestContract:
        """Generate valid batch location request"""
        device_id = overrides.pop("device_id", LocationTestDataFactory.make_device_id())
        locations = [
            LocationTestDataFactory.make_location_report_request(device_id=device_id)
            for _ in range(count)
        ]
        defaults = {
            "locations": locations,
            "batch_id": LocationTestDataFactory.make_uuid(),
        }
        defaults.update(overrides)
        return LocationBatchRequestContract(**defaults)

    @staticmethod
    def make_circle_geofence_request(**overrides) -> GeofenceCreateRequestContract:
        """Generate valid circle geofence creation request"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        defaults = {
            "name": LocationTestDataFactory.make_geofence_name(),
            "description": LocationTestDataFactory.make_description(),
            "shape_type": GeofenceShapeType.CIRCLE,
            "center_lat": lat,
            "center_lon": lon,
            "radius": LocationTestDataFactory.make_radius(100, 1000),
            "trigger_on_enter": True,
            "trigger_on_exit": True,
            "trigger_on_dwell": False,
            "target_devices": [],
            "target_groups": [],
            "tags": [],
            "metadata": {},
        }
        defaults.update(overrides)
        return GeofenceCreateRequestContract(**defaults)

    @staticmethod
    def make_polygon_geofence_request(**overrides) -> GeofenceCreateRequestContract:
        """Generate valid polygon geofence creation request"""
        coords = LocationTestDataFactory.make_polygon_coordinates(4)
        center_lat = sum(c[0] for c in coords) / len(coords)
        center_lon = sum(c[1] for c in coords) / len(coords)
        defaults = {
            "name": LocationTestDataFactory.make_geofence_name(),
            "description": LocationTestDataFactory.make_description(),
            "shape_type": GeofenceShapeType.POLYGON,
            "center_lat": center_lat,
            "center_lon": center_lon,
            "polygon_coordinates": coords,
            "trigger_on_enter": True,
            "trigger_on_exit": True,
            "target_devices": [],
            "tags": [],
            "metadata": {},
        }
        defaults.update(overrides)
        return GeofenceCreateRequestContract(**defaults)

    @staticmethod
    def make_geofence_update_request(**overrides) -> GeofenceUpdateRequestContract:
        """Generate valid geofence update request"""
        defaults = {
            "name": LocationTestDataFactory.make_geofence_name(),
        }
        defaults.update(overrides)
        return GeofenceUpdateRequestContract(**defaults)

    @staticmethod
    def make_place_request(**overrides) -> PlaceCreateRequestContract:
        """Generate valid place creation request"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        categories = [PlaceCategory.HOME, PlaceCategory.WORK, PlaceCategory.SCHOOL, PlaceCategory.FAVORITE]
        defaults = {
            "name": LocationTestDataFactory.make_place_name(),
            "category": random.choice(categories),
            "latitude": lat,
            "longitude": lon,
            "address": LocationTestDataFactory.make_address(),
            "radius": 100.0,
            "tags": [],
        }
        defaults.update(overrides)
        return PlaceCreateRequestContract(**defaults)

    @staticmethod
    def make_place_update_request(**overrides) -> PlaceUpdateRequestContract:
        """Generate valid place update request"""
        defaults = {
            "name": LocationTestDataFactory.make_place_name(),
        }
        defaults.update(overrides)
        return PlaceUpdateRequestContract(**defaults)

    @staticmethod
    def make_nearby_search_request(**overrides) -> NearbySearchRequestContract:
        """Generate valid nearby search request"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        defaults = {
            "latitude": lat,
            "longitude": lon,
            "radius_meters": 1000,
            "time_window_minutes": 30,
            "limit": 50,
        }
        defaults.update(overrides)
        return NearbySearchRequestContract(**defaults)

    @staticmethod
    def make_radius_search_request(**overrides) -> RadiusSearchRequestContract:
        """Generate valid radius search request"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        start, end = LocationTestDataFactory.make_time_range(24)
        defaults = {
            "center_lat": lat,
            "center_lon": lon,
            "radius_meters": 5000,
            "start_time": start,
            "end_time": end,
            "limit": 100,
        }
        defaults.update(overrides)
        return RadiusSearchRequestContract(**defaults)

    @staticmethod
    def make_distance_request(**overrides) -> DistanceRequestContract:
        """Generate valid distance calculation request"""
        lat1, lon1 = LocationTestDataFactory.make_san_francisco_coordinates()
        lat2, lon2 = LocationTestDataFactory.make_new_york_coordinates()
        defaults = {
            "from_lat": lat1,
            "from_lon": lon1,
            "to_lat": lat2,
            "to_lon": lon2,
        }
        defaults.update(overrides)
        return DistanceRequestContract(**defaults)

    # =========================================================================
    # Response Generators
    # =========================================================================

    @staticmethod
    def make_location_response(**overrides) -> Dict[str, Any]:
        """Generate location response data"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        now = LocationTestDataFactory.make_timestamp()
        defaults = {
            "location_id": LocationTestDataFactory.make_location_id(),
            "device_id": LocationTestDataFactory.make_device_id(),
            "user_id": LocationTestDataFactory.make_user_id(),
            "latitude": lat,
            "longitude": lon,
            "altitude": LocationTestDataFactory.make_altitude(),
            "accuracy": LocationTestDataFactory.make_accuracy(),
            "heading": LocationTestDataFactory.make_heading(),
            "speed": LocationTestDataFactory.make_speed(),
            "address": LocationTestDataFactory.make_address(),
            "city": LocationTestDataFactory.make_city(),
            "state": LocationTestDataFactory.make_state(),
            "country": LocationTestDataFactory.make_country(),
            "location_method": "gps",
            "battery_level": LocationTestDataFactory.make_battery_level(),
            "source": "device",
            "metadata": {},
            "timestamp": now.isoformat(),
            "created_at": now.isoformat(),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_geofence_response(**overrides) -> Dict[str, Any]:
        """Generate geofence response data"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        now = LocationTestDataFactory.make_timestamp()
        defaults = {
            "geofence_id": LocationTestDataFactory.make_geofence_id(),
            "name": LocationTestDataFactory.make_geofence_name(),
            "description": LocationTestDataFactory.make_description(),
            "user_id": LocationTestDataFactory.make_user_id(),
            "organization_id": None,
            "shape_type": "circle",
            "center_lat": lat,
            "center_lon": lon,
            "radius": 500.0,
            "polygon_coordinates": None,
            "active": True,
            "trigger_on_enter": True,
            "trigger_on_exit": True,
            "trigger_on_dwell": False,
            "dwell_time_seconds": None,
            "target_devices": [],
            "target_groups": [],
            "active_days": None,
            "active_hours": None,
            "notification_channels": [],
            "notification_template": None,
            "total_triggers": random.randint(0, 100),
            "last_triggered": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "tags": [],
            "metadata": {},
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_place_response(**overrides) -> Dict[str, Any]:
        """Generate place response data"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        now = LocationTestDataFactory.make_timestamp()
        defaults = {
            "place_id": LocationTestDataFactory.make_place_id(),
            "user_id": LocationTestDataFactory.make_user_id(),
            "name": LocationTestDataFactory.make_place_name(),
            "category": "home",
            "latitude": lat,
            "longitude": lon,
            "address": LocationTestDataFactory.make_address(),
            "radius": 100.0,
            "icon": None,
            "color": None,
            "visit_count": random.randint(0, 100),
            "total_time_spent": random.randint(0, 86400),
            "last_visit": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "tags": [],
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_operation_result(success: bool = True, operation: str = "test", **overrides) -> Dict[str, Any]:
        """Generate operation result data"""
        defaults = {
            "success": success,
            "operation": operation,
            "message": f"{operation} completed successfully" if success else f"{operation} failed",
            "data": None,
            "affected_count": 1 if success else 0,
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_distance_response(**overrides) -> Dict[str, Any]:
        """Generate distance response data"""
        distance_m = random.uniform(1000, 5000000)
        defaults = {
            "from_lat": 37.7749,
            "from_lon": -122.4194,
            "to_lat": 40.7128,
            "to_lon": -74.0060,
            "distance_meters": round(distance_m, 2),
            "distance_km": round(distance_m / 1000, 2),
        }
        defaults.update(overrides)
        return defaults

    # =========================================================================
    # Invalid Data Generators
    # =========================================================================

    @staticmethod
    def make_invalid_location_id() -> str:
        """Generate invalid location ID (wrong format)"""
        return "invalid_id_format"

    @staticmethod
    def make_invalid_geofence_id() -> str:
        """Generate invalid geofence ID"""
        return "bad_geo_id"

    @staticmethod
    def make_invalid_device_id_empty() -> str:
        """Generate empty device ID"""
        return ""

    @staticmethod
    def make_invalid_device_id_whitespace() -> str:
        """Generate whitespace device ID"""
        return "   "

    @staticmethod
    def make_invalid_latitude_too_low() -> float:
        """Generate latitude below -90"""
        return -91.0

    @staticmethod
    def make_invalid_latitude_too_high() -> float:
        """Generate latitude above 90"""
        return 91.0

    @staticmethod
    def make_invalid_longitude_too_low() -> float:
        """Generate longitude below -180"""
        return -181.0

    @staticmethod
    def make_invalid_longitude_too_high() -> float:
        """Generate longitude above 180"""
        return 181.0

    @staticmethod
    def make_invalid_accuracy_zero() -> float:
        """Generate zero accuracy (invalid)"""
        return 0.0

    @staticmethod
    def make_invalid_accuracy_negative() -> float:
        """Generate negative accuracy"""
        return -10.0

    @staticmethod
    def make_invalid_heading_negative() -> float:
        """Generate negative heading"""
        return -10.0

    @staticmethod
    def make_invalid_heading_too_high() -> float:
        """Generate heading >= 360"""
        return 360.0

    @staticmethod
    def make_invalid_speed_negative() -> float:
        """Generate negative speed"""
        return -5.0

    @staticmethod
    def make_invalid_battery_negative() -> float:
        """Generate negative battery level"""
        return -10.0

    @staticmethod
    def make_invalid_battery_too_high() -> float:
        """Generate battery level > 100"""
        return 150.0

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
    def make_invalid_radius_zero() -> float:
        """Generate zero radius"""
        return 0.0

    @staticmethod
    def make_invalid_radius_negative() -> float:
        """Generate negative radius"""
        return -100.0

    @staticmethod
    def make_invalid_radius_too_large() -> float:
        """Generate radius exceeding max (50km for nearby search)"""
        return 100000.0

    @staticmethod
    def make_invalid_dwell_time() -> int:
        """Generate invalid dwell time (< 60 seconds)"""
        return 30

    @staticmethod
    def make_invalid_polygon_too_few_points() -> List[Tuple[float, float]]:
        """Generate polygon with only 2 points"""
        return [(37.7749, -122.4194), (37.7849, -122.4294)]

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
    def make_invalid_time_window() -> int:
        """Generate invalid time window (exceeds 1440 minutes)"""
        return 2000

    # =========================================================================
    # Edge Case Generators
    # =========================================================================

    @staticmethod
    def make_boundary_latitude_min() -> float:
        """Generate minimum valid latitude"""
        return -90.0

    @staticmethod
    def make_boundary_latitude_max() -> float:
        """Generate maximum valid latitude"""
        return 90.0

    @staticmethod
    def make_boundary_longitude_min() -> float:
        """Generate minimum valid longitude"""
        return -180.0

    @staticmethod
    def make_boundary_longitude_max() -> float:
        """Generate maximum valid longitude"""
        return 180.0

    @staticmethod
    def make_unicode_name() -> str:
        """Generate name with unicode characters"""
        return f"Test \u4e2d\u6587 Location {secrets.token_hex(2)}"

    @staticmethod
    def make_special_chars_name() -> str:
        """Generate name with special characters"""
        return f"Test!@#$%^&*() {secrets.token_hex(2)}"

    @staticmethod
    def make_max_length_name() -> str:
        """Generate name at max length (200 chars)"""
        return "x" * 200

    @staticmethod
    def make_min_length_name() -> str:
        """Generate name at min length (1 char)"""
        return "x"

    @staticmethod
    def make_zero_coordinates() -> Tuple[float, float]:
        """Generate coordinates at (0, 0)"""
        return (0.0, 0.0)

    @staticmethod
    def make_north_pole_coordinates() -> Tuple[float, float]:
        """Generate North Pole coordinates"""
        return (90.0, 0.0)

    @staticmethod
    def make_south_pole_coordinates() -> Tuple[float, float]:
        """Generate South Pole coordinates"""
        return (-90.0, 0.0)

    # =========================================================================
    # Batch Generators
    # =========================================================================

    @staticmethod
    def make_batch_location_requests(count: int = 5) -> List[LocationReportRequestContract]:
        """Generate multiple location report requests"""
        return [LocationTestDataFactory.make_location_report_request() for _ in range(count)]

    @staticmethod
    def make_batch_location_ids(count: int = 5) -> List[str]:
        """Generate multiple location IDs"""
        return [LocationTestDataFactory.make_location_id() for _ in range(count)]

    @staticmethod
    def make_batch_geofence_ids(count: int = 5) -> List[str]:
        """Generate multiple geofence IDs"""
        return [LocationTestDataFactory.make_geofence_id() for _ in range(count)]

    @staticmethod
    def make_batch_device_ids(count: int = 5) -> List[str]:
        """Generate multiple device IDs"""
        return [LocationTestDataFactory.make_device_id() for _ in range(count)]


# =============================================================================
# REQUEST BUILDERS - FLUENT API
# =============================================================================


class LocationReportRequestBuilder:
    """Builder for location report requests with fluent API"""

    def __init__(self):
        """Initialize with factory-generated defaults"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        self._device_id = LocationTestDataFactory.make_device_id()
        self._latitude = lat
        self._longitude = lon
        self._accuracy = LocationTestDataFactory.make_accuracy()
        self._altitude: Optional[float] = None
        self._heading: Optional[float] = None
        self._speed: Optional[float] = None
        self._location_method = LocationMethod.GPS
        self._battery_level: Optional[float] = None
        self._timestamp: Optional[datetime] = None
        self._metadata: Dict[str, Any] = {}

    def with_device_id(self, device_id: str) -> 'LocationReportRequestBuilder':
        """Set custom device ID"""
        self._device_id = device_id
        return self

    def with_coordinates(self, latitude: float, longitude: float) -> 'LocationReportRequestBuilder':
        """Set custom coordinates"""
        self._latitude = latitude
        self._longitude = longitude
        return self

    def with_accuracy(self, accuracy: float) -> 'LocationReportRequestBuilder':
        """Set custom accuracy"""
        self._accuracy = accuracy
        return self

    def with_altitude(self, altitude: float) -> 'LocationReportRequestBuilder':
        """Set custom altitude"""
        self._altitude = altitude
        return self

    def with_heading(self, heading: float) -> 'LocationReportRequestBuilder':
        """Set custom heading"""
        self._heading = heading
        return self

    def with_speed(self, speed: float) -> 'LocationReportRequestBuilder':
        """Set custom speed"""
        self._speed = speed
        return self

    def with_location_method(self, method: LocationMethod) -> 'LocationReportRequestBuilder':
        """Set location method"""
        self._location_method = method
        return self

    def with_battery_level(self, level: float) -> 'LocationReportRequestBuilder':
        """Set battery level"""
        self._battery_level = level
        return self

    def with_timestamp(self, timestamp: datetime) -> 'LocationReportRequestBuilder':
        """Set custom timestamp"""
        self._timestamp = timestamp
        return self

    def with_metadata(self, metadata: Dict[str, Any]) -> 'LocationReportRequestBuilder':
        """Set custom metadata"""
        self._metadata = metadata
        return self

    def with_invalid_coordinates(self) -> 'LocationReportRequestBuilder':
        """Set invalid coordinates for negative testing"""
        self._latitude = LocationTestDataFactory.make_invalid_latitude_too_high()
        return self

    def with_invalid_accuracy(self) -> 'LocationReportRequestBuilder':
        """Set invalid accuracy for negative testing"""
        self._accuracy = LocationTestDataFactory.make_invalid_accuracy_negative()
        return self

    def build(self) -> LocationReportRequestContract:
        """Build the request contract"""
        return LocationReportRequestContract(
            device_id=self._device_id,
            latitude=self._latitude,
            longitude=self._longitude,
            accuracy=self._accuracy,
            altitude=self._altitude,
            heading=self._heading,
            speed=self._speed,
            location_method=self._location_method,
            battery_level=self._battery_level,
            timestamp=self._timestamp,
            metadata=self._metadata,
        )

    def build_dict(self) -> Dict[str, Any]:
        """Build as dictionary for API calls"""
        return self.build().model_dump(exclude_none=True)


class GeofenceCreateRequestBuilder:
    """Builder for geofence creation requests with fluent API"""

    def __init__(self):
        """Initialize with factory-generated defaults"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        self._name = LocationTestDataFactory.make_geofence_name()
        self._description: Optional[str] = None
        self._shape_type = GeofenceShapeType.CIRCLE
        self._center_lat = lat
        self._center_lon = lon
        self._radius: Optional[float] = 500.0
        self._polygon_coordinates: Optional[List[Tuple[float, float]]] = None
        self._trigger_on_enter = True
        self._trigger_on_exit = True
        self._trigger_on_dwell = False
        self._dwell_time_seconds: Optional[int] = None
        self._target_devices: List[str] = []
        self._tags: List[str] = []
        self._metadata: Dict[str, Any] = {}

    def with_name(self, name: str) -> 'GeofenceCreateRequestBuilder':
        """Set custom name"""
        self._name = name
        return self

    def with_description(self, description: str) -> 'GeofenceCreateRequestBuilder':
        """Set description"""
        self._description = description
        return self

    def as_circle(self, center_lat: float, center_lon: float, radius: float) -> 'GeofenceCreateRequestBuilder':
        """Configure as circle geofence"""
        self._shape_type = GeofenceShapeType.CIRCLE
        self._center_lat = center_lat
        self._center_lon = center_lon
        self._radius = radius
        self._polygon_coordinates = None
        return self

    def as_polygon(self, coordinates: List[Tuple[float, float]]) -> 'GeofenceCreateRequestBuilder':
        """Configure as polygon geofence"""
        self._shape_type = GeofenceShapeType.POLYGON
        self._polygon_coordinates = coordinates
        if coordinates:
            self._center_lat = sum(c[0] for c in coordinates) / len(coordinates)
            self._center_lon = sum(c[1] for c in coordinates) / len(coordinates)
        self._radius = None
        return self

    def with_enter_trigger(self, enabled: bool = True) -> 'GeofenceCreateRequestBuilder':
        """Enable/disable enter trigger"""
        self._trigger_on_enter = enabled
        return self

    def with_exit_trigger(self, enabled: bool = True) -> 'GeofenceCreateRequestBuilder':
        """Enable/disable exit trigger"""
        self._trigger_on_exit = enabled
        return self

    def with_dwell_trigger(self, enabled: bool, dwell_seconds: int = 300) -> 'GeofenceCreateRequestBuilder':
        """Enable/disable dwell trigger"""
        self._trigger_on_dwell = enabled
        self._dwell_time_seconds = dwell_seconds if enabled else None
        return self

    def with_target_devices(self, device_ids: List[str]) -> 'GeofenceCreateRequestBuilder':
        """Set target devices"""
        self._target_devices = device_ids
        return self

    def with_tags(self, tags: List[str]) -> 'GeofenceCreateRequestBuilder':
        """Set tags"""
        self._tags = tags
        return self

    def with_invalid_name(self) -> 'GeofenceCreateRequestBuilder':
        """Set invalid name for negative testing"""
        self._name = LocationTestDataFactory.make_invalid_name_empty()
        return self

    def with_invalid_polygon(self) -> 'GeofenceCreateRequestBuilder':
        """Set invalid polygon for negative testing"""
        self._shape_type = GeofenceShapeType.POLYGON
        self._polygon_coordinates = LocationTestDataFactory.make_invalid_polygon_too_few_points()
        return self

    def build(self) -> GeofenceCreateRequestContract:
        """Build the request contract"""
        return GeofenceCreateRequestContract(
            name=self._name,
            description=self._description,
            shape_type=self._shape_type,
            center_lat=self._center_lat,
            center_lon=self._center_lon,
            radius=self._radius,
            polygon_coordinates=self._polygon_coordinates,
            trigger_on_enter=self._trigger_on_enter,
            trigger_on_exit=self._trigger_on_exit,
            trigger_on_dwell=self._trigger_on_dwell,
            dwell_time_seconds=self._dwell_time_seconds,
            target_devices=self._target_devices,
            tags=self._tags,
            metadata=self._metadata,
        )

    def build_dict(self) -> Dict[str, Any]:
        """Build as dictionary for API calls"""
        return self.build().model_dump(exclude_none=True)


class PlaceCreateRequestBuilder:
    """Builder for place creation requests with fluent API"""

    def __init__(self):
        """Initialize with factory-generated defaults"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        self._name = LocationTestDataFactory.make_place_name()
        self._category = PlaceCategory.HOME
        self._latitude = lat
        self._longitude = lon
        self._address: Optional[str] = None
        self._radius = 100.0
        self._icon: Optional[str] = None
        self._color: Optional[str] = None
        self._tags: List[str] = []

    def with_name(self, name: str) -> 'PlaceCreateRequestBuilder':
        """Set custom name"""
        self._name = name
        return self

    def with_category(self, category: PlaceCategory) -> 'PlaceCreateRequestBuilder':
        """Set category"""
        self._category = category
        return self

    def with_coordinates(self, latitude: float, longitude: float) -> 'PlaceCreateRequestBuilder':
        """Set coordinates"""
        self._latitude = latitude
        self._longitude = longitude
        return self

    def with_address(self, address: str) -> 'PlaceCreateRequestBuilder':
        """Set address"""
        self._address = address
        return self

    def with_radius(self, radius: float) -> 'PlaceCreateRequestBuilder':
        """Set recognition radius"""
        self._radius = radius
        return self

    def with_icon(self, icon: str) -> 'PlaceCreateRequestBuilder':
        """Set icon"""
        self._icon = icon
        return self

    def with_color(self, color: str) -> 'PlaceCreateRequestBuilder':
        """Set color"""
        self._color = color
        return self

    def with_tags(self, tags: List[str]) -> 'PlaceCreateRequestBuilder':
        """Set tags"""
        self._tags = tags
        return self

    def as_home(self) -> 'PlaceCreateRequestBuilder':
        """Configure as home place"""
        self._category = PlaceCategory.HOME
        self._icon = "home"
        return self

    def as_work(self) -> 'PlaceCreateRequestBuilder':
        """Configure as work place"""
        self._category = PlaceCategory.WORK
        self._icon = "work"
        return self

    def as_school(self) -> 'PlaceCreateRequestBuilder':
        """Configure as school place"""
        self._category = PlaceCategory.SCHOOL
        self._icon = "school"
        return self

    def with_invalid_name(self) -> 'PlaceCreateRequestBuilder':
        """Set invalid name for negative testing"""
        self._name = LocationTestDataFactory.make_invalid_name_empty()
        return self

    def with_invalid_radius(self) -> 'PlaceCreateRequestBuilder':
        """Set invalid radius for negative testing"""
        self._radius = LocationTestDataFactory.make_invalid_radius_negative()
        return self

    def build(self) -> PlaceCreateRequestContract:
        """Build the request contract"""
        return PlaceCreateRequestContract(
            name=self._name,
            category=self._category,
            latitude=self._latitude,
            longitude=self._longitude,
            address=self._address,
            radius=self._radius,
            icon=self._icon,
            color=self._color,
            tags=self._tags,
        )

    def build_dict(self) -> Dict[str, Any]:
        """Build as dictionary for API calls"""
        return self.build().model_dump(exclude_none=True)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Enums
    "LocationMethod",
    "GeofenceShapeType",
    "GeofenceTriggerType",
    "PlaceCategory",
    "RouteStatus",
    # Request Contracts
    "LocationReportRequestContract",
    "LocationBatchRequestContract",
    "GeofenceCreateRequestContract",
    "GeofenceUpdateRequestContract",
    "PlaceCreateRequestContract",
    "PlaceUpdateRequestContract",
    "NearbySearchRequestContract",
    "RadiusSearchRequestContract",
    "PolygonSearchRequestContract",
    "DistanceRequestContract",
    # Response Contracts
    "LocationResponseContract",
    "GeofenceResponseContract",
    "PlaceResponseContract",
    "LocationOperationResultContract",
    "DistanceResponseContract",
    "NearbyDeviceResponseContract",
    "LocationListResponseContract",
    "GeofenceListResponseContract",
    "PlaceListResponseContract",
    "ErrorResponseContract",
    # Factory
    "LocationTestDataFactory",
    # Builders
    "LocationReportRequestBuilder",
    "GeofenceCreateRequestBuilder",
    "PlaceCreateRequestBuilder",
]
