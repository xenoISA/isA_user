# Credit Service - Domain Context

## Overview

The Credit Service is the **promotional credit and bonus management engine** for the isA Platform. It provides centralized credit lifecycle management, allocation, consumption tracking, and expiration handling. All promotional, bonus, referral, and subscription-allocated credits flow through the Credit Service.

**Business Context**: Enable flexible promotional credit systems that incentivize user acquisition, retention, and engagement. Credit Service owns "free money management" - tracking credit sources, managing expiration policies, handling allocation rules, and coordinating credit consumption with the billing system.

**Core Value Proposition**: Transform various promotional programs (referrals, sign-up bonuses, campaigns) into actionable credit balances with comprehensive lifecycle management, supporting multiple credit types with independent expiration policies, enabling transparent credit tracking and governance.

---

## Business Taxonomy

### Core Entities

#### 1. Credit Account
**Definition**: A ledger entry tracking credits of a specific type for a user or organization.

**Business Purpose**:
- Track credits by source type (promotional, bonus, referral, subscription)
- Maintain independent balances per credit type
- Enforce type-specific expiration policies
- Support credit audit and reconciliation
- Enable promotional analytics

**Key Attributes**:
- Account ID (unique identifier)
- User ID (credit owner)
- Organization ID (optional, for org-level credits)
- Credit Type (promotional, bonus, referral, subscription, compensation)
- Balance (current available credits)
- Total Allocated (lifetime credits received)
- Total Consumed (lifetime credits used)
- Total Expired (lifetime credits expired)
- Currency (CREDIT, USD equivalent tracking)
- Expiration Policy (policy governing this account)
- Is Active (account status)
- Created At (account creation timestamp)
- Updated At (last modification timestamp)

**Credit Types**:
- **promotional**: Marketing campaigns, seasonal offers
- **bonus**: Sign-up bonuses, achievement rewards
- **referral**: Referrer and referee rewards
- **subscription**: Monthly subscription credit allocations
- **compensation**: Customer service credits, refunds

#### 2. Credit Transaction
**Definition**: An immutable record of credit movement (allocation, consumption, expiration, transfer).

**Business Purpose**:
- Maintain complete audit trail
- Enable transaction reconciliation
- Support rollback and dispute resolution
- Provide analytics data
- Track credit lifecycle

**Key Attributes**:
- Transaction ID (unique identifier)
- Account ID (credit account reference)
- User ID (transaction owner)
- Transaction Type (allocate, consume, expire, transfer_in, transfer_out, adjust)
- Amount (credit quantity)
- Balance Before (pre-transaction balance)
- Balance After (post-transaction balance)
- Reference ID (external reference - campaign_id, billing_record_id, etc.)
- Reference Type (campaign, billing, refund, subscription, manual)
- Description (human-readable description)
- Metadata (JSONB - additional context)
- Created At (transaction timestamp)
- Expires At (when allocated credits expire)

**Transaction Types**:
- **allocate**: Credits added to account
- **consume**: Credits deducted for usage
- **expire**: Credits removed due to expiration
- **transfer_in**: Credits received from another account
- **transfer_out**: Credits sent to another account
- **adjust**: Administrative adjustment (positive or negative)

#### 3. Credit Campaign
**Definition**: A promotional program that allocates credits based on specific rules and conditions.

**Business Purpose**:
- Define promotional rules and limits
- Control credit distribution
- Track campaign effectiveness
- Manage budget constraints
- Enable A/B testing of promotions

**Key Attributes**:
- Campaign ID (unique identifier)
- Name (campaign name)
- Description (campaign details)
- Credit Type (type of credits allocated)
- Credit Amount (credits per allocation)
- Total Budget (maximum credits to allocate)
- Allocated Amount (credits already allocated)
- Remaining Budget (budget - allocated)
- Eligibility Rules (JSONB - who qualifies)
- Allocation Rules (JSONB - how/when to allocate)
- Start Date (campaign start)
- End Date (campaign end)
- Expiration Days (days until credits expire)
- Max Allocations Per User (limit per user)
- Is Active (campaign status)
- Created At
- Updated At

**Campaign Examples**:
- **Sign-up Bonus**: 1000 credits for new users
- **Referral Program**: 500 credits for referrer and referee
- **Holiday Promotion**: 2000 credits for December purchases
- **Loyalty Reward**: 100 credits per month for active users

#### 4. Credit Allocation
**Definition**: A record of credits allocated from a campaign to a user.

**Business Purpose**:
- Track campaign-to-user allocations
- Prevent duplicate allocations
- Support allocation limits
- Enable allocation analytics

**Key Attributes**:
- Allocation ID (unique identifier)
- Campaign ID (source campaign)
- User ID (recipient)
- Credit Account ID (target account)
- Amount (credits allocated)
- Status (pending, completed, failed, revoked)
- Expires At (credit expiration date)
- Allocated At (allocation timestamp)
- Metadata (JSONB - allocation context)

#### 5. Credit Balance Summary
**Definition**: Aggregated view of a user's credit status across all accounts.

**Business Purpose**:
- Provide unified balance view
- Support billing integration
- Enable balance alerts
- Show expiring credits

**Key Attributes**:
- User ID
- Total Balance (sum of all accounts)
- Available Balance (non-expired credits)
- Expiring Soon (credits expiring in 7 days)
- By Type (balance breakdown by credit type)
- Next Expiration (earliest expiration date)

---

## Domain Scenarios

### Scenario 1: New User Sign-up Bonus
**Actor**: New User, Account Service (via event)
**Trigger**: User completes registration
**Flow**:
1. Account Service publishes `user.created` event
2. Credit Service event handler receives event
3. Checks idempotency (user not already processed)
4. Finds active sign-up bonus campaign
5. Validates user eligibility:
   - Is new user (no previous allocations)
   - Campaign has remaining budget
   - Campaign is within date range
6. Creates Credit Account (type: bonus)
7. Creates Credit Transaction (type: allocate)
8. Creates Credit Allocation record
9. Updates campaign allocated_amount
10. Publishes `credit.allocated` event

**Outcome**: New user receives sign-up bonus credits

### Scenario 2: Referral Credit Allocation
**Actor**: Referrer User, Referee User
**Trigger**: Referee completes qualifying action (e.g., first purchase)
**Flow**:
1. Order Service publishes `order.completed` event with referral_code
2. Credit Service event handler receives event
3. Validates referral:
   - Referral code exists and is valid
   - Referee not already rewarded for this referral
   - Referrer is active user
4. For Referee:
   - Finds/creates referral credit account
   - Allocates referee bonus credits
   - Creates allocation record
5. For Referrer:
   - Finds/creates referral credit account
   - Allocates referrer bonus credits
   - Creates allocation record
6. Publishes `credit.referral.completed` event

**Outcome**: Both referrer and referee receive referral credits

### Scenario 3: Credit Consumption for Billing
**Actor**: Billing Service
**Trigger**: Usage billing calculation needs credit deduction
**Flow**:
1. Billing Service calls `POST /api/v1/credits/consume`
2. Request includes: user_id, amount, billing_record_id
3. Credit Service checks available credits:
   - Queries all active credit accounts for user
   - Orders by expiration (FIFO - first to expire, first to use)
4. If sufficient credits:
   - Creates consumption transactions (may span multiple accounts)
   - Updates account balances
   - Publishes `credit.consumed` event
   - Returns success with balance_after
5. If insufficient credits:
   - Returns available_credits and deficit
   - Billing Service proceeds with wallet/payment

**Outcome**: Credits consumed in FIFO order, billing record linked

### Scenario 4: Credit Expiration Processing
**Actor**: System (scheduled job)
**Trigger**: Daily expiration check cron
**Flow**:
1. Scheduler triggers expiration check
2. Credit Service queries transactions with:
   - expires_at <= NOW()
   - status = 'active'
3. For each expiring allocation:
   - Calculate remaining balance from that allocation
   - Create expire transaction
   - Update account balance
   - Update allocation status
4. Publishes `credit.expired` event for each expiration
5. Optionally sends notification via Notification Service

**Outcome**: Expired credits removed, users notified

### Scenario 5: Credit Balance Inquiry
**Actor**: User, Billing Service
**Trigger**: User views credit balance or billing pre-check
**Flow**:
1. Client calls `GET /api/v1/credits/balance?user_id={user_id}`
2. Credit Service queries:
   - All credit accounts for user
   - Aggregates balances by type
   - Calculates expiring_soon (7 days)
   - Finds next expiration date
3. Returns CreditBalanceSummary:
   - total_balance
   - available_balance
   - expiring_soon
   - by_type breakdown
   - next_expiration
4. Optionally warns if balance is low

**Outcome**: User sees comprehensive credit status

### Scenario 6: Subscription Credit Allocation
**Actor**: Subscription Service (via event)
**Trigger**: Monthly subscription renewal
**Flow**:
1. Subscription Service publishes `subscription.renewed` event
2. Credit Service event handler receives event
3. Checks subscription tier includes credits
4. Gets monthly credit amount from subscription plan
5. Creates/finds subscription credit account
6. Allocates monthly credits with 30-day expiration
7. Creates allocation record
8. Publishes `credit.subscription.allocated` event

**Outcome**: Subscriber receives monthly credit allocation

### Scenario 7: Credit Transfer Between Users
**Actor**: User (sender)
**Trigger**: User requests credit transfer
**Flow**:
1. Client calls `POST /api/v1/credits/transfer`
2. Request: from_user_id, to_user_id, amount, credit_type
3. Validates:
   - Sender has sufficient credits of type
   - Recipient exists and is active
   - Credit type allows transfers
4. Atomically:
   - Deducts from sender account (transfer_out)
   - Adds to recipient account (transfer_in)
   - Creates paired transactions
5. Publishes `credit.transferred` event

**Outcome**: Credits moved between users

### Scenario 8: Campaign Budget Exhausted
**Actor**: System
**Trigger**: Campaign reaches budget limit
**Flow**:
1. During allocation attempt
2. Credit Service checks remaining_budget
3. If remaining_budget < credit_amount:
   - Mark campaign as budget_exhausted
   - Publish `campaign.budget.exhausted` event
   - Return error to caller
4. If allocation would deplete budget:
   - Complete allocation
   - Check if budget now exhausted
   - Publish event if so

**Outcome**: Campaign stops allocating when budget depleted

---

## Domain Events

### Published Events

#### 1. credit.allocated (EventType.CREDIT_ALLOCATED)
**Trigger**: Credits successfully allocated to user
**Source**: credit_service
**Payload**:
- allocation_id: Allocation record ID
- user_id: Recipient user ID
- credit_type: Type of credit
- amount: Credits allocated
- campaign_id: Source campaign (if applicable)
- expires_at: Expiration date
- balance_after: New balance
- timestamp: Allocation timestamp

**Subscribers**:
- **notification_service**: Notify user of credits received
- **analytics_service**: Track promotional effectiveness

#### 2. credit.consumed (EventType.CREDIT_CONSUMED)
**Trigger**: Credits deducted for billing
**Source**: credit_service
**Payload**:
- transaction_id: Transaction ID
- user_id: User ID
- amount: Credits consumed
- billing_record_id: Related billing record
- balance_before: Previous balance
- balance_after: New balance
- timestamp: Consumption timestamp

**Subscribers**:
- **billing_service**: Confirm credit deduction
- **analytics_service**: Track credit usage

#### 3. credit.expired (EventType.CREDIT_EXPIRED)
**Trigger**: Credits expired due to expiration policy
**Source**: credit_service
**Payload**:
- transaction_id: Expiration transaction ID
- user_id: User ID
- amount: Credits expired
- credit_type: Type of expired credit
- balance_after: Remaining balance
- timestamp: Expiration timestamp

**Subscribers**:
- **notification_service**: Notify user of expired credits
- **analytics_service**: Track expiration metrics

#### 4. credit.transferred (EventType.CREDIT_TRANSFERRED)
**Trigger**: Credits transferred between users
**Source**: credit_service
**Payload**:
- transfer_id: Transfer identifier
- from_user_id: Sender user ID
- to_user_id: Recipient user ID
- amount: Credits transferred
- credit_type: Type of credit
- timestamp: Transfer timestamp

**Subscribers**:
- **notification_service**: Notify both users

#### 5. credit.expiring_soon (EventType.CREDIT_EXPIRING_SOON)
**Trigger**: Credits approaching expiration (7 days warning)
**Source**: credit_service
**Payload**:
- user_id: User ID
- amount: Credits expiring
- expires_at: Expiration date
- credit_type: Type of credit
- timestamp: Warning timestamp

**Subscribers**:
- **notification_service**: Warn user of upcoming expiration

#### 6. campaign.budget.exhausted (EventType.CAMPAIGN_BUDGET_EXHAUSTED)
**Trigger**: Campaign reaches budget limit
**Source**: credit_service
**Payload**:
- campaign_id: Campaign ID
- campaign_name: Campaign name
- total_budget: Original budget
- allocated_amount: Total allocated
- timestamp: Exhaustion timestamp

**Subscribers**:
- **notification_service**: Alert campaign managers
- **admin_service**: Dashboard alert

### Subscribed Events

#### 1. user.created
**Source**: account_service
**Purpose**: Allocate sign-up bonus credits
**Payload**:
- user_id
- email
- created_at
- referral_code (optional)

**Handler Action**: Check for sign-up campaigns, allocate bonus

#### 2. subscription.created / subscription.renewed
**Source**: subscription_service
**Purpose**: Allocate subscription credits
**Payload**:
- subscription_id
- user_id
- plan_id
- credits_included
- period_start
- period_end

**Handler Action**: Allocate monthly subscription credits

#### 3. order.completed
**Source**: order_service
**Purpose**: Process referral rewards
**Payload**:
- order_id
- user_id
- referral_code
- total_amount

**Handler Action**: Allocate referral credits if applicable

#### 4. billing.calculated
**Source**: billing_service
**Purpose**: Check credit availability for billing
**Payload**:
- billing_record_id
- user_id
- amount_to_charge
- service_type

**Handler Action**: Reserve or consume credits for billing

#### 5. user.deleted
**Source**: account_service
**Purpose**: Clean up credit data on account deletion
**Payload**:
- user_id
- timestamp

**Handler Action**: Archive credit accounts, cancel pending allocations

---

## Core Concepts

### Credit Lifecycle
1. **Allocation**: Credits added from campaign, subscription, or manual adjustment
2. **Available**: Credits ready for consumption (not expired)
3. **Consumption**: Credits deducted for service usage
4. **Expiration**: Credits removed after expiration date
5. **Archive**: Historical record maintained for audit

### Credit Priority (FIFO Expiration)
```
Credit Consumption Order:
1. Credits expiring soonest (FIFO by expires_at)
2. Within same expiration: oldest first (FIFO by created_at)
3. Within same date: by credit_type priority
   - compensation (highest - use first)
   - promotional
   - bonus
   - referral
   - subscription (lowest - preserve subscription value)
```

### Expiration Policies
```
Policy Types:
- fixed_days: Expire N days after allocation
- end_of_month: Expire at month end
- end_of_year: Expire at year end
- subscription_period: Expire with subscription period
- never: No expiration (rare, admin-only)
```

### Credit Account Isolation
- Each user has separate accounts per credit_type
- Organization-level accounts for B2B credits
- Accounts cannot go negative
- Consumption spans accounts via priority

### Campaign Management
- Campaigns define allocation rules and limits
- Budget tracking prevents over-allocation
- Eligibility rules filter qualified users
- Time-bounded with start/end dates

### Event-Driven Architecture
- Allocation triggered by user lifecycle events
- Consumption triggered by billing events
- Expiration triggered by scheduled jobs
- All actions publish events for downstream

### Separation of Concerns
**Credit Service owns**:
- Credit account lifecycle
- Credit type management
- Campaign and promotion rules
- Expiration policy enforcement
- Credit transaction history

**Credit Service does NOT own**:
- Wallet balance (wallet_service)
- Usage billing logic (billing_service)
- Payment processing (payment_service)
- Subscription management (subscription_service)
- User authentication (auth_service)

---

## Business Rules (High-Level)

### Credit Account Rules
- **BR-ACC-001**: Each user has one account per credit_type
- **BR-ACC-002**: Account balance cannot be negative
- **BR-ACC-003**: Inactive accounts reject all operations
- **BR-ACC-004**: Account creation requires valid user_id
- **BR-ACC-005**: Organization accounts require organization_id
- **BR-ACC-006**: Deleted user accounts are archived, not removed

### Allocation Rules
- **BR-ALC-001**: Allocation requires valid campaign or manual approval
- **BR-ALC-002**: Allocation amount must be positive
- **BR-ALC-003**: Campaign budget check before allocation
- **BR-ALC-004**: User eligibility check before allocation
- **BR-ALC-005**: Duplicate allocations prevented by idempotency
- **BR-ALC-006**: Expiration date set based on policy

### Consumption Rules
- **BR-CON-001**: Consumption requires sufficient balance
- **BR-CON-002**: FIFO expiration order for consumption
- **BR-CON-003**: Consumption amount must be positive
- **BR-CON-004**: Billing reference required for usage consumption
- **BR-CON-005**: Partial consumption supported (use what's available)
- **BR-CON-006**: Atomic consumption across multiple accounts

### Expiration Rules
- **BR-EXP-001**: Expired credits cannot be consumed
- **BR-EXP-002**: Expiration processing runs daily
- **BR-EXP-003**: Warning sent 7 days before expiration
- **BR-EXP-004**: Expired credits logged for audit
- **BR-EXP-005**: Expiration creates transaction record

### Campaign Rules
- **BR-CMP-001**: Campaign requires start_date <= end_date
- **BR-CMP-002**: Campaign budget must be positive
- **BR-CMP-003**: Inactive campaigns cannot allocate
- **BR-CMP-004**: Budget-exhausted campaigns auto-deactivate
- **BR-CMP-005**: Campaign eligibility validated per allocation
- **BR-CMP-006**: Max allocations per user enforced

### Transfer Rules
- **BR-TRF-001**: Transfer requires sufficient balance
- **BR-TRF-002**: Transfer requires active recipient
- **BR-TRF-003**: Self-transfer prohibited
- **BR-TRF-004**: Some credit types non-transferable
- **BR-TRF-005**: Transfer creates paired transactions

### Query Rules
- **BR-QRY-001**: Balance queries return real-time data
- **BR-QRY-002**: Transaction history paginated (max 100)
- **BR-QRY-003**: Date range filtering required for large queries
- **BR-QRY-004**: User can only query own credits (or admin)

### Event Rules
- **BR-EVT-001**: All credit operations publish events
- **BR-EVT-002**: Event publishing failures logged but don't block
- **BR-EVT-003**: Events use ISO 8601 timestamps

---

## Credit Service in the Ecosystem

### Upstream Dependencies
- **Account Service**: User validation and lifecycle events
- **Subscription Service**: Subscription status and credit allocations
- **Order Service**: Referral tracking and order events
- **PostgreSQL gRPC Service**: Persistent storage
- **NATS Event Bus**: Event publishing/subscribing
- **Consul**: Service discovery and health checks

### Downstream Consumers
- **Billing Service**: Credit availability check and consumption
- **Wallet Service**: Balance aggregation
- **Notification Service**: Credit alerts and warnings
- **Analytics Service**: Promotional effectiveness metrics
- **Admin Dashboard**: Campaign management

### Integration Patterns
- **Synchronous REST**: CRUD operations via FastAPI endpoints
- **Asynchronous Events**: NATS for lifecycle events
- **Service Discovery**: Consul for dynamic service location
- **Protocol Buffers**: PostgreSQL gRPC communication
- **Health Checks**: `/health` and `/health/detailed` endpoints

### Dependency Injection
- **Repository Pattern**: CreditRepository for data access
- **Protocol Interfaces**: CreditRepositoryProtocol, EventBusProtocol
- **Client Protocols**: AccountClientProtocol, SubscriptionClientProtocol
- **Factory Pattern**: create_credit_service() for production instances
- **Mock-Friendly**: Protocols enable test doubles and mocks

---

## Success Metrics

### Promotional Metrics
- **Total Credits Allocated**: By campaign, type, period
- **Credit Utilization Rate**: Consumed / Allocated (target: >60%)
- **Expiration Rate**: Expired / Allocated (target: <20%)
- **Referral Conversion**: Referral credits leading to purchases

### Operational Metrics
- **Allocation Success Rate**: % successful allocations (target: >99%)
- **Consumption Latency**: Time to process consumption (target: <100ms)
- **Expiration Processing Time**: Daily job duration (target: <5min)
- **Event Publishing Success**: % events published (target: >99.9%)

### Business Metrics
- **Cost of Credits**: Total promotional cost
- **Revenue from Credit Users**: Revenue from users with credits
- **Credit-Influenced Purchases**: Orders using credits
- **Campaign ROI**: Revenue generated / Credits allocated

### System Metrics
- **Service Uptime**: Credit Service availability (target: 99.9%)
- **Database Connectivity**: PostgreSQL connection success rate
- **Query Performance**: Average query latency (target: <50ms)

---

## Glossary

**Credit Account**: Ledger entry tracking credits of a specific type
**Credit Transaction**: Immutable record of credit movement
**Credit Campaign**: Promotional program allocating credits
**Credit Allocation**: Record of credits allocated from campaign to user
**Credit Type**: Category of credit (promotional, bonus, referral, subscription, compensation)
**FIFO Expiration**: First to expire, first to consume
**Expiration Policy**: Rules governing when credits expire
**Budget**: Maximum credits a campaign can allocate
**Eligibility Rules**: Conditions determining who qualifies for credits
**Reference ID**: External identifier linking transaction to source
**Balance Summary**: Aggregated view of user's credit status

---

**Document Version**: 1.0
**Last Updated**: 2025-12-18
**Maintained By**: Credit Service Team
