# Sharing Service PRD

## Product Overview

The Sharing Service enables users to create secure, revocable share links for
session content without exposing the full authenticated application.

## Users

### Owners
- create links for sessions they own
- choose permission level and optional expiry
- revoke links at any time

### Recipients
- open a share URL without signing in
- view the shared session payload allowed by the link

### Platform Services
- audit share creation/access/revocation through events
- resolve shared session views without duplicating session logic

## Goals

1. Make session sharing one-click and URL-driven.
2. Keep authorization rules simple: owner-controlled, token-authenticated.
3. Provide observability through access counters and events.

## User Stories

### Story 1: Create a Link
As a session owner, I want a share URL so I can send my session to another
person without asking them to log in.

Acceptance criteria:
- `POST /api/v1/sessions/{session_id}/shares` creates a tokenized share link.
- Owner can choose permissions and optional expiry.
- Non-owners receive `403`.

### Story 2: Open a Link
As a recipient, I want to open a share URL directly so I can read the session
content with minimal friction.

Acceptance criteria:
- `GET /api/v1/shares/{token}` returns shared session content for valid links.
- Unknown tokens return `404`.
- Expired links return `410`.

### Story 3: Revoke a Link
As an owner, I want to revoke a link so previously shared URLs stop working.

Acceptance criteria:
- `DELETE /api/v1/shares/{token}` revokes an existing link.
- Revoked links stop resolving immediately.

### Story 4: Audit Usage
As a platform operator, I want to see share activity so support and security
teams can reason about access.

Acceptance criteria:
- Service increments `access_count` on successful access.
- `share.created`, `share.accessed`, and `share.revoked` events are emitted
  when the event bus is available.

## Out of Scope

- collaborative editing semantics beyond the stored permission field
- anonymous write access to session data
- full document/file sharing outside session payloads
