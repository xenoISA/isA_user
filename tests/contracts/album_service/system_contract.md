# Album Service - System Contract (Layer 6)

## Overview

This document defines HOW album_service implements the 12 standard system patterns.

**Service**: album_service
**Port**: 8219
**Category**: User Microservice
**Version**: 1.0.0

---

## 1. Architecture Pattern

### Service Layer Structure

```
microservices/album_service/
├── __init__.py
├── main.py                          # FastAPI app, routes, DI setup, lifespan
├── album_service.py                 # Business logic layer
├── album_repository.py              # Data access layer
├── models.py                        # Pydantic models (Album, AlbumPhoto, etc.)
├── protocols.py                     # DI interfaces
├── factory.py                       # DI factory
├── routes_registry.py               # Consul route metadata
├── client.py                        # Service client
├── clients/
│   ├── __init__.py
│   ├── account_client.py
│   ├── media_client.py
│   └── storage_client.py
├── events/
│   ├── __init__.py
│   ├── models.py                    # Event models (album + inbound file/device events)
│   ├── handlers.py                  # AlbumEventHandler class
│   └── publishers.py
├── mqtt/
│   ├── __init__.py
│   └── publisher.py                 # AlbumMQTTPublisher (smart frame notifications)
└── migrations/
    ├── 000_init_schema.sql
    └── 001_create_album_tables.sql
```

### External Dependencies

| Dependency | Type | Purpose | Endpoint |
|------------|------|---------|----------|
| PostgreSQL | AsyncPostgresClient | Primary data store | postgres:5432 |
| NATS | Native | Event pub/sub | nats:4222 |
| Consul | HTTP | Service registration | consul:8500 |
| MQTT (gRPC) | gRPC | Smart frame push notifications | mqtt-grpc:50053 |

---

## 2. Dependency Injection Pattern

### Protocol Definition (`protocols.py`)

```python
@runtime_checkable
class AlbumRepositoryProtocol(Protocol):
    async def create_album(self, album_data: Album) -> Optional[Album]: ...
    async def get_album_by_id(self, album_id: str, user_id=None) -> Optional[Album]: ...
    async def list_user_albums(self, user_id: str, organization_id=None, is_family_shared=None, limit=50, offset=0) -> List[Album]: ...
    async def update_album(self, album_id: str, user_id: str, update_data: Dict) -> bool: ...
    async def delete_album(self, album_id: str, user_id: str) -> bool: ...
    async def add_photos_to_album(self, album_id: str, photo_ids: List[str], added_by: str) -> int: ...
    async def remove_photos_from_album(self, album_id: str, photo_ids: List[str]) -> int: ...
    async def get_album_photos(self, album_id: str, limit=50, offset=0) -> List[AlbumPhoto]: ...
    async def get_album_sync_status(self, album_id: str, frame_id: str) -> Optional[AlbumSyncStatus]: ...
    async def update_album_sync_status(self, album_id: str, frame_id: str, user_id: str, status_data: Dict) -> bool: ...
    async def remove_photo_from_all_albums(self, photo_id: str) -> int: ...
    async def delete_sync_status_by_frame(self, frame_id: str) -> int: ...
    async def check_connection(self) -> bool: ...

class EventBusProtocol(Protocol):
    async def publish_event(self, event: Any) -> None: ...
```

### Custom Exceptions

| Exception | HTTP Status |
|-----------|-------------|
| AlbumNotFoundError | 404 |
| AlbumValidationError | 400 |
| AlbumPermissionError | 403 |
| AlbumServiceError | 500 |

---

## 3. Factory Implementation

```python
def create_album_service(config=None, event_bus=None) -> AlbumService:
    from .album_repository import AlbumRepository
    repository = AlbumRepository(config=config)
    return AlbumService(repository=repository, event_bus=event_bus)
```

---

## 4. Singleton Management

Global variable pattern:
```python
album_service = None
mqtt_publisher: Optional[AlbumMQTTPublisher] = None
```

---

## 5. Service Registration (Consul)

- **Route count**: 8 routes
- **Base path**: `/api/v1/albums`
- **Tags**: `["v1", "user-microservice", "album-management", "photo-organization"]`
- **Capabilities**: album_management, photo_organization, album_sync, frame_integration, photo_sharing
- **Health check type**: TTL

---

## 6. Health Check Contract

| Endpoint | Auth | Response |
|----------|------|----------|
| `/health` | No | `{status, service, timestamp}` |
| `/api/v1/albums/health` | No | Same |
| `/` | No | Root health check |

---

## 7. Event System Contract (NATS)

### Published Events

| Event | Subject | Trigger |
|-------|---------|---------|
| `album.created` | `album.created` | Album created |
| `album.updated` | `album.updated` | Album updated |
| `album.deleted` | `album.deleted` | Album deleted |
| `album.photo.added` | `album.photo.added` | Photo added to album |
| `album.photo.removed` | `album.photo.removed` | Photo removed |
| `album.synced` | `album.synced` | Album synced to frame |

### Subscribed Events

| Pattern | Source | Handler |
|---------|--------|---------|
| `storage_service.file.uploaded.with_ai` | storage_service | Auto-add photo to album |
| `storage_service.file.deleted` | storage_service | Remove photo from all albums |
| `device_service.device.deleted` | device_service | Clean up sync status |
| `account_service.user.deleted` | account_service | Delete all user albums |

Event handler uses class-based pattern (`AlbumEventHandler`).

### MQTT Integration

Album service publishes MQTT messages to smart frames via `AlbumMQTTPublisher`:
- `MQTTPhotoAddedMessage` - Photo added notification
- `MQTTAlbumSyncMessage` - Full album sync
- `MQTTFrameCommandMessage` - Frame control commands

---

## 8. Configuration Contract

| Variable | Description | Default |
|----------|-------------|---------|
| `ALBUM_SERVICE_PORT` | HTTP port | 8219 |
| `MQTT_HOST` | MQTT gRPC host | mqtt-grpc |
| `MQTT_PORT` | MQTT gRPC port | 50053 |

---

## 9. Error Handling Contract

Route handlers use try/except with exception type mapping to HTTP status codes.

---

## 10. Logging Contract

```python
app_logger = setup_service_logger("album_service")
```

---

## 11. Testing Contract

```python
mock_repo = AsyncMock(spec=AlbumRepositoryProtocol)
service = AlbumService(repository=mock_repo, event_bus=AsyncMock())
```

---

## 12. Deployment Contract

### Lifecycle

1. Install signal handlers
2. Initialize MQTT publisher (connect to mqtt-grpc)
3. Initialize NATS event bus
4. Create AlbumService via factory
5. Set up AlbumEventHandler with repo, service, and mqtt_publisher
6. Subscribe to events
7. Consul TTL registration
8. **yield**
9. Graceful shutdown
10. Consul deregistration
11. Event bus close

### Special: Smart Frame Integration

Album service uniquely integrates with MQTT for real-time smart frame push notifications. When photos are added or albums synced, MQTT messages are published to frame-specific topics.

---

## Reference Files

| File | Purpose |
|------|---------|
| `microservices/album_service/main.py` | FastAPI app, routes, lifespan |
| `microservices/album_service/album_service.py` | Business logic |
| `microservices/album_service/album_repository.py` | Data access |
| `microservices/album_service/protocols.py` | DI interfaces |
| `microservices/album_service/factory.py` | DI factory |
| `microservices/album_service/models.py` | Pydantic schemas |
| `microservices/album_service/routes_registry.py` | Consul metadata |
| `microservices/album_service/events/handlers.py` | AlbumEventHandler class |
| `microservices/album_service/events/models.py` | Event + MQTT models |
| `microservices/album_service/mqtt/publisher.py` | MQTT smart frame publisher |
