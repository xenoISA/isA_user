# Organization Service - Domain Context

## Overview

The Organization Service is the **multi-tenancy and group management foundation** for the isA_user platform. It provides centralized organization management, member administration, role-based access control, and family sharing capabilities. Every organization, team, or family group in the system is managed through this service.

**Business Context**: Enable scalable multi-tenant architecture that supports business organizations, family groups, and team structures with granular permission management, resource sharing, and member lifecycle orchestration.

**Core Value Proposition**: Transform individual user accounts into collaborative organizational units with flexible membership models, hierarchical role management, and sophisticated resource sharing capabilities for families, teams, and enterprises.

---

## Business Taxonomy

### Core Entities

#### 1. Organization
**Definition**: A logical grouping of users with shared resources, permissions, and billing. Can represent a business, family, team, or any collaborative group.

**Business Purpose**:
- Establish multi-tenant boundaries and data isolation
- Enable shared resource management (subscriptions, storage, devices)
- Provide centralized billing and administration
- Support family sharing and team collaboration

**Key Attributes**:
- Organization ID (unique identifier)
- Name (organization display name)
- Type (business, family, team, enterprise)
- Billing Email (contact for billing)
- Status (active, suspended, deleted)
- Plan (free, family, team, enterprise)
- Credits Pool (shared credits balance)
- Max Members (plan-based limit)
- Settings (JSONB - flexible configuration)
- Created At (creation timestamp)
- Updated At (last modification timestamp)

**Organization States**:
- **Active**: Normal operational state
- **Suspended**: Temporarily disabled (payment issues, policy violation)
- **Deleted**: Soft-deleted, marked for cleanup

#### 2. Organization Member
**Definition**: A user's membership record within an organization, including role and permissions.

**Business Purpose**:
- Track user-organization relationships
- Define access levels and permissions
- Manage member lifecycle (invited, active, suspended)
- Enable role-based access control

**Key Attributes**:
- Organization ID (reference to organization)
- User ID (reference to user account)
- Role (owner, admin, member, guest)
- Status (pending, active, suspended, removed)
- Permissions (list of specific permissions)
- Joined At (membership start timestamp)
- Updated At (last modification timestamp)

**Member Roles**:
- **Owner**: Full control, can delete organization
- **Admin**: Can manage members and settings
- **Member**: Standard access to shared resources
- **Guest**: Limited access, read-only

#### 3. Family Sharing Resource
**Definition**: A shared resource within an organization, such as subscriptions, devices, storage, or wallets.

**Business Purpose**:
- Enable resource sharing across family members
- Track shared access permissions
- Manage quotas and usage limits
- Support device and subscription sharing

**Key Attributes**:
- Sharing ID (unique identifier)
- Organization ID (owning organization)
- Resource Type (subscription, device, storage, wallet, album)
- Resource ID (reference to actual resource)
- Resource Name (display name)
- Created By (user who created sharing)
- Share With All Members (boolean flag)
- Default Permission (permission level for shared access)
- Status (active, paused, expired, revoked)
- Quota Settings (usage limits)
- Restrictions (time/feature restrictions)
- Expires At (optional expiration)

**Resource Types**:
- **Subscription**: Shared subscription plans (family plan)
- **Device**: Smart home devices, smart frames
- **Storage**: Cloud storage allocation
- **Wallet**: Family wallet with spending limits
- **Album**: Photo albums for smart frames
- **Media Library**: Shared photo/video libraries
- **Calendar**: Family calendar sharing
- **Location**: Location sharing for family members

#### 4. Member Sharing Permission
**Definition**: Individual member's permission record for a shared resource.

**Business Purpose**:
- Grant granular access to shared resources
- Track individual usage and quotas
- Enable custom permission overrides
- Support time-based access control

**Key Attributes**:
- Permission ID (unique identifier)
- Sharing ID (reference to sharing resource)
- User ID (member receiving permission)
- Permission Level (owner, admin, full_access, read_write, read_only)
- Quota Allocated (individual quota limits)
- Quota Used (current usage)
- Is Active (permission status)
- Granted At (when permission was granted)
- Last Accessed At (last resource access)

---

## Domain Scenarios

### Scenario 1: Organization Creation
**Actor**: User, System
**Trigger**: User creates a new organization/family group
**Flow**:
1. User provides organization name, type, and billing email
2. System validates user has permission to create organizations
3. System creates organization record in PostgreSQL
4. System adds creator as owner member
5. System assigns default plan (free tier)
6. Publishes `organization.created` event to NATS
7. Returns complete organization details
8. Billing Service receives event and creates billing profile
9. Wallet Service creates organization wallet

**Outcome**: Organization created with owner, ready for member invitations

### Scenario 2: Member Invitation and Addition
**Actor**: Admin, Owner
**Trigger**: Admin invites new member to organization
**Flow**:
1. Admin submits member invitation with user_id and role
2. System validates admin has permission to add members
3. System validates organization hasn't reached max members
4. System verifies target user exists in account service
5. System creates member record with pending status
6. Publishes `organization.member_added` event
7. Invitation Service sends invitation notification
8. Account Service receives event and updates user's organization list

**Outcome**: Member added to organization with specified role

### Scenario 3: Context Switching
**Actor**: User
**Trigger**: User switches between personal and organization context
**Flow**:
1. User requests context switch to organization_id
2. System validates user is member of organization
3. System validates membership is active
4. System retrieves user's role and permissions
5. System returns context with organization details
6. Session Service updates active context
7. All subsequent requests use organization context

**Outcome**: User operates within organization context with appropriate permissions

### Scenario 4: Family Resource Sharing
**Actor**: Family Admin/Owner
**Trigger**: Admin shares a resource with family members
**Flow**:
1. Admin creates sharing request for resource (e.g., device, album)
2. System validates admin has permission to share
3. System creates sharing record with permissions
4. If share_with_all_members=true, grants access to all members
5. Otherwise, creates individual permissions for specified members
6. Publishes `family.resource_shared` event
7. Notification Service notifies affected members
8. Device/Album/Storage Service receives event and updates access

**Outcome**: Resource shared with specified members and permissions

### Scenario 5: Organization Statistics and Analytics
**Actor**: Admin, Owner
**Trigger**: Admin views organization dashboard
**Flow**:
1. Admin requests organization statistics
2. System validates admin access
3. System queries member counts, status distribution
4. System aggregates usage data from related services
5. System calculates credits consumption and storage usage
6. Returns comprehensive statistics response

**Outcome**: Admin has visibility into organization health and usage

### Scenario 6: Member Role Update
**Actor**: Owner, Admin
**Trigger**: Admin changes member role
**Flow**:
1. Admin submits role update request
2. System validates admin has permission (admins can't modify owners)
3. System validates role hierarchy (can't promote to higher than self)
4. System updates member role in database
5. Publishes `organization.member_updated` event
6. Authorization Service updates cached permissions

**Outcome**: Member role updated with cascading permission changes

### Scenario 7: Organization Deletion
**Actor**: Owner
**Trigger**: Owner deletes organization
**Flow**:
1. Owner requests organization deletion
2. System validates user is the owner
3. System validates organization can be deleted (no active subscriptions blocking)
4. System soft-deletes organization record
5. System removes all member associations
6. Publishes `organization.deleted` event
7. Storage Service archives organization data
8. Billing Service closes billing profile
9. All shared resources are revoked

**Outcome**: Organization deleted, all members removed, resources cleaned up

---

## Domain Events

### Published Events

#### 1. organization.created
**Trigger**: New organization successfully created
**Payload**:
- organization_id: Unique identifier
- organization_name: Display name
- owner_user_id: Creator user ID
- billing_email: Billing contact
- plan: Initial plan type
- timestamp: Creation timestamp

**Subscribers**:
- **Billing Service**: Create billing profile
- **Wallet Service**: Initialize organization wallet
- **Audit Service**: Log organization creation
- **Analytics Service**: Track organization metrics

#### 2. organization.updated
**Trigger**: Organization details modified
**Payload**:
- organization_id: Organization identifier
- organization_name: Updated name
- updated_by: User who made changes
- updated_fields: List of changed fields
- timestamp: Update timestamp

**Subscribers**:
- **Audit Service**: Track changes
- **Search Service**: Reindex organization
- **Billing Service**: Update billing info if changed

#### 3. organization.deleted
**Trigger**: Organization soft-deleted
**Payload**:
- organization_id: Organization identifier
- organization_name: Organization name
- deleted_by: User who deleted
- timestamp: Deletion timestamp

**Subscribers**:
- **Account Service**: Remove organization from user accounts
- **Storage Service**: Archive organization files
- **Billing Service**: Close billing profile
- **Session Service**: Invalidate organization sessions
- **Device Service**: Revoke device access

#### 4. organization.member_added
**Trigger**: New member added to organization
**Payload**:
- organization_id: Organization identifier
- user_id: New member user ID
- role: Assigned role
- added_by: Admin who added member
- permissions: Initial permissions list
- timestamp: Addition timestamp

**Subscribers**:
- **Account Service**: Update user's organization list
- **Notification Service**: Send welcome notification
- **Audit Service**: Log membership addition

#### 5. organization.member_removed
**Trigger**: Member removed from organization
**Payload**:
- organization_id: Organization identifier
- user_id: Removed member user ID
- removed_by: Admin who removed member
- timestamp: Removal timestamp

**Subscribers**:
- **Account Service**: Update user's organization list
- **Session Service**: Invalidate member sessions
- **Storage Service**: Revoke file access
- **Device Service**: Revoke device access

#### 6. family.resource_shared
**Trigger**: Resource shared within organization
**Payload**:
- sharing_id: Sharing identifier
- organization_id: Organization identifier
- resource_type: Type of shared resource
- resource_id: Resource identifier
- resource_name: Display name
- created_by: User who shared
- share_with_all_members: Whether all members have access
- default_permission: Default permission level
- shared_with_count: Number of members with access
- timestamp: Sharing timestamp

**Subscribers**:
- **Device Service**: Update device access (if device sharing)
- **Album Service**: Update album access (if album sharing)
- **Storage Service**: Update storage access (if storage sharing)
- **Notification Service**: Notify affected members

### Subscribed Events

#### 1. account_service.user.deleted
**Source**: account_service
**Purpose**: Remove deleted users from organizations
**Handler Action**: Remove user from all organizations, transfer ownership if needed

#### 2. album_service.album.deleted
**Source**: album_service
**Purpose**: Remove sharing references for deleted albums
**Handler Action**: Delete sharing records for the album

#### 3. billing_service.billing.subscription_changed
**Source**: billing_service
**Purpose**: Update organization plan when subscription changes
**Handler Action**: Update organization plan and member limits

---

## Core Concepts

### Multi-Tenancy Model
- Organizations provide logical data isolation
- Resources can be scoped to individual users or organizations
- Context switching allows users to operate in different scopes
- Billing and quotas are organization-level

### Membership Hierarchy
1. **Owner**: Highest privilege, can delete organization
2. **Admin**: Can manage members and settings
3. **Member**: Standard access to shared resources
4. **Guest**: Limited read-only access

### Permission Model
- Role-based access control (RBAC)
- Permission lists for granular control
- Context-aware authorization
- Hierarchical permission inheritance

### Family Sharing Architecture
- Resource-agnostic sharing framework
- Supports subscriptions, devices, storage, wallets
- Individual quota management
- Time-based and usage-based restrictions

### Context Switching
- Users can switch between personal and organization contexts
- All operations are scoped to active context
- Session maintains current context state
- Gateway enforces context-based authorization

---

## Business Rules (High-Level)

### Organization Management Rules
- **BR-ORG-001**: Organization name must be unique within platform
- **BR-ORG-002**: Organization must have at least one owner
- **BR-ORG-003**: Organization cannot be deleted with active paid subscriptions
- **BR-ORG-004**: Organization type cannot be changed after creation
- **BR-ORG-005**: Billing email must be valid email format
- **BR-ORG-006**: Organization name must be 1-100 characters
- **BR-ORG-007**: Only active organizations can accept new members

### Membership Rules
- **BR-MEM-001**: User can be member of multiple organizations
- **BR-MEM-002**: User can only have one role per organization
- **BR-MEM-003**: Owner role cannot be removed (only transferred)
- **BR-MEM-004**: Admins cannot modify owners or other admins
- **BR-MEM-005**: Members can only remove themselves (not others)
- **BR-MEM-006**: Last owner cannot leave organization
- **BR-MEM-007**: Suspended members cannot access organization resources
- **BR-MEM-008**: Member limit enforced by organization plan

### Role and Permission Rules
- **BR-ROL-001**: Only owners can delete organization
- **BR-ROL-002**: Only owners and admins can add/remove members
- **BR-ROL-003**: Only owners can promote to admin
- **BR-ROL-004**: Admins can demote members but not other admins
- **BR-ROL-005**: Role changes are immediate and broadcast

### Family Sharing Rules
- **BR-FSH-001**: Only admins/owners can create sharing
- **BR-FSH-002**: Sharing creator has full control
- **BR-FSH-003**: Permission levels are hierarchical
- **BR-FSH-004**: Quota cannot exceed organization allocation
- **BR-FSH-005**: Expired sharing automatically revokes access
- **BR-FSH-006**: Revoked sharing cannot be reactivated
- **BR-FSH-007**: Resource-specific permissions override defaults

### Context and Access Rules
- **BR-CTX-001**: Default context is personal (no organization)
- **BR-CTX-002**: Context switch requires active membership
- **BR-CTX-003**: Suspended membership prevents context switch
- **BR-CTX-004**: Context determines resource scope
- **BR-CTX-005**: Invalid context requests return error

### Event Publishing Rules
- **BR-EVT-001**: All organization mutations publish events
- **BR-EVT-002**: Event publishing failures are logged but don't block operations
- **BR-EVT-003**: Events include full context for subscribers
- **BR-EVT-004**: Events use ISO 8601 timestamps
- **BR-EVT-005**: Member events include role and permissions

---

## Organization Service in the Ecosystem

### Upstream Dependencies
- **Account Service**: User identity validation
- **Auth Service**: Authentication tokens
- **PostgreSQL gRPC Service**: Data persistence
- **NATS Event Bus**: Event publishing
- **Consul**: Service discovery

### Downstream Consumers
- **Account Service**: User organization list
- **Authorization Service**: Permission resolution
- **Billing Service**: Organization billing
- **Storage Service**: Storage quotas
- **Device Service**: Device sharing
- **Album Service**: Album sharing
- **Media Service**: Media library sharing
- **Wallet Service**: Wallet sharing
- **Session Service**: Context management
- **Invitation Service**: Member invitations
- **Notification Service**: Member notifications

### Integration Patterns
- **Synchronous REST**: CRUD operations via FastAPI
- **Asynchronous Events**: NATS for cross-service sync
- **Service Discovery**: Consul for dynamic routing
- **Protocol Buffers**: PostgreSQL gRPC communication

### Dependency Injection
- **Repository Pattern**: OrganizationRepository, FamilySharingRepository
- **Protocol Interfaces**: OrganizationRepositoryProtocol, FamilySharingRepositoryProtocol
- **Factory Pattern**: create_organization_service(), create_family_sharing_service()
- **Mock-Friendly**: Protocols enable test doubles

---

## Success Metrics

### Organization Metrics
- **Organization Creation Rate**: New organizations per day/week
- **Member Growth Rate**: Members added per organization
- **Active Organization Ratio**: Active vs total organizations (target: >90%)
- **Average Members Per Organization**: Organization size distribution

### Sharing Metrics
- **Resources Shared Per Organization**: Average sharing count
- **Sharing Utilization Rate**: Active sharings vs total
- **Permission Distribution**: Read-only vs read-write vs admin

### Performance Metrics
- **Organization Creation Latency**: Time to create (target: <300ms)
- **Member Addition Latency**: Time to add member (target: <200ms)
- **Context Switch Latency**: Time to switch context (target: <100ms)
- **Sharing Creation Latency**: Time to create sharing (target: <250ms)

### Availability Metrics
- **Service Uptime**: Organization Service availability (target: 99.9%)
- **Database Connectivity**: PostgreSQL connection success (target: 99.99%)
- **Event Publishing Success**: Events published successfully (target: >99.5%)

---

## Glossary

**Organization**: Logical grouping of users with shared resources
**Member**: User's membership record within an organization
**Owner**: Highest privilege role, full organizational control
**Admin**: Management role, can manage members and settings
**Context**: Active operational scope (personal or organization)
**Family Sharing**: Resource sharing within organization members
**Sharing Resource**: Shared entity (device, storage, subscription)
**Permission Level**: Access level for shared resource
**Quota**: Usage limit for shared resource
**Multi-Tenancy**: Architecture supporting isolated organizational units
**Context Switching**: Changing operational scope between personal and organization
**RBAC**: Role-Based Access Control
**Soft Delete**: Marking as deleted without physical removal

---

**Document Version**: 1.0
**Last Updated**: 2025-12-15
**Maintained By**: Organization Service Team
