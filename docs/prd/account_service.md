# Account Service - Product Requirements Document (PRD)

## Product Overview

**Product Name**: Account Service
**Version**: 1.1.0
**Status**: Production
**Owner**: Identity & Platform Team
**Last Updated**: 2025-12-11

### Vision
Establish the most reliable, scalable identity anchor for the isA_user platform with idempotent account management, event-driven synchronization, and zero-downtime identity operations.

### Mission
Provide a production-grade identity service that guarantees every user has exactly one account record, serves as the single source of truth for user identity, and seamlessly integrates with all platform services through events and APIs.

### Target Users
- **Internal Services**: Auth, Subscription, Billing, Storage, Organization, Device
- **Platform Admins**: User management, compliance, support
- **End Users**: Profile management, preferences, account settings
- **Analytics Teams**: User metrics, acquisition tracking, health monitoring

### Key Differentiators
1. **Idempotent Account Creation**: `/ensure` endpoint guarantees exactly-once semantics
2. **Event-Driven Architecture**: Real-time synchronization across 25+ microservices
3. **Separation of Concerns**: Identity only - no auth, billing, or subscription coupling
4. **Zero-Schema Preferences**: JSONB preferences without schema migrations
5. **Soft Delete Architecture**: Audit-friendly account deactivation with recovery

---

## Product Goals

### Primary Goals
1. **Idempotent Identity**: Guarantee unique user accounts with zero duplicates (99.99% constraint enforcement)
2. **Sub-100ms Reads**: Profile fetches complete in <100ms (p95)
3. **High Availability**: 99.9% uptime with graceful degradation
4. **Event Reliability**: 99.5%+ event publishing success rate
5. **Data Integrity**: ACID guarantees for all account mutations

### Secondary Goals
1. **Self-Service Admin**: Admin dashboard for account management
2. **Preference Flexibility**: Schema-free settings storage for all services
3. **Audit Trail**: Complete change tracking for compliance (GDPR, SOC2)
4. **Search Performance**: Sub-200ms account search across 1M+ users
5. **Statistics API**: Real-time account health metrics

---

## Epics and User Stories

### Epic 1: Idempotent Account Management

**Objective**: Enable safe, concurrent account creation with guaranteed uniqueness.

#### E1-US1: Idempotent Account Ensure
**As an** Auth Service
**I want to** ensure a user account exists without risking duplicates
**So that** multiple registration flows can safely call the same endpoint

**Acceptance Criteria**:
- AC1: POST /api/v1/accounts/ensure accepts user_id, email, name
- AC2: If user_id exists, return existing account (200 OK)
- AC3: If user_id new, create account and return (201 Created)
- AC4: Email uniqueness enforced (return 400 if email used by different user)
- AC5: Publish user.created event only on new account creation
- AC6: Response time <200ms
- AC7: Thread-safe with concurrent requests

**API Reference**: `POST /api/v1/accounts/ensure`

**Example Request**:
```json
{
  "user_id": "usr_abc123",
  "email": "john@example.com",
  "name": "John Doe"
}
```

**Example Response** (New Account):
```json
{
  "user_id": "usr_abc123",
  "email": "john@example.com",
  "name": "John Doe",
  "is_active": true,
  "preferences": {},
  "created_at": "2025-12-11T10:00:00Z",
  "updated_at": "2025-12-11T10:00:00Z"
}
```

#### E1-US2: Prevent Duplicate Emails
**As a** Platform Administrator
**I want to** enforce email uniqueness across active accounts
**So that** users cannot register with the same email multiple times

**Acceptance Criteria**:
- AC1: Email uniqueness validated on account creation
- AC2: Email uniqueness validated on profile updates
- AC3: Inactive accounts exempt from uniqueness check (deactivated accounts can reuse emails)
- AC4: Return 400 Bad Request with clear error message on duplicate
- AC5: Case-insensitive email matching
- AC6: Whitespace trimmed before validation

#### E1-US3: Account Creation with Defaults
**As a** System
**I want to** create accounts with sensible defaults
**So that** downstream services have consistent data

**Acceptance Criteria**:
- AC1: Default is_active = true
- AC2: Default preferences = {} (empty JSONB)
- AC3: created_at and updated_at auto-generated
- AC4: user_id validated as non-empty string
- AC5: email validated with basic regex
- AC6: name validated as 1-255 characters

---

### Epic 2: Profile Management

**Objective**: Enable users and admins to update account profile information.

#### E2-US1: Get Account Profile by ID
**As a** Mobile App
**I want to** retrieve a user's full profile by user_id
**So that** I can display their account information

**Acceptance Criteria**:
- AC1: GET /api/v1/accounts/profile/{user_id} returns profile
- AC2: Includes all fields: user_id, email, name, is_active, preferences, created_at, updated_at
- AC3: Returns 404 if account not found
- AC4: Only returns active accounts by default
- AC5: Response time <50ms
- AC6: No authentication (handled by gateway)

**API Reference**: `GET /api/v1/accounts/profile/{user_id}`

#### E2-US2: Update Account Profile
**As a** User
**I want to** update my name or email
**So that** my profile stays current

**Acceptance Criteria**:
- AC1: PUT /api/v1/accounts/profile/{user_id} accepts name, email
- AC2: Validates email uniqueness if email changed
- AC3: Validates name length (1-255 chars)
- AC4: Updates updated_at timestamp
- AC5: Publishes user.profile_updated event with updated_fields list
- AC6: Returns updated profile
- AC7: Returns 404 if account not found
- AC8: Returns 400 on validation errors

**API Reference**: `PUT /api/v1/accounts/profile/{user_id}`

**Example Request**:
```json
{
  "name": "John Smith",
  "email": "john.smith@example.com"
}
```

**Example Response**:
```json
{
  "user_id": "usr_abc123",
  "email": "john.smith@example.com",
  "name": "John Smith",
  "is_active": true,
  "preferences": {"theme": "dark"},
  "created_at": "2025-12-11T10:00:00Z",
  "updated_at": "2025-12-11T10:15:00Z"
}
```

#### E2-US3: Get Account by Email
**As a** Support Agent
**I want to** find a user account by email address
**So that** I can assist with user inquiries

**Acceptance Criteria**:
- AC1: GET /api/v1/accounts/by-email/{email} returns profile
- AC2: Case-insensitive email lookup
- AC3: Returns 404 if email not found
- AC4: Only returns active accounts
- AC5: Response time <100ms

**API Reference**: `GET /api/v1/accounts/by-email/{email}`

---

### Epic 3: Preferences Management

**Objective**: Provide flexible, schema-free preference storage for all services.

#### E3-US1: Update User Preferences
**As a** Web Application
**I want to** store user-specific settings
**So that** users have personalized experiences

**Acceptance Criteria**:
- AC1: PUT /api/v1/accounts/preferences/{user_id} accepts JSONB preferences
- AC2: Merges new preferences with existing (not replace)
- AC3: Updates updated_at timestamp
- AC4: Returns success confirmation
- AC5: Response time <50ms
- AC6: Validates JSON structure
- AC7: No size limit (PostgreSQL JSONB handles it)

**API Reference**: `PUT /api/v1/accounts/preferences/{user_id}`

**Example Request**:
```json
{
  "theme": "dark",
  "language": "en",
  "notifications": {
    "email": true,
    "push": false
  }
}
```

**Example Response**:
```json
{
  "message": "Preferences updated successfully"
}
```

#### E3-US2: Read Preferences from Profile
**As a** Service
**I want to** retrieve user preferences via profile endpoint
**So that** I can apply custom settings

**Acceptance Criteria**:
- AC1: Preferences included in GET /api/v1/accounts/profile/{user_id}
- AC2: Returns empty object {} if no preferences set
- AC3: Full JSONB structure returned
- AC4: No filtering or transformation

---

### Epic 4: Account Status Management

**Objective**: Enable admins to activate, deactivate, and delete accounts.

#### E4-US1: Change Account Status
**As an** Admin
**I want to** activate or deactivate user accounts
**So that** I can manage access control

**Acceptance Criteria**:
- AC1: PUT /api/v1/accounts/status/{user_id} accepts is_active, reason
- AC2: Sets is_active to true (activate) or false (deactivate)
- AC3: Reason optional but recommended
- AC4: Updates updated_at timestamp
- AC5: Publishes user.status_changed event with reason, changed_by
- AC6: Returns success confirmation
- AC7: Response time <50ms

**API Reference**: `PUT /api/v1/accounts/status/{user_id}`

**Example Request**:
```json
{
  "is_active": false,
  "reason": "Policy violation - spam activity"
}
```

**Example Response**:
```json
{
  "message": "Account deactivated successfully"
}
```

#### E4-US2: Soft Delete Account
**As a** User or Admin
**I want to** delete a user account
**So that** users can exercise right to deletion

**Acceptance Criteria**:
- AC1: DELETE /api/v1/accounts/profile/{user_id} soft-deletes account
- AC2: Sets is_active = false (same as deactivate)
- AC3: Optional reason query parameter
- AC4: Publishes user.deleted event with reason
- AC5: Account data preserved for audit trail
- AC6: Returns success confirmation
- AC7: Response time <50ms

**API Reference**: `DELETE /api/v1/accounts/profile/{user_id}?reason=User%20requested%20deletion`

#### E4-US3: Reactivate Deactivated Account
**As an** Admin
**I want to** reactivate a deactivated account
**So that** users can be restored after suspension

**Acceptance Criteria**:
- AC1: PUT /api/v1/accounts/status/{user_id} with is_active=true reactivates
- AC2: Works on both deactivated and deleted accounts
- AC3: Publishes user.status_changed event
- AC4: Returns success confirmation

---

### Epic 5: Account Search and Listing

**Objective**: Enable efficient account discovery and bulk operations.

#### E5-US1: List Accounts with Pagination
**As a** Admin Dashboard
**I want to** list all accounts with pagination
**So that** I can browse users efficiently

**Acceptance Criteria**:
- AC1: GET /api/v1/accounts accepts page, page_size, is_active, search
- AC2: page_size: 1-100 (default: 50)
- AC3: page: 1+ (default: 1)
- AC4: is_active filter optional (default: active only)
- AC5: search applies to name and email (ILIKE)
- AC6: Results sorted by created_at DESC
- AC7: Returns accounts array, total count, pagination metadata
- AC8: Response time <200ms for 100 results

**API Reference**: `GET /api/v1/accounts?page=1&page_size=50&is_active=true&search=john`

**Example Response**:
```json
{
  "accounts": [
    {
      "user_id": "usr_123",
      "email": "john@example.com",
      "name": "John Doe",
      "is_active": true,
      "created_at": "2025-12-11T10:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 50,
  "pages": 1
}
```

#### E5-US2: Search Accounts by Query
**As a** Support Agent
**I want to** search accounts by partial name or email
**So that** I can quickly find users

**Acceptance Criteria**:
- AC1: GET /api/v1/accounts/search accepts query, limit, include_inactive
- AC2: query applies to both name and email (ILIKE)
- AC3: limit: 1-100 (default: 50)
- AC4: include_inactive: boolean (default: false)
- AC5: Results sorted by created_at DESC
- AC6: Returns array of account summaries
- AC7: Response time <150ms

**API Reference**: `GET /api/v1/accounts/search?query=john&limit=50&include_inactive=false`

#### E5-US3: Get Account Statistics
**As a** Monitoring Dashboard
**I want to** see account health metrics
**So that** I can track user growth and status

**Acceptance Criteria**:
- AC1: GET /api/v1/accounts/stats returns statistics
- AC2: Includes: total_accounts, active_accounts, inactive_accounts
- AC3: Includes: recent_registrations_7d, recent_registrations_30d
- AC4: Response time <200ms
- AC5: Uses concurrent queries for performance

**API Reference**: `GET /api/v1/accounts/stats`

**Example Response**:
```json
{
  "total_accounts": 15420,
  "active_accounts": 14985,
  "inactive_accounts": 435,
  "recent_registrations_7d": 245,
  "recent_registrations_30d": 1089
}
```

---

### Epic 6: Event-Driven Integration

**Objective**: Publish events for all account lifecycle changes to enable real-time synchronization.

#### E6-US1: Publish Account Created Event
**As an** Account Service
**I want to** publish user.created events
**So that** downstream services can initialize user data

**Acceptance Criteria**:
- AC1: user.created published on new account creation only (not on existing account)
- AC2: Event payload includes: user_id, email, name, subscription_plan (deprecated), created_at
- AC3: Published to NATS event bus
- AC4: Event publishing failures logged but don't block operation
- AC5: Subscribers: Subscription, Wallet, Audit, Analytics, Organization

#### E6-US2: Publish Profile Updated Event
**As an** Account Service
**I want to** publish user.profile_updated events
**So that** other services stay synchronized with profile changes

**Acceptance Criteria**:
- AC1: user.profile_updated published on PUT /api/v1/accounts/profile/{user_id}
- AC2: Event payload includes: user_id, email, name, updated_fields list, updated_at
- AC3: updated_fields tracks exactly which fields changed (e.g., ["name", "email"])
- AC4: Subscribers: Audit, Search, Notification, Session

#### E6-US3: Publish Account Deleted Event
**As an** Account Service
**I want to** publish user.deleted events
**So that** other services can cleanup user data

**Acceptance Criteria**:
- AC1: user.deleted published on DELETE /api/v1/accounts/profile/{user_id}
- AC2: Event payload includes: user_id, email, reason, deleted_at
- AC3: Subscribers: Subscription, Storage, Session, Audit, Billing, Organization

#### E6-US4: Publish Status Changed Event
**As an** Account Service
**I want to** publish user.status_changed events
**So that** services can respond to activation/deactivation

**Acceptance Criteria**:
- AC1: user.status_changed published on PUT /api/v1/accounts/status/{user_id}
- AC2: Event payload includes: user_id, email, is_active, reason, changed_at, changed_by
- AC3: Subscribers: Session, Subscription, Audit, Notification, Compliance

---

## API Surface Documentation

### Base URL
- **Development**: `http://localhost:8201`
- **Staging**: `https://staging-account.isa.ai`
- **Production**: `https://account.isa.ai`

### API Version
All endpoints prefixed with `/api/v1/`

### Authentication
- **Current**: Handled by API Gateway (JWT validation)
- **Header**: `Authorization: Bearer <token>`
- **User Context**: user_id extracted from JWT claims

### Core Endpoints Summary

| Method | Endpoint | Purpose | Response Time |
|--------|----------|---------|---------------|
| POST | `/api/v1/accounts/ensure` | Idempotent account creation | <200ms |
| GET | `/api/v1/accounts/profile/{user_id}` | Get full profile | <50ms |
| PUT | `/api/v1/accounts/profile/{user_id}` | Update profile | <100ms |
| PUT | `/api/v1/accounts/preferences/{user_id}` | Update preferences | <50ms |
| DELETE | `/api/v1/accounts/profile/{user_id}` | Soft delete account | <50ms |
| GET | `/api/v1/accounts` | List with pagination | <200ms |
| GET | `/api/v1/accounts/search` | Search by query | <150ms |
| GET | `/api/v1/accounts/by-email/{email}` | Find by email | <100ms |
| PUT | `/api/v1/accounts/status/{user_id}` | Change status | <50ms |
| GET | `/api/v1/accounts/stats` | Get statistics | <200ms |
| GET | `/health` | Health check | <20ms |
| GET | `/health/detailed` | Detailed health | <50ms |

### HTTP Status Codes
- `200 OK`: Successful operation
- `201 Created`: New account created
- `400 Bad Request`: Validation error (duplicate email, invalid input)
- `404 Not Found`: Account not found
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Database unavailable

### Common Response Format

**Success Response**:
```json
{
  "user_id": "usr_abc123",
  "email": "user@example.com",
  "name": "John Doe",
  "is_active": true,
  "preferences": {},
  "created_at": "2025-12-11T10:00:00Z",
  "updated_at": "2025-12-11T10:00:00Z"
}
```

**Error Response**:
```json
{
  "detail": "Account not found with user_id: usr_xyz"
}
```

### Rate Limits (Future)
- **Per User**: 1000 requests/hour
- **Per IP**: 5000 requests/hour
- **Burst**: 100 requests/minute

### Pagination Format
```
GET /api/v1/accounts?page=1&page_size=50
```
Response includes:
```json
{
  "accounts": [...],
  "total": 1500,
  "page": 1,
  "page_size": 50,
  "pages": 30
}
```

---

## Functional Requirements

### FR-1: Idempotent Account Creation
System SHALL provide `/ensure` endpoint that creates account if new, returns existing if present

### FR-2: Email Uniqueness
System SHALL enforce unique email addresses across active accounts

### FR-3: Profile Management
System SHALL support updating name, email with validation

### FR-4: Preferences Storage
System SHALL store user preferences as JSONB with merge-on-update behavior

### FR-5: Account Status Management
System SHALL support activate, deactivate, soft delete operations

### FR-6: Account Search
System SHALL provide case-insensitive partial search on name and email

### FR-7: Pagination
System SHALL support pagination for list endpoints (page_size: 1-100)

### FR-8: Event Publishing
System SHALL publish events for all account mutations to NATS

### FR-9: Health Checks
System SHALL provide /health and /health/detailed endpoints

### FR-10: Statistics
System SHALL provide real-time account statistics

---

## Non-Functional Requirements

### NFR-1: Performance
- **Account Ensure**: <200ms (p95)
- **Profile Fetch**: <50ms (p95)
- **Profile Update**: <100ms (p95)
- **Account Search**: <150ms (p95)
- **List Accounts**: <200ms for 100 results (p95)
- **Health Check**: <20ms (p99)

### NFR-2: Availability
- **Uptime**: 99.9% (excluding planned maintenance)
- **Database Failover**: Automatic with <30s recovery
- **Graceful Degradation**: Event publishing failures don't block operations

### NFR-3: Scalability
- **Concurrent Users**: 100K+ concurrent requests
- **Total Accounts**: 10M+ accounts supported
- **Throughput**: 5K requests/second
- **Database Connections**: Pooled with max 100 connections

### NFR-4: Data Integrity
- **ACID Transactions**: All mutations wrapped in PostgreSQL transactions
- **Unique Constraints**: Enforced at database level
- **Validation**: Pydantic models validate all inputs
- **Audit Trail**: All changes tracked with timestamps

### NFR-5: Security
- **Authentication**: JWT validation by API Gateway
- **Authorization**: User-scoped data access
- **Input Sanitization**: SQL injection prevention via parameterized queries
- **Email Validation**: Regex validation for format

### NFR-6: Observability
- **Structured Logging**: JSON logs for all operations
- **Metrics**: Prometheus-compatible (future)
- **Tracing**: Request IDs for debugging
- **Health Monitoring**: Database connectivity checked

### NFR-7: API Compatibility
- **Versioning**: /api/v1/ for backward compatibility
- **Deprecation Policy**: 6-month notice for breaking changes
- **OpenAPI**: Swagger documentation auto-generated

---

## Dependencies

### External Services

1. **PostgreSQL gRPC Service**: Account data storage
   - Host: `isa-postgres-grpc:50061`
   - Schema: `account.users`
   - Indexes: user_id (PK), email, is_active, preferences (GIN)
   - SLA: 99.9% availability

2. **NATS Event Bus**: Event publishing
   - Host: `isa-nats:4222`
   - Subjects: `user.created`, `user.profile_updated`, `user.deleted`, `user.status_changed`
   - SLA: 99.9% availability

3. **Consul**: Service discovery and health checks
   - Host: `localhost:8500`
   - Service Name: `account_service`
   - Health Check: HTTP `/health`
   - SLA: 99.9% availability

4. **Subscription Service** (Optional): Cross-service data enrichment
   - Used for subscription_plan data (deprecated pattern)
   - Future: Remove dependency

### Internal Dependencies
- **core.config_manager**: Configuration management
- **core.logger**: Structured logging
- **core.nats_client**: Event bus client
- **isa_common.consul_client**: Service registration
- **isa_common.AsyncPostgresClient**: Database client

---

## Success Criteria

### Phase 1: Core Identity (Complete)
- [x] Idempotent account creation working
- [x] Profile CRUD operations functional
- [x] PostgreSQL storage stable
- [x] Event publishing active
- [x] Health checks implemented

### Phase 2: Search and Admin (Complete)
- [x] Account search working
- [x] Pagination implemented
- [x] Statistics endpoint functional
- [x] Status management working
- [x] Preferences storage stable

### Phase 3: Production Hardening (Current)
- [x] Migration from subscription data to subscription_service
- [ ] Comprehensive test coverage (Component, Integration, API, Smoke)
- [ ] Performance benchmarks met (sub-100ms reads)
- [ ] Monitoring and alerting setup
- [ ] Load testing completed

### Phase 4: Scale and Optimize (Future)
- [ ] Rate limiting implemented
- [ ] Advanced search filters (created_at ranges, sorting)
- [ ] Bulk operations (batch updates)
- [ ] Audit log export
- [ ] Multi-region support

---

## Out of Scope

The following are explicitly NOT included in this release:

1. **Authentication**: Handled by auth_service (JWT generation, password management)
2. **Authorization**: Role-based access handled by authorization_service
3. **Subscription Management**: Moved to subscription_service (subscription_plan, billing_cycle)
4. **Credit/Wallet**: Handled by wallet_service
5. **Organization Membership**: Handled by organization_service
6. **Device Management**: Handled by device_service
7. **Email Verification**: Handled by notification_service
8. **Password Reset**: Handled by auth_service
9. **Multi-Factor Auth**: Handled by auth_service
10. **Account Merging**: Future feature (duplicate account consolidation)

---

## Appendix: Request/Response Examples

### 1. Idempotent Account Creation

**Request**:
```bash
curl -X POST http://localhost:8201/api/v1/accounts/ensure \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "user_id": "usr_abc123",
    "email": "john@example.com",
    "name": "John Doe"
  }'
```

**Response** (New Account - 201 Created):
```json
{
  "user_id": "usr_abc123",
  "email": "john@example.com",
  "name": "John Doe",
  "is_active": true,
  "preferences": {},
  "created_at": "2025-12-11T10:00:00Z",
  "updated_at": "2025-12-11T10:00:00Z"
}
```

**Response** (Existing Account - 200 OK):
```json
{
  "user_id": "usr_abc123",
  "email": "john@example.com",
  "name": "John Doe",
  "is_active": true,
  "preferences": {"theme": "dark"},
  "created_at": "2025-12-10T08:30:00Z",
  "updated_at": "2025-12-11T09:45:00Z"
}
```

### 2. Update Profile

**Request**:
```bash
curl -X PUT http://localhost:8201/api/v1/accounts/profile/usr_abc123 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "name": "John Smith"
  }'
```

**Response**:
```json
{
  "user_id": "usr_abc123",
  "email": "john@example.com",
  "name": "John Smith",
  "is_active": true,
  "preferences": {},
  "created_at": "2025-12-11T10:00:00Z",
  "updated_at": "2025-12-11T10:15:00Z"
}
```

### 3. Update Preferences

**Request**:
```bash
curl -X PUT http://localhost:8201/api/v1/accounts/preferences/usr_abc123 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "theme": "dark",
    "language": "en",
    "notifications": {
      "email": true,
      "push": false
    }
  }'
```

**Response**:
```json
{
  "message": "Preferences updated successfully"
}
```

### 4. Search Accounts

**Request**:
```bash
curl -X GET "http://localhost:8201/api/v1/accounts/search?query=john&limit=10" \
  -H "Authorization: Bearer <token>"
```

**Response**:
```json
[
  {
    "user_id": "usr_abc123",
    "email": "john@example.com",
    "name": "John Doe",
    "is_active": true,
    "created_at": "2025-12-11T10:00:00Z"
  },
  {
    "user_id": "usr_def456",
    "email": "john.smith@example.com",
    "name": "John Smith",
    "is_active": true,
    "created_at": "2025-12-10T08:30:00Z"
  }
]
```

### 5. Get Statistics

**Request**:
```bash
curl -X GET "http://localhost:8201/api/v1/accounts/stats" \
  -H "Authorization: Bearer <token>"
```

**Response**:
```json
{
  "total_accounts": 15420,
  "active_accounts": 14985,
  "inactive_accounts": 435,
  "recent_registrations_7d": 245,
  "recent_registrations_30d": 1089
}
```

### 6. Change Account Status

**Request**:
```bash
curl -X PUT http://localhost:8201/api/v1/accounts/status/usr_abc123 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "is_active": false,
    "reason": "Policy violation"
  }'
```

**Response**:
```json
{
  "message": "Account deactivated successfully"
}
```

---

## Migration Notes

### Subscription Data Migration
**Status**: In Progress
**Target**: Q1 2026

Account Service previously managed `subscription_status` and `subscription_plan` fields. These have been migrated to `subscription_service`:

**Before** (Deprecated):
```json
{
  "user_id": "usr_123",
  "subscription_status": "active",
  "subscription_plan": "pro"
}
```

**After** (Current):
```json
// account_service response:
{
  "user_id": "usr_123",
  "email": "user@example.com",
  "name": "User Name"
}

// subscription_service response (separate call):
{
  "user_id": "usr_123",
  "tier_code": "pro",
  "status": "active"
}
```

**Migration Steps**:
1. ✅ subscription_service deployed with subscription data
2. ✅ Migration script 002_remove_subscription_status.sql executed
3. ✅ API contracts updated (removed subscription fields from responses)
4. ⏳ Event contracts updated (user.created event still includes deprecated subscription_plan for backward compatibility)
5. ⏳ Downstream services updated to call subscription_service directly
6. ⏳ Remove subscription_plan from user.created event (Q1 2026)

---

**Document Version**: 1.0
**Last Updated**: 2025-12-11
**Maintained By**: Account Service Product Team
**Related Documents**:
- Domain Context: docs/domain/account_service.md
- Design Doc: docs/design/account_service.md (next)
- Data Contract: tests/contracts/account/data_contract.py (next)
- Logic Contract: tests/contracts/account/logic_contract.md (next)
