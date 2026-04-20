# isA Admin Dashboard — Role Management UI — Product Requirements Document (PRD)

> **Role taxonomy**: see [`docs/guidance/role-taxonomy.md`](../guidance/role-taxonomy.md) for the canonical definition of platform-admin / org-admin / org-user / c-user archetypes. Tracked by epic [#270](https://github.com/xenoISA/isA_user/issues/270); this story is [#282](https://github.com/xenoISA/isA_user/issues/282).
>
> **Parent doc**: [`admin_dashboard.md`](./admin_dashboard.md) is the umbrella PRD for the `isA_Admin` console. This document specifies only the role-management surface and is referenced from Phase 1 (Foundation) and Phase 3 (User/Account Admin) of that plan.

## Product Overview

**Surface Name**: Admin Role Management
**Owner**: Platform Team
**Status**: Planning
**Last Updated**: 2026-04-18
**Host Project**: `isA_Admin` (separate from `isA_Console`)

### Purpose

Give platform operators a UI to manage `admin_roles[]` on user accounts — the JSONB column stamped into JWTs by `POST /api/v1/auth/admin/login` that turns a regular user into a platform admin. The surface covers listing users by admin role, assigning or revoking an admin role, viewing the audit trail of role changes, and starting a read-only "impersonate-as-support" session for customer assistance.

### How this differs from isA_Console member management

`isA_Console` (#436) lets an organization `owner` or `admin` manage **org-scoped** roles (`owner`, `admin`, `member`, `viewer`) for members of a single tenant. That surface never issues a token with `scope: admin` and never touches the `admin_roles[]` column.

`isA_Admin` role management operates one level up. It is platform-scoped: callers hold a JWT with `scope: admin` minted by admin login, and every mutation changes `account_service.accounts.admin_roles` — the canonical platform-admin grant. Only `super_admin` can grant or revoke admin roles; the two surfaces cannot cross-contaminate.

### Target Users

- **Super Admin** — the only role that can grant or revoke any `admin_role`. Sees every control on this surface.
- **Billing Admin**, **Product Admin**, **Support Admin**, **Compliance Admin** — can reach this surface through the admin console. They see a **read-only** view of role assignments and audit history. Grant/revoke controls are hidden (not just disabled).
- **Support Admin** — additionally gets the "Impersonate" action for read-only support sessions (see §Primary flows #4).

---

## Primary Flows

### 1. List users filtered by role

**Actor**: any `admin_role`.
**Goal**: "Show me every user who currently holds `billing_admin`."

Flow:

1. Admin opens `/admin/roles` in isA_Admin.
2. UI calls `GET /api/v1/account/admin/accounts?admin_role=billing_admin&page=1&page_size=50` (new query param; see §API contract).
3. Result table renders one row per matching user, with columns: email, name, `admin_roles[]` (comma-joined), status (active/suspended), last login, created-at.
4. Admin can add secondary filters (status, created range, search by email/name), sort, paginate, or export CSV.

ASCII wireframe:

```
┌───────────────────────────────────── isA_Admin › Role Management ──────────────────────────────────────┐
│  Filter by admin role: [ All ▾ ]  super_admin  billing_admin  product_admin  support_admin  compliance │
│  Status: [ Active ▾ ]    Search: [ __________________ 🔍 ]                              [ Export CSV ] │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ □ │ Email                    │ Name          │ Admin Roles               │ Status │ Last login   │ ⋯  │
├───┼──────────────────────────┼───────────────┼───────────────────────────┼────────┼──────────────┼────┤
│ □ │ alice@isa.ai             │ Alice Chen    │ super_admin               │ Active │ 2026-04-17   │ ⋮  │
│ □ │ bob@isa.ai               │ Bob Kim       │ billing_admin             │ Active │ 2026-04-15   │ ⋮  │
│ □ │ carol@isa.ai             │ Carol Reyes   │ billing_admin, support_…  │ Active │ 2026-04-18   │ ⋮  │
│ □ │ dan@isa.ai               │ Dan Park      │ compliance_admin          │ Susp.  │ 2026-03-02   │ ⋮  │
├───┴──────────────────────────┴───────────────┴───────────────────────────┴────────┴──────────────┴────┤
│  Showing 1–4 of 27                                                    « Prev   [1] 2 3 …   Next »     │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

Row overflow menu (`⋮`): **View detail** · **Manage roles** (super_admin only) · **View role history** · **Impersonate (read-only)** (support_admin + super_admin only).

### 2. Assign or revoke an admin_role

**Actor**: `super_admin` only.
**Goal**: Promote a user to `product_admin`, or revoke `billing_admin` from someone leaving the team.

Flow:

1. From the list table, super_admin picks a row and clicks **Manage roles**, or opens `/admin/accounts/{user_id}/roles` directly.
2. UI loads the current account via `GET /api/v1/account/admin/accounts/{user_id}`. The `admin_roles[]` field is presented as a set of five checkboxes (one per `PlatformAdminRole`).
3. Admin toggles checkboxes. A live preview shows the pending diff ("+ product_admin", "− billing_admin").
4. Admin clicks **Save**. A confirmation modal enumerates every delta and requires the admin to type the target user's email to confirm.
5. On confirm, UI calls `PUT /api/v1/account/admin/accounts/{user_id}/roles` with the full new `admin_roles` array.
6. On 200, the row refreshes and a toast reports success. On 403 (`only_super_admin_can_assign`) or 400 (`invalid_platform_role`), the UI surfaces the server's `rule`/`message` verbatim.
7. Every mutation emits a `role.assigned` or `role.revoked` audit event (see #280); the UI does not need to write audit data itself.

ASCII wireframe:

```
┌─── Manage admin roles for carol@isa.ai ───────────────────────────────────────────┐
│  User: Carol Reyes  ·  user_id: usr_01HX…            Current scope: Platform      │
│                                                                                   │
│  Platform admin roles                                                             │
│    [x] super_admin          Full platform authority, incl. granting admin roles   │
│    [x] billing_admin        Subscriptions, credits, refunds, invoices             │
│    [ ] product_admin        Products, pricing, cost definitions, AI models        │
│    [x] support_admin        Account lookup, status changes, impersonation         │
│    [ ] compliance_admin     Data requests, content moderation, audit logs         │
│                                                                                   │
│  Pending changes                                                                  │
│    − billing_admin                                                                │
│    + compliance_admin                                                             │
│                                                                                   │
│  [ Cancel ]                                                     [ Save changes ]  │
└───────────────────────────────────────────────────────────────────────────────────┘

                        ┌─── Confirm role change ────────────────┐
                        │  You will apply these deltas to        │
                        │    carol@isa.ai                        │
                        │      − billing_admin                   │
                        │      + compliance_admin                │
                        │                                        │
                        │  Type the user's email to confirm:     │
                        │  [ _______________________________ ]   │
                        │                                        │
                        │  [ Cancel ]          [ Apply changes ] │
                        └────────────────────────────────────────┘
```

**Authorization short-circuits**. If the current admin is not `super_admin`, the **Manage roles** action is not rendered in the overflow menu, the route `/admin/accounts/{user_id}/roles` returns a 403-style empty state, and direct `PUT` attempts fail at the backend with `only_super_admin_can_assign`.

### 3. View audit history of role changes

**Actor**: any `admin_role`. Presented read-only.
**Goal**: "Who granted Carol `compliance_admin`, when, and from where?"

Audit data comes from the `role.assigned` / `role.revoked` events emitted by `account_service`, `authorization_service`, and `organization_service` per #280 and persisted by `audit_service`.

Flow:

1. From a user detail page, admin clicks **Role history**, or opens `/admin/roles/history?user_id=…`.
2. UI calls `GET /api/v1/audit/events?event_type=role.assigned,role.revoked&target_user_id={user_id}&page=1` against `audit_service`.
3. Timeline renders newest-first. Each entry shows: timestamp, event type, actor (email), scope (platform / org / app), old → new role set, IP, admin session id.
4. Global view at `/admin/roles/history` (no user filter) is filterable by actor, event type, scope, and time range. Exportable as JSON or CSV for compliance review.

ASCII wireframe:

```
┌─── Role change history: carol@isa.ai ─────────────────────────────────────────────┐
│  Filter: [ All events ▾ ]  Actor: [ _____ ]  Range: [ Last 90 days ▾ ]  [ Export ]│
├───────────────────────────────────────────────────────────────────────────────────┤
│ 2026-04-18 14:02:11 UTC   role.assigned    scope=platform                         │
│   actor: alice@isa.ai (super_admin)                                               │
│   target: carol@isa.ai                                                            │
│   diff:  + compliance_admin                                                       │
│   audit_id: aud_01HXABC…   session: adm_sess_9f2…   ip: 203.0.113.17              │
├───────────────────────────────────────────────────────────────────────────────────┤
│ 2026-04-18 14:02:11 UTC   role.revoked     scope=platform                         │
│   actor: alice@isa.ai (super_admin)                                               │
│   target: carol@isa.ai                                                            │
│   diff:  − billing_admin                                                          │
│   audit_id: aud_01HXABD…   session: adm_sess_9f2…   ip: 203.0.113.17              │
├───────────────────────────────────────────────────────────────────────────────────┤
│ 2026-02-11 09:41:03 UTC   role.assigned    scope=platform                         │
│   actor: alice@isa.ai (super_admin)                                               │
│   target: carol@isa.ai                                                            │
│   diff:  + billing_admin, + support_admin, + super_admin                          │
│   audit_id: aud_01HXA99…   session: adm_sess_6b1…   ip: 198.51.100.4              │
└───────────────────────────────────────────────────────────────────────────────────┘
```

### 4. Impersonate-as-support (read-only)

**Actor**: `super_admin` or `support_admin`.
**Goal**: Reproduce a customer-reported bug by viewing the platform as the target user, without mutating any of their data.

Constraints:

- The impersonation token is **read-only**: every write-verb request made with it is rejected at the service boundary and logged with an `impersonation_write_denied` audit event.
- Impersonation tokens carry `scope: admin_impersonation` (distinct from `admin` and from the target user's regular scope) plus `impersonated_user_id` and `actor_user_id` claims so downstream services can distinguish.
- Sessions are capped at 30 minutes and require a typed reason + a linked support ticket id.
- A banner pinned to the top of every impersonated page names the actor, the target, the session expiry, and an **End session** button.
- Starting and ending a session each emit an audit event (`impersonation.started`, `impersonation.ended`).

Flow:

1. From a user detail page, admin clicks **Impersonate (read-only)**.
2. Modal captures: `reason` (free text, required), `support_ticket_id` (required), and shows the 30-minute expiry.
3. UI calls `POST /api/v1/auth/admin/impersonate` with `{ target_user_id, reason, support_ticket_id }`. Response returns an impersonation access token.
4. UI opens isA_Console in a new tab with the impersonation token injected. The Console's middleware (#436) recognizes `scope: admin_impersonation` and renders the banner + enforces read-only UI.
5. Admin inspects the target's session. Any mutation attempt is blocked.
6. Admin clicks **End session**, or the token expires. `POST /api/v1/auth/admin/impersonate/{session_id}/end` is called. Audit trail records both start and end.

ASCII wireframe:

```
┌─── Start read-only support session ─────────────────────────────────────┐
│  Target user: carol@isa.ai                                              │
│                                                                         │
│  Reason (required):                                                     │
│  [ Customer reports missing projects after org transfer — checking    ] │
│  [ project list visibility for this user only.                        ] │
│                                                                         │
│  Support ticket id (required):                                          │
│  [ SUP-1042 ]                                                           │
│                                                                         │
│  Session will:                                                          │
│    • Issue a read-only admin_impersonation token (scope limited).       │
│    • Expire automatically in 30:00.                                     │
│    • Emit impersonation.started + impersonation.ended audit events.     │
│    • Never permit writes — any write attempt is logged and blocked.     │
│                                                                         │
│  [ Cancel ]                                          [ Start session ]  │
└─────────────────────────────────────────────────────────────────────────┘

Once running, every page in the impersonated Console tab shows:
┌───────────────────────────────────────────────────────────────────────────────────────┐
│ ⚠  SUPPORT SESSION · Acting as carol@isa.ai (read-only) · Ends in 27:41 · [End now]   │
└───────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Authorization Rules

All rules below derive from `docs/guidance/role-taxonomy.md` and the existing `role_validator` in `account_service`, `authorization_service`, and `organization_service`. The UI layer enforces them for presentation; the backend enforces them again for correctness. The backend is the source of truth — the UI only hides controls that would be rejected.

| Capability | super_admin | billing_admin | product_admin | support_admin | compliance_admin |
|---|:-:|:-:|:-:|:-:|:-:|
| List users filtered by admin_role | ✓ | R | R | R | R |
| View a user's current admin_roles | ✓ | R | R | R | R |
| Grant an admin_role | ✓ | — | — | — | — |
| Revoke an admin_role | ✓ | — | — | — | — |
| View role-change audit history | ✓ | ✓ | R | R | ✓ |
| Start read-only impersonation | ✓ | — | — | ✓ | — |
| End an impersonation session | ✓ | — | — | ✓ (own sessions only) | — |

Legend: **✓** = full access  ·  **R** = read-only  ·  **—** = control hidden.

Invariants:

1. **Only super_admin can grant or revoke admin_roles.** The `Manage roles` control is hidden for every other role. A direct backend call fails with HTTP 403 and `rule: only_super_admin_can_assign` (see `account_service.main.admin_update_roles`).
2. **billing_admin has view-only access** to role assignments and to audit history — surfaced in the UI but every mutation control is suppressed.
3. **Every admin_role mutation emits an audit event** consumed by #280 (`role.assigned` / `role.revoked`, with `actor_user_id`, `target_user_id`, `scope`, `org_id` (nullable), `old_role`, `new_role`, `timestamp`). The UI never bypasses this path; it depends entirely on the services emitting events on mutation.
4. **Impersonation sessions are read-only and time-bounded** — 30 min cap, write verbs rejected, start/end events emitted, actor + target + reason + ticket recorded.
5. **Cannot promote beyond your own scope.** Although super_admin is the only role that can grant admin_roles today, the UI trusts `RoleValidator.canAssignRole` for all scope transitions; any future scoped admin is blocked if it tries to mint a role higher than its own scope.
6. **Admin JWTs expire fast.** Per `auth_service.admin_login`, admin JWTs expire in 4 hours. The UI shows a countdown and forces re-auth for any role mutation within the last 5 minutes of the token's life.

---

## API Contract

All endpoints are called through the APISIX gateway; the UI uses the unified `@isa/core` SDK and the `AdminAccountService` / `AdminAuthService` / `AdminAuditService` classes sketched in [`admin_dashboard.md`](./admin_dashboard.md). Role payload shapes reference `CanonicalRole` and `PlatformAdminRole` from `@isa/core/roles` (per #272).

### From `@isa/core/roles` (reference)

```ts
export type PlatformAdminRole =
  | 'super_admin'
  | 'billing_admin'
  | 'product_admin'
  | 'support_admin'
  | 'compliance_admin';

export type CanonicalRole = PlatformAdminRole | 'owner' | 'admin' | 'member' | 'viewer' | 'consumer';
```

### auth_service — session + impersonation

| Method | Path | Purpose | Caller | Notes |
|---|---|---|---|---|
| `POST` | `/api/v1/auth/admin/login` | Exchange email + password for an admin JWT (`scope: admin`, `admin_roles[]`). | unauthenticated | Existing. |
| `GET` | `/api/v1/auth/admin/verify` | Verify the current admin JWT and return `admin_roles`, `scope`, `expires_at`. | any admin_role | Existing. Used to drive the UI's own gating. |
| `POST` | `/api/v1/auth/admin/impersonate` | **New**. Mint a read-only `admin_impersonation` token for a target user. | super_admin · support_admin | Request: `{ target_user_id, reason, support_ticket_id }`. Response: `{ session_id, access_token, expires_in, target_user_id, actor_user_id }`. Emits `impersonation.started`. |
| `POST` | `/api/v1/auth/admin/impersonate/{session_id}/end` | **New**. End an impersonation session early. | same actor + super_admin | Emits `impersonation.ended`. Idempotent. |

### account_service — admin_role CRUD

| Method | Path | Purpose | Caller | Notes |
|---|---|---|---|---|
| `GET` | `/api/v1/account/admin/accounts` | Paginated list of accounts. **Extended** with `admin_role` query param (value ∈ `PlatformAdminRole`) to filter by role and an `has_any_admin_role=true` flag to list every platform admin. | any admin_role | Existing endpoint; query params are the delta this surface needs. |
| `GET` | `/api/v1/account/admin/accounts/{user_id}` | Account detail — includes `admin_roles: PlatformAdminRole[]`, `is_active`, `created_at`, `updated_at`. | any admin_role | Existing. |
| `PUT` | `/api/v1/account/admin/accounts/{user_id}/roles` | Replace `admin_roles[]` on a user. Body: `{ admin_roles: PlatformAdminRole[] }`. | super_admin only | Existing. Backend enforces `only_super_admin_can_assign` (403) and `invalid_platform_role` (400). Emits `role.assigned` / `role.revoked` per delta. |
| `PUT` | `/api/v1/accounts/status/{user_id}` | Suspend / activate / delete. | super_admin · support_admin | Used from the "Manage roles" page for account-level actions adjacent to role changes. |

Example `PUT /api/v1/account/admin/accounts/{user_id}/roles`:

```http
PUT /api/v1/account/admin/accounts/usr_01HX.../roles
Authorization: Bearer <admin JWT, scope=admin, admin_roles=[super_admin]>
Content-Type: application/json

{
  "admin_roles": ["super_admin", "support_admin", "compliance_admin"]
}
```

Response (200):

```json
{
  "user_id": "usr_01HX...",
  "email": "carol@isa.ai",
  "name": "Carol Reyes",
  "is_active": true,
  "admin_roles": ["super_admin", "support_admin", "compliance_admin"],
  "created_at": "2026-01-04T11:02:00Z",
  "updated_at": "2026-04-18T14:02:11Z"
}
```

Response (403) when caller is not `super_admin`:

```json
{
  "detail": {
    "rule": "only_super_admin_can_assign",
    "message": "only super_admin can assign platform admin roles"
  }
}
```

### authorization_service — scope-aware role assignment (shared with org-scope)

The admin surface reuses the canonical assign-role endpoint only when the target assignment is **not** a `PlatformAdminRole` (that path belongs to `account_service`). It is listed here so the isA_Admin SDK can dispatch to the correct service from a unified UI.

| Method | Path | Purpose | Caller | Notes |
|---|---|---|---|---|
| `POST` | `/api/v1/authorization/assign-role` | Canonical role assignment across scopes. Body: `{ assigner_user_id, assignee_user_id, assignee_role: CanonicalRole, scope: 'platform'\|'organization'\|'app', org_id? }`. | super_admin (for platform scope); scope-appropriate callers for other scopes | Existing. Returns `rule` + `message` on failure; emits `role.assigned` / `role.revoked` on success. |

### audit_service — role-change history + impersonation history

| Method | Path | Purpose | Caller | Notes |
|---|---|---|---|---|
| `GET` | `/api/v1/audit/events?event_type=role.assigned,role.revoked&target_user_id=…` | Query role-change events for a single user or across the platform. | any admin_role (view scope governed by matrix above) | Existing. Supports `actor_user_id`, `scope`, `from_ts`, `to_ts`, `page`, `page_size`. |
| `GET` | `/api/v1/audit/events?event_type=impersonation.started,impersonation.ended` | Query impersonation sessions. | super_admin · compliance_admin | Existing. |
| `GET` | `/api/v1/audit/admin/actions` | Cross-service admin-action feed. | super_admin · compliance_admin | Existing; used on the global history page when no user filter is set. |

Event payload shape (from #280):

```json
{
  "event_id": "aud_01HXABC...",
  "event_type": "role.assigned",
  "timestamp": "2026-04-18T14:02:11Z",
  "actor_user_id": "usr_01HX_alice",
  "target_user_id": "usr_01HX_carol",
  "scope": "platform",
  "org_id": null,
  "old_role": null,
  "new_role": "compliance_admin",
  "metadata": {
    "actor_admin_roles": ["super_admin"],
    "source_ip": "203.0.113.17",
    "admin_session_id": "adm_sess_9f2..."
  }
}
```

### SDK mapping

| SDK method (`@isa/core`) | HTTP |
|---|---|
| `AdminAccountService.listAccounts({ admin_role })` | `GET /api/v1/account/admin/accounts` |
| `AdminAccountService.getAccount(user_id)` | `GET /api/v1/account/admin/accounts/{user_id}` |
| `AdminAccountService.assignRoles(user_id, roles: PlatformAdminRole[])` | `PUT /api/v1/account/admin/accounts/{user_id}/roles` |
| `AdminAuthService.startImpersonation({ target_user_id, reason, support_ticket_id })` | `POST /api/v1/auth/admin/impersonate` |
| `AdminAuthService.endImpersonation(session_id)` | `POST /api/v1/auth/admin/impersonate/{session_id}/end` |
| `AdminAuditService.listRoleChanges({ target_user_id? })` | `GET /api/v1/audit/events?event_type=role.assigned,role.revoked` |
| `AdminAuditService.listImpersonations({ actor_user_id? })` | `GET /api/v1/audit/events?event_type=impersonation.started,impersonation.ended` |

---

## Out of Scope

1. **Org-level member management.** `isA_Console` #436 owns org `owner`/`admin`/`member`/`viewer` management — not this surface.
2. **App-level c-user management.** Consuming apps own their c-user lifecycle via the isA_App_SDK. `admin_role` grants do not apply.
3. **Custom admin role creation.** The five predefined `PlatformAdminRole` values are the universe; adding a new one requires extending `@isa/core/roles` and the backend enum (see the taxonomy doc's "When to extend the tree" section).
4. **Bulk role grants.** No bulk assign/revoke in v0.1 — every change is per-user with a confirmation step.
5. **Writeable impersonation.** Impersonation is read-only by contract; a "support-with-write" mode is explicitly out of scope and would require a separate security review.
6. **Self-service role request / approval workflow.** A future enhancement (e.g. "request billing_admin, super_admin approves") is not covered here.

---

**Document Version**: 0.1
**Last Updated**: 2026-04-18
**Maintained By**: Platform Team
