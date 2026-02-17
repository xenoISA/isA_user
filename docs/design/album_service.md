# Album Service - Design Document

## Design Overview

**Service Name**: album_service
**Port**: 8219
**Version**: 1.0.0
**Protocol**: HTTP REST API
**Last Updated**: 2025-12-16

### Design Principles
1. **Photo Organization First**: Single source of truth for album-photo relationships
2. **Smart Frame Native**: Built-in MQTT sync for IoT smart frame devices
3. **Event-Driven Synchronization**: Loose coupling via NATS events
4. **AI Metadata Preservation**: Store and leverage AI-generated photo metadata
5. **ACID Guarantees**: PostgreSQL transactions for data integrity
6. **Graceful Degradation**: Event/MQTT failures don't block operations

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     External Clients                        │
│   (Mobile Apps, Web Apps, Smart Frames, Other Services)     │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP REST API
                       │ (via API Gateway - JWT validation)
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                 Album Service (Port 8219)                   │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │              FastAPI HTTP Layer (main.py)             │ │
│  │  - Request validation (Pydantic models)               │ │
│  │  - Response formatting                                │ │
│  │  - Error handling & exception handlers                │ │
│  │  - Health checks (/health)                            │ │
│  │  - Lifecycle management (startup/shutdown)            │ │
│  └─────────────────────┬─────────────────────────────────┘ │
│                        │                                     │
│  ┌─────────────────────▼─────────────────────────────────┐ │
│  │      Service Layer (album_service.py)                │ │
│  │  - Business logic (validation, ownership)             │ │
│  │  - Album CRUD operations                             │ │
│  │  - Photo management (add/remove/list)                │ │
│  │  - Smart frame sync orchestration                    │ │
│  │  - Event publishing coordination                     │ │
│  └─────────────────────┬─────────────────────────────────┘ │
│                        │                                     │
│  ┌─────────────────────▼─────────────────────────────────┐ │
│  │      Repository Layer (album_repository.py)          │ │
│  │  - Database CRUD operations                           │ │
│  │  - PostgreSQL gRPC communication                      │ │
│  │  - Query construction (parameterized)                 │ │
│  │  - Result parsing (proto to Pydantic)                 │ │
│  │  - No business logic                                  │ │
│  └─────────────────────┬─────────────────────────────────┘ │
│                        │                                     │
│  ┌─────────────────────▼─────────────────────────────────┐ │
│  │      Event Layer (events/)                           │ │
│  │  - NATS event bus publishing (publishers.py)         │ │
│  │  - Event handlers for subscriptions (handlers.py)    │ │
│  │  - Event model definitions (models.py)               │ │
│  └─────────────────────┬─────────────────────────────────┘ │
│                        │                                     │
│  ┌─────────────────────▼─────────────────────────────────┐ │
│  │      MQTT Layer (mqtt/publisher.py)                  │ │
│  │  - Smart frame notifications                         │ │
│  │  - Sync status updates                               │ │
│  │  - Device communication                              │ │
│  └───────────────────────────────────────────────────────┘ │
└───────────────────────┼──────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┬───────────────┐
        │               │               │               │
        ↓               ↓               ↓               ↓
┌──────────────┐ ┌─────────────┐ ┌────────────┐ ┌────────────┐
│  PostgreSQL  │ │    NATS     │ │   Consul   │ │  MQTT gRPC │
│   (gRPC)     │ │  (Events)   │ │ (Discovery)│ │  (Frames)  │
│              │ │             │ │            │ │            │
│  Schema:     │ │  Subjects:  │ │  Service:  │ │  Topics:   │
│  album       │ │  album.*    │ │  album_    │ │  isa/frame │
│              │ │             │ │  service   │ │  /{id}/    │
│  Tables:     │ │  Subscribe: │ │            │ │  sync      │
│  - albums    │ │  - file.*   │ │  Health:   │ │            │
│  - album_    │ │  - device.* │ │  /health   │ │            │
│    photos    │ │  - user.*   │ │            │ │            │
│  - album_    │ │             │ │            │ │            │
│    sync_     │ │  Publish:   │ │            │ │            │
│    status    │ │  - album.*  │ │            │ │            │
└──────────────┘ └─────────────┘ └────────────┘ └────────────┘
```

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      Album Service                          │
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────────┐   │
│  │   Models    │───→│   Service   │───→│ Repository   │   │
│  │  (Pydantic) │    │ (Business)  │    │   (Data)     │   │
│  │             │    │             │    │              │   │
│  │ - Album     │    │ - Album     │    │ - Album      │   │
│  │ - AlbumPhoto│    │   Service   │    │   Repository │   │
│  │ - AlbumSync │    │             │    │              │   │
│  │   Status    │    │             │    │              │   │
│  │ - SyncStatus│    │             │    │              │   │
│  │   (Enum)    │    │             │    │              │   │
│  └─────────────┘    └─────────────┘    └──────────────┘   │
│         ↑                  ↑                    ↑           │
│         │                  │                    │           │
│  ┌──────┴──────────────────┴────────────────────┴───────┐  │
│  │              FastAPI Main (main.py)                   │  │
│  │  - Dependency Injection (get_album_service)          │  │
│  │  - Route Handlers (11 endpoints)                     │  │
│  │  - Exception Handlers (custom errors)                │  │
│  └────────────────────────┬──────────────────────────────┘  │
│                           │                                 │
│  ┌────────────────────────▼──────────────────────────────┐  │
│  │              Event Publishers & Handlers              │  │
│  │  (events/publishers.py, events/handlers.py)          │  │
│  │  Publishers:                                         │  │
│  │  - publish_album_created                             │  │
│  │  - publish_album_updated                             │  │
│  │  - publish_album_deleted                             │  │
│  │  - publish_album_photo_added                         │  │
│  │  - publish_album_photo_removed                       │  │
│  │  - publish_album_synced                              │  │
│  │  Handlers:                                           │  │
│  │  - handle_file_uploaded                              │  │
│  │  - handle_file_deleted                               │  │
│  │  - handle_device_offline                             │  │
│  │  - handle_device_deleted                             │  │
│  │  - handle_user_deleted                               │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              MQTT Publisher (mqtt/publisher.py)       │  │
│  │  - Frame sync notifications                          │  │
│  │  - Photo update broadcasts                           │  │
│  │  - Device status messages                            │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                 Factory Pattern                       │  │
│  │              (factory.py, protocols.py)               │  │
│  │  - create_album_service (production)                  │  │
│  │  - AlbumRepositoryProtocol (interface)                │  │
│  │  - EventBusProtocol (interface)                       │  │
│  │  - Enables dependency injection for tests             │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Design

### 1. FastAPI HTTP Layer (main.py)

**Responsibilities**:
- HTTP request/response handling
- Request validation via Pydantic models
- Route definitions (11 endpoints)
- Health checks
- Service initialization (lifespan management)
- Consul registration
- NATS event bus setup and subscriptions
- MQTT publisher initialization
- Exception handling

**Key Endpoints**:
```python
# Health Checks
GET /                                         # Root - service status
GET /health                                   # Health check

# Album Management
POST /api/v1/albums                           # Create album
GET  /api/v1/albums/{album_id}                # Get album by ID
GET  /api/v1/albums                           # List user albums
PUT  /api/v1/albums/{album_id}                # Update album
DELETE /api/v1/albums/{album_id}              # Delete album

# Photo Management
POST /api/v1/albums/{album_id}/photos         # Add photos to album
DELETE /api/v1/albums/{album_id}/photos       # Remove photos from album
GET  /api/v1/albums/{album_id}/photos         # Get album photos

# Sync Operations
POST /api/v1/albums/{album_id}/sync           # Sync album to frame
GET  /api/v1/albums/{album_id}/sync/{frame_id} # Get sync status
```

**Lifecycle Management**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # 1. Initialize MQTT publisher
    mqtt_publisher = AlbumMQTTPublisher(...)
    await mqtt_publisher.connect()

    # 2. Initialize event bus
    event_bus = await get_event_bus("album_service")

    # 3. Initialize service with factory
    album_service = create_album_service(config=config_manager, event_bus=event_bus)

    # 4. Check database connection
    db_connected = await album_service.check_connection()

    # 5. Set up event subscriptions
    event_handler = AlbumEventHandler(album_repo, album_service, mqtt_publisher)
    await event_bus.subscribe_to_events("events.*.file.uploaded.with_ai", ...)
    await event_bus.subscribe_to_events("events.*.file.deleted", ...)
    await event_bus.subscribe_to_events("events.*.device.offline", ...)
    await event_bus.subscribe_to_events("events.*.device.deleted", ...)
    await event_bus.subscribe_to_events("events.*.user.deleted", ...)

    # 6. Consul registration
    if config.consul_enabled:
        consul_registry.register()

    yield  # Service runs

    # Shutdown
    await mqtt_publisher.cleanup()
    consul_registry.deregister()
    await event_bus.close()
```

### 2. Service Layer (album_service.py)

**Class**: `AlbumService`

**Responsibilities**:
- Business logic execution
- Album CRUD with ownership validation
- Photo management with deduplication
- Smart frame sync orchestration
- Event publishing coordination
- Input validation
- Error handling and custom exceptions

**Key Methods**:
```python
class AlbumService:
    def __init__(
        self,
        repository: AlbumRepositoryProtocol,
        event_bus: Optional[EventBusProtocol] = None
    ):
        self.repository = repository
        self.event_bus = event_bus

    # Album Operations
    async def create_album(
        self,
        request: AlbumCreateRequest,
        user_id: str
    ) -> AlbumResponse:
        """Create new album"""
        # 1. Validate name
        if not request.name or len(request.name.strip()) == 0:
            raise AlbumValidationError("Album name is required")
        if len(request.name) > 255:
            raise AlbumValidationError("Album name exceeds 255 characters")

        # 2. Generate album_id
        album_id = f"album_{secrets.token_hex(8)}"

        # 3. Create in database
        album = await self.repository.create_album(
            album_id=album_id,
            user_id=user_id,
            name=request.name.strip(),
            description=request.description,
            auto_sync=request.auto_sync,
            sync_frames=request.sync_frames,
            is_family_shared=request.is_family_shared,
            organization_id=request.organization_id
        )

        # 4. Publish event
        if self.event_bus:
            await publish_album_created(self.event_bus, album)

        return to_response(album)

    async def get_album(
        self,
        album_id: str,
        user_id: str
    ) -> AlbumResponse:
        """Get album by ID with ownership check"""
        album = await self.repository.get_album_by_id(album_id)
        if not album:
            raise AlbumNotFoundError(f"Album not found: {album_id}")

        # Check ownership or family sharing
        if album.user_id != user_id and not album.is_family_shared:
            raise AlbumPermissionError("Access denied to this album")

        return to_response(album)

    async def list_user_albums(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 50,
        organization_id: Optional[str] = None,
        is_family_shared: Optional[bool] = None
    ) -> AlbumListResponse:
        """List albums for user with pagination"""
        offset = (page - 1) * page_size
        albums, total = await self.repository.list_albums(
            user_id=user_id,
            limit=page_size,
            offset=offset,
            organization_id=organization_id,
            is_family_shared=is_family_shared
        )

        return AlbumListResponse(
            albums=[to_response(a) for a in albums],
            total=total,
            page=page,
            page_size=page_size,
            pages=(total + page_size - 1) // page_size
        )

    async def update_album(
        self,
        album_id: str,
        user_id: str,
        request: AlbumUpdateRequest
    ) -> AlbumResponse:
        """Update album with ownership check"""
        # 1. Validate ownership
        album = await self.repository.get_album_by_id(album_id)
        if not album:
            raise AlbumNotFoundError(f"Album not found: {album_id}")
        if album.user_id != user_id:
            raise AlbumPermissionError("Only album owner can update")

        # 2. Update
        updated = await self.repository.update_album(album_id, request)

        # 3. Publish event
        if self.event_bus:
            await publish_album_updated(self.event_bus, updated)

        return to_response(updated)

    async def delete_album(
        self,
        album_id: str,
        user_id: str
    ) -> bool:
        """Delete album with ownership check"""
        # 1. Validate ownership
        album = await self.repository.get_album_by_id(album_id)
        if not album:
            raise AlbumNotFoundError(f"Album not found: {album_id}")
        if album.user_id != user_id:
            raise AlbumPermissionError("Only album owner can delete")

        # 2. Delete (cascades to album_photos and sync_status)
        success = await self.repository.delete_album(album_id)

        # 3. Publish event
        if success and self.event_bus:
            await publish_album_deleted(self.event_bus, album_id, user_id)

        return success

    # Photo Operations
    async def add_photos_to_album(
        self,
        album_id: str,
        user_id: str,
        request: AlbumAddPhotosRequest
    ) -> Dict[str, Any]:
        """Add photos to album with AI metadata"""
        # 1. Validate album ownership
        album = await self.repository.get_album_by_id(album_id)
        if not album:
            raise AlbumNotFoundError(f"Album not found: {album_id}")
        if album.user_id != user_id:
            raise AlbumPermissionError("Only album owner can add photos")

        # 2. Add photos (with deduplication)
        added_count = await self.repository.add_photos_to_album(
            album_id=album_id,
            photos=request.photos,
            added_by=user_id
        )

        # 3. Update photo_count
        new_count = await self.repository.get_photo_count(album_id)

        # 4. Publish event
        if self.event_bus and added_count > 0:
            photo_ids = [p.photo_id for p in request.photos]
            await publish_album_photo_added(
                self.event_bus, album_id, user_id, photo_ids, added_count
            )

        return {
            "success": True,
            "added_count": added_count,
            "album_id": album_id,
            "new_photo_count": new_count
        }

    async def remove_photos_from_album(
        self,
        album_id: str,
        user_id: str,
        request: AlbumRemovePhotosRequest
    ) -> Dict[str, Any]:
        """Remove photos from album"""
        # Validate ownership, remove, update count, publish event
        ...

    async def get_album_photos(
        self,
        album_id: str,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[AlbumPhoto]:
        """Get photos in album with AI metadata"""
        # Validate access, return photos sorted by display_order
        ...

    # Sync Operations
    async def sync_album_to_frame(
        self,
        album_id: str,
        user_id: str,
        request: AlbumSyncRequest
    ) -> AlbumSyncStatusResponse:
        """Initiate sync to smart frame"""
        # 1. Validate album and ownership
        album = await self.repository.get_album_by_id(album_id)
        if not album:
            raise AlbumNotFoundError(f"Album not found: {album_id}")
        if album.user_id != user_id:
            raise AlbumPermissionError("Only album owner can sync")

        # 2. Create/update sync status
        sync_status = await self.repository.create_or_update_sync_status(
            album_id=album_id,
            frame_id=request.frame_id,
            status=SyncStatus.IN_PROGRESS,
            total_photos=album.photo_count
        )

        # 3. Publish event
        if self.event_bus:
            await publish_album_synced(self.event_bus, sync_status)

        return to_sync_response(sync_status)

    async def get_album_sync_status(
        self,
        album_id: str,
        frame_id: str,
        user_id: str
    ) -> AlbumSyncStatusResponse:
        """Get sync status for album-frame pair"""
        ...

    # Health Check
    async def check_connection(self) -> bool:
        """Database connectivity check"""
        return await self.repository.check_connection()
```

**Custom Exceptions** (protocols.py):
```python
class AlbumServiceError(Exception):
    """Base exception for album service"""
    pass

class AlbumNotFoundError(AlbumServiceError):
    """Album not found"""
    pass

class AlbumValidationError(AlbumServiceError):
    """Validation error"""
    pass

class AlbumPermissionError(AlbumServiceError):
    """Permission denied"""
    pass
```

### 3. Repository Layer (album_repository.py)

**Class**: `AlbumRepository`

**Responsibilities**:
- PostgreSQL CRUD operations for 3 tables
- gRPC communication with postgres_grpc_service
- Query construction (parameterized)
- Result parsing (proto to Pydantic)
- Photo count maintenance
- Sync status tracking

**Key Methods**:
```python
class AlbumRepository:
    def __init__(self, config: Optional[ConfigManager] = None):
        host, port = config.discover_service(...)
        self.db = AsyncPostgresClient(host=host, port=port, user_id='album_service')
        self.schema = "album"
        self.albums_table = "albums"
        self.photos_table = "album_photos"
        self.sync_table = "album_sync_status"

    # Album Operations
    async def create_album(self, album_id, user_id, name, ...) -> Album:
        """Create new album"""
        async with self.db:
            await self.db.execute(
                f"""INSERT INTO {self.schema}.{self.albums_table}
                    (album_id, user_id, name, description, photo_count,
                     auto_sync, sync_frames, is_family_shared, organization_id)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)""",
                params=[album_id, user_id, name, description, 0,
                        auto_sync, sync_frames, is_family_shared, organization_id]
            )
        return await self.get_album_by_id(album_id)

    async def get_album_by_id(self, album_id: str) -> Optional[Album]:
        """Get album by ID"""
        async with self.db:
            result = await self.db.query_row(
                f"SELECT * FROM {self.schema}.{self.albums_table} WHERE album_id = $1",
                params=[album_id]
            )
        return self._row_to_album(result) if result else None

    async def list_albums(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        organization_id: Optional[str] = None,
        is_family_shared: Optional[bool] = None
    ) -> Tuple[List[Album], int]:
        """List albums with filters and pagination"""
        # Build WHERE clause with filters
        # Return albums and total count
        ...

    async def update_album(self, album_id: str, request: AlbumUpdateRequest) -> Album:
        """Update album fields"""
        # Dynamic SET clause based on provided fields
        ...

    async def delete_album(self, album_id: str) -> bool:
        """Delete album and cascade to photos and sync status"""
        async with self.db:
            # Delete sync status records
            await self.db.execute(
                f"DELETE FROM {self.schema}.{self.sync_table} WHERE album_id = $1",
                params=[album_id]
            )
            # Delete album photos
            await self.db.execute(
                f"DELETE FROM {self.schema}.{self.photos_table} WHERE album_id = $1",
                params=[album_id]
            )
            # Delete album
            await self.db.execute(
                f"DELETE FROM {self.schema}.{self.albums_table} WHERE album_id = $1",
                params=[album_id]
            )
        return True

    # Photo Operations
    async def add_photos_to_album(
        self,
        album_id: str,
        photos: List[PhotoInput],
        added_by: str
    ) -> int:
        """Add photos with deduplication"""
        added_count = 0
        async with self.db:
            for photo in photos:
                # ON CONFLICT DO NOTHING for deduplication
                result = await self.db.execute(
                    f"""INSERT INTO {self.schema}.{self.photos_table}
                        (album_id, photo_id, display_order, ai_tags, ai_objects,
                         ai_scenes, face_detection_results, added_by)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        ON CONFLICT (album_id, photo_id) DO NOTHING""",
                    params=[album_id, photo.photo_id, ...]
                )
                if result.rows_affected > 0:
                    added_count += 1

            # Update photo_count
            await self._update_photo_count(album_id)

        return added_count

    async def remove_photos_from_album(
        self,
        album_id: str,
        photo_ids: List[str]
    ) -> int:
        """Remove photos from album"""
        ...

    async def get_album_photos(
        self,
        album_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[AlbumPhoto]:
        """Get photos sorted by display_order, then added_at"""
        ...

    # Sync Operations
    async def create_or_update_sync_status(
        self,
        album_id: str,
        frame_id: str,
        status: SyncStatus,
        total_photos: int
    ) -> AlbumSyncStatus:
        """Upsert sync status record"""
        ...

    async def get_sync_status(
        self,
        album_id: str,
        frame_id: str
    ) -> Optional[AlbumSyncStatus]:
        """Get sync status for album-frame pair"""
        ...

    async def delete_sync_status_by_frame(self, frame_id: str) -> int:
        """Delete all sync records for a frame (device deleted)"""
        ...

    async def delete_sync_status_by_album(self, album_id: str) -> int:
        """Delete all sync records for an album"""
        ...

    # Utility
    async def _update_photo_count(self, album_id: str) -> None:
        """Update album's photo_count from actual count"""
        async with self.db:
            await self.db.execute(
                f"""UPDATE {self.schema}.{self.albums_table}
                    SET photo_count = (
                        SELECT COUNT(*) FROM {self.schema}.{self.photos_table}
                        WHERE album_id = $1
                    ), updated_at = NOW()
                    WHERE album_id = $1""",
                params=[album_id]
            )
```

### 4. Event Handler Layer (events/handlers.py)

**Class**: `AlbumEventHandler`

**Responsibilities**:
- Handle incoming events from other services
- Maintain data consistency across services
- Clean up orphaned data

**Key Handlers**:
```python
class AlbumEventHandler:
    def __init__(
        self,
        repository: AlbumRepository,
        album_service: AlbumService,
        mqtt_publisher: Optional[AlbumMQTTPublisher] = None
    ):
        self.repository = repository
        self.album_service = album_service
        self.mqtt_publisher = mqtt_publisher

    async def handle_event(self, event: Dict[str, Any]) -> None:
        """Route event to appropriate handler"""
        event_type = event.get("event_type", "")

        if "file.uploaded.with_ai" in event_type:
            await self.handle_file_uploaded(event)
        elif "file.deleted" in event_type:
            await self.handle_file_deleted(event)
        elif "device.offline" in event_type:
            await self.handle_device_offline(event)
        elif "device.deleted" in event_type:
            await self.handle_device_deleted(event)
        elif "user.deleted" in event_type:
            await self.handle_user_deleted(event)

    async def handle_file_uploaded(self, event: Dict) -> None:
        """Handle file.uploaded.with_ai - potentially auto-add to album"""
        # Future: Auto-add photos based on AI metadata
        pass

    async def handle_file_deleted(self, event: Dict) -> None:
        """Handle file.deleted - remove photo from all albums"""
        photo_id = event.get("data", {}).get("file_id")
        if not photo_id:
            return

        # Get all albums containing this photo
        affected_albums = await self.repository.get_albums_containing_photo(photo_id)

        # Remove from each album
        for album_id in affected_albums:
            await self.repository.remove_photos_from_album(album_id, [photo_id])
            await self.repository._update_photo_count(album_id)

    async def handle_device_offline(self, event: Dict) -> None:
        """Handle device.offline - update sync status"""
        frame_id = event.get("data", {}).get("device_id")
        if not frame_id:
            return

        # Mark all syncs for this frame as FAILED or PENDING
        await self.repository.mark_sync_status_by_frame(frame_id, SyncStatus.FAILED)

    async def handle_device_deleted(self, event: Dict) -> None:
        """Handle device.deleted - cleanup sync status records"""
        frame_id = event.get("data", {}).get("device_id")
        if not frame_id:
            return

        await self.repository.delete_sync_status_by_frame(frame_id)

    async def handle_user_deleted(self, event: Dict) -> None:
        """Handle user.deleted - delete all user's albums"""
        user_id = event.get("data", {}).get("user_id")
        if not user_id:
            return

        # Get all albums for user
        albums = await self.repository.get_albums_by_user(user_id)

        # Delete each album (cascade handles photos and sync)
        for album in albums:
            await self.repository.delete_album(album.album_id)
```

### 5. MQTT Layer (mqtt/publisher.py)

**Class**: `AlbumMQTTPublisher`

**Responsibilities**:
- Communicate with smart frame devices via MQTT
- Send sync notifications
- Broadcast photo updates

**Key Methods**:
```python
class AlbumMQTTPublisher:
    def __init__(self, mqtt_host: str, mqtt_port: int):
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.channel = None

    async def connect(self) -> None:
        """Connect to MQTT gRPC service"""
        self.channel = grpc.aio.insecure_channel(f"{self.mqtt_host}:{self.mqtt_port}")
        self.stub = mqtt_pb2_grpc.MQTTServiceStub(self.channel)

    async def publish_sync_notification(
        self,
        frame_id: str,
        album_id: str,
        action: str,
        data: Dict[str, Any]
    ) -> None:
        """Send sync notification to frame"""
        topic = f"isa/frame/{frame_id}/sync"
        payload = {
            "album_id": album_id,
            "action": action,  # "start", "update", "complete", "cancel"
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        await self.stub.Publish(mqtt_pb2.PublishRequest(
            topic=topic,
            payload=json.dumps(payload)
        ))

    async def publish_photo_update(
        self,
        frame_id: str,
        album_id: str,
        photo_ids: List[str],
        action: str
    ) -> None:
        """Notify frame about photo changes"""
        topic = f"isa/frame/{frame_id}/photos"
        payload = {
            "album_id": album_id,
            "photo_ids": photo_ids,
            "action": action,  # "added", "removed"
            "timestamp": datetime.now().isoformat()
        }
        await self.stub.Publish(mqtt_pb2.PublishRequest(
            topic=topic,
            payload=json.dumps(payload)
        ))

    async def cleanup(self) -> None:
        """Close MQTT connection"""
        if self.channel:
            await self.channel.close()
```

---

## Database Schema Design

### PostgreSQL Schema: `album`

#### Table: album.albums

```sql
-- Create album schema
CREATE SCHEMA IF NOT EXISTS album;

-- Create albums table
CREATE TABLE IF NOT EXISTS album.albums (
    -- Primary Key
    album_id VARCHAR(255) PRIMARY KEY,

    -- Ownership
    user_id VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255),

    -- Album Info
    name VARCHAR(255) NOT NULL,
    description TEXT,
    cover_photo_id VARCHAR(255),

    -- Counts
    photo_count INTEGER DEFAULT 0,

    -- Sync Settings
    auto_sync BOOLEAN DEFAULT TRUE,
    sync_frames JSONB DEFAULT '[]'::jsonb,

    -- Sharing
    is_family_shared BOOLEAN DEFAULT FALSE,
    sharing_resource_id VARCHAR(255),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_albums_user_id ON album.albums(user_id);
CREATE INDEX IF NOT EXISTS idx_albums_organization_id ON album.albums(organization_id);
CREATE INDEX IF NOT EXISTS idx_albums_is_family_shared ON album.albums(is_family_shared);
CREATE INDEX IF NOT EXISTS idx_albums_updated_at ON album.albums(updated_at DESC);

-- Comments
COMMENT ON TABLE album.albums IS 'Photo albums for organizing and sharing photos';
COMMENT ON COLUMN album.albums.album_id IS 'Unique album identifier (format: album_{hex16})';
COMMENT ON COLUMN album.albums.sync_frames IS 'Array of frame device IDs for auto-sync';
```

#### Table: album.album_photos

```sql
-- Create album_photos table
CREATE TABLE IF NOT EXISTS album.album_photos (
    -- Composite Primary Key
    album_id VARCHAR(255) NOT NULL,
    photo_id VARCHAR(255) NOT NULL,
    PRIMARY KEY (album_id, photo_id),

    -- Display
    display_order INTEGER DEFAULT 0,
    is_featured BOOLEAN DEFAULT FALSE,

    -- AI Metadata (from storage_service)
    ai_tags JSONB DEFAULT '[]'::jsonb,
    ai_objects JSONB DEFAULT '[]'::jsonb,
    ai_scenes JSONB DEFAULT '[]'::jsonb,
    face_detection_results JSONB,

    -- Tracking
    added_at TIMESTAMPTZ DEFAULT NOW(),
    added_by VARCHAR(255),

    -- Foreign Key
    FOREIGN KEY (album_id) REFERENCES album.albums(album_id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_album_photos_album_id ON album.album_photos(album_id);
CREATE INDEX IF NOT EXISTS idx_album_photos_photo_id ON album.album_photos(photo_id);
CREATE INDEX IF NOT EXISTS idx_album_photos_display_order ON album.album_photos(album_id, display_order);
CREATE INDEX IF NOT EXISTS idx_album_photos_ai_tags ON album.album_photos USING GIN(ai_tags);

-- Comments
COMMENT ON TABLE album.album_photos IS 'Junction table linking photos to albums with AI metadata';
COMMENT ON COLUMN album.album_photos.ai_tags IS 'AI-generated descriptive tags (beach, sunset, family)';
COMMENT ON COLUMN album.album_photos.ai_objects IS 'AI-detected objects (car, dog, building)';
COMMENT ON COLUMN album.album_photos.ai_scenes IS 'AI-classified scene types (outdoor, landscape)';
```

#### Table: album.album_sync_status

```sql
-- Create album_sync_status table
CREATE TABLE IF NOT EXISTS album.album_sync_status (
    -- Composite Primary Key
    album_id VARCHAR(255) NOT NULL,
    frame_id VARCHAR(255) NOT NULL,
    PRIMARY KEY (album_id, frame_id),

    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',

    -- Progress
    total_photos INTEGER DEFAULT 0,
    synced_photos INTEGER DEFAULT 0,
    pending_photos INTEGER DEFAULT 0,
    failed_photos INTEGER DEFAULT 0,

    -- Versioning
    sync_version INTEGER DEFAULT 1,

    -- Timestamps
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Foreign Key
    FOREIGN KEY (album_id) REFERENCES album.albums(album_id) ON DELETE CASCADE
);

-- Index
CREATE INDEX IF NOT EXISTS idx_sync_status_frame_id ON album.album_sync_status(frame_id);
CREATE INDEX IF NOT EXISTS idx_sync_status_status ON album.album_sync_status(status);

-- Comments
COMMENT ON TABLE album.album_sync_status IS 'Tracks sync progress per album-frame pair';
COMMENT ON COLUMN album.album_sync_status.status IS 'PENDING, IN_PROGRESS, COMPLETED, FAILED, CANCELLED';
COMMENT ON COLUMN album.album_sync_status.sync_version IS 'Incremental version for conflict resolution';
```

### Index Strategy

1. **Primary Keys**:
   - `album_id` on albums (clustered)
   - `(album_id, photo_id)` on album_photos (composite)
   - `(album_id, frame_id)` on album_sync_status (composite)

2. **Foreign Keys**: Cascade delete ensures referential integrity

3. **Query Optimization**:
   - `idx_albums_user_id`: List albums by user
   - `idx_albums_updated_at`: Sort by most recent
   - `idx_album_photos_display_order`: Photo ordering
   - `idx_album_photos_ai_tags`: GIN for AI tag queries
   - `idx_sync_status_frame_id`: Device cleanup queries

---

## Event-Driven Architecture

### Event Publishing (events/publishers.py)

**NATS Subjects Published**:
```
album.created               # New album created
album.updated               # Album properties modified
album.deleted               # Album removed
album.photo.added           # Photos added to album
album.photo.removed         # Photos removed from album
album.synced                # Album sync initiated
```

### Event Subscriptions

**NATS Subjects Subscribed**:
```
events.*.file.uploaded.with_ai   # From storage_service
events.*.file.deleted            # From storage_service
events.*.device.offline          # From device_service
events.*.device.deleted          # From device_service
events.*.user.deleted            # From account_service
```

### Event Flow Diagram

```
┌─────────────────┐
│   User/App      │
└────────┬────────┘
         │ POST /api/v1/albums
         ↓
┌─────────────────────┐
│  Album Service      │
│                     │
│  1. Validate input  │
│  2. Create album    │───→ PostgreSQL (album.albums)
│  3. Publish event   │         │
└─────────────────────┘         │ Success
         │                      ↓
         │               ┌──────────────┐
         │               │ Return Album │
         │               └──────────────┘
         │ Event: album.created
         ↓
┌─────────────────────┐
│      NATS Bus       │
│ Subject:            │
│ album.created       │
└──────────┬──────────┘
           │
           ├──→ notification_service (notify user)
           └──→ audit_service (log creation)

========================================

┌─────────────────┐
│ storage_service │
└────────┬────────┘
         │ Event: file.deleted
         ↓
┌─────────────────────┐
│      NATS Bus       │
└──────────┬──────────┘
           │
           ↓
┌─────────────────────────┐
│  Album Service Handler  │
│                         │
│  1. Find albums with    │
│     this photo          │───→ PostgreSQL: SELECT ...
│  2. Remove photo from   │
│     each album          │───→ PostgreSQL: DELETE ...
│  3. Update photo_count  │───→ PostgreSQL: UPDATE ...
└─────────────────────────┘
```

---

## Data Flow Diagrams

### 1. Add Photos to Album Flow

```
User adds photos to album
    │
    ↓
POST /api/v1/albums/{album_id}/photos
    │
    ↓
┌──────────────────────────────────────┐
│  AlbumService.add_photos_to_album    │
│                                      │
│  Step 1: Validate album ownership    │
│    repository.get_album_by_id() ─────┼──→ PostgreSQL
│                                 ←────┤    Result: Album
│    Check: album.user_id == user_id   │
│                                      │
│  Step 2: Add photos with dedup       │
│    repository.add_photos_to_album()──┼──→ PostgreSQL: INSERT ... ON CONFLICT DO NOTHING
│                                 ←────┤    Result: added_count
│                                      │
│  Step 3: Update photo_count          │
│    repository._update_photo_count()──┼──→ PostgreSQL: UPDATE albums SET photo_count = ...
│                                      │
│  Step 4: Publish event               │
│    publish_album_photo_added() ──────┼──→ NATS: album.photo.added
│                                      │
└──────────────────────────────────────┘
    │
    ↓
Return {success: true, added_count: N, new_photo_count: M}
```

### 2. Smart Frame Sync Flow

```
User initiates album sync
    │
    ↓
POST /api/v1/albums/{album_id}/sync
    │
    ↓
┌──────────────────────────────────────┐
│  AlbumService.sync_album_to_frame    │
│                                      │
│  Step 1: Validate album ownership    │
│    repository.get_album_by_id() ─────┼──→ PostgreSQL
│                                 ←────┤    Result: Album
│                                      │
│  Step 2: Create/Update sync status   │
│    repository.create_or_update_      │
│      sync_status() ──────────────────┼──→ PostgreSQL: UPSERT album_sync_status
│                                 ←────┤    Result: AlbumSyncStatus
│                                      │
│  Step 3: Publish NATS event          │
│    publish_album_synced() ───────────┼──→ NATS: album.synced
│                                      │
│  Step 4: Send MQTT notification      │
│    mqtt_publisher.publish_sync_      │
│      notification() ─────────────────┼──→ MQTT: isa/frame/{frame_id}/sync
│                                      │
└──────────────────────────────────────┘
    │
    ↓
Return AlbumSyncStatusResponse
    │
    ↓
┌────────────────────────────────────┐
│  Smart Frame receives MQTT         │
│  - Downloads photos from storage   │
│  - Reports progress                │
│  - Displays photos                 │
└────────────────────────────────────┘
```

---

## Technology Stack

### Core Technologies
- **Python 3.11+**: Programming language
- **FastAPI 0.104+**: Web framework
- **Pydantic 2.0+**: Data validation
- **asyncio**: Async/await concurrency
- **uvicorn**: ASGI server

### Data Storage
- **PostgreSQL 15+**: Primary database
- **AsyncPostgresClient** (gRPC): Database communication
- **Schema**: `album`
- **Tables**: `albums`, `album_photos`, `album_sync_status`

### Event-Driven
- **NATS 2.9+**: Event bus
- **Subjects**: `album.*`
- **Publishers**: Album Service
- **Subscribers**: notification_service, audit_service, device_service

### Real-Time Communication
- **MQTT** (via gRPC): Smart frame communication
- **Topics**: `isa/frame/{frame_id}/*`

### Service Discovery
- **Consul 1.15+**: Service registry
- **Health Checks**: HTTP `/health`
- **Metadata**: Route registration

### Dependency Injection
- **Protocols (typing.Protocol)**: Interface definitions
- **Factory Pattern**: Production vs test instances
- **ConfigManager**: Environment-based configuration

---

## Security Considerations

### Input Validation
- **Pydantic Models**: All requests validated
- **Name Length**: 1-255 characters enforced
- **Description Length**: Max 1000 characters
- **SQL Injection**: Parameterized queries via gRPC

### Access Control
- **Album Ownership**: All operations validate user_id
- **Family Sharing**: Read access to organization members
- **JWT Authentication**: Handled by API Gateway
- **Permission Errors**: 403 for unauthorized access

### Data Privacy
- **Cascade Delete**: Photos remain when album deleted
- **User Deletion**: All albums cleaned up via event
- **Encryption in Transit**: TLS for all communication

---

## Performance Optimization

### Database Optimization
- **Indexes**: Strategic indexes on user_id, photo_id, display_order
- **GIN Index**: For AI metadata JSONB queries
- **Connection Pooling**: gRPC client pools connections
- **Cascade Delete**: Database handles cleanup efficiently

### API Optimization
- **Async Operations**: All I/O is async
- **Batch Operations**: Multiple photos added in single request
- **Pagination**: Max page_size=100, photo limit=200
- **Photo Deduplication**: ON CONFLICT DO NOTHING

### Event Publishing
- **Non-Blocking**: Event/MQTT failures don't block operations
- **Async Publishing**: Fire-and-forget pattern
- **Error Logging**: Failed publishes logged for debugging

---

## Error Handling

### HTTP Status Codes
- `200 OK`: Successful operation
- `201 Created`: New album created
- `400 Bad Request`: Validation error
- `403 Forbidden`: Permission denied
- `404 Not Found`: Album not found
- `500 Internal Server Error`: Database/unexpected error
- `503 Service Unavailable`: Database unavailable

### Error Response Format
```json
{
  "detail": "Album not found with album_id: album_xyz"
}
```

---

## Testing Strategy

### Contract Testing (Layer 4 & 5)
- **Data Contract**: Pydantic schema validation
- **Logic Contract**: Business rule documentation
- **Component Tests**: Factory, builder, validation tests

### Integration Testing
- **HTTP + Database**: Full request/response cycle
- **Event Publishing**: Verify events published correctly
- **Event Handlers**: Verify cleanup on external events

### API Testing
- **Endpoint Contracts**: All 11 endpoints tested
- **Error Handling**: Validation, not found, permission errors
- **Pagination**: Page boundaries, empty results

### Smoke Testing
- **E2E Scripts**: Bash scripts for critical paths
- **Health Checks**: Service startup validation
- **Database Connectivity**: PostgreSQL availability

---

**Document Version**: 1.0
**Last Updated**: 2025-12-16
**Maintained By**: Album Service Engineering Team
**Related Documents**:
- Domain Context: docs/domain/album_service.md
- PRD: docs/prd/album_service.md
- Data Contract: tests/contracts/album/data_contract.py
- Logic Contract: tests/contracts/album/logic_contract.md
