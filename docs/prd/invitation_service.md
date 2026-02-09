# Invitation Service - Product Requirements Document (PRD)

## Product Overview

**Product Name**: Invitation Service
**Version**: 1.0.0
**Status**: Production
**Owner**: Platform & Organization Team
**Last Updated**: 2025-12-19

### Vision
Enable seamless, secure, and auditable organization membership growth through a world-class invitation workflow that converts prospects into members with minimal friction and maximum security.

### Mission
Provide a production-grade invitation management system that handles the complete invitation lifecycle - from creation through acceptance - with token-based security, role assignment, expiration control, and event-driven integration.

### Target Users
- **Organization Admins**: Create and manage invitations to grow organization membership
- **End Users (Invitees)**: Receive, view, and accept invitations to join organizations
- **Platform Services**: Organization Service integration for membership management
- **Analytics Teams**: Track invitation metrics, conversion rates, and growth patterns

### Key Differentiators
1. **Token-Based Security**: Cryptographically secure URL-safe tokens for invitation acceptance
2. **Role Pre-Assignment**: Members join with designated roles (owner/admin/member/viewer/guest)
3. **Expiration Control**: 7-day default with resend capability for extended validity
4. **Event-Driven Integration**: Real-time synchronization with Organization, Audit, and Notification services
5. **Cross-Service Validation**: Permission verification via Organization Service before invitation creation

---

## Product Goals

### Primary Goals
1. **Secure Invitations**: 100% token-secured acceptance flow with email verification
2. **High Conversion**: >60% invitation-to-acceptance conversion rate
3. **Sub-500ms Acceptance**: Complete acceptance workflow (status + member add) in <500ms (p95)
4. **Event Reliability**: 99.5%+ event publishing success rate
5. **Zero Unauthorized Access**: No invitation acceptance without valid token

### Secondary Goals
1. **Self-Service Management**: Admins can view, cancel, and resend invitations
2. **Audit Trail**: Complete invitation lifecycle tracking for compliance
3. **Expiration Hygiene**: Automatic cleanup of stale pending invitations
4. **Organization Growth Metrics**: Track invitation funnel for business insights
5. **Email Integration**: Seamless email notification for invitation delivery

---

## Epics and User Stories

### Epic 1: Invitation Creation

**Objective**: Enable organization admins to invite new members with role assignment.

#### E1-US1: Create Organization Invitation
**As an** Organization Admin
**I want to** invite someone to join my organization with a specific role
**So that** I can grow my team with appropriate access levels

**Acceptance Criteria**:
- AC1: POST /api/v1/invitations/organizations/{org_id} accepts email, role, message
- AC2: Validates inviter has owner or admin role in organization
- AC3: Verifies organization exists via Organization Service
- AC4: Rejects if pending invitation exists for same email/org
- AC5: Rejects if user already a member of organization
- AC6: Generates secure 32-byte URL-safe invitation token
- AC7: Sets 7-day expiration from creation time
- AC8: Publishes invitation.sent event
- AC9: Response time <300ms

**API Reference**: `POST /api/v1/invitations/organizations/{organization_id}`

**Example Request**:
```json
{
  "email": "newmember@example.com",
  "role": "member",
  "message": "Join our team!"
}
```

**Example Response** (201 Created):
```json
{
  "invitation_id": "inv_abc123",
  "invitation_token": "xK9mN2pQ7rS3tU6vW8xY0zA1bC4dE5fG",
  "email": "newmember@example.com",
  "role": "member",
  "status": "pending",
  "expires_at": "2025-12-26T10:00:00Z",
  "message": "Invitation created successfully"
}
```

#### E1-US2: Email Validation on Invitation
**As a** System
**I want to** validate email format before creating invitation
**So that** only valid emails receive invitations

**Acceptance Criteria**:
- AC1: Email must contain '@' character
- AC2: Email normalized to lowercase
- AC3: Returns 400 with clear error for invalid email
- AC4: Whitespace trimmed before validation

#### E1-US3: Prevent Duplicate Pending Invitations
**As a** System
**I want to** prevent multiple pending invitations to same email for same organization
**So that** users don't receive spam invitations

**Acceptance Criteria**:
- AC1: Check for existing PENDING invitation with same email and org_id
- AC2: Return 400 if pending invitation exists
- AC3: Allow new invitation if previous was accepted/expired/cancelled
- AC4: Error message clearly states duplicate exists

#### E1-US4: Invitation with Custom Message
**As an** Organization Admin
**I want to** include a personal message in the invitation
**So that** the invitee feels welcomed

**Acceptance Criteria**:
- AC1: Optional message field (max 500 characters)
- AC2: Message included in invitation email
- AC3: Message stored with invitation record

---

### Epic 2: Invitation Viewing

**Objective**: Enable invitees to view invitation details before accepting.

#### E2-US1: View Invitation by Token
**As an** Invitee
**I want to** view invitation details using the link from my email
**So that** I can decide whether to accept

**Acceptance Criteria**:
- AC1: GET /api/v1/invitations/{invitation_token} returns invitation details
- AC2: Includes organization_id, organization_name, email, role, inviter_name
- AC3: Returns 404 if token not found
- AC4: Returns 400 if invitation already accepted/expired/cancelled
- AC5: If expired during access, updates status to EXPIRED
- AC6: Publishes invitation.expired event when detecting expiration
- AC7: No authentication required (token is the auth)
- AC8: Response time <100ms

**API Reference**: `GET /api/v1/invitations/{invitation_token}`

**Example Response** (200 OK):
```json
{
  "invitation_id": "inv_abc123",
  "organization_id": "org_xyz789",
  "organization_name": "Acme Corp",
  "organization_domain": "acme.com",
  "email": "newmember@example.com",
  "role": "member",
  "status": "pending",
  "inviter_name": "John Admin",
  "inviter_email": "admin@acme.com",
  "expires_at": "2025-12-26T10:00:00Z",
  "created_at": "2025-12-19T10:00:00Z"
}
```

#### E2-US2: Handle Expired Invitation Access
**As a** System
**I want to** properly handle access to expired invitations
**So that** invitees get clear feedback

**Acceptance Criteria**:
- AC1: Check expires_at timestamp on access
- AC2: If expired, update status to EXPIRED
- AC3: Publish invitation.expired event
- AC4: Return 400 with message "Invitation has expired"
- AC5: Handle timezone-aware datetime comparison correctly

---

### Epic 3: Invitation Acceptance

**Objective**: Enable invitees to accept invitations and join organizations.

#### E3-US1: Accept Invitation
**As an** Authenticated Invitee
**I want to** accept an invitation and join the organization
**So that** I become a member with my assigned role

**Acceptance Criteria**:
- AC1: POST /api/v1/invitations/accept accepts invitation_token
- AC2: Validates invitation is PENDING and not expired
- AC3: Verifies user email matches invitation email (best effort)
- AC4: Updates invitation status to ACCEPTED with accepted_at timestamp
- AC5: Calls Organization Service to add user as member with role
- AC6: Rolls back invitation status if member addition fails
- AC7: Publishes invitation.accepted event on success
- AC8: Returns organization details and membership confirmation
- AC9: Response time <500ms

**API Reference**: `POST /api/v1/invitations/accept`

**Example Request**:
```json
{
  "invitation_token": "xK9mN2pQ7rS3tU6vW8xY0zA1bC4dE5fG",
  "user_id": "usr_def456"
}
```

**Example Response** (200 OK):
```json
{
  "invitation_id": "inv_abc123",
  "organization_id": "org_xyz789",
  "organization_name": "Acme Corp",
  "user_id": "usr_def456",
  "role": "member",
  "accepted_at": "2025-12-20T14:30:00Z"
}
```

#### E3-US2: Email Match Verification
**As a** System
**I want to** verify accepting user's email matches invitation email
**So that** only the intended recipient can accept

**Acceptance Criteria**:
- AC1: Compare user email (from user service) with invitation email
- AC2: Return 400 "Email mismatch" if different
- AC3: Case-insensitive comparison
- AC4: Verification is best-effort (may not block in all cases)

#### E3-US3: Atomic Acceptance with Rollback
**As a** System
**I want to** ensure invitation acceptance is atomic
**So that** partial failures don't leave inconsistent state

**Acceptance Criteria**:
- AC1: Invitation status update and member addition treated as unit
- AC2: If member addition to org fails, revert invitation to PENDING
- AC3: Return error indicating what failed
- AC4: No orphaned accepted invitations without membership

---

### Epic 4: Invitation Management

**Objective**: Enable admins to manage organization invitations.

#### E4-US1: Cancel Pending Invitation
**As an** Organization Admin
**I want to** cancel a pending invitation
**So that** I can revoke invitations before acceptance

**Acceptance Criteria**:
- AC1: DELETE /api/v1/invitations/{invitation_id} cancels invitation
- AC2: Only inviter OR org owner/admin can cancel
- AC3: Only PENDING invitations can be cancelled
- AC4: Updates status to CANCELLED
- AC5: Publishes invitation.cancelled event
- AC6: Returns success confirmation
- AC7: Response time <100ms

**API Reference**: `DELETE /api/v1/invitations/{invitation_id}`

**Example Response** (200 OK):
```json
{
  "message": "Invitation cancelled successfully"
}
```

#### E4-US2: Resend Invitation
**As an** Organization Admin
**I want to** resend an invitation with extended expiration
**So that** invitees who missed the email can still join

**Acceptance Criteria**:
- AC1: POST /api/v1/invitations/{invitation_id}/resend resends invitation
- AC2: Only inviter OR org owner/admin can resend
- AC3: Only PENDING invitations can be resent
- AC4: Extends expiration by 7 days from current time
- AC5: Triggers new email with same token
- AC6: Returns success confirmation (notes if email failed)
- AC7: Response time <200ms

**API Reference**: `POST /api/v1/invitations/{invitation_id}/resend`

**Example Response** (200 OK):
```json
{
  "message": "Invitation resent successfully"
}
```

#### E4-US3: List Organization Invitations
**As an** Organization Admin
**I want to** view all invitations for my organization
**So that** I can track pending, accepted, and expired invitations

**Acceptance Criteria**:
- AC1: GET /api/v1/invitations/organizations/{org_id} returns invitation list
- AC2: Only org owner/admin can view (permission check)
- AC3: Returns all statuses (pending, accepted, expired, cancelled)
- AC4: Supports limit (default 100) and offset pagination
- AC5: Ordered by created_at DESC
- AC6: Returns total count for pagination
- AC7: Response time <150ms

**API Reference**: `GET /api/v1/invitations/organizations/{organization_id}?limit=100&offset=0`

**Example Response** (200 OK):
```json
{
  "invitations": [
    {
      "invitation_id": "inv_abc123",
      "email": "user1@example.com",
      "role": "member",
      "status": "pending",
      "invited_by": "usr_admin1",
      "expires_at": "2025-12-26T10:00:00Z",
      "created_at": "2025-12-19T10:00:00Z"
    },
    {
      "invitation_id": "inv_def456",
      "email": "user2@example.com",
      "role": "admin",
      "status": "accepted",
      "invited_by": "usr_admin1",
      "accepted_at": "2025-12-18T14:30:00Z",
      "created_at": "2025-12-15T10:00:00Z"
    }
  ],
  "total": 2,
  "limit": 100,
  "offset": 0
}
```

---

### Epic 5: System Maintenance

**Objective**: Enable automated system maintenance and cleanup.

#### E5-US1: Bulk Expire Old Invitations
**As a** System Scheduler
**I want to** periodically expire old pending invitations
**So that** stale invitations are cleaned up automatically

**Acceptance Criteria**:
- AC1: POST /api/v1/invitations/admin/expire-invitations triggers bulk expiration
- AC2: Updates all PENDING invitations where expires_at < now to EXPIRED
- AC3: Returns count of expired invitations
- AC4: Admin endpoint (no user auth check - internal use)
- AC5: Response time scales with number of expired invitations

**API Reference**: `POST /api/v1/invitations/admin/expire-invitations`

**Example Response** (200 OK):
```json
{
  "expired_count": 47,
  "message": "Expired 47 old invitations"
}
```

#### E5-US2: Get Invitation Statistics
**As a** Analytics Dashboard
**I want to** view invitation metrics per organization
**So that** I can track invitation funnel performance

**Acceptance Criteria**:
- AC1: Repository provides get_invitation_stats(organization_id) method
- AC2: Returns counts by status (pending, accepted, expired, cancelled)
- AC3: Returns total invitation count
- AC4: Optional organization_id filter
- AC5: Response time <100ms

---

### Epic 6: Event-Driven Integration

**Objective**: Publish events for invitation lifecycle and subscribe to related events.

#### E6-US1: Publish Invitation Sent Event
**As an** Invitation Service
**I want to** publish invitation.sent events on creation
**So that** Audit and Analytics services can track invitations

**Acceptance Criteria**:
- AC1: invitation.sent published after successful invitation creation
- AC2: Payload includes: invitation_id, organization_id, email, role, invited_by, email_sent, timestamp
- AC3: Published to NATS event bus
- AC4: Event failures logged but don't block operation
- AC5: Subscribers: Audit Service, Analytics Service

#### E6-US2: Publish Invitation Accepted Event
**As an** Invitation Service
**I want to** publish invitation.accepted events
**So that** other services know when members join

**Acceptance Criteria**:
- AC1: invitation.accepted published after successful acceptance
- AC2: Payload includes: invitation_id, organization_id, user_id, email, role, accepted_at, timestamp
- AC3: Subscribers: Organization Service (confirmation), Audit, Analytics, Notification

#### E6-US3: Publish Invitation Expired Event
**As an** Invitation Service
**I want to** publish invitation.expired events
**So that** Analytics can track expiration rates

**Acceptance Criteria**:
- AC1: invitation.expired published when expiration detected during access
- AC2: Payload includes: invitation_id, organization_id, email, expired_at, timestamp
- AC3: Note: Bulk expiration does NOT publish individual events (performance)

#### E6-US4: Publish Invitation Cancelled Event
**As an** Invitation Service
**I want to** publish invitation.cancelled events
**So that** cancellations are auditable

**Acceptance Criteria**:
- AC1: invitation.cancelled published after cancellation
- AC2: Payload includes: invitation_id, organization_id, email, cancelled_by, timestamp
- AC3: Subscribers: Audit Service, Analytics Service

#### E6-US5: Handle Organization Deleted Event
**As an** Invitation Service
**I want to** cancel pending invitations when organization is deleted
**So that** orphaned invitations don't exist

**Acceptance Criteria**:
- AC1: Subscribe to organization.deleted event
- AC2: Cancel all PENDING invitations for deleted organization
- AC3: Log count of cancelled invitations
- AC4: Idempotent handling

#### E6-US6: Handle User Deleted Event
**As an** Invitation Service
**I want to** cancel invitations sent by deleted users
**So that** orphaned invitations are cleaned up

**Acceptance Criteria**:
- AC1: Subscribe to user.deleted event
- AC2: Cancel all PENDING invitations where invited_by = deleted user_id
- AC3: Log count of cancelled invitations
- AC4: Idempotent handling

---

### Epic 7: Service Health and Info

**Objective**: Provide health monitoring and service information endpoints.

#### E7-US1: Health Check Endpoint
**As a** Kubernetes/Consul
**I want to** check if the service is healthy
**So that** I can route traffic appropriately

**Acceptance Criteria**:
- AC1: GET /health returns service health status
- AC2: Response includes: status, service name, port, version
- AC3: Returns 200 if healthy
- AC4: Response time <20ms

**API Reference**: `GET /health`

**Example Response**:
```json
{
  "status": "healthy",
  "service": "invitation_service",
  "port": 8213,
  "version": "1.0.0"
}
```

#### E7-US2: Service Info Endpoint
**As a** Developer
**I want to** see service capabilities and endpoints
**So that** I understand what the service offers

**Acceptance Criteria**:
- AC1: GET /info returns service information
- AC2: Includes capabilities, version, endpoint documentation
- AC3: Also available at /api/v1/invitations/info

**API Reference**: `GET /info`

**Example Response**:
```json
{
  "service": "invitation_service",
  "version": "1.0.0",
  "description": "Organization invitation management microservice",
  "capabilities": {
    "invitation_creation": true,
    "email_sending": true,
    "invitation_acceptance": true,
    "invitation_management": true,
    "organization_integration": true
  },
  "endpoints": {
    "health": "/health",
    "create_invitation": "/api/v1/organizations/{org_id}/invitations",
    "get_invitation": "/api/v1/invitations/{token}",
    "accept_invitation": "/api/v1/invitations/accept",
    "organization_invitations": "/api/v1/organizations/{org_id}/invitations"
  }
}
```

---

## API Surface Documentation

### Base URL
- **Development**: `http://localhost:8213`
- **Staging**: `https://staging-invitation.isa.ai`
- **Production**: `https://invitation.isa.ai`

### API Version
All endpoints prefixed with `/api/v1/`

### Authentication
- **Current**: Handled by API Gateway (JWT validation)
- **Header**: `Authorization: Bearer <token>` (via gateway)
- **User Context**: `X-User-Id` header extracted from JWT by gateway
- **Token-based**: GET invitation by token requires no auth (token IS the auth)

### Core Endpoints Summary

| Method | Endpoint | Purpose | Auth Required | Response Time |
|--------|----------|---------|---------------|---------------|
| POST | `/api/v1/invitations/organizations/{org_id}` | Create invitation | Yes (X-User-Id) | <300ms |
| GET | `/api/v1/invitations/{token}` | View invitation by token | No (token auth) | <100ms |
| POST | `/api/v1/invitations/accept` | Accept invitation | Yes (X-User-Id) | <500ms |
| GET | `/api/v1/invitations/organizations/{org_id}` | List org invitations | Yes (X-User-Id) | <150ms |
| DELETE | `/api/v1/invitations/{invitation_id}` | Cancel invitation | Yes (X-User-Id) | <100ms |
| POST | `/api/v1/invitations/{invitation_id}/resend` | Resend invitation | Yes (X-User-Id) | <200ms |
| POST | `/api/v1/invitations/admin/expire-invitations` | Bulk expire | Admin only | varies |
| GET | `/health` | Health check | No | <20ms |
| GET | `/info` | Service info | No | <20ms |

### HTTP Status Codes
- `200 OK`: Successful operation
- `201 Created`: New invitation created
- `400 Bad Request`: Validation error, duplicate invitation, expired/cancelled status
- `401 Unauthorized`: Missing X-User-Id header
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Invitation/organization not found
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Database/dependency unavailable

### Common Response Format

**Success Response (Create)**:
```json
{
  "invitation_id": "string",
  "invitation_token": "string",
  "email": "string",
  "role": "member|admin|owner|viewer|guest",
  "status": "pending",
  "expires_at": "ISO8601 datetime",
  "message": "Invitation created successfully"
}
```

**Error Response**:
```json
{
  "detail": "Error message describing what went wrong"
}
```

### Pagination Format
```
GET /api/v1/invitations/organizations/{org_id}?limit=100&offset=0
```
Response includes:
```json
{
  "invitations": [...],
  "total": 150,
  "limit": 100,
  "offset": 0
}
```

---

## Functional Requirements

### FR-1: Invitation Creation with Permission Check
System SHALL verify inviter has owner/admin role via Organization Service before creating invitation

### FR-2: Unique Pending Invitations
System SHALL enforce one PENDING invitation per email/organization combination

### FR-3: Secure Token Generation
System SHALL generate cryptographically secure 32-byte URL-safe tokens for invitations

### FR-4: 7-Day Default Expiration
System SHALL set invitation expiration to 7 days from creation

### FR-5: Token-Based Invitation Access
System SHALL allow retrieving invitation details using only the invitation token (no auth)

### FR-6: Atomic Invitation Acceptance
System SHALL atomically update invitation status and add member to organization

### FR-7: Acceptance Rollback
System SHALL revert invitation to PENDING if member addition fails

### FR-8: Permission-Based Cancellation
System SHALL allow only inviter or org owner/admin to cancel invitations

### FR-9: Resend with Expiration Extension
System SHALL extend expiration by 7 days when invitation is resent

### FR-10: List with Pagination
System SHALL support limit/offset pagination for invitation listing

### FR-11: Event Publishing
System SHALL publish events for sent, accepted, expired, cancelled lifecycle states

### FR-12: Organization Deleted Handling
System SHALL cancel pending invitations when organization is deleted

### FR-13: User Deleted Handling
System SHALL cancel pending invitations sent by deleted users

### FR-14: Email Validation
System SHALL validate email format (must contain '@')

### FR-15: Role Assignment
System SHALL support roles: owner, admin, member, viewer, guest

### FR-16: Health Check Endpoint
System SHALL provide /health endpoint for service monitoring

### FR-17: Bulk Expiration
System SHALL provide admin endpoint for bulk expiring old invitations

### FR-18: Status State Machine
System SHALL enforce valid status transitions: PENDING → (ACCEPTED|EXPIRED|CANCELLED)

---

## Non-Functional Requirements

### NFR-1: Performance
- **Invitation Creation**: <300ms (p95)
- **Token Lookup**: <100ms (p95)
- **Invitation Acceptance**: <500ms (p95) including org service call
- **List Invitations**: <150ms for 100 results (p95)
- **Cancellation**: <100ms (p95)
- **Health Check**: <20ms (p99)

### NFR-2: Availability
- **Uptime**: 99.9% (excluding planned maintenance)
- **Database Failover**: Automatic with <30s recovery
- **Graceful Degradation**: Event publishing failures don't block operations
- **Organization Service Timeout**: 5s timeout with graceful error handling

### NFR-3: Scalability
- **Concurrent Invitations**: 10K+ concurrent invitation operations
- **Total Invitations**: 1M+ invitation records supported
- **Throughput**: 500 requests/second
- **Database Connections**: Pooled with max 50 connections

### NFR-4: Data Integrity
- **ACID Transactions**: All mutations wrapped in PostgreSQL transactions
- **Token Uniqueness**: Enforced at database level (if collision, regenerate)
- **Validation**: Pydantic models validate all inputs
- **Audit Trail**: All status changes tracked with timestamps

### NFR-5: Security
- **Token Security**: 32-byte cryptographically random tokens (secrets.token_urlsafe)
- **Permission Verification**: Organization Service validates inviter role
- **Input Sanitization**: SQL injection prevention via parameterized queries
- **Email Validation**: Format validation before storage

### NFR-6: Observability
- **Structured Logging**: JSON logs for all operations
- **Event Correlation**: Invitation events include correlation IDs
- **Request Tracing**: X-User-Id logged for debugging
- **Health Monitoring**: Database and NATS connectivity checked

### NFR-7: API Compatibility
- **Versioning**: /api/v1/ for backward compatibility
- **Deprecation Policy**: 6-month notice for breaking changes
- **OpenAPI**: Swagger documentation auto-generated via FastAPI

### NFR-8: Event Delivery
- **At-Least-Once**: Events published with retry on failure
- **Ordered Processing**: Per-invitation ordering for consistency
- **Failure Isolation**: Event bus failures don't block API operations

---

## Dependencies

### External Services

1. **PostgreSQL gRPC Service**: Invitation data storage
   - Host: `isa-postgres-grpc:50061`
   - Schema: `invitation`
   - Table: `organization_invitations`
   - SLA: 99.9% availability

2. **Organization Service**: Permission verification and member addition
   - Host: `organization_service:8212`
   - Endpoints: `/api/v1/organizations/{id}`, `/api/v1/organizations/{id}/members`
   - SLA: 99.9% availability

3. **NATS Event Bus**: Event publishing
   - Host: `isa-nats:4222`
   - Subjects: `invitation.sent`, `invitation.accepted`, `invitation.expired`, `invitation.cancelled`
   - Subscriptions: `organization.deleted`, `user.deleted`
   - SLA: 99.9% availability

4. **Consul**: Service discovery and health checks
   - Host: `localhost:8500`
   - Service Name: `invitation_service`
   - Health Check: HTTP `/health`
   - SLA: 99.9% availability

5. **Notification Service** (Future): Email delivery
   - Currently: Email sending is simplified (logging only)
   - Future: Integration with notification_service for actual delivery

### Internal Dependencies
- **core.config_manager**: Configuration management
- **core.logger**: Structured logging
- **core.nats_client**: Event bus client
- **isa_common.consul_client**: Service registration
- **isa_common.AsyncPostgresClient**: Database client

---

## Success Criteria

### Phase 1: Core Invitation Flow (Complete)
- [x] Invitation creation with permission check
- [x] Token-based invitation viewing
- [x] Invitation acceptance with member addition
- [x] PostgreSQL storage stable
- [x] Event publishing active
- [x] Health checks implemented

### Phase 2: Management Features (Complete)
- [x] Invitation cancellation working
- [x] Invitation resend functional
- [x] List invitations with pagination
- [x] Bulk expiration endpoint
- [x] Event subscriptions active (org.deleted, user.deleted)

### Phase 3: Production Hardening (Current)
- [ ] Comprehensive test coverage (Component, Integration, API, Smoke)
- [ ] Performance benchmarks met (sub-500ms acceptance)
- [ ] Monitoring and alerting setup
- [ ] Dependency injection pattern (protocols.py, factory.py)
- [ ] Load testing completed

### Phase 4: Scale and Optimize (Future)
- [ ] Real email integration via Notification Service
- [ ] Rate limiting per organization
- [ ] Invitation templates/branding
- [ ] Bulk invitation creation
- [ ] Analytics dashboard integration
- [ ] Multi-language invitation emails

---

## Out of Scope

The following are explicitly NOT included in this release:

1. **Organization Management**: Handled by organization_service
2. **User Authentication**: Handled by auth_service
3. **User Accounts**: Handled by account_service
4. **Membership Management**: After acceptance, handled by organization_service
5. **Email Delivery**: Currently simplified; full integration with notification_service is future
6. **Invitation Branding**: Custom invitation templates per organization
7. **Bulk Invitations**: Creating multiple invitations in one API call
8. **Invitation Analytics Dashboard**: Visualization of invitation metrics
9. **Magic Link Registration**: Creating user account as part of acceptance (users must pre-exist)
10. **Domain-Based Auto-Join**: Auto-accepting invitations based on email domain

---

## Appendix: Request/Response Examples

### 1. Create Invitation

**Request**:
```bash
curl -X POST http://localhost:8213/api/v1/invitations/organizations/org_xyz789 \
  -H "Content-Type: application/json" \
  -H "X-User-Id: usr_admin123" \
  -d '{
    "email": "newmember@example.com",
    "role": "member",
    "message": "Welcome to our team!"
  }'
```

**Response** (201 Created):
```json
{
  "invitation_id": "inv_abc123",
  "invitation_token": "xK9mN2pQ7rS3tU6vW8xY0zA1bC4dE5fG",
  "email": "newmember@example.com",
  "role": "member",
  "status": "pending",
  "expires_at": "2025-12-26T10:00:00Z",
  "message": "Invitation created successfully"
}
```

### 2. View Invitation by Token

**Request**:
```bash
curl -X GET http://localhost:8213/api/v1/invitations/xK9mN2pQ7rS3tU6vW8xY0zA1bC4dE5fG
```

**Response** (200 OK):
```json
{
  "invitation_id": "inv_abc123",
  "organization_id": "org_xyz789",
  "organization_name": "Acme Corp",
  "organization_domain": "acme.com",
  "email": "newmember@example.com",
  "role": "member",
  "status": "pending",
  "inviter_name": "John Admin",
  "inviter_email": "admin@acme.com",
  "expires_at": "2025-12-26T10:00:00Z",
  "created_at": "2025-12-19T10:00:00Z"
}
```

### 3. Accept Invitation

**Request**:
```bash
curl -X POST http://localhost:8213/api/v1/invitations/accept \
  -H "Content-Type: application/json" \
  -H "X-User-Id: usr_newmember456" \
  -d '{
    "invitation_token": "xK9mN2pQ7rS3tU6vW8xY0zA1bC4dE5fG"
  }'
```

**Response** (200 OK):
```json
{
  "invitation_id": "inv_abc123",
  "organization_id": "org_xyz789",
  "organization_name": "Acme Corp",
  "user_id": "usr_newmember456",
  "role": "member",
  "accepted_at": "2025-12-20T14:30:00Z"
}
```

### 4. List Organization Invitations

**Request**:
```bash
curl -X GET "http://localhost:8213/api/v1/invitations/organizations/org_xyz789?limit=50&offset=0" \
  -H "X-User-Id: usr_admin123"
```

**Response** (200 OK):
```json
{
  "invitations": [
    {
      "invitation_id": "inv_abc123",
      "organization_id": "org_xyz789",
      "email": "user1@example.com",
      "role": "member",
      "status": "accepted",
      "invited_by": "usr_admin123",
      "invitation_token": "***",
      "expires_at": "2025-12-26T10:00:00Z",
      "accepted_at": "2025-12-20T14:30:00Z",
      "created_at": "2025-12-19T10:00:00Z"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

### 5. Cancel Invitation

**Request**:
```bash
curl -X DELETE http://localhost:8213/api/v1/invitations/inv_def456 \
  -H "X-User-Id: usr_admin123"
```

**Response** (200 OK):
```json
{
  "message": "Invitation cancelled successfully"
}
```

### 6. Resend Invitation

**Request**:
```bash
curl -X POST http://localhost:8213/api/v1/invitations/inv_ghi789/resend \
  -H "X-User-Id: usr_admin123"
```

**Response** (200 OK):
```json
{
  "message": "Invitation resent successfully"
}
```

### 7. Bulk Expire Invitations

**Request**:
```bash
curl -X POST http://localhost:8213/api/v1/invitations/admin/expire-invitations
```

**Response** (200 OK):
```json
{
  "expired_count": 47,
  "message": "Expired 47 old invitations"
}
```

### 8. Health Check

**Request**:
```bash
curl http://localhost:8213/health
```

**Response** (200 OK):
```json
{
  "status": "healthy",
  "service": "invitation_service",
  "port": 8213,
  "version": "1.0.0"
}
```

---

**Document Version**: 1.0
**Last Updated**: 2025-12-19
**Maintained By**: Invitation Service Product Team
**Related Documents**:
- Domain Context: docs/domain/invitation_service.md
- Design Doc: docs/design/invitation_service.md
- Data Contract: tests/contracts/invitation_service/data_contract.py
- Logic Contract: tests/contracts/invitation_service/logic_contract.md
- System Contract: tests/contracts/invitation_service/system_contract.md
