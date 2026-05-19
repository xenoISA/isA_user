# Project Service - System Contract

## Overview

This document describes how `project_service` implements the required system patterns for project CRUD and project knowledge file management.

**Service**: `project_service`  
**Port**: `8260`  
**Category**: User Microservice

---

## 1. Architecture Pattern

```
microservices/project_service/
├── main.py
├── project_service.py
├── project_repository.py
├── protocols.py
├── factory.py
├── client.py
├── models.py
├── routes_registry.py
└── migrations/
    └── 001_create_project_schema.sql
```

### Layer responsibilities

- `main.py`: FastAPI routes, auth dependency, exception mapping, lifespan
- `project_service.py`: ownership validation, storage orchestration, audit publishing
- `project_repository.py`: PostgreSQL persistence for projects and `project_files`
- `factory.py`: wires repository + storage client + optional event bus
- `client.py`: inter-service client for project CRUD and project file operations

---

## 2. Dependency Injection Pattern

`ProjectService` accepts:

- `ProjectRepositoryProtocol`
- `StorageServiceProtocol`
- optional `EventBusProtocol`

This allows service-layer component tests to swap in in-memory/mocked repository and storage implementations.

---

## 3. Auth Contract

`main.py` defines `get_authenticated_caller(request)` and supports:

- internal service headers
- bearer token verification helpers
- API key verification helpers

Failure to resolve the caller returns `401 User authentication required`.

---

## 4. Persistence Contract

### Schema

- `project.projects`
- `project.project_files`

### Migration

- `microservices/project_service/migrations/001_create_project_schema.sql`

The migration is idempotent and safe for new environments.

---

## 5. Route Contract

Protected routes:

- `POST /api/v1/projects`
- `GET /api/v1/projects`
- `GET /api/v1/projects/export` (internal service only, GDPR subject export)
- `GET /api/v1/projects/{project_id}`
- `PUT /api/v1/projects/{project_id}`
- `DELETE /api/v1/projects/{project_id}`
- `PUT /api/v1/projects/{project_id}/instructions`
- `GET /api/v1/projects/{project_id}/files`
- `POST /api/v1/projects/{project_id}/files`
- `DELETE /api/v1/projects/{project_id}/files/{file_id}`

Health routes:

- `/health`
- `/api/v1/projects/health`

---

## 6. External Dependency Contract

### PostgreSQL
- primary system of record for projects and project file associations

### storage_service
- stores uploaded file bytes
- deletes underlying file objects on project-file removal

### NATS
- optional audit event publishing

---

## 7. Error Handling Contract

Mapped exceptions:

- `ProjectNotFoundError` -> `404`
- `ProjectPermissionError` -> `403`
- `ProjectLimitExceeded` -> `400`
- `InvalidProjectUpdate` -> `422`
- `RepositoryError` -> `500`
- `ProjectStorageError` -> `502`
- non-internal callers to `GET /api/v1/projects/export` -> `403`

Error response shape:

```json
{
  "status": "error",
  "error": "storage_error",
  "detail": "Failed to upload project file"
}
```

---

## 8. Testing Contract

Minimum coverage expected for this service slice:

- unit tests for project models/exceptions
- component tests for service-layer file upload/list/delete flows
- component endpoint tests for multipart upload and list/delete routes
- existing golden CRUD tests remain green alongside the new file behaviors

---

## 9. Operational Notes

- route metadata is declared in `routes_registry.py`
- graceful shutdown uses the shared shutdown middleware
- project file associations are metadata only; blob lifecycle remains delegated to `storage_service`
