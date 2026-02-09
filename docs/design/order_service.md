# Order Service - Design Document

## Architecture Overview

### Service Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Order Service (Port 8210)                        │
├─────────────────────────────────────────────────────────────────────────┤
│  FastAPI Application (main.py)                                           │
│  ├─ Health Endpoints (/health, /health/detailed)                         │
│  ├─ Order CRUD (/api/v1/orders/*)                                        │
│  ├─ Search & Stats (/api/v1/orders/search, /statistics)                  │
│  ├─ Integration (/api/v1/payments/*/orders, /subscriptions/*/orders)     │
│  └─ Dependency Injection (get_order_service)                             │
├─────────────────────────────────────────────────────────────────────────┤
│  Service Layer (order_service.py)                                        │
│  ├─ OrderService (Business Logic)                                        │
│  │   ├─ create_order()                                                   │
│  │   ├─ get_order()                                                      │
│  │   ├─ update_order()                                                   │
│  │   ├─ cancel_order()                                                   │
│  │   ├─ complete_order()                                                 │
│  │   ├─ list_orders()                                                    │
│  │   ├─ search_orders()                                                  │
│  │   └─ get_order_statistics()                                           │
│  └─ Lazy-loaded Event Publishers                                         │
├─────────────────────────────────────────────────────────────────────────┤
│  Repository Layer (order_repository.py)                                  │
│  ├─ OrderRepository                                                      │
│  │   ├─ create_order()                                                   │
│  │   ├─ get_order()                                                      │
│  │   ├─ update_order()                                                   │
│  │   ├─ list_orders()                                                    │
│  │   ├─ search_orders()                                                  │
│  │   ├─ cancel_order()                                                   │
│  │   ├─ complete_order()                                                 │
│  │   └─ get_order_statistics()                                           │
│  └─ AsyncPostgresClient (gRPC)                                           │
├─────────────────────────────────────────────────────────────────────────┤
│  Protocols Layer (protocols.py) - DI Interfaces                          │
│  ├─ OrderRepositoryProtocol                                              │
│  ├─ EventBusProtocol                                                     │
│  ├─ PaymentClientProtocol                                                │
│  ├─ WalletClientProtocol                                                 │
│  ├─ AccountClientProtocol                                                │
│  └─ BillingClientProtocol                                                │
├─────────────────────────────────────────────────────────────────────────┤
│  Factory Layer (factory.py)                                              │
│  └─ create_order_service() - Creates service with real dependencies      │
├─────────────────────────────────────────────────────────────────────────┤
│  Events Layer (events/)                                                  │
│  ├─ handlers.py - Incoming event handlers                                │
│  ├─ publishers.py - Outgoing event publishers                            │
│  └─ models.py - Event data models                                        │
├─────────────────────────────────────────────────────────────────────────┤
│  Clients Layer (clients/)                                                │
│  ├─ PaymentClient                                                        │
│  ├─ WalletClient                                                         │
│  ├─ AccountClient                                                        │
│  ├─ StorageClient                                                        │
│  └─ BillingClient                                                        │
└─────────────────────────────────────────────────────────────────────────┘

External Dependencies:
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   PostgreSQL    │  │      NATS       │  │     Consul      │
│   (via gRPC)    │  │   Event Bus     │  │  Service Disc.  │
│   Port 50061    │  │   Port 4222     │  │   Port 8500     │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### Component Interactions

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Client     │────>│   Gateway    │────>│   Order      │
│   (App/Web)  │     │   (APISIX)   │     │   Service    │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
        ┌────────────────────────────────────────┼────────────────────────────────────────┐
        │                                        │                                        │
        ▼                                        ▼                                        ▼
┌──────────────┐                         ┌──────────────┐                         ┌──────────────┐
│   Payment    │                         │   Wallet     │                         │   Account    │
│   Service    │                         │   Service    │                         │   Service    │
│   (8207)     │                         │   (8208)     │                         │   (8202)     │
└──────────────┘                         └──────────────┘                         └──────────────┘
        │                                        │                                        │
        │         ┌──────────────────────────────┼──────────────────────────────┐        │
        │         │                              │                              │        │
        ▼         ▼                              ▼                              ▼        ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    NATS Event Bus                                            │
│  Events: order.*, payment.*, wallet.*, subscription.*, user.*                               │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Database Schemas

### Schema: orders

#### Table: orders.orders

```sql
CREATE SCHEMA IF NOT EXISTS orders;

CREATE TABLE IF NOT EXISTS orders.orders (
    order_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    organization_id VARCHAR(50),

    -- Order Classification
    order_type VARCHAR(30) NOT NULL CHECK (order_type IN ('purchase', 'subscription', 'credit_purchase', 'premium_upgrade')),
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled', 'refunded')),

    -- Pricing
    total_amount DECIMAL(15, 2) NOT NULL CHECK (total_amount > 0),
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    discount_amount DECIMAL(15, 2) DEFAULT 0,
    tax_amount DECIMAL(15, 2) DEFAULT 0,
    final_amount DECIMAL(15, 2) NOT NULL,

    -- Payment
    payment_status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (payment_status IN ('pending', 'processing', 'completed', 'failed', 'refunded')),
    payment_intent_id VARCHAR(100),
    payment_method VARCHAR(50),

    -- References
    subscription_id VARCHAR(50),
    wallet_id VARCHAR(50),
    invoice_id VARCHAR(50),

    -- Order Content
    items JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Fulfillment
    fulfillment_status VARCHAR(30) DEFAULT 'pending',
    tracking_number VARCHAR(100),
    shipping_address JSONB,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,

    -- Cancellation
    cancellation_reason TEXT,
    cancelled_by VARCHAR(50)
);

-- Indexes for common queries
CREATE INDEX idx_orders_user_id ON orders.orders(user_id);
CREATE INDEX idx_orders_status ON orders.orders(status);
CREATE INDEX idx_orders_order_type ON orders.orders(order_type);
CREATE INDEX idx_orders_payment_status ON orders.orders(payment_status);
CREATE INDEX idx_orders_payment_intent ON orders.orders(payment_intent_id);
CREATE INDEX idx_orders_subscription ON orders.orders(subscription_id);
CREATE INDEX idx_orders_wallet ON orders.orders(wallet_id);
CREATE INDEX idx_orders_created_at ON orders.orders(created_at DESC);
CREATE INDEX idx_orders_user_status ON orders.orders(user_id, status);
CREATE INDEX idx_orders_expires_at ON orders.orders(expires_at) WHERE expires_at IS NOT NULL AND status = 'pending';
```

### Migration: 001_initial_schema.sql

```sql
-- Orders service initial schema
-- Creates the orders schema and main orders table

CREATE SCHEMA IF NOT EXISTS orders;

CREATE TABLE IF NOT EXISTS orders.orders (
    order_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    organization_id VARCHAR(50),
    order_type VARCHAR(30) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    total_amount DECIMAL(15, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    discount_amount DECIMAL(15, 2) DEFAULT 0,
    tax_amount DECIMAL(15, 2) DEFAULT 0,
    final_amount DECIMAL(15, 2) NOT NULL,
    payment_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    payment_intent_id VARCHAR(100),
    payment_method VARCHAR(50),
    subscription_id VARCHAR(50),
    wallet_id VARCHAR(50),
    invoice_id VARCHAR(50),
    items JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    fulfillment_status VARCHAR(30) DEFAULT 'pending',
    tracking_number VARCHAR(100),
    shipping_address JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    cancellation_reason TEXT,
    cancelled_by VARCHAR(50)
);

CREATE INDEX idx_orders_user_id ON orders.orders(user_id);
CREATE INDEX idx_orders_status ON orders.orders(status);
CREATE INDEX idx_orders_created_at ON orders.orders(created_at DESC);
```

---

## Data Flow Diagrams

### Order Creation Flow

```
Client                   API Gateway            Order Service           Payment Service         Database
   │                         │                        │                        │                   │
   │  POST /api/v1/orders    │                        │                        │                   │
   │────────────────────────>│                        │                        │                   │
   │                         │  Forward (JWT auth)    │                        │                   │
   │                         │───────────────────────>│                        │                   │
   │                         │                        │                        │                   │
   │                         │                        │  Validate user (async)  │                   │
   │                         │                        │───────────────────────────────────────────>│
   │                         │                        │                        │                   │
   │                         │                        │  INSERT order          │                   │
   │                         │                        │─────────────────────────────────────────>│
   │                         │                        │<─────────────────────────────────────────│
   │                         │                        │                        │                   │
   │                         │                        │  Publish order.created │                   │
   │                         │                        │──────────────────────>NATS                 │
   │                         │                        │                        │                   │
   │                         │<───────────────────────│                        │                   │
   │<────────────────────────│                        │                        │                   │
   │      200 OK + order     │                        │                        │                   │
```

### Payment Completion Flow

```
Payment Service                    NATS                    Order Service              Database
      │                             │                            │                       │
      │  payment.completed event    │                            │                       │
      │────────────────────────────>│                            │                       │
      │                             │  Route to subscriber       │                       │
      │                             │───────────────────────────>│                       │
      │                             │                            │                       │
      │                             │                            │  Get order by         │
      │                             │                            │  payment_intent_id    │
      │                             │                            │──────────────────────>│
      │                             │                            │<──────────────────────│
      │                             │                            │                       │
      │                             │                            │  UPDATE status        │
      │                             │                            │──────────────────────>│
      │                             │                            │<──────────────────────│
      │                             │                            │                       │
      │                             │<───────────────────────────│                       │
      │                             │  order.completed event     │                       │
```

### Order Cancellation Flow

```
Client                Order Service              Wallet Service              Database
   │                        │                          │                        │
   │  POST /cancel          │                          │                        │
   │───────────────────────>│                          │                        │
   │                        │                          │                        │
   │                        │  Get order               │                        │
   │                        │─────────────────────────────────────────────────>│
   │                        │<─────────────────────────────────────────────────│
   │                        │                          │                        │
   │                        │  Validate cancellable    │                        │
   │                        │                          │                        │
   │                        │  Process refund          │                        │
   │                        │────────────────────────>│                        │
   │                        │<────────────────────────│                        │
   │                        │                          │                        │
   │                        │  UPDATE status=cancelled │                        │
   │                        │─────────────────────────────────────────────────>│
   │                        │                          │                        │
   │                        │  Publish order.canceled  │                        │
   │                        │────────────────────────>NATS                      │
   │                        │                          │                        │
   │<───────────────────────│                          │                        │
   │   200 OK               │                          │                        │
```

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Language | Python 3.9+ | Service implementation |
| Framework | FastAPI | REST API framework |
| Validation | Pydantic | Request/response validation |
| Database | PostgreSQL | Data persistence |
| DB Client | AsyncPostgresClient (gRPC) | Database access |
| Event Bus | NATS | Event messaging |
| HTTP Client | httpx (async) | External service calls |
| Service Discovery | Consul | Service registration |
| Configuration | ConfigManager | Environment/Consul config |
| Logging | Python logging | Structured logging |

---

## Security Considerations

### Authentication
- JWT tokens validated by API Gateway
- Service-to-service calls use X-Internal-Call header
- Token verification delegated to auth_service

### Authorization
- Users can only access their own orders
- Admin roles can access all orders
- Service accounts have elevated permissions

### Input Validation
- Pydantic models enforce schema validation
- Amount validation (positive, decimal precision)
- Currency code validation
- Order type validation against enum

### Data Protection
- PII anonymization on user deletion
- Audit trail for all modifications
- No sensitive payment data stored (only references)

### SQL Injection Prevention
- Parameterized queries via AsyncPostgresClient
- No raw SQL string interpolation
- Schema-qualified table names

---

## Event-Driven Architecture

### Published Events

| Event | Type | Trigger | Data |
|-------|------|---------|------|
| order.created | ORDER_CREATED | New order | order_id, user_id, type, amount, items |
| order.updated | ORDER_UPDATED | Order modified | order_id, updated_fields, old/new status |
| order.completed | ORDER_COMPLETED | Payment confirmed | order_id, transaction_id, credits_added |
| order.canceled | ORDER_CANCELED | Order cancelled | order_id, reason, refund_amount |
| order.expired | ORDER_EXPIRED | Order timeout | order_id, expired_at |

### Consumed Events

| Event | Source | Handler | Action |
|-------|--------|---------|--------|
| payment.completed | payment_service | handle_payment_completed | Complete order |
| payment.failed | payment_service | handle_payment_failed | Mark order failed |
| payment.refunded | payment_service | handle_payment_refunded | Mark order refunded |
| wallet.credits_added | wallet_service | handle_wallet_credits_added | Fulfill credit orders |
| subscription.created | subscription_service | handle_subscription_created | Create tracking order |
| subscription.canceled | subscription_service | handle_subscription_canceled | Cancel pending orders |
| user.deleted | account_service | handle_user_deleted | Anonymize/cancel orders |

### Event Idempotency

```python
# Event ID tracking for idempotency
processed_event_ids = set()

def is_event_processed(event_id: str) -> bool:
    return event_id in processed_event_ids

def mark_event_processed(event_id: str):
    processed_event_ids.add(event_id)
    # Limit size to prevent memory issues
    if len(processed_event_ids) > 10000:
        processed_event_ids = set(list(processed_event_ids)[5000:])
```

---

## Error Handling

### Exception Hierarchy

```
OrderServiceError (Base)
├── OrderValidationError (400)
├── OrderNotFoundError (404)
├── InvalidOrderStateError (400)
├── PaymentRequiredError (402)
└── DuplicateOrderError (409)
```

### HTTP Error Mapping

| Exception | HTTP Code | Response |
|-----------|-----------|----------|
| OrderValidationError | 400 | `{"detail": "validation message"}` |
| OrderNotFoundError | 404 | `{"detail": "Order not found"}` |
| InvalidOrderStateError | 400 | `{"detail": "Invalid state transition"}` |
| PaymentRequiredError | 402 | `{"detail": "Payment required"}` |
| General Exception | 500 | `{"detail": "Internal server error"}` |

### Error Response Format

```json
{
    "success": false,
    "message": "Error description",
    "error_code": "ERROR_CODE",
    "order": null
}
```

---

## Performance Considerations

### Database Optimization
- Indexed columns: user_id, status, order_type, payment_intent_id
- Composite index on (user_id, status) for user queries
- Partial index on expires_at for expiration queries

### Connection Pooling
- AsyncPostgresClient manages connection pool
- Configurable pool size via environment
- Connection health checks

### Caching Strategy
- Statistics can be cached (TTL: 60s)
- User order lists can be cached (TTL: 30s)
- Cache invalidation on order changes

### Query Optimization
- Pagination with LIMIT/OFFSET
- Selective field retrieval where possible
- Avoid N+1 queries in list operations

---

## Deployment Configuration

### Environment Variables

```bash
# Service Configuration
SERVICE_NAME=order_service
SERVICE_HOST=0.0.0.0
SERVICE_PORT=8210
DEBUG=false
LOG_LEVEL=INFO

# PostgreSQL (via gRPC)
POSTGRES_HOST=isa-postgres-grpc
POSTGRES_PORT=50061

# NATS Event Bus
NATS_URL=nats://nats:4222

# Consul Service Discovery
CONSUL_ENABLED=true
CONSUL_HOST=consul
CONSUL_PORT=8500

# Service URLs (fallback if Consul unavailable)
PAYMENT_SERVICE_URL=http://payment:8207
WALLET_SERVICE_URL=http://wallet:8208
ACCOUNT_SERVICE_URL=http://account:8202
```

### Health Check Configuration

```yaml
# Kubernetes liveness probe
livenessProbe:
  httpGet:
    path: /health
    port: 8210
  initialDelaySeconds: 10
  periodSeconds: 10

# Kubernetes readiness probe
readinessProbe:
  httpGet:
    path: /health/detailed
    port: 8210
  initialDelaySeconds: 5
  periodSeconds: 5
```

### Resource Limits

```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "100m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

---

## Testing Strategy

### Test Layers

| Layer | Location | Purpose | Coverage Target |
|-------|----------|---------|-----------------|
| Unit | tests/unit/tdd/order_service/ | Model validation, factories | 75-85 tests |
| Component | tests/component/tdd/order_service/ | Service logic with mocks | 75-85 tests |
| Integration | tests/integration/tdd/order_service/ | Real HTTP + DB | 30-35 tests |
| API | tests/api/tdd/order_service/ | Full API contracts | 25-30 tests |
| Smoke | tests/smoke/order_service/ | E2E bash scripts | 15-18 tests |

### Dependency Injection for Testing

```python
# Production: Use factory with real dependencies
from .factory import create_order_service
service = create_order_service(config, event_bus)

# Testing: Inject mock dependencies directly
from .order_service import OrderService
service = OrderService(
    repository=mock_repository,
    event_bus=mock_event_bus
)
```

---

## Monitoring and Observability

### Metrics to Track
- Order creation rate
- Order completion rate
- Average order value
- Payment failure rate
- API response times
- Event processing lag

### Logging Format

```python
logger.info(f"Order created: {order_id} for user {user_id}")
logger.error(f"Failed to process payment for order {order_id}: {error}")
logger.warning(f"Order {order_id} expired without payment")
```

### Correlation IDs
- Request ID passed through headers
- Used in all log entries
- Enables distributed tracing

---

## Future Considerations

### Planned Enhancements
- Order splitting/merging
- Partial fulfillment support
- Multi-tenant order isolation
- Advanced fraud detection
- Order recommendation system

### Scalability Path
- Read replicas for queries
- Event sourcing for audit
- CQRS for complex queries
- Sharding by user_id
