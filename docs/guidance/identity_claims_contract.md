# Identity Claims Contract

Canonical identity claims emitted by `auth_service` and consumed by JupyterHub,
MLflow, APISIX, and isA_Model APIs.

## Scope

This contract covers the two auth endpoints model-side consumers should call:

| Endpoint | Purpose |
| --- | --- |
| `POST /api/v1/auth/verify-token` | Fast token validity check for gateways and request filters. |
| `POST /api/v1/auth/user-info` | Rich user, tenant, account, role, and permission context. |

Consumers should treat `user-info` as the richer authorization context. `verify-token`
is intentionally smaller and stable for APISIX/JupyterHub request admission.

## Source of Truth

| Claim | Endpoint | Required | Source of truth | Notes |
| --- | --- | --- | --- | --- |
| `valid` | `verify-token` | Required | `auth_service.verify_token` | Boolean token validity. `false` responses include `error`. |
| `provider` | both | Optional | Token issuer/provider detection | Usually `isa_user`; `local` is a development alias. |
| `user_id` | both | Required for user tokens | JWT `sub` / auth repository | Canonical platform user id. |
| `sub` | `user-info` | Required for user tokens | `user_id` | OIDC-compatible subject alias for model consumers. |
| `email` | both | Required for user tokens | JWT/auth repository | Normalized user email. |
| `preferred_username` | `user-info` | Optional | Token metadata, email local part, or `user_id` | Display/login hint; not an authorization key. |
| `name` | `user-info` | Optional | `account_service` claims endpoint, then token metadata | Account profile name wins over token metadata. |
| `account_active` | `user-info` | Optional | `account_service` claims endpoint | `true`/`false` when account exists; `null` when account service is unavailable or not wired. |
| `account_missing` | `user-info` | Required | `account_service` claims endpoint | `true` only when account lookup returns missing. Service failures degrade to `false` with unknown active state. |
| `organization_id` | both | Optional | `organization_service` user context, then token metadata | Tenant organization when the user has active org context. |
| `tenant_id` | `user-info` | Optional | `organization_service` user context, then metadata/org fallback | Equal to `organization_id` for organization context. |
| `org_role` | `user-info` | Optional | `organization_service` user role | Normalized role value from organization membership. |
| `organization_permissions` | `user-info` | Required | `organization_service` permissions | Empty list for individual/no-org or degraded org service. |
| `permissions` | both | Required | JWT permissions plus org permissions; dev admin may add `auth.admin` | Deduplicated in `user-info`. |
| `role` | `verify-token` | Optional | JWT scope plus dev-bypass admin policy | `admin` when admin scope or dev-bypass admin applies. |
| `roles` | `user-info` | Required | Token metadata, org role, admin inference | Includes `admin` when admin permission/admin roles/admin scope applies. |
| `admin_roles` | `user-info` | Required | Token metadata plus `account_service` admin roles | Platform admin roles such as `super_admin`, `billing_admin`, or `support_admin`. |
| `scopes` | `verify-token` | Optional | JWT scopes plus dev-bypass admin policy | Dev-bypass admin returns `read`, `write`, `admin`. |
| `subscription_level` | `verify-token` | Optional | JWT metadata | Present only when token metadata includes it. |
| `expires_at` | both | Optional | JWT expiration | ISO datetime when available. |
| `error` | `verify-token` | Optional | Verification failure | Only populated for invalid verification. |

## Dev-Bypass Admin Behavior

`/api/v1/auth/dev-bypass` is a local-development shortcut only. It is available
only when:

| Environment variable | Required value |
| --- | --- |
| `AUTH_DEV_BYPASS_ENABLED` | `true` |
| `AUTH_DEV_BYPASS_USERS` | Comma-separated allowlist containing the requested email. |
| `AUTH_DEV_BYPASS_ADMINS` | Comma-separated admin allowlist for emails that should receive admin claims. |

When a requested email is in both `AUTH_DEV_BYPASS_USERS` and
`AUTH_DEV_BYPASS_ADMINS`, `verify-token` and `user-info` expose admin context:

| Endpoint | Expected admin claims |
| --- | --- |
| `verify-token` | `role: "admin"`, `permissions` includes `auth.admin`, `scopes` includes `admin`. |
| `user-info` | `roles` includes `admin`, `permissions` includes `auth.admin`. |

When `AUTH_DEV_BYPASS_ENABLED` is not `true`, dev-bypass admin promotion must not
apply even if the email appears in `AUTH_DEV_BYPASS_ADMINS`. Do not enable
dev-bypass in staging or production validation unless the environment is
explicitly dedicated to development testing.

## Validation Commands

Set these values for local validation:

```bash
export AUTH_BASE_URL=http://localhost:8201
export AUTH_DEV_BYPASS_ENABLED=true
export AUTH_DEV_BYPASS_USERS=admin@example.com,user@example.com
export AUTH_DEV_BYPASS_ADMINS=admin@example.com
```

Issue an admin dev-bypass token:

```bash
ADMIN_TOKEN=$(
  curl -sS -X POST "$AUTH_BASE_URL/api/v1/auth/dev-bypass" \
    -H "Content-Type: application/json" \
    -d '{"email":"admin@example.com","expires_in":900}' \
  | jq -r '.token'
)
```

Validate gateway-oriented claims:

```bash
curl -sS -X POST "$AUTH_BASE_URL/api/v1/auth/verify-token" \
  -H "Content-Type: application/json" \
  -d "{\"token\":\"$ADMIN_TOKEN\"}" \
  | jq '{valid,email,user_id,organization_id,role,permissions,scopes,expires_at}'
```

Validate model-consumer user context:

```bash
curl -sS -X POST "$AUTH_BASE_URL/api/v1/auth/user-info" \
  -H "Content-Type: application/json" \
  -d "{\"token\":\"$ADMIN_TOKEN\"}" \
  | jq '{sub,user_id,email,preferred_username,name,account_active,account_missing,organization_id,tenant_id,org_role,roles,admin_roles,organization_permissions,permissions,provider,expires_at}'
```

Expected admin assertions:

```bash
curl -sS -X POST "$AUTH_BASE_URL/api/v1/auth/verify-token" \
  -H "Content-Type: application/json" \
  -d "{\"token\":\"$ADMIN_TOKEN\"}" \
  | jq -e '.valid == true and .role == "admin" and (.permissions | index("auth.admin")) and (.scopes | index("admin"))'

curl -sS -X POST "$AUTH_BASE_URL/api/v1/auth/user-info" \
  -H "Content-Type: application/json" \
  -d "{\"token\":\"$ADMIN_TOKEN\"}" \
  | jq -e '(.roles | index("admin")) and (.permissions | index("auth.admin"))'
```

## Consumer Guidance

JupyterHub and MLflow should use `verify-token` for request admission and
`user-info` when they need a stable display name, tenant id, or admin role list.
APISIX should avoid depending on account profile fields and should use
`verify-token.valid`, `user_id`, `email`, `organization_id`, `role`, and
`permissions`.

isA_Model APIs should prefer:

| Need | Claim |
| --- | --- |
| Principal id | `user_id` or `sub` |
| Display identity | `name`, then `preferred_username`, then `email` |
| Tenant routing | `tenant_id`, then `organization_id` |
| Organization authorization | `org_role`, `organization_permissions` |
| Platform admin authorization | `admin_roles`, `roles`, `permissions` |

## Related Evidence Stories

- `xenoISA/isA_Model#837` - JupyterHub auth claims evidence.
- `xenoISA/isA_Model#841` - MLflow auth claims evidence.
- `xenoISA/isA_Model#844` - model consumer identity claims validation follow-up.
