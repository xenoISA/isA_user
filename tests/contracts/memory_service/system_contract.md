# Memory Service - System Contract (Layer 6)

## Overview

This document defines HOW memory_service implements the 12 standard system patterns.

**Service**: memory_service
**Port**: 8223
**Category**: User Microservice (AI-Powered)
**Version**: 1.0.0

---

## 1. Architecture Pattern

### Service Layer Structure

```
microservices/memory_service/
├── __init__.py
├── main.py                     # FastAPI app, routes, DI setup, lifespan
├── memory_service.py           # Orchestrator service (delegates to sub-services)
├── factual_service.py          # Factual memory sub-service
├── factual_repository.py       # Factual memory data access
├── procedural_service.py       # Procedural memory sub-service
├── procedural_repository.py    # Procedural memory data access
├── episodic_service.py         # Episodic memory sub-service
├── episodic_repository.py      # Episodic memory data access
├── semantic_service.py         # Semantic memory sub-service
├── semantic_repository.py      # Semantic memory data access
├── working_service.py          # Working memory sub-service
├── working_repository.py       # Working memory data access
├── session_service.py          # Session memory sub-service
├── session_repository.py       # Session memory data access
├── association_service.py      # Memory association service
├── association_repository.py   # Association data access
├── base_repository.py          # Shared repository base class
├── graph_client.py             # Neo4j graph client
├── hybrid_search.py            # Combined vector + graph search
├── context_compressor.py       # Context compression for LLM
├── context_ordering.py         # Context ordering by importance
├── mmr_reranker.py             # MMR diversity reranking
├── decay_service.py            # Memory decay/forgetting
├── consolidation_service.py    # Memory consolidation
├── models.py                   # Pydantic models
├── protocols.py                # DI interfaces
├── factory.py                  # DI factory (create_memory_service)
├── routes_registry.py          # Consul route metadata
├── client.py                   # HTTP client for inter-service calls
└── events/
    ├── __init__.py
    ├── models.py
    ├── handlers.py
    └── publishers.py
```

### Layer Responsibilities

| Layer | File | Responsibility | Dependencies |
|-------|------|----------------|--------------|
| **Routes** | `main.py` | HTTP endpoints, DI wiring | FastAPI, MemoryService |
| **Orchestrator** | `memory_service.py` | Delegates to sub-services by memory type | All sub-services |
| **Sub-Services** | `*_service.py` | Type-specific memory logic | Corresponding repository |
| **Repositories** | `*_repository.py` | Data access (PostgreSQL + Qdrant) | AsyncPostgresClient, Qdrant |
| **Graph** | `graph_client.py` | Neo4j entity/relationship queries | Neo4j |
| **Search** | `hybrid_search.py` | Combined vector + graph search | Qdrant, Neo4j |

### External Dependencies

| Dependency | Type | Purpose | Endpoint |
|------------|------|---------|----------|
| PostgreSQL | gRPC | Structured memory storage | isa-postgres-grpc:50061 |
| Qdrant | HTTP/gRPC | Vector embeddings search | qdrant:6333/6334 |
| Neo4j | Bolt | Entity relationship graph | neo4j:7687 |
| NATS | Native | Event pub/sub | nats:4222 |
| Consul | HTTP | Service registration | consul:8500 |
| ISA Model | HTTP | AI extraction and embeddings | via service discovery |

---

## 2. Dependency Injection Pattern

### Protocol Definition (`protocols.py`)

```python
class MemoryServiceError(Exception): ...
class MemoryNotFoundError(MemoryServiceError): ...
class MemoryValidationError(MemoryServiceError): ...
class MemoryPermissionError(MemoryServiceError): ...

@runtime_checkable
class MemoryRepositoryProtocol(Protocol):
    async def create(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]: ...
    async def get_by_id(self, memory_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]: ...
    async def update(self, memory_id: str, updates: Dict[str, Any], user_id: str) -> bool: ...
    async def delete(self, memory_id: str, user_id: str) -> bool: ...
    async def list_by_user(self, user_id: str, ...) -> List[Dict[str, Any]]: ...
    async def check_connection(self) -> bool: ...

@runtime_checkable
class FactualServiceProtocol(MemoryTypeServiceProtocol):
    async def store_factual_memory(self, user_id: str, dialog_content: str, importance_score: float) -> Any: ...

@runtime_checkable
class EpisodicServiceProtocol(MemoryTypeServiceProtocol):
    async def store_episodic_memory(self, user_id: str, dialog_content: str, importance_score: float) -> Any: ...

@runtime_checkable
class ProceduralServiceProtocol(MemoryTypeServiceProtocol):
    async def store_procedural_memory(self, user_id: str, dialog_content: str, importance_score: float) -> Any: ...

@runtime_checkable
class SemanticServiceProtocol(MemoryTypeServiceProtocol):
    async def store_semantic_memory(self, user_id: str, dialog_content: str, importance_score: float) -> Any: ...

class WorkingServiceProtocol(MemoryTypeServiceProtocol): ...
class SessionServiceProtocol(MemoryTypeServiceProtocol): ...
class EventBusProtocol(Protocol): ...
```

### Factory Implementation (`factory.py`)

```python
def create_memory_service(consul_registry=None, event_bus=None) -> MemoryService:
    from .factual_service import FactualMemoryService
    from .procedural_service import ProceduralMemoryService
    from .episodic_service import EpisodicMemoryService
    from .semantic_service import SemanticMemoryService
    from .working_service import WorkingMemoryService
    from .session_service import SessionMemoryService
    from .association_service import AssociationService

    return MemoryService(
        consul_registry=consul_registry, event_bus=event_bus,
        factual_service=FactualMemoryService(),
        procedural_service=ProceduralMemoryService(),
        episodic_service=EpisodicMemoryService(),
        semantic_service=SemanticMemoryService(),
        working_service=WorkingMemoryService(),
        session_service=SessionMemoryService(),
        association_service=AssociationService(),
    )
```

---

## 3. Event Publishing Pattern

### Published Events

| Event | Trigger |
|-------|---------|
| `memory.created` | New memory stored |
| `memory.updated` | Memory updated |
| `memory.deleted` | Memory deleted |
| `memory.extracted` | AI extraction completed |
| `memory.consolidated` | Memory consolidation completed |

### Subscribed Events

Subscribes to entity extraction events for graph updates.

---

## 4. Error Handling Pattern

| Exception | HTTP Status |
|-----------|-------------|
| MemoryValidationError | 400 |
| MemoryPermissionError | 403 |
| MemoryNotFoundError | 404 |
| MemoryServiceError | 500 |

---

## 5-6. Client & Repository Pattern

Each memory type has its own repository. Repositories use both PostgreSQL (structured data) and Qdrant (vector embeddings). Graph client uses Neo4j for entity relationships.

**Unique Features:**
- Hybrid search (vector + graph)
- MMR reranking for diversity
- Context compression for LLM context windows
- Memory decay/forgetting curves
- Memory consolidation

---

## 7. Service Registration Pattern (Consul)

```python
SERVICE_METADATA = {
    "service_name": "memory_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "ai-powered", "memory-management"],
    "capabilities": [
        "factual_memory", "episodic_memory", "procedural_memory",
        "semantic_memory", "working_memory", "session_memory",
        "ai_extraction", "vector_search", "memory_statistics"
    ]
}
```

21 routes: health (3), extraction (4), storage CRUD (2), session (4), working (3), search (4), statistics (1).

---

## 8. Health Check Contract

| Endpoint | Auth Required | Purpose |
|----------|---------------|---------|
| `/` | No | Root health check |
| `/health` | No | Basic health check |
| `/api/v1/memories/health` | No | API-versioned health check |

---

## 9-12. Event System, Configuration, Logging, Deployment

- NATS event bus for memory lifecycle events
- ConfigManager with port 8223
- `setup_service_logger("memory_service")`
- GracefulShutdown with signal handlers
- Graph client (Neo4j) initialization for entity extraction
- Hybrid search combining Qdrant vectors and Neo4j graph

---

## System Contract Checklist

- [x] `protocols.py` defines 8 protocol interfaces (Repository + 6 memory types + EventBus)
- [x] `factory.py` creates orchestrator with 7 sub-services
- [x] 6 memory types (factual, procedural, episodic, semantic, working, session)
- [x] Triple-store architecture (PostgreSQL + Qdrant + Neo4j)
- [x] AI-powered extraction via ISA Model
- [x] Hybrid search (vector + graph)
- [x] Memory decay and consolidation
- [x] Consul TTL registration with 21 routes and 9 capabilities

---

## Reference Files

| File | Purpose |
|------|---------|
| `microservices/memory_service/main.py` | FastAPI app, routes, lifespan |
| `microservices/memory_service/memory_service.py` | Orchestrator |
| `microservices/memory_service/factual_service.py` | Factual memory logic |
| `microservices/memory_service/protocols.py` | DI interfaces |
| `microservices/memory_service/factory.py` | DI factory |
| `microservices/memory_service/graph_client.py` | Neo4j client |
| `microservices/memory_service/hybrid_search.py` | Combined search |
| `microservices/memory_service/routes_registry.py` | Consul metadata |
| `microservices/memory_service/events/` | Event handlers, models, publishers |
