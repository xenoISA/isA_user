# isA Super Admin Dashboard — Product Requirements Document (PRD)

## Product Overview

**Product Name**: isA Admin Dashboard
**Version**: 0.1.0
**Status**: Planning
**Owner**: Platform Team
**Last Updated**: 2026-03-29
**Project**: `isA_Admin` (new project, `~/Documents/Fun/isA/isA_Admin`)

### Vision
A dedicated super admin portal for platform-wide management — users, billing, products, AI models, infrastructure, and compliance. Deployed independently from the consumer console, sharing the `@isa/core` SDK and `@isa/ui-web` component library.

### Mission
Give platform operators a single pane of glass to manage all 37 microservices, respond to support requests, adjust billing, update AI model pricing, and maintain compliance — without touching SQL, APIs, or CLI tools.

### Target Users
- **Super Admin**: Full platform access (everything)
- **Billing Admin**: Subscriptions, credits, refunds, invoices, pricing
- **Product Admin**: Products, pricing, cost definitions, AI models
- **Support Admin**: Account lookup, status changes, subscription info
- **Compliance Admin**: Data requests, content moderation, audit logs

---

## Architecture

```
isA_Admin (Next.js 16) → @isa/core SDK → 37 microservices (isA_user)
```

- **Framework**: Next.js 16 + React 19 + Tailwind v4 (same as isA_Console)
- **SDK**: `@isa/core`, `@isa/hooks`, `@isa/ui-web`, `@isa/theme` from isA_App_SDK
- **Port**: 4300 (dev)
- **Domain**: `admin.isa.ai` (production)
- **Auth**: Admin-scoped JWT tokens via auth_service

---

## Phases

### Phase 1: Foundation (P0)
- Scaffold isA_Admin project
- Unified admin authentication (admin JWT scope)
- Admin action audit trail
- Admin role hierarchy (super_admin, billing_admin, product_admin, support_admin, compliance_admin) — role-management UI spec: [`admin_dashboard_role_management.md`](./admin_dashboard_role_management.md)

### Phase 2: Product Admin UI (P1)
- Product catalog management (wires to existing Epic #174 endpoints)
- AI model catalog dashboard
- Cost rotation wizard

### Phase 3: User/Account Admin (P1)
- User management (search, view, suspend, ban, impersonate)
- Organization management (members, roles, plans)
- Account admin API endpoints

### Phase 4: Billing Admin (P1)
- Subscription management (tier changes, credit adjustments)
- Billing records and refunds
- Wallet balance adjustments
- Revenue and usage analytics dashboards

### Phase 5: Platform Operations (P1)
- Service health dashboard (37 services, live status)
- Infrastructure monitoring (PostgreSQL, Redis, NATS, etc.)
- Database schema and migration status

### Phase 6: Compliance & Moderation (P2)
- Audit log viewer with advanced filtering
- GDPR data export/deletion request management
- Content moderation queue

---

## SDK Additions (isA_App_SDK)

| Service Class | Backend | Key Methods |
|--------------|---------|-------------|
| AdminAuthService | auth_service | adminLogin, verifyAdmin, listAdminUsers |
| AdminAccountService | account_service | listAccounts, getAccount, updateStatus, assignRoles |
| AdminProductService | product_service | createProduct, updateProduct, deleteProduct, rotateCosts |
| AdminBillingService | billing_service | listRecords, issueRefund, adjustBilling |
| AdminSubscriptionService | subscription_service | listAll, changeTier, adjustCredits |
| AdminWalletService | wallet_service | getWallet, adjustBalance |
| AdminOrgService | organization_service | listOrgs, getOrg, manageMember |
| AdminPlatformService | all services | getHealthAll, getServiceDetail |
| AdminAuditService | audit_service | searchLogs, exportLogs |

## Shared UI Components (isA_App_SDK)

| Component | Purpose |
|-----------|---------|
| AdminDataTable | Sortable, filterable, paginated table with bulk actions |
| StatsCard | Metric card (value, trend, sparkline) |
| StatusBadge | Service health indicator |
| AuditLogEntry | Formatted audit log row |
| ConfirmDialog | Destructive action confirmation |
| AdminPageLayout | Standard admin page layout |

---

## Out of Scope (v0.1)

1. Real-time log streaming (use Grafana/Loki directly)
2. CI/CD pipeline management (use GitHub Actions directly)
3. Custom admin role creation (predefined roles only)
4. Multi-tenant admin (single platform admin only)
5. Mobile admin app (web-only)

---

**Document Version**: 0.1
**Last Updated**: 2026-03-29
**Maintained By**: Platform Team
