# Weather Service System Contract

> Layer 6: Implementation Patterns
> Generated: 2025-12-17
> Service: weather_service
> Port: 8241

This document defines HOW weather_service implements the 12 standard CDD patterns, bridging the Logic Contract (business rules) to actual code implementation.

---

## Table of Contents

1. [Architecture Pattern](#1-architecture-pattern)
2. [Dependency Injection Pattern](#2-dependency-injection-pattern)
3. [Event Publishing Pattern](#3-event-publishing-pattern)
4. [Error Handling Pattern](#4-error-handling-pattern)
5. [Client Pattern](#5-client-pattern-external-apis)
6. [Repository Pattern](#6-repository-pattern)
7. [Service Registration Pattern](#7-service-registration-pattern)
8. [Migration Pattern](#8-migration-pattern)
9. [Lifecycle Pattern](#9-lifecycle-pattern)
10. [Configuration Pattern](#10-configuration-pattern)
11. [Logging Pattern](#11-logging-pattern)
12. [Event Subscription Pattern](#12-event-subscription-pattern)

---

## 1. Architecture Pattern

### Service Layer Structure

```
microservices/weather_service/
├── __init__.py
├── main.py                      # FastAPI app, routes, DI setup, lifespan
├── weather_service.py           # Business logic layer
├── weather_repository.py        # Data access layer (PostgreSQL + Redis)
├── models.py                    # Pydantic models (request/response)
├── protocols.py                 # DI interfaces (Protocol classes) [TO CREATE]
├── factory.py                   # DI factory [TO CREATE]
├── routes_registry.py           # Consul route metadata
├── clients/                     # External API clients [TO CREATE]
│   ├── __init__.py
│   ├── openweathermap_client.py
│   └── weatherapi_client.py
├── events/
│   ├── __init__.py
│   ├── models.py                # Event Pydantic models
│   └── handlers.py              # Event subscription handlers
└── migrations/
    └── 001_migrate_to_weather_schema.sql
```

### Layer Responsibilities

| Layer | File | Responsibility | Dependencies |
|-------|------|----------------|--------------|
| **HTTP** | `main.py` | Routes, request validation, DI wiring | FastAPI, WeatherService |
| **Service** | `weather_service.py` | Business logic, caching strategy, provider orchestration | Repository, EventBus, HTTP Client |
| **Repository** | `weather_repository.py` | Data access (PostgreSQL + Redis cache) | AsyncPostgresClient, Redis |
| **Events** | `events/` | Event publishing/subscription | NATS |
| **Models** | `models.py` | Request/Response schemas, domain models | Pydantic |

### Weather Service Unique Architecture

Weather service implements a **multi-provider architecture** with **two-tier caching**:

```
┌─────────────────────────────────────────────────────────────────┐
│                        HTTP Layer (main.py)                      │
│  GET /current, GET /forecast, GET /alerts, POST/GET/DELETE /loc │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Service Layer (weather_service.py)               │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐    │
│  │ Cache-First │  │   Provider   │  │   Event Publishing  │    │
│  │   Strategy  │  │   Failover   │  │  (weather.fetched)  │    │
│  └─────────────┘  └──────────────┘  └─────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
           │                    │
           ▼                    ▼
┌──────────────────┐  ┌─────────────────────────────────────────┐
│  Repository      │  │        External Weather Providers        │
│ ┌──────────────┐ │  │  ┌────────────────┐ ┌────────────────┐  │
│ │ Redis (Hot)  │ │  │  │ OpenWeatherMap │ │  WeatherAPI    │  │
│ │  TTL: 15min  │ │  │  │   (Primary)    │ │   (Fallback)   │  │
│ └──────────────┘ │  │  └────────────────┘ └────────────────┘  │
│ ┌──────────────┐ │  └─────────────────────────────────────────┘
│ │PostgreSQL    │ │
│ │(Warm Backup) │ │
│ └──────────────┘ │
└──────────────────┘
```

---

## 2. Dependency Injection Pattern

### Protocol Definition (`protocols.py`) - TO BE CREATED

```python
"""
Weather Service Protocols - DI Interfaces

All dependencies defined as Protocol classes for testability.
"""
from typing import Protocol, runtime_checkable, Optional, Dict, Any, List
from datetime import datetime


@runtime_checkable
class WeatherRepositoryProtocol(Protocol):
    """Repository interface for weather data access"""

    async def get_cached_weather(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached weather data by key"""
        ...

    async def set_cached_weather(
        self, cache_key: str, data: Dict[str, Any], ttl_seconds: int
    ) -> bool:
        """Cache weather data with TTL"""
        ...

    async def clear_location_cache(self, location: str) -> None:
        """Clear all cache entries for a location"""
        ...

    async def save_location(self, location_data: Dict[str, Any]) -> Optional[Any]:
        """Save user's favorite location"""
        ...

    async def get_user_locations(self, user_id: str) -> List[Any]:
        """Get all locations for a user"""
        ...

    async def get_default_location(self, user_id: str) -> Optional[Any]:
        """Get user's default location"""
        ...

    async def delete_location(self, location_id: int, user_id: str) -> bool:
        """Delete a saved location"""
        ...

    async def save_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Save weather alert"""
        ...

    async def get_active_alerts(self, location: str) -> List[Dict[str, Any]]:
        """Get active alerts for location"""
        ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Event bus interface for NATS publishing"""

    async def publish_event(self, event: Any) -> None:
        """Publish event to NATS"""
        ...

    async def connect(self) -> None:
        """Connect to NATS"""
        ...

    async def close(self) -> None:
        """Disconnect from NATS"""
        ...


@runtime_checkable
class WeatherProviderProtocol(Protocol):
    """External weather provider interface"""

    async def get_current_weather(
        self, location: str, units: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch current weather from provider"""
        ...

    async def get_forecast(
        self, location: str, days: int
    ) -> Optional[Dict[str, Any]]:
        """Fetch weather forecast from provider"""
        ...

    async def close(self) -> None:
        """Close HTTP client connections"""
        ...


@runtime_checkable
class CacheProtocol(Protocol):
    """Cache interface for Redis operations"""

    def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        ...

    def setex(self, key: str, ttl: int, value: str) -> None:
        """Set value with TTL in seconds"""
        ...

    def delete(self, key: str) -> None:
        """Delete key from cache"""
        ...

    def scan_iter(self, match: str) -> Any:
        """Scan keys matching pattern"""
        ...
```

### Factory Implementation (`factory.py`) - TO BE CREATED

```python
"""
Weather Service Factory - Dependency Injection Setup

Creates service instances with real or mock dependencies.
"""
from typing import Optional
from microservices.weather_service.weather_service import WeatherService
from microservices.weather_service.weather_repository import WeatherRepository
from microservices.weather_service.protocols import (
    WeatherRepositoryProtocol,
    EventBusProtocol,
    WeatherProviderProtocol,
)
from core.config_manager import ConfigManager


class WeatherServiceFactory:
    """Factory for creating WeatherService with dependencies"""

    @staticmethod
    def create_service(
        config: Optional[ConfigManager] = None,
        repository: Optional[WeatherRepositoryProtocol] = None,
        event_bus: Optional[EventBusProtocol] = None,
    ) -> WeatherService:
        """
        Create WeatherService instance.

        Args:
            config: Configuration manager instance
            repository: Repository implementation (default: real repository)
            event_bus: Event bus implementation (default: real NATS)

        Returns:
            Configured WeatherService instance
        """
        if config is None:
            config = ConfigManager("weather_service")

        # WeatherService creates its own repository internally
        # For DI, we would need to refactor to accept repository
        service = WeatherService(event_bus=event_bus)

        return service

    @staticmethod
    def create_for_testing(
        mock_repository: WeatherRepositoryProtocol,
        mock_event_bus: Optional[EventBusProtocol] = None,
    ) -> WeatherService:
        """
        Create service with mock dependencies for testing.

        Note: Current WeatherService creates repository internally.
        Full DI requires refactoring weather_service.py constructor.
        """
        # TODO: Refactor WeatherService to accept repository via constructor
        return WeatherService(event_bus=mock_event_bus)


def create_weather_service(
    config: Optional[ConfigManager] = None,
    event_bus: Optional[EventBusProtocol] = None,
) -> WeatherService:
    """Convenience function for creating weather service"""
    return WeatherServiceFactory.create_service(
        config=config,
        event_bus=event_bus,
    )
```

### Current Service Implementation Pattern

```python
# File: weather_service.py (Current Implementation)
class WeatherService:
    """Weather service business logic"""

    def __init__(self, event_bus=None):
        # Repository created internally (not injected)
        self.repository = WeatherRepository()
        self.event_bus = event_bus

        # External API configuration via environment
        self.openweather_api_key = os.getenv("OPENWEATHER_API_KEY", "")
        self.weatherapi_key = os.getenv("WEATHERAPI_KEY", "")

        # Cache TTL settings
        self.current_weather_ttl = int(os.getenv("WEATHER_CACHE_TTL", "900"))
        self.forecast_ttl = int(os.getenv("FORECAST_CACHE_TTL", "1800"))
        self.alerts_ttl = int(os.getenv("ALERTS_CACHE_TTL", "600"))

        # HTTP client for external APIs
        self.http_client = httpx.AsyncClient(timeout=30.0)
```

### DI Migration Path

To fully implement DI pattern:

1. **Phase 1**: Create `protocols.py` with interface definitions
2. **Phase 2**: Create `factory.py` for service instantiation
3. **Phase 3**: Refactor `WeatherService.__init__` to accept:
   - `repository: WeatherRepositoryProtocol`
   - `openweathermap_client: WeatherProviderProtocol`
   - `weatherapi_client: WeatherProviderProtocol`
4. **Phase 4**: Update `main.py` to use factory

---

## 3. Event Publishing Pattern

### Event Types Published by Weather Service

| Event Type | Subject | Trigger | Data |
|------------|---------|---------|------|
| `WEATHER_DATA_FETCHED` | `weather.data.fetched` | Cache miss, fresh fetch | location, temperature, condition, provider |
| `WEATHER_ALERT_CREATED` | `weather.alert.created` | Active alerts detected | location, alert_count, alerts[] |
| `WEATHER_LOCATION_SAVED` | `weather.location.saved` | User saves location | user_id, location_id, location, is_default |

### Event Model Definition

```python
# File: events/models.py (Current Implementation)
class WeatherLocationSavedEventData(BaseModel):
    """Event: weather.location_saved"""
    user_id: str
    location_id: int
    location: str
    latitude: float
    longitude: float
    is_default: bool = False
    nickname: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WeatherAlertEventData(BaseModel):
    """Event: weather.alert_issued"""
    user_id: str
    location: str
    alert_type: str
    severity: str
    description: str
    start_time: datetime
    end_time: Optional[datetime] = None
    issued_at: datetime = Field(default_factory=datetime.utcnow)
```

### Event Publishing in Service Layer

```python
# File: weather_service.py - Publishing Pattern
async def get_current_weather(self, request: WeatherCurrentRequest):
    # 1. Check cache first
    cached = await self.repository.get_cached_weather(cache_key)
    if cached:
        return cached  # No event on cache hit

    # 2. Fetch from external API
    weather_data = await self._fetch_current_weather(...)

    # 3. Cache the result
    await self.repository.set_cached_weather(cache_key, weather_data, ttl)

    # 4. Publish event AFTER successful operation
    if self.event_bus:
        try:
            event = Event(
                event_type=EventType.WEATHER_DATA_FETCHED,
                source=ServiceSource.WEATHER_SERVICE,
                data={
                    "location": request.location,
                    "temperature": weather_data.get("temperature"),
                    "condition": weather_data.get("condition"),
                    "units": request.units,
                    "provider": self.default_provider,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            await self.event_bus.publish_event(event)
        except Exception as e:
            # Log but don't fail the request
            logger.error(f"Failed to publish event: {e}")

    return weather_data
```

### Event Publishing Rules

| Rule | Implementation |
|------|----------------|
| **Publish after success** | Events published only after data persisted/cached |
| **Fire-and-forget** | Event publish failures logged but don't fail request |
| **Idempotent events** | Include timestamp for deduplication |
| **Correlation ID** | Propagate via request context (TODO) |

---

## 4. Error Handling Pattern

### Custom Exceptions (To Be Defined)

```python
"""
Weather Service Exceptions - Domain-specific errors
"""

class WeatherServiceError(Exception):
    """Base exception for weather service"""
    pass


class WeatherNotFoundError(WeatherServiceError):
    """Raised when weather data is not available for location"""
    def __init__(self, location: str):
        self.location = location
        super().__init__(f"Weather data not found for: {location}")


class ProviderError(WeatherServiceError):
    """Raised when external weather provider fails"""
    def __init__(self, provider: str, message: str):
        self.provider = provider
        super().__init__(f"Provider {provider} error: {message}")


class ProviderConfigurationError(WeatherServiceError):
    """Raised when provider API key is missing"""
    def __init__(self, provider: str):
        self.provider = provider
        super().__init__(f"API key not configured for: {provider}")


class LocationNotFoundError(WeatherServiceError):
    """Raised when saved location not found"""
    def __init__(self, location_id: int):
        self.location_id = location_id
        super().__init__(f"Location not found: {location_id}")


class InvalidCoordinatesError(WeatherServiceError):
    """Raised when coordinates are invalid"""
    def __init__(self, latitude: float, longitude: float):
        self.latitude = latitude
        self.longitude = longitude
        super().__init__(f"Invalid coordinates: ({latitude}, {longitude})")


class ForecastDaysExceededError(WeatherServiceError):
    """Raised when forecast days exceed limit"""
    def __init__(self, requested: int, maximum: int):
        self.requested = requested
        self.maximum = maximum
        super().__init__(f"Forecast days {requested} exceeds maximum {maximum}")
```

### HTTP Error Mapping (main.py - Current Pattern)

```python
# Current implementation uses direct HTTPException
@app.get("/api/v1/weather/current")
async def get_current_weather(...):
    try:
        weather = await microservice.service.get_current_weather(request)
        if not weather:
            raise HTTPException(status_code=404, detail="Weather data not found")
        return weather
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current weather: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

### Recommended Error Mapping Pattern

```python
# Exception to HTTP status mapping
EXCEPTION_STATUS_MAP = {
    WeatherNotFoundError: 404,
    LocationNotFoundError: 404,
    ProviderError: 502,           # Bad Gateway - upstream failure
    ProviderConfigurationError: 503,  # Service unavailable
    InvalidCoordinatesError: 422,
    ForecastDaysExceededError: 422,
}

@app.exception_handler(WeatherServiceError)
async def weather_error_handler(request, exc: WeatherServiceError):
    status_code = EXCEPTION_STATUS_MAP.get(type(exc), 500)
    return JSONResponse(
        status_code=status_code,
        content={
            "error": type(exc).__name__,
            "message": str(exc),
            "detail": getattr(exc, "__dict__", {})
        }
    )
```

---

## 5. Client Pattern (External APIs)

### Weather Provider Clients

Weather service differs from other services - it primarily consumes **external APIs** rather than internal microservices.

#### OpenWeatherMap Client (Current - Inline Implementation)

```python
# File: weather_service.py - Current inline implementation
async def _fetch_openweathermap_current(
    self, location: str, units: str
) -> Optional[Dict[str, Any]]:
    """Fetch current weather from OpenWeatherMap"""
    try:
        if not self.openweather_api_key:
            logger.error("OpenWeatherMap API key not configured")
            return None

        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": location,
            "appid": self.openweather_api_key,
            "units": units
        }

        response = await self.http_client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        # Transform to internal format
        return {
            "location": data["name"],
            "temperature": data["main"]["temp"],
            "feels_like": data["main"]["feels_like"],
            "humidity": data["main"]["humidity"],
            "condition": data["weather"][0]["main"].lower(),
            "description": data["weather"][0]["description"],
            "icon": data["weather"][0]["icon"],
            "wind_speed": data.get("wind", {}).get("speed"),
            "observed_at": datetime.utcnow(),
        }

    except httpx.HTTPStatusError as e:
        logger.error(f"OpenWeatherMap API error: {e.response.status_code}")
        return None
    except Exception as e:
        logger.error(f"Error fetching weather: {e}")
        return None
```

#### Recommended Client Pattern (To Be Extracted)

```python
# File: clients/openweathermap_client.py (TO CREATE)
"""
OpenWeatherMap Client - External API integration
"""
import httpx
import os
from typing import Optional, Dict, Any
from datetime import datetime


class OpenWeatherMapClient:
    """Client for OpenWeatherMap API"""

    BASE_URL = "https://api.openweathermap.org/data/2.5"

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.getenv("OPENWEATHER_API_KEY", "")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                timeout=30.0,
                headers={"User-Agent": "isA-WeatherService/1.0"}
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def is_configured(self) -> bool:
        """Check if API key is configured"""
        return bool(self._api_key)

    async def get_current_weather(
        self, location: str, units: str = "metric"
    ) -> Optional[Dict[str, Any]]:
        """
        Get current weather for location.

        Args:
            location: City name or "lat,lon" coordinates
            units: "metric" (Celsius) or "imperial" (Fahrenheit)

        Returns:
            Normalized weather data or None if failed
        """
        if not self.is_configured:
            return None

        try:
            client = await self._get_client()
            response = await client.get(
                "/weather",
                params={"q": location, "appid": self._api_key, "units": units}
            )
            response.raise_for_status()
            data = response.json()

            return self._normalize_current(data)
        except httpx.HTTPStatusError:
            return None
        except Exception:
            return None

    async def get_forecast(
        self, location: str, days: int = 5
    ) -> Optional[Dict[str, Any]]:
        """Get weather forecast"""
        if not self.is_configured:
            return None

        try:
            client = await self._get_client()
            # OpenWeatherMap free: 3-hour intervals, max 5 days
            cnt = min(days * 8, 40)

            response = await client.get(
                "/forecast",
                params={
                    "q": location,
                    "appid": self._api_key,
                    "units": "metric",
                    "cnt": cnt
                }
            )
            response.raise_for_status()
            data = response.json()

            return self._normalize_forecast(data, days)
        except Exception:
            return None

    def _normalize_current(self, data: Dict) -> Dict[str, Any]:
        """Transform OpenWeatherMap response to internal format"""
        return {
            "location": data["name"],
            "temperature": data["main"]["temp"],
            "feels_like": data["main"]["feels_like"],
            "humidity": data["main"]["humidity"],
            "condition": data["weather"][0]["main"].lower(),
            "description": data["weather"][0]["description"],
            "icon": data["weather"][0]["icon"],
            "wind_speed": data.get("wind", {}).get("speed"),
            "observed_at": datetime.utcnow(),
        }

    def _normalize_forecast(self, data: Dict, days: int) -> Dict[str, Any]:
        """Transform forecast response to internal format"""
        # Aggregate 3-hour intervals to daily forecasts
        # ... implementation ...
        pass
```

### Client Configuration

| Provider | Environment Variable | Base URL | Rate Limit |
|----------|---------------------|----------|------------|
| OpenWeatherMap | `OPENWEATHER_API_KEY` | `api.openweathermap.org/data/2.5` | 60/min (free) |
| WeatherAPI | `WEATHERAPI_KEY` | `api.weatherapi.com/v1` | 1M/month (free) |

---

## 6. Repository Pattern

### WeatherRepository Implementation

```python
# File: weather_repository.py (Current Implementation)
class WeatherRepository:
    """Weather data access layer - PostgreSQL + Redis"""

    def __init__(self, config: Optional[ConfigManager] = None):
        # Service discovery for PostgreSQL
        host, port = config.discover_service(
            service_name="postgres_grpc_service",
            default_host="isa-postgres-grpc",
            default_port=50061,
        )

        self.db = AsyncPostgresClient(host=host, port=port, user_id="weather_service")
        self.schema = "weather"
        self.locations_table = "weather_locations"
        self.cache_table = "weather_cache"
        self.alerts_table = "weather_alerts"

        # Redis for hot cache (optional)
        self.redis = None
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis = redis.from_url(redis_url, decode_responses=True)
        except Exception:
            logger.warning("Redis not available, using database cache")
```

### Two-Tier Caching Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                     Cache Lookup Flow                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Request ──► Redis (Hot)  ──HIT──► Return cached data          │
│                   │                                              │
│                   │ MISS                                         │
│                   ▼                                              │
│              PostgreSQL (Warm) ──HIT──► Return + refresh Redis  │
│                   │                                              │
│                   │ MISS                                         │
│                   ▼                                              │
│            External API ──► Cache in Redis + PostgreSQL         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Cache Operations

```python
async def get_cached_weather(self, cache_key: str) -> Optional[Dict[str, Any]]:
    """Get cached weather data - Redis first, then PostgreSQL"""
    # 1. Try Redis (hot cache)
    if self.redis:
        cached = self.redis.get(cache_key)
        if cached:
            return json.loads(cached)

    # 2. Fallback to PostgreSQL (warm cache)
    query = """
        SELECT data FROM weather.weather_cache
        WHERE cache_key = $1 AND expires_at >= $2
    """
    results = await self.db.query(query, [cache_key, datetime.now(timezone.utc)])
    if results:
        return results[0].get("data")

    return None

async def set_cached_weather(
    self, cache_key: str, data: Dict[str, Any], ttl_seconds: int
) -> bool:
    """Cache weather data in both Redis and PostgreSQL"""
    # 1. Set in Redis with TTL
    if self.redis:
        self.redis.setex(cache_key, ttl_seconds, json.dumps(data))

    # 2. Upsert in PostgreSQL
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    query = """
        INSERT INTO weather.weather_cache (cache_key, location, data, expires_at, ...)
        VALUES ($1, $2, $3, $4, ...)
        ON CONFLICT (cache_key) DO UPDATE
        SET data = EXCLUDED.data, expires_at = EXCLUDED.expires_at
    """
    await self.db.execute(query, params)
    return True
```

### Repository Methods Summary

| Method | Table | Description |
|--------|-------|-------------|
| `get_cached_weather` | `weather_cache` | Two-tier cache lookup |
| `set_cached_weather` | `weather_cache` | Write-through to Redis + PostgreSQL |
| `clear_location_cache` | `weather_cache` | Pattern-based cache invalidation |
| `save_location` | `weather_locations` | Save with default management |
| `get_user_locations` | `weather_locations` | List with default first |
| `get_default_location` | `weather_locations` | Single default lookup |
| `delete_location` | `weather_locations` | Owner-verified deletion |
| `save_alert` | `weather_alerts` | Store incoming alerts |
| `get_active_alerts` | `weather_alerts` | Time-filtered alert query |

---

## 7. Service Registration Pattern

### Routes Registry (`routes_registry.py`)

```python
# File: routes_registry.py (Current Implementation)
SERVICE_ROUTES = [
    {
        "path": "/health",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Service health check"
    },
    {
        "path": "/api/v1/weather/current",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Get current weather for a location"
    },
    {
        "path": "/api/v1/weather/forecast",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Get weather forecast"
    },
    {
        "path": "/api/v1/weather/alerts",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Get weather alerts"
    },
    {
        "path": "/api/v1/weather/locations",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Save favorite location"
    },
    {
        "path": "/api/v1/weather/locations/{user_id}",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get user locations"
    },
    {
        "path": "/api/v1/weather/locations/{location_id}",
        "methods": ["DELETE"],
        "auth_required": True,
        "description": "Delete location"
    },
]

SERVICE_METADATA = {
    "service_name": "weather_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "weather", "data"],
    "capabilities": [
        "current_weather",
        "weather_forecast",
        "weather_alerts",
        "location_management",
        "weather_caching"
    ]
}
```

### Consul Registration in main.py

```python
async def initialize(self):
    # Consul service registration
    if config.consul_enabled:
        route_meta = get_routes_for_consul()
        consul_meta = {
            "version": SERVICE_METADATA["version"],
            "capabilities": ",".join(SERVICE_METADATA["capabilities"]),
            **route_meta,
        }

        self.consul_registry = ConsulRegistry(
            service_name=SERVICE_METADATA["service_name"],
            service_port=config.service_port,
            consul_host=config.consul_host,
            consul_port=config.consul_port,
            tags=SERVICE_METADATA["tags"],
            meta=consul_meta,
            health_check_type="http",
        )
        self.consul_registry.register()
```

### Route Metadata for Consul

```python
def get_routes_for_consul() -> Dict[str, Any]:
    """Compact route metadata for Consul (512 char limit per field)"""
    return {
        "route_count": "8",
        "base_path": "/api/v1/weather",
        "health": "root,health",
        "weather": "current,forecast,alerts",
        "locations": "/,/{user_id},/{location_id}",
        "methods": "GET,POST,DELETE",
        "public_count": "5",
        "protected_count": "3",
    }
```

---

## 8. Migration Pattern

### Migration Files

```
microservices/weather_service/migrations/
└── 001_migrate_to_weather_schema.sql   # Initial schema creation
```

### Schema Definition

```sql
-- File: 001_migrate_to_weather_schema.sql
-- Create weather schema
CREATE SCHEMA IF NOT EXISTS weather;

-- 1. weather_locations - User favorite locations
CREATE TABLE weather.weather_locations (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,      -- Cross-service reference (no FK)
    location VARCHAR(255) NOT NULL,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    is_default BOOLEAN DEFAULT FALSE,
    nickname VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. weather_cache - Two-tier cache warm storage
CREATE TABLE weather.weather_cache (
    id SERIAL PRIMARY KEY,
    cache_key VARCHAR(255) UNIQUE NOT NULL,
    location VARCHAR(255) NOT NULL,
    data JSONB NOT NULL,                -- Weather data JSON
    cached_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. weather_alerts - Active weather alerts
CREATE TABLE weather.weather_alerts (
    id SERIAL PRIMARY KEY,
    location VARCHAR(255) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,    -- storm, flood, heat, etc.
    severity VARCHAR(20) NOT NULL,      -- info, warning, severe, extreme
    headline VARCHAR(500) NOT NULL,
    description TEXT,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    source VARCHAR(100) NOT NULL,       -- Alert provider
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_locations_user_id ON weather.weather_locations(user_id);
CREATE INDEX idx_locations_is_default ON weather.weather_locations(user_id, is_default);
CREATE INDEX idx_cache_key ON weather.weather_cache(cache_key);
CREATE INDEX idx_cache_expires_at ON weather.weather_cache(expires_at);
CREATE INDEX idx_alerts_location ON weather.weather_alerts(location);
CREATE INDEX idx_alerts_time_range ON weather.weather_alerts(location, end_time);
```

### Running Migrations

```bash
# Via postgres-grpc service
kubectl port-forward svc/postgres-grpc 50051:50051

# Execute migration
python -c "
from core.postgres_grpc_client import PostgresGRPCClient
import asyncio

async def run():
    client = PostgresGRPCClient()
    with open('microservices/weather_service/migrations/001_migrate_to_weather_schema.sql') as f:
        await client.execute_raw(f.read())
    print('Migration complete')

asyncio.run(run())
"
```

---

## 9. Lifecycle Pattern

### WeatherMicroservice Class

```python
# File: main.py (Current Implementation)
class WeatherMicroservice:
    """Weather microservice core class"""

    def __init__(self):
        self.service = None
        self.repository = None
        self.event_bus = None
        self.consul_registry = None

    async def initialize(self):
        """Initialize the microservice"""
        logger.info("Initializing weather microservice...")

        # 1. Initialize event bus
        try:
            self.event_bus = await get_event_bus("weather_service")
            logger.info("Event bus initialized")
        except Exception as e:
            logger.warning(f"Event bus init failed: {e}")
            self.event_bus = None

        # 2. Create repository and service
        self.repository = WeatherRepository(config=config_manager)
        self.service = WeatherService(event_bus=self.event_bus)

        # 3. Consul registration
        if config.consul_enabled:
            # ... registration logic ...
            self.consul_registry.register()

        logger.info("Weather microservice initialized")

    async def shutdown(self):
        """Shutdown the microservice"""
        # 1. Deregister from Consul
        if self.consul_registry:
            self.consul_registry.deregister()

        # 2. Close event bus
        if self.event_bus:
            await self.event_bus.close()

        # 3. Close service (HTTP client)
        if self.service:
            await self.service.close()

        logger.info("Weather microservice shutdown completed")
```

### FastAPI Lifespan

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    await microservice.initialize()

    yield  # Application runs

    # Shutdown
    await microservice.shutdown()

# Create FastAPI app
app = FastAPI(
    title="Weather Service",
    description="Weather data fetching and caching",
    version="1.0.0",
    lifespan=lifespan,
)
```

### Initialization Order

```
┌─────────────────────────────────────────────────────────────────┐
│                    Startup Sequence                              │
├─────────────────────────────────────────────────────────────────┤
│ 1. ConfigManager initialization (module level)                   │
│ 2. Logger setup (module level)                                   │
│ 3. lifespan() called by FastAPI                                  │
│    ├── 3.1 Event bus connection (NATS)                          │
│    ├── 3.2 Repository initialization (DB + Redis connections)   │
│    ├── 3.3 Service layer initialization                         │
│    └── 3.4 Consul service registration                          │
│ 4. FastAPI ready to serve requests                               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    Shutdown Sequence                             │
├─────────────────────────────────────────────────────────────────┤
│ 1. Consul deregistration (remove from service mesh)              │
│ 2. Event bus disconnection (NATS)                                │
│ 3. Service cleanup (close HTTP clients)                          │
│ 4. Repository cleanup (close DB connections)                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 10. Configuration Pattern

### ConfigManager Usage

```python
# File: main.py (Current Implementation)
from core.config_manager import ConfigManager

# Initialize at module level
config_manager = ConfigManager("weather_service")
config = config_manager.get_service_config()

# Available config properties
config.service_name      # "weather_service"
config.service_port      # 8241
config.service_host      # "0.0.0.0"
config.debug             # True/False
config.log_level         # "INFO"
config.consul_enabled    # True/False
config.consul_host       # "consul"
config.consul_port       # 8500
config.nats_url          # "nats://nats:4222"
```

### Weather-Specific Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENWEATHER_API_KEY` | `""` | OpenWeatherMap API key |
| `WEATHERAPI_KEY` | `""` | WeatherAPI API key |
| `WEATHER_PROVIDER` | `openweathermap` | Default provider |
| `WEATHER_CACHE_TTL` | `900` | Current weather cache TTL (15 min) |
| `FORECAST_CACHE_TTL` | `1800` | Forecast cache TTL (30 min) |
| `ALERTS_CACHE_TTL` | `600` | Alerts cache TTL (10 min) |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection URL |

### Service Port Assignment

```
Weather Service: 8241
```

### Service Discovery Pattern

```python
# Repository uses ConfigManager for service discovery
host, port = config.discover_service(
    service_name="postgres_grpc_service",
    default_host="isa-postgres-grpc",
    default_port=50061,
    env_host_key="POSTGRES_HOST",
    env_port_key="POSTGRES_PORT",
)
```

---

## 11. Logging Pattern

### Logger Setup

```python
# File: main.py (Current Implementation)
from core.logger import setup_service_logger

# Setup at module level
app_logger = setup_service_logger("weather_service")
logger = app_logger
```

### Logging Usage Patterns

```python
# Informational messages
logger.info("Weather service initialized")
logger.info(f"Cached in Redis: {cache_key} (TTL: {ttl}s)")

# Warning messages (degraded but working)
logger.warning(f"Event bus init failed: {e}. Continuing without events.")
logger.warning("Redis not available, using database cache")

# Error messages (failures)
logger.error(f"Error getting current weather: {e}")
logger.error(f"OpenWeatherMap API error: {status_code}")
logger.error(f"Failed to publish event: {e}")

# Debug messages (verbose)
logger.debug(f"Cache hit (Redis): {cache_key}")
logger.debug(f"Cache miss: {cache_key}")
```

### Structured Logging Context

```python
# Recommended pattern with context
logger.info(
    "Weather data fetched",
    extra={
        "location": location,
        "provider": provider,
        "cached": False,
        "response_time_ms": elapsed_ms,
    }
)

logger.error(
    "Provider request failed",
    extra={
        "provider": "openweathermap",
        "location": location,
        "status_code": response.status_code,
    },
    exc_info=True
)
```

---

## 12. Event Subscription Pattern

### Current Implementation

Weather service is primarily an **event publisher**, not a subscriber. It publishes weather data events but doesn't need to react to other services' events.

```python
# File: events/handlers.py (Current Implementation)
def get_event_handlers(weather_service, event_bus):
    """
    Get event handlers for weather service.
    Weather service primarily publishes events.
    """
    return {}  # No subscriptions currently
```

### Potential Event Subscriptions

If weather service needed to subscribe to events:

| Event | Source | Action |
|-------|--------|--------|
| `user.created` | account_service | Create default location (home) |
| `user.deleted` | account_service | Clean up saved locations |
| `user.location_updated` | account_service | Refresh weather for new location |

### Subscription Implementation Pattern (If Needed)

```python
# File: events/handlers.py (Future Implementation)
import json
import logging

logger = logging.getLogger(__name__)

_service = None

def set_service(service):
    """Set service reference for handlers"""
    global _service
    _service = service


async def handle_user_deleted(msg) -> None:
    """
    Handle user.deleted event.

    Source: account_service
    Action: Clean up user's saved locations
    """
    try:
        data = json.loads(msg.data.decode())
        user_id = data.get("user_id")

        if _service and user_id:
            # Delete all user's saved locations
            await _service.delete_all_user_locations(user_id)
            logger.info(f"Cleaned up locations for deleted user: {user_id}")

        await msg.ack()
    except Exception as e:
        logger.error(f"Failed to handle user.deleted: {e}")
        await msg.nak()


def get_event_handlers(weather_service, event_bus):
    """Get event handlers for subscription"""
    set_service(weather_service)
    return {
        "account.user.deleted": handle_user_deleted,
    }
```

---

## System Contract Checklist

### Implementation Status

| Pattern | Status | File(s) | Notes |
|---------|--------|---------|-------|
| **1. Architecture** | ✅ Complete | All service files | Multi-provider + two-tier cache |
| **2. Dependency Injection** | ⚠️ Partial | `protocols.py`, `factory.py` | TO CREATE |
| **3. Event Publishing** | ✅ Complete | `weather_service.py`, `events/models.py` | WEATHER_DATA_FETCHED, WEATHER_ALERT_CREATED |
| **4. Error Handling** | ⚠️ Partial | `main.py` | Custom exceptions TO CREATE |
| **5. Client Pattern** | ⚠️ Inline | `weather_service.py` | Extract to `clients/` |
| **6. Repository** | ✅ Complete | `weather_repository.py` | Two-tier caching implemented |
| **7. Service Registration** | ✅ Complete | `routes_registry.py`, `main.py` | Consul integration |
| **8. Migration** | ✅ Complete | `migrations/001_...sql` | 3 tables defined |
| **9. Lifecycle** | ✅ Complete | `main.py` | WeatherMicroservice class |
| **10. Configuration** | ✅ Complete | `main.py` | ConfigManager + env vars |
| **11. Logging** | ✅ Complete | All files | setup_service_logger |
| **12. Event Subscription** | ✅ N/A | `events/handlers.py` | Publisher-only service |

### Required Actions for Full Compliance

1. **Create `protocols.py`**: Define WeatherRepositoryProtocol, EventBusProtocol, WeatherProviderProtocol
2. **Create `factory.py`**: WeatherServiceFactory with create_service and create_for_testing
3. **Refactor `weather_service.py`**: Accept repository via constructor for full DI
4. **Create custom exceptions**: WeatherServiceError hierarchy
5. **Extract API clients**: Move inline HTTP calls to `clients/openweathermap_client.py`

---

## Appendix: Quick Reference

### API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Health check |
| GET | `/api/v1/weather/current` | No | Current weather |
| GET | `/api/v1/weather/forecast` | No | Weather forecast |
| GET | `/api/v1/weather/alerts` | No | Weather alerts |
| POST | `/api/v1/weather/locations` | Yes | Save location |
| GET | `/api/v1/weather/locations/{user_id}` | Yes | List locations |
| DELETE | `/api/v1/weather/locations/{location_id}` | Yes | Delete location |

### Event Subjects

| Event | Subject | Direction |
|-------|---------|-----------|
| Weather Data Fetched | `weather.data.fetched` | Publish |
| Weather Alert Created | `weather.alert.created` | Publish |
| Location Saved | `weather.location.saved` | Publish |

### Cache Keys

| Pattern | Example | TTL |
|---------|---------|-----|
| Current Weather | `weather:current:London:metric` | 15 min |
| Forecast | `weather:forecast:London:5` | 30 min |
| Alerts | `weather:alerts:London` | 10 min |

### Database Tables

| Schema | Table | Purpose |
|--------|-------|---------|
| weather | weather_locations | User favorite locations |
| weather | weather_cache | PostgreSQL warm cache |
| weather | weather_alerts | Active weather alerts |
