# Project Service - Design Document

## Architecture Overview

`project_service` follows the standard `main.py -> service -> repository` layout with dependency-injected collaborators.

```
FastAPI routes (main.py)
  -> ProjectService
     -> ProjectRepository
     -> StorageServiceClient
     -> EventBusProtocol (optional)
```

### Responsibilities

- `main.py`
  - HTTP route declarations
  - request validation
  - auth dependency
  - exception mapping
- `project_service.py`
  - ownership checks
  - project/file business rules
  - orchestration between repository and storage client
  - audit event publishing
- `project_repository.py`
  - PostgreSQL persistence for projects and project file associations
- `storage_service.client.py`
  - stores and deletes the underlying file objects

---

## Knowledge File Flow

### Upload

1. `POST /api/v1/projects/{project_id}/files`
2. Route resolves authenticated caller and passes `UploadFile` to `ProjectService.upload_project_file(...)`
3. Service verifies project ownership
4. Service streams file bytes to `StorageServiceClient.upload_file(...)`
5. Storage response (`file_id`, `file_path`, `file_size`, `content_type`) is persisted through `ProjectRepository.create_project_file(...)`
6. API returns `ProjectFileResponse`

### List

1. `GET /api/v1/projects/{project_id}/files`
2. Service verifies ownership
3. Repository returns project file associations ordered by `created_at DESC`
4. API wraps them in `{files, total}`

### Delete

1. `DELETE /api/v1/projects/{project_id}/files/{file_id}`
2. Service verifies ownership and confirms the association exists
3. Service deletes the underlying storage object with `permanent=True`
4. Repository deletes the association row
5. API returns `204 No Content`

---

## Data Model

### `project.projects`

- `id`
- `user_id`
- `org_id`
- `name`
- `description`
- `custom_instructions`
- `created_at`
- `updated_at`

### `project.project_files`

- `id`
- `project_id`
- `filename`
- `file_type`
- `file_size`
- `storage_path`
- `created_at`

The file association table intentionally stores only metadata needed by the frontend and downstream project context assembly. Blob lifecycle remains the responsibility of `storage_service`.

---

## Dependency Injection

`create_project_service(...)` now wires:

- `ProjectRepository`
- `StorageServiceClient`
- optional `EventBusProtocol`

Tests can replace either repository or storage client through protocol-compatible mocks.

---

## Error Handling

- `ProjectNotFoundError` -> `404`
- `ProjectPermissionError` -> `403`
- `InvalidProjectUpdate` -> `422`
- `RepositoryError` -> `500`
- `ProjectStorageError` -> `502`

This keeps file-operation failures distinguishable from pure persistence failures.

---

## Deployment / Migration Notes

The service now includes a managed SQL migration:

- `microservices/project_service/migrations/001_create_project_schema.sql`

It creates the `project` schema plus both `projects` and `project_files` tables with idempotent `IF NOT EXISTS` guards so new environments can bootstrap cleanly.

---

## Testing Strategy

- Unit
  - model and exception coverage for project file list/response shapes
- Component
  - service-level file upload/list/delete behavior using mocked repository + storage client
  - route-level multipart/list/delete behavior using FastAPI dependency overrides
- Existing golden tests
  - CRUD and ownership behavior remain green alongside the new file flows
