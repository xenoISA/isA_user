# Project Service - Product Requirements Document (PRD)

## Product Overview

The Project Service provides centralized project management for the isA_user platform. It enables users to create, organize, and configure projects with custom instructions, file associations, and organizational scoping through a unified API.

**Product Vision**: Deliver a production-ready project management service with clean separation of concerns, testable architecture, and full observability — matching the quality bar set by authorization_service and other mature isA_user microservices.

**Key Capabilities**:
- Project CRUD lifecycle (create, read, update, delete)
- Custom instructions per project
- File association and management
- Organization-scoped project access
- Audit trail for compliance
- Inter-service client SDK

---

## Target Users

### 1. End Users (Individuals)
- Create and manage personal projects
- Set custom instructions per project
- Organize files within projects
- View project history and audit trail

### 2. Organization Members
- Access organization-scoped projects
- Collaborate on shared project configurations
- View project activity within their org

### 3. Platform Services (Internal)
- Query project configuration for agent context
- Resolve custom instructions during session setup
- Validate project ownership and access

### 4. API Developers
- Integrate project management into client applications
- Use ProjectServiceClient for inter-service calls
- Build project selection and configuration UIs

---

## Epics and User Stories

### Epic 1: Protocol-Based Dependency Injection
**Goal**: Enable testable, loosely-coupled service architecture

**User Stories**:
- As a service maintainer, I want to inject mock repositories into ProjectService so that I can test business logic in isolation
- As a service maintainer, I want to inject an event bus so that I can test audit logging without external dependencies
- As a developer, I want a factory function that accepts optional dependencies so that production and test configurations are explicit

**Acceptance Criteria**:
- `ProjectService.__init__` accepts optional `repository: ProjectRepositoryProtocol`
- `ProjectService.__init__` accepts optional `event_bus: EventBusProtocol`
- Factory function `create_project_service()` supports mock injection
- Service methods do not instantiate repository at import time
- Unit tests pass without PostgreSQL connection

### Epic 2: Structured Error Responses
**Goal**: Consistent, debuggable error handling across all endpoints

**User Stories**:
- As a service operator, I want structured error responses so that I can debug issues from logs and API output
- As an API consumer, I want consistent error shapes so that I can handle failures programmatically
- As a developer, I want domain-specific exceptions so that error handling is explicit

**Acceptance Criteria**:
- All endpoints return `{status, error, detail}` structure
- `ProjectNotFoundError` -> 404, `PermissionError` -> 403, `ProjectLimitExceeded` -> 400, `InvalidProjectUpdate` -> 422
- Database errors wrapped in `RepositoryError` -> 500 with safe message
- All errors logged with context (user_id, project_id, timestamp)

### Epic 3: Audit Logging
**Goal**: Compliance-ready activity tracking for all project operations

**User Stories**:
- As a compliance auditor, I want to trace who accessed which projects and when
- As a service operator, I want CRUD events published to an event bus for centralized logging
- As a project owner, I want to view recent activity on my projects

**Acceptance Criteria**:
- Every CRUD operation logs: user_id, project_id, action, timestamp, success/failure
- Audit logs sent to event bus (if provided)
- Audit endpoint `GET /api/v1/projects/{project_id}/audit?limit=50`
- Audit endpoint requires ownership or admin role

### Epic 4: Injectable Configuration
**Goal**: Eliminate hardcoded defaults; support environment-driven configuration

**User Stories**:
- As a DevOps engineer, I want to configure database connections via environment variables
- As a developer, I want configuration injected at startup so that I can run against different environments

**Acceptance Criteria**:
- ProjectRepository accepts `config: ConfigManager` parameter
- No hardcoded "localhost" or "postgres" defaults in repository
- Config supports override via environment variables or file

### Epic 5: Deployment Readiness
**Goal**: Production-grade health checks, graceful shutdown, and service registration

**User Stories**:
- As a DevOps engineer, I want health check endpoints so that K8s can manage pod lifecycle
- As a platform engineer, I want graceful shutdown so that in-flight requests complete before termination
- As an operator, I want Consul registration so that the service is discoverable

**Acceptance Criteria**:
- `/health` returns `{status, service, version, db_connected}`
- Graceful shutdown waits for in-flight requests
- Startup/shutdown events logged with timestamp
- Routes auto-register with Consul via routes_registry
- Integration test confirms lifecycle

### Epic 6: Client SDK
**Goal**: Enable other services to call project_service without raw HTTP

**User Stories**:
- As a service developer, I want a typed client library so that I can call project_service safely
- As an SDK consumer, I want configurable retries and timeouts

**Acceptance Criteria**:
- `client.py` provides `ProjectServiceClient` class
- Methods: `create_project()`, `get_project()`, `list_projects()`, `update_project()`, `delete_project()`, `set_instructions()`
- Auth header injection and response parsing
- Optional retries and timeout configuration

---

## Edge Cases

- **Concurrency**: Simultaneous project creation by different users succeeds independently
- **Cascading deletes**: Deleting a project cleans up associated files
- **Ownership validation**: Accessing another user's project returns 403 (not 404, to avoid leaking existence)
- **Name conflicts**: Same project name allowed for different owners; unique constraint on (user_id, name) if enforced
- **Large instructions**: 8000+ char custom_instructions updates succeed
- **Soft deletes**: Deleted projects excluded from list; get returns 404
- **Org-level access**: Org membership enforced by authorization_service (separation of concerns)

---

## Out of Scope

- Billing/cost tracking (not relevant to project CRUD)
- BaseService inheritance from isA_MCP (architectural mismatch)
- ServiceBuilder pattern from isA_Agent_SDK (over-engineered for CRUD)
- File storage implementation (handled by storage_service)

---

## Related Issues

- #291 — Integrate project_service into deployment pipeline
- #258 — Add project CRUD API endpoints (closed)
