# Artifact Service - Product Requirements Document

## Product Summary

Artifact Service provides the backend for an artifact library: durable storage,
version history, sharing, remixing, runtime invocation, MCP approval, and scoped
artifact state. It lets users keep AI-generated outputs as reusable assets
instead of losing them inside chat transcripts.

## Users

- End users who save and reopen generated artifacts.
- Console users who test artifacts with runtime prompts and MCP tools.
- Admin and audit surfaces that need lifecycle events and ownership metadata.
- Downstream services that subscribe to artifact events for analytics and
  governance.

## Goals

- Persist artifacts with immutable versions and compact listing APIs.
- Enforce owner-scoped library access and explicit share-token access.
- Support revocable public and organization-scoped artifact shares.
- Allow users to remix shared artifacts into private owned copies.
- Track runtime usage and enforce daily call quotas.
- Gate MCP tool calls behind persisted user approval.
- Provide personal/shared artifact KV state without leaking cross-user data.

## Non-Goals

- General-purpose file storage. Large binary storage belongs in storage_service.
- Full document collaboration. Shared editing is outside this service boundary.
- Authorization policy authoring. Policy decisions are consumed here, not owned.
- Guaranteed upstream model/MCP availability. Runtime and MCP paths use safe
  fallback behavior when dependencies are unavailable.

## Functional Requirements

| ID | Requirement |
| --- | --- |
| ART-001 | Create an artifact with a required first version. |
| ART-002 | List artifacts by owner with scope, text query, cursor, and limit filters. |
| ART-003 | Read, update, soft-delete, and add versions for owner-owned artifacts. |
| ART-004 | Publish, revoke, and list share tokens for artifact owners. |
| ART-005 | Read public share payloads by token and optional version selector. |
| ART-006 | Remix valid shares into new private artifacts owned by the caller. |
| ART-007 | Invoke runtime prompts with quota tracking and model fallback. |
| ART-008 | Return runtime usage counters and remaining daily quota. |
| ART-009 | Persist MCP grant decisions and require approval for ungranted tool calls. |
| ART-010 | Read, write, and delete artifact KV entries by personal/shared scope. |
| ART-011 | Publish lifecycle events for mutations and runtime side effects. |
| ART-012 | Register health and route metadata through service discovery. |

## Acceptance Criteria

- Owner library APIs reject unauthorized users.
- Share APIs respect revoked and expired tokens.
- Org-scoped share reads require matching organization context.
- Runtime quota is enforced before model invocation.
- Runtime and MCP upstream failures return documented stub/fallback payloads.
- KV personal scope requires a user id and never returns another user's value.
- Shared KV writes fail unless the artifact has `storage_scope=shared`.
- All mutation paths publish best-effort events without breaking the main flow.
- API response models match `microservices.artifact_service.models`.

## Metrics

- Artifact create/read/update/delete success rate.
- Runtime calls per artifact/user/day and quota exhaustion rate.
- MCP approval prompt rate versus granted-call rate.
- Share creation, read, revoke, and remix counts.
- KV read/write/delete counts by scope.

