# Account Service - Design Document

## Design Overview

**Service Name**: account_service
**Port**: 8201
**Version**: 1.1.0
**Protocol**: HTTP REST API
**Last Updated**: 2025-12-11

### Design Principles
1. **Identity Anchor First**: Single source of truth for user identity
2. **Idempotent by Design**: All operations safe for retry
3. **Event-Driven Synchronization**: Loose coupling via NATS events
4. **Separation of Concerns**: Identity only - no auth, billing, or subscription logic
5. **ACID Guarantees**: PostgreSQL transactions for data integrity
6. **Graceful Degradation**: Event failures don't block operations

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     External Clients                        │
│   (Auth Service, Apps, Admin Dashboard, Other Services)     │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP REST API
                       │ (via API Gateway - JWT validation)
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                 Account Service (Port 8201)                 │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │              FastAPI HTTP Layer (main.py)             │ │
│  │  - Request validation (Pydantic models)               │ │
│  │  - Response formatting                                │ │
│  │  - Error handling & exception handlers                │ │
│  │  - Health checks (/health, /health/detailed)          │ │
│  │  - Lifecycle management (startup/shutdown)            │ │
│  └─────────────────────┬─────────────────────────────────┘ │
│                        │                                     │
│  ┌─────────────────────▼─────────────────────────────────┐ │
│  │      Service Layer (account_service.py)               │ │
│  │  - Business logic (idempotency, validation)           │ │
│  │  - Account ensure operation                           │ │
│  │  - Profile update coordination                        │ │
│  │  - Preferences merge logic                            │ │
│  │  - Status management (activate/deactivate)            │ │
│  │  - Event publishing orchestration                     │ │
│  │  - Statistics aggregation                             │ │
│  │  - Cross-service client calls (subscription_service)  │ │
│  └─────────────────────┬─────────────────────────────────┘ │
│                        │                                     │
│  ┌─────────────────────▼─────────────────────────────────┐ │
│  │      Repository Layer (account_repository.py)         │ │
│  │  - Database CRUD operations                           │ │
│  │  - PostgreSQL gRPC communication                      │ │
│  │  - Query construction (parameterized)                 │ │
│  │  - Result parsing (proto to Pydantic)                 │ │
│  │  - No business logic                                  │ │
│  └─────────────────────┬─────────────────────────────────┘ │
│                        │                                     │
│  ┌─────────────────────▼─────────────────────────────────┐ │
│  │      Event Publishing (events/publishers.py)          │ │
│  │  - NATS event bus integration                         │ │
│  │  - Event model construction                           │ │
│  │  - Async non-blocking publishing                      │ │
│  └───────────────────────────────────────────────────────┘ │
└───────────────────────┼──────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ↓               ↓               ↓
┌──────────────┐ ┌─────────────┐ ┌────────────┐
│  PostgreSQL  │ │    NATS     │ │   Consul   │
│   (gRPC)     │ │  (Events)   │ │ (Discovery)│
│              │ │             │ │            │
│  Schema:     │ │  Subjects:  │ │  Service:  │
│  account     │ │  user.*     │ │  account_  │
│  Table:      │ │             │ │  service   │
│  users       │ │  Publishers:│ │            │
│              │ │  - created  │ │  Health:   │
│  Indexes:    │ │  - updated  │ │  /health   │
│  - user_id   │ │  - deleted  │ │            │
│  - email     │ │  - status   │ │            │
│  - is_active │ │  changed    │ │            │
│  - prefs(GIN)│ │             │ │            │
└──────────────┘ └─────────────┘ └────────────┘

Optional:
┌──────────────────┐
│ subscription_    │ ← Cross-service call for enrichment
│ service          │   (deprecated pattern, being removed)
│ (Port 8214)      │
└──────────────────┘
```

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      Account Service                        │
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────────┐   │
│  │   Models    │───→│   Service   │───→│ Repository   │   │
│  │  (Pydantic) │    │ (Business)  │    │   (Data)     │   │
│  │             │    │             │    │              │   │
│  │ - User      │    │ - Account   │    │ - Account    │   │
│  │ - Account   │    │   Service   │    │   Repository │   │
│  │   Profile   │    │             │    │              │   │
│  │ - Account   │    │             │    │              │   │
│  │   Ensure    │    │             │    │              │   │
│  │   Request   │    │             │    │              │   │
│  │ - Prefs     │    │             │    │              │   │
│  │   Request   │    │             │    │              │   │
│  └─────────────┘    └─────────────┘    └──────────────┘   │
│         ↑                  ↑                    ↑           │
│         │                  │                    │           │
│  ┌──────┴──────────────────┴────────────────────┴───────┐  │
│  │              FastAPI Main (main.py)                   │  │
│  │  - Dependency Injection (get_account_service)        │  │
│  │  - Route Handlers (15 endpoints)                     │  │
│  │  - Exception Handlers (custom errors)                │  │
│  └────────────────────────┬──────────────────────────────┘  │
│                           │                                 │
│  ┌────────────────────────▼──────────────────────────────┐  │
│  │              Event Publishers                         │  │
│  │  (events/publishers.py, events/models.py)            │  │
│  │  - publish_user_created                              │  │
│  │  - publish_user_profile_updated                      │  │
│  │  - publish_user_deleted                              │  │
│  │  - publish_user_status_changed                       │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                 Factory Pattern                       │  │
│  │              (factory.py, protocols.py)               │  │
│  │  - create_account_service (production)                │  │
│  │  - AccountRepositoryProtocol (interface)              │  │
│  │  - Enables dependency injection for tests             │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Design

### 1. FastAPI HTTP Layer (main.py)

**Responsibilities**:
- HTTP request/response handling
- Request validation via Pydantic models
- Route definitions (15 endpoints)
- Health checks
- Service initialization (lifespan management)
- Consul registration
- NATS event bus setup
- Exception handling

**Key Endpoints**:
```python
# Health Checks
GET /health                                  # Basic health check
GET /health/detailed                         # Database connectivity check

# Account Management
POST /api/v1/accounts/ensure                 # Idempotent account creation
GET  /api/v1/accounts/profile/{user_id}      # Get profile by user_id
PUT  /api/v1/accounts/profile/{user_id}      # Update profile
PUT  /api/v1/accounts/preferences/{user_id}  # Update preferences
DELETE /api/v1/accounts/profile/{user_id}    # Soft delete

# Account Discovery
GET /api/v1/accounts                         # List with pagination
GET /api/v1/accounts/search                  # Search by query
GET /api/v1/accounts/by-email/{email}        # Find by email

# Admin Operations
PUT /api/v1/accounts/status/{user_id}        # Change account status

# Statistics
GET /api/v1/accounts/stats                   # Account statistics
```

**Lifecycle Management**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    event_bus = await get_event_bus("account_service")
    await account_microservice.initialize(event_bus=event_bus)

    # Subscribe to events (handlers from events/handlers.py)
    event_handlers = get_event_handlers()
    for event_type, handler in event_handlers.items():
        await event_bus.subscribe_to_events(event_type, handler)

    # Consul registration (metadata includes routes)
    if config.consul_enabled:
        consul_registry.register()

    yield  # Service runs

    # Shutdown
    await account_microservice.shutdown()
    if event_bus:
        await event_bus.close()
```

### 2. Service Layer (account_service.py)

**Class**: `AccountService`

**Responsibilities**:
- Business logic execution
- Idempotent operations
- Event publishing coordination
- Input validation
- Error handling and custom exceptions
- Cross-service integration (subscription_service)

**Key Methods**:
```python
class AccountService:
    def __init__(
        self,
        repository: AccountRepositoryProtocol,
        event_bus: Optional[EventBusProtocol] = None,
        subscription_client: Optional[SubscriptionClientProtocol] = None
    ):
        self.repository = repository
        self.event_bus = event_bus
        self.subscription_client = subscription_client

    # Core Operations
    async def ensure_account(
        self,
        request: AccountEnsureRequest
    ) -> Tuple[AccountProfileResponse, bool]:
        """
        Idempotent account creation.
        Returns (account_profile, was_created: bool)
        """
        # 1. Check if user_id exists
        existing = await self.repository.get_account_by_id(request.user_id)
        if existing:
            return (to_profile_response(existing), False)

        # 2. Check email uniqueness
        email_user = await self.repository.get_account_by_email(request.email)
        if email_user:
            raise AccountValidationError(f"Email {request.email} already exists")

        # 3. Create account in database
        new_account = await self.repository.ensure_account_exists(
            user_id=request.user_id,
            email=request.email,
            name=request.name
        )

        # 4. Publish user.created event (non-blocking)
        if self.event_bus:
            await publish_user_created(
                self.event_bus,
                user_id=new_account.user_id,
                email=new_account.email,
                name=new_account.name,
                subscription_plan="free"  # Deprecated field
            )

        return (to_profile_response(new_account), True)

    async def get_account_profile(
        self,
        user_id: str
    ) -> AccountProfileResponse:
        """Get full account profile"""
        account = await self.repository.get_account_by_id(user_id)
        if not account:
            raise AccountNotFoundError(f"Account not found: {user_id}")
        return to_profile_response(account)

    async def update_account_profile(
        self,
        user_id: str,
        request: AccountUpdateRequest
    ) -> AccountProfileResponse:
        """Update profile fields (name, email)"""
        # 1. Validate account exists
        existing = await self.repository.get_account_by_id(user_id)
        if not existing:
            raise AccountNotFoundError(f"Account not found: {user_id}")

        # 2. Track which fields changed
        updated_fields = []
        update_data = {}

        if request.name and request.name != existing.name:
            update_data["name"] = request.name
            updated_fields.append("name")

        if request.email and request.email != existing.email:
            # Check email uniqueness
            email_account = await self.repository.get_account_by_email(request.email)
            if email_account and email_account.user_id != user_id:
                raise AccountValidationError(f"Email {request.email} already in use")
            update_data["email"] = request.email
            updated_fields.append("email")

        # 3. Update database
        updated_account = await self.repository.update_account_profile(
            user_id, update_data
        )

        # 4. Publish event with changed fields
        if self.event_bus and updated_fields:
            await publish_user_profile_updated(
                self.event_bus,
                user_id=user_id,
                email=updated_account.email,
                name=updated_account.name,
                updated_fields=updated_fields
            )

        return to_profile_response(updated_account)

    async def update_account_preferences(
        self,
        user_id: str,
        request: AccountPreferencesRequest
    ) -> bool:
        """Update preferences (merge strategy)"""
        success = await self.repository.update_account_preferences(
            user_id, request.model_dump()
        )
        return success

    async def change_account_status(
        self,
        user_id: str,
        request: AccountStatusChangeRequest
    ) -> bool:
        """Activate or deactivate account"""
        if request.is_active:
            success = await self.repository.activate_account(user_id)
        else:
            success = await self.repository.deactivate_account(user_id)

        if success and self.event_bus:
            account = await self.repository.get_account_by_id_include_inactive(user_id)
            await publish_user_status_changed(
                self.event_bus,
                user_id=user_id,
                is_active=request.is_active,
                email=account.email if account else None,
                reason=request.reason,
                changed_by="admin"  # TODO: Extract from JWT
            )

        return success

    async def delete_account(
        self,
        user_id: str,
        reason: Optional[str] = None
    ) -> bool:
        """Soft delete account (deactivate)"""
        success = await self.repository.delete_account(user_id)

        if success and self.event_bus:
            account = await self.repository.get_account_by_id_include_inactive(user_id)
            await publish_user_deleted(
                self.event_bus,
                user_id=user_id,
                email=account.email if account else None,
                reason=reason
            )

        return success

    # Query Operations
    async def list_accounts(
        self,
        params: AccountListParams
    ) -> AccountSearchResponse:
        """List accounts with pagination"""
        offset = (params.page - 1) * params.page_size
        accounts = await self.repository.list_accounts(
            limit=params.page_size,
            offset=offset,
            is_active=params.is_active,
            search=params.search
        )

        # Get total count for pagination (future optimization: cache)
        total = await self.repository.get_account_stats()
        total_count = total.get("total_accounts", 0)

        return AccountSearchResponse(
            accounts=[to_summary_response(a) for a in accounts],
            total=total_count,
            page=params.page,
            page_size=params.page_size,
            pages=(total_count + params.page_size - 1) // params.page_size
        )

    async def search_accounts(
        self,
        params: AccountSearchParams
    ) -> List[AccountSummaryResponse]:
        """Search accounts by query"""
        accounts = await self.repository.search_accounts(
            params.query, params.limit
        )
        return [to_summary_response(a) for a in accounts]

    async def get_account_by_email(
        self,
        email: str
    ) -> Optional[AccountProfileResponse]:
        """Get account by email"""
        account = await self.repository.get_account_by_email(email)
        if not account:
            return None
        return to_profile_response(account)

    # Statistics
    async def get_service_stats(self) -> AccountStatsResponse:
        """Get account statistics"""
        stats = await self.repository.get_account_stats()
        return AccountStatsResponse(**stats)

    # Health Check
    async def health_check(self) -> Dict[str, Any]:
        """Database connectivity check"""
        db_connected = await self.repository.check_connection()
        return {
            "status": "healthy" if db_connected else "unhealthy",
            "database_connected": db_connected,
            "timestamp": datetime.utcnow().isoformat()
        }
```

**Custom Exceptions**:
```python
class AccountServiceError(Exception):
    """Base exception for account service"""
    pass

class AccountNotFoundError(AccountServiceError):
    """Account not found"""
    pass

class AccountValidationError(AccountServiceError):
    """Validation error"""
    pass
```

### 3. Repository Layer (account_repository.py)

**Class**: `AccountRepository`

**Responsibilities**:
- PostgreSQL CRUD operations
- gRPC communication with postgres_grpc_service
- Query construction (parameterized)
- Result parsing (proto JSONB to Python dict)
- No business logic

**Key Methods**:
```python
class AccountRepository:
    def __init__(self, config: Optional[ConfigManager] = None):
        # Discover PostgreSQL gRPC service via Consul
        host, port = config.discover_service(
            service_name='postgres_grpc_service',
            default_host='isa-postgres-grpc',
            default_port=50061
        )
        self.db = AsyncPostgresClient(host=host, port=port, user_id='account_service')
        self.schema = "account"
        self.users_table = "users"

    async def get_account_by_id(self, user_id: str) -> Optional[User]:
        """Get active account by user_id"""
        async with self.db:
            result = await self.db.query_row(
                f"SELECT * FROM {self.schema}.{self.users_table} WHERE user_id = $1 AND is_active = TRUE",
                params=[user_id]
            )
        if result:
            return self._row_to_user(result)
        return None

    async def get_account_by_email(self, email: str) -> Optional[User]:
        """Get active account by email"""
        async with self.db:
            result = await self.db.query_row(
                f"SELECT * FROM {self.schema}.{self.users_table} WHERE email = $1 AND is_active = TRUE",
                params=[email]
            )
        if result:
            return self._row_to_user(result)
        return None

    async def ensure_account_exists(
        self,
        user_id: str,
        email: str,
        name: str
    ) -> User:
        """Create account if not exists (idempotent)"""
        # Check existence
        existing = await self.get_account_by_id(user_id)
        if existing:
            return existing

        # Check email uniqueness
        email_user = await self.get_account_by_email(email)
        if email_user:
            raise DuplicateEntryError(f"Email {email} already exists")

        # Create account
        async with self.db:
            await self.db.execute(
                f"""INSERT INTO {self.schema}.{self.users_table}
                    (user_id, email, name, is_active, preferences)
                    VALUES ($1, $2, $3, $4, $5)""",
                params=[user_id, email, name, True, {}]
            )

        created_user = await self.get_account_by_id(user_id)
        if not created_user:
            raise Exception("Failed to create account")
        return created_user

    async def update_account_profile(
        self,
        user_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[User]:
        """Update profile fields (name, email)"""
        allowed_fields = ['name', 'email']
        filtered = {k: v for k, v in update_data.items() if k in allowed_fields and v is not None}

        if not filtered:
            return await self.get_account_by_id(user_id)

        # Build SET clause
        set_parts = []
        values = []
        for i, (field, value) in enumerate(filtered.items(), start=1):
            set_parts.append(f"{field} = ${i}")
            values.append(value)

        # Add updated_at
        set_parts.append(f"updated_at = ${len(values) + 1}")
        values.append(datetime.now(tz=timezone.utc))
        values.append(user_id)

        set_clause = ", ".join(set_parts)

        async with self.db:
            await self.db.execute(
                f"UPDATE {self.schema}.{self.users_table} SET {set_clause} WHERE user_id = ${len(values)}",
                params=values
            )

        return await self.get_account_by_id(user_id)

    async def update_account_preferences(
        self,
        user_id: str,
        preferences: Dict[str, Any]
    ) -> bool:
        """Update preferences (merge strategy)"""
        existing = await self.get_account_by_id(user_id)
        if not existing:
            return False

        # Merge preferences
        current_prefs = getattr(existing, 'preferences', {})
        updated_prefs = {**current_prefs, **preferences}

        async with self.db:
            await self.db.execute(
                f"UPDATE {self.schema}.{self.users_table} SET preferences = $1, updated_at = $2 WHERE user_id = $3",
                params=[updated_prefs, datetime.now(tz=timezone.utc), user_id]
            )
        return True

    async def activate_account(self, user_id: str) -> bool:
        """Activate account"""
        async with self.db:
            await self.db.execute(
                f"UPDATE {self.schema}.{self.users_table} SET is_active = TRUE, updated_at = $1 WHERE user_id = $2",
                params=[datetime.now(tz=timezone.utc), user_id]
            )
        return True

    async def deactivate_account(self, user_id: str) -> bool:
        """Deactivate account"""
        async with self.db:
            await self.db.execute(
                f"UPDATE {self.schema}.{self.users_table} SET is_active = FALSE, updated_at = $1 WHERE user_id = $2",
                params=[datetime.now(tz=timezone.utc), user_id]
            )
        return True

    async def delete_account(self, user_id: str) -> bool:
        """Soft delete (deactivate)"""
        return await self.deactivate_account(user_id)

    async def list_accounts(
        self,
        limit: int = 50,
        offset: int = 0,
        is_active: Optional[bool] = None,
        search: Optional[str] = None
    ) -> List[User]:
        """List accounts with pagination"""
        conditions = []
        params = []
        param_count = 1

        if is_active is not None:
            conditions.append(f"is_active = ${param_count}")
            params.append(is_active)
            param_count += 1

        if search:
            conditions.append(f"(name ILIKE ${param_count} OR email ILIKE ${param_count})")
            params.append(f"%{search}%")
            param_count += 1

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.extend([limit, offset])

        query = f"""
            SELECT * FROM {self.schema}.{self.users_table}
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ${param_count} OFFSET ${param_count + 1}
        """

        async with self.db:
            rows = await self.db.query(query, params=params)

        return [self._row_to_user(row) for row in rows] if rows else []

    async def search_accounts(self, query: str, limit: int = 50) -> List[User]:
        """Search by name or email (ILIKE)"""
        search_pattern = f"%{query}%"

        async with self.db:
            rows = await self.db.query(
                f"""SELECT * FROM {self.schema}.{self.users_table}
                    WHERE (name ILIKE $1 OR email ILIKE $1) AND is_active = TRUE
                    ORDER BY created_at DESC
                    LIMIT $2""",
                params=[search_pattern, limit]
            )

        return [self._row_to_user(row) for row in rows] if rows else []

    async def get_account_stats(self) -> Dict[str, Any]:
        """Get account statistics (concurrent queries)"""
        async with self.db:
            results = await asyncio.gather(
                self.db.query_row(f"SELECT COUNT(*) as total FROM {self.schema}.{self.users_table}"),
                self.db.query_row(f"SELECT COUNT(*) as active FROM {self.schema}.{self.users_table} WHERE is_active = TRUE"),
                self.db.query_row(f"SELECT COUNT(*) as count FROM {self.schema}.{self.users_table} WHERE created_at >= NOW() - INTERVAL '7 days'"),
                self.db.query_row(f"SELECT COUNT(*) as count FROM {self.schema}.{self.users_table} WHERE created_at >= NOW() - INTERVAL '30 days'")
            )

        total_row, active_row, recent_7d_row, recent_30d_row = results
        total_accounts = total_row['total'] if total_row else 0
        active_accounts = active_row['active'] if active_row else 0

        return {
            "total_accounts": total_accounts,
            "active_accounts": active_accounts,
            "inactive_accounts": total_accounts - active_accounts,
            "recent_registrations_7d": recent_7d_row['count'] if recent_7d_row else 0,
            "recent_registrations_30d": recent_30d_row['count'] if recent_30d_row else 0
        }

    def _row_to_user(self, row: Dict[str, Any]) -> User:
        """Convert database row to User model"""
        preferences = row.get('preferences', {})
        if hasattr(preferences, 'fields'):  # proto JSONB
            preferences = MessageToDict(preferences)
        elif not preferences:
            preferences = {}

        return User(
            user_id=row["user_id"],
            email=row.get("email"),
            name=row.get("name"),
            is_active=row.get("is_active", True),
            preferences=preferences,
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at")
        )
```

---

## Database Schema Design

### PostgreSQL Schema: `account`

#### Table: account.users

```sql
-- Create account schema
CREATE SCHEMA IF NOT EXISTS account;

-- Create users table
CREATE TABLE IF NOT EXISTS account.users (
    -- Primary Key
    user_id VARCHAR(255) PRIMARY KEY,

    -- Identity Fields
    email VARCHAR(255),
    name VARCHAR(255),

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Preferences (flexible JSONB)
    preferences JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON account.users(email);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON account.users(is_active);
CREATE INDEX IF NOT EXISTS idx_users_preferences ON account.users USING GIN(preferences);

-- Comments
COMMENT ON TABLE account.users IS 'User account profiles - identity anchor for the platform';
COMMENT ON COLUMN account.users.user_id IS 'Unique user identifier (from auth_service)';
COMMENT ON COLUMN account.users.email IS 'User email address (unique across active accounts)';
COMMENT ON COLUMN account.users.name IS 'User display name';
COMMENT ON COLUMN account.users.is_active IS 'Account active status (soft delete)';
COMMENT ON COLUMN account.users.preferences IS 'User preferences (schema-free JSONB)';
```

**Migration 002: Remove Subscription Data** (Completed):
```sql
-- Remove deprecated subscription fields
ALTER TABLE account.users DROP COLUMN IF EXISTS subscription_status;
DROP INDEX IF EXISTS idx_users_subscription_status;
```

### Index Strategy

1. **Primary Key** (`user_id`): Clustered index for fast lookups
2. **Email Index** (`idx_users_email`): B-tree for email searches (exact match, case-insensitive)
3. **Status Index** (`idx_users_is_active`): Filter active/inactive accounts
4. **Preferences Index** (`idx_users_preferences`): GIN index for JSONB queries (supports `@>`, `?`, etc.)

### JSONB Preferences Examples

```sql
-- Query users with dark theme preference
SELECT * FROM account.users WHERE preferences @> '{"theme": "dark"}';

-- Query users with email notifications enabled
SELECT * FROM account.users WHERE preferences @> '{"notifications": {"email": true}}';

-- Check if user has beta_features flag
SELECT * FROM account.users WHERE preferences ? 'beta_features';
```

---

## Event-Driven Architecture

### Event Publishing (events/publishers.py)

**NATS Subjects**:
```
user.created                # New account created
user.profile_updated        # Profile fields updated
user.deleted                # Account soft-deleted
user.status_changed         # Account activated/deactivated
user.subscription_changed   # Deprecated (migrating to subscription_service)
```

### Event Models (events/models.py)

```python
class UserCreatedEventData(BaseModel):
    """Event: user.created"""
    user_id: str
    email: str
    name: str
    subscription_plan: str  # Deprecated (default: "free")
    created_at: datetime

class UserProfileUpdatedEventData(BaseModel):
    """Event: user.profile_updated"""
    user_id: str
    email: str
    name: str
    updated_fields: List[str]  # e.g., ["name", "email"]
    updated_at: datetime

class UserDeletedEventData(BaseModel):
    """Event: user.deleted"""
    user_id: str
    email: Optional[str]
    reason: Optional[str]  # "user_requested", "policy_violation", "admin_action"
    deleted_at: datetime

class UserStatusChangedEventData(BaseModel):
    """Event: user.status_changed"""
    user_id: str
    email: Optional[str]
    is_active: bool
    reason: Optional[str]
    changed_at: datetime
    changed_by: Optional[str]  # "admin", "system"
```

### Event Flow Diagram

```
┌─────────────┐
│   Client    │ (Auth Service, Admin)
└──────┬──────┘
       │ POST /accounts/ensure
       ↓
┌──────────────────┐
│  Account Service │
│                  │
│  1. Validate     │
│  2. Create User  │───→ PostgreSQL (account.users)
│  3. Publish      │         │
└──────────────────┘         │ Success
       │                     ↓
       │              ┌──────────────┐
       │              │ Return User  │
       │              └──────────────┘
       │ Event: user.created
       ↓
┌─────────────────┐
│   NATS Bus      │
│ Subject:        │
│ user.created    │
└────────┬────────┘
         │
         ├──→ Subscription Service (create subscription)
         ├──→ Wallet Service (initialize wallet)
         ├──→ Audit Service (log creation)
         ├──→ Analytics Service (track acquisition)
         └──→ Organization Service (check invitations)
```

---

## Data Flow Diagrams

### 1. Idempotent Account Creation Flow

```
Auth Service calls POST /api/v1/accounts/ensure
    │
    ↓
┌─────────────────────────────────┐
│  AccountService.ensure_account  │
│                                 │
│  Step 1: Check if user exists   │
│    repository.get_account_by_id()├──→ PostgreSQL: SELECT ... WHERE user_id = $1
│                            ←────┤         │
│    If exists → Return account   │         │ Result: User | None
│                                 │         │
│  Step 2: Check email uniqueness │         │
│    repository.get_account_by_email()─────→ PostgreSQL: SELECT ... WHERE email = $1
│                            ←────┤               │
│    If exists → Raise error      │               │ Result: User | None
│                                 │               │
│  Step 3: Create account         │               │
│    repository.ensure_account_exists()──────────→ PostgreSQL: INSERT INTO account.users
│                            ←────┤                       │
│    Success                      │                       │ Result: User
│                                 │                       │
│  Step 4: Publish event          │                       │
│    publish_user_created() ──────┼──────────────────────→ NATS: user.created
│                                 │                            │
└─────────────────────────────────┘                            │
    │                                                          │
    │ Return (User, was_created=True)                         │
    ↓                                                          │
Auth Service receives profile                                 │
                                                               ↓
                                               ┌────────────────────────────┐
                                               │   Event Subscribers        │
                                               │ - Subscription Service     │
                                               │ - Wallet Service           │
                                               │ - Audit Service            │
                                               │ - Analytics Service        │
                                               └────────────────────────────┘
```

### 2. Profile Update Flow

```
User updates name: "John Doe" → "John Smith"
    │
    ↓
PUT /api/v1/accounts/profile/{user_id}
    │
    ↓
┌──────────────────────────────────────┐
│  AccountService.update_account_profile│
│                                       │
│  Step 1: Validate account exists      │
│    repository.get_account_by_id()  ───┼──→ PostgreSQL
│                                   ←───┤    Result: User
│                                       │
│  Step 2: Track changed fields         │
│    Compare: request.name != existing.name │
│    updated_fields = ["name"]          │
│                                       │
│  Step 3: Email uniqueness (if changed)│
│    (if email changed)                 │
│    repository.get_account_by_email()──┼──→ PostgreSQL
│                                   ←───┤    Result: None (OK)
│                                       │
│  Step 4: Update database              │
│    repository.update_account_profile()├──→ PostgreSQL: UPDATE account.users
│                                   ←───┤         SET name = $1, updated_at = $2
│    Success                            │         WHERE user_id = $3
│                                       │
│  Step 5: Publish event                │
│    publish_user_profile_updated()  ───┼──→ NATS: user.profile_updated
│    Payload:                           │    {user_id, email, name, updated_fields: ["name"]}
│      updated_fields = ["name"]        │
└───────────────────────────────────────┘
    │
    ↓
Return updated profile to user
```

### 3. Account Search Flow

```
Admin searches: "john"
    │
    ↓
GET /api/v1/accounts/search?query=john&limit=50
    │
    ↓
┌─────────────────────────────────┐
│  AccountService.search_accounts │
│                                 │
│  repository.search_accounts()   │───→ PostgreSQL:
│    query="john"                 │       SELECT * FROM account.users
│    limit=50                     │       WHERE (name ILIKE '%john%' OR email ILIKE '%john%')
│                            ←────┤         AND is_active = TRUE
│    Result: List[User]           │       ORDER BY created_at DESC
│                                 │       LIMIT 50
│  Convert to summary responses   │
│    [to_summary_response(user)   │
│     for user in users]          │
└─────────────────────────────────┘
    │
    ↓
Return [AccountSummaryResponse, ...]
```

### 4. Account Deactivation Flow

```
Admin deactivates account (policy violation)
    │
    ↓
PUT /api/v1/accounts/status/{user_id}
{is_active: false, reason: "Policy violation"}
    │
    ↓
┌─────────────────────────────────────┐
│ AccountService.change_account_status│
│                                     │
│  Step 1: Deactivate                 │
│    repository.deactivate_account() ─┼──→ PostgreSQL:
│                                ←────┤      UPDATE account.users
│    Success                          │      SET is_active = FALSE, updated_at = NOW()
│                                     │      WHERE user_id = $1
│  Step 2: Get account for event      │
│    repository.get_account_by_id_    │
│      include_inactive()          ───┼──→ PostgreSQL
│                                ←────┤    Result: User (email for event)
│                                     │
│  Step 3: Publish event              │
│    publish_user_status_changed() ───┼──→ NATS: user.status_changed
│    Payload:                         │    {user_id, email, is_active: false,
│      is_active=false                │     reason: "Policy violation",
│      reason="Policy violation"      │     changed_by: "admin"}
│      changed_by="admin"             │
└─────────────────────────────────────┘
    │
    ↓
Return {message: "Account deactivated successfully"}
    │
    ↓
┌────────────────────────────────┐
│   Event Subscribers React       │
│ - Session Service: Invalidate   │
│ - Subscription Service: Pause   │
│ - Audit Service: Log event      │
│ - Notification: Email user      │
└────────────────────────────────┘
```

---

## Technology Stack

### Core Technologies
- **Python 3.11+**: Programming language
- **FastAPI 0.104+**: Web framework
- **Pydantic 2.0+**: Data validation
- **asyncio**: Async/await concurrency
- **uvicorn**: ASGI server

### Data Storage
- **PostgreSQL 15+**: Primary database
- **AsyncPostgresClient** (gRPC): Database communication
- **Schema**: `account`
- **Table**: `users`

### Event-Driven
- **NATS 2.9+**: Event bus
- **Subjects**: `user.*`
- **Publishers**: Account Service
- **Subscribers**: 10+ services

### Service Discovery
- **Consul 1.15+**: Service registry
- **Health Checks**: HTTP `/health`
- **Metadata**: Route registration

### Dependency Injection
- **Protocols (typing.Protocol)**: Interface definitions
- **Factory Pattern**: Production vs test instances
- **ConfigManager**: Environment-based configuration

### Observability
- **Structured Logging**: JSON format
- **core.logger**: Service logger
- **Health Endpoints**: `/health`, `/health/detailed`

---

## Security Considerations

### Input Validation
- **Pydantic Models**: All requests validated
- **Email Validation**: Regex pattern matching
- **SQL Injection**: Parameterized queries via gRPC
- **XSS Prevention**: Input sanitization

### Access Control
- **User Isolation**: All queries filtered by user_id
- **JWT Authentication**: Handled by API Gateway
- **Authorization**: Admin endpoints require admin role
- **RBAC**: Future enhancement

### Data Privacy
- **Soft Delete**: Account data preserved for audit
- **GDPR Compliance**: Right to deletion supported
- **Encryption in Transit**: TLS for all communication
- **Encryption at Rest**: Database-level encryption (future)

### Rate Limiting (Future)
- **Per User**: 1000 requests/hour
- **Per IP**: 5000 requests/hour
- **Burst**: 100 requests/minute

---

## Performance Optimization

### Database Optimization
- **Indexes**: Strategic indexes on user_id, email, is_active, preferences
- **Connection Pooling**: gRPC client pools connections
- **Concurrent Queries**: `asyncio.gather` for stats
- **Query Optimization**: Avoid N+1, use LIMIT/OFFSET

### API Optimization
- **Async Operations**: All I/O is async
- **Batch Operations**: Future: Bulk update endpoints
- **Pagination**: Max page_size=100 to prevent memory overflow
- **Caching**: Future: Redis for frequently accessed profiles

### Event Publishing
- **Non-Blocking**: Event failures don't block operations
- **Async Publishing**: Fire-and-forget pattern
- **Error Logging**: Failed publishes logged for retry

---

## Error Handling

### HTTP Status Codes
- `200 OK`: Successful operation
- `201 Created`: New account created
- `400 Bad Request`: Validation error, duplicate email
- `404 Not Found`: Account not found
- `500 Internal Server Error`: Database error, unexpected error
- `503 Service Unavailable`: Database unavailable

### Error Response Format
```json
{
  "detail": "Account not found with user_id: usr_xyz"
}
```

### Exception Handling
```python
@app.exception_handler(AccountValidationError)
async def validation_error_handler(request, exc):
    return HTTPException(status_code=400, detail=str(exc))

@app.exception_handler(AccountNotFoundError)
async def not_found_error_handler(request, exc):
    return HTTPException(status_code=404, detail=str(exc))

@app.exception_handler(AccountServiceError)
async def service_error_handler(request, exc):
    return HTTPException(status_code=500, detail=str(exc))
```

---

## Testing Strategy

### Contract Testing (Layer 4 & 5)
- **Data Contract**: Pydantic schema validation
- **Logic Contract**: Business rule documentation
- **Component Tests**: Factory, builder, validation tests

### Integration Testing
- **HTTP + Database**: Full request/response cycle
- **Event Publishing**: Verify events published correctly
- **Cross-Service**: Subscription service client mocks

### API Testing
- **Endpoint Contracts**: All 15 endpoints tested
- **Error Handling**: Validation, not found, server errors
- **Pagination**: Page boundaries, empty results

### Smoke Testing
- **E2E Scripts**: Bash scripts for critical paths
- **Health Checks**: Service startup validation
- **Database Connectivity**: PostgreSQL availability

---

**Document Version**: 1.0
**Last Updated**: 2025-12-11
**Maintained By**: Account Service Engineering Team
**Related Documents**:
- Domain Context: docs/domain/account_service.md
- PRD: docs/prd/account_service.md
- Data Contract: tests/contracts/account/data_contract.py (next)
- Logic Contract: tests/contracts/account/logic_contract.md (next)
