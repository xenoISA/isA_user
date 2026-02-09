# OTA Service Logic Contract

This document defines the complete business logic contract for the OTA Service, including business rules, state machines, validation logic, edge case handling, data consistency rules, integration contracts, and error handling. All rules are designed to be testable and enforceable through code.

---

## Business Rules

### Firmware Management Rules (BR-FW-001 to BR-FW-012)

#### BR-FW-001: Firmware Name Validation
- **Given**: User uploads firmware
- **When**: name field is provided
- **Then**: name MUST be 1-200 characters, non-empty
- **Validation**: On create operations
- **Error**: ValidationError("Firmware name must be 1-200 characters")
- **Example**:
  - Valid: "SmartFrame Firmware v2.0" (24 chars)
  - Invalid: "" (empty), "x" * 201 (too long)

#### BR-FW-002: Firmware Version Format
- **Given**: User uploads firmware
- **When**: version field is provided
- **Then**: Version MUST match semantic versioning pattern (X.Y.Z)
- **Validation**: Regex pattern `^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)?$`
- **Error**: ValidationError("Version must follow semantic versioning (e.g., 1.0.0)")
- **Example**:
  - Valid: "1.0.0", "2.1.3", "3.0.0-beta"
  - Invalid: "1.0", "v1.0.0", "1.0.0.0"

#### BR-FW-003: Firmware Unique Constraint
- **Given**: User uploads firmware
- **When**: Same name, version, and device_model combination exists
- **Then**: System MUST reject with DuplicateError
- **Scope**: Unique within name:version:device_model
- **Error**: DuplicateError("Firmware with this name, version, and device model already exists")

#### BR-FW-004: File Size Validation
- **Given**: User uploads firmware binary
- **When**: file_content is provided
- **Then**: File size MUST NOT exceed 500MB (524,288,000 bytes)
- **Validation**: Before processing upload
- **Error**: ValidationError("File size exceeds maximum limit of 500MB")

#### BR-FW-005: Checksum Verification
- **Given**: User uploads firmware with checksum
- **When**: checksum_md5 or checksum_sha256 is provided
- **Then**: System MUST verify checksum matches file content
- **Validation**: Compare provided checksum with calculated checksum
- **Error**: ValidationError("MD5 checksum mismatch"), ValidationError("SHA256 checksum mismatch")

#### BR-FW-006: Supported File Formats
- **Given**: User uploads firmware file
- **When**: Filename extension is extracted
- **Then**: Extension MUST be in supported formats list
- **Supported**: .bin, .hex, .elf, .tar.gz, .zip
- **Error**: ValidationError("Unsupported firmware file format")

#### BR-FW-007: Device Model Validation
- **Given**: User uploads firmware
- **When**: device_model is provided
- **Then**: device_model MUST be 1-100 characters
- **Validation**: On create operations
- **Error**: ValidationError("Device model must be 1-100 characters")

#### BR-FW-008: Hardware Version Compatibility
- **Given**: User uploads firmware with hardware version constraints
- **When**: min_hardware_version and max_hardware_version are provided
- **Then**: min MUST be less than or equal to max
- **Validation**: Version comparison check
- **Error**: ValidationError("Minimum hardware version cannot exceed maximum")

#### BR-FW-009: Beta Firmware Restrictions
- **Given**: User uploads beta firmware (is_beta=true)
- **When**: Firmware is used in campaign
- **Then**: Campaign MUST explicitly allow beta firmware
- **Validation**: Check campaign configuration
- **Error**: ValidationError("Beta firmware requires explicit campaign approval")

#### BR-FW-010: Security Update Priority
- **Given**: Firmware marked as security update (is_security_update=true)
- **When**: Campaign or device update is created
- **Then**: System SHOULD prioritize security updates
- **Behavior**: Auto-elevate priority to HIGH if NORMAL or below
- **Event**: Log security update prioritization

#### BR-FW-011: Firmware Download Tracking
- **Given**: Device downloads firmware
- **When**: Download completes successfully
- **Then**: System MUST increment download_count
- **Tracking**: Atomic increment per download
- **Statistics**: Used for success_rate calculation

#### BR-FW-012: Firmware Soft Delete
- **Given**: Admin deletes firmware
- **When**: Firmware is referenced by active campaigns
- **Then**: System MUST soft-delete (mark deprecated)
- **Behavior**: Deprecated firmware excluded from new campaigns
- **Recovery**: Admin can restore within retention period


### Campaign Management Rules (BR-CAM-001 to BR-CAM-012)

#### BR-CAM-001: Campaign Name Validation
- **Given**: User creates update campaign
- **When**: name field is provided
- **Then**: name MUST be 1-200 characters, non-empty
- **Validation**: On create, update operations
- **Error**: ValidationError("Campaign name must be 1-200 characters")

#### BR-CAM-002: Firmware Reference Validation
- **Given**: User creates campaign
- **When**: firmware_id is provided
- **Then**: Firmware MUST exist and be active (not deprecated)
- **Validation**: Lookup firmware before campaign creation
- **Error**: NotFoundError("Firmware not found"), ValidationError("Cannot use deprecated firmware")

#### BR-CAM-003: Target Device Requirements
- **Given**: User creates campaign
- **When**: No target devices specified
- **Then**: At least one of target_devices, target_groups, or target_filters required
- **Validation**: Check non-empty targeting
- **Error**: ValidationError("Campaign must specify target devices, groups, or filters")

#### BR-CAM-004: Deployment Strategy Validation
- **Given**: User creates campaign
- **When**: deployment_strategy is provided
- **Then**: Strategy MUST be valid enum value
- **Valid**: immediate, scheduled, staged, canary, blue_green
- **Error**: ValidationError("Invalid deployment strategy")

#### BR-CAM-005: Rollout Percentage Constraints
- **Given**: User creates staged/canary campaign
- **When**: rollout_percentage is provided
- **Then**: Value MUST be between 1 and 100 inclusive
- **Validation**: Range check on percentage
- **Error**: ValidationError("Rollout percentage must be between 1 and 100")

#### BR-CAM-006: Batch Size Limits
- **Given**: User creates campaign
- **When**: batch_size is provided
- **Then**: Value MUST be between 1 and 500 inclusive
- **Validation**: Range check on batch_size
- **Error**: ValidationError("Batch size must be between 1 and 500")

#### BR-CAM-007: Concurrent Update Limits
- **Given**: User creates campaign
- **When**: max_concurrent_updates is provided
- **Then**: Value MUST be between 1 and 1000 inclusive
- **Validation**: Range check on concurrent limit
- **Error**: ValidationError("Max concurrent updates must be between 1 and 1000")

#### BR-CAM-008: Schedule Validation
- **Given**: User creates scheduled campaign
- **When**: scheduled_start and scheduled_end are provided
- **Then**: scheduled_start MUST be before scheduled_end
- **Then**: scheduled_start MUST be in the future
- **Error**: ValidationError("Scheduled start must be before end"), ValidationError("Scheduled start must be in the future")

#### BR-CAM-009: Timeout Configuration
- **Given**: User creates campaign
- **When**: timeout_minutes is provided
- **Then**: Value MUST be between 5 and 1440 (24 hours) inclusive
- **Validation**: Range check on timeout
- **Error**: ValidationError("Timeout must be between 5 and 1440 minutes")

#### BR-CAM-010: Failure Threshold Configuration
- **Given**: User creates campaign with auto_rollback=true
- **When**: failure_threshold_percent is provided
- **Then**: Value MUST be between 1 and 100 inclusive
- **Default**: 20% failure threshold
- **Error**: ValidationError("Failure threshold must be between 1 and 100")

#### BR-CAM-011: Campaign Approval Requirements
- **Given**: Campaign has requires_approval=true
- **When**: Start campaign is requested
- **Then**: Campaign MUST be approved before starting
- **Validation**: Check approved=true before start
- **Error**: StateTransitionError("Campaign requires approval before starting")

#### BR-CAM-012: Campaign Immutability After Start
- **Given**: Campaign is started (status=in_progress)
- **When**: Update campaign is requested
- **Then**: Only specific fields can be modified (paused, cancelled)
- **Immutable**: firmware_id, target_devices, deployment_strategy
- **Error**: ValidationError("Cannot modify started campaign")


### Device Update Rules (BR-DEV-001 to BR-DEV-010)

#### BR-DEV-001: Device Existence Validation
- **Given**: User requests device update
- **When**: device_id is provided
- **Then**: Device MUST exist in Device Service
- **Validation**: Call Device Service to verify
- **Error**: NotFoundError("Device not found")

#### BR-DEV-002: Firmware Compatibility Check
- **Given**: Device update is requested
- **When**: Firmware has hardware version constraints
- **Then**: Device hardware version MUST be within range
- **Validation**: Check device.hardware_version against firmware constraints
- **Error**: ValidationError("Firmware not compatible with device hardware version")

#### BR-DEV-003: Priority Enforcement
- **Given**: Device update is created
- **When**: priority is provided
- **Then**: Priority MUST be valid enum value
- **Valid**: low, normal, high, critical, emergency
- **Default**: normal
- **Error**: ValidationError("Invalid priority level")

#### BR-DEV-004: Update Uniqueness
- **Given**: Device update is requested
- **When**: Device has pending/in_progress update for same firmware
- **Then**: System MUST reject duplicate update
- **Validation**: Check existing updates for device+firmware
- **Error**: DuplicateError("Device already has pending update for this firmware")

#### BR-DEV-005: Force Update Bypass
- **Given**: User requests device update with force_update=true
- **When**: Device already has same or newer firmware
- **Then**: System MUST allow update (skip version check)
- **Behavior**: Bypass normal version comparison
- **Logging**: Log force update with reason

#### BR-DEV-006: Retry Limits
- **Given**: Device update fails
- **When**: retry_count < max_retries
- **Then**: System MAY retry update automatically
- **Default**: max_retries=3
- **Backoff**: Exponential backoff (1min, 2min, 4min)
- **Error**: After max retries: UpdateError("Maximum retry attempts exceeded")

#### BR-DEV-007: Timeout Handling
- **Given**: Device update is in progress
- **When**: timeout_at is reached
- **Then**: System MUST mark update as FAILED with timeout error
- **Validation**: Periodic timeout check
- **Error**: error_code="TIMEOUT", error_message="Update timed out"

#### BR-DEV-008: Download Progress Tracking
- **Given**: Device is downloading firmware
- **When**: Progress updates are received
- **Then**: download_progress MUST be between 0.0 and 100.0
- **Validation**: Range check on progress values
- **Update**: progress_percentage = weighted average of phases

#### BR-DEV-009: Checksum Verification Requirement
- **Given**: Device downloads firmware
- **When**: Download completes
- **Then**: Device MUST verify checksum before installation
- **Validation**: Compare against firmware.checksum_sha256
- **Error**: UpdateError("Checksum verification failed")

#### BR-DEV-010: Signature Verification
- **Given**: Device downloads firmware
- **When**: Firmware has digital signature
- **Then**: Device MUST verify signature before installation
- **Validation**: Cryptographic signature verification
- **Error**: UpdateError("Signature verification failed")


### Rollback Rules (BR-RB-001 to BR-RB-008)

#### BR-RB-001: Manual Rollback Authorization
- **Given**: User requests manual rollback
- **When**: User is device owner or admin
- **Then**: System MUST allow rollback
- **Authorization**: Check user permissions
- **Error**: AuthorizationError("Unauthorized to initiate rollback")

#### BR-RB-002: Auto-Rollback Trigger - Failure Rate
- **Given**: Campaign has auto_rollback=true
- **When**: Failed devices percentage >= failure_threshold_percent
- **Then**: System MUST automatically initiate rollback
- **Calculation**: (failed_devices / total_devices) * 100
- **Event**: Publish rollback.initiated event

#### BR-RB-003: Auto-Rollback Trigger - Health Check
- **Given**: Device update completes
- **When**: Post-update health check fails
- **Then**: System MAY initiate rollback for device
- **Condition**: rollback_triggers contains "health_check"
- **Event**: Publish rollback.initiated event

#### BR-RB-004: Auto-Rollback Trigger - Timeout
- **Given**: Device update times out
- **When**: rollback_triggers contains "timeout"
- **Then**: System MAY initiate rollback for device
- **Behavior**: Restore previous firmware version
- **Event**: Publish rollback.initiated event

#### BR-RB-005: Rollback Version Validation
- **Given**: Rollback is requested
- **When**: to_version is provided
- **Then**: to_version MUST exist in device update history
- **Validation**: Check device has previously had that version
- **Error**: ValidationError("Cannot rollback to version not in device history")

#### BR-RB-006: Campaign-Wide Rollback
- **Given**: Campaign rollback is initiated
- **When**: device_id is null/empty
- **Then**: System MUST rollback all affected devices in campaign
- **Behavior**: Parallel rollback with batch processing
- **Tracking**: Individual device rollback status

#### BR-RB-007: Rollback State Tracking
- **Given**: Rollback is initiated
- **When**: Rollback process runs
- **Then**: System MUST track rollback status (in_progress, completed, failed)
- **Fields**: rollback_id, status, started_at, completed_at, success
- **Event**: Publish rollback.completed or rollback.failed event

#### BR-RB-008: Rollback Reason Documentation
- **Given**: Rollback is initiated
- **When**: reason is provided
- **Then**: System MUST store reason for audit purposes
- **Required**: reason field mandatory
- **Audit**: Include in rollback_logs table


### State Transition Rules (BR-STATE-001 to BR-STATE-008)

#### BR-STATE-001: Campaign Status Transitions
- **Given**: Campaign status change requested
- **When**: Current status = X, target status = Y
- **Then**: Transition MUST be in allowed transitions
- **Allowed**:
  - CREATED -> SCHEDULED (on schedule)
  - CREATED -> IN_PROGRESS (immediate start)
  - CREATED -> CANCELLED (on cancel)
  - SCHEDULED -> IN_PROGRESS (on start time)
  - SCHEDULED -> CANCELLED (on cancel)
  - IN_PROGRESS -> COMPLETED (all devices done)
  - IN_PROGRESS -> FAILED (threshold exceeded)
  - IN_PROGRESS -> ROLLBACK (rollback triggered)
  - IN_PROGRESS -> CANCELLED (on cancel)
- **Error**: StateTransitionError("Cannot transition campaign from X to Y")

#### BR-STATE-002: Device Update Status Transitions
- **Given**: Device update status change requested
- **When**: Current status = X, target status = Y
- **Then**: Transition MUST follow update lifecycle
- **Allowed**:
  - CREATED -> SCHEDULED (on schedule)
  - SCHEDULED -> IN_PROGRESS (on start)
  - SCHEDULED -> CANCELLED (on cancel)
  - IN_PROGRESS -> DOWNLOADING (download started)
  - DOWNLOADING -> VERIFYING (download complete)
  - VERIFYING -> INSTALLING (verification passed)
  - INSTALLING -> REBOOTING (installation complete)
  - REBOOTING -> COMPLETED (reboot success)
  - * -> FAILED (on error at any stage)
  - * -> CANCELLED (on cancel at non-terminal stage)
  - FAILED -> SCHEDULED (on retry)
- **Error**: StateTransitionError("Cannot transition update from X to Y")

#### BR-STATE-003: Terminal State Protection
- **Given**: Entity in terminal state
- **When**: Any status change requested
- **Then**: System MUST reject transition
- **Terminal States**: COMPLETED, CANCELLED (for updates)
- **Error**: StateTransitionError("Cannot modify completed/cancelled entity")

#### BR-STATE-004: Status Timestamps
- **Given**: Status change occurs
- **When**: Transition is valid
- **Then**: System MUST update relevant timestamp
- **Timestamps**:
  - started_at: On transition to IN_PROGRESS
  - completed_at: On transition to COMPLETED/FAILED/CANCELLED
  - updated_at: On any modification

#### BR-STATE-005: Progress Phase Mapping
- **Given**: Device update status changes
- **When**: Status is IN_PROGRESS or beyond
- **Then**: current_phase MUST reflect actual phase
- **Phases**: scheduled, downloading, verifying, installing, rebooting, completed, failed
- **Update**: Set current_phase with status change

#### BR-STATE-006: Campaign Progress Counters
- **Given**: Device update status changes
- **When**: Update belongs to campaign
- **Then**: Campaign counters MUST be updated atomically
- **Counters**: pending_devices, in_progress_devices, completed_devices, failed_devices, cancelled_devices
- **Consistency**: Sum of counters = total_devices

#### BR-STATE-007: Rollback State Transitions
- **Given**: Rollback status change requested
- **When**: Current status = X, target status = Y
- **Then**: Transition MUST follow rollback lifecycle
- **Allowed**:
  - IN_PROGRESS -> COMPLETED (success)
  - IN_PROGRESS -> FAILED (error)
- **Error**: StateTransitionError("Cannot transition rollback from X to Y")

#### BR-STATE-008: Concurrent Campaign Limits
- **Given**: User starts new campaign
- **When**: User already has active campaigns
- **Then**: System MUST enforce concurrent campaign limit
- **Limit**: 5 active campaigns per organization
- **Error**: ValidationError("Maximum concurrent campaigns exceeded")


### Event Rules (BR-EVT-001 to BR-EVT-006)

#### BR-EVT-001: Firmware Upload Event
- **Given**: Firmware uploads successfully
- **When**: Database transaction commits
- **Then**: System MUST publish firmware.uploaded event
- **Payload**: firmware_id, name, version, device_model, file_size, is_security_update, uploaded_by
- **Timing**: After commit, before response

#### BR-EVT-002: Campaign Created Event
- **Given**: Campaign creates successfully
- **When**: Database transaction commits
- **Then**: System MUST publish campaign.created event
- **Payload**: campaign_id, name, firmware_id, firmware_version, target_device_count, deployment_strategy, priority, created_by
- **Timing**: After commit, before response

#### BR-EVT-003: Campaign Started Event
- **Given**: Campaign starts
- **When**: Status transitions to IN_PROGRESS
- **Then**: System MUST publish campaign.started event
- **Payload**: campaign_id, name, firmware_id, firmware_version, target_device_count
- **Timing**: After status update

#### BR-EVT-004: Update Cancelled Event
- **Given**: Device update is cancelled
- **When**: Status transitions to CANCELLED
- **Then**: System MUST publish update.cancelled event
- **Payload**: update_id, device_id, firmware_id, firmware_version, campaign_id
- **Timing**: After status update

#### BR-EVT-005: Rollback Initiated Event
- **Given**: Rollback is started
- **When**: Rollback record is created
- **Then**: System MUST publish rollback.initiated event
- **Payload**: rollback_id, device_id, from_version, to_version, trigger
- **Timing**: After creation

#### BR-EVT-006: Event Idempotency
- **Given**: Event handler receives event
- **When**: Same event_id processed before
- **Then**: Handler MUST skip processing
- **Implementation**: Store processed event_ids with TTL
- **TTL**: 7 days


### Integration Rules (BR-INT-001 to BR-INT-005)

#### BR-INT-001: Device Service Validation
- **Given**: Device update is requested
- **When**: device_id is provided
- **Then**: System MUST verify device exists via Device Service
- **Check**: GET /api/v1/devices/{device_id}
- **Error**: NotFoundError("Device not found")

#### BR-INT-002: Storage Service Integration
- **Given**: Firmware binary is uploaded
- **When**: File content is provided
- **Then**: System MUST store in Storage Service (MinIO/S3)
- **Fallback**: Local storage URL if Storage Service unavailable
- **Metadata**: version, device_model, checksums

#### BR-INT-003: Notification Service Integration
- **Given**: Campaign has notification settings enabled
- **When**: notify_on_start/notify_on_complete/notify_on_failure is true
- **Then**: System MUST send notification via Notification Service
- **Channels**: notification_channels list
- **Events**: Campaign start, completion, failure

#### BR-INT-004: Firmware Compatibility Check
- **Given**: Device update is requested
- **When**: Firmware has hardware constraints
- **Then**: System SHOULD verify compatibility via Device Service
- **Check**: device.hardware_version within firmware range
- **Graceful**: Warning only if Device Service unavailable

#### BR-INT-005: Device Firmware Version Query
- **Given**: Device update is created
- **When**: from_version needs to be populated
- **Then**: System SHOULD query Device Service for current version
- **Check**: GET device firmware version
- **Fallback**: null if unavailable


### Authorization Rules (BR-AUTH-001 to BR-AUTH-004)

#### BR-AUTH-001: Firmware Upload Authorization
- **Given**: User uploads firmware
- **When**: User has admin or firmware_manager role
- **Then**: Grant upload permission
- **Check**: user.roles contains "admin" or "firmware_manager"
- **Error**: AuthorizationError("Unauthorized to upload firmware")

#### BR-AUTH-002: Campaign Creation Authorization
- **Given**: User creates campaign
- **When**: User owns target devices or has organization admin role
- **Then**: Grant creation permission
- **Check**: user.org_id matches or user.roles contains "admin"
- **Error**: AuthorizationError("Unauthorized to create campaign")

#### BR-AUTH-003: Device Update Authorization
- **Given**: User requests device update
- **When**: User is device owner or family member with permissions
- **Then**: Grant update permission
- **Check**: device.user_id == user_id OR family sharing check
- **Error**: AuthorizationError("Unauthorized to update device")

#### BR-AUTH-004: Rollback Authorization
- **Given**: User initiates rollback
- **When**: User is device owner or admin
- **Then**: Grant rollback permission
- **Check**: Ownership or admin role
- **Error**: AuthorizationError("Unauthorized to initiate rollback")

---

## State Machines

### 1. Update Campaign Lifecycle State Machine

```
                         ┌─────────────┐
                         │   CREATED   │
                         └──────┬──────┘
                                │
               ┌────────────────┼────────────────┐
               │ schedule()     │ start()        │ cancel()
               ▼                ▼                ▼
        ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
        │  SCHEDULED  │  │ IN_PROGRESS │  │  CANCELLED  │
        └──────┬──────┘  └──────┬──────┘  └─────────────┘
               │                │
               │ start_time     │
               ▼                │
        ┌─────────────┐         │
        │ IN_PROGRESS │◄────────┘
        └──────┬──────┘
               │
    ┌──────────┼──────────┬───────────────┐
    │ all_done │ threshold│ rollback      │ cancel()
    ▼          ▼          ▼               ▼
┌─────────┐ ┌──────┐ ┌──────────┐ ┌─────────────┐
│COMPLETED│ │FAILED│ │ ROLLBACK │ │  CANCELLED  │
└─────────┘ └──────┘ └──────────┘ └─────────────┘
```

**States**:
| State | Description | Allowed Operations |
|-------|-------------|-------------------|
| CREATED | Campaign created, not yet scheduled/started | schedule, start, cancel, update |
| SCHEDULED | Campaign scheduled for future start | start, cancel, update |
| IN_PROGRESS | Campaign actively updating devices | pause, cancel, monitor |
| COMPLETED | All devices successfully updated | archive, report |
| FAILED | Failure threshold exceeded | retry, rollback, archive |
| ROLLBACK | Rollback in progress | monitor |
| CANCELLED | Campaign cancelled by user | archive |

**Transitions**:
| From | To | Trigger | Conditions | Event |
|------|-----|---------|------------|-------|
| CREATED | SCHEDULED | schedule() | scheduled_start set | campaign.scheduled |
| CREATED | IN_PROGRESS | start() | No approval required OR approved=true | campaign.started |
| CREATED | CANCELLED | cancel() | None | campaign.cancelled |
| SCHEDULED | IN_PROGRESS | scheduled_start reached | Current time >= scheduled_start | campaign.started |
| SCHEDULED | CANCELLED | cancel() | None | campaign.cancelled |
| IN_PROGRESS | COMPLETED | all devices done | completed_devices + cancelled_devices == total_devices | campaign.completed |
| IN_PROGRESS | FAILED | threshold exceeded | (failed_devices / total_devices) * 100 >= failure_threshold_percent | campaign.failed |
| IN_PROGRESS | ROLLBACK | rollback triggered | Auto or manual rollback | campaign.rollback_started |
| IN_PROGRESS | CANCELLED | cancel() | None | campaign.cancelled |

**Invariants**:
1. Terminal states (COMPLETED, FAILED, CANCELLED) cannot transition
2. Campaign progress counters sum to total_devices
3. All state changes emit events
4. Timestamps (actual_start, actual_end) recorded on transitions


### 2. Device Update Lifecycle State Machine

```
┌─────────────┐
│   CREATED   │
└──────┬──────┘
       │ schedule()
       ▼
┌─────────────┐     ┌─────────────┐
│  SCHEDULED  │────►│  CANCELLED  │
└──────┬──────┘     └─────────────┘
       │ start()           ▲
       ▼                   │ cancel()
┌─────────────┐            │
│ IN_PROGRESS │────────────┤
└──────┬──────┘            │
       │                   │
       ▼                   │
┌─────────────┐            │
│ DOWNLOADING │────────────┤
└──────┬──────┘            │
       │ download_complete │
       ▼                   │
┌─────────────┐            │
│  VERIFYING  │────────────┤
└──────┬──────┘            │
       │ verification_pass │
       ▼                   │
┌─────────────┐            │
│ INSTALLING  │────────────┤
└──────┬──────┘            │
       │ install_complete  │
       ▼                   │
┌─────────────┐            │
│  REBOOTING  │            │
└──────┬──────┘            │
       │ reboot_success    │
       ▼                   │
┌─────────────┐     ┌──────┴──────┐
│  COMPLETED  │     │   FAILED    │◄── error at any stage
└─────────────┘     └─────────────┘
                           │
                           │ retry() if retry_count < max_retries
                           ▼
                    ┌─────────────┐
                    │  SCHEDULED  │
                    └─────────────┘
```

**States**:
| State | Description | Progress % |
|-------|-------------|-----------|
| CREATED | Update record created | 0% |
| SCHEDULED | Update scheduled, waiting | 0% |
| IN_PROGRESS | Update process started | 5% |
| DOWNLOADING | Firmware downloading | 5-50% |
| VERIFYING | Checksum/signature verification | 50-60% |
| INSTALLING | Firmware being installed | 60-90% |
| REBOOTING | Device rebooting with new firmware | 90-95% |
| COMPLETED | Update successful | 100% |
| FAILED | Update failed | N/A |
| CANCELLED | Update cancelled | N/A |

**Phase Progress Mapping**:
```
progress_percentage = {
    "CREATED": 0.0,
    "SCHEDULED": 0.0,
    "IN_PROGRESS": 5.0,
    "DOWNLOADING": 5.0 + (download_progress * 0.45),  # 5-50%
    "VERIFYING": 55.0,
    "INSTALLING": 60.0 + (install_progress * 0.30),   # 60-90%
    "REBOOTING": 92.0,
    "COMPLETED": 100.0
}
```


### 3. Rollback Operation State Machine

```
┌─────────────┐
│  INITIATED  │
└──────┬──────┘
       │ start()
       ▼
┌─────────────┐
│ IN_PROGRESS │
└──────┬──────┘
       │
       ├─────────────────────┐
       │ success             │ error
       ▼                     ▼
┌─────────────┐       ┌──────────┐
│  COMPLETED  │       │  FAILED  │
└─────────────┘       └──────────┘
```

**States**:
- **INITIATED**: Rollback created, not yet started
- **IN_PROGRESS**: Rollback actively reverting firmware
- **COMPLETED**: Rollback succeeded, device on previous version
- **FAILED**: Rollback failed, manual intervention needed

**Invariants**:
1. success=true only if status=COMPLETED
2. error_message populated if status=FAILED
3. completed_at set on terminal states


### 4. Deployment Strategy State Machine (Canary)

```
┌─────────────────┐
│ CANARY_STARTED  │──────────────────────────────┐
└────────┬────────┘                              │
         │ deploy to canary group (5-10%)        │
         ▼                                       │
┌─────────────────┐                              │
│ CANARY_MONITOR  │──────────────────────────────┤
└────────┬────────┘                              │
         │                                       │
    ┌────┴────────────────┐                      │
    │ success             │ failure              │
    ▼                     ▼                      │
┌─────────────────┐ ┌─────────────────┐          │
│ STAGED_ROLLOUT  │ │ CANARY_ROLLBACK │          │
└────────┬────────┘ └─────────────────┘          │
         │                                       │
         │ deploy to 25%, 50%, 100%              │
         ▼                                       │
┌─────────────────┐                              │
│ FULL_DEPLOYMENT │                              │
└────────┬────────┘                              │
         │ all done                              │
         ▼                                       │
┌─────────────────┐                              │
│    COMPLETED    │◄─────────────────────────────┘
└─────────────────┘   (if rollback succeeds)
```

**Canary Configuration**:
- Initial canary: 5-10% of devices
- Monitor period: 30 minutes to 24 hours
- Success criteria: Error rate < 5%, no critical failures
- Staged rollout: 25% -> 50% -> 100%

---

## Edge Cases

### Input Validation Edge Cases

#### EC-001: Empty vs Null Firmware Name
- **Input**: name = "" vs name = null
- **Expected Behavior**:
  - Empty string: ValidationError("Firmware name cannot be empty")
  - Null/missing: ValidationError("Firmware name is required")
- **Implementation**: Separate validators for required vs non-empty

#### EC-002: Whitespace-Only Version
- **Input**: version = "   " (only spaces)
- **Expected Behavior**: ValidationError("Version cannot be whitespace only")
- **Implementation**: Strip and check length > 0, then validate format

#### EC-003: Checksum Case Sensitivity
- **Input**: checksum_md5 = "ABC123..." vs "abc123..."
- **Expected Behavior**: Accept both (case-insensitive comparison)
- **Implementation**: Normalize to lowercase before comparison

#### EC-004: Zero-Byte Firmware File
- **Input**: file_content = b"" (empty bytes)
- **Expected Behavior**: ValidationError("Firmware file cannot be empty")
- **Implementation**: Check len(file_content) > 0

#### EC-005: Maximum File Size Boundary
- **Input**: file_content = 500MB exactly
- **Expected Behavior**: Accept (500MB is the limit)
- **Input**: file_content = 500MB + 1 byte
- **Expected Behavior**: ValidationError("File size exceeds maximum limit")


### Concurrency Edge Cases

#### EC-006: Concurrent Campaign Start
- **Input**: Two simultaneous start requests for same campaign
- **Expected Behavior**: First succeeds, second returns "Campaign already started"
- **Implementation**: Database row-level locking on campaign

#### EC-007: Race Condition - Device Update While Campaign Running
- **Input**: Manual device update while device in active campaign
- **Expected Behavior**:
  - Option A: Reject manual update during campaign
  - Option B: Allow with warning, track both
- **Chosen**: Option A for consistency
- **Error**: ValidationError("Device has active campaign update")

#### EC-008: Concurrent Rollback Requests
- **Input**: Multiple rollback requests for same device
- **Expected Behavior**: First succeeds, subsequent rejected
- **Implementation**: Check for existing rollback before creating


### State Transition Edge Cases

#### EC-009: Campaign Start During Scheduled Window
- **Input**: start() called on SCHEDULED campaign after scheduled_start
- **Expected Behavior**: Idempotent - return success if already running
- **Implementation**: Check current state, return success if IN_PROGRESS

#### EC-010: Cancel Completed Update
- **Input**: cancel() called on COMPLETED update
- **Expected Behavior**: StateTransitionError("Cannot cancel completed update")
- **Implementation**: Terminal state check before transition

#### EC-011: Retry Failed Update After Max Retries
- **Input**: retry() called when retry_count >= max_retries
- **Expected Behavior**: ValidationError("Maximum retry attempts exceeded")
- **Implementation**: Check retry_count before allowing retry


### Integration Edge Cases

#### EC-012: Device Service Unavailable
- **Input**: Device Service returns 503 during update creation
- **Expected Behavior**:
  - Log warning
  - Proceed with update (graceful degradation)
  - Mark device_validated=false
- **Recovery**: Background job validates devices when service recovers

#### EC-013: Storage Service Upload Failure
- **Input**: Storage Service fails during firmware upload
- **Expected Behavior**:
  - Return local storage URL as fallback
  - Log error for admin attention
  - Set storage_type="local"
- **Recovery**: Background job retries upload to Storage Service

#### EC-014: Event Publishing Failure
- **Input**: NATS unavailable during event publish
- **Expected Behavior**:
  - Log error
  - Do NOT rollback main transaction
  - Queue event for retry
- **Recovery**: Background job republishes failed events

#### EC-015: Partial Campaign Completion
- **Input**: Some devices complete, some fail, some cancelled
- **Expected Behavior**:
  - Campaign status = COMPLETED if no failures exceed threshold
  - Campaign status = FAILED if failures exceed threshold
  - All device statuses individually tracked

---

## Data Consistency Rules

### DC-001: Firmware ID Generation
- Format: SHA-256 hash of `{name}:{version}:{device_model}` truncated to 32 chars
- Example: `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`
- Deterministic: Same inputs produce same ID
- Immutable after creation

### DC-002: Timestamp Consistency
- All timestamps stored in UTC
- created_at: Set once at creation, immutable
- updated_at: Updated on every modification
- Format: ISO 8601 with timezone
- Database: TIMESTAMP WITH TIME ZONE

### DC-003: Campaign Counter Consistency
- **Invariant**: total_devices = pending_devices + in_progress_devices + completed_devices + failed_devices + cancelled_devices
- **Enforcement**: Atomic counter updates
- **Validation**: Background job verifies counter integrity

### DC-004: Version Normalization
- All versions normalized to semantic versioning
- Leading zeros stripped: "01.02.03" -> "1.2.3"
- Pre-release suffixes preserved: "1.0.0-beta" stays as-is
- Applied: Before storage, before comparison

### DC-005: Checksum Storage
- MD5: 32 lowercase hex characters
- SHA-256: 64 lowercase hex characters
- Normalization: Convert to lowercase before storage
- Validation: Regex pattern check on input

### DC-006: Progress Percentage Precision
- Storage: DECIMAL(5,2) - allows 0.00 to 100.00
- Rounding: Round to 2 decimal places
- Clamping: Ensure 0.0 <= progress <= 100.0

### DC-007: Soft Delete Consistency
- Firmware: Marked deprecated (not physically deleted)
- Campaigns: Status = CANCELLED
- Updates: Status = CANCELLED
- Excluded from normal queries
- Included in admin/audit queries

---

## Integration Contracts

### Device Service Integration

**Purpose**: Verify device existence and compatibility

**Endpoint**: `GET /api/v1/devices/{device_id}`

**Request**:
```http
GET /api/v1/devices/dev_123456
X-Internal-Call: true
X-Correlation-ID: uuid
```

**Success Response** (200):
```json
{
  "device_id": "dev_123456",
  "name": "Living Room Frame",
  "device_type": "smart_frame",
  "status": "active",
  "hardware_version": "2.0.0",
  "firmware_version": "1.5.0",
  "user_id": "usr_abc123"
}
```

**Not Found Response** (404):
```json
{
  "error": "NotFoundError",
  "message": "Device not found"
}
```

**Error Handling**:
| Status | Action |
|--------|--------|
| 200 | Continue with update |
| 404 | Reject with "Device not found" |
| 503 | Log warning, proceed without validation |
| Timeout | Retry 3x, then proceed with warning |


### Storage Service Integration

**Purpose**: Store firmware binary files

**Endpoint**: `POST /api/v1/files/upload`

**Request**:
```http
POST /api/v1/files/upload
Content-Type: multipart/form-data
X-Internal-Call: true

file: <binary>
bucket: firmware
path: /{firmware_id}/{filename}
metadata: {"version": "1.0.0", "device_model": "SmartFrame"}
```

**Success Response** (200):
```json
{
  "file_id": "file_xyz789",
  "download_url": "https://storage.example.com/firmware/abc123/firmware_v1.0.0.bin",
  "size": 52428800,
  "checksum_md5": "d41d8cd98f00b204e9800998ecf8427e"
}
```

**Error Handling**:
| Status | Action |
|--------|--------|
| 200 | Use returned download_url |
| 503 | Fallback to local storage URL |
| 413 | Reject - file too large |


### Notification Service Integration

**Purpose**: Send campaign notifications

**Subject**: `notification.send`

**Payload**:
```json
{
  "event_type": "campaign.started",
  "recipient_type": "organization",
  "recipient_id": "org_xyz",
  "channels": ["email", "push"],
  "template": "ota_campaign_started",
  "data": {
    "campaign_name": "Security Update v2.0",
    "target_device_count": 150,
    "firmware_version": "2.0.0"
  }
}
```


### Event Publishing Contract

**Subject Pattern**: `ota.{entity}.{action}`

**Examples**:
- `ota.firmware.uploaded`
- `ota.campaign.created`
- `ota.campaign.started`
- `ota.update.cancelled`
- `ota.rollback.initiated`

**Payload Schema**:
```json
{
  "event_id": "evt_uuid",
  "event_type": "firmware.uploaded",
  "timestamp": "2025-01-15T10:30:00Z",
  "source_service": "ota_service",
  "correlation_id": "corr_uuid",
  "entity_id": "fw_abc123",
  "data": {
    "firmware_id": "fw_abc123",
    "name": "SmartFrame Firmware",
    "version": "2.0.0",
    "device_model": "SF-100",
    "file_size": 52428800,
    "is_security_update": true,
    "uploaded_by": "usr_xyz"
  }
}
```

**Guarantees**:
- At-least-once delivery
- Per-entity ordering
- Retry on consumer failure
- 7-day event retention

---

## Error Handling Contracts

### HTTP Status Code Mapping

| Error Type | HTTP Status | Error Code |
|------------|-------------|------------|
| ValidationError | 422 | VALIDATION_ERROR |
| NotFoundError | 404 | NOT_FOUND |
| DuplicateError | 409 | DUPLICATE |
| AuthorizationError | 403 | FORBIDDEN |
| AuthenticationError | 401 | UNAUTHORIZED |
| StateTransitionError | 400 | INVALID_STATE_TRANSITION |
| RateLimitError | 429 | RATE_LIMITED |
| ServiceUnavailable | 503 | SERVICE_UNAVAILABLE |
| InternalError | 500 | INTERNAL_ERROR |
| TimeoutError | 504 | GATEWAY_TIMEOUT |

### Error Response Format

```json
{
  "success": false,
  "error": "ValidationError",
  "message": "Firmware name must be 1-200 characters",
  "detail": {
    "field": "name",
    "value": "",
    "constraint": "min_length=1, max_length=200"
  },
  "status_code": 422,
  "request_id": "req_uuid"
}
```

### Validation Error Detail

```json
{
  "success": false,
  "error": "ValidationError",
  "message": "Validation failed",
  "detail": [
    {
      "loc": ["body", "name"],
      "msg": "field required",
      "type": "value_error.missing"
    },
    {
      "loc": ["body", "version"],
      "msg": "string does not match regex",
      "type": "value_error.str.regex"
    }
  ],
  "status_code": 422,
  "request_id": "req_uuid"
}
```

### State Transition Error

```json
{
  "success": false,
  "error": "StateTransitionError",
  "message": "Cannot transition campaign from COMPLETED to IN_PROGRESS",
  "detail": {
    "entity_type": "campaign",
    "entity_id": "camp_abc123",
    "current_state": "COMPLETED",
    "target_state": "IN_PROGRESS",
    "allowed_transitions": []
  },
  "status_code": 400,
  "request_id": "req_uuid"
}
```

### Not Found Error

```json
{
  "success": false,
  "error": "NotFoundError",
  "message": "Firmware not found",
  "detail": {
    "resource_type": "firmware",
    "resource_id": "fw_nonexistent"
  },
  "status_code": 404,
  "request_id": "req_uuid"
}
```

### Duplicate Error

```json
{
  "success": false,
  "error": "DuplicateError",
  "message": "Firmware with this name, version, and device model already exists",
  "detail": {
    "resource_type": "firmware",
    "conflicting_field": "name:version:device_model",
    "existing_id": "fw_existing123"
  },
  "status_code": 409,
  "request_id": "req_uuid"
}
```

---

## Validation Logic Examples

### Firmware Validation

```python
def validate_firmware_upload(request: FirmwareUploadRequest, file_content: bytes) -> ValidationResult:
    """Validate firmware upload request"""
    errors = []

    # Name validation
    if not request.name or len(request.name.strip()) == 0:
        errors.append(ValidationError("name", "Firmware name is required"))
    elif len(request.name) > 200:
        errors.append(ValidationError("name", "Firmware name max 200 characters"))

    # Version validation
    version_pattern = r'^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)?$'
    if not re.match(version_pattern, request.version):
        errors.append(ValidationError("version", "Version must follow semantic versioning"))

    # File size validation
    if len(file_content) == 0:
        errors.append(ValidationError("file", "Firmware file cannot be empty"))
    elif len(file_content) > 500 * 1024 * 1024:
        errors.append(ValidationError("file", "File size exceeds 500MB limit"))

    # Checksum validation
    if request.checksum_md5:
        actual_md5 = hashlib.md5(file_content).hexdigest()
        if actual_md5.lower() != request.checksum_md5.lower():
            errors.append(ValidationError("checksum_md5", "MD5 checksum mismatch"))

    if request.checksum_sha256:
        actual_sha256 = hashlib.sha256(file_content).hexdigest()
        if actual_sha256.lower() != request.checksum_sha256.lower():
            errors.append(ValidationError("checksum_sha256", "SHA256 checksum mismatch"))

    # Hardware version range validation
    if request.min_hardware_version and request.max_hardware_version:
        if compare_versions(request.min_hardware_version, request.max_hardware_version) > 0:
            errors.append(ValidationError("hardware_version", "Min version cannot exceed max version"))

    return ValidationResult(len(errors) == 0, errors)
```

### Campaign Validation

```python
def validate_campaign_create(request: CampaignCreateRequest) -> ValidationResult:
    """Validate campaign creation request"""
    errors = []

    # Name validation
    if not request.name or len(request.name.strip()) == 0:
        errors.append(ValidationError("name", "Campaign name is required"))
    elif len(request.name) > 200:
        errors.append(ValidationError("name", "Campaign name max 200 characters"))

    # Target validation
    if not request.target_devices and not request.target_groups and not request.target_filters:
        errors.append(ValidationError("targets", "At least one target must be specified"))

    # Schedule validation
    if request.scheduled_start and request.scheduled_end:
        if request.scheduled_start >= request.scheduled_end:
            errors.append(ValidationError("schedule", "Start must be before end"))

    if request.scheduled_start and request.scheduled_start <= datetime.utcnow():
        errors.append(ValidationError("scheduled_start", "Start time must be in the future"))

    # Range validations
    if not (1 <= request.rollout_percentage <= 100):
        errors.append(ValidationError("rollout_percentage", "Must be between 1 and 100"))

    if not (1 <= request.batch_size <= 500):
        errors.append(ValidationError("batch_size", "Must be between 1 and 500"))

    if not (5 <= request.timeout_minutes <= 1440):
        errors.append(ValidationError("timeout_minutes", "Must be between 5 and 1440"))

    return ValidationResult(len(errors) == 0, errors)
```

### State Transition Validation

```python
class CampaignStateMachine:
    """Campaign state machine with transition validation"""

    ALLOWED_TRANSITIONS = {
        UpdateStatus.CREATED: [UpdateStatus.SCHEDULED, UpdateStatus.IN_PROGRESS, UpdateStatus.CANCELLED],
        UpdateStatus.SCHEDULED: [UpdateStatus.IN_PROGRESS, UpdateStatus.CANCELLED],
        UpdateStatus.IN_PROGRESS: [UpdateStatus.COMPLETED, UpdateStatus.FAILED, UpdateStatus.ROLLBACK, UpdateStatus.CANCELLED],
        UpdateStatus.COMPLETED: [],  # Terminal
        UpdateStatus.FAILED: [],     # Terminal
        UpdateStatus.ROLLBACK: [UpdateStatus.COMPLETED, UpdateStatus.FAILED],
        UpdateStatus.CANCELLED: [],  # Terminal
    }

    def can_transition(self, current: UpdateStatus, target: UpdateStatus) -> bool:
        """Check if transition is allowed"""
        allowed = self.ALLOWED_TRANSITIONS.get(current, [])
        return target in allowed

    def transition(self, campaign: Campaign, target: UpdateStatus) -> Campaign:
        """Execute state transition with validation"""
        if not self.can_transition(campaign.status, target):
            raise StateTransitionError(
                f"Cannot transition campaign from {campaign.status.value} to {target.value}"
            )

        campaign.status = target
        campaign.updated_at = datetime.utcnow()

        # Set timestamps based on transition
        if target == UpdateStatus.IN_PROGRESS:
            campaign.actual_start = datetime.utcnow()
        elif target in [UpdateStatus.COMPLETED, UpdateStatus.FAILED, UpdateStatus.CANCELLED]:
            campaign.actual_end = datetime.utcnow()

        return campaign
```

---

This logic contract provides comprehensive coverage of all business rules, state machines, edge cases, data consistency rules, integration contracts, and error handling for the OTA Service. Each rule is designed to be independently testable and enforceable through code implementation.
