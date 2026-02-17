# Authorization Service - Technical Design Document

## Architecture Overview

### Service Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                      Authorization Service                                  │
│                         Port: 8203                                         │
├────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      FastAPI Application                              │  │
│  │                         (main.py)                                     │  │
│  │  ┌─────────────┐  ┌────────────────┐  ┌───────────────────────────┐  │  │
│  │  │   Routes    │  │  Middleware    │  │  Exception Handlers       │  │  │
│  │  │ /check-accs │  │  CORS/Auth     │  │  Global Error Handler     │  │  │
│  │  │ /grant      │  │                │  │                           │  │  │
│  │  │ /revoke     │  │                │  │                           │  │  │
│  │  │ /bulk-*     │  │                │  │                           │  │  │
│  │  └─────────────┘  └────────────────┘  └───────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      Service Layer                                    │  │
│  │                (authorization_service.py)                             │  │
│  │  ┌───────────────────┐  ┌───────────────────┐  ┌─────────────────┐   │  │
│  │  │ Access Control    │  │ Permission Mgmt   │  │ Bulk Operations │   │  │
│  │  │ check_access()    │  │ grant_permission()│  │ bulk_grant()    │   │  │
│  │  │ _check_org_access │  │ revoke_permission │  │ bulk_revoke()   │   │  │
│  │  │ _check_sub_access │  │ get_summary()     │  │                 │   │  │
│  │  └───────────────────┘  └───────────────────┘  └─────────────────┘   │  │
│  │  ┌───────────────────┐  ┌───────────────────┐  ┌─────────────────┐   │  │
│  │  │ Hierarchy Logic   │  │ Event Publishing  │  │ Audit Logging   │   │  │
│  │  │ tier_sufficient() │  │ publish_event()   │  │ log_action()    │   │  │
│  │  │ level_sufficient()│  │                   │  │ log_check()     │   │  │
│  │  └───────────────────┘  └───────────────────┘  └─────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      Repository Layer                                 │  │
│  │                (authorization_repository.py)                          │  │
│  │  ┌───────────────────┐  ┌───────────────────┐  ┌─────────────────┐   │  │
│  │  │ Resource Perms    │  │ User Perms        │  │ Org Perms       │   │  │
│  │  │ create_resource() │  │ grant_user()      │  │ create_org()    │   │  │
│  │  │ get_resource()    │  │ get_user()        │  │ get_org()       │   │  │
│  │  │ list_resources()  │  │ list_user()       │  │ list_org()      │   │  │
│  │  │                   │  │ revoke_user()     │  │                 │   │  │
│  │  └───────────────────┘  └───────────────────┘  └─────────────────┘   │  │
│  │  ┌───────────────────┐  ┌───────────────────┐  ┌─────────────────┐   │  │
│  │  │ Service Clients   │  │ Analytics         │  │ Cleanup         │   │  │
│  │  │ get_user_info()   │  │ get_summary()     │  │ cleanup_expired │   │  │
│  │  │ get_org_info()    │  │ get_statistics()  │  │ cleanup()       │   │  │
│  │  │ is_member()       │  │                   │  │                 │   │  │
│  │  └───────────────────┘  └───────────────────┘  └─────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                   Dependency Injection Layer                          │  │
│  │                       (protocols.py)                                  │  │
│  │  ┌───────────────────┐  ┌───────────────────┐                        │  │
│  │  │ Repository        │  │ EventBus          │                        │  │
│  │  │ Protocol          │  │ Protocol          │                        │  │
│  │  │ (19 methods)      │  │ publish_event()   │                        │  │
│  │  └───────────────────┘  └───────────────────┘                        │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      Event Layer (events/)                            │  │
│  │  ┌───────────────────┐  ┌───────────────────┐                        │  │
│  │  │ Publishers        │  │ Handlers          │                        │  │
│  │  │ permission.granted│  │ user.deleted      │                        │  │
│  │  │ permission.revoked│  │ org.deleted       │                        │  │
│  │  │ access.denied     │  │ org.member_added  │                        │  │
│  │  │ bulk_granted      │  │ org.member_removed│                        │  │
│  │  └───────────────────┘  └───────────────────┘                        │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         │                           │                           │
         ▼                           ▼                           ▼
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│   PostgreSQL    │         │      NATS       │         │ account_service │
│   (via gRPC)    │         │   JetStream     │         │   Port: 8202    │
│   Port: 50061   │         │   Port: 4222    │         │                 │
│   Schema: authz │         │                 │         │  get_profile()  │
└─────────────────┘         └─────────────────┘         └─────────────────┘
                                                                 │
                                                                 ▼
                                                        ┌─────────────────┐
                                                        │  org_service    │
                                                        │   Port: 8206    │
                                                        │                 │
                                                        │  get_org()      │
                                                        │  get_members()  │
                                                        └─────────────────┘
```

### External Dependencies

| Dependency | Type | Purpose | Port | Protocol |
|------------|------|---------|------|----------|
| PostgreSQL | gRPC | Permission data storage | 50061 | gRPC |
| NATS | Native | Event messaging | 4222 | NATS |
| account_service | HTTP | User validation & info | 8202 | REST |
| organization_service | HTTP | Org membership & info | 8206 | REST |
| Consul | HTTP | Service discovery | 8500 | HTTP |

### Request Flow Overview

```
┌─────────┐     ┌─────────┐     ┌──────────────────┐     ┌────────────────┐
│ Client  │────>│ Gateway │────>│ auth_service     │────>│ authorization  │
│         │     │  8080   │     │ verify JWT       │     │   _service     │
└─────────┘     └─────────┘     └──────────────────┘     │     8203       │
                                                          └────────────────┘
                                                                  │
                    ┌─────────────────────────────────────────────┼─────┐
                    │                                             │     │
                    ▼                                             ▼     ▼
            ┌──────────────┐                              ┌──────────────────┐
            │ account_svc  │                              │   PostgreSQL     │
            │ user info    │                              │  permission data │
            └──────────────┘                              └──────────────────┘
```

---

## Component Design

### Service Layer (`authorization_service.py`)

**Responsibilities**:
- Permission resolution with priority hierarchy
- Access level and subscription tier comparison
- Event publishing for permission changes
- Audit trail logging
- Bulk operation orchestration

**Key Methods**:
| Method | Description | Events Published |
|--------|-------------|------------------|
| `check_resource_access()` | Evaluate user access with priority order | `access.denied` (on deny) |
| `grant_resource_permission()` | Grant permission to user | `permission.granted` |
| `revoke_resource_permission()` | Revoke permission from user | `permission.revoked` |
| `bulk_grant_permissions()` | Batch grant operations | `permissions.bulk_granted` |
| `bulk_revoke_permissions()` | Batch revoke operations | `permissions.bulk_revoked` |
| `get_user_permission_summary()` | Aggregate user permissions | None |
| `list_user_accessible_resources()` | List all accessible resources | None |
| `initialize_default_permissions()` | Setup default resource configs | None |
| `cleanup_expired_permissions()` | Remove expired permissions | None |

**Private Helper Methods**:
| Method | Description |
|--------|-------------|
| `_check_organization_access()` | Evaluate org-level permissions |
| `_check_subscription_access()` | Evaluate subscription-based permissions |
| `_subscription_tier_sufficient()` | Compare subscription tiers |
| `_has_sufficient_access()` | Compare access levels |
| `_organization_plan_sufficient()` | Compare organization plans |
| `_log_access_check()` | Log access check decisions |
| `_log_permission_action()` | Log permission modifications |

### Repository Layer (`authorization_repository.py`)

**Responsibilities**:
- PostgreSQL data access via gRPC
- Cross-service communication (account, organization)
- Permission CRUD operations
- Audit log persistence
- Statistics aggregation

**Key Methods**:
| Method | SQL Operation | Index Used |
|--------|---------------|------------|
| `create_resource_permission()` | INSERT | - |
| `get_resource_permission()` | SELECT | permission_type, resource |
| `list_resource_permissions()` | SELECT with filter | permission_type |
| `grant_user_permission()` | INSERT | - |
| `get_user_permission()` | SELECT | permission_type, target_id |
| `list_user_permissions()` | SELECT with filter | target_id |
| `revoke_user_permission()` | UPDATE is_active | target_id |
| `get_organization_permission()` | SELECT | permission_type, target_id |
| `list_organization_permissions()` | SELECT | target_id |
| `get_user_info()` | HTTP call | - |
| `get_organization_info()` | HTTP call | - |
| `is_user_organization_member()` | HTTP call | - |
| `get_user_permission_summary()` | Aggregation | target_id |
| `get_service_statistics()` | COUNT queries | permission_type |
| `cleanup_expired_permissions()` | DELETE | expires_at |
| `log_permission_action()` | INSERT | - |

### Client Layer (`clients/`)

**External Service Clients**:
| Client | Service | Methods | Purpose |
|--------|---------|---------|---------|
| `AccountServiceClient` | account_service:8202 | `get_account_profile()` | User validation |
| `OrganizationServiceClient` | organization_service:8206 | `get_organization()`, `get_members()`, `get_user_organizations()` | Org membership |

### Event Layer (`events/`)

**Event Models** (`events/models.py`):
| Model | Event Type | Fields |
|-------|------------|--------|
| `PermissionGrantedEventData` | permission.granted | user_id, resource_type, resource_name, access_level, permission_source, granted_by |
| `PermissionRevokedEventData` | permission.revoked | user_id, resource_type, resource_name, revoked_by, reason |
| `BulkPermissionsGrantedEventData` | permissions.bulk_granted | user_ids, permission_count, granted_by, organization_id |
| `BulkPermissionsRevokedEventData` | permissions.bulk_revoked | user_ids, permission_count, revoked_by, reason |

**Event Handlers** (`events/handlers.py`):
| Handler | Consumed Event | Action |
|---------|----------------|--------|
| `handle_user_deleted()` | user.deleted | Revoke all user permissions |
| `handle_organization_deleted()` | organization.deleted | Delete org permissions, revoke user grants |
| `handle_org_member_added()` | organization.member_added | Auto-grant org permissions to new member |
| `handle_org_member_removed()` | organization.member_removed | Revoke org-sourced permissions |

### Factory Layer (`factory.py`)

**Factory Function**:
```python
def create_authorization_service(
    config: Optional[ConfigManager] = None,
    event_bus: Optional[EventBusProtocol] = None
) -> AuthorizationService
```

**Dependency Injection Flow**:
1. Create repository with config
2. Inject repository into service
3. Inject optional event_bus
4. Return configured service instance

---

## Database Schemas

### Schema: `authz`

```sql
-- Create schema for authorization data
CREATE SCHEMA IF NOT EXISTS authz;

-- Main permissions table (unified for all permission types)
CREATE TABLE IF NOT EXISTS authz.permissions (
    -- Primary key
    id SERIAL PRIMARY KEY,

    -- Permission classification
    permission_type VARCHAR(50) NOT NULL,
    -- Values: 'resource_config', 'user_permission', 'org_permission', 'audit_log'

    -- Target identification
    target_type VARCHAR(50) NOT NULL,
    -- Values: 'global', 'user', 'organization', 'system'
    target_id VARCHAR(100),
    -- user_id, organization_id, or NULL for global

    -- Resource identification
    resource_type VARCHAR(50) NOT NULL,
    -- Values: 'mcp_tool', 'prompt', 'resource', 'api_endpoint', 'database', 'file_storage', 'compute', 'ai_model'
    resource_name VARCHAR(255) NOT NULL,
    resource_category VARCHAR(100),

    -- Access control
    access_level VARCHAR(20),
    -- Values: 'none', 'read_only', 'read_write', 'admin', 'owner'
    permission_source VARCHAR(50),
    -- Values: 'subscription', 'organization', 'admin_grant', 'system_default', 'organization_admin', 'audit_system'
    subscription_tier_required VARCHAR(20),
    -- Values: 'free', 'pro', 'enterprise', 'custom' (for resource_config)
    -- or organization plan for org_permission

    -- Status and metadata
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',

    -- Timestamps
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT valid_permission_type CHECK (permission_type IN ('resource_config', 'user_permission', 'org_permission', 'audit_log')),
    CONSTRAINT valid_target_type CHECK (target_type IN ('global', 'user', 'organization', 'system')),
    CONSTRAINT valid_resource_type CHECK (resource_type IN ('mcp_tool', 'prompt', 'resource', 'api_endpoint', 'database', 'file_storage', 'compute', 'ai_model')),
    CONSTRAINT valid_access_level CHECK (access_level IS NULL OR access_level IN ('none', 'read_only', 'read_write', 'admin', 'owner'))
);

-- Indexes for query performance
-- Index for resource configuration lookups
CREATE INDEX idx_permissions_resource_config
    ON authz.permissions(permission_type, resource_type, resource_name)
    WHERE permission_type = 'resource_config' AND is_active = TRUE;

-- Index for user permission lookups
CREATE INDEX idx_permissions_user
    ON authz.permissions(permission_type, target_id, resource_type, resource_name)
    WHERE permission_type = 'user_permission' AND is_active = TRUE;

-- Index for organization permission lookups
CREATE INDEX idx_permissions_org
    ON authz.permissions(permission_type, target_id)
    WHERE permission_type = 'org_permission' AND is_active = TRUE;

-- Index for cleanup operations
CREATE INDEX idx_permissions_expires
    ON authz.permissions(permission_type, expires_at)
    WHERE permission_type = 'user_permission' AND expires_at IS NOT NULL;

-- Index for statistics queries
CREATE INDEX idx_permissions_type_active
    ON authz.permissions(permission_type, is_active);

-- Index for audit log queries
CREATE INDEX idx_permissions_audit
    ON authz.permissions(permission_type, target_id, created_at DESC)
    WHERE permission_type = 'audit_log';

-- Unique constraint to prevent duplicate user permissions
CREATE UNIQUE INDEX idx_permissions_user_unique
    ON authz.permissions(target_id, resource_type, resource_name)
    WHERE permission_type = 'user_permission' AND is_active = TRUE;

-- Unique constraint to prevent duplicate resource configs
CREATE UNIQUE INDEX idx_permissions_resource_unique
    ON authz.permissions(resource_type, resource_name)
    WHERE permission_type = 'resource_config' AND is_active = TRUE;
```

### Database Record Types

```sql
-- Example: Resource Configuration Record
-- permission_type = 'resource_config'
INSERT INTO authz.permissions (
    permission_type, target_type, target_id, resource_type, resource_name,
    resource_category, access_level, permission_source, subscription_tier_required,
    description, is_active, metadata, created_at, updated_at
) VALUES (
    'resource_config', 'global', NULL, 'mcp_tool', 'weather_api',
    'utilities', 'read_only', 'system_default', 'free',
    'Basic weather information tool', TRUE, '{}', NOW(), NOW()
);

-- Example: User Permission Record
-- permission_type = 'user_permission'
INSERT INTO authz.permissions (
    permission_type, target_type, target_id, resource_type, resource_name,
    access_level, permission_source, is_active, metadata, created_at, updated_at
) VALUES (
    'user_permission', 'user', 'user_123', 'api_endpoint', '/api/admin',
    'admin', 'admin_grant', TRUE, '{"granted_by": "admin_001"}', NOW(), NOW()
);

-- Example: Organization Permission Record
-- permission_type = 'org_permission'
INSERT INTO authz.permissions (
    permission_type, target_type, target_id, resource_type, resource_name,
    access_level, permission_source, subscription_tier_required, is_active,
    created_at, updated_at
) VALUES (
    'org_permission', 'organization', 'org_001', 'database', 'analytics_db',
    'read_write', 'organization_admin', 'growth', TRUE, NOW(), NOW()
);

-- Example: Audit Log Record
-- permission_type = 'audit_log'
INSERT INTO authz.permissions (
    permission_type, target_type, target_id, resource_type, resource_name,
    access_level, permission_source, is_active, created_at, updated_at
) VALUES (
    'audit_log', 'system', 'user_123', 'api_endpoint', '/api/admin',
    'admin', 'audit_system', TRUE, NOW(), NOW()
);
```

### Database Migrations

| Version | Description | File |
|---------|-------------|------|
| 001 | Initial schema and permissions table | `001_initial_schema.sql` |
| 002 | Add indexes for performance | `002_add_indexes.sql` |
| 003 | Add unique constraints | `003_unique_constraints.sql` |

---

## Data Flow Diagrams

### Check Resource Access Flow

```
Client                    Service                  Repository          Account Svc
  │                          │                          │                   │
  │  POST /check-access      │                          │                   │
  │  {user_id, resource,     │                          │                   │
  │   required_level}        │                          │                   │
  │─────────────────────────>│                          │                   │
  │                          │                          │                   │
  │                          │  get_user_info(user_id)  │                   │
  │                          │─────────────────────────>│                   │
  │                          │                          │  GET /profile     │
  │                          │                          │──────────────────>│
  │                          │                          │  {user, sub_tier} │
  │                          │                          │<──────────────────│
  │                          │  return user_info        │                   │
  │                          │<─────────────────────────│                   │
  │                          │                          │                   │
  │                          │  get_user_permission()   │                   │
  │                          │─────────────────────────>│                   │
  │                          │                          │  SELECT           │
  │                          │                          │─────────┐         │
  │                          │                          │<────────┘         │
  │                          │  return admin_permission │                   │
  │                          │<─────────────────────────│                   │
  │                          │                          │                   │
  │                          │  [If admin grant exists] │                   │
  │                          │  _has_sufficient_access()│                   │
  │                          │─────────┐               │                   │
  │                          │<────────┘               │                   │
  │                          │                          │                   │
  │                          │  [If no admin grant]    │                   │
  │                          │  _check_org_access()     │                   │
  │                          │  _check_sub_access()     │                   │
  │                          │                          │                   │
  │                          │  _log_access_check()     │                   │
  │                          │─────────────────────────>│                   │
  │                          │                          │  INSERT audit     │
  │                          │                          │─────────┐         │
  │                          │                          │<────────┘         │
  │                          │                          │                   │
  │  200 OK                  │                          │                   │
  │  {has_access, level,     │                          │                   │
  │   source, reason}        │                          │                   │
  │<─────────────────────────│                          │                   │
```

### Grant Permission Flow

```
Admin                     Service                  Repository              NATS
  │                          │                          │                    │
  │  POST /grant             │                          │                    │
  │  {user_id, resource,     │                          │                    │
  │   level, source}         │                          │                    │
  │─────────────────────────>│                          │                    │
  │                          │                          │                    │
  │                          │  get_user_info(user_id)  │                    │
  │                          │─────────────────────────>│                    │
  │                          │                          │  HTTP call         │
  │                          │                          │─────────┐          │
  │                          │                          │<────────┘          │
  │                          │  return user_info        │                    │
  │                          │<─────────────────────────│                    │
  │                          │                          │                    │
  │                          │  [Validate user exists]  │                    │
  │                          │                          │                    │
  │                          │  grant_user_permission() │                    │
  │                          │─────────────────────────>│                    │
  │                          │                          │  INSERT            │
  │                          │                          │─────────┐          │
  │                          │                          │<────────┘          │
  │                          │  return permission       │                    │
  │                          │<─────────────────────────│                    │
  │                          │                          │                    │
  │                          │  _log_permission_action()│                    │
  │                          │─────────────────────────>│                    │
  │                          │                          │                    │
  │                          │  publish(permission.granted)                  │
  │                          │───────────────────────────────────────────────>│
  │                          │                          │                    │
  │  200 OK                  │                          │                    │
  │  {message: "granted"}    │                          │                    │
  │<─────────────────────────│                          │                    │
```

### Bulk Grant Flow

```
Admin                     Service                  Repository              NATS
  │                          │                          │                    │
  │  POST /bulk-grant        │                          │                    │
  │  {operations: [...]}     │                          │                    │
  │─────────────────────────>│                          │                    │
  │                          │                          │                    │
  │                          │  generate batch_id       │                    │
  │                          │─────────┐               │                    │
  │                          │<────────┘               │                    │
  │                          │                          │                    │
  │                          │  for each operation:     │                    │
  │                          │    grant_resource_perm() │                    │
  │                          │─────────────────────────>│                    │
  │                          │                          │  INSERT            │
  │                          │                          │─────────┐          │
  │                          │                          │<────────┘          │
  │                          │    collect result        │                    │
  │                          │<─────────────────────────│                    │
  │                          │                          │                    │
  │                          │  publish(permissions.bulk_granted)            │
  │                          │───────────────────────────────────────────────>│
  │                          │                          │                    │
  │  200 OK                  │                          │                    │
  │  {total, success, fail,  │                          │                    │
  │   results: [...]}        │                          │                    │
  │<─────────────────────────│                          │                    │
```

### Event Handler: User Deleted

```
NATS                     Handler                   Repository
  │                          │                          │
  │  user.deleted            │                          │
  │  {user_id}               │                          │
  │─────────────────────────>│                          │
  │                          │                          │
  │                          │  list_user_permissions() │
  │                          │─────────────────────────>│
  │                          │                          │  SELECT
  │                          │                          │─────────┐
  │                          │                          │<────────┘
  │                          │  return [permissions]    │
  │                          │<─────────────────────────│
  │                          │                          │
  │                          │  for each permission:    │
  │                          │    revoke_user_perm()    │
  │                          │─────────────────────────>│
  │                          │                          │  UPDATE
  │                          │                          │─────────┐
  │                          │                          │<────────┘
  │                          │                          │
  │  ack                     │                          │
  │<─────────────────────────│                          │
```

### Event Handler: Organization Member Added

```
NATS                     Handler                   Repository
  │                          │                          │
  │  org.member_added        │                          │
  │  {org_id, user_id}       │                          │
  │─────────────────────────>│                          │
  │                          │                          │
  │                          │  list_org_permissions()  │
  │                          │─────────────────────────>│
  │                          │                          │  SELECT
  │                          │                          │─────────┐
  │                          │                          │<────────┘
  │                          │  return [org_permissions]│
  │                          │<─────────────────────────│
  │                          │                          │
  │                          │  for each org_permission:│
  │                          │    get_user_permission() │
  │                          │─────────────────────────>│
  │                          │                          │  SELECT
  │                          │                          │─────────┐
  │                          │                          │<────────┘
  │                          │    [If not exists]       │
  │                          │    grant_user_perm()     │
  │                          │─────────────────────────>│
  │                          │                          │  INSERT
  │                          │                          │─────────┐
  │                          │                          │<────────┘
  │                          │                          │
  │  ack                     │                          │
  │<─────────────────────────│                          │
```

---

## Technology Stack

### Core Technologies

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Language | Python | 3.9+ | Primary language |
| Framework | FastAPI | 0.100+ | HTTP API framework |
| Validation | Pydantic | 2.0+ | Data validation and models |
| Async HTTP | httpx | 0.24+ | Service-to-service calls |
| Database | PostgreSQL | 14+ | Permission data storage |
| DB Access | gRPC | - | PostgreSQL communication |
| Messaging | NATS | 2.9+ | Event bus (JetStream) |
| Config | ConfigManager | - | Service configuration |

### Internal Libraries

| Library | Purpose |
|---------|---------|
| `isa_common.AsyncPostgresClient` | Async PostgreSQL via gRPC |
| `isa_common.consul_client.ConsulRegistry` | Service discovery |
| `core.nats_client` | NATS JetStream integration |
| `core.config_manager` | Configuration management |
| `core.logger` | Structured logging |

### Development Tools

| Tool | Purpose |
|------|---------|
| pytest | Testing framework |
| pytest-asyncio | Async test support |
| black | Code formatting |
| ruff | Linting |
| mypy | Type checking |

---

## Security Considerations

### Authentication

- **JWT Token Validation**: All requests validated via API Gateway
- **Token Content**: Contains user_id, roles, organization_id
- **Internal Calls**: `X-Internal-Call: true` header for service-to-service

### Authorization Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                   Permission Resolution Order                │
├─────────────────────────────────────────────────────────────┤
│  1. Admin Grant (HIGHEST PRIORITY)                          │
│     ↓ If not found                                          │
│  2. Organization Permission                                  │
│     ↓ If not found or insufficient                          │
│  3. Subscription-Based Permission                           │
│     ↓ If not found or insufficient                          │
│  4. User-Specific Permission (non-admin)                    │
│     ↓ If not found or insufficient                          │
│  5. DENY (DEFAULT)                                          │
└─────────────────────────────────────────────────────────────┘
```

### Access Level Hierarchy

```
┌───────────────────────────────────────────────────────────┐
│  OWNER (4) > ADMIN (3) > READ_WRITE (2) > READ_ONLY (1)  │
│                                                           │
│  Higher levels automatically satisfy lower requirements   │
└───────────────────────────────────────────────────────────┘
```

### Data Protection

| Concern | Mitigation |
|---------|------------|
| SQL Injection | Parameterized queries via gRPC |
| Input Validation | Pydantic models with validators |
| Sensitive Data | Metadata stored as JSONB, no PII in logs |
| Audit Trail | Immutable audit_log records |

### Rate Limiting

- Access checks: High limit (critical path)
- Grant/Revoke: Moderate limit
- Bulk operations: Lower limit with batch size cap

---

## Event-Driven Architecture

### Published Events

| Event Type | Trigger | Payload | Consumers |
|------------|---------|---------|-----------|
| `permission.granted` | After grant_resource_permission() | user_id, resource, level, source, granted_by | audit_service, notification_service |
| `permission.revoked` | After revoke_resource_permission() | user_id, resource, previous_level, revoked_by, reason | audit_service, session_service |
| `access.denied` | On failed access check | user_id, resource, required_level, reason | audit_service, telemetry_service |
| `permissions.bulk_granted` | After bulk_grant_permissions() | user_ids, count, granted_by | audit_service |
| `permissions.bulk_revoked` | After bulk_revoke_permissions() | user_ids, count, revoked_by, reason | audit_service, session_service |

### Consumed Events

| Event Type | Source | Handler | Action |
|------------|--------|---------|--------|
| `user.deleted` | account_service | `handle_user_deleted()` | Revoke all user permissions |
| `organization.deleted` | organization_service | `handle_organization_deleted()` | Delete org permissions, revoke related user permissions |
| `organization.member_added` | organization_service | `handle_org_member_added()` | Auto-grant org permissions |
| `organization.member_removed` | organization_service | `handle_org_member_removed()` | Revoke org-sourced permissions |

### Event Delivery Guarantees

| Guarantee | Implementation |
|-----------|----------------|
| At-least-once | NATS JetStream acknowledgment |
| Ordering | Per-user ordering for permission events |
| Idempotency | Check existing state before modifications |
| Retry | 3 retries with exponential backoff |

---

## Error Handling

### Exception Hierarchy

```
AuthorizationException (Base)
├── PermissionNotFoundException
├── UserNotFoundException
├── OrganizationNotFoundException
└── InvalidPermissionError
```

### HTTP Status Code Mapping

| Exception | HTTP Status | Error Code | Description |
|-----------|-------------|------------|-------------|
| ValidationError | 422 | VALIDATION_ERROR | Invalid input data |
| UserNotFoundException | 404 | USER_NOT_FOUND | User does not exist |
| PermissionNotFoundException | 404 | PERMISSION_NOT_FOUND | Permission not found |
| OrganizationNotFoundException | 404 | ORG_NOT_FOUND | Organization not found |
| InvalidPermissionError | 400 | INVALID_PERMISSION | Invalid permission config |
| AuthenticationError | 401 | UNAUTHORIZED | Missing/invalid token |
| AuthorizationError | 403 | FORBIDDEN | Insufficient permissions |
| ServiceUnavailable | 503 | SERVICE_UNAVAILABLE | Service not initialized |
| InternalError | 500 | INTERNAL_ERROR | Unexpected error |

### Error Response Format

```json
{
  "detail": "Human-readable error message",
  "error_code": "ERROR_CODE",
  "timestamp": "2025-01-01T12:00:00Z"
}
```

---

## Performance Considerations

### Caching Strategy

| Data Type | Cache Location | TTL | Invalidation |
|-----------|----------------|-----|--------------|
| User info | Repository | Request-scoped | Per-request |
| Resource configs | In-memory | 5 minutes | On update event |
| Access decisions | None (always fresh) | - | - |

### Query Optimization

| Query Type | Optimization |
|------------|--------------|
| Access check | Indexed lookup by user_id + resource |
| Permission list | Paginated with limit |
| Statistics | COUNT with indexed columns |
| Cleanup | Indexed by expires_at |

### Performance Targets

| Operation | Target Latency (p95) |
|-----------|---------------------|
| Check access | < 100ms |
| Grant/Revoke | < 200ms |
| Bulk (100 ops) | < 5s |
| List permissions | < 150ms |
| Get summary | < 200ms |

### Connection Pooling

- PostgreSQL: Managed by isa_common.AsyncPostgresClient
- HTTP clients: httpx with async connection pool
- NATS: Single persistent connection per instance

---

## Deployment Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SERVICE_NAME` | Service identifier | authorization_service |
| `SERVICE_PORT` | HTTP port | 8203 |
| `SERVICE_HOST` | Bind address | 0.0.0.0 |
| `POSTGRES_HOST` | PostgreSQL gRPC host | isa-postgres-grpc |
| `POSTGRES_PORT` | PostgreSQL gRPC port | 50061 |
| `NATS_URL` | NATS connection URL | nats://nats:4222 |
| `CONSUL_HOST` | Consul host | consul |
| `CONSUL_PORT` | Consul port | 8500 |
| `CONSUL_ENABLED` | Enable Consul registration | true |
| `LOG_LEVEL` | Logging level | INFO |

### Kubernetes Resources

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: authorization
  namespace: isa-cloud-staging
spec:
  replicas: 2
  selector:
    matchLabels:
      app: authorization
  template:
    metadata:
      labels:
        app: authorization
    spec:
      containers:
      - name: authorization
        image: authorization_service:latest
        ports:
        - containerPort: 8203
        env:
        - name: SERVICE_PORT
          value: "8203"
        - name: POSTGRES_HOST
          value: "isa-postgres-grpc"
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8203
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health/detailed
            port: 8203
          initialDelaySeconds: 5
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: authorization
  namespace: isa-cloud-staging
spec:
  selector:
    app: authorization
  ports:
  - port: 8203
    targetPort: 8203
```

### Health Check Endpoints

**Basic Health** (`GET /health`):
```json
{
  "status": "healthy",
  "service": "authorization_service",
  "port": 8203,
  "version": "1.0.0"
}
```

**Detailed Health** (`GET /health/detailed`):
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

### Consul Registration

```json
{
  "service_name": "authorization",
  "service_port": 8203,
  "tags": ["authorization", "rbac", "permission-management", "v1"],
  "meta": {
    "version": "1.0.0",
    "capabilities": "resource_access_control,permission_management,bulk_operations",
    "route_count": "10"
  },
  "health_check_type": "http"
}
```

---

## Summary

| Metric | Value |
|--------|-------|
| Total Lines of Code | ~2,500 |
| API Endpoints | 10 |
| Published Events | 5 |
| Consumed Events | 4 |
| Database Tables | 1 (unified) |
| Database Indexes | 7 |
| Service Dependencies | 4 |
| Protocol Interfaces | 2 |
| Repository Methods | 19 |
