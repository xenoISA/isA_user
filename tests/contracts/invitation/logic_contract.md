# Invitation Service Logic Contract

**Business Rules and Specifications for Invitation Service Testing**

All tests MUST verify these specifications. This is the SINGLE SOURCE OF TRUTH for invitation service behavior.

---

## Table of Contents

1. [Business Rules](#business-rules)
2. [State Machines](#state-machines)
3. [Edge Cases](#edge-cases)
4. [Data Consistency Rules](#data-consistency-rules)
5. [Integration Contracts](#integration-contracts)
6. [Error Handling Contracts](#error-handling-contracts)
7. [Performance SLAs](#performance-slas)

---

## Business Rules

### Invitation Creation Rules

### BR-CRE-001: Organization Existence Verification
**Given**: User requests to create invitation
**When**: POST /api/v1/invitations/organizations/{org_id} is called
**Then**:
- System MUST verify organization exists via Organization Service
- Call GET /api/v1/organizations/{org_id}
- If 404 returned: Reject with "Organization not found"
- If 200 returned: Continue with permission check

**Validation Rules**:
- `organization_id`: Required, non-empty string
- Must correspond to existing organization
- Organization must be active

**Edge Cases**:
- Empty organization_id → **ValidationError**
- Non-existent organization_id → **NotFoundError** ("Organization not found")
- Organization Service unavailable → **ServiceUnavailableError** (after retry)

---

### BR-CRE-002: Inviter Permission Verification
**Given**: Organization exists
**When**: User attempts to create invitation
**Then**:
- System MUST verify inviter has owner OR admin role
- Call GET /api/v1/organizations/{org_id}/members
- Find member with matching user_id
- Check if role in ['owner', 'admin']
- If not authorized: Reject with "You don't have permission to invite users"

**Permission Requirements**:
- `owner`: Full invite permission
- `admin`: Full invite permission
- `member`: NO invite permission
- `viewer`: NO invite permission
- `guest`: NO invite permission

**Implementation**:
```python
for member in members:
    if member['user_id'] == inviter_user_id:
        role = member.get('role', '').lower()
        return role in ['owner', 'admin']
return False
```

---

### BR-CRE-003: Duplicate Pending Invitation Prevention
**Given**: Inviter has permission to invite
**When**: Creating invitation for email/org combination
**Then**:
- System MUST check for existing PENDING invitation with same email AND organization_id
- If pending invitation exists: Reject with "A pending invitation already exists"
- EXPIRED, CANCELLED, or ACCEPTED invitations do NOT block new invitation

**Query**:
```sql
SELECT * FROM invitation.organization_invitations
WHERE email = $1 AND organization_id = $2 AND status = 'pending'
```

**Edge Cases**:
- Same email, same org, PENDING exists → **DuplicateError**
- Same email, same org, EXPIRED exists → Allow new invitation
- Same email, different org, PENDING exists → Allow new invitation

---

### BR-CRE-004: Existing Membership Check
**Given**: No duplicate pending invitation
**When**: Creating invitation
**Then**:
- System SHOULD verify user is not already a member of organization
- If already member: Reject with "User is already a member"
- Check via Organization Service members list

**Implementation**: (Future enhancement)
```python
# Check if email corresponds to existing member
for member in members:
    if member.get('email') == email:
        return False, None, "User is already a member"
```

---

### BR-CRE-005: Email Format Validation
**Given**: Invitation creation request with email
**When**: Email is validated
**Then**:
- Email MUST contain '@' character
- Email is normalized to lowercase
- Whitespace is trimmed before validation
- Invalid email format → **ValidationError** ("Invalid email format")

**Validation Rules**:
- Must contain '@': `'@' in email`
- Normalized: `email.lower().strip()`
- No empty strings
- No whitespace-only strings

**Edge Cases**:
- `user@domain.com` → Valid
- `userdomain.com` → **ValidationError** (no @)
- `` → **ValidationError** (empty)
- `   ` → **ValidationError** (whitespace only)
- `USER@DOMAIN.COM` → Valid, normalized to `user@domain.com`

---

### BR-CRE-006: Role Assignment Validation
**Given**: Invitation creation request with role
**When**: Role is validated
**Then**:
- Role MUST be one of: owner, admin, member, viewer, guest
- Default role is 'member' if not specified
- Invalid role → **ValidationError**

**Valid Roles**:
```python
class OrganizationRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"
    GUEST = "guest"
```

---

### BR-CRE-007: Secure Token Generation
**Given**: Invitation passes all validations
**When**: Invitation is created
**Then**:
- System MUST generate cryptographically secure token
- Token: 32-byte URL-safe random string
- Generated via `secrets.token_urlsafe(32)`
- Token is unique (database UNIQUE constraint)

**Token Properties**:
- Length: ~43 characters (base64url encoded 32 bytes)
- URL-safe: Can be used directly in URLs
- Cryptographically random: Unpredictable
- Unique: Database enforces uniqueness

**Implementation**:
```python
invitation_token = secrets.token_urlsafe(32)
```

---

### BR-CRE-008: Expiration Time Setting
**Given**: Invitation is created
**When**: expires_at is set
**Then**:
- Default expiration: 7 days from creation
- Timestamp in UTC
- Format: datetime with timezone

**Implementation**:
```python
expires_at = datetime.now(timezone.utc) + timedelta(days=7)
```

---

### BR-CRE-009: Message Length Limit
**Given**: Invitation creation with optional message
**When**: Message is provided
**Then**:
- Message MUST NOT exceed 500 characters
- Message is optional (can be None)
- Empty string is valid
- Message > 500 chars → **ValidationError**

**Validation**:
```python
message: Optional[str] = Field(None, max_length=500)
```

---

### BR-CRE-010: Event Publishing on Creation
**Given**: Invitation created successfully
**When**: Database transaction commits
**Then**:
- System MUST publish `invitation.sent` event
- Event includes: invitation_id, organization_id, email, role, invited_by, email_sent
- Event failure is logged but does not block operation

**Event Data**:
```json
{
  "invitation_id": "inv_xxx",
  "organization_id": "org_xxx",
  "email": "user@example.com",
  "role": "member",
  "invited_by": "usr_admin",
  "email_sent": true,
  "timestamp": "2025-12-19T10:00:00Z"
}
```

---

### Token Access Rules

### BR-TKN-001: Public Token Access
**Given**: User has invitation token (from email)
**When**: GET /api/v1/invitations/{token} is called
**Then**:
- No authentication required (token IS the authentication)
- Token is looked up in database
- Returns invitation details with org/inviter info
- Token not found → **NotFoundError** ("Invitation not found")

**Accessibility**:
- Anyone with valid token can view invitation details
- Token should be treated as sensitive (equivalent to a single-use password)

---

### BR-TKN-002: Status Validation on Access
**Given**: Token lookup succeeds
**When**: Invitation is retrieved
**Then**:
- Only PENDING invitations can be viewed for acceptance
- ACCEPTED → Return error "Invitation is accepted"
- EXPIRED → Return error "Invitation has expired"
- CANCELLED → Return error "Invitation is cancelled"

**Status Check**:
```python
if invitation.status != InvitationStatus.PENDING:
    return False, None, f"Invitation is {invitation.status}"
```

---

### BR-TKN-003: Expiration Detection on Access
**Given**: PENDING invitation retrieved
**When**: Current time is checked against expires_at
**Then**:
- If expires_at < now: Update status to EXPIRED
- Publish `invitation.expired` event
- Return error "Invitation has expired"

**Timezone Handling**:
```python
if expires_at.tzinfo is None:
    expires_at = expires_at.replace(tzinfo=timezone.utc)

if expires_at < datetime.now(timezone.utc):
    # Mark as expired
    await self.repository.update_invitation(invitation_id, {'status': 'expired'})
    await publish_invitation_expired(...)
    return False, None, "Invitation has expired"
```

---

### BR-TKN-004: Detail Response Enrichment
**Given**: Valid PENDING invitation accessed
**When**: Response is built
**Then**:
- Include organization_name (from org service or stored)
- Include organization_domain (if available)
- Include inviter_name (from user lookup or stored)
- Include inviter_email (from user lookup or stored)

**Response Fields**:
- invitation_id, organization_id, organization_name, organization_domain
- email, role, status
- inviter_name, inviter_email
- expires_at, created_at

---

### Acceptance Rules

### BR-ACC-001: Token Validation on Accept
**Given**: User calls POST /api/v1/invitations/accept
**When**: Request is processed
**Then**:
- Token MUST be valid and correspond to PENDING invitation
- Token not found → **NotFoundError**
- Token for non-PENDING invitation → **ValidationError**
- Token for expired invitation → **ValidationError** (after expiration update)

---

### BR-ACC-002: User Authentication Required
**Given**: Acceptance request received
**When**: X-User-Id header is checked
**Then**:
- User MUST be authenticated (X-User-Id header present)
- Missing header → **AuthenticationError** (401)
- User ID is used as the member to add to organization

---

### BR-ACC-003: Email Match Verification (Best Effort)
**Given**: Authenticated user accepts invitation
**When**: User's email is compared to invitation email
**Then**:
- System SHOULD verify user email matches invitation email
- If mismatch detected → Return error "Email mismatch"
- Comparison is case-insensitive
- This is best-effort (may not always block)

**Implementation**:
```python
async def _verify_user_email_match(self, user_id: str, invitation_email: str) -> bool:
    # Call account service to get user email
    # Compare with invitation_email (case-insensitive)
    return user_email.lower() == invitation_email.lower()
```

---

### BR-ACC-004: Atomic Status Update
**Given**: Acceptance validation passes
**When**: Invitation status is updated
**Then**:
- Status changed from PENDING to ACCEPTED
- accepted_at timestamp set to current UTC time
- updated_at timestamp updated
- Single database transaction

**SQL**:
```sql
UPDATE invitation.organization_invitations
SET status = 'accepted', accepted_at = $1, updated_at = $2
WHERE invitation_token = $3 AND status = 'pending'
```

---

### BR-ACC-005: Member Addition to Organization
**Given**: Invitation status updated to ACCEPTED
**When**: Member addition is attempted
**Then**:
- Call Organization Service POST /api/v1/organizations/{org_id}/members
- Include user_id, role from invitation
- Use inviter's permission context for authorization

**Request Body**:
```json
{
  "user_id": "usr_newmember",
  "role": "member",
  "permissions": []
}
```

---

### BR-ACC-006: Acceptance Rollback on Failure
**Given**: Invitation marked as ACCEPTED
**When**: Member addition to organization fails
**Then**:
- Rollback invitation status to PENDING
- Clear accepted_at timestamp
- Return error "Failed to add user to organization"
- User can retry acceptance later

**Rollback**:
```python
await self.repository.update_invitation(invitation_id, {
    'status': InvitationStatus.PENDING.value,
    'accepted_at': None
})
```

---

### BR-ACC-007: Event Publishing on Accept
**Given**: Acceptance succeeds (invitation + member addition)
**When**: Operation completes
**Then**:
- Publish `invitation.accepted` event
- Include: invitation_id, organization_id, user_id, email, role, accepted_at
- Event failure is logged but does not block

**Event Data**:
```json
{
  "invitation_id": "inv_xxx",
  "organization_id": "org_xxx",
  "user_id": "usr_newmember",
  "email": "user@example.com",
  "role": "member",
  "accepted_at": "2025-12-20T14:30:00Z",
  "timestamp": "2025-12-20T14:30:00Z"
}
```

---

### BR-ACC-008: Single-Use Token
**Given**: Invitation has been accepted
**When**: Same token used for acceptance again
**Then**:
- Status is ACCEPTED, not PENDING
- Return error "Invitation is accepted"
- Cannot be accepted twice

---

### Cancellation Rules

### BR-CAN-001: Cancellation Permission Check
**Given**: User requests to cancel invitation
**When**: DELETE /api/v1/invitations/{invitation_id} is called
**Then**:
- Verify requester is either:
  - The original inviter (invited_by == user_id)
  - An admin/owner of the organization
- If neither → Return error "You don't have permission to cancel"

**Permission Logic**:
```python
if invitation.invited_by != user_id:
    if not await self._verify_inviter_permissions(invitation.organization_id, user_id):
        return False, "You don't have permission to cancel this invitation"
```

---

### BR-CAN-002: Cancellation Status Check
**Given**: User has permission to cancel
**When**: Invitation status is checked
**Then**:
- Only PENDING invitations can be cancelled
- ACCEPTED invitations cannot be cancelled (member already added)
- EXPIRED invitations can be cancelled (but effectively no-op)
- CANCELLED invitations → Return success (idempotent)

**Valid Transitions**:
- PENDING → CANCELLED: Success
- CANCELLED → CANCELLED: Success (idempotent)
- ACCEPTED → CANCELLED: Error
- EXPIRED → CANCELLED: Success (cleanup)

---

### BR-CAN-003: Cancellation Event Publishing
**Given**: Invitation cancelled successfully
**When**: Status updated to CANCELLED
**Then**:
- Publish `invitation.cancelled` event
- Include: invitation_id, organization_id, email, cancelled_by
- cancelled_by is the user who cancelled (not original inviter)

**Event Data**:
```json
{
  "invitation_id": "inv_xxx",
  "organization_id": "org_xxx",
  "email": "user@example.com",
  "cancelled_by": "usr_admin",
  "timestamp": "2025-12-19T15:00:00Z"
}
```

---

### Resend Rules

### BR-RES-001: Resend Permission Check
**Given**: User requests to resend invitation
**When**: POST /api/v1/invitations/{invitation_id}/resend is called
**Then**:
- Same permission rules as cancellation
- Requester must be inviter OR org admin/owner

---

### BR-RES-002: Resend Status Check
**Given**: User has permission to resend
**When**: Invitation status is checked
**Then**:
- Only PENDING invitations can be resent
- ACCEPTED → Error "Cannot resend accepted invitation"
- EXPIRED → Error "Cannot resend expired invitation"
- CANCELLED → Error "Cannot resend cancelled invitation"

---

### BR-RES-003: Expiration Extension
**Given**: PENDING invitation being resent
**When**: Resend operation executes
**Then**:
- Extend expires_at by 7 days from current time
- Same token remains valid (not regenerated)
- Trigger email resend

**Update**:
```python
new_expires_at = datetime.now(timezone.utc) + timedelta(days=7)
await self.repository.update_invitation(invitation_id, {
    'expires_at': new_expires_at.isoformat()
})
```

---

### BR-RES-004: Email Resend Trigger
**Given**: Expiration extended
**When**: Email is sent
**Then**:
- Send invitation email with same token
- Email failure does not block operation
- Return message indicates email status

**Response**:
```json
{"message": "Invitation resent successfully"}
// or
{"message": "Invitation resent successfully (but email sending failed)"}
```

---

### List and Query Rules

### BR-LST-001: Organization Scope
**Given**: User requests invitation list
**When**: GET /api/v1/invitations/organizations/{org_id} is called
**Then**:
- Return only invitations for specified organization
- All statuses included (pending, accepted, expired, cancelled)
- Ordered by created_at DESC (newest first)

---

### BR-LST-002: Permission Check for List
**Given**: User requests invitation list
**When**: User's role is checked
**Then**:
- Only org owner/admin can view invitations
- Member/viewer/guest cannot list invitations
- Return error if insufficient permission

---

### BR-LST-003: Pagination Support
**Given**: List request with pagination params
**When**: Query is executed
**Then**:
- `limit`: Maximum results (default 100, max 1000)
- `offset`: Skip first N results (default 0)
- Return total count for pagination UI
- Limit and offset must be >= 0

**Query**:
```sql
SELECT * FROM invitation.organization_invitations
WHERE organization_id = $1
ORDER BY created_at DESC
LIMIT $2 OFFSET $3
```

---

### BR-LST-004: Status Filtering
**Given**: List request with status filter
**When**: status query param provided
**Then**:
- Filter by specific status (pending, accepted, expired, cancelled)
- No filter = return all statuses
- Invalid status → **ValidationError**

---

### Event Subscription Rules

### BR-SUB-001: Organization Deleted Handler
**Given**: `organization.deleted` event received
**When**: Event is processed
**Then**:
- Cancel all PENDING invitations for that organization
- Set status to CANCELLED
- Log count of cancelled invitations
- Idempotent: Safe to process same event twice

**Implementation**:
```python
async def handle_organization_deleted(self, event_data: Dict) -> bool:
    organization_id = event_data.get('organization_id')
    cancelled_count = await self.invitation_repo.cancel_organization_invitations(organization_id)
    logger.info(f"Cancelled {cancelled_count} invitations for org {organization_id}")
    return True
```

---

### BR-SUB-002: User Deleted Handler
**Given**: `user.deleted` event received
**When**: Event is processed
**Then**:
- Cancel all PENDING invitations where invited_by = deleted user_id
- Invitations TO the deleted user are NOT affected
- Log count of cancelled invitations

**Implementation**:
```python
async def handle_user_deleted(self, event_data: Dict) -> bool:
    user_id = event_data.get('user_id')
    cancelled_count = await self.invitation_repo.cancel_invitations_by_inviter(user_id)
    logger.info(f"Cancelled {cancelled_count} invitations sent by user {user_id}")
    return True
```

---

### Bulk Expiration Rules

### BR-EXP-001: Bulk Expire Old Invitations
**Given**: Admin calls POST /api/v1/invitations/admin/expire-invitations
**When**: Bulk expiration runs
**Then**:
- Find all PENDING invitations where expires_at < now
- Update status to EXPIRED
- Return count of expired invitations
- Do NOT publish individual expiration events (performance)

**SQL**:
```sql
UPDATE invitation.organization_invitations
SET status = 'expired', updated_at = CURRENT_TIMESTAMP
WHERE status = 'pending' AND expires_at < $1
```

---

### BR-EXP-002: Admin-Only Access
**Given**: Bulk expire endpoint
**When**: Request is received
**Then**:
- No user authentication required (internal admin endpoint)
- Should be protected at infrastructure level (internal network only)
- Used by scheduled jobs, not end users

---

## State Machines

### Invitation Lifecycle State Machine

```
                    ┌───────────────┐
                    │    PENDING    │ Initial state after creation
                    │  (7 day TTL)  │
                    └───────┬───────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
          ▼                 ▼                 ▼
    ┌──────────┐     ┌──────────┐     ┌───────────┐
    │ ACCEPTED │     │ EXPIRED  │     │ CANCELLED │
    │ (final)  │     │ (final)  │     │  (final)  │
    └──────────┘     └──────────┘     └───────────┘
```

**States**:
| State | Description | Entry Condition |
|-------|-------------|-----------------|
| PENDING | Active invitation awaiting response | Created by admin |
| ACCEPTED | User accepted, member added | User accepts via token |
| EXPIRED | Time limit exceeded | expires_at < now |
| CANCELLED | Revoked by admin/inviter | Admin/inviter cancels |

**Transitions**:
| From | To | Trigger | Conditions | Event Published |
|------|-----|---------|------------|-----------------|
| (new) | PENDING | create_invitation() | Permission check passed | invitation.sent |
| PENDING | ACCEPTED | accept_invitation() | Valid token, user authenticated | invitation.accepted |
| PENDING | EXPIRED | token_access() or bulk_expire() | expires_at < now | invitation.expired (on access only) |
| PENDING | CANCELLED | cancel_invitation() | Permission check passed | invitation.cancelled |

**Invariants**:
1. All final states (ACCEPTED, EXPIRED, CANCELLED) are terminal
2. No transitions out of terminal states
3. PENDING → PENDING via resend (only extends expiration)
4. All state changes update `updated_at` timestamp
5. ACCEPTED sets `accepted_at` timestamp

**Invalid Transitions**:
- ACCEPTED → any: Already accepted, member added
- EXPIRED → ACCEPTED: Cannot accept expired invitation
- EXPIRED → PENDING: Cannot reactivate expired (must create new)
- CANCELLED → any: Permanently revoked

---

### Invitation Creation Workflow State Machine

```
┌───────────────┐
│   INITIATED   │ Request received
└───────┬───────┘
        │
        ▼
┌───────────────┐     ┌───────────────┐
│  ORG_VERIFY   │────►│   REJECTED    │ Organization not found
└───────┬───────┘     └───────────────┘
        │ org exists
        ▼
┌───────────────┐     ┌───────────────┐
│  PERM_CHECK   │────►│   REJECTED    │ Not admin/owner
└───────┬───────┘     └───────────────┘
        │ has permission
        ▼
┌───────────────┐     ┌───────────────┐
│  DUP_CHECK    │────►│   REJECTED    │ Pending invitation exists
└───────┬───────┘     └───────────────┘
        │ no duplicate
        ▼
┌───────────────┐
│  TOKEN_GEN    │ Generate secure token
└───────┬───────┘
        │
        ▼
┌───────────────┐
│  DB_CREATE    │ Insert invitation record
└───────┬───────┘
        │
        ▼
┌───────────────┐
│  EMAIL_SEND   │ Send invitation email (best effort)
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ EVENT_PUBLISH │ Publish invitation.sent
└───────┬───────┘
        │
        ▼
┌───────────────┐
│   COMPLETED   │ Return invitation to caller
└───────────────┘
```

**Rejection Points**:
- Organization not found: 400 "Organization not found"
- Permission denied: 400 "You don't have permission to invite users"
- Duplicate exists: 400 "A pending invitation already exists"

---

### Invitation Acceptance Workflow State Machine

```
┌───────────────┐
│   INITIATED   │ Accept request received
└───────┬───────┘
        │
        ▼
┌───────────────┐     ┌───────────────┐
│ TOKEN_LOOKUP  │────►│   REJECTED    │ Token not found
└───────┬───────┘     └───────────────┘
        │ found
        ▼
┌───────────────┐     ┌───────────────┐
│ STATUS_CHECK  │────►│   REJECTED    │ Not PENDING
└───────┬───────┘     └───────────────┘
        │ is PENDING
        ▼
┌───────────────┐     ┌───────────────┐
│ EXPIRY_CHECK  │────►│   REJECTED    │ Expired (updates to EXPIRED)
└───────┬───────┘     └───────────────┘
        │ not expired
        ▼
┌───────────────┐     ┌───────────────┐
│ EMAIL_VERIFY  │────►│   REJECTED    │ Email mismatch
└───────┬───────┘     └───────────────┘
        │ matches (or skipped)
        ▼
┌───────────────┐
│ STATUS_UPDATE │ Update to ACCEPTED
└───────┬───────┘
        │
        ▼
┌───────────────┐     ┌───────────────┐
│ MEMBER_ADD    │────►│   ROLLBACK    │ Failed → revert to PENDING
└───────┬───────┘     └───────────────┘
        │ success
        ▼
┌───────────────┐
│ EVENT_PUBLISH │ Publish invitation.accepted
└───────┬───────┘
        │
        ▼
┌───────────────┐
│   COMPLETED   │ Return success response
└───────────────┘
```

**Rollback Point**:
- Member addition failure triggers rollback
- Invitation reverts to PENDING
- accepted_at is cleared
- User can retry later

---

## Edge Cases

### Token Edge Cases

### EC-TKN-001: Token Case Sensitivity
**Scenario**: Token lookup with different case
**Expected**:
- Tokens are case-sensitive
- `xK9mN2pQ7r...` ≠ `XK9MN2PQ7R...`
- Exact match required

**Implementation**: Direct string comparison in SQL

---

### EC-TKN-002: Token with Special Characters
**Scenario**: Token contains URL-encoded characters
**Expected**:
- Tokens are URL-safe (no encoding needed)
- `secrets.token_urlsafe` uses only safe characters
- No decoding should be necessary

**URL-Safe Alphabet**: `A-Za-z0-9-_`

---

### EC-TKN-003: Very Old Expired Invitation
**Scenario**: Access invitation expired months ago
**Expected**:
- Same handling as recently expired
- Update status to EXPIRED if still PENDING
- Return "Invitation has expired"
- No special handling for age

---

### EC-TKN-004: Token Reuse After Acceptance
**Scenario**: User tries to accept same token twice
**Expected**:
- First acceptance: Success
- Second attempt: "Invitation is accepted"
- No duplicate member addition
- Idempotent behavior

---

### Expiration Edge Cases

### EC-EXP-001: Expiration at Exact Boundary
**Scenario**: Access invitation exactly at expires_at timestamp
**Expected**:
- expires_at < now: Expired
- expires_at == now: Edge case, treat as expired
- expires_at > now: Valid

**Implementation**: Use `<` comparison (not `<=`)

---

### EC-EXP-002: Timezone Mismatch
**Scenario**: expires_at stored without timezone info
**Expected**:
- Assume UTC if no timezone
- Add timezone info before comparison
- All timestamps stored as UTC

**Fix**:
```python
if expires_at.tzinfo is None:
    expires_at = expires_at.replace(tzinfo=timezone.utc)
```

---

### EC-EXP-003: Resend Near Expiration
**Scenario**: Resend invitation that expires in 1 minute
**Expected**:
- Extend by 7 days from current time (not from old expires_at)
- New expires_at = now + 7 days
- Invitation becomes valid again

---

### EC-EXP-004: Accept During Expiration Check
**Scenario**: Invitation expires during acceptance flow
**Expected**:
- Expiration checked early in flow
- If expired during processing, fails gracefully
- Atomic status update prevents race

---

### Email Edge Cases

### EC-EML-001: Email Normalization
**Scenario**: Create invitation with "USER@DOMAIN.COM"
**Expected**:
- Normalized to "user@domain.com"
- Stored in lowercase
- Duplicate check uses lowercase comparison

---

### EC-EML-002: Email with Plus Sign
**Scenario**: Email "user+tag@example.com"
**Expected**:
- Valid email format
- Treated as distinct from "user@example.com"
- No plus-addressing normalization

---

### EC-EML-003: Unicode in Email
**Scenario**: Email with international characters
**Expected**:
- Internationalized emails accepted if valid
- Proper Unicode handling
- No truncation or corruption

---

### Permission Edge Cases

### EC-PRM-001: Inviter Removed from Organization
**Scenario**: Inviter removed from org after creating invitation
**Expected**:
- Existing invitation remains valid
- Invitation can still be accepted
- Cancel/resend checks current permissions (may fail)

---

### EC-PRM-002: Inviter Demoted to Member
**Scenario**: Admin demoted to member after creating invitation
**Expected**:
- Existing invitation remains valid
- Cannot cancel or resend (permission denied)
- Original inviter info preserved

---

### EC-PRM-003: Organization Role Changed
**Scenario**: Inviter's role changes during request processing
**Expected**:
- Permission checked at start of request
- Changes during processing don't affect current request
- Consistent within single request

---

### Concurrency Edge Cases

### EC-CON-001: Concurrent Accept Attempts
**Scenario**: Two users try to accept same invitation simultaneously
**Expected**:
- Only one succeeds
- Database status update is atomic
- WHERE status = 'pending' prevents double update
- Second attempt gets "Invitation is accepted"

---

### EC-CON-002: Accept and Cancel Race
**Scenario**: Accept and cancel requests arrive simultaneously
**Expected**:
- Whichever updates status first wins
- Loser gets appropriate error message
- No inconsistent state

---

### EC-CON-003: Concurrent Invitation Creation
**Scenario**: Two admins invite same email simultaneously
**Expected**:
- One succeeds, one fails
- Unique index on (org_id, email) WHERE status='pending' prevents duplicates
- Second gets "A pending invitation already exists"

---

### Organization Integration Edge Cases

### EC-ORG-001: Organization Service Timeout
**Scenario**: Organization Service doesn't respond within 5 seconds
**Expected**:
- Retry up to 3 times with exponential backoff
- After retries: Return 503 Service Unavailable
- Log timeout error

---

### EC-ORG-002: Organization Service Returns 500
**Scenario**: Organization Service has internal error
**Expected**:
- Retry with backoff
- After retries: Return 503
- Don't expose internal error details to user

---

### EC-ORG-003: Member Addition Partial Failure
**Scenario**: User added to org but event publish fails
**Expected**:
- User remains in organization
- Invitation marked as ACCEPTED
- Event failure logged
- Eventually consistent

---

## Data Consistency Rules

### ID Format Consistency

**Rule**: All IDs follow pattern `<entity>_<uuid_hex>`
- invitation_id: `inv_a1b2c3d4e5f6...`
- organization_id: `org_a1b2c3d4e5f6...`
- user_id: `usr_a1b2c3d4e5f6...`

**Generation**:
```python
invitation_id = f"inv_{uuid.uuid4().hex[:24]}"
```

**Properties**:
- Immutable after creation
- Globally unique
- URL-safe

---

### Token Consistency

**Rule**: Invitation tokens are secure random strings
- Length: 32 bytes → ~43 base64url characters
- Generation: `secrets.token_urlsafe(32)`
- Unique: Database UNIQUE constraint

**Storage**:
- Stored as-is (no hashing)
- Used for direct lookup
- Single-use for acceptance

---

### Timestamp Consistency

**Rule**: All timestamps in UTC
- `created_at`: Set once, immutable
- `updated_at`: Updated on every modification
- `expires_at`: Set on creation, extended on resend
- `accepted_at`: Set only when accepted

**Format**: PostgreSQL TIMESTAMP WITH TIME ZONE

**Precision**: Microseconds

---

### Email Consistency

**Rule**: Emails normalized to lowercase
- Stored: lowercase
- Comparison: case-insensitive via lowercase
- Whitespace: Trimmed before storage

---

### Status Consistency

**Rule**: Status transitions are one-way to terminal states
- PENDING: Only non-terminal state
- ACCEPTED, EXPIRED, CANCELLED: Terminal (no changes)
- No reverting from terminal states (except rollback on failure)

---

### Soft State

**Rule**: No hard deletes on invitations
- All invitations preserved for audit
- Status indicates current state
- Historical data retained

---

## Integration Contracts

### Organization Service Integration

**Base URL**: `http://organization_service:8212` (via Consul)

**Endpoints Used**:

#### GET /api/v1/organizations/{org_id}
**Purpose**: Verify organization exists
**Request**:
```http
GET /api/v1/organizations/org_xyz789
X-User-Id: usr_admin123
```
**Success Response** (200):
```json
{
  "organization_id": "org_xyz789",
  "name": "Acme Corp",
  "status": "active"
}
```
**Error Response** (404):
```json
{
  "detail": "Organization not found"
}
```

#### GET /api/v1/organizations/{org_id}/members
**Purpose**: Verify inviter permissions
**Request**:
```http
GET /api/v1/organizations/org_xyz789/members
X-User-Id: usr_admin123
```
**Success Response** (200):
```json
{
  "members": [
    {"user_id": "usr_admin123", "role": "admin", "email": "admin@acme.com"},
    {"user_id": "usr_member456", "role": "member", "email": "member@acme.com"}
  ]
}
```

#### POST /api/v1/organizations/{org_id}/members
**Purpose**: Add member on invitation acceptance
**Request**:
```http
POST /api/v1/organizations/org_xyz789/members
X-User-Id: usr_inviter123
Content-Type: application/json

{
  "user_id": "usr_newmember456",
  "role": "member",
  "permissions": []
}
```
**Success Response** (200):
```json
{
  "message": "Member added successfully"
}
```
**Error Response** (400):
```json
{
  "detail": "User is already a member"
}
```

**Error Handling**:
| Status | Action |
|--------|--------|
| 200 | Continue |
| 400 | Return error to user |
| 404 | Return "Organization not found" |
| 500 | Retry 3x, then 503 |
| Timeout (5s) | Retry 3x, then 503 |

---

### PostgreSQL gRPC Service Integration

**Service**: `postgres_grpc_service`
**Host**: `isa-postgres-grpc:50061` (via Consul)

**Schema**: `invitation`
**Table**: `organization_invitations`

**Connection**:
```python
self.db = AsyncPostgresClient(host=host, port=port, user_id="invitation_service")
```

**Query Format**: Parameterized with `$1`, `$2`, etc.

---

### NATS Event Bus Integration

**Connection**: `nats://isa-nats:4222`

**Published Events**:
| Subject | Event Type | Trigger |
|---------|------------|---------|
| `invitation.sent` | INVITATION_SENT | After invitation creation |
| `invitation.accepted` | INVITATION_ACCEPTED | After successful acceptance |
| `invitation.expired` | INVITATION_EXPIRED | On expiration detection |
| `invitation.cancelled` | INVITATION_CANCELLED | After cancellation |

**Subscribed Events**:
| Subject | Source | Handler |
|---------|--------|---------|
| `events.organization.deleted` | organization_service | Cancel pending invitations |
| `events.user.deleted` | account_service | Cancel invitations by inviter |

**Event Envelope**:
```python
Event(
    event_type=EventType.INVITATION_SENT,
    source=ServiceSource.INVITATION_SERVICE,
    data={...}
)
```

**Guarantees**:
- At-least-once delivery
- Retry on publish failure (logged, not blocking)
- Idempotent handlers

---

### Consul Service Discovery

**Service Registration**:
```python
ConsulRegistry(
    service_name="invitation_service",
    service_port=8213,
    tags=["api", "v1", "invitation"],
    health_check_type="http"
)
```

**Service Discovery**:
```python
host, port = config.discover_service(
    service_name='organization_service',
    default_host='localhost',
    default_port=8212
)
```

---

## Error Handling Contracts

### HTTP Status Code Mapping

| Error Type | HTTP Status | Error Code | Example |
|------------|-------------|------------|---------|
| ValidationError | 400 | VALIDATION_ERROR | Invalid email format |
| NotFoundError | 404 | NOT_FOUND | Invitation not found |
| DuplicateError | 400 | DUPLICATE | Pending invitation exists |
| PermissionError | 403 | FORBIDDEN | Not admin/owner |
| AuthenticationError | 401 | UNAUTHORIZED | Missing X-User-Id |
| StateError | 400 | INVALID_STATE | Cannot accept expired invitation |
| ServiceUnavailable | 503 | SERVICE_UNAVAILABLE | Org service down |
| InternalError | 500 | INTERNAL_ERROR | Unexpected failure |

---

### Error Response Format

**Standard Error**:
```json
{
  "detail": "Human-readable error message"
}
```

**Validation Error (Pydantic)**:
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

---

### Specific Error Messages

**Creation Errors**:
- "Organization not found"
- "You don't have permission to invite users"
- "A pending invitation already exists"
- "User is already a member"
- "Invalid email format"

**Token Access Errors**:
- "Invitation not found"
- "Invitation is accepted"
- "Invitation is cancelled"
- "Invitation has expired"

**Acceptance Errors**:
- "Invitation not found"
- "Invitation is not pending"
- "Invitation has expired"
- "Email mismatch"
- "Failed to add user to organization"

**Cancellation Errors**:
- "Invitation not found"
- "You don't have permission to cancel this invitation"
- "Cannot cancel accepted invitation"

**Resend Errors**:
- "Invitation not found"
- "You don't have permission to resend"
- "Cannot resend {status} invitation"

---

## Performance SLAs

### Response Time Targets (p95)

| Operation | Target | Max Acceptable |
|-----------|--------|----------------|
| Create invitation | < 300ms | < 1000ms |
| Get invitation by token | < 100ms | < 300ms |
| Accept invitation | < 500ms | < 1500ms |
| Cancel invitation | < 100ms | < 300ms |
| Resend invitation | < 200ms | < 500ms |
| List org invitations | < 150ms | < 500ms |
| Bulk expire | varies | < 10s for 1000 invitations |
| Health check | < 20ms | < 100ms |

**Notes**:
- Accept is slower due to Organization Service call
- Create includes email sending (best effort)
- Bulk expire scales with invitation count

---

### Throughput Targets

| Operation | Target (req/s) |
|-----------|----------------|
| Create invitation | 100 |
| Get invitation | 500 |
| Accept invitation | 50 |
| List invitations | 200 |
| Cancel/Resend | 100 |

---

### Resource Limits

| Resource | Limit |
|----------|-------|
| Max invitations per query | 1000 (limit param) |
| Max message length | 500 characters |
| Token length | 43 characters |
| Default expiration | 7 days |
| Max concurrent connections | 50 |
| Organization Service timeout | 5 seconds |
| Retry attempts | 3 |

---

## Test Coverage Requirements

All tests MUST cover:

- [ ] Happy path for all operations (create, get, accept, cancel, resend, list)
- [ ] Permission validation (admin/owner only)
- [ ] Status transitions (PENDING → ACCEPTED/EXPIRED/CANCELLED)
- [ ] Token security (unique, cryptographically random)
- [ ] Expiration handling (on access, bulk)
- [ ] Duplicate prevention (same email/org)
- [ ] Rollback on failure (member addition fails)
- [ ] Event publishing (sent, accepted, expired, cancelled)
- [ ] Event subscription handling (org.deleted, user.deleted)
- [ ] Edge cases (EC-XXX scenarios)
- [ ] Error responses (all error types)
- [ ] Cross-service integration (Organization Service)
- [ ] Pagination (limit/offset)
- [ ] Email normalization (lowercase)
- [ ] Concurrent operations (accept races)
- [ ] Performance within SLAs

---

**Version**: 1.0.0
**Last Updated**: 2025-12-19
**Owner**: Invitation Service Team
