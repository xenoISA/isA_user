# Subscription Service - Product Requirements Document (PRD)

## Product Overview

The Subscription Service provides centralized subscription management and credit-based billing for the isA_user platform. It enables users to select subscription tiers, track credit usage, and manage their billing lifecycle through a unified API.

**Product Vision**: Deliver a flexible, credit-based subscription system that scales from individual free users to large enterprise deployments, with transparent usage tracking and fair billing.

**Key Capabilities**:
- Subscription lifecycle management (create, update, cancel, renew)
- Credit allocation and consumption tracking
- Multi-tier pricing with trial support
- Organization/team subscription management
- Comprehensive audit trail and history

---

## Target Users

### 1. End Users (Individuals)
- Select and manage personal subscriptions
- Monitor credit usage and balance
- Upgrade/downgrade subscription tiers
- Start free trials of paid features

### 2. Organization Administrators
- Manage team/enterprise subscriptions
- Allocate seats to team members
- Monitor organization credit consumption
- Handle billing and payment methods

### 3. Platform Services (Internal)
- Validate user subscription status
- Consume credits for service usage
- Check feature access based on tier

### 4. Billing/Finance Teams
- Generate usage reports
- Process subscription renewals
- Handle cancellation and refunds

### 5. API Developers
- Integrate credit consumption
- Build subscription management UIs
- Implement tier-based feature gates

---

## Epics and User Stories

### Epic 1: Subscription Creation
**Goal**: Enable users to create and activate subscriptions

**User Stories**:
- As a user, I want to create a free subscription so that I can start using the platform
- As a user, I want to start a trial of a paid tier so that I can evaluate premium features
- As a user, I want to select my billing cycle (monthly/quarterly/yearly) so that I can optimize costs
- As an org admin, I want to create a team subscription so that my team can share credits
- As a system, I want to prevent duplicate active subscriptions so that billing is accurate

### Epic 2: Credit Management
**Goal**: Enable precise tracking and consumption of credits

**User Stories**:
- As a user, I want to view my credit balance so that I know how much I can use
- As a service, I want to consume credits for usage so that billing is accurate
- As a user, I want to receive alerts when credits are low so that I can avoid service interruption
- As a user, I want unused credits to roll over so that I don't lose value
- As a system, I want to block consumption when credits are insufficient so that users don't incur debt

### Epic 3: Subscription Lifecycle
**Goal**: Manage full subscription lifecycle

**User Stories**:
- As a user, I want to cancel my subscription so that I'm not charged anymore
- As a user, I want to choose immediate or end-of-period cancellation so that I have flexibility
- As a user, I want my subscription to auto-renew so that service continues uninterrupted
- As a system, I want to process renewals automatically so that subscriptions stay active
- As a user, I want to pause my subscription temporarily so that I can return later

### Epic 4: Tier Management
**Goal**: Support tier upgrades, downgrades, and changes

**User Stories**:
- As a user, I want to upgrade to a higher tier so that I get more credits
- As a user, I want to downgrade at period end so that I can reduce costs
- As a user, I want to see tier comparison so that I can choose the right plan
- As an org admin, I want to add seats to my team plan so that more members can access
- As a system, I want to prorate upgrade charges so that billing is fair

### Epic 5: History and Reporting
**Goal**: Provide comprehensive audit trail and analytics

**User Stories**:
- As a user, I want to view my subscription history so that I can track changes
- As a user, I want to see my credit consumption history so that I can analyze usage
- As an admin, I want to generate usage reports so that I can plan capacity
- As a finance user, I want to see billing history so that I can reconcile accounts

### Epic 6: Organization Subscriptions
**Goal**: Support team and enterprise subscription models

**User Stories**:
- As an org admin, I want to purchase multiple seats so that my team can use the platform
- As an org admin, I want to manage seat assignments so that I control access
- As an org member, I want to consume from org credits so that I don't need personal subscription
- As an org admin, I want to set usage limits per member so that I can control costs

---

## API Surface Documentation

### Health Endpoints

#### GET /health
**Purpose**: Basic service health check

**Response** (200 OK):
```json
{
  "status": "healthy",
  "service": "subscription_service",
  "port": 8217,
  "version": "1.0.0",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### GET /health/detailed
**Purpose**: Detailed health check with database status

**Response** (200 OK):
```json
{
  "status": "healthy",
  "service": "subscription_service",
  "port": 8217,
  "version": "1.0.0",
  "timestamp": "2025-01-15T10:30:00Z",
  "database_connected": true
}
```

---

### Subscription Endpoints

#### POST /api/v1/subscriptions
**Purpose**: Create a new subscription

**Request Schema**:
```json
{
  "user_id": "user_abc123",
  "organization_id": null,
  "tier_code": "pro",
  "billing_cycle": "monthly",
  "payment_method_id": "pm_xyz789",
  "seats": 1,
  "use_trial": true,
  "promo_code": null,
  "metadata": {}
}
```

**Response Schema** (200 OK):
```json
{
  "success": true,
  "message": "Subscription created successfully",
  "subscription": {
    "subscription_id": "sub_abc123",
    "user_id": "user_abc123",
    "tier_code": "pro",
    "status": "trialing",
    "credits_allocated": 30000000,
    "credits_remaining": 30000000,
    "current_period_start": "2025-01-15T00:00:00Z",
    "current_period_end": "2025-02-14T23:59:59Z",
    "is_trial": true,
    "trial_end": "2025-01-29T23:59:59Z"
  },
  "credits_allocated": 30000000,
  "next_billing_date": "2025-01-29T23:59:59Z"
}
```

**Error Codes**:
- 400: Invalid request parameters
- 404: Tier not found
- 409: User already has active subscription
- 500: Internal server error

**Example**:
```bash
curl -X POST http://localhost:8217/api/v1/subscriptions \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_123", "tier_code": "pro", "billing_cycle": "monthly"}'
```

---

#### GET /api/v1/subscriptions
**Purpose**: List subscriptions with filters

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_id | string | No | Filter by user ID |
| organization_id | string | No | Filter by organization ID |
| status | enum | No | Filter by status |
| page | int | No | Page number (default: 1) |
| page_size | int | No | Items per page (default: 50, max: 100) |

**Response Schema** (200 OK):
```json
{
  "success": true,
  "message": "Subscriptions retrieved",
  "subscriptions": [
    {
      "subscription_id": "sub_abc123",
      "user_id": "user_abc123",
      "tier_code": "pro",
      "status": "active",
      "credits_remaining": 25000000
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 50
}
```

**Example**:
```bash
curl "http://localhost:8217/api/v1/subscriptions?user_id=user_123&status=active"
```

---

#### GET /api/v1/subscriptions/{subscription_id}
**Purpose**: Get subscription by ID

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| subscription_id | string | Yes | Subscription ID |

**Response Schema** (200 OK):
```json
{
  "success": true,
  "message": "Subscription found",
  "subscription": {
    "subscription_id": "sub_abc123",
    "user_id": "user_abc123",
    "tier_code": "pro",
    "status": "active",
    "billing_cycle": "monthly",
    "credits_allocated": 30000000,
    "credits_used": 5000000,
    "credits_remaining": 25000000,
    "current_period_start": "2025-01-01T00:00:00Z",
    "current_period_end": "2025-01-31T23:59:59Z",
    "auto_renew": true
  }
}
```

**Error Codes**:
- 404: Subscription not found
- 500: Internal server error

---

#### POST /api/v1/subscriptions/{subscription_id}/cancel
**Purpose**: Cancel a subscription

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| subscription_id | string | Yes | Subscription ID |

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_id | string | Yes | User ID for authorization |

**Request Schema**:
```json
{
  "immediate": false,
  "reason": "Too expensive",
  "feedback": "Would use again if cheaper"
}
```

**Response Schema** (200 OK):
```json
{
  "success": true,
  "message": "Subscription will cancel at period end",
  "canceled_at": "2025-01-15T10:30:00Z",
  "effective_date": "2025-01-31T23:59:59Z",
  "credits_remaining": 25000000
}
```

**Error Codes**:
- 403: Not authorized to cancel
- 404: Subscription not found
- 500: Internal server error

---

#### GET /api/v1/subscriptions/user/{user_id}
**Purpose**: Get active subscription for a user

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_id | string | Yes | User ID |

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| organization_id | string | No | Organization ID |

**Response Schema** (200 OK):
```json
{
  "success": true,
  "message": "Subscription found",
  "subscription": {
    "subscription_id": "sub_abc123",
    "user_id": "user_abc123",
    "tier_code": "pro",
    "status": "active",
    "credits_remaining": 25000000
  }
}
```

---

### Credit Endpoints

#### GET /api/v1/subscriptions/credits/balance
**Purpose**: Get credit balance for a user

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_id | string | Yes | User ID |
| organization_id | string | No | Organization ID |

**Response Schema** (200 OK):
```json
{
  "success": true,
  "message": "Credit balance retrieved",
  "user_id": "user_abc123",
  "organization_id": null,
  "subscription_credits_remaining": 25000000,
  "subscription_credits_total": 30000000,
  "subscription_period_end": "2025-01-31T23:59:59Z",
  "total_credits_available": 25000000,
  "subscription_id": "sub_abc123",
  "tier_code": "pro",
  "tier_name": "Pro"
}
```

**Example**:
```bash
curl "http://localhost:8217/api/v1/subscriptions/credits/balance?user_id=user_123"
```

---

#### POST /api/v1/subscriptions/credits/consume
**Purpose**: Consume credits from a user's subscription

**Request Schema**:
```json
{
  "user_id": "user_abc123",
  "organization_id": null,
  "credits_to_consume": 5000,
  "service_type": "model_inference",
  "usage_record_id": "usage_xyz789",
  "description": "GPT-4 inference call",
  "metadata": {
    "model": "gpt-4",
    "tokens": 500
  }
}
```

**Response Schema** (200 OK):
```json
{
  "success": true,
  "message": "Credits consumed successfully",
  "credits_consumed": 5000,
  "credits_remaining": 24995000,
  "subscription_id": "sub_abc123",
  "consumed_from": "subscription"
}
```

**Error Codes**:
- 402: Insufficient credits
- 404: No active subscription found
- 500: Internal server error

**Example**:
```bash
curl -X POST http://localhost:8217/api/v1/subscriptions/credits/consume \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_123", "credits_to_consume": 5000, "service_type": "model_inference"}'
```

---

### History Endpoint

#### GET /api/v1/subscriptions/{subscription_id}/history
**Purpose**: Get subscription history

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| subscription_id | string | Yes | Subscription ID |

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| page | int | No | Page number (default: 1) |
| page_size | int | No | Items per page (default: 50, max: 100) |

**Response Schema** (200 OK):
```json
{
  "success": true,
  "message": "History retrieved",
  "history": [
    {
      "history_id": "hist_abc123",
      "subscription_id": "sub_abc123",
      "action": "credits_consumed",
      "credits_change": -5000,
      "credits_balance_after": 24995000,
      "reason": "model_inference: GPT-4 inference call",
      "initiated_by": "system",
      "created_at": "2025-01-15T10:30:00Z"
    }
  ],
  "total": 1
}
```

---

## Functional Requirements

### FR-001: Subscription Creation
The system MUST allow users to create subscriptions with valid tier codes.
- **Acceptance**: Subscription created with allocated credits

### FR-002: Duplicate Prevention
The system MUST prevent creation of duplicate active subscriptions for the same user/org context.
- **Acceptance**: Error returned if active subscription exists

### FR-003: Credit Allocation
The system MUST allocate credits based on tier and billing cycle.
- **Acceptance**: Credits calculated correctly (monthly * cycle_multiplier)

### FR-004: Trial Period Support
The system MUST support trial periods for eligible tiers.
- **Acceptance**: Trial status set, trial_end date calculated

### FR-005: Credit Consumption
The system MUST deduct credits from subscription balance.
- **Acceptance**: credits_remaining decremented, history recorded

### FR-006: Insufficient Credit Blocking
The system MUST reject consumption requests when credits are insufficient.
- **Acceptance**: 402 error returned, no credits deducted

### FR-007: Subscription Cancellation
The system MUST support immediate and end-of-period cancellation.
- **Acceptance**: Status updated, effective_date set correctly

### FR-008: Ownership Validation
The system MUST validate that cancellation requestor owns the subscription.
- **Acceptance**: 403 error if user_id mismatch

### FR-009: Credit Balance Query
The system MUST return accurate credit balance for users.
- **Acceptance**: All credit fields populated correctly

### FR-010: History Recording
The system MUST record all subscription actions in history.
- **Acceptance**: History entry created for each action

### FR-011: Event Publishing
The system MUST publish events for all subscription changes.
- **Acceptance**: Events published to NATS

### FR-012: Pagination Support
The system MUST support pagination for list endpoints.
- **Acceptance**: page, page_size, total fields work correctly

### FR-013: Filter Support
The system MUST support filtering by user_id, org_id, status.
- **Acceptance**: Filters narrow result set correctly

### FR-014: Health Check
The system MUST provide health check endpoints.
- **Acceptance**: /health returns status

### FR-015: Error Handling
The system MUST return appropriate HTTP codes for errors.
- **Acceptance**: 400, 402, 403, 404, 500 used correctly

---

## Non-Functional Requirements

### NFR-001: Response Time
- GET endpoints: < 100ms p95
- POST endpoints: < 200ms p95
- Credit consumption: < 50ms p95

### NFR-002: Throughput
- Support 10,000 credit consumptions per second
- Support 1,000 subscription operations per second

### NFR-003: Availability
- 99.9% uptime
- Zero data loss on failures

### NFR-004: Scalability
- Horizontal scaling via Kubernetes
- Stateless service design

### NFR-005: Security
- JWT authentication required
- User can only access own subscriptions
- Rate limiting on all endpoints

### NFR-006: Data Integrity
- ACID transactions for credit operations
- Idempotent consumption with usage_record_id

### NFR-007: Auditability
- All actions logged to history
- Immutable audit records

### NFR-008: Monitoring
- Prometheus metrics exposed
- Health check endpoints

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Subscription creation success rate | > 99.5% |
| Credit consumption p95 latency | < 50ms |
| Monthly active subscriptions | Track growth |
| Trial to paid conversion rate | > 15% |
| Average credit utilization | 60-80% |
| Cancellation rate (monthly) | < 5% |

---

## API Summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | /health | Health check |
| GET | /health/detailed | Detailed health |
| POST | /api/v1/subscriptions | Create subscription |
| GET | /api/v1/subscriptions | List subscriptions |
| GET | /api/v1/subscriptions/{id} | Get subscription |
| POST | /api/v1/subscriptions/{id}/cancel | Cancel subscription |
| GET | /api/v1/subscriptions/user/{user_id} | Get user subscription |
| GET | /api/v1/subscriptions/credits/balance | Get credit balance |
| POST | /api/v1/subscriptions/credits/consume | Consume credits |
| GET | /api/v1/subscriptions/{id}/history | Get history |

---

**Document Statistics**:
- Lines: ~700
- Epics: 6
- User Stories: 25
- Functional Requirements: 15
- Non-Functional Requirements: 8
- API Endpoints: 10
