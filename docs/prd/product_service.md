# Product Service - Product Requirements Document (PRD)

## Product Overview

**Product Name**: Product Service
**Version**: 1.0.0
**Status**: Production
**Owner**: Platform Commerce Team
**Last Updated**: 2025-12-16

### Vision
Enable seamless monetization of platform services through flexible product catalog, pricing models, and subscription management that scales from individual users to enterprise organizations.

### Mission
Provide a centralized product and subscription management system that powers all commercial operations on the isA_user platform with usage-based billing and tiered subscriptions.

### Target Users
- **End Users**: Subscribe to plans, consume products, track usage
- **Developers**: Integrate product pricing, record usage from services
- **Administrators**: Manage product catalog, configure pricing
- **Billing Systems**: Query subscriptions, aggregate usage for invoicing

### Key Differentiators
1. **Flexible Pricing Models**: Support usage-based, subscription, freemium, and hybrid pricing
2. **Credit-Based System**: Platform credits (1 credit = $0.00001 USD) enable micro-transactions
3. **Real-Time Usage Tracking**: Record and query usage with millisecond granularity
4. **Subscription Lifecycle Management**: Full state machine for subscription status
5. **Event-Driven Integration**: NATS events for billing, wallet, and analytics synchronization

---

## Product Goals

### Primary Goals
1. **Product Catalog**: Manage 100+ products across 15 categories with <150ms query latency
2. **Subscription Management**: Support 10K+ active subscriptions with <500ms creation
3. **Usage Recording**: Process 1M+ usage records/day with <100ms recording latency
4. **Pricing Flexibility**: Support 5 pricing types with tiered volume discounts
5. **Event Integration**: 99.5%+ event publishing success rate

### Secondary Goals
1. **Self-Service**: Enable user subscription management without support intervention
2. **Analytics Ready**: Provide usage statistics for business intelligence
3. **Multi-Tenant**: Support organization-level subscriptions
4. **Audit Compliance**: Track all subscription and usage changes
5. **API Gateway Integration**: Validate product availability at request time

---

## Epics and User Stories

### Epic 1: Product Catalog Management

**Objective**: Enable comprehensive product discovery and pricing information

#### E1-US1: Browse Product Categories
**As a** user or developer
**I want to** browse product categories
**So that** I can discover available products by type

**Acceptance Criteria**:
- AC1: `GET /api/v1/product/categories` returns all categories
- AC2: Categories include id, name, description, parent_category_id
- AC3: Only active categories returned by default
- AC4: Response includes display_order for sorting
- AC5: Response time <100ms for 50 categories
- AC6: Categories support hierarchical nesting

**API Reference**: `GET /api/v1/product/categories`

**Example Response**:
```json
[
  {
    "category_id": "cat_ai_models",
    "name": "AI Models",
    "description": "Language models and inference APIs",
    "parent_category_id": null,
    "display_order": 1,
    "is_active": true
  }
]
```

#### E1-US2: List Products with Filtering
**As a** user
**I want to** list products with filters
**So that** I can find specific product types

**Acceptance Criteria**:
- AC1: `GET /api/v1/product/products` returns product list
- AC2: Filter by category_id (optional)
- AC3: Filter by product_type (optional, enum validation)
- AC4: Filter by is_active (default: true)
- AC5: Response includes full product details
- AC6: Response time <150ms for 100 products
- AC7: Invalid product_type returns 400 with error message

**API Reference**: `GET /api/v1/product/products?category_id={id}&product_type={type}&is_active=true`

**Example Response**:
```json
[
  {
    "product_id": "prod_claude_sonnet",
    "category_id": "cat_ai_models",
    "name": "Claude Sonnet",
    "description": "Anthropic Claude 3.5 Sonnet model",
    "product_type": "model_inference",
    "provider": "anthropic",
    "is_active": true,
    "is_public": true,
    "version": "3.5",
    "specifications": {
      "context_window": 200000,
      "max_output_tokens": 8192
    },
    "capabilities": ["text_generation", "code_generation", "analysis"]
  }
]
```

#### E1-US3: Get Product Details
**As a** developer
**I want to** get detailed product information
**So that** I can understand product capabilities and limitations

**Acceptance Criteria**:
- AC1: `GET /api/v1/product/products/{product_id}` returns single product
- AC2: Response includes specifications, capabilities, limitations
- AC3: Non-existent product returns 404
- AC4: Response time <50ms
- AC5: Includes service_endpoint if applicable
- AC6: Includes version and release_date

**API Reference**: `GET /api/v1/product/products/{product_id}`

#### E1-US4: Get Product Pricing
**As a** user
**I want to** view product pricing details
**So that** I can understand costs before using

**Acceptance Criteria**:
- AC1: `GET /api/v1/product/products/{product_id}/pricing` returns pricing
- AC2: Optional user_id for personalized pricing
- AC3: Optional subscription_id for plan-based discounts
- AC4: Response includes unit prices, free tier info
- AC5: Non-existent product returns 404
- AC6: Response time <100ms

**API Reference**: `GET /api/v1/product/products/{product_id}/pricing?user_id={id}&subscription_id={id}`

**Example Response**:
```json
{
  "product_id": "prod_claude_sonnet",
  "pricing_model_id": "pm_sonnet_usage",
  "pricing_type": "usage_based",
  "unit_type": "token",
  "input_unit_price": "0.000003",
  "output_unit_price": "0.000015",
  "free_tier_limit": "100000",
  "free_tier_period": "monthly",
  "currency": "CREDIT"
}
```

---

### Epic 2: Subscription Management

**Objective**: Enable full subscription lifecycle management

#### E2-US1: Create Subscription
**As a** user
**I want to** create a subscription to a service plan
**So that** I can access platform products

**Acceptance Criteria**:
- AC1: `POST /api/v1/product/subscriptions` creates subscription
- AC2: Validates user_id exists (via account client)
- AC3: Validates plan_id exists in service plans
- AC4: Sets status to ACTIVE by default
- AC5: Calculates current_period_end based on billing_cycle
- AC6: Publishes `subscription.created` event
- AC7: Response time <500ms
- AC8: Invalid plan_id returns 400 with error

**API Reference**: `POST /api/v1/product/subscriptions`

**Example Request**:
```json
{
  "user_id": "user_abc123",
  "plan_id": "plan_pro_monthly",
  "organization_id": null,
  "billing_cycle": "monthly",
  "metadata": {"source": "web_app"}
}
```

**Example Response**:
```json
{
  "subscription_id": "sub_xyz789",
  "user_id": "user_abc123",
  "plan_id": "plan_pro_monthly",
  "plan_tier": "pro",
  "status": "active",
  "billing_cycle": "monthly",
  "current_period_start": "2025-12-16T00:00:00Z",
  "current_period_end": "2026-01-15T00:00:00Z"
}
```

#### E2-US2: Get User Subscriptions
**As a** user
**I want to** view my subscriptions
**So that** I can manage my plans

**Acceptance Criteria**:
- AC1: `GET /api/v1/product/subscriptions/user/{user_id}` returns list
- AC2: Optional status filter
- AC3: Returns all subscription details
- AC4: Response time <100ms for 10 subscriptions
- AC5: Invalid status returns 400

**API Reference**: `GET /api/v1/product/subscriptions/user/{user_id}?status={status}`

#### E2-US3: Get Subscription Details
**As a** user
**I want to** view subscription details
**So that** I can see my current plan status

**Acceptance Criteria**:
- AC1: `GET /api/v1/product/subscriptions/{subscription_id}` returns details
- AC2: Includes current period, status, plan info
- AC3: Non-existent subscription returns 404
- AC4: Response time <50ms

**API Reference**: `GET /api/v1/product/subscriptions/{subscription_id}`

#### E2-US4: Update Subscription Status
**As an** administrator or system
**I want to** change subscription status
**So that** I can manage subscription lifecycle

**Acceptance Criteria**:
- AC1: `PUT /api/v1/product/subscriptions/{subscription_id}/status` updates status
- AC2: Validates status is valid SubscriptionStatus enum
- AC3: Non-existent subscription returns 404
- AC4: Publishes `subscription.status_changed` event
- AC5: Returns updated subscription
- AC6: Response time <100ms

**API Reference**: `PUT /api/v1/product/subscriptions/{subscription_id}/status`

**Example Request**:
```json
{
  "status": "canceled"
}
```

**Subscription Status Values**:
- `active`: Subscription in good standing
- `trialing`: Free trial period
- `past_due`: Payment failed, grace period
- `canceled`: User canceled
- `incomplete`: Setup not finished
- `incomplete_expired`: Setup expired
- `unpaid`: Payment required
- `paused`: Temporarily suspended

---

### Epic 3: Usage Tracking

**Objective**: Enable detailed product consumption tracking

#### E3-US1: Record Product Usage
**As a** backend service
**I want to** record product usage
**So that** consumption is tracked for billing

**Acceptance Criteria**:
- AC1: `POST /api/v1/product/usage/record` records usage
- AC2: Validates product exists and is active
- AC3: Validates subscription is ACTIVE if provided
- AC4: Records user_id, product_id, usage_amount required
- AC5: Optional session_id, request_id for tracing
- AC6: Publishes `product.usage.recorded` event
- AC7: Response time <100ms
- AC8: Returns usage confirmation with cost breakdown

**API Reference**: `POST /api/v1/product/usage/record`

**Example Request**:
```json
{
  "user_id": "user_abc123",
  "product_id": "prod_claude_sonnet",
  "usage_amount": 1500,
  "organization_id": null,
  "subscription_id": "sub_xyz789",
  "session_id": "sess_123",
  "request_id": "req_456",
  "usage_details": {
    "input_tokens": 1000,
    "output_tokens": 500,
    "model_version": "claude-sonnet-4-20250514"
  }
}
```

**Example Response**:
```json
{
  "success": true,
  "message": "Usage recorded successfully",
  "usage_record_id": "usage_789",
  "product": {"product_id": "prod_claude_sonnet", "name": "Claude Sonnet"},
  "recorded_amount": 1500,
  "timestamp": "2025-12-16T10:30:00Z"
}
```

#### E3-US2: Query Usage Records
**As a** user or administrator
**I want to** query usage history
**So that** I can analyze consumption patterns

**Acceptance Criteria**:
- AC1: `GET /api/v1/product/usage/records` returns usage list
- AC2: Filter by user_id, organization_id, subscription_id, product_id
- AC3: Filter by date range (start_date, end_date)
- AC4: Pagination with limit (default 100) and offset
- AC5: Response time <200ms for 100 records

**API Reference**: `GET /api/v1/product/usage/records?user_id={id}&start_date={date}&end_date={date}&limit=100&offset=0`

---

### Epic 4: Product Availability

**Objective**: Enable real-time product access validation

#### E4-US1: Check Product Availability
**As a** service
**I want to** check if a product is available for a user
**So that** I can enforce access control

**Acceptance Criteria**:
- AC1: `GET /api/v1/product/products/{product_id}/availability` checks availability
- AC2: Requires user_id query parameter
- AC3: Optional organization_id for org-level access
- AC4: Returns available: true/false with reason
- AC5: Non-existent product returns available: false
- AC6: Inactive product returns available: false with reason
- AC7: Response time <50ms

**API Reference**: `GET /api/v1/product/products/{product_id}/availability?user_id={id}&organization_id={id}`

**Example Response (Available)**:
```json
{
  "available": true,
  "product": {
    "product_id": "prod_claude_sonnet",
    "name": "Claude Sonnet",
    "is_active": true
  }
}
```

**Example Response (Unavailable)**:
```json
{
  "available": false,
  "reason": "Product is not active"
}
```

---

### Epic 5: Statistics and Analytics

**Objective**: Provide usage and service metrics

#### E5-US1: Get Usage Statistics
**As an** administrator
**I want to** view usage statistics
**So that** I can analyze consumption trends

**Acceptance Criteria**:
- AC1: `GET /api/v1/product/statistics/usage` returns aggregated stats
- AC2: Filter by user_id, organization_id, product_id
- AC3: Filter by date range (start_date, end_date)
- AC4: Returns totals, breakdowns, trends
- AC5: Response time <300ms

**API Reference**: `GET /api/v1/product/statistics/usage?user_id={id}&start_date={date}&end_date={date}`

#### E5-US2: Get Service Statistics
**As an** administrator
**I want to** view service health statistics
**So that** I can monitor system status

**Acceptance Criteria**:
- AC1: `GET /api/v1/product/statistics/service` returns service stats
- AC2: Includes product counts, subscription counts
- AC3: Includes usage record counts by time period
- AC4: Response time <200ms

**API Reference**: `GET /api/v1/product/statistics/service`

**Example Response**:
```json
{
  "service": "product_service",
  "statistics": {
    "total_products": 45,
    "active_subscriptions": 1250,
    "usage_records_24h": 15420,
    "usage_records_7d": 89530,
    "usage_records_30d": 312450
  },
  "timestamp": "2025-12-16T10:00:00Z"
}
```

---

### Epic 6: Event-Driven Integration

**Objective**: Synchronize state changes across platform services

#### E6-US1: Publish Subscription Created Event
**As** Product Service
**I want to** publish subscription.created events
**So that** billing and wallet services can initialize

**Acceptance Criteria**:
- AC1: Event published after successful subscription creation
- AC2: Payload includes subscription_id, user_id, plan_id, plan_tier
- AC3: Payload includes billing_cycle, status, period dates
- AC4: Event bus failure logged but doesn't block operation
- AC5: Subscribers: billing_service, wallet_service, notification_service

#### E6-US2: Publish Subscription Status Changed Event
**As** Product Service
**I want to** publish subscription.status_changed events
**So that** services can respond to status transitions

**Acceptance Criteria**:
- AC1: Event published after status update
- AC2: Payload includes old_status, new_status
- AC3: Payload includes subscription_id, user_id, plan_id
- AC4: Subscribers: billing_service, notification_service, session_service

#### E6-US3: Publish Product Usage Recorded Event
**As** Product Service
**I want to** publish product.usage.recorded events
**So that** billing can aggregate usage

**Acceptance Criteria**:
- AC1: Event published after usage recording
- AC2: Payload includes usage_record_id, user_id, product_id, usage_amount
- AC3: Payload includes session_id, request_id for tracing
- AC4: Subscribers: billing_service, wallet_service, analytics_service

#### E6-US4: Handle Payment Events
**As** Product Service
**I want to** handle payment.completed events
**So that** subscription status reflects payment result

**Acceptance Criteria**:
- AC1: Subscribe to `payment_service.payment.completed`
- AC2: If payment failed, update subscription to PAST_DUE
- AC3: Log event handling for debugging

#### E6-US5: Handle User Deleted Events
**As** Product Service
**I want to** handle user.deleted events
**So that** subscriptions are cleaned up

**Acceptance Criteria**:
- AC1: Subscribe to `account_service.user.deleted`
- AC2: Cancel all user subscriptions
- AC3: Log cleanup actions

---

## API Surface Documentation

### Base URL
- **Development**: `http://localhost:8215`
- **Staging**: `https://staging-product.isa.ai`
- **Production**: `https://product.isa.ai`

### API Version
All endpoints prefixed with `/api/v1/`

### Authentication
- **Current**: Handled by API Gateway (JWT validation)
- **Header**: `Authorization: Bearer <token>`
- **User Context**: user_id extracted from JWT claims or query parameter

### Core Endpoints Summary

| Method | Endpoint | Purpose | Response Time |
|--------|----------|---------|---------------|
| GET | `/api/v1/product/categories` | List categories | <100ms |
| GET | `/api/v1/product/products` | List products | <150ms |
| GET | `/api/v1/product/products/{id}` | Get product | <50ms |
| GET | `/api/v1/product/products/{id}/pricing` | Get pricing | <100ms |
| GET | `/api/v1/product/products/{id}/availability` | Check availability | <50ms |
| POST | `/api/v1/product/subscriptions` | Create subscription | <500ms |
| GET | `/api/v1/product/subscriptions/user/{id}` | User subscriptions | <100ms |
| GET | `/api/v1/product/subscriptions/{id}` | Get subscription | <50ms |
| PUT | `/api/v1/product/subscriptions/{id}/status` | Update status | <100ms |
| POST | `/api/v1/product/usage/record` | Record usage | <100ms |
| GET | `/api/v1/product/usage/records` | Query usage | <200ms |
| GET | `/api/v1/product/statistics/usage` | Usage stats | <300ms |
| GET | `/api/v1/product/statistics/service` | Service stats | <200ms |
| GET | `/api/v1/product/info` | Service info | <20ms |
| GET | `/health` | Health check | <20ms |

### HTTP Status Codes
- `200 OK`: Successful operation
- `201 Created`: New subscription created
- `400 Bad Request`: Validation error (invalid enum, missing required)
- `404 Not Found`: Product/subscription not found
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Database unavailable

---

## Functional Requirements

### FR-1: Product Catalog
System SHALL maintain product catalog with categories, products, and pricing models

### FR-2: Product Types
System SHALL support 14 product types: model, model_inference, storage, storage_minio, agent, agent_execution, mcp_tool, mcp_service, api_service, api_gateway, notification, computation, data_processing, integration

### FR-3: Pricing Types
System SHALL support 5 pricing types: usage_based, subscription, one_time, freemium, hybrid

### FR-4: Subscription Lifecycle
System SHALL support subscription states: active, trialing, past_due, canceled, incomplete, incomplete_expired, unpaid, paused

### FR-5: Usage Recording
System SHALL record product usage with user, product, amount, and tracing context

### FR-6: Event Publishing
System SHALL publish events for subscription.created, subscription.status_changed, product.usage.recorded

### FR-7: Event Handling
System SHALL handle events from payment_service, wallet_service, account_service

### FR-8: Availability Check
System SHALL validate product availability for users in real-time

### FR-9: Health Checks
System SHALL provide /health endpoint for infrastructure monitoring

---

## Non-Functional Requirements

### NFR-1: Performance
- **Category List**: <100ms (p95)
- **Product List**: <150ms (p95)
- **Product Get**: <50ms (p95)
- **Subscription Create**: <500ms (p95)
- **Usage Record**: <100ms (p95)
- **Health Check**: <20ms (p99)

### NFR-2: Availability
- **Uptime**: 99.9% (excluding planned maintenance)
- **Database Failover**: Automatic with <30s recovery
- **Graceful Degradation**: Event failures don't block operations
- **Client Validation**: Fail-open for testing environments

### NFR-3: Scalability
- **Concurrent Requests**: 500+ concurrent requests
- **Products**: 1000+ products supported
- **Subscriptions**: 100K+ subscriptions supported
- **Usage Records**: 10M+ records/month
- **Database Connections**: Pooled with max 100 connections

### NFR-4: Data Integrity
- **ACID Transactions**: All mutations wrapped in PostgreSQL transactions
- **Enum Validation**: All enums validated at API boundary
- **Validation**: Pydantic models validate all inputs
- **Audit Trail**: Created/updated timestamps on all entities

### NFR-5: Security
- **Authentication**: JWT validation by API Gateway
- **Authorization**: User-scoped subscription access
- **Input Sanitization**: SQL injection prevention via parameterized queries
- **Enum Validation**: Invalid values rejected with 400

### NFR-6: Observability
- **Structured Logging**: JSON logs for all operations
- **Event Tracing**: session_id, request_id in usage records
- **Health Monitoring**: Database connectivity checked
- **Error Logging**: All exceptions logged with context

---

## Dependencies

### External Services

1. **PostgreSQL gRPC Service**: Product and subscription data storage
   - Host: `isa-postgres-grpc:50061`
   - Schema: `isa_core`
   - Tables: `products`, `product_categories`, `pricing_models`, `service_plans`, `user_subscriptions`, `product_usage_records`
   - SLA: 99.9% availability

2. **NATS Event Bus**: Event publishing and subscription
   - Host: `isa-nats:4222`
   - Subjects: `product_service.subscription.created`, `product_service.subscription.status_changed`, `product_service.product.usage.recorded`
   - SLA: 99.9% availability

3. **Consul**: Service discovery and health checks
   - Host: `localhost:8500`
   - Service Name: `product_service`
   - Health Check: HTTP `/health`
   - SLA: 99.9% availability

4. **Account Service** (Optional): User validation
   - Validates user existence before subscription creation
   - Fail-open for testing

5. **Organization Service** (Optional): Organization validation
   - Validates organization for org-level subscriptions
   - Fail-open for testing

### Internal Dependencies
- **core.config_manager**: Configuration management
- **core.logger**: Structured logging
- **core.nats_client**: Event bus client
- **isa_common.consul_client**: Service registration
- **isa_common.AsyncPostgresClient**: Database client

---

## Success Criteria

### Phase 1: Core Functionality (Complete)
- [x] Product catalog API working
- [x] Subscription CRUD functional
- [x] Usage recording implemented
- [x] PostgreSQL storage stable
- [x] Health checks implemented

### Phase 2: Event Integration (Complete)
- [x] Subscription events publishing
- [x] Usage events publishing
- [x] Payment event handling
- [x] User deleted event handling
- [x] Consul registration working

### Phase 3: Production Hardening (Current)
- [ ] Comprehensive test coverage (Unit, Component, Integration, API, Smoke)
- [ ] DI pattern compliance (protocols.py, factory.py)
- [ ] Performance benchmarks met
- [ ] Monitoring and alerting setup

### Phase 4: Scale and Optimize (Future)
- [ ] Subscription tier management UI
- [ ] Cost definition admin API
- [ ] Usage quota enforcement
- [ ] Bulk operations API
- [ ] Advanced analytics

---

## Out of Scope

The following are explicitly NOT included in this release:

1. **Payment Processing**: Handled by payment_service
2. **Credit Balance**: Handled by wallet_service
3. **Invoice Generation**: Handled by billing_service
4. **User Identity**: Handled by account_service
5. **Organization Management**: Handled by organization_service
6. **Real-time Quota Enforcement**: Future feature

---

## Appendix: Request/Response Examples

### 1. Create Subscription

**Request**:
```bash
curl -X POST http://localhost:8215/api/v1/product/subscriptions \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_abc123",
    "plan_id": "plan_pro_monthly",
    "billing_cycle": "monthly"
  }'
```

**Response** (201 Created):
```json
{
  "subscription_id": "sub_xyz789",
  "user_id": "user_abc123",
  "plan_id": "plan_pro_monthly",
  "plan_tier": "pro",
  "status": "active",
  "billing_cycle": "monthly",
  "current_period_start": "2025-12-16T00:00:00Z",
  "current_period_end": "2026-01-15T00:00:00Z"
}
```

### 2. Record Usage

**Request**:
```bash
curl -X POST http://localhost:8215/api/v1/product/usage/record \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_abc123",
    "product_id": "prod_claude_sonnet",
    "usage_amount": 1500,
    "session_id": "sess_123",
    "usage_details": {"input_tokens": 1000, "output_tokens": 500}
  }'
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Usage recorded successfully",
  "usage_record_id": "usage_789",
  "recorded_amount": 1500,
  "timestamp": "2025-12-16T10:30:00Z"
}
```

### 3. Check Product Availability

**Request**:
```bash
curl -X GET "http://localhost:8215/api/v1/product/products/prod_claude_sonnet/availability?user_id=user_abc123"
```

**Response** (200 OK):
```json
{
  "available": true,
  "product": {
    "product_id": "prod_claude_sonnet",
    "name": "Claude Sonnet",
    "is_active": true
  }
}
```

---

**Document Version**: 1.0
**Last Updated**: 2025-12-16
**Maintained By**: Product Service Product Team
**Related Documents**:
- Domain Context: docs/domain/product_service.md
- Design Doc: docs/design/product_service.md
- Data Contract: tests/contracts/product/data_contract.py
- Logic Contract: tests/contracts/product/logic_contract.md
