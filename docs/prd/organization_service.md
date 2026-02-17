# Organization Service - Product Requirements Document (PRD)

## Product Overview

The Organization Service provides multi-tenancy and group management capabilities for the isA_user platform. It enables users to create and manage organizations (businesses, families, teams), invite and manage members, control access permissions, and share resources like subscriptions, devices, storage, and wallets among organization members.

**Business Value**: Enable collaborative use cases including family sharing of smart devices, team-based subscription management, and enterprise multi-tenant deployments.

---

## Target Users

### Primary Users
- **Family Organizers**: Parents managing family device sharing and parental controls
- **Team Administrators**: Team leads managing shared subscriptions and resources
- **Enterprise Admins**: IT administrators managing organizational deployments

### Secondary Users
- **Organization Members**: Users accessing shared resources
- **Platform Administrators**: System operators managing all organizations
- **API Developers**: Building integrations with organization features

---

## Epics and User Stories

### Epic 1: Organization Lifecycle Management
**Goal**: Enable users to create, manage, and delete organizations

**User Stories**:
- As a user, I want to create a new organization so that I can invite family members or colleagues
- As an organization owner, I want to update organization settings so that I can change billing email or plan
- As an organization owner, I want to delete my organization so that all associated data is cleaned up
- As a user, I want to see all organizations I belong to so that I can switch between contexts
- As an organization owner, I want to view organization statistics so that I understand usage patterns

### Epic 2: Member Management
**Goal**: Enable organization admins to invite and manage members

**User Stories**:
- As an admin, I want to add a new member to my organization so that they can access shared resources
- As an admin, I want to assign roles to members so that I can control their access levels
- As an admin, I want to remove a member from the organization so that they lose access
- As an admin, I want to update member permissions so that I can adjust their capabilities
- As a member, I want to leave an organization so that I can disassociate from it

### Epic 3: Context Switching
**Goal**: Enable users to switch between personal and organization contexts

**User Stories**:
- As a user, I want to switch to my organization context so that my actions are scoped to the organization
- As a user, I want to switch to personal context so that my actions are scoped to myself
- As a user, I want to see my current context so that I know which scope I'm operating in
- As the system, I want to validate context switches so that users only access authorized organizations

### Epic 4: Family Resource Sharing
**Goal**: Enable sharing of resources among organization members

**User Stories**:
- As an admin, I want to share a device with family members so that they can control it
- As an admin, I want to share a subscription with organization members so that they benefit from the plan
- As an admin, I want to share storage space with members so that we can collaborate on files
- As an admin, I want to share a wallet with spending limits so that children can make purchases
- As an admin, I want to set permissions per member so that I can control access granularly

### Epic 5: Permission and Quota Management
**Goal**: Enable fine-grained control over shared resource access

**User Stories**:
- As an admin, I want to update a member's permission level so that I can promote or demote them
- As an admin, I want to set usage quotas so that members don't exceed limits
- As an admin, I want to revoke a member's access so that they immediately lose permission
- As an admin, I want to view usage statistics so that I can monitor resource consumption

### Epic 6: Platform Administration
**Goal**: Enable platform operators to manage all organizations

**User Stories**:
- As a platform admin, I want to list all organizations so that I can monitor the platform
- As a platform admin, I want to search for organizations so that I can find specific ones
- As a platform admin, I want to filter organizations by plan so that I can analyze subscription distribution

---

## API Surface Documentation

### Health and Info Endpoints

#### GET /health
**Description**: Service health check
**Authentication**: None required
**Response Schema**:
```json
{
  "status": "healthy",
  "service": "organization_service",
  "port": 8203,
  "version": "1.0.0"
}
```
**HTTP Codes**: 200 (OK)

#### GET /info
**Description**: Service information
**Authentication**: None required
**Response Schema**:
```json
{
  "service": "organization_service",
  "version": "1.0.0",
  "description": "Organization management microservice"
}
```
**HTTP Codes**: 200 (OK)

---

### Organization Management Endpoints

#### POST /api/v1/organizations
**Description**: Create a new organization
**Authentication**: Required (JWT or internal service)
**Request Schema**:
```json
{
  "name": "string (1-100 chars, required)",
  "type": "business|family|team|enterprise (optional, default: business)",
  "billing_email": "string (valid email, required)",
  "description": "string (optional)",
  "settings": {"key": "value"} (optional JSONB)
}
```
**Response Schema**:
```json
{
  "organization_id": "org_abc123",
  "name": "My Organization",
  "type": "family",
  "billing_email": "billing@example.com",
  "status": "active",
  "plan": "free",
  "credits_pool": 0,
  "max_members": 10,
  "settings": {},
  "created_at": "2025-12-15T10:00:00Z",
  "updated_at": "2025-12-15T10:00:00Z"
}
```
**HTTP Codes**: 200 (Created), 400 (Validation Error), 401 (Unauthorized), 500 (Server Error)

#### GET /api/v1/organizations/{organization_id}
**Description**: Get organization by ID
**Authentication**: Required
**Path Parameters**:
- organization_id: Organization ID (required)
**Response Schema**: Same as POST response
**HTTP Codes**: 200 (OK), 403 (Forbidden), 404 (Not Found), 500 (Server Error)

#### PUT /api/v1/organizations/{organization_id}
**Description**: Update organization
**Authentication**: Required (Admin or Owner)
**Path Parameters**:
- organization_id: Organization ID (required)
**Request Schema**:
```json
{
  "name": "string (optional)",
  "billing_email": "string (optional)",
  "description": "string (optional)",
  "settings": {} (optional)
}
```
**Response Schema**: Same as POST response
**HTTP Codes**: 200 (OK), 400 (Validation Error), 403 (Forbidden), 404 (Not Found), 500 (Server Error)

#### DELETE /api/v1/organizations/{organization_id}
**Description**: Delete organization (Owner only)
**Authentication**: Required (Owner only)
**Path Parameters**:
- organization_id: Organization ID (required)
**Response Schema**:
```json
{
  "message": "Organization deleted successfully"
}
```
**HTTP Codes**: 200 (OK), 403 (Forbidden), 404 (Not Found), 500 (Server Error)

#### GET /api/v1/organizations
**Description**: Get user's organizations
**Authentication**: Required
**Response Schema**:
```json
{
  "organizations": [
    {
      "organization_id": "org_abc123",
      "name": "My Organization",
      ...
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```
**HTTP Codes**: 200 (OK), 500 (Server Error)

---

### Member Management Endpoints

#### POST /api/v1/organizations/{organization_id}/members
**Description**: Add member to organization
**Authentication**: Required (Admin or Owner)
**Path Parameters**:
- organization_id: Organization ID (required)
**Request Schema**:
```json
{
  "user_id": "string (required)",
  "email": "string (optional, for invitation)",
  "role": "owner|admin|member|guest (default: member)",
  "permissions": ["permission1", "permission2"] (optional)
}
```
**Response Schema**:
```json
{
  "organization_id": "org_abc123",
  "user_id": "user_xyz789",
  "role": "member",
  "status": "active",
  "permissions": [],
  "joined_at": "2025-12-15T10:00:00Z",
  "updated_at": "2025-12-15T10:00:00Z"
}
```
**HTTP Codes**: 200 (OK), 400 (Validation Error), 403 (Forbidden), 404 (Not Found), 500 (Server Error)

#### GET /api/v1/organizations/{organization_id}/members
**Description**: List organization members
**Authentication**: Required (Member access)
**Path Parameters**:
- organization_id: Organization ID (required)
**Query Parameters**:
- limit: int (1-1000, default: 100)
- offset: int (default: 0)
- role: owner|admin|member|guest (optional filter)
**Response Schema**:
```json
{
  "members": [
    {
      "organization_id": "org_abc123",
      "user_id": "user_xyz789",
      "role": "member",
      "status": "active",
      ...
    }
  ],
  "total": 5,
  "limit": 100,
  "offset": 0
}
```
**HTTP Codes**: 200 (OK), 403 (Forbidden), 404 (Not Found), 500 (Server Error)

#### PUT /api/v1/organizations/{organization_id}/members/{member_user_id}
**Description**: Update member role/permissions
**Authentication**: Required (Admin or Owner)
**Path Parameters**:
- organization_id: Organization ID (required)
- member_user_id: Member's user ID (required)
**Request Schema**:
```json
{
  "role": "admin|member|guest (optional)",
  "status": "active|suspended (optional)",
  "permissions": [] (optional)
}
```
**Response Schema**: Same as POST member response
**HTTP Codes**: 200 (OK), 400 (Validation Error), 403 (Forbidden), 404 (Not Found), 500 (Server Error)

#### DELETE /api/v1/organizations/{organization_id}/members/{member_user_id}
**Description**: Remove member from organization
**Authentication**: Required (Admin/Owner or self-removal)
**Path Parameters**:
- organization_id: Organization ID (required)
- member_user_id: Member's user ID (required)
**Response Schema**:
```json
{
  "message": "Member removed successfully"
}
```
**HTTP Codes**: 200 (OK), 400 (Validation Error), 403 (Forbidden), 404 (Not Found), 500 (Server Error)

---

### Context Switching Endpoints

#### POST /api/v1/organizations/context
**Description**: Switch user context (organization or personal)
**Authentication**: Required
**Request Schema**:
```json
{
  "organization_id": "string (optional, null for personal context)"
}
```
**Response Schema**:
```json
{
  "context_type": "organization|individual",
  "organization_id": "org_abc123",
  "organization_name": "My Organization",
  "user_role": "admin",
  "permissions": ["manage_members", "manage_sharing"],
  "credits_available": 1000
}
```
**HTTP Codes**: 200 (OK), 403 (Forbidden), 404 (Not Found), 500 (Server Error)

---

### Statistics and Analytics Endpoints

#### GET /api/v1/organizations/{organization_id}/stats
**Description**: Get organization statistics
**Authentication**: Required (Member access)
**Path Parameters**:
- organization_id: Organization ID (required)
**Response Schema**:
```json
{
  "organization_id": "org_abc123",
  "total_members": 10,
  "active_members": 8,
  "suspended_members": 2,
  "members_by_role": {
    "owner": 1,
    "admin": 2,
    "member": 7
  },
  "total_sharings": 5,
  "active_sharings": 4,
  "credits_balance": 1000,
  "storage_used_gb": 25.5
}
```
**HTTP Codes**: 200 (OK), 403 (Forbidden), 404 (Not Found), 500 (Server Error)

#### GET /api/v1/organizations/{organization_id}/usage
**Description**: Get organization usage (Admin only)
**Authentication**: Required (Admin or Owner)
**Path Parameters**:
- organization_id: Organization ID (required)
**Query Parameters**:
- start_date: datetime (optional)
- end_date: datetime (optional)
**Response Schema**:
```json
{
  "organization_id": "org_abc123",
  "period_start": "2025-12-01T00:00:00Z",
  "period_end": "2025-12-15T23:59:59Z",
  "credits_consumed": 500,
  "api_calls": 10000,
  "storage_gb_hours": 100.5,
  "active_users": 8,
  "top_users": [...],
  "usage_by_service": {...}
}
```
**HTTP Codes**: 200 (OK), 403 (Forbidden), 404 (Not Found), 500 (Server Error)

---

### Family Sharing Endpoints

#### POST /api/v1/organizations/{organization_id}/sharing
**Description**: Create shared resource
**Authentication**: Required (Admin or Owner)
**Path Parameters**:
- organization_id: Organization ID (required)
**Request Schema**:
```json
{
  "resource_type": "subscription|device|storage|wallet|album|media_library|calendar|location",
  "resource_id": "string (required)",
  "resource_name": "string (optional)",
  "shared_with_members": ["user_id1", "user_id2"] (optional),
  "share_with_all_members": false,
  "default_permission": "owner|admin|full_access|read_write|read_only|limited|view_only",
  "custom_permissions": {"user_id": "permission_level"},
  "quota_settings": {},
  "restrictions": {},
  "expires_at": "2025-12-31T23:59:59Z" (optional),
  "metadata": {}
}
```
**Response Schema**:
```json
{
  "sharing_id": "share_abc123",
  "organization_id": "org_abc123",
  "resource_type": "device",
  "resource_id": "device_xyz",
  "resource_name": "Living Room Speaker",
  "created_by": "user_owner",
  "share_with_all_members": false,
  "default_permission": "read_write",
  "status": "active",
  "total_members_shared": 3,
  "quota_settings": {},
  "restrictions": {},
  "expires_at": null,
  "created_at": "2025-12-15T10:00:00Z",
  "updated_at": null,
  "metadata": {}
}
```
**HTTP Codes**: 200 (OK), 400 (Validation Error), 403 (Forbidden), 500 (Server Error)

#### GET /api/v1/organizations/{organization_id}/sharing/{sharing_id}
**Description**: Get sharing details with member permissions
**Authentication**: Required
**Path Parameters**:
- organization_id: Organization ID (required)
- sharing_id: Sharing ID (required)
**Response Schema**:
```json
{
  "sharing": {...},
  "member_permissions": [
    {
      "user_id": "user_xyz",
      "sharing_id": "share_abc123",
      "resource_type": "device",
      "resource_id": "device_xyz",
      "permission_level": "read_write",
      "quota_allocated": {},
      "quota_used": {},
      "is_active": true,
      "granted_at": "2025-12-15T10:00:00Z",
      "last_accessed_at": null
    }
  ],
  "usage_stats": {}
}
```
**HTTP Codes**: 200 (OK), 403 (Forbidden), 404 (Not Found), 500 (Server Error)

#### PUT /api/v1/organizations/{organization_id}/sharing/{sharing_id}
**Description**: Update sharing resource
**Authentication**: Required (Admin or Creator)
**Request Schema**: Same fields as POST (all optional)
**Response Schema**: Same as POST response
**HTTP Codes**: 200 (OK), 403 (Forbidden), 404 (Not Found), 500 (Server Error)

#### DELETE /api/v1/organizations/{organization_id}/sharing/{sharing_id}
**Description**: Delete sharing resource
**Authentication**: Required (Admin or Creator)
**Response Schema**:
```json
{
  "message": "Sharing deleted successfully"
}
```
**HTTP Codes**: 200 (OK), 403 (Forbidden), 404 (Not Found), 500 (Server Error)

#### GET /api/v1/organizations/{organization_id}/sharing
**Description**: List organization sharings
**Authentication**: Required
**Query Parameters**:
- resource_type: filter by type (optional)
- status: active|paused|expired|revoked (optional)
- limit: int (1-100, default: 50)
- offset: int (default: 0)
**Response Schema**: Array of sharing responses
**HTTP Codes**: 200 (OK), 403 (Forbidden), 500 (Server Error)

#### PUT /api/v1/organizations/{organization_id}/sharing/{sharing_id}/members
**Description**: Update member's sharing permission
**Authentication**: Required (Admin)
**Request Schema**:
```json
{
  "user_id": "string (required)",
  "permission_level": "permission level (required)",
  "quota_override": {} (optional),
  "restrictions_override": {} (optional)
}
```
**Response Schema**: Member permission response
**HTTP Codes**: 200 (OK), 403 (Forbidden), 404 (Not Found), 500 (Server Error)

#### DELETE /api/v1/organizations/{organization_id}/sharing/{sharing_id}/members/{member_user_id}
**Description**: Revoke member's sharing access
**Authentication**: Required (Admin)
**Response Schema**:
```json
{
  "message": "Member access revoked successfully"
}
```
**HTTP Codes**: 200 (OK), 403 (Forbidden), 404 (Not Found), 500 (Server Error)

#### GET /api/v1/organizations/{organization_id}/members/{member_user_id}/shared-resources
**Description**: Get member's shared resources
**Authentication**: Required
**Query Parameters**:
- resource_type: filter by type (optional)
- status: filter by status (optional)
- limit: int (1-100, default: 50)
- offset: int (default: 0)
**Response Schema**:
```json
{
  "user_id": "user_xyz",
  "organization_id": "org_abc123",
  "shared_resources": [...],
  "total": 5,
  "limit": 50,
  "offset": 0
}
```
**HTTP Codes**: 200 (OK), 500 (Server Error)

---

### Platform Admin Endpoints

#### GET /api/v1/admin/organizations
**Description**: List all organizations (Platform admin)
**Authentication**: Required (Platform Admin)
**Query Parameters**:
- limit: int (1-1000, default: 100)
- offset: int (default: 0)
- search: string (optional)
- plan: string (optional filter)
- status: string (optional filter)
**Response Schema**: Same as GET user organizations
**HTTP Codes**: 200 (OK), 403 (Forbidden), 500 (Server Error)

---

## Functional Requirements

**FR-001**: System MUST create organizations with unique IDs and valid owner
**FR-002**: System MUST validate billing email format on organization creation
**FR-003**: System MUST enforce member limits based on organization plan
**FR-004**: System MUST validate role hierarchy when modifying members
**FR-005**: System MUST prevent owner deletion when only one owner exists
**FR-006**: System MUST publish events for all organization mutations
**FR-007**: System MUST validate user membership before context switching
**FR-008**: System MUST support multiple resource types for sharing
**FR-009**: System MUST enforce permission levels hierarchically
**FR-010**: System MUST track usage quotas for shared resources
**FR-011**: System MUST support automatic expiration of sharings
**FR-012**: System MUST handle concurrent member modifications safely
**FR-013**: System MUST cascade organization deletion to members and sharings
**FR-014**: System MUST validate admin permissions for management operations
**FR-015**: System MUST support internal service calls without JWT

---

## Non-Functional Requirements

**NFR-001**: Organization creation MUST complete within 300ms
**NFR-002**: Member addition MUST complete within 200ms
**NFR-003**: Context switch MUST complete within 100ms
**NFR-004**: Service MUST maintain 99.9% uptime
**NFR-005**: API MUST handle 1000 concurrent requests
**NFR-006**: Database queries MUST be optimized with proper indexes
**NFR-007**: Event publishing failures MUST NOT block operations
**NFR-008**: Service MUST gracefully degrade without event bus
**NFR-009**: All sensitive data MUST be logged without PII
**NFR-010**: API MUST support pagination for list operations (max 1000)

---

## Success Metrics

### Adoption Metrics
- Organizations created per day: Target 50+
- Average members per organization: Target 5+
- Family sharing adoption rate: Target 30% of organizations

### Performance Metrics
- P95 latency for organization operations: <300ms
- P95 latency for member operations: <200ms
- P95 latency for sharing operations: <250ms

### Quality Metrics
- API error rate: <0.1%
- Event publishing success rate: >99.5%
- Test coverage: >80%

---

**Document Version**: 1.0
**Last Updated**: 2025-12-15
**Product Owner**: Organization Service Team
