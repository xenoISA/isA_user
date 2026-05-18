# Developer Service - Domain Context

## Domain

`developer_service` is the backend read-model boundary for the Developer Portal Journey Cockpit. It aggregates organization, project, credential, billing, trace, and evaluation state into a single cockpit response without owning those source-of-truth records.

## Responsibilities

- Return setup progress for organization selection, project activation, credential creation, and first API call.
- Surface degraded dependency state as warnings instead of misleading zero values.
- Keep Developer Portal orchestration out of Console and out of domain services such as auth, project, and billing.
- Provide a stable backend contract for Console stories `xenoISA/isA_Console#600`, `#601`, `#603`, and `#606`.

## Boundaries

- Source-of-truth organization membership remains in organization service.
- Source-of-truth project ownership remains in project service.
- API key and service account credential state remains in auth service.
- Usage and cost data remains in billing service.
- Trace and eval details remain in their respective telemetry/evaluation systems.

## Events

The initial skeleton is read-only and emits no domain events. Future write workflows should publish explicit developer journey events only after the source-of-truth service has accepted the change.

## Failure Policy

Dependency failure produces a partial response with `warnings[]` and degraded health. The service must not invent project, credential, usage, trace, or eval data when a dependency is unavailable.
