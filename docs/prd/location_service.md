# Location Service - Product Requirements Document (PRD)

## Product Overview

**Service Name**: location_service
**Port**: 8224
**Purpose**: Location Service provides spatial intelligence for the isA platform, enabling real-time device tracking, geofencing, place management, and location-based automation. It is the foundation for family safety features, device finder, and location-aware services.

### Key Capabilities

- **Real-time Location Tracking**: Receive and store device location updates with GPS, WiFi, cellular, and hybrid positioning
- **Geofencing Engine**: Create virtual boundaries that trigger events when devices enter, exit, or dwell within areas
- **Place Management**: Define and manage named locations (home, work, school) with automatic recognition
- **Spatial Search**: Find nearby devices, search locations within radius or polygon areas
- **Location History**: Query historical device locations with time range and pagination
- **Distance Calculation**: Compute distances between geographic points

### Service Boundaries

- **Owns**:
  - Location records (coordinates, accuracy, metadata)
  - Geofence definitions and trigger history
  - Place definitions and visit statistics
  - Route recordings and waypoints

- **Consumes**:
  - `device_service`: Device ownership verification
  - `account_service`: User existence validation
  - `notification_service`: Alert delivery on geofence triggers

- **Publishes**:
  - `location.updated`: Device location change
  - `geofence.entered`: Device entered geofence
  - `geofence.exited`: Device left geofence
  - `geofence.created`: New geofence created
  - `geofence.deleted`: Geofence removed
  - `place.created`: New place created

---

## Target Users

### Primary Users

- **End User (Parent/Guardian)**: Tracks family members' devices, sets up safety geofences (school, home), receives arrival/departure notifications
- **End User (Device Owner)**: Views own location history, manages personal places, shares location with family
- **Family Admin**: Manages family-wide geofences, monitors all family devices

### Internal Users

- **notification_service**: Receives geofence events to send push notifications
- **automation_service**: Triggers location-based automations
- **analytics_service**: Aggregates location data for usage insights
- **calendar_service**: Links places to calendar events

### Personas

1. **Sarah (Concerned Parent)**
   - Role: Mother of two children with school devices
   - Needs: Know when kids arrive at school, leave soccer practice
   - Pain Points: Worries about children's safety, wants peace of mind
   - Goal: Automatic notifications without actively checking app

2. **Mike (Tech-Savvy Dad)**
   - Role: Family administrator managing 5 devices
   - Needs: Set up complex geofences, view location history
   - Pain Points: Wants flexibility in geofence shapes and schedules
   - Goal: Complete visibility and control over family device locations

3. **Emma (Teenager)**
   - Role: Device user being tracked
   - Needs: Privacy when appropriate, share location voluntarily
   - Pain Points: Feels surveilled, wants agency
   - Goal: Balance between safety and independence

4. **System Integrator**
   - Role: Developer building on location API
   - Needs: Reliable API, clear documentation, real-time events
   - Pain Points: Needs consistent data formats, low latency
   - Goal: Build location-aware features efficiently

---

## Epics and User Stories

### Epic 1: Location Tracking
**Goal**: Enable devices to report locations and users to view them
**Priority**: High

**User Stories**:

**US-1.1**: As a device, I want to report my current location so that the system knows where I am
- **Acceptance Criteria**:
  - [ ] Location stored with coordinates, accuracy, timestamp
  - [ ] Supports GPS, WiFi, cellular, hybrid methods
  - [ ] Returns location_id on success
  - [ ] Publishes location.updated event
- **API**: `POST /api/v1/locations`

**US-1.2**: As a device, I want to upload cached locations in batch so that offline periods are synced
- **Acceptance Criteria**:
  - [ ] Accepts up to 1000 locations per batch
  - [ ] Processes each location and tracks success/failure
  - [ ] Returns summary with counts
- **API**: `POST /api/v1/locations/batch`

**US-1.3**: As a parent, I want to see my child's current location so that I know they're safe
- **Acceptance Criteria**:
  - [ ] Returns latest location for specified device
  - [ ] Only returns if user owns the device
  - [ ] Returns 404 if no location found
- **API**: `GET /api/v1/locations/device/{device_id}/latest`

**US-1.4**: As a user, I want to view location history for my device so that I can see where it has been
- **Acceptance Criteria**:
  - [ ] Supports time range filtering (start_time, end_time)
  - [ ] Supports pagination (limit, offset)
  - [ ] Returns locations sorted by timestamp descending
- **API**: `GET /api/v1/locations/device/{device_id}/history`

**US-1.5**: As a user, I want to see all my devices' locations on a map so that I have family overview
- **Acceptance Criteria**:
  - [ ] Returns latest location for each user device
  - [ ] Only returns user's own devices
- **API**: `GET /api/v1/locations/user/{user_id}`

---

### Epic 2: Geofence Management
**Goal**: Enable users to create and manage geofences
**Priority**: High

**User Stories**:

**US-2.1**: As a parent, I want to create a geofence around school so that I'm notified when my child arrives/leaves
- **Acceptance Criteria**:
  - [ ] Supports circle, polygon, rectangle shapes
  - [ ] Requires radius for circle shapes
  - [ ] Requires 3+ coordinates for polygon
  - [ ] Publishes geofence.created event
- **API**: `POST /api/v1/geofences`

**US-2.2**: As a user, I want to list all my geofences so that I can manage them
- **Acceptance Criteria**:
  - [ ] Returns all user's geofences
  - [ ] Supports active_only filter
  - [ ] Supports pagination
- **API**: `GET /api/v1/geofences`

**US-2.3**: As a user, I want to view geofence details so that I can see its configuration
- **Acceptance Criteria**:
  - [ ] Returns full geofence data including trigger settings
  - [ ] Returns 404 if not found or not owned
- **API**: `GET /api/v1/geofences/{geofence_id}`

**US-2.4**: As a user, I want to update my geofence settings so that I can adjust triggers and targets
- **Acceptance Criteria**:
  - [ ] Supports partial updates
  - [ ] Can update triggers, target devices, schedule
  - [ ] Returns 403 if not owned
- **API**: `PUT /api/v1/geofences/{geofence_id}`

**US-2.5**: As a user, I want to delete a geofence so that it stops monitoring
- **Acceptance Criteria**:
  - [ ] Permanently removes geofence
  - [ ] Publishes geofence.deleted event
  - [ ] Returns 403 if not owned
- **API**: `DELETE /api/v1/geofences/{geofence_id}`

---

### Epic 3: Geofence Activation
**Goal**: Enable users to temporarily enable/disable geofences
**Priority**: Medium

**User Stories**:

**US-3.1**: As a user, I want to deactivate a geofence temporarily so that I stop getting notifications during vacation
- **Acceptance Criteria**:
  - [ ] Sets geofence active=false
  - [ ] Preserves all configuration
  - [ ] Inactive geofences don't trigger events
- **API**: `POST /api/v1/geofences/{geofence_id}/deactivate`

**US-3.2**: As a user, I want to reactivate a geofence so that monitoring resumes
- **Acceptance Criteria**:
  - [ ] Sets geofence active=true
  - [ ] Immediately begins monitoring
- **API**: `POST /api/v1/geofences/{geofence_id}/activate`

**US-3.3**: As a user, I want to view geofence event history so that I can see past triggers
- **Acceptance Criteria**:
  - [ ] Lists enter/exit/dwell events for geofence
  - [ ] Includes device info and timestamps
  - [ ] Supports pagination
- **API**: `GET /api/v1/geofences/{geofence_id}/events`

**US-3.4**: As a user, I want to check if a device is currently in any geofences so that I know their context
- **Acceptance Criteria**:
  - [ ] Returns list of geofences containing device's latest location
  - [ ] Only checks active geofences
- **API**: `GET /api/v1/geofences/device/{device_id}/check`

---

### Epic 4: Place Management
**Goal**: Enable users to create and manage named places
**Priority**: Medium

**User Stories**:

**US-4.1**: As a user, I want to save a place as "Home" so that the system recognizes when I'm home
- **Acceptance Criteria**:
  - [ ] Creates place with name, category, coordinates
  - [ ] Supports categories: home, work, school, favorite, custom
  - [ ] Sets recognition radius (default 100m)
- **API**: `POST /api/v1/places`

**US-4.2**: As a user, I want to list my saved places so that I can see all my locations
- **Acceptance Criteria**:
  - [ ] Returns all user's places
  - [ ] Includes visit statistics (count, last visit)
- **API**: `GET /api/v1/places/user/{user_id}`

**US-4.3**: As a user, I want to view place details so that I can see its configuration
- **Acceptance Criteria**:
  - [ ] Returns place with all fields
  - [ ] Returns 404 if not found or not owned
- **API**: `GET /api/v1/places/{place_id}`

**US-4.4**: As a user, I want to update my place so that I can change its name or location
- **Acceptance Criteria**:
  - [ ] Supports partial updates
  - [ ] Returns 403 if not owned
- **API**: `PUT /api/v1/places/{place_id}`

**US-4.5**: As a user, I want to delete a place so that it's no longer tracked
- **Acceptance Criteria**:
  - [ ] Permanently removes place
  - [ ] Returns 403 if not owned
- **API**: `DELETE /api/v1/places/{place_id}`

---

### Epic 5: Location Search
**Goal**: Enable users to find devices and search locations spatially
**Priority**: Medium

**User Stories**:

**US-5.1**: As a user, I want to find devices near a location so that I can see who's nearby
- **Acceptance Criteria**:
  - [ ] Searches by center point and radius
  - [ ] Returns devices with recent locations (time window)
  - [ ] Calculates distance from search point
  - [ ] Maximum radius 50km
- **API**: `GET /api/v1/locations/nearby`

**US-5.2**: As a user, I want to search locations in a circular area so that I can find historical visits
- **Acceptance Criteria**:
  - [ ] Supports center point, radius, time range
  - [ ] Returns matching location records
  - [ ] Maximum radius 100km
- **API**: `POST /api/v1/locations/search/radius`

**US-5.3**: As a user, I want to search locations in a polygon area so that I can query custom shapes
- **Acceptance Criteria**:
  - [ ] Accepts polygon coordinates (3+ points)
  - [ ] Returns locations within polygon
- **API**: `POST /api/v1/locations/search/polygon`

**US-5.4**: As a user, I want to calculate distance between two points so that I can plan routes
- **Acceptance Criteria**:
  - [ ] Returns distance in meters and kilometers
  - [ ] Uses Haversine formula
- **API**: `GET /api/v1/locations/distance`

---

### Epic 6: Statistics and Monitoring
**Goal**: Provide location statistics and service health
**Priority**: Low

**User Stories**:

**US-6.1**: As a user, I want to see my location statistics so that I understand usage
- **Acceptance Criteria**:
  - [ ] Returns total locations, devices, geofences, places
  - [ ] Returns 24-hour activity counts
- **API**: `GET /api/v1/stats/user/{user_id}`

**US-6.2**: As an operator, I want to check service health so that I can monitor system status
- **Acceptance Criteria**:
  - [ ] Returns service status (operational/degraded)
  - [ ] Indicates database connectivity
  - [ ] Indicates feature availability
- **API**: `GET /health`

---

## API Surface Documentation

### Base URL
`http://localhost:8224/api/v1`

### Authentication
- **Method**: JWT Bearer Token
- **Header**: `Authorization: Bearer <token>`
- **Internal**: `X-Internal-Call: true` bypasses auth (service-to-service)

---

### Endpoint: Report Location
- **Method**: `POST`
- **Path**: `/api/v1/locations`
- **Description**: Report device location update

**Request Body**:
```json
{
  "device_id": "string (required, 1-100 chars)",
  "latitude": "float (required, -90 to 90)",
  "longitude": "float (required, -180 to 180)",
  "altitude": "float (optional)",
  "accuracy": "float (required, > 0)",
  "heading": "float (optional, 0-360)",
  "speed": "float (optional, >= 0)",
  "address": "string (optional, max 500)",
  "city": "string (optional, max 100)",
  "state": "string (optional, max 100)",
  "country": "string (optional, max 100)",
  "postal_code": "string (optional, max 20)",
  "location_method": "string (enum: gps, wifi, cellular, bluetooth, manual, hybrid)",
  "battery_level": "float (optional, 0-100)",
  "timestamp": "ISO8601 datetime (optional, default: server time)",
  "source": "string (optional, default: device)",
  "metadata": "object (optional)"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "location_id": "loc_abc123",
  "operation": "report_location",
  "message": "Location reported successfully",
  "data": {
    "location_id": "loc_abc123",
    "device_id": "dev_xyz789",
    "latitude": 37.7749,
    "longitude": -122.4194
  }
}
```

**Error Responses**:
| Status | Code | Description |
|--------|------|-------------|
| 400 | BAD_REQUEST | Invalid request format |
| 422 | VALIDATION_ERROR | Field validation failed |
| 500 | INTERNAL_ERROR | Server error |

**Example**:
```bash
curl -X POST http://localhost:8224/api/v1/locations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "dev_123",
    "latitude": 37.7749,
    "longitude": -122.4194,
    "accuracy": 10.0,
    "location_method": "gps"
  }'
```

---

### Endpoint: Batch Report Locations
- **Method**: `POST`
- **Path**: `/api/v1/locations/batch`
- **Description**: Report multiple locations (offline sync)

**Request Body**:
```json
{
  "locations": [
    {
      "device_id": "string",
      "latitude": "float",
      "longitude": "float",
      "accuracy": "float",
      "timestamp": "ISO8601 datetime"
    }
  ],
  "compression": "string (optional: gzip, lz4)",
  "batch_id": "string (optional)"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "operation": "batch_report_locations",
  "message": "Batch processed: 98 successful, 2 failed",
  "affected_count": 98,
  "data": {
    "location_ids": ["loc_1", "loc_2", "..."]
  }
}
```

---

### Endpoint: Get Device Latest Location
- **Method**: `GET`
- **Path**: `/api/v1/locations/device/{device_id}/latest`
- **Description**: Get most recent location for device

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| device_id | string | Device identifier |

**Response** (200 OK):
```json
{
  "location_id": "loc_abc123",
  "device_id": "dev_xyz789",
  "user_id": "usr_123",
  "latitude": 37.7749,
  "longitude": -122.4194,
  "altitude": 50.0,
  "accuracy": 10.5,
  "heading": 180.0,
  "speed": 1.2,
  "address": "123 Main St",
  "city": "San Francisco",
  "state": "CA",
  "country": "USA",
  "location_method": "gps",
  "battery_level": 85.0,
  "timestamp": "2025-01-01T12:00:00Z",
  "created_at": "2025-01-01T12:00:01Z"
}
```

**Error Responses**:
| Status | Code | Description |
|--------|------|-------------|
| 403 | ACCESS_DENIED | Device not owned by user |
| 404 | NOT_FOUND | No location found |

---

### Endpoint: Get Device Location History
- **Method**: `GET`
- **Path**: `/api/v1/locations/device/{device_id}/history`
- **Description**: Get historical locations for device

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| start_time | datetime | - | Filter from this time |
| end_time | datetime | - | Filter until this time |
| limit | integer | 100 | Max results (1-1000) |
| offset | integer | 0 | Skip first N results |

**Response** (200 OK):
```json
{
  "locations": [
    {
      "location_id": "loc_abc123",
      "latitude": 37.7749,
      "longitude": -122.4194,
      "timestamp": "2025-01-01T12:00:00Z"
    }
  ],
  "count": 50
}
```

---

### Endpoint: Create Geofence
- **Method**: `POST`
- **Path**: `/api/v1/geofences`
- **Description**: Create a new geofence

**Request Body**:
```json
{
  "name": "string (required, 1-200 chars)",
  "description": "string (optional, max 1000)",
  "shape_type": "string (enum: circle, polygon, rectangle)",
  "center_lat": "float (required, -90 to 90)",
  "center_lon": "float (required, -180 to 180)",
  "radius": "float (required for circle, > 0)",
  "polygon_coordinates": "array of [lat, lon] (required for polygon, 3+ points)",
  "trigger_on_enter": "boolean (default: true)",
  "trigger_on_exit": "boolean (default: true)",
  "trigger_on_dwell": "boolean (default: false)",
  "dwell_time_seconds": "integer (optional, >= 60)",
  "target_devices": "array of device_ids",
  "target_groups": "array of group_ids",
  "active_days": "array of day names",
  "active_hours": "object {start: HH:MM, end: HH:MM}",
  "notification_channels": "array of channel types",
  "notification_template": "string (optional)",
  "tags": "array of strings",
  "metadata": "object (optional)"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "geofence_id": "geo_abc123",
  "operation": "create_geofence",
  "message": "Geofence created successfully",
  "data": {
    "geofence_id": "geo_abc123",
    "name": "School",
    "shape_type": "circle",
    "active": true
  }
}
```

**Error Responses**:
| Status | Code | Description |
|--------|------|-------------|
| 400 | BAD_REQUEST | Missing radius for circle |
| 400 | BAD_REQUEST | Less than 3 polygon coordinates |
| 422 | VALIDATION_ERROR | Field validation failed |

---

### Endpoint: List Geofences
- **Method**: `GET`
- **Path**: `/api/v1/geofences`
- **Description**: List user's geofences

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| active_only | boolean | false | Only return active geofences |
| limit | integer | 100 | Max results (1-500) |
| offset | integer | 0 | Skip first N results |

**Response** (200 OK):
```json
{
  "geofences": [
    {
      "geofence_id": "geo_abc123",
      "name": "School",
      "shape_type": "circle",
      "center_lat": 37.7749,
      "center_lon": -122.4194,
      "radius": 100,
      "active": true
    }
  ],
  "count": 5
}
```

---

### Endpoint: Get Geofence
- **Method**: `GET`
- **Path**: `/api/v1/geofences/{geofence_id}`
- **Description**: Get geofence details

**Response** (200 OK):
```json
{
  "geofence_id": "geo_abc123",
  "name": "School",
  "description": "Elementary school",
  "user_id": "usr_123",
  "shape_type": "circle",
  "center_lat": 37.7749,
  "center_lon": -122.4194,
  "radius": 100,
  "active": true,
  "trigger_on_enter": true,
  "trigger_on_exit": true,
  "trigger_on_dwell": false,
  "target_devices": ["dev_123"],
  "total_triggers": 45,
  "last_triggered": "2025-01-01T08:00:00Z",
  "created_at": "2024-09-01T00:00:00Z",
  "updated_at": "2025-01-01T08:00:00Z"
}
```

---

### Endpoint: Update Geofence
- **Method**: `PUT`
- **Path**: `/api/v1/geofences/{geofence_id}`
- **Description**: Update geofence settings

**Request Body** (partial update):
```json
{
  "name": "string (optional)",
  "trigger_on_enter": "boolean (optional)",
  "target_devices": "array (optional)"
}
```

---

### Endpoint: Delete Geofence
- **Method**: `DELETE`
- **Path**: `/api/v1/geofences/{geofence_id}`
- **Description**: Delete geofence

**Response** (200 OK):
```json
{
  "success": true,
  "operation": "delete_geofence",
  "message": "Geofence deleted successfully"
}
```

---

### Endpoint: Activate/Deactivate Geofence
- **Method**: `POST`
- **Path**: `/api/v1/geofences/{geofence_id}/activate` or `/deactivate`
- **Description**: Toggle geofence active status

**Response** (200 OK):
```json
{
  "success": true,
  "geofence_id": "geo_abc123",
  "operation": "toggle_geofence",
  "message": "Geofence activated successfully"
}
```

---

### Endpoint: Create Place
- **Method**: `POST`
- **Path**: `/api/v1/places`
- **Description**: Create a named place

**Request Body**:
```json
{
  "name": "string (required, 1-200 chars)",
  "category": "string (enum: home, work, school, favorite, custom)",
  "latitude": "float (required, -90 to 90)",
  "longitude": "float (required, -180 to 180)",
  "address": "string (optional, max 500)",
  "radius": "float (default: 100, 0-1000)",
  "icon": "string (optional)",
  "color": "string (optional)",
  "tags": "array of strings"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "place_id": "plc_abc123",
  "operation": "create_place",
  "message": "Place created successfully"
}
```

---

### Endpoint: List User Places
- **Method**: `GET`
- **Path**: `/api/v1/places/user/{user_id}`
- **Description**: List user's saved places

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "places": [
      {
        "place_id": "plc_abc123",
        "name": "Home",
        "category": "home",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "visit_count": 150,
        "last_visit": "2025-01-01T20:00:00Z"
      }
    ],
    "count": 3
  }
}
```

---

### Endpoint: Find Nearby Devices
- **Method**: `GET`
- **Path**: `/api/v1/locations/nearby`
- **Description**: Find devices near a location

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| latitude | float | required | Search center latitude |
| longitude | float | required | Search center longitude |
| radius_meters | float | required | Search radius (max 50000) |
| device_types | string | - | Comma-separated types |
| time_window_minutes | integer | 30 | Max age (1-1440) |
| limit | integer | 50 | Max results (1-500) |

**Response** (200 OK):
```json
{
  "devices": [
    {
      "device_id": "dev_123",
      "device_name": "John's Phone",
      "latitude": 37.7750,
      "longitude": -122.4195,
      "distance": 45.2,
      "timestamp": "2025-01-01T12:00:00Z"
    }
  ],
  "count": 2
}
```

---

### Endpoint: Calculate Distance
- **Method**: `GET`
- **Path**: `/api/v1/locations/distance`
- **Description**: Calculate distance between two points

**Query Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| from_lat | float | Origin latitude |
| from_lon | float | Origin longitude |
| to_lat | float | Destination latitude |
| to_lon | float | Destination longitude |

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "from_lat": 37.7749,
    "from_lon": -122.4194,
    "to_lat": 37.7849,
    "to_lon": -122.4294,
    "distance_meters": 1532.5,
    "distance_km": 1.53
  }
}
```

---

### Endpoint: Health Check
- **Method**: `GET`
- **Path**: `/health`
- **Description**: Service health status

**Response** (200 OK):
```json
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

---

## Functional Requirements

### Location Management

**FR-001: Location Reporting**
- System SHALL accept location reports with coordinates, accuracy, and device_id
- System SHALL validate coordinate ranges (-90/90 lat, -180/180 lon)
- System SHALL require positive accuracy value
- System SHALL generate unique location_id on creation
- System SHALL publish `location.updated` event on success

**FR-002: Batch Location Upload**
- System SHALL accept batch of up to 1000 locations
- System SHALL process locations sequentially
- System SHALL track success/failure counts
- System SHALL return summary with processed counts

**FR-003: Location Retrieval**
- System SHALL return latest location for specified device
- System SHALL verify user owns the device before returning data
- System SHALL return 404 if no location exists

**FR-004: Location History**
- System SHALL support time range filtering (start_time, end_time)
- System SHALL support pagination (limit: 1-1000, offset: 0+)
- System SHALL return locations sorted by timestamp descending

### Geofence Management

**FR-005: Geofence Creation**
- System SHALL support circle, polygon, and rectangle shapes
- System SHALL require radius for circle shapes
- System SHALL require 3+ coordinates for polygon shapes
- System SHALL validate center coordinates
- System SHALL publish `geofence.created` event

**FR-006: Geofence Triggering**
- System SHALL check all active geofences on location update
- System SHALL publish `geofence.entered` when device enters
- System SHALL publish `geofence.exited` when device exits
- System SHALL only trigger for targeted devices

**FR-007: Geofence Modification**
- System SHALL support partial updates
- System SHALL verify ownership before update
- System SHALL support activation/deactivation

**FR-008: Geofence Deletion**
- System SHALL permanently remove geofence on delete
- System SHALL publish `geofence.deleted` event
- System SHALL verify ownership before delete

### Place Management

**FR-009: Place Creation**
- System SHALL create places with name, category, coordinates
- System SHALL support predefined categories (home, work, school, favorite, custom)
- System SHALL set default recognition radius (100m)

**FR-010: Place Retrieval**
- System SHALL return place data by ID
- System SHALL include visit statistics
- System SHALL verify ownership

### Search Operations

**FR-011: Nearby Device Search**
- System SHALL search by center point and radius
- System SHALL filter by time window (default 30 minutes)
- System SHALL calculate distance from search point
- System SHALL limit radius to 50km maximum

**FR-012: Spatial Search**
- System SHALL support radius-based search
- System SHALL support polygon-based search
- System SHALL limit radius to 100km maximum

**FR-013: Distance Calculation**
- System SHALL calculate distance using Haversine formula
- System SHALL return distance in meters and kilometers

### Data Management

**FR-014: Device Data Cleanup**
- System SHALL delete all locations when device deleted
- System SHALL handle `device.deleted` event
- System SHALL be idempotent

**FR-015: User Data Cleanup**
- System SHALL delete all user data when user deleted
- System SHALL handle `user.deleted` event
- System SHALL cascade to all user's devices

### Validation

**FR-016: Input Validation**
- System SHALL validate all input fields
- System SHALL return 422 with details on validation failure
- System SHALL trim whitespace from string inputs

**FR-017: Authorization Validation**
- System SHALL verify user owns resource before access
- System SHALL return 403 on unauthorized access

---

## Non-Functional Requirements

### Performance

**NFR-001: Response Time**
- Location report API SHALL complete in < 100ms (p95)
- Geofence check SHALL complete in < 50ms per geofence
- Database spatial queries SHALL complete in < 100ms (p95)

**NFR-002: Throughput**
- System SHALL handle 5000 location reports/second
- System SHALL support 10000 active geofences per instance

**NFR-003: Batch Processing**
- Batch upload of 1000 locations SHALL complete in < 10 seconds

### Reliability

**NFR-004: Availability**
- System SHALL maintain 99.9% uptime
- System SHALL gracefully degrade if database unavailable

**NFR-005: Data Durability**
- All location data SHALL be persisted to PostgreSQL
- Events SHALL be delivered at-least-once

**NFR-006: Idempotency**
- Event handlers SHALL be idempotent
- Duplicate event processing SHALL not cause errors

### Security

**NFR-007: Authentication**
- All endpoints SHALL require JWT authentication
- Internal calls SHALL use X-Internal-Call header

**NFR-008: Authorization**
- Users SHALL only access their own locations
- Users SHALL only modify their own geofences/places

**NFR-009: Data Privacy**
- Location data SHALL be encrypted at rest
- Location data SHALL not be exposed to unauthorized users

### Scalability

**NFR-010: Horizontal Scaling**
- Service SHALL scale horizontally
- Database connections SHALL use connection pooling

### Observability

**NFR-011: Logging**
- All requests SHALL be logged with correlation_id
- Location updates SHALL log device_id and coordinates
- Errors SHALL include stack traces

**NFR-012: Health Checks**
- Service SHALL expose /health endpoint
- Health check SHALL verify database connectivity
- Health check SHALL verify PostGIS availability

---

## Success Metrics

### Operational Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Uptime | 99.9% | Monthly |
| Location Report Latency (p95) | < 100ms | Daily |
| Geofence Check Latency | < 50ms | Daily |
| Error Rate | < 0.1% | Hourly |
| Event Delivery Rate | 99.99% | Daily |

### Business Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Daily Active Devices | Track growth | Daily |
| Locations Stored (daily) | Track volume | Daily |
| Geofence Triggers (daily) | Track engagement | Daily |
| Active Geofences | Track adoption | Weekly |
| Places Created | Track feature usage | Weekly |

### Quality Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Location Accuracy | < 20m median | Weekly |
| Geofence False Positive Rate | < 1% | Weekly |
| Batch Success Rate | > 99% | Daily |

---

## Summary

| Section | Count |
|---------|-------|
| Epics | 6 |
| User Stories | 26 |
| API Endpoints | 18 |
| Functional Requirements | 17 |
| Non-Functional Requirements | 12 |
| Success Metrics | 13 |
