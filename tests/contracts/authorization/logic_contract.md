# Authorization Service - Logic Contract

## Business Rules (50 rules)

### Access Control Rules (BR-ACL-001 to BR-ACL-012)

**BR-ACL-001: User ID Required**
- All access check requests MUST include a user_id
- System validates user_id is non-empty string
- Error returned if violated: "user_id is required"
- Example: `{"user_id": ""}` -> 400 Bad Request

**BR-ACL-002: Resource Type Required**
- Access check MUST specify a valid resource_type
- Valid types: mcp_tool, prompt, resource, api_endpoint, database, file_storage, compute, ai_model
- Invalid type rejected with 422 Validation Error
- Example: `{"resource_type": "invalid"}` -> 422 Unprocessable Entity

**BR-ACL-003: Resource Name Required**
- Access check MUST specify a resource_name
- Resource name is non-empty string
- Whitespace-only strings are rejected
- Example: `{"resource_name": ""}` -> 400 Bad Request

**BR-ACL-004: Required Access Level Default**
- required_access_level defaults to "read_only" if not specified
- Valid levels: none, read_only, read_write, admin, owner
- Invalid level rejected with 422 Validation Error

**BR-ACL-005: User Must Be Active**
- Inactive users have no access to any resources
- Access check returns has_access=false for inactive users
- Reason: "User not found or inactive"
- No information leak about user existence

**BR-ACL-006: Permission Priority Hierarchy**
- Priority order (highest to lowest):
  1. Admin-granted permissions (ADMIN_GRANT)
  2. Organization permissions (ORGANIZATION)
  3. Subscription-based permissions (SUBSCRIPTION)
  4. User-specific permissions (non-admin)
  5. System default (SYSTEM_DEFAULT) - always deny
- Higher priority permission takes precedence

**BR-ACL-007: Admin Grant Highest Priority**
- Admin-granted permissions override all other permission sources
- Checked first in access evaluation
- Never downgraded by other permission sources

**BR-ACL-008: Access Level Hierarchy**
- Hierarchy (highest to lowest): owner > admin > read_write > read_only > none
- User with higher level can access resources requiring lower level
- Example: admin access grants read_write access implicitly

**BR-ACL-009: Access Denied Default**
- If no matching permission found, access is denied
- Default permission_source: SYSTEM_DEFAULT
- Default user_access_level: NONE
- Reason includes resource type and name

**BR-ACL-010: Organization Context Optional**
- organization_id is optional in access check
- If not provided, uses user's default organization_id
- Non-organization users skip organization permission check

**BR-ACL-011: Context Metadata Optional**
- Access check context is optional JSONB field
- Used for additional authorization context
- Does not affect core access decision

**BR-ACL-012: Access Check Response Structure**
- Response MUST include: has_access, user_access_level, permission_source, reason
- Optional fields: subscription_tier, organization_plan, expires_at, metadata
- Response always returns, never throws (fail-safe)

### Subscription Rules (BR-SUB-001 to BR-SUB-010)

**BR-SUB-001: Subscription Tier Hierarchy**
- Hierarchy (lowest to highest): free < pro < enterprise < custom
- Higher tier includes all lower tier permissions
- Example: Pro tier can access Free tier resources

**BR-SUB-002: Free Tier Default**
- Unknown subscription_status maps to FREE tier
- Invalid subscription values treated as FREE
- Ensures graceful degradation

**BR-SUB-003: Subscription-Based Resource Access**
- Resources have subscription_tier_required configuration
- User tier must meet or exceed required tier
- Tier comparison uses hierarchy not string equality

**BR-SUB-004: Resource Category Classification**
- Resources grouped by category (utilities, assistance, ai_tools, ai_models, data, admin)
- Categories are informational, not authorization criteria
- Used for filtering and reporting

**BR-SUB-005: Resource Permission Configuration**
- ResourcePermission defines base access for subscription tiers
- Fields: resource_type, resource_name, subscription_tier_required, access_level
- Configuration checked when no explicit permission exists

**BR-SUB-006: Subscription Tier Caching**
- User subscription tier may be cached
- Cache invalidated on subscription change event
- Stale cache fails-open (may grant access)

**BR-SUB-007: Resource Enabled State**
- ResourcePermission has is_enabled flag
- Disabled resources return no access regardless of subscription
- Used for feature rollouts and deprecation

**BR-SUB-008: Subscription Access Level**
- Subscription grants specific access_level per resource
- Cannot exceed configured level through subscription alone
- Admin grants can override subscription limits

**BR-SUB-009: Missing Resource Configuration**
- If no ResourcePermission configured for resource
- Access denied: "Resource not configured for subscription access"
- Explicit configuration required for subscription access

**BR-SUB-010: Subscription Response Metadata**
- Subscription access includes metadata:
  - subscription_required: tier needed for resource
  - resource_category: resource classification
- Enables client-side feature display logic

### Organization Rules (BR-ORG-001 to BR-ORG-008)

**BR-ORG-001: Organization Membership Required**
- User MUST be organization member for organization permissions
- Non-members receive: "User is not a member of the organization"
- Membership verified via repository

**BR-ORG-002: Organization Must Be Active**
- Inactive organizations grant no permissions
- Access denied: "Organization not found or inactive"
- Affects all organization members

**BR-ORG-003: Organization Plan Hierarchy**
- Hierarchy (lowest to highest): startup < growth < enterprise < custom
- Higher plan includes lower plan permissions
- Case-insensitive comparison

**BR-ORG-004: Organization Permission Configuration**
- OrganizationPermission: organization_id, resource_type, resource_name, access_level
- org_plan_required specifies minimum organization plan
- Defaults to "startup" if not specified

**BR-ORG-005: Organization Permission Priority**
- Organization permissions checked after admin grants
- Checked before subscription-based permissions
- Organization context overrides user subscription for matching resources

**BR-ORG-006: Organization Response Metadata**
- Organization access includes metadata:
  - organization_id: granting organization
  - org_plan: current organization plan
  - plan_required: minimum plan for resource
- Enables organization-aware UI logic

**BR-ORG-007: User Default Organization**
- User may have default organization_id in profile
- Used when request doesn't specify organization_id
- Null organization_id skips organization permission check

**BR-ORG-008: Organization Permission Enabled State**
- OrganizationPermission has is_enabled flag
- Disabled permissions ignored in access checks
- Used for organization-specific feature management

### Permission Grant Rules (BR-GRT-001 to BR-GRT-010)

**BR-GRT-001: Target User Must Exist**
- Permission can only be granted to existing users
- Non-existent user returns false (no permission created)
- Log error: "Cannot grant permission to non-existent user"

**BR-GRT-002: User ID Required for Grant**
- GrantPermissionRequest MUST include user_id
- Empty or null user_id rejected with validation error
- Identifies the permission recipient

**BR-GRT-003: Resource Type Required for Grant**
- GrantPermissionRequest MUST include valid resource_type
- Invalid type rejected with validation error
- Identifies the resource being authorized

**BR-GRT-004: Resource Name Required for Grant**
- GrantPermissionRequest MUST include resource_name
- Empty or null resource_name rejected
- Specific resource identifier

**BR-GRT-005: Access Level Required for Grant**
- GrantPermissionRequest MUST include access_level
- Must be valid AccessLevel enum value
- Defines level of access being granted

**BR-GRT-006: Permission Source Required for Grant**
- GrantPermissionRequest MUST include permission_source
- Valid sources: SUBSCRIPTION, ORGANIZATION, ADMIN_GRANT, SYSTEM_DEFAULT
- Determines permission priority

**BR-GRT-007: Granted By User Optional**
- granted_by_user_id tracks who created permission
- May be null for system-generated permissions
- Used for audit trail

**BR-GRT-008: Permission Expiry Validation**
- expires_at MUST be in the future if provided
- Past expiry date rejected: "Expiry date must be in the future"
- Null expires_at means no expiration

**BR-GRT-009: Grant Reason Optional**
- reason field is optional
- Used for audit logging
- Describes why permission was granted

**BR-GRT-010: Grant Creates Active Permission**
- New permissions created with is_active = true
- created_at and updated_at set to current UTC timestamp
- Permission ID auto-generated

### Permission Revoke Rules (BR-REV-001 to BR-REV-006)

**BR-REV-001: User ID Required for Revoke**
- RevokePermissionRequest MUST include user_id
- Identifies permission holder to revoke from

**BR-REV-002: Resource Identification Required**
- RevokePermissionRequest MUST include resource_type and resource_name
- Together identify the specific permission to revoke

**BR-REV-003: Revoke Non-Existent Permission**
- Revoking non-existent permission returns false
- No error thrown, operation is idempotent
- Logged as failed action

**BR-REV-004: Revoked By User Optional**
- revoked_by_user_id tracks who removed permission
- May be null for system-triggered revocations
- Used for audit trail

**BR-REV-005: Revoke Reason Optional**
- reason field is optional
- Used for audit logging
- Describes why permission was revoked

**BR-REV-006: Revoke Logs Previous Level**
- Audit log captures old_access_level before revocation
- Enables permission history tracking
- Supports compliance requirements

---

## State Machines (4 machines)

### Permission Lifecycle State Machine

```
States:
- ACTIVE: Permission is valid and grants access
- EXPIRED: Permission past expires_at, no longer grants access
- REVOKED: Permission explicitly revoked, no longer grants access
- SUSPENDED: Permission temporarily disabled (organization inactive, etc.)

Transitions:
ACTIVE -> EXPIRED (current_time > expires_at)
ACTIVE -> REVOKED (revoke_resource_permission called)
ACTIVE -> SUSPENDED (user/organization becomes inactive)
SUSPENDED -> ACTIVE (user/organization reactivated)

Terminal States:
- EXPIRED: Cannot be reactivated, must create new permission
- REVOKED: Cannot be reactivated, must create new permission

Rules:
- Only ACTIVE permissions grant access
- EXPIRED checked on every access evaluation
- REVOKED permissions may be soft-deleted or archived
- SUSPENDED permissions auto-reactivate on dependency restoration
```

### Access Check State Machine

```
States:
- PENDING: Access check initiated
- ADMIN_CHECK: Evaluating admin-granted permissions
- ORG_CHECK: Evaluating organization permissions
- SUB_CHECK: Evaluating subscription permissions
- USER_CHECK: Evaluating user-specific permissions
- GRANTED: Access approved
- DENIED: Access rejected

Transitions:
PENDING -> ADMIN_CHECK (always first)
ADMIN_CHECK -> GRANTED (admin permission found with sufficient level)
ADMIN_CHECK -> ORG_CHECK (no admin permission or insufficient)
ORG_CHECK -> GRANTED (org permission found with sufficient level)
ORG_CHECK -> SUB_CHECK (no org permission or insufficient)
SUB_CHECK -> GRANTED (subscription grants access)
SUB_CHECK -> USER_CHECK (subscription insufficient)
USER_CHECK -> GRANTED (user permission found)
USER_CHECK -> DENIED (no permission found)

Rules:
- Checks proceed in strict priority order
- First sufficient permission terminates evaluation
- DENIED only reached after all checks fail
- Error during check -> DENIED (fail-secure)
```

### User Permission Summary State Machine

```
States:
- LOADING: Fetching user permission data
- AGGREGATING: Computing permission counts by type/source/level
- ENRICHING: Adding organization and subscription context
- COMPLETE: Summary ready for return
- ERROR: Failed to generate summary

Transitions:
LOADING -> AGGREGATING (data fetched successfully)
LOADING -> ERROR (fetch failed)
AGGREGATING -> ENRICHING (counts computed)
AGGREGATING -> ERROR (aggregation failed)
ENRICHING -> COMPLETE (context added)
ENRICHING -> ERROR (enrichment failed)

Rules:
- Summary reflects current permission state
- expires_soon_count: permissions expiring within 7 days
- last_access_check: most recent access check timestamp
```

### Bulk Operation State Machine

```
States:
- INITIALIZED: Batch created, not started
- PROCESSING: Operations being executed
- PARTIAL_COMPLETE: Some operations succeeded, some failed
- COMPLETE: All operations processed (success or fail)
- ABORTED: Batch terminated early (not currently implemented)

Transitions:
INITIALIZED -> PROCESSING (first operation starts)
PROCESSING -> PROCESSING (each operation completes)
PROCESSING -> PARTIAL_COMPLETE (all processed, some failures)
PROCESSING -> COMPLETE (all processed, all success)

Rules:
- Each operation independent, failures don't stop batch
- Results tracked per operation with operation_id
- execution_time_seconds captures total processing time
- No rollback on partial failure (eventual consistency)
```

---

## Edge Cases (20 cases)

### EC-001: User Not Found
- **Input**: Access check for non-existent user_id
- **Expected**: has_access=false, reason="User not found or inactive"
- **Actual**: Graceful denial, no exception thrown
- **Note**: No information leak about user existence

### EC-002: Expired Permission During Access Check
- **Input**: User has permission that expires during evaluation
- **Expected**: Permission treated as expired, check continues to next source
- **Actual**: Expiry checked at evaluation time
- **Note**: Race condition possible, acceptable for security

### EC-003: Concurrent Permission Grant and Revoke
- **Input**: Grant and revoke for same user/resource simultaneously
- **Expected**: Last write wins at database level
- **Actual**: No transaction isolation for operations
- **Note**: Audit log captures both operations

### EC-004: Organization Becomes Inactive During Check
- **Input**: Organization deactivated while access check in progress
- **Expected**: Organization check fails, continues to subscription check
- **Actual**: Each check fetches fresh data
- **Note**: Minimal latency impact

### EC-005: Invalid Subscription Status Value
- **Input**: User has subscription_status not in SubscriptionTier enum
- **Expected**: Treated as FREE tier
- **Actual**: Falls back to FREE for unknown values
- **Note**: Ensures graceful degradation

### EC-006: Empty Permission List for User
- **Input**: list_user_accessible_resources for user with no explicit permissions
- **Expected**: Returns subscription-based resources only
- **Actual**: Combines explicit and subscription resources
- **Note**: User always has some accessible resources based on tier

### EC-007: Resource Not Configured for Subscription
- **Input**: Access check for resource with no ResourcePermission
- **Expected**: has_access=false, reason="Resource not configured..."
- **Actual**: No implicit access without configuration
- **Note**: Explicit configuration required

### EC-008: Admin Grant with Expiry in Past
- **Input**: GrantPermissionRequest with expires_at < now
- **Expected**: Validation error: "Expiry date must be in the future"
- **Actual**: Pydantic validator rejects at request parsing
- **Note**: Prevents creating already-expired permissions

### EC-009: Bulk Grant with Some Invalid Users
- **Input**: BulkPermissionRequest with mix of valid and invalid user_ids
- **Expected**: Valid operations succeed, invalid return success=false
- **Actual**: Each operation independent
- **Note**: Partial success is acceptable

### EC-010: Permission Grant Overwrites Existing
- **Input**: Grant permission when user already has permission for resource
- **Expected**: Depends on repository implementation (update or fail)
- **Actual**: Repository handles conflict
- **Note**: May need explicit upsert logic

### EC-011: Organization Permission Without User Membership
- **Input**: Access check with organization_id where user is not member
- **Expected**: Organization check fails, continues to subscription
- **Actual**: Membership verified before permission check
- **Note**: Non-members cannot use organization permissions

### EC-012: Subscription Downgrade During Access
- **Input**: User tier changes from PRO to FREE mid-access
- **Expected**: Next access check reflects new tier
- **Actual**: No real-time tier sync, relies on events
- **Note**: Brief window of stale access possible

### EC-013: Very Long Resource Name
- **Input**: resource_name exceeds 255 characters
- **Expected**: Validation error if length constrained
- **Actual**: Database column limit may truncate
- **Note**: Client should validate length

### EC-014: Unicode in Resource Name
- **Input**: Resource name with emojis, CJK characters
- **Expected**: Correctly stored and matched
- **Actual**: PostgreSQL handles Unicode properly
- **Note**: Case sensitivity depends on collation

### EC-015: Null vs Empty Context
- **Input**: Access check with context=null vs context={}
- **Expected**: Both acceptable, treated as no context
- **Actual**: Pydantic normalizes to None or empty dict
- **Note**: No functional difference

### EC-016: Cleanup Expired Called During Grant
- **Input**: cleanup_expired_permissions runs while granting
- **Expected**: No conflict, different permission records
- **Actual**: Operations on different rows
- **Note**: New permission unaffected by cleanup

### EC-017: Repository Unavailable
- **Input**: Database connection lost during access check
- **Expected**: has_access=false, reason includes error
- **Actual**: Exception caught, safe denial returned
- **Note**: Fail-secure on infrastructure failure

### EC-018: Event Bus Unavailable
- **Input**: NATS unavailable when publishing access.denied
- **Expected**: Access check still completes
- **Actual**: Event publishing failure logged, not blocking
- **Note**: Events are best-effort

### EC-019: Zero Permissions in Bulk Request
- **Input**: BulkPermissionRequest with empty operations list
- **Expected**: Empty results list returned
- **Actual**: No operations processed
- **Note**: Valid no-op request

### EC-020: Same Resource in Multiple Bulk Operations
- **Input**: Grant then revoke same resource in single batch
- **Expected**: Both operations execute in order
- **Actual**: Sequential processing, revoke undoes grant
- **Note**: Order-dependent results

---

## Data Consistency Rules

### DC-001: Permission ID Uniqueness
- UserPermissionRecord.id is unique identifier
- UUID generation ensures uniqueness
- Database enforces primary key constraint

### DC-002: User-Resource Permission Uniqueness
- One active permission per (user_id, resource_type, resource_name)
- Business key enforced at repository level
- New grant may update or conflict

### DC-003: Organization Permission Uniqueness
- One permission per (organization_id, resource_type, resource_name)
- Prevents conflicting organization access rules
- Latest configuration takes precedence

### DC-004: Timestamp Ordering
- created_at <= updated_at (always)
- Timestamps in UTC timezone
- expires_at > created_at (if set)

### DC-005: Access Level Consistency
- Access level from enum, no custom values
- Database stores enum value as string
- API accepts only valid enum values

### DC-006: Permission Source Consistency
- permission_source from enum
- Cannot mix sources for same permission record
- Source determines priority in access evaluation

### DC-007: Audit Log Immutability
- PermissionAuditLog records are append-only
- No updates or deletes to audit entries
- Provides complete permission history

### DC-008: Resource Permission Uniqueness
- One ResourcePermission per (resource_type, resource_name)
- Defines base subscription access
- Updates replace configuration

---

## Integration Contracts

### Account Service Integration

**Purpose**: Validate user existence and subscription status

**Endpoint**: GET /api/v1/accounts/profile/{user_id}

**When**:
- Access check (get_user_info)
- Permission grant (verify target user)

**Expected Response**:
- 200: { user_id, email, subscription_status, is_active, organization_id }
- 404: User not found

**Error Handling**:
- Timeout: Use cached data or fail-open for access checks
- 404: Access denied for check, grant fails for permission
- 5xx: Log error, return safe default

**Event Subscriptions**:
- user.deleted: Revoke all user permissions
- user.status_changed: Update cached user info
- subscription.changed: Invalidate subscription cache

### Organization Service Integration

**Purpose**: Validate organization membership and plan

**Endpoint**: GET /api/v1/organizations/{org_id}

**When**:
- Access check with organization context
- Organization permission evaluation

**Expected Response**:
- 200: { organization_id, plan, is_active, member_count }
- 404: Organization not found

**Membership Check**: GET /api/v1/organizations/{org_id}/members/{user_id}

**Error Handling**:
- Timeout: Skip organization check, continue to subscription
- 404: Organization access denied
- 5xx: Log error, skip organization permissions

**Event Subscriptions**:
- organization.member_added: No action (permissions checked on demand)
- organization.member_removed: May revoke organization-based permissions
- organization.plan_changed: Invalidate organization cache

### Subscription Service Integration

**Purpose**: Get current subscription tier for user

**When**: Access check subscription evaluation

**Expected Response**: { user_id, tier, status, features }

**Error Handling**:
- Use cached tier from user profile
- Default to FREE tier on failure
- Log degraded access

**Event Subscriptions**:
- subscription.created: Update user subscription cache
- subscription.upgraded: Update user subscription cache
- subscription.downgraded: Update user subscription cache
- subscription.cancelled: Set tier to FREE

### Audit Service Integration

**Purpose**: Record permission changes and access events

**Event Types Published**:
- permission.granted: New permission created
- permission.revoked: Permission removed
- access.denied: Access check failed

**Event Payload**:
```json
{
  "event_type": "permission.granted",
  "source": "authorization_service",
  "data": {
    "user_id": "user_123",
    "resource_type": "mcp_tool",
    "resource_name": "image_generator",
    "access_level": "read_write",
    "permission_source": "admin_grant",
    "granted_by_user_id": "admin_456",
    "timestamp": "2025-12-17T10:00:00Z"
  }
}
```

**Error Handling**:
- Event publishing is non-blocking
- Failures logged but don't affect operation
- Local audit log as backup

---

## Error Handling Contracts

### Access Check Errors

| Error Condition | HTTP Code | Error Message | has_access |
|-----------------|-----------|---------------|------------|
| User not found | 200 | "User not found or inactive" | false |
| User inactive | 200 | "User not found or inactive" | false |
| Resource not configured | 200 | "Resource not configured for subscription access" | false |
| Insufficient tier | 200 | "Subscription tier 'X' insufficient, requires 'Y'" | false |
| Insufficient level | 200 | "Insufficient permissions for X:Y, required: Z" | false |
| Internal error | 200 | "Access check failed: {error}" | false |

Note: Access checks return 200 OK with has_access=false, not HTTP error codes.

### Permission Grant Errors

| Error Condition | HTTP Code | Error Message |
|-----------------|-----------|---------------|
| Missing user_id | 422 | Validation error: user_id required |
| Invalid resource_type | 422 | Validation error: invalid enum value |
| Invalid access_level | 422 | Validation error: invalid enum value |
| Expired expiry date | 422 | "Expiry date must be in the future" |
| User not found | 200 | Operation returns false (not HTTP error) |
| Database error | 500 | "Internal server error" |

### Permission Revoke Errors

| Error Condition | HTTP Code | Error Message |
|-----------------|-----------|---------------|
| Missing user_id | 422 | Validation error: user_id required |
| Missing resource_type | 422 | Validation error: resource_type required |
| Missing resource_name | 422 | Validation error: resource_name required |
| Permission not found | 200 | Operation returns false |
| Database error | 500 | "Internal server error" |

### Bulk Operation Errors

| Error Condition | HTTP Code | Error Message |
|-----------------|-----------|---------------|
| Empty operations list | 200 | Empty results list |
| Invalid operation type | 422 | Validation error on request |
| Partial failures | 200 | Results list with success=false entries |
| Database error | 500 | "Internal server error" |

### Health Check Errors

| Error Condition | HTTP Code | Response |
|-----------------|-----------|----------|
| Service healthy | 200 | { status: "healthy", service: "authorization", ... } |
| Database unavailable | 503 | { status: "unhealthy", ... } |
| Dependency unhealthy | 200 | { status: "degraded", dependencies: [...] } |

---

## Performance Contracts

### Response Time SLAs

| Operation | Target P50 | Target P99 | Max |
|-----------|------------|------------|-----|
| Access Check | < 10ms | < 50ms | 200ms |
| Permission Grant | < 20ms | < 100ms | 500ms |
| Permission Revoke | < 20ms | < 100ms | 500ms |
| Bulk Grant (10 ops) | < 100ms | < 500ms | 2000ms |
| User Permission Summary | < 50ms | < 200ms | 1000ms |
| List Accessible Resources | < 50ms | < 200ms | 1000ms |

### Throughput Targets

| Operation | Target RPS |
|-----------|------------|
| Access Check | 10,000 |
| Permission Grant | 1,000 |
| Permission Revoke | 1,000 |
| Bulk Operations | 100 |
| Summary/List | 500 |

### Caching Strategy

**Permission Cache**:
- TTL: 15 minutes
- Key: user_id:resource_type:resource_name
- Invalidation: On grant/revoke events

**User Info Cache**:
- TTL: 5 minutes
- Key: user_id
- Invalidation: On user events

**Resource Config Cache**:
- TTL: 1 hour
- Key: resource_type:resource_name
- Invalidation: On config changes

---

## Security Contracts

### Authentication Requirements

| Endpoint | Auth Required | Token Type |
|----------|---------------|------------|
| POST /access/check | Yes | JWT or API Key |
| POST /permissions/grant | Yes | JWT (Admin) |
| POST /permissions/revoke | Yes | JWT (Admin) |
| GET /users/{id}/permissions | Yes | JWT |
| GET /health | No | None |

### Authorization Requirements

| Operation | Required Role |
|-----------|---------------|
| Access Check | Any authenticated user |
| Grant Admin Permission | System Admin |
| Grant Org Permission | Org Admin |
| Revoke Any Permission | System Admin or Grantor |
| View Own Permissions | User (self) |
| View Any Permissions | System Admin |

### Rate Limiting

| Endpoint | Rate Limit |
|----------|------------|
| Access Check | 1000/min per user |
| Permission Grant | 100/min per admin |
| Permission Revoke | 100/min per admin |
| Bulk Operations | 10/min per admin |

### Audit Requirements

- All permission grants logged with grantor
- All permission revokes logged with revoker
- All access denials logged
- Audit logs retained for 90 days
- Logs include timestamp, user_id, resource, action, result

---

**Document Version**: 1.0
**Last Updated**: 2025-12-17
**Maintained By**: Authorization Service Team
