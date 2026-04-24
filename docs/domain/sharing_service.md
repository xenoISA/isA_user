# Sharing Service Domain Context

## Overview

The Sharing Service owns token-based links for read-only or limited-access
session sharing. The share token is the credential: public access is allowed
only when a valid share token is present.

## Core Entities

### Share Link
- `id`: share record identifier
- `session_id`: shared session
- `owner_id`: user who created the share
- `share_token`: URL-safe bearer token
- `permissions`: one of `view_only`, `can_comment`, `can_edit`
- `expires_at`: optional expiry timestamp
- `access_count`: number of public accesses
- `created_at` / `updated_at`: lifecycle timestamps

### Shared Session Snapshot
- `session_id`: referenced session
- `session_summary`: public summary text
- `messages`: session message payload exposed to the recipient
- `message_count`: summary count
- `permissions`: effective share permissions

## Domain Rules

1. Only the session owner can create or revoke shares.
2. Public share access does not require a user session; the token is the auth.
3. Expired links return `410 Gone`.
4. Revoked or unknown links return `404`.
5. Every successful public access increments `access_count`.
6. Share creation, access, and revocation publish best-effort events when the
   event bus is available.

## Bounded Context

### Internal Dependencies
- `SharingService`: domain logic and permission checks
- `ShareRepository`: persistence for share links
- `SessionServiceClient`: lookup for session ownership and message payloads

### External Dependencies
- `session_service`: source of session metadata and messages
- `NATS`: optional event publication
- `Consul`: service registration
- `PostgreSQL`: share-link storage

## Events Published
- `share.created`
- `share.accessed`
- `share.revoked`

## Primary Use Cases

### UC-1: Create Share Link
1. Owner requests a share for a session.
2. Service verifies session ownership through `session_service`.
3. Service generates a URL-safe token and optional expiry.
4. Repository persists the share record.
5. Service returns a share URL and publishes `share.created`.

### UC-2: Access Shared Session
1. Recipient calls `/api/v1/shares/{token}`.
2. Service validates token existence and expiry.
3. Repository increments the access counter.
4. Session details and messages are fetched from `session_service`.
5. Service returns the shared session payload and publishes `share.accessed`.

### UC-3: Revoke Share Link
1. Owner requests deletion by token.
2. Service verifies ownership.
3. Repository deletes the share record.
4. Service returns success and publishes `share.revoked`.
