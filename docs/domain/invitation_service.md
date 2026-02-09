# Invitation Service - Domain Context

## Overview

The Invitation Service is the **organizational onboarding gateway** for the isA_user platform. It manages the complete invitation lifecycle for organization membership, enabling secure, controlled, and auditable user onboarding to organizations, families, and teams.

**Business Context**: Enable organizations to grow their membership through secure email-based invitations with role assignment, expiration control, and cross-service integration. Every new organization member joins through an invitation workflow.

**Core Value Proposition**: Transform the complex process of organization membership onboarding into a streamlined, secure, and event-driven workflow with token-based verification, permission validation, and automatic member provisioning.

---

## Business Taxonomy

### Core Entities

#### 1. Invitation
**Definition**: A time-limited membership offer sent to an email address inviting the recipient to join a specific organization with a designated role.

**Business Purpose**:
- Enable controlled growth of organization membership
- Establish role assignment before membership begins
- Provide secure token-based acceptance workflow
- Track invitation lifecycle for audit and compliance
- Support email notification integration

**Key Attributes**:
- Invitation ID (unique identifier, UUID)
- Organization ID (target organization)
- Email (invited person's email address)
- Role (assigned organization role)
- Status (invitation state)
- Invitation Token (secure URL-safe token for acceptance)
- Invited By (user ID of inviter)
- Expires At (7-day expiration timestamp)
- Accepted At (when invitation was accepted)
- Created At (invitation creation timestamp)
- Updated At (last modification timestamp)

**Invitation States**:
- **Pending**: Active invitation awaiting acceptance
- **Accepted**: Invitation accepted, user added to organization
- **Expired**: Invitation past expiration date
- **Cancelled**: Invitation revoked by inviter or admin

#### 2. Organization Role
**Definition**: Permission level assigned to invited users defining their capabilities within the organization.

**Business Purpose**:
- Define access control levels before membership
- Enable hierarchical organization structure
- Support principle of least privilege
- Allow role-based feature access

**Role Hierarchy**:
- **Owner**: Full organization control, can delete organization
- **Admin**: Manage members, settings, can invite users
- **Member**: Standard access, cannot manage others
- **Viewer**: Read-only access to organization resources
- **Guest**: Limited temporary access

#### 3. Invitation Token
**Definition**: Cryptographically secure, URL-safe token for validating invitation acceptance.

**Business Purpose**:
- Enable secure email-based invitation links
- Prevent unauthorized invitation acceptance
- Support single-use acceptance workflow
- Provide URL-friendly acceptance mechanism

**Key Attributes**:
- Token Value (32-byte URL-safe string via secrets.token_urlsafe)
- Associated Invitation ID
- Expiration inherited from invitation

#### 4. Invitation Detail
**Definition**: Extended invitation information including organization and inviter context for display purposes.

**Business Purpose**:
- Provide rich context for invitation acceptance pages
- Display organization name and inviter information
- Support informed decision-making by invitee

**Key Attributes**:
- Base invitation fields
- Organization Name
- Organization Domain
- Inviter Name
- Inviter Email

---

## Domain Scenarios

### Scenario 1: Create Organization Invitation
**Actor**: Organization Admin/Owner
**Trigger**: Admin wants to add new member to organization
**Flow**:
1. Admin navigates to organization members page
2. Admin enters invitee email and selects role (e.g., "member")
3. App calls `POST /api/v1/invitations/organizations/{org_id}` with X-User-Id header
4. Invitation Service verifies organization exists via Organization Service
5. Invitation Service validates admin has invite permissions (owner/admin role)
6. Invitation Service checks no pending invitation exists for this email/org combination
7. Invitation Service checks user is not already an organization member
8. Invitation Service generates secure invitation token (secrets.token_urlsafe(32))
9. Invitation Service creates invitation record with 7-day expiration
10. Invitation Service sends invitation email with acceptance link
11. Invitation Service publishes `invitation.sent` event to NATS
12. Returns invitation details with token to admin

**Outcome**: Invitation created, email sent, event published for audit tracking

### Scenario 2: View Invitation by Token
**Actor**: Invited User (via email link)
**Trigger**: User clicks invitation link in email
**Flow**:
1. User clicks `https://app.iapro.ai/accept-invitation?token={token}`
2. App frontend calls `GET /api/v1/invitations/{invitation_token}`
3. Invitation Service retrieves invitation by token
4. Invitation Service validates invitation status is PENDING
5. Invitation Service checks expiration date:
   - If expired: Updates status to EXPIRED, publishes `invitation.expired` event, returns error
   - If valid: Continues
6. Invitation Service fetches organization info for display
7. Returns InvitationDetailResponse with org name, inviter info, role
8. Frontend displays "Join {org_name} as {role}" confirmation page

**Outcome**: User sees invitation details before accepting

### Scenario 3: Accept Invitation
**Actor**: Authenticated Invited User
**Trigger**: User confirms invitation acceptance
**Flow**:
1. User (logged in) clicks "Accept Invitation" button
2. App calls `POST /api/v1/invitations/accept` with token and X-User-Id header
3. Invitation Service retrieves invitation by token
4. Invitation Service validates invitation is PENDING and not expired
5. Invitation Service verifies user email matches invitation email
6. Invitation Service updates invitation status to ACCEPTED with accepted_at timestamp
7. Invitation Service calls Organization Service to add user as member with assigned role
8. If member addition fails: Rolls back invitation status to PENDING
9. If successful: Publishes `invitation.accepted` event
10. Returns AcceptInvitationResponse with org name, role, accepted_at

**Outcome**: User added to organization, invitation closed, downstream services notified

### Scenario 4: Cancel Invitation
**Actor**: Inviter or Organization Admin
**Trigger**: Admin decides to revoke pending invitation
**Flow**:
1. Admin views organization pending invitations list
2. Admin clicks "Cancel" on specific invitation
3. App calls `DELETE /api/v1/invitations/{invitation_id}` with X-User-Id header
4. Invitation Service retrieves invitation by ID
5. Invitation Service validates:
   - Invitation exists
   - User is inviter OR user has admin/owner role in organization
6. Invitation Service updates invitation status to CANCELLED
7. Publishes `invitation.cancelled` event
8. Returns success confirmation

**Outcome**: Invitation revoked, cannot be accepted, event published for audit

### Scenario 5: Resend Invitation
**Actor**: Inviter or Organization Admin
**Trigger**: Original invitation email was lost or about to expire
**Flow**:
1. Admin views organization pending invitations list
2. Admin clicks "Resend" on specific invitation
3. App calls `POST /api/v1/invitations/{invitation_id}/resend` with X-User-Id header
4. Invitation Service retrieves invitation by ID
5. Invitation Service validates:
   - Invitation exists
   - Invitation status is PENDING
   - User is inviter OR user has admin/owner role
6. Invitation Service extends expiration by 7 days from now
7. Invitation Service sends new email with same token
8. Returns success confirmation

**Outcome**: Expiration extended, new email sent, original token still valid

### Scenario 6: List Organization Invitations
**Actor**: Organization Admin/Owner
**Trigger**: Admin wants to view all invitations for organization
**Flow**:
1. Admin navigates to organization invitations page
2. App calls `GET /api/v1/invitations/organizations/{org_id}?limit=100&offset=0`
3. Invitation Service validates user has admin/owner role in organization
4. Invitation Service queries all invitations for organization
5. Returns paginated InvitationListResponse with all statuses
6. Admin can filter by status (pending, accepted, expired, cancelled)

**Outcome**: Admin sees complete invitation history for organization

### Scenario 7: Expire Old Invitations (System Job)
**Actor**: System Scheduler
**Trigger**: Scheduled job runs periodically (e.g., daily)
**Flow**:
1. System calls `POST /api/v1/invitations/admin/expire-invitations`
2. Invitation Service queries all PENDING invitations where expires_at < now
3. Invitation Service bulk updates status to EXPIRED
4. Returns count of expired invitations
5. (Note: Individual expiration events not published for bulk operation)

**Outcome**: Stale invitations cleaned up, system hygiene maintained

### Scenario 8: Handle Organization Deleted Event
**Actor**: Organization Service (Event Publisher)
**Trigger**: Organization is deleted
**Flow**:
1. Organization Service publishes `organization.deleted` event
2. Invitation Service receives event via NATS subscription
3. Invitation Service identifies organization_id from event data
4. Invitation Service cancels all PENDING invitations for organization
5. Logs count of cancelled invitations

**Outcome**: Orphaned invitations automatically cleaned up

---

## Domain Events

### Published Events

#### 1. invitation.sent (EventType.INVITATION_SENT)
**Trigger**: After successful invitation creation and email dispatch
**Payload**:
- invitation_id: Unique invitation identifier
- organization_id: Target organization
- email: Invited person's email
- role: Assigned role (owner/admin/member/viewer/guest)
- invited_by: User ID who created invitation
- email_sent: Boolean indicating email delivery status
- timestamp: ISO 8601 event timestamp

**Subscribers**:
- **Audit Service**: Log invitation for compliance tracking
- **Analytics Service**: Track invitation metrics and conversion rates
- **Notification Service**: (Future) Send push notification to org admins

#### 2. invitation.expired (EventType.INVITATION_EXPIRED)
**Trigger**: When invitation is accessed after expiration or during bulk cleanup
**Payload**:
- invitation_id: Invitation identifier
- organization_id: Target organization
- email: Invited person's email
- expired_at: Expiration timestamp
- timestamp: ISO 8601 event timestamp

**Subscribers**:
- **Audit Service**: Log expiration for compliance
- **Analytics Service**: Track invitation expiration rates

#### 3. invitation.accepted (EventType.INVITATION_ACCEPTED)
**Trigger**: After user successfully accepts invitation and is added to organization
**Payload**:
- invitation_id: Invitation identifier
- organization_id: Organization joined
- user_id: User who accepted
- email: User's email
- role: Role assigned to user
- accepted_at: ISO 8601 acceptance timestamp
- timestamp: ISO 8601 event timestamp

**Subscribers**:
- **Organization Service**: (Confirmation) Member already added via sync call
- **Audit Service**: Log membership addition for compliance
- **Analytics Service**: Track conversion metrics
- **Notification Service**: Send welcome notification to new member
- **Billing Service**: (Future) Update organization seat count

#### 4. invitation.cancelled (EventType.INVITATION_CANCELLED)
**Trigger**: When inviter or admin cancels pending invitation
**Payload**:
- invitation_id: Invitation identifier
- organization_id: Target organization
- email: Invited person's email
- cancelled_by: User ID who cancelled
- timestamp: ISO 8601 event timestamp

**Subscribers**:
- **Audit Service**: Log cancellation for compliance
- **Analytics Service**: Track cancellation rates

### Subscribed Events

#### 1. organization.deleted
**Source**: organization_service
**Handler**: InvitationEventHandler.handle_organization_deleted()
**Purpose**: Cancel all pending invitations when organization is deleted

**Payload**:
- organization_id: Deleted organization ID

**Side Effects**:
- All PENDING invitations for organization set to CANCELLED
- Count of cancelled invitations logged

#### 2. user.deleted (EventType.USER_DELETED)
**Source**: account_service
**Handler**: InvitationEventHandler.handle_user_deleted()
**Purpose**: Cancel pending invitations sent by deleted user

**Payload**:
- user_id: Deleted user ID

**Side Effects**:
- All PENDING invitations where invited_by = user_id set to CANCELLED
- Count of cancelled invitations logged

---

## Core Concepts

### Invitation Lifecycle
1. **Creation**: Admin creates invitation → Status: PENDING
2. **Email Sent**: Invitation email dispatched with token link
3. **Viewed**: User clicks link, sees invitation details (no status change)
4. **Accepted**: User accepts → Status: ACCEPTED → Member added to org
5. **Expired**: Time passes expiration → Status: EXPIRED (on access or bulk job)
6. **Cancelled**: Admin revokes → Status: CANCELLED

### State Machine
```
                    ┌──────────────┐
                    │   PENDING    │
                    └──────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
    ┌──────────┐   ┌──────────┐   ┌───────────┐
    │ ACCEPTED │   │ EXPIRED  │   │ CANCELLED │
    └──────────┘   └──────────┘   └───────────┘

Transitions:
- PENDING → ACCEPTED: User accepts invitation
- PENDING → EXPIRED: Time expires (7 days)
- PENDING → CANCELLED: Admin cancels
```

### Security Model
- **Token Security**: 32-byte cryptographically random URL-safe tokens
- **Permission Validation**: Only org owner/admin can create invitations
- **Email Verification**: Accepting user's email must match invitation email
- **Expiration**: 7-day default expiration prevents stale invitations
- **Single Use**: Accepted invitations cannot be reused

### Separation of Concerns
**Invitation Service owns**:
- Invitation records and lifecycle
- Token generation and validation
- Expiration management
- Invitation-related events

**Invitation Service does NOT own**:
- Organization data (organization_service)
- User accounts (account_service)
- Membership records (organization_service)
- Email delivery (notification_service/external)
- Authentication (auth_service)

### Cross-Service Integration
- **Organization Service**: Verify org exists, check permissions, add members
- **Account Service**: (Future) Verify user email match
- **Notification Service**: (Future) Email delivery
- **Audit Service**: Compliance logging via events

---

## Business Rules (High-Level)

### Invitation Creation Rules
- **BR-INV-001**: Inviter must have owner or admin role in target organization
- **BR-INV-002**: Target organization must exist and be active
- **BR-INV-003**: Email must be valid format (contains '@')
- **BR-INV-004**: Email is normalized to lowercase
- **BR-INV-005**: Only one PENDING invitation per email/organization combination
- **BR-INV-006**: Invitation token is 32-byte URL-safe random string
- **BR-INV-007**: Default expiration is 7 days from creation
- **BR-INV-008**: Cannot invite user already in organization

### Token Rules
- **BR-TKN-001**: Token must be unique across all invitations
- **BR-TKN-002**: Token used for lookup, not invitation_id in public APIs
- **BR-TKN-003**: Token is case-sensitive
- **BR-TKN-004**: Token is URL-safe (no encoding required)

### Acceptance Rules
- **BR-ACC-001**: Only PENDING invitations can be accepted
- **BR-ACC-002**: Invitation must not be expired at acceptance time
- **BR-ACC-003**: Accepting user's email should match invitation email
- **BR-ACC-004**: Acceptance atomically updates status and adds member
- **BR-ACC-005**: If member addition fails, invitation remains PENDING (rollback)
- **BR-ACC-006**: Accepted invitations cannot be cancelled or reused

### Expiration Rules
- **BR-EXP-001**: PENDING invitations expire after 7 days
- **BR-EXP-002**: Expiration checked on token access, not proactively
- **BR-EXP-003**: Bulk expiration job updates status without individual events
- **BR-EXP-004**: Expired invitations cannot be accepted
- **BR-EXP-005**: Resending extends expiration by 7 days from current time

### Cancellation Rules
- **BR-CAN-001**: Only inviter or org owner/admin can cancel invitation
- **BR-CAN-002**: Only PENDING invitations can be cancelled
- **BR-CAN-003**: Cancelled invitations cannot be reactivated
- **BR-CAN-004**: Cancellation publishes event for audit trail

### Permission Rules
- **BR-PRM-001**: Organization existence verified via Organization Service
- **BR-PRM-002**: Inviter role verified via Organization Service members endpoint
- **BR-PRM-003**: Owner and admin roles have invite permission
- **BR-PRM-004**: Member, viewer, guest roles cannot invite
- **BR-PRM-005**: View invitation by token is public (no auth required)

### Role Assignment Rules
- **BR-ROL-001**: Valid roles: owner, admin, member, viewer, guest
- **BR-ROL-002**: Default role is 'member' if not specified
- **BR-ROL-003**: Role is assigned when member added to organization
- **BR-ROL-004**: Role changes after acceptance handled by Organization Service

### Email Rules
- **BR-EML-001**: Invitation email sent on creation (best effort)
- **BR-EML-002**: Email failure does not block invitation creation
- **BR-EML-003**: Email sent flag tracked for debugging
- **BR-EML-004**: Resend triggers new email with same token

### Event Publishing Rules
- **BR-EVT-001**: invitation.sent published after successful creation
- **BR-EVT-002**: invitation.accepted published after successful acceptance
- **BR-EVT-003**: invitation.cancelled published after cancellation
- **BR-EVT-004**: invitation.expired published on expiration detection
- **BR-EVT-005**: Event bus failure does not block operations
- **BR-EVT-006**: Events include full context for downstream processing

### Data Consistency Rules
- **BR-CON-001**: Invitation creation is atomic (PostgreSQL transaction)
- **BR-CON-002**: Acceptance update is atomic
- **BR-CON-003**: Status transitions are one-way (no reverting except rollback)
- **BR-CON-004**: Soft state - no hard deletes, cancelled invitations preserved

---

## Invitation Service in the Ecosystem

### Upstream Dependencies
- **Organization Service**: Verify organization, check permissions, add members
- **Account Service**: (Future) Verify user email match
- **PostgreSQL gRPC Service**: Persistent storage for invitation records
- **NATS Event Bus**: Event publishing infrastructure
- **Consul**: Service discovery and health checks
- **API Gateway**: Request routing and X-User-Id header

### Downstream Consumers
- **Organization Service**: Receives member addition request
- **Audit Service**: Compliance and change tracking via events
- **Analytics Service**: Invitation metrics and conversion tracking
- **Notification Service**: (Future) Email delivery and notifications

### Integration Patterns
- **Synchronous REST**: CRUD operations via FastAPI endpoints
- **Asynchronous Events**: NATS for real-time updates
- **Service Discovery**: Consul for dynamic Organization Service location
- **Protocol Buffers**: PostgreSQL gRPC communication
- **Health Checks**: `/health` and `/info` endpoints

### Dependency Injection
- **Repository Pattern**: InvitationRepository for data access
- **Protocol Interfaces**: (To be implemented) InvitationRepositoryProtocol
- **Factory Pattern**: (To be implemented) create_invitation_service()
- **Event Bus**: Injected via constructor for testability

---

## Success Metrics

### Invitation Quality Metrics
- **Invitation Conversion Rate**: accepted / (sent - cancelled) (target: >60%)
- **Expiration Rate**: expired / sent (target: <20%)
- **Cancellation Rate**: cancelled / sent (target: <10%)
- **Email Delivery Rate**: emails sent successfully / invitations created (target: >99%)

### Performance Metrics
- **Invitation Creation Latency**: Time to create invitation (target: <300ms)
- **Token Lookup Latency**: Time to fetch invitation by token (target: <100ms)
- **Acceptance Latency**: Time to accept and add member (target: <500ms)
- **List Query Latency**: Time for paginated list (target: <150ms)

### Availability Metrics
- **Service Uptime**: Invitation Service availability (target: 99.9%)
- **Database Connectivity**: PostgreSQL connection success rate (target: 99.99%)
- **Event Publishing Success**: % of events successfully published (target: >99.5%)
- **Organization Service Reachability**: Permission check success rate (target: >99.9%)

### Business Metrics
- **Daily Invitations Sent**: New invitations per day
- **Weekly Acceptances**: Invitations accepted per week
- **Average Time to Accept**: Mean time from invitation to acceptance
- **Organization Growth Rate**: Members added via invitation per month

### System Health Metrics
- **PostgreSQL Query Performance**: Average query execution time
- **NATS Event Throughput**: Events published per second
- **Token Generation Speed**: Time to generate secure token
- **Cross-Service Call Latency**: Time for Organization Service calls

---

## Glossary

**Invitation**: A time-limited offer to join an organization with a specific role
**Invitation Token**: Cryptographically secure string for invitation acceptance
**Organization Role**: Permission level assigned to organization members
**Inviter**: User who creates an invitation (must be owner/admin)
**Invitee**: Person receiving the invitation (identified by email)
**Pending**: Invitation awaiting acceptance (active state)
**Accepted**: Invitation completed, member added to organization
**Expired**: Invitation past its 7-day validity period
**Cancelled**: Invitation revoked before acceptance
**Email Verification**: Matching accepting user's email to invitation email
**Token Lookup**: Retrieving invitation by its secure token
**Invitation Link**: URL containing token for acceptance (e.g., https://app.iapro.ai/accept-invitation?token=xxx)
**Role Assignment**: Specifying member role during invitation creation
**Bulk Expiration**: System job that marks old PENDING invitations as EXPIRED
**Event Bus**: NATS messaging system for asynchronous event publishing
**Repository Pattern**: Data access abstraction layer
**Idempotent Check**: Preventing duplicate pending invitations for same email/org

---

**Document Version**: 1.0
**Last Updated**: 2025-12-19
**Maintained By**: Invitation Service Team
