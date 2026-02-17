# OTA Service - Domain Context

## Overview

The OTA (Over-The-Air) Service is the firmware lifecycle management hub for the isA IoT platform. It manages the complete firmware update journey from upload through deployment to completion, ensuring secure and reliable updates across thousands of distributed IoT devices.

**Business Context**: IoT devices require continuous software updates to address security vulnerabilities, add features, and fix bugs. Manual updates are impractical at scale, making OTA updates essential for enterprise IoT deployments.

**Core Value Proposition**: Enables administrators to safely deploy firmware updates to device fleets with sophisticated deployment strategies, rollback protection, and real-time progress tracking.

---

## Business Taxonomy

### Core Entities

#### 1. Firmware
**Definition**: A binary package containing software updates for specific device models.

**Business Purpose**:
- Store device software updates in a central repository
- Track firmware versions and compatibility information
- Enable secure distribution with checksum verification
- Support beta releases and security patches

**Key Attributes**:
- firmware_id (unique identifier based on name:version:model hash)
- name (firmware package name)
- version (semantic version string)
- device_model (target device model compatibility)
- manufacturer (device manufacturer)
- file_size (binary size in bytes)
- checksum_md5 / checksum_sha256 (integrity verification)
- is_beta (beta release flag)
- is_security_update (security patch flag)
- file_url (download location)

**Entity States**:
- **Available**: Firmware uploaded and ready for deployment
- **Deprecated**: Older version, not recommended for new deployments
- **Recalled**: Removed from availability due to critical issues

#### 2. Update Campaign
**Definition**: An orchestrated deployment operation targeting multiple devices with a specific firmware version.

**Business Purpose**:
- Coordinate mass device updates with controlled rollout
- Monitor deployment progress across device fleets
- Implement deployment strategies (staged, canary, blue-green)
- Enable automatic rollback on failure thresholds

**Key Attributes**:
- campaign_id (unique identifier)
- name (campaign name for identification)
- firmware_id (target firmware to deploy)
- status (created, in_progress, completed, failed, cancelled)
- deployment_strategy (immediate, scheduled, staged, canary, blue_green)
- priority (low, normal, high, critical, emergency)
- target_device_count (number of devices targeted)
- rollout_percentage (percentage of devices to update)
- auto_rollback (automatic rollback on failure threshold)
- failure_threshold_percent (failure rate triggering rollback)

**Entity States**:
- **Created**: Campaign defined but not started
- **In Progress**: Campaign actively deploying updates
- **Completed**: All target devices updated successfully
- **Failed**: Campaign stopped due to failures
- **Cancelled**: Campaign manually stopped

#### 3. Device Update
**Definition**: An individual update operation for a specific device within or outside a campaign.

**Business Purpose**:
- Track individual device update progress
- Monitor download, verification, and installation phases
- Support retry mechanisms for failed updates
- Maintain update history for compliance

**Key Attributes**:
- update_id (unique identifier)
- device_id (target device)
- campaign_id (optional parent campaign)
- firmware_id (firmware being installed)
- status (scheduled, in_progress, downloading, verifying, installing, completed, failed, cancelled, rollback)
- progress_percentage (0-100% completion)
- current_phase (downloading, verifying, installing, rebooting)
- error_code / error_message (failure details)
- retry_count / max_retries (retry tracking)

**Entity States**:
- **Scheduled**: Update queued for execution
- **In Progress**: Update actively running
- **Downloading**: Device downloading firmware
- **Verifying**: Device verifying firmware integrity
- **Installing**: Device installing firmware
- **Rebooting**: Device restarting with new firmware
- **Completed**: Update successfully finished
- **Failed**: Update failed after retries
- **Cancelled**: Update manually cancelled
- **Rollback**: Device reverting to previous version

#### 4. Rollback Operation
**Definition**: A recovery operation reverting a device to a previous firmware version.

**Business Purpose**:
- Recover devices from failed or problematic updates
- Support both automatic and manual rollback triggers
- Maintain device availability during update failures
- Track rollback history for analysis

**Key Attributes**:
- rollback_id (unique identifier)
- device_id (device being rolled back)
- campaign_id (optional related campaign)
- from_version (current firmware version)
- to_version (target rollback version)
- trigger (manual, failure_rate, health_check, timeout, error_threshold)
- status (in_progress, completed, failed)
- reason (rollback justification)

---

## Domain Scenarios

### Scenario 1: Firmware Upload and Registration

**Actor**: Administrator / System
**Trigger**: New firmware version ready for deployment

**Flow**:
1. Administrator prepares firmware binary and metadata
2. Administrator calls `POST /api/v1/ota/firmware` with file and metadata
3. Service validates file format and size constraints
4. Service calculates MD5 and SHA256 checksums
5. If checksums provided, service verifies against calculated values
6. Service generates deterministic firmware_id from name:version:model
7. Service uploads binary to Storage Service (MinIO/S3)
8. Service saves firmware metadata to PostgreSQL
9. `firmware.uploaded` event published to NATS
10. Device Service notifies compatible devices of new firmware

**Outcome**: Firmware available for deployment to compatible devices

**Events**:
- `firmware.uploaded` (EventType.FIRMWARE_UPLOADED)

**Business Rules Applied**:
- BR-OTA-001: File size limit (500MB)
- BR-OTA-002: Supported file formats
- BR-OTA-003: Checksum verification
- BR-OTA-004: Deterministic firmware ID

---

### Scenario 2: Create and Start Update Campaign

**Actor**: Administrator
**Trigger**: Decision to deploy firmware to device fleet

**Flow**:
1. Administrator calls `POST /api/v1/ota/campaigns` with campaign configuration
2. Service validates firmware_id exists and is available
3. Service calculates target device count from device IDs, groups, and filters
4. Campaign created with status=created
5. `campaign.created` event published
6. Administrator calls `POST /api/v1/ota/campaigns/{id}/start`
7. Service validates campaign is in created status
8. Campaign status updated to in_progress
9. Batch update process initiated based on deployment_strategy
10. `campaign.started` event published
11. Device updates scheduled according to batch_size and max_concurrent_updates

**Outcome**: Campaign actively deploying updates to target devices

**Events**:
- `campaign.created` (EventType.CAMPAIGN_CREATED)
- `campaign.started` (EventType.CAMPAIGN_STARTED)

**Business Rules Applied**:
- BR-OTA-010: Campaign requires valid firmware
- BR-OTA-011: Target device validation
- BR-OTA-012: Deployment strategy execution
- BR-OTA-013: Concurrent update limits

---

### Scenario 3: Single Device Update

**Actor**: Administrator / System
**Trigger**: Need to update specific device outside campaign

**Flow**:
1. Administrator calls `POST /api/v1/ota/devices/{device_id}/update` with firmware_id
2. Service validates device exists via Device Service
3. Service retrieves device current firmware version
4. Service checks firmware compatibility (device_model, hardware_version)
5. Device update record created with status=scheduled
6. Update command sent to device via MQTT (future) or polling
7. Device downloads firmware from file_url
8. Device verifies checksum (signature_verified, checksum_verified)
9. Device installs firmware and reboots
10. Device reports completion status

**Outcome**: Individual device updated to target firmware version

**Events**:
- None directly published (tracked via device update status)

**Business Rules Applied**:
- BR-OTA-020: Device validation required
- BR-OTA-021: Firmware compatibility check
- BR-OTA-022: Update timeout handling
- BR-OTA-025: Retry mechanism

---

### Scenario 4: Update Progress Monitoring

**Actor**: Administrator / Dashboard
**Trigger**: Need to track update status

**Flow**:
1. Administrator calls `GET /api/v1/ota/updates/{update_id}`
2. Service queries device_updates table
3. Service retrieves associated firmware information
4. Response includes progress_percentage, current_phase, status
5. If campaign update, campaign progress also available
6. Real-time metrics include download_progress, download_speed
7. Error details available if status=failed

**Outcome**: Current update status with actionable metrics

**Events**: None (query operation)

**Business Rules Applied**:
- BR-OTA-030: Progress tracking granularity
- BR-OTA-031: Phase transition tracking

---

### Scenario 5: Campaign Rollback on Failure Threshold

**Actor**: System (Automatic)
**Trigger**: Failure rate exceeds configured threshold

**Flow**:
1. System monitors campaign failure rate during deployment
2. Failure rate exceeds failure_threshold_percent (e.g., 20%)
3. If auto_rollback=true, rollback initiated automatically
4. Campaign status updated to rollback
5. Pending device updates cancelled
6. Completed devices scheduled for rollback to previous version
7. `rollback.initiated` event published
8. Rollback operations executed device by device
9. Campaign status updated to failed after rollback completes

**Outcome**: Devices restored to previous firmware, preventing widespread failure

**Events**:
- `rollback.initiated` (EventType.ROLLBACK_INITIATED)

**Business Rules Applied**:
- BR-OTA-040: Failure rate calculation
- BR-OTA-041: Auto-rollback trigger
- BR-OTA-042: Rollback priority

---

### Scenario 6: Manual Device Rollback

**Actor**: Administrator
**Trigger**: Need to revert specific device firmware

**Flow**:
1. Administrator calls `POST /api/v1/ota/devices/{device_id}/rollback`
2. Request includes to_version (target rollback version)
3. Service validates device and target version availability
4. Rollback record created with trigger=manual
5. Device notified of rollback requirement
6. Device downloads previous firmware version
7. Device installs and reboots with previous version
8. `rollback.initiated` event published
9. Rollback status updated on completion

**Outcome**: Device reverted to specified previous firmware version

**Events**:
- `rollback.initiated` (EventType.ROLLBACK_INITIATED)

**Business Rules Applied**:
- BR-OTA-043: Rollback version validation
- BR-OTA-044: Device state before rollback

---

### Scenario 7: Update Statistics and Analytics

**Actor**: Administrator / Dashboard
**Trigger**: Need fleet update status overview

**Flow**:
1. Administrator calls `GET /api/v1/ota/stats`
2. Service aggregates campaign statistics from database
3. Service aggregates device update statistics
4. Success rate calculated from completed/total updates
5. Last 24h metrics compiled
6. Response includes comprehensive statistics

**Outcome**: Fleet-wide update health and progress metrics

**Events**: None (query operation)

**Business Rules Applied**:
- BR-OTA-050: Statistics calculation accuracy
- BR-OTA-051: Time-based filtering

---

### Scenario 8: Device Deletion Cleanup

**Actor**: System (Event-Driven)
**Trigger**: device.deleted event from Device Service

**Flow**:
1. Device Service publishes `device.deleted` event
2. OTA Service receives event via NATS subscription
3. Service cancels all pending/in-progress updates for device
4. Update records retained for audit purposes
5. Device removed from active campaign targets

**Outcome**: No orphaned updates for deleted devices

**Events Consumed**:
- `device.deleted` (from Device Service)

**Business Rules Applied**:
- BR-OTA-060: Update cancellation on device deletion
- BR-OTA-061: Audit trail retention

---

## Domain Events

### Published Events

**1. firmware.uploaded** (EventType.FIRMWARE_UPLOADED)
- **When**: After successful firmware upload and storage
- **Data**:
  ```json
  {
    "firmware_id": "abc123...",
    "name": "Smart Frame Firmware",
    "version": "2.1.0",
    "device_model": "SF-100",
    "file_size": 52428800,
    "is_security_update": false,
    "uploaded_by": "admin_user_123",
    "timestamp": "2025-12-15T10:00:00Z"
  }
  ```
- **Consumers**:
  - **device_service**: Notifies compatible devices of update availability
  - **audit_service**: Logs firmware upload for compliance
  - **notification_service**: Optional admin notification

**2. campaign.created** (EventType.CAMPAIGN_CREATED)
- **When**: After update campaign successfully created
- **Data**:
  ```json
  {
    "campaign_id": "camp_789...",
    "name": "Security Patch Q4 2025",
    "firmware_id": "abc123...",
    "firmware_version": "2.1.0",
    "target_device_count": 500,
    "deployment_strategy": "staged",
    "priority": "high",
    "created_by": "admin_user_123",
    "timestamp": "2025-12-15T10:05:00Z"
  }
  ```
- **Consumers**:
  - **audit_service**: Campaign creation logging
  - **notification_service**: Admin notification of new campaign

**3. campaign.started** (EventType.CAMPAIGN_STARTED)
- **When**: After campaign deployment begins
- **Data**:
  ```json
  {
    "campaign_id": "camp_789...",
    "name": "Security Patch Q4 2025",
    "firmware_id": "abc123...",
    "firmware_version": "2.1.0",
    "target_device_count": 500,
    "timestamp": "2025-12-15T10:10:00Z"
  }
  ```
- **Consumers**:
  - **audit_service**: Campaign start logging
  - **telemetry_service**: Begin campaign metrics collection
  - **notification_service**: Stakeholder notification

**4. update.cancelled** (EventType.UPDATE_CANCELLED)
- **When**: After device update is cancelled
- **Data**:
  ```json
  {
    "update_id": "upd_456...",
    "device_id": "dev_123...",
    "firmware_id": "abc123...",
    "firmware_version": "2.1.0",
    "campaign_id": "camp_789...",
    "timestamp": "2025-12-15T10:15:00Z"
  }
  ```
- **Consumers**:
  - **device_service**: Update device metadata
  - **audit_service**: Cancellation logging

**5. rollback.initiated** (EventType.ROLLBACK_INITIATED)
- **When**: After rollback operation starts (manual or automatic)
- **Data**:
  ```json
  {
    "rollback_id": "rb_999...",
    "device_id": "dev_123...",
    "from_version": "2.1.0",
    "to_version": "2.0.0",
    "trigger": "failure_rate",
    "timestamp": "2025-12-15T10:20:00Z"
  }
  ```
- **Consumers**:
  - **device_service**: Update device firmware version
  - **audit_service**: Rollback event logging
  - **notification_service**: Alert administrators

### Consumed Events

**1. device.deleted** (from device_service)
- **When**: Device is decommissioned or removed
- **Handler**: `handle_device_deleted()`
- **Action**: Cancel all pending/in-progress updates for device
- **Side Effects**:
  - Update records set to cancelled status
  - Campaign device counts updated

**2. user.deleted** (from account_service)
- **When**: User account is deleted
- **Handler**: `handle_user_deleted()`
- **Action**: Cancel updates for all user's devices, clean preferences
- **Side Effects**:
  - All user device updates cancelled
  - User firmware preferences deleted

---

## Core Concepts

### Firmware Lifecycle Management

1. **Upload**: Firmware binary uploaded with metadata validation
2. **Validation**: Checksum verification, format validation
3. **Storage**: Binary stored in object storage (MinIO/S3)
4. **Availability**: Firmware registered and available for deployment
5. **Deprecation**: Older versions marked deprecated
6. **Recall**: Critical issues trigger firmware recall

### Deployment Strategies

- **Immediate**: All target devices updated simultaneously
- **Scheduled**: Updates begin at specified time
- **Staged**: Gradual rollout in batches (percentage-based)
- **Canary**: Small subset first, then full rollout if successful
- **Blue-Green**: Parallel deployment with instant switchover

### Update State Machine

```
Created → Scheduled → In Progress → [Downloading → Verifying → Installing → Rebooting] → Completed
                          ↓                                                                    ↓
                       Failed ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←
                          ↓
                       Rollback
                          ↓
                       Cancelled
```

### Rollback Protection

- **Automatic Rollback**: Triggered when failure_rate > threshold
- **Manual Rollback**: Administrator-initiated recovery
- **Rollback Triggers**:
  - failure_rate: Too many update failures
  - health_check: Post-update health check fails
  - timeout: Update exceeds timeout
  - error_threshold: Critical error count exceeded

### Data Integrity Guarantees

- **Checksum Verification**: MD5 and SHA256 for all firmware
- **Atomic Operations**: PostgreSQL transactions for data consistency
- **Idempotent Updates**: Safe retry without duplicate effects
- **Audit Trail**: All operations logged for compliance

### Service Boundaries

**OTA Service owns**:
- Firmware metadata and binary storage
- Update campaigns and deployment strategies
- Device update tracking and progress
- Rollback operations and history
- Update statistics and analytics

**OTA Service does NOT own**:
- Device registration and management (device_service)
- Device authentication (auth_service)
- File storage infrastructure (storage_service)
- User notifications (notification_service)
- Device telemetry (telemetry_service)

---

## Business Rules (High-Level)

### Firmware Rules (BR-OTA-001 to BR-OTA-010)

**BR-OTA-001: Maximum Firmware File Size**
- Firmware file size MUST NOT exceed 500MB
- Validated during upload before storage
- Error: "File size exceeds maximum limit"

**BR-OTA-002: Supported Firmware Formats**
- File extension MUST be one of: .bin, .hex, .elf, .tar.gz, .zip
- Validated by file extension, not content type
- Error: "Unsupported file format"

**BR-OTA-003: Checksum Verification**
- If checksums provided in request, MUST match calculated values
- MD5 and SHA256 both validated if provided
- Error: "MD5 checksum mismatch" or "SHA256 checksum mismatch"

**BR-OTA-004: Deterministic Firmware ID**
- firmware_id = SHA256(name + ":" + version + ":" + device_model)[:32]
- Same input always produces same ID
- Prevents duplicate firmware versions

**BR-OTA-005: Firmware Uniqueness**
- Combination of device_model + version MUST be unique
- Duplicate upload returns existing firmware record
- No error, idempotent operation

**BR-OTA-006: Required Firmware Metadata**
- Mandatory fields: name, version, device_model, manufacturer
- Version MUST be 1-50 characters
- Name MUST be 1-200 characters

**BR-OTA-007: Firmware Tags and Metadata**
- tags: Optional array of strings for categorization
- metadata: Optional JSON object for custom attributes
- Both support arbitrary user-defined values

**BR-OTA-008: Security Update Flag**
- is_security_update: Boolean indicating security patch
- Security updates may receive priority deployment
- Used for reporting and compliance

**BR-OTA-009: Beta Release Flag**
- is_beta: Boolean indicating pre-release firmware
- Beta firmware requires explicit opt-in for deployment
- Separate from production firmware lifecycle

**BR-OTA-010: Firmware Download Tracking**
- download_count incremented on each download
- success_rate calculated from update completions
- Used for analytics and quality metrics

### Campaign Rules (BR-OTA-011 to BR-OTA-020)

**BR-OTA-011: Campaign Requires Valid Firmware**
- firmware_id MUST reference existing firmware
- Validation occurs during campaign creation
- Error: "Firmware not found"

**BR-OTA-012: Target Device Specification**
- At least one of: target_devices, target_groups, target_filters MUST be provided
- Empty campaign (0 devices) is valid but not useful
- Target count calculated from all sources

**BR-OTA-013: Deployment Strategy Values**
- MUST be one of: immediate, scheduled, staged, canary, blue_green
- Default: staged (safest option)
- Strategy determines rollout behavior

**BR-OTA-014: Priority Values**
- MUST be one of: low, normal, high, critical, emergency
- Default: normal
- Higher priority updates scheduled first

**BR-OTA-015: Rollout Percentage Range**
- MUST be 1-100 (integer percentage)
- Default: 100 (all target devices)
- Used with staged deployment strategy

**BR-OTA-016: Concurrent Update Limits**
- max_concurrent_updates: 1-1000
- Default: 10
- Prevents overwhelming device fleet

**BR-OTA-017: Batch Size Limits**
- batch_size: 1-500
- Default: 50
- Devices processed in batches

**BR-OTA-018: Timeout Configuration**
- timeout_minutes: 5-1440 (5 min to 24 hours)
- Default: 60 minutes
- Update fails if exceeds timeout

**BR-OTA-019: Failure Threshold Range**
- failure_threshold_percent: 1-100
- Default: 20%
- Triggers auto-rollback if exceeded

**BR-OTA-020: Auto-Rollback Default**
- auto_rollback: Boolean, default true
- Recommended for production deployments
- Can be disabled for debugging

### Device Update Rules (BR-OTA-021 to BR-OTA-030)

**BR-OTA-021: Device Validation**
- device_id MUST exist in Device Service
- Service calls device_client.get_device() for validation
- Error: "Device not found"

**BR-OTA-022: Firmware Compatibility**
- Firmware device_model SHOULD match device model
- Hardware version range checked if specified
- Warning logged if compatibility uncertain

**BR-OTA-023: Update Priority Range**
- MUST be one of: low, normal, high, critical, emergency
- Default: normal
- Affects scheduling order

**BR-OTA-024: Maximum Retry Count**
- max_retries: 0-10
- Default: 3
- Update fails permanently after max retries

**BR-OTA-025: Update Timeout**
- timeout_minutes: 5-1440
- Default: 60 minutes
- Same constraints as campaign timeout

**BR-OTA-026: Force Update Option**
- force_update: Boolean
- If true, skips version comparison
- Used for re-flashing same version

**BR-OTA-027: Pre/Post Update Commands**
- Optional command lists for device execution
- Executed before download and after installation
- Supports custom device preparation

**BR-OTA-028: Maintenance Window**
- Optional JSON object specifying update window
- Format: {"start": "HH:MM", "end": "HH:MM", "timezone": "TZ"}
- Update scheduled within window only

**BR-OTA-029: Update Status Tracking**
- Status transitions tracked with timestamps
- scheduled_at, started_at, completed_at recorded
- Used for SLA monitoring

**BR-OTA-030: Progress Tracking**
- progress_percentage: 0.0-100.0 (float)
- Updated during download and installation
- Enables real-time progress display

### Rollback Rules (BR-OTA-031 to BR-OTA-040)

**BR-OTA-031: Rollback Trigger Types**
- MUST be one of: manual, failure_rate, health_check, timeout, error_threshold
- Manual: Administrator-initiated
- Others: System-initiated based on conditions

**BR-OTA-032: Rollback Version Validation**
- to_version MUST be a previously installed firmware
- Ideally from update history
- Cannot rollback to arbitrary version

**BR-OTA-033: Rollback Priority**
- Rollback operations have priority=critical
- Processed before regular updates
- Minimizes device downtime

**BR-OTA-034: Campaign Rollback Scope**
- Campaign rollback affects all updated devices
- Pending updates cancelled
- In-progress updates allowed to complete first

**BR-OTA-035: Rollback Reason Documentation**
- reason field MUST be provided
- Stored for audit and analysis
- Helps identify recurring issues

### Statistics Rules (BR-OTA-041 to BR-OTA-045)

**BR-OTA-041: Success Rate Calculation**
- success_rate = (completed_updates / total_finished_updates) * 100
- Only completed and failed updates counted
- Pending/in-progress excluded

**BR-OTA-042: Campaign Progress Calculation**
- Progress counters: pending, in_progress, completed, failed, cancelled
- Total = sum of all counters
- Used for dashboard displays

**BR-OTA-043: Time-Based Statistics**
- last_24h metrics filtered by created_at
- Rolling window calculation
- Updated on each query (not cached)

**BR-OTA-044: Average Update Time**
- Calculated from completed updates only
- Time from started_at to completed_at
- Reported in minutes

**BR-OTA-045: Data Transfer Tracking**
- total_data_transferred: Sum of firmware file_size for completed updates
- Used for bandwidth planning
- Reported in bytes

### Event Publishing Rules (BR-EVT-001 to BR-EVT-005)

**BR-EVT-001: Event Publishing on Mutations**
- All firmware uploads publish firmware.uploaded
- All campaign creations publish campaign.created
- All campaign starts publish campaign.started

**BR-EVT-002: Event Publishing Failures**
- Event publishing failures logged but don't block operations
- Try-catch around all publish calls
- Operation succeeds even if event fails

**BR-EVT-003: Event Payload Completeness**
- Events include all fields needed by consumers
- Timestamps in ISO 8601 format
- IDs allow event correlation

**BR-EVT-004: Event Ordering**
- No strict ordering guaranteed
- Consumers handle out-of-order events
- Idempotent event processing

**BR-EVT-005: Event Subscription Patterns**
- Pattern format: `{source_service}.{entity}.{action}`
- Example: `device_service.device.deleted`
- Wildcard support for batch subscriptions

### Data Consistency Rules (BR-CON-001 to BR-CON-005)

**BR-CON-001: Atomic Firmware Creation**
- Firmware record created in single PostgreSQL transaction
- Storage upload completes before database write
- Rollback on any failure

**BR-CON-002: Atomic Campaign Creation**
- Campaign and initial device updates created atomically
- No partial campaign states
- Transaction rollback on failure

**BR-CON-003: Update Status Transitions**
- Status changes atomic with timestamp updates
- Concurrent updates handled with optimistic locking
- Last-write-wins for status conflicts

**BR-CON-004: Soft Delete for Audit**
- Firmware and campaign records never hard deleted
- Status set to deprecated/cancelled
- Historical data preserved for compliance

**BR-CON-005: Cross-Service Consistency**
- Device validation eventual consistency
- Device deletion handled via events
- Orphan cleanup via scheduled jobs

---

## OTA Service in the Ecosystem

### Upstream Dependencies

- **Device Service**: Device validation and firmware version tracking
- **Storage Service**: Firmware binary storage (MinIO/S3)
- **Auth Service**: User authentication and authorization
- **Notification Service**: Update notifications (future)
- **PostgreSQL gRPC Service**: Persistent storage for metadata
- **NATS Event Bus**: Event publishing infrastructure
- **Consul**: Service discovery and health checks

### Downstream Consumers

- **Device Service**: Firmware version updates, compatibility checks
- **Telemetry Service**: Update metrics and monitoring
- **Audit Service**: Compliance logging of all operations
- **Notification Service**: User and admin notifications
- **Dashboard**: Real-time update progress visualization

### Integration Patterns

- **Synchronous REST**: CRUD operations via FastAPI endpoints
- **Asynchronous Events**: NATS for real-time updates
- **Service Discovery**: Consul for dynamic service location
- **Protocol Buffers**: PostgreSQL gRPC communication
- **Health Checks**: `/health` and `/health/detailed` endpoints

### Dependency Injection

- **Repository Pattern**: OTARepository for data access
- **Protocol Interfaces**: OTAServiceProtocol, OTARepositoryProtocol
- **Factory Pattern**: create_ota_service() for production instances
- **Client Injection**: DeviceClient, StorageClient, NotificationClient

---

## Success Metrics

### Firmware Quality Metrics

- **Upload Success Rate**: Successful uploads / total attempts (target: >99%)
- **Checksum Validation Rate**: Checksum matches / total validations (target: 100%)
- **Storage Success Rate**: Successful storage operations (target: >99.9%)

### Update Performance Metrics

- **Campaign Completion Rate**: Completed campaigns / started campaigns (target: >95%)
- **Device Update Success Rate**: Successful updates / total updates (target: >98%)
- **Average Update Duration**: Mean time from scheduled to completed (target: <30 min)
- **Rollback Rate**: Rollback operations / total campaigns (target: <5%)

### Availability Metrics

- **Service Uptime**: OTA service availability (target: 99.9%)
- **Database Connectivity**: PostgreSQL connection success (target: 99.99%)
- **Event Publishing Success**: Events successfully published (target: >99.5%)
- **Storage Availability**: MinIO/S3 availability (target: 99.95%)

### Business Metrics

- **Devices on Latest Firmware**: % of fleet on current version
- **Security Patch Adoption**: Time to 90% adoption of security updates
- **Fleet Update Velocity**: Devices updated per hour during campaigns
- **Mean Time to Rollback**: Average rollback execution time

---

## Glossary

**Campaign**: Orchestrated deployment of firmware to multiple devices
**Canary Deployment**: Releasing to small subset before full rollout
**Checksum**: Hash value used to verify file integrity
**Device Update**: Individual update operation for single device
**Failure Threshold**: Percentage of failures triggering rollback
**Firmware**: Software binary for device updates
**FOTA**: Firmware Over-The-Air (firmware updates)
**OTA**: Over-The-Air updates (wireless software delivery)
**Rollback**: Reverting to previous firmware version
**Rollout Percentage**: Portion of target devices to update
**Staged Deployment**: Gradual rollout in controlled phases
**Event Bus**: NATS messaging system for asynchronous events
**Repository Pattern**: Data access abstraction layer
**Protocol Interface**: Abstract contract for dependency injection

---

**Document Version**: 1.0
**Last Updated**: 2025-12-18
**Maintained By**: OTA Service Team
