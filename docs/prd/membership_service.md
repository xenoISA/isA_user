# Membership Service - Product Requirements Document (PRD)

## Product Overview

**Product Name**: Membership Service
**Version**: 1.0.0
**Status**: Development
**Owner**: Loyalty Platform Team
**Last Updated**: 2025-12-19

### Vision
Become the central loyalty engine that transforms user engagement into lasting relationships through meaningful rewards and tier-based recognition.

### Mission
Deliver a flexible, points-based membership system that scales from casual users to elite members, with transparent point tracking and compelling tier benefits.

### Target Users
- **Individual Users**: Enroll in membership, earn points, redeem rewards
- **Organization Admins**: Manage corporate membership programs
- **Platform Services**: Award points for user activities, validate tier access
- **Marketing Teams**: Configure campaigns, analyze engagement
- **Customer Support**: Handle member inquiries, adjust points

### Key Differentiators
1. **Unified Point System**: Single currency across all platform services
2. **Dynamic Tier Progression**: Real-time tier evaluation and upgrades
3. **Flexible Benefit Engine**: Configurable tier benefits
4. **Event-Driven Architecture**: Real-time point allocation from activities
5. **Complete Audit Trail**: Full history of all membership actions

---

## Product Goals

### Primary Goals
1. **Member Enrollment**: Achieve 50% user enrollment rate within 6 months
2. **Engagement Lift**: 25% increase in user activity from members
3. **Retention Impact**: 15% improvement in annual user retention
4. **Point Velocity**: 40-60% of points redeemed within 6 months
5. **Tier Distribution**: 30% of members reach Silver+ tier

### Secondary Goals
1. **Corporate Adoption**: 100 organizations with corporate memberships
2. **API Integration**: All platform services integrated for point earning
3. **Campaign Support**: Enable marketing-driven point promotions
4. **Self-Service**: 90% of member actions via self-service
5. **Support Efficiency**: <5 min average resolution for member issues

---

## Epics and User Stories

### Epic 1: Membership Enrollment

**Objective**: Enable users to join and manage their membership

#### E1-US1: Enroll in Membership Program
**As a** user
**I want to** join the membership program
**So that** I can earn points and access benefits

**Acceptance Criteria**:
- AC1: POST /api/v1/memberships creates new membership
- AC2: user_id required and validated
- AC3: Response includes membership_id, tier, points_balance
- AC4: Error if user already has active membership
- AC5: membership.enrolled event published
- AC6: Response time < 200ms
- AC7: Enrollment bonus points awarded if configured

**API Reference**: `POST /api/v1/memberships`

**Example Request**:
```json
{
  "user_id": "user_abc123",
  "enrollment_source": "web_signup",
  "promo_code": "WELCOME2025"
}
```

**Example Response**:
```json
{
  "success": true,
  "message": "Membership enrolled successfully",
  "membership": {
    "membership_id": "mem_xyz789",
    "user_id": "user_abc123",
    "tier_code": "bronze",
    "status": "active",
    "points_balance": 500,
    "enrollment_bonus": 500,
    "enrolled_at": "2025-01-15T10:00:00Z"
  }
}
```

#### E1-US2: Prevent Duplicate Enrollment
**As a** system
**I want to** prevent duplicate memberships
**So that** each user has only one membership

**Acceptance Criteria**:
- AC1: Enrollment fails if active membership exists
- AC2: Error message indicates existing membership
- AC3: HTTP 409 Conflict returned

#### E1-US3: Apply Enrollment Bonus
**As a** user
**I want to** receive bonus points on enrollment
**So that** I have immediate value from joining

**Acceptance Criteria**:
- AC1: Bonus points awarded based on promo code
- AC2: Bonus points added to initial balance
- AC3: History entry records bonus allocation
- AC4: Default bonus (0) if no promo code

---

### Epic 2: Points Management

**Objective**: Enable precise point earning and redemption

#### E2-US1: Earn Points from Activity
**As a** platform service
**I want to** award points to members
**So that** users are rewarded for engagement

**Acceptance Criteria**:
- AC1: POST /api/v1/memberships/points/earn adds points
- AC2: user_id and points_amount required
- AC3: Tier multiplier applied to base points
- AC4: points.earned event published
- AC5: Response includes new balance
- AC6: Response time < 50ms

**API Reference**: `POST /api/v1/memberships/points/earn`

**Example Request**:
```json
{
  "user_id": "user_abc123",
  "points_amount": 1000,
  "source": "order_completed",
  "reference_id": "order_12345",
  "description": "Purchase $100 order"
}
```

**Example Response**:
```json
{
  "success": true,
  "message": "Points earned successfully",
  "points_earned": 1250,
  "multiplier": 1.25,
  "points_balance": 5750,
  "tier_points": 12500
}
```

#### E2-US2: Redeem Points for Rewards
**As a** member
**I want to** redeem points for rewards
**So that** I can use my earned loyalty

**Acceptance Criteria**:
- AC1: POST /api/v1/memberships/points/redeem deducts points
- AC2: Validates sufficient point balance
- AC3: Returns HTTP 402 if insufficient points
- AC4: points.redeemed event published
- AC5: Response time < 50ms

**API Reference**: `POST /api/v1/memberships/points/redeem`

**Example Request**:
```json
{
  "user_id": "user_abc123",
  "points_amount": 2500,
  "reward_code": "FREE_SHIPPING",
  "description": "Redeem for free shipping"
}
```

**Example Response**:
```json
{
  "success": true,
  "message": "Points redeemed successfully",
  "points_redeemed": 2500,
  "points_balance": 3250,
  "reward_code": "FREE_SHIPPING"
}
```

#### E2-US3: Check Points Balance
**As a** member
**I want to** view my points balance
**So that** I know what I can redeem

**Acceptance Criteria**:
- AC1: GET endpoint returns current balance
- AC2: Includes breakdown by point type
- AC3: Shows pending points if any
- AC4: Response time < 30ms

**API Reference**: `GET /api/v1/memberships/points/balance?user_id={user_id}`

**Example Response**:
```json
{
  "success": true,
  "user_id": "user_abc123",
  "points_balance": 5750,
  "tier_points": 12500,
  "lifetime_points": 25000,
  "pending_points": 0,
  "points_expiring_soon": 1000,
  "expiration_date": "2025-06-15T00:00:00Z"
}
```

#### E2-US4: Expire Points
**As a** system
**I want to** expire old points automatically
**So that** points don't accumulate indefinitely

**Acceptance Criteria**:
- AC1: Points expire 12 months after earning
- AC2: Expiration batch job runs daily
- AC3: Notification before expiration
- AC4: History records expiration

---

### Epic 3: Tier Management

**Objective**: Support dynamic tier progression and benefits

#### E3-US1: Check Tier Status
**As a** member
**I want to** view my current tier
**So that** I know my membership level

**Acceptance Criteria**:
- AC1: GET endpoint returns tier information
- AC2: Includes tier benefits list
- AC3: Shows progress to next tier
- AC4: Response time < 50ms

**API Reference**: `GET /api/v1/memberships/{membership_id}/tier`

**Example Response**:
```json
{
  "success": true,
  "membership_id": "mem_xyz789",
  "current_tier": {
    "tier_code": "silver",
    "tier_name": "Silver",
    "point_multiplier": 1.25
  },
  "tier_progress": {
    "current_tier_points": 12500,
    "next_tier_threshold": 20000,
    "points_to_next_tier": 7500,
    "progress_percentage": 62.5
  },
  "benefits": [
    {"benefit_code": "PRIORITY_SUPPORT", "name": "Priority Support"},
    {"benefit_code": "EARLY_ACCESS", "name": "Early Access"}
  ]
}
```

#### E3-US2: Upgrade Tier
**As a** system
**I want to** upgrade members when they qualify
**So that** engaged users get better benefits

**Acceptance Criteria**:
- AC1: Tier upgrade immediate upon qualification
- AC2: membership.tier_upgraded event published
- AC3: New benefits immediately available
- AC4: History records tier change

#### E3-US3: Evaluate Tier Retention
**As a** system
**I want to** evaluate tier retention periodically
**So that** tiers reflect current engagement

**Acceptance Criteria**:
- AC1: Batch job evaluates tier qualification
- AC2: Grace period before downgrade
- AC3: Notification before tier change
- AC4: membership.tier_downgraded event if applicable

---

### Epic 4: Membership Lifecycle

**Objective**: Manage full membership lifecycle

#### E4-US1: Get Membership Details
**As a** member
**I want to** view my membership details
**So that** I understand my membership status

**Acceptance Criteria**:
- AC1: GET endpoint returns full membership
- AC2: Includes tier, points, benefits
- AC3: Shows expiration date
- AC4: Response time < 50ms

**API Reference**: `GET /api/v1/memberships/{membership_id}`

#### E4-US2: Suspend Membership
**As an** admin
**I want to** suspend a membership
**So that** I can handle policy violations

**Acceptance Criteria**:
- AC1: PUT endpoint changes status to suspended
- AC2: Benefits frozen during suspension
- AC3: membership.suspended event published
- AC4: Reason required and recorded

**API Reference**: `PUT /api/v1/memberships/{membership_id}/suspend`

#### E4-US3: Reactivate Membership
**As an** admin
**I want to** reactivate a suspended membership
**So that** I can restore member access

**Acceptance Criteria**:
- AC1: PUT endpoint changes status to active
- AC2: Benefits restored
- AC3: membership.reactivated event published

**API Reference**: `PUT /api/v1/memberships/{membership_id}/reactivate`

#### E4-US4: Cancel Membership
**As a** member
**I want to** cancel my membership
**So that** I can opt out of the program

**Acceptance Criteria**:
- AC1: POST endpoint cancels membership
- AC2: Points balance forfeited or options given
- AC3: membership.canceled event published
- AC4: Reason captured for analytics

**API Reference**: `POST /api/v1/memberships/{membership_id}/cancel`

---

### Epic 5: Benefit Tracking

**Objective**: Track and manage tier benefits

#### E5-US1: List Available Benefits
**As a** member
**I want to** see my available benefits
**So that** I know what I can use

**Acceptance Criteria**:
- AC1: GET endpoint returns tier benefits
- AC2: Shows usage limits and current usage
- AC3: Indicates available vs exhausted benefits

**API Reference**: `GET /api/v1/memberships/{membership_id}/benefits`

**Example Response**:
```json
{
  "success": true,
  "membership_id": "mem_xyz789",
  "tier_code": "gold",
  "benefits": [
    {
      "benefit_code": "FREE_SHIPPING",
      "name": "Free Shipping",
      "usage_limit": 5,
      "used_count": 2,
      "remaining": 3
    },
    {
      "benefit_code": "PRIORITY_SUPPORT",
      "name": "Priority Support",
      "usage_limit": null,
      "is_unlimited": true
    }
  ]
}
```

#### E5-US2: Use a Benefit
**As a** member
**I want to** use a tier benefit
**So that** I can enjoy my membership perks

**Acceptance Criteria**:
- AC1: POST endpoint records benefit usage
- AC2: Validates benefit available at tier
- AC3: Checks usage limits
- AC4: benefit.redeemed event published

**API Reference**: `POST /api/v1/memberships/{membership_id}/benefits/use`

---

### Epic 6: History and Reporting

**Objective**: Provide comprehensive audit trail

#### E6-US1: View Points History
**As a** member
**I want to** see my points history
**So that** I can track my earning and spending

**Acceptance Criteria**:
- AC1: GET endpoint returns point transactions
- AC2: Supports pagination
- AC3: Filterable by type (earn/redeem)
- AC4: Response time < 100ms

**API Reference**: `GET /api/v1/memberships/{membership_id}/history`

**Example Response**:
```json
{
  "success": true,
  "membership_id": "mem_xyz789",
  "history": [
    {
      "history_id": "hist_001",
      "action": "points_earned",
      "points_change": 1250,
      "balance_after": 5750,
      "source": "order_completed",
      "created_at": "2025-01-15T10:00:00Z"
    }
  ],
  "total": 50,
  "page": 1,
  "page_size": 20
}
```

#### E6-US2: Get Membership Statistics
**As an** admin
**I want to** view membership statistics
**So that** I can monitor program health

**Acceptance Criteria**:
- AC1: GET endpoint returns aggregated stats
- AC2: Includes tier distribution
- AC3: Shows point activity metrics

**API Reference**: `GET /api/v1/memberships/stats`

---

## API Surface Documentation

### Base URL
- **Development**: `http://localhost:8250`
- **Staging**: `https://staging-membership.isa.ai`
- **Production**: `https://membership.isa.ai`

### API Version
All endpoints prefixed with `/api/v1/`

### Authentication
- **Current**: Handled by API Gateway (JWT validation)
- **Header**: `Authorization: Bearer <token>`
- **User Context**: user_id extracted from JWT claims

### Core Endpoints Summary

| Method | Endpoint | Purpose | Response Time |
|--------|----------|---------|---------------|
| POST | `/api/v1/memberships` | Enroll membership | <200ms |
| GET | `/api/v1/memberships/{id}` | Get membership | <50ms |
| GET | `/api/v1/memberships/user/{user_id}` | Get by user | <50ms |
| GET | `/api/v1/memberships` | List memberships | <100ms |
| POST | `/api/v1/memberships/{id}/cancel` | Cancel membership | <100ms |
| PUT | `/api/v1/memberships/{id}/suspend` | Suspend membership | <50ms |
| PUT | `/api/v1/memberships/{id}/reactivate` | Reactivate | <50ms |
| GET | `/api/v1/memberships/{id}/tier` | Get tier status | <50ms |
| POST | `/api/v1/memberships/points/earn` | Earn points | <50ms |
| POST | `/api/v1/memberships/points/redeem` | Redeem points | <50ms |
| GET | `/api/v1/memberships/points/balance` | Get balance | <30ms |
| GET | `/api/v1/memberships/{id}/benefits` | List benefits | <50ms |
| POST | `/api/v1/memberships/{id}/benefits/use` | Use benefit | <50ms |
| GET | `/api/v1/memberships/{id}/history` | Get history | <100ms |
| GET | `/api/v1/memberships/stats` | Get statistics | <200ms |
| GET | `/health` | Health check | <20ms |
| GET | `/health/detailed` | Detailed health | <50ms |

### HTTP Status Codes
- `200 OK`: Successful operation
- `201 Created`: New membership enrolled
- `400 Bad Request`: Validation error
- `402 Payment Required`: Insufficient points
- `404 Not Found`: Membership not found
- `409 Conflict`: Duplicate enrollment
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Database unavailable

---

## Functional Requirements

### FR-1: Membership Enrollment
System SHALL allow users to enroll in membership program with idempotent handling

### FR-2: Duplicate Prevention
System SHALL prevent multiple active memberships per user

### FR-3: Point Earning
System SHALL accept point earning requests with tier multiplier application

### FR-4: Point Redemption
System SHALL validate sufficient points before redemption

### FR-5: Insufficient Points Blocking
System SHALL reject redemption when points are insufficient (HTTP 402)

### FR-6: Tier Evaluation
System SHALL automatically upgrade tiers when qualification thresholds met

### FR-7: Point Expiration
System SHALL expire points after configurable duration (default 12 months)

### FR-8: Benefit Tracking
System SHALL track benefit usage against tier limits

### FR-9: History Recording
System SHALL record all membership actions immutably

### FR-10: Event Publishing
System SHALL publish events for all membership mutations

### FR-11: Pagination Support
System SHALL support pagination for list and history endpoints

### FR-12: Health Check
System SHALL provide health check endpoints

---

## Non-Functional Requirements

### NFR-1: Performance
- **Point Earning**: <50ms (p95)
- **Point Redemption**: <50ms (p95)
- **Balance Query**: <30ms (p95)
- **Enrollment**: <200ms (p95)
- **Health Check**: <20ms (p99)

### NFR-2: Availability
- **Uptime**: 99.9% (excluding planned maintenance)
- **Database Failover**: Automatic with <30s recovery
- **Graceful Degradation**: Event failures don't block operations

### NFR-3: Scalability
- **Concurrent Users**: 10,000+ concurrent requests
- **Total Memberships**: 10,000,000+ supported
- **Throughput**: 50,000 point operations/second
- **Database Connections**: Pooled with max 100 connections

### NFR-4: Data Integrity
- **ACID Transactions**: All point mutations wrapped in transactions
- **Idempotency**: Point operations support idempotency keys
- **Validation**: Pydantic models validate all inputs
- **Audit Trail**: All changes tracked with timestamps

### NFR-5: Security
- **Authentication**: JWT validation by API Gateway
- **Authorization**: User-scoped data access
- **Input Sanitization**: SQL injection prevention
- **Point Validation**: Prevent negative balance attacks

### NFR-6: Observability
- **Structured Logging**: JSON logs for all operations
- **Metrics**: Prometheus-compatible (future)
- **Tracing**: Request IDs for debugging
- **Health Monitoring**: Database connectivity checked

---

## Dependencies

### External Services

1. **PostgreSQL gRPC Service**: Membership data storage
   - Host: `isa-postgres-grpc:50061`
   - Schema: `membership`
   - SLA: 99.9% availability

2. **NATS Event Bus**: Event publishing
   - Host: `isa-nats:4222`
   - Subjects: `membership.*`, `points.*`, `benefit.*`
   - SLA: 99.9% availability

3. **Consul**: Service discovery and health checks
   - Host: `localhost:8500`
   - Service Name: `membership_service`
   - Health Check: HTTP `/health`

4. **Account Service**: User validation
   - Optional user existence check
   - Graceful degradation if unavailable

### Internal Dependencies
- **core.config_manager**: Configuration management
- **core.logger**: Structured logging
- **core.nats_client**: Event bus client
- **isa_common.consul_client**: Service registration
- **isa_common.AsyncPostgresClient**: Database client

---

## Success Criteria

### Phase 1: Core Functionality
- [ ] Membership enrollment working
- [ ] Point earning/redemption functional
- [ ] Tier evaluation active
- [ ] PostgreSQL storage stable
- [ ] Event publishing active
- [ ] Health checks implemented

### Phase 2: Benefits and History
- [ ] Benefit tracking working
- [ ] History endpoints functional
- [ ] Statistics endpoint working
- [ ] Pagination implemented

### Phase 3: Production Hardening
- [ ] Comprehensive test coverage
- [ ] Performance benchmarks met
- [ ] Monitoring setup
- [ ] Load testing completed

### Phase 4: Scale and Optimize
- [ ] Point expiration batch job
- [ ] Advanced tier evaluation
- [ ] Bulk operations
- [ ] Analytics integration

---

## Out of Scope

1. **Payment Processing**: Handled by payment_service
2. **Subscription Billing**: Handled by subscription_service
3. **Reward Inventory**: Handled by product_service
4. **User Authentication**: Handled by auth_service
5. **Email Delivery**: Handled by notification_service

---

**Document Version**: 1.0
**Last Updated**: 2025-12-19
**Maintained By**: Membership Service Product Team
**Related Documents**:
- Domain Context: docs/domain/membership_service.md
- Design Doc: docs/design/membership_service.md
- Data Contract: tests/contracts/membership/data_contract.py
- Logic Contract: tests/contracts/membership/logic_contract.md
