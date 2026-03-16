# Document Service - System Contract (Layer 6)

## Overview

This document defines HOW document_service implements the 12 standard system patterns.

**Service**: document_service
**Port**: 8227
**Category**: User Microservice (Knowledge Base)
**Version**: 1.0.0

---

## 1. Architecture Pattern

### Service Layer Structure

```
microservices/document_service/
├── __init__.py
├── main.py                 # FastAPI app, routes, DI setup, lifespan
├── document_service.py     # Business logic layer
├── document_repository.py  # Data access layer
├── models.py               # Pydantic models (KnowledgeDocument, etc.)
├── protocols.py            # DI interfaces (Protocol classes)
├── factory.py              # DI factory (create_document_service)
├── routes_registry.py      # Consul route metadata
├── clients/                # Service client implementations
│   ├── __init__.py
│   ├── storage_client.py
│   ├── authorization_client.py
│   └── digital_analytics_client.py
└── events/
    ├── __init__.py
    ├── models.py
    ├── handlers.py
    └── publishers.py
```

### External Dependencies

| Dependency | Type | Purpose | Endpoint |
|------------|------|---------|----------|
| PostgreSQL | gRPC | Document metadata storage | isa-postgres-grpc:50061 |
| Qdrant | HTTP | Vector embeddings for RAG | qdrant:6333 |
| NATS | Native | Event pub/sub | nats:4222 |
| Consul | HTTP | Service registration | consul:8500 |
| storage_service | HTTP | File storage | via service discovery |
| authorization_service | HTTP | Permission checks | localhost:8203 |
| digital_analytics | HTTP | RAG indexing/search | via service discovery |

---

## 2. Dependency Injection Pattern

### Protocol Definition (`protocols.py`)

```python
class DocumentNotFoundError(Exception): ...
class DocumentValidationError(Exception): ...
class DocumentPermissionError(Exception): ...
class DocumentServiceError(Exception): ...

@runtime_checkable
class DocumentRepositoryProtocol(Protocol):
    async def create_document(self, document_data: KnowledgeDocument) -> Optional[KnowledgeDocument]: ...
    async def get_document_by_id(self, doc_id: str) -> Optional[KnowledgeDocument]: ...
    async def list_user_documents(self, user_id: str, ...) -> List[KnowledgeDocument]: ...
    async def update_document(self, doc_id: str, update_data: Dict[str, Any]) -> Optional[KnowledgeDocument]: ...
    async def delete_document(self, doc_id: str, user_id: str, soft: bool = True) -> bool: ...
    async def update_document_permissions(self, doc_id: str, ...) -> bool: ...
    async def check_connection(self) -> bool: ...

class EventBusProtocol(Protocol): ...
class StorageClientProtocol(Protocol): ...
class AuthorizationClientProtocol(Protocol): ...
class DigitalAnalyticsClientProtocol(Protocol): ...
```

### Factory Implementation (`factory.py`)

```python
def create_document_service(config=None, event_bus=None) -> DocumentService:
    from .document_repository import DocumentRepository
    from .clients import StorageServiceClient, AuthorizationServiceClient, DigitalAnalyticsClient
    repository = DocumentRepository(config=config)
    storage_client = StorageServiceClient()
    auth_client = AuthorizationServiceClient()
    digital_client = DigitalAnalyticsClient()
    return DocumentService(
        repository=repository, event_bus=event_bus, config_manager=config,
        storage_client=storage_client, auth_client=auth_client, digital_client=digital_client,
    )
```

---

## 3. Event Publishing Pattern

### Published Events

| Event | Trigger |
|-------|---------|
| `document.created` | New document created and indexed |
| `document.updated` | Document content updated (RAG reindex) |
| `document.deleted` | Document deleted |
| `document.permissions_changed` | Permissions updated |

### Subscribed Events

```python
await event_bus.subscribe_to_events(pattern="*.file.>", handler=..., durable="document-file-consumer-v1")
await event_bus.subscribe_to_events(pattern="*.user.>", handler=..., durable="document-user-consumer-v1")
await event_bus.subscribe_to_events(pattern="*.organization.>", handler=..., durable="document-org-consumer-v1")
```

---

## 4. Error Handling Pattern

| Exception | HTTP Status |
|-----------|-------------|
| DocumentValidationError | 400 |
| DocumentPermissionError | 403 |
| DocumentNotFoundError | 404 |
| DocumentServiceError | 500 |
| General Exception | 500 (global handler) |

---

## 5-6. Client & Repository Pattern

Three service clients for storage, authorization, and digital analytics (RAG). Repository uses AsyncPostgresClient with document versioning support.

---

## 7. Service Registration Pattern (Consul)

```python
SERVICE_METADATA = {
    'service_name': 'document_service',
    'version': '1.0.0',
    'capabilities': [
        'knowledge_base', 'rag_incremental_update',
        'document_permissions', 'semantic_search', 'document_versioning'
    ],
    'tags': ['v1', 'document', 'knowledge_base', 'rag', 'vector_search', 'authorization']
}
```

12 routes: health (2), CRUD (4), RAG update (1), permissions (2), RAG query (2), stats (1).

---

## 8. Health Check Contract

| Endpoint | Auth Required | Purpose |
|----------|---------------|---------|
| `/` | No | Root service status |
| `/health` | No | Basic health check |
| `/api/v1/documents/health` | No | API-versioned health check |

Database connection is verified during startup; service fails to start if DB is unreachable.

---

## 9-12. Event System, Configuration, Logging, Deployment

- NATS with durable consumers for file, user, and organization events
- ConfigManager("document_service") with port 8227
- `setup_service_logger("document_service")`
- GracefulShutdown with signal handlers
- Database health check required during startup (raises RuntimeError on failure)

---

## System Contract Checklist

- [x] `protocols.py` defines Document, EventBus, Storage, Authorization, DigitalAnalytics protocols
- [x] `factory.py` creates service with 3 client dependencies
- [x] RAG incremental update support (FULL, SMART, DIFF strategies)
- [x] Permission-filtered RAG queries
- [x] Document versioning
- [x] Durable NATS consumers for file/user/org events
- [x] Consul TTL registration with 5 capabilities

---

## Reference Files

| File | Purpose |
|------|---------|
| `microservices/document_service/main.py` | FastAPI app, routes, lifespan |
| `microservices/document_service/document_service.py` | Business logic |
| `microservices/document_service/document_repository.py` | Data access |
| `microservices/document_service/protocols.py` | DI interfaces |
| `microservices/document_service/factory.py` | DI factory |
| `microservices/document_service/routes_registry.py` | Consul metadata |
| `microservices/document_service/events/` | Event handlers, models, publishers |
