# Location Service - Domain Context

## Overview

Location Service is the spatial intelligence layer of the isA platform, responsible for real-time device location tracking, geofencing, place management, and route recording. It provides the foundation for location-aware features across the platform, enabling family safety, device tracking, and location-based automation.

**Service Identity:**
- **Port**: 8224
- **Schema**: `location`
- **Version**: 1.0.0

---

## Business Taxonomy

### Primary Entities

- **Location**: A point-in-time geographic position of a device, including coordinates (latitude/longitude), altitude, accuracy, speed, and heading. Each location is associated with a device and user.

- **Geofence**: A virtual geographic boundary (circle, polygon, or rectangle) that triggers events when devices enter, exit, or dwell within the area. Used for safety alerts, automation triggers, and location-based reminders.

- **Place**: A user-defined named location with semantic meaning (home, work, school, etc.). Places have a recognition radius and track visit statistics.

- **Route**: A recorded path of device movement over time, capturing waypoints, distance traveled, duration, and speed metrics.

- **Location Event**: A significant location-related occurrence such as geofence trigger, significant movement detection, or device state change.

### Supporting Concepts

- **Location Method**: The technology used to determine position (GPS, WiFi, Cellular, Bluetooth, Hybrid, Manual).

- **Geofence Shape**: The geometric form of a geofence boundary (Circle with radius, Polygon with vertices, Rectangle with bounds).

- **Geofence Trigger**: The condition that activates a geofence event (Enter, Exit, Dwell).

- **Place Category**: Classification of user-defined places (Home, Work, School, Favorite, Custom).

- **Accuracy**: The estimated precision of a location fix in meters. Lower values indicate higher confidence.

- **Heading**: The direction of travel in degrees (0-360), where 0 is North.

### Domain Terminology

- **Dwell Time**: The minimum duration a device must remain within a geofence to trigger a dwell event.
- **Recognition Radius**: The distance from a place's center within which the device is considered "at" that place.
- **Significant Movement**: A location change exceeding a threshold distance from the previous position.
- **Time Window**: A period used to filter location queries (e.g., locations within last 30 minutes).
- **Reverse Geocoding**: Converting coordinates to human-readable addresses.
- **Spatial Query**: Database query using geographic operations (within radius, inside polygon).

---

## Domain Scenarios

### 1. Device Location Reporting

- **Trigger**: Device app or firmware reports current position
- **Actors**: Device, Location Service, NATS Event Bus
- **Preconditions**: Device is registered and associated with a user
- **Flow**:
  1. Device sends location data (coordinates, accuracy, speed, etc.)
  2. Service validates coordinate ranges and accuracy
  3. Service stores location in PostgreSQL with PostGIS
  4. Service checks if location triggers any active geofences
  5. Service publishes `location.updated` event
  6. If geofence triggered, publishes `geofence.entered` or `geofence.exited`
- **Outcome**: Location stored, events published for downstream processing
- **Events**: `location.updated`, optionally `geofence.entered`/`geofence.exited`
- **Errors**:
  - ValidationError: Invalid coordinates or accuracy
  - AuthorizationError: Device not owned by user

### 2. Batch Location Upload

- **Trigger**: Device uploads multiple cached locations (offline sync)
- **Actors**: Device, Location Service
- **Preconditions**: Device has accumulated offline locations
- **Flow**:
  1. Device sends array of locations (up to 1000)
  2. Service processes each location sequentially
  3. Service tracks success/failure counts
  4. Service returns batch result summary
- **Outcome**: Multiple locations stored efficiently
- **Events**: Multiple `location.updated` events
- **Errors**:
  - PartialFailure: Some locations failed validation
  - BatchTooLarge: Exceeded 1000 location limit

### 3. Geofence Creation and Management

- **Trigger**: User creates a geofence via app/API
- **Actors**: User, Location Service
- **Preconditions**: User is authenticated
- **Flow**:
  1. User specifies geofence parameters (name, shape, triggers)
  2. Service validates shape-specific requirements (radius for circle, 3+ points for polygon)
  3. Service creates geofence with unique ID
  4. Service publishes `geofence.created` event
  5. Service begins monitoring targeted devices
- **Outcome**: Geofence active and monitoring devices
- **Events**: `geofence.created`
- **Errors**:
  - ValidationError: Missing radius for circle shape
  - ValidationError: Less than 3 coordinates for polygon

### 4. Geofence Trigger Detection

- **Trigger**: Device location update intersects geofence boundary
- **Actors**: Device (implicit), Location Service, Notification Service
- **Preconditions**: Geofence is active, device is targeted
- **Flow**:
  1. New location reported for device
  2. Service queries geofences targeting this device
  3. Service performs spatial query (point-in-polygon/radius)
  4. If device entered geofence, publishes `geofence.entered`
  5. If device exited geofence, publishes `geofence.exited`
  6. Notification Service sends configured alerts
- **Outcome**: Geofence events published, notifications sent
- **Events**: `geofence.entered`, `geofence.exited`
- **Errors**:
  - GeofenceInactive: Geofence was deactivated
  - TimeRestriction: Outside active hours

### 5. Place Management

- **Trigger**: User creates/updates a named place
- **Actors**: User, Location Service
- **Preconditions**: User is authenticated
- **Flow**:
  1. User provides place details (name, category, location, radius)
  2. Service validates coordinates and radius
  3. Service creates/updates place record
  4. Service publishes `place.created` event
- **Outcome**: Place saved for location recognition
- **Events**: `place.created`
- **Errors**:
  - ValidationError: Invalid coordinates
  - DuplicateName: Place with same name exists

### 6. Nearby Device Discovery

- **Trigger**: User queries for devices near a location
- **Actors**: User, Location Service
- **Preconditions**: User has device access permissions
- **Flow**:
  1. User specifies center point and search radius
  2. Service queries recent locations within radius
  3. Service filters by time window (default 30 minutes)
  4. Service calculates distance from search point
  5. Service returns sorted list by distance
- **Outcome**: List of nearby devices with distances
- **Events**: None
- **Errors**:
  - RadiusTooLarge: Exceeds 50km maximum
  - NoRecentLocations: No locations in time window

### 7. Location History Query

- **Trigger**: User requests device location history
- **Actors**: User, Location Service
- **Preconditions**: User owns the device
- **Flow**:
  1. User specifies device ID, time range, pagination
  2. Service verifies user owns device
  3. Service queries historical locations
  4. Service returns paginated results
- **Outcome**: Historical location data returned
- **Events**: None
- **Errors**:
  - AccessDenied: User doesn't own device
  - NotFound: No locations for device

### 8. Device Data Cleanup

- **Trigger**: Device or user deleted from system
- **Actors**: Device Service/Account Service, Location Service
- **Preconditions**: Deletion event received via NATS
- **Flow**:
  1. Service receives `device.deleted` or `user.deleted` event
  2. Service deletes all location records for device/user
  3. Service deletes associated geofences
  4. Service deletes associated places
- **Outcome**: All location data cleaned up
- **Events**: None (reactive handler)
- **Errors**:
  - CleanupPartialFailure: Some records failed to delete

---

## Domain Events

### Published Events

#### 1. `location.updated` (EventType.LOCATION_UPDATED)

- **When**: After successful location storage
- **Subject**: `location.updated`
- **Payload**:
  ```json
  {
    "event_type": "location.updated",
    "location_id": "loc_abc123",
    "device_id": "dev_xyz789",
    "user_id": "usr_123",
    "latitude": 37.7749,
    "longitude": -122.4194,
    "accuracy": 10.5,
    "altitude": 50.0,
    "speed": 1.2,
    "heading": 180.0,
    "location_method": "gps",
    "timestamp": "2025-01-01T12:00:00Z"
  }
  ```
- **Consumers**:
  - `notification_service`: Sends location alerts
  - `analytics_service`: Updates device activity metrics
  - `session_service`: Updates last known location
- **Ordering**: Per-device ordering guaranteed
- **Retry**: 3 retries with exponential backoff

#### 2. `geofence.entered` (EventType.GEOFENCE_ENTERED)

- **When**: Device enters a geofence boundary
- **Subject**: `location.geofence.entered`
- **Payload**:
  ```json
  {
    "event_type": "geofence.entered",
    "device_id": "dev_xyz789",
    "user_id": "usr_123",
    "geofence_id": "geo_abc123",
    "geofence_name": "Home",
    "latitude": 37.7749,
    "longitude": -122.4194,
    "timestamp": "2025-01-01T12:00:00Z"
  }
  ```
- **Consumers**:
  - `notification_service`: Sends "arrived at" notifications
  - `automation_service`: Triggers arrival automations

#### 3. `geofence.exited` (EventType.GEOFENCE_EXITED)

- **When**: Device exits a geofence boundary
- **Subject**: `location.geofence.exited`
- **Payload**:
  ```json
  {
    "event_type": "geofence.exited",
    "device_id": "dev_xyz789",
    "user_id": "usr_123",
    "geofence_id": "geo_abc123",
    "geofence_name": "Home",
    "latitude": 37.7749,
    "longitude": -122.4194,
    "timestamp": "2025-01-01T12:00:00Z"
  }
  ```
- **Consumers**:
  - `notification_service`: Sends "left" notifications
  - `automation_service`: Triggers departure automations

#### 4. `geofence.created` (EventType.GEOFENCE_CREATED)

- **When**: New geofence created
- **Subject**: `location.geofence.created`
- **Payload**:
  ```json
  {
    "event_type": "geofence.created",
    "geofence_id": "geo_abc123",
    "user_id": "usr_123",
    "name": "Office",
    "shape_type": "circle",
    "center_lat": 37.7749,
    "center_lon": -122.4194,
    "timestamp": "2025-01-01T12:00:00Z"
  }
  ```
- **Consumers**:
  - `notification_service`: Setup notification templates

#### 5. `geofence.deleted` (EventType.GEOFENCE_DELETED)

- **When**: Geofence deleted
- **Subject**: `location.geofence.deleted`
- **Payload**:
  ```json
  {
    "event_type": "geofence.deleted",
    "geofence_id": "geo_abc123",
    "user_id": "usr_123",
    "timestamp": "2025-01-01T12:00:00Z"
  }
  ```
- **Consumers**:
  - `notification_service`: Cleanup notification config

#### 6. `place.created` (EventType.PLACE_CREATED)

- **When**: New place created
- **Subject**: `location.place.created`
- **Payload**:
  ```json
  {
    "event_type": "place.created",
    "place_id": "plc_abc123",
    "user_id": "usr_123",
    "name": "Grandma's House",
    "category": "favorite",
    "latitude": 37.7749,
    "longitude": -122.4194,
    "timestamp": "2025-01-01T12:00:00Z"
  }
  ```
- **Consumers**:
  - `calendar_service`: Link to calendar events
  - `notification_service`: Enable place-based reminders

### Subscribed Events

#### 1. `device.deleted` from device_service

- **Subject**: `*.device.deleted`
- **Handler**: `handle_device_deleted()`
- **Purpose**: Clean up all location data for deleted device
- **Processing**: Idempotent, deletes locations/geofences/places for device

#### 2. `user.deleted` from account_service

- **Subject**: `*.user.deleted`
- **Handler**: `handle_user_deleted()`
- **Purpose**: Clean up all location data for deleted user
- **Processing**: Idempotent, cascades to all user's devices

---

## Core Concepts

### Concept 1: Spatial Data Management

Location Service uses PostgreSQL with PostGIS extension for spatial data operations. This enables efficient geographic queries like "find all devices within 1km" or "check if point is inside polygon". All coordinates are stored using WGS84 (SRID 4326), the standard GPS coordinate system. Spatial indexes dramatically accelerate these queries, essential for real-time geofence checking.

### Concept 2: Geofencing Engine

Geofences are virtual boundaries that generate events when crossed. The engine supports three shapes: circles (most common, defined by center + radius), polygons (arbitrary shapes with 3+ vertices), and rectangles. Each geofence can trigger on entry, exit, or dwell (staying inside for a minimum duration). Geofences can be time-restricted (active only certain hours/days) and targeted at specific devices or device groups.

### Concept 3: Location Accuracy and Confidence

Not all location fixes are equal. GPS provides high accuracy (5-15m) outdoors but struggles indoors. WiFi positioning works indoors but with lower accuracy (30-100m). Cellular is least accurate (100-1000m). The `accuracy` field indicates the estimated error radius. Services consuming location data should consider accuracy when making decisions - a 500m accuracy location should not trigger a 100m radius geofence.

### Concept 4: Battery-Aware Location Tracking

Continuous GPS tracking drains device batteries quickly. Location Service supports multiple tracking modes: high-accuracy (frequent GPS), balanced (hybrid GPS/WiFi), and power-save (cellular only). The service also receives `battery_level` with each location report, enabling adaptive tracking. Low battery locations may be less accurate as devices switch to power-saving modes.

### Concept 5: Privacy and Access Control

Location data is highly sensitive. All queries verify the requesting user owns the device before returning location data. Users can only see locations for their own devices. Organization-level access (family sharing) is handled through the organization_service, which provides group membership. Geofences and places are user-private by default.

### Concept 6: Offline and Batch Sync

Mobile devices frequently lose connectivity. Location Service supports batch upload of cached locations (up to 1000 per request). Each location includes its original timestamp, allowing accurate historical reconstruction. The batch endpoint processes locations sequentially, tracking success/failure counts, and returns a summary enabling clients to retry failed items.

---

## High-Level Business Rules

### Location Rules (BR-LOC-001 to BR-LOC-010)

**BR-LOC-001: Coordinate Range Validation**
- Latitude MUST be between -90 and 90 degrees
- Longitude MUST be between -180 and 180 degrees
- System validates on every location report
- Error: "ValidationError: Invalid coordinates"
- Example: `latitude=-91` fails, `latitude=37.7749` passes

**BR-LOC-002: Accuracy Requirement**
- Accuracy MUST be a positive number (meters)
- System rejects locations with zero or negative accuracy
- Error: "ValidationError: Accuracy must be positive"
- Example: `accuracy=0` fails, `accuracy=10.5` passes

**BR-LOC-003: Heading Range**
- Heading MUST be between 0 and 360 degrees (exclusive)
- 0 represents North, 90 East, 180 South, 270 West
- Error: "ValidationError: Heading must be 0-360"
- Example: `heading=360` fails, `heading=180` passes

**BR-LOC-004: Speed Non-Negative**
- Speed MUST be non-negative (m/s)
- Negative speeds indicate calculation error
- Error: "ValidationError: Speed cannot be negative"
- Example: `speed=-5` fails, `speed=0` passes (stationary)

**BR-LOC-005: Device Ownership for Location Access**
- User can ONLY access locations for devices they own
- System verifies ownership on every query
- Error: "AccessDenied: Device not owned by user"
- Related Rules: BR-AUTH-001

**BR-LOC-006: Timestamp Handling**
- If no timestamp provided, server UTC time is used
- Client timestamp MUST not be in future
- Error: "ValidationError: Timestamp cannot be future"
- Example: `timestamp=2099-01-01` fails

**BR-LOC-007: Batch Size Limit**
- Batch upload MUST NOT exceed 1000 locations
- Protects against memory exhaustion
- Error: "ValidationError: Batch exceeds 1000 limit"
- Related Rules: BR-LOC-008

**BR-LOC-008: Device ID Required**
- Every location MUST have a device_id
- Device ID MUST be 1-100 characters
- Error: "ValidationError: device_id required"

**BR-LOC-009: Location History Pagination**
- Limit MUST be 1-1000 (default 100)
- Offset MUST be non-negative
- Error: "ValidationError: Invalid pagination"

**BR-LOC-010: Time Window for Search**
- Time window MUST be 1-1440 minutes (24 hours max)
- Default is 30 minutes for nearby search
- Error: "ValidationError: Time window out of range"

### Geofence Rules (BR-GEO-001 to BR-GEO-010)

**BR-GEO-001: Circle Geofence Requires Radius**
- Circle shape MUST have radius > 0
- System validates on creation
- Error: "ValidationError: Radius required for circle"
- Related Rules: BR-GEO-002

**BR-GEO-002: Polygon Minimum Vertices**
- Polygon shape MUST have >= 3 coordinates
- Less than 3 points cannot form a polygon
- Error: "ValidationError: Polygon needs 3+ coordinates"
- Example: 2 coordinates fails

**BR-GEO-003: Geofence Name Constraints**
- Name MUST be 1-200 characters
- Empty names not allowed
- Error: "ValidationError: Name required"

**BR-GEO-004: Dwell Time Minimum**
- Dwell time MUST be >= 60 seconds if enabled
- Prevents false triggers from brief visits
- Error: "ValidationError: Dwell time min 60 seconds"

**BR-GEO-005: Geofence Ownership**
- User can ONLY modify their own geofences
- System verifies ownership on update/delete
- Error: "AccessDenied: Geofence not owned by user"
- Related Rules: BR-AUTH-002

**BR-GEO-006: Active Geofence for Triggers**
- Only ACTIVE geofences generate trigger events
- Deactivated geofences are ignored during checks
- Related Rules: BR-GEO-007

**BR-GEO-007: Toggle Activation**
- Geofences can be activated/deactivated without deletion
- Preserves configuration for temporary disable
- Related Rules: BR-GEO-006

**BR-GEO-008: Search Radius Maximum**
- Nearby search radius MUST NOT exceed 50,000 meters (50km)
- Prevents excessive database load
- Error: "ValidationError: Radius exceeds maximum"

**BR-GEO-009: Description Length**
- Description MUST NOT exceed 1000 characters
- Error: "ValidationError: Description too long"

**BR-GEO-010: Center Coordinates Required**
- All geofences MUST have center_lat and center_lon
- Even polygons need a center point for queries
- Error: "ValidationError: Center coordinates required"

### Place Rules (BR-PLC-001 to BR-PLC-005)

**BR-PLC-001: Place Name Required**
- Name MUST be 1-200 characters
- Empty names not allowed
- Error: "ValidationError: Place name required"

**BR-PLC-002: Recognition Radius Range**
- Radius MUST be 0-1000 meters (default 100)
- Controls "at this place" detection sensitivity
- Error: "ValidationError: Radius out of range"

**BR-PLC-003: Valid Place Category**
- Category MUST be one of: home, work, school, favorite, custom
- Invalid category rejected
- Error: "ValidationError: Invalid place category"

**BR-PLC-004: Place Ownership**
- User can ONLY access/modify their own places
- System verifies ownership on all operations
- Error: "AccessDenied: Place not owned by user"

**BR-PLC-005: Coordinate Validation**
- Place latitude/longitude follow same rules as locations
- Same coordinate range validation applies
- Related Rules: BR-LOC-001

### Authorization Rules (BR-AUTH-001 to BR-AUTH-005)

**BR-AUTH-001: User Device Access**
- User can ONLY query locations for their own devices
- Device ownership verified via device_service or user_id match
- Error: "AccessDenied: Device not owned by user"

**BR-AUTH-002: Geofence Modification Rights**
- Only geofence owner can update/delete geofence
- Organization admins may have elevated access (future)
- Error: "AccessDenied: Geofence not owned by user"

**BR-AUTH-003: Place Modification Rights**
- Only place owner can update/delete place
- Places are private by default
- Error: "AccessDenied: Place not owned by user"

**BR-AUTH-004: Statistics Access**
- User can ONLY view their own statistics
- System verifies user_id match
- Error: "AccessDenied: Statistics not accessible"

**BR-AUTH-005: Internal Service Calls**
- X-Internal-Call header bypasses authentication
- Used for service-to-service communication
- Related: API Gateway validation

### Data Cleanup Rules (BR-CLN-001 to BR-CLN-003)

**BR-CLN-001: Device Deletion Cascade**
- When device deleted, ALL related data MUST be removed:
  - Location history
  - Geofences targeting device
  - Route recordings
- Processing: Async via event subscription

**BR-CLN-002: User Deletion Cascade**
- When user deleted, ALL related data MUST be removed:
  - All locations for all user's devices
  - All geofences owned by user
  - All places owned by user
- Processing: Async via event subscription

**BR-CLN-003: Cleanup Idempotency**
- Cleanup handlers MUST be idempotent
- Re-processing same event should not cause errors
- Already-deleted data returns success

---

## Summary

| Metric | Count |
|--------|-------|
| Primary Entities | 4 (Location, Geofence, Place, Route) |
| Domain Scenarios | 8 |
| Published Events | 6 |
| Subscribed Events | 2 |
| Business Rules | 33 |
| Core Concepts | 6 |
