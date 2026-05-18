# Developer Service - Logic Contract

## Business Rules

### BR-001: Overview Requires Organization Context

`GET /api/v1/developer/overview` requires an `organization_id`. The service must not return developer setup state without an organization boundary.

### BR-002: Project Selection Drives Setup State

- If `project_id` is absent, the project step is `todo`.
- If `project_id` is present, the selected project is reflected in `selected_project` and project setup is `complete`.
- Credential and first-call steps remain blocked/todo until source services report active credentials and usage.

### BR-003: Partial Data Is Explicit

When a downstream dependency is unavailable, the overview response includes a warning with the dependency source and degraded status.

### BR-004: No Source-of-Truth Writes

The initial developer service is read-only. Project, credential, billing, trace, and eval writes stay in their owning services.

### BR-005: Health Reflects Dependency State

The health response is `healthy` only when all configured dependencies are healthy. Missing clients are `not_configured`; failing clients are `unhealthy`.

## Route Contracts

- `GET /health` returns platform health output.
- `GET /api/v1/developer/health` returns dependency health.
- `GET /api/v1/developer/overview` returns `DeveloperOverviewResponse`.

## Edge Cases

- Missing project: overview remains organization-scoped with project action.
- Missing client: overview still returns with warning.
- Client health exception: dependency status becomes `unhealthy`.
