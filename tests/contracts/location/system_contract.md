# Location Service - System Contract

## Overview

This document defines how the Location Service implements the 12 standard microservice patterns. It serves as the bridge between the Logic Contract (business rules) and actual code implementation.

**Service Identity:**
- **Port**: 8224
- **Schema**: `location`
- **Version**: 1.0.0

---

## 1. Architecture Pattern

### Service Layer Structure

```
microservices/location_service/
├── __init__.py
├── main.py                     # FastAPI app, routes, lifespan management
├── location_service.py         # Business logic layer
├── location_repository.py      # Data access layer (PostGIS queries)
├── models.py                   # Pydantic request/response models
├── routes_registry.py          # Consul route registration metadata
├── client.py                   # Legacy client (deprecated)
├── clients/
│   ├── __init__.py             # Client exports
│   ├── account_client.py       # Account service HTTP client
│   ├── device_client.py        # Device service HTTP client
│   └── notification_client.py  # Notification service HTTP client
└── events/
    ├── __init__.py
    ├── event_types.py          # Event type enums
    ├── models.py               # Event Pydantic models
    ├── publishers.py           # Event publishing logic
    └── handlers.py             # Event subscription handlers
```

### Layer Responsibilities

| Layer | File | Responsibility | Dependencies |
|-------|------|----------------|--------------|
| **API** | `main.py` | HTTP routes, request validation, lifespan | FastAPI, LocationService |
| **Service** | `location_service.py` | Business logic, orchestration, event publishing | Repository, EventBus, Clients |
| **Repository** | `location_repository.py` | Data access, PostGIS spatial queries | PostgreSQL gRPC |
| **Clients** | `clients/*.py` | External service communication | httpx |
| **Events** | `events/*.py` | Event publishing/subscription | NATS |

### Current Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| main.py | Implemented | Full route definitions |
| location_service.py | Implemented | Business logic complete |
| location_repository.py | Implemented | PostGIS queries working |
| protocols.py | **TODO** | Needs DI interfaces |
| factory.py | **TODO** | Needs DI factory |
| clients/account_client.py | Implemented | Async HTTP client |
| clients/device_client.py | Implemented | Async HTTP client |
| events/handlers.py | Implemented | device.deleted, user.deleted |

---

## 2. Dependency Injection Pattern

### Current State

The location_service currently uses **direct instantiation** rather than protocol-based DI:

```python
# location_service.py - Current Implementation
class LocationService:
    def __init__(self, consul_registry=None, event_bus=None):
        self.consul_registry = consul_registry
        self.event_bus = event_bus
        self.repository = LocationRepository()  # Direct instantiation
```

### Required Implementation: `protocols.py`

```python
"""
Location Service Protocols - DI Interfaces

All dependencies defined as Protocol classes for testability.
"""
from typing import Protocol, runtime_checkable, Optional, Dict, Any, List
from datetime import datetime


@runtime_checkable
class LocationRepositoryProtocol(Protocol):
    """Repository interface for location data access"""

    async def create_location(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create location and return created data"""
        ...

    async def get_device_latest_location(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get device's latest location"""
        ...

    async def get_device_location_history(
        self,
        device_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get device location history"""
        ...

    async def create_geofence(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create geofence"""
        ...

    async def get_geofence_by_id(self, geofence_id: str) -> Optional[Dict[str, Any]]:
        """Get geofence by ID"""
        ...

    async def list_geofences(
        self,
        user_id: str,
        active_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List user's geofences"""
        ...

    async def update_geofence(self, geofence_id: str, data: Dict[str, Any]) -> bool:
        """Update geofence"""
        ...

    async def delete_geofence(self, geofence_id: str) -> bool:
        """Delete geofence"""
        ...

    async def check_point_in_geofences(
        self,
        latitude: float,
        longitude: float,
        device_id: str,
        user_id: str,
    ) -> List[Dict[str, Any]]:
        """Check if point triggers any geofences"""
        ...

    async def create_place(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create place"""
        ...

    async def get_place_by_id(self, place_id: str) -> Optional[Dict[str, Any]]:
        """Get place by ID"""
        ...

    async def list_user_places(self, user_id: str) -> List[Dict[str, Any]]:
        """List user's places"""
        ...

    async def update_place(self, place_id: str, data: Dict[str, Any]) -> bool:
        """Update place"""
        ...

    async def delete_place(self, place_id: str) -> bool:
        """Delete place"""
        ...

    async def find_nearby_devices(
        self,
        latitude: float,
        longitude: float,
        radius_meters: float,
        user_id: str,
        time_window_minutes: int = 30,
        device_types: Optional[List[str]] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Find devices near a location"""
        ...

    async def search_locations_in_radius(
        self,
        center_lat: float,
        center_lon: float,
        radius_meters: float,
        start_time: datetime,
        end_time: datetime,
        device_ids: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Search locations within radius"""
        ...

    async def delete_device_locations(self, device_id: str) -> int:
        """Delete all locations for device, return count"""
        ...

    async def delete_user_locations(self, user_id: str) -> int:
        """Delete all locations for user, return count"""
        ...

    async def delete_user_places(self, user_id: str) -> int:
        """Delete all places for user, return count"""
        ...

    async def delete_user_geofences(self, user_id: str) -> int:
        """Delete all geofences for user, return count"""
        ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Event bus interface for NATS publishing"""

    async def publish_event(self, event: Any) -> None:
        """Publish event to NATS"""
        ...

    async def close(self) -> None:
        """Close event bus connection"""
        ...


@runtime_checkable
class DeviceClientProtocol(Protocol):
    """Device service client interface"""

    async def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get device by ID"""
        ...

    async def verify_ownership(self, device_id: str, user_id: str) -> bool:
        """Verify user owns device"""
        ...

    async def close(self) -> None:
        """Close client connection"""
        ...


@runtime_checkable
class AccountClientProtocol(Protocol):
    """Account service client interface"""

    async def get_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Get account by ID"""
        ...

    async def verify_exists(self, account_id: str) -> bool:
        """Verify account exists"""
        ...

    async def close(self) -> None:
        """Close client connection"""
        ...
```

### Required Implementation: `factory.py`

```python
"""
Location Service Factory - Dependency Injection Setup

Creates service instances with real or mock dependencies.
"""
from typing import Optional
from core.config_manager import ConfigManager

from .location_service import LocationService
from .location_repository import LocationRepository
from .protocols import (
    LocationRepositoryProtocol,
    EventBusProtocol,
    DeviceClientProtocol,
    AccountClientProtocol,
)
from .clients import DeviceClient, AccountClient


class LocationServiceFactory:
    """Factory for creating LocationService with dependencies"""

    @staticmethod
    def create_service(
        config: Optional[ConfigManager] = None,
        repository: Optional[LocationRepositoryProtocol] = None,
        event_bus: Optional[EventBusProtocol] = None,
        device_client: Optional[DeviceClientProtocol] = None,
        account_client: Optional[AccountClientProtocol] = None,
    ) -> LocationService:
        """
        Create LocationService instance with dependencies.

        Args:
            config: Configuration manager
            repository: Repository implementation (default: real)
            event_bus: Event bus implementation (default: None)
            device_client: Device client (default: real)
            account_client: Account client (default: real)

        Returns:
            Configured LocationService instance
        """
        if repository is None:
            repository = LocationRepository()

        if device_client is None:
            device_client = DeviceClient()

        if account_client is None:
            account_client = AccountClient()

        return LocationService(
            repository=repository,
            event_bus=event_bus,
            device_client=device_client,
            account_client=account_client,
        )

    @staticmethod
    def create_for_testing(
        mock_repository: LocationRepositoryProtocol,
        mock_event_bus: Optional[EventBusProtocol] = None,
        mock_device_client: Optional[DeviceClientProtocol] = None,
        mock_account_client: Optional[AccountClientProtocol] = None,
    ) -> LocationService:
        """Create service with mock dependencies for testing"""
        return LocationService(
            repository=mock_repository,
            event_bus=mock_event_bus,
            device_client=mock_device_client,
            account_client=mock_account_client,
        )


# Convenience function for main.py
def create_location_service(
    config: ConfigManager,
    event_bus: Optional[EventBusProtocol] = None,
) -> LocationService:
    """Create location service with standard configuration"""
    return LocationServiceFactory.create_service(
        config=config,
        event_bus=event_bus,
    )
```

---

## 3. Event Publishing Pattern

### Event Types (`events/event_types.py`)

```python
from enum import Enum

class LocationEventType(str, Enum):
    """Location service event types"""
    LOCATION_UPDATED = "location.updated"
    GEOFENCE_ENTERED = "geofence.entered"
    GEOFENCE_EXITED = "geofence.exited"
    GEOFENCE_CREATED = "geofence.created"
    GEOFENCE_DELETED = "geofence.deleted"
    PLACE_CREATED = "place.created"
```

### Event Publishing (Current Implementation)

The service uses `core.nats_client.Event` and `EventType` for publishing:

```python
# In location_service.py
from core.nats_client import Event, EventType, ServiceSource

# Publishing location update
event = Event(
    event_type=EventType.LOCATION_UPDATED,
    source=ServiceSource.LOCATION_SERVICE,
    data={
        "location_id": location_id,
        "device_id": request.device_id,
        "user_id": user_id,
        "latitude": request.latitude,
        "longitude": request.longitude,
        "timestamp": timestamp.isoformat(),
    },
)
await self.event_bus.publish_event(event)
```

### Published Events

| Event | Subject | Trigger | Data |
|-------|---------|---------|------|
| `location.updated` | `location.updated` | After location stored | location_id, device_id, user_id, coordinates, timestamp |
| `geofence.entered` | `location.geofence.entered` | Device enters geofence | geofence_id, geofence_name, device_id, user_id |
| `geofence.created` | `location.geofence.created` | Geofence created | geofence_id, name, user_id, shape_type |
| `geofence.deleted` | `location.geofence.deleted` | Geofence deleted | geofence_id, user_id |

---

## 4. Error Handling Pattern

### Custom Exceptions (Not Yet Implemented)

The service should define domain-specific exceptions in `exceptions.py`:

```python
"""
Location Service Exceptions
"""

class LocationServiceError(Exception):
    """Base exception for location service"""
    pass


class LocationNotFoundError(LocationServiceError):
    """Raised when location is not found"""
    def __init__(self, location_id: str):
        self.location_id = location_id
        super().__init__(f"Location not found: {location_id}")


class GeofenceNotFoundError(LocationServiceError):
    """Raised when geofence is not found"""
    def __init__(self, geofence_id: str):
        self.geofence_id = geofence_id
        super().__init__(f"Geofence not found: {geofence_id}")


class PlaceNotFoundError(LocationServiceError):
    """Raised when place is not found"""
    def __init__(self, place_id: str):
        self.place_id = place_id
        super().__init__(f"Place not found: {place_id}")


class AccessDeniedError(LocationServiceError):
    """Raised when user doesn't have access"""
    def __init__(self, resource_type: str, resource_id: str, user_id: str):
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.user_id = user_id
        super().__init__(f"Access denied: {user_id} cannot access {resource_type} {resource_id}")


class ValidationError(LocationServiceError):
    """Raised when validation fails"""
    pass


class DuplicatePlaceError(LocationServiceError):
    """Raised when duplicate place name exists"""
    def __init__(self, name: str, user_id: str):
        self.name = name
        self.user_id = user_id
        super().__init__(f"Place '{name}' already exists for user {user_id}")
```

### Current Error Handling

The service currently uses `LocationOperationResult` for error handling:

```python
# Current pattern in location_service.py
return LocationOperationResult(
    success=False,
    operation="create_geofence",
    message="Radius is required for circle geofences",
)
```

### Recommended Error Mapping for main.py

```python
from fastapi import HTTPException

EXCEPTION_STATUS_MAP = {
    LocationNotFoundError: 404,
    GeofenceNotFoundError: 404,
    PlaceNotFoundError: 404,
    AccessDeniedError: 403,
    ValidationError: 422,
    DuplicatePlaceError: 409,
}

@app.exception_handler(LocationServiceError)
async def location_error_handler(request, exc: LocationServiceError):
    status_code = EXCEPTION_STATUS_MAP.get(type(exc), 500)
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": type(exc).__name__,
            "message": str(exc),
        }
    )
```

---

## 5. Client Pattern (Sync Communication)

### Implemented Clients

| Client | File | Target Service | Port |
|--------|------|----------------|------|
| AccountClient | `clients/account_client.py` | account_service | 8202 |
| DeviceClient | `clients/device_client.py` | device_service | 8220 |
| NotificationClient | `clients/notification_client.py` | notification_service | 8206 |

### Client Implementation Pattern

```python
"""
Device Client - Async HTTP client for device_service
"""
import httpx
from typing import Optional, Dict, Any
import os


class DeviceClient:
    """Async client for device_service"""

    def __init__(self, base_url: Optional[str] = None):
        self._base_url = base_url or os.getenv(
            "DEVICE_SERVICE_URL",
            "http://localhost:8220"
        )
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=30.0,
                headers={"X-Internal-Call": "true"}
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get device by ID"""
        client = await self._get_client()
        response = await client.get(f"/api/v1/devices/{device_id}")

        if response.status_code == 404:
            return None

        response.raise_for_status()
        return response.json()

    async def verify_ownership(self, device_id: str, user_id: str) -> bool:
        """Verify user owns device"""
        device = await self.get_device(device_id)
        return device is not None and device.get("user_id") == user_id
```

### Client Usage in Service

Currently, clients are **not integrated** into LocationService. They need to be:

```python
# Recommended integration in location_service.py
class LocationService:
    def __init__(
        self,
        repository: LocationRepositoryProtocol,
        event_bus: Optional[EventBusProtocol] = None,
        device_client: Optional[DeviceClientProtocol] = None,
        account_client: Optional[AccountClientProtocol] = None,
    ):
        self._repository = repository
        self._event_bus = event_bus
        self._device_client = device_client
        self._account_client = account_client

    async def _verify_device_ownership(self, device_id: str, user_id: str) -> bool:
        """Verify user owns device via device_service"""
        if self._device_client:
            return await self._device_client.verify_ownership(device_id, user_id)
        # Fallback to local check
        return True
```

---

## 6. Repository Pattern (Database Access)

### Repository Implementation

File: `location_repository.py`

The repository uses `core.postgres_grpc_client.PostgresGRPCClient` for database access with PostGIS spatial queries.

### Key Repository Methods

| Method | SQL Operation | PostGIS Function |
|--------|---------------|------------------|
| `create_location()` | INSERT | ST_SetSRID, ST_Point |
| `get_device_latest_location()` | SELECT ORDER BY timestamp DESC LIMIT 1 | None |
| `get_device_location_history()` | SELECT with time range | None |
| `create_geofence()` | INSERT | ST_Buffer (for circles) |
| `check_point_in_geofences()` | SELECT with spatial check | ST_DWithin, ST_Contains |
| `find_nearby_devices()` | SELECT with distance | ST_DWithin, ST_Distance |
| `search_locations_in_radius()` | SELECT in circle | ST_DWithin |

### PostGIS Query Example

```python
# Spatial query for nearby devices
async def find_nearby_devices(
    self,
    latitude: float,
    longitude: float,
    radius_meters: float,
    user_id: str,
    time_window_minutes: int = 30,
    ...
) -> List[Dict[str, Any]]:
    query = """
        SELECT DISTINCT ON (device_id)
            location_id, device_id, user_id, latitude, longitude,
            accuracy, timestamp,
            ST_Distance(
                geom::geography,
                ST_SetSRID(ST_Point($2, $1), 4326)::geography
            ) as distance_meters
        FROM location.locations
        WHERE user_id = $3
        AND timestamp > NOW() - INTERVAL '$4 minutes'
        AND ST_DWithin(
            geom::geography,
            ST_SetSRID(ST_Point($2, $1), 4326)::geography,
            $5
        )
        ORDER BY device_id, timestamp DESC
        LIMIT $6
    """
    # Note: PostGIS Point is (longitude, latitude)
```

### Coordinate Order

**Important**: PostGIS uses `(longitude, latitude)` order, opposite of typical `(latitude, longitude)`:

```python
# Correct: ST_Point(longitude, latitude)
ST_SetSRID(ST_Point(-122.4194, 37.7749), 4326)

# Wrong: ST_Point(latitude, longitude)
# ST_SetSRID(ST_Point(37.7749, -122.4194), 4326)  # INCORRECT!
```

---

## 7. Service Registration Pattern (Consul)

### Routes Registry (`routes_registry.py`)

The service defines all routes for Consul registration:

```python
SERVICE_ROUTES = [
    # Health (2 routes)
    {"path": "/", "methods": ["GET"], "auth_required": False},
    {"path": "/health", "methods": ["GET"], "auth_required": False},

    # Location Management (7 routes)
    {"path": "/api/v1/locations", "methods": ["POST"], "auth_required": True},
    {"path": "/api/v1/locations/batch", "methods": ["POST"], "auth_required": True},
    {"path": "/api/v1/locations/{location_id}", "methods": ["DELETE"], "auth_required": True},
    {"path": "/api/v1/locations/device/{device_id}", "methods": ["GET"], "auth_required": True},
    {"path": "/api/v1/locations/device/{device_id}/latest", "methods": ["GET"], "auth_required": True},
    {"path": "/api/v1/locations/device/{device_id}/history", "methods": ["GET"], "auth_required": True},
    {"path": "/api/v1/locations/user/{user_id}", "methods": ["GET"], "auth_required": True},

    # Geofences (6 routes)
    {"path": "/api/v1/geofences", "methods": ["GET", "POST"], "auth_required": True},
    {"path": "/api/v1/geofences/{geofence_id}", "methods": ["GET", "PUT", "DELETE"], "auth_required": True},
    {"path": "/api/v1/geofences/{geofence_id}/activate", "methods": ["POST"], "auth_required": True},
    {"path": "/api/v1/geofences/{geofence_id}/deactivate", "methods": ["POST"], "auth_required": True},
    {"path": "/api/v1/geofences/{geofence_id}/events", "methods": ["GET"], "auth_required": True},
    {"path": "/api/v1/geofences/device/{device_id}/check", "methods": ["GET"], "auth_required": True},

    # Places (3 routes)
    {"path": "/api/v1/places", "methods": ["POST"], "auth_required": True},
    {"path": "/api/v1/places/user/{user_id}", "methods": ["GET"], "auth_required": True},
    {"path": "/api/v1/places/{place_id}", "methods": ["GET", "PUT", "DELETE"], "auth_required": True},

    # Search (3 routes)
    {"path": "/api/v1/locations/nearby", "methods": ["GET"], "auth_required": True},
    {"path": "/api/v1/locations/search/radius", "methods": ["POST"], "auth_required": True},
    {"path": "/api/v1/locations/search/polygon", "methods": ["POST"], "auth_required": True},

    # Distance & Stats (3 routes)
    {"path": "/api/v1/locations/distance", "methods": ["GET"], "auth_required": True},
    {"path": "/api/v1/distance", "methods": ["GET"], "auth_required": True},
    {"path": "/api/v1/stats/user/{user_id}", "methods": ["GET"], "auth_required": True},
]

SERVICE_METADATA = {
    "service_name": "location_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "location-tracking", "geofencing"],
    "capabilities": [
        "location_tracking",
        "geofencing",
        "place_management",
        "location_search",
        "distance_calculation",
        "location_history",
        "geofence_events"
    ]
}
```

### Consul Registration in main.py

```python
# Consul registration on startup
if service_config.consul_enabled:
    route_meta = get_routes_for_consul()
    consul_meta = {
        "version": SERVICE_METADATA["version"],
        "capabilities": ",".join(SERVICE_METADATA["capabilities"]),
        **route_meta,
    }

    consul_registry = ConsulRegistry(
        service_name=SERVICE_METADATA["service_name"],
        service_port=service_config.service_port,
        consul_host=service_config.consul_host,
        consul_port=service_config.consul_port,
        tags=SERVICE_METADATA["tags"],
        meta=consul_meta,
        health_check_type="http",
    )
    consul_registry.register()

# Consul deregistration on shutdown
if consul_registry:
    consul_registry.deregister()
```

---

## 8. Migration Pattern (Database Schema)

### Migration Files Location

```
microservices/location_service/migrations/
├── 001_initial_schema.sql        # Create schema + PostGIS extension
├── 002_locations_table.sql       # Locations table with spatial index
├── 003_geofences_table.sql       # Geofences table with spatial index
├── 004_places_table.sql          # Places table
├── 005_geofence_events.sql       # Geofence events tracking
├── 006_routes_table.sql          # Route recording (future)
└── 007_spatial_indexes.sql       # Additional spatial indexes
```

### Schema: `location`

```sql
-- Migration 001: Create schema with PostGIS
CREATE SCHEMA IF NOT EXISTS location;
CREATE EXTENSION IF NOT EXISTS postgis;

-- Migration 002: Locations table
CREATE TABLE IF NOT EXISTS location.locations (
    location_id VARCHAR(50) PRIMARY KEY,
    device_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL CHECK (latitude >= -90 AND latitude <= 90),
    longitude DOUBLE PRECISION NOT NULL CHECK (longitude >= -180 AND longitude <= 180),
    altitude DOUBLE PRECISION,
    accuracy DOUBLE PRECISION NOT NULL CHECK (accuracy > 0),
    heading DOUBLE PRECISION CHECK (heading >= 0 AND heading < 360),
    speed DOUBLE PRECISION CHECK (speed >= 0),
    address VARCHAR(500),
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),
    postal_code VARCHAR(20),
    location_method VARCHAR(20) DEFAULT 'gps',
    battery_level DOUBLE PRECISION CHECK (battery_level >= 0 AND battery_level <= 100),
    source VARCHAR(50) DEFAULT 'device',
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    geom GEOMETRY(Point, 4326) GENERATED ALWAYS AS (
        ST_SetSRID(ST_Point(longitude, latitude), 4326)
    ) STORED
);

-- Indexes
CREATE INDEX idx_locations_device_timestamp ON location.locations(device_id, timestamp DESC);
CREATE INDEX idx_locations_user ON location.locations(user_id);
CREATE INDEX idx_locations_geom ON location.locations USING GIST (geom);
```

### Key Tables

| Table | Purpose | Spatial Index |
|-------|---------|---------------|
| `location.locations` | Device location history | GIST on geom |
| `location.geofences` | Virtual boundaries | GIST on geom |
| `location.places` | User-defined locations | GIST on geom |
| `location.geofence_events` | Trigger history | None |
| `location.routes` | Travel paths (future) | GIST on geom |

---

## 9. Lifecycle Pattern (main.py Setup)

### Lifespan Context Manager

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    global location_service, consul_registry

    logger.info("Starting Location Service...")

    # 1. Initialize event bus
    event_bus = None
    try:
        event_bus = await get_event_bus("location_service")
        logger.info("Event bus initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize event bus: {e}")

    # 2. Initialize service
    location_service = LocationService(event_bus=event_bus)

    # 3. Check database connection
    if not await location_service.check_connection():
        logger.error("Failed to connect to database")
        raise RuntimeError("Database connection failed")

    # 4. Consul registration
    if service_config.consul_enabled:
        # Register with Consul...
        consul_registry.register()

    logger.info("Location Service initialized successfully")

    yield  # Application runs

    # Shutdown
    logger.info("Shutting down Location Service...")

    # 5. Close event bus
    if event_bus:
        await event_bus.close()

    # 6. Deregister from Consul
    if consul_registry:
        consul_registry.deregister()
```

### Startup Order

1. Initialize event bus (NATS)
2. Create LocationService instance
3. Verify database connection
4. Register with Consul
5. Start accepting requests

### Shutdown Order

1. Stop accepting requests (FastAPI handles)
2. Close event bus connection
3. Deregister from Consul
4. Log completion

---

## 10. Configuration Pattern (ConfigManager)

### Configuration Usage

```python
from core.config_manager import ConfigManager

# Initialize at module level
config_manager = ConfigManager("location_service")
service_config = config_manager.get_service_config()

# Available config properties
service_config.service_name      # "location_service"
service_config.service_port      # 8224
service_config.service_host      # "0.0.0.0"
service_config.debug             # True/False
service_config.log_level         # "INFO"
service_config.consul_enabled    # True/False
service_config.consul_host       # "consul"
service_config.consul_port       # 8500
service_config.nats_url          # "nats://nats:4222"
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOCATION_SERVICE_PORT` | 8224 | HTTP server port |
| `POSTGRES_GRPC_HOST` | localhost | Database host |
| `POSTGRES_GRPC_PORT` | 50061 | Database port |
| `NATS_URL` | nats://localhost:4222 | Event bus URL |
| `REDIS_GRPC_HOST` | localhost | Cache host |
| `REDIS_GRPC_PORT` | 50055 | Cache port |
| `CONSUL_HOST` | consul | Consul host |
| `CONSUL_PORT` | 8500 | Consul port |
| `CONSUL_ENABLED` | true | Enable Consul |

---

## 11. Logging Pattern

### Logger Setup

```python
from core.logger import setup_service_logger

# Setup at module level
logger = setup_service_logger("location_service")

# Usage patterns
logger.info("Location Service initialized successfully")
logger.warning(f"Failed to initialize event bus: {e}")
logger.error(f"Database connection check failed: {e}")
logger.error(f"Error reporting location: {e}", exc_info=True)
```

### Logging Levels

| Level | Usage |
|-------|-------|
| INFO | Startup/shutdown, successful operations |
| WARNING | Non-fatal errors (event bus unavailable) |
| ERROR | Operation failures with stack trace |
| DEBUG | Detailed operation flow (not in production) |

### Structured Logging Context

```python
# Include context for debugging
logger.info(
    f"Deleted {deleted_count} location records for device {device_id}"
)

logger.warning(
    f"User {user_id} attempted to access device {device_id} location"
)
```

---

## 12. Event Subscription Pattern (Async Communication)

### Event Handlers (`events/handlers.py`)

```python
async def handle_device_deleted(event: Event, location_repository):
    """
    Handle device.deleted event

    Subscribed to: device_service.device.deleted, *.device.deleted
    Action: Delete all location data for device
    """
    event_data = parse_device_deleted_event(event.data)
    device_id = event_data.device_id

    deleted_count = await location_repository.delete_device_locations(device_id)
    logger.info(f"Deleted {deleted_count} location records for device {device_id}")


async def handle_user_deleted(event: Event, location_repository):
    """
    Handle user.deleted event

    Subscribed to: account_service.user.deleted, *.user.deleted
    Action: Delete all location data for user
    """
    event_data = parse_user_deleted_event(event.data)
    user_id = event_data.user_id

    locations_deleted = await location_repository.delete_user_locations(user_id)
    places_deleted = await location_repository.delete_user_places(user_id)
    geofences_deleted = await location_repository.delete_user_geofences(user_id)

    logger.info(
        f"Cleaned up data for deleted user {user_id}: "
        f"{locations_deleted} locations, {places_deleted} places, "
        f"{geofences_deleted} geofences"
    )
```

### Event Handler Registry

```python
def get_event_handlers(location_repository) -> Dict[str, Callable]:
    """Get all event handlers for subscription"""
    return {
        "device_service.device.deleted": lambda event: handle_device_deleted(
            event, location_repository
        ),
        "*.device.deleted": lambda event: handle_device_deleted(
            event, location_repository
        ),
        "account_service.user.deleted": lambda event: handle_user_deleted(
            event, location_repository
        ),
        "*.user.deleted": lambda event: handle_user_deleted(
            event, location_repository
        ),
    }
```

### Subscribed Events

| Event | Source | Handler | Action |
|-------|--------|---------|--------|
| `device.deleted` | device_service | `handle_device_deleted()` | Delete device locations |
| `user.deleted` | account_service | `handle_user_deleted()` | Delete all user data |

---

## Implementation Checklist

### Currently Implemented

- [x] Architecture pattern (layer structure)
- [x] Event publishing (location.updated, geofence.*)
- [x] Client pattern (DeviceClient, AccountClient, NotificationClient)
- [x] Repository pattern (LocationRepository with PostGIS)
- [x] Service registration (Consul with routes_registry)
- [x] Lifecycle pattern (lifespan context manager)
- [x] Configuration pattern (ConfigManager)
- [x] Logging pattern (setup_service_logger)
- [x] Event subscription (device.deleted, user.deleted handlers)

### TODO: Needs Implementation

- [ ] Dependency Injection: Create `protocols.py` with Protocol interfaces
- [ ] Dependency Injection: Create `factory.py` with LocationServiceFactory
- [ ] Error Handling: Create `exceptions.py` with domain exceptions
- [ ] Error Handling: Add exception handlers in main.py
- [ ] Client Integration: Wire clients into LocationService constructor
- [ ] Event Subscription: Register handlers in lifespan (currently not wired)

---

## Summary

| Pattern | Status | Implementation |
|---------|--------|----------------|
| 1. Architecture | Complete | Standard layer structure |
| 2. Dependency Injection | Partial | Needs protocols.py, factory.py |
| 3. Event Publishing | Complete | Using core.nats_client |
| 4. Error Handling | Partial | Uses LocationOperationResult, needs exceptions |
| 5. Client Pattern | Complete | 3 clients implemented |
| 6. Repository Pattern | Complete | PostGIS queries working |
| 7. Service Registration | Complete | Consul with routes_registry |
| 8. Migration Pattern | Complete | Schema defined in design doc |
| 9. Lifecycle Pattern | Complete | Lifespan context manager |
| 10. Configuration | Complete | ConfigManager usage |
| 11. Logging Pattern | Complete | setup_service_logger |
| 12. Event Subscription | Partial | Handlers exist, need wiring |
