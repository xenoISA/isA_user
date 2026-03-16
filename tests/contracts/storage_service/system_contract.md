# Storage Service - System Contract (Layer 6)

## Overview

This document defines HOW storage_service implements the 12 standard system patterns.

**Service**: storage_service
**Port**: 8209
**Category**: User Microservice
**Version**: 1.0.0

---

## 1. Architecture Pattern

### Service Layer Structure

```
microservices/storage_service/
├── main.py                          # FastAPI app, routes, DI setup, lifespan
├── storage_service.py               # Business logic (MinIO + DB)
├── storage_repository.py            # Data access layer
├── models.py                        # Pydantic models (StoredFile, FileShare, etc.)
├── protocols.py                     # DI interfaces
├── factory.py                       # DI factory
├── routes_registry.py               # Consul route metadata (44 routes)
├── client.py                        # Service client
├── clients/
│   ├── __init__.py
│   ├── account_client.py
│   └── organization_client.py
├── events/
│   ├── __init__.py
│   ├── models.py
│   ├── handlers.py
│   └── publishers.py               # StorageEventPublisher class
└── migrations/
    ├── 000_init_schema.sql
    ├── 001_create_storage_files_table.sql
    ├── 002_create_file_shares_table.sql
    ├── 003_create_storage_quotas_table.sql
    ├── 004_add_intelligence_index.sql
    └── 005_add_chunk_id_mapping.sql
```

### External Dependencies

| Dependency | Type | Purpose | Endpoint |
|------------|------|---------|----------|
| PostgreSQL | AsyncPostgresClient | File metadata store | postgres:5432 |
| MinIO | S3 API | Object storage | minio:9000 |
| NATS | Native | Event pub/sub | nats:4222 |
| Consul | HTTP | Service registration | consul:8500 |

---

## 2. Dependency Injection Pattern

### Protocol Definition (`protocols.py`)

```python
class StorageServiceError(Exception): ...
class FileNotFoundError(Exception): ...
class QuotaExceededError(Exception): ...

@runtime_checkable
class StorageRepositoryProtocol(Protocol):
    async def check_connection(self) -> bool: ...
    async def create_file_record(self, file_data: StoredFile) -> Optional[StoredFile]: ...
    async def get_file_by_id(self, file_id: str, user_id=None) -> Optional[StoredFile]: ...
    async def list_user_files(self, user_id: str, ...) -> List[StoredFile]: ...
    async def update_file_status(self, file_id: str, user_id: str, status: FileStatus, ...) -> bool: ...
    async def delete_file(self, file_id: str, user_id: str) -> bool: ...
    async def create_file_share(self, share_data: FileShare) -> Optional[FileShare]: ...
    async def get_storage_quota(self, quota_type: str, entity_id: str) -> Optional[StorageQuota]: ...
    async def update_storage_usage(self, quota_type: str, entity_id: str, bytes_delta: int, ...) -> bool: ...

class EventBusProtocol(Protocol):
    async def publish_event(self, event: Any) -> None: ...
```

---

## 3. Factory Implementation

```python
def create_storage_service(config=None, config_manager=None, event_bus=None, event_publisher=None) -> StorageService:
    return StorageService(config=config, config_manager=config_manager, event_bus=event_bus, event_publisher=event_publisher)
```

Note: main.py creates StorageService directly, not via factory.

---

## 4. Singleton Management

Global variable pattern:
```python
storage_service = None
event_bus = None
event_publisher = None
```

---

## 5. Service Registration (Consul)

- **Route count**: 44 routes
- **Base path**: `/api/v1/storage`
- **Tags**: `["v1", "user-microservice", "storage"]`
- **Capabilities**: file_storage, photo_management, semantic_search, rag_queries, album_management, gallery_display, image_ai
- **Health check type**: TTL

---

## 6. Health Check Contract

| Endpoint | Auth | Response |
|----------|------|----------|
| `/health` | No | `{status, service, timestamp}` |
| `/api/v1/storage/health` | No | Same |
| `/info` | No | Service info with capabilities |

Database connection check on startup (raises RuntimeError if failed).

---

## 7. Event System Contract (NATS)

### Event Publisher

Uses `StorageEventPublisher` class (initialized with event_bus).

### Subscribed Events

Handler map from `get_event_handlers(storage_service, intelligence_service, event_bus)` with durable consumers:
- `storage-{pattern}-consumer` naming convention

---

## 8. Configuration Contract

| Variable | Description | Default |
|----------|-------------|---------|
| `STORAGE_SERVICE_PORT` | HTTP port | 8209 |
| `MINIO_ENDPOINT` | MinIO endpoint | minio:9000 |
| `MINIO_ACCESS_KEY` | MinIO access key | required |
| `MINIO_SECRET_KEY` | MinIO secret key | required |

Rate limiting:
- Default: 60 req/min
- Upload: 10 req/min

---

## 9. Error Handling Contract

Global exception handlers:
```python
@app.exception_handler(HTTPException) -> JSONResponse
@app.exception_handler(Exception) -> 500 JSONResponse
```

Authentication via `get_authenticated_user_id()` with JWT/API Key/Internal Service support.

---

## 10. Logging Contract

```python
app_logger = setup_service_logger("storage_service")
```

---

## 11. Testing Contract

```python
mock_repo = AsyncMock(spec=StorageRepositoryProtocol)
```

---

## 12. Deployment Contract

### Lifecycle

1. Install signal handlers
2. Initialize event bus
3. Initialize StorageEventPublisher
4. Create StorageService
5. Check database connection (fail-fast)
6. Subscribe to events with durable consumers
7. Consul TTL registration
8. **yield**
9. Graceful shutdown
10. Consul deregistration
11. Event bus close

---

## Reference Files

| File | Purpose |
|------|---------|
| `microservices/storage_service/main.py` | FastAPI app, routes, lifespan |
| `microservices/storage_service/storage_service.py` | Business logic |
| `microservices/storage_service/storage_repository.py` | Data access |
| `microservices/storage_service/protocols.py` | DI interfaces |
| `microservices/storage_service/factory.py` | DI factory |
| `microservices/storage_service/models.py` | Pydantic schemas |
| `microservices/storage_service/routes_registry.py` | Consul metadata |
| `microservices/storage_service/events/handlers.py` | NATS handlers |
| `microservices/storage_service/events/publishers.py` | StorageEventPublisher |
