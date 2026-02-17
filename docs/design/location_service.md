# Location Service - Technical Design Document

## Overview

Location Service provides spatial intelligence for the isA platform, managing real-time device tracking, geofencing, place management, and location-based automation. It leverages PostgreSQL with PostGIS extension for efficient spatial queries and operations.

**Service Identity:**
- **Port**: 8224
- **Schema**: `location`
- **Version**: 1.0.0

---

## Architecture Overview

### Service Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Location Service                                    │
│                            Port: 8224                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                       FastAPI Application                              │  │
│  │                           (main.py)                                    │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐   │  │
│  │  │  Location API   │  │   Geofence API  │  │     Place API       │   │  │
│  │  │   Endpoints     │  │    Endpoints    │  │    Endpoints        │   │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘   │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐   │  │
│  │  │   Search API    │  │    Stats API    │  │   Health Check      │   │  │
│  │  │   Endpoints     │  │    Endpoints    │  │    Endpoint         │   │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│                                    ▼                                         │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        Service Layer                                   │  │
│  │                    (location_service.py)                               │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐   │  │
│  │  │    Location     │  │    Geofence     │  │      Place          │   │  │
│  │  │    Operations   │  │    Operations   │  │    Operations       │   │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘   │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐   │  │
│  │  │    Search       │  │  Geofence Check │  │   Event Publishing  │   │  │
│  │  │   Operations    │  │     Engine      │  │                     │   │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│                                    ▼                                         │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                       Repository Layer                                 │  │
│  │                   (location_repository.py)                             │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐   │  │
│  │  │   Location      │  │    Geofence     │  │      Place          │   │  │
│  │  │    CRUD         │  │     CRUD        │  │      CRUD           │   │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘   │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐   │  │
│  │  │   Spatial       │  │    Distance     │  │     Query           │   │  │
│  │  │   Queries       │  │   Calculator    │  │    Builder          │   │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                   Dependency Injection Layer                           │  │
│  │                       (protocols.py)                                   │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐   │  │
│  │  │  Repository     │  │   EventBus      │  │     Client          │   │  │
│  │  │   Protocol      │  │   Protocol      │  │   Protocols         │   │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         │                           │                           │
         ▼                           ▼                           ▼
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│   PostgreSQL        │  │        NATS         │  │       Redis         │
│   with PostGIS      │  │     Event Bus       │  │      (Cache)        │
│   (via gRPC)        │  │                     │  │    (via gRPC)       │
│   Port: 50061       │  │    Port: 4222       │  │   Port: 50055       │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘
```

### External Dependencies

| Dependency | Type | Purpose | Port |
|------------|------|---------|------|
| PostgreSQL + PostGIS | gRPC | Spatial data storage | 50061 |
| NATS JetStream | Native | Event messaging | 4222 |
| Redis | gRPC | Caching | 50055 |
| Consul | HTTP | Service discovery | 8500 |
| device_service | HTTP | Device ownership | 8220 |
| account_service | HTTP | User validation | 8202 |
| notification_service | HTTP | Alert delivery | 8206 |

### Service Dependencies Diagram

```
                    ┌─────────────────┐
                    │  notification   │
                    │    _service     │
                    │     (8206)      │
                    └────────▲────────┘
                             │ geofence events
                             │
┌─────────────────┐  ┌───────┴───────┐  ┌─────────────────┐
│   device        │  │   location    │  │   calendar      │
│   _service      │◄─┤   _service    ├─►│   _service      │
│    (8220)       │  │    (8224)     │  │    (8217)       │
└─────────────────┘  └───────┬───────┘  └─────────────────┘
  device ownership           │           place events
                             │
                    ┌────────▼────────┐
                    │   account       │
                    │   _service      │
                    │    (8202)       │
                    └─────────────────┘
                      user validation
```

---

## Component Design

### Service Layer (`location_service.py`)

**Responsibilities:**
- Business logic orchestration
- Input validation and transformation
- Event publishing on state changes
- Geofence trigger detection
- Cross-service coordination

**Key Methods:**

| Method | Description | Events Published |
|--------|-------------|------------------|
| `report_location()` | Store device location | `location.updated` |
| `batch_report_locations()` | Bulk location upload | Multiple `location.updated` |
| `get_device_latest_location()` | Get current position | None |
| `get_device_location_history()` | Query historical locations | None |
| `create_geofence()` | Create virtual boundary | `geofence.created` |
| `update_geofence()` | Modify geofence settings | None |
| `delete_geofence()` | Remove geofence | `geofence.deleted` |
| `activate_geofence()` | Enable geofence | None |
| `deactivate_geofence()` | Disable geofence | None |
| `_check_geofences_for_location()` | Detect geofence triggers | `geofence.entered`, `geofence.exited` |
| `create_place()` | Save named location | `place.created` |
| `update_place()` | Modify place | None |
| `delete_place()` | Remove place | None |
| `find_nearby_devices()` | Spatial proximity search | None |
| `search_radius()` | Circular area search | None |
| `calculate_distance()` | Haversine distance | None |

### Repository Layer (`location_repository.py`)

**Responsibilities:**
- Data access abstraction
- SQL query construction with PostGIS functions
- PostgreSQL gRPC communication
- Spatial index utilization

**Key Methods:**

| Method | SQL Operation | PostGIS Function |
|--------|---------------|------------------|
| `create_location()` | INSERT | ST_SetSRID, ST_Point |
| `get_device_latest_location()` | SELECT ORDER BY timestamp | None |
| `get_device_location_history()` | SELECT with time range | None |
| `create_geofence()` | INSERT | ST_Buffer, ST_MakePolygon |
| `get_geofence_by_id()` | SELECT WHERE id= | None |
| `list_geofences()` | SELECT with filters | None |
| `update_geofence()` | UPDATE WHERE id= | None |
| `delete_geofence()` | DELETE | None |
| `check_point_in_geofences()` | SELECT with spatial check | ST_Contains, ST_DWithin |
| `create_place()` | INSERT | ST_SetSRID, ST_Point |
| `get_place_by_id()` | SELECT WHERE id= | None |
| `list_user_places()` | SELECT WHERE user_id= | None |
| `find_nearby_devices()` | SELECT with distance | ST_DWithin, ST_Distance |
| `search_locations_in_radius()` | SELECT in circle | ST_DWithin |
| `calculate_distance()` | N/A (Python) | Haversine formula |

### Client Layer (`clients/`)

**External Service Clients:**

| Client | Service | Methods | Purpose |
|--------|---------|---------|---------|
| `AccountClient` | account_service | `get_account()`, `verify_exists()` | User validation |
| `DeviceClient` | device_service | `get_device()`, `verify_ownership()` | Device ownership |
| `NotificationClient` | notification_service | `send_notification()` | Alert delivery |

### Event Layer (`events/`)

**Publishers (`events/publishers.py`):**

| Event | Subject | Trigger |
|-------|---------|---------|
| `LocationUpdatedEvent` | `location.updated` | After location stored |
| `GeofenceEnteredEvent` | `location.geofence.entered` | Device crosses into geofence |
| `GeofenceExitedEvent` | `location.geofence.exited` | Device crosses out of geofence |
| `GeofenceCreatedEvent` | `location.geofence.created` | New geofence created |
| `GeofenceDeletedEvent` | `location.geofence.deleted` | Geofence removed |
| `PlaceCreatedEvent` | `location.place.created` | New place saved |

**Handlers (`events/handlers.py`):**

| Handler | Source Event | Action |
|---------|--------------|--------|
| `handle_device_deleted()` | `device.deleted` | Delete device's locations |
| `handle_user_deleted()` | `user.deleted` | Delete user's locations, geofences, places |

### Models Layer (`models.py`)

**Request Models:**

| Model | Purpose | Key Fields |
|-------|---------|------------|
| `LocationReportRequest` | Location upload | device_id, lat, lon, accuracy |
| `LocationBatchRequest` | Bulk upload | locations[] |
| `GeofenceCreateRequest` | Create geofence | name, shape_type, center, radius/polygon |
| `GeofenceUpdateRequest` | Update geofence | All optional fields |
| `PlaceCreateRequest` | Create place | name, category, lat, lon |
| `PlaceUpdateRequest` | Update place | All optional fields |
| `NearbySearchRequest` | Find nearby | lat, lon, radius_meters |
| `RadiusSearchRequest` | Circle search | center, radius, time range |
| `PolygonSearchRequest` | Polygon search | polygon_coordinates, time range |

**Response Models:**

| Model | Purpose | Key Fields |
|-------|---------|------------|
| `LocationResponse` | Location data | All location fields + timestamps |
| `GeofenceResponse` | Geofence data | All geofence fields + stats |
| `PlaceResponse` | Place data | All place fields + visit stats |
| `LocationOperationResult` | Operation result | success, id, message |
| `DistanceResponse` | Distance calc | distance_meters, distance_km |

**Enums:**

| Enum | Values |
|------|--------|
| `LocationMethod` | gps, wifi, cellular, bluetooth, manual, hybrid |
| `GeofenceShapeType` | circle, polygon, rectangle |
| `GeofenceTriggerType` | enter, exit, dwell |
| `PlaceCategory` | home, work, school, favorite, custom |
| `LocationEventType` | location_update, geofence_enter, geofence_exit, etc. |
| `RouteStatus` | active, paused, completed, cancelled |

---

## Database Schemas

### Schema: `location`

```sql
-- Create schema with PostGIS extension
CREATE SCHEMA IF NOT EXISTS location;
CREATE EXTENSION IF NOT EXISTS postgis;

-- ============================================================
-- LOCATIONS TABLE
-- Stores device location history with spatial indexing
-- ============================================================
CREATE TABLE IF NOT EXISTS location.locations (
    location_id VARCHAR(50) PRIMARY KEY,
    device_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(50) NOT NULL,

    -- Geographic coordinates
    latitude DOUBLE PRECISION NOT NULL CHECK (latitude >= -90 AND latitude <= 90),
    longitude DOUBLE PRECISION NOT NULL CHECK (longitude >= -180 AND longitude <= 180),
    altitude DOUBLE PRECISION,

    -- Location quality
    accuracy DOUBLE PRECISION NOT NULL CHECK (accuracy > 0),
    heading DOUBLE PRECISION CHECK (heading >= 0 AND heading < 360),
    speed DOUBLE PRECISION CHECK (speed >= 0),

    -- Address information (reverse geocoded)
    address VARCHAR(500),
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),
    postal_code VARCHAR(20),

    -- Metadata
    location_method VARCHAR(20) DEFAULT 'gps',
    battery_level DOUBLE PRECISION CHECK (battery_level >= 0 AND battery_level <= 100),
    source VARCHAR(50) DEFAULT 'device',
    metadata JSONB DEFAULT '{}',

    -- Timestamps
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- PostGIS geometry column for spatial queries
    geom GEOMETRY(Point, 4326) GENERATED ALWAYS AS (
        ST_SetSRID(ST_Point(longitude, latitude), 4326)
    ) STORED,

    -- Constraints
    CONSTRAINT locations_method_check CHECK (
        location_method IN ('gps', 'wifi', 'cellular', 'bluetooth', 'manual', 'hybrid')
    )
);

-- Indexes for location queries
CREATE INDEX idx_locations_device_timestamp
    ON location.locations(device_id, timestamp DESC);

CREATE INDEX idx_locations_user
    ON location.locations(user_id);

CREATE INDEX idx_locations_timestamp
    ON location.locations(timestamp DESC);

-- Spatial index for geographic queries
CREATE INDEX idx_locations_geom
    ON location.locations USING GIST (geom);

-- Partial index for recent locations (last 24 hours optimization)
CREATE INDEX idx_locations_recent
    ON location.locations(device_id, timestamp DESC)
    WHERE timestamp > NOW() - INTERVAL '24 hours';
```

```sql
-- ============================================================
-- GEOFENCES TABLE
-- Virtual boundaries for location-based triggers
-- ============================================================
CREATE TABLE IF NOT EXISTS location.geofences (
    geofence_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    user_id VARCHAR(50) NOT NULL,
    organization_id VARCHAR(50),

    -- Shape definition
    shape_type VARCHAR(20) NOT NULL,
    center_lat DOUBLE PRECISION NOT NULL CHECK (center_lat >= -90 AND center_lat <= 90),
    center_lon DOUBLE PRECISION NOT NULL CHECK (center_lon >= -180 AND center_lon <= 180),
    radius DOUBLE PRECISION CHECK (radius > 0),  -- For circle shapes (meters)
    polygon_coordinates JSONB,  -- For polygon shapes: [[lat, lon], ...]

    -- Status
    active BOOLEAN DEFAULT TRUE,

    -- Trigger configuration
    trigger_on_enter BOOLEAN DEFAULT TRUE,
    trigger_on_exit BOOLEAN DEFAULT TRUE,
    trigger_on_dwell BOOLEAN DEFAULT FALSE,
    dwell_time_seconds INTEGER CHECK (dwell_time_seconds >= 60),

    -- Targeting
    target_devices JSONB DEFAULT '[]',  -- Array of device_ids
    target_groups JSONB DEFAULT '[]',   -- Array of group_ids

    -- Schedule restrictions
    active_days JSONB,  -- ["monday", "tuesday", ...]
    active_hours JSONB, -- {"start": "09:00", "end": "18:00"}

    -- Notifications
    notification_channels JSONB DEFAULT '[]',
    notification_template TEXT,

    -- Statistics
    total_triggers INTEGER DEFAULT 0,
    last_triggered TIMESTAMP WITH TIME ZONE,

    -- Metadata
    tags JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- PostGIS geometry column
    geom GEOMETRY(Geometry, 4326),

    -- Constraints
    CONSTRAINT geofences_shape_check CHECK (
        shape_type IN ('circle', 'polygon', 'rectangle')
    ),
    CONSTRAINT geofences_circle_radius CHECK (
        shape_type != 'circle' OR radius IS NOT NULL
    ),
    CONSTRAINT geofences_polygon_coords CHECK (
        shape_type != 'polygon' OR polygon_coordinates IS NOT NULL
    )
);

-- Indexes for geofence queries
CREATE INDEX idx_geofences_user
    ON location.geofences(user_id);

CREATE INDEX idx_geofences_active
    ON location.geofences(active)
    WHERE active = TRUE;

CREATE INDEX idx_geofences_org
    ON location.geofences(organization_id)
    WHERE organization_id IS NOT NULL;

-- Spatial index for geofence boundary checks
CREATE INDEX idx_geofences_geom
    ON location.geofences USING GIST (geom);

-- GIN index for target device array searches
CREATE INDEX idx_geofences_target_devices
    ON location.geofences USING GIN (target_devices);
```

```sql
-- ============================================================
-- GEOFENCE_EVENTS TABLE
-- History of geofence triggers
-- ============================================================
CREATE TABLE IF NOT EXISTS location.geofence_events (
    event_id VARCHAR(50) PRIMARY KEY,
    geofence_id VARCHAR(50) NOT NULL REFERENCES location.geofences(geofence_id) ON DELETE CASCADE,
    device_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(50) NOT NULL,

    -- Event details
    event_type VARCHAR(20) NOT NULL,  -- enter, exit, dwell
    location_id VARCHAR(50),

    -- Location at event time
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,

    -- Timestamps
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT geofence_events_type_check CHECK (
        event_type IN ('enter', 'exit', 'dwell')
    )
);

-- Indexes for geofence event queries
CREATE INDEX idx_geofence_events_geofence
    ON location.geofence_events(geofence_id, timestamp DESC);

CREATE INDEX idx_geofence_events_device
    ON location.geofence_events(device_id, timestamp DESC);

CREATE INDEX idx_geofence_events_timestamp
    ON location.geofence_events(timestamp DESC);
```

```sql
-- ============================================================
-- PLACES TABLE
-- User-defined named locations
-- ============================================================
CREATE TABLE IF NOT EXISTS location.places (
    place_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    name VARCHAR(200) NOT NULL,
    category VARCHAR(20) NOT NULL,

    -- Location
    latitude DOUBLE PRECISION NOT NULL CHECK (latitude >= -90 AND latitude <= 90),
    longitude DOUBLE PRECISION NOT NULL CHECK (longitude >= -180 AND longitude <= 180),
    address VARCHAR(500),
    radius DOUBLE PRECISION DEFAULT 100 CHECK (radius > 0 AND radius <= 1000),

    -- Customization
    icon VARCHAR(50),
    color VARCHAR(20),

    -- Statistics
    visit_count INTEGER DEFAULT 0,
    total_time_spent INTEGER DEFAULT 0,  -- seconds
    last_visit TIMESTAMP WITH TIME ZONE,

    -- Metadata
    tags JSONB DEFAULT '[]',

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- PostGIS geometry column
    geom GEOMETRY(Point, 4326) GENERATED ALWAYS AS (
        ST_SetSRID(ST_Point(longitude, latitude), 4326)
    ) STORED,

    -- Constraints
    CONSTRAINT places_category_check CHECK (
        category IN ('home', 'work', 'school', 'favorite', 'custom')
    )
);

-- Indexes for place queries
CREATE INDEX idx_places_user
    ON location.places(user_id);

CREATE INDEX idx_places_category
    ON location.places(user_id, category);

-- Spatial index for place proximity searches
CREATE INDEX idx_places_geom
    ON location.places USING GIST (geom);

-- Unique name per user
CREATE UNIQUE INDEX idx_places_unique_name
    ON location.places(user_id, LOWER(name));
```

```sql
-- ============================================================
-- ROUTES TABLE
-- Recorded travel paths (future feature)
-- ============================================================
CREATE TABLE IF NOT EXISTS location.routes (
    route_id VARCHAR(50) PRIMARY KEY,
    device_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    name VARCHAR(200),

    -- Status
    status VARCHAR(20) DEFAULT 'active',

    -- Start/end locations
    start_location_id VARCHAR(50),
    end_location_id VARCHAR(50),

    -- Statistics
    waypoint_count INTEGER DEFAULT 0,
    total_distance DOUBLE PRECISION,  -- meters
    total_duration DOUBLE PRECISION,  -- seconds
    avg_speed DOUBLE PRECISION,       -- m/s
    max_speed DOUBLE PRECISION,       -- m/s

    -- Timestamps
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    ended_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Route geometry (LineString)
    geom GEOMETRY(LineString, 4326),

    -- Constraints
    CONSTRAINT routes_status_check CHECK (
        status IN ('active', 'paused', 'completed', 'cancelled')
    )
);

-- Indexes for route queries
CREATE INDEX idx_routes_device
    ON location.routes(device_id, started_at DESC);

CREATE INDEX idx_routes_user
    ON location.routes(user_id, started_at DESC);

CREATE INDEX idx_routes_status
    ON location.routes(status)
    WHERE status = 'active';
```

### Database Migrations

| Version | Description | File |
|---------|-------------|------|
| 001 | Initial schema with PostGIS | `001_initial_schema.sql` |
| 002 | Add locations table | `002_locations_table.sql` |
| 003 | Add geofences table | `003_geofences_table.sql` |
| 004 | Add places table | `004_places_table.sql` |
| 005 | Add geofence_events table | `005_geofence_events.sql` |
| 006 | Add routes table | `006_routes_table.sql` |
| 007 | Add spatial indexes | `007_spatial_indexes.sql` |

---

## Data Flow Diagrams

### Report Location Flow

```
Client                    Service                  Repository              NATS
  │                          │                          │                    │
  │  POST /api/v1/locations  │                          │                    │
  │─────────────────────────>│                          │                    │
  │                          │                          │                    │
  │                          │  validate coordinates    │                    │
  │                          │─────────┐               │                    │
  │                          │<────────┘               │                    │
  │                          │                          │                    │
  │                          │  create_location(data)  │                    │
  │                          │─────────────────────────>│                    │
  │                          │                          │  INSERT INTO       │
  │                          │                          │  location.locations│
  │                          │                          │─────────┐          │
  │                          │                          │<────────┘          │
  │                          │  return location_id      │                    │
  │                          │<─────────────────────────│                    │
  │                          │                          │                    │
  │                          │  check_geofences()       │                    │
  │                          │─────────────────────────>│                    │
  │                          │                          │  ST_DWithin/       │
  │                          │                          │  ST_Contains       │
  │                          │                          │─────────┐          │
  │                          │                          │<────────┘          │
  │                          │  triggered_geofences[]   │                    │
  │                          │<─────────────────────────│                    │
  │                          │                          │                    │
  │                          │  publish(location.updated)                    │
  │                          │──────────────────────────────────────────────>│
  │                          │                          │                    │
  │                          │  for each triggered:     │                    │
  │                          │  publish(geofence.entered)                    │
  │                          │──────────────────────────────────────────────>│
  │                          │                          │                    │
  │  200 OK {success: true}  │                          │                    │
  │<─────────────────────────│                          │                    │
```

### Create Geofence Flow

```
Client                    Service                  Repository              NATS
  │                          │                          │                    │
  │  POST /api/v1/geofences  │                          │                    │
  │─────────────────────────>│                          │                    │
  │                          │                          │                    │
  │                          │  validate shape          │                    │
  │                          │  (radius for circle,     │                    │
  │                          │   3+ coords for polygon) │                    │
  │                          │─────────┐               │                    │
  │                          │<────────┘               │                    │
  │                          │                          │                    │
  │                          │  create_geofence(data)  │                    │
  │                          │─────────────────────────>│                    │
  │                          │                          │  INSERT +          │
  │                          │                          │  ST_Buffer (circle)│
  │                          │                          │  ST_MakePolygon    │
  │                          │                          │─────────┐          │
  │                          │                          │<────────┘          │
  │                          │  return geofence_id      │                    │
  │                          │<─────────────────────────│                    │
  │                          │                          │                    │
  │                          │  publish(geofence.created)                    │
  │                          │──────────────────────────────────────────────>│
  │                          │                          │                    │
  │  200 OK {geofence_id}    │                          │                    │
  │<─────────────────────────│                          │                    │
```

### Geofence Check Flow (Internal)

```
                     Service                       Repository
                        │                              │
  location stored       │                              │
  ─────────────────────>│                              │
                        │                              │
                        │  check_point_in_geofences()  │
                        │  (lat, lon, device_id)       │
                        │─────────────────────────────>│
                        │                              │
                        │                              │  SELECT geofences
                        │                              │  WHERE active = true
                        │                              │  AND (device_id IN target_devices
                        │                              │       OR target_devices = '[]')
                        │                              │  AND ST_DWithin(
                        │                              │        geom,
                        │                              │        ST_SetSRID(ST_Point(lon,lat), 4326),
                        │                              │        0.001  -- ~100m tolerance
                        │                              │      )
                        │                              │─────────┐
                        │                              │<────────┘
                        │                              │
                        │  return triggered_geofences[]│
                        │<─────────────────────────────│
                        │                              │
  for each triggered:   │                              │
  - determine enter/exit│                              │
  - publish event       │                              │
  - update stats        │                              │
                        │                              │
```

### Find Nearby Devices Flow

```
Client                    Service                  Repository
  │                          │                          │
  │  GET /nearby?lat=X&lon=Y&radius=Z                   │
  │─────────────────────────>│                          │
  │                          │                          │
  │                          │  find_nearby_devices()   │
  │                          │─────────────────────────>│
  │                          │                          │
  │                          │                          │  SELECT DISTINCT ON (device_id)
  │                          │                          │  device_id, lat, lon, timestamp,
  │                          │                          │  ST_Distance(geom, point) as distance
  │                          │                          │  FROM location.locations
  │                          │                          │  WHERE ST_DWithin(geom, point, radius)
  │                          │                          │  AND timestamp > NOW() - time_window
  │                          │                          │  ORDER BY device_id, timestamp DESC
  │                          │                          │─────────┐
  │                          │                          │<────────┘
  │                          │                          │
  │                          │  return nearby_devices[] │
  │                          │<─────────────────────────│
  │                          │                          │
  │  200 OK {devices: [...]} │                          │
  │<─────────────────────────│                          │
```

### Event Handler: Device Deleted

```
NATS                     Handler                   Repository
  │                          │                          │
  │  device.deleted          │                          │
  │  {device_id: "dev_123"}  │                          │
  │─────────────────────────>│                          │
  │                          │                          │
  │                          │  delete_device_locations()
  │                          │─────────────────────────>│
  │                          │                          │  DELETE FROM locations
  │                          │                          │  WHERE device_id = 'dev_123'
  │                          │                          │─────────┐
  │                          │                          │<────────┘
  │                          │                          │
  │                          │  delete_device_geofences()
  │                          │─────────────────────────>│
  │                          │                          │  UPDATE geofences
  │                          │                          │  SET target_devices = target_devices - 'dev_123'
  │                          │                          │─────────┐
  │                          │                          │<────────┘
  │                          │                          │
  │  ack()                   │                          │
  │<─────────────────────────│                          │
```

---

## Technology Stack

### Core Technologies

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Language | Python | 3.9+ | Primary language |
| Framework | FastAPI | 0.104+ | HTTP API framework |
| Validation | Pydantic | 2.5+ | Data validation |
| Async HTTP | httpx | 0.25+ | Service clients |
| Database | PostgreSQL + PostGIS | 14+ / 3.3+ | Spatial data storage |
| DB Access | gRPC | - | PostgreSQL communication |
| Messaging | NATS JetStream | 2.9+ | Event bus |
| Cache | Redis | 7+ | Caching layer |
| Service Discovery | Consul | 1.15+ | Service registry |

### Spatial Technologies

| Component | Purpose |
|-----------|---------|
| PostGIS | PostgreSQL spatial extension |
| GIST Index | Spatial indexing for fast queries |
| WGS84 (SRID 4326) | Standard GPS coordinate system |
| Haversine | Great-circle distance calculation |

### Development Tools

| Tool | Purpose |
|------|---------|
| pytest | Testing framework |
| pytest-asyncio | Async test support |
| factory-boy | Test data generation |
| syrupy | Snapshot testing |
| black | Code formatting |
| mypy | Type checking |

---

## Security Considerations

### Authentication

- JWT token validation via auth_service
- Token expiry: 24 hours
- Internal calls: `X-Internal-Call: true` header bypasses JWT
- Device API keys for IoT devices (future)

### Authorization

| Resource | Access Rule |
|----------|-------------|
| Locations | User can only access own devices' locations |
| Geofences | User can only access/modify own geofences |
| Places | User can only access/modify own places |
| Statistics | User can only view own statistics |

### Data Protection

- **Input Validation**: All coordinates validated against ranges
- **SQL Injection Prevention**: Parameterized queries via gRPC
- **Rate Limiting**: 100 location reports/minute per device
- **Data Retention**: Configurable location history retention (default 90 days)

### Privacy Considerations

- Location data is highly sensitive PII
- No location sharing without explicit consent
- Audit logging for all location access
- GDPR-compliant data deletion

---

## Event-Driven Architecture

### Published Events

| Event | Subject | Trigger | Payload |
|-------|---------|---------|---------|
| `location.updated` | `location.updated` | After location stored | location_id, device_id, lat, lon, timestamp |
| `geofence.entered` | `location.geofence.entered` | Device enters boundary | geofence_id, device_id, lat, lon |
| `geofence.exited` | `location.geofence.exited` | Device exits boundary | geofence_id, device_id, lat, lon |
| `geofence.created` | `location.geofence.created` | New geofence created | geofence_id, name, shape_type |
| `geofence.deleted` | `location.geofence.deleted` | Geofence removed | geofence_id |
| `place.created` | `location.place.created` | New place saved | place_id, name, category |

### Consumed Events

| Event | Source | Handler | Action |
|-------|--------|---------|--------|
| `device.deleted` | device_service | `handle_device_deleted()` | Delete device locations |
| `user.deleted` | account_service | `handle_user_deleted()` | Delete all user data |

### Event Processing Guarantees

- **Delivery**: At-least-once via NATS JetStream
- **Ordering**: Per-subject ordering preserved
- **Idempotency**: Handlers check for duplicate processing
- **Retry**: 3 retries with exponential backoff

---

## Error Handling

### Exception Mapping

| Exception | HTTP Status | Error Code | Message |
|-----------|-------------|------------|---------|
| ValidationError | 422 | VALIDATION_ERROR | Field validation details |
| NotFoundError | 404 | NOT_FOUND | Resource not found |
| AccessDeniedError | 403 | ACCESS_DENIED | User doesn't own resource |
| AuthenticationError | 401 | UNAUTHORIZED | Invalid or missing token |
| DatabaseError | 500 | INTERNAL_ERROR | Database operation failed |
| EventPublishError | 500 | EVENT_ERROR | Event publishing failed |

### Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid coordinates",
    "details": {
      "latitude": "must be between -90 and 90"
    }
  },
  "timestamp": "2025-01-01T12:00:00Z"
}
```

### Graceful Degradation

| Failure | Degradation Strategy |
|---------|---------------------|
| Database unavailable | Return 503, health check fails |
| NATS unavailable | Store events locally, retry later |
| Redis unavailable | Skip caching, use database directly |
| Consul unavailable | Use cached service addresses |

---

## Performance Considerations

### Caching Strategy

| Data | Cache TTL | Invalidation |
|------|-----------|--------------|
| Device latest location | 30 seconds | On new location |
| Geofence definitions | 5 minutes | On update/delete |
| Place definitions | 10 minutes | On update/delete |
| User statistics | 1 minute | On location update |

### Query Optimization

| Query | Optimization | Index Used |
|-------|--------------|------------|
| Latest location by device | LIMIT 1 + ORDER BY | idx_locations_device_timestamp |
| Location history | Time range filter | idx_locations_device_timestamp |
| Nearby devices | ST_DWithin + time filter | idx_locations_geom |
| Geofence check | ST_DWithin on active only | idx_geofences_geom |

### Batch Processing

- Batch location upload: Process sequentially, commit every 100
- Parallel geofence checking: Check multiple geofences concurrently
- Async event publishing: Non-blocking event publication

### Performance Targets

| Metric | Target |
|--------|--------|
| Location report latency (p95) | < 100ms |
| Geofence check latency | < 50ms |
| Nearby search latency | < 200ms |
| Throughput | 5000 locations/second |

---

## Deployment Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LOCATION_SERVICE_PORT` | HTTP port | 8224 |
| `POSTGRES_GRPC_HOST` | Database host | localhost |
| `POSTGRES_GRPC_PORT` | Database port | 50061 |
| `NATS_URL` | NATS connection | nats://localhost:4222 |
| `REDIS_GRPC_HOST` | Redis host | localhost |
| `REDIS_GRPC_PORT` | Redis port | 50055 |
| `CONSUL_HOST` | Consul host | localhost |
| `CONSUL_PORT` | Consul port | 8500 |
| `CONSUL_ENABLED` | Enable Consul registration | true |
| `LOG_LEVEL` | Logging level | INFO |

### Health Check

```json
GET /health
{
  "status": "operational",
  "service": "location_service",
  "version": "1.0.0",
  "database_connected": true,
  "cache_connected": true,
  "geofencing_enabled": true,
  "route_tracking_enabled": true,
  "timestamp": "2025-01-01T12:00:00Z"
}
```

### Kubernetes Resources

```yaml
resources:
  requests:
    cpu: "250m"
    memory: "512Mi"
  limits:
    cpu: "1000m"
    memory: "2Gi"
```

### Scaling Configuration

- **Horizontal**: Stateless, scale via replicas
- **Connection Pool**: Max 20 database connections per instance
- **Event Processing**: NATS queue groups for distributed handling

---

## Summary

| Section | Items |
|---------|-------|
| Components | 5 (Service, Repository, Clients, Events, Models) |
| Database Tables | 4 (locations, geofences, places, routes) |
| PostGIS Functions Used | 6 (ST_Point, ST_DWithin, ST_Contains, etc.) |
| Published Events | 6 |
| Consumed Events | 2 |
| API Endpoints | 18 |
