# Developer Service - System Contract

## Overview

`developer_service` is a FastAPI read-model service for the Developer Portal Journey Cockpit.

**Service**: `developer_service`  
**Port**: `8261`  
**Category**: User Microservice

## Architecture Pattern

```
microservices/developer_service/
├── __init__.py
├── developer_service.py
├── factory.py
├── main.py
├── models.py
└── routes_registry.py
```

## Dependency Injection

`DeveloperOverviewService` accepts optional clients for organization, project, credential, billing, trace, and evaluation services. Tests inject fake clients directly.

## Auth Contract

`main.py` uses `require_auth_or_internal_service` for the protected overview endpoint. Health routes are public.

## Persistence Contract

The skeleton has no database. It returns typed read models from source services and warning metadata.

## Route Contract

- `GET /health`
- `GET /api/v1/developer/health`
- `GET /api/v1/developer/overview`

## Health Contract

`DeveloperHealthResponse` includes:

- `status`
- `service`
- `version`
- `dependencies`
- `timestamp`

## Test Pyramid

- Unit: model defaults and empty overview builder.
- Component: dependency health and warning behavior.
- Integration: routes registry metadata.
- API: FastAPI overview contract with dependency overrides.
- Smoke: minimal create service and overview workflow.

## Operational Notes

The service registers route metadata through Consul when Consul is enabled. APISIX/local-dev registration is tracked separately by issue #430.
