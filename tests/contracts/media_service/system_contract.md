# Media Service - System Contract (Layer 6)

## Overview

This document defines HOW media_service implements the 12 standard system patterns.

**Service**: media_service
**Port**: 8222
**Category**: User Microservice (Smart Frame Ecosystem)
**Version**: 1.0.0

---

## 1. Architecture Pattern

### Service Layer Structure

```
microservices/media_service/
├── __init__.py
├── main.py                 # FastAPI app, routes, DI setup, lifespan
├── media_service.py        # Business logic layer
├── media_repository.py     # Data access layer
├── models.py               # Pydantic models (PhotoVersion, Playlist, etc.)
├── protocols.py            # DI interfaces (Protocol classes)
├── factory.py              # DI factory (create_media_service)
├── routes_registry.py      # Consul route metadata
├── client.py               # HTTP client for inter-service calls
├── clients/                # Service client implementations
├── events.py               # Legacy events (deprecated)
└── events/
    ├── __init__.py
    ├── models.py
    ├── handlers.py
    └── publishers.py
```

### External Dependencies

| Dependency | Type | Purpose | Endpoint |
|------------|------|---------|----------|
| PostgreSQL | gRPC | Primary data store | isa-postgres-grpc:50061 |
| NATS | Native | Event pub/sub | nats:4222 |
| Consul | HTTP | Service registration | consul:8500 |
| storage_service | HTTP | File storage | via service discovery |
| device_service | HTTP | Frame device data | localhost:8220 |

---

## 2. Dependency Injection Pattern

### Protocol Definition (`protocols.py`)

```python
class MediaServiceError(Exception): ...
class MediaNotFoundError(MediaServiceError): ...
class MediaValidationError(MediaServiceError): ...
class MediaPermissionError(MediaServiceError): ...

@runtime_checkable
class MediaRepositoryProtocol(Protocol):
    # Photo Version operations
    async def create_photo_version(self, version_data: PhotoVersion) -> Optional[PhotoVersion]: ...
    async def get_photo_version(self, version_id: str) -> Optional[PhotoVersion]: ...
    async def list_photo_versions(self, photo_id: str, user_id: str) -> List[PhotoVersion]: ...
    # Photo Metadata operations
    async def create_or_update_metadata(self, metadata: PhotoMetadata) -> Optional[PhotoMetadata]: ...
    async def get_photo_metadata(self, file_id: str) -> Optional[PhotoMetadata]: ...
    # Playlist operations
    async def create_playlist(self, playlist_data: Playlist) -> Optional[Playlist]: ...
    async def list_user_playlists(self, user_id: str, ...) -> List[Playlist]: ...
    # Rotation Schedule operations
    async def create_rotation_schedule(self, schedule_data: RotationSchedule) -> Optional[RotationSchedule]: ...
    async def list_frame_schedules(self, frame_id: str) -> List[RotationSchedule]: ...
    # Photo Cache operations
    async def create_photo_cache(self, cache_data: PhotoCache) -> Optional[PhotoCache]: ...
    async def list_frame_cache(self, frame_id: str) -> List[PhotoCache]: ...
    async def check_connection(self) -> bool: ...

class EventBusProtocol(Protocol): ...
class StorageClientProtocol(Protocol): ...
class DeviceClientProtocol(Protocol): ...
```

### Factory Implementation (`factory.py`)

```python
def create_media_service(config=None, event_bus=None) -> MediaService:
    from .media_repository import MediaRepository
    repository = MediaRepository(config=config)
    storage_client = StorageServiceClient()  # optional
    device_client = DeviceServiceClient()    # optional
    return MediaService(
        repository=repository, event_bus=event_bus,
        storage_client=storage_client, device_client=device_client,
    )
```

---

## 3. Event Publishing Pattern

### Published Events

| Event | Trigger |
|-------|---------|
| `media.version_created` | Photo version created |
| `media.playlist_created` | Playlist created |
| `media.schedule_created` | Rotation schedule created |
| `media.cache_updated` | Cache status changed |

### Subscribed Events

Subscribes to file upload, device status, and album events for cache management and playlist synchronization.

---

## 4. Error Handling Pattern

| Exception | HTTP Status |
|-----------|-------------|
| MediaValidationError | 400 |
| MediaPermissionError | 403 |
| MediaNotFoundError | 404 |
| MediaServiceError | 500 |

---

## 5-6. Client & Repository Pattern

Storage and device service clients. Repository manages photo versions, metadata, playlists, rotation schedules, and photo cache.

---

## 7. Service Registration Pattern (Consul)

```python
SERVICE_METADATA = {
    "service_name": "media_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "media-management", "photo-frame"],
    "capabilities": [
        "file_upload", "photo_versions", "metadata_management",
        "playlist_management", "rotation_schedules", "photo_cache", "gallery_api"
    ]
}
```

30 routes: health (3), file upload (1), photo versions (6), metadata (1), playlists (2), schedules (4), cache (3), gallery (10).

---

## 8. Health Check Contract

| Endpoint | Auth Required | Purpose |
|----------|---------------|---------|
| `/` | No | Root health check |
| `/health` | No | Basic health check |
| `/api/v1/media/health` | No | API-versioned health check |

---

## 9-12. Event System, Configuration, Logging, Deployment

- NATS event bus for media lifecycle events
- ConfigManager("media_service") with port 8222
- `setup_service_logger("media_service")`
- GracefulShutdown with signal handlers
- Database health check on startup

---

## System Contract Checklist

- [x] `protocols.py` defines Media, EventBus, Storage, Device protocols
- [x] `factory.py` creates service with optional storage and device clients
- [x] Gallery API endpoints for smart frame ecosystem
- [x] Photo cache management (preload, clear, stats)
- [x] Rotation schedule support
- [x] Consul TTL registration with 30 routes and 7 capabilities

---

## Reference Files

| File | Purpose |
|------|---------|
| `microservices/media_service/main.py` | FastAPI app, routes, lifespan |
| `microservices/media_service/media_service.py` | Business logic |
| `microservices/media_service/media_repository.py` | Data access |
| `microservices/media_service/protocols.py` | DI interfaces |
| `microservices/media_service/factory.py` | DI factory |
| `microservices/media_service/routes_registry.py` | Consul metadata |
| `microservices/media_service/events/` | Event handlers, models, publishers |
