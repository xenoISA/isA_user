# Device Service - Domain Context

## Business Taxonomy

### Core Entities

**Device**
- A physical or virtual IoT device registered in the system
- Has unique identity (device_id), ownership (user_id), and lifecycle status
- Supports 11 device types: sensor, actuator, gateway, smart_home, industrial, medical, automotive, wearable, camera, controller, smart_frame
- Lifecycle: pending → active → inactive/maintenance/error → decommissioned

**Device Group**
- Logical organization of devices for management purposes
- Supports hierarchical grouping (parent_group_id)
- Used for bulk operations and access control
- Contains metadata for custom attributes

**Device Command**
- Instruction sent from service to device via MQTT
- Tracked with command_id, status, and execution timeline
- Supports priority levels (1-10), timeout configuration, acknowledgment requirements
- Status flow: pending → sent → acknowledged → executed/failed/timeout

**Smart Frame**
- Specialized device type for photo display (smart_frame)
- Extended configuration: display mode, slideshow settings, sync schedules
- Integration with album_service and media_service for content
- Supports family sharing via organization_service

**Pairing Token**
- Time-limited token for device-user association
- Generated during device setup (QR code display)
- Verified by auth_service during pairing flow
- Single-use, expires after successful pairing or timeout

### Domain Concepts

**Device Lifecycle**
- **pending**: Initial state after registration, awaiting activation
- **active**: Device is online and operational
- **inactive**: Device is offline but not in error state
- **maintenance**: Device undergoing planned maintenance
- **error**: Device in failure state requiring attention
- **decommissioned**: Device permanently disabled (soft delete)

**Connectivity Types**
- Physical: wifi, ethernet, bluetooth, zigbee
- Cellular: 4g, 5g, nb-iot
- Protocol: mqtt, coap, lora
- Each type has different network requirements and reliability profiles

**Security Levels**
- **none**: No security (legacy devices)
- **basic**: Simple password/key authentication
- **standard**: Encrypted communication, device secret
- **high**: Certificate-based authentication, mutual TLS
- **critical**: Multi-factor authentication, hardware security module

**Device Health**
- Composite score (0-100) from hardware metrics
- Includes: CPU usage, memory usage, disk usage, temperature, battery level, signal strength
- Error/warning counts from telemetry data
- Last check timestamp and diagnostics data

**Command Delivery**
- **MQTT-first**: Primary delivery via MQTT broker
- **Fallback simulation**: If MQTT unavailable, simulate for testing
- **Acknowledgment**: Optional confirmation from device
- **Priority queue**: Commands executed by priority level

**Smart Frame Display Modes**
- photo_slideshow: Rotating photos with transition effects
- video_playback: Video content display
- clock_display: Digital clock with weather
- weather_info: Weather dashboard
- calendar_view: Calendar events display
- off: Screen powered off

## Domain Scenarios

### 1. Device Registration and Activation

**Trigger**: User purchases new IoT device (e.g., smart sensor, smart frame)

**Flow**:
1. User unboxes device, powers on
2. Device broadcasts setup signal (AP mode or BLE)
3. User connects via mobile app, scans device info
4. App calls `POST /api/v1/devices` with registration data
5. Service generates device_id from serial_number + mac_address hash
6. Device saved with status=pending
7. `device.registered` event published

**Outcome**: Device registered in system, awaiting authentication

**Events**:
- `device.registered` (EventType.DEVICE_REGISTERED)

**Business Rules Applied**:
- BR-DEV-001: Unique device ID generation
- BR-DEV-002: Serial number uniqueness
- BR-DEV-005: Default security level assignment

---

### 2. Device Authentication and Online Status

**Trigger**: Device connects to internet and authenticates

**Flow**:
1. Device calls `POST /api/v1/devices/auth` with device_id + device_secret
2. Service verifies credentials with auth_service
3. JWT token generated (24-hour expiry)
4. MQTT broker address and topic returned
5. Device status updated to active
6. last_seen timestamp updated
7. `device.online` event published

**Outcome**: Device authenticated, MQTT connected, status=active

**Events**:
- `device.online` (EventType.DEVICE_ONLINE)

**Business Rules Applied**:
- BR-DEV-008: JWT token expiry (24 hours)
- BR-DEV-011: Status transition pending→active
- BR-DEV-015: Last seen timestamp update

---

### 3. Command Delivery to Device

**Trigger**: User sends command via mobile app (e.g., "display photo", "reboot")

**Flow**:
1. App calls `POST /api/v1/devices/{device_id}/commands` with command data
2. Service validates device exists and is active
3. Command saved to database with status=pending
4. Command sent via MQTT to device topic
5. If MQTT succeeds, status updated to sent
6. `device.command_sent` event published
7. Device acknowledges via MQTT (optional)
8. Device executes command, sends result

**Outcome**: Command delivered, tracked, and executed

**Events**:
- `device.command_sent` (EventType.DEVICE_COMMAND_SENT)

**Business Rules Applied**:
- BR-DEV-020: Command timeout validation
- BR-DEV-021: Priority range (1-10)
- BR-DEV-022: MQTT topic format
- BR-DEV-025: Command status tracking

**Fallback**: If MQTT unavailable, simulation mode for testing

---

### 4. Device Health Monitoring

**Trigger**: Periodic health check request or dashboard refresh

**Flow**:
1. User/system calls `GET /api/v1/devices/{device_id}/health`
2. Service queries telemetry_service for device metrics
3. Metrics aggregated: CPU, memory, disk, temperature, battery, signal
4. Health score calculated (0-100) based on thresholds
5. Error/warning counts from recent telemetry
6. Response includes diagnostics and last_check timestamp

**Outcome**: Current health status with actionable metrics

**Events**: None (query operation)

**Business Rules Applied**:
- BR-DEV-030: Health score calculation
- BR-DEV-031: Telemetry integration
- BR-DEV-035: Error threshold detection

**Integration**: telemetry_service provides real-time metrics

---

### 5. Device Pairing Flow (QR Code)

**Trigger**: User scans QR code displayed on smart frame device

**Flow**:
1. Device displays QR code: `EMOFRAME:deviceId:pairingToken`
2. User scans with mobile app
3. App calls `POST /api/v1/devices/{device_id}/pair` with pairing_token
4. Service calls auth_service.verify_pairing_token()
5. If valid, device owner_id updated to user_id
6. Device status updated from pending to active
7. `device.paired` event published
8. Pairing token invalidated

**Outcome**: Device associated with user account, ready for use

**Events**:
- `device.paired` (EventType.DEVICE_PAIRED)

**Business Rules Applied**:
- BR-DEV-040: Pairing token validation
- BR-DEV-041: Single-use pairing token
- BR-DEV-042: Ownership assignment
- BR-DEV-043: Status transition on pairing

**Integration**: auth_service for token verification

---

### 6. Smart Frame Content Sync

**Trigger**: User adds photos to album or schedules sync

**Flow**:
1. User calls `POST /api/v1/devices/frames/{frame_id}/sync`
2. Service validates frame ownership or family sharing permission
3. Sync command created with album_ids and sync_type
4. Command sent to frame via MQTT (priority=5)
5. Frame downloads new photos from media_service
6. Frame updates local cache and playlist
7. Frame sends completion acknowledgment

**Outcome**: Frame displays latest photos from user albums

**Events**:
- `device.command_sent` (EventType.DEVICE_COMMAND_SENT)

**Business Rules Applied**:
- BR-DEV-050: Frame ownership validation
- BR-DEV-051: Family sharing permissions
- BR-DEV-052: Sync timeout (300 seconds)
- BR-DEV-055: Album ID validation

**Integration**: organization_service for family sharing, album_service for album data

---

### 7. Device Status Change (Online/Offline Detection)

**Trigger**: Device goes offline or comes back online

**Flow - Offline**:
1. Telemetry monitoring detects no heartbeat for 5 minutes
2. Service updates device status to inactive
3. last_seen timestamp preserved
4. `device.offline` event published
5. notification_service notifies user

**Flow - Online**:
1. Device sends heartbeat or telemetry data
2. Service receives `telemetry.data.received` event
3. last_seen timestamp updated
4. If status=inactive, changed to active
5. `device.online` event published
6. offline_duration_seconds calculated

**Outcome**: Accurate device availability tracking

**Events**:
- `device.offline` (EventType.DEVICE_OFFLINE)
- `device.online` (EventType.DEVICE_ONLINE)

**Business Rules Applied**:
- BR-DEV-060: Offline detection threshold (5 minutes)
- BR-DEV-061: Status transition inactive↔active
- BR-DEV-065: Last seen timestamp tracking

---

### 8. Firmware Update Notification

**Trigger**: New firmware uploaded to ota_service

**Flow**:
1. ota_service publishes `firmware.uploaded` event
2. device_service receives event with device_model + version
3. Service queries devices matching model
4. Compatible devices flagged for update availability
5. Devices notified on next connection
6. When device completes update, `update.completed` event received
7. Service updates device firmware_version field
8. `device.firmware.updated` event published

**Outcome**: Devices updated to latest firmware version

**Events Consumed**:
- `firmware.uploaded` (from ota_service)
- `update.completed` (from ota_service)

**Events Published**:
- `device.firmware.updated` (EventType.DEVICE_FIRMWARE_UPDATED)

**Business Rules Applied**:
- BR-DEV-070: Firmware version validation
- BR-DEV-071: Model compatibility check
- BR-DEV-075: Update completion tracking

---

## Domain Events

### Published Events

**1. device.registered** (EventType.DEVICE_REGISTERED)
- **When**: New device successfully registered
- **Data**:
  ```json
  {
    "device_id": "abc123...",
    "device_name": "Living Room Sensor",
    "device_type": "sensor",
    "user_id": "user_456",
    "manufacturer": "Acme Corp",
    "model": "SensorPro",
    "serial_number": "SN12345",
    "connectivity_type": "wifi",
    "timestamp": "2025-12-15T10:00:00Z"
  }
  ```
- **Consumers**: audit_service (logging), telemetry_service (monitoring setup)

**2. device.online** (EventType.DEVICE_ONLINE)
- **When**: Device connects and authenticates, or comes back online
- **Data**:
  ```json
  {
    "device_id": "abc123...",
    "device_name": "Living Room Sensor",
    "device_type": "sensor",
    "status": "active",
    "last_seen": "2025-12-15T10:05:00Z",
    "timestamp": "2025-12-15T10:05:00Z"
  }
  ```
- **Consumers**: telemetry_service (status tracking), notification_service (user alerts)

**3. device.offline** (EventType.DEVICE_OFFLINE)
- **When**: Device heartbeat timeout (5 minutes)
- **Data**:
  ```json
  {
    "device_id": "abc123...",
    "device_name": "Living Room Sensor",
    "device_type": "sensor",
    "status": "inactive",
    "last_seen": "2025-12-15T10:00:00Z",
    "timestamp": "2025-12-15T10:05:00Z"
  }
  ```
- **Consumers**: notification_service (user alerts), telemetry_service (status tracking)

**4. device.command_sent** (EventType.DEVICE_COMMAND_SENT)
- **When**: Command successfully sent to device via MQTT
- **Data**:
  ```json
  {
    "command_id": "cmd_789",
    "device_id": "abc123...",
    "user_id": "user_456",
    "command": "display_photo",
    "parameters": {"photo_id": "photo_123"},
    "priority": 5,
    "timestamp": "2025-12-15T10:10:00Z"
  }
  ```
- **Consumers**: audit_service (command logging), telemetry_service (command tracking)

**5. device.paired** (EventType.DEVICE_PAIRED)
- **When**: Device successfully paired with user via pairing token
- **Data**:
  ```json
  {
    "device_id": "abc123...",
    "user_id": "user_456",
    "device_name": "Living Room Frame",
    "device_type": "smart_frame",
    "timestamp": "2025-12-15T10:15:00Z"
  }
  ```
- **Consumers**: organization_service (ownership tracking), notification_service (pairing confirmation)

**6. device.status.changed** (EventType.DEVICE_STATUS_CHANGED)
- **When**: Device status transitions (e.g., active→maintenance, active→error)
- **Data**:
  ```json
  {
    "device_id": "abc123...",
    "old_status": "active",
    "new_status": "maintenance",
    "reason": "Scheduled firmware update",
    "timestamp": "2025-12-15T10:20:00Z"
  }
  ```
- **Consumers**: telemetry_service (status history), notification_service (user alerts)

**7. device.firmware.updated** (EventType.DEVICE_FIRMWARE_UPDATED)
- **When**: Device firmware version updated after OTA update
- **Data**:
  ```json
  {
    "device_id": "abc123...",
    "old_version": "1.0.0",
    "new_version": "1.1.0",
    "update_id": "update_xyz",
    "timestamp": "2025-12-15T10:25:00Z"
  }
  ```
- **Consumers**: ota_service (update tracking), audit_service (version history)

**8. device.deleted** (EventType.DEVICE_DELETED)
- **When**: Device decommissioned (soft delete)
- **Data**:
  ```json
  {
    "device_id": "abc123...",
    "user_id": "user_456",
    "device_type": "sensor",
    "reason": "Device replaced",
    "timestamp": "2025-12-15T10:30:00Z"
  }
  ```
- **Consumers**: telemetry_service (cleanup metrics), location_service (cleanup location data), album_service (cleanup sync status)

### Consumed Events

**1. firmware.uploaded** (from ota_service)
- **When**: New firmware available for device model
- **Action**: Notify compatible devices, flag for update

**2. update.completed** (from ota_service)
- **When**: Device completes firmware update
- **Action**: Update device firmware_version field

**3. telemetry.data.received** (from telemetry_service)
- **When**: Device sends telemetry data (heartbeat)
- **Action**: Update last_seen, check if status should change to active

## Core Concepts

### Device Identity and Uniqueness

Each device has multiple identity attributes:
- **device_id**: SHA-256 hash of serial_number + mac_address + timestamp (32 chars)
- **serial_number**: Manufacturer-assigned unique identifier (must be unique in system)
- **mac_address**: Network hardware address (optional but recommended)

The device_id is deterministic yet unique due to timestamp inclusion. This allows offline device registration while preventing collisions.

### Device Ownership and Multi-Tenancy

Devices support both individual and organizational ownership:
- **user_id**: Primary owner of device
- **organization_id**: Optional organization membership (for enterprise devices)
- **group_id**: Optional logical grouping for management

Family sharing for smart frames is handled via organization_service permissions, not direct device ownership.

### Command Delivery Guarantees

Commands are delivered with best-effort guarantees:
1. **Persistent storage**: Commands saved to database before MQTT send
2. **MQTT QoS 1**: At-least-once delivery via MQTT
3. **Acknowledgment tracking**: Optional device confirmation
4. **Timeout handling**: Commands expire after timeout period
5. **Retry mechanism**: Failed commands can be retried

No strict ordering guarantees - use priority for important commands.

### Smart Frame Architecture

Smart frames are specialized devices (type=smart_frame) with extended capabilities:
- **Display configuration**: Brightness, orientation, slideshow settings
- **Content sync**: Integration with album_service for photo retrieval
- **Power management**: Sleep schedules, motion detection
- **Family sharing**: Multi-user access via organization_service

Frame configs stored separately in frame_configs table for extensibility.

### Device Health Scoring

Health score (0-100) calculated from multiple factors:
- **Hardware metrics**: CPU (0-100%), memory (0-100%), disk (0-100%)
- **Environmental**: Temperature (safe range), battery (if applicable)
- **Network**: Signal strength, connectivity stability
- **Error history**: Recent error/warning counts

Algorithm:
```
base_score = 100
- Deduct 20% if CPU > 80%
- Deduct 15% if memory > 80%
- Deduct 10% if disk > 90%
- Deduct 5% per error in last 24h (max 25%)
- Deduct 10% if temperature > threshold
health_score = max(0, base_score)
```

### Event-Driven Integration

Device service is a central hub in event-driven architecture:

**Publishes**:
- Lifecycle events (registered, paired, deleted)
- Status events (online, offline, status_changed)
- Operational events (command_sent, firmware_updated)

**Subscribes**:
- firmware.uploaded (ota_service) - notify devices of updates
- update.completed (ota_service) - track firmware versions
- telemetry.data.received (telemetry_service) - update last_seen

Event-driven design enables:
- Loose coupling between services
- Asynchronous processing
- Audit trail and observability
- Service scaling and resilience

## High-Level Business Rules

### Device Registration (BR-DEV-001 to BR-DEV-010)

**BR-DEV-001: Unique Device ID Generation**
- Device ID generated from SHA-256(serial_number + mac_address + timestamp)
- Truncated to 32 characters for database efficiency
- Deterministic yet unique due to timestamp component

**BR-DEV-002: Serial Number Uniqueness**
- Serial numbers must be unique across all devices in system
- Database constraint enforces uniqueness
- Registration fails if serial_number already exists

**BR-DEV-003: MAC Address Validation**
- If provided, MAC address must match pattern: XX:XX:XX:XX:XX:XX or XX-XX-XX-XX-XX-XX
- Validation performed by Pydantic model
- Optional field, but recommended for network devices

**BR-DEV-004: Device Type Validation**
- Must be one of 11 supported types: sensor, actuator, gateway, smart_home, industrial, medical, automotive, wearable, camera, controller, smart_frame
- Enum validation enforced at API and database layers

**BR-DEV-005: Default Security Level**
- If not specified, security_level defaults to "standard"
- Can be overridden during registration for high-security devices

**BR-DEV-006: Initial Status Assignment**
- All new devices start with status="pending"
- Status transitions to "active" only after successful authentication or pairing

**BR-DEV-007: Organization Assignment**
- organization_id is optional during registration
- If provided, must reference valid organization in organization_service
- Used for enterprise device management

**BR-DEV-008: JWT Token Expiry**
- Device authentication tokens expire after 24 hours (86400 seconds)
- Tokens include device_id, scope="device:all", iat, exp
- Algorithm: HS256 with service-specific secret key

**BR-DEV-009: Required Registration Fields**
- Mandatory: device_name, device_type, manufacturer, model, serial_number, firmware_version, connectivity_type
- Optional: hardware_version, mac_address, location, metadata, group_id, tags

**BR-DEV-010: Firmware Version Format**
- Must be non-empty string, max 50 characters
- No specific versioning scheme enforced (semantic versioning recommended)

### Device Lifecycle (BR-DEV-011 to BR-DEV-020)

**BR-DEV-011: Status Transition Rules**
- Valid transitions: pending→active, active→inactive, active→maintenance, active→error, any→decommissioned
- Invalid transitions rejected (e.g., pending→decommissioned without intermediate state)

**BR-DEV-012: Decommissioning Behavior**
- Decommission is soft delete: status set to "decommissioned", decommissioned_at timestamp set
- Device record retained for audit purposes
- Device cannot be reactivated after decommissioning

**BR-DEV-013: Last Seen Timestamp**
- Updated on every authentication, telemetry data, or command acknowledgment
- Used to detect offline devices (threshold: 5 minutes of inactivity)

**BR-DEV-014: Offline Detection**
- Device marked inactive if no last_seen update for 5 minutes
- Monitored by telemetry_service, not real-time
- device.offline event published when detected

**BR-DEV-015: Online Restoration**
- When inactive device sends telemetry or authenticates, status updated to active
- device.online event published with offline_duration_seconds

**BR-DEV-016: Maintenance Mode**
- User or system can set status to "maintenance" for planned downtime
- Prevents offline alerts during maintenance window
- Requires manual restoration to active after maintenance

**BR-DEV-017: Error State Handling**
- Device set to "error" status when critical failure detected
- Error details stored in metadata or diagnostics
- Requires investigation and manual intervention to restore

**BR-DEV-018: Device Deletion Cascade**
- When device deleted, device.deleted event triggers cleanup in dependent services
- telemetry_service: Delete metrics and alert rules
- location_service: Delete location history
- album_service: Delete sync status

**BR-DEV-019: Ownership Transfer**
- Devices can be transferred between users (future enhancement)
- Requires user consent and auth_service token revocation
- Not currently implemented in v1.0

**BR-DEV-020: Multi-Tenancy Isolation**
- Devices scoped to user_id or organization_id
- List operations automatically filter by authenticated user
- Prevents cross-tenant data leakage

### Command Management (BR-DEV-021 to BR-DEV-030)

**BR-DEV-021: Priority Range Validation**
- Command priority must be integer 1-10 (1=lowest, 10=highest)
- Default priority: 5 (medium)
- Devices execute higher priority commands first

**BR-DEV-022: MQTT Topic Format**
- Device command topic: `devices/{device_id}/commands`
- Device response topic: `devices/{device_id}/responses`
- Service-wide topic structure for consistency

**BR-DEV-023: Timeout Constraints**
- Minimum timeout: 1 second
- Maximum timeout: 300 seconds (5 minutes)
- Default timeout: 30 seconds

**BR-DEV-024: Command Parameters Validation**
- Parameters must be valid JSON object
- Maximum size: 10KB (prevents MQTT payload overflow)
- Specific parameter validation depends on command type

**BR-DEV-025: Command Status Lifecycle**
- Status flow: pending → sent → acknowledged → executed/failed/timeout
- Timestamps: created_at, sent_at, acknowledged_at, completed_at
- Terminal states: executed, failed, timeout

**BR-DEV-026: MQTT Fallback Behavior**
- If MQTT client unavailable, command simulated for testing
- Simulation: 100ms delay, status set to "simulated"
- Production deployments must have MQTT available

**BR-DEV-027: Acknowledgment Requirements**
- If require_ack=true, device must send acknowledgment within timeout
- If require_ack=false, command considered successful after MQTT send
- Default: require_ack=true

**BR-DEV-028: Bulk Command Constraints**
- Maximum devices per bulk command: 100
- Commands sent sequentially with 10ms delay between sends
- Results array includes success/failure per device

**BR-DEV-029: Command Idempotency**
- Commands identified by unique command_id (32-char hex)
- Duplicate command_id rejected
- Supports retry without duplicate execution

**BR-DEV-030: Command Authorization**
- User must own device or have organization permissions
- Checked via user_context from auth token
- Smart frames additionally check family sharing permissions

### Device Health (BR-DEV-031 to BR-DEV-040)

**BR-DEV-031: Telemetry Integration**
- Health data sourced from telemetry_service
- Falls back to device status if telemetry unavailable
- Real-time data preferred, cached data acceptable

**BR-DEV-032: Health Score Calculation**
- Base score: 100
- CPU >80%: -20 points
- Memory >80%: -15 points
- Disk >90%: -10 points
- Each error: -5 points (max -25)
- Temperature >threshold: -10 points

**BR-DEV-033: Metric Thresholds**
- CPU critical: >80%, warning: >60%
- Memory critical: >80%, warning: >60%
- Disk critical: >90%, warning: >75%
- Temperature critical: >80°C, warning: >70°C

**BR-DEV-034: Battery Level Monitoring**
- Applicable only for battery-powered devices
- Critical: <10%, warning: <20%
- Null for mains-powered devices

**BR-DEV-035: Error Threshold Detection**
- Error count: Cumulative errors in last 24 hours
- Warning count: Cumulative warnings in last 24 hours
- Last error: Most recent error message from telemetry

**BR-DEV-036: Signal Strength Interpretation**
- RSSI values: -30 (excellent) to -90 (poor) dBm
- Normalized to 0-100 scale for display
- Null for wired connectivity types

**BR-DEV-037: Diagnostics Data Structure**
- Free-form JSON object for extensibility
- Common fields: last_reboot, uptime, network_stats
- Service-specific diagnostics as needed

**BR-DEV-038: Health Check Frequency**
- On-demand via API call (not periodic)
- Cached for 60 seconds to prevent telemetry service overload
- Real-time data available for critical alerts

**BR-DEV-039: Health Score History**
- Historical health scores stored in telemetry_service
- device_service only returns current health
- Trending analysis performed in telemetry_service

**BR-DEV-040: Degraded Performance Detection**
- Health score <50: Critical state, alert user
- Health score 50-70: Degraded state, monitor closely
- Health score >70: Normal operation

### Device Pairing (BR-DEV-041 to BR-DEV-050)

**BR-DEV-041: Pairing Token Validation**
- Token verified by auth_service.verify_pairing_token()
- Token must be valid, not expired, not already used
- Token format: opaque string from QR code

**BR-DEV-042: Single-Use Pairing Token**
- Each token can only be used once
- After successful pairing, token invalidated
- Prevents unauthorized device claims

**BR-DEV-043: Pairing Token Expiry**
- Tokens expire after 15 minutes (configurable in auth_service)
- Expired tokens rejected during pairing
- User must regenerate QR code if expired

**BR-DEV-044: Ownership Assignment on Pairing**
- Device owner_id set to pairing user_id
- Previous owner_id (if any) overwritten
- Ownership transfer requires re-pairing flow

**BR-DEV-045: Status Transition on Pairing**
- Device status changed from "pending" to "active"
- Triggers device.paired event
- Device immediately usable after pairing

**BR-DEV-046: QR Code Format**
- Format: `EMOFRAME:{device_id}:{pairing_token}`
- Colon-separated, no URL encoding
- Displayed on device screen during setup

**BR-DEV-047: Pairing API Authorization**
- Pairing endpoint requires valid user authentication
- User ID extracted from JWT token in Authorization header
- Prevents anonymous device claims

**BR-DEV-048: Concurrent Pairing Prevention**
- If device already paired (has owner_id), pairing fails
- User must depair/reset device first
- Prevents ownership conflicts

**BR-DEV-049: Pairing Event Publishing**
- device.paired event includes device_id, user_id, device_name, device_type
- Consumed by organization_service for family sharing setup
- Audit trail for device ownership changes

**BR-DEV-050: Cross-Service Pairing Flow**
- Step 1: auth_service generates pairing token
- Step 2: Device displays QR code with token
- Step 3: User scans, calls device_service.pair_device()
- Step 4: device_service verifies with auth_service
- Step 5: Ownership assigned, status updated, event published

### Smart Frame Features (BR-DEV-051 to BR-DEV-060)

**BR-DEV-051: Frame Ownership Validation**
- User must own frame (device.user_id == user_id) OR
- Have family sharing permission via organization_service
- Checked before any frame configuration or command

**BR-DEV-052: Display Mode Constraints**
- Must be one of: photo_slideshow, video_playback, clock_display, weather_info, calendar_view, off
- Stored in frame_configs table, not device metadata
- Default: photo_slideshow

**BR-DEV-053: Slideshow Interval Limits**
- Minimum: 5 seconds (prevent rapid transitions)
- Maximum: 3600 seconds (1 hour)
- Default: 30 seconds

**BR-DEV-054: Brightness Range**
- Integer 0-100 (percentage)
- Default: 80
- Auto-brightness overrides manual setting if enabled

**BR-DEV-055: Album Sync Validation**
- auto_sync_albums: List of album IDs from album_service
- Each album_id validated against album_service API
- User must have access to albums (ownership or sharing)

**BR-DEV-056: Sync Frequency Options**
- Values: hourly, daily, weekly, manual
- Default: hourly
- Manual sync requires explicit user action

**BR-DEV-057: Sleep Schedule Format**
- JSON object: `{"start": "23:00", "end": "07:00"}`
- Times in HH:MM format (24-hour)
- Timezone applied from frame location or user profile

**BR-DEV-058: Motion Detection Wake**
- If motion_detection=true, frame wakes on movement
- Requires hardware motion sensor support
- Falls back to manual wake if sensor unavailable

**BR-DEV-059: Frame Config Storage**
- Separate table: device.frame_configs (one-to-one with device)
- Extended config separate from core device attributes
- Allows future device type configs without schema changes

**BR-DEV-060: Family Sharing Permissions**
- Checked via organization_service.check_smart_frame_access(device_id, user_id, permission)
- Permissions: read (view), read_write (control)
- Owner has full permissions, shared users have limited
