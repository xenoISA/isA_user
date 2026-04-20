# Role Taxonomy

Canonical definition of user archetypes across the isA platform. Every service that authorizes a request — and every consumer (isA_Console, isA_Admin, isA_App_SDK, consuming apps) — should reason in terms of the four archetypes below.

**Status**: Spec. Backed by epic [#270](https://github.com/xenoISA/isA_user/issues/270).

Until the unified `@isa/core` types (#272) land, existing role strings remain valid and are mapped below.

## The four archetypes

| Archetype | One-line | Where they authenticate | Scope of authority |
|---|---|---|---|
| **Platform admin** | Operator of isA itself | `/api/v1/auth/admin/login` | Platform-wide (cross-org). JWT: `scope: admin` + `admin_roles[]`. |
| **Org admin** | Owner or admin inside a tenant | Regular login + org context | One organization. JWT: regular + `org_id` + `role ∈ {owner, admin}`. |
| **Org user** | Member or viewer inside a tenant | Regular login + org context | One organization, non-administrative. JWT: regular + `org_id` + `role ∈ {member, viewer}`. |
| **c-user** | Consumer end-user of an app built on isA | App-side SDK auth | The consuming app's data only. JWT: `scope: app` + `app_id` + `user_id`. Not expected in isA_Console. |

### Platform admin

The people running isA. Five named roles today (`ADMIN_ROLES` in `auth_service/models.py` and `account_service/models.py`):

- `super_admin` — full platform authority, including granting other admin roles.
- `billing_admin` — customer billing, invoices, refunds.
- `product_admin` — platform configuration, feature flags, product data.
- `support_admin` — read everywhere, limited write for customer assistance, impersonation.
- `compliance_admin` — audit-log access, compliance reports, PII handling.

Identity: regular user account with a non-empty `admin_roles` JSONB column. Admin login mints a JWT with `scope: admin` plus the `admin_roles` claim. **Only `super_admin` can grant admin roles.**

Natural home: **isA_Admin console** (separate from the tenant-facing isA_Console).

### Org admin

`owner` or `admin` inside an organization. Manages members, billing, settings, rate limits, audit log, and compliance reports for that tenant. `owner` is distinguished from `admin` only by (a) transferring ownership and (b) deleting the organization.

Every organization has exactly one `owner`. Multiple `admin`s are allowed.

### Org user

Regular member of a tenant — uses the platform but has no administrative authority. Two levels:

- `member` — normal read/write within the org's resources.
- `viewer` — read-only.

### c-user (consumer end-user)

The person using an app **built on** isA. They do not log into isA_Console; they authenticate via the consuming app's SDK. They are bound to the org that owns the consuming app for billing, rate limits, and data scoping, but they have zero administrative capability anywhere. A single human can simultaneously be an org member of org B and a c-user of app A owned by org C — the JWT scope disambiguates.

Detailed semantics are expanded in #281.

## Permission matrix

Rows = archetype. Columns = capability buckets derived from the console's `RoleEditor` permission groups plus admin-only surfaces.

Legend: **✓** = full access  ·  **R** = read-only  ·  **—** = hidden  ·  **scoped** = depends on the named admin role.

| Capability | super_admin | billing_admin | product_admin | support_admin | compliance_admin | Org owner | Org admin | Org member | Org viewer | c-user |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| Dashboard / Overview | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | R | — |
| Models (deploy, train, eval) | ✓ | R | ✓ | R | — | ✓ | ✓ | ✓ | R | — |
| Agents (create, edit, delete) | ✓ | — | ✓ | R | — | ✓ | ✓ | ✓ | R | — |
| MCP (manage servers, tools) | ✓ | — | ✓ | R | — | ✓ | ✓ | ✓ | R | — |
| Playground | ✓ | — | ✓ | ✓ | — | ✓ | ✓ | ✓ | — | — |
| Traces | ✓ | — | ✓ | R | R | ✓ | ✓ | ✓ | R | — |
| Logs | ✓ | — | ✓ | R | R | ✓ | ✓ | ✓ | R | — |
| Vector Stores / Datasets | ✓ | — | ✓ | R | — | ✓ | ✓ | ✓ | R | — |
| Marketplace (browse + install) | ✓ | — | ✓ | R | — | ✓ | ✓ | ✓ | R | — |
| Monitoring / Health | ✓ | R | ✓ | ✓ | R | ✓ | ✓ | R | R | — |
| API Keys | ✓ | — | — | R | — | ✓ | ✓ | R | R | — |
| Projects | ✓ | — | ✓ | R | — | ✓ | ✓ | ✓ | R | — |
| Members (invite, remove, assign role) | ✓ | — | — | R | R | ✓ | ✓ | R | R | — |
| Custom Roles (manage) | ✓ | — | — | R | — | ✓ | ✓ | — | — | — |
| Billing / Subscription | ✓ | ✓ | — | R | — | ✓ | R | R | R | — |
| Usage / Analytics | ✓ | ✓ | ✓ | R | R | ✓ | ✓ | R | R | — |
| Audit Log | ✓ | R | — | R | ✓ | ✓ | ✓ | — | — | — |
| Compliance Reports | ✓ | — | — | — | ✓ | ✓ | ✓ | — | — | — |
| Rate Limits (configure) | ✓ | — | ✓ | — | — | ✓ | ✓ | — | — | — |
| Settings (org-level) | ✓ | — | — | R | — | ✓ | ✓ | R | R | — |
| App Integrations (consume agent) | ✓ | — | ✓ | R | — | ✓ | ✓ | ✓ | R | ✓ |

Notes:

- The matrix expresses a default. Custom roles (defined via the isA_Console `RoleEditor`) can relax *but never expand* an org user's base permissions — an org admin cannot hand a `member` capabilities beyond `member`'s ceiling.
- `c-user` has a single column because every c-user's envelope is identical: they can only operate inside the consuming app's feature set.
- "R" for org admins on `Billing` reflects that only `owner` can change billing by default; admins can view. Teams running a flat org should set `allow_admin_billing: true` in org settings to promote admins to full billing access.

## Mapping from existing role strings

Until #272 lands the canonical types in `@isa/core`, the strings below are the source of truth. Read every row as: "when the service returns this string, the downstream consumer should treat the user as the archetype on the right."

| Service / enum | Role string | Archetype | Notes |
|---|---|---|---|
| `auth_service.ADMIN_ROLES` | `super_admin` | Platform admin | Full platform authority. |
| `auth_service.ADMIN_ROLES` | `billing_admin` | Platform admin (scoped) | Billing column only + read elsewhere. |
| `auth_service.ADMIN_ROLES` | `product_admin` | Platform admin (scoped) | Product / config. |
| `auth_service.ADMIN_ROLES` | `support_admin` | Platform admin (scoped) | Read-everywhere + impersonation. |
| `auth_service.ADMIN_ROLES` | `compliance_admin` | Platform admin (scoped) | Audit + compliance. |
| `organization_service.OrgRoleEnum` | `owner` | Org admin | Exactly one per org. |
| `organization_service.OrgRoleEnum` | `admin` | Org admin | Multiple allowed. |
| `organization_service.OrgRoleEnum` | `member` | Org user | Read/write within org scope. |
| `organization_service.OrgRoleEnum` | `viewer` | Org user (read-only) | Read within org scope. |
| `organization_service.OrgRoleEnum` | `guest` | Org user (read-only) | Legacy; treated as `viewer` for new code. |
| `authorization_service.RoleEnum` | `owner` | Org admin | Same mapping as org_service. |
| `authorization_service.RoleEnum` | `admin` | Org admin | — |
| `authorization_service.RoleEnum` | `editor` | Org user | Approx. `member`; align in #273. |
| `authorization_service.RoleEnum` | `viewer` | Org user (read-only) | — |
| `authorization_service.RoleEnum` | `service` | **Service account** | Not a human archetype. Machine-to-machine principal. Out of scope for this taxonomy. |
| `project_service.ProjectRole` | `owner` | Org user (resource-scoped) | Scope is a project, not an org. |
| `project_service.ProjectRole` | `editor` | Org user (resource-scoped) | — |
| `project_service.ProjectRole` | `viewer` | Org user (resource-scoped) | — |
| *(new)* | `consumer` | c-user | Introduced by #272 + #281. |

Principles:

1. **An archetype is a bundle of capabilities, not a single role string.** Mapping is many-to-one.
2. **Scope matters.** `owner` at org scope and `owner` at project scope produce different permission sets; the scope comes from the resource the permission is being checked against, not from the string.
3. **Service role is not a human archetype.** Treat `authorization_service.RoleEnum.service` as a separate principal class. Human-role gating should never hand out `service`.

## Decision tree

Follow top to bottom, stop at the first match.

1. JWT has `scope: admin` and non-empty `admin_roles[]`? → **Platform admin** (use the first element for scoped admin variants).
2. JWT has `scope: app` and `app_id`? → **c-user**.
3. JWT has `org_id` and org role ∈ `{owner, admin}`? → **Org admin**.
4. JWT has `org_id` and org role ∈ `{member, viewer, guest}`? → **Org user** (read-only if `viewer` or `guest`).
5. None of the above? → Unauthenticated, or user without an org context. Default: **Org user** with no `org_id` (personal account).

A visual Mermaid flowchart is added by #279.

## Edge cases

- **Platform admin inside a tenant**. A user with both `admin_roles[]` and org membership gets the **union** of permissions, not the intersection. The admin column wins when columns disagree.
- **Cross-org user**. A user can belong to N orgs with different roles. The active archetype is determined per-request by `org_id` in the token/session; switching org context switches archetype.
- **Simultaneous archetypes**. Bob can be an org member of Acme (using isA_Console) and a c-user of an app owned by a different org. Two distinct JWTs; the scope disambiguates.
- **Org admin attempts to grant platform admin**. Blocked at `RoleValidator.canAssignRole` (#272): assigners cannot promote beyond their own scope.
- **c-user attempts to hit isA_Console**. Console middleware rejects `scope: app` tokens at the route layer — c-users never see Console UI.
- **Organization suspended**. All member roles degrade to read-only; platform admin retains full visibility for remediation.
- **User removed from org**. Org-scoped permissions revoke immediately; the user's platform and c-user archetypes are unaffected.
- **Permission expiry mid-request**. In-flight requests complete against the permission set at request start; subsequent requests re-evaluate.
- **Custom org role**. An org admin may create a custom role (see isA_Console `RoleEditor`). The role's permission set must be a **subset** of the caller's own permissions — you cannot mint a role stronger than yourself.

## Which doc goes where

| Topic | Source of truth |
|---|---|
| Archetype definitions, permission matrix, mapping | This doc |
| Service-level role validation behavior | `docs/prd/authorization_service.md`, `docs/prd/organization_service.md`, `docs/prd/account_service.md` |
| JWT claim shapes per archetype | `docs/guidance/authentication.md` |
| isA_Console UI gating implementation | isA_Console #436 |
| c-user consumer-end-user deep dive | #281 |
| Decision-tree flowchart | #279 |
| Admin-dashboard role management UI | #282 |

## Changes required in downstream docs

When this spec lands:

1. Add a "Roles" section to `docs/prd/authorization_service.md` linking here.
2. Add a "Roles" section to `docs/prd/organization_service.md` linking here.
3. Add a "Roles" section to `docs/prd/account_service.md` linking here.
4. Link this doc from the top of `docs/guidance/authentication.md` under "Overview".

Those linkings are bundled with the corresponding service stories (#273, #274, #275) rather than this story.
