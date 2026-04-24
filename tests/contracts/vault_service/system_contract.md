# Vault Service - System Contract (Layer 6)

## Overview

This document defines HOW `vault_service` implements the standard service
patterns.

**Service**: `vault_service`  
**Port**: `8214`  
**Version**: `1.0.0`

## 1. Architecture Pattern

```text
microservices/vault_service/
├── main.py
├── factory.py
├── models.py
├── vault_service.py
├── vault_repository.py
├── routes_registry.py
├── client.py
├── clients/
└── events/
```

- `main.py` owns FastAPI routing, auth extraction, health checks, and startup.
- `VaultService` owns encryption-aware secret lifecycle behavior.
- `VaultRepository` owns PostgreSQL persistence.
- Optional blockchain and NATS integrations are wired at startup.

## 2. Dependency Injection Pattern

- `create_vault_service(config, event_bus=None, blockchain_client=None)` wires
  production dependencies.
- `get_vault_service()` exposes the initialized singleton to FastAPI routes.

## 3. API Contract

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | basic health |
| `GET` | `/api/v1/vault/health` | versioned health |
| `GET` | `/info` | service metadata |
| `POST` | `/api/v1/vault/secrets` | create secret |
| `GET` | `/api/v1/vault/secrets/{vault_id}` | get secret |
| `GET` | `/api/v1/vault/secrets` | list secrets |
| `PUT` | `/api/v1/vault/secrets/{vault_id}` | update secret |
| `DELETE` | `/api/v1/vault/secrets/{vault_id}` | delete secret |
| `POST` | `/api/v1/vault/secrets/{vault_id}/rotate` | rotate secret |
| `POST` | `/api/v1/vault/secrets/{vault_id}/test` | test credential |
| `POST` | `/api/v1/vault/secrets/{vault_id}/share` | share secret |
| `GET` | `/api/v1/vault/shared` | list shared secrets |
| `GET` | `/api/v1/vault/audit-logs` | audit log view |
| `GET` | `/api/v1/vault/stats` | usage stats |

## 4. Service Registration Contract

- Consul metadata comes from `routes_registry.py`.
- Tags: `v1`, `user-microservice`, `vault`, `security`
- Capabilities: secret management, credential storage, secret sharing, audit
  logging, encryption

## 5. Event Contract

When NATS is available, startup registers handlers from `events/handlers.py`.
The service publishes vault lifecycle events and subscribes to wildcard
`*.user.deleted` cleanup flows.

## 6. Lifecycle Contract

1. Install graceful-shutdown handlers.
2. Optionally initialize the blockchain client.
3. Attempt NATS event-bus initialization.
4. Create `VaultService` through the factory.
5. Register event subscriptions when the event bus is available.
6. Register Consul TTL checks when enabled.
7. On shutdown, drain requests, close dependencies, and deregister from Consul.
