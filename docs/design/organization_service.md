# Organization Service - Design Document

## Architecture Overview

### Service Architecture
```
┌────────────────────────────────────────────────────────────────────────────┐
│                        Organization Service                                  │
├────────────────────────────────────────────────────────────────────────────┤
│  FastAPI Application (main.py)                                              │
│  ├─ Organization Routes (CRUD, Members, Context)                            │
│  ├─ Family Sharing Routes (Sharing, Permissions, Usage)                     │
│  ├─ Admin Routes (Platform management)                                      │
│  └─ Dependency Injection Setup (get_organization_service, etc.)             │
├────────────────────────────────────────────────────────────────────────────┤
│  Service Layer (organization_service.py, family_sharing_service.py)         │
│  ├─ Business Logic                                                          │
│  ├─ Access Control Validation                                               │
│  ├─ Event Publishing                                                        │
│  └─ Cross-Service Orchestration                                             │
├────────────────────────────────────────────────────────────────────────────┤
│  Repository Layer (organization_repository.py, family_sharing_repository.py)│
│  ├─ Database Queries (PostgreSQL via gRPC)                                  │
│  ├─ Data Mapping                                                            │
│  └─ Transaction Management                                                  │
├────────────────────────────────────────────────────────────────────────────┤
│  Dependency Injection (protocols.py, factory.py)                            │
│  ├─ OrganizationRepositoryProtocol                                          │
│  ├─ FamilySharingRepositoryProtocol                                         │
│  ├─ EventBusProtocol                                                        │
│  └─ AccountClientProtocol                                                   │
└────────────────────────────────────────────────────────────────────────────┘

External Dependencies:
- PostgreSQL via gRPC (data persistence)
- NATS (event publishing)
- Consul (service discovery)
- Account Service (user validation)
- Auth Service (token validation via gateway)
```

### Component Diagram
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   API Gateway   │────▶│  Organization   │────▶│   PostgreSQL    │
│                 │     │    Service      │     │   (gRPC)        │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
                    ▼            ▼            ▼
            ┌───────────┐ ┌───────────┐ ┌───────────┐
            │   NATS    │ │  Consul   │ │  Account  │
            │  Events   │ │  Registry │ │  Service  │
            └───────────┘ └───────────┘ └───────────┘
```

---

## Component Design

### Service Layer

#### OrganizationService
```python
class OrganizationService:
    """Organization business logic"""

    def __init__(
        self,
        repository: OrganizationRepositoryProtocol,
        event_bus: EventBusProtocol,
        account_client: AccountClientProtocol
    ):
        self.repository = repository
        self.event_bus = event_bus
        self.account_client = account_client

    # Organization CRUD
    async def create_organization(request, owner_user_id) -> OrganizationResponse
    async def get_organization(organization_id, user_id) -> OrganizationResponse
    async def update_organization(organization_id, request, user_id) -> OrganizationResponse
    async def delete_organization(organization_id, user_id) -> bool
    async def get_user_organizations(user_id) -> OrganizationListResponse

    # Member Management
    async def add_organization_member(org_id, request, requesting_user_id) -> OrganizationMemberResponse
    async def update_organization_member(org_id, member_id, request, requesting_user_id) -> OrganizationMemberResponse
    async def remove_organization_member(org_id, member_id, requesting_user_id) -> bool
    async def get_organization_members(org_id, user_id, limit, offset, role_filter) -> OrganizationMemberListResponse

    # Context Switching
    async def switch_user_context(user_id, organization_id) -> OrganizationContextResponse

    # Statistics
    async def get_organization_stats(organization_id, user_id) -> OrganizationStatsResponse
    async def get_organization_usage(organization_id, user_id, start_date, end_date) -> OrganizationUsageResponse

    # Access Control Helpers
    async def check_user_access(organization_id, user_id) -> bool
    async def check_admin_access(organization_id, user_id) -> bool
    async def check_owner_access(organization_id, user_id) -> bool
```

#### FamilySharingService
```python
class FamilySharingService:
    """Family sharing business logic"""

    def __init__(
        self,
        repository: FamilySharingRepositoryProtocol,
        event_bus: EventBusProtocol
    ):
        self.repository = repository
        self.event_bus = event_bus

    # Sharing CRUD
    async def create_sharing(organization_id, request, created_by) -> SharingResourceResponse
    async def get_sharing(sharing_id, user_id) -> SharedResourceDetailResponse
    async def update_sharing(sharing_id, request, updated_by) -> SharingResourceResponse
    async def delete_sharing(sharing_id, deleted_by) -> bool
    async def list_organization_sharings(org_id, user_id, resource_type, status, limit, offset) -> List

    # Permission Management
    async def update_member_permission(sharing_id, request, updated_by) -> MemberSharingPermissionResponse
    async def revoke_member_access(sharing_id, user_id, revoked_by) -> bool
    async def get_member_shared_resources(org_id, request) -> MemberSharedResourcesResponse

    # Usage Statistics
    async def get_sharing_usage_stats(sharing_id, period_days) -> SharingUsageStatsResponse
```

### Repository Layer

#### OrganizationRepository
```python
class OrganizationRepository:
    """PostgreSQL data access for organizations"""

    # Organization Operations
    async def create_organization(data, owner_user_id) -> OrganizationResponse
    async def get_organization(organization_id) -> Optional[OrganizationResponse]
    async def update_organization(organization_id, data) -> Optional[OrganizationResponse]
    async def delete_organization(organization_id) -> bool
    async def get_user_organizations(user_id) -> List[Dict]
    async def list_all_organizations(limit, offset, search, plan_filter, status_filter) -> List

    # Member Operations
    async def add_organization_member(org_id, user_id, role, permissions) -> OrganizationMemberResponse
    async def update_organization_member(org_id, user_id, data) -> Optional[OrganizationMemberResponse]
    async def remove_organization_member(org_id, user_id) -> bool
    async def get_organization_member(org_id, user_id) -> Optional[OrganizationMemberResponse]
    async def get_organization_members(org_id, limit, offset, role_filter, status_filter) -> List
    async def get_user_organization_role(org_id, user_id) -> Optional[Dict]
    async def get_organization_member_count(org_id) -> int

    # Statistics
    async def get_organization_stats(organization_id) -> Dict
```

#### FamilySharingRepository
```python
class FamilySharingRepository:
    """PostgreSQL data access for family sharing"""

    # Sharing Operations
    async def create_sharing(data) -> Optional[Dict]
    async def get_sharing(sharing_id) -> Optional[Dict]
    async def update_sharing(sharing_id, data) -> Optional[Dict]
    async def delete_sharing(sharing_id) -> bool
    async def list_organization_sharings(org_id, resource_type, status, limit, offset) -> List

    # Permission Operations
    async def create_member_permission(data) -> Optional[Dict]
    async def get_member_permission(sharing_id, user_id) -> Optional[Dict]
    async def update_member_permission(sharing_id, user_id, data) -> Optional[Dict]
    async def delete_member_permission(sharing_id, user_id) -> bool
    async def get_sharing_member_permissions(sharing_id) -> List[Dict]
    async def delete_sharing_member_permissions(sharing_id) -> bool

    # Queries
    async def get_member_permissions(org_id, user_id, resource_type, status, limit, offset) -> List
    async def count_member_permissions(org_id, user_id, resource_type, status) -> int

    # Validation Helpers
    async def check_organization_admin(org_id, user_id) -> bool
    async def check_organization_member(org_id, user_id) -> bool
    async def get_organization_members(org_id) -> List[Dict]
```

---

## Database Schemas

### Table: organization_service.organizations
```sql
CREATE TABLE IF NOT EXISTS organization_service.organizations (
    organization_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(20) DEFAULT 'business',
    billing_email VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'active',
    plan VARCHAR(50) DEFAULT 'free',
    credits_pool INTEGER DEFAULT 0,
    max_members INTEGER DEFAULT 10,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_org_status ON organization_service.organizations(status);
CREATE INDEX idx_org_plan ON organization_service.organizations(plan);
CREATE INDEX idx_org_name ON organization_service.organizations(name);
```

### Table: organization_service.organization_members
```sql
CREATE TABLE IF NOT EXISTS organization_service.organization_members (
    organization_id VARCHAR(50) REFERENCES organization_service.organizations(organization_id) ON DELETE CASCADE,
    user_id VARCHAR(50) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'member',
    status VARCHAR(20) DEFAULT 'active',
    permissions JSONB DEFAULT '[]',
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (organization_id, user_id)
);

CREATE INDEX idx_member_user ON organization_service.organization_members(user_id);
CREATE INDEX idx_member_role ON organization_service.organization_members(role);
CREATE INDEX idx_member_status ON organization_service.organization_members(status);
```

### Table: organization_service.family_sharings
```sql
CREATE TABLE IF NOT EXISTS organization_service.family_sharings (
    sharing_id VARCHAR(50) PRIMARY KEY,
    organization_id VARCHAR(50) REFERENCES organization_service.organizations(organization_id) ON DELETE CASCADE,
    resource_type VARCHAR(30) NOT NULL,
    resource_id VARCHAR(100) NOT NULL,
    resource_name VARCHAR(255),
    created_by VARCHAR(50) NOT NULL,
    share_with_all_members BOOLEAN DEFAULT false,
    default_permission VARCHAR(30) DEFAULT 'read_write',
    status VARCHAR(20) DEFAULT 'active',
    quota_settings JSONB DEFAULT '{}',
    restrictions JSONB DEFAULT '{}',
    expires_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sharing_org ON organization_service.family_sharings(organization_id);
CREATE INDEX idx_sharing_type ON organization_service.family_sharings(resource_type);
CREATE INDEX idx_sharing_status ON organization_service.family_sharings(status);
CREATE INDEX idx_sharing_resource ON organization_service.family_sharings(resource_id);
```

### Table: organization_service.sharing_member_permissions
```sql
CREATE TABLE IF NOT EXISTS organization_service.sharing_member_permissions (
    permission_id VARCHAR(50) PRIMARY KEY,
    sharing_id VARCHAR(50) REFERENCES organization_service.family_sharings(sharing_id) ON DELETE CASCADE,
    user_id VARCHAR(50) NOT NULL,
    permission_level VARCHAR(30) DEFAULT 'read_write',
    quota_allocated JSONB DEFAULT '{}',
    quota_used JSONB DEFAULT '{}',
    restrictions JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_accessed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(sharing_id, user_id)
);

CREATE INDEX idx_perm_sharing ON organization_service.sharing_member_permissions(sharing_id);
CREATE INDEX idx_perm_user ON organization_service.sharing_member_permissions(user_id);
CREATE INDEX idx_perm_active ON organization_service.sharing_member_permissions(is_active);
```

---

## Data Flow Diagrams

### Organization Creation Flow
```
Client -> POST /api/v1/organizations
  -> require_auth_or_internal_service (validate token)
    -> OrganizationService.create_organization(request, user_id)
      -> Validate request (name, billing_email)
      -> repository.create_organization(data, owner_user_id)
        -> PostgreSQL (via gRPC)
        -> Create organization record
        -> Add owner as member
      <- organization
      -> event_bus.publish_event(organization.created)
        -> NATS
    <- OrganizationResponse
  <- HTTP 200 {organization}
```

### Member Addition Flow
```
Client -> POST /api/v1/organizations/{org_id}/members
  -> require_auth_or_internal_service (validate token)
    -> OrganizationService.add_organization_member(org_id, request, user_id)
      -> check_admin_access(org_id, user_id)
        -> repository.get_user_organization_role()
        <- role (owner/admin/member)
      -> Validate member limit not exceeded
      -> Validate user_id exists (optional)
      -> repository.add_organization_member(org_id, user_id, role, permissions)
        -> PostgreSQL (via gRPC)
        -> Insert member record
      <- member
      -> event_bus.publish_event(organization.member_added)
        -> NATS
    <- OrganizationMemberResponse
  <- HTTP 200 {member}
```

### Context Switch Flow
```
Client -> POST /api/v1/organizations/context
  -> require_auth_or_internal_service (validate token)
    -> OrganizationService.switch_user_context(user_id, organization_id)
      -> repository.get_user_organization_role(org_id, user_id)
        -> PostgreSQL (via gRPC)
      <- role_data (role, status, permissions)
      -> Validate status == 'active'
      -> repository.get_organization(organization_id)
        -> PostgreSQL (via gRPC)
      <- organization
      -> Build context response
    <- OrganizationContextResponse
  <- HTTP 200 {context}
```

### Family Sharing Creation Flow
```
Client -> POST /api/v1/organizations/{org_id}/sharing
  -> require_auth_or_internal_service (validate token)
    -> FamilySharingService.create_sharing(org_id, request, user_id)
      -> _check_organization_admin_permission(org_id, user_id)
        -> repository.check_organization_admin()
      <- has_permission
      -> Generate sharing_id (UUID)
      -> repository.create_sharing(sharing_data)
        -> PostgreSQL (via gRPC)
      <- sharing
      -> If shared_with_members: create individual permissions
      -> If share_with_all_members: create permissions for all members
      -> event_bus.publish_event(family.resource_shared)
        -> NATS
    <- SharingResourceResponse
  <- HTTP 200 {sharing}
```

---

## Technology Stack

- **Language**: Python 3.9+
- **Framework**: FastAPI
- **Validation**: Pydantic
- **Database**: PostgreSQL (via gRPC client)
- **Event Bus**: NATS
- **Service Discovery**: Consul
- **HTTP Client**: httpx (async)
- **Logging**: Python logging with structured output

---

## Security Considerations

### Authentication
- JWT token validation via API Gateway
- Internal service calls via X-Internal-Call header
- User ID extracted from validated token claims

### Authorization
- Role-based access control (RBAC)
- Owner > Admin > Member > Guest hierarchy
- Permission validation before all operations
- Context-aware authorization

### Data Protection
- No PII in logs (user IDs only)
- Soft delete for audit trails
- Input validation via Pydantic
- SQL injection prevention (parameterized queries)

### API Security
- Rate limiting at gateway level
- Request validation
- Error messages don't expose internals

---

## Event-Driven Architecture

### Published Events

| Event Type | Trigger | Data |
|------------|---------|------|
| organization.created | Organization created | org_id, name, owner, plan |
| organization.updated | Organization updated | org_id, updated_fields |
| organization.deleted | Organization deleted | org_id, name, deleted_by |
| organization.member_added | Member added | org_id, user_id, role |
| organization.member_removed | Member removed | org_id, user_id, removed_by |
| family.resource_shared | Resource shared | sharing_id, resource_type, org_id |

### Subscribed Events

| Event Pattern | Source | Action |
|---------------|--------|--------|
| account_service.user.deleted | account_service | Remove user from all orgs |
| album_service.album.deleted | album_service | Remove album sharing refs |
| billing_service.billing.subscription_changed | billing_service | Update org plan |

---

## Error Handling

### Error Types and HTTP Codes

| Exception | HTTP Code | Description |
|-----------|-----------|-------------|
| OrganizationNotFoundError | 404 | Organization not found |
| OrganizationAccessDeniedError | 403 | Access denied |
| OrganizationValidationError | 400 | Validation failed |
| SharingNotFoundError | 404 | Sharing not found |
| SharingAccessDeniedError | 403 | Sharing access denied |
| OrganizationServiceError | 500 | Internal error |

### Error Response Format
```json
{
  "detail": "Error message describing the issue"
}
```

---

## Performance Considerations

### Database Optimization
- Indexes on frequently queried columns (status, user_id, org_id)
- Pagination for list operations (max 1000)
- Efficient JOIN queries for member lookups

### Caching Strategy
- No caching in service layer (stateless)
- Database-level query caching
- Gateway-level response caching for health endpoints

### Async Operations
- All repository operations are async
- Event publishing is fire-and-forget (non-blocking)
- Connection pooling for PostgreSQL

---

## Deployment Configuration

### Environment Variables
```
SERVICE_NAME=organization_service
SERVICE_PORT=8203
SERVICE_HOST=0.0.0.0
DEBUG=false
LOG_LEVEL=INFO

# PostgreSQL
POSTGRES_HOST=isa-postgres-grpc
POSTGRES_PORT=50061

# NATS
NATS_URL=nats://nats:4222

# Consul
CONSUL_ENABLED=true
CONSUL_HOST=consul
CONSUL_PORT=8500
```

### Health Checks
- GET /health: Basic health check
- GET /info: Service information

### Service Discovery
- Consul registration on startup
- Automatic deregistration on shutdown
- Health check via HTTP endpoint

---

## Dependency Injection Pattern

### Factory Functions
```python
# factory.py
def create_organization_service(config, event_bus, account_client):
    from .organization_repository import OrganizationRepository
    repository = OrganizationRepository(config=config)
    return OrganizationService(
        repository=repository,
        event_bus=event_bus,
        account_client=account_client
    )

def create_family_sharing_service(config, event_bus):
    from .family_sharing_repository import FamilySharingRepository
    repository = FamilySharingRepository(config=config)
    return FamilySharingService(
        repository=repository,
        event_bus=event_bus
    )
```

### Testing Pattern
```python
# Tests inject mock repositories
mock_repo = MockOrganizationRepository()
mock_event_bus = MockEventBus()
service = OrganizationService(
    repository=mock_repo,
    event_bus=mock_event_bus
)
```

---

## Testing Strategy

### Layer 1: Unit Tests
- Pydantic model validation
- Factory method validation
- Pure function testing

### Layer 2: Component Tests
- Service logic with mocked dependencies
- Event publishing verification
- Business rule validation

### Layer 3: Integration Tests
- Real HTTP requests to service
- Database persistence verification
- X-Internal-Call header for auth bypass

### Layer 4: API Tests
- Contract validation with JWT auth
- Error response validation
- End-to-end flow testing

### Layer 5: Smoke Tests
- E2E bash scripts
- Basic operation verification
- Health check validation

---

**Document Version**: 1.0
**Last Updated**: 2025-12-15
**Maintained By**: Organization Service Team
