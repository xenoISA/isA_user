# Billing Service - Product Requirements Document (PRD)

## Product Overview

The Billing Service provides usage metering, cost calculation, and billing orchestration for the isA_user platform, enabling accurate real-time billing with multiple payment methods, quota management, and comprehensive usage tracking.

**Product Goal**: Deliver a reliable, scalable billing system that accurately tracks resource usage, calculates costs with free tier and subscription consideration, and orchestrates payment processing across multiple billing methods.

**Key Capabilities**:
- Real-time usage recording and tracking
- Cost calculation with free tier and subscription support
- Multiple billing method orchestration (credits, wallet, payment)
- Quota management with soft/hard limits
- Billing statistics and reporting
- Event-driven integration for automatic billing

---

## Target Users

### Primary Users

#### 1. Platform Services (Internal API Consumers)
- **Description**: Session Service, Storage Service, and other services generating billable usage
- **Needs**: Real-time usage reporting, immediate billing feedback
- **Goals**: Report usage events and receive billing confirmation

#### 2. End Users (via Client Applications)
- **Description**: Individuals using platform services with billable resources
- **Needs**: Transparent billing, usage visibility, quota awareness
- **Goals**: Understand and control resource consumption and costs

### Secondary Users

#### 3. Finance and Business Teams
- **Description**: Revenue operations, financial analysts, product managers
- **Needs**: Revenue metrics, billing statistics, usage analytics
- **Goals**: Monitor revenue, analyze billing patterns, forecast growth

#### 4. Internal Services
- **Description**: Wallet Service, Subscription Service, Notification Service
- **Needs**: Billing events, processing results, quota alerts
- **Goals**: Process payments, update balances, send notifications

#### 5. Platform Administrators
- **Description**: DevOps, support team, billing operations
- **Needs**: Service health, error monitoring, billing debugging
- **Goals**: Ensure billing reliability, resolve billing issues

---

## Epics and User Stories

### Epic 1: Usage Recording and Tracking
**Goal**: Enable accurate, real-time usage tracking for all billable services

**User Stories**:
- As a session service, I want to report token usage so that billing is accurate
- As a storage service, I want to report storage consumption so that users are billed correctly
- As a user, I want duplicate events rejected so that I'm not double-charged
- As a billing system, I want idempotent event processing so that retries are safe
- As an admin, I want usage audit trails so that I can investigate billing issues

### Epic 2: Cost Calculation
**Goal**: Provide accurate cost calculation with free tier and subscription support

**User Stories**:
- As a user, I want free tier applied first so that I maximize free usage
- As a subscriber, I want subscription coverage checked so that included usage isn't charged
- As a user, I want pre-flight cost estimates so that I know costs before committing
- As a product manager, I want configurable pricing so that I can adjust rates
- As a system, I want cost breakdown in responses so that billing is transparent

### Epic 3: Billing Method Orchestration
**Goal**: Enable flexible payment processing across multiple billing methods

**User Stories**:
- As a user with credits, I want credits used first so that free credits aren't wasted
- As a user with wallet balance, I want wallet deducted before payment card so that prepaid funds are used
- As a user, I want billing method recorded so that I know how charges were paid
- As a system, I want graceful fallback so that billing succeeds when possible
- As an admin, I want billing method statistics so that I understand payment patterns

### Epic 4: Quota Management
**Goal**: Enable resource governance through usage quotas

**User Stories**:
- As a user, I want quota warnings so that I know when approaching limits
- As an admin, I want hard limits so that runaway usage is prevented
- As a user, I want quota visibility so that I can plan usage
- As a system, I want quota check endpoints so that I can pre-validate usage
- As an admin, I want per-service quotas so that limits are granular

### Epic 5: Statistics and Reporting
**Goal**: Provide comprehensive billing analytics and reporting

**User Stories**:
- As a user, I want billing history so that I can review past charges
- As finance, I want revenue statistics so that I can report financials
- As a product manager, I want usage by service type so that I understand product adoption
- As DevOps, I want billing success rates so that I can monitor health
- As an admin, I want filtering capabilities so that I can drill into specific data

### Epic 6: Event Integration
**Goal**: Enable event-driven billing for seamless service integration

**User Stories**:
- As a session service, I want events processed asynchronously so that latency is minimized
- As a billing service, I want to publish processing results so that dependent services react
- As a notification service, I want billing events so that users are notified of charges
- As an analytics service, I want billing events so that I can track revenue metrics

---

## API Surface Documentation

### Health Check Endpoints

#### GET /health
**Description**: Basic health check
**Auth Required**: No
**Request**: None
**Response**:
```json
{
  "status": "healthy",
  "service": "billing_service",
  "port": 8208,
  "version": "1.0.0",
  "timestamp": "2025-12-15T10:30:00Z"
}
```
**Error Codes**: 500 (Service Unavailable)

#### GET /health/detailed
**Description**: Detailed health check with database and client status
**Auth Required**: No
**Response**:
```json
{
  "service": "billing_service",
  "status": "operational",
  "port": 8208,
  "version": "1.0.0",
  "database_connected": true,
  "wallet_client_available": true,
  "subscription_client_available": true,
  "product_client_available": true,
  "timestamp": "2025-12-15T10:30:00Z"
}
```

### Usage Recording Endpoints

#### POST /api/v1/billing/usage/record
**Description**: Record usage and trigger billing
**Auth Required**: Yes
**Request Schema**:
```json
{
  "user_id": "user_12345",
  "service_type": "session",
  "quantity": 1500,
  "unit_cost": 0.0001,
  "currency": "USD",
  "metadata": {
    "session_id": "sess_abc123",
    "model": "gpt-4"
  }
}
```
**Response Schema**:
```json
{
  "record_id": "bill_xyz789",
  "user_id": "user_12345",
  "service_type": "session",
  "usage_amount": 1500,
  "unit_cost": 0.0001,
  "total_cost": 0.15,
  "currency": "USD",
  "billing_method": "wallet_deduction",
  "status": "completed",
  "metadata": {
    "session_id": "sess_abc123",
    "model": "gpt-4"
  },
  "created_at": "2025-12-15T10:30:00Z",
  "processed_at": "2025-12-15T10:30:01Z"
}
```
**Error Codes**: 400 (Bad Request), 402 (Payment Required - insufficient funds), 422 (Validation Error), 500 (Internal Error)
**Example**:
```bash
curl -X POST http://localhost:8208/api/v1/billing/usage/record \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_12345", "service_type": "session", "quantity": 1500, "unit_cost": 0.0001}'
```

### Cost Calculation Endpoints

#### POST /api/v1/billing/calculate
**Description**: Calculate billing cost with free tier and subscription consideration
**Auth Required**: Yes
**Request Schema**:
```json
{
  "user_id": "user_12345",
  "service_type": "session",
  "quantity": 1500,
  "unit_cost": 0.0001
}
```
**Response Schema**:
```json
{
  "user_id": "user_12345",
  "service_type": "session",
  "original_amount": 1500,
  "free_tier_applied": 500,
  "billable_amount": 1000,
  "unit_cost": 0.0001,
  "total_cost": 0.10,
  "currency": "USD",
  "billing_method": "wallet_deduction",
  "has_subscription": false,
  "subscription_covers": false
}
```
**Error Codes**: 400 (Bad Request), 422 (Validation Error), 500 (Internal Error)
**Example**:
```bash
curl -X POST http://localhost:8208/api/v1/billing/calculate \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_12345", "service_type": "session", "quantity": 1500}'
```

### Billing Processing Endpoints

#### POST /api/v1/billing/process
**Description**: Process a pending billing record
**Auth Required**: Yes
**Request Schema**:
```json
{
  "record_id": "bill_xyz789",
  "user_id": "user_12345"
}
```
**Response Schema**:
```json
{
  "record_id": "bill_xyz789",
  "status": "completed",
  "billing_method": "wallet_deduction",
  "amount_charged": 0.15,
  "wallet_balance_after": 9.85,
  "processed_at": "2025-12-15T10:30:01Z"
}
```
**Error Codes**: 400 (Bad Request), 402 (Payment Required), 404 (Record Not Found), 500 (Internal Error)

### Quota Management Endpoints

#### POST /api/v1/billing/quota/check
**Description**: Check if usage would exceed quota
**Auth Required**: Yes
**Request Schema**:
```json
{
  "user_id": "user_12345",
  "service_type": "session",
  "requested_amount": 5000
}
```
**Response Schema**:
```json
{
  "is_allowed": true,
  "user_id": "user_12345",
  "service_type": "session",
  "current_usage": 10000,
  "limit": 100000,
  "remaining": 90000,
  "requested_amount": 5000,
  "would_exceed": false,
  "warning_message": null
}
```
**Error Codes**: 400 (Bad Request), 422 (Validation Error), 500 (Internal Error)
**Example**:
```bash
curl -X POST http://localhost:8208/api/v1/billing/quota/check \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_12345", "service_type": "session", "requested_amount": 5000}'
```

#### GET /api/v1/billing/quota/{user_id}
**Description**: Get user's quota status
**Auth Required**: Yes
**Path Parameters**:
- user_id: User identifier
**Query Parameters**:
- service_type: (optional) Filter by service type
**Response Schema**:
```json
{
  "user_id": "user_12345",
  "quotas": [
    {
      "service_type": "session",
      "quota_type": "soft_limit",
      "limit_value": 100000,
      "current_usage": 10000,
      "period_type": "monthly",
      "period_start": "2025-12-01T00:00:00Z",
      "period_end": "2025-12-31T23:59:59Z",
      "is_active": true
    }
  ]
}
```
**Error Codes**: 404 (User Not Found), 500 (Internal Error)

### Statistics and Reporting Endpoints

#### GET /api/v1/billing/statistics
**Description**: Get billing statistics
**Auth Required**: Yes
**Query Parameters**:
- start_date: (optional) Filter start date
- end_date: (optional) Filter end date
- service_type: (optional) Filter by service type
**Response Schema**:
```json
{
  "total_revenue": 15420.50,
  "total_records": 45230,
  "records_by_status": {
    "completed": 44800,
    "failed": 330,
    "pending": 100
  },
  "revenue_by_service": {
    "session": 12000.00,
    "storage": 2500.50,
    "api_call": 920.00
  },
  "average_transaction_value": 0.34,
  "billing_success_rate": 99.27
}
```
**Error Codes**: 400 (Bad Request), 500 (Internal Error)
**Example**:
```bash
curl "http://localhost:8208/api/v1/billing/statistics?start_date=2025-12-01&end_date=2025-12-31"
```

#### GET /api/v1/billing/records
**Description**: List billing records
**Auth Required**: Yes
**Query Parameters**:
- user_id: (optional) Filter by user ID
- service_type: (optional) Filter by service type
- status: (optional) Filter by status
- start_date: (optional) Filter start date
- end_date: (optional) Filter end date
- page: (optional, default: 1) Page number
- page_size: (optional, default: 50, max: 100) Items per page
**Response Schema**:
```json
{
  "records": [
    {
      "record_id": "bill_xyz789",
      "user_id": "user_12345",
      "service_type": "session",
      "usage_amount": 1500,
      "total_cost": 0.15,
      "currency": "USD",
      "billing_method": "wallet_deduction",
      "status": "completed",
      "created_at": "2025-12-15T10:30:00Z",
      "processed_at": "2025-12-15T10:30:01Z"
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 50
}
```
**Error Codes**: 422 (Validation Error), 500 (Internal Error)
**Example**:
```bash
curl "http://localhost:8208/api/v1/billing/records?user_id=user_12345&page=1&page_size=20"
```

#### GET /api/v1/billing/records/{record_id}
**Description**: Get specific billing record
**Auth Required**: Yes
**Path Parameters**:
- record_id: Billing record identifier
**Response Schema**: Same as individual record in list response
**Error Codes**: 404 (Not Found), 500 (Internal Error)

---

## Functional Requirements

### Usage Recording

**FR-001**: System MUST record usage with user_id and service_type
- Accept quantity and unit_cost
- Generate unique record_id
- Initialize status as "pending"

**FR-002**: System MUST prevent duplicate billing
- Track processed event IDs
- Reject duplicate events with same idempotency key
- Return existing record for duplicates

**FR-003**: System MUST support multiple service types
- session, storage, api_call, compute, bandwidth, media
- Validate service_type is known enum value

### Cost Calculation

**FR-004**: System MUST check subscription coverage first
- If subscription includes service type, return cost = 0
- Set billing_method = "subscription_included"

**FR-005**: System MUST apply free tier before billing
- Track free tier usage per user per period
- Subtract free tier from billable amount
- Return free_tier_applied in response

**FR-006**: System MUST calculate total cost accurately
- total_cost = billable_amount × unit_cost
- Support configurable default unit costs per service
- Return full cost breakdown in response

### Billing Processing

**FR-007**: System MUST process billing with method priority
- Check credit balance first
- Check wallet balance second
- Attempt payment charge last
- Record billing_method used

**FR-008**: System MUST handle insufficient funds
- Return 402 Payment Required
- Set status = "failed"
- Include error details in response
- Publish billing.error event

**FR-009**: System MUST update balances on successful billing
- Deduct from credit/wallet via service calls
- Record balance after transaction
- Publish billing.processed event

### Quota Management

**FR-010**: System MUST check quotas before allowing usage
- Validate against soft and hard limits
- Return is_allowed boolean
- Include remaining quota in response

**FR-011**: System MUST support soft and hard limits
- Soft limit: warn but allow
- Hard limit: deny and return is_allowed = false
- Publish quota.exceeded event on hard limit

**FR-012**: System MUST track quota usage per period
- Support daily, weekly, monthly periods
- Reset usage at period boundaries
- Track current_usage accurately

### Statistics and Reporting

**FR-013**: System MUST provide billing statistics
- Total revenue, record counts
- Breakdown by status and service type
- Success rate calculation

**FR-014**: System MUST support filtering and pagination
- Filter by user_id, service_type, status, date range
- Support page and page_size parameters
- Return total count for pagination

### Event Publishing

**FR-015**: System MUST publish events for billing operations
- billing.usage_recorded on recording
- billing.calculated on cost calculation
- billing.processed on successful processing
- billing.error on failures
- quota.exceeded on hard limit hit

**FR-016**: System MUST subscribe to upstream events
- session.tokens_used for token billing
- order.completed for order billing
- session.ended for session finalization
- user.deleted for cleanup

---

## Non-Functional Requirements

### Performance

**NFR-001**: Usage recording MUST complete within 200ms (p95)

**NFR-002**: Cost calculation MUST complete within 100ms (p95)

**NFR-003**: Billing processing MUST complete within 500ms (p95)

**NFR-004**: Quota check MUST complete within 50ms (p95)

**NFR-005**: Service MUST handle 500 billing events per second

### Scalability

**NFR-006**: Service MUST scale horizontally behind load balancer

**NFR-007**: Database queries MUST use proper indexing on user_id, created_at

**NFR-008**: Event processing MUST be parallelizable

### Reliability

**NFR-009**: Service uptime MUST be 99.9%

**NFR-010**: Event publishing failures MUST NOT block billing operations

**NFR-011**: Client service unavailability MUST NOT crash service (fail-open)

**NFR-012**: Billing MUST be idempotent (retries safe)

### Data Integrity

**NFR-013**: Billing records MUST be immutable after completion

**NFR-014**: Balance deductions MUST be atomic

**NFR-015**: Quota tracking MUST be accurate to within 1%

### Security

**NFR-016**: All billing data MUST be isolated per user

**NFR-017**: Billing access MUST validate user ownership

**NFR-018**: Payment information MUST NOT be stored in billing service

---

## Success Metrics

### Revenue Metrics
- **Daily Revenue**: Total billing per day
- **Revenue by Service**: Breakdown by service type
- **Average Transaction Value**: Mean billing amount
- **Revenue Growth Rate**: Week-over-week, month-over-month

### Operational Metrics
- **Billing Success Rate**: % completed vs failed (target: >99%)
- **Processing Latency**: p50, p95, p99 billing time
- **Event Processing Lag**: Time from event to billing
- **Error Rate**: % of requests returning 5xx

### Usage Metrics
- **Total Usage Volume**: By service type
- **Free Tier Utilization**: % of free tier consumed
- **Quota Hit Rate**: % of users hitting quotas
- **Billing Method Distribution**: Credits vs wallet vs payment

### Business Metrics
- **Active Billing Users**: Users with billing activity
- **Billing per User**: Average revenue per user
- **Service Adoption**: Usage volume by service type

---

**Document Version**: 1.0
**Last Updated**: 2025-12-15
**Maintained By**: Billing Service Team
