# Sharing Service Design

## Architecture

`sharing_service` is a FastAPI microservice that fronts a repository-backed
share table and delegates session reads to `session_service`.

```text
FastAPI main.py
  -> SharingService
     -> ShareRepository
     -> SessionServiceClient
     -> optional NATS event bus
  -> Consul registration + health checks
```

## File Structure

```text
microservices/sharing_service/
├── main.py
├── factory.py
├── models.py
├── protocols.py
├── sharing_service.py
├── sharing_repository.py
├── routes_registry.py
├── clients/session_client.py
└── events/
    ├── handlers.py
    └── publishers.py
```

## API Surface

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | basic health |
| `GET` | `/api/v1/sharing/health` | versioned health |
| `POST` | `/api/v1/sessions/{session_id}/shares` | create share link |
| `GET` | `/api/v1/sessions/{session_id}/shares` | list active shares |
| `GET` | `/api/v1/shares/{token}` | public access by token |
| `DELETE` | `/api/v1/shares/{token}` | revoke share |

## Runtime Rules

- Event bus initialization is optional; the service still starts without NATS.
- Consul registration is enabled when `config.consul_enabled` is true.
- The share repository is lazily constructed inside `SharingService` when tests
  do not inject a repository.

## Error Mapping

- `ShareValidationError` -> `400`
- `SharePermissionError` -> `403`
- `ShareNotFoundError` -> `404`
- `ShareExpiredError` -> `410`
- `ShareServiceError` -> `500`

## Lifecycle

1. Install graceful-shutdown signal handlers.
2. Attempt event-bus initialization.
3. Create `SharingService` through the factory.
4. Register Consul TTL checks when enabled.
5. Serve token and owner endpoints.
6. On shutdown, drain requests, deregister from Consul, and close the event
   bus.
