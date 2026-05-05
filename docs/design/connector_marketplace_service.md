# Connector Marketplace Service - API Contract

## Design Overview

**Service Name**: connector_marketplace_service
**Protocol**: HTTP REST API
**Parent Epic**: xenoISA/isA_#183
**Source Issue**: xenoISA/isA_user#342
**Status**: Contract ready for implementation

The connector marketplace service provides the durable catalog and per-user
install/connect state used by the isA_ ConnectorMarketplace UI. The UI must not
fabricate connected state when this API is unavailable; the backend is the
source of truth for catalog availability, connection status, provider auth
handoff, and disconnect state.

## Ownership And Auth

- Catalog reads may be public to authenticated users, but install state is
  always scoped to the authenticated user.
- Install/connect/disconnect operations require an authenticated user context.
- Clients may pass `user_id` only where existing isA_user gateway conventions
  require it; the service must validate that it matches the authenticated user.
- Users can view and mutate only their own connector install records.
- Ownership mismatch returns `403 forbidden`; missing auth returns `401
  unauthenticated`.

## Connector Catalog Model

### ConnectorCatalogItem

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `id` | string | yes | Stable provider id, for example `google_calendar` |
| `name` | string | yes | User-visible name |
| `description` | string | yes | Short marketplace description |
| `icon` | string | no | Icon id or URL understood by clients |
| `category` | string | yes | `calendar`, `storage`, `crm`, `email`, `productivity`, or `custom` |
| `auth_type` | string | yes | `oauth2`, `api_key`, `none`, or `custom` |
| `capabilities` | string[] | yes | Machine-readable capabilities |
| `availability` | string | yes | `available`, `beta`, `disabled`, or `unsupported` |
| `provider_metadata` | object | no | OAuth scopes, provider slug, docs URL |
| `created_at` | string | yes | ISO 8601 UTC |
| `updated_at` | string | yes | ISO 8601 UTC |

### ConnectorInstallState

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `id` | string | yes | Opaque install id, recommended prefix `uci_` |
| `owner_user_id` | string | yes | Authenticated owner |
| `connector_id` | string | yes | References `ConnectorCatalogItem.id` |
| `status` | string | yes | `connected`, `pending_auth`, `error`, or `disconnected` |
| `auth_url` | string | no | Present only when provider auth handoff is required |
| `last_synced_at` | string | no | ISO 8601 UTC |
| `error_code` | string | no | Stable provider/service error code |
| `error_message` | string | no | User-safe error summary |
| `created_at` | string | yes | ISO 8601 UTC |
| `updated_at` | string | yes | ISO 8601 UTC |

## REST API

Base path: `/api/v1/connectors`

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/connectors/catalog` | List connector catalog items |
| `GET` | `/api/v1/connectors/installed` | List authenticated user's install states |
| `GET` | `/api/v1/connectors/{connector_id}` | Fetch catalog item plus current user state |
| `POST` | `/api/v1/connectors/{connector_id}/install` | Create or resume install/connect flow |
| `POST` | `/api/v1/connectors/{connector_id}/disconnect` | Disconnect an installed connector |
| `GET` | `/api/v1/connectors/{connector_id}/status` | Fetch current user state for one connector |

### Catalog List

`GET /api/v1/connectors/catalog?category=calendar&query=google&include_disabled=false`

Response:

```json
{
  "connectors": [
    {
      "id": "google_calendar",
      "name": "Google Calendar",
      "description": "Sync events and availability from Google Calendar.",
      "icon": "logos:google-calendar",
      "category": "calendar",
      "auth_type": "oauth2",
      "capabilities": ["calendar.read", "calendar.write", "availability.read"],
      "availability": "available",
      "provider_metadata": {
        "provider": "google",
        "scopes": ["calendar.events.readonly"],
        "docs_url": "https://developers.google.com/calendar/api"
      },
      "created_at": "2026-05-05T00:00:00Z",
      "updated_at": "2026-05-05T00:00:00Z"
    }
  ],
  "count": 1
}
```

### Installed Connectors

`GET /api/v1/connectors/installed?status=connected`

Response:

```json
{
  "installed": [
    {
      "id": "uci_123",
      "owner_user_id": "usr_123",
      "connector_id": "google_calendar",
      "status": "connected",
      "last_synced_at": "2026-05-05T00:00:00Z",
      "created_at": "2026-05-05T00:00:00Z",
      "updated_at": "2026-05-05T00:00:00Z"
    }
  ],
  "count": 1
}
```

### Catalog Item With User State

`GET /api/v1/connectors/google_calendar`

Response:

```json
{
  "connector": {
    "id": "google_calendar",
    "name": "Google Calendar",
    "description": "Sync events and availability from Google Calendar.",
    "icon": "logos:google-calendar",
    "category": "calendar",
    "auth_type": "oauth2",
    "capabilities": ["calendar.read", "calendar.write", "availability.read"],
    "availability": "available",
    "created_at": "2026-05-05T00:00:00Z",
    "updated_at": "2026-05-05T00:00:00Z"
  },
  "install_state": {
    "id": "uci_123",
    "owner_user_id": "usr_123",
    "connector_id": "google_calendar",
    "status": "pending_auth",
    "auth_url": "https://auth.example/connect/google_calendar",
    "created_at": "2026-05-05T00:00:00Z",
    "updated_at": "2026-05-05T00:00:00Z"
  }
}
```

### Install Or Connect

`POST /api/v1/connectors/{connector_id}/install`

Request:

```json
{
  "return_url": "https://app.example/settings?tab=integrations",
  "requested_capabilities": ["calendar.read"]
}
```

Response for OAuth providers: `202 Accepted`

```json
{
  "install_state": {
    "id": "uci_123",
    "owner_user_id": "usr_123",
    "connector_id": "google_calendar",
    "status": "pending_auth",
    "auth_url": "https://auth.example/connect/google_calendar",
    "created_at": "2026-05-05T00:00:00Z",
    "updated_at": "2026-05-05T00:00:00Z"
  }
}
```

Response for no-auth connectors: `200 OK` with `status: "connected"`.

### Disconnect

`POST /api/v1/connectors/{connector_id}/disconnect`

Response:

```json
{
  "install_state": {
    "id": "uci_123",
    "owner_user_id": "usr_123",
    "connector_id": "google_calendar",
    "status": "disconnected",
    "created_at": "2026-05-05T00:00:00Z",
    "updated_at": "2026-05-05T00:00:00Z"
  }
}
```

## Error Contract

All non-2xx errors return a stable machine-readable code:

```json
{
  "error": {
    "code": "provider_auth_required",
    "message": "Provider authorization is required before this connector can be used."
  }
}
```

Required codes:

| HTTP | Code | Meaning |
| --- | --- | --- |
| 400 | `validation_error` | Invalid query, return URL, or requested capabilities |
| 401 | `unauthenticated` | Missing or invalid authenticated user |
| 403 | `forbidden` | Authenticated user cannot mutate this install state |
| 404 | `connector_not_found` | Connector id is not in the catalog |
| 409 | `connector_disabled` | Connector exists but is not available for install |
| 409 | `provider_auth_required` | Provider auth must complete before connected state |
| 502 | `provider_unavailable` | Provider/OAuth handoff failed |
| 500 | `internal_error` | Unexpected service failure |

## Storage And Migration Plan

Create schema/tables:

```sql
CREATE SCHEMA IF NOT EXISTS connector_marketplace;

CREATE TABLE connector_marketplace.catalog (
  id VARCHAR(100) PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  description TEXT NOT NULL,
  icon VARCHAR(255),
  category VARCHAR(50) NOT NULL,
  auth_type VARCHAR(30) NOT NULL,
  capabilities JSONB NOT NULL,
  availability VARCHAR(30) NOT NULL DEFAULT 'available',
  provider_metadata JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE connector_marketplace.installs (
  id VARCHAR(64) PRIMARY KEY,
  owner_user_id VARCHAR(128) NOT NULL,
  connector_id VARCHAR(100) NOT NULL,
  status VARCHAR(30) NOT NULL,
  auth_url TEXT,
  last_synced_at TIMESTAMPTZ,
  error_code VARCHAR(100),
  error_message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(owner_user_id, connector_id)
);

CREATE INDEX idx_connector_installs_owner_status
  ON connector_marketplace.installs(owner_user_id, status);
```

Migration sequence:

1. Add catalog and install-state tables.
2. Seed initial catalog rows for known first-party connectors.
3. Deploy read-only catalog list first.
4. Enable install/connect initiation per provider as OAuth credentials become
   available.
5. Migrate isA_ ConnectorMarketplace from local/static data to this API.

## OAuth And Provider Handoff

- OAuth connectors return `pending_auth` plus `auth_url` until the provider
  callback completes.
- The service must not return `connected` until provider tokens or credentials
  are persisted and validated.
- `return_url` must be validated against configured allowed origins.
- Provider callbacks should update `status`, `last_synced_at`, and
  provider-specific metadata through an internal route or provider integration
  worker. Callback route details are out of scope for the marketplace client
  contract.
- Provider credentials must be stored in the existing secrets/vault path, not in
  `connector_marketplace.installs`.

## Client Expectations

- Render catalog rows from `/catalog`; do not hard-code connected state.
- Merge `/installed` or item-level `install_state` into catalog UI state.
- Show `pending_auth` distinctly from `connected`.
- Surface `error_code` and `error_message` in the integrations UI.
- If the API is unavailable, show an error/empty state rather than marking
  connectors connected.

