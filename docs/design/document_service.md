# Document Service - Design Document

## Architecture Overview

### Service Architecture (ASCII diagram)

```
┌────────────────────────────────────────────────────────────────────┐
│                      Document Service (Port 8227)                    │
├────────────────────────────────────────────────────────────────────┤
│  FastAPI Application (main.py)                                       │
│  ├─ Route Handlers                                                   │
│  ├─ Dependency Injection Setup                                       │
│  └─ Lifespan Management                                              │
├────────────────────────────────────────────────────────────────────┤
│  Service Layer (document_service.py)                                 │
│  ├─ Business Logic                                                   │
│  ├─ Permission Checking                                              │
│  ├─ Event Publishing                                                 │
│  └─ Service Client Coordination                                      │
├────────────────────────────────────────────────────────────────────┤
│  Repository Layer (document_repository.py)                           │
│  ├─ Database Queries                                                 │
│  ├─ CRUD Operations                                                  │
│  └─ Statistics Aggregation                                           │
├────────────────────────────────────────────────────────────────────┤
│  Dependency Injection (protocols.py + factory.py)                    │
│  ├─ DocumentRepositoryProtocol                                       │
│  ├─ EventBusProtocol                                                 │
│  ├─ StorageClientProtocol                                            │
│  ├─ AuthorizationClientProtocol                                      │
│  └─ DigitalAnalyticsClientProtocol                                   │
├────────────────────────────────────────────────────────────────────┤
│  Events Layer (events/)                                              │
│  ├─ DocumentEventHandler (handlers.py)                               │
│  └─ DocumentEventPublisher (publishers.py)                           │
├────────────────────────────────────────────────────────────────────┤
│  Service Clients (clients/)                                          │
│  ├─ StorageServiceClient                                             │
│  ├─ AuthorizationServiceClient                                       │
│  └─ DigitalAnalyticsClient                                           │
└────────────────────────────────────────────────────────────────────┘

External Dependencies:
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│   PostgreSQL        │  │      NATS           │  │  Digital Analytics  │
│   (via gRPC)        │  │   (Event Bus)       │  │     Service         │
│   Port: 50061       │  │   Port: 4222        │  │   (RAG/Vector)      │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘
         │                        │                        │
         └────────────────────────┴────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │     Consul Registry       │
                    │   (Service Discovery)     │
                    └───────────────────────────┘
```

### Component Interaction Flow

```
User Request
     │
     ▼
┌─────────────┐
│  FastAPI    │
│  Router     │
└─────────────┘
     │
     ▼
┌─────────────┐     ┌─────────────────────┐
│  Document   │────▶│  Permission Check   │
│  Service    │     │  (Auth Client)      │
└─────────────┘     └─────────────────────┘
     │
     ├──────────────────────┐
     │                      │
     ▼                      ▼
┌─────────────┐     ┌─────────────────────┐
│  Repository │     │  Digital Analytics  │
│  (PostgreSQL)│    │  (RAG/Indexing)     │
└─────────────┘     └─────────────────────┘
     │                      │
     ▼                      ▼
┌─────────────┐     ┌─────────────────────┐
│  Event Bus  │     │  Storage Service    │
│  (NATS)     │     │  (File Content)     │
└─────────────┘     └─────────────────────┘
```

---

## Component Design

### Service Layer (DocumentService)

**File**: `microservices/document_service/document_service.py`

**Responsibilities**:
- Business logic orchestration
- Permission validation
- Event publishing
- Service client coordination
- Request validation

**Key Methods**:
```python
class DocumentService:
    # Document CRUD
    async def create_document(request, user_id, organization_id) -> DocumentResponse
    async def get_document(doc_id, user_id) -> DocumentResponse
    async def list_user_documents(user_id, filters) -> List[DocumentResponse]
    async def delete_document(doc_id, user_id, permanent) -> bool

    # RAG Operations
    async def update_document_incremental(doc_id, request, user_id) -> DocumentResponse
    async def rag_query_secure(request, user_id, organization_id) -> RAGQueryResponse
    async def semantic_search_secure(request, user_id, organization_id) -> SemanticSearchResponse

    # Permission Management
    async def update_document_permissions(doc_id, request, user_id) -> DocumentPermissionResponse
    async def get_document_permissions(doc_id, user_id) -> DocumentPermissionResponse

    # Statistics
    async def get_user_stats(user_id, organization_id) -> DocumentStatsResponse

    # Health
    async def check_health() -> Dict[str, Any]
```

### Repository Layer (DocumentRepository)

**File**: `microservices/document_service/document_repository.py`

**Responsibilities**:
- Database CRUD operations
- Query building
- Data conversion
- Connection management

**Database Client**: AsyncPostgresClient (gRPC-based)

**Key Methods**:
```python
class DocumentRepository:
    # Document Operations
    async def create_document(document_data) -> KnowledgeDocument
    async def get_document_by_id(doc_id) -> KnowledgeDocument
    async def get_document_by_file_id(file_id, user_id) -> KnowledgeDocument
    async def list_user_documents(user_id, filters) -> List[KnowledgeDocument]
    async def update_document(doc_id, update_data) -> KnowledgeDocument
    async def update_document_status(doc_id, status, chunk_count) -> bool
    async def delete_document(doc_id, user_id, soft) -> bool

    # Version Operations
    async def create_document_version(base_doc_id, new_file_id, ...) -> KnowledgeDocument
    async def mark_version_as_old(doc_id) -> bool
    async def list_document_versions(file_id, user_id) -> List[KnowledgeDocument]

    # Permission Operations
    async def update_document_permissions(doc_id, access_level, ...) -> bool
    async def record_permission_change(history_data) -> bool
    async def get_permission_history(doc_id, limit) -> List[DocumentPermissionHistory]

    # Statistics
    async def get_user_stats(user_id, organization_id) -> Dict[str, Any]

    # Health
    async def check_connection() -> bool
```

### Protocols Layer (Dependency Injection)

**File**: `microservices/document_service/protocols.py`

**Purpose**: Define interfaces for testability

```python
@runtime_checkable
class DocumentRepositoryProtocol(Protocol):
    """Interface for Document Repository"""
    ...

@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for Event Bus"""
    ...

@runtime_checkable
class StorageClientProtocol(Protocol):
    """Interface for Storage Service Client"""
    ...

@runtime_checkable
class AuthorizationClientProtocol(Protocol):
    """Interface for Authorization Service Client"""
    ...

@runtime_checkable
class DigitalAnalyticsClientProtocol(Protocol):
    """Interface for Digital Analytics Client"""
    ...
```

### Factory Layer

**File**: `microservices/document_service/factory.py`

**Purpose**: Create service instances with real dependencies

```python
def create_document_service(
    config: Optional[ConfigManager] = None,
    event_bus = None,
) -> DocumentService:
    """Create DocumentService with real dependencies"""
    from .document_repository import DocumentRepository
    repository = DocumentRepository(config=config)
    return DocumentService(repository=repository, event_bus=event_bus, ...)
```

---

## Database Schemas

### Schema: document

#### Table: knowledge_documents

```sql
CREATE TABLE IF NOT EXISTS document.knowledge_documents (
    doc_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    organization_id VARCHAR(50),

    -- Document Info
    title VARCHAR(500) NOT NULL,
    description TEXT,
    doc_type VARCHAR(20) NOT NULL,
    file_id VARCHAR(100) NOT NULL,
    file_size BIGINT DEFAULT 0,
    file_url TEXT,

    -- Version Control
    version INTEGER DEFAULT 1,
    parent_version_id VARCHAR(50),
    is_latest BOOLEAN DEFAULT true,

    -- RAG Indexing
    status VARCHAR(20) DEFAULT 'draft',
    chunk_count INTEGER DEFAULT 0,
    chunking_strategy VARCHAR(20) DEFAULT 'semantic',
    indexed_at TIMESTAMP WITH TIME ZONE,
    last_updated_at TIMESTAMP WITH TIME ZONE,

    -- Authorization
    access_level VARCHAR(20) DEFAULT 'private',
    allowed_users JSONB DEFAULT '[]'::jsonb,
    allowed_groups JSONB DEFAULT '[]'::jsonb,
    denied_users JSONB DEFAULT '[]'::jsonb,

    -- Qdrant Info
    collection_name VARCHAR(100) DEFAULT 'default',
    point_ids JSONB DEFAULT '[]'::jsonb,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    tags JSONB DEFAULT '[]'::jsonb,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_documents_user_id ON document.knowledge_documents(user_id);
CREATE INDEX idx_documents_organization_id ON document.knowledge_documents(organization_id);
CREATE INDEX idx_documents_file_id ON document.knowledge_documents(file_id);
CREATE INDEX idx_documents_status ON document.knowledge_documents(status);
CREATE INDEX idx_documents_doc_type ON document.knowledge_documents(doc_type);
CREATE INDEX idx_documents_is_latest ON document.knowledge_documents(is_latest);
CREATE INDEX idx_documents_created_at ON document.knowledge_documents(created_at);
```

#### Table: document_permission_history

```sql
CREATE TABLE IF NOT EXISTS document.document_permission_history (
    history_id SERIAL PRIMARY KEY,
    doc_id VARCHAR(50) NOT NULL REFERENCES document.knowledge_documents(doc_id),
    changed_by VARCHAR(50) NOT NULL,

    -- Permission Changes
    old_access_level VARCHAR(20),
    new_access_level VARCHAR(20),
    users_added JSONB DEFAULT '[]'::jsonb,
    users_removed JSONB DEFAULT '[]'::jsonb,
    groups_added JSONB DEFAULT '[]'::jsonb,
    groups_removed JSONB DEFAULT '[]'::jsonb,

    -- Timestamp
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index
CREATE INDEX idx_permission_history_doc_id ON document.document_permission_history(doc_id);
CREATE INDEX idx_permission_history_changed_at ON document.document_permission_history(changed_at);
```

---

## Data Flow Diagrams

### Document Creation Flow

```
Client -> POST /api/v1/documents
  -> RouteHandler
    -> get_user_id(user_id from query)
    -> get_document_service()
    -> DocumentService.create_document(request, user_id, organization_id)
      -> _validate_document_create_request(request)
      -> Generate doc_id: doc_{uuid.hex[:12]}
      -> StorageClient.get_file_info(file_id, user_id) [optional]
      -> Create KnowledgeDocument model
      -> Repository.create_document(document)
        -> PostgreSQL INSERT via gRPC
      <- KnowledgeDocument
      -> _index_document_async(document, user_id) [background]
        -> Repository.update_document_status(INDEXING)
        -> _download_file_content(file_id, user_id)
        -> DigitalAnalyticsClient.store_content(...)
        -> Repository.update_document_status(INDEXED, chunk_count)
      -> EventBus.publish_event(document.created)
        -> NATS
      <- DocumentResponse
    <- HTTP 201 {response}
```

### RAG Query Flow

```
Client -> POST /api/v1/documents/rag/query
  -> RouteHandler
    -> get_user_id(user_id from query)
    -> DocumentService.rag_query_secure(request, user_id, organization_id)
      -> Start timer
      -> DigitalAnalyticsClient.generate_response(
           user_id, query, collection_name=user_{user_id}, top_k)
        -> Digital Analytics Service
        <- {response, sources}
      -> Build RAGQueryResponse
      <- RAGQueryResponse with latency_ms
    <- HTTP 200 {response}
```

### Permission Update Flow

```
Client -> PUT /api/v1/documents/{doc_id}/permissions
  -> RouteHandler
    -> get_user_id(user_id from query)
    -> DocumentService.update_document_permissions(doc_id, request, user_id)
      -> Repository.get_document_by_id(doc_id)
        -> PostgreSQL SELECT via gRPC
      <- KnowledgeDocument
      -> _check_document_permission(user_id, document, "admin")
        -> Check owner OR authorization_service
      -> Build new permission state
      -> Repository.update_document_permissions(doc_id, ...)
        -> PostgreSQL UPDATE via gRPC
      -> Repository.record_permission_change(history)
        -> PostgreSQL INSERT via gRPC
      -> EventBus.publish_event(document.permission.updated)
        -> NATS
      <- DocumentPermissionResponse
    <- HTTP 200 {response}
```

### Document Delete Flow

```
Client -> DELETE /api/v1/documents/{doc_id}
  -> RouteHandler
    -> get_user_id(user_id from query)
    -> DocumentService.delete_document(doc_id, user_id, permanent)
      -> Repository.get_document_by_id(doc_id)
      <- KnowledgeDocument
      -> _check_document_permission(user_id, document, "delete")
      -> Repository.delete_document(doc_id, user_id, soft=!permanent)
        -> PostgreSQL UPDATE/DELETE via gRPC
      -> EventBus.publish_event(document.deleted)
        -> NATS
      <- success: bool
    <- HTTP 200 {success, message}
```

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| **Language** | Python 3.9+ |
| **Framework** | FastAPI |
| **Validation** | Pydantic v2 |
| **Database** | PostgreSQL (via gRPC AsyncPostgresClient) |
| **Vector DB** | Qdrant (via Digital Analytics) |
| **Event Bus** | NATS |
| **HTTP Client** | httpx (async) |
| **Service Discovery** | Consul |

---

## Security Considerations

### Authentication
- All endpoints require `user_id` query parameter
- `user_id` validated against account_service
- X-Internal-Call header for internal service calls

### Authorization
- Document owner has full access
- `denied_users` blacklist overrides all other permissions
- `allowed_users/allowed_groups` whitelist for explicit access
- `access_level` controls default visibility:
  - PRIVATE: Only owner
  - TEAM: Team members (via authorization_service)
  - ORGANIZATION: Organization members
  - PUBLIC: Anyone

### Data Protection
- Sensitive data (permissions, content) not logged
- File content accessed via storage_service with user validation
- Collection scoped to user for data isolation

### Input Validation
- Pydantic models validate all request data
- Title length limit: 500 characters
- Description length limit: 2000 characters
- Query length limit: enforced at model level

---

## Event-Driven Architecture

### Published Events

| Event | Subject Pattern | Payload |
|-------|-----------------|---------|
| document.created | `document.document.created` | `{doc_id, user_id, title, doc_type, timestamp}` |
| document.updated | `document.document.updated` | `{doc_id, old_doc_id, version, user_id, timestamp}` |
| document.deleted | `document.document.deleted` | `{doc_id, user_id, permanent, timestamp}` |
| document.permission.updated | `document.document.permission.updated` | `{doc_id, user_id, access_level, timestamp}` |

### Consumed Events

| Event Pattern | Source | Handler Action |
|---------------|--------|----------------|
| `*.file.>` | storage_service | Clean up documents referencing deleted files |
| `*.user.>` | account_service | Delete user's documents on user deletion |
| `*.organization.>` | organization_service | Update organization references |

### Event Handler

```python
class DocumentEventHandler:
    async def handle_event(self, msg):
        event_type = extract_event_type(msg)
        if event_type == "file.deleted":
            await self._handle_file_deleted(msg)
        elif event_type == "user.deleted":
            await self._handle_user_deleted(msg)
        elif event_type == "organization.deleted":
            await self._handle_organization_deleted(msg)
```

---

## Error Handling

### Exception Hierarchy

```
DocumentServiceError (base)
├── DocumentNotFoundError -> 404
├── DocumentValidationError -> 400
└── DocumentPermissionError -> 403
```

### HTTP Error Mapping

| Exception | HTTP Code | Response |
|-----------|-----------|----------|
| DocumentNotFoundError | 404 | `{"error": "Document not found", "status_code": 404}` |
| DocumentValidationError | 400 | `{"error": "Validation error message", "status_code": 400}` |
| DocumentPermissionError | 403 | `{"error": "Access denied", "status_code": 403}` |
| HTTPException | varies | `{"error": "...", "status_code": ...}` |
| Exception (unhandled) | 500 | `{"error": "Internal server error", "status_code": 500}` |

---

## Performance Considerations

### Query Optimization
- Indexes on frequently queried columns (user_id, status, doc_type)
- LIMIT/OFFSET pagination for list queries
- Collection scoping reduces search space

### Async Operations
- All I/O operations are async
- Document indexing runs as background task
- Event publishing non-blocking

### Caching Strategy
- No in-memory caching (stateless design)
- Digital Analytics may cache embeddings
- Consider Redis caching for hot documents

### Connection Management
- Async database client with connection pooling
- HTTP client with connection reuse
- Graceful shutdown releases connections

---

## Deployment Configuration

### Environment Variables

```bash
# Service Configuration
SERVICE_PORT=8227
SERVICE_NAME=document_service

# Database
POSTGRES_HOST=isa-postgres-grpc
POSTGRES_PORT=50061

# NATS
NATS_URL=nats://nats:4222

# Consul
CONSUL_ENABLED=true
CONSUL_HOST=consul
CONSUL_PORT=8500

# Digital Analytics
DIGITAL_ANALYTICS_URL=http://digital-analytics:8300
```

### Health Check

```yaml
# Kubernetes liveness/readiness probe
livenessProbe:
  httpGet:
    path: /health
    port: 8227
  initialDelaySeconds: 10
  periodSeconds: 30
readinessProbe:
  httpGet:
    path: /health
    port: 8227
  initialDelaySeconds: 5
  periodSeconds: 10
```

### Resource Limits

```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "100m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

---

## File Structure

```
microservices/document_service/
├── __init__.py
├── main.py                     # FastAPI application entry
├── document_service.py         # Business logic layer
├── document_repository.py      # Data access layer
├── models.py                   # Pydantic models
├── protocols.py                # DI interfaces
├── factory.py                  # Service factory
├── routes_registry.py          # Consul route metadata
├── clients/
│   ├── __init__.py
│   ├── storage_client.py       # Storage service client
│   ├── authorization_client.py # Authorization service client
│   └── digital_analytics_client.py # Digital Analytics client
├── events/
│   ├── __init__.py
│   ├── handlers.py             # Event handlers
│   └── publishers.py           # Event publishers
└── migrations/
    └── 001_initial_schema.sql  # Database schema
```

---

## Testing Strategy

### Test Layers

1. **Unit Tests**: Pure function testing, model validation
2. **Component Tests**: Service layer with mocked dependencies
3. **Integration Tests**: Full CRUD with real database
4. **API Tests**: HTTP endpoint testing with auth
5. **Smoke Tests**: E2E bash scripts

### Test Data Factory

```python
class DocumentTestDataFactory:
    @staticmethod
    def make_doc_id() -> str: ...
    @staticmethod
    def make_create_request() -> DocumentCreateRequest: ...
    @staticmethod
    def make_update_request() -> DocumentUpdateRequest: ...
    @staticmethod
    def make_permission_request() -> DocumentPermissionUpdateRequest: ...
    @staticmethod
    def make_rag_query_request() -> RAGQueryRequest: ...
    @staticmethod
    def make_search_request() -> SemanticSearchRequest: ...
```

---

**End of Design Document**
