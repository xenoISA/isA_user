# Task Service - Design Document

## Architecture Overview

### Service Architecture
```
┌────────────────────────────────────────────────────────────────────────┐
│                          Task Service (8211)                            │
├────────────────────────────────────────────────────────────────────────┤
│  FastAPI Application (main.py)                                          │
│  ├─ Route Handlers                                                      │
│  │   ├─ Task CRUD: /api/v1/tasks/*                                     │
│  │   ├─ Execution: /api/v1/tasks/{id}/execute                          │
│  │   ├─ Templates: /api/v1/templates                                   │
│  │   ├─ Analytics: /api/v1/analytics                                   │
│  │   └─ Health: /health, /health/detailed                              │
│  ├─ Dependency Injection Setup                                          │
│  └─ Event Subscription Setup                                            │
├────────────────────────────────────────────────────────────────────────┤
│  Service Layer (task_service.py)                                        │
│  ├─ TaskService class                                                   │
│  │   ├─ create_task() - Create new task                                │
│  │   ├─ get_task() - Get task by ID                                    │
│  │   ├─ list_tasks() - List user tasks                                 │
│  │   ├─ update_task() - Update task                                    │
│  │   ├─ delete_task() - Soft delete task                               │
│  │   ├─ execute_task() - Manual task execution                         │
│  │   ├─ get_executions() - Get execution history                       │
│  │   ├─ list_templates() - List available templates                    │
│  │   ├─ create_from_template() - Create task from template             │
│  │   └─ get_analytics() - Get task analytics                           │
│  └─ Event Publishing (lazy loaded)                                      │
├────────────────────────────────────────────────────────────────────────┤
│  Repository Layer (task_repository.py)                                  │
│  ├─ TaskRepository class                                                │
│  │   ├─ create_task() - Insert task record                             │
│  │   ├─ get_task_by_id() - Query task by ID                            │
│  │   ├─ get_user_tasks() - Query tasks with filters                    │
│  │   ├─ update_task() - Update task fields                             │
│  │   ├─ delete_task() - Soft delete (set deleted_at)                   │
│  │   ├─ create_execution() - Insert execution record                   │
│  │   ├─ update_execution() - Update execution result                   │
│  │   ├─ list_task_executions() - Query execution history               │
│  │   ├─ get_task_templates() - Query templates                         │
│  │   ├─ get_template() - Query template by ID                          │
│  │   └─ get_task_analytics() - Aggregate analytics                     │
│  └─ Data Parsing Helpers                                                │
├────────────────────────────────────────────────────────────────────────┤
│  Dependency Injection (protocols.py + factory.py)                       │
│  ├─ TaskRepositoryProtocol - Repository interface                      │
│  ├─ EventBusProtocol - Event publishing interface                      │
│  ├─ NotificationClientProtocol - Notification client interface         │
│  ├─ CalendarClientProtocol - Calendar client interface                 │
│  ├─ AccountClientProtocol - Account client interface                   │
│  └─ create_task_service() - Factory function                           │
└────────────────────────────────────────────────────────────────────────┘

External Dependencies:
- PostgreSQL via gRPC (data persistence)
- NATS (event publishing and subscription)
- Notification Service (send notifications)
- Calendar Service (calendar integration)
- Account Service (user subscription level)
- Consul (service discovery)
```

### Data Flow Overview
```
                                    ┌─────────────────┐
                                    │   API Gateway   │
                                    └────────┬────────┘
                                             │
                    ┌────────────────────────┼────────────────────────┐
                    │                        │                        │
                    ▼                        ▼                        ▼
         ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
         │  Task CRUD       │    │  Task Execution  │    │  Task Analytics  │
         │  Endpoints       │    │  Endpoints       │    │  Endpoints       │
         └────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘
                  │                       │                       │
                  └───────────────────────┼───────────────────────┘
                                          │
                                          ▼
                               ┌──────────────────────┐
                               │    TaskService       │
                               │  (Business Logic)    │
                               └────────┬─────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │                   │
                    ▼                   ▼                   ▼
         ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
         │ TaskRepository   │ │   Event Bus      │ │  Service Clients │
         │ (Data Access)    │ │   (NATS)         │ │  (HTTP)          │
         └────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘
                  │                    │                    │
                  ▼                    ▼                    ▼
         ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
         │   PostgreSQL     │ │  NATS Server     │ │ Other Services   │
         │   (via gRPC)     │ │                  │ │ - Notification   │
         └──────────────────┘ └──────────────────┘ │ - Calendar       │
                                                   │ - Account        │
                                                   └──────────────────┘
```

---

## Component Design

### Service Layer (task_service.py)

**Responsibilities**:
- Business logic for task operations
- Input validation and transformation
- Event publishing coordination
- Cross-service client calls
- Error handling and response formatting

**Key Methods**:

| Method | Description | Events Published |
|--------|-------------|------------------|
| `create_task()` | Create new task | `task.created` |
| `get_task()` | Get task by ID | - |
| `list_tasks()` | List user tasks with filters | - |
| `update_task()` | Update task configuration | `task.updated` |
| `delete_task()` | Soft delete task | `task.deleted` |
| `execute_task()` | Execute task manually | `task.executed` |
| `get_executions()` | Get execution history | - |
| `list_templates()` | List available templates | - |
| `create_from_template()` | Create task from template | `task.created` |
| `get_analytics()` | Get aggregated analytics | - |

### Repository Layer (task_repository.py)

**Responsibilities**:
- Database operations via PostgreSQL gRPC
- Query building and parameter binding
- Data parsing from Protobuf to Pydantic models
- Transaction management

**Tables Accessed**:
- `task.user_tasks` - Task records
- `task.task_executions` - Execution history
- `task.task_templates` - Pre-configured templates

### Protocols Layer (protocols.py)

**Responsibilities**:
- Define interfaces for dependency injection
- Custom exception definitions
- No I/O imports - safe to import anywhere

**Defined Protocols**:
- `TaskRepositoryProtocol` - Repository interface
- `EventBusProtocol` - Event publishing interface
- `NotificationClientProtocol` - Notification client
- `CalendarClientProtocol` - Calendar client
- `AccountClientProtocol` - Account client

**Custom Exceptions**:
- `TaskNotFoundError` - Task not found
- `TaskExecutionError` - Execution failed
- `TaskLimitExceededError` - Quota exceeded
- `TaskPermissionDeniedError` - Access denied
- `TaskValidationError` - Invalid configuration

### Factory Layer (factory.py)

**Responsibilities**:
- Create production service instances
- Import I/O-dependent modules
- Wire dependencies together

---

## Database Schemas

### Schema: task

#### Table: task.user_tasks
```sql
CREATE TABLE task.user_tasks (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    task_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    priority VARCHAR(20) DEFAULT 'medium',

    -- Configuration
    config JSONB DEFAULT '{}'::jsonb,
    schedule JSONB,
    credits_per_run DOUBLE PRECISION DEFAULT 0,

    -- Metadata
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Execution tracking
    next_run_time TIMESTAMPTZ,
    last_run_time TIMESTAMPTZ,
    last_success_time TIMESTAMPTZ,
    last_error TEXT,
    last_result JSONB,

    -- Statistics
    run_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    total_credits_consumed DOUBLE PRECISION DEFAULT 0,

    -- Calendar/Todo specific
    due_date TIMESTAMPTZ,
    reminder_time TIMESTAMPTZ,
    is_completed BOOLEAN DEFAULT false,
    completed_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_tasks_user_id ON task.user_tasks(user_id);
CREATE INDEX idx_tasks_status ON task.user_tasks(status);
CREATE INDEX idx_tasks_type ON task.user_tasks(task_type);
CREATE INDEX idx_tasks_user_status ON task.user_tasks(user_id, status) WHERE deleted_at IS NULL;
CREATE INDEX idx_tasks_scheduled_pending ON task.user_tasks(status, next_run_time)
    WHERE status = 'scheduled' AND deleted_at IS NULL;
CREATE INDEX idx_tasks_tags ON task.user_tasks USING GIN (tags);
```

#### Table: task.task_executions
```sql
CREATE TABLE task.task_executions (
    id SERIAL PRIMARY KEY,
    execution_id VARCHAR(255) NOT NULL UNIQUE,
    task_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,

    -- Execution details
    status VARCHAR(50) NOT NULL,
    trigger_type VARCHAR(50) DEFAULT 'manual',
    trigger_data JSONB,

    -- Results
    result JSONB,
    error_message TEXT,
    error_details JSONB,

    -- Resource usage
    credits_consumed DOUBLE PRECISION DEFAULT 0,
    tokens_used INTEGER,
    api_calls_made INTEGER DEFAULT 0,
    duration_ms INTEGER,

    -- Timestamps
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_executions_task_id ON task.task_executions(task_id);
CREATE INDEX idx_executions_user_id ON task.task_executions(user_id);
CREATE INDEX idx_executions_task_started ON task.task_executions(task_id, started_at DESC);
```

#### Table: task.task_templates
```sql
CREATE TABLE task.task_templates (
    id SERIAL PRIMARY KEY,
    template_id VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100) NOT NULL,
    task_type VARCHAR(50) NOT NULL,
    default_config JSONB DEFAULT '{}'::jsonb,
    required_fields TEXT[] DEFAULT ARRAY[]::TEXT[],
    optional_fields TEXT[] DEFAULT ARRAY[]::TEXT[],
    config_schema JSONB DEFAULT '{}'::jsonb,
    required_subscription_level VARCHAR(50) DEFAULT 'free',
    credits_per_run DOUBLE PRECISION DEFAULT 0,
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    metadata JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_templates_category ON task.task_templates(category);
CREATE INDEX idx_templates_type ON task.task_templates(task_type);
CREATE INDEX idx_templates_active ON task.task_templates(is_active) WHERE is_active = true;
```

---

## Data Flow Diagrams

### Task Creation Flow
```
Client -> POST /api/v1/tasks
  -> main.py: create_task_endpoint()
    -> TaskService.create_task()
      -> Validate request data
      -> Check user subscription limits (optional)
      -> TaskRepository.create_task()
        -> PostgreSQL INSERT
      <- TaskResponse
      -> EventPublisher.publish_task_created()
        -> NATS: task.created
    <- TaskResponse
  <- HTTP 201 {task_data}
```

### Task Execution Flow
```
Client -> POST /api/v1/tasks/{task_id}/execute
  -> main.py: execute_task_endpoint()
    -> TaskService.execute_task()
      -> TaskRepository.get_task_by_id()
        -> PostgreSQL SELECT
      <- TaskResponse
      -> Validate task is executable
      -> TaskRepository.create_execution()
        -> PostgreSQL INSERT
      <- ExecutionResponse
      -> Execute task logic based on task_type
        -> External API calls (weather, news, etc.)
      <- Execution result
      -> TaskRepository.update_execution()
        -> PostgreSQL UPDATE
      -> TaskRepository.update_task_execution_info()
        -> PostgreSQL UPDATE (statistics)
      -> EventPublisher.publish_task_executed()
        -> NATS: task.executed
    <- ExecutionResponse
  <- HTTP 200 {execution_result}
```

### Template-Based Task Creation Flow
```
Client -> POST /api/v1/tasks/from-template
  -> main.py: create_from_template_endpoint()
    -> TaskService.create_from_template()
      -> TaskRepository.get_template()
        -> PostgreSQL SELECT
      <- TemplateResponse
      -> Validate subscription level
      -> Merge user config with template defaults
      -> Validate required fields provided
      -> TaskRepository.create_task()
        -> PostgreSQL INSERT
      <- TaskResponse
      -> EventPublisher.publish_task_created()
        -> NATS: task.created
    <- TaskResponse
  <- HTTP 201 {task_data}
```

### Analytics Query Flow
```
Client -> GET /api/v1/analytics?days=30
  -> main.py: get_analytics_endpoint()
    -> TaskService.get_analytics()
      -> TaskRepository.get_task_analytics()
        -> PostgreSQL aggregate queries
          -> Task counts by status
          -> Execution statistics
          -> Resource consumption
          -> Task type distribution
          -> Busiest hours/days
      <- TaskAnalyticsResponse
    <- TaskAnalyticsResponse
  <- HTTP 200 {analytics_data}
```

---

## Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Language | Python | 3.9+ |
| Framework | FastAPI | 0.100+ |
| Validation | Pydantic | 2.0+ |
| Database | PostgreSQL | 14+ |
| Database Client | AsyncPostgresClient (gRPC) | Custom |
| Event Bus | NATS | 2.0+ |
| Service Discovery | Consul | 1.15+ |
| HTTP Client | httpx | 0.24+ |
| MQTT | paho-mqtt | 1.6+ |

---

## Security Considerations

### Authentication
- JWT tokens validated at API Gateway
- User ID extracted from token claims
- `X-User-ID` header injected by gateway

### Authorization
- Task ownership enforced on all operations
- Only task owner can read/update/delete their tasks
- Template access controlled by subscription level

### Input Validation
- All inputs validated via Pydantic models
- Task name length: 1-255 characters
- Task type must be valid enum value
- Schedule configuration validated
- JSONB fields sanitized

### Data Protection
- Soft delete preserves audit trail
- Execution history retained for compliance
- No PII in task configurations (user responsibility)

### Rate Limiting
- Implemented at API Gateway level
- Per-user task creation limits
- Per-task execution frequency limits

---

## Event-Driven Architecture

### Published Events

| Event | Subject Pattern | Payload |
|-------|-----------------|---------|
| task.created | task_service.task.created | task_id, user_id, task_type, name |
| task.updated | task_service.task.updated | task_id, user_id, updated_fields |
| task.deleted | task_service.task.deleted | task_id, user_id |
| task.executed | task_service.task.executed | task_id, execution_id, status, credits |
| task.status_changed | task_service.task.status_changed | task_id, old_status, new_status |

### Subscribed Events

| Event | Source | Handler |
|-------|--------|---------|
| user.deleted | account_service | cancel_user_tasks() |
| subscription.changed | subscription_service | update_task_limits() |

---

## Error Handling

### Error Types and HTTP Codes

| Error | HTTP Code | Response Format |
|-------|-----------|-----------------|
| TaskNotFoundError | 404 | `{"detail": "Task not found", "task_id": "..."}` |
| TaskValidationError | 422 | `{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}` |
| TaskPermissionDeniedError | 403 | `{"detail": "Permission denied", "action": "..."}` |
| TaskLimitExceededError | 429 | `{"detail": "Task limit exceeded", "limit_type": "..."}` |
| TaskExecutionError | 500 | `{"detail": "Execution failed", "error_code": "..."}` |
| DatabaseError | 500 | `{"detail": "Internal server error"}` |

### Retry Strategy
- Database operations: 3 retries with exponential backoff
- Event publishing: Fire-and-forget with logging on failure
- External API calls: Configurable per task type

---

## Performance Considerations

### Database Optimization
- Composite indexes for common query patterns
- GIN index on tags array for fast filtering
- Partial indexes for active tasks only
- Connection pooling via gRPC client

### Caching Strategy
- Template list cached with 5-minute TTL
- Analytics cached with 1-minute TTL
- No caching for task data (real-time accuracy)

### Query Optimization
- Pagination enforced on list operations
- Maximum limit of 100 per page
- Deleted tasks filtered at database level

### Execution Performance
- Async execution to prevent blocking
- Timeout enforcement per task type
- Background job queue for heavy tasks

---

## Deployment Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| SERVICE_NAME | Service identifier | task_service |
| SERVICE_PORT | HTTP port | 8211 |
| POSTGRES_HOST | Database host | isa-postgres-grpc |
| POSTGRES_PORT | Database port | 50061 |
| NATS_URL | NATS connection URL | nats://nats:4222 |
| CONSUL_HOST | Consul host | consul |
| CONSUL_PORT | Consul port | 8500 |
| LOG_LEVEL | Logging level | INFO |

### Health Checks

| Endpoint | Check | Interval |
|----------|-------|----------|
| /health | Basic liveness | 10s |
| /health/detailed | All dependencies | 30s |

### Resource Limits

| Resource | Recommended |
|----------|-------------|
| CPU | 500m request, 1 core limit |
| Memory | 256Mi request, 512Mi limit |
| Replicas | 2-4 based on load |

---

## Dependency Injection Pattern

### Protocol-Based Interfaces

```python
# protocols.py - No I/O imports
@runtime_checkable
class TaskRepositoryProtocol(Protocol):
    async def create_task(...) -> TaskResponse: ...
    async def get_task_by_id(...) -> TaskResponse: ...
    ...

@runtime_checkable
class EventBusProtocol(Protocol):
    async def publish_event(event: Any) -> None: ...
```

### Factory Pattern

```python
# factory.py - Only place that imports repository
def create_task_service(config, event_bus) -> TaskService:
    from .task_repository import TaskRepository  # I/O import here
    repository = TaskRepository(config=config)
    return TaskService(repository=repository, event_bus=event_bus)
```

### Service Instantiation

```python
# main.py - Production setup
from .factory import create_task_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    service = create_task_service(config=config, event_bus=event_bus)
    app.state.service = service
    yield
```

### Testing with Mocks

```python
# tests/component/task_service/test_task_service.py
from microservices.task_service.task_service import TaskService

def test_create_task():
    mock_repo = MockTaskRepository()
    mock_bus = MockEventBus()
    service = TaskService(repository=mock_repo, event_bus=mock_bus)
    # Test with injected mocks
```

---

**Document Version**: 1.0
**Last Updated**: 2025-12-17
**Maintained By**: Task Service Team
