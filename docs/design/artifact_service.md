# Artifact Service - Design

## Architecture

Artifact Service is a FastAPI microservice with a route layer, business service,
repository, Pydantic models, route registry, and factory wiring.

```text
microservices/artifact_service/
├── main.py                 # FastAPI routes, health, Consul registration
├── artifact_service.py     # Business logic and upstream runtime/MCP adapters
├── artifact_repository.py  # PostgreSQL access
├── models.py               # Pydantic request/response/domain models
├── protocols.py            # Repository/event-bus protocols and errors
├── factory.py              # Service construction
└── routes_registry.py      # Gateway/Consul route metadata
```

## Persistence

The repository owns SQL access for:

- `artifact.artifacts`
- `artifact.artifact_versions`
- `artifact.artifact_shares`
- `artifact.artifact_runtime_usage`
- `artifact.artifact_mcp_grants`
- `artifact.artifact_kv`

Repository methods return model-ready dictionaries or Pydantic models and keep
database details out of the route layer.

## Service Layer

`ArtifactService` coordinates validation, authorization, repository calls,
event publication, and best-effort upstream integration.

Important invariants:

- Creation validates title and first version content before persistence.
- Owner checks happen in service methods before mutating protected resources.
- Share-token reads validate token activity and organization scope.
- Runtime quota is checked before model invocation.
- MCP tool calls check persisted grants before invoking upstream tools.
- KV scope validation happens before repository access.

## Runtime Model Calls

`runtime_invoke` builds a prompt envelope from artifact metadata and version
content, forwards the caller bearer token to isA_Model when available, records
usage, and publishes `artifact.runtime.invoked`.

If isA_Model is unavailable or returns invalid content, the method returns the
documented stub response and still records usage. This protects the API surface
from transient upstream failures.

## MCP Tool Calls

MCP calls use a session-aware streamable-HTTP client:

1. Initialize session and cache `Mcp-Session-Id` by artifact/server.
2. Send `notifications/initialized`.
3. Call `tools/call`.
4. Reset and retry once when the session expires.

Calls without an active `allow` + `always` grant return an approval prompt.
Transport failures return a stub result so the endpoint remains stable.

## Eventing

The service publishes best-effort events for artifact creation, update, delete,
version creation, sharing, runtime invocation, MCP approval, and KV changes.
Event publication failures must not corrupt repository state or turn successful
mutations into API failures unless the business operation itself fails.

## API Surface

Core route families:

- `POST /api/v1/artifacts`
- `GET /api/v1/artifacts`
- `GET/PATCH/DELETE /api/v1/artifacts/{artifact_id}`
- `POST /api/v1/artifacts/{artifact_id}/versions`
- `POST /api/v1/artifacts/{artifact_id}/publish`
- `POST /api/v1/artifacts/{artifact_id}/revoke`
- `GET /api/v1/artifacts/{artifact_id}/shares`
- `GET /api/v1/shares/artifacts/{token}`
- `POST /api/v1/artifacts/remix`
- `POST /api/v1/artifacts/{artifact_id}/runtime/invoke`
- `GET /api/v1/artifacts/{artifact_id}/runtime/usage`
- `POST /api/v1/artifacts/{artifact_id}/mcp/approve`
- `POST /api/v1/artifacts/{artifact_id}/mcp/call`
- `GET /api/v1/artifacts/{artifact_id}/mcp/grants`
- `GET/PUT/DELETE /api/v1/artifacts/{artifact_id}/kv/{key}`

## Failure Handling

- Domain errors map to 400, 403, or 404 in the route layer.
- Unexpected route errors return 500 with logging.
- Runtime/MCP upstream errors fall back to stable stub payloads.
- Event publication is best-effort and logged by the service.

