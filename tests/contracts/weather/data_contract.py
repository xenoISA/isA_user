"""
Weather Service Data Contract

Defines canonical data structures for weather service testing.
All tests MUST use these Pydantic models and factories for consistency.

This is the SINGLE SOURCE OF TRUTH for weather service test data.

Zero Hardcoded Data Pattern:
- ALL test data generated through WeatherTestDataFactory methods
- NEVER hardcode values like "London", "15.5", "user_123"
- Factory methods ensure unique, realistic test data
"""

import uuid
import random
import string
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Enumerations
# ============================================================================

class UnitSystem(str, Enum):
    """Weather data unit system"""
    METRIC = "metric"
    IMPERIAL = "imperial"


class WeatherCondition(str, Enum):
    """Standard weather conditions"""
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    SNOW = "snow"
    THUNDERSTORM = "thunderstorm"
    MIST = "mist"
    FOG = "fog"
    DRIZZLE = "drizzle"
    OVERCAST = "overcast"


class AlertSeverity(str, Enum):
    """Weather alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    SEVERE = "severe"
    EXTREME = "extreme"


class AlertType(str, Enum):
    """Weather alert types"""
    STORM = "storm"
    FLOOD = "flood"
    HEAT = "heat"
    COLD = "cold"
    HURRICANE = "hurricane"
    TORNADO = "tornado"
    WILDFIRE = "wildfire"
    WIND = "wind"
    SNOW = "snow"
    FOG = "fog"


# ============================================================================
# Request Contracts (Input Schemas)
# ============================================================================

class WeatherCurrentRequestContract(BaseModel):
    """
    Contract: Current weather request schema

    Used for fetching current weather conditions for a location.
    Maps to GET /api/v1/weather/current
    """
    location: str = Field(..., min_length=1, max_length=200, description="Location name (city, region)")
    units: UnitSystem = Field(default=UnitSystem.METRIC, description="Unit system (metric/imperial)")

    @field_validator('location')
    @classmethod
    def validate_location(cls, v: str) -> str:
        """Location must not be empty or whitespace"""
        if not v or not v.strip():
            raise ValueError("location cannot be empty or whitespace")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "location": "London",
                "units": "metric"
            }
        }


class WeatherForecastRequestContract(BaseModel):
    """
    Contract: Weather forecast request schema

    Used for fetching multi-day weather forecasts.
    Maps to GET /api/v1/weather/forecast
    """
    location: str = Field(..., min_length=1, max_length=200, description="Location name")
    days: int = Field(default=5, ge=1, le=16, description="Number of forecast days (1-16)")
    units: UnitSystem = Field(default=UnitSystem.METRIC, description="Unit system")

    @field_validator('location')
    @classmethod
    def validate_location(cls, v: str) -> str:
        """Location must not be empty"""
        if not v or not v.strip():
            raise ValueError("location cannot be empty or whitespace")
        return v.strip()

    @field_validator('days')
    @classmethod
    def validate_days(cls, v: int) -> int:
        """Days must be within valid range"""
        if v < 1:
            raise ValueError("days must be at least 1")
        if v > 16:
            raise ValueError("days cannot exceed 16")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "location": "Tokyo",
                "days": 7,
                "units": "metric"
            }
        }


class WeatherAlertQueryContract(BaseModel):
    """
    Contract: Weather alert query request schema

    Used for fetching active weather alerts for a location.
    Maps to GET /api/v1/weather/alerts
    """
    location: str = Field(..., min_length=1, max_length=200, description="Location name")

    @field_validator('location')
    @classmethod
    def validate_location(cls, v: str) -> str:
        """Location must not be empty"""
        if not v or not v.strip():
            raise ValueError("location cannot be empty or whitespace")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "location": "Miami"
            }
        }


class LocationSaveRequestContract(BaseModel):
    """
    Contract: Save favorite location request schema

    Used for saving user's favorite weather locations.
    Maps to POST /api/v1/weather/locations
    """
    user_id: str = Field(..., min_length=1, max_length=100, description="User identifier")
    location: str = Field(..., min_length=1, max_length=200, description="Location name")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude coordinate")
    is_default: bool = Field(default=False, description="Set as default location")
    nickname: Optional[str] = Field(None, max_length=100, description="User-friendly name")

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """User ID must not be empty"""
        if not v or not v.strip():
            raise ValueError("user_id cannot be empty or whitespace")
        return v.strip()

    @field_validator('location')
    @classmethod
    def validate_location(cls, v: str) -> str:
        """Location must not be empty"""
        if not v or not v.strip():
            raise ValueError("location cannot be empty or whitespace")
        return v.strip()

    @field_validator('nickname')
    @classmethod
    def validate_nickname(cls, v: Optional[str]) -> Optional[str]:
        """Nickname trimmed if provided"""
        if v is not None:
            return v.strip() if v.strip() else None
        return None

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_abc123",
                "location": "New York",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "is_default": True,
                "nickname": "Home"
            }
        }


class LocationDeleteRequestContract(BaseModel):
    """
    Contract: Delete location request schema

    Used for deleting a saved location.
    Maps to DELETE /api/v1/weather/locations/{location_id}
    """
    location_id: int = Field(..., ge=1, description="Location ID to delete")
    user_id: str = Field(..., min_length=1, max_length=100, description="User ID for authorization")

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """User ID must not be empty"""
        if not v or not v.strip():
            raise ValueError("user_id cannot be empty or whitespace")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "location_id": 42,
                "user_id": "user_abc123"
            }
        }


class LocationListRequestContract(BaseModel):
    """
    Contract: List user locations request schema

    Used for retrieving all saved locations for a user.
    Maps to GET /api/v1/weather/locations/{user_id}
    """
    user_id: str = Field(..., min_length=1, max_length=100, description="User identifier")

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """User ID must not be empty"""
        if not v or not v.strip():
            raise ValueError("user_id cannot be empty or whitespace")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_abc123"
            }
        }


# ============================================================================
# Response Contracts (Output Schemas)
# ============================================================================

class WeatherCurrentResponseContract(BaseModel):
    """
    Contract: Current weather response schema

    Validates API response structure for current weather data.
    """
    location: str = Field(..., description="Location name")
    temperature: float = Field(..., description="Temperature in requested units")
    feels_like: Optional[float] = Field(None, description="Feels-like temperature")
    humidity: int = Field(..., ge=0, le=100, description="Humidity percentage")
    condition: str = Field(..., description="Weather condition")
    description: Optional[str] = Field(None, description="Detailed description")
    icon: Optional[str] = Field(None, description="Weather icon code")
    wind_speed: Optional[float] = Field(None, ge=0, description="Wind speed")
    observed_at: datetime = Field(..., description="Observation timestamp")
    cached: bool = Field(..., description="Whether data was served from cache")

    class Config:
        json_schema_extra = {
            "example": {
                "location": "London",
                "temperature": 15.5,
                "feels_like": 14.2,
                "humidity": 72,
                "condition": "cloudy",
                "description": "overcast clouds",
                "icon": "04d",
                "wind_speed": 3.6,
                "observed_at": "2025-12-17T10:30:00Z",
                "cached": False
            }
        }


class ForecastDayContract(BaseModel):
    """
    Contract: Single day forecast schema

    Represents one day in a multi-day forecast.
    """
    date: datetime = Field(..., description="Forecast date")
    temp_max: float = Field(..., description="Maximum temperature")
    temp_min: float = Field(..., description="Minimum temperature")
    temp_avg: Optional[float] = Field(None, description="Average temperature")
    condition: str = Field(..., description="Weather condition")
    description: Optional[str] = Field(None, description="Detailed description")
    icon: Optional[str] = Field(None, description="Weather icon code")
    humidity: Optional[int] = Field(None, ge=0, le=100, description="Humidity percentage")
    wind_speed: Optional[float] = Field(None, ge=0, description="Wind speed")
    precipitation_chance: Optional[int] = Field(None, ge=0, le=100, description="Chance of precipitation")
    precipitation_amount: Optional[float] = Field(None, ge=0, description="Precipitation amount in mm")

    class Config:
        json_schema_extra = {
            "example": {
                "date": "2025-12-17T00:00:00Z",
                "temp_max": 12.5,
                "temp_min": 6.2,
                "temp_avg": 9.4,
                "condition": "clear",
                "description": "clear sky",
                "icon": "01d",
                "humidity": 45,
                "wind_speed": 2.1,
                "precipitation_chance": 10,
                "precipitation_amount": 0.0
            }
        }


class WeatherForecastResponseContract(BaseModel):
    """
    Contract: Weather forecast response schema

    Validates API response structure for multi-day forecasts.
    """
    location: str = Field(..., description="Location name")
    forecast: List[ForecastDayContract] = Field(..., description="Daily forecasts")
    generated_at: datetime = Field(..., description="Forecast generation timestamp")
    cached: bool = Field(..., description="Whether data was served from cache")

    class Config:
        json_schema_extra = {
            "example": {
                "location": "Tokyo",
                "forecast": [],
                "generated_at": "2025-12-17T08:00:00Z",
                "cached": False
            }
        }


class WeatherAlertContract(BaseModel):
    """
    Contract: Single weather alert schema

    Represents one weather alert for a location.
    """
    id: Optional[int] = Field(None, description="Alert ID")
    location: str = Field(..., description="Affected location")
    alert_type: str = Field(..., description="Alert type (storm, flood, etc.)")
    severity: AlertSeverity = Field(..., description="Alert severity level")
    headline: str = Field(..., description="Alert headline")
    description: str = Field(..., description="Detailed alert description")
    start_time: datetime = Field(..., description="Alert effective start time")
    end_time: datetime = Field(..., description="Alert expiration time")
    source: str = Field(..., description="Alert issuing authority")
    created_at: Optional[datetime] = Field(None, description="When alert was received")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "location": "Miami",
                "alert_type": "hurricane",
                "severity": "severe",
                "headline": "Hurricane Warning in Effect",
                "description": "A hurricane warning means hurricane conditions are expected...",
                "start_time": "2025-12-17T14:00:00Z",
                "end_time": "2025-12-18T06:00:00Z",
                "source": "NWS",
                "created_at": "2025-12-17T08:00:00Z"
            }
        }


class WeatherAlertResponseContract(BaseModel):
    """
    Contract: Weather alerts response schema

    Validates API response structure for weather alerts.
    """
    alerts: List[WeatherAlertContract] = Field(..., description="List of active alerts")
    location: str = Field(..., description="Queried location")
    checked_at: datetime = Field(..., description="When alerts were checked")

    class Config:
        json_schema_extra = {
            "example": {
                "alerts": [],
                "location": "Miami",
                "checked_at": "2025-12-17T10:30:00Z"
            }
        }


class LocationResponseContract(BaseModel):
    """
    Contract: Saved location response schema

    Validates API response structure for a saved location.
    """
    id: int = Field(..., description="Location ID")
    user_id: str = Field(..., description="Owner user ID")
    location: str = Field(..., description="Location name")
    latitude: Optional[float] = Field(None, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, description="Longitude coordinate")
    is_default: bool = Field(..., description="Is default location")
    nickname: Optional[str] = Field(None, description="User-friendly name")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 42,
                "user_id": "user_abc123",
                "location": "New York",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "is_default": True,
                "nickname": "Home",
                "created_at": "2025-12-17T10:00:00Z"
            }
        }


class LocationListResponseContract(BaseModel):
    """
    Contract: Location list response schema

    Validates API response structure for listing user's locations.
    """
    locations: List[LocationResponseContract] = Field(..., description="List of saved locations")
    total: int = Field(..., ge=0, description="Total number of locations")

    class Config:
        json_schema_extra = {
            "example": {
                "locations": [],
                "total": 0
            }
        }


class ErrorResponseContract(BaseModel):
    """
    Contract: Standard error response schema

    Validates error response structure from weather service.
    """
    detail: str = Field(..., description="Error message")

    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Weather data not found"
            }
        }


# ============================================================================
# Event Contracts
# ============================================================================

class WeatherDataFetchedEventContract(BaseModel):
    """
    Contract: weather.data.fetched event payload

    Published when fresh weather data is fetched from external API.
    """
    location: str = Field(..., description="Location name")
    temperature: float = Field(..., description="Temperature value")
    condition: str = Field(..., description="Weather condition")
    units: str = Field(..., description="Unit system used")
    provider: str = Field(..., description="Data provider name")
    timestamp: str = Field(..., description="ISO 8601 timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "location": "London",
                "temperature": 15.5,
                "condition": "cloudy",
                "units": "metric",
                "provider": "openweathermap",
                "timestamp": "2025-12-17T10:30:00Z"
            }
        }


class WeatherAlertCreatedEventContract(BaseModel):
    """
    Contract: weather.alert.created event payload

    Published when active weather alerts are detected.
    """
    location: str = Field(..., description="Affected location")
    alert_count: int = Field(..., ge=0, description="Number of active alerts")
    alerts: List[Dict[str, Any]] = Field(..., description="Alert summaries")
    timestamp: str = Field(..., description="ISO 8601 timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "location": "Miami",
                "alert_count": 2,
                "alerts": [
                    {"severity": "severe", "alert_type": "hurricane", "headline": "Hurricane Warning"}
                ],
                "timestamp": "2025-12-17T14:00:00Z"
            }
        }


class WeatherLocationSavedEventContract(BaseModel):
    """
    Contract: weather.location_saved event payload

    Published when user saves a favorite location.
    """
    user_id: str = Field(..., description="User identifier")
    location_id: int = Field(..., description="Location ID")
    location: str = Field(..., description="Location name")
    latitude: Optional[float] = Field(None, description="Latitude")
    longitude: Optional[float] = Field(None, description="Longitude")
    is_default: bool = Field(..., description="Is default location")
    nickname: Optional[str] = Field(None, description="Location nickname")
    created_at: str = Field(..., description="ISO 8601 timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_abc123",
                "location_id": 42,
                "location": "New York",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "is_default": True,
                "nickname": "Home",
                "created_at": "2025-12-17T10:00:00Z"
            }
        }


# ============================================================================
# Test Data Factory
# ============================================================================

class WeatherTestDataFactory:
    """
    Test data factory for weather_service.

    Zero hardcoded data - all values generated dynamically.

    Method Naming Convention:
    - make_*: Generates VALID data
    - make_invalid_*: Generates INVALID data for negative testing
    - make_edge_*: Generates edge case data for boundary testing
    - make_batch_*: Generates multiple items

    Usage:
        # Generate valid current weather request
        request = WeatherTestDataFactory.make_current_weather_request()

        # Generate with custom location
        request = WeatherTestDataFactory.make_current_weather_request(location="Tokyo")

        # Generate invalid request for negative testing
        invalid_location = WeatherTestDataFactory.make_invalid_location_empty()
    """

    # Cities pool for realistic location generation
    _CITIES = [
        "London", "New York", "Tokyo", "Paris", "Sydney", "Berlin",
        "Toronto", "Singapore", "Dubai", "Mumbai", "Hong Kong", "Seoul",
        "Los Angeles", "Chicago", "San Francisco", "Miami", "Boston",
        "Seattle", "Denver", "Phoenix", "Amsterdam", "Barcelona", "Rome"
    ]

    _WEATHER_CONDITIONS = [
        "clear", "cloudy", "rain", "snow", "thunderstorm", "mist",
        "fog", "drizzle", "overcast", "partly cloudy"
    ]

    _ALERT_TYPES = [
        "storm", "flood", "heat", "cold", "hurricane", "tornado",
        "wildfire", "wind", "snow", "fog"
    ]

    _ALERT_SOURCES = ["NWS", "NOAA", "Met Office", "Environment Canada", "JMA"]

    _NICKNAMES = ["Home", "Office", "Work", "Parents", "Vacation", "Beach House", "Mountain Cabin"]

    # ==========================================================================
    # ID Generators
    # ==========================================================================

    @staticmethod
    def make_user_id() -> str:
        """Generate valid user ID"""
        return f"user_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_location_id() -> int:
        """Generate valid location ID"""
        return random.randint(1, 10000)

    @staticmethod
    def make_alert_id() -> int:
        """Generate valid alert ID"""
        return random.randint(1, 10000)

    @staticmethod
    def make_uuid() -> str:
        """Generate UUID string"""
        return str(uuid.uuid4())

    @staticmethod
    def make_correlation_id() -> str:
        """Generate correlation ID for tracing"""
        return f"corr_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def make_cache_key(data_type: str = "current") -> str:
        """Generate cache key format"""
        location = random.choice(WeatherTestDataFactory._CITIES)
        units = random.choice(["metric", "imperial"])
        return f"weather:{data_type}:{location}:{units}"

    # ==========================================================================
    # Location Generators
    # ==========================================================================

    @staticmethod
    def make_location() -> str:
        """Generate valid location name"""
        return random.choice(WeatherTestDataFactory._CITIES)

    @staticmethod
    def make_unique_location() -> str:
        """Generate unique location name with suffix"""
        city = random.choice(WeatherTestDataFactory._CITIES)
        suffix = secrets.token_hex(3)
        return f"{city}_{suffix}"

    @staticmethod
    def make_latitude() -> float:
        """Generate valid latitude (-90 to 90)"""
        return round(random.uniform(-90, 90), 6)

    @staticmethod
    def make_longitude() -> float:
        """Generate valid longitude (-180 to 180)"""
        return round(random.uniform(-180, 180), 6)

    @staticmethod
    def make_coordinates() -> Dict[str, float]:
        """Generate valid coordinate pair"""
        return {
            "latitude": WeatherTestDataFactory.make_latitude(),
            "longitude": WeatherTestDataFactory.make_longitude()
        }

    @staticmethod
    def make_realistic_coordinates() -> Dict[str, float]:
        """Generate realistic city coordinates"""
        coords = {
            "London": (51.5074, -0.1278),
            "New York": (40.7128, -74.0060),
            "Tokyo": (35.6762, 139.6503),
            "Paris": (48.8566, 2.3522),
            "Sydney": (-33.8688, 151.2093),
        }
        city = random.choice(list(coords.keys()))
        lat, lon = coords[city]
        return {"latitude": lat, "longitude": lon, "city": city}

    @staticmethod
    def make_nickname() -> str:
        """Generate valid location nickname"""
        return random.choice(WeatherTestDataFactory._NICKNAMES)

    # ==========================================================================
    # Weather Data Generators
    # ==========================================================================

    @staticmethod
    def make_temperature(units: str = "metric") -> float:
        """Generate realistic temperature"""
        if units == "metric":
            return round(random.uniform(-20, 45), 1)  # Celsius
        else:
            return round(random.uniform(-4, 113), 1)  # Fahrenheit

    @staticmethod
    def make_feels_like(temperature: float, units: str = "metric") -> float:
        """Generate feels-like temperature based on actual temperature"""
        variation = random.uniform(-5, 5) if units == "metric" else random.uniform(-9, 9)
        return round(temperature + variation, 1)

    @staticmethod
    def make_humidity() -> int:
        """Generate humidity percentage (0-100)"""
        return random.randint(0, 100)

    @staticmethod
    def make_wind_speed(units: str = "metric") -> float:
        """Generate wind speed"""
        if units == "metric":
            return round(random.uniform(0, 30), 1)  # m/s
        else:
            return round(random.uniform(0, 67), 1)  # mph

    @staticmethod
    def make_condition() -> str:
        """Generate weather condition"""
        return random.choice(WeatherTestDataFactory._WEATHER_CONDITIONS)

    @staticmethod
    def make_description() -> str:
        """Generate weather description"""
        conditions = [
            "clear sky", "few clouds", "scattered clouds", "broken clouds",
            "overcast clouds", "light rain", "moderate rain", "heavy rain",
            "light snow", "moderate snow", "thunderstorm", "mist", "fog"
        ]
        return random.choice(conditions)

    @staticmethod
    def make_weather_icon() -> str:
        """Generate weather icon code"""
        icons = ["01d", "01n", "02d", "02n", "03d", "03n", "04d", "04n",
                 "09d", "09n", "10d", "10n", "11d", "11n", "13d", "13n", "50d", "50n"]
        return random.choice(icons)

    @staticmethod
    def make_precipitation_chance() -> int:
        """Generate precipitation chance (0-100)"""
        return random.randint(0, 100)

    @staticmethod
    def make_precipitation_amount() -> float:
        """Generate precipitation amount in mm"""
        return round(random.uniform(0, 50), 1)

    # ==========================================================================
    # Timestamp Generators
    # ==========================================================================

    @staticmethod
    def make_timestamp() -> datetime:
        """Generate current UTC timestamp"""
        return datetime.now(timezone.utc)

    @staticmethod
    def make_past_timestamp(hours: int = 24) -> datetime:
        """Generate timestamp in the past"""
        return datetime.now(timezone.utc) - timedelta(hours=random.randint(1, hours))

    @staticmethod
    def make_future_timestamp(hours: int = 24) -> datetime:
        """Generate timestamp in the future"""
        return datetime.now(timezone.utc) + timedelta(hours=random.randint(1, hours))

    @staticmethod
    def make_timestamp_iso() -> str:
        """Generate ISO format timestamp string"""
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def make_forecast_date(days_ahead: int = 0) -> datetime:
        """Generate forecast date"""
        base = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        return base + timedelta(days=days_ahead)

    # ==========================================================================
    # Alert Generators
    # ==========================================================================

    @staticmethod
    def make_alert_type() -> str:
        """Generate alert type"""
        return random.choice(WeatherTestDataFactory._ALERT_TYPES)

    @staticmethod
    def make_alert_severity() -> AlertSeverity:
        """Generate alert severity"""
        return random.choice(list(AlertSeverity))

    @staticmethod
    def make_alert_headline() -> str:
        """Generate alert headline"""
        alert_type = WeatherTestDataFactory.make_alert_type()
        headlines = [
            f"{alert_type.title()} Warning in Effect",
            f"{alert_type.title()} Watch Issued",
            f"Severe {alert_type.title()} Expected",
            f"{alert_type.title()} Advisory Active",
        ]
        return random.choice(headlines)

    @staticmethod
    def make_alert_description() -> str:
        """Generate alert description"""
        descriptions = [
            "A weather warning has been issued for your area. Take precautions.",
            "Hazardous conditions expected. Stay indoors if possible.",
            "Monitor local news and weather updates for the latest information.",
            "This warning is in effect until further notice.",
        ]
        return random.choice(descriptions)

    @staticmethod
    def make_alert_source() -> str:
        """Generate alert source/authority"""
        return random.choice(WeatherTestDataFactory._ALERT_SOURCES)

    @staticmethod
    def make_alert_time_window() -> Dict[str, datetime]:
        """Generate alert start and end times"""
        now = datetime.now(timezone.utc)
        start = now + timedelta(hours=random.randint(1, 6))
        end = start + timedelta(hours=random.randint(6, 48))
        return {"start_time": start, "end_time": end}

    # ==========================================================================
    # Request Generators (Valid Data)
    # ==========================================================================

    @staticmethod
    def make_current_weather_request(**overrides) -> WeatherCurrentRequestContract:
        """Generate valid current weather request"""
        defaults = {
            "location": WeatherTestDataFactory.make_location(),
            "units": random.choice([UnitSystem.METRIC, UnitSystem.IMPERIAL]),
        }
        defaults.update(overrides)
        return WeatherCurrentRequestContract(**defaults)

    @staticmethod
    def make_forecast_request(**overrides) -> WeatherForecastRequestContract:
        """Generate valid forecast request"""
        defaults = {
            "location": WeatherTestDataFactory.make_location(),
            "days": random.randint(1, 16),
            "units": random.choice([UnitSystem.METRIC, UnitSystem.IMPERIAL]),
        }
        defaults.update(overrides)
        return WeatherForecastRequestContract(**defaults)

    @staticmethod
    def make_alert_query(**overrides) -> WeatherAlertQueryContract:
        """Generate valid alert query"""
        defaults = {
            "location": WeatherTestDataFactory.make_location(),
        }
        defaults.update(overrides)
        return WeatherAlertQueryContract(**defaults)

    @staticmethod
    def make_location_save_request(**overrides) -> LocationSaveRequestContract:
        """Generate valid location save request"""
        coords = WeatherTestDataFactory.make_realistic_coordinates()
        defaults = {
            "user_id": WeatherTestDataFactory.make_user_id(),
            "location": coords.get("city", WeatherTestDataFactory.make_location()),
            "latitude": coords["latitude"],
            "longitude": coords["longitude"],
            "is_default": random.choice([True, False]),
            "nickname": WeatherTestDataFactory.make_nickname() if random.random() > 0.3 else None,
        }
        defaults.update(overrides)
        return LocationSaveRequestContract(**defaults)

    @staticmethod
    def make_location_delete_request(**overrides) -> LocationDeleteRequestContract:
        """Generate valid location delete request"""
        defaults = {
            "location_id": WeatherTestDataFactory.make_location_id(),
            "user_id": WeatherTestDataFactory.make_user_id(),
        }
        defaults.update(overrides)
        return LocationDeleteRequestContract(**defaults)

    @staticmethod
    def make_location_list_request(**overrides) -> LocationListRequestContract:
        """Generate valid location list request"""
        defaults = {
            "user_id": WeatherTestDataFactory.make_user_id(),
        }
        defaults.update(overrides)
        return LocationListRequestContract(**defaults)

    # ==========================================================================
    # Response Generators
    # ==========================================================================

    @staticmethod
    def make_current_weather_response(**overrides) -> Dict[str, Any]:
        """Generate current weather response data"""
        now = WeatherTestDataFactory.make_timestamp()
        temp = WeatherTestDataFactory.make_temperature()
        defaults = {
            "location": WeatherTestDataFactory.make_location(),
            "temperature": temp,
            "feels_like": WeatherTestDataFactory.make_feels_like(temp),
            "humidity": WeatherTestDataFactory.make_humidity(),
            "condition": WeatherTestDataFactory.make_condition(),
            "description": WeatherTestDataFactory.make_description(),
            "icon": WeatherTestDataFactory.make_weather_icon(),
            "wind_speed": WeatherTestDataFactory.make_wind_speed(),
            "observed_at": now.isoformat(),
            "cached": random.choice([True, False]),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_forecast_day_response(days_ahead: int = 0, **overrides) -> Dict[str, Any]:
        """Generate single forecast day response"""
        temp_max = WeatherTestDataFactory.make_temperature()
        temp_min = temp_max - random.uniform(3, 10)
        temp_avg = (temp_max + temp_min) / 2
        defaults = {
            "date": WeatherTestDataFactory.make_forecast_date(days_ahead).isoformat(),
            "temp_max": round(temp_max, 1),
            "temp_min": round(temp_min, 1),
            "temp_avg": round(temp_avg, 1),
            "condition": WeatherTestDataFactory.make_condition(),
            "description": WeatherTestDataFactory.make_description(),
            "icon": WeatherTestDataFactory.make_weather_icon(),
            "humidity": WeatherTestDataFactory.make_humidity(),
            "wind_speed": WeatherTestDataFactory.make_wind_speed(),
            "precipitation_chance": WeatherTestDataFactory.make_precipitation_chance(),
            "precipitation_amount": WeatherTestDataFactory.make_precipitation_amount(),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_forecast_response(days: int = 5, **overrides) -> Dict[str, Any]:
        """Generate forecast response with multiple days"""
        forecast = [
            WeatherTestDataFactory.make_forecast_day_response(i)
            for i in range(days)
        ]
        now = WeatherTestDataFactory.make_timestamp()
        defaults = {
            "location": WeatherTestDataFactory.make_location(),
            "forecast": forecast,
            "generated_at": now.isoformat(),
            "cached": random.choice([True, False]),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_alert_response(**overrides) -> Dict[str, Any]:
        """Generate single weather alert response"""
        time_window = WeatherTestDataFactory.make_alert_time_window()
        defaults = {
            "id": WeatherTestDataFactory.make_alert_id(),
            "location": WeatherTestDataFactory.make_location(),
            "alert_type": WeatherTestDataFactory.make_alert_type(),
            "severity": WeatherTestDataFactory.make_alert_severity().value,
            "headline": WeatherTestDataFactory.make_alert_headline(),
            "description": WeatherTestDataFactory.make_alert_description(),
            "start_time": time_window["start_time"].isoformat(),
            "end_time": time_window["end_time"].isoformat(),
            "source": WeatherTestDataFactory.make_alert_source(),
            "created_at": WeatherTestDataFactory.make_timestamp().isoformat(),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_alerts_response(count: int = 2, **overrides) -> Dict[str, Any]:
        """Generate weather alerts list response"""
        location = WeatherTestDataFactory.make_location()
        alerts = [
            WeatherTestDataFactory.make_alert_response(location=location)
            for _ in range(count)
        ]
        now = WeatherTestDataFactory.make_timestamp()
        defaults = {
            "alerts": alerts,
            "location": location,
            "checked_at": now.isoformat(),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_location_response(**overrides) -> Dict[str, Any]:
        """Generate saved location response"""
        coords = WeatherTestDataFactory.make_realistic_coordinates()
        now = WeatherTestDataFactory.make_timestamp()
        defaults = {
            "id": WeatherTestDataFactory.make_location_id(),
            "user_id": WeatherTestDataFactory.make_user_id(),
            "location": coords.get("city", WeatherTestDataFactory.make_location()),
            "latitude": coords["latitude"],
            "longitude": coords["longitude"],
            "is_default": random.choice([True, False]),
            "nickname": WeatherTestDataFactory.make_nickname(),
            "created_at": now.isoformat(),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_location_list_response(count: int = 3, **overrides) -> Dict[str, Any]:
        """Generate location list response"""
        user_id = WeatherTestDataFactory.make_user_id()
        locations = [
            WeatherTestDataFactory.make_location_response(user_id=user_id, is_default=(i == 0))
            for i in range(count)
        ]
        defaults = {
            "locations": locations,
            "total": count,
        }
        defaults.update(overrides)
        return defaults

    # ==========================================================================
    # Invalid Data Generators (Negative Testing)
    # ==========================================================================

    @staticmethod
    def make_invalid_location_empty() -> str:
        """Generate empty location (invalid)"""
        return ""

    @staticmethod
    def make_invalid_location_whitespace() -> str:
        """Generate whitespace-only location (invalid)"""
        return "   "

    @staticmethod
    def make_invalid_location_too_long() -> str:
        """Generate location exceeding max length (invalid)"""
        return "x" * 201

    @staticmethod
    def make_invalid_user_id_empty() -> str:
        """Generate empty user ID (invalid)"""
        return ""

    @staticmethod
    def make_invalid_user_id_whitespace() -> str:
        """Generate whitespace-only user ID (invalid)"""
        return "   "

    @staticmethod
    def make_invalid_days_zero() -> int:
        """Generate zero days (invalid)"""
        return 0

    @staticmethod
    def make_invalid_days_negative() -> int:
        """Generate negative days (invalid)"""
        return -1

    @staticmethod
    def make_invalid_days_too_large() -> int:
        """Generate days exceeding max (invalid)"""
        return 17

    @staticmethod
    def make_invalid_units() -> str:
        """Generate invalid units value"""
        return "kelvin"

    @staticmethod
    def make_invalid_latitude_too_low() -> float:
        """Generate latitude below -90 (invalid)"""
        return -91.0

    @staticmethod
    def make_invalid_latitude_too_high() -> float:
        """Generate latitude above 90 (invalid)"""
        return 91.0

    @staticmethod
    def make_invalid_longitude_too_low() -> float:
        """Generate longitude below -180 (invalid)"""
        return -181.0

    @staticmethod
    def make_invalid_longitude_too_high() -> float:
        """Generate longitude above 180 (invalid)"""
        return 181.0

    @staticmethod
    def make_invalid_location_id_zero() -> int:
        """Generate zero location ID (invalid)"""
        return 0

    @staticmethod
    def make_invalid_location_id_negative() -> int:
        """Generate negative location ID (invalid)"""
        return -1

    @staticmethod
    def make_invalid_humidity_negative() -> int:
        """Generate negative humidity (invalid)"""
        return -1

    @staticmethod
    def make_invalid_humidity_over_100() -> int:
        """Generate humidity over 100 (invalid)"""
        return 101

    @staticmethod
    def make_invalid_alert_severity() -> str:
        """Generate invalid alert severity"""
        return "critical"

    # ==========================================================================
    # Edge Case Generators
    # ==========================================================================

    @staticmethod
    def make_edge_location_min_length() -> str:
        """Generate minimum length location (1 char)"""
        return "A"

    @staticmethod
    def make_edge_location_max_length() -> str:
        """Generate maximum length location (200 chars)"""
        return "x" * 200

    @staticmethod
    def make_edge_location_unicode() -> str:
        """Generate location with unicode characters"""
        return f"Tokyo \u6771\u4eac {secrets.token_hex(2)}"

    @staticmethod
    def make_edge_location_special_chars() -> str:
        """Generate location with special characters"""
        return f"St. John's, N.L. {secrets.token_hex(2)}"

    @staticmethod
    def make_edge_temperature_extreme_cold() -> float:
        """Generate extreme cold temperature"""
        return -60.0

    @staticmethod
    def make_edge_temperature_extreme_hot() -> float:
        """Generate extreme hot temperature"""
        return 55.0

    @staticmethod
    def make_edge_latitude_boundary_low() -> float:
        """Generate latitude at lower boundary (-90)"""
        return -90.0

    @staticmethod
    def make_edge_latitude_boundary_high() -> float:
        """Generate latitude at upper boundary (90)"""
        return 90.0

    @staticmethod
    def make_edge_longitude_boundary_low() -> float:
        """Generate longitude at lower boundary (-180)"""
        return -180.0

    @staticmethod
    def make_edge_longitude_boundary_high() -> float:
        """Generate longitude at upper boundary (180)"""
        return 180.0

    @staticmethod
    def make_edge_forecast_days_min() -> int:
        """Generate minimum forecast days (1)"""
        return 1

    @staticmethod
    def make_edge_forecast_days_max() -> int:
        """Generate maximum forecast days (16)"""
        return 16

    # ==========================================================================
    # Batch Generators
    # ==========================================================================

    @staticmethod
    def make_batch_current_weather_requests(count: int = 5) -> List[WeatherCurrentRequestContract]:
        """Generate multiple current weather requests"""
        return [
            WeatherTestDataFactory.make_current_weather_request()
            for _ in range(count)
        ]

    @staticmethod
    def make_batch_forecast_requests(count: int = 5) -> List[WeatherForecastRequestContract]:
        """Generate multiple forecast requests"""
        return [
            WeatherTestDataFactory.make_forecast_request()
            for _ in range(count)
        ]

    @staticmethod
    def make_batch_location_save_requests(
        count: int = 5,
        user_id: Optional[str] = None
    ) -> List[LocationSaveRequestContract]:
        """Generate multiple location save requests"""
        user = user_id or WeatherTestDataFactory.make_user_id()
        return [
            WeatherTestDataFactory.make_location_save_request(
                user_id=user,
                is_default=(i == 0)  # First one is default
            )
            for i in range(count)
        ]

    @staticmethod
    def make_batch_locations() -> List[str]:
        """Generate batch of unique locations"""
        return random.sample(WeatherTestDataFactory._CITIES, min(10, len(WeatherTestDataFactory._CITIES)))

    @staticmethod
    def make_batch_user_ids(count: int = 5) -> List[str]:
        """Generate multiple user IDs"""
        return [WeatherTestDataFactory.make_user_id() for _ in range(count)]

    # ==========================================================================
    # Event Generators
    # ==========================================================================

    @staticmethod
    def make_weather_data_fetched_event(**overrides) -> Dict[str, Any]:
        """Generate weather.data.fetched event payload"""
        defaults = {
            "location": WeatherTestDataFactory.make_location(),
            "temperature": WeatherTestDataFactory.make_temperature(),
            "condition": WeatherTestDataFactory.make_condition(),
            "units": "metric",
            "provider": random.choice(["openweathermap", "weatherapi"]),
            "timestamp": WeatherTestDataFactory.make_timestamp_iso(),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_weather_alert_created_event(**overrides) -> Dict[str, Any]:
        """Generate weather.alert.created event payload"""
        location = WeatherTestDataFactory.make_location()
        alert_count = random.randint(1, 3)
        alerts = [
            {
                "severity": WeatherTestDataFactory.make_alert_severity().value,
                "alert_type": WeatherTestDataFactory.make_alert_type(),
                "headline": WeatherTestDataFactory.make_alert_headline(),
            }
            for _ in range(alert_count)
        ]
        defaults = {
            "location": location,
            "alert_count": alert_count,
            "alerts": alerts,
            "timestamp": WeatherTestDataFactory.make_timestamp_iso(),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_weather_location_saved_event(**overrides) -> Dict[str, Any]:
        """Generate weather.location_saved event payload"""
        coords = WeatherTestDataFactory.make_realistic_coordinates()
        defaults = {
            "user_id": WeatherTestDataFactory.make_user_id(),
            "location_id": WeatherTestDataFactory.make_location_id(),
            "location": coords.get("city", WeatherTestDataFactory.make_location()),
            "latitude": coords["latitude"],
            "longitude": coords["longitude"],
            "is_default": random.choice([True, False]),
            "nickname": WeatherTestDataFactory.make_nickname(),
            "created_at": WeatherTestDataFactory.make_timestamp_iso(),
        }
        defaults.update(overrides)
        return defaults


# ============================================================================
# Request Builders (Fluent API)
# ============================================================================

class WeatherCurrentRequestBuilder:
    """
    Builder for current weather requests with fluent API.

    Usage:
        request = (WeatherCurrentRequestBuilder()
            .with_location("London")
            .with_units("metric")
            .build())
    """

    def __init__(self):
        """Initialize with factory-generated defaults"""
        self._location = WeatherTestDataFactory.make_location()
        self._units = UnitSystem.METRIC

    def with_location(self, location: str) -> 'WeatherCurrentRequestBuilder':
        """Set custom location"""
        self._location = location
        return self

    def with_units(self, units: UnitSystem) -> 'WeatherCurrentRequestBuilder':
        """Set custom units"""
        self._units = units
        return self

    def with_metric_units(self) -> 'WeatherCurrentRequestBuilder':
        """Set metric units"""
        self._units = UnitSystem.METRIC
        return self

    def with_imperial_units(self) -> 'WeatherCurrentRequestBuilder':
        """Set imperial units"""
        self._units = UnitSystem.IMPERIAL
        return self

    def with_invalid_location(self) -> 'WeatherCurrentRequestBuilder':
        """Set invalid location for negative testing"""
        self._location = WeatherTestDataFactory.make_invalid_location_empty()
        return self

    def build(self) -> WeatherCurrentRequestContract:
        """Build the request contract"""
        return WeatherCurrentRequestContract(
            location=self._location,
            units=self._units,
        )

    def build_dict(self) -> Dict[str, Any]:
        """Build as dictionary for API calls"""
        return {
            "location": self._location,
            "units": self._units.value,
        }

    def build_query_params(self) -> Dict[str, str]:
        """Build as query parameters"""
        return {
            "location": self._location,
            "units": self._units.value,
        }


class WeatherForecastRequestBuilder:
    """
    Builder for forecast requests with fluent API.

    Usage:
        request = (WeatherForecastRequestBuilder()
            .with_location("Tokyo")
            .with_days(7)
            .build())
    """

    def __init__(self):
        """Initialize with factory-generated defaults"""
        self._location = WeatherTestDataFactory.make_location()
        self._days = 5
        self._units = UnitSystem.METRIC

    def with_location(self, location: str) -> 'WeatherForecastRequestBuilder':
        """Set custom location"""
        self._location = location
        return self

    def with_days(self, days: int) -> 'WeatherForecastRequestBuilder':
        """Set forecast days"""
        self._days = days
        return self

    def with_units(self, units: UnitSystem) -> 'WeatherForecastRequestBuilder':
        """Set custom units"""
        self._units = units
        return self

    def with_max_days(self) -> 'WeatherForecastRequestBuilder':
        """Set maximum forecast days (16)"""
        self._days = 16
        return self

    def with_min_days(self) -> 'WeatherForecastRequestBuilder':
        """Set minimum forecast days (1)"""
        self._days = 1
        return self

    def with_invalid_days(self) -> 'WeatherForecastRequestBuilder':
        """Set invalid days for negative testing"""
        self._days = WeatherTestDataFactory.make_invalid_days_too_large()
        return self

    def build(self) -> WeatherForecastRequestContract:
        """Build the request contract"""
        return WeatherForecastRequestContract(
            location=self._location,
            days=self._days,
            units=self._units,
        )

    def build_dict(self) -> Dict[str, Any]:
        """Build as dictionary"""
        return {
            "location": self._location,
            "days": self._days,
            "units": self._units.value,
        }

    def build_query_params(self) -> Dict[str, str]:
        """Build as query parameters"""
        return {
            "location": self._location,
            "days": str(self._days),
            "units": self._units.value,
        }


class LocationSaveRequestBuilder:
    """
    Builder for location save requests with fluent API.

    Usage:
        request = (LocationSaveRequestBuilder()
            .with_user_id("user_123")
            .with_location("New York")
            .as_default()
            .build())
    """

    def __init__(self):
        """Initialize with factory-generated defaults"""
        coords = WeatherTestDataFactory.make_realistic_coordinates()
        self._user_id = WeatherTestDataFactory.make_user_id()
        self._location = coords.get("city", WeatherTestDataFactory.make_location())
        self._latitude: Optional[float] = coords["latitude"]
        self._longitude: Optional[float] = coords["longitude"]
        self._is_default = False
        self._nickname: Optional[str] = None

    def with_user_id(self, user_id: str) -> 'LocationSaveRequestBuilder':
        """Set user ID"""
        self._user_id = user_id
        return self

    def with_location(self, location: str) -> 'LocationSaveRequestBuilder':
        """Set location name"""
        self._location = location
        return self

    def with_coordinates(self, latitude: float, longitude: float) -> 'LocationSaveRequestBuilder':
        """Set coordinates"""
        self._latitude = latitude
        self._longitude = longitude
        return self

    def without_coordinates(self) -> 'LocationSaveRequestBuilder':
        """Remove coordinates"""
        self._latitude = None
        self._longitude = None
        return self

    def as_default(self) -> 'LocationSaveRequestBuilder':
        """Set as default location"""
        self._is_default = True
        return self

    def not_default(self) -> 'LocationSaveRequestBuilder':
        """Set as non-default location"""
        self._is_default = False
        return self

    def with_nickname(self, nickname: str) -> 'LocationSaveRequestBuilder':
        """Set nickname"""
        self._nickname = nickname
        return self

    def without_nickname(self) -> 'LocationSaveRequestBuilder':
        """Remove nickname"""
        self._nickname = None
        return self

    def with_invalid_user_id(self) -> 'LocationSaveRequestBuilder':
        """Set invalid user ID for negative testing"""
        self._user_id = WeatherTestDataFactory.make_invalid_user_id_empty()
        return self

    def with_invalid_location(self) -> 'LocationSaveRequestBuilder':
        """Set invalid location for negative testing"""
        self._location = WeatherTestDataFactory.make_invalid_location_empty()
        return self

    def with_invalid_latitude(self) -> 'LocationSaveRequestBuilder':
        """Set invalid latitude for negative testing"""
        self._latitude = WeatherTestDataFactory.make_invalid_latitude_too_high()
        return self

    def build(self) -> LocationSaveRequestContract:
        """Build the request contract"""
        return LocationSaveRequestContract(
            user_id=self._user_id,
            location=self._location,
            latitude=self._latitude,
            longitude=self._longitude,
            is_default=self._is_default,
            nickname=self._nickname,
        )

    def build_dict(self) -> Dict[str, Any]:
        """Build as dictionary for API calls"""
        data = {
            "user_id": self._user_id,
            "location": self._location,
            "is_default": self._is_default,
        }
        if self._latitude is not None:
            data["latitude"] = self._latitude
        if self._longitude is not None:
            data["longitude"] = self._longitude
        if self._nickname is not None:
            data["nickname"] = self._nickname
        return data


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Enumerations
    "UnitSystem",
    "WeatherCondition",
    "AlertSeverity",
    "AlertType",
    # Request Contracts
    "WeatherCurrentRequestContract",
    "WeatherForecastRequestContract",
    "WeatherAlertQueryContract",
    "LocationSaveRequestContract",
    "LocationDeleteRequestContract",
    "LocationListRequestContract",
    # Response Contracts
    "WeatherCurrentResponseContract",
    "WeatherForecastResponseContract",
    "ForecastDayContract",
    "WeatherAlertResponseContract",
    "WeatherAlertContract",
    "LocationResponseContract",
    "LocationListResponseContract",
    "ErrorResponseContract",
    # Event Contracts
    "WeatherDataFetchedEventContract",
    "WeatherAlertCreatedEventContract",
    "WeatherLocationSavedEventContract",
    # Factory
    "WeatherTestDataFactory",
    # Builders
    "WeatherCurrentRequestBuilder",
    "WeatherForecastRequestBuilder",
    "LocationSaveRequestBuilder",
]
