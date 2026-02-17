# Authorization Service - Product Requirements Document (PRD)

## Product Overview

**Service Name**: authorization_service
**Port**: 8203
**Purpose**: Comprehensive resource-based access control (RBAC) service that validates user permissions across multiple sources including subscription tiers, organization memberships, and administrative grants.

### Key Capabilities
- **Multi-Source Permission Resolution**: Evaluates permissions from admin grants, organizations, subscriptions, and system defaults
- **Hierarchical Access Control**: Supports access level hierarchy (owner > admin > read_write > read_only > none)
- **Subscription-Based Feature Gating**: Automatically grants/denies access based on subscription tier
- **Organization Permission Inheritance**: Members inherit permissions from their organization
- **Bulk Operations**: Efficient batch permission grant/revoke operations
- **Audit Trail**: Complete logging of all permission changes and access checks

### Service Boundaries
- **Owns**: Permission configurations, user permission records, organization permissions, audit logs
- **Consumes**: User info from account_service, organization info from organization_service
- **Publishes**: permission.granted, permission.revoked, access.denied, permissions.bulk_granted, permissions.bulk_revoked

### Dependencies
| Service | Purpose |
|---------|---------|
| account_service | User existence and status verification |
| organization_service | Organization membership and plan verification |
| PostgreSQL | Permission data persistence |
| NATS JetStream | Event publishing and subscription |

---

## Target Users

### Primary Users

#### End Users
- Check their own permission status
- View accessible resources based on subscription
- Understand why access was granted or denied

#### Administrators
- Grant/revoke individual permissions
- Perform bulk permission operations
- Configure organization-level permissions
- Review permission audit logs
- Manage subscription-based access rules

### Internal Users

#### Other Services
- **API Gateway**: Validates access before routing requests
- **All Protected Services**: Check user permissions before operations
- **Audit Service**: Receives permission change events
- **Session Service**: May invalidate sessions on permission revocation

#### API Consumers
- Third-party integrations needing permission validation
- Admin dashboards managing user access

### Personas

#### 1. Platform Administrator (Admin Alex)
**Role**: Manages user access across the platform
**Needs**:
- Grant emergency access to specific resources
- Bulk update permissions during migrations
- Audit who has access to what
**Pain Points**:
- Complex permission inheritance can be confusing
- Need visibility into effective permissions from all sources

#### 2. Organization Manager (Manager Maria)
**Role**: Manages access for organization members
**Needs**:
- Configure default permissions for org members
- Onboard new members with appropriate access
- Revoke access when members leave
**Pain Points**:
- Manual permission management is time-consuming
- Ensuring consistent access across members

#### 3. Service Developer (Dev Dana)
**Role**: Integrates services with authorization
**Needs**:
- Simple API to check user permissions
- Clear error messages for debugging
- Reliable performance for inline access checks
**Pain Points**:
- Permission check latency impacts user experience
- Understanding permission resolution order

#### 4. End User (User Uma)
**Role**: Accesses protected resources
**Needs**:
- Clear feedback on why access was denied
- Understanding of what subscription provides
- Self-service permission status checking
**Pain Points**:
- Confusing permission denied messages
- Not knowing which upgrade grants desired access

---

## Epics and User Stories

### Epic 1: Resource Access Validation
**Goal**: Enable services to validate user access to protected resources
**Priority**: High (Critical Path)

**User Stories**:

**US-1.1**: As a service developer, I want to check if a user can access a resource so that I can enforce access control
- **Acceptance Criteria**:
  - [ ] Returns has_access boolean with reason
  - [ ] Returns effective access level and source
  - [ ] Evaluates permissions in priority order
  - [ ] Completes in < 100ms (p95)
- **API**: `POST /api/v1/authorization/check-access`

**US-1.2**: As a service developer, I want to know the permission source so that I can provide appropriate user feedback
- **Acceptance Criteria**:
  - [ ] Returns permission_source (subscription, organization, admin_grant, system_default)
  - [ ] Includes subscription tier if applicable
  - [ ] Includes organization plan if applicable
- **API**: `POST /api/v1/authorization/check-access`

**US-1.3**: As a security team member, I want denied access attempts logged so that I can detect suspicious activity
- **Acceptance Criteria**:
  - [ ] Publishes access.denied event on denial
  - [ ] Event includes user_id, resource, required_level
  - [ ] Event includes denial reason
- **Events**: `access.denied`

**US-1.4**: As a user, I want clear denial reasons so that I understand why I can't access a resource
- **Acceptance Criteria**:
  - [ ] Response includes human-readable reason
  - [ ] Reason specifies what's missing (subscription upgrade, permission grant)
  - [ ] Includes required vs actual access level
- **API**: `POST /api/v1/authorization/check-access`

### Epic 2: Permission Grant Management
**Goal**: Allow administrators to grant specific resource permissions to users
**Priority**: High

**User Stories**:

**US-2.1**: As an admin, I want to grant a user permission to a resource so that they can access it
- **Acceptance Criteria**:
  - [ ] Accepts user_id, resource_type, resource_name, access_level
  - [ ] Validates target user exists and is active
  - [ ] Records who granted the permission
  - [ ] Publishes permission.granted event
- **API**: `POST /api/v1/authorization/grant`

**US-2.2**: As an admin, I want to grant time-limited permissions so that temporary access expires automatically
- **Acceptance Criteria**:
  - [ ] Accepts optional expires_at datetime
  - [ ] Validates expiry is in the future
  - [ ] Expired permissions are not effective
  - [ ] System cleans up expired permissions
- **API**: `POST /api/v1/authorization/grant`

**US-2.3**: As an admin, I want to specify a reason for grants so that audits are meaningful
- **Acceptance Criteria**:
  - [ ] Accepts optional reason field
  - [ ] Reason is logged in audit trail
  - [ ] Reason included in events
- **API**: `POST /api/v1/authorization/grant`

**US-2.4**: As an admin, I want admin grants to override other permissions so that I can handle special cases
- **Acceptance Criteria**:
  - [ ] Admin-granted permissions evaluated first
  - [ ] Override subscription and organization permissions
  - [ ] Clearly marked as permission_source=ADMIN_GRANT
- **API**: `POST /api/v1/authorization/grant`

### Epic 3: Permission Revocation
**Goal**: Allow administrators to remove resource permissions from users
**Priority**: High

**User Stories**:

**US-3.1**: As an admin, I want to revoke a user's permission so that they can no longer access a resource
- **Acceptance Criteria**:
  - [ ] Accepts user_id, resource_type, resource_name
  - [ ] Records who revoked the permission
  - [ ] Publishes permission.revoked event
  - [ ] Previous access level logged for audit
- **API**: `POST /api/v1/authorization/revoke`

**US-3.2**: As an admin, I want to specify a reason for revocation so that audits are meaningful
- **Acceptance Criteria**:
  - [ ] Accepts optional reason field
  - [ ] Reason logged in audit trail
  - [ ] Reason included in events
- **API**: `POST /api/v1/authorization/revoke`

**US-3.3**: As a security admin, I want to quickly revoke compromised permissions so that I can respond to incidents
- **Acceptance Criteria**:
  - [ ] Revocation takes effect immediately
  - [ ] No caching delays access denial
  - [ ] Session service notified for active sessions
- **API**: `POST /api/v1/authorization/revoke`

**US-3.4**: As an admin, I want to revoke non-existent permissions gracefully so that bulk operations don't fail
- **Acceptance Criteria**:
  - [ ] Returns success or clear not-found indication
  - [ ] Does not throw exception
  - [ ] Logs the attempt
- **API**: `POST /api/v1/authorization/revoke`

### Epic 4: Bulk Permission Operations
**Goal**: Enable efficient batch permission management
**Priority**: Medium

**User Stories**:

**US-4.1**: As an admin, I want to grant permissions to multiple users at once so that onboarding is efficient
- **Acceptance Criteria**:
  - [ ] Accepts list of grant operations
  - [ ] Processes each independently
  - [ ] Returns success/failure for each
  - [ ] Publishes permissions.bulk_granted event
- **API**: `POST /api/v1/authorization/bulk-grant`

**US-4.2**: As an admin, I want to revoke permissions from multiple users at once so that security incidents can be handled quickly
- **Acceptance Criteria**:
  - [ ] Accepts list of revoke operations
  - [ ] Processes each independently
  - [ ] Returns success/failure for each
  - [ ] Publishes permissions.bulk_revoked event
- **API**: `POST /api/v1/authorization/bulk-revoke`

**US-4.3**: As an admin, I want to see detailed results for bulk operations so that I can identify and retry failures
- **Acceptance Criteria**:
  - [ ] Returns individual result for each operation
  - [ ] Includes error message for failures
  - [ ] Summary shows total/success/failed counts
- **API**: `POST /api/v1/authorization/bulk-grant`, `POST /api/v1/authorization/bulk-revoke`

**US-4.4**: As an admin, I want bulk operations to continue on individual failures so that one bad record doesn't block others
- **Acceptance Criteria**:
  - [ ] Partial success allowed
  - [ ] Failed operations logged with reason
  - [ ] Can retry failed operations individually
- **API**: `POST /api/v1/authorization/bulk-grant`, `POST /api/v1/authorization/bulk-revoke`

### Epic 5: Permission Visibility
**Goal**: Provide visibility into user permissions and accessible resources
**Priority**: Medium

**User Stories**:

**US-5.1**: As a user, I want to see my permission summary so that I understand my access rights
- **Acceptance Criteria**:
  - [ ] Shows total permissions by type
  - [ ] Shows permissions by source
  - [ ] Shows permissions by access level
  - [ ] Identifies permissions expiring soon
- **API**: `GET /api/v1/authorization/user-permissions/{user_id}`

**US-5.2**: As an admin, I want to see all resources a user can access so that I can audit their permissions
- **Acceptance Criteria**:
  - [ ] Lists all accessible resources
  - [ ] Shows permission source for each
  - [ ] Can filter by resource type
  - [ ] Includes subscription-based resources
- **API**: `GET /api/v1/authorization/user-resources/{user_id}`

**US-5.3**: As a user, I want to know my subscription tier so that I understand baseline access
- **Acceptance Criteria**:
  - [ ] Permission summary includes subscription_tier
  - [ ] Accessible resources show subscription_required
  - [ ] Clear indication of subscription-based permissions
- **API**: `GET /api/v1/authorization/user-permissions/{user_id}`

**US-5.4**: As an admin, I want to see organization context in permissions so that I understand inheritance
- **Acceptance Criteria**:
  - [ ] Summary includes organization_id and plan
  - [ ] Resources show if from organization
  - [ ] Clear distinction between direct and inherited permissions
- **API**: `GET /api/v1/authorization/user-permissions/{user_id}`

### Epic 6: Service Administration
**Goal**: Provide administrative capabilities for the authorization service
**Priority**: Medium

**User Stories**:

**US-6.1**: As an admin, I want to clean up expired permissions so that the database stays clean
- **Acceptance Criteria**:
  - [ ] Removes/deactivates expired permissions
  - [ ] Returns count of cleaned permissions
  - [ ] Can be triggered manually or scheduled
- **API**: `POST /api/v1/authorization/cleanup-expired`

**US-6.2**: As an ops team member, I want service statistics so that I can monitor authorization usage
- **Acceptance Criteria**:
  - [ ] Shows total permissions count
  - [ ] Shows active users count
  - [ ] Shows resource types count
  - [ ] Includes operational metrics
- **API**: `GET /api/v1/authorization/stats`

**US-6.3**: As an ops team member, I want health checks so that I can monitor service availability
- **Acceptance Criteria**:
  - [ ] Basic health check returns quickly
  - [ ] Detailed health shows database connectivity
  - [ ] Returns degraded status on partial failures
- **API**: `GET /health`, `GET /health/detailed`

**US-6.4**: As a developer, I want service info so that I understand service capabilities
- **Acceptance Criteria**:
  - [ ] Lists all supported capabilities
  - [ ] Documents available endpoints
  - [ ] Shows service version
- **API**: `GET /api/v1/authorization/info`

### Epic 7: Event-Driven Synchronization
**Goal**: Maintain permission consistency through event handling
**Priority**: High

**User Stories**:

**US-7.1**: As the system, I want to clean up permissions when users are deleted so that orphaned records don't exist
- **Acceptance Criteria**:
  - [ ] Subscribes to user.deleted events
  - [ ] Revokes all permissions for deleted user
  - [ ] Logs cleanup action
- **Events**: Consumes `user.deleted`

**US-7.2**: As the system, I want to clean up permissions when organizations are deleted so that orphaned records don't exist
- **Acceptance Criteria**:
  - [ ] Subscribes to organization.deleted events
  - [ ] Deletes organization permission configs
  - [ ] Revokes user permissions granted by org
- **Events**: Consumes `organization.deleted`

**US-7.3**: As the system, I want to auto-grant permissions when users join organizations so that onboarding is seamless
- **Acceptance Criteria**:
  - [ ] Subscribes to organization.member_added events
  - [ ] Grants configured org permissions to new member
  - [ ] Skips if permission already exists
- **Events**: Consumes `organization.member_added`

**US-7.4**: As the system, I want to auto-revoke permissions when users leave organizations so that access is properly removed
- **Acceptance Criteria**:
  - [ ] Subscribes to organization.member_removed events
  - [ ] Revokes org-sourced permissions
  - [ ] Preserves admin-granted and subscription permissions
- **Events**: Consumes `organization.member_removed`

---

## API Surface Documentation

### Base URL
`http://localhost:8203/api/v1`

### Authentication
- **Method**: JWT Bearer Token (via API Gateway)
- **Header**: `Authorization: Bearer <token>`
- **Internal**: `X-Internal-Call: true` bypasses auth for service-to-service

---

### Endpoint: Check Resource Access
- **Method**: `POST`
- **Path**: `/api/v1/authorization/check-access`
- **Description**: Check if a user has access to a specific resource at the required level

**Request Body**:
```json
{
  "user_id": "string (required)",
  "resource_type": "string (required, enum: mcp_tool|prompt|resource|api_endpoint|database|file_storage|compute|ai_model)",
  "resource_name": "string (required)",
  "required_access_level": "string (optional, default: read_only, enum: none|read_only|read_write|admin|owner)",
  "organization_id": "string (optional)",
  "context": "object (optional, additional context)"
}
```

**Response** (200 OK):
```json
{
  "has_access": true,
  "user_access_level": "read_write",
  "permission_source": "subscription",
  "subscription_tier": "pro",
  "organization_plan": null,
  "reason": "Subscription access: read_write",
  "expires_at": null,
  "metadata": {
    "subscription_required": "pro",
    "resource_category": "ai_tools"
  }
}
```

**Error Responses**:
| Status | Code | Description |
|--------|------|-------------|
| 400 | BAD_REQUEST | Invalid request format |
| 422 | VALIDATION_ERROR | Invalid resource_type or access_level |
| 500 | INTERNAL_ERROR | Access check failed |
| 503 | SERVICE_UNAVAILABLE | Service not initialized |

**Example**:
```bash
curl -X POST http://localhost:8203/api/v1/authorization/check-access \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "resource_type": "api_endpoint",
    "resource_name": "/api/admin",
    "required_access_level": "admin"
  }'
```

---

### Endpoint: Grant Permission
- **Method**: `POST`
- **Path**: `/api/v1/authorization/grant`
- **Description**: Grant resource permission to a user

**Request Body**:
```json
{
  "user_id": "string (required)",
  "resource_type": "string (required, enum)",
  "resource_name": "string (required)",
  "access_level": "string (required, enum)",
  "permission_source": "string (required, enum: subscription|organization|admin_grant|system_default)",
  "granted_by_user_id": "string (optional)",
  "organization_id": "string (optional)",
  "expires_at": "datetime (optional, ISO8601, must be future)",
  "reason": "string (optional)"
}
```

**Response** (200 OK):
```json
{
  "message": "Permission granted successfully"
}
```

**Error Responses**:
| Status | Code | Description |
|--------|------|-------------|
| 400 | BAD_REQUEST | Failed to grant permission or invalid user |
| 422 | VALIDATION_ERROR | Invalid enum values or expiry in past |
| 500 | INTERNAL_ERROR | Grant operation failed |
| 503 | SERVICE_UNAVAILABLE | Service not initialized |

**Example**:
```bash
curl -X POST http://localhost:8203/api/v1/authorization/grant \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "resource_type": "api_endpoint",
    "resource_name": "/api/admin",
    "access_level": "admin",
    "permission_source": "admin_grant",
    "granted_by_user_id": "admin_001",
    "reason": "Temporary admin access for migration"
  }'
```

---

### Endpoint: Revoke Permission
- **Method**: `POST`
- **Path**: `/api/v1/authorization/revoke`
- **Description**: Revoke resource permission from a user

**Request Body**:
```json
{
  "user_id": "string (required)",
  "resource_type": "string (required, enum)",
  "resource_name": "string (required)",
  "revoked_by_user_id": "string (optional)",
  "reason": "string (optional)"
}
```

**Response** (200 OK):
```json
{
  "message": "Permission revoked successfully"
}
```

**Error Responses**:
| Status | Code | Description |
|--------|------|-------------|
| 404 | NOT_FOUND | Permission not found |
| 500 | INTERNAL_ERROR | Revoke operation failed |
| 503 | SERVICE_UNAVAILABLE | Service not initialized |

**Example**:
```bash
curl -X POST http://localhost:8203/api/v1/authorization/revoke \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "resource_type": "api_endpoint",
    "resource_name": "/api/admin",
    "revoked_by_user_id": "admin_001",
    "reason": "Migration completed"
  }'
```

---

### Endpoint: Get User Permissions
- **Method**: `GET`
- **Path**: `/api/v1/authorization/user-permissions/{user_id}`
- **Description**: Get comprehensive permission summary for a user

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| user_id | string | Target user identifier |

**Response** (200 OK):
```json
{
  "user_id": "user_123",
  "subscription_tier": "pro",
  "organization_id": "org_001",
  "organization_plan": "growth",
  "total_permissions": 15,
  "permissions_by_type": {
    "api_endpoint": 5,
    "mcp_tool": 3,
    "ai_model": 7
  },
  "permissions_by_source": {
    "subscription": 10,
    "organization": 3,
    "admin_grant": 2
  },
  "permissions_by_level": {
    "read_only": 5,
    "read_write": 8,
    "admin": 2
  },
  "expires_soon_count": 1,
  "last_access_check": "2025-01-01T12:00:00Z",
  "summary_generated_at": "2025-01-01T12:05:00Z"
}
```

**Error Responses**:
| Status | Code | Description |
|--------|------|-------------|
| 404 | NOT_FOUND | User not found |
| 500 | INTERNAL_ERROR | Failed to get permissions |
| 503 | SERVICE_UNAVAILABLE | Service not initialized |

---

### Endpoint: List User Accessible Resources
- **Method**: `GET`
- **Path**: `/api/v1/authorization/user-resources/{user_id}`
- **Description**: List all resources accessible to a user

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| user_id | string | Target user identifier |

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| resource_type | string | - | Filter by resource type |

**Response** (200 OK):
```json
{
  "user_id": "user_123",
  "resource_type_filter": "api_endpoint",
  "accessible_resources": [
    {
      "resource_type": "api_endpoint",
      "resource_name": "/api/data",
      "access_level": "read_write",
      "permission_source": "subscription",
      "expires_at": null,
      "subscription_required": "pro",
      "resource_category": "data"
    }
  ],
  "total_count": 1
}
```

---

### Endpoint: Bulk Grant Permissions
- **Method**: `POST`
- **Path**: `/api/v1/authorization/bulk-grant`
- **Description**: Grant multiple permissions in a single operation

**Request Body**:
```json
{
  "operations": [
    {
      "user_id": "user_001",
      "resource_type": "api_endpoint",
      "resource_name": "/api/data",
      "access_level": "read_write",
      "permission_source": "admin_grant",
      "granted_by_user_id": "admin_001"
    },
    {
      "user_id": "user_002",
      "resource_type": "api_endpoint",
      "resource_name": "/api/data",
      "access_level": "read_only",
      "permission_source": "admin_grant",
      "granted_by_user_id": "admin_001"
    }
  ],
  "executed_by_user_id": "admin_001",
  "batch_reason": "Team onboarding"
}
```

**Response** (200 OK):
```json
{
  "total_operations": 2,
  "successful": 2,
  "failed": 0,
  "results": [
    {
      "operation_id": "uuid",
      "operation_type": "grant",
      "target_user_id": "user_001",
      "resource_type": "api_endpoint",
      "resource_name": "/api/data",
      "success": true,
      "error_message": null,
      "processed_at": "2025-01-01T12:00:00Z"
    },
    {
      "operation_id": "uuid",
      "operation_type": "grant",
      "target_user_id": "user_002",
      "resource_type": "api_endpoint",
      "resource_name": "/api/data",
      "success": true,
      "error_message": null,
      "processed_at": "2025-01-01T12:00:01Z"
    }
  ]
}
```

---

### Endpoint: Bulk Revoke Permissions
- **Method**: `POST`
- **Path**: `/api/v1/authorization/bulk-revoke`
- **Description**: Revoke multiple permissions in a single operation

**Request Body**:
```json
{
  "operations": [
    {
      "user_id": "user_001",
      "resource_type": "api_endpoint",
      "resource_name": "/api/data",
      "revoked_by_user_id": "admin_001",
      "reason": "Access review"
    }
  ],
  "executed_by_user_id": "admin_001",
  "batch_reason": "Quarterly access review"
}
```

**Response** (200 OK):
```json
{
  "total_operations": 1,
  "successful": 1,
  "failed": 0,
  "results": [
    {
      "operation_id": "uuid",
      "operation_type": "revoke",
      "target_user_id": "user_001",
      "resource_type": "api_endpoint",
      "resource_name": "/api/data",
      "success": true,
      "error_message": null,
      "processed_at": "2025-01-01T12:00:00Z"
    }
  ]
}
```

---

### Endpoint: Cleanup Expired Permissions
- **Method**: `POST`
- **Path**: `/api/v1/authorization/cleanup-expired`
- **Description**: Clean up expired permissions (admin operation)

**Response** (200 OK):
```json
{
  "message": "Expired permissions cleaned up successfully",
  "cleaned_count": 15
}
```

---

### Endpoint: Service Statistics
- **Method**: `GET`
- **Path**: `/api/v1/authorization/stats`
- **Description**: Get service statistics and metrics

**Response** (200 OK):
```json
{
  "service": "authorization_service",
  "version": "1.0.0",
  "status": "operational",
  "uptime": "running",
  "endpoints_count": 8,
  "statistics": {
    "total_permissions": 1500,
    "active_users": 250,
    "resource_types": 8
  }
}
```

---

### Endpoint: Service Info
- **Method**: `GET`
- **Path**: `/api/v1/authorization/info`
- **Description**: Get service information and capabilities

**Response** (200 OK):
```json
{
  "service": "authorization_service",
  "version": "1.0.0",
  "description": "Comprehensive resource authorization and permission management",
  "capabilities": {
    "resource_access_control": true,
    "multi_level_authorization": ["subscription", "organization", "admin"],
    "permission_management": true,
    "bulk_operations": true
  },
  "endpoints": {
    "check_access": "/api/v1/authorization/check-access",
    "grant_permission": "/api/v1/authorization/grant",
    "revoke_permission": "/api/v1/authorization/revoke",
    "user_permissions": "/api/v1/authorization/user-permissions",
    "bulk_operations": "/api/v1/authorization/bulk"
  }
}
```

---

### Endpoint: Health Check
- **Method**: `GET`
- **Path**: `/health`
- **Description**: Basic health check

**Response** (200 OK):
```json
{
  "status": "healthy",
  "service": "authorization_service",
  "port": 8203,
  "version": "1.0.0"
}
```

---

### Endpoint: Detailed Health Check
- **Method**: `GET`
- **Path**: `/health/detailed`
- **Description**: Detailed health check with dependency status

**Response** (200 OK):
```json
{
  "service": "authorization_service",
  "status": "operational",
  "port": 8203,
  "version": "1.0.0",
  "database_connected": true,
  "timestamp": "2025-01-01T12:00:00Z"
}
```

---

## Functional Requirements

### Core Functionality

**FR-001: Resource Access Check**
- System SHALL evaluate user access to resources with priority: admin_grant > organization > subscription > user_specific > system_default
- System SHALL return has_access boolean, access_level, and permission_source
- System SHALL complete access checks in < 100ms (p95)

**FR-002: User Validation**
- System SHALL verify user exists and is_active before granting access
- System SHALL deny access to inactive users with clear reason
- System SHALL fetch user info from account_service

**FR-003: Permission Grant**
- System SHALL create permission records with user_id, resource, level, source
- System SHALL record granted_by_user_id for admin grants
- System SHALL publish permission.granted event on success

**FR-004: Permission Revoke**
- System SHALL deactivate or delete permission records
- System SHALL record previous access level for audit
- System SHALL publish permission.revoked event on success

**FR-005: Bulk Operations**
- System SHALL process multiple operations in single request
- System SHALL continue processing on individual failures
- System SHALL return individual results with success/failure status

**FR-006: Permission Expiration**
- System SHALL support optional expires_at for time-limited permissions
- System SHALL validate expiry is in the future
- System SHALL not grant access for expired permissions

**FR-007: Permission Summary**
- System SHALL aggregate user permissions by type, source, and level
- System SHALL identify permissions expiring soon (within 7 days)
- System SHALL include subscription and organization context

**FR-008: Resource Listing**
- System SHALL list all resources accessible to a user
- System SHALL include subscription-based resources
- System SHALL support filtering by resource_type

### Validation

**FR-009: Input Validation**
- System SHALL validate resource_type against enum values
- System SHALL validate access_level against enum values
- System SHALL return 422 with field details on validation failure

**FR-010: User ID Validation**
- System SHALL validate user_id is non-empty string
- System SHALL verify user exists for grant operations
- System SHALL return appropriate error for invalid users

### Event Handling

**FR-011: Event Publishing**
- System SHALL publish permission.granted on successful grants
- System SHALL publish permission.revoked on successful revokes
- System SHALL publish access.denied on access denials

**FR-012: Event Consumption**
- System SHALL subscribe to user.deleted events
- System SHALL subscribe to organization.deleted events
- System SHALL subscribe to organization.member_added/removed events

**FR-013: User Deletion Cleanup**
- System SHALL revoke all permissions when user is deleted
- System SHALL log cleanup operations
- System SHALL handle cleanup failures gracefully

**FR-014: Organization Member Sync**
- System SHALL auto-grant org permissions on member_added
- System SHALL auto-revoke org permissions on member_removed
- System SHALL not duplicate existing permissions

### Administration

**FR-015: Expired Permission Cleanup**
- System SHALL provide endpoint to clean expired permissions
- System SHALL return count of cleaned permissions
- System SHALL log cleanup operations

**FR-016: Service Statistics**
- System SHALL expose total permissions count
- System SHALL expose active users count
- System SHALL expose resource types count

**FR-017: Health Checks**
- System SHALL expose /health for basic status
- System SHALL expose /health/detailed for dependency status
- System SHALL verify database connectivity in detailed check

---

## Non-Functional Requirements

### Performance

**NFR-001: Response Time**
- Access check requests SHALL complete in < 100ms (p95)
- Permission grant/revoke SHALL complete in < 200ms (p95)
- Bulk operations SHALL process 100 operations in < 5s

**NFR-002: Throughput**
- System SHALL handle 2000 access checks/second
- System SHALL handle 500 permission modifications/second
- System SHALL scale horizontally

### Reliability

**NFR-003: Availability**
- System SHALL maintain 99.9% uptime
- System SHALL gracefully degrade on dependency failures
- System SHALL cache user/org info to reduce external calls

**NFR-004: Data Durability**
- All permissions SHALL be persisted to PostgreSQL
- Events SHALL be delivered at-least-once via NATS JetStream
- Audit logs SHALL be immutable

**NFR-005: Consistency**
- Permission changes SHALL be immediately effective
- No stale permission cache SHALL grant unauthorized access
- Distributed consistency via event-driven updates

### Security

**NFR-006: Authentication**
- All API endpoints SHALL be protected by API Gateway
- Internal calls SHALL use X-Internal-Call header
- Audit log access SHALL require admin role

**NFR-007: Authorization**
- Grant/revoke operations SHALL require admin permissions
- Users SHALL only view their own permission summaries
- Bulk operations SHALL require elevated permissions

**NFR-008: Audit**
- All permission changes SHALL be logged
- Audit logs SHALL include actor, action, timestamp
- Audit logs SHALL be retained for compliance period

### Observability

**NFR-009: Logging**
- All requests SHALL be logged with correlation_id
- Permission decisions SHALL include reasoning in logs
- Errors SHALL include stack traces and context

**NFR-010: Metrics**
- System SHALL expose access check latency histogram
- System SHALL expose permission change counters
- System SHALL expose cache hit/miss ratios

**NFR-011: Health Monitoring**
- Service SHALL expose Prometheus-compatible metrics
- Health checks SHALL detect database connectivity issues
- Alerts SHALL trigger on error rate thresholds

### Scalability

**NFR-012: Horizontal Scaling**
- Service SHALL be stateless for horizontal scaling
- Database connections SHALL be pooled
- Event handlers SHALL support parallel processing

---

## Success Metrics

### Operational Metrics
| Metric | Target | Measurement |
|--------|--------|-------------|
| Uptime | 99.9% | Monthly |
| Access Check Latency (p95) | < 100ms | Continuous |
| Permission Change Latency (p95) | < 200ms | Continuous |
| Error Rate | < 0.1% | Hourly |
| Event Delivery Success | 99.99% | Daily |

### Business Metrics
| Metric | Target | Measurement |
|--------|--------|-------------|
| Access Checks/Day | Track volume | Daily |
| Permission Changes/Day | Track activity | Daily |
| Denied Access Rate | Monitor security | Daily |
| Subscription-Based Access | Track feature adoption | Weekly |
| Admin Override Usage | Monitor exceptions | Weekly |

### Quality Metrics
| Metric | Target | Measurement |
|--------|--------|-------------|
| Test Coverage | > 80% | Per release |
| API Documentation | 100% endpoints | Per release |
| Security Audit Compliance | 100% | Quarterly |
