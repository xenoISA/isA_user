# Project Service Design

## Architecture

`project_service` follows the lightweight CRUD microservice pattern used across
`isA_user`.

```text
FastAPI main.py
  -> auth dependency resolves caller
  -> ProjectService enforces ownership and limits
  -> ProjectRepository persists project state
  -> optional NATS event bus publishes audit-style events
```

## File Structure

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

## API Surface

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | basic health |
| `GET` | `/api/v1/projects/health` | versioned health |
| `POST` | `/api/v1/projects` | create project |
| `GET` | `/api/v1/projects` | list owned projects |
| `GET` | `/api/v1/projects/{project_id}` | fetch owned project |
| `PUT` | `/api/v1/projects/{project_id}` | update owned project |
| `DELETE` | `/api/v1/projects/{project_id}` | delete owned project |
| `PUT` | `/api/v1/projects/{project_id}/instructions` | update instructions |

## Dependency Injection

- `create_project_service()` owns repository construction in production.
- `ProjectService` accepts a repository and optional event bus directly for
  tests.
- `main.py` keeps the singleton only at the FastAPI boundary.

## Error Model

`main.py` maps domain exceptions to structured JSON:

- `ProjectNotFoundError` -> `404`
- `ProjectPermissionError` -> `403`
- `ProjectLimitExceeded` -> `400`
- `InvalidProjectUpdate` -> `422`
- `RepositoryError` -> `500`

## Lifecycle

1. Install graceful-shutdown signal handlers.
2. Attempt NATS event-bus initialization.
3. Create `ProjectService` through the factory.
4. Expose FastAPI routes and health checks.
5. On shutdown, log service drain and release process resources.
