# Location Service - Logic Contract

## Overview

This document defines the business logic rules, state machines, edge cases, and integration contracts for the Location Service. It serves as the authoritative reference for implementation and testing.

**Service Identity:**
- **Port**: 8224
- **Schema**: `location`
- **Version**: 1.0.0

---

## Business Rules

### Location Rules (BR-LOC-001 to BR-LOC-012)

**BR-LOC-001: Coordinate Range Validation**
- **Given**: Device reports location
- **When**: Latitude or longitude provided
- **Then**:
  - Latitude MUST be between -90 and 90 (inclusive)
  - Longitude MUST be between -180 and 180 (inclusive)
- **Validation**: On every location report
- **Error**: ValidationError("Invalid coordinates: latitude must be -90 to 90, longitude must be -180 to 180")
- **Example**:
  - Valid: `latitude=37.7749, longitude=-122.4194`
  - Invalid: `latitude=91.0` (exceeds max)
  - Invalid: `longitude=-181.0` (below min)

**BR-LOC-002: Accuracy Requirement**
- **Given**: Device reports location
- **When**: Accuracy field provided
- **Then**: Accuracy MUST be a positive number (> 0)
- **Validation**: On create
- **Error**: ValidationError("Accuracy must be positive")
- **Example**:
  - Valid: `accuracy=10.5`
  - Invalid: `accuracy=0` (zero not allowed)
  - Invalid: `accuracy=-5` (negative not allowed)

**BR-LOC-003: Heading Range Validation**
- **Given**: Device reports location with heading
- **When**: Heading field provided
- **Then**: Heading MUST be >= 0 and < 360 degrees
- **Note**: 0 = North, 90 = East, 180 = South, 270 = West
- **Error**: ValidationError("Heading must be 0-360")
- **Example**:
  - Valid: `heading=180.0` (South)
  - Invalid: `heading=360.0` (must be < 360)
  - Invalid: `heading=-10.0` (negative not allowed)

**BR-LOC-004: Speed Non-Negative**
- **Given**: Device reports location with speed
- **When**: Speed field provided
- **Then**: Speed MUST be >= 0 (m/s)
- **Note**: Negative speed indicates calculation error
- **Error**: ValidationError("Speed cannot be negative")
- **Example**:
  - Valid: `speed=0` (stationary)
  - Valid: `speed=30.5` (moving)
  - Invalid: `speed=-5.0` (negative)

**BR-LOC-005: Device Ownership for Location Access**
- **Given**: User requests device location data
- **When**: Querying any location endpoint
- **Then**: User MUST own the device OR be organization admin
- **Check**: `device.user_id == request.user_id` OR `user.role >= ADMIN`
- **Error**: AccessDeniedError("Device not owned by user")
- **Audit**: Log unauthorized access attempts

**BR-LOC-006: Timestamp Handling**
- **Given**: Device reports location
- **When**: Timestamp field provided or omitted
- **Then**:
  - If omitted: Use current server UTC time
  - If provided: MUST not be in future (> now + 1 minute tolerance)
- **Error**: ValidationError("Timestamp cannot be in future")
- **Note**: 1-minute tolerance for clock drift

**BR-LOC-007: Batch Size Limit**
- **Given**: Device uploads batch of locations
- **When**: Batch request received
- **Then**: Batch MUST contain 1-1000 locations
- **Error**: ValidationError("Batch must contain 1-1000 locations")
- **Reason**: Memory protection and processing limits

**BR-LOC-008: Device ID Required**
- **Given**: Location report received
- **When**: Processing location data
- **Then**:
  - device_id MUST be present
  - device_id MUST be 1-100 characters
  - device_id MUST NOT be empty or whitespace-only
- **Error**: ValidationError("device_id required")

**BR-LOC-009: Location History Pagination**
- **Given**: User requests location history
- **When**: Pagination parameters provided
- **Then**:
  - Limit MUST be 1-1000 (default 100)
  - Offset MUST be >= 0
- **Error**: ValidationError("Invalid pagination parameters")
- **Default**: `limit=100, offset=0`

**BR-LOC-010: Time Window for Search**
- **Given**: User performs nearby device search
- **When**: time_window_minutes parameter provided
- **Then**: Time window MUST be 1-1440 minutes (24 hours max)
- **Default**: 30 minutes
- **Error**: ValidationError("Time window must be 1-1440 minutes")

**BR-LOC-011: Battery Level Range**
- **Given**: Device reports location with battery level
- **When**: Battery level field provided
- **Then**: Battery level MUST be 0-100 (percentage)
- **Error**: ValidationError("Battery level must be 0-100")
- **Example**:
  - Valid: `battery_level=85.5`
  - Invalid: `battery_level=150.0`
  - Invalid: `battery_level=-10.0`

**BR-LOC-012: Location Method Validation**
- **Given**: Device reports location method
- **When**: Location method field provided
- **Then**: Method MUST be one of: gps, wifi, cellular, bluetooth, manual, hybrid
- **Default**: `gps`
- **Error**: ValidationError("Invalid location method")

---

### Geofence Rules (BR-GEO-001 to BR-GEO-015)

**BR-GEO-001: Circle Geofence Requires Radius**
- **Given**: User creates circle geofence
- **When**: shape_type = 'circle'
- **Then**: radius MUST be provided and > 0
- **Error**: ValidationError("Radius required for circle geofence")
- **Example**:
  - Valid: `shape_type=circle, radius=500`
  - Invalid: `shape_type=circle, radius=null`
  - Invalid: `shape_type=circle, radius=0`

**BR-GEO-002: Polygon Minimum Vertices**
- **Given**: User creates polygon geofence
- **When**: shape_type = 'polygon'
- **Then**: polygon_coordinates MUST have >= 3 points
- **Error**: ValidationError("Polygon requires at least 3 coordinates")
- **Example**:
  - Valid: 4 coordinates forming a rectangle
  - Invalid: 2 coordinates (line, not polygon)

**BR-GEO-003: Geofence Name Constraints**
- **Given**: User creates or updates geofence
- **When**: Name field provided
- **Then**:
  - Name MUST be 1-200 characters
  - Name MUST NOT be empty or whitespace-only
- **Error**: ValidationError("Name must be 1-200 characters")

**BR-GEO-004: Dwell Time Minimum**
- **Given**: User creates geofence with dwell trigger
- **When**: trigger_on_dwell = true
- **Then**: dwell_time_seconds MUST be >= 60 seconds
- **Reason**: Prevents false triggers from brief visits
- **Error**: ValidationError("Dwell time must be at least 60 seconds")

**BR-GEO-005: Geofence Ownership**
- **Given**: User modifies geofence
- **When**: Update or delete operation requested
- **Then**: User MUST be geofence owner
- **Check**: `geofence.user_id == request.user_id`
- **Error**: AccessDeniedError("Geofence not owned by user")

**BR-GEO-006: Active Geofence for Triggers**
- **Given**: Device location reported
- **When**: Checking geofence triggers
- **Then**: Only geofences with `active = true` generate trigger events
- **Note**: Deactivated geofences silently ignored
- **Related**: BR-GEO-007

**BR-GEO-007: Toggle Activation**
- **Given**: User activates/deactivates geofence
- **When**: Activation toggle requested
- **Then**: Geofence active status toggled without deletion
- **Benefit**: Preserves configuration for temporary disable
- **Event**: None (status change, not state change)

**BR-GEO-008: Search Radius Maximum**
- **Given**: User performs nearby search
- **When**: radius_meters parameter provided
- **Then**: Radius MUST NOT exceed 50,000 meters (50km)
- **Reason**: Performance and resource protection
- **Error**: ValidationError("Search radius cannot exceed 50km")

**BR-GEO-009: Description Length**
- **Given**: User creates/updates geofence
- **When**: Description field provided
- **Then**: Description MUST NOT exceed 1000 characters
- **Error**: ValidationError("Description cannot exceed 1000 characters")

**BR-GEO-010: Center Coordinates Required**
- **Given**: User creates any geofence
- **When**: Creating circle, polygon, or rectangle
- **Then**: center_lat and center_lon MUST be provided
- **Reason**: Used for spatial queries and UI centering
- **Error**: ValidationError("Center coordinates required")

**BR-GEO-011: Geofence Event Recording**
- **Given**: Geofence triggered (enter/exit/dwell)
- **When**: Device crosses geofence boundary
- **Then**:
  - Create geofence_event record
  - Update geofence total_triggers count
  - Update geofence last_triggered timestamp
- **Event**: `geofence.entered` or `geofence.exited`

**BR-GEO-012: Target Device Filtering**
- **Given**: Geofence has target_devices specified
- **When**: Checking if location triggers geofence
- **Then**:
  - If target_devices is empty: Apply to ALL devices
  - If target_devices has values: Only apply to listed devices
- **Query**: Check `device_id IN target_devices OR target_devices = '[]'`

**BR-GEO-013: Time Schedule Restriction**
- **Given**: Geofence has active_hours/active_days configured
- **When**: Device crosses geofence boundary
- **Then**: Only trigger if current time within schedule
- **Check**:
  - Current day IN active_days
  - Current time BETWEEN active_hours.start AND active_hours.end
- **Note**: Timezone handling uses user's timezone preference

**BR-GEO-014: Geofence Spatial Index Usage**
- **Given**: Location update triggers geofence check
- **When**: Querying potentially triggered geofences
- **Then**: Use PostGIS GIST index for efficient spatial query
- **Query**: `ST_DWithin(geom, point, tolerance)` uses spatial index
- **Performance**: < 50ms for geofence check

**BR-GEO-015: Enter vs Exit Detection**
- **Given**: Device position changes
- **When**: Comparing previous and current position vs geofence
- **Then**:
  - ENTER: Previous outside, current inside
  - EXIT: Previous inside, current outside
  - DWELL: Inside for >= dwell_time_seconds
- **Tracking**: Store last known geofence state per device

---

### Place Rules (BR-PLC-001 to BR-PLC-008)

**BR-PLC-001: Place Name Required**
- **Given**: User creates place
- **When**: Name field provided
- **Then**:
  - Name MUST be 1-200 characters
  - Name MUST NOT be empty or whitespace-only
- **Error**: ValidationError("Place name required")

**BR-PLC-002: Recognition Radius Range**
- **Given**: User creates/updates place
- **When**: Radius field provided
- **Then**: Radius MUST be 0-1000 meters (default 100)
- **Use**: Controls "at this place" detection sensitivity
- **Error**: ValidationError("Radius must be 0-1000 meters")

**BR-PLC-003: Valid Place Category**
- **Given**: User creates/updates place
- **When**: Category field provided
- **Then**: Category MUST be one of: home, work, school, favorite, custom
- **Error**: ValidationError("Invalid place category")

**BR-PLC-004: Place Ownership**
- **Given**: User accesses place
- **When**: Any place operation (read, update, delete)
- **Then**: User MUST be place owner
- **Check**: `place.user_id == request.user_id`
- **Error**: AccessDeniedError("Place not owned by user")

**BR-PLC-005: Place Coordinate Validation**
- **Given**: User creates/updates place
- **When**: Coordinates provided
- **Then**: Same coordinate range validation as locations (BR-LOC-001)
- **Error**: ValidationError("Invalid place coordinates")

**BR-PLC-006: Unique Place Name Per User**
- **Given**: User creates place
- **When**: Name provided
- **Then**: Name MUST be unique within user's places (case-insensitive)
- **Error**: DuplicateError("Place with this name already exists")
- **Index**: `UNIQUE(user_id, LOWER(name))`

**BR-PLC-007: Place Visit Statistics**
- **Given**: Device detected at place location
- **When**: Within recognition radius
- **Then**:
  - Increment visit_count
  - Add duration to total_time_spent
  - Update last_visit timestamp
- **Trigger**: Automatic via location updates

**BR-PLC-008: Place Icon and Color**
- **Given**: User creates/updates place
- **When**: Icon or color field provided
- **Then**:
  - Icon MUST be max 50 characters
  - Color MUST be max 20 characters
- **Use**: UI customization
- **Default**: Based on category if not specified

---

### Authorization Rules (BR-AUTH-001 to BR-AUTH-006)

**BR-AUTH-001: User Device Access**
- **Given**: User requests location data
- **When**: Any device-specific query
- **Then**: User can ONLY query locations for their own devices
- **Verification**: Call device_service to verify ownership OR check user_id match
- **Error**: AccessDeniedError("Device not owned by user")

**BR-AUTH-002: Geofence Modification Rights**
- **Given**: User attempts to modify geofence
- **When**: Update or delete operation
- **Then**: Only geofence owner can modify
- **Future**: Organization admins may have elevated access
- **Error**: AccessDeniedError("Geofence not owned by user")

**BR-AUTH-003: Place Modification Rights**
- **Given**: User attempts to modify place
- **When**: Update or delete operation
- **Then**: Only place owner can modify
- **Note**: Places are private by default
- **Error**: AccessDeniedError("Place not owned by user")

**BR-AUTH-004: Statistics Access**
- **Given**: User requests statistics
- **When**: Any statistics endpoint
- **Then**: User can ONLY view their own statistics
- **Check**: `stats.user_id == request.user_id`
- **Error**: AccessDeniedError("Statistics not accessible")

**BR-AUTH-005: Internal Service Calls**
- **Given**: Service-to-service call detected
- **When**: `X-Internal-Call: true` header present
- **Then**: Bypass user authentication
- **Use**: For event handlers, background jobs
- **Security**: Only accept from trusted internal network

**BR-AUTH-006: JWT Token Validation**
- **Given**: External API request received
- **When**: Authorization header present
- **Then**: Validate JWT via auth_service
- **Expiry**: 24 hours default
- **Error**: AuthenticationError("Invalid or expired token")

---

### Data Cleanup Rules (BR-CLN-001 to BR-CLN-005)

**BR-CLN-001: Device Deletion Cascade**
- **Given**: `device.deleted` event received
- **When**: Device is deleted from device_service
- **Then**: Delete ALL related data:
  - All location records for device
  - Remove device from geofence target_devices
  - All route recordings for device
- **Processing**: Async via NATS event subscription
- **Event**: `*.device.deleted`

**BR-CLN-002: User Deletion Cascade**
- **Given**: `user.deleted` event received
- **When**: User is deleted from account_service
- **Then**: Delete ALL related data:
  - All locations for all user's devices
  - All geofences owned by user
  - All places owned by user
  - All routes owned by user
- **Processing**: Async via NATS event subscription
- **Event**: `*.user.deleted`

**BR-CLN-003: Cleanup Idempotency**
- **Given**: Cleanup event received
- **When**: Processing deletion
- **Then**: Handler MUST be idempotent
  - Re-processing same event should not cause errors
  - Already-deleted data returns success
  - Use event_id tracking for deduplication
- **Implementation**: Check if data exists before delete

**BR-CLN-004: Data Retention Policy**
- **Given**: Location data stored
- **When**: Data age exceeds retention period
- **Then**: Automatically delete old locations
- **Default**: 90 days retention
- **Config**: `LOCATION_RETENTION_DAYS` environment variable
- **Schedule**: Daily cleanup job at 3 AM UTC

**BR-CLN-005: Audit Log Preservation**
- **Given**: Location data deleted
- **When**: Any deletion operation
- **Then**: Preserve audit log entries for compliance
- **Retention**: Audit logs retained for 7 years (separate from location data)
- **GDPR**: Anonymize rather than delete for compliance

---

### Event Rules (BR-EVT-001 to BR-EVT-006)

**BR-EVT-001: Event Publishing on Location Update**
- **Given**: Location successfully stored
- **When**: Database transaction commits
- **Then**: Publish `location.updated` event
- **Timing**: After commit, before response
- **Payload**: location_id, device_id, user_id, coordinates, timestamp

**BR-EVT-002: Event Publishing on Geofence Trigger**
- **Given**: Device crosses geofence boundary
- **When**: Enter or exit detected
- **Then**:
  - Publish `geofence.entered` or `geofence.exited`
  - Include geofence_id, device_id, coordinates
- **Consumers**: notification_service, automation_service

**BR-EVT-003: Event Publishing on Geofence CRUD**
- **Given**: Geofence created or deleted
- **When**: Database operation completes
- **Then**:
  - Create: Publish `geofence.created`
  - Delete: Publish `geofence.deleted`
- **Consumers**: notification_service

**BR-EVT-004: Event Publishing on Place Created**
- **Given**: Place successfully created
- **When**: Database transaction commits
- **Then**: Publish `place.created` event
- **Consumers**: calendar_service, notification_service

**BR-EVT-005: Event Idempotency**
- **Given**: Event handler receives event
- **When**: Same event_id processed before
- **Then**: Handler MUST skip processing
- **Implementation**: Store processed event_ids with TTL

**BR-EVT-006: Event Retry Policy**
- **Given**: Event publish fails
- **When**: NATS unavailable or error
- **Then**:
  - Retry 3 times with exponential backoff (1s, 2s, 4s)
  - Log failure after max retries
  - Store for later retry via background job
- **Guarantee**: At-least-once delivery

---

## State Machines

### 1. Geofence Lifecycle State Machine

```
                    ┌─────────────────┐
                    │     CREATED     │
                    │  (active=true)  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
    ┌─────────────────┐  deactivate()  ┌─────────────────┐
    │  MONITORING     │◄──────────────►│   DEACTIVATED   │
    │  (active=true)  │   activate()   │  (active=false) │
    └────────┬────────┘                └────────┬────────┘
             │                                  │
             │ delete()                         │ delete()
             │                                  │
             ▼                                  ▼
    ┌─────────────────────────────────────────────────────┐
    │                      DELETED                        │
    │               (record removed)                      │
    └─────────────────────────────────────────────────────┘
```

**States:**

| State | Description | active Field | Allowed Operations |
|-------|-------------|--------------|-------------------|
| CREATED | Newly created geofence | true | update, deactivate, delete |
| MONITORING | Actively checking for triggers | true | update, deactivate, delete |
| DEACTIVATED | Temporarily disabled | false | update, activate, delete |
| DELETED | Permanently removed | N/A | none |

**Transitions:**

| From | To | Trigger | Conditions | Event |
|------|-----|---------|------------|-------|
| CREATED | MONITORING | First location check | None | None |
| MONITORING | DEACTIVATED | deactivate() | Owner only | None |
| DEACTIVATED | MONITORING | activate() | Owner only | None |
| MONITORING | DELETED | delete() | Owner only | `geofence.deleted` |
| DEACTIVATED | DELETED | delete() | Owner only | `geofence.deleted` |

**Invariants:**
1. DELETED is terminal - no transitions out
2. Only owner can perform state transitions
3. Geofence updates allowed in any non-deleted state
4. Trigger detection only occurs in MONITORING state

---

### 2. Location Processing State Machine

```
┌─────────────────┐
│    RECEIVED     │
│  (API request)  │
└────────┬────────┘
         │ validate()
         ▼
┌─────────────────┐     ┌─────────────────┐
│   VALIDATED     │     │    REJECTED     │
│  (data valid)   │     │  (invalid data) │
└────────┬────────┘     └─────────────────┘
         │ store()              ▲
         ▼                      │ validation_failed
┌─────────────────┐             │
│     STORED      │─────────────┘
│  (in database)  │
└────────┬────────┘
         │ check_geofences()
         ▼
┌─────────────────┐     ┌─────────────────┐
│  GEOFENCE_CHECK │────►│ TRIGGERS_FOUND  │
│  (checking...)  │     │  (events ready) │
└────────┬────────┘     └────────┬────────┘
         │ no triggers           │ publish_events()
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│    COMPLETED    │◄────│ EVENTS_PUBLISHED│
│   (success)     │     │                 │
└─────────────────┘     └─────────────────┘
```

**States:**

| State | Description | Next State |
|-------|-------------|------------|
| RECEIVED | API request received | VALIDATED or REJECTED |
| VALIDATED | Passed all validation | STORED |
| REJECTED | Failed validation | Terminal |
| STORED | Written to database | GEOFENCE_CHECK |
| GEOFENCE_CHECK | Checking geofence triggers | TRIGGERS_FOUND or COMPLETED |
| TRIGGERS_FOUND | Geofences triggered | EVENTS_PUBLISHED |
| EVENTS_PUBLISHED | Events sent to NATS | COMPLETED |
| COMPLETED | Processing finished | Terminal |

**Processing Steps:**
1. Validate coordinates, accuracy, device_id
2. Store location with PostGIS geometry
3. Query active geofences for device
4. Check point-in-polygon for each geofence
5. Compare with previous state for enter/exit
6. Publish events for triggered geofences
7. Return success response

---

### 3. Route Recording State Machine

```
┌─────────────────┐
│    NOT_STARTED  │
└────────┬────────┘
         │ start_route()
         ▼
┌─────────────────┐     ┌─────────────────┐
│     ACTIVE      │────►│     PAUSED      │
│  (recording)    │     │  (suspended)    │
└────────┬────────┘     └────────┬────────┘
    │    ▲                  │    │
    │    │ resume()         │    │ resume()
    │    └──────────────────┘    │
    │                            │
    │ complete()                 │ complete()
    ▼                            ▼
┌─────────────────┐     ┌─────────────────┐
│   COMPLETED     │     │   CANCELLED     │
│  (finished)     │     │  (aborted)      │
└─────────────────┘     └─────────────────┘
```

**States:**

| State | Description | Waypoint Recording |
|-------|-------------|-------------------|
| NOT_STARTED | Route not yet begun | No |
| ACTIVE | Recording in progress | Yes |
| PAUSED | Recording suspended | No |
| COMPLETED | Route finished successfully | No |
| CANCELLED | Route aborted | No |

**Transitions:**

| From | To | Trigger | Conditions |
|------|-----|---------|------------|
| NOT_STARTED | ACTIVE | start_route() | Device connected |
| ACTIVE | PAUSED | pause() | User request |
| ACTIVE | COMPLETED | complete() | User request |
| ACTIVE | CANCELLED | cancel() | User request or timeout |
| PAUSED | ACTIVE | resume() | User request |
| PAUSED | COMPLETED | complete() | User request |
| PAUSED | CANCELLED | cancel() | User request or timeout |

**Waypoint Recording:**
- Only record waypoints when state = ACTIVE
- Calculate running statistics (distance, duration, speed)
- Update route geometry (LineString)

---

### 4. Geofence Device Tracking State Machine

```
                    ┌─────────────────┐
                    │     UNKNOWN     │
                    │  (no history)   │
                    └────────┬────────┘
                             │ first_location()
                             ▼
         ┌───────────────────────────────────────┐
         │                                       │
         ▼                                       ▼
┌─────────────────┐                    ┌─────────────────┐
│     OUTSIDE     │                    │     INSIDE      │
│  (not in zone)  │                    │   (in zone)     │
└────────┬────────┘                    └────────┬────────┘
         │                                      │
         │ location_inside()                    │ location_outside()
         │                                      │
         │         ┌────────────────┐           │
         └────────►│    ENTERING    │◄──────────┘
                   │ (crossing in)  │
                   └────────┬───────┘
                            │ confirmed
                            ▼
                   ┌────────────────┐
                   │     INSIDE     │────────┐
                   │   (in zone)    │        │ dwell_time_reached
                   └────────┬───────┘        ▼
                            │       ┌────────────────┐
                            │       │    DWELLING    │
                            │       │ (stayed long)  │
                            │       └────────┬───────┘
                            │                │ location_outside()
                            ▼                ▼
                   ┌────────────────────────────────┐
                   │            EXITING            │
                   │        (crossing out)         │
                   └────────────────┬──────────────┘
                                    │ confirmed
                                    ▼
                            ┌────────────────┐
                            │    OUTSIDE     │
                            │  (not in zone) │
                            └────────────────┘
```

**Per-Device-Per-Geofence State:**

| State | Description | Trigger Event |
|-------|-------------|---------------|
| UNKNOWN | No location history for this device/geofence | None |
| OUTSIDE | Device is outside geofence | None |
| INSIDE | Device is inside geofence | `geofence.entered` |
| DWELLING | Device inside for >= dwell_time | `geofence.dwell` |
| EXITING | Device leaving geofence | `geofence.exited` |

**Tracking Storage:**
- Key: `geofence:{geofence_id}:device:{device_id}:state`
- Value: `{state, entered_at, last_location_at}`
- TTL: 24 hours (reset on each location)

---

## Edge Cases

### Input Validation Edge Cases

**EC-001: Empty String vs Null for Device ID**
- **Input**: `device_id = ""` vs `device_id = null`
- **Expected Behavior**:
  - Empty string: ValidationError("device_id cannot be empty")
  - Null: ValidationError("device_id is required")
- **Implementation**: Pydantic validators with separate checks

**EC-002: Whitespace-Only Input**
- **Input**: `name = "   "` (only spaces/tabs)
- **Expected Behavior**: ValidationError("name cannot be whitespace only")
- **Implementation**: Strip whitespace, then check length > 0
- **Affected Fields**: device_id, name, description

**EC-003: Maximum Length Boundary**
- **Input**: `name = "x" * 200` (exactly max)
- **Expected Behavior**: Accept (200 chars allowed)
- **Input**: `name = "x" * 201` (max + 1)
- **Expected Behavior**: ValidationError("name max 200 characters")
- **Test**: Both boundary and boundary+1

**EC-004: Unicode Characters in Names**
- **Input**: `name = "Test 中文 \u4e2d\u6587"`
- **Expected Behavior**: Accept (valid UTF-8)
- **Note**: Count characters, not bytes
- **Database**: UTF-8 encoding required

**EC-005: Special Characters in Names**
- **Input**: `name = "Test!@#$%^&*()"`
- **Expected Behavior**: Accept (no character restrictions)
- **SQL Injection**: Prevented by parameterized queries

---

### Coordinate Edge Cases

**EC-006: Boundary Coordinates**
- **Input**: `latitude = -90.0` (South Pole)
- **Expected Behavior**: Accept (valid boundary)
- **Input**: `latitude = 90.0` (North Pole)
- **Expected Behavior**: Accept (valid boundary)
- **Input**: `longitude = -180.0` or `180.0` (Date Line)
- **Expected Behavior**: Accept (valid boundary)

**EC-007: Zero Coordinates**
- **Input**: `latitude = 0.0, longitude = 0.0` (Gulf of Guinea)
- **Expected Behavior**: Accept (valid real location)
- **Note**: Not a null island, actual coordinates

**EC-008: High Precision Coordinates**
- **Input**: `latitude = 37.77493812345678`
- **Expected Behavior**: Accept, store with database precision
- **Storage**: DOUBLE PRECISION in PostgreSQL
- **Rounding**: Apply 6 decimal places for display

---

### Geofence Edge Cases

**EC-009: Circle with Minimum Radius**
- **Input**: `radius = 0.001` (1 millimeter)
- **Expected Behavior**: Accept if > 0
- **Note**: Practical minimum for usability is ~10 meters
- **Recommendation**: UI may enforce minimum

**EC-010: Polygon Self-Intersection**
- **Input**: Polygon coordinates that create figure-8
- **Expected Behavior**: Accept (PostGIS handles complex polygons)
- **Note**: Self-intersecting polygons may cause unexpected trigger behavior
- **Validation**: Consider adding ST_IsValid check

**EC-011: Polygon with Duplicate Points**
- **Input**: Same coordinate repeated in polygon
- **Expected Behavior**: Accept (PostGIS normalizes)
- **Note**: First and last point same is valid (closed polygon)

**EC-012: Geofence at Poles**
- **Input**: Geofence centered at latitude 90.0
- **Expected Behavior**: Accept
- **Limitation**: Geofence crossing 180/-180 longitude may behave unexpectedly
- **Recommendation**: Use separate geofences for polar regions

---

### Concurrency Edge Cases

**EC-013: Concurrent Location Updates**
- **Input**: Two simultaneous locations for same device
- **Expected Behavior**: Both stored, ordered by timestamp
- **Implementation**: No locking, append-only design
- **Query**: ORDER BY timestamp DESC for latest

**EC-014: Geofence Update During Location Check**
- **Input**: Geofence updated while checking triggers
- **Expected Behavior**: Use geofence state at check start
- **Implementation**: Read geofence data once, process
- **Consistency**: Eventual consistency acceptable

**EC-015: Batch Upload with Partial Failures**
- **Input**: 100 locations, 5 with invalid coordinates
- **Expected Behavior**:
  - Process all valid locations
  - Return summary with success_count and failure_count
  - Include details of failed locations
- **Response**: `{success_count: 95, failure_count: 5, failures: [...]}`

---

## Data Consistency Rules

**DC-001: Coordinate Normalization**
- All coordinates stored as DOUBLE PRECISION
- Latitude range: -90 to 90 (inclusive)
- Longitude range: -180 to 180 (inclusive)
- PostGIS SRID: 4326 (WGS84)
- Applied: Before storage, in SQL layer

**DC-002: Timestamp Consistency**
- All timestamps stored as TIMESTAMP WITH TIME ZONE
- Internal storage: UTC
- Display: Convert to user's timezone
- Format: ISO 8601 with timezone offset
- Fields: created_at, updated_at, timestamp, last_triggered

**DC-003: ID Format Consistency**
- Location ID: `loc_<uuid_hex>` (e.g., `loc_a1b2c3d4e5f6...`)
- Geofence ID: `geo_<uuid_hex>`
- Place ID: `plc_<uuid_hex>`
- Route ID: `route_<uuid_hex>`
- Device ID: `dev_<uuid_hex[:12]>`
- User ID: `usr_<uuid_hex[:12]>`
- Generated: Server-side only, immutable after creation

**DC-004: PostGIS Geometry Consistency**
- Point geometry: `ST_SetSRID(ST_Point(longitude, latitude), 4326)`
- Note: PostGIS uses (lon, lat) order, opposite of typical (lat, lon)
- Index: GIST spatial index on geometry columns
- Validation: All geometries must be valid (ST_IsValid)

**DC-005: Soft Delete Consistency**
- Geofences and places are hard-deleted (no soft delete)
- Locations are hard-deleted after retention period
- Geofence events preserved for historical queries
- Audit logs preserved separately

**DC-006: Cascade Delete Consistency**
- Device deleted → Delete all device's locations
- Device deleted → Remove from geofence target_devices (array update)
- User deleted → Delete all geofences, places, locations
- Geofence deleted → Delete all geofence_events

**DC-007: Statistics Counter Consistency**
- total_triggers: INCREMENT on geofence trigger
- visit_count: INCREMENT on place visit
- total_time_spent: ADD duration on place exit
- Implementation: Atomic database operations
- Reset: Only on explicit user action

---

## Integration Contracts

### Account Service Integration

**Purpose**: Validate user exists, get user timezone

**Endpoint**: `GET /api/v1/accounts/{account_id}`

**Request**:
```http
GET http://localhost:8202/api/v1/accounts/usr_abc123
X-Internal-Call: true
```

**Success Response** (200):
```json
{
  "account_id": "usr_abc123",
  "email": "user@example.com",
  "status": "active",
  "timezone": "America/Los_Angeles"
}
```

**Error Handling**:
| Status | Action |
|--------|--------|
| 200 | Continue with user data |
| 404 | Reject operation (user not found) |
| 500 | Retry 3x, then 503 |
| Timeout | Retry 3x, then 503 |

---

### Device Service Integration

**Purpose**: Verify device ownership, get device info

**Endpoint**: `GET /api/v1/devices/{device_id}`

**Request**:
```http
GET http://localhost:8220/api/v1/devices/dev_xyz789
X-Internal-Call: true
```

**Success Response** (200):
```json
{
  "device_id": "dev_xyz789",
  "user_id": "usr_abc123",
  "device_name": "iPhone 15",
  "device_type": "phone",
  "status": "active"
}
```

**Ownership Check**:
```python
def verify_device_ownership(device_id: str, user_id: str) -> bool:
    device = device_client.get_device(device_id)
    return device and device.user_id == user_id
```

**Error Handling**:
| Status | Action |
|--------|--------|
| 200 | Continue, verify user_id match |
| 404 | AccessDeniedError("Device not found") |
| 500 | Retry 3x, then ServiceUnavailableError |

---

### Notification Service Integration

**Purpose**: Send geofence trigger notifications

**Endpoint**: `POST /api/v1/notifications`

**Request**:
```http
POST http://localhost:8206/api/v1/notifications
Content-Type: application/json
X-Internal-Call: true

{
  "user_id": "usr_abc123",
  "notification_type": "geofence_alert",
  "title": "Geofence Entered",
  "body": "Device entered 'Home Zone'",
  "data": {
    "geofence_id": "geo_abc123",
    "device_id": "dev_xyz789",
    "event_type": "enter"
  },
  "channels": ["push", "email"]
}
```

**Success Response** (201):
```json
{
  "notification_id": "ntf_abc123",
  "status": "sent",
  "channels_sent": ["push"]
}
```

**Error Handling**:
| Status | Action |
|--------|--------|
| 201 | Log success |
| 4xx | Log warning, continue (non-critical) |
| 5xx | Retry 3x, log error, continue |

---

### Event Publishing Contract

**Subject Pattern**: `location.<entity>.<action>`

**Published Events**:

| Event | Subject | Trigger |
|-------|---------|---------|
| LocationUpdated | `location.updated` | After location stored |
| GeofenceEntered | `location.geofence.entered` | Device enters geofence |
| GeofenceExited | `location.geofence.exited` | Device exits geofence |
| GeofenceCreated | `location.geofence.created` | Geofence created |
| GeofenceDeleted | `location.geofence.deleted` | Geofence deleted |
| PlaceCreated | `location.place.created` | Place created |

**Payload Schema (LocationUpdated)**:
```json
{
  "event_id": "evt_abc123",
  "event_type": "location.updated",
  "timestamp": "2025-01-01T12:00:00Z",
  "source_service": "location_service",
  "correlation_id": "corr_xyz789",
  "data": {
    "location_id": "loc_abc123",
    "device_id": "dev_xyz789",
    "user_id": "usr_123",
    "latitude": 37.7749,
    "longitude": -122.4194,
    "accuracy": 10.5,
    "location_method": "gps"
  }
}
```

**Payload Schema (GeofenceEntered/Exited)**:
```json
{
  "event_id": "evt_def456",
  "event_type": "geofence.entered",
  "timestamp": "2025-01-01T12:00:00Z",
  "source_service": "location_service",
  "data": {
    "geofence_id": "geo_abc123",
    "geofence_name": "Home",
    "device_id": "dev_xyz789",
    "user_id": "usr_123",
    "latitude": 37.7749,
    "longitude": -122.4194,
    "triggered_at": "2025-01-01T12:00:00Z"
  }
}
```

**Delivery Guarantees**:
- At-least-once delivery via NATS JetStream
- Per-device ordering guaranteed
- Consumer acknowledgment required
- Retry on failure with exponential backoff

---

### Event Subscription Contract

**Subscribed Events**:

| Event | Source | Subject | Handler |
|-------|--------|---------|---------|
| DeviceDeleted | device_service | `*.device.deleted` | `handle_device_deleted()` |
| UserDeleted | account_service | `*.user.deleted` | `handle_user_deleted()` |

**DeviceDeleted Payload**:
```json
{
  "event_type": "device.deleted",
  "device_id": "dev_xyz789",
  "user_id": "usr_123",
  "timestamp": "2025-01-01T12:00:00Z"
}
```

**Handler Implementation**:
```python
async def handle_device_deleted(event: DeviceDeletedEvent):
    device_id = event.device_id

    # Delete all locations for device
    await location_repository.delete_device_locations(device_id)

    # Remove device from geofence targets
    await geofence_repository.remove_device_from_targets(device_id)

    # Delete device tracking state
    await cache.delete(f"device:{device_id}:*")

    logger.info(f"Cleaned up data for device {device_id}")
```

**Idempotency**: Check if already processed via event_id tracking

---

## Error Handling Contracts

### HTTP Status Code Mapping

| Error Type | HTTP Status | Error Code |
|------------|-------------|------------|
| ValidationError | 422 | VALIDATION_ERROR |
| NotFoundError | 404 | NOT_FOUND |
| DuplicateError | 409 | DUPLICATE |
| AccessDeniedError | 403 | FORBIDDEN |
| AuthenticationError | 401 | UNAUTHORIZED |
| RateLimitError | 429 | RATE_LIMITED |
| ServiceUnavailableError | 503 | SERVICE_UNAVAILABLE |
| InternalError | 500 | INTERNAL_ERROR |

### Error Response Format

```json
{
  "success": false,
  "error": "ValidationError",
  "message": "Invalid coordinates",
  "detail": {
    "field": "latitude",
    "value": 91.0,
    "constraint": "must be between -90 and 90"
  },
  "status_code": 422,
  "request_id": "req_abc123",
  "timestamp": "2025-01-01T12:00:00Z"
}
```

### Validation Error Detail (Pydantic)

```json
{
  "success": false,
  "error": "ValidationError",
  "message": "Validation failed",
  "detail": [
    {
      "loc": ["body", "latitude"],
      "msg": "ensure this value is less than or equal to 90",
      "type": "value_error.number.not_le"
    },
    {
      "loc": ["body", "device_id"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ],
  "status_code": 422
}
```

### Not Found Error

```json
{
  "success": false,
  "error": "NotFoundError",
  "message": "Geofence not found",
  "detail": {
    "resource": "geofence",
    "id": "geo_nonexistent"
  },
  "status_code": 404
}
```

### Access Denied Error

```json
{
  "success": false,
  "error": "AccessDeniedError",
  "message": "Device not owned by user",
  "detail": {
    "device_id": "dev_xyz789",
    "user_id": "usr_123"
  },
  "status_code": 403
}
```

### Service Unavailable Error

```json
{
  "success": false,
  "error": "ServiceUnavailableError",
  "message": "Database connection failed",
  "detail": {
    "dependency": "postgresql",
    "retry_after": 30
  },
  "status_code": 503
}
```

### Rate Limit Error

```json
{
  "success": false,
  "error": "RateLimitError",
  "message": "Too many requests",
  "detail": {
    "limit": 100,
    "window": "minute",
    "retry_after": 45
  },
  "status_code": 429
}
```

---

## Summary

| Section | Count |
|---------|-------|
| Business Rules | 47 |
| State Machines | 4 |
| Edge Cases | 15 |
| Data Consistency Rules | 7 |
| Integration Contracts | 4 |
| Error Types | 8 |
| Total Lines | ~1300 |
