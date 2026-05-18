# Developer Service - Design

## Architecture

`developer_service` is a thin FastAPI aggregation service. It owns response composition and dependency health checks, but delegates source-of-truth reads to existing domain services.

```
microservices/developer_service/
├── main.py
├── developer_service.py
├── factory.py
├── models.py
└── routes_registry.py
```

## Runtime Flow

1. `main.py` authenticates the caller through `require_auth_or_internal_service`.
2. The route forwards `user_id`, `organization_id`, optional `project_id`, and `period_days`.
3. `DeveloperOverviewService` checks dependency health.
4. The service builds a minimal overview response with setup state and warnings.
5. The API returns a typed `DeveloperOverviewResponse`.

## Dependency Model

`DeveloperOverviewService` accepts optional clients for:

- organization service
- project service
- auth/credential service
- billing service
- trace service
- evaluation service

Clients are optional in the skeleton so tests can exercise degraded behavior without live infrastructure.

## Error Handling

- Missing service instance returns `503`.
- Invalid route input is handled by FastAPI/Pydantic.
- Dependency health exceptions are converted to `unhealthy`.
- Overview degradation is represented in `warnings[]`.

## Persistence

The skeleton owns no database schema. Future issues may add caches or materialized read models, but source-of-truth writes remain in domain services.

## Observability

- FastAPI health endpoint at `/health`.
- Developer dependency health at `/api/v1/developer/health`.
- Consul route metadata via `routes_registry.py`.
