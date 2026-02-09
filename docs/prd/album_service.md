# Album Service - Product Requirements Document (PRD)

## Product Overview

**Product Name**: Album Service
**Version**: 1.0.0
**Status**: Production
**Owner**: Media & Device Team
**Last Updated**: 2025-12-16

### Vision
Enable seamless photo organization and smart frame synchronization for the isA_user platform, creating a unified experience where photos can be grouped, shared, and automatically displayed on IoT smart frames.

### Mission
Provide a comprehensive album management service that allows users to create albums, organize photos with AI-enriched metadata, share with family members, and synchronize content to smart frame devices with real-time status tracking.

### Target Users
- **End Users**: Photo organization, family sharing, smart frame management
- **Mobile/Web Apps**: Album display, photo browsing, sync initiation
- **Smart Frame Devices**: Photo synchronization, display scheduling
- **Internal Services**: Storage, Device, Notification for cross-service coordination

### Key Differentiators
1. **Smart Frame Integration**: Native MQTT-based synchronization to IoT smart frames
2. **AI Metadata Preservation**: Stores AI tags, objects, scenes, and face detection from storage_service
3. **Family Sharing**: Organization-level album sharing with role-based visibility
4. **Event-Driven Architecture**: Real-time sync with storage and device services
5. **Progressive Sync**: Tracks sync progress with resume capability and failure handling

---

## Product Goals

### Primary Goals
1. **Album Organization**: Enable users to create and manage unlimited albums
2. **Photo Management**: Support efficient photo addition/removal with metadata preservation
3. **Smart Frame Sync**: <500ms sync initiation with real-time progress tracking
4. **Family Sharing**: Seamless album sharing within organization members
5. **Data Consistency**: Maintain accurate photo counts and sync status

### Secondary Goals
1. **Auto-Sync**: Automatic synchronization on photo changes for linked frames
2. **AI-Powered Discovery**: Leverage AI metadata for photo search within albums
3. **Bulk Operations**: Efficient handling of multi-photo operations
4. **Offline Resilience**: Handle device offline scenarios gracefully
5. **Cross-Device Consistency**: Same album state across all user devices

---

## Epics and User Stories

### Epic 1: Album Management

**Objective**: Enable users to create, update, and delete albums for photo organization.

#### E1-US1: Create Album
**As a** User
**I want to** create a new album with a name and description
**So that** I can organize my photos by topic or event

**Acceptance Criteria**:
- AC1: POST /api/v1/albums accepts name, description, auto_sync, sync_frames, is_family_shared
- AC2: Name required, 1-255 characters with at least 1 non-whitespace
- AC3: Description optional, max 1000 characters
- AC4: System generates unique album_id (format: album_{hex16})
- AC5: Default photo_count = 0, auto_sync = true
- AC6: Publish album.created event
- AC7: Response time <200ms

**API Reference**: `POST /api/v1/albums?user_id={user_id}`

**Example Request**:
```json
{
  "name": "Summer Vacation 2025",
  "description": "Photos from our trip to Hawaii",
  "auto_sync": true,
  "sync_frames": ["frame_001"],
  "is_family_shared": true
}
```

**Example Response**:
```json
{
  "album_id": "album_1a2b3c4d5e6f7890",
  "name": "Summer Vacation 2025",
  "description": "Photos from our trip to Hawaii",
  "user_id": "usr_abc123",
  "photo_count": 0,
  "cover_photo_id": null,
  "auto_sync": true,
  "sync_frames": ["frame_001"],
  "is_family_shared": true,
  "organization_id": null,
  "created_at": "2025-12-16T10:00:00Z",
  "updated_at": "2025-12-16T10:00:00Z"
}
```

#### E1-US2: Album Name Validation
**As a** System
**I want to** validate album names before creation
**So that** data integrity is maintained

**Acceptance Criteria**:
- AC1: Name must be 1-255 characters
- AC2: Name must contain at least 1 non-whitespace character
- AC3: Return 400 Bad Request with clear error on validation failure
- AC4: Whitespace trimmed from name

#### E1-US3: Album Default Settings
**As a** User
**I want to** have sensible defaults when creating albums
**So that** I don't need to specify every setting

**Acceptance Criteria**:
- AC1: auto_sync defaults to true
- AC2: photo_count initialized to 0
- AC3: sync_frames defaults to empty array
- AC4: is_family_shared defaults to false
- AC5: created_at and updated_at auto-generated

---

### Epic 2: Album Retrieval

**Objective**: Enable efficient album discovery and retrieval.

#### E2-US1: Get Album by ID
**As a** Mobile App
**I want to** retrieve full album details by ID
**So that** I can display album information and photos

**Acceptance Criteria**:
- AC1: GET /api/v1/albums/{album_id}?user_id={user_id} returns album
- AC2: Includes all fields: album_id, name, description, photo_count, cover_photo_id, auto_sync, sync_frames, timestamps
- AC3: Returns 404 if album not found
- AC4: Returns 403 if user lacks permission
- AC5: Response time <50ms

**API Reference**: `GET /api/v1/albums/{album_id}?user_id={user_id}`

#### E2-US2: Update Album
**As a** User
**I want to** update album name, description, or settings
**So that** I can keep my albums current

**Acceptance Criteria**:
- AC1: PUT /api/v1/albums/{album_id}?user_id={user_id} accepts partial updates
- AC2: Validates name length (1-255 chars) if provided
- AC3: Validates description length (max 1000 chars) if provided
- AC4: Updates updated_at timestamp
- AC5: Publish album.updated event
- AC6: Returns updated album
- AC7: Returns 404 if not found, 403 if no permission

**API Reference**: `PUT /api/v1/albums/{album_id}?user_id={user_id}`

**Example Request**:
```json
{
  "name": "Hawaii Vacation 2025",
  "is_family_shared": true
}
```

#### E2-US3: List User Albums
**As a** User
**I want to** see all my albums with pagination
**So that** I can browse my photo collections

**Acceptance Criteria**:
- AC1: GET /api/v1/albums?user_id={user_id} with pagination params
- AC2: page_size: 1-100 (default: 50)
- AC3: page: 1+ (default: 1)
- AC4: Filter by organization_id (optional)
- AC5: Filter by is_family_shared (optional)
- AC6: Results sorted by updated_at DESC
- AC7: Returns albums array with pagination metadata
- AC8: Response time <200ms

**API Reference**: `GET /api/v1/albums?user_id={user_id}&page=1&page_size=50`

**Example Response**:
```json
{
  "albums": [
    {
      "album_id": "album_1a2b3c4d5e6f7890",
      "name": "Summer Vacation 2025",
      "photo_count": 47,
      "cover_photo_id": "photo_xyz",
      "is_family_shared": true,
      "created_at": "2025-12-16T10:00:00Z"
    }
  ],
  "total": 15,
  "page": 1,
  "page_size": 50,
  "pages": 1
}
```

---

### Epic 3: Album Deletion

**Objective**: Enable safe album deletion with proper cleanup.

#### E3-US1: Delete Album
**As a** User
**I want to** delete an album I no longer need
**So that** I can clean up my photo organization

**Acceptance Criteria**:
- AC1: DELETE /api/v1/albums/{album_id}?user_id={user_id}
- AC2: Verify user is album owner
- AC3: Remove all album_photo associations (photos NOT deleted)
- AC4: Remove all sync_status records for the album
- AC5: Publish album.deleted event
- AC6: Return success confirmation
- AC7: Response time <100ms

**API Reference**: `DELETE /api/v1/albums/{album_id}?user_id={user_id}`

**Example Response**:
```json
{
  "success": true,
  "message": "Album album_1a2b3c4d5e6f7890 deleted"
}
```

---

### Epic 4: Photo Management

**Objective**: Enable adding and removing photos from albums with metadata preservation.

#### E4-US1: Add Photos to Album
**As a** User
**I want to** add photos to an album
**So that** I can organize them together

**Acceptance Criteria**:
- AC1: POST /api/v1/albums/{album_id}/photos accepts photo_ids array
- AC2: Verify album exists and user has permission
- AC3: Support batch addition (multiple photos at once)
- AC4: Preserve AI metadata (tags, objects, scenes, faces) from request
- AC5: Assign display_order sequentially
- AC6: Deduplicate - adding existing photo succeeds silently
- AC7: Update album.photo_count
- AC8: Publish album.photo.added event
- AC9: Response time <200ms for up to 100 photos

**API Reference**: `POST /api/v1/albums/{album_id}/photos?user_id={user_id}`

**Example Request**:
```json
{
  "photos": [
    {
      "photo_id": "photo_123",
      "ai_tags": ["beach", "sunset"],
      "ai_objects": ["palm tree", "ocean"],
      "ai_scenes": ["outdoor", "landscape"]
    },
    {
      "photo_id": "photo_456",
      "ai_tags": ["family", "portrait"]
    }
  ]
}
```

**Example Response**:
```json
{
  "success": true,
  "added_count": 2,
  "album_id": "album_1a2b3c4d5e6f7890",
  "new_photo_count": 49
}
```

#### E4-US2: Remove Photos from Album
**As a** User
**I want to** remove photos from an album
**So that** I can refine my photo selection

**Acceptance Criteria**:
- AC1: DELETE /api/v1/albums/{album_id}/photos accepts photo_ids array
- AC2: Verify album exists and user has permission
- AC3: Support batch removal
- AC4: Update album.photo_count
- AC5: Publish album.photo.removed event
- AC6: Response time <200ms

**API Reference**: `DELETE /api/v1/albums/{album_id}/photos?user_id={user_id}`

**Example Request**:
```json
{
  "photo_ids": ["photo_123", "photo_456"]
}
```

**Example Response**:
```json
{
  "success": true,
  "removed_count": 2,
  "album_id": "album_1a2b3c4d5e6f7890",
  "new_photo_count": 47
}
```

#### E4-US3: Get Album Photos
**As a** User
**I want to** view photos in an album
**So that** I can browse my organized collection

**Acceptance Criteria**:
- AC1: GET /api/v1/albums/{album_id}/photos returns photo list
- AC2: Support limit (1-200, default 50) and offset pagination
- AC3: Include AI metadata (ai_tags, ai_objects, ai_scenes, face_detection_results)
- AC4: Sort by display_order ASC, then added_at DESC
- AC5: Response time <100ms for 50 photos

**API Reference**: `GET /api/v1/albums/{album_id}/photos?user_id={user_id}&limit=50&offset=0`

**Example Response**:
```json
{
  "photos": [
    {
      "album_id": "album_1a2b3c4d5e6f7890",
      "photo_id": "photo_123",
      "display_order": 0,
      "is_featured": false,
      "ai_tags": ["beach", "sunset"],
      "ai_objects": ["palm tree", "ocean"],
      "ai_scenes": ["outdoor", "landscape"],
      "face_detection_results": null,
      "added_at": "2025-12-16T10:30:00Z",
      "added_by": "usr_abc123"
    }
  ]
}
```

---

### Epic 5: Smart Frame Synchronization

**Objective**: Enable album synchronization to IoT smart frame devices.

#### E5-US1: Sync Album to Frame
**As a** User
**I want to** sync an album to my smart frame
**So that** my photos display on the frame

**Acceptance Criteria**:
- AC1: POST /api/v1/albums/{album_id}/sync accepts frame_id
- AC2: Validate album exists and user has permission
- AC3: Create/update sync status record (PENDING -> IN_PROGRESS)
- AC4: Track total_photos, synced_photos, pending_photos, failed_photos
- AC5: Publish album.synced event
- AC6: Publish MQTT message to frame device
- AC7: Response time <500ms for sync initiation

**API Reference**: `POST /api/v1/albums/{album_id}/sync?user_id={user_id}`

**Example Request**:
```json
{
  "frame_id": "frame_001"
}
```

**Example Response**:
```json
{
  "album_id": "album_1a2b3c4d5e6f7890",
  "frame_id": "frame_001",
  "status": "IN_PROGRESS",
  "total_photos": 47,
  "synced_photos": 0,
  "pending_photos": 47,
  "failed_photos": 0,
  "sync_version": 1,
  "started_at": "2025-12-16T11:00:00Z",
  "completed_at": null
}
```

#### E5-US2: Get Sync Status
**As a** User
**I want to** check sync progress for my album
**So that** I know when photos will appear on my frame

**Acceptance Criteria**:
- AC1: GET /api/v1/albums/{album_id}/sync/{frame_id} returns status
- AC2: Include progress metrics (synced, pending, failed counts)
- AC3: Include sync_version for conflict detection
- AC4: Include started_at and completed_at timestamps
- AC5: Response time <50ms

**API Reference**: `GET /api/v1/albums/{album_id}/sync/{frame_id}?user_id={user_id}`

#### E5-US3: Auto-Sync on Photo Changes
**As a** User
**I want** my linked frames to automatically receive new photos
**So that** I don't need to manually sync

**Acceptance Criteria**:
- AC1: When auto_sync=true and sync_frames not empty, trigger sync
- AC2: Photo additions trigger sync to all linked frames
- AC3: Sync only if album.auto_sync is enabled
- AC4: Publish MQTT notifications to frames

---

### Epic 6: Event-Driven Integration

**Objective**: Maintain data consistency through event-driven architecture.

#### E6-US1: Publish Album Created Event
**As an** Album Service
**I want to** publish album.created events
**So that** downstream services can respond

**Acceptance Criteria**:
- AC1: Publish on new album creation
- AC2: Payload: album_id, user_id, name, organization_id, is_family_shared, auto_sync, sync_frames, timestamp
- AC3: Published to NATS event bus
- AC4: Event failures logged but don't block operation
- AC5: Subscribers: notification_service, audit_service

#### E6-US2: Publish Album Photo Events
**As an** Album Service
**I want to** publish photo add/remove events
**So that** device_service can trigger frame sync

**Acceptance Criteria**:
- AC1: album.photo.added published on photo addition
- AC2: album.photo.removed published on photo removal
- AC3: Payload: album_id, user_id, photo_ids, count, timestamp
- AC4: Subscribers: notification_service, device_service

#### E6-US3: Handle File Deleted Events
**As an** Album Service
**I want to** remove photos when files are deleted
**So that** albums don't reference missing photos

**Acceptance Criteria**:
- AC1: Subscribe to file.deleted from storage_service
- AC2: Remove photo from all albums containing it
- AC3: Update photo_count for affected albums
- AC4: Handler is idempotent (safe to process multiple times)

#### E6-US4: Handle Device Deleted Events
**As an** Album Service
**I want to** cleanup sync status when devices are deleted
**So that** no orphaned sync records remain

**Acceptance Criteria**:
- AC1: Subscribe to device.deleted from device_service
- AC2: Remove all sync_status records for the frame_id
- AC3: Handler is idempotent

#### E6-US5: Handle User Deleted Events
**As an** Album Service
**I want to** cleanup all user albums when user is deleted
**So that** user data is properly removed

**Acceptance Criteria**:
- AC1: Subscribe to user.deleted from account_service
- AC2: Delete all albums for the user
- AC3: Cascade delete album_photos and sync_status
- AC4: Handler is idempotent

---

## API Surface Documentation

### Base URL
- **Development**: `http://localhost:8219`
- **Staging**: `https://staging-album.isa.ai`
- **Production**: `https://album.isa.ai`

### API Version
All endpoints prefixed with `/api/v1/`

### Authentication
- **Current**: Handled by API Gateway (JWT validation)
- **Header**: `Authorization: Bearer <token>`
- **User Context**: user_id passed as query parameter

### Core Endpoints Summary

| Method | Endpoint | Purpose | Response Time |
|--------|----------|---------|---------------|
| POST | `/api/v1/albums` | Create album | <200ms |
| GET | `/api/v1/albums/{album_id}` | Get album by ID | <50ms |
| GET | `/api/v1/albums` | List user albums | <200ms |
| PUT | `/api/v1/albums/{album_id}` | Update album | <100ms |
| DELETE | `/api/v1/albums/{album_id}` | Delete album | <100ms |
| POST | `/api/v1/albums/{album_id}/photos` | Add photos | <200ms |
| DELETE | `/api/v1/albums/{album_id}/photos` | Remove photos | <200ms |
| GET | `/api/v1/albums/{album_id}/photos` | Get album photos | <100ms |
| POST | `/api/v1/albums/{album_id}/sync` | Sync to frame | <500ms |
| GET | `/api/v1/albums/{album_id}/sync/{frame_id}` | Get sync status | <50ms |
| GET | `/health` | Health check | <20ms |

### HTTP Status Codes
- `200 OK`: Successful operation
- `201 Created`: New album created
- `400 Bad Request`: Validation error
- `403 Forbidden`: Permission denied
- `404 Not Found`: Album not found
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Database unavailable

### Common Response Format

**Success Response**:
```json
{
  "album_id": "album_1a2b3c4d5e6f7890",
  "name": "Album Name",
  "photo_count": 10,
  "created_at": "2025-12-16T10:00:00Z",
  "updated_at": "2025-12-16T10:00:00Z"
}
```

**Error Response**:
```json
{
  "detail": "Album not found with album_id: album_xyz"
}
```

### Pagination Format
```
GET /api/v1/albums?user_id={user_id}&page=1&page_size=50
```
Response includes:
```json
{
  "albums": [...],
  "total": 15,
  "page": 1,
  "page_size": 50,
  "pages": 1
}
```

---

## Functional Requirements

### FR-1: Album CRUD
System SHALL support create, read, update, delete operations for albums

### FR-2: Album Ownership
System SHALL enforce that only album owners can modify or delete albums

### FR-3: Photo Management
System SHALL support adding and removing photos from albums in batches

### FR-4: AI Metadata Storage
System SHALL preserve AI-generated metadata (tags, objects, scenes, faces) for album photos

### FR-5: Photo Deduplication
System SHALL prevent duplicate photos in the same album (silently succeed)

### FR-6: Smart Frame Sync
System SHALL support synchronization of albums to IoT smart frame devices

### FR-7: Sync Progress Tracking
System SHALL track sync progress with counts (synced, pending, failed)

### FR-8: Family Sharing
System SHALL support sharing albums with organization members

### FR-9: Event Publishing
System SHALL publish events for all album mutations to NATS

### FR-10: Event Handling
System SHALL handle events from storage_service, device_service, and account_service

---

## Non-Functional Requirements

### NFR-1: Performance
- **Album Create**: <200ms (p95)
- **Album Fetch**: <50ms (p95)
- **Album List**: <200ms for 50 results (p95)
- **Photo Add**: <200ms for 100 photos (p95)
- **Sync Initiation**: <500ms (p95)
- **Health Check**: <20ms (p99)

### NFR-2: Availability
- **Uptime**: 99.9% (excluding planned maintenance)
- **Database Failover**: Automatic with <30s recovery
- **Graceful Degradation**: Event/MQTT failures don't block operations

### NFR-3: Scalability
- **Concurrent Users**: 10K+ concurrent requests
- **Albums per User**: Unlimited
- **Photos per Album**: 10K+ photos supported
- **Throughput**: 1K requests/second
- **Database Connections**: Pooled with max 50 connections

### NFR-4: Data Integrity
- **ACID Transactions**: All mutations wrapped in PostgreSQL transactions
- **Photo Count Accuracy**: Maintained atomically on add/remove
- **Validation**: Pydantic models validate all inputs
- **Referential Integrity**: album_photos cleaned on album/photo deletion

### NFR-5: Security
- **Authentication**: JWT validation by API Gateway
- **Authorization**: User-scoped data access (album ownership)
- **Input Sanitization**: SQL injection prevention via parameterized queries

### NFR-6: Observability
- **Structured Logging**: JSON logs for all operations
- **Health Monitoring**: Database connectivity checked
- **Event Tracing**: Event publishing logged

### NFR-7: API Compatibility
- **Versioning**: /api/v1/ for backward compatibility
- **OpenAPI**: Swagger documentation auto-generated

---

## Dependencies

### External Services

1. **PostgreSQL gRPC Service**: Album data storage
   - Host: `isa-postgres-grpc:50061`
   - Schema: `album.albums`, `album.album_photos`, `album.album_sync_status`
   - SLA: 99.9% availability

2. **NATS Event Bus**: Event publishing/subscribing
   - Host: `isa-nats:4222`
   - Subjects: `album.created`, `album.updated`, `album.deleted`, `album.photo.added`, `album.photo.removed`, `album.synced`
   - SLA: 99.9% availability

3. **MQTT gRPC Service**: Smart frame notifications
   - Host: `mqtt-grpc:50053`
   - Topics: `isa/frame/{frame_id}/sync`
   - SLA: 99.5% availability

4. **Consul**: Service discovery and health checks
   - Host: `localhost:8500`
   - Service Name: `album_service`
   - Health Check: HTTP `/health`
   - SLA: 99.9% availability

### Internal Dependencies
- **core.config_manager**: Configuration management
- **core.logger**: Structured logging
- **core.nats_client**: Event bus client
- **isa_common.consul_client**: Service registration
- **isa_common.AsyncPostgresClient**: Database client

### Service Dependencies
- **storage_service**: Source of photos and AI metadata
- **device_service**: Smart frame device validation
- **account_service**: User validation (via events)
- **organization_service**: Family/org membership validation

---

## Success Criteria

### Phase 1: Core Album Management (Complete)
- [x] Album CRUD operations working
- [x] Photo add/remove functional
- [x] PostgreSQL storage stable
- [x] Event publishing active
- [x] Health checks implemented

### Phase 2: Smart Frame Integration (Complete)
- [x] Sync to frame working
- [x] Sync status tracking functional
- [x] MQTT notifications active
- [x] Auto-sync on photo changes

### Phase 3: Production Hardening (Current)
- [ ] Comprehensive test coverage (Unit, Component, Integration, API, Smoke)
- [ ] Performance benchmarks met
- [ ] Event handlers battle-tested
- [ ] Documentation complete

### Phase 4: Enhanced Features (Future)
- [ ] Photo reordering within albums
- [ ] Album sharing with non-family users
- [ ] Bulk album operations
- [ ] Album templates/presets

---

## Out of Scope

The following are explicitly NOT included in this release:

1. **Photo Storage**: Handled by storage_service
2. **Photo Processing**: AI analysis handled by storage_service
3. **Device Management**: Smart frame CRUD handled by device_service
4. **User Management**: Handled by account_service
5. **Organization Management**: Handled by organization_service
6. **Photo Editing**: Out of scope for album service
7. **Album Templates**: Future feature
8. **Collaborative Editing**: Multiple editors for same album

---

## Appendix: Request/Response Examples

### 1. Create Album

**Request**:
```bash
curl -X POST "http://localhost:8219/api/v1/albums?user_id=usr_abc123" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "name": "Summer Vacation 2025",
    "description": "Hawaii trip photos",
    "auto_sync": true,
    "sync_frames": ["frame_001"],
    "is_family_shared": true
  }'
```

**Response** (201 Created):
```json
{
  "album_id": "album_1a2b3c4d5e6f7890",
  "name": "Summer Vacation 2025",
  "description": "Hawaii trip photos",
  "user_id": "usr_abc123",
  "photo_count": 0,
  "cover_photo_id": null,
  "auto_sync": true,
  "sync_frames": ["frame_001"],
  "is_family_shared": true,
  "organization_id": null,
  "created_at": "2025-12-16T10:00:00Z",
  "updated_at": "2025-12-16T10:00:00Z"
}
```

### 2. Add Photos to Album

**Request**:
```bash
curl -X POST "http://localhost:8219/api/v1/albums/album_1a2b3c4d/photos?user_id=usr_abc123" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "photos": [
      {
        "photo_id": "photo_123",
        "ai_tags": ["beach", "sunset"],
        "ai_objects": ["ocean", "palm tree"]
      }
    ]
  }'
```

**Response**:
```json
{
  "success": true,
  "added_count": 1,
  "album_id": "album_1a2b3c4d",
  "new_photo_count": 1
}
```

### 3. Sync Album to Frame

**Request**:
```bash
curl -X POST "http://localhost:8219/api/v1/albums/album_1a2b3c4d/sync?user_id=usr_abc123" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "frame_id": "frame_001"
  }'
```

**Response**:
```json
{
  "album_id": "album_1a2b3c4d",
  "frame_id": "frame_001",
  "status": "IN_PROGRESS",
  "total_photos": 47,
  "synced_photos": 0,
  "pending_photos": 47,
  "failed_photos": 0,
  "sync_version": 1,
  "started_at": "2025-12-16T11:00:00Z",
  "completed_at": null
}
```

### 4. Get Album Photos

**Request**:
```bash
curl -X GET "http://localhost:8219/api/v1/albums/album_1a2b3c4d/photos?user_id=usr_abc123&limit=10" \
  -H "Authorization: Bearer <token>"
```

**Response**:
```json
{
  "photos": [
    {
      "album_id": "album_1a2b3c4d",
      "photo_id": "photo_123",
      "display_order": 0,
      "is_featured": false,
      "ai_tags": ["beach", "sunset"],
      "ai_objects": ["ocean", "palm tree"],
      "ai_scenes": ["outdoor"],
      "face_detection_results": null,
      "added_at": "2025-12-16T10:30:00Z",
      "added_by": "usr_abc123"
    }
  ]
}
```

### 5. Delete Album

**Request**:
```bash
curl -X DELETE "http://localhost:8219/api/v1/albums/album_1a2b3c4d?user_id=usr_abc123" \
  -H "Authorization: Bearer <token>"
```

**Response**:
```json
{
  "success": true,
  "message": "Album album_1a2b3c4d deleted"
}
```

---

**Document Version**: 1.0
**Last Updated**: 2025-12-16
**Maintained By**: Album Service Product Team
**Related Documents**:
- Domain Context: docs/domain/album_service.md
- Design Doc: docs/design/album_service.md
- Data Contract: tests/contracts/album/data_contract.py
- Logic Contract: tests/contracts/album/logic_contract.md
