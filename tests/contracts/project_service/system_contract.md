# Project Service - System Contract (Layer 6)

## Overview

This document defines HOW `project_service` implements the standard service
patterns.

**Service**: `project_service`  
**Port**: `8260`  
**Version**: `1.0.0`

## 1. Architecture Pattern

```text
microservices/project_service/
├── main.py
├── factory.py
├── models.py
├── project_service.py
├── project_repository.py
├── protocols.py
├── client.py
└── routes_registry.py
```

- `main.py` owns FastAPI routing, health checks, and exception handlers.
- `ProjectService` owns limits, ownership checks, and event publication.
- `ProjectRepository` owns persistence.

## 2. Dependency Injection Pattern

- `ProjectService(repository, event_bus=None)` is the unit under test.
- `create_project_service(config_manager, repository=None, event_bus=None)`
  wires production dependencies.
- `get_service()` returns the singleton from the FastAPI layer only.

## 3. API Contract

| Method | Path | Auth |
|--------|------|------|
| `GET` | `/health` | no |
| `GET` | `/api/v1/projects/health` | no |
| `POST` | `/api/v1/projects` | yes |
| `GET` | `/api/v1/projects` | yes |
| `GET` | `/api/v1/projects/{project_id}` | yes |
| `PUT` | `/api/v1/projects/{project_id}` | yes |
| `DELETE` | `/api/v1/projects/{project_id}` | yes |
| `PUT` | `/api/v1/projects/{project_id}/instructions` | yes |

## 4. Error Handling Contract

- `ProjectNotFoundError` -> `404`
- `ProjectPermissionError` -> `403`
- `ProjectLimitExceeded` -> `400`
- `InvalidProjectUpdate` -> `422`
- `RepositoryError` -> `500`

All error payloads use `{status, error, detail}`.

## 5. Event Contract

When an event bus is configured, the service publishes:
- `project.create`
- `project.read`
- `project.update`
- `project.delete`
- `project.set_instructions`

Event publication is best-effort and must not fail the HTTP request path.

## 6. Lifecycle Contract

1. Install graceful-shutdown handlers.
2. Attempt NATS event-bus initialization.
3. Create `ProjectService` through the factory.
4. Serve requests and health checks.
5. Log clean shutdown on process exit.
