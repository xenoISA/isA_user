# Credit Service - Product Requirements Document (PRD)

## Product Overview

The Credit Service provides promotional credit management, bonus allocation, referral rewards, and credit lifecycle handling for the isA Platform, enabling flexible promotional programs with comprehensive expiration policies, consumption tracking, and campaign management.

**Product Goal**: Deliver a reliable, scalable credit system that accurately tracks promotional credits, manages expiration policies, supports multiple credit types, and integrates seamlessly with billing for credit consumption.

**Key Capabilities**:
- Multi-type credit account management (promotional, bonus, referral, subscription, compensation)
- Campaign-based credit allocation with budget tracking
- FIFO expiration-based credit consumption
- Automatic credit expiration processing
- Credit transfer between users
- Real-time balance and expiration tracking
- Event-driven integration for automatic allocations

---

## Target Users

### Primary Users

#### 1. Platform Services (Internal API Consumers)
- **Description**: Billing Service, Subscription Service, Order Service consuming credit APIs
- **Needs**: Real-time credit availability, consumption processing, balance queries
- **Goals**: Integrate credits into billing flow, allocate subscription credits

#### 2. End Users (via Client Applications)
- **Description**: Users earning and spending promotional credits
- **Needs**: View credit balance, understand expiration, use credits for purchases
- **Goals**: Maximize credit utilization before expiration

### Secondary Users

#### 3. Marketing and Growth Teams
- **Description**: Campaign managers, growth hackers, marketing analysts
- **Needs**: Campaign creation, budget tracking, effectiveness analytics
- **Goals**: Run effective promotional campaigns, optimize CAC

#### 4. Finance Team
- **Description**: Revenue operations, financial analysts
- **Needs**: Credit liability tracking, expiration forecasting, cost analysis
- **Goals**: Accurate promotional cost accounting

#### 5. Customer Support
- **Description**: Support agents handling credit-related inquiries
- **Needs**: Credit history lookup, manual adjustments, refund credits
- **Goals**: Resolve credit disputes, issue compensation credits

#### 6. Platform Administrators
- **Description**: DevOps, system administrators
- **Needs**: Service health, expiration job monitoring, error tracking
- **Goals**: Ensure credit service reliability

---

## Epics and User Stories

### Epic 1: Credit Account Management
**Goal**: Enable credit account lifecycle management for all credit types

**User Stories**:
- As a new user, I want a credit account created automatically so that I can receive promotional credits
- As a user, I want to view my credit balance by type so that I know what credits I have
- As a user, I want to see my credit transaction history so that I understand my credit activity
- As a system, I want to create accounts per credit type so that I can track sources independently
- As an admin, I want to deactivate accounts so that I can handle fraud or abuse

### Epic 2: Credit Allocation
**Goal**: Enable credit allocation through campaigns and manual processes

**User Stories**:
- As a new user, I want sign-up bonus credits so that I can try the platform
- As a referrer, I want referral credits when my friends sign up so that I'm rewarded for sharing
- As a referee, I want welcome credits via referral so that I get a bonus for being referred
- As a subscriber, I want monthly credits so that my subscription provides ongoing value
- As a support agent, I want to issue compensation credits so that I can resolve complaints

### Epic 3: Credit Consumption
**Goal**: Enable credit consumption for billing integration

**User Stories**:
- As a user, I want credits used before my wallet so that I don't lose promotional credits
- As a user, I want expiring credits used first so that I maximize credit utilization
- As billing service, I want to check credit balance so that I know what's available
- As billing service, I want to consume credits so that I can apply them to charges
- As a user, I want partial consumption supported so that I can use what I have

### Epic 4: Credit Expiration
**Goal**: Manage credit expiration lifecycle

**User Stories**:
- As a user, I want expiration warnings so that I know when credits expire
- As a user, I want to see expiration dates so that I can plan usage
- As a system, I want expired credits removed so that balances are accurate
- As a user, I want 7-day warnings so that I have time to use credits
- As an admin, I want expiration reports so that I understand liability changes

### Epic 5: Campaign Management
**Goal**: Enable promotional campaign creation and management

**User Stories**:
- As a marketer, I want to create campaigns so that I can run promotions
- As a marketer, I want budget limits so that I don't overspend
- As a marketer, I want eligibility rules so that I target the right users
- As a marketer, I want campaign analytics so that I measure effectiveness
- As a system, I want budget exhaustion alerts so that campaigns don't fail silently

### Epic 6: Credit Transfer
**Goal**: Enable credit transfer between users

**User Stories**:
- As a user, I want to transfer credits so that I can share with family/team
- As a sender, I want transfer confirmation so that I know it completed
- As a receiver, I want transfer notification so that I know credits arrived
- As a system, I want transfer limits so that I prevent abuse

### Epic 7: Statistics and Reporting
**Goal**: Provide comprehensive credit analytics

**User Stories**:
- As a user, I want balance summary so that I see all credits at once
- As finance, I want credit liability reports so that I track promotional costs
- As marketing, I want campaign ROI metrics so that I optimize spend
- As an admin, I want system statistics so that I monitor health

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
  "service": "credit_service",
  "port": 8229,
  "version": "1.0.0",
  "timestamp": "2025-12-18T10:30:00Z"
}
```
**Error Codes**: 500 (Service Unavailable)

#### GET /health/detailed
**Description**: Detailed health check with database and client status
**Auth Required**: No
**Response**:
```json
{
  "service": "credit_service",
  "status": "operational",
  "port": 8229,
  "version": "1.0.0",
  "database_connected": true,
  "account_client_available": true,
  "subscription_client_available": true,
  "expiration_job_healthy": true,
  "timestamp": "2025-12-18T10:30:00Z"
}
```

### Credit Account Endpoints

#### POST /api/v1/credits/accounts
**Description**: Create credit account for user
**Auth Required**: Yes
**Request Schema**:
```json
{
  "user_id": "user_12345",
  "organization_id": null,
  "credit_type": "promotional",
  "expiration_policy": "fixed_days",
  "expiration_days": 90,
  "metadata": {}
}
```
**Response Schema**:
```json
{
  "success": true,
  "message": "Credit account created",
  "account_id": "cred_acc_abc123",
  "user_id": "user_12345",
  "credit_type": "promotional",
  "balance": 0,
  "created_at": "2025-12-18T10:30:00Z"
}
```
**Error Codes**: 400 (Bad Request), 409 (Duplicate), 422 (Validation Error)

#### GET /api/v1/credits/accounts/{account_id}
**Description**: Get credit account by ID
**Auth Required**: Yes
**Path Parameters**: account_id
**Response Schema**:
```json
{
  "account_id": "cred_acc_abc123",
  "user_id": "user_12345",
  "credit_type": "promotional",
  "balance": 1000,
  "total_allocated": 1500,
  "total_consumed": 400,
  "total_expired": 100,
  "is_active": true,
  "created_at": "2025-12-18T10:30:00Z",
  "updated_at": "2025-12-18T10:30:00Z"
}
```
**Error Codes**: 404 (Not Found)

#### GET /api/v1/credits/accounts?user_id={user_id}
**Description**: List credit accounts for user
**Auth Required**: Yes
**Query Parameters**:
- user_id: (required) User ID
- credit_type: (optional) Filter by type
- is_active: (optional) Filter by active status
**Response Schema**:
```json
{
  "accounts": [
    {
      "account_id": "cred_acc_abc123",
      "credit_type": "promotional",
      "balance": 1000,
      "is_active": true
    }
  ],
  "total": 1
}
```

### Credit Balance Endpoints

#### GET /api/v1/credits/balance?user_id={user_id}
**Description**: Get aggregated credit balance for user
**Auth Required**: Yes
**Query Parameters**:
- user_id: (required) User ID
**Response Schema**:
```json
{
  "user_id": "user_12345",
  "total_balance": 2500,
  "available_balance": 2300,
  "expiring_soon": 500,
  "by_type": {
    "promotional": 1000,
    "bonus": 800,
    "referral": 500,
    "subscription": 200
  },
  "next_expiration": {
    "amount": 500,
    "expires_at": "2025-12-25T00:00:00Z"
  }
}
```
**Example**:
```bash
curl "http://localhost:8229/api/v1/credits/balance?user_id=user_12345" \
  -H "Authorization: Bearer <token>"
```

### Credit Allocation Endpoints

#### POST /api/v1/credits/allocate
**Description**: Allocate credits to user
**Auth Required**: Yes
**Request Schema**:
```json
{
  "user_id": "user_12345",
  "credit_type": "promotional",
  "amount": 1000,
  "campaign_id": "camp_holiday2025",
  "description": "Holiday promotion",
  "expires_at": "2026-03-18T00:00:00Z",
  "metadata": {
    "source": "marketing_campaign"
  }
}
```
**Response Schema**:
```json
{
  "success": true,
  "message": "Credits allocated successfully",
  "allocation_id": "alloc_xyz789",
  "account_id": "cred_acc_abc123",
  "amount": 1000,
  "balance_after": 2000,
  "expires_at": "2026-03-18T00:00:00Z"
}
```
**Error Codes**: 400 (Bad Request), 402 (Budget Exhausted), 422 (Validation Error)
**Example**:
```bash
curl -X POST http://localhost:8229/api/v1/credits/allocate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"user_id": "user_12345", "credit_type": "bonus", "amount": 500}'
```

### Credit Consumption Endpoints

#### POST /api/v1/credits/consume
**Description**: Consume credits for billing
**Auth Required**: Yes
**Request Schema**:
```json
{
  "user_id": "user_12345",
  "amount": 500,
  "billing_record_id": "bill_xyz789",
  "description": "AI usage billing",
  "metadata": {}
}
```
**Response Schema**:
```json
{
  "success": true,
  "message": "Credits consumed successfully",
  "amount_consumed": 500,
  "balance_before": 2500,
  "balance_after": 2000,
  "transactions": [
    {
      "transaction_id": "txn_abc123",
      "account_id": "cred_acc_123",
      "amount": 300,
      "credit_type": "promotional"
    },
    {
      "transaction_id": "txn_def456",
      "account_id": "cred_acc_456",
      "amount": 200,
      "credit_type": "bonus"
    }
  ]
}
```
**Error Codes**: 400 (Bad Request), 402 (Insufficient Credits), 422 (Validation Error)
**Example**:
```bash
curl -X POST http://localhost:8229/api/v1/credits/consume \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"user_id": "user_12345", "amount": 500, "billing_record_id": "bill_xyz789"}'
```

#### POST /api/v1/credits/check-availability
**Description**: Check if user has sufficient credits
**Auth Required**: Yes
**Request Schema**:
```json
{
  "user_id": "user_12345",
  "amount": 500
}
```
**Response Schema**:
```json
{
  "available": true,
  "total_balance": 2500,
  "requested_amount": 500,
  "deficit": 0,
  "consumption_plan": [
    {
      "account_id": "cred_acc_123",
      "credit_type": "promotional",
      "amount": 300,
      "expires_at": "2025-12-25T00:00:00Z"
    },
    {
      "account_id": "cred_acc_456",
      "credit_type": "bonus",
      "amount": 200,
      "expires_at": "2026-01-15T00:00:00Z"
    }
  ]
}
```

### Credit Transfer Endpoints

#### POST /api/v1/credits/transfer
**Description**: Transfer credits between users
**Auth Required**: Yes
**Request Schema**:
```json
{
  "from_user_id": "user_12345",
  "to_user_id": "user_67890",
  "credit_type": "bonus",
  "amount": 200,
  "description": "Gift to family member"
}
```
**Response Schema**:
```json
{
  "success": true,
  "message": "Credits transferred successfully",
  "transfer_id": "trf_abc123",
  "from_transaction_id": "txn_out_123",
  "to_transaction_id": "txn_in_456",
  "amount": 200,
  "from_balance_after": 800,
  "to_balance_after": 700
}
```
**Error Codes**: 400 (Bad Request), 402 (Insufficient Credits), 403 (Transfer Not Allowed), 404 (User Not Found)

### Credit Transaction Endpoints

#### GET /api/v1/credits/transactions
**Description**: List credit transactions
**Auth Required**: Yes
**Query Parameters**:
- user_id: (required) User ID
- account_id: (optional) Filter by account
- transaction_type: (optional) Filter by type (allocate, consume, expire, transfer_in, transfer_out, adjust)
- start_date: (optional) Filter start date
- end_date: (optional) Filter end date
- page: (optional, default: 1) Page number
- page_size: (optional, default: 50, max: 100) Items per page
**Response Schema**:
```json
{
  "transactions": [
    {
      "transaction_id": "txn_abc123",
      "account_id": "cred_acc_123",
      "user_id": "user_12345",
      "transaction_type": "allocate",
      "amount": 1000,
      "balance_before": 0,
      "balance_after": 1000,
      "description": "Sign-up bonus",
      "created_at": "2025-12-18T10:30:00Z"
    }
  ],
  "total": 45,
  "page": 1,
  "page_size": 50
}
```

### Campaign Endpoints

#### POST /api/v1/credits/campaigns
**Description**: Create credit campaign
**Auth Required**: Yes (Admin)
**Request Schema**:
```json
{
  "name": "Holiday Promotion 2025",
  "description": "2000 credits for holiday purchases",
  "credit_type": "promotional",
  "credit_amount": 2000,
  "total_budget": 1000000,
  "eligibility_rules": {
    "min_account_age_days": 30,
    "user_tier": ["gold", "platinum"]
  },
  "start_date": "2025-12-20T00:00:00Z",
  "end_date": "2025-12-31T23:59:59Z",
  "expiration_days": 90,
  "max_allocations_per_user": 1
}
```
**Response Schema**:
```json
{
  "success": true,
  "message": "Campaign created",
  "campaign_id": "camp_holiday2025",
  "name": "Holiday Promotion 2025",
  "total_budget": 1000000,
  "remaining_budget": 1000000,
  "is_active": true
}
```
**Error Codes**: 400 (Bad Request), 403 (Forbidden), 422 (Validation Error)

#### GET /api/v1/credits/campaigns/{campaign_id}
**Description**: Get campaign details
**Auth Required**: Yes (Admin)
**Response Schema**:
```json
{
  "campaign_id": "camp_holiday2025",
  "name": "Holiday Promotion 2025",
  "credit_type": "promotional",
  "credit_amount": 2000,
  "total_budget": 1000000,
  "allocated_amount": 250000,
  "remaining_budget": 750000,
  "allocation_count": 125,
  "start_date": "2025-12-20T00:00:00Z",
  "end_date": "2025-12-31T23:59:59Z",
  "is_active": true
}
```

### Statistics Endpoints

#### GET /api/v1/credits/statistics
**Description**: Get credit statistics
**Auth Required**: Yes (Admin)
**Query Parameters**:
- start_date: (optional) Period start
- end_date: (optional) Period end
- credit_type: (optional) Filter by type
**Response Schema**:
```json
{
  "period_start": "2025-12-01T00:00:00Z",
  "period_end": "2025-12-31T23:59:59Z",
  "total_allocated": 5000000,
  "total_consumed": 3500000,
  "total_expired": 250000,
  "utilization_rate": 0.70,
  "expiration_rate": 0.05,
  "by_credit_type": {
    "promotional": {
      "allocated": 2000000,
      "consumed": 1500000,
      "expired": 100000
    },
    "bonus": {
      "allocated": 1500000,
      "consumed": 1000000,
      "expired": 100000
    }
  },
  "active_campaigns": 5,
  "active_accounts": 15000
}
```

---

## Functional Requirements

### Credit Account Management

**FR-001**: System MUST create credit accounts with unique account_id
- Auto-generate account_id format: `cred_acc_{uuid.hex[:24]}`
- One account per user per credit_type
- Initial balance is 0

**FR-002**: System MUST prevent duplicate accounts
- Check existing account before creation
- Return existing account for duplicate requests
- Support idempotent creation

**FR-003**: System MUST support all credit types
- promotional, bonus, referral, subscription, compensation
- Validate credit_type is known enum value

### Credit Allocation

**FR-004**: System MUST allocate credits with expiration
- Set expires_at based on expiration policy
- Support fixed_days, end_of_month, subscription_period policies
- Record allocation transaction

**FR-005**: System MUST enforce campaign budget limits
- Check remaining_budget before allocation
- Update allocated_amount after allocation
- Prevent over-allocation atomically

**FR-006**: System MUST validate user eligibility
- Check campaign eligibility_rules
- Enforce max_allocations_per_user
- Validate campaign date range

**FR-007**: System MUST support manual allocations
- Allow admin to allocate without campaign
- Require description for manual allocations
- Set appropriate credit_type

### Credit Consumption

**FR-008**: System MUST consume credits in FIFO order
- Order by expires_at ASC (soonest first)
- Within same expiration: oldest first
- Support priority by credit_type

**FR-009**: System MUST support partial consumption
- Consume what's available if insufficient
- Return amount_consumed and deficit
- Allow caller to proceed with partial

**FR-010**: System MUST prevent negative balance
- Validate sufficient balance before consumption
- Atomic balance update across accounts
- Rollback on partial failure

**FR-011**: System MUST link consumption to billing
- Require billing_record_id for usage consumption
- Store reference in transaction
- Enable reconciliation

### Credit Expiration

**FR-012**: System MUST process expired credits
- Daily batch job for expiration
- Query allocations with expires_at <= NOW()
- Create expire transactions

**FR-013**: System MUST send expiration warnings
- 7-day warning before expiration
- Publish credit.expiring_soon event
- Include amount and expiration date

**FR-014**: System MUST maintain audit trail
- Log all expiration transactions
- Record original allocation reference
- Preserve for compliance

### Credit Transfer

**FR-015**: System MUST support user-to-user transfers
- Validate sender has sufficient balance
- Validate recipient exists and is active
- Create paired transactions

**FR-016**: System MUST enforce transfer restrictions
- Some credit types non-transferable (e.g., compensation)
- Configurable per credit_type
- Return error for restricted transfers

### Campaign Management

**FR-017**: System MUST support campaign CRUD
- Create with budget, dates, rules
- Update active status
- Query by various filters

**FR-018**: System MUST handle budget exhaustion
- Deactivate campaign when budget exhausted
- Publish campaign.budget.exhausted event
- Prevent new allocations

### Statistics and Reporting

**FR-019**: System MUST provide balance summary
- Aggregate across all accounts for user
- Include expiring_soon calculation
- Show breakdown by credit_type

**FR-020**: System MUST provide credit statistics
- Allocation, consumption, expiration totals
- Utilization and expiration rates
- By credit_type and campaign

### Event Publishing

**FR-021**: System MUST publish events for credit operations
- credit.allocated on allocation
- credit.consumed on consumption
- credit.expired on expiration
- credit.transferred on transfer
- credit.expiring_soon on warning

**FR-022**: System MUST subscribe to upstream events
- user.created for sign-up bonus
- subscription.created/renewed for subscription credits
- order.completed for referral credits
- user.deleted for cleanup

---

## Non-Functional Requirements

### Performance

**NFR-001**: Balance query MUST complete within 50ms (p95)

**NFR-002**: Credit consumption MUST complete within 100ms (p95)

**NFR-003**: Credit allocation MUST complete within 200ms (p95)

**NFR-004**: Expiration job MUST complete within 5 minutes for 100K records

**NFR-005**: Service MUST handle 1000 credit operations per second

### Scalability

**NFR-006**: Service MUST scale horizontally behind load balancer

**NFR-007**: Database queries MUST use proper indexing on user_id, expires_at

**NFR-008**: Batch expiration MUST be parallelizable

### Reliability

**NFR-009**: Service uptime MUST be 99.9%

**NFR-010**: Event publishing failures MUST NOT block credit operations

**NFR-011**: Client service unavailability MUST NOT crash service (fail-open)

**NFR-012**: Credit operations MUST be idempotent (retries safe)

### Data Integrity

**NFR-013**: Credit transactions MUST be immutable after creation

**NFR-014**: Balance updates MUST be atomic across accounts

**NFR-015**: Campaign budget tracking MUST be accurate to within 1%

**NFR-016**: All credit amounts stored as integers (no floating point)

### Security

**NFR-017**: All credit data MUST be isolated per user

**NFR-018**: Credit access MUST validate user ownership

**NFR-019**: Admin operations MUST require admin role

**NFR-020**: Transfer limits MUST prevent fraud

---

## Success Metrics

### Promotional Metrics
- **Credit Utilization Rate**: Consumed / Allocated (target: >60%)
- **Expiration Rate**: Expired / Allocated (target: <20%)
- **Campaign Completion Rate**: Budget used / Total budget
- **Referral Conversion Rate**: Referred users making purchases

### Operational Metrics
- **Allocation Success Rate**: % successful allocations (target: >99%)
- **Consumption Latency**: p50, p95, p99 consumption time
- **Expiration Job Duration**: Time to process daily expirations
- **Error Rate**: % of requests returning 5xx

### Business Metrics
- **Total Credit Liability**: Outstanding unexpired credits
- **Credit-Influenced Revenue**: Revenue from orders using credits
- **CAC Impact**: Customer acquisition cost with/without credits
- **Retention Impact**: Retention rate of credit users vs non-credit

### System Metrics
- **Active Credit Accounts**: Users with positive balance
- **Daily Allocations**: Credits allocated per day
- **Daily Consumption**: Credits consumed per day
- **Daily Expirations**: Credits expired per day

---

**Document Version**: 1.0
**Last Updated**: 2025-12-18
**Maintained By**: Credit Service Team
