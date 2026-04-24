# Project Service Logic Contract

## BR-001: Create project
- Given an authenticated caller below the 100-project limit
- When they submit a valid create request
- Then a project is persisted for that caller and `project.create` is published

## BR-002: Enforce ownership on reads and mutations
- Given a project owned by another user
- When a caller requests get, update, delete, or set instructions
- Then the service returns `403`

## BR-003: Enforce project limit
- Given a caller who already owns 100 projects
- When they create another project
- Then the service returns `400` via `ProjectLimitExceeded`

## BR-004: Reject empty updates
- Given an update request with no fields
- When the caller hits `PUT /api/v1/projects/{project_id}`
- Then the service returns `422` via `InvalidProjectUpdate`

## BR-005: Preserve structured errors
- `ProjectNotFoundError` -> `404`
- `ProjectPermissionError` -> `403`
- `ProjectLimitExceeded` -> `400`
- `InvalidProjectUpdate` -> `422`
- `RepositoryError` -> `500` with safe detail

## BR-006: Instruction updates are auditable
- Given a valid instruction update
- When the owner changes `custom_instructions`
- Then the repository stores the new text and `project.set_instructions` is
  published when an event bus is configured
