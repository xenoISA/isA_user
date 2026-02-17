# Billing Service - Design Document

## Architecture Overview

### Service Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    Billing Service                          │
├────────────────────────────────────────────────────────────┤
│  FastAPI Application (main.py)                             │
│  ├─ Route Handlers (usage, calculate, process, quota)      │
│  ├─ Dependency Injection Setup                             │
│  └─ Lifespan Management (startup/shutdown)                 │
├────────────────────────────────────────────────────────────┤
│  Service Layer (billing_service.py)                        │
│  ├─ Usage Recording                                        │
│  ├─ Cost Calculation (free tier, subscription)             │
│  ├─ Billing Processing (credit/wallet/payment)             │
│  ├─ Quota Management                                       │
│  └─ Event Publishing                                       │
├────────────────────────────────────────────────────────────┤
│  Repository Layer (billing_repository.py)                  │
│  ├─ BillingRecordRepository                                │
│  ├─ BillingEventRepository                                 │
│  └─ BillingQuotaRepository                                 │
├────────────────────────────────────────────────────────────┤
│  Dependency Injection (protocols.py)                       │
│  ├─ BillingRepositoryProtocol                              │
│  ├─ EventBusProtocol                                       │
│  ├─ ProductClientProtocol                                  │
│  ├─ WalletClientProtocol                                   │
│  └─ SubscriptionClientProtocol                             │
├────────────────────────────────────────────────────────────┤
│  Factory (factory.py)                                      │
│  └─ create_billing_service() - production instantiation    │
└────────────────────────────────────────────────────────────┘

External Dependencies:
- PostgreSQL via gRPC (data persistence)
- NATS (event publishing/subscribing)
- Wallet Service (balance checks, deductions)
- Subscription Service (subscription status)
- Product Service (pricing information)
- Consul (service discovery)
```

### Component Diagram

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Session   │    │  Storage    │    │   Order     │
│   Service   │───>│  Service    │───>│  Service    │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                   │
       │   (NATS Events)  │                   │
       └──────────────────┼───────────────────┘
                          ▼
                   ┌─────────────┐
                   │   Billing   │
                   │   Service   │
                   └──────┬──────┘
                          │
       ┌──────────────────┼──────────────────┐
       │                  │                  │
       ▼                  ▼                  ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Wallet    │    │Subscription │    │  Product    │
│   Service   │    │   Service   │    │  Service    │
└─────────────┘    └─────────────┘    └─────────────┘
       │
       ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ PostgreSQL  │    │    NATS     │    │Notification │
│   (gRPC)    │    │ Event Bus   │    │  Service    │
└─────────────┘    └─────────────┘    └─────────────┘
```

---

## Component Design

### Service Layer (billing_service.py)

```python
class BillingService:
    """
    Billing orchestration service.

    Responsibilities:
    - Usage recording and tracking
    - Cost calculation with free tier and subscription
    - Billing method selection and processing
    - Quota management and enforcement
    - Event publishing for integration
    """

    def __init__(
        self,
        repository: Optional[BillingRepositoryProtocol] = None,
        event_bus: Optional[EventBusProtocol] = None,
        product_client: Optional[ProductClientProtocol] = None,
        wallet_client: Optional[WalletClientProtocol] = None,
        subscription_client: Optional[SubscriptionClientProtocol] = None,
    ):
        # Lazy initialization via properties
        ...

    # Core Billing Operations
    async def record_usage_and_bill(request: UsageRecordRequest) -> BillingRecordResponse
    async def calculate_billing_cost(request: BillingCalculateRequest) -> BillingCostResponse
    async def process_billing(request: BillingProcessRequest) -> BillingProcessResponse

    # Quota Operations
    async def check_quota(request: QuotaCheckRequest) -> QuotaCheckResponse
    async def get_user_quota(user_id: str, service_type: Optional[str]) -> QuotaStatusResponse

    # Statistics and Queries
    async def get_billing_statistics(filters: StatisticsFilters) -> BillingStatisticsResponse
    async def get_billing_records(filters: RecordFilters) -> BillingRecordListResponse
    async def get_billing_record(record_id: str) -> BillingRecordResponse

    # Health
    async def health_check() -> Dict[str, Any]
```

### Repository Layer

#### BillingRepository

```python
class BillingRepository:
    """Billing record data access layer"""

    def __init__(self, config: Optional[ConfigManager] = None):
        # PostgreSQL gRPC client setup
        ...

    # Record Operations
    async def create_record(record_data: Dict[str, Any]) -> Optional[BillingRecord]
    async def get_by_record_id(record_id: str) -> Optional[BillingRecord]
    async def update_record_status(record_id: str, status: str, processed_at: datetime) -> bool
    async def get_user_records(user_id: str, filters: Dict) -> List[BillingRecord]

    # Event Operations
    async def create_event(event_data: Dict[str, Any]) -> Optional[BillingEvent]
    async def get_event_by_idempotency_key(key: str) -> Optional[BillingEvent]
    async def mark_event_processed(event_id: str) -> bool

    # Quota Operations
    async def get_user_quota(user_id: str, service_type: str) -> Optional[BillingQuota]
    async def update_quota_usage(user_id: str, service_type: str, amount: int) -> bool
    async def reset_quota(user_id: str, service_type: str) -> bool

    # Statistics
    async def get_statistics(filters: Dict) -> Dict[str, Any]
    async def get_service_breakdown(filters: Dict) -> Dict[str, float]
```

### Protocol Interfaces (protocols.py)

```python
@runtime_checkable
class BillingRepositoryProtocol(Protocol):
    """Interface for billing repository - enables testing with mocks"""

    async def create_record(self, record_data: Dict[str, Any]) -> Optional[BillingRecord]: ...
    async def get_by_record_id(self, record_id: str) -> Optional[BillingRecord]: ...
    async def update_record_status(self, record_id: str, status: str, processed_at: datetime) -> bool: ...
    async def get_user_records(self, user_id: str, filters: Dict) -> List[BillingRecord]: ...
    async def get_event_by_idempotency_key(self, key: str) -> Optional[BillingEvent]: ...
    async def get_user_quota(self, user_id: str, service_type: str) -> Optional[BillingQuota]: ...
    async def update_quota_usage(self, user_id: str, service_type: str, amount: int) -> bool: ...
    async def get_statistics(self, filters: Dict) -> Dict[str, Any]: ...

@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for event publishing"""

    async def publish_event(self, event: Any) -> None: ...

@runtime_checkable
class WalletClientProtocol(Protocol):
    """Interface for wallet service client"""

    async def get_balance(self, user_id: str) -> Optional[Dict[str, Any]]: ...
    async def get_credit_balance(self, user_id: str) -> Optional[float]: ...
    async def deduct_balance(self, user_id: str, amount: float, reason: str) -> bool: ...
    async def deduct_credits(self, user_id: str, amount: float, reason: str) -> bool: ...

@runtime_checkable
class SubscriptionClientProtocol(Protocol):
    """Interface for subscription service client"""

    async def get_user_subscription(self, user_id: str) -> Optional[Dict[str, Any]]: ...
    async def check_service_coverage(self, user_id: str, service_type: str) -> bool: ...

@runtime_checkable
class ProductClientProtocol(Protocol):
    """Interface for product service client"""

    async def get_service_pricing(self, service_type: str) -> Optional[Dict[str, Any]]: ...
    async def get_free_tier_config(self, service_type: str) -> Optional[Dict[str, Any]]: ...
```

---

## Database Schemas

### Schema: billing

#### Table: billing.billing_records

```sql
CREATE SCHEMA IF NOT EXISTS billing;

CREATE TABLE IF NOT EXISTS billing.billing_records (
    record_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    service_type VARCHAR(30) NOT NULL,
    usage_amount DECIMAL(18,6) NOT NULL,
    unit_cost DECIMAL(18,8) NOT NULL,
    total_cost DECIMAL(18,6) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    billing_method VARCHAR(30),
    status VARCHAR(20) DEFAULT 'pending',
    metadata JSONB DEFAULT '{}',
    idempotency_key VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_billing_records_user_id ON billing.billing_records(user_id);
CREATE INDEX idx_billing_records_status ON billing.billing_records(status);
CREATE INDEX idx_billing_records_service_type ON billing.billing_records(service_type);
CREATE INDEX idx_billing_records_created_at ON billing.billing_records(created_at DESC);
CREATE INDEX idx_billing_records_user_status ON billing.billing_records(user_id, status);
CREATE UNIQUE INDEX idx_billing_records_idempotency ON billing.billing_records(idempotency_key) WHERE idempotency_key IS NOT NULL;
```

#### Table: billing.billing_events

```sql
CREATE TABLE IF NOT EXISTS billing.billing_events (
    event_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    service_type VARCHAR(30) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    quantity DECIMAL(18,6) NOT NULL,
    unit VARCHAR(20),
    metadata JSONB DEFAULT '{}',
    is_processed BOOLEAN DEFAULT FALSE,
    record_id VARCHAR(50) REFERENCES billing.billing_records(record_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_billing_events_user_id ON billing.billing_events(user_id);
CREATE INDEX idx_billing_events_is_processed ON billing.billing_events(is_processed);
CREATE INDEX idx_billing_events_created_at ON billing.billing_events(created_at DESC);
```

#### Table: billing.billing_quotas

```sql
CREATE TABLE IF NOT EXISTS billing.billing_quotas (
    quota_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    service_type VARCHAR(30) NOT NULL,
    quota_type VARCHAR(20) DEFAULT 'soft_limit',
    limit_value DECIMAL(18,6) NOT NULL,
    current_usage DECIMAL(18,6) DEFAULT 0,
    period_type VARCHAR(20) DEFAULT 'monthly',
    period_start TIMESTAMP WITH TIME ZONE,
    period_end TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, service_type, period_type)
);

-- Indexes for performance
CREATE INDEX idx_billing_quotas_user_id ON billing.billing_quotas(user_id);
CREATE INDEX idx_billing_quotas_service_type ON billing.billing_quotas(service_type);
CREATE INDEX idx_billing_quotas_user_service ON billing.billing_quotas(user_id, service_type);
```

#### Table: billing.usage_aggregations

```sql
CREATE TABLE IF NOT EXISTS billing.usage_aggregations (
    aggregation_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    service_type VARCHAR(30) NOT NULL,
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    total_usage DECIMAL(18,6) DEFAULT 0,
    total_cost DECIMAL(18,6) DEFAULT 0,
    record_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, service_type, period_start)
);

-- Indexes for performance
CREATE INDEX idx_usage_agg_user_id ON billing.usage_aggregations(user_id);
CREATE INDEX idx_usage_agg_period ON billing.usage_aggregations(period_start, period_end);
```

---

## Data Flow Diagrams

### Usage Recording and Billing Flow

```
Source Service -> NATS Event (session.tokens_used)
  -> EventHandler (handlers.py)
    -> Check idempotency (event_id)
    <- [If duplicate] Return existing result
    -> BillingService.record_usage_and_bill()
      -> Create BillingRecord (status="pending")
      -> BillingService.calculate_billing_cost()
        -> SubscriptionClient.check_service_coverage()
        <- [If covered] Return cost=0, method="subscription_included"
        -> ProductClient.get_free_tier_config()
        -> Calculate free_tier_applied
        -> Calculate billable_amount = quantity - free_tier
        -> Calculate total_cost = billable_amount × unit_cost
        <- BillingCostResponse
      -> [If total_cost > 0] BillingService.process_billing()
        -> WalletClient.get_credit_balance()
        <- [If sufficient credits]
          -> WalletClient.deduct_credits()
          -> Update record (method="credit_consumption")
        <- [Else] WalletClient.get_balance()
          <- [If sufficient wallet]
            -> WalletClient.deduct_balance()
            -> Update record (method="wallet_deduction")
          <- [Else] Return error (insufficient funds)
      -> Update record status="completed"
      -> EventBus.publish_event(BILLING_PROCESSED)
    <- BillingRecordResponse
  <- Event processed
```

### Cost Calculation Flow

```
Client -> POST /api/v1/billing/calculate
  -> RouteHandler (main.py)
    -> BillingService.calculate_billing_cost()
      -> SubscriptionClient.get_user_subscription()
      <- [If active subscription]
        -> SubscriptionClient.check_service_coverage()
        <- [If covered] Return {
            billable_amount: 0,
            total_cost: 0,
            billing_method: "subscription_included"
          }
      -> ProductClient.get_free_tier_config()
      <- FreeTierConfig {daily_limit: 1000, remaining: 500}
      -> free_tier_applied = min(quantity, remaining)
      -> billable_amount = quantity - free_tier_applied
      -> total_cost = billable_amount × unit_cost
      -> Determine billing_method based on balances
    <- BillingCostResponse
  <- HTTP 200 {cost breakdown}
```

### Quota Check Flow

```
Client -> POST /api/v1/billing/quota/check
  -> RouteHandler (main.py)
    -> BillingService.check_quota()
      -> BillingRepository.get_user_quota()
      <- BillingQuota {limit_value, current_usage, quota_type}
      -> remaining = limit_value - current_usage
      -> would_exceed = (current_usage + requested_amount) > limit_value
      <- [If hard_limit AND would_exceed]
        -> EventBus.publish_event(QUOTA_EXCEEDED)
        <- QuotaCheckResponse {is_allowed: false}
      <- [If soft_limit AND would_exceed]
        <- QuotaCheckResponse {is_allowed: true, warning_message: "..."}
      <- QuotaCheckResponse {is_allowed: true}
    <- QuotaCheckResponse
  <- HTTP 200 {quota status}
```

### Billing Processing Flow

```
Client -> POST /api/v1/billing/process
  -> RouteHandler (main.py)
    -> BillingService.process_billing()
      -> BillingRepository.get_by_record_id()
      <- BillingRecord (verify exists and pending)
      -> WalletClient.get_credit_balance()
      <- credit_balance
      <- [If credit_balance >= total_cost]
        -> WalletClient.deduct_credits(total_cost)
        <- success
        -> billing_method = "credit_consumption"
      <- [Else]
        -> WalletClient.get_balance()
        <- wallet_balance
        <- [If wallet_balance >= total_cost]
          -> WalletClient.deduct_balance(total_cost)
          <- success
          -> billing_method = "wallet_deduction"
        <- [Else]
          -> status = "failed"
          -> EventBus.publish_event(BILLING_ERROR)
          <- BillingProcessResponse {status: "failed"}
      -> BillingRepository.update_record_status("completed")
      -> EventBus.publish_event(BILLING_PROCESSED)
    <- BillingProcessResponse
  <- HTTP 200 {processing result}
```

---

## Technology Stack

- **Language**: Python 3.9+
- **Framework**: FastAPI (async support)
- **Validation**: Pydantic v2 (models and schemas)
- **Database**: PostgreSQL (via AsyncPostgresClient/gRPC)
- **Event Bus**: NATS (via core.nats_client)
- **Service Discovery**: Consul (via isa_common.consul_client)
- **HTTP Client**: httpx (async) for internal service calls
- **Configuration**: ConfigManager (core.config_manager)
- **Logging**: Python logging (core.logger)

---

## Security Considerations

### Authentication
- JWT token validation at API Gateway level
- X-Internal-Call header for internal service-to-service calls
- Billing Service trusts gateway-authenticated requests

### Authorization
- Billing records isolated by user_id
- Only record owner can view their billing history
- Admin role required for service-wide statistics
- 404 returned for both not found and unauthorized

### Input Validation
- Pydantic models validate all request payloads
- ServiceType enumeration validates service types
- Quantity and amount must be positive
- SQL injection prevented by parameterized queries

### Financial Security
- No payment card details stored in billing service
- Wallet/credit deductions via service calls
- Idempotency prevents double-charging
- All transactions logged for audit

### Data Privacy
- Billing records stored encrypted at rest
- User data isolated by user_id
- GDPR: user.deleted event triggers cleanup
- Audit trail maintained for compliance

---

## Event-Driven Architecture

### Published Events

| Event Type | When Published | Payload |
|------------|----------------|---------|
| USAGE_RECORDED | Usage recorded | record_id, user_id, service_type, quantity, timestamp |
| BILLING_CALCULATED | Cost calculated | record_id, user_id, original_amount, billable_amount, total_cost, billing_method, timestamp |
| BILLING_PROCESSED | Billing completed | record_id, user_id, total_cost, billing_method, balance_after, timestamp |
| QUOTA_EXCEEDED | Hard limit hit | user_id, service_type, quota_type, limit_value, current_usage, requested_amount, timestamp |
| BILLING_ERROR | Processing failed | record_id, user_id, error_type, error_message, timestamp |

### Subscribed Events

| Event Pattern | Source | Handler Action |
|---------------|--------|----------------|
| session.tokens_used | session_service | Record token usage, calculate cost, process billing |
| order.completed | order_service | Create billing record for order |
| session.ended | session_service | Finalize session billing |
| user.deleted | account_service | Archive billing records, cancel pending |

### Event Model Examples

```python
# BILLING_PROCESSED
{
    "event_type": "BILLING_PROCESSED",
    "source": "billing_service",
    "data": {
        "record_id": "bill_xyz789",
        "user_id": "user_12345",
        "total_cost": 0.15,
        "billing_method": "wallet_deduction",
        "wallet_balance_after": 9.85,
        "timestamp": "2025-12-15T10:30:00Z"
    }
}

# QUOTA_EXCEEDED
{
    "event_type": "QUOTA_EXCEEDED",
    "source": "billing_service",
    "data": {
        "user_id": "user_12345",
        "service_type": "session",
        "quota_type": "hard_limit",
        "limit_value": 100000,
        "current_usage": 95000,
        "requested_amount": 10000,
        "timestamp": "2025-12-15T10:30:00Z"
    }
}
```

---

## Error Handling

### Exception Hierarchy

```python
class BillingServiceError(Exception):
    """Base exception for billing service errors"""
    # Maps to HTTP 500

class BillingValidationError(BillingServiceError):
    """Validation error"""
    # Maps to HTTP 400

class BillingRecordNotFoundError(BillingServiceError):
    """Record not found error"""
    # Maps to HTTP 404

class InsufficientFundsError(BillingServiceError):
    """Insufficient balance/credits"""
    # Maps to HTTP 402

class QuotaExceededError(BillingServiceError):
    """Quota limit exceeded"""
    # Maps to HTTP 429

class DuplicateBillingError(BillingServiceError):
    """Duplicate billing attempt"""
    # Maps to HTTP 409
```

### HTTP Error Mapping

| Exception | HTTP Code | Response |
|-----------|-----------|----------|
| BillingValidationError | 400 | `{"detail": "error message"}` |
| InsufficientFundsError | 402 | `{"detail": "Insufficient funds", "balance": 5.00, "required": 10.00}` |
| BillingRecordNotFoundError | 404 | `{"detail": "Billing record not found: {id}"}` |
| DuplicateBillingError | 409 | `{"detail": "Duplicate billing", "existing_record_id": "..."}` |
| QuotaExceededError | 429 | `{"detail": "Quota exceeded", "limit": 100000, "current": 95000}` |
| BillingServiceError | 500 | `{"detail": "error message"}` |

### Error Response Format

```json
{
    "error": "InsufficientFundsError",
    "detail": "Insufficient wallet balance",
    "balance": 5.00,
    "required": 10.50,
    "timestamp": "2025-12-15T10:30:00Z"
}
```

---

## Performance Considerations

### Database Optimization
- Indexes on user_id, record_id, status, created_at
- Composite index on (user_id, status) for user billing queries
- Unique index on idempotency_key for duplicate prevention
- Pagination enforced to limit result sets

### Caching Strategy
- Subscription status: Cache for 5 minutes (reduce service calls)
- Free tier remaining: Cache with TTL until period end
- Product pricing: Cache for 15 minutes
- Statistics: Cache aggregate results for 60 seconds

### Connection Pooling
- AsyncPostgresClient manages connection pool
- Pool size configured via environment variables
- Connections reused across requests
- Separate pools for heavy queries vs. OLTP

### Event Processing
- Non-blocking async event handling
- Idempotency check prevents redundant processing
- Batch processing for high-volume events
- Dead letter queue for failed events

### Billing Processing
- Credit check before wallet check (optimization)
- Early return if subscription covers usage
- Atomic balance deduction via service calls
- Retry logic with exponential backoff

---

## Deployment Configuration

### Environment Variables

```bash
# Service Configuration
SERVICE_NAME=billing_service
SERVICE_HOST=0.0.0.0
SERVICE_PORT=8208
LOG_LEVEL=INFO
DEBUG=false

# Database
POSTGRES_HOST=isa-postgres-grpc
POSTGRES_PORT=50061

# NATS Event Bus
NATS_URL=nats://nats:4222

# Consul
CONSUL_ENABLED=true
CONSUL_HOST=consul
CONSUL_PORT=8500

# Service Clients
WALLET_SERVICE_URL=http://wallet_service:8210
SUBSCRIPTION_SERVICE_URL=http://subscription_service:8211
PRODUCT_SERVICE_URL=http://product_service:8212

# Billing Configuration
DEFAULT_CURRENCY=USD
FREE_TIER_ENABLED=true
QUOTA_ENFORCEMENT_ENABLED=true
BILLING_RETRY_MAX_ATTEMPTS=3
```

### Health Checks

```yaml
# Kubernetes liveness probe
livenessProbe:
  httpGet:
    path: /health
    port: 8208
  initialDelaySeconds: 10
  periodSeconds: 30

# Kubernetes readiness probe
readinessProbe:
  httpGet:
    path: /health/detailed
    port: 8208
  initialDelaySeconds: 5
  periodSeconds: 10
```

### Service Registration (Consul)

```json
{
  "service_name": "billing_service",
  "version": "1.0.0",
  "tags": ["v1", "billing", "metering", "quota"],
  "capabilities": [
    "usage_recording",
    "cost_calculation",
    "billing_processing",
    "quota_management",
    "billing_statistics",
    "event_driven"
  ],
  "health_check": {
    "type": "http",
    "path": "/health",
    "interval": "30s"
  }
}
```

### Resource Requirements

```yaml
resources:
  requests:
    cpu: 200m
    memory: 512Mi
  limits:
    cpu: 1000m
    memory: 1Gi
```

---

## Testing Strategy

### Unit Tests (Layer 1)
- Test Pydantic model validation
- Test cost calculation formulas
- Test factory data generation
- No I/O, no mocks needed

### Component Tests (Layer 2)
- Test BillingService with mocked repositories
- Verify cost calculation logic
- Verify billing method selection
- Verify quota enforcement
- Verify event publishing calls

### Integration Tests (Layer 3)
- Test with real PostgreSQL
- Test full billing lifecycle
- Test idempotency handling
- Use X-Internal-Call header

### API Tests (Layer 4)
- Test HTTP endpoints
- Validate response contracts
- Test error handling
- Test pagination

### Smoke Tests (Layer 5)
- End-to-end bash scripts
- Test happy path billing
- Test quota checking
- Quick production validation

---

**Document Version**: 1.0
**Last Updated**: 2025-12-15
**Maintained By**: Billing Service Team
