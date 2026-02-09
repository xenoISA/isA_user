# Album Service - Domain Context

## Business Taxonomy

### Core Entities

- **Album**: A collection of photos organized by user for a specific purpose (e.g., vacation, family events)
- **Album Photo**: Junction entity representing a photo's membership in an album with AI metadata
- **Album Sync Status**: Tracks synchronization state between albums and smart frame devices
- **Smart Frame**: IoT device that displays photos from synchronized albums
- **Cover Photo**: Featured photo representing the album in lists and previews

### Key Concepts

- **Photo Count**: Automatically maintained count of photos in an album
- **Auto Sync**: Setting that enables automatic synchronization to linked frames
- **Family Sharing**: Feature allowing albums to be shared with family members
- **Organization Album**: Albums owned by organizations rather than individual users
- **Display Order**: Custom ordering of photos within an album
- **Sync Version**: Incremental version number for conflict resolution during sync

### Value Objects

- **SyncStatus**: Enumeration (PENDING, IN_PROGRESS, COMPLETED, FAILED, CANCELLED)
- **AI Tags**: AI-generated descriptive tags for photos
- **AI Objects**: AI-detected objects within photos
- **AI Scenes**: AI-classified scene types (landscape, portrait, indoor, etc.)
- **Face Detection Results**: Identified faces within photos

---

## Domain Scenarios

### Scenario 1: Album Creation
- **Trigger**: User creates a new photo album
- **Flow**:
  1. User provides album name, description, and settings
  2. System validates input (name required, max lengths)
  3. System generates unique album_id
  4. Album created with default settings (auto_sync=true, photo_count=0)
  5. Album.created event published
- **Outcome**: New album available for photo organization
- **Events**: album.created

### Scenario 2: Adding Photos to Album
- **Trigger**: User adds photos to an existing album
- **Flow**:
  1. User selects photos to add (photo_ids from storage service)
  2. System verifies album exists and user has permission
  3. Photos added with metadata (display_order, added_at, added_by)
  4. Album photo_count incremented
  5. AI metadata from storage service preserved
  6. Album.photo.added event published
- **Outcome**: Photos organized in album, ready for viewing/sync
- **Events**: album.photo.added

### Scenario 3: Smart Frame Synchronization
- **Trigger**: User initiates album sync to smart frame device
- **Flow**:
  1. User selects album and target frame device
  2. System verifies album and frame access
  3. Sync status created/updated to IN_PROGRESS
  4. System begins transferring photos to frame
  5. Progress tracked (synced_photos, pending_photos, failed_photos)
  6. Album.synced event published
- **Outcome**: Album photos displayed on smart frame
- **Events**: album.synced

### Scenario 4: Family Sharing
- **Trigger**: User enables family sharing for album
- **Flow**:
  1. User toggles is_family_shared setting
  2. System generates sharing_resource_id if not present
  3. Album becomes visible to family members
  4. Album.updated event published
- **Outcome**: Album accessible to family organization members
- **Events**: album.updated

### Scenario 5: Album Deletion
- **Trigger**: User deletes an album
- **Flow**:
  1. User requests album deletion
  2. System verifies ownership
  3. All album_photos associations removed
  4. Sync status records cleaned up
  5. Album record deleted
  6. Album.deleted event published
- **Outcome**: Album and associations removed from system
- **Events**: album.deleted

### Scenario 6: Photo Removal (Event-Driven)
- **Trigger**: file.deleted event received from storage_service
- **Flow**:
  1. System receives file.deleted event
  2. Photo removed from all albums containing it
  3. Affected albums' photo_count updated
- **Outcome**: Photo references cleaned from all albums
- **Events**: Internal cleanup (no album event published)

### Scenario 7: Device Cleanup (Event-Driven)
- **Trigger**: device.deleted event received from device_service
- **Flow**:
  1. System receives device.deleted event
  2. All sync status records for frame_id removed
  3. Albums unlinked from deleted frame
- **Outcome**: Sync relationships cleaned for deleted device
- **Events**: Internal cleanup

---

## Domain Events

### Published Events

1. **album.created** (EventType.ALBUM_CREATED)
   - When: New album created
   - Data: album_id, user_id, name, organization_id, is_family_shared, auto_sync, sync_frames, timestamp
   - Consumers: notification_service, audit_service

2. **album.updated** (EventType.ALBUM_UPDATED)
   - When: Album properties modified
   - Data: album_id, user_id, updates, timestamp
   - Consumers: notification_service, audit_service

3. **album.deleted** (EventType.ALBUM_DELETED)
   - When: Album removed from system
   - Data: album_id, user_id, timestamp
   - Consumers: notification_service, storage_service, audit_service

4. **album.photo.added** (EventType.ALBUM_PHOTO_ADDED)
   - When: Photos added to album
   - Data: album_id, user_id, photo_ids, added_count, timestamp
   - Consumers: notification_service, device_service (for sync)

5. **album.photo.removed** (EventType.ALBUM_PHOTO_REMOVED)
   - When: Photos removed from album
   - Data: album_id, user_id, photo_ids, removed_count, timestamp
   - Consumers: notification_service, device_service (for sync)

6. **album.synced** (EventType.ALBUM_SYNCED)
   - When: Album sync initiated to frame
   - Data: album_id, user_id, frame_id, sync_status, total_photos, timestamp
   - Consumers: device_service, notification_service

### Subscribed Events

1. **file.uploaded.with_ai** - From storage_service
   - Purpose: Auto-add photos to albums based on AI analysis
   - Handler: AlbumEventHandler.handle_file_uploaded

2. **file.deleted** - From storage_service
   - Purpose: Remove photo from all albums when deleted
   - Handler: AlbumEventHandler.handle_file_deleted

3. **device.offline** - From device_service
   - Purpose: Update sync status for offline frames
   - Handler: AlbumEventHandler.handle_device_offline

4. **device.deleted** - From device_service
   - Purpose: Clean up sync status records
   - Handler: AlbumEventHandler.handle_device_deleted

5. **user.deleted** - From account_service
   - Purpose: Clean up all albums for deleted user
   - Handler: AlbumEventHandler.handle_user_deleted

---

## Core Concepts

### Concept 1: Album Ownership Model

Albums follow a strict ownership model:
- Each album has exactly one owner (user_id)
- Organization albums have both user_id and organization_id
- Only the owner can modify or delete the album
- Family sharing extends read access to organization members
- Shared albums maintain original ownership

### Concept 2: Photo-Album Relationship

Albums don't store photos directly:
- AlbumPhoto junction table links albums to photos
- Photos stored in storage_service (file_id references)
- Same photo can exist in multiple albums
- Deleting album doesn't delete photos
- Deleting photo removes it from all albums

### Concept 3: Smart Frame Sync Architecture

Sync follows a staged approach:
- Sync status tracks progress per album-frame pair
- IN_PROGRESS allows partial sync continuation
- Failed photos tracked separately for retry
- Sync version enables conflict detection
- MQTT used for real-time frame communication

### Concept 4: AI Metadata Integration

Photos carry AI-enriched metadata:
- ai_tags: Descriptive keywords (sunset, beach, family)
- ai_objects: Detected objects (car, dog, building)
- ai_scenes: Scene classification (outdoor, indoor, landscape)
- face_detection_results: Identified faces for grouping
- Metadata from storage_service preserved when adding to album

---

## High-Level Business Rules (30 rules)

### Album Lifecycle Rules

**BR-ALB-001: Album Name Required**
- Album MUST have a non-empty name
- Name MUST NOT exceed 255 characters
- Name MUST have at least 1 non-whitespace character

**BR-ALB-002: Album Description Length**
- Description is optional
- Description MUST NOT exceed 1000 characters

**BR-ALB-003: Unique Album ID**
- System generates unique album_id (format: album_{hex16})
- Album IDs are immutable after creation

**BR-ALB-004: Album Ownership**
- Every album MUST have exactly one user_id (owner)
- Only owner can modify or delete album
- Ownership cannot be transferred

**BR-ALB-005: Album Creation Timestamp**
- created_at set automatically on creation
- updated_at set on every modification
- Timestamps immutable externally

### Photo Management Rules

**BR-ALB-006: Photo Count Accuracy**
- photo_count MUST reflect actual count of album_photos
- System updates count after add/remove operations
- Count never negative

**BR-ALB-007: Photo Deduplication**
- Same photo_id cannot appear twice in same album
- INSERT uses ON CONFLICT DO NOTHING
- Adding existing photo silently succeeds

**BR-ALB-008: Photo Display Order**
- display_order starts at 0
- Sequential assignment on add
- Custom reordering supported

**BR-ALB-009: Featured Photo**
- is_featured flag marks featured photos
- Used for cover photo selection if no explicit cover

**BR-ALB-010: Photo Metadata Preservation**
- AI metadata preserved from storage_service
- face_detection_results stored as JSON
- Metadata can be updated independently

### Smart Frame Sync Rules

**BR-ALB-011: Sync Frame Validation**
- frame_id MUST be valid device ID
- Frame access validated via device_service
- Invalid frames rejected

**BR-ALB-012: Sync Status States**
- PENDING: Initial state, not yet started
- IN_PROGRESS: Sync actively running
- COMPLETED: All photos successfully synced
- FAILED: Sync failed with errors
- CANCELLED: User cancelled sync

**BR-ALB-013: Sync Progress Tracking**
- total_photos = album.photo_count at sync start
- synced_photos incremented on success
- failed_photos incremented on failure
- pending_photos = total - synced - failed

**BR-ALB-014: Auto Sync Setting**
- auto_sync=true enables automatic sync on photo changes
- Applies only to frames in sync_frames list
- Can be disabled per album

**BR-ALB-015: Sync Frames List**
- sync_frames array contains frame device IDs
- Empty array means no automatic sync
- Frames validated on first sync

### Family Sharing Rules

**BR-ALB-016: Family Sharing Toggle**
- is_family_shared boolean controls access
- Requires organization membership
- Creates sharing_resource_id if not exists

**BR-ALB-017: Shared Album Visibility**
- Shared albums visible to organization members
- Read-only access for non-owners
- Owner retains full control

**BR-ALB-018: Organization Albums**
- organization_id associates album with org
- Null organization_id = personal album
- Org albums have additional sharing options

### Data Integrity Rules

**BR-ALB-019: Cascade Photo Cleanup**
- Deleting album removes all album_photos entries
- Does NOT delete actual photos in storage
- Updates photo_count before deletion

**BR-ALB-020: Cascade Sync Cleanup**
- Deleting album removes sync_status records
- Orphaned sync records cleaned periodically

**BR-ALB-021: Photo Removal Cascade**
- file.deleted event triggers removal from all albums
- All containing albums' photo_count updated
- Maintains referential integrity

**BR-ALB-022: Device Removal Cleanup**
- device.deleted removes sync_status records
- Albums' sync_frames list not auto-updated
- Manual cleanup may be needed

### Pagination Rules

**BR-ALB-023: Album List Pagination**
- Default page_size: 50
- Maximum page_size: 100
- Minimum page_size: 1
- page starts at 1 (1-indexed)

**BR-ALB-024: Photo List Pagination**
- Default limit: 50
- Maximum limit: 200
- offset starts at 0

**BR-ALB-025: Sort Order**
- Albums sorted by updated_at DESC (newest first)
- Photos sorted by display_order ASC, then added_at DESC

### Query Filter Rules

**BR-ALB-026: Organization Filter**
- organization_id filter returns only org albums
- Null filter returns all user albums
- Filter ANDed with user_id

**BR-ALB-027: Family Shared Filter**
- is_family_shared filter for shared albums
- Boolean filter (true/false/null)
- Null returns all albums

### Event Rules

**BR-ALB-028: Event Publishing**
- All CRUD operations publish events
- Events include timestamp and user context
- Failed event publishing logged but not blocking

**BR-ALB-029: Event Idempotency**
- Event handlers must be idempotent
- Same event processed multiple times = same result
- Uses unique identifiers for deduplication

**BR-ALB-030: Event Ordering**
- Events processed in received order
- No cross-event dependencies guaranteed
- Handlers must be order-independent

---

## Error Handling

### Exception Types

- **AlbumNotFoundError**: Album with given ID doesn't exist or user lacks access
- **AlbumValidationError**: Invalid input data (empty name, invalid length)
- **AlbumPermissionError**: User doesn't have permission for operation
- **AlbumServiceError**: Internal service error (database, network)

### HTTP Status Mapping

| Exception | HTTP Code | Description |
|-----------|-----------|-------------|
| AlbumNotFoundError | 404 | Album not found |
| AlbumValidationError | 400 | Invalid request data |
| AlbumPermissionError | 403 | Permission denied |
| AlbumServiceError | 500 | Internal server error |

---

## Integration Points

### Dependencies

1. **storage_service**: Photo storage and AI metadata
2. **device_service**: Frame device validation
3. **account_service**: User validation (via events)
4. **organization_service**: Family/org membership

### Communication

- **Synchronous**: HTTP API for user requests
- **Asynchronous**: NATS for event publishing/subscribing
- **Real-time**: MQTT for frame sync notifications
