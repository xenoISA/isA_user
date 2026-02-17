# Order Service - Product Requirements Document (PRD)

## Product Overview

The Order Service is a critical e-commerce microservice responsible for managing the complete order lifecycle in the isA platform. It handles order creation, payment coordination, status tracking, cancellations, refunds, and provides comprehensive order analytics. The service integrates with payment, wallet, subscription, and billing services to deliver a seamless transaction experience.

### Value Proposition

- **Centralized Order Management**: Single source of truth for all purchase transactions
- **Payment Orchestration**: Coordinates payment flows across multiple providers
- **Real-time Status Tracking**: Event-driven updates for order lifecycle
- **Multi-type Support**: Handles purchases, subscriptions, credits, and upgrades
- **Compliance Ready**: Maintains audit trails for financial regulations

---

## Target Users

### End Users
- **Consumers**: Users making purchases, subscriptions, or credit purchases
- **Subscribers**: Users managing recurring billing orders
- **Premium Users**: Users upgrading account tiers

### Internal Users
- **Customer Support**: Staff handling order inquiries and refunds
- **Finance Team**: Staff managing revenue reconciliation
- **Operations**: Staff monitoring order fulfillment

### System Users
- **Payment Service**: Processes payment transactions
- **Wallet Service**: Manages credit/token balances
- **Subscription Service**: Handles recurring billing
- **Notification Service**: Sends order status updates
- **Billing Service**: Generates invoices

---

## Epics and User Stories

### Epic 1: Order Creation
**Goal**: Enable users to create and track orders for various transaction types

**User Stories**:
- As a user, I want to create a purchase order so that I can buy products
- As a user, I want to create a credit purchase order so that I can add credits to my wallet
- As a user, I want to create a subscription order so that I can subscribe to premium features
- As a user, I want my order to auto-expire if I don't complete payment so that I'm not locked into stale orders
- As a user, I want to see my order details immediately after creation

### Epic 2: Order Lifecycle Management
**Goal**: Provide complete order status management and transitions

**User Stories**:
- As a user, I want to view my order status in real-time so that I know if payment succeeded
- As a user, I want to cancel my pending order so that I can change my mind before payment
- As a user, I want to receive notifications when my order status changes
- As a system, I want to auto-complete orders when payment succeeds
- As a system, I want to mark orders as failed when payment fails

### Epic 3: Payment Integration
**Goal**: Seamlessly coordinate with payment processing

**User Stories**:
- As a user, I want my order linked to my payment so that I can track the transaction
- As a user, I want automatic order completion when my payment clears
- As a system, I want to process payment.completed events to update order status
- As a system, I want to handle payment failures gracefully
- As a system, I want to coordinate refunds through the payment service

### Epic 4: Order Queries and Search
**Goal**: Enable efficient order retrieval and search

**User Stories**:
- As a user, I want to list all my orders with pagination
- As a user, I want to filter orders by status, type, or date range
- As a user, I want to search orders by order ID or type
- As support staff, I want to find orders by user or payment reference
- As an admin, I want to view order statistics for reporting

### Epic 5: Refund and Cancellation
**Goal**: Handle order cancellations and refund processing

**User Stories**:
- As a user, I want to cancel my order before payment completion
- As a user, I want to request a refund for completed orders
- As a system, I want to process refunds to the original payment method
- As a system, I want to restore wallet credits on credit order refunds
- As support staff, I want to process customer refund requests

### Epic 6: Cross-Service Integration
**Goal**: Maintain consistency across the microservice ecosystem

**User Stories**:
- As a system, I want to handle user deletion by cancelling pending orders
- As a system, I want to track subscription orders from subscription events
- As a system, I want to fulfill credit orders when wallet is updated
- As a system, I want to publish events for order lifecycle changes

### Epic 7: Analytics and Reporting
**Goal**: Provide order metrics and business intelligence

**User Stories**:
- As a finance user, I want to see total revenue by currency
- As an admin, I want to view order counts by status
- As an admin, I want to see order volume trends (24h, 7d, 30d)
- As a product manager, I want to see order breakdown by type

---

## API Surface Documentation

### Health Endpoints

#### GET /health
- **Description**: Basic service health check
- **Auth Required**: No
- **Request**: None
- **Response**:
  ```json
  {
    "status": "healthy",
    "service": "order_service",
    "port": 8210,
    "version": "1.0.0",
    "timestamp": "2024-01-15T10:30:00Z"
  }
  ```
- **Error Codes**: 500 (Service Unavailable)

#### GET /health/detailed
- **Description**: Detailed health with database connectivity
- **Auth Required**: No
- **Response**:
  ```json
  {
    "service": "order_service",
    "status": "operational",
    "port": 8210,
    "version": "1.0.0",
    "database_connected": true,
    "timestamp": "2024-01-15T10:30:00Z"
  }
  ```

### Order Management Endpoints

#### POST /api/v1/orders
- **Description**: Create a new order
- **Auth Required**: Yes
- **Request Schema**:
  ```json
  {
    "user_id": "user_abc123",
    "order_type": "purchase|subscription|credit_purchase|premium_upgrade",
    "total_amount": 99.99,
    "currency": "USD",
    "payment_intent_id": "pi_xxx",
    "subscription_id": "sub_xxx",
    "wallet_id": "wallet_xxx",
    "items": [
      {
        "product_id": "prod_001",
        "name": "Premium Plan",
        "quantity": 1,
        "unit_price": 99.99
      }
    ],
    "metadata": {},
    "expires_in_minutes": 30
  }
  ```
- **Response Schema**:
  ```json
  {
    "success": true,
    "order": {
      "order_id": "order_abc123def456",
      "user_id": "user_abc123",
      "order_type": "purchase",
      "status": "pending",
      "total_amount": 99.99,
      "currency": "USD",
      "payment_status": "pending",
      "items": [...],
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z",
      "expires_at": "2024-01-15T11:00:00Z"
    },
    "message": "Order created successfully"
  }
  ```
- **Error Codes**: 400 (Validation), 401 (Unauthorized), 500 (Server Error)

#### GET /api/v1/orders
- **Description**: List orders with filtering and pagination
- **Auth Required**: Yes
- **Query Parameters**:
  - `page` (int, default: 1): Page number
  - `page_size` (int, default: 50, max: 100): Items per page
  - `user_id` (string, optional): Filter by user
  - `order_type` (string, optional): Filter by type
  - `status` (string, optional): Filter by status
  - `payment_status` (string, optional): Filter by payment status
  - `start_date` (datetime, optional): Start date filter
  - `end_date` (datetime, optional): End date filter
- **Response Schema**:
  ```json
  {
    "orders": [...],
    "total_count": 150,
    "page": 1,
    "page_size": 50,
    "has_next": true
  }
  ```
- **Error Codes**: 400 (Invalid params), 401 (Unauthorized), 500 (Server Error)

#### GET /api/v1/orders/{order_id}
- **Description**: Get order details by ID
- **Auth Required**: Yes
- **Path Parameters**:
  - `order_id` (string): Order ID
- **Response Schema**:
  ```json
  {
    "order_id": "order_abc123def456",
    "user_id": "user_abc123",
    "order_type": "purchase",
    "status": "completed",
    "total_amount": 99.99,
    "currency": "USD",
    "payment_status": "completed",
    "payment_intent_id": "pi_xxx",
    "items": [...],
    "metadata": {},
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:35:00Z",
    "completed_at": "2024-01-15T10:35:00Z"
  }
  ```
- **Error Codes**: 401 (Unauthorized), 404 (Not Found), 500 (Server Error)

#### PUT /api/v1/orders/{order_id}
- **Description**: Update order details
- **Auth Required**: Yes
- **Request Schema**:
  ```json
  {
    "status": "processing",
    "payment_status": "processing",
    "payment_intent_id": "pi_xxx",
    "metadata": {"key": "value"}
  }
  ```
- **Response Schema**:
  ```json
  {
    "success": true,
    "order": {...},
    "message": "Order updated successfully"
  }
  ```
- **Error Codes**: 400 (Validation), 401 (Unauthorized), 404 (Not Found), 500 (Server Error)

#### POST /api/v1/orders/{order_id}/cancel
- **Description**: Cancel an order
- **Auth Required**: Yes
- **Request Schema**:
  ```json
  {
    "reason": "User requested cancellation",
    "refund_amount": 99.99
  }
  ```
- **Response Schema**:
  ```json
  {
    "success": true,
    "message": "Order cancelled successfully"
  }
  ```
- **Error Codes**: 400 (Invalid state), 401 (Unauthorized), 404 (Not Found), 500 (Server Error)

#### POST /api/v1/orders/{order_id}/complete
- **Description**: Complete an order after payment confirmation
- **Auth Required**: Yes
- **Request Schema**:
  ```json
  {
    "payment_confirmed": true,
    "transaction_id": "txn_xxx",
    "credits_added": 100.00
  }
  ```
- **Response Schema**:
  ```json
  {
    "success": true,
    "message": "Order completed successfully"
  }
  ```
- **Error Codes**: 400 (Payment not confirmed), 401 (Unauthorized), 404 (Not Found), 500 (Server Error)

### Search and Analytics Endpoints

#### GET /api/v1/orders/search
- **Description**: Search orders by query
- **Auth Required**: Yes
- **Query Parameters**:
  - `query` (string, required): Search query
  - `limit` (int, default: 50): Max results
  - `user_id` (string, optional): Filter by user
  - `include_cancelled` (bool, default: false): Include cancelled orders
- **Response Schema**:
  ```json
  {
    "orders": [...],
    "count": 10,
    "query": "order_abc"
  }
  ```
- **Error Codes**: 400 (Missing query), 401 (Unauthorized), 500 (Server Error)

#### GET /api/v1/orders/statistics
- **Description**: Get order statistics
- **Auth Required**: Yes
- **Response Schema**:
  ```json
  {
    "total_orders": 1500,
    "orders_by_status": {
      "pending": 50,
      "processing": 20,
      "completed": 1400,
      "failed": 15,
      "cancelled": 10,
      "refunded": 5
    },
    "orders_by_type": {
      "purchase": 800,
      "subscription": 500,
      "credit_purchase": 150,
      "premium_upgrade": 50
    },
    "total_revenue": 149500.00,
    "revenue_by_currency": {
      "USD": 149500.00
    },
    "avg_order_value": 99.67,
    "recent_orders_24h": 50,
    "recent_orders_7d": 300,
    "recent_orders_30d": 1200
  }
  ```
- **Error Codes**: 401 (Unauthorized), 500 (Server Error)

### Integration Endpoints

#### GET /api/v1/payments/{payment_intent_id}/orders
- **Description**: Get orders by payment intent
- **Auth Required**: Yes
- **Response Schema**:
  ```json
  {
    "orders": [...],
    "payment_intent_id": "pi_xxx",
    "count": 1
  }
  ```
- **Error Codes**: 401 (Unauthorized), 500 (Server Error)

#### GET /api/v1/subscriptions/{subscription_id}/orders
- **Description**: Get orders by subscription
- **Auth Required**: Yes
- **Response Schema**:
  ```json
  {
    "orders": [...],
    "subscription_id": "sub_xxx",
    "count": 12
  }
  ```
- **Error Codes**: 401 (Unauthorized), 500 (Server Error)

#### GET /api/v1/order/info
- **Description**: Get service information
- **Auth Required**: Yes
- **Response Schema**:
  ```json
  {
    "service": "order_service",
    "version": "1.0.0",
    "port": 8210,
    "status": "operational",
    "capabilities": {
      "order_management": true,
      "payment_integration": true,
      "wallet_integration": true,
      "transaction_recording": true,
      "order_analytics": true
    }
  }
  ```

---

## Functional Requirements

### FR-001: Order Creation
- System MUST create orders with unique order_id
- System MUST validate required fields (user_id, order_type, total_amount)
- System MUST set initial status to PENDING

### FR-002: Order Type Validation
- System MUST require wallet_id for CREDIT_PURCHASE orders
- System MUST require subscription_id for SUBSCRIPTION orders
- System MUST reject invalid order_type values

### FR-003: Amount Validation
- System MUST reject zero or negative amounts
- System MUST maintain decimal precision
- System MUST validate currency codes

### FR-004: Order Status Management
- System MUST enforce valid state transitions
- System MUST prevent invalid status changes
- System MUST auto-update timestamps on changes

### FR-005: Order Cancellation
- System MUST only allow cancellation of PENDING/PROCESSING orders
- System MUST store cancellation reason
- System MUST process refunds when applicable

### FR-006: Order Completion
- System MUST require payment_confirmed=true for completion
- System MUST set completed_at timestamp
- System MUST add credits for CREDIT_PURCHASE orders

### FR-007: Order Listing
- System MUST support pagination with configurable page size
- System MUST support filtering by multiple criteria
- System MUST return total count for pagination

### FR-008: Order Search
- System MUST search by order_id, order_type, status
- System MUST support partial matching
- System MUST respect user isolation

### FR-009: Statistics Generation
- System MUST calculate accurate order counts
- System MUST calculate revenue totals per currency
- System MUST track recent order volumes

### FR-010: Event Integration
- System MUST publish events for all lifecycle changes
- System MUST handle incoming payment events
- System MUST maintain event idempotency

### FR-011: Payment Integration
- System MUST link orders to payment intents
- System MUST auto-complete on payment success
- System MUST mark failed on payment failure

### FR-012: Subscription Integration
- System MUST create orders from subscription events
- System MUST cancel orders on subscription cancellation
- System MUST track subscription_id reference

### FR-013: User Deletion Handling
- System MUST cancel pending orders on user deletion
- System MUST anonymize PII in historical orders
- System MUST maintain financial records

### FR-014: Order Expiration
- System MUST support configurable expiration times
- System MUST auto-expire unpaid orders
- System MUST publish expired events

### FR-015: Audit Trail
- System MUST log all order changes
- System MUST maintain creation/update timestamps
- System MUST preserve metadata history

---

## Non-Functional Requirements

### NFR-001: Performance - Response Time
- Order creation: < 500ms p95
- Order retrieval: < 200ms p95
- Order listing: < 500ms p95 (50 items)
- Statistics: < 1000ms p95

### NFR-002: Performance - Throughput
- Support 100 concurrent order creations
- Handle 1000 orders/minute at peak
- Process 50 events/second

### NFR-003: Availability
- 99.9% service availability
- Graceful degradation without event bus
- Health checks every 10 seconds

### NFR-004: Scalability
- Horizontal scaling support
- Stateless service design
- Database connection pooling

### NFR-005: Data Consistency
- ACID transactions for order operations
- Eventually consistent event processing
- Idempotent event handlers

### NFR-006: Security
- JWT authentication required for API
- User isolation enforced
- Input validation on all endpoints

### NFR-007: Observability
- Structured logging with correlation IDs
- Metrics for order operations
- Distributed tracing support

### NFR-008: Resilience
- Retry logic for external service calls
- Circuit breaker for payment service
- Graceful timeout handling

### NFR-009: Compliance
- Financial audit trail maintained
- GDPR data handling for user deletion
- PCI compliance for payment data

### NFR-010: Maintainability
- Dependency injection for testability
- Protocol-based interfaces
- Comprehensive test coverage

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Order Creation Success Rate | > 99% | Orders created / attempts |
| Payment Completion Rate | > 95% | Completed / created orders |
| Average Order Value | Track trend | Total revenue / order count |
| Order Cancellation Rate | < 5% | Cancelled / total orders |
| API Response Time (p95) | < 500ms | Latency metrics |
| Event Processing Lag | < 100ms | Event timestamp delta |
| System Uptime | 99.9% | Health check monitoring |
| Test Coverage | > 80% | Lines covered / total |

---

## Dependencies

### Upstream Services
- **Account Service**: User validation
- **Payment Service**: Payment processing
- **Wallet Service**: Credit management
- **Subscription Service**: Recurring billing

### Downstream Consumers
- **Notification Service**: Status updates
- **Billing Service**: Invoice generation
- **Analytics Service**: Reporting data
- **Fulfillment Service**: Delivery triggers

### Infrastructure
- **PostgreSQL**: Data persistence (via gRPC)
- **NATS**: Event messaging
- **Consul**: Service discovery
- **Redis**: Caching (optional)
