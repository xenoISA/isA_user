# Developer Service - Product Requirements Document

## Product Overview

The Developer Service powers the Developer Portal Journey Cockpit by returning a server-backed overview of setup state, credentials, first-call status, usage, traces, and evaluation failures.

## Users

- Developers setting up an organization/project for API usage.
- Organization admins reviewing team readiness and credential status.
- Console UI flows that need one stable backend contract instead of multiple ad hoc client joins.

## Goals

- Provide `GET /api/v1/developer/overview`.
- Verify organization access before returning cockpit state.
- Return setup progress, next action, warnings, and dependency health.
- Degrade safely when downstream services fail.

## Non-Goals

- Owning project, credential, billing, trace, or eval persistence.
- Replacing source-of-truth services.
- Performing write-side setup actions in the initial skeleton.

## User Stories

### Story 1: Overview Contract

As a Console client, I can fetch one developer overview payload so the cockpit can render setup progress without stitching together service-specific contracts.

Acceptance:
- Response includes organization context, selected project, setup steps, credentials, first-call, usage, traces, eval failures, next action, and warnings.
- Missing downstream state is represented as warnings or blocked/todo setup steps.

### Story 2: Health Contract

As an operator, I can inspect dependency health for the developer aggregation boundary.

Acceptance:
- `GET /api/v1/developer/health` returns status, version, and dependency statuses.
- Missing clients report `not_configured`.

### Story 3: Authenticated Overview

As a platform service, I can call the overview endpoint with internal-service or authenticated caller credentials.

Acceptance:
- Unauthenticated requests are rejected by the shared auth dependency.
- The caller id is forwarded into the overview service.

## API Summary

- `GET /health`
- `GET /api/v1/developer/health`
- `GET /api/v1/developer/overview?organization_id={id}&project_id={id}&period_days=7`
