# Artifact Service - System Contract

## Overview

This document defines how `artifact_service` implements the standard isA
microservice patterns.

**Service**: artifact_service
**Port**: 8291
**Category**: User Microservice
**Version**: 1.0.0

## 1. Architecture Pattern

| Layer | File | Responsibility |
| --- | --- | --- |
| Routes | `microservices/artifact_service/main.py` | FastAPI endpoints, error mapping, health, Consul lifecycle. |
| Service | `microservices/artifact_service/artifact_service.py` | Domain validation, authorization, events, runtime/MCP adapters. |
| Repository | `microservices/artifact_service/artifact_repository.py` | PostgreSQL persistence and row shaping. |
| Models | `microservices/artifact_service/models.py` | Pydantic schemas and enums. |
| Protocols | `microservices/artifact_service/protocols.py` | Repository/event interfaces and domain errors. |
| Factory | `microservices/artifact_service/factory.py` | Service construction and dependency injection. |

## 2. Dependency Injection Pattern

The factory creates `ArtifactService` with repository and optional event bus.
Tests may instantiate `ArtifactService.__new__` with fake repositories for
isolated unit coverage. Runtime and MCP dependencies are imported lazily so
unit tests can patch service-level methods without starting upstream services.

## 3. Repository Pattern

The repository hides SQL details and exposes async methods for:

- artifact CRUD and listing
- version creation
- share token persistence
- runtime usage counters
- MCP grants
- KV get/put/delete

Service methods should not embed SQL.

## 4. Event Pattern

The service publishes best-effort events through `EventBusProtocol`. Event
publication failure must be logged or ignored without corrupting the primary
repository mutation.

## 5. Error Pattern

Domain errors are raised from service/protocol classes:

- `ArtifactValidationError`
- `ArtifactPermissionError`
- `ArtifactNotFoundError`
- `ArtifactQuotaExceededError`

`main.py` maps them to HTTP responses. Unexpected exceptions are logged and
returned as 500s.

## 6. Configuration Pattern

Configuration comes from environment variables and `ConfigManager`:

- `ARTIFACT_DAILY_QUOTA`
- `ARTIFACT_RUNTIME_MODEL`
- `ARTIFACT_RUNTIME_PROVIDER`
- `ARTIFACT_RUNTIME_MAX_TOKENS`
- `ISA_MODEL_URL`
- `ISA_MCP_URL`

Environment values are resolved at call time where tests need overrides.

## 7. Security Pattern

- Owner checks protect mutations and private reads.
- Share tokens gate non-owner reads.
- Org share reads require matching organization context.
- Bearer tokens are forwarded to isA_Model and isA_MCP when present.
- MCP tool calls require persisted user approval.

## 8. Observability Pattern

The service uses structured logging, common health checks, metrics setup, route
metadata, and Consul registration. Runtime and MCP fallback paths log warnings
with upstream failure details.

## 9. Resilience Pattern

Model and MCP upstream calls are best-effort. The API returns stable fallback
payloads when dependencies are unavailable, while quota and usage accounting
remain consistent.

## 10. Test Pattern

Unit tests cover runtime invocation, MCP sessions, JWT pass-through, quota
behavior, and fallback paths. Golden API tests cover artifact CRUD, sharing,
remix, runtime, MCP, and KV route behavior against a running service.

## 11. Contract Pattern

Layer 4 data fixtures live in
`tests/contracts/artifact_service/data_contract.py`. Business rules live in
`logic_contract.md`. This system contract defines implementation boundaries.

## 12. Deployment Pattern

The service registers route metadata from `routes_registry.py`, exposes
`/health`, and runs on port 8291 in local development and gateway-routed
environments.

