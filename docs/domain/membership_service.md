# Membership Service - Domain Context

## Overview

The Membership Service is the **loyalty and engagement engine** for the isA_user platform. It manages membership tiers, member benefits, points/rewards tracking, and member lifecycle management. Every loyalty action in the system passes through this service for tier validation, point allocation, and benefit verification.

**Business Context**: Enable a comprehensive membership program that rewards user engagement, provides tiered benefits, and drives long-term user retention through a unified membership system.

**Core Value Proposition**: Transform user engagement into measurable loyalty through a tiered membership system where users earn points, unlock benefits, and progress through membership levels based on their platform activity and spending.

---

## Business Taxonomy

### Core Entities

#### 1. Membership
**Definition**: A user's enrollment status in the platform's loyalty program with associated tier, points, and benefits.

**Business Purpose**:
- Establish loyalty program enrollment for users
- Track membership lifecycle (enrollment, activation, renewal, expiration)
- Manage tier assignments and progressions
- Control access to member-exclusive benefits

**Key Attributes**:
- Membership ID (unique identifier)
- User ID (owner of the membership)
- Organization ID (optional, for corporate memberships)
- Tier Code (bronze, silver, gold, platinum, diamond)
- Status (active, pending, suspended, expired, canceled)
- Points Balance (current redeemable points)
- Lifetime Points (total points ever earned)
- Tier Points (points counting toward tier qualification)
- Enrollment Date
- Expiration Date
- Auto Renew Flag

**Membership States**:
- **Pending**: Enrollment initiated, awaiting activation
- **Active**: Full membership benefits available
- **Suspended**: Temporarily suspended, benefits frozen
- **Expired**: Membership period ended, grace period
- **Canceled**: User-initiated cancellation

#### 2. Membership Tier
**Definition**: A predefined membership level with specific benefits, point multipliers, and qualification thresholds.

**Business Purpose**:
- Define membership levels with clear value propositions
- Enable tiered reward structure
- Support tier progression and demotion paths
- Manage tier-specific benefit access

**Available Tiers**:
| Tier | Annual Spend | Tier Points | Point Multiplier | Benefits |
|------|--------------|-------------|------------------|----------|
| Bronze | $0 | 0 | 1.0x | Basic benefits |
| Silver | $500 | 5,000 | 1.25x | Priority support |
| Gold | $2,000 | 20,000 | 1.5x | Free shipping |
| Platinum | $5,000 | 50,000 | 2.0x | Exclusive access |
| Diamond | $10,000 | 100,000 | 3.0x | VIP concierge |

#### 3. Points
**Definition**: The platform's loyalty currency for measuring engagement and providing rewards.

**Business Purpose**:
- Provide unified reward system across platform services
- Enable precise activity tracking
- Support redemption for rewards
- Allow flexible point allocation and consumption

**Point System**:
- 1 Point = $0.01 USD redemption value
- $1 USD spent = 100 Base Points
- Points multiplied by tier multiplier
- Points expire 12 months from earn date

**Point Types**:
- **Base Points**: Earned from purchases
- **Bonus Points**: Promotional or event-based
- **Tier Points**: Count toward tier qualification (non-redeemable)
- **Reward Points**: Redeemable for benefits

#### 4. Member Benefit
**Definition**: A privilege or reward available to members based on their tier level.

**Business Purpose**:
- Define tier-specific rewards and privileges
- Track benefit usage and limits
- Support one-time and recurring benefits
- Enable benefit redemption tracking

**Benefit Categories**:
- **Discounts**: Percentage or fixed discounts
- **Free Services**: Complimentary features
- **Priority Access**: Early access to features
- **Exclusive Content**: Member-only content
- **Rewards**: Redeemable point-based rewards

#### 5. Membership History
**Definition**: An audit trail of all membership actions and point transactions.

**Business Purpose**:
- Maintain complete audit trail for compliance
- Track membership changes over time
- Support dispute resolution
- Enable analytics and reporting

**Key Actions Tracked**:
- Enrolled, Activated, Renewed, Expired
- Upgraded, Downgraded, Suspended, Reactivated
- Points Earned, Points Redeemed, Points Expired
- Benefit Used, Tier Qualified

---

## Domain Scenarios

### Scenario 1: New Member Enrollment
**Actor**: User
**Trigger**: User opts into membership program

**Flow**:
1. Validate user ID exists and is active
2. Check for existing active membership
3. Determine initial tier (typically Bronze)
4. Calculate enrollment bonus points (if any)
5. Create membership record with initial points
6. Record history entry (ENROLLED)
7. Publish membership.enrolled event

**Outcome**: User has active membership with initial tier and points

### Scenario 2: Point Earning
**Actor**: Platform Service
**Trigger**: User completes qualifying action (purchase, activity)

**Flow**:
1. Receive point allocation request with user ID and base points
2. Lookup user's active membership
3. Apply tier multiplier to base points
4. Add points to balance and lifetime totals
5. Update tier points if qualifying action
6. Record history entry (POINTS_EARNED)
7. Publish points.earned event
8. Check tier qualification thresholds

**Outcome**: Points added to member's balance, tier checked

### Scenario 3: Point Redemption
**Actor**: User
**Trigger**: User requests to redeem points for reward

**Flow**:
1. Validate membership exists and is active
2. Check sufficient points available
3. Validate reward is available at user's tier
4. Deduct points from balance
5. Record history entry (POINTS_REDEEMED)
6. Publish points.redeemed event
7. Trigger reward fulfillment

**Outcome**: Points deducted, reward issued

### Scenario 4: Tier Upgrade
**Actor**: System
**Trigger**: Member reaches tier qualification threshold

**Flow**:
1. Calculate qualifying tier based on tier points or spend
2. Compare with current tier
3. If higher tier qualified, update tier code
4. Unlock new tier benefits
5. Reset tier evaluation period if needed
6. Record history entry (TIER_UPGRADED)
7. Publish membership.tier_upgraded event

**Outcome**: Member upgraded to new tier with enhanced benefits

### Scenario 5: Membership Renewal
**Actor**: System/User
**Trigger**: Membership period approaching expiration

**Flow**:
1. Check membership is nearing expiration
2. Evaluate renewal eligibility
3. If auto_renew enabled, process renewal
4. Evaluate tier retention based on annual activity
5. Update expiration date
6. Record history entry (RENEWED)
7. Publish membership.renewed event

**Outcome**: Membership renewed for new period

### Scenario 6: Benefit Redemption
**Actor**: User
**Trigger**: User requests to use a tier benefit

**Flow**:
1. Validate membership is active
2. Check benefit is available at user's tier
3. Verify benefit usage limits not exceeded
4. Mark benefit as used
5. Record history entry (BENEFIT_USED)
6. Publish benefit.redeemed event

**Outcome**: Benefit applied, usage tracked

### Scenario 7: Tier Evaluation (Periodic)
**Actor**: System
**Trigger**: End of tier evaluation period

**Flow**:
1. Calculate total tier points in evaluation period
2. Determine qualified tier
3. If downgrade required, update tier
4. If retention achieved, maintain tier
5. Reset tier points for new period
6. Record history entries
7. Publish tier evaluation events

**Outcome**: Tier adjusted based on activity

---

## Domain Events

### Published Events

#### 1. membership.enrolled
**Trigger**: New membership created
**Payload**:
- membership_id: Membership identifier
- user_id: User identifier
- tier_code: Initial tier
- enrollment_bonus: Bonus points awarded
- created_at: Timestamp

**Subscribers**:
- **Notification Service**: Welcome email
- **Analytics Service**: Enrollment tracking
- **Credit Service**: Sync membership status

#### 2. membership.tier_upgraded
**Trigger**: Member advances to higher tier
**Payload**:
- membership_id: Membership identifier
- user_id: User identifier
- previous_tier: Previous tier code
- new_tier: New tier code
- tier_points: Qualifying points
- upgraded_at: Timestamp

**Subscribers**:
- **Notification Service**: Upgrade notification
- **Authorization Service**: Update permissions

#### 3. points.earned
**Trigger**: Points added to member account
**Payload**:
- membership_id: Membership identifier
- user_id: User identifier
- points_earned: Points amount
- point_type: Type of points
- source: Earning source
- balance_after: New balance
- earned_at: Timestamp

**Subscribers**:
- **Analytics Service**: Points tracking

#### 4. points.redeemed
**Trigger**: Points redeemed for reward
**Payload**:
- membership_id: Membership identifier
- user_id: User identifier
- points_redeemed: Points amount
- reward_type: Type of reward
- balance_after: New balance
- redeemed_at: Timestamp

**Subscribers**:
- **Order Service**: Reward fulfillment
- **Notification Service**: Redemption confirmation

#### 5. membership.expired
**Trigger**: Membership period ended
**Payload**:
- membership_id: Membership identifier
- user_id: User identifier
- expired_at: Timestamp

**Subscribers**:
- **Notification Service**: Expiration notice
- **Authorization Service**: Revoke benefits

#### 6. benefit.redeemed
**Trigger**: Member uses a tier benefit
**Payload**:
- membership_id: Membership identifier
- user_id: User identifier
- benefit_code: Benefit identifier
- benefit_type: Type of benefit
- redeemed_at: Timestamp

**Subscribers**:
- **Notification Service**: Usage confirmation

### Subscribed Events

#### 1. order.completed
**Source**: Order Service
**Handler**: Award points for purchase
**Side Effects**:
- Calculate points based on order value
- Apply tier multiplier
- Update tier points

#### 2. user.deleted
**Source**: Account Service
**Handler**: GDPR cleanup
**Side Effects**:
- Expire membership
- Anonymize history

---

## Core Concepts

### Concept 1: Point Lifecycle
Points flow through the following stages:
1. **Earned**: Added to balance from qualifying action
2. **Available**: Ready for redemption
3. **Pending**: Earned but not yet available (hold period)
4. **Redeemed**: Exchanged for reward
5. **Expired**: Passed expiration date without use

### Concept 2: Tier Progression
Tiers follow a qualification cycle:
- **Qualification Period**: 12 months rolling
- **Retention**: Must maintain qualifying activity
- **Demotion**: Occurs if thresholds not met
- **Grace Period**: 30 days before demotion

### Concept 3: Tier Points vs Reward Points
- **Tier Points**: Count toward tier qualification, not redeemable
- **Reward Points**: Redeemable for benefits, may or may not count toward tier

### Concept 4: Membership Separation
**Membership Service owns**:
- Membership enrollment and status
- Tier assignments and progressions
- Points balances and transactions
- Benefit eligibility and tracking

**Membership Service does NOT own**:
- User authentication (auth_service)
- Payment processing (payment_service)
- Subscription billing (subscription_service)
- Reward inventory (product_service)

### Concept 5: Event-Driven Point Allocation
- Points allocated via events from other services
- Order completion triggers point earning
- Activities across platform contribute to tiers
- Asynchronous processing ensures eventual consistency

---

## Business Rules (High-Level)

### Enrollment Rules
- **BR-MBR-001**: One active membership per user
- **BR-MBR-002**: Enrollment requires active user account
- **BR-MBR-003**: Initial tier is always Bronze
- **BR-MBR-004**: Enrollment bonus configurable per campaign
- **BR-MBR-005**: Membership ID format: mem_{uuid}

### Tier Rules
- **BR-TIR-001**: Tier upgrades immediate upon qualification
- **BR-TIR-002**: Tier downgrades at evaluation period end
- **BR-TIR-003**: Grace period of 30 days before demotion
- **BR-TIR-004**: Tier multiplier applies to all point earnings
- **BR-TIR-005**: Diamond tier has no expiration on benefits

### Point Rules
- **BR-PNT-001**: Minimum point transaction: 1 point
- **BR-PNT-002**: Points expire 12 months after earning
- **BR-PNT-003**: Point redemption cannot exceed balance
- **BR-PNT-004**: Negative point balance not allowed
- **BR-PNT-005**: Point transactions are atomic

### Benefit Rules
- **BR-BNF-001**: Benefits tied to current tier only
- **BR-BNF-002**: Some benefits have usage limits
- **BR-BNF-003**: Tier downgrade revokes higher-tier benefits
- **BR-BNF-004**: Benefit usage tracked per period
- **BR-BNF-005**: Some benefits stackable, others exclusive

### History Rules
- **BR-HST-001**: All actions logged immutably
- **BR-HST-002**: History includes initiator (user/system)
- **BR-HST-003**: Point changes include before/after balance
- **BR-HST-004**: Tier changes include previous/new tier
- **BR-HST-005**: History retention: 7 years minimum

### Event Publishing Rules
- **BR-EVT-001**: All membership mutations publish events
- **BR-EVT-002**: Event failures logged but don't block operations
- **BR-EVT-003**: Events include full context for subscribers
- **BR-EVT-004**: Events use ISO 8601 timestamps

### Data Consistency Rules
- **BR-CON-001**: Point operations use atomic transactions
- **BR-CON-002**: Tier evaluations use consistent snapshots
- **BR-CON-003**: Concurrent point operations handled safely
- **BR-CON-004**: History records immutable after creation

---

## Membership Service in the Ecosystem

### Upstream Dependencies
- **Account Service**: User validation
- **Subscription Service**: Premium membership tiers
- **PostgreSQL gRPC Service**: Persistent storage
- **NATS Event Bus**: Event publishing infrastructure
- **Consul**: Service discovery and health checks
- **API Gateway**: Request routing and authorization

### Downstream Consumers
- **Order Service**: Point earning integration
- **Product Service**: Reward catalog
- **Notification Service**: Member communications
- **Authorization Service**: Tier-based permissions
- **Analytics Service**: Membership metrics
- **Credit Service**: Credit-membership sync

### Integration Patterns
- **Synchronous REST**: CRUD operations via FastAPI endpoints
- **Asynchronous Events**: NATS for real-time updates
- **Service Discovery**: Consul for dynamic service location
- **Protocol Buffers**: PostgreSQL gRPC communication
- **Health Checks**: `/health` and `/health/detailed` endpoints

### Dependency Injection
- **Repository Pattern**: MembershipRepository for data access
- **Protocol Interfaces**: MembershipRepositoryProtocol, EventBusProtocol
- **Factory Pattern**: create_membership_service() for production instances
- **Mock-Friendly**: Protocols enable test doubles and mocks

---

## Success Metrics

### Membership Metrics
- **Enrollment Rate**: New memberships per period (target: +10%/month)
- **Active Rate**: % of memberships active (target: >80%)
- **Retention Rate**: Annual retention (target: >85%)

### Point Metrics
- **Points Earned**: Monthly points issued
- **Redemption Rate**: % of points redeemed (target: 40-60%)
- **Point Velocity**: Avg time to redemption

### Tier Metrics
- **Tier Distribution**: % at each tier level
- **Upgrade Rate**: Members advancing tiers (target: >15%)
- **Downgrade Rate**: Members losing tier (target: <10%)

### Performance Metrics
- **Enrollment Latency**: < 200ms p99
- **Point Operation Latency**: < 50ms p99
- **Balance Query Latency**: < 30ms p99
- **Tier Evaluation Latency**: < 500ms p99

### System Health Metrics
- **Service Uptime**: 99.9% availability
- **Database Connectivity**: 99.99% success rate
- **Event Publishing Success**: >99.5%

---

## Glossary

**Membership**: User's enrollment in the loyalty program
**Tier**: Membership level with associated benefits
**Points**: Loyalty currency earned and redeemable
**Tier Points**: Non-redeemable points counting toward tier qualification
**Reward Points**: Redeemable points for benefits
**Benefit**: Privilege or reward available to members
**Enrollment**: Initial membership creation
**Qualification Period**: Time window for tier evaluation
**Point Multiplier**: Tier-based factor applied to earned points
**Event Bus**: NATS messaging system for asynchronous event publishing
**Repository Pattern**: Data access abstraction layer
**Protocol Interface**: Abstract contract for dependency injection

---

**Document Version**: 1.0
**Last Updated**: 2025-12-19
**Maintained By**: Membership Service Team
