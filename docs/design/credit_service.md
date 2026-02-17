# Credit Service - Design Document

## Architecture Overview

### Service Architecture

```
+------------------------------------------------------------+
|                    Credit Service                           |
+------------------------------------------------------------+
|  FastAPI Application (main.py)                             |
|  +- Route Handlers (accounts, balance, allocate, consume)  |
|  +- Dependency Injection Setup                             |
|  +- Lifespan Management (startup/shutdown)                 |
+------------------------------------------------------------+
|  Service Layer (credit_service.py)                         |
|  +- Credit Account Management                              |
|  +- Credit Allocation (campaign, manual)                   |
|  +- Credit Consumption (FIFO expiration)                   |
|  +- Credit Expiration Processing                           |
|  +- Credit Transfer                                        |
|  +- Balance Aggregation                                    |
|  +- Event Publishing                                       |
+------------------------------------------------------------+
|  Repository Layer (credit_repository.py)                   |
|  +- CreditAccountRepository                                |
|  +- CreditTransactionRepository                            |
|  +- CreditCampaignRepository                               |
|  +- CreditAllocationRepository                             |
+------------------------------------------------------------+
|  Dependency Injection (protocols.py)                       |
|  +- CreditRepositoryProtocol                               |
|  +- EventBusProtocol                                       |
|  +- AccountClientProtocol                                  |
|  +- SubscriptionClientProtocol                             |
+------------------------------------------------------------+
|  Factory (factory.py)                                      |
|  +- create_credit_service() - production instantiation     |
+------------------------------------------------------------+

External Dependencies:
- PostgreSQL via gRPC (data persistence)
- NATS (event publishing/subscribing)
- Account Service (user validation)
- Subscription Service (subscription credits)
- Consul (service discovery)
```

### Component Diagram

```
+-------------+    +-------------+    +-------------+
|   Account   |    |Subscription |    |   Order     |
|   Service   |--->|   Service   |--->|  Service    |
+------+------+    +------+------+    +------+------+
       |                  |                   |
       |   (NATS Events)  |                   |
       +------------------+-----------------+
                          v
                   +-------------+
                   |   Credit    |
                   |   Service   |
                   +------+------+
                          |
       +------------------+-----------------+
       |                  |                 |
       v                  v                 v
+-------------+    +-------------+    +-------------+
|   Billing   |    |   Wallet    |    |Notification |
|   Service   |    |   Service   |    |  Service    |
+-------------+    +-------------+    +-------------+
       |
       v
+-------------+    +-------------+    +-------------+
| PostgreSQL  |    |    NATS     |    |   Consul    |
|   (gRPC)    |    | Event Bus   |    |  Discovery  |
+-------------+    +-------------+    +-------------+
```

---

## Component Design

### Service Layer (credit_service.py)

```python
class CreditService:
    """
    Credit management service.

    Responsibilities:
    - Credit account lifecycle management
    - Credit allocation from campaigns and manual
    - Credit consumption with FIFO expiration
    - Credit expiration processing
    - Credit transfer between users
    - Balance aggregation and reporting
    - Event publishing for integration
    """

    def __init__(
        self,
        repository: Optional[CreditRepositoryProtocol] = None,
        event_bus: Optional[EventBusProtocol] = None,
        account_client: Optional[AccountClientProtocol] = None,
        subscription_client: Optional[SubscriptionClientProtocol] = None,
    ):
        # Lazy initialization via properties
        ...

    # Credit Account Operations
    async def create_account(request: CreateAccountRequest) -> CreditAccountResponse
    async def get_account(account_id: str) -> CreditAccountResponse
    async def list_accounts(user_id: str, filters: AccountFilters) -> AccountListResponse
    async def deactivate_account(account_id: str) -> bool

    # Balance Operations
    async def get_balance(user_id: str) -> CreditBalanceSummary
    async def check_availability(user_id: str, amount: int) -> AvailabilityResponse

    # Allocation Operations
    async def allocate_credits(request: AllocateRequest) -> AllocationResponse
    async def allocate_from_campaign(user_id: str, campaign_id: str) -> AllocationResponse

    # Consumption Operations
    async def consume_credits(request: ConsumeRequest) -> ConsumptionResponse
    async def get_consumption_plan(user_id: str, amount: int) -> List[ConsumptionItem]

    # Expiration Operations
    async def process_expirations() -> ExpirationResult
    async def get_expiring_soon(user_id: str, days: int = 7) -> List[ExpiringCredit]

    # Transfer Operations
    async def transfer_credits(request: TransferRequest) -> TransferResponse

    # Campaign Operations
    async def create_campaign(request: CreateCampaignRequest) -> CampaignResponse
    async def get_campaign(campaign_id: str) -> CampaignResponse
    async def update_campaign(campaign_id: str, updates: CampaignUpdate) -> CampaignResponse

    # Transaction Operations
    async def get_transactions(user_id: str, filters: TransactionFilters) -> TransactionListResponse

    # Statistics
    async def get_statistics(filters: StatisticsFilters) -> CreditStatistics

    # Health
    async def health_check() -> Dict[str, Any]
```

### Repository Layer

#### CreditRepository

```python
class CreditRepository:
    """Credit data access layer"""

    def __init__(self, config: Optional[ConfigManager] = None):
        # PostgreSQL gRPC client setup
        ...

    # Account Operations
    async def create_account(account_data: Dict[str, Any]) -> Optional[CreditAccount]
    async def get_account_by_id(account_id: str) -> Optional[CreditAccount]
    async def get_account_by_user_type(user_id: str, credit_type: str) -> Optional[CreditAccount]
    async def get_user_accounts(user_id: str, filters: Dict) -> List[CreditAccount]
    async def update_account_balance(account_id: str, new_balance: int) -> bool
    async def deactivate_account(account_id: str) -> bool

    # Transaction Operations
    async def create_transaction(txn_data: Dict[str, Any]) -> Optional[CreditTransaction]
    async def get_transaction_by_id(transaction_id: str) -> Optional[CreditTransaction]
    async def get_user_transactions(user_id: str, filters: Dict) -> List[CreditTransaction]
    async def get_account_transactions(account_id: str, filters: Dict) -> List[CreditTransaction]

    # Allocation Operations
    async def create_allocation(alloc_data: Dict[str, Any]) -> Optional[CreditAllocation]
    async def get_allocation_by_id(allocation_id: str) -> Optional[CreditAllocation]
    async def get_user_campaign_allocations(user_id: str, campaign_id: str) -> List[CreditAllocation]
    async def get_expiring_allocations(before: datetime) -> List[CreditAllocation]

    # Campaign Operations
    async def create_campaign(campaign_data: Dict[str, Any]) -> Optional[CreditCampaign]
    async def get_campaign_by_id(campaign_id: str) -> Optional[CreditCampaign]
    async def get_active_campaigns(credit_type: Optional[str] = None) -> List[CreditCampaign]
    async def update_campaign_budget(campaign_id: str, allocated_amount: int) -> bool
    async def deactivate_campaign(campaign_id: str) -> bool

    # Balance Operations
    async def get_aggregated_balance(user_id: str) -> Dict[str, int]
    async def get_expiring_soon(user_id: str, days: int) -> List[Dict]

    # Statistics
    async def get_statistics(filters: Dict) -> Dict[str, Any]
```

### Protocol Interfaces (protocols.py)

```python
@runtime_checkable
class CreditRepositoryProtocol(Protocol):
    """Interface for credit repository - enables testing with mocks"""

    async def create_account(self, account_data: Dict[str, Any]) -> Optional[CreditAccount]: ...
    async def get_account_by_id(self, account_id: str) -> Optional[CreditAccount]: ...
    async def get_account_by_user_type(self, user_id: str, credit_type: str) -> Optional[CreditAccount]: ...
    async def get_user_accounts(self, user_id: str, filters: Dict) -> List[CreditAccount]: ...
    async def update_account_balance(self, account_id: str, new_balance: int) -> bool: ...
    async def create_transaction(self, txn_data: Dict[str, Any]) -> Optional[CreditTransaction]: ...
    async def get_user_transactions(self, user_id: str, filters: Dict) -> List[CreditTransaction]: ...
    async def create_allocation(self, alloc_data: Dict[str, Any]) -> Optional[CreditAllocation]: ...
    async def get_expiring_allocations(self, before: datetime) -> List[CreditAllocation]: ...
    async def create_campaign(self, campaign_data: Dict[str, Any]) -> Optional[CreditCampaign]: ...
    async def get_campaign_by_id(self, campaign_id: str) -> Optional[CreditCampaign]: ...
    async def get_aggregated_balance(self, user_id: str) -> Dict[str, int]: ...
    async def get_statistics(self, filters: Dict) -> Dict[str, Any]: ...

@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for event publishing"""

    async def publish_event(self, event: Any) -> None: ...

@runtime_checkable
class AccountClientProtocol(Protocol):
    """Interface for account service client"""

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]: ...
    async def validate_user(self, user_id: str) -> bool: ...

@runtime_checkable
class SubscriptionClientProtocol(Protocol):
    """Interface for subscription service client"""

    async def get_user_subscription(self, user_id: str) -> Optional[Dict[str, Any]]: ...
    async def get_subscription_credits(self, subscription_id: str) -> Optional[int]: ...
```

---

## Database Schemas

### Schema: credit

#### Table: credit.credit_accounts

```sql
CREATE SCHEMA IF NOT EXISTS credit;

CREATE TABLE IF NOT EXISTS credit.credit_accounts (
    id SERIAL PRIMARY KEY,
    account_id VARCHAR(50) UNIQUE NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    organization_id VARCHAR(50),
    credit_type VARCHAR(30) NOT NULL,
    balance INTEGER DEFAULT 0,
    total_allocated INTEGER DEFAULT 0,
    total_consumed INTEGER DEFAULT 0,
    total_expired INTEGER DEFAULT 0,
    currency VARCHAR(10) DEFAULT 'CREDIT',
    expiration_policy VARCHAR(30) DEFAULT 'fixed_days',
    expiration_days INTEGER DEFAULT 90,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, credit_type)
);

-- Indexes for performance
CREATE INDEX idx_credit_accounts_user_id ON credit.credit_accounts(user_id);
CREATE INDEX idx_credit_accounts_type ON credit.credit_accounts(credit_type);
CREATE INDEX idx_credit_accounts_user_type ON credit.credit_accounts(user_id, credit_type);
CREATE INDEX idx_credit_accounts_active ON credit.credit_accounts(is_active) WHERE is_active = TRUE;
```

#### Table: credit.credit_transactions

```sql
CREATE TABLE IF NOT EXISTS credit.credit_transactions (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(50) UNIQUE NOT NULL,
    account_id VARCHAR(50) NOT NULL REFERENCES credit.credit_accounts(account_id),
    user_id VARCHAR(50) NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    amount INTEGER NOT NULL,
    balance_before INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    reference_id VARCHAR(100),
    reference_type VARCHAR(30),
    description TEXT,
    metadata JSONB DEFAULT '{}',
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_credit_transactions_account_id ON credit.credit_transactions(account_id);
CREATE INDEX idx_credit_transactions_user_id ON credit.credit_transactions(user_id);
CREATE INDEX idx_credit_transactions_type ON credit.credit_transactions(transaction_type);
CREATE INDEX idx_credit_transactions_created_at ON credit.credit_transactions(created_at DESC);
CREATE INDEX idx_credit_transactions_expires_at ON credit.credit_transactions(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX idx_credit_transactions_reference ON credit.credit_transactions(reference_id, reference_type);
```

#### Table: credit.credit_campaigns

```sql
CREATE TABLE IF NOT EXISTS credit.credit_campaigns (
    id SERIAL PRIMARY KEY,
    campaign_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    credit_type VARCHAR(30) NOT NULL,
    credit_amount INTEGER NOT NULL,
    total_budget INTEGER NOT NULL,
    allocated_amount INTEGER DEFAULT 0,
    remaining_budget INTEGER GENERATED ALWAYS AS (total_budget - allocated_amount) STORED,
    eligibility_rules JSONB DEFAULT '{}',
    allocation_rules JSONB DEFAULT '{}',
    start_date TIMESTAMP WITH TIME ZONE NOT NULL,
    end_date TIMESTAMP WITH TIME ZONE NOT NULL,
    expiration_days INTEGER DEFAULT 90,
    max_allocations_per_user INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_by VARCHAR(50),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_credit_campaigns_type ON credit.credit_campaigns(credit_type);
CREATE INDEX idx_credit_campaigns_active ON credit.credit_campaigns(is_active);
CREATE INDEX idx_credit_campaigns_dates ON credit.credit_campaigns(start_date, end_date);
CREATE INDEX idx_credit_campaigns_active_current ON credit.credit_campaigns(is_active, start_date, end_date)
    WHERE is_active = TRUE;
```

#### Table: credit.credit_allocations

```sql
CREATE TABLE IF NOT EXISTS credit.credit_allocations (
    id SERIAL PRIMARY KEY,
    allocation_id VARCHAR(50) UNIQUE NOT NULL,
    campaign_id VARCHAR(50) REFERENCES credit.credit_campaigns(campaign_id),
    user_id VARCHAR(50) NOT NULL,
    account_id VARCHAR(50) NOT NULL REFERENCES credit.credit_accounts(account_id),
    transaction_id VARCHAR(50) REFERENCES credit.credit_transactions(transaction_id),
    amount INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'completed',
    expires_at TIMESTAMP WITH TIME ZONE,
    expired_amount INTEGER DEFAULT 0,
    consumed_amount INTEGER DEFAULT 0,
    remaining_amount INTEGER GENERATED ALWAYS AS (amount - expired_amount - consumed_amount) STORED,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_credit_allocations_user_id ON credit.credit_allocations(user_id);
CREATE INDEX idx_credit_allocations_campaign ON credit.credit_allocations(campaign_id);
CREATE INDEX idx_credit_allocations_account ON credit.credit_allocations(account_id);
CREATE INDEX idx_credit_allocations_expires_at ON credit.credit_allocations(expires_at);
CREATE INDEX idx_credit_allocations_user_campaign ON credit.credit_allocations(user_id, campaign_id);
CREATE INDEX idx_credit_allocations_active_expiring ON credit.credit_allocations(expires_at, status)
    WHERE status = 'completed' AND remaining_amount > 0;
```

---

## Data Flow Diagrams

### Credit Allocation Flow

```
Source Event (user.created) -> NATS
  -> EventHandler (handlers.py)
    -> Check idempotency (user_id + campaign_id)
    <- [If duplicate] Skip, log warning
    -> CreditService.allocate_from_campaign()
      -> Get active sign-up campaign
      <- [If no campaign] Return, no allocation
      -> Validate user eligibility
      <- [If ineligible] Return, publish event
      -> Check campaign budget
      <- [If exhausted] Return budget_exhausted error
      -> Get or create credit account (type: bonus)
      -> Create credit transaction (type: allocate)
      -> Create allocation record
      -> Update account balance
      -> Update campaign allocated_amount
      -> EventBus.publish_event(CREDIT_ALLOCATED)
    <- AllocationResponse
  <- Event processed
```

### Credit Consumption Flow (FIFO)

```
Billing Service -> POST /api/v1/credits/consume
  -> RouteHandler (main.py)
    -> CreditService.consume_credits()
      -> Get user's credit accounts (active, balance > 0)
      -> Order by expiration (FIFO):
         1. expires_at ASC (soonest first)
         2. created_at ASC (oldest first)
         3. credit_type priority
      -> Calculate consumption plan
      -> [If insufficient] Return available + deficit
      -> For each account in plan:
         -> Create consumption transaction
         -> Update account balance
         -> Update allocation consumed_amount
      -> Sum total consumed
      -> EventBus.publish_event(CREDIT_CONSUMED)
    <- ConsumptionResponse {
         amount_consumed,
         balance_before,
         balance_after,
         transactions[]
       }
  <- HTTP 200 {consumption result}
```

### Credit Expiration Flow

```
Scheduler -> Trigger expiration job
  -> CreditService.process_expirations()
    -> Query allocations WHERE:
       - expires_at <= NOW()
       - remaining_amount > 0
       - status = 'completed'
    -> For each expiring allocation:
       -> Get account
       -> remaining = allocation.remaining_amount
       -> Create expire transaction
       -> Update account balance (-= remaining)
       -> Update account total_expired (+= remaining)
       -> Update allocation:
          - expired_amount += remaining
          - status = 'expired' (if fully expired)
       -> EventBus.publish_event(CREDIT_EXPIRED)
    -> Aggregate results
  <- ExpirationResult {
       processed_count,
       total_expired,
       accounts_affected
     }
```

### Balance Summary Flow

```
Client -> GET /api/v1/credits/balance?user_id={user_id}
  -> RouteHandler (main.py)
    -> CreditService.get_balance()
      -> CreditRepository.get_user_accounts()
      -> For each account:
         -> Sum balance by credit_type
         -> Track total_balance
      -> CreditRepository.get_expiring_soon(days=7)
      -> Find earliest expiration
    <- CreditBalanceSummary {
         user_id,
         total_balance,
         available_balance,
         expiring_soon,
         by_type: {promotional: X, bonus: Y, ...},
         next_expiration: {amount, expires_at}
       }
  <- HTTP 200 {balance summary}
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
- **Scheduling**: APScheduler (for expiration job)

---

## Security Considerations

### Authentication
- JWT token validation at API Gateway level
- X-Internal-Call header for internal service-to-service calls
- Credit Service trusts gateway-authenticated requests

### Authorization
- Credit accounts isolated by user_id
- Only account owner can view their credits
- Admin role required for campaign management
- 404 returned for both not found and unauthorized

### Input Validation
- Pydantic models validate all request payloads
- CreditType enumeration validates credit types
- Amount must be positive integer
- SQL injection prevented by parameterized queries

### Financial Security
- All credit amounts stored as integers (no floating point)
- Atomic balance updates prevent race conditions
- Consumption linked to billing records for audit
- All transactions logged immutably

### Data Privacy
- Credit records stored encrypted at rest
- User data isolated by user_id
- GDPR: user.deleted event triggers cleanup
- Audit trail maintained for compliance

---

## Event-Driven Architecture

### Published Events

| Event Type | When Published | Payload |
|------------|----------------|---------|
| CREDIT_ALLOCATED | Credits allocated | allocation_id, user_id, credit_type, amount, expires_at, balance_after, campaign_id |
| CREDIT_CONSUMED | Credits consumed | transaction_id, user_id, amount, billing_record_id, balance_before, balance_after |
| CREDIT_EXPIRED | Credits expired | transaction_id, user_id, amount, credit_type, balance_after |
| CREDIT_TRANSFERRED | Credits transferred | transfer_id, from_user_id, to_user_id, amount, credit_type |
| CREDIT_EXPIRING_SOON | 7-day warning | user_id, amount, expires_at, credit_type |
| CAMPAIGN_BUDGET_EXHAUSTED | Budget depleted | campaign_id, campaign_name, total_budget, allocated_amount |

### Subscribed Events

| Event Pattern | Source | Handler Action |
|---------------|--------|----------------|
| user.created | account_service | Allocate sign-up bonus credits |
| subscription.created | subscription_service | Allocate subscription credits |
| subscription.renewed | subscription_service | Allocate monthly subscription credits |
| order.completed | order_service | Process referral credits |
| user.deleted | account_service | Archive credit accounts and data |

### Event Model Examples

```python
# CREDIT_ALLOCATED
{
    "event_type": "CREDIT_ALLOCATED",
    "source": "credit_service",
    "data": {
        "allocation_id": "alloc_abc123",
        "user_id": "user_12345",
        "credit_type": "bonus",
        "amount": 1000,
        "campaign_id": "camp_signup2025",
        "expires_at": "2026-03-18T00:00:00Z",
        "balance_after": 1000,
        "timestamp": "2025-12-18T10:30:00Z"
    }
}

# CREDIT_CONSUMED
{
    "event_type": "CREDIT_CONSUMED",
    "source": "credit_service",
    "data": {
        "transaction_id": "txn_xyz789",
        "user_id": "user_12345",
        "amount": 500,
        "billing_record_id": "bill_abc123",
        "balance_before": 2500,
        "balance_after": 2000,
        "timestamp": "2025-12-18T10:35:00Z"
    }
}
```

---

## Error Handling

### Exception Hierarchy

```python
class CreditServiceError(Exception):
    """Base exception for credit service errors"""
    # Maps to HTTP 500

class CreditValidationError(CreditServiceError):
    """Validation error"""
    # Maps to HTTP 400

class CreditAccountNotFoundError(CreditServiceError):
    """Account not found error"""
    # Maps to HTTP 404

class InsufficientCreditsError(CreditServiceError):
    """Insufficient credit balance"""
    # Maps to HTTP 402

class CampaignBudgetExhaustedError(CreditServiceError):
    """Campaign budget depleted"""
    # Maps to HTTP 402

class CampaignNotFoundError(CreditServiceError):
    """Campaign not found"""
    # Maps to HTTP 404

class TransferNotAllowedError(CreditServiceError):
    """Credit type non-transferable"""
    # Maps to HTTP 403

class DuplicateAllocationError(CreditServiceError):
    """Duplicate allocation attempt"""
    # Maps to HTTP 409
```

### HTTP Error Mapping

| Exception | HTTP Code | Response |
|-----------|-----------|----------|
| CreditValidationError | 400 | `{"detail": "error message"}` |
| InsufficientCreditsError | 402 | `{"detail": "Insufficient credits", "balance": 500, "required": 1000}` |
| CampaignBudgetExhaustedError | 402 | `{"detail": "Campaign budget exhausted", "campaign_id": "..."}` |
| TransferNotAllowedError | 403 | `{"detail": "Credit type not transferable", "credit_type": "..."}` |
| CreditAccountNotFoundError | 404 | `{"detail": "Credit account not found: {id}"}` |
| DuplicateAllocationError | 409 | `{"detail": "Duplicate allocation", "existing_allocation_id": "..."}` |
| CreditServiceError | 500 | `{"detail": "error message"}` |

---

## Performance Considerations

### Database Optimization
- Indexes on user_id, account_id, credit_type, expires_at
- Composite index on (user_id, credit_type) for account lookup
- Partial index on active allocations for expiration queries
- Pagination enforced to limit result sets

### Caching Strategy
- Balance summary: Cache for 30 seconds (invalidate on transaction)
- Campaign config: Cache for 5 minutes
- User eligibility: No cache (real-time check)
- Statistics: Cache aggregate results for 60 seconds

### Connection Pooling
- AsyncPostgresClient manages connection pool
- Pool size configured via environment variables
- Connections reused across requests
- Separate pools for heavy queries vs. OLTP

### Batch Processing
- Expiration job processes in batches of 1000
- Parallelized across accounts
- Transaction batching for performance
- Dead letter handling for failures

### FIFO Consumption Optimization
- Pre-sorted query by expires_at, created_at
- Limit accounts queried to those with balance > 0
- Short-circuit if first account covers full amount
- Atomic multi-account consumption via transaction

---

## Deployment Configuration

### Environment Variables

```bash
# Service Configuration
SERVICE_NAME=credit_service
SERVICE_HOST=0.0.0.0
SERVICE_PORT=8229
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
ACCOUNT_SERVICE_URL=http://account_service:8202
SUBSCRIPTION_SERVICE_URL=http://subscription_service:8228

# Credit Configuration
DEFAULT_EXPIRATION_DAYS=90
EXPIRATION_WARNING_DAYS=7
EXPIRATION_JOB_CRON="0 0 * * *"
MAX_CONSUMPTION_ACCOUNTS=10
TRANSFER_ENABLED=true
```

### Health Checks

```yaml
# Kubernetes liveness probe
livenessProbe:
  httpGet:
    path: /health
    port: 8229
  initialDelaySeconds: 10
  periodSeconds: 30

# Kubernetes readiness probe
readinessProbe:
  httpGet:
    path: /health/detailed
    port: 8229
  initialDelaySeconds: 5
  periodSeconds: 10
```

### Service Registration (Consul)

```json
{
  "service_name": "credit_service",
  "version": "1.0.0",
  "tags": ["v1", "credit", "promotional", "bonus"],
  "capabilities": [
    "credit_accounts",
    "credit_allocation",
    "credit_consumption",
    "credit_expiration",
    "credit_transfer",
    "campaign_management",
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
- Test FIFO ordering logic
- Test expiration date calculation
- Test factory data generation
- No I/O, no mocks needed

### Component Tests (Layer 2)
- Test CreditService with mocked repositories
- Verify allocation logic
- Verify consumption FIFO ordering
- Verify expiration processing
- Verify transfer restrictions
- Verify event publishing calls

### Integration Tests (Layer 3)
- Test with real PostgreSQL
- Test full credit lifecycle
- Test idempotency handling
- Test campaign budget tracking
- Use X-Internal-Call header

### API Tests (Layer 4)
- Test HTTP endpoints
- Validate response contracts
- Test error handling
- Test pagination

### Smoke Tests (Layer 5)
- End-to-end bash scripts
- Test happy path allocation
- Test consumption flow
- Quick production validation

---

**Document Version**: 1.0
**Last Updated**: 2025-12-18
**Maintained By**: Credit Service Team
