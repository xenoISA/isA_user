# Subscription Service - Design Document

## Architecture Overview

### Service Architecture
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Subscription Service (Port 8217)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  FastAPI Application (main.py)                                               │
│  ├─ Health Endpoints (/health, /health/detailed)                             │
│  ├─ Subscription Endpoints (CRUD, cancel)                                    │
│  ├─ Credit Endpoints (balance, consume)                                      │
│  ├─ History Endpoint                                                         │
│  └─ Dependency Injection Setup                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  Service Layer (subscription_service.py)                                     │
│  ├─ SubscriptionService                                                      │
│  │   ├─ create_subscription()                                                │
│  │   ├─ get_subscription()                                                   │
│  │   ├─ get_user_subscription()                                              │
│  │   ├─ get_subscriptions()                                                  │
│  │   ├─ cancel_subscription()                                                │
│  │   ├─ consume_credits()                                                    │
│  │   ├─ get_credit_balance()                                                 │
│  │   └─ get_subscription_history()                                           │
│  └─ Tier Cache (in-memory)                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  Repository Layer (subscription_repository.py)                               │
│  ├─ SubscriptionRepository                                                   │
│  │   ├─ create_subscription()                                                │
│  │   ├─ get_subscription()                                                   │
│  │   ├─ get_user_subscription()                                              │
│  │   ├─ update_subscription()                                                │
│  │   ├─ consume_credits()                                                    │
│  │   ├─ add_history()                                                        │
│  │   └─ get_subscription_history()                                           │
│  └─ PostgreSQL via gRPC                                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  Dependency Injection (protocols.py)                                         │
│  ├─ SubscriptionRepositoryProtocol                                           │
│  ├─ EventBusProtocol                                                         │
│  └─ Custom Exceptions                                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  Factory (factory.py)                                                        │
│  └─ create_subscription_service()                                            │
└─────────────────────────────────────────────────────────────────────────────┘

External Dependencies:
- PostgreSQL (via gRPC client)     - Data persistence
- NATS                              - Event publishing
- Consul                            - Service discovery
- Product Service                   - Tier definitions (future)
- Payment Service                   - Payment processing (future)
```

### Component Diagram
```
                    ┌─────────────────┐
                    │   API Gateway   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Subscription   │
                    │    Service      │
                    └────────┬────────┘
           ┌─────────────────┼─────────────────┐
           │                 │                 │
    ┌──────▼──────┐  ┌───────▼───────┐  ┌──────▼──────┐
    │  PostgreSQL │  │     NATS      │  │   Consul    │
    │   (gRPC)    │  │ (Event Bus)   │  │  (Service   │
    │             │  │               │  │  Discovery) │
    └─────────────┘  └───────────────┘  └─────────────┘
```

---

## Component Design

### Service Layer (subscription_service.py)

The SubscriptionService handles all business logic:

```python
class SubscriptionService:
    """
    Subscription management service.
    Uses dependency injection for testability.
    """

    def __init__(
        self,
        repository: Optional[SubscriptionRepositoryProtocol] = None,
        event_bus=None,
    ):
        self.repository = repository
        self.event_bus = event_bus
        self._tier_cache: Dict[str, Dict[str, Any]] = {}

    async def initialize(self):
        """Initialize service and load tier cache"""
        await self.repository.initialize()
        await self._load_tier_cache()

    async def create_subscription(self, request: CreateSubscriptionRequest) -> CreateSubscriptionResponse:
        """Create new subscription with validation and event publishing"""
        ...

    async def consume_credits(self, request: ConsumeCreditsRequest) -> ConsumeCreditsResponse:
        """Consume credits from subscription with validation"""
        ...
```

### Repository Layer (subscription_repository.py)

The repository handles data access via gRPC:

```python
class SubscriptionRepository:
    """Data access layer for subscriptions"""

    def __init__(self, config: Optional[ConfigManager] = None):
        self.config = config
        self.grpc_client = None

    async def initialize(self):
        """Initialize gRPC client"""
        self.grpc_client = await create_grpc_client()

    async def create_subscription(self, subscription: UserSubscription) -> Optional[UserSubscription]:
        """Insert subscription into database"""
        ...

    async def consume_credits(self, subscription_id: str, credits_to_consume: int) -> Optional[UserSubscription]:
        """Atomically decrement credits"""
        ...
```

### Protocols (protocols.py)

Defines interfaces for dependency injection:

```python
@runtime_checkable
class SubscriptionRepositoryProtocol(Protocol):
    """Interface for Subscription Repository"""

    async def initialize(self) -> None: ...
    async def create_subscription(self, subscription: UserSubscription) -> Optional[UserSubscription]: ...
    async def get_subscription(self, subscription_id: str) -> Optional[UserSubscription]: ...
    async def get_user_subscription(self, user_id: str, organization_id: Optional[str], active_only: bool) -> Optional[UserSubscription]: ...
    async def update_subscription(self, subscription_id: str, update_data: Dict[str, Any]) -> Optional[UserSubscription]: ...
    async def consume_credits(self, subscription_id: str, credits: int) -> bool: ...
    async def add_history(self, history: SubscriptionHistory) -> Optional[SubscriptionHistory]: ...

# Custom exceptions
class SubscriptionNotFoundError(Exception): ...
class SubscriptionValidationError(Exception): ...
class InsufficientCreditsError(Exception): ...
class TierNotFoundError(Exception): ...
```

### Factory (factory.py)

Creates service instances with real dependencies:

```python
def create_subscription_service(
    config: Optional[ConfigManager] = None,
    event_bus=None,
) -> SubscriptionService:
    """Create SubscriptionService with real dependencies"""
    from .subscription_repository import SubscriptionRepository

    repository = SubscriptionRepository(config=config)
    return SubscriptionService(repository=repository, event_bus=event_bus)
```

---

## Database Schemas

### Table: subscription.user_subscriptions
```sql
CREATE TABLE IF NOT EXISTS subscription.user_subscriptions (
    id SERIAL PRIMARY KEY,
    subscription_id VARCHAR(50) UNIQUE NOT NULL,

    -- Owner Information
    user_id VARCHAR(50) NOT NULL,
    organization_id VARCHAR(50),

    -- Subscription Plan
    tier_id VARCHAR(50) NOT NULL,
    tier_code VARCHAR(20) NOT NULL,

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'active',

    -- Billing
    billing_cycle VARCHAR(20) NOT NULL DEFAULT 'monthly',
    price_paid DECIMAL(12, 2) NOT NULL DEFAULT 0,
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',

    -- Credits
    credits_allocated BIGINT NOT NULL DEFAULT 0,
    credits_used BIGINT NOT NULL DEFAULT 0,
    credits_remaining BIGINT NOT NULL DEFAULT 0,
    credits_rolled_over BIGINT NOT NULL DEFAULT 0,

    -- Period
    current_period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    current_period_end TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Trial
    trial_start TIMESTAMP WITH TIME ZONE,
    trial_end TIMESTAMP WITH TIME ZONE,
    is_trial BOOLEAN NOT NULL DEFAULT FALSE,

    -- Seats
    seats_purchased INTEGER NOT NULL DEFAULT 1,
    seats_used INTEGER NOT NULL DEFAULT 1,

    -- Cancellation
    cancel_at_period_end BOOLEAN NOT NULL DEFAULT FALSE,
    canceled_at TIMESTAMP WITH TIME ZONE,
    cancellation_reason TEXT,

    -- Payment
    payment_method_id VARCHAR(50),
    external_subscription_id VARCHAR(100),

    -- Renewal
    auto_renew BOOLEAN NOT NULL DEFAULT TRUE,
    next_billing_date TIMESTAMP WITH TIME ZONE,
    last_billing_date TIMESTAMP WITH TIME ZONE,

    -- Metadata
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_subscriptions_user_id ON subscription.user_subscriptions(user_id);
CREATE INDEX idx_subscriptions_org_id ON subscription.user_subscriptions(organization_id);
CREATE INDEX idx_subscriptions_status ON subscription.user_subscriptions(status);
CREATE INDEX idx_subscriptions_tier ON subscription.user_subscriptions(tier_code);
CREATE INDEX idx_subscriptions_user_org ON subscription.user_subscriptions(user_id, organization_id);
CREATE INDEX idx_subscriptions_active ON subscription.user_subscriptions(user_id, status) WHERE status IN ('active', 'trialing');
```

### Table: subscription.subscription_history
```sql
CREATE TABLE IF NOT EXISTS subscription.subscription_history (
    id SERIAL PRIMARY KEY,
    history_id VARCHAR(50) UNIQUE NOT NULL,

    -- References
    subscription_id VARCHAR(50) NOT NULL REFERENCES subscription.user_subscriptions(subscription_id),
    user_id VARCHAR(50) NOT NULL,
    organization_id VARCHAR(50),

    -- Action
    action VARCHAR(30) NOT NULL,

    -- State Changes
    previous_tier_code VARCHAR(20),
    new_tier_code VARCHAR(20),
    previous_status VARCHAR(20),
    new_status VARCHAR(20),

    -- Credit Changes
    credits_change BIGINT NOT NULL DEFAULT 0,
    credits_balance_after BIGINT,

    -- Price
    price_change DECIMAL(12, 2) NOT NULL DEFAULT 0,

    -- Period
    period_start TIMESTAMP WITH TIME ZONE,
    period_end TIMESTAMP WITH TIME ZONE,

    -- Details
    reason TEXT,
    initiated_by VARCHAR(20) NOT NULL DEFAULT 'system',
    metadata JSONB NOT NULL DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_history_subscription ON subscription.subscription_history(subscription_id);
CREATE INDEX idx_history_user ON subscription.subscription_history(user_id);
CREATE INDEX idx_history_action ON subscription.subscription_history(action);
CREATE INDEX idx_history_created ON subscription.subscription_history(created_at DESC);
```

### Table: subscription.tiers (Reference Data)
```sql
CREATE TABLE IF NOT EXISTS subscription.tiers (
    id SERIAL PRIMARY KEY,
    tier_id VARCHAR(50) UNIQUE NOT NULL,
    tier_code VARCHAR(20) UNIQUE NOT NULL,
    tier_name VARCHAR(50) NOT NULL,

    -- Pricing
    monthly_price_usd DECIMAL(10, 2) NOT NULL DEFAULT 0,

    -- Credits
    monthly_credits BIGINT NOT NULL DEFAULT 0,
    credit_rollover BOOLEAN NOT NULL DEFAULT FALSE,
    max_rollover_credits BIGINT DEFAULT 0,

    -- Trial
    trial_days INTEGER NOT NULL DEFAULT 0,

    -- Features
    features JSONB NOT NULL DEFAULT '{}',

    -- Status
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    display_order INTEGER NOT NULL DEFAULT 0,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Seed data
INSERT INTO subscription.tiers (tier_id, tier_code, tier_name, monthly_price_usd, monthly_credits, credit_rollover, max_rollover_credits, trial_days, display_order) VALUES
('tier_free_001', 'free', 'Free', 0, 1000000, FALSE, 0, 0, 1),
('tier_pro_001', 'pro', 'Pro', 20.00, 30000000, TRUE, 15000000, 14, 2),
('tier_max_001', 'max', 'Max', 50.00, 100000000, TRUE, 50000000, 14, 3),
('tier_team_001', 'team', 'Team', 25.00, 50000000, TRUE, 25000000, 14, 4),
('tier_enterprise_001', 'enterprise', 'Enterprise', 0, 0, TRUE, NULL, 30, 5);
```

---

## Data Flow Diagrams

### Create Subscription Flow
```
Client -> POST /api/v1/subscriptions
  -> RouteHandler (main.py)
    -> get_subscription_service() [DI]
    -> SubscriptionService.create_subscription(request)
      -> _get_tier_info(tier_code)       # Validate tier
        <- Tier info from cache
      -> repository.get_user_subscription()  # Check existing
        -> PostgreSQL (gRPC)
        <- None or existing subscription
      -> Calculate credits, trial, price
      -> repository.create_subscription()
        -> PostgreSQL (gRPC)
        <- Created subscription
      -> repository.add_history()        # Audit trail
        -> PostgreSQL (gRPC)
      -> event_bus.publish_event()       # Notify
        -> NATS
    <- CreateSubscriptionResponse
  <- HTTP 200 {success: true, subscription: {...}}
```

### Consume Credits Flow
```
Service -> POST /api/v1/subscriptions/credits/consume
  -> RouteHandler (main.py)
    -> get_subscription_service() [DI]
    -> SubscriptionService.consume_credits(request)
      -> repository.get_user_subscription()  # Get active sub
        -> PostgreSQL (gRPC)
        <- UserSubscription
      -> Validate credits_remaining >= credits_to_consume
      -> repository.consume_credits()    # Atomic decrement
        -> PostgreSQL (gRPC UPDATE)
        <- Updated subscription
      -> repository.add_history()        # Audit trail
        -> PostgreSQL (gRPC)
      -> event_bus.publish_event()       # Notify
        -> NATS
    <- ConsumeCreditsResponse
  <- HTTP 200 {success: true, credits_consumed: X, credits_remaining: Y}
```

### Cancel Subscription Flow
```
Client -> POST /api/v1/subscriptions/{id}/cancel?user_id=X
  -> RouteHandler (main.py)
    -> get_subscription_service() [DI]
    -> SubscriptionService.cancel_subscription(id, request, user_id)
      -> repository.get_subscription()   # Fetch subscription
        -> PostgreSQL (gRPC)
        <- UserSubscription
      -> Validate ownership (subscription.user_id == user_id)
      -> Determine immediate vs end-of-period
      -> repository.update_subscription()  # Update status
        -> PostgreSQL (gRPC)
        <- Updated subscription
      -> repository.add_history()        # Audit trail
        -> PostgreSQL (gRPC)
      -> event_bus.publish_event()       # Notify
        -> NATS
    <- CancelSubscriptionResponse
  <- HTTP 200 {success: true, effective_date: ...}
```

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Language | Python 3.9+ | Service implementation |
| Framework | FastAPI | HTTP API |
| Validation | Pydantic | Request/response models |
| Database | PostgreSQL | Data persistence |
| Database Client | gRPC | Async database access |
| Event Bus | NATS | Event publishing |
| Service Discovery | Consul | Registration and health |
| Configuration | ConfigManager | Environment config |
| Logging | Python logging | Structured logging |

---

## Security Considerations

### Authentication
- All endpoints require JWT authentication (via Gateway)
- user_id extracted from JWT claims
- Internal service calls use service tokens

### Authorization
- Users can only access their own subscriptions
- Organization admins can manage org subscriptions
- Cancellation requires ownership validation

### Data Protection
- Credit operations use atomic transactions
- No sensitive payment data stored (payment_method_id only)
- History records are immutable

### Input Validation
- All inputs validated via Pydantic models
- tier_code validated against known tiers
- credits_to_consume must be positive integer

### Rate Limiting
- Applied at API Gateway level
- Credit consumption: 1000 req/min per user
- Subscription creation: 10 req/min per user

---

## Event-Driven Architecture

### Published Events

| Event Type | Trigger | Data |
|------------|---------|------|
| subscription.created | New subscription | subscription_id, user_id, tier_code, credits_allocated, is_trial |
| subscription.canceled | Cancellation | subscription_id, user_id, immediate, effective_date |
| credits.consumed | Credit consumption | subscription_id, user_id, credits_consumed, credits_remaining, service_type |
| subscription.renewed | Period renewal | subscription_id, user_id, new_period_start, credits_allocated |
| subscription.upgraded | Tier upgrade | subscription_id, previous_tier, new_tier |
| credits.low_balance | Balance < 10% | subscription_id, user_id, credits_remaining |

### Event Publishing Pattern
```python
async def _publish_event(self, event_type: EventType, data: Dict[str, Any], subject: Optional[str] = None):
    """Publish event using NATS event bus"""
    if self.event_bus:
        event = Event(
            event_type=event_type,
            source=ServiceSource.SUBSCRIPTION_SERVICE,
            data=data,
            subject=subject
        )
        await self.event_bus.publish_event(event)
```

### Consumed Events
- payment.succeeded - Update subscription after payment
- payment.failed - Handle failed payment
- account.deleted - Clean up subscriptions

---

## Error Handling

### Exception Hierarchy
```
SubscriptionServiceError (base)
├── SubscriptionNotFoundError -> HTTP 404
├── SubscriptionValidationError -> HTTP 400/403
├── InsufficientCreditsError -> HTTP 402
└── TierNotFoundError -> HTTP 404
```

### Error Response Format
```json
{
  "success": false,
  "error": "Subscription not found",
  "error_code": "SUBSCRIPTION_NOT_FOUND",
  "details": {
    "subscription_id": "sub_xyz"
  }
}
```

### HTTP Status Codes
| Code | Meaning | When Used |
|------|---------|-----------|
| 200 | Success | All successful operations |
| 400 | Bad Request | Invalid request parameters |
| 402 | Payment Required | Insufficient credits |
| 403 | Forbidden | Not authorized for action |
| 404 | Not Found | Subscription/tier not found |
| 422 | Validation Error | Pydantic validation failure |
| 500 | Server Error | Internal errors |

---

## Performance Considerations

### Tier Caching
- Tier definitions cached in memory
- Cache loaded at service startup
- No database query for tier validation

### Database Optimization
- Indexes on frequently queried columns
- Partial index for active subscriptions
- Atomic credit updates (no race conditions)

### Connection Pooling
- gRPC client uses connection pooling
- Pool size configured via environment

### Query Optimization
```sql
-- Efficient active subscription lookup
SELECT * FROM subscription.user_subscriptions
WHERE user_id = $1
  AND (organization_id = $2 OR (organization_id IS NULL AND $2 IS NULL))
  AND status IN ('active', 'trialing')
LIMIT 1;
```

---

## Deployment Configuration

### Environment Variables
| Variable | Description | Default |
|----------|-------------|---------|
| SERVICE_NAME | Service identifier | subscription_service |
| SERVICE_PORT | HTTP port | 8217 |
| SERVICE_HOST | Bind address | 0.0.0.0 |
| POSTGRES_HOST | Database host | localhost |
| POSTGRES_PORT | Database port | 5432 |
| NATS_URL | NATS server | nats://localhost:4222 |
| CONSUL_HOST | Consul host | localhost |
| CONSUL_PORT | Consul port | 8500 |
| LOG_LEVEL | Logging level | INFO |

### Health Check Configuration
```json
{
  "check": {
    "http": "http://localhost:8217/health",
    "interval": "10s",
    "timeout": "5s"
  }
}
```

### Kubernetes Resources
```yaml
resources:
  requests:
    cpu: "100m"
    memory: "256Mi"
  limits:
    cpu: "500m"
    memory: "512Mi"
```

---

## Testing Strategy

### Unit Tests (tests/unit/golden/subscription_service/)
- Model validation tests
- Business rule tests
- Factory method tests

### Component Tests (tests/component/golden/subscription_service/)
- Service layer with mocked repository
- Credit consumption logic
- Subscription lifecycle

### Integration Tests (tests/integration/golden/subscription_service/)
- Real database operations
- Event publishing verification

### API Tests (tests/api/golden/subscription_service/)
- HTTP endpoint testing
- Response contract validation

### Smoke Tests (tests/smoke/)
- End-to-end bash scripts
- Production validation

---

**Document Statistics**:
- Lines: ~900
- Architecture diagrams: 3
- Database tables: 3
- Data flows: 3
- Events: 6
