# Organization Service Logic Contract

**Business Rules and Specifications for Organization Service Testing**

All tests MUST verify these specifications. This is the SINGLE SOURCE OF TRUTH for organization service behavior.

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

### Organization Creation Rules

### BR-ORG-001: Organization Name Required
**Given**: Valid organization creation request
**When**: Organization is created via create_organization
**Then**:
- Organization name must be provided
- Empty name → **OrganizationValidationError**
- Organization name stored as provided

**Validation Rules**:
- `name`: Required, non-empty string
- Length: 1-100 characters
- Must not contain only whitespace

**Edge Cases**:
- Empty name → **OrganizationValidationError**
- Whitespace-only name → **OrganizationValidationError**
- Name > 100 chars → **422 Validation Error** (Pydantic)

---

### BR-ORG-002: Billing Email Required
**Given**: Valid organization creation request
**When**: Organization is created
**Then**:
- Billing email must be provided
- Must be valid email format
- Billing email used for billing notifications

**Validation Rules**:
- `billing_email`: Required, valid email format
- Format: `^[^\s@]+@[^\s@]+\.[^\s@]+$`
- No whitespace characters allowed

**Edge Cases**:
- Empty billing_email → **OrganizationValidationError**
- Invalid email format → **OrganizationValidationError**
- Email with spaces → **OrganizationValidationError**

---

### BR-ORG-003: Creator Becomes Owner
**Given**: New organization creation
**When**: Organization is created successfully
**Then**:
- Creator is automatically added as owner
- Owner has full control of organization
- Owner membership status is ACTIVE
- Cannot have organization without owner

**Implementation**:
```python
await self.repository.create_organization(
    request.model_dump(exclude_none=True),
    owner_user_id
)
```

---

### BR-ORG-004: Default Values on Creation
**Given**: New organization creation
**When**: Organization is created
**Then**:
- `status` = `active` (always)
- `plan` = `free` (default unless specified)
- `credits_pool` = 0 (default)
- `max_members` = plan-based limit
- `settings` = `{}` (empty dict)
- `created_at` = current timestamp (UTC)
- `updated_at` = current timestamp (UTC)

**Default Values**:
```python
{
    "status": "active",
    "plan": "free",
    "credits_pool": 0,
    "max_members": 5,
    "settings": {},
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc)
}
```

---

### BR-ORG-005: Organization Type Immutable
**Given**: Existing organization
**When**: Organization update is attempted
**Then**:
- Organization type cannot be changed after creation
- Type field is immutable
- Update requests with type field ignored or rejected

**Organization Types**:
- `business`: Business organization
- `family`: Family group
- `team`: Team structure
- `enterprise`: Enterprise organization

---

### Organization Update Rules

### BR-UPD-001: Admin-Only Updates
**Given**: Organization update request
**When**: User attempts to update organization
**Then**:
- Only owners and admins can update organization
- Members and guests cannot update
- Non-member users → **OrganizationAccessDeniedError**

**Permission Check**:
```python
is_admin = await self.check_admin_access(organization_id, user_id)
if not is_admin:
    raise OrganizationAccessDeniedError(...)
```

---

### BR-UPD-002: Updated Fields Tracking
**Given**: Organization update succeeds
**When**: organization.updated event is published
**Then**:
- Event includes `updated_fields` list
- Contains only fields that were actually updated
- Example: `["name", "billing_email"]`
- Used for audit trail and downstream subscribers

**Event Data**:
```json
{
  "organization_id": "org_123",
  "organization_name": "New Name",
  "updated_by": "user_123",
  "updated_fields": ["name", "billing_email"],
  "timestamp": "2025-12-15T10:00:00Z"
}
```

---

### BR-UPD-003: Updated_at Timestamp Management
**Given**: Any organization update operation
**When**: Update is saved to database
**Then**:
- `updated_at` automatically set to current UTC timestamp
- Happens for: organization updates, member changes, settings changes
- Always uses `datetime.now(timezone.utc)`

---

### Organization Deletion Rules

### BR-DEL-001: Owner-Only Deletion
**Given**: Organization deletion request
**When**: User attempts to delete organization
**Then**:
- Only owners can delete organization
- Admins cannot delete organization
- Non-owners → **OrganizationAccessDeniedError**

**Permission Check**:
```python
is_owner = await self.check_owner_access(organization_id, user_id)
if not is_owner:
    raise OrganizationAccessDeniedError(...)
```

---

### BR-DEL-002: Soft Delete Behavior
**Given**: Organization deletion request
**When**: delete_organization is called
**Then**:
- Organization is NOT removed from database
- `status` set to `deleted` (soft delete)
- Organization data preserved for audit/recovery
- All members removed from organization

---

### BR-DEL-003: Event Publishing on Deletion
**Given**: Organization deletion succeeds
**When**: organization.deleted event published
**Then**:
- Event includes organization_id, name, deleted_by
- Downstream services receive notification
- Storage Service archives organization data
- Billing Service closes billing profile
- All shared resources are revoked

---

### Member Management Rules

### BR-MEM-001: Admin-Only Member Addition
**Given**: Member addition request
**When**: User attempts to add member
**Then**:
- Only owners and admins can add members
- Members and guests cannot add others
- Non-admin → **OrganizationAccessDeniedError**

**Validation Rules**:
- Requesting user must be owner or admin
- Either user_id or email must be provided
- Target user must exist (for user_id)

---

### BR-MEM-002: User ID or Email Required
**Given**: Member addition request
**When**: Request is validated
**Then**:
- Either `user_id` or `email` must be provided
- Both empty → **OrganizationValidationError**
- Email-only invitations → (Not implemented yet)

**Validation**:
```python
if not request.user_id and not request.email:
    raise OrganizationValidationError("Either user_id or email must be provided")
```

---

### BR-MEM-003: Member Limit Enforcement
**Given**: Member addition request
**When**: Organization member limit is checked
**Then**:
- Members cannot exceed organization's max_members
- Plan determines max_members limit
- Exceeding limit → **OrganizationValidationError**

**Plan Limits**:
- `free`: 5 members
- `family`: 6 members
- `team`: 25 members
- `enterprise`: unlimited

---

### BR-MEM-004: Duplicate Member Prevention
**Given**: Member addition request
**When**: User is already a member
**Then**:
- Duplicate addition is prevented
- Existing membership returned (idempotent)
- No error thrown for duplicate

---

### BR-MEM-005: Role Assignment on Addition
**Given**: Member addition with role
**When**: Member is added
**Then**:
- Role assigned as specified
- Default role is `member` if not specified
- Valid roles: owner, admin, member, guest

**Role Hierarchy**:
1. **owner**: Full control, can delete organization
2. **admin**: Can manage members and settings
3. **member**: Standard access to shared resources
4. **guest**: Limited read-only access

---

### BR-MEM-006: Event Publishing on Member Addition
**Given**: Member addition succeeds
**When**: organization.member_added event published
**Then**:
- Event includes user_id, role, added_by, permissions
- Account Service updates user's organization list
- Notification Service sends welcome notification

**Event Data**:
```json
{
  "organization_id": "org_123",
  "user_id": "user_456",
  "role": "member",
  "added_by": "user_123",
  "permissions": [],
  "timestamp": "2025-12-15T10:00:00Z"
}
```

---

### Member Update Rules

### BR-MUP-001: Admin Role Restrictions
**Given**: Member update request by admin
**When**: Admin attempts to modify member
**Then**:
- Admins cannot modify owners
- Admins cannot modify other admins
- Admins can only modify members and guests
- Violation → **OrganizationAccessDeniedError**

**Validation**:
```python
if requesting_role['role'] == 'admin' and target_role['role'] in ['owner', 'admin']:
    raise OrganizationAccessDeniedError("Admins cannot modify owners or other admins")
```

---

### BR-MUP-002: Owner Can Modify Anyone
**Given**: Member update request by owner
**When**: Owner modifies any member
**Then**:
- Owners can modify any member's role
- Owners can modify admin roles
- Owners cannot demote themselves (last owner rule)

---

### BR-MUP-003: Role Change Validation
**Given**: Role change request
**When**: Role is updated
**Then**:
- Only valid roles accepted
- Cannot promote to role higher than self (except owner)
- Role changes are immediate and broadcast

---

### Member Removal Rules

### BR-MRM-001: Admin Removal Restrictions
**Given**: Member removal request by admin
**When**: Admin attempts to remove member
**Then**:
- Admins cannot remove owners
- Admins cannot remove other admins
- Admins can only remove members and guests
- Violation → **OrganizationAccessDeniedError**

**Validation**:
```python
if requesting_role['role'] == 'admin':
    if target_role['role'] in ['owner', 'admin']:
        raise OrganizationAccessDeniedError("Admins cannot remove owners or other admins")
```

---

### BR-MRM-002: Owner Removal Restrictions
**Given**: Owner removal request
**When**: Attempting to remove last owner
**Then**:
- Cannot remove the last owner
- Organization must have at least one owner
- Last owner removal → **OrganizationValidationError**

**Validation**:
```python
if target_role['role'] == 'owner':
    members = await self.repository.get_organization_members(
        organization_id, role_filter=OrganizationRole.OWNER
    )
    if len(members) <= 1:
        raise OrganizationValidationError("Cannot remove the last owner from organization")
```

---

### BR-MRM-003: Self-Removal by Members
**Given**: Member removal request by non-admin
**When**: Member attempts to remove someone
**Then**:
- Members can only remove themselves
- Cannot remove other members
- Violation → **OrganizationAccessDeniedError**

---

### BR-MRM-004: Event Publishing on Removal
**Given**: Member removal succeeds
**When**: organization.member_removed event published
**Then**:
- Event includes user_id, removed_by
- Account Service updates user's organization list
- Session Service invalidates member sessions
- Storage Service revokes file access

---

### Context Switching Rules

### BR-CTX-001: Active Membership Required
**Given**: Context switch request
**When**: User switches to organization context
**Then**:
- User must be member of organization
- Membership status must be ACTIVE
- Inactive/suspended membership → **OrganizationAccessDeniedError**

**Validation**:
```python
role_data = await self.repository.get_user_organization_role(organization_id, user_id)
if not role_data:
    raise OrganizationAccessDeniedError(...)
if role_data['status'] != MemberStatus.ACTIVE.value:
    raise OrganizationAccessDeniedError("User membership is not active")
```

---

### BR-CTX-002: Personal Context Default
**Given**: Context switch without organization_id
**When**: User switches context
**Then**:
- Returns personal/individual context
- No organization_id in response
- Empty permissions list
- No credits_available

**Response**:
```python
OrganizationContextResponse(
    context_type="individual",
    organization_id=None,
    organization_name=None,
    user_role=None,
    permissions=[],
    credits_available=None
)
```

---

### BR-CTX-003: Organization Context Response
**Given**: Valid context switch to organization
**When**: Context is retrieved
**Then**:
- Returns organization context details
- Includes user's role and permissions
- Includes available credits

**Response**:
```python
OrganizationContextResponse(
    context_type="organization",
    organization_id=organization_id,
    organization_name=org.name,
    user_role=role_data['role'],
    permissions=role_data['permissions'],
    credits_available=org.credits_pool
)
```

---

### Access Control Rules

### BR-ACC-001: Internal Service Bypass
**Given**: Request with user_id="internal-service"
**When**: Access is checked
**Then**:
- Internal service calls bypass permission checks
- Used for service-to-service communication
- No access denied for internal services

**Check**:
```python
if user_id != "internal-service":
    has_access = await self.check_user_access(organization_id, user_id)
    if not has_access:
        raise OrganizationAccessDeniedError(...)
```

---

### BR-ACC-002: Member Access Validation
**Given**: Organization access request
**When**: User access is checked
**Then**:
- User must be organization member
- Membership status must be ACTIVE
- Returns True only if both conditions met

**Implementation**:
```python
async def check_user_access(self, organization_id: str, user_id: str) -> bool:
    role_data = await self.repository.get_user_organization_role(organization_id, user_id)
    return role_data is not None and role_data['status'] == MemberStatus.ACTIVE.value
```

---

### BR-ACC-003: Admin Access Validation
**Given**: Admin operation request
**When**: Admin access is checked
**Then**:
- User must be owner or admin
- Membership status must be ACTIVE
- Returns True only if both conditions met

---

### BR-ACC-004: Owner Access Validation
**Given**: Owner-only operation request
**When**: Owner access is checked
**Then**:
- User must be owner (not admin)
- Membership status must be ACTIVE
- Used for delete operations

---

### Family Sharing Rules

### BR-FSH-001: Admin-Only Sharing Creation
**Given**: Sharing creation request
**When**: User creates sharing
**Then**:
- Only admins/owners can create sharing
- Non-admin → **SharingAccessDeniedError**
- Sharing creator has full control

---

### BR-FSH-002: Resource Type Validation
**Given**: Sharing creation request
**When**: Resource type is validated
**Then**:
- Must be valid resource type
- Types: subscription, device, storage, wallet, album, media_library, calendar, location
- Invalid type → **ValidationError**

---

### BR-FSH-003: Share With All Members Option
**Given**: Sharing with share_with_all_members=true
**When**: Sharing is created
**Then**:
- All current organization members receive permission
- Uses default_permission for all members
- New members added later need manual permission

---

### BR-FSH-004: Custom Permissions Override
**Given**: Sharing with custom_permissions dict
**When**: Member permissions are assigned
**Then**:
- Custom permissions override default
- Per-member permission levels supported
- Unspecified members get default_permission

---

### BR-FSH-005: Permission Level Hierarchy
**Given**: Sharing permission levels
**When**: Access is determined
**Then**:
- Hierarchical permission model
- owner > admin > full_access > read_write > read_only
- Higher level includes lower level access

**Permission Levels**:
1. **owner**: Full control including deletion
2. **admin**: Can modify sharing settings
3. **full_access**: Read, write, and share
4. **read_write**: Read and write access
5. **read_only**: Read-only access

---

### BR-FSH-006: Quota Settings Support
**Given**: Sharing with quota_settings
**When**: Sharing is created
**Then**:
- Quota limits enforced per sharing
- Individual member quotas supported
- Exceeding quota → **SharingQuotaExceededError**

---

### BR-FSH-007: Sharing Expiration
**Given**: Sharing with expires_at
**When**: Expiration time is reached
**Then**:
- Sharing status changes to expired
- Access automatically revoked
- Event published for cleanup

---

### BR-FSH-008: Sharing Status Transitions
**Given**: Sharing status update
**When**: Status is changed
**Then**:
- Valid statuses: active, paused, expired, revoked
- Paused sharing retains permissions but blocks access
- Revoked sharing cannot be reactivated

---

### BR-FSH-009: Creator Always Has Access
**Given**: Sharing access check
**When**: Creator accesses sharing
**Then**:
- Creator always has access regardless of permissions
- Cannot revoke creator's own access
- Creator can delete sharing

---

### BR-FSH-010: Event Publishing on Sharing
**Given**: Sharing operation succeeds
**When**: family.resource_shared event published
**Then**:
- Event includes sharing details
- Downstream services update access
- Notification Service notifies members

**Event Data**:
```json
{
  "sharing_id": "share_123",
  "organization_id": "org_123",
  "resource_type": "device",
  "resource_id": "device_456",
  "resource_name": "Smart Frame",
  "created_by": "user_123",
  "share_with_all_members": true,
  "default_permission": "read_write",
  "shared_with_count": 5,
  "timestamp": "2025-12-15T10:00:00Z"
}
```

---

### Event Publishing Rules

### BR-EVT-001: All Mutations Publish Events
**Given**: Any organization mutation operation
**When**: Operation succeeds
**Then**:
- Event published to NATS
- Event type matches operation
- Event contains full context data

**Events Published**:
- `organization.created` → After create_organization
- `organization.updated` → After update_organization
- `organization.deleted` → After delete_organization
- `organization.member_added` → After add_organization_member
- `organization.member_removed` → After remove_organization_member
- `family.resource_shared` → After create_sharing

---

### BR-EVT-002: Event Failures Don't Block Operations
**Given**: Organization operation succeeds
**When**: Event publishing fails
**Then**:
- Operation completes successfully
- Error logged but not raised
- Response returned to client
- Event failure doesn't rollback transaction

**Implementation**:
```python
try:
    await self.event_bus.publish_event(event)
except Exception as e:
    logger.error(f"Failed to publish event: {e}")
    # Don't raise - event publishing is best-effort
```

---

### BR-EVT-003: ISO 8601 Timestamps
**Given**: Event published
**When**: Event data includes timestamps
**Then**:
- All timestamps in ISO 8601 format
- UTC timezone
- Generated by `datetime.now(timezone.utc).isoformat()`

**Format**: `2025-12-15T10:00:00Z`

---

## State Machines

### Organization Lifecycle State Machine

```
┌─────────┐
│   NEW   │ Organization creation initiated
└────┬────┘
     │
     ▼
┌─────────┐
│ ACTIVE  │ Organization active and operational
└────┬────┘
     │
     ├────► SUSPENDED  (payment issues, policy violation)
     │
     └────► DELETED    (soft delete by owner)

From SUSPENDED:
     │
     ├────► ACTIVE     (reactivated by admin/payment)
     │
     └────► DELETED    (deleted while suspended)

From DELETED:
     │
     └────► (Terminal state - no recovery)
```

**States**:
- **NEW**: Temporary state during organization creation (not persisted)
- **ACTIVE**: Organization is active, normal operations
- **SUSPENDED**: Organization temporarily disabled
- **DELETED**: Organization soft-deleted, marked for cleanup

**Valid Transitions**:
- `NEW` → `ACTIVE` (organization creation)
- `ACTIVE` → `SUSPENDED` (suspension)
- `ACTIVE` → `DELETED` (deletion)
- `SUSPENDED` → `ACTIVE` (reactivation)
- `SUSPENDED` → `DELETED` (deletion while suspended)

**Invalid Transitions**:
- `DELETED` → any state (terminal)
- `ACTIVE` → `NEW` (invalid)

**Transition Triggers**:
- `create_organization()` → NEW → ACTIVE
- `suspend_organization()` → ACTIVE → SUSPENDED
- `reactivate_organization()` → SUSPENDED → ACTIVE
- `delete_organization()` → ACTIVE/SUSPENDED → DELETED

---

### Member Lifecycle State Machine

```
┌─────────┐
│ PENDING │ Member invited, awaiting acceptance
└────┬────┘
     │
     ▼
┌─────────┐
│ ACTIVE  │ Member active in organization
└────┬────┘
     │
     ├────► SUSPENDED  (suspended by admin)
     │
     └────► REMOVED    (removed by admin or self)

From SUSPENDED:
     │
     ├────► ACTIVE     (reactivated by admin)
     │
     └────► REMOVED    (removed while suspended)

From PENDING:
     │
     ├────► ACTIVE     (invitation accepted)
     │
     └────► REMOVED    (invitation declined/expired)
```

**States**:
- **PENDING**: Member invited but not yet accepted
- **ACTIVE**: Member active with full access
- **SUSPENDED**: Member temporarily suspended
- **REMOVED**: Member removed from organization

**Valid Transitions**:
- `PENDING` → `ACTIVE` (invitation accepted)
- `PENDING` → `REMOVED` (invitation declined)
- `ACTIVE` → `SUSPENDED` (member suspended)
- `ACTIVE` → `REMOVED` (member removed)
- `SUSPENDED` → `ACTIVE` (member reactivated)
- `SUSPENDED` → `REMOVED` (member removed)

---

### Sharing Resource State Machine

```
┌─────────┐
│ CREATED │ Sharing resource created
└────┬────┘
     │
     ▼
┌─────────┐
│ ACTIVE  │ Sharing active, members can access
└────┬────┘
     │
     ├────► PAUSED     (temporarily disabled)
     │
     ├────► EXPIRED    (expiration time reached)
     │
     └────► REVOKED    (permanently revoked)

From PAUSED:
     │
     ├────► ACTIVE     (resumed)
     │
     └────► REVOKED    (revoked while paused)

From EXPIRED:
     │
     └────► REVOKED    (cleanup after expiration)
```

**States**:
- **CREATED**: Temporary state during creation
- **ACTIVE**: Sharing active and accessible
- **PAUSED**: Sharing temporarily disabled
- **EXPIRED**: Sharing expired automatically
- **REVOKED**: Sharing permanently revoked

**Valid Transitions**:
- `CREATED` → `ACTIVE` (creation complete)
- `ACTIVE` → `PAUSED` (admin pause)
- `ACTIVE` → `EXPIRED` (time-based expiration)
- `ACTIVE` → `REVOKED` (admin revoke)
- `PAUSED` → `ACTIVE` (admin resume)
- `PAUSED` → `REVOKED` (admin revoke)
- `EXPIRED` → `REVOKED` (cleanup)

**Invalid Transitions**:
- `REVOKED` → any state (terminal)
- `EXPIRED` → `ACTIVE` (cannot reactivate expired)

---

### Member Role State Machine

```
┌─────────┐
│  GUEST  │ Lowest privilege level
└────┬────┘
     │
     ▼
┌─────────┐
│ MEMBER  │ Standard access level
└────┬────┘
     │
     ▼
┌─────────┐
│  ADMIN  │ Management access level
└────┬────┘
     │
     ▼
┌─────────┐
│  OWNER  │ Highest privilege level
└─────────┘
```

**Roles (ascending privilege)**:
- **GUEST**: Read-only access
- **MEMBER**: Standard access
- **ADMIN**: Management access
- **OWNER**: Full control

**Valid Promotions**:
- `GUEST` → `MEMBER` (by admin/owner)
- `MEMBER` → `ADMIN` (by owner only)
- `ADMIN` → `OWNER` (by owner only)

**Valid Demotions**:
- `OWNER` → `ADMIN` (by owner, if not last owner)
- `ADMIN` → `MEMBER` (by owner)
- `MEMBER` → `GUEST` (by admin/owner)

**Rules**:
- Admins cannot promote to admin or owner
- Admins cannot demote other admins
- Must have at least one owner

---

## Edge Cases

### Member Management Edge Cases

### EC-001: Add Member Who Is Already Member
**Scenario**: add_organization_member called for existing member
**Expected**:
- Idempotent operation
- Returns existing membership
- No duplicate records created
- No error thrown

---

### EC-002: Remove Last Owner
**Scenario**: remove_organization_member called for the only owner
**Expected**:
- **OrganizationValidationError** raised
- Error message: "Cannot remove the last owner from organization"
- Owner remains in organization
- No state change

---

### EC-003: Admin Tries to Modify Owner
**Scenario**: Admin attempts to update or remove owner
**Expected**:
- **OrganizationAccessDeniedError** raised
- Error message: "Admins cannot modify owners or other admins"
- No state change

---

### EC-004: Member Tries to Remove Another Member
**Scenario**: Non-admin member tries to remove different member
**Expected**:
- **OrganizationAccessDeniedError** raised
- Error message: "Members can only remove themselves"
- No state change

---

### EC-005: Self-Removal by Member
**Scenario**: Member removes themselves from organization
**Expected**:
- Operation succeeds
- Member removed from organization
- Event published
- User can rejoin if invited again

---

### Organization Access Edge Cases

### EC-006: Access Organization Without Membership
**Scenario**: User tries to access organization they're not member of
**Expected**:
- **OrganizationAccessDeniedError** raised
- Error message: "User does not have access to organization"
- No data returned

---

### EC-007: Access Organization with Suspended Membership
**Scenario**: User with suspended status tries to access organization
**Expected**:
- **OrganizationAccessDeniedError** raised
- Error message: "User membership is not active"
- Access denied despite being a member

---

### EC-008: Context Switch to Non-Existent Organization
**Scenario**: switch_user_context with invalid organization_id
**Expected**:
- **OrganizationNotFoundError** raised
- Error message: "Organization not found"
- No context change

---

### Family Sharing Edge Cases

### EC-009: Share Resource to Non-Member
**Scenario**: Creating sharing with user who is not organization member
**Expected**:
- Permission created but user cannot access
- Access check fails at runtime
- Warning logged

---

### EC-010: Access Revoked Sharing
**Scenario**: User tries to access sharing with revoked status
**Expected**:
- **SharingAccessDeniedError** raised
- No access granted
- Status checked before access

---

### EC-011: Share With All Members Then Add New Member
**Scenario**: Sharing created with share_with_all_members=true, then new member added
**Expected**:
- New member does NOT automatically get access
- Must manually add permission for new member
- Or create new sharing

---

### EC-012: Delete Organization With Active Sharings
**Scenario**: Owner deletes organization that has active sharings
**Expected**:
- Organization deleted (soft delete)
- All sharings become inaccessible
- Events published for cleanup
- Downstream services revoke access

---

### Concurrent Operation Edge Cases

### EC-013: Concurrent Member Addition
**Scenario**: Two admins add same member simultaneously
**Expected**:
- Only one membership created
- Database constraint prevents duplicates
- One request succeeds, other returns existing

---

### EC-014: Concurrent Organization Updates
**Scenario**: Two admins update organization simultaneously
**Expected**:
- Last write wins
- Both updates applied (different fields)
- Conflicting field: last update wins

---

### EC-015: Delete While Updating
**Scenario**: Owner deletes organization while admin updates it
**Expected**:
- Delete operation takes precedence
- Update may fail with NotFoundError
- Organization ends up deleted

---

## Data Consistency Rules

### Transaction Boundaries

**Rule**: Each repository method operates in its own transaction
- `create_organization`: Single transaction (create org + add owner)
- `add_organization_member`: Single transaction (add member)
- `remove_organization_member`: Single transaction (remove member)
- `create_sharing`: Multiple operations (create sharing + permissions)

**Implementation**:
```python
async with self.db:
    await self.db.execute(...)
```

---

### Concurrent Update Handling

**Rule**: Last write wins (no optimistic locking)
- No version tracking on Organization model
- Concurrent updates to different fields: Both succeed
- Concurrent updates to same field: Last update wins
- No conflict detection

---

### Membership Uniqueness

**Rule**: User can only have one membership per organization
- Database constraint on (organization_id, user_id)
- Duplicate add returns existing membership
- No duplicate memberships possible

---

### Owner Invariant

**Rule**: Organization must always have at least one owner
- Enforced at remove_organization_member
- Cannot demote last owner
- Cannot remove last owner
- Validation before any owner modification

---

### Soft Delete Data Preservation

**Rule**: Soft deleted organizations preserve all data
- `status` set to `deleted`
- All fields preserved
- Members marked as removed
- Sharings become inaccessible

---

### Event Ordering

**Rule**: Events published after database commit
- Database operation completes first
- Event publishing is best-effort
- Event failure doesn't rollback database
- Events may be lost in failure scenarios

---

## Integration Contracts

### PostgreSQL gRPC Service

**Expectations**:
- Service name: `postgres_grpc_service`
- Default host: `isa-postgres-grpc`
- Default port: `50061`
- Protocol: gRPC with AsyncPostgresClient
- Schema: `organization`
- Tables: `organization.organizations`, `organization.organization_members`, `organization.family_sharing_resources`, `organization.member_sharing_permissions`

**Connection**:
```python
self.db = AsyncPostgresClient(host=host, port=port, user_id='organization_service')
```

**Query Format**:
- Parameterized queries with `$1`, `$2`, etc.
- JSONB support for settings, permissions fields
- Async context manager for connection pooling

---

### NATS Event Publishing

**Expectations**:
- Event bus provided via dependency injection
- Events published asynchronously
- Event failures logged but don't block operations
- Subject format: `organization_service.{event_type}`

**Event Types**:
- `ORG_CREATED` → `organization_service.organization.created`
- `ORG_UPDATED` → `organization_service.organization.updated`
- `ORG_DELETED` → `organization_service.organization.deleted`
- `ORG_MEMBER_ADDED` → `organization_service.organization.member_added`
- `ORG_MEMBER_REMOVED` → `organization_service.organization.member_removed`
- `FAMILY_RESOURCE_SHARED` → `organization_service.family.resource_shared`

**Event Structure**:
```python
Event(
    event_type=EventType.ORG_CREATED,
    source=ServiceSource.ORG_SERVICE,
    data={...}
)
```

---

### Consul Service Discovery

**Expectations**:
- Service registered at startup
- Service name: `organization_service`
- Health check endpoint: `/health`
- Discovers `postgres_grpc_service` via Consul
- Discovers `account_service` for user validation

**Configuration**:
```python
host, port = config.discover_service(
    service_name='postgres_grpc_service',
    default_host='isa-postgres-grpc',
    default_port=50061
)
```

---

### Account Service Client

**Expectations**:
- Used for user existence validation
- Validates user_id before adding member
- Fail-open for eventual consistency
- Used via AccountClientProtocol interface

**Usage**:
```python
# Validate user exists
user = await self.account_client.get_account(user_id)
```

---

## Error Handling Contracts

### OrganizationNotFoundError

**When Raised**:
- `get_organization`: Organization ID not found
- `update_organization`: Organization ID not found
- `delete_organization`: Organization ID not found
- `switch_user_context`: Organization ID not found

**HTTP Status**: 404 Not Found

**Response**:
```json
{
  "detail": "Organization org_123 not found"
}
```

---

### OrganizationAccessDeniedError

**When Raised**:
- User not a member of organization
- User lacks required role (admin/owner)
- Membership is not active (suspended)
- Admin trying to modify owner/admin

**HTTP Status**: 403 Forbidden

**Response Examples**:
```json
{"detail": "User user_123 does not have access to organization org_456"}
{"detail": "User user_123 does not have admin access to organization org_456"}
{"detail": "User user_123 is not the owner of organization org_456"}
{"detail": "Admins cannot modify owners or other admins"}
```

---

### OrganizationValidationError

**When Raised**:
- Name is empty or missing
- Billing email is empty or invalid
- Either user_id or email not provided
- Attempting to remove last owner
- Member limit exceeded

**HTTP Status**: 400 Bad Request

**Response Examples**:
```json
{"detail": "Organization name and billing email are required"}
{"detail": "Either user_id or email must be provided"}
{"detail": "Cannot remove the last owner from organization"}
```

---

### OrganizationServiceError

**When Raised**:
- Unexpected errors during operations
- Database connection failures
- Generic operation failures

**HTTP Status**: 500 Internal Server Error

**Response**:
```json
{
  "detail": "Failed to create organization: {error_message}"
}
```

---

### SharingNotFoundError

**When Raised**:
- `get_sharing`: Sharing ID not found
- `update_sharing`: Sharing ID not found
- `delete_sharing`: Sharing ID not found

**HTTP Status**: 404 Not Found

**Response**:
```json
{
  "detail": "Sharing share_123 not found"
}
```

---

### SharingAccessDeniedError

**When Raised**:
- User not admin when creating sharing
- User not creator or admin when updating/deleting
- User lacks permission to access sharing

**HTTP Status**: 403 Forbidden

**Response**:
```json
{
  "detail": "User user_123 does not have permission to create sharing"
}
```

---

### SharingQuotaExceededError

**When Raised**:
- User exceeds allocated quota
- Organization exceeds total quota
- Resource-specific limits exceeded

**HTTP Status**: 429 Too Many Requests

**Response**:
```json
{
  "detail": "Quota exceeded for sharing share_123"
}
```

---

### HTTP Status Code Mappings

| Error Type | HTTP Status | Example Scenario |
|------------|-------------|------------------|
| OrganizationNotFoundError | 404 | Organization ID not found |
| OrganizationAccessDeniedError | 403 | User not admin/owner |
| OrganizationValidationError | 400 | Name/email missing |
| OrganizationServiceError | 500 | Database failure |
| SharingNotFoundError | 404 | Sharing ID not found |
| SharingAccessDeniedError | 403 | Not sharing admin |
| SharingQuotaExceededError | 429 | Quota exceeded |
| Pydantic ValidationError | 422 | Name too long |

---

## Performance SLAs

### Response Time Targets (p95)

| Operation | Target | Max Acceptable |
|-----------|--------|----------------|
| create_organization | < 300ms | < 800ms |
| get_organization | < 50ms | < 200ms |
| update_organization | < 100ms | < 300ms |
| delete_organization | < 200ms | < 500ms |
| add_organization_member | < 200ms | < 500ms |
| remove_organization_member | < 100ms | < 300ms |
| get_organization_members | < 150ms | < 500ms |
| switch_user_context | < 100ms | < 300ms |
| get_organization_stats | < 200ms | < 500ms |
| create_sharing | < 250ms | < 600ms |
| get_sharing | < 100ms | < 300ms |
| list_organization_sharings | < 200ms | < 500ms |

### Throughput Targets

- Organization creation: 50 req/s
- Organization queries: 500 req/s
- Member operations: 200 req/s
- Context switching: 1000 req/s
- Sharing operations: 100 req/s

### Resource Limits

- Max concurrent connections: 100
- Max members per organization: Plan-based (5-unlimited)
- Max organizations per query: 100 (page_size limit)
- Max sharing permissions per resource: 100
- Settings/permissions JSON size: 10KB recommended

---

## Test Coverage Requirements

All tests MUST cover:

- ✅ Happy path (BR-XXX success scenarios)
- ✅ Validation errors (400, 422)
- ✅ Not found errors (404)
- ✅ Access denied errors (403)
- ✅ State transitions (organization/member lifecycle)
- ✅ Event publishing (verify published)
- ✅ Edge cases (EC-XXX scenarios)
- ✅ Role-based access control
- ✅ Member limit enforcement
- ✅ Last owner protection
- ✅ Context switching (personal/organization)
- ✅ Family sharing operations
- ✅ Permission hierarchy
- ✅ Concurrent operations
- ✅ Performance within SLAs

---

**Version**: 1.0.0
**Last Updated**: 2025-12-15
**Owner**: Organization Service Team
