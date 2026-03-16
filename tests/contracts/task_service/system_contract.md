# Task Service - System Contract (Layer 6)

## Overview

This document defines HOW task_service implements the 12 standard system patterns.

**Service**: task_service
**Port**: 8217
**Category**: User Microservice
**Version**: 1.0.0

---

## 1. Architecture Pattern

### Service Layer Structure

```
microservices/task_service/
├── __init__.py
├── main.py                          # FastAPI app, routes, DI setup, lifespan
├── task_service.py                  # Business logic layer
├── task_repository.py               # Data access layer
├── models.py                        # Pydantic models (Task, TaskExecution, etc.)
├── protocols.py                     # DI interfaces (rich protocol set)
├── factory.py                       # DI factory
├── routes_registry.py               # Consul route metadata
├── client.py                        # Service client
├── mqtt_notifications.py            # MQTT notification support
├── clients/
│   ├── __init__.py
│   ├── account_client.py
│   ├── calendar_client.py
│   └── notification_client.py
├── events/
│   ├── __init__.py
│   ├── models.py
│   ├── handlers.py
│   └── publishers.py
└── migrations/
    └── 004_migrate_to_task_schema.sql
```

### External Dependencies

| Dependency | Type | Purpose | Endpoint |
|------------|------|---------|----------|
| PostgreSQL | AsyncPostgresClient | Primary data store | postgres:5432 |
| NATS | Native | Event pub/sub | nats:4222 |
| Consul | HTTP | Service registration | consul:8500 |
| Auth Service | HTTP | Token/API key verification | localhost:8201 |

---

## 2. Dependency Injection Pattern

### Protocol Definition (`protocols.py`)

```python
@runtime_checkable
class TaskRepositoryProtocol(Protocol):
    async def create_task(self, user_id: str, task_data: Dict) -> Optional[TaskResponse]: ...
    async def get_task_by_id(self, task_id: str, user_id=None) -> Optional[TaskResponse]: ...
    async def get_user_tasks(self, user_id: str, status=None, task_type=None, limit=100, offset=0) -> List[TaskResponse]: ...
    async def update_task(self, task_id: str, updates: Dict, user_id=None) -> bool: ...
    async def delete_task(self, task_id: str, user_id=None) -> bool: ...
    async def get_pending_tasks(self, limit=100) -> List[TaskResponse]: ...
    async def create_execution_record(self, task_id: str, user_id: str, execution_data: Dict) -> Optional[TaskExecutionResponse]: ...
    async def get_task_executions(self, task_id: str, limit=50, offset=0) -> List[TaskExecutionResponse]: ...
    async def get_task_templates(self, subscription_level=None, ...) -> List[TaskTemplateResponse]: ...
    async def get_task_analytics(self, user_id: str, days=30) -> Optional[TaskAnalyticsResponse]: ...
    async def cancel_user_tasks(self, user_id: str) -> int: ...

class EventBusProtocol(Protocol):
    async def publish_event(self, event: Any) -> None: ...

class NotificationClientProtocol(Protocol):
    async def send_notification(self, recipient_id: str, ...) -> bool: ...

class CalendarClientProtocol(Protocol):
    async def create_calendar_event(self, user_id: str, ...) -> Optional[Dict]: ...

class AccountClientProtocol(Protocol):
    async def get_user_subscription_level(self, user_id: str) -> str: ...
```

### Custom Exceptions

| Exception | Description |
|-----------|-------------|
| TaskNotFoundError | Task not found (with task_id) |
| TaskExecutionError | Execution failed (with error_code) |
| TaskLimitExceededError | Limit reached (with limit_type) |
| TaskPermissionDeniedError | Permission denied (with action) |
| TaskValidationError | Validation error (with field) |
| DuplicateTaskError | Duplicate task |

---

## 3. Factory Implementation

```python
def create_task_service(config=None, event_bus=None, ...) -> TaskService:
    if config is None:
        config = ConfigManager("task_service")
    return TaskService(event_bus=event_bus, config_manager=config)
```

Note: TaskService creates its own repository internally from config_manager.

---

## 4. Singleton Management

Uses `TaskMicroservice` class:
```python
class TaskMicroservice:
    def __init__(self):
        self.service = None
        self.repository = None
        self.consul_registry = None
microservice = TaskMicroservice()
```

---

## 5. Service Registration (Consul)

- **Route count**: 16 routes
- **Base path**: `/api/v1/tasks`
- **Tags**: `["v1", "task", "todo", "scheduler", "user-microservice"]`
- **Capabilities**: task_management, task_execution, task_templates, task_scheduling, task_analytics, todo_lists
- **Health check type**: TTL

---

## 6. Health Check Contract

| Endpoint | Auth | Response |
|----------|------|----------|
| `/health` | No | `{status, service, port, version}` |
| `/api/v1/tasks/health` | No | Same |
| `/health/detailed` | No | With database component status |

---

## 7. Event System Contract (NATS)

### Subscribed Events

Registered via `get_event_handlers(task_repository=task_repo)` with durable consumers:
- `task-{event}-consumer` naming convention

### Authentication

Uses custom `get_user_context()` dependency that verifies JWT/API Key against auth_service via httpx, with internal service bypass.

---

## 8. Configuration Contract

| Variable | Description | Default |
|----------|-------------|---------|
| `TASK_SERVICE_PORT` | HTTP port | 8217 |
| `AUTH_SERVICE_HOST` | Auth service host | localhost |
| `AUTH_SERVICE_PORT` | Auth service port | 8201 |

---

## 9. Error Handling Contract

All route handlers use try/except with generic 500 fallback. No app-level exception handlers.

---

## 10. Logging Contract

```python
app_logger = setup_service_logger("task_service")
```

---

## 11. Testing Contract

```python
mock_repo = AsyncMock(spec=TaskRepositoryProtocol)
service = TaskService(event_bus=AsyncMock(), config_manager=mock_config)
```

---

## 12. Deployment Contract

### Lifecycle

1. Install signal handlers
2. Initialize event bus
3. Initialize TaskMicroservice (creates repo + service)
4. Subscribe to events with durable consumers
5. Consul TTL registration
6. **yield**
7. Graceful shutdown
8. Consul deregistration
9. Event bus close
10. Microservice shutdown

### Special Routes

- `/api/v1/scheduler/pending` - Internal scheduler endpoint (key-authenticated)
- `/api/v1/scheduler/execute/{task_id}` - Internal scheduler execution
- `/api/v1/templates` - Task template listing
- `/api/v1/tasks/from-template` - Template-based task creation

---

## Reference Files

| File | Purpose |
|------|---------|
| `microservices/task_service/main.py` | FastAPI app, routes, lifespan |
| `microservices/task_service/task_service.py` | Business logic |
| `microservices/task_service/task_repository.py` | Data access |
| `microservices/task_service/protocols.py` | DI interfaces |
| `microservices/task_service/factory.py` | DI factory |
| `microservices/task_service/models.py` | Pydantic schemas |
| `microservices/task_service/routes_registry.py` | Consul metadata |
| `microservices/task_service/events/handlers.py` | NATS handlers |
| `microservices/task_service/events/models.py` | Event schemas |
