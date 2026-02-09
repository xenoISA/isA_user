# Authorization Service - Domain Context

## Overview

The Authorization Service is the **access control engine** for the entire isA_user platform. It provides comprehensive resource-based access control (RBAC), managing permissions across multiple sources: subscription tiers, organization memberships, and administrative grants. This service answers the critical question: "Can this user access this resource with this level of permission?"

**Business Context**: Enable fine-grained, hierarchical access control that scales across subscription models, organization structures, and individual grants. Authorization Service owns the "what can they do" of the system - ensuring every resource access is validated against a clear permission hierarchy.

**Core Value Proposition**: Transform complex access control requirements into a unified, priority-based permission system with subscription-aware features, organization-level permissions, and admin override capabilities.

---

## Business Taxonomy

### Core Entities

#### 1. Resource Permission
**Definition**: A base permission configuration defining access requirements for a specific resource.

**Business Purpose**:
- Define which subscription tiers can access which resources
- Establish default access levels for resource categories
- Enable feature gating based on subscription status
- Configure resource-specific permission requirements

**Key Attributes**:
- Resource Type (mcp_tool, prompt, api_endpoint, database, file_storage, compute, ai_model)
- Resource Name (unique identifier within type)
- Resource Category (grouping for management)
- Subscription Tier Required (free, pro, enterprise, custom)
- Access Level (none, read_only, read_write, admin, owner)
- Is Enabled (activation status)
- Description (human-readable purpose)

**Resource Types**:
- **MCP_TOOL**: Model Context Protocol tools for AI agents
- **PROMPT**: AI assistant prompt templates
- **RESOURCE**: Generic resources
- **API_ENDPOINT**: REST API endpoints
- **DATABASE**: Database access permissions
- **FILE_STORAGE**: File and object storage access
- **COMPUTE**: Compute resource access
- **AI_MODEL**: AI model access permissions

#### 2. User Permission Record
**Definition**: A specific permission grant linking a user to a resource with defined access level.

**Business Purpose**:
- Track individual user permissions
- Record permission source (who/what granted it)
- Support time-limited permissions with expiry
- Enable audit trail for permission changes

**Key Attributes**:
- User ID (target user)
- Resource Type (what category)
- Resource Name (specific resource)
- Access Level (permission level)
- Permission Source (subscription, organization, admin_grant, system_default)
- Granted By User ID (admin who granted, if applicable)
- Organization ID (org context, if applicable)
- Expires At (optional expiration)
- Is Active (current status)

**Permission Sources**:
- **SUBSCRIPTION**: Auto-granted based on subscription tier
- **ORGANIZATION**: Inherited from organization membership
- **ADMIN_GRANT**: Manually granted by administrator (highest priority)
- **SYSTEM_DEFAULT**: Baseline permissions for all users

#### 3. Organization Permission
**Definition**: Organization-level permission configuration that applies to all members.

**Business Purpose**:
- Define resource access at organization level
- Support B2B subscription models
- Enable group-based permission management
- Simplify enterprise permission administration

**Key Attributes**:
- Organization ID (target organization)
- Resource Type (what category)
- Resource Name (specific resource)
- Access Level (permission level)
- Organization Plan Required (startup, growth, enterprise, custom)
- Is Enabled (activation status)
- Created By User ID (admin who configured)

#### 4. Permission Audit Log
**Definition**: Immutable record of permission-related actions for compliance and debugging.

**Business Purpose**:
- Track all permission grants and revocations
- Record access check decisions for security analysis
- Support compliance and audit requirements
- Enable troubleshooting permission issues

**Key Attributes**:
- User ID (affected user)
- Resource Type (target resource category)
- Resource Name (specific resource)
- Action (grant, revoke, access_check_grant, access_check_deny)
- Old Access Level (before change)
- New Access Level (after change)
- Performed By User ID (actor)
- Reason (justification)
- Success (operation result)
- Error Message (if failed)
- Timestamp (when it happened)

### Domain Concepts

#### Access Level Hierarchy
Access levels follow a strict hierarchy where higher levels include lower permissions:
```
OWNER (4) > ADMIN (3) > READ_WRITE (2) > READ_ONLY (1) > NONE (0)
```
A user with ADMIN access automatically satisfies READ_WRITE requirements.

#### Subscription Tier Hierarchy
Subscription tiers determine baseline resource access:
```
CUSTOM (3) > ENTERPRISE (2) > PRO (1) > FREE (0)
```
Higher tiers include all permissions from lower tiers.

#### Organization Plan Hierarchy
Organization plans for B2B features:
```
CUSTOM (3) > ENTERPRISE (2) > GROWTH (1) > STARTUP (0)
```

### Terminology
- **Permission Resolution**: Process of determining effective access level from multiple sources
- **Permission Priority**: Order in which permission sources are evaluated (admin > org > subscription > default)
- **Access Check**: Single validation of user access to specific resource at required level
- **Permission Grant**: Action of assigning access to a user for a resource
- **Permission Revocation**: Action of removing access from a user for a resource
- **Bulk Operation**: Processing multiple permission changes in single transaction

---

## Domain Scenarios

### 1. Check Resource Access
- **Trigger**: User attempts to access a protected resource
- **Actors**: User, Authorization Service, Account Service, Organization Service
- **Preconditions**: User is authenticated, resource exists
- **Flow**:
  1. System receives access check request with user_id, resource_type, resource_name, required_level
  2. System fetches user information from Account Service
  3. System checks for admin-granted permissions (highest priority)
  4. If no admin grant, system checks organization permissions
  5. If no org permission, system checks subscription-based permissions
  6. If no subscription match, system checks user-specific non-admin permissions
  7. System logs the access check decision
  8. System returns access response with decision, level, and source
- **Outcome**: User receives boolean access decision with detailed reasoning
- **Events**: `access.denied` (if denied)
- **Errors**:
  - UserNotFound: User ID does not exist or is inactive
  - ResourceNotConfigured: Resource has no permission configuration

### 2. Grant Permission to User
- **Trigger**: Administrator grants specific resource access to a user
- **Actors**: Administrator, Target User, Authorization Service
- **Preconditions**: Admin has permission to grant, target user exists
- **Flow**:
  1. Admin submits grant request with user_id, resource details, access level
  2. System validates target user exists and is active
  3. System creates or updates user permission record
  4. System logs the grant action in audit trail
  5. System publishes permission.granted event
  6. System returns success confirmation
- **Outcome**: User now has explicit permission to access resource
- **Events**: `permission.granted`
- **Errors**:
  - UserNotFound: Target user does not exist
  - InvalidPermission: Invalid resource or access level

### 3. Revoke Permission from User
- **Trigger**: Administrator removes resource access from a user
- **Actors**: Administrator, Target User, Authorization Service
- **Preconditions**: Permission exists for user
- **Flow**:
  1. Admin submits revoke request with user_id, resource details
  2. System retrieves current permission for logging
  3. System marks permission as inactive or deletes record
  4. System logs the revoke action in audit trail
  5. System publishes permission.revoked event
  6. System returns success confirmation
- **Outcome**: User no longer has explicit permission (may still have via subscription/org)
- **Events**: `permission.revoked`
- **Errors**:
  - PermissionNotFound: No permission exists to revoke

### 4. Bulk Grant Permissions
- **Trigger**: Administrator needs to grant multiple permissions efficiently
- **Actors**: Administrator, Multiple Target Users, Authorization Service
- **Preconditions**: Admin has bulk operation permission
- **Flow**:
  1. Admin submits bulk request with list of grant operations
  2. System generates batch ID and starts processing
  3. For each operation, system attempts to grant permission
  4. System collects success/failure results for each operation
  5. System returns batch summary with individual results
- **Outcome**: Multiple permissions granted with detailed status for each
- **Events**: `permissions.bulk_granted` (aggregate event)
- **Errors**:
  - PartialFailure: Some operations succeeded, some failed

### 5. Bulk Revoke Permissions
- **Trigger**: Administrator needs to revoke multiple permissions (e.g., security incident)
- **Actors**: Administrator, Multiple Target Users, Authorization Service
- **Preconditions**: Admin has bulk operation permission
- **Flow**:
  1. Admin submits bulk request with list of revoke operations
  2. System generates batch ID and starts processing
  3. For each operation, system attempts to revoke permission
  4. System collects success/failure results for each operation
  5. System returns batch summary with individual results
- **Outcome**: Multiple permissions revoked with detailed status for each
- **Events**: `permissions.bulk_revoked` (aggregate event)
- **Errors**:
  - PartialFailure: Some operations succeeded, some failed

### 6. Get User Permission Summary
- **Trigger**: User or admin requests comprehensive permission overview
- **Actors**: User, Administrator, Authorization Service
- **Preconditions**: User exists
- **Flow**:
  1. Request received with user_id
  2. System fetches user information including subscription tier
  3. System aggregates all user permissions by type, source, and level
  4. System identifies permissions expiring soon
  5. System returns comprehensive summary
- **Outcome**: Complete view of user's permission landscape
- **Events**: None
- **Errors**:
  - UserNotFound: User does not exist

### 7. Handle User Deletion Event
- **Trigger**: User is deleted from Account Service
- **Actors**: Account Service, Authorization Service
- **Preconditions**: User existed with permissions
- **Flow**:
  1. Authorization Service receives user.deleted event
  2. System retrieves all permissions for deleted user
  3. System revokes each permission
  4. System logs cleanup action
- **Outcome**: All permissions for deleted user are cleaned up
- **Events**: None (cleanup operation)
- **Errors**:
  - CleanupFailure: Some permissions could not be revoked

### 8. Handle Organization Member Added Event
- **Trigger**: User is added to an organization
- **Actors**: Organization Service, Authorization Service
- **Preconditions**: Organization has configured permissions
- **Flow**:
  1. Authorization Service receives organization.member_added event
  2. System retrieves organization's configured permissions
  3. For each org permission, system grants to new member
  4. System logs auto-grant actions
- **Outcome**: New member inherits organization's permissions
- **Events**: None (reactive operation)
- **Errors**:
  - AutoGrantFailure: Some permissions could not be auto-granted

---

## Domain Events

### Published Events

#### 1. `permission.granted` (EventType.PERMISSION_GRANTED)
- **When**: After successful permission grant to a user
- **Payload**:
  ```json
  {
    "event_id": "uuid",
    "event_type": "permission.granted",
    "user_id": "user_12345",
    "resource_type": "api_endpoint",
    "resource_name": "/api/data",
    "access_level": "read_write",
    "permission_source": "admin_grant",
    "granted_by_user_id": "admin_001",
    "organization_id": "org_001",
    "timestamp": "2025-01-01T00:00:00Z"
  }
  ```
- **Consumers**:
  - `audit_service`: Records permission change
  - `notification_service`: May notify user of new access
- **Ordering**: Per-user ordering guaranteed
- **Retry**: 3 retries, exponential backoff

#### 2. `permission.revoked` (EventType.PERMISSION_REVOKED)
- **When**: After successful permission revocation from a user
- **Payload**:
  ```json
  {
    "event_id": "uuid",
    "event_type": "permission.revoked",
    "user_id": "user_12345",
    "resource_type": "api_endpoint",
    "resource_name": "/api/data",
    "previous_access_level": "read_write",
    "revoked_by_user_id": "admin_001",
    "reason": "Policy change",
    "timestamp": "2025-01-01T00:00:00Z"
  }
  ```
- **Consumers**:
  - `audit_service`: Records permission change
  - `session_service`: May invalidate active sessions
- **Ordering**: Per-user ordering guaranteed
- **Retry**: 3 retries, exponential backoff

#### 3. `access.denied` (EventType.ACCESS_DENIED)
- **When**: User access check fails (insufficient permissions)
- **Payload**:
  ```json
  {
    "event_id": "uuid",
    "event_type": "access.denied",
    "user_id": "user_12345",
    "resource_type": "api_endpoint",
    "resource_name": "/api/admin",
    "required_access_level": "admin",
    "reason": "Insufficient permissions",
    "timestamp": "2025-01-01T00:00:00Z"
  }
  ```
- **Consumers**:
  - `audit_service`: Records access attempt
  - `telemetry_service`: Tracks denied access patterns
- **Ordering**: Best-effort
- **Retry**: 1 retry (non-critical)

#### 4. `permissions.bulk_granted` (EventType.PERMISSIONS_BULK_GRANTED)
- **When**: After bulk permission grant operation completes
- **Payload**:
  ```json
  {
    "event_id": "uuid",
    "event_type": "permissions.bulk_granted",
    "user_ids": ["user_001", "user_002", "user_003"],
    "permission_count": 15,
    "granted_by_user_id": "admin_001",
    "organization_id": "org_001",
    "timestamp": "2025-01-01T00:00:00Z"
  }
  ```
- **Consumers**:
  - `audit_service`: Records bulk operation
- **Ordering**: Per-operation ordering
- **Retry**: 3 retries

#### 5. `permissions.bulk_revoked` (EventType.PERMISSIONS_BULK_REVOKED)
- **When**: After bulk permission revoke operation completes
- **Payload**:
  ```json
  {
    "event_id": "uuid",
    "event_type": "permissions.bulk_revoked",
    "user_ids": ["user_001", "user_002"],
    "permission_count": 10,
    "revoked_by_user_id": "admin_001",
    "reason": "Security audit",
    "timestamp": "2025-01-01T00:00:00Z"
  }
  ```
- **Consumers**:
  - `audit_service`: Records bulk operation
  - `session_service`: May invalidate affected sessions
- **Ordering**: Per-operation ordering
- **Retry**: 3 retries

### Consumed Events

#### 1. `user.deleted` from account_service
- **Handler**: `handle_user_deleted()`
- **Purpose**: Clean up all permissions when user is deleted
- **Processing**: Idempotent, revokes all user permissions

#### 2. `organization.deleted` from organization_service
- **Handler**: `handle_organization_deleted()`
- **Purpose**: Clean up organization permissions and revoke user permissions from org
- **Processing**: Idempotent, deletes org permissions and revokes user grants

#### 3. `organization.member_added` from organization_service
- **Handler**: `handle_org_member_added()`
- **Purpose**: Auto-grant organization permissions to new member
- **Processing**: Idempotent, grants only if permission doesn't exist

#### 4. `organization.member_removed` from organization_service
- **Handler**: `handle_org_member_removed()`
- **Purpose**: Revoke organization-granted permissions from removed member
- **Processing**: Idempotent, revokes only ORGANIZATION-sourced permissions

---

## Core Concepts

### Concept 1: Permission Priority Hierarchy
The authorization service evaluates permissions in a strict priority order:

1. **Admin-Granted Permissions** (Highest Priority): Explicit grants by administrators override all other sources. This allows admins to grant access regardless of subscription or organization status.

2. **Organization Permissions**: If user is member of an organization with configured permissions, those permissions apply. Requires organization plan to meet resource requirements.

3. **Subscription-Based Permissions**: User's subscription tier determines baseline access to features. Free tier gets basic features, Pro gets advanced, Enterprise gets full access.

4. **User-Specific Permissions**: Non-admin specific grants for the user.

5. **System Defaults** (Lowest Priority): Fallback when no other permission source applies.

This hierarchy ensures that administrative overrides always work, while subscription and organization contexts provide scalable default permissions.

### Concept 2: Access Level Inheritance
Higher access levels automatically satisfy lower-level requirements:
- A user with OWNER access can perform any operation
- A user with ADMIN access can perform READ_WRITE and READ_ONLY operations
- A user with READ_WRITE access can perform READ_ONLY operations

This simplifies permission management by avoiding redundant grants.

### Concept 3: Subscription-Tier Feature Gating
Resources can be gated behind subscription tiers:
- **FREE**: Basic features available to all users
- **PRO**: Advanced features for paying customers
- **ENTERPRISE**: Full feature access plus admin capabilities
- **CUSTOM**: Tailored access for special arrangements

Each resource defines its minimum required tier, and users with that tier or higher gain access automatically.

### Concept 4: Permission Expiration
Permissions can have optional expiration dates:
- Time-limited access for trials or temporary needs
- Automatic cleanup of expired permissions
- Prevents permission accumulation over time

### Concept 5: Audit Trail
Every permission operation is logged:
- Who performed the action
- What changed (before/after)
- When it happened
- Why it was done (reason)
- Whether it succeeded

This supports compliance requirements and enables troubleshooting.

---

## High-Level Business Rules

### Permission Check Rules (BR-AUTH-001 to BR-AUTH-010)

**BR-AUTH-001: User Must Be Active**
- User MUST have is_active=true to pass any access check
- Inactive users receive ACCESS_DENIED regardless of permissions
- Error: "User not found or inactive"
- Example: `user.is_active == true`

**BR-AUTH-002: Admin Grant Priority**
- Admin-granted permissions (permission_source=ADMIN_GRANT) MUST be evaluated first
- Admin grants override subscription and organization permissions
- Example: `admin_grant > org_permission > subscription`

**BR-AUTH-003: Access Level Hierarchy**
- Higher access levels MUST satisfy lower level requirements
- OWNER(4) > ADMIN(3) > READ_WRITE(2) > READ_ONLY(1) > NONE(0)
- Example: `user_level >= required_level`

**BR-AUTH-004: Subscription Tier Hierarchy**
- Higher tiers MUST include all permissions from lower tiers
- CUSTOM(3) > ENTERPRISE(2) > PRO(1) > FREE(0)
- Example: `user_tier >= resource_required_tier`

**BR-AUTH-005: Organization Membership Required**
- Organization permissions ONLY apply if user is active member
- System MUST verify membership before checking org permissions
- Error: "User is not a member of the organization"

**BR-AUTH-006: Organization Plan Requirement**
- Organization permissions require org plan to meet resource requirements
- CUSTOM > ENTERPRISE > GROWTH > STARTUP
- Example: `org_plan >= permission.org_plan_required`

**BR-AUTH-007: Expired Permission Invalid**
- Permissions with expires_at in the past MUST NOT grant access
- System validates expiration during access check
- Error: "Permission has expired"

**BR-AUTH-008: Permission Source Tracking**
- Every permission MUST have a valid permission_source
- Valid sources: SUBSCRIPTION, ORGANIZATION, ADMIN_GRANT, SYSTEM_DEFAULT
- Used for audit and priority determination

**BR-AUTH-009: Access Check Logging**
- Every access check MUST be logged to audit trail
- Log includes: user_id, resource, action, result, reason
- Enables security analysis and debugging

**BR-AUTH-010: Deny Default**
- If no permission source grants access, system MUST deny
- Returns has_access=false with detailed reason
- Publishes access.denied event

### Permission Grant Rules (BR-GRANT-001 to BR-GRANT-010)

**BR-GRANT-001: Target User Must Exist**
- Permission grant MUST fail if target user does not exist
- System validates user existence before granting
- Error: "Cannot grant permission to non-existent user"

**BR-GRANT-002: Valid Resource Type Required**
- Resource type MUST be from defined ResourceType enum
- Valid: mcp_tool, prompt, resource, api_endpoint, database, file_storage, compute, ai_model
- Error: "Invalid resource type"

**BR-GRANT-003: Valid Access Level Required**
- Access level MUST be from defined AccessLevel enum
- Valid: none, read_only, read_write, admin, owner
- Error: "Invalid access level"

**BR-GRANT-004: Expiry Date Future Only**
- If expires_at is provided, it MUST be in the future
- System rejects past dates during grant
- Error: "Expiry date must be in the future"

**BR-GRANT-005: Grant Action Logging**
- Every grant operation MUST be logged to audit trail
- Log includes: user_id, resource, new_access_level, granted_by, reason
- Required for compliance

**BR-GRANT-006: Permission Event Publication**
- Successful grant MUST publish permission.granted event
- Event includes full permission details
- Enables downstream system synchronization

**BR-GRANT-007: Idempotent Grant**
- Granting existing permission SHOULD update, not duplicate
- System checks for existing permission before insert
- Prevents permission record bloat

**BR-GRANT-008: Organization Context Preservation**
- If granted via organization, organization_id MUST be stored
- Enables proper cleanup when user leaves organization
- Example: `permission.organization_id = org_id`

**BR-GRANT-009: Grantor Tracking**
- Admin grants MUST record granted_by_user_id
- Enables accountability and audit
- Example: `permission.granted_by_user_id = admin_id`

**BR-GRANT-010: Active Status Default**
- New permissions MUST default to is_active=true
- Inactive permissions are effectively soft-deleted
- Example: `permission.is_active = true`

### Permission Revoke Rules (BR-REVOKE-001 to BR-REVOKE-005)

**BR-REVOKE-001: Revoke Non-Existent Graceful**
- Revoking non-existent permission MAY return success or failure
- System logs the attempt regardless
- Design decision: return false if not found

**BR-REVOKE-002: Previous State Logging**
- Revoke MUST log the previous access level
- Enables audit trail showing what was removed
- Example: `audit.old_access_level = previous.access_level`

**BR-REVOKE-003: Revoke Event Publication**
- Successful revoke MUST publish permission.revoked event
- Event includes previous access level
- Enables downstream cache invalidation

**BR-REVOKE-004: Revoker Tracking**
- Revoke MUST record revoked_by_user_id if provided
- Enables accountability and audit
- Example: `audit.performed_by_user_id = revoker_id`

**BR-REVOKE-005: Reason Recording**
- Revoke SHOULD include reason for audit purposes
- Helps explain permission changes
- Example: `audit.reason = "Policy change"`

### Bulk Operation Rules (BR-BULK-001 to BR-BULK-005)

**BR-BULK-001: Partial Failure Allowed**
- Bulk operations MUST continue on individual failures
- Each operation result is recorded separately
- Summary shows success/failure counts

**BR-BULK-002: Batch ID Tracking**
- Each bulk operation MUST generate unique batch_id
- Enables correlation of related operations
- Example: `batch_id = uuid()`

**BR-BULK-003: Individual Result Reporting**
- Bulk response MUST include result for each operation
- Includes success status and error message if failed
- Enables targeted retry of failures

**BR-BULK-004: Execution Time Tracking**
- Bulk operations SHOULD track execution time
- Helps identify performance issues
- Example: `execution_time = end - start`

**BR-BULK-005: Bulk Event Publication**
- Bulk operations SHOULD publish aggregate events
- permissions.bulk_granted or permissions.bulk_revoked
- Includes affected user_ids and counts

### Event Handling Rules (BR-EVENT-001 to BR-EVENT-005)

**BR-EVENT-001: User Deletion Cleanup**
- On user.deleted event, ALL user permissions MUST be revoked
- Prevents orphaned permission records
- Cleanup logged for audit

**BR-EVENT-002: Organization Deletion Cleanup**
- On organization.deleted, org permissions and related user permissions MUST be cleaned
- Two-phase: delete org permissions, revoke org-granted user permissions
- Cleanup logged for audit

**BR-EVENT-003: Member Add Auto-Grant**
- On organization.member_added, org permissions SHOULD be auto-granted to new member
- Only grants if permission doesn't already exist
- Enables seamless onboarding

**BR-EVENT-004: Member Remove Auto-Revoke**
- On organization.member_removed, ORGANIZATION-sourced permissions SHOULD be revoked
- Only revokes permissions with source=ORGANIZATION
- Preserves admin-granted and subscription permissions

**BR-EVENT-005: Idempotent Event Handling**
- Event handlers MUST be idempotent
- Processing same event twice produces same result
- Prevents duplicate operations on retry

---

## Summary

| Metric | Count |
|--------|-------|
| Entities | 4 (ResourcePermission, UserPermissionRecord, OrganizationPermission, PermissionAuditLog) |
| Domain Scenarios | 8 |
| Published Events | 5 |
| Consumed Events | 4 |
| Business Rules | 35 |
| Core Concepts | 5 |
