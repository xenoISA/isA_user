# Sharing Service Logic Contract

## BR-001: Owners can create share links
- Given a valid session owned by the caller
- When the caller submits `POST /api/v1/sessions/{session_id}/shares`
- Then the service generates a token, persists the share, and returns a share
  URL

## BR-002: Non-owners cannot create or revoke shares
- Given a session owned by another user
- When a caller tries to create or delete a share
- Then the service returns `403`

## BR-003: Public token access is the auth model
- Given a valid share token
- When a client requests `GET /api/v1/shares/{token}`
- Then the service returns session content without requiring a user session

## BR-004: Expired and revoked links fail distinctly
- Unknown or revoked tokens return `404`
- Expired tokens return `410`

## BR-005: Access is observable
- Successful public access increments `access_count`
- `share.accessed` is emitted when an event bus is configured

## BR-006: Share lifecycle events are best-effort
- `share.created`, `share.accessed`, and `share.revoked` should be emitted when
  possible
- HTTP requests still complete when event publication fails
