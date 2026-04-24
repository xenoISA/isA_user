# Sharing Service - System Contract (Layer 6)

## Overview

This document defines HOW `sharing_service` implements the standard service
patterns.

**Service**: `sharing_service`  
**Port**: `8255`  
**Version**: `1.0.0`

## 1. Architecture Pattern

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
```

- `main.py` owns FastAPI routes, health checks, and lifecycle wiring.
- `SharingService` owns token generation, expiry checks, and revoke logic.
- `ShareRepository` persists share links.
- `SessionServiceClient` resolves session ownership and messages.

## 2. Dependency Injection Pattern

- `create_sharing_service(config, event_bus=None, share_repo=None, session_client=None)`
  wires production or test dependencies.
- `SharingService` lazily initializes repository and session client when tests do
  not inject them.

## 3. API Contract

| Method | Path | Auth |
|--------|------|------|
| `GET` | `/health` | no |
| `GET` | `/api/v1/sharing/health` | no |
| `POST` | `/api/v1/sessions/{session_id}/shares` | owner |
| `GET` | `/api/v1/sessions/{session_id}/shares` | owner |
| `GET` | `/api/v1/shares/{token}` | token only |
| `DELETE` | `/api/v1/shares/{token}` | owner |

## 4. Event Contract

When the event bus is available, the service publishes:
- `share.created`
- `share.accessed`
- `share.revoked`

## 5. Error Handling Contract

- `ShareValidationError` -> `400`
- `SharePermissionError` -> `403`
- `ShareNotFoundError` -> `404`
- `ShareExpiredError` -> `410`
- `ShareServiceError` -> `500`

## 6. Lifecycle Contract

1. Install graceful-shutdown handlers.
2. Attempt event-bus initialization.
3. Create `SharingService` through the factory.
4. Register Consul TTL checks when enabled.
5. Drain requests and close the event bus on shutdown.
