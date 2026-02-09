# Membership Service - Design Document

## Design Overview

**Service Name**: membership_service
**Port**: 8250
**Version**: 1.0.0
**Protocol**: HTTP REST API
**Last Updated**: 2025-12-19

### Design Principles
1. **Loyalty-First Design**: Optimized for high-frequency point operations
2. **Atomic Point Transactions**: No partial point operations allowed
3. **Event-Driven Synchronization**: Loose coupling via NATS events
4. **Separation of Concerns**: Membership owns tiers/points, not rewards/payments
5. **ACID Guarantees**: PostgreSQL transactions for data integrity
6. **Graceful Degradation**: Event failures don't block operations

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     External Clients                        │
│   (Web App, Mobile App, Other Services)                    │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP REST API
                       │ (via API Gateway - JWT validation)
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                 Membership Service (Port 8250)              │
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
│  │      Service Layer (membership_service.py)            │ │
│  │  - Business logic (enrollment, points, tiers)         │ │
│  │  - Tier multiplier calculation                        │ │
│  │  - Point transaction management                       │ │
│  │  - Tier evaluation and progression                    │ │
│  │  - Event publishing orchestration                     │ │
│  │  - Statistics aggregation                             │ │
│  └─────────────────────┬─────────────────────────────────┘ │
│                        │                                     │
│  ┌─────────────────────▼─────────────────────────────────┐ │
│  │      Repository Layer (membership_repository.py)      │ │
│  │  - Database CRUD operations                           │ │
│  │  - PostgreSQL gRPC communication                      │ │
│  │  - Query construction (parameterized)                 │ │
│  │  - Result parsing (proto to Pydantic)                 │ │
│  │  - Atomic point transactions                          │ │
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
│  membership  │ │  membership │ │  membership│
│              │ │  .enrolled  │ │  _service  │
│  Tables:     │ │  .upgraded  │ │            │
│  - members   │ │  points.*   │ │  Health:   │
│  - history   │ │  benefit.*  │ │  /health   │
│  - benefits  │ │             │ │            │
└──────────────┘ └─────────────┘ └────────────┘
```

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      Membership Service                     │
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────────┐   │
│  │   Models    │───→│   Service   │───→│ Repository   │   │
│  │  (Pydantic) │    │ (Business)  │    │   (Data)     │   │
│  │             │    │             │    │              │   │
│  │ - Membership│    │ -Membership │    │ -Membership  │   │
│  │ - MemberTier│    │  Service    │    │  Repository  │   │
│  │ - Points    │    │             │    │              │   │
│  │ - History   │    │             │    │              │   │
│  │ - Benefit   │    │             │    │              │   │
│  └─────────────┘    └─────────────┘    └──────────────┘   │
│         ↑                  ↑                    ↑           │
│         │                  │                    │           │
│  ┌──────┴──────────────────┴────────────────────┴───────┐  │
│  │              FastAPI Main (main.py)                   │  │
│  │  - Dependency Injection (get_membership_service)     │  │
│  │  - Route Handlers (17 endpoints)                     │  │
│  │  - Exception Handlers (custom errors)                │  │
│  └────────────────────────┬──────────────────────────────┘  │
│                           │                                 │
│  ┌────────────────────────▼──────────────────────────────┐  │
│  │              Event Publishers                         │  │
│  │  (events/publishers.py, events/models.py)            │  │
│  │  - publish_membership_enrolled                       │  │
│  │  - publish_membership_tier_upgraded                  │  │
│  │  - publish_points_earned                             │  │
│  │  - publish_points_redeemed                           │  │
│  │  - publish_benefit_used                              │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                 Factory Pattern                       │  │
│  │              (factory.py, protocols.py)               │  │
│  │  - create_membership_service (production)            │  │
│  │  - MembershipRepositoryProtocol (interface)          │  │
│  │  - EventBusProtocol (interface)                      │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Design

### 1. FastAPI HTTP Layer (main.py)

**Responsibilities**:
- HTTP request/response handling
- Request validation via Pydantic models
- Route definitions (17 endpoints)
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

# Membership Management
POST /api/v1/memberships                     # Enroll membership
GET  /api/v1/memberships/{id}               # Get by ID
GET  /api/v1/memberships/user/{user_id}     # Get by user
GET  /api/v1/memberships                    # List memberships
POST /api/v1/memberships/{id}/cancel        # Cancel membership
PUT  /api/v1/memberships/{id}/suspend       # Suspend membership
PUT  /api/v1/memberships/{id}/reactivate    # Reactivate membership

# Tier Operations
GET  /api/v1/memberships/{id}/tier          # Get tier status

# Points Operations
POST /api/v1/memberships/points/earn        # Earn points
POST /api/v1/memberships/points/redeem      # Redeem points
GET  /api/v1/memberships/points/balance     # Get balance

# Benefits Operations
GET  /api/v1/memberships/{id}/benefits      # List benefits
POST /api/v1/memberships/{id}/benefits/use  # Use benefit

# History & Stats
GET  /api/v1/memberships/{id}/history       # Get history
GET  /api/v1/memberships/stats              # Get statistics
```

**Lifecycle Management**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    event_bus = await get_event_bus("membership_service")
    await membership_microservice.initialize(event_bus=event_bus)

    # Subscribe to events (handlers from events/handlers.py)
    event_handlers = get_event_handlers()
    for event_type, handler in event_handlers.items():
        await event_bus.subscribe_to_events(event_type, handler)

    # Consul registration
    if config.consul_enabled:
        consul_registry.register()

    yield  # Service runs

    # Shutdown
    await membership_microservice.shutdown()
    if event_bus:
        await event_bus.close()
```

### 2. Service Layer (membership_service.py)

**Class**: `MembershipService`

**Responsibilities**:
- Business logic execution
- Tier multiplier calculation
- Point transaction management
- Tier evaluation and progression
- Event publishing coordination
- Error handling and custom exceptions

**Key Methods**:
```python
class MembershipService:
    def __init__(
        self,
        repository: MembershipRepositoryProtocol,
        event_bus: Optional[EventBusProtocol] = None,
    ):
        self.repository = repository
        self.event_bus = event_bus
        self._tier_cache: Dict[str, TierConfig] = {}

    async def initialize(self):
        """Initialize service and load tier cache"""
        await self.repository.initialize()
        await self._load_tier_cache()

    async def enroll_membership(
        self,
        request: EnrollMembershipRequest
    ) -> Tuple[MembershipResponse, bool]:
        """
        Enroll new membership.
        Returns (membership_response, was_created: bool)
        """
        # 1. Check if user already has membership
        existing = await self.repository.get_membership_by_user(request.user_id)
        if existing and existing.status in ['active', 'pending']:
            raise DuplicateMembershipError("User already has active membership")

        # 2. Determine initial tier (bronze)
        tier = self._tier_cache.get('bronze')

        # 3. Calculate enrollment bonus
        bonus_points = self._calculate_enrollment_bonus(request.promo_code)

        # 4. Create membership
        membership = await self.repository.create_membership(
            user_id=request.user_id,
            tier_code='bronze',
            points_balance=bonus_points,
            # ... other fields
        )

        # 5. Publish event
        if self.event_bus:
            await publish_membership_enrolled(
                self.event_bus,
                membership_id=membership.membership_id,
                user_id=membership.user_id,
                tier_code=membership.tier_code,
                enrollment_bonus=bonus_points
            )

        return (to_response(membership), True)

    async def earn_points(
        self,
        request: EarnPointsRequest
    ) -> EarnPointsResponse:
        """Award points to membership with tier multiplier"""
        # 1. Get active membership
        membership = await self.repository.get_membership_by_user(request.user_id)
        if not membership or membership.status != 'active':
            raise MembershipNotFoundError("No active membership found")

        # 2. Get tier multiplier
        tier = self._tier_cache.get(membership.tier_code)
        multiplier = tier.point_multiplier if tier else 1.0

        # 3. Calculate final points
        final_points = int(request.points_amount * multiplier)

        # 4. Add points atomically
        updated = await self.repository.add_points(
            membership_id=membership.membership_id,
            points=final_points,
            tier_points=request.points_amount,  # Base points for tier
            source=request.source,
            reference_id=request.reference_id
        )

        # 5. Check tier upgrade
        await self._check_tier_upgrade(updated)

        # 6. Publish event
        if self.event_bus:
            await publish_points_earned(
                self.event_bus,
                membership_id=membership.membership_id,
                user_id=request.user_id,
                points_earned=final_points,
                multiplier=multiplier,
                balance_after=updated.points_balance
            )

        return EarnPointsResponse(
            success=True,
            points_earned=final_points,
            multiplier=multiplier,
            points_balance=updated.points_balance,
            tier_points=updated.tier_points
        )

    async def redeem_points(
        self,
        request: RedeemPointsRequest
    ) -> RedeemPointsResponse:
        """Redeem points for reward"""
        # 1. Get active membership
        membership = await self.repository.get_membership_by_user(request.user_id)
        if not membership:
            raise MembershipNotFoundError("No active membership found")

        # 2. Validate sufficient points
        if membership.points_balance < request.points_amount:
            raise InsufficientPointsError(
                f"Insufficient points. Available: {membership.points_balance}, Requested: {request.points_amount}"
            )

        # 3. Deduct points atomically
        updated = await self.repository.deduct_points(
            membership_id=membership.membership_id,
            points=request.points_amount,
            reward_code=request.reward_code,
            description=request.description
        )

        # 4. Publish event
        if self.event_bus:
            await publish_points_redeemed(
                self.event_bus,
                membership_id=membership.membership_id,
                user_id=request.user_id,
                points_redeemed=request.points_amount,
                reward_code=request.reward_code,
                balance_after=updated.points_balance
            )

        return RedeemPointsResponse(
            success=True,
            points_redeemed=request.points_amount,
            points_balance=updated.points_balance
        )

    async def _check_tier_upgrade(self, membership: Membership) -> Optional[str]:
        """Check if membership qualifies for tier upgrade"""
        current_tier = membership.tier_code
        tier_points = membership.tier_points

        # Find highest qualified tier
        qualified_tier = current_tier
        for tier_code, tier in self._tier_cache.items():
            if tier_points >= tier.qualification_threshold:
                if self._tier_rank(tier_code) > self._tier_rank(qualified_tier):
                    qualified_tier = tier_code

        if qualified_tier != current_tier:
            await self.repository.update_tier(
                membership_id=membership.membership_id,
                new_tier=qualified_tier
            )
            if self.event_bus:
                await publish_membership_tier_upgraded(
                    self.event_bus,
                    membership_id=membership.membership_id,
                    previous_tier=current_tier,
                    new_tier=qualified_tier
                )
            return qualified_tier
        return None
```

**Custom Exceptions**:
```python
class MembershipServiceError(Exception):
    """Base exception for membership service"""
    pass

class MembershipNotFoundError(MembershipServiceError):
    """Membership not found"""
    pass

class DuplicateMembershipError(MembershipServiceError):
    """User already has membership"""
    pass

class InsufficientPointsError(MembershipServiceError):
    """Not enough points for redemption"""
    pass

class BenefitNotAvailableError(MembershipServiceError):
    """Benefit not available at tier"""
    pass
```

### 3. Repository Layer (membership_repository.py)

**Class**: `MembershipRepository`

**Responsibilities**:
- PostgreSQL CRUD operations
- gRPC communication with postgres_grpc_service
- Atomic point transactions
- Query construction (parameterized)
- Result parsing

**Key Methods**:
```python
class MembershipRepository:
    def __init__(self, config: Optional[ConfigManager] = None):
        host, port = config.discover_service(
            service_name='postgres_grpc_service',
            default_host='isa-postgres-grpc',
            default_port=50061
        )
        self.db = AsyncPostgresClient(host=host, port=port, user_id='membership_service')
        self.schema = "membership"

    async def create_membership(
        self,
        user_id: str,
        tier_code: str,
        points_balance: int = 0,
        **kwargs
    ) -> Membership:
        """Create new membership"""
        membership_id = f"mem_{uuid.uuid4().hex[:16]}"
        async with self.db:
            await self.db.execute(
                f"""INSERT INTO {self.schema}.memberships
                    (membership_id, user_id, tier_code, status,
                     points_balance, tier_points, lifetime_points,
                     enrolled_at, expiration_date)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)""",
                params=[
                    membership_id, user_id, tier_code, 'active',
                    points_balance, 0, points_balance,
                    datetime.utcnow(), datetime.utcnow() + timedelta(days=365)
                ]
            )
        return await self.get_membership(membership_id)

    async def add_points(
        self,
        membership_id: str,
        points: int,
        tier_points: int,
        source: str,
        reference_id: Optional[str] = None
    ) -> Membership:
        """Atomically add points and record history"""
        async with self.db:
            # Update membership points
            await self.db.execute(
                f"""UPDATE {self.schema}.memberships
                    SET points_balance = points_balance + $2,
                        tier_points = tier_points + $3,
                        lifetime_points = lifetime_points + $2,
                        updated_at = NOW()
                    WHERE membership_id = $1""",
                params=[membership_id, points, tier_points]
            )

            # Record history
            await self.db.execute(
                f"""INSERT INTO {self.schema}.membership_history
                    (history_id, membership_id, action, points_change,
                     source, reference_id, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, NOW())""",
                params=[
                    f"hist_{uuid.uuid4().hex[:16]}",
                    membership_id, 'points_earned', points,
                    source, reference_id
                ]
            )
        return await self.get_membership(membership_id)

    async def deduct_points(
        self,
        membership_id: str,
        points: int,
        reward_code: str,
        description: Optional[str] = None
    ) -> Membership:
        """Atomically deduct points and record history"""
        async with self.db:
            # Verify sufficient balance
            result = await self.db.query_row(
                f"SELECT points_balance FROM {self.schema}.memberships WHERE membership_id = $1",
                params=[membership_id]
            )
            if not result or result['points_balance'] < points:
                raise InsufficientPointsError("Insufficient points")

            # Update membership points
            await self.db.execute(
                f"""UPDATE {self.schema}.memberships
                    SET points_balance = points_balance - $2,
                        updated_at = NOW()
                    WHERE membership_id = $1""",
                params=[membership_id, points]
            )

            # Record history
            await self.db.execute(
                f"""INSERT INTO {self.schema}.membership_history
                    (history_id, membership_id, action, points_change,
                     reward_code, description, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, NOW())""",
                params=[
                    f"hist_{uuid.uuid4().hex[:16]}",
                    membership_id, 'points_redeemed', -points,
                    reward_code, description
                ]
            )
        return await self.get_membership(membership_id)
```

---

## Database Schema Design

### PostgreSQL Schema: `membership`

#### Table: membership.memberships

```sql
CREATE SCHEMA IF NOT EXISTS membership;

CREATE TABLE IF NOT EXISTS membership.memberships (
    -- Primary Key
    id SERIAL PRIMARY KEY,
    membership_id VARCHAR(50) UNIQUE NOT NULL,

    -- Owner Information
    user_id VARCHAR(50) NOT NULL,
    organization_id VARCHAR(50),

    -- Tier Information
    tier_code VARCHAR(20) NOT NULL DEFAULT 'bronze',

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'active',

    -- Points
    points_balance BIGINT NOT NULL DEFAULT 0,
    tier_points BIGINT NOT NULL DEFAULT 0,
    lifetime_points BIGINT NOT NULL DEFAULT 0,
    pending_points BIGINT NOT NULL DEFAULT 0,

    -- Dates
    enrolled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expiration_date TIMESTAMPTZ,
    last_activity_at TIMESTAMPTZ,

    -- Auto-renewal
    auto_renew BOOLEAN NOT NULL DEFAULT TRUE,

    -- Metadata
    enrollment_source VARCHAR(50),
    promo_code VARCHAR(50),
    metadata JSONB NOT NULL DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_memberships_user_id ON membership.memberships(user_id);
CREATE INDEX idx_memberships_org_id ON membership.memberships(organization_id);
CREATE INDEX idx_memberships_status ON membership.memberships(status);
CREATE INDEX idx_memberships_tier ON membership.memberships(tier_code);
CREATE INDEX idx_memberships_expiration ON membership.memberships(expiration_date);
CREATE UNIQUE INDEX idx_memberships_user_active
    ON membership.memberships(user_id)
    WHERE status IN ('active', 'pending');
```

#### Table: membership.membership_history

```sql
CREATE TABLE IF NOT EXISTS membership.membership_history (
    -- Primary Key
    id SERIAL PRIMARY KEY,
    history_id VARCHAR(50) UNIQUE NOT NULL,

    -- References
    membership_id VARCHAR(50) NOT NULL REFERENCES membership.memberships(membership_id),

    -- Action
    action VARCHAR(30) NOT NULL,

    -- Point Changes
    points_change BIGINT NOT NULL DEFAULT 0,
    balance_after BIGINT,

    -- Tier Changes
    previous_tier VARCHAR(20),
    new_tier VARCHAR(20),

    -- Context
    source VARCHAR(50),
    reference_id VARCHAR(100),
    reward_code VARCHAR(50),
    benefit_code VARCHAR(50),
    description TEXT,

    -- Initiator
    initiated_by VARCHAR(20) NOT NULL DEFAULT 'system',

    -- Metadata
    metadata JSONB NOT NULL DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_history_membership ON membership.membership_history(membership_id);
CREATE INDEX idx_history_action ON membership.membership_history(action);
CREATE INDEX idx_history_created ON membership.membership_history(created_at DESC);
```

#### Table: membership.tiers (Reference Data)

```sql
CREATE TABLE IF NOT EXISTS membership.tiers (
    id SERIAL PRIMARY KEY,
    tier_code VARCHAR(20) UNIQUE NOT NULL,
    tier_name VARCHAR(50) NOT NULL,
    display_order INTEGER NOT NULL DEFAULT 0,

    -- Qualification
    qualification_threshold BIGINT NOT NULL DEFAULT 0,
    annual_spend_threshold DECIMAL(12, 2) NOT NULL DEFAULT 0,

    -- Multiplier
    point_multiplier DECIMAL(4, 2) NOT NULL DEFAULT 1.0,

    -- Status
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed data
INSERT INTO membership.tiers (tier_code, tier_name, display_order, qualification_threshold, annual_spend_threshold, point_multiplier) VALUES
('bronze', 'Bronze', 1, 0, 0, 1.0),
('silver', 'Silver', 2, 5000, 500, 1.25),
('gold', 'Gold', 3, 20000, 2000, 1.5),
('platinum', 'Platinum', 4, 50000, 5000, 2.0),
('diamond', 'Diamond', 5, 100000, 10000, 3.0);
```

#### Table: membership.tier_benefits

```sql
CREATE TABLE IF NOT EXISTS membership.tier_benefits (
    id SERIAL PRIMARY KEY,
    benefit_id VARCHAR(50) UNIQUE NOT NULL,
    tier_code VARCHAR(20) NOT NULL,
    benefit_code VARCHAR(50) NOT NULL,
    benefit_name VARCHAR(100) NOT NULL,
    benefit_type VARCHAR(30) NOT NULL,

    -- Limits
    usage_limit INTEGER,
    reset_period VARCHAR(20),

    -- Value
    benefit_value JSONB NOT NULL DEFAULT '{}',

    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_benefits_tier ON membership.tier_benefits(tier_code);
```

---

## Event-Driven Architecture

### Event Publishing (events/publishers.py)

**NATS Subjects**:
```
membership.enrolled              # New membership created
membership.tier_upgraded        # Member advanced tier
membership.tier_downgraded      # Member lost tier
membership.suspended            # Membership suspended
membership.reactivated          # Membership reactivated
membership.expired              # Membership expired
membership.canceled             # Membership canceled
points.earned                   # Points added
points.redeemed                 # Points redeemed
points.expired                  # Points expired
benefit.used                    # Benefit redeemed
```

### Event Models (events/models.py)

```python
class MembershipEnrolledEventData(BaseModel):
    """Event: membership.enrolled"""
    membership_id: str
    user_id: str
    tier_code: str
    enrollment_bonus: int
    enrolled_at: datetime

class PointsEarnedEventData(BaseModel):
    """Event: points.earned"""
    membership_id: str
    user_id: str
    points_earned: int
    multiplier: float
    source: str
    balance_after: int
    earned_at: datetime

class PointsRedeemedEventData(BaseModel):
    """Event: points.redeemed"""
    membership_id: str
    user_id: str
    points_redeemed: int
    reward_code: str
    balance_after: int
    redeemed_at: datetime

class TierUpgradedEventData(BaseModel):
    """Event: membership.tier_upgraded"""
    membership_id: str
    user_id: str
    previous_tier: str
    new_tier: str
    tier_points: int
    upgraded_at: datetime
```

### Event Flow Diagram

```
┌─────────────┐
│Order Service│ (order completed)
└──────┬──────┘
       │ Event: order.completed
       │ {user_id, order_total}
       ↓
┌──────────────────┐
│  Membership      │
│  Service         │
│                  │
│  1. Get membership
│  2. Calculate pts │───→ PostgreSQL
│  3. Apply multiplier
│  4. Add points    │
│  5. Check tier    │
│  6. Publish       │
└──────────────────┘
       │
       │ Event: points.earned
       ↓
┌─────────────────┐
│   NATS Bus      │
└────────┬────────┘
         │
         ├──→ Analytics Service (track engagement)
         └──→ Notification Service (milestone alerts)
```

---

## Data Flow Diagrams

### 1. Point Earning Flow

```
Platform Service calls POST /api/v1/memberships/points/earn
    │
    ↓
┌─────────────────────────────────┐
│  MembershipService.earn_points  │
│                                 │
│  Step 1: Get membership         │
│    repository.get_by_user()────→ PostgreSQL
│                            ←────┤
│    If not found → Error         │
│                                 │
│  Step 2: Get tier multiplier    │
│    tier_cache[tier_code]        │
│    multiplier = 1.25x           │
│                                 │
│  Step 3: Calculate final points │
│    final = base * multiplier    │
│                                 │
│  Step 4: Add points atomically  │
│    repository.add_points() ─────┼──→ PostgreSQL (Transaction)
│                            ←────┤       UPDATE memberships
│                                 │       INSERT history
│                                 │
│  Step 5: Check tier upgrade     │
│    _check_tier_upgrade()        │
│    If qualified → upgrade tier  │
│                                 │
│  Step 6: Publish event          │
│    publish_points_earned() ─────┼──→ NATS
│                                 │
└─────────────────────────────────┘
    │
    │ Return EarnPointsResponse
    ↓
Platform Service receives response
```

### 2. Point Redemption Flow

```
User calls POST /api/v1/memberships/points/redeem
    │
    ↓
┌──────────────────────────────────────┐
│  MembershipService.redeem_points     │
│                                       │
│  Step 1: Get membership              │
│    repository.get_by_user() ────────→ PostgreSQL
│                                 ←────┤
│    If not found → Error              │
│                                       │
│  Step 2: Validate balance            │
│    if balance < requested → 402 Error│
│                                       │
│  Step 3: Deduct points atomically    │
│    repository.deduct_points() ───────┼──→ PostgreSQL (Transaction)
│                                 ←────┤       UPDATE memberships
│                                       │       INSERT history
│                                       │
│  Step 4: Publish event               │
│    publish_points_redeemed() ────────┼──→ NATS
│                                       │
└───────────────────────────────────────┘
    │
    │ Return RedeemPointsResponse
    ↓
User receives confirmation
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
- **Schema**: `membership`

### Event-Driven
- **NATS 2.9+**: Event bus
- **Subjects**: `membership.*`, `points.*`, `benefit.*`
- **Publishers**: Membership Service

### Service Discovery
- **Consul 1.15+**: Service registry
- **Health Checks**: HTTP `/health`

---

## Security Considerations

### Input Validation
- **Pydantic Models**: All requests validated
- **Point Validation**: Prevent negative/overflow attacks
- **SQL Injection**: Parameterized queries via gRPC

### Access Control
- **Membership Isolation**: Queries filtered by user_id
- **JWT Authentication**: Handled by API Gateway
- **Point Limits**: Maximum points per transaction

### Data Privacy
- **Soft Delete**: Membership data preserved for audit
- **GDPR Compliance**: Right to deletion supported
- **History Retention**: Configurable retention periods

---

## Error Handling

### HTTP Status Codes
- `200 OK`: Successful operation
- `201 Created`: New membership enrolled
- `400 Bad Request`: Validation error
- `402 Payment Required`: Insufficient points
- `404 Not Found`: Membership not found
- `409 Conflict`: Duplicate membership
- `500 Internal Server Error`: Server error

### Error Response Format
```json
{
  "success": false,
  "error": "Insufficient points. Available: 500, Requested: 1000",
  "error_code": "INSUFFICIENT_POINTS",
  "details": {
    "available": 500,
    "requested": 1000
  }
}
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

### API Testing
- **Endpoint Contracts**: All 17 endpoints tested
- **Error Handling**: Validation, not found, server errors

### Smoke Testing
- **E2E Scripts**: Bash scripts for critical paths
- **Health Checks**: Service startup validation

---

**Document Version**: 1.0
**Last Updated**: 2025-12-19
**Maintained By**: Membership Service Engineering Team
**Related Documents**:
- Domain Context: docs/domain/membership_service.md
- PRD: docs/prd/membership_service.md
- Data Contract: tests/contracts/membership/data_contract.py
- Logic Contract: tests/contracts/membership/logic_contract.md
