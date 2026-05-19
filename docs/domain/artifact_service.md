# Artifact Service - Domain Context

## Overview

Artifact Service owns persisted user artifacts created from AI sessions: code
blocks, markdown, HTML, SVG, prompts, generated documents, and other reusable
outputs that users want to reopen, publish, remix, or run later.

The service turns transient chat outputs into durable product objects. It keeps
artifact metadata, immutable versions, share links, runtime usage, MCP grants,
and scoped key-value storage separate from the chat/session domain so artifacts
can be managed independently across Console, Admin, and user-facing surfaces.

## Core Concepts

| Concept | Meaning |
| --- | --- |
| Artifact | Durable top-level object owned by a user, optionally scoped to an organization. |
| Version | Immutable content snapshot attached to an artifact. |
| Visibility | Owner-only, unlisted, organization-scoped, or public sharing intent. |
| Share token | Revocable link that exposes a selected artifact version. |
| Remix | Copying a shared artifact into a new owner-owned artifact. |
| Runtime invocation | User prompt execution against an artifact with daily quota tracking. |
| MCP grant | User approval for an artifact to call an MCP tool. |
| KV storage | Personal or shared JSON state attached to an artifact. |

## Ownership Model

Artifacts are owned by `owner_user_id`. `owner_org_id` is optional and supports
organization visibility and future governance controls. Direct library reads and
writes are owner-scoped; non-owner access is mediated through share tokens.

Private artifacts are never returned to other users through the library API.
Public and organization sharing are expressed through explicit share records so
revocation, expiry, and version pinning remain auditable.

## Lifecycle

1. A user creates an artifact with a required first version.
2. The owner may list, read, update metadata, add versions, or soft-delete it.
3. The owner may publish a share token with optional version pin and expiry.
4. Any valid token holder may read the public share payload.
5. A token holder may remix the artifact into their own private artifact.
6. Runtime, MCP, and KV features operate only after the artifact exists.

## Domain Rules

- Artifact titles must be non-empty and bounded for library display.
- Creation always requires a first version with non-empty content.
- Version numbers are immutable and monotonically increasing per artifact.
- Soft delete hides artifacts from normal library reads while preserving audit
  and lineage state.
- Owner-only mutations must reject non-owner callers.
- Share tokens must be unguessable, revocable, and expiry-aware.
- Organization shares require an organization identifier from the request or the
  artifact owner organization.
- Runtime calls must enforce the configured daily quota before invoking models.
- MCP calls without an active `allow` + `always` grant must return an approval
  prompt instead of executing the tool.
- Personal KV scope requires a user id; shared KV writes require the artifact to
  opt into shared storage.

## Integrations

| Integration | Purpose |
| --- | --- |
| PostgreSQL | Artifact, version, share, runtime usage, MCP grant, and KV persistence. |
| NATS | Artifact lifecycle, runtime, MCP, and KV events for audit/analytics. |
| Consul | Service registration and route metadata for gateway discovery. |
| isA_Model | Best-effort runtime inference with stub fallback. |
| isA_MCP | Session-aware MCP tool calls with approval gating. |

## Privacy And Safety

Artifact content can contain user data, generated code, or business context.
The service preserves owner boundaries, uses explicit share grants for
distribution, forwards bearer tokens to upstream runtime services when present,
and falls back safely when upstream model or MCP transports are unavailable.

