# Album Service Logic Contract

**Business Rules and Specifications for Album Service Testing**

All tests MUST verify these specifications. This is the SINGLE SOURCE OF TRUTH for album service behavior.

---

## Table of Contents

1. [Business Rules](#business-rules)
2. [State Machines](#state-machines)
3. [Edge Cases](#edge-cases)
4. [Data Consistency Rules](#data-consistency-rules)
5. [Integration Contracts](#integration-contracts)
6. [Error Handling Contracts](#error-handling-contracts)
7. [Performance SLAs](#performance-slas)

---

## Business Rules

### Album Creation Rules

### BR-ALB-001: Album Name Required
**Given**: Album creation request
**When**: Album is created via create_album
**Then**:
- Name must be non-empty after stripping whitespace
- Name must be 1-255 characters
- Empty string after strip → **AlbumValidationError**

**Validation Rules**:
- `name`: Required, non-empty string
- Must have at least 1 non-whitespace character
- Maximum 255 characters

**Edge Cases**:
- Empty name → **AlbumValidationError**
- Whitespace-only name → **AlbumValidationError**
- Name > 255 chars → **AlbumValidationError** (or 422 from Pydantic)

---

### BR-ALB-002: Album Description Length
**Given**: Album creation or update request with description
**When**: Description is validated
**Then**:
- Description is optional (can be None)
- Maximum length: 1000 characters
- Longer description → **AlbumValidationError**

**Validation Rules**:
- `description`: Optional string
- Max 1000 characters if provided

---

### BR-ALB-003: Unique Album ID Generation
**Given**: New album creation
**When**: Album ID is generated
**Then**:
- Format: `album_{hex16}` (album_ prefix + 16 hex chars)
- Generated using `secrets.token_hex(8)`
- IDs are immutable after creation
- Collision probability negligible

**Implementation**:
```python
album_id = f"album_{secrets.token_hex(8)}"
```

---

### BR-ALB-004: Album Ownership
**Given**: Any album operation requiring ownership
**When**: User attempts operation
**Then**:
- Every album has exactly one owner (user_id)
- Only owner can modify or delete album
- Ownership cannot be transferred
- Non-owner access → **AlbumPermissionError**

**Ownership Check**:
```python
if album.user_id != user_id:
    raise AlbumPermissionError("Only album owner can perform this operation")
```

---

### BR-ALB-005: Default Values on Creation
**Given**: New album creation
**When**: Album is created
**Then**:
- `photo_count` = 0
- `auto_sync` = true (unless specified)
- `sync_frames` = [] (empty array)
- `is_family_shared` = false (unless specified)
- `created_at` = current UTC timestamp
- `updated_at` = current UTC timestamp

**Default Values**:
```python
{
    "photo_count": 0,
    "auto_sync": True,
    "sync_frames": [],
    "is_family_shared": False,
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc)
}
```

---

### Photo Management Rules

### BR-ALB-006: Photo Count Accuracy
**Given**: Photo add or remove operation
**When**: Operation completes
**Then**:
- `photo_count` MUST reflect actual count of album_photos
- Count updated atomically after add/remove
- Count is never negative
- Count verified against actual table count

**Implementation**:
```sql
UPDATE album.albums SET photo_count = (
    SELECT COUNT(*) FROM album.album_photos WHERE album_id = $1
) WHERE album_id = $1
```

---

### BR-ALB-007: Photo Deduplication
**Given**: Add photos to album request
**When**: Photo already exists in album
**Then**:
- Same photo_id cannot appear twice in same album
- INSERT uses ON CONFLICT DO NOTHING
- Adding existing photo silently succeeds (idempotent)
- Returned added_count reflects actual new additions

**SQL**:
```sql
INSERT INTO album.album_photos (album_id, photo_id, ...)
VALUES ($1, $2, ...)
ON CONFLICT (album_id, photo_id) DO NOTHING
```

---

### BR-ALB-008: Photo Display Order
**Given**: Photos in an album
**When**: Photos are listed
**Then**:
- `display_order` starts at 0
- Sequential assignment on add (0, 1, 2, ...)
- Custom reordering supported via update
- Sort by display_order ASC, then added_at DESC

**Query Order**:
```sql
ORDER BY display_order ASC, added_at DESC
```

---

### BR-ALB-009: Featured Photo
**Given**: Photo in album
**When**: Photo is marked as featured
**Then**:
- `is_featured` flag marks featured photos
- Used for cover photo selection if no explicit cover
- Multiple photos can be featured
- Featured photos may appear first in galleries

---

### BR-ALB-010: AI Metadata Preservation
**Given**: Photo added with AI metadata
**When**: Photo is stored in album
**Then**:
- AI metadata preserved from storage_service
- `ai_tags`: Array of descriptive keywords
- `ai_objects`: Array of detected objects
- `ai_scenes`: Array of scene classifications
- `face_detection_results`: JSON object with face data
- Metadata stored in JSONB columns

**Metadata Fields**:
- `ai_tags`: ["beach", "sunset", "family"]
- `ai_objects`: ["person", "car", "dog"]
- `ai_scenes`: ["outdoor", "landscape"]
- `face_detection_results`: {"faces": [...]}

---

### Smart Frame Sync Rules

### BR-ALB-011: Frame ID Validation
**Given**: Sync request with frame_id
**When**: Sync is initiated
**Then**:
- frame_id must be non-empty string
- Frame validation may occur via device_service (future)
- Invalid frame_id currently accepted (no validation)
- Frame removal handled via device.deleted event

---

### BR-ALB-012: Sync Status States
**Given**: Album sync operation
**When**: Sync state changes
**Then**:
- **PENDING**: Initial state, not yet started
- **IN_PROGRESS**: Sync actively running
- **COMPLETED**: All photos successfully synced
- **FAILED**: Sync failed with errors
- **CANCELLED**: User cancelled sync

**Valid Transitions**:
- PENDING → IN_PROGRESS (sync started)
- IN_PROGRESS → COMPLETED (success)
- IN_PROGRESS → FAILED (errors)
- IN_PROGRESS → CANCELLED (user cancel)
- FAILED → PENDING (retry)
- Any → PENDING (resync)

---

### BR-ALB-013: Sync Progress Tracking
**Given**: Sync in progress
**When**: Progress is tracked
**Then**:
- `total_photos` = album.photo_count at sync start
- `synced_photos` incremented on success
- `failed_photos` incremented on failure
- `pending_photos` = total - synced - failed

**Invariant**:
```
synced_photos + failed_photos + pending_photos = total_photos
```

---

### BR-ALB-014: Auto Sync Setting
**Given**: Album with auto_sync enabled
**When**: Photos are added to album
**Then**:
- If `auto_sync=true` and `sync_frames` not empty
- System MAY trigger automatic sync (future feature)
- Currently: auto_sync setting stored but not enforced

---

### BR-ALB-015: Sync Frames List
**Given**: Album sync_frames array
**When**: Auto sync evaluates frames
**Then**:
- `sync_frames` contains frame device IDs
- Empty array means no automatic sync
- Frames validated on first sync attempt
- Invalid frames removed via device.deleted event

---

### Family Sharing Rules

### BR-ALB-016: Family Sharing Toggle
**Given**: Album with is_family_shared setting
**When**: Family sharing is toggled
**Then**:
- `is_family_shared` boolean controls access
- Requires organization membership to be meaningful
- Creates `sharing_resource_id` if not exists
- Organization members gain read access

---

### BR-ALB-017: Shared Album Visibility
**Given**: Album with is_family_shared=true
**When**: Organization member queries albums
**Then**:
- Shared albums visible to organization members
- Read-only access for non-owners
- Owner retains full control (CRUD)
- Currently: visibility managed at query level

---

### BR-ALB-018: Organization Albums
**Given**: Album with organization_id
**When**: Album is created or updated
**Then**:
- `organization_id` associates album with org
- Null organization_id = personal album
- Org albums have additional sharing options
- Org membership verified externally

---

### Data Integrity Rules

### BR-ALB-019: Cascade Photo Cleanup on Album Delete
**Given**: Album deletion request
**When**: Album is deleted
**Then**:
- All album_photos entries removed
- Does NOT delete actual photos in storage
- Photo files remain in storage_service
- Only junction table entries removed

**SQL Order**:
```sql
1. DELETE FROM album_sync_status WHERE album_id = $1
2. DELETE FROM album_photos WHERE album_id = $1
3. DELETE FROM albums WHERE album_id = $1
```

---

### BR-ALB-020: Cascade Sync Cleanup on Album Delete
**Given**: Album deletion request
**When**: Album is deleted
**Then**:
- All sync_status records for album removed
- Cleanup happens before album deletion
- No orphaned sync records remain

---

### BR-ALB-021: Photo Removal on File Delete (Event)
**Given**: file.deleted event from storage_service
**When**: Event handler processes event
**Then**:
- Photo removed from ALL albums containing it
- All containing albums' photo_count updated
- Handler is idempotent
- Maintains referential integrity

**Handler**:
```python
async def handle_file_deleted(event):
    photo_id = event.data.get("file_id")
    affected_albums = await repo.get_albums_containing_photo(photo_id)
    for album_id in affected_albums:
        await repo.remove_photos_from_album(album_id, [photo_id])
```

---

### BR-ALB-022: Device Removal Cleanup (Event)
**Given**: device.deleted event from device_service
**When**: Event handler processes event
**Then**:
- All sync_status records for frame_id removed
- Albums' sync_frames list NOT auto-updated
- Manual cleanup may be needed for sync_frames

---

### Pagination Rules

### BR-ALB-023: Album List Pagination
**Given**: List albums request
**When**: Pagination params provided
**Then**:
- Default page_size: 50
- Maximum page_size: 100
- Minimum page_size: 1
- page starts at 1 (1-indexed)
- Invalid page → 422 Validation Error

**Validation**:
```python
page: int = Field(1, ge=1)
page_size: int = Field(50, ge=1, le=100)
```

---

### BR-ALB-024: Photo List Pagination
**Given**: Get album photos request
**When**: Pagination params provided
**Then**:
- Default limit: 50
- Maximum limit: 200
- offset starts at 0
- Invalid limit → 422 Validation Error

**Validation**:
```python
limit: int = Field(50, ge=1, le=200)
offset: int = Field(0, ge=0)
```

---

### BR-ALB-025: Sort Order
**Given**: List or query operations
**When**: Results are returned
**Then**:
- Albums sorted by updated_at DESC (newest first)
- Photos sorted by display_order ASC, then added_at DESC

**SQL**:
```sql
-- Albums
ORDER BY updated_at DESC

-- Photos
ORDER BY display_order ASC, added_at DESC
```

---

### Query Filter Rules

### BR-ALB-026: Organization Filter
**Given**: List albums with organization_id filter
**When**: Filter is applied
**Then**:
- Returns only albums with matching organization_id
- Null filter returns all user albums
- Filter ANDed with user_id

**SQL**:
```sql
WHERE user_id = $1 AND organization_id = $2
```

---

### BR-ALB-027: Family Shared Filter
**Given**: List albums with is_family_shared filter
**When**: Filter is applied
**Then**:
- Boolean filter (true/false)
- Null filter returns all albums
- True: Only shared albums
- False: Only non-shared albums

---

### Event Rules

### BR-ALB-028: Event Publishing
**Given**: Album mutation operation
**When**: Operation succeeds
**Then**:
- All CRUD operations publish events
- Events include timestamp and user context
- Failed event publishing logged but not blocking
- Subject format: `album_service.{event_type}`

**Events**:
- `album.created` → CREATE
- `album.updated` → UPDATE
- `album.deleted` → DELETE
- `album.photo.added` → Photo add
- `album.photo.removed` → Photo remove
- `album.synced` → Sync initiated

---

### BR-ALB-029: Event Idempotency
**Given**: Same event received multiple times
**When**: Event handler processes events
**Then**:
- Event handlers must be idempotent
- Same event processed multiple times = same result
- Uses unique identifiers for deduplication
- No duplicate side effects

---

### BR-ALB-030: Event Ordering
**Given**: Multiple events in queue
**When**: Events are processed
**Then**:
- Events processed in received order
- No cross-event dependencies guaranteed
- Handlers must be order-independent
- Each handler self-contained

---

## State Machines

### Album Lifecycle State Machine

```
┌─────────────┐
│   CREATED   │ Album created
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   ACTIVE    │ Album in use
└──────┬──────┘
       │
       └────► DELETED  (user deletes album)

No soft delete - albums are permanently deleted
```

**States**:
- **CREATED**: Initial state after creation
- **ACTIVE**: Album is active and usable
- **DELETED**: Album permanently removed

**Transitions**:
- CREATE → ACTIVE (immediate)
- ACTIVE → DELETED (delete operation)

---

### Sync Status State Machine

```
┌─────────────┐
│   PENDING   │ Sync requested, not started
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ IN_PROGRESS │ Sync actively running
└──────┬──────┘
       │
       ├────► COMPLETED  (all photos synced)
       │
       ├────► FAILED     (errors occurred)
       │
       └────► CANCELLED  (user cancelled)

From FAILED/CANCELLED:
       │
       └────► PENDING    (retry/resync)
```

**States**:
- **PENDING**: Sync queued, not yet started
- **IN_PROGRESS**: Sync actively transferring photos
- **COMPLETED**: All photos synced successfully
- **FAILED**: Sync encountered errors
- **CANCELLED**: User cancelled the sync

**Valid Transitions**:
- PENDING → IN_PROGRESS (sync starts)
- IN_PROGRESS → COMPLETED (success)
- IN_PROGRESS → FAILED (errors)
- IN_PROGRESS → CANCELLED (user cancel)
- FAILED → PENDING (retry)
- CANCELLED → PENDING (resync)
- COMPLETED → PENDING (resync with new photos)

---

## Edge Cases

### Album Creation Edge Cases

### EC-ALB-001: Empty Album Name
**Scenario**: Create album with name=""
**Expected**:
- **AlbumValidationError** raised
- Error message: "Album name is required"
- No album created

---

### EC-ALB-002: Whitespace-Only Album Name
**Scenario**: Create album with name="   "
**Expected**:
- **AlbumValidationError** raised
- Error message: "Album name cannot be empty"
- No album created

---

### EC-ALB-003: Very Long Album Name
**Scenario**: Create album with name > 255 characters
**Expected**:
- **422 Validation Error** from Pydantic
- Or **AlbumValidationError** from service
- No album created

---

### Photo Management Edge Cases

### EC-ALB-004: Add Same Photo Twice
**Scenario**: Add photo_id that already exists in album
**Expected**:
- Operation succeeds (idempotent)
- added_count = 0 (no new additions)
- photo_count unchanged
- No error thrown

**Implementation**: ON CONFLICT DO NOTHING

---

### EC-ALB-005: Add Photos to Non-Existent Album
**Scenario**: Add photos to album_id that doesn't exist
**Expected**:
- **AlbumNotFoundError** raised
- Error message: "Album not found: {album_id}"
- No photos added

---

### EC-ALB-006: Add Photos Without Permission
**Scenario**: Non-owner tries to add photos
**Expected**:
- **AlbumPermissionError** raised
- Error message: "Only album owner can add photos"
- No photos added

---

### EC-ALB-007: Remove Photo Not in Album
**Scenario**: Remove photo_id that doesn't exist in album
**Expected**:
- Operation succeeds (idempotent)
- removed_count = 0
- photo_count unchanged
- No error thrown

---

### EC-ALB-008: Add 100+ Photos at Once
**Scenario**: Add more than 100 photos in single request
**Expected**:
- **422 Validation Error** from Pydantic
- max_length=100 enforced on photos array
- Request rejected before processing

---

### Sync Edge Cases

### EC-ALB-009: Sync Empty Album
**Scenario**: Initiate sync for album with 0 photos
**Expected**:
- Operation succeeds
- Sync status created
- total_photos = 0
- Status: COMPLETED (immediately)

---

### EC-ALB-010: Sync to Invalid Frame
**Scenario**: Sync to frame_id that doesn't exist
**Expected**:
- Currently: Operation succeeds (no validation)
- Sync status created
- Actual sync will fail during transfer
- Future: May validate via device_service

---

### EC-ALB-011: Multiple Concurrent Syncs to Same Frame
**Scenario**: Same album synced to same frame twice
**Expected**:
- Second sync updates existing sync_status
- UPSERT behavior on (album_id, frame_id)
- Only one sync_status record per pair
- sync_version incremented

---

### Ownership Edge Cases

### EC-ALB-012: Get Album Without Permission
**Scenario**: Non-owner tries to get non-shared album
**Expected**:
- If is_family_shared=false and user not owner
- **AlbumPermissionError** raised
- Error message: "Access denied to this album"

---

### EC-ALB-013: Update Album Without Permission
**Scenario**: Non-owner tries to update album
**Expected**:
- **AlbumPermissionError** raised
- Error message: "Only album owner can update"
- No changes made

---

### EC-ALB-014: Delete Album Without Permission
**Scenario**: Non-owner tries to delete album
**Expected**:
- **AlbumPermissionError** raised
- Error message: "Only album owner can delete"
- Album not deleted

---

## Data Consistency Rules

### Transaction Boundaries

**Rule**: Each repository method operates in its own transaction
- `create_album`: Single transaction (insert album)
- `add_photos_to_album`: Single transaction (insert photos + update count)
- `delete_album`: Single transaction (delete sync + photos + album)
- No cross-service transactions

**Implementation**:
```python
async with self.db:
    await self.db.execute(...)
```

---

### Photo Count Consistency

**Rule**: photo_count always matches actual album_photos count
- Updated atomically after add/remove operations
- Calculated from actual count, not incremented
- Prevents drift from race conditions

**Update Query**:
```sql
UPDATE album.albums SET photo_count = (
    SELECT COUNT(*) FROM album.album_photos WHERE album_id = $1
), updated_at = NOW()
WHERE album_id = $1
```

---

### Sync Status Consistency

**Rule**: Sync progress invariant must hold
```
synced_photos + failed_photos + pending_photos = total_photos
```

**Enforcement**:
- Calculated fields, not stored
- pending_photos derived: total - synced - failed
- total_photos set once at sync start

---

### Cascade Delete Ordering

**Rule**: Deletion order prevents FK violations
1. Delete sync_status records (no FK dependency)
2. Delete album_photos (FK to albums)
3. Delete albums (parent table)

**SQL Order**:
```sql
DELETE FROM album.album_sync_status WHERE album_id = $1;
DELETE FROM album.album_photos WHERE album_id = $1;
DELETE FROM album.albums WHERE album_id = $1;
```

---

## Integration Contracts

### PostgreSQL gRPC Service

**Expectations**:
- Service name: `postgres_grpc_service`
- Default host: `isa-postgres-grpc`
- Default port: `50061`
- Protocol: gRPC with AsyncPostgresClient
- Schema: `album`
- Tables: `albums`, `album_photos`, `album_sync_status`

**Connection**:
```python
self.db = AsyncPostgresClient(host=host, port=port, user_id='album_service')
```

---

### NATS Event Publishing

**Expectations**:
- Event bus provided via dependency injection
- Events published asynchronously
- Event failures logged but don't block operations
- Subject format: `album_service.{event_type}`

**Event Types Published**:
- `ALBUM_CREATED` → album.created
- `ALBUM_UPDATED` → album.updated
- `ALBUM_DELETED` → album.deleted
- `ALBUM_PHOTO_ADDED` → album.photo.added
- `ALBUM_PHOTO_REMOVED` → album.photo.removed
- `ALBUM_SYNCED` → album.synced

**Event Structure**:
```python
Event(
    event_type=EventType.ALBUM_CREATED,
    source=ServiceSource.ALBUM_SERVICE,
    data={...}
)
```

---

### NATS Event Subscriptions

**Events Consumed**:
- `events.*.file.uploaded.with_ai` - Auto-add photos (future)
- `events.*.file.deleted` - Remove photo from albums
- `events.*.device.offline` - Update sync status
- `events.*.device.deleted` - Cleanup sync records
- `events.*.user.deleted` - Delete user's albums

**Handler Pattern**:
```python
async def handle_event(event: Dict) -> None:
    event_type = event.get("event_type")
    # Route to appropriate handler
```

---

### MQTT gRPC Service

**Expectations**:
- Service for smart frame notifications
- Host: `mqtt-grpc` (via Consul)
- Port: `50053`
- Protocol: gRPC

**Topics Published**:
- `isa/frame/{frame_id}/sync` - Sync notifications
- `isa/frame/{frame_id}/photos` - Photo updates

**Message Format**:
```json
{
    "album_id": "album_xyz",
    "action": "start|update|complete|cancel",
    "data": {...},
    "timestamp": "2025-12-16T10:00:00Z"
}
```

---

### Consul Service Discovery

**Expectations**:
- Service registered at startup
- Service name: `album_service`
- Health check endpoint: `/health`
- Discovers `postgres_grpc_service` via Consul
- Discovers `mqtt-grpc` via Consul

---

## Error Handling Contracts

### AlbumNotFoundError

**When Raised**:
- `get_album`: Album ID not found
- `update_album`: Album ID not found
- `delete_album`: Album ID not found
- `add_photos_to_album`: Album ID not found
- `remove_photos_from_album`: Album ID not found
- `sync_album_to_frame`: Album ID not found

**HTTP Status**: 404 Not Found

**Response**:
```json
{
    "detail": "Album not found with album_id: album_xyz"
}
```

---

### AlbumValidationError

**When Raised**:
- Album name is empty or whitespace-only
- Album name exceeds 255 characters
- Album description exceeds 1000 characters
- Invalid sync_frames format
- Invalid request payload

**HTTP Status**: 400 Bad Request

**Response Examples**:
```json
{"detail": "Album name is required"}
{"detail": "Album name exceeds maximum length of 255 characters"}
{"detail": "Album description exceeds maximum length of 1000 characters"}
```

---

### AlbumPermissionError

**When Raised**:
- Non-owner attempts to modify album
- Non-owner attempts to delete album
- Non-owner attempts to add/remove photos
- Non-owner attempts to initiate sync
- Non-owner access to non-shared album

**HTTP Status**: 403 Forbidden

**Response**:
```json
{
    "detail": "Only album owner can perform this operation"
}
```

---

### AlbumServiceError

**When Raised**:
- Database connection failure
- gRPC service unavailable
- Unexpected internal errors

**HTTP Status**: 500 Internal Server Error

**Response**:
```json
{
    "detail": "Failed to create album: {error_message}"
}
```

---

### HTTP Status Code Mappings

| Error Type | HTTP Status | Example Scenario |
|------------|-------------|------------------|
| AlbumNotFoundError | 404 | Album ID not found |
| AlbumValidationError | 400 | Empty album name |
| AlbumPermissionError | 403 | Non-owner access |
| AlbumServiceError | 500 | Database failure |
| Pydantic ValidationError | 422 | Invalid request format |

---

## Performance SLAs

### Response Time Targets (p95)

| Operation | Target | Max Acceptable |
|-----------|--------|----------------|
| create_album | < 200ms | < 500ms |
| get_album | < 50ms | < 200ms |
| list_user_albums | < 200ms | < 500ms |
| update_album | < 100ms | < 300ms |
| delete_album | < 100ms | < 300ms |
| add_photos_to_album | < 200ms (100 photos) | < 500ms |
| remove_photos_from_album | < 200ms | < 400ms |
| get_album_photos | < 100ms (50 photos) | < 300ms |
| sync_album_to_frame | < 500ms | < 1000ms |
| get_sync_status | < 50ms | < 200ms |

### Throughput Targets

- Album creation: 100 req/s
- Album queries: 500 req/s
- Photo operations: 200 req/s
- Sync operations: 50 req/s

### Resource Limits

- Max albums per user: Unlimited
- Max photos per album: 10,000+
- Max photos per add request: 100
- Max sync_frames per album: 20
- Max page_size (albums): 100
- Max limit (photos): 200

---

## Test Coverage Requirements

All tests MUST cover:

- ✅ Happy path (BR-ALB success scenarios)
- ✅ Validation errors (400, 422)
- ✅ Not found errors (404)
- ✅ Permission errors (403)
- ✅ Photo deduplication (idempotency)
- ✅ Photo count accuracy
- ✅ Sync state transitions
- ✅ Event publishing (verify published)
- ✅ Event handlers (file.deleted, device.deleted, user.deleted)
- ✅ Edge cases (EC-ALB scenarios)
- ✅ Pagination boundaries
- ✅ Cascade delete behavior
- ✅ Performance within SLAs

---

**Version**: 1.0.0
**Last Updated**: 2025-12-16
**Owner**: Album Service Team
