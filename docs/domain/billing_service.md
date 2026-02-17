# Billing Service - Domain Context

## Overview

The Billing Service is the **usage metering and cost processing engine** for the isA_user platform. It provides centralized billing orchestration, usage tracking, cost calculation, and quota management. Every billable action in the system flows through the Billing Service.

**Business Context**: Enable accurate, real-time usage tracking and billing for platform services. Billing Service owns the "how much and when to charge" - tracking usage metrics, calculating costs, managing quotas, and orchestrating payment processing.

**Core Value Proposition**: Transform raw service usage into actionable billing records with comprehensive cost calculation, supporting multiple billing methods (wallet deduction, credit consumption, subscription coverage, direct payment), enabling transparent billing and resource governance.

---

## Business Taxonomy

### Core Entities

#### 1. Billing Record
**Definition**: A unique record representing a billable event or usage occurrence in the system.

**Business Purpose**:
- Track individual usage events
- Calculate associated costs
- Record billing method used
- Support billing reconciliation
- Enable usage analytics

**Key Attributes**:
- Record ID (unique identifier)
- User ID (billed user)
- Service Type (session, storage, api_call, etc.)
- Usage Amount (quantity of usage)
- Unit Cost (cost per unit)
- Total Cost (calculated total)
- Currency (USD, EUR, etc.)
- Billing Method (wallet_deduction, credit_consumption, subscription_included, payment_charge)
- Status (pending, processing, completed, failed, refunded)
- Metadata (JSONB - additional context)
- Created At (billing timestamp)
- Processed At (completion timestamp)

**Billing Statuses**:
- **Pending**: Usage recorded, awaiting cost calculation
- **Processing**: Cost calculated, payment in progress
- **Completed**: Successfully billed and processed
- **Failed**: Billing failed (insufficient funds, etc.)
- **Refunded**: Billing reversed

#### 2. Billing Event
**Definition**: An atomic usage occurrence that triggers billing tracking.

**Business Purpose**:
- Capture granular usage data
- Support event-driven billing
- Enable real-time cost tracking
- Provide audit trail
- Feed analytics systems

**Key Attributes**:
- Event ID (unique identifier)
- User ID (event owner)
- Service Type (service generating event)
- Event Type (specific action type)
- Quantity (usage amount)
- Unit (measurement unit)
- Metadata (JSONB - event context)
- Timestamp (event occurrence time)
- Is Processed (billing status)

**Service Types**:
- **session**: AI conversation tokens
- **storage**: File storage bytes
- **api_call**: API request count
- **compute**: Processing time
- **bandwidth**: Data transfer
- **media**: Media processing

#### 3. Usage Aggregation
**Definition**: Aggregated usage metrics for a user over a time period.

**Business Purpose**:
- Summarize usage for billing cycles
- Support usage reporting
- Enable quota checking
- Optimize billing calculations
- Provide usage dashboards

**Key Attributes**:
- Aggregation ID
- User ID
- Period Start (aggregation window start)
- Period End (aggregation window end)
- Service Type
- Total Usage
- Total Cost
- Record Count
- Metadata

#### 4. Billing Quota
**Definition**: Usage limits and thresholds for a user or service.

**Business Purpose**:
- Enforce resource limits
- Prevent unexpected charges
- Support tiered service offerings
- Enable soft/hard limits
- Provide usage warnings

**Key Attributes**:
- Quota ID
- User ID
- Service Type
- Quota Type (soft_limit, hard_limit)
- Limit Value
- Current Usage
- Period Type (daily, weekly, monthly)
- Is Active
- Created At
- Updated At

**Quota Types**:
- **Soft Limit**: Warning threshold, usage continues
- **Hard Limit**: Block threshold, usage denied

#### 5. Billing Statistics
**Definition**: Aggregated metrics for billing service health and usage.

**Business Purpose**:
- Monitor revenue metrics
- Track billing success rates
- Support financial reporting
- Enable capacity planning
- Provide billing dashboards

**Key Metrics**:
- Total Revenue
- Total Records
- Records by Status
- Revenue by Service Type
- Average Transaction Value
- Billing Success Rate

---

## Domain Scenarios

### Scenario 1: Real-Time Usage Recording and Billing
**Actor**: Service (Session, Storage, etc.), User
**Trigger**: User consumes billable resource (tokens, storage, etc.)
**Flow**:
1. Source service publishes usage event (e.g., `session.tokens_used`)
2. Billing Service event handler receives usage event
3. Checks idempotency (event not already processed)
4. Calls `record_usage_and_bill()` with usage data:
   - user_id: User consuming resource
   - service_type: "session"
   - quantity: token count
   - unit_cost: price per token
5. Creates BillingRecord with status "pending"
6. Calculates billing cost (free tier, subscription check)
7. If billable amount > 0:
   - Checks user's wallet balance
   - Checks user's credit balance
   - Selects billing method (credit first, then wallet)
   - Processes deduction
8. Updates record status to "completed"
9. Publishes `billing.processed` event
10. Returns billing result

**Outcome**: Usage tracked, cost calculated, payment processed, events published

### Scenario 2: Cost Calculation with Free Tier
**Actor**: Billing Service
**Trigger**: Usage event with potential free tier coverage
**Flow**:
1. Billing Service receives usage to calculate cost
2. Calls `calculate_billing_cost()` with:
   - user_id
   - service_type
   - quantity
3. Fetches user's subscription status
4. If subscription active:
   - Checks subscription includes service type
   - Returns billing_method = "subscription_included", cost = 0
5. If no subscription:
   - Calculates free tier remaining
   - Applies free tier if available
   - Calculates billable amount = quantity - free_tier
6. Computes total_cost = billable_amount * unit_cost
7. Returns BillingCostResponse with:
   - original_amount
   - free_tier_applied
   - billable_amount
   - total_cost
   - billing_method

**Outcome**: Accurate cost calculated with free tier consideration

### Scenario 3: Quota Checking and Enforcement
**Actor**: User, Client Application
**Trigger**: Pre-flight check before resource consumption
**Flow**:
1. Client calls `POST /api/v1/billing/quota/check` with:
   - user_id
   - service_type
   - requested_amount
2. Billing Service fetches user's quota for service type
3. Calculates current_usage + requested_amount
4. Compares against soft_limit and hard_limit
5. Returns QuotaCheckResponse:
   - is_allowed: boolean
   - current_usage
   - limit
   - remaining
   - warning_message (if approaching limit)
6. If hard_limit exceeded:
   - Publishes `quota.exceeded` event
   - Returns is_allowed = false
7. Client proceeds or blocks based on response

**Outcome**: Resource consumption controlled, overage prevented

### Scenario 4: Billing Processing with Multiple Methods
**Actor**: Billing Service
**Trigger**: Billable usage needs payment processing
**Flow**:
1. Billing Service determines amount to charge
2. Checks billing method priority:
   - First: Credit balance (free credits)
   - Second: Wallet balance (prepaid funds)
   - Third: Direct payment (payment method on file)
3. For credit deduction:
   - Calls Wallet Service `deduct_credits()`
   - Records billing_method = "credit_consumption"
4. For wallet deduction:
   - Calls Wallet Service `deduct_balance()`
   - Records billing_method = "wallet_deduction"
5. For payment charge:
   - Calls Payment Service `charge()`
   - Records billing_method = "payment_charge"
6. If all methods fail:
   - Records status = "failed"
   - Publishes `billing.error` event
7. Updates billing record with method used
8. Returns processing result

**Outcome**: Payment processed using optimal method

### Scenario 5: Usage Statistics and Reporting
**Actor**: User, Dashboard
**Trigger**: User views billing statistics
**Flow**:
1. Client calls `GET /api/v1/billing/statistics`
2. Billing Service executes aggregate queries:
   - SUM(total_cost) for total revenue
   - COUNT(*) for total records
   - GROUP BY status for status breakdown
   - GROUP BY service_type for service breakdown
3. Calculates derived metrics:
   - Average transaction value
   - Success rate
4. Returns BillingStatisticsResponse
5. Dashboard displays billing analytics

**Outcome**: Comprehensive billing visibility

### Scenario 6: User Billing History
**Actor**: User
**Trigger**: User views billing history
**Flow**:
1. Client calls `GET /api/v1/billing/records?user_id={user_id}`
2. Billing Service queries records with filters:
   - user_id = provided
   - Optional: service_type filter
   - Optional: status filter
   - Optional: date range filter
3. Orders by created_at DESC
4. Applies pagination
5. Returns list of BillingRecordResponse
6. Client displays billing history

**Outcome**: User can review billing history

### Scenario 7: Session End Billing Finalization
**Actor**: Session Service (via event)
**Trigger**: User ends conversation session
**Flow**:
1. Session Service publishes `session.ended` event with:
   - session_id
   - user_id
   - total_tokens
   - total_cost
2. Billing Service event handler receives event
3. Creates final billing record for session
4. Processes any remaining unbilled usage
5. Updates usage aggregation
6. Logs billing completion

**Outcome**: Session usage fully billed

### Scenario 8: User Account Deletion Cascade
**Actor**: Account Service (via event)
**Trigger**: User deletes their account
**Flow**:
1. Account Service publishes `user.deleted` event
2. Billing Service event handler receives event
3. Fetches all pending billing records for user
4. Processes or cancels pending records
5. Archives billing history for compliance
6. Logs cleanup completion

**Outcome**: Billing data properly handled on account deletion

---

## Domain Events

### Published Events

#### 1. billing.usage_recorded (EventType.USAGE_RECORDED)
**Trigger**: Usage successfully recorded via Billing Service
**Source**: billing_service
**Payload**:
- record_id: Billing record identifier
- user_id: User identifier
- service_type: Type of service
- quantity: Usage amount
- timestamp: Recording timestamp

**Subscribers**:
- **Analytics Service**: Track usage patterns
- **Audit Service**: Log usage events

#### 2. billing.calculated (EventType.BILLING_CALCULATED)
**Trigger**: Cost calculation completed
**Source**: billing_service
**Payload**:
- record_id: Billing record identifier
- user_id: User identifier
- original_amount: Pre-discount amount
- billable_amount: Amount to charge
- total_cost: Calculated cost
- billing_method: Method determined
- timestamp: Calculation timestamp

**Subscribers**:
- **Analytics Service**: Track billing metrics
- **Notification Service**: Send cost notifications

#### 3. billing.processed (EventType.BILLING_PROCESSED)
**Trigger**: Billing successfully processed
**Source**: billing_service
**Payload**:
- record_id: Billing record identifier
- user_id: User identifier
- total_cost: Amount charged
- billing_method: Method used
- wallet_balance_after: Remaining balance (if wallet)
- credit_balance_after: Remaining credits (if credit)
- timestamp: Processing timestamp

**Subscribers**:
- **Wallet Service**: Update balance records
- **Notification Service**: Send payment confirmation
- **Analytics Service**: Track revenue

#### 4. billing.quota_exceeded (EventType.QUOTA_EXCEEDED)
**Trigger**: User exceeds quota limit
**Source**: billing_service
**Payload**:
- user_id: User identifier
- service_type: Service type
- quota_type: soft_limit or hard_limit
- limit_value: Quota limit
- current_usage: Current usage
- requested_amount: Amount that exceeded
- timestamp: Exceedance timestamp

**Subscribers**:
- **Notification Service**: Alert user of quota limit
- **Analytics Service**: Track quota events
- **Admin Service**: Alert admins of hard limit hits

#### 5. billing.error (EventType.BILLING_ERROR)
**Trigger**: Billing processing fails
**Source**: billing_service
**Payload**:
- record_id: Billing record identifier
- user_id: User identifier
- error_type: Type of error
- error_message: Error details
- billing_method_attempted: Method that failed
- timestamp: Error timestamp

**Subscribers**:
- **Notification Service**: Alert user of billing failure
- **Admin Service**: Alert admins of billing errors
- **Audit Service**: Log billing failures

### Subscribed Events

#### 1. session.tokens_used
**Source**: session_service
**Purpose**: Track token usage for billing
**Payload**:
- session_id
- user_id
- tokens_used
- cost_usd
- message_id
- timestamp

**Handler Action**: Records usage, calculates cost, processes billing

#### 2. order.completed
**Source**: order_service
**Purpose**: Record completed order billing
**Payload**:
- order_id
- user_id
- total_amount
- currency
- items
- timestamp

**Handler Action**: Creates billing record for order

#### 3. session.ended
**Source**: session_service
**Purpose**: Finalize session billing
**Payload**:
- session_id
- user_id
- total_tokens
- total_cost
- timestamp

**Handler Action**: Creates final session billing record

#### 4. user.deleted
**Source**: account_service
**Purpose**: Clean up billing data on user deletion
**Payload**:
- user_id
- timestamp

**Handler Action**: Archives billing records, cancels pending

---

## Core Concepts

### Billing Lifecycle
1. **Usage Recording**: Event captured, record created with "pending" status
2. **Cost Calculation**: Free tier, subscription, unit cost applied
3. **Method Selection**: Credit -> Wallet -> Payment priority
4. **Processing**: Deduction/charge executed
5. **Completion**: Status updated to "completed" or "failed"
6. **Reconciliation**: Periodic aggregation and reporting

### Billing Method Priority
```
1. Subscription (if includes service) -> billing_method = "subscription_included"
2. Free Tier (if remaining) -> Reduce billable amount
3. Credits (if available) -> billing_method = "credit_consumption"
4. Wallet (if balance) -> billing_method = "wallet_deduction"
5. Payment (if on file) -> billing_method = "payment_charge"
6. Fail (no methods) -> status = "failed"
```

### Cost Calculation Flow
```
User Usage Event
       ↓
Check Subscription → Included? → Return cost=0, method="subscription_included"
       ↓ No
Check Free Tier → Remaining? → Reduce billable_amount
       ↓
Calculate cost = billable_amount × unit_cost
       ↓
Return BillingCostResponse
```

### Quota Management
- **Soft Limits**: Warnings issued, usage continues
- **Hard Limits**: Usage blocked, operation fails
- **Period Types**: Daily, Weekly, Monthly resets
- **Per-Service**: Different limits for different services
- **Real-time Tracking**: Current usage maintained

### Event-Driven Billing
- Source services publish usage events (session.tokens_used, etc.)
- Billing Service subscribes and processes asynchronously
- Idempotency prevents duplicate billing
- Events published for downstream systems (notifications, analytics)

### Separation of Concerns
**Billing Service owns**:
- Usage recording and tracking
- Cost calculation logic
- Billing method orchestration
- Quota management
- Billing record persistence

**Billing Service does NOT own**:
- Wallet balance management (wallet_service)
- Payment processing (payment_service)
- Subscription management (subscription_service)
- Product pricing (product_service)
- User authentication (auth_service)

---

## Business Rules (High-Level)

### Usage Recording Rules
- **BR-USG-001**: User ID is required for usage recording
- **BR-USG-002**: Service type must be valid enum value
- **BR-USG-003**: Quantity must be positive
- **BR-USG-004**: Unit cost defaults to service-specific rate
- **BR-USG-005**: Event idempotency checked by event_id
- **BR-USG-006**: Duplicate events are ignored (no re-billing)

### Cost Calculation Rules
- **BR-CST-001**: Subscription coverage checked first
- **BR-CST-002**: Free tier applied before billable calculation
- **BR-CST-003**: Billable amount = quantity - free_tier_applied
- **BR-CST-004**: Total cost = billable_amount × unit_cost
- **BR-CST-005**: Zero cost if subscription includes service
- **BR-CST-006**: Currency defaults to USD if not specified

### Billing Method Rules
- **BR-MTD-001**: Credit balance checked before wallet
- **BR-MTD-002**: Wallet balance checked before payment
- **BR-MTD-003**: Partial deductions not supported (full amount or fail)
- **BR-MTD-004**: Billing method recorded on successful processing
- **BR-MTD-005**: Failed billing retries configurable

### Quota Rules
- **BR-QTA-001**: Quota checked before usage allowed
- **BR-QTA-002**: Soft limit triggers warning event
- **BR-QTA-003**: Hard limit blocks operation
- **BR-QTA-004**: Quotas reset per period_type
- **BR-QTA-005**: Admin can override quotas

### Processing Rules
- **BR-PRC-001**: Pending records processed sequentially
- **BR-PRC-002**: Failed records marked with error details
- **BR-PRC-003**: Successful records marked "completed"
- **BR-PRC-004**: Refunds create new record with "refunded" status
- **BR-PRC-005**: All processing publishes events

### Query Rules
- **BR-QRY-001**: List records requires user_id or admin role
- **BR-QRY-002**: Default pagination: page=1, page_size=50
- **BR-QRY-003**: Max page_size: 100
- **BR-QRY-004**: Records ordered by created_at DESC
- **BR-QRY-005**: Statistics require time range filter

### Event Publishing Rules
- **BR-EVT-001**: All billing operations publish events
- **BR-EVT-002**: Event publishing failures logged but don't block
- **BR-EVT-003**: Error events include error details
- **BR-EVT-004**: Events use ISO 8601 timestamps

---

## Billing Service in the Ecosystem

### Upstream Dependencies
- **Product Service**: Product pricing and tiers
- **Subscription Service**: Subscription status and coverage
- **Wallet Service**: Balance checking and deductions
- **Account Service**: User validation (fail-open)
- **PostgreSQL gRPC Service**: Persistent storage
- **NATS Event Bus**: Event publishing/subscribing
- **Consul**: Service discovery and health checks

### Downstream Consumers
- **Notification Service**: Billing alerts and confirmations
- **Analytics Service**: Revenue and usage metrics
- **Audit Service**: Billing activity logging
- **Admin Service**: Billing management dashboard

### Integration Patterns
- **Synchronous REST**: CRUD operations via FastAPI endpoints
- **Asynchronous Events**: NATS for usage events and notifications
- **Service Discovery**: Consul for dynamic service location
- **Protocol Buffers**: PostgreSQL gRPC communication
- **Health Checks**: `/health` and `/health/detailed` endpoints

### Dependency Injection
- **Repository Pattern**: BillingRepository for data access
- **Protocol Interfaces**: BillingRepositoryProtocol, EventBusProtocol
- **Client Protocols**: ProductClientProtocol, WalletClientProtocol, SubscriptionClientProtocol
- **Factory Pattern**: create_billing_service() for production instances
- **Mock-Friendly**: Protocols enable test doubles and mocks

---

## Success Metrics

### Revenue Metrics
- **Total Revenue**: Daily/weekly/monthly billing totals
- **Revenue by Service**: Breakdown by service type
- **Average Transaction Value**: Mean billing amount
- **Revenue Growth Rate**: Period-over-period growth

### Operational Metrics
- **Billing Success Rate**: % of records completed vs failed (target: >99%)
- **Processing Latency**: Time from usage to completion (target: <500ms)
- **Event Processing Latency**: Time to process usage events (target: <100ms)
- **Retry Rate**: % of records requiring retry

### Usage Metrics
- **Total Usage Volume**: By service type
- **Free Tier Utilization**: % of free tier consumed
- **Quota Utilization**: % of quotas approached/exceeded
- **Active Billing Users**: Users with billing activity

### System Metrics
- **Service Uptime**: Billing Service availability (target: 99.9%)
- **Database Connectivity**: PostgreSQL connection success rate
- **Event Publishing Success**: % of events successfully published
- **Client Service Availability**: Wallet, Subscription service health

---

## Glossary

**Billing Record**: Individual record of billable usage
**Billing Event**: Atomic usage occurrence triggering billing
**Usage Aggregation**: Summarized usage over a time period
**Billing Quota**: Usage limit for a user/service
**Billing Method**: Payment mechanism (wallet, credit, subscription, payment)
**Service Type**: Category of billable service (session, storage, etc.)
**Unit Cost**: Price per unit of usage
**Free Tier**: Included usage at no charge
**Soft Limit**: Warning threshold, usage continues
**Hard Limit**: Block threshold, usage denied
**Credit Consumption**: Payment using platform credits
**Wallet Deduction**: Payment using prepaid balance
**Subscription Included**: Usage covered by subscription
**Payment Charge**: Direct payment method charge
**Event Bus**: NATS messaging system for asynchronous events
**Idempotency**: Ensuring duplicate events don't cause duplicate billing

---

**Document Version**: 1.0
**Last Updated**: 2025-12-15
**Maintained By**: Billing Service Team
