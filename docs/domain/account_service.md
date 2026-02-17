# Account Service - Domain Context

## Overview

The Account Service is the **identity anchor** for the entire isA_user platform. It provides centralized user identity management, profile data, preferences, and account lifecycle orchestration. Every user in the system begins with an account record.

**Business Context**: Enable secure, scalable identity management that serves as the foundation for all user-centric services. Account Service owns the "who" of the system - ensuring every user has a unique, verifiable identity with associated profile data and preferences.

**Core Value Proposition**: Transform disparate user data into a unified identity layer with idempotent account creation, intelligent profile management, and event-driven synchronization across the platform.

---

## Business Taxonomy

### Core Entities

#### 1. Account (User Identity)
**Definition**: A unique user identity record representing an individual person's presence in the system.

**Business Purpose**:
- Establish single source of truth for user identity
- Track account lifecycle (creation, activation, deactivation, deletion)
- Maintain basic profile information
- Store user preferences and settings

**Key Attributes**:
- User ID (unique identifier, typically from auth system)
- Email (unique contact and login identifier)
- Name (display name for the user)
- Is Active (account status - active or deactivated)
- Preferences (JSONB - flexible user settings)
- Created At (account registration timestamp)
- Updated At (last profile modification timestamp)

**Account States**:
- **Active**: Normal operational state, user can access system
- **Inactive**: Deactivated by admin or user, account suspended
- **Deleted**: Soft-deleted, marked inactive with deletion reason

#### 2. User Profile
**Definition**: Extended identity information and personal details for a user account.

**Business Purpose**:
- Provide rich user context for other services
- Enable personalization and customization
- Support user-facing profile displays
- Track identity changes over time

**Key Attributes**:
- User ID (reference to account)
- Email (validated, unique)
- Name (display name, updatable)
- Profile completeness indicator
- Last profile update timestamp

#### 3. Account Preferences
**Definition**: User-specific configuration settings stored as flexible JSONB data.

**Business Purpose**:
- Store user customization choices
- Enable feature flags and experimental features
- Track communication preferences
- Support service-specific settings

**Examples**:
```json
{
  "theme": "dark",
  "language": "en",
  "timezone": "America/Los_Angeles",
  "notifications": {
    "email": true,
    "push": false
  },
  "feature_flags": {
    "beta_features": true
  }
}
```

**Key Attributes**:
- User ID (reference to account)
- Preferences (flexible JSONB dictionary)
- Updated At (last preference change)

#### 4. Account Summary
**Definition**: Lightweight account representation for list views and search results.

**Business Purpose**:
- Optimize list/search endpoints performance
- Provide essential account info without full profile
- Enable efficient batch operations

**Key Attributes**:
- User ID
- Email
- Name
- Is Active
- Created At

---

## Domain Scenarios

### Scenario 1: Idempotent Account Creation
**Actor**: Auth Service, New User
**Trigger**: User completes registration or first login via OAuth
**Flow**:
1. Auth Service generates unique user_id after successful authentication
2. Auth Service calls `/api/v1/accounts/ensure` with user_id, email, name
3. Account Service checks if user_id already exists:
   - **If exists**: Returns existing account (idempotent behavior)
   - **If new**: Creates account record in PostgreSQL
4. Account Service validates email uniqueness
5. Account Service creates default preferences (empty JSONB)
6. Publishes `user.created` event to NATS
7. Returns complete account profile to Auth Service
8. Subscription Service listens to `user.created` and creates free tier subscription
9. Wallet Service creates initial wallet for user

**Outcome**: User account guaranteed to exist, no duplicate accounts, downstream services notified

### Scenario 2: Profile Update and Change Tracking
**Actor**: User, Mobile App
**Trigger**: User updates their name or email in profile settings
**Flow**:
1. User updates name from "John Doe" to "John Smith" via mobile app
2. App calls `PUT /api/v1/accounts/profile/{user_id}` with updated fields
3. Account Service validates:
   - Account exists and is active
   - Email uniqueness (if email changed)
   - Name meets length requirements
4. Account Service updates PostgreSQL record
5. Sets `updated_at` timestamp
6. Publishes `user.profile_updated` event with changed fields list
7. Returns updated profile to app
8. Audit Service records change for compliance
9. Search Service reindexes user profile

**Outcome**: Profile updated, changes tracked, audit trail created, other services synchronized

### Scenario 3: Account Search and Discovery
**Actor**: Admin, Support Agent
**Trigger**: Need to find user account by name or email
**Flow**:
1. Admin searches for "john@example.com" via admin dashboard
2. Dashboard calls `GET /api/v1/accounts/search?query=john@example.com&limit=50`
3. Account Service performs ILIKE search on name and email fields
4. Filters only active accounts (unless `include_inactive=true`)
5. Returns list of matching account summaries ordered by creation date
6. Admin selects the correct user
7. Dashboard fetches full profile via `GET /api/v1/accounts/profile/{user_id}`
8. Admin views complete account details

**Outcome**: Efficient account discovery with partial text search, privacy-preserving results

### Scenario 4: Account Deactivation (Soft Delete)
**Actor**: Admin, Compliance System
**Trigger**: Account flagged for policy violation or user requests deletion
**Flow**:
1. Admin identifies account for deactivation: user_12345
2. Admin calls `PUT /api/v1/accounts/status/{user_id}` with `is_active: false, reason: "Policy violation"`
3. Account Service validates account exists
4. Sets `is_active = false` in PostgreSQL
5. Updates `updated_at` timestamp
6. Publishes `user.status_changed` event with reason
7. Subscription Service receives event, pauses subscription
8. Storage Service restricts file access
9. Session Service invalidates all active sessions
10. Returns success confirmation to admin

**Outcome**: Account immediately deactivated, all services synchronized, user cannot access system

### Scenario 5: Bulk Account Listing with Pagination
**Actor**: Analytics Service, Reporting System
**Trigger**: Generate monthly active user report
**Flow**:
1. Analytics calls `GET /api/v1/accounts?page=1&page_size=100&is_active=true`
2. Account Service queries PostgreSQL with LIMIT/OFFSET
3. Applies `is_active = true` filter
4. Orders results by `created_at DESC`
5. Returns page 1 (accounts 1-100) with pagination metadata
6. Analytics processes page 1
7. Analytics fetches page 2, page 3, etc. until all pages retrieved
8. Generates aggregate statistics

**Outcome**: Efficient paginated access to account data, prevents memory overflow, enables large-scale analytics

### Scenario 6: Preferences Management
**Actor**: User, Web Application
**Trigger**: User changes theme from light to dark mode
**Flow**:
1. User toggles theme preference in settings
2. App calls `PUT /api/v1/accounts/preferences/{user_id}` with `{"theme": "dark"}`
3. Account Service fetches current preferences: `{"language": "en"}`
4. Merges new preferences: `{"language": "en", "theme": "dark"}`
5. Updates JSONB preferences field in PostgreSQL
6. Sets `updated_at` timestamp
7. Returns success confirmation
8. App immediately applies dark theme
9. Subsequent logins load dark theme preference

**Outcome**: Flexible preference storage without schema migrations, instant personalization

### Scenario 7: Account Statistics and Health Monitoring
**Actor**: Monitoring Dashboard, DevOps
**Trigger**: Scheduled health check every 5 minutes
**Flow**:
1. Monitoring calls `GET /api/v1/accounts/stats`
2. Account Service executes concurrent PostgreSQL queries:
   - Total accounts count
   - Active accounts count
   - Inactive accounts count
   - New registrations (last 7 days)
   - New registrations (last 30 days)
3. Returns aggregated statistics:
   ```json
   {
     "total_accounts": 15420,
     "active_accounts": 14985,
     "inactive_accounts": 435,
     "recent_registrations_7d": 245,
     "recent_registrations_30d": 1089
   }
   ```
4. Monitoring dashboard displays charts
5. Alerts triggered if active accounts drop >5%

**Outcome**: Real-time account health visibility, proactive issue detection

---

## Domain Events

### Published Events

#### 1. user.created
**Trigger**: New account successfully created via `/api/v1/accounts/ensure`
**Payload**:
- user_id: Unique user identifier
- email: User email address
- name: User display name
- subscription_plan: Initial subscription tier (deprecated, now handled by subscription_service)
- created_at: Account creation timestamp

**Subscribers**:
- **Subscription Service**: Create default free tier subscription
- **Wallet Service**: Initialize user wallet
- **Audit Service**: Log account creation event
- **Analytics Service**: Track user acquisition metrics
- **Organization Service**: Check for pending invitations

#### 2. user.profile_updated
**Trigger**: User profile data modified via `PUT /api/v1/accounts/profile/{user_id}`
**Payload**:
- user_id: User identifier
- email: Updated email (if changed)
- name: Updated name (if changed)
- updated_fields: List of modified fields (e.g., ["name", "email"])
- updated_at: Update timestamp

**Subscribers**:
- **Audit Service**: Track profile changes for compliance
- **Search Service**: Reindex user profile
- **Notification Service**: Send profile update confirmation email
- **Session Service**: Update cached user display name

#### 3. user.deleted
**Trigger**: Account soft-deleted via `DELETE /api/v1/accounts/profile/{user_id}`
**Payload**:
- user_id: User identifier
- email: User email (if available)
- reason: Deletion reason ("user_requested", "policy_violation", "admin_action")
- deleted_at: Deletion timestamp

**Subscribers**:
- **Subscription Service**: Cancel active subscriptions
- **Storage Service**: Archive or delete user files
- **Session Service**: Invalidate all sessions
- **Audit Service**: Log deletion for compliance (GDPR)
- **Billing Service**: Process final invoice
- **Organization Service**: Remove from organizations

#### 4. user.status_changed
**Trigger**: Account activation status changed via `PUT /api/v1/accounts/status/{user_id}`
**Payload**:
- user_id: User identifier
- email: User email
- is_active: New status (true = activated, false = deactivated)
- reason: Status change reason
- changed_at: Timestamp
- changed_by: Actor who triggered change (admin ID or "system")

**Subscribers**:
- **Session Service**: Invalidate sessions if deactivated
- **Subscription Service**: Pause/resume subscription
- **Audit Service**: Log status change
- **Notification Service**: Send account status notification
- **Compliance Service**: Track account status for regulatory reporting

#### 5. user.subscription_changed (Deprecated)
**Trigger**: User subscription plan changed (now handled by subscription_service)
**Status**: DEPRECATED - kept for backward compatibility
**Migration Path**: Subscription Service now publishes `subscription.updated` event

**Note**: This event is being phased out. Account Service no longer manages subscription data directly.

### Subscribed Events

#### 1. payment.completed
**Source**: billing_service
**Purpose**: Update user subscription status when payment is processed

**Payload**:
- user_id: User ID
- payment_type: Type of payment (subscription/one_time)
- subscription_plan: New subscription plan (if applicable)
- amount: Payment amount

**Handler Action**: Updates user's subscription status if payment_type is "subscription"

#### 2. organization.member_added
**Source**: organization_service
**Purpose**: Track when user is added to an organization

**Payload**:
- organization_id: Organization ID
- user_id: User ID
- role: User's role in organization

**Handler Action**: Log membership for tracking (future: update user's default organization)

#### 3. wallet.created
**Source**: wallet_service
**Purpose**: Confirm wallet creation for new users

**Payload**:
- user_id: User ID
- wallet_id: Wallet ID
- currency: Wallet currency

**Handler Action**: Log confirmation for debugging account creation flows

#### 4. subscription_service.subscription.created
**Source**: subscription_service
**Purpose**: Update user's subscription status when they subscribe

**Payload**:
- user_id: User ID
- subscription_id: Subscription ID
- tier_code: Subscription tier
- credits_allocated: Monthly credits

**Handler Action**: Updates user's subscription_id and subscription_status in account record

#### 5. subscription_service.subscription.canceled
**Source**: subscription_service
**Purpose**: Reset user's subscription status when cancelled

**Payload**:
- user_id: User ID
- subscription_id: Subscription ID
- reason: Cancellation reason

**Handler Action**: Resets user's subscription to free tier

#### 6. organization_service.organization.deleted
**Source**: organization_service
**Purpose**: Remove organization association from users when org is deleted

**Payload**:
- organization_id: Organization ID

**Handler Action**: Removes organization_id from all affected user accounts

---

## Core Concepts

### Account Lifecycle
1. **Creation**: User registers → Auth Service authenticates → Account Service ensures account exists
2. **Activation**: Account created with `is_active = true` by default
3. **Profile Updates**: User or admin updates profile fields (name, email, preferences)
4. **Deactivation**: Admin or system sets `is_active = false` (soft delete)
5. **Deletion**: Same as deactivation (account preserved for audit trail)
6. **Reactivation**: Admin can restore deactivated account by setting `is_active = true`

### Identity Guarantees
- **Unique User ID**: Every account has unique user_id (typically from auth provider)
- **Unique Email**: Email addresses are unique across all active accounts
- **Idempotent Creation**: Multiple calls to `/api/v1/accounts/ensure` with same user_id are safe
- **Referential Integrity**: Other services reference user_id as foreign key

### Separation of Concerns
**Account Service owns**:
- User identity (user_id, email, name)
- Account status (is_active)
- User preferences (JSONB settings)
- Profile lifecycle events

**Account Service does NOT own**:
- Authentication/authorization (auth_service)
- Subscription/billing data (subscription_service, billing_service)
- Credits/balance (wallet_service)
- Organization membership (organization_service)
- User devices (device_service)

### Preferences Architecture
- Stored as PostgreSQL JSONB for flexibility
- No fixed schema - services define their own preference keys
- Merge strategy on updates (new keys added, existing keys updated)
- GIN index on preferences field for efficient querying
- Default empty object `{}` on account creation

### Event-Driven Synchronization
- All account mutations publish events to NATS
- Downstream services subscribe to relevant events
- Account Service does not make synchronous calls to other services
- Ensures loose coupling and horizontal scalability

---

## Business Rules (High-Level)

### Account Creation Rules
- **BR-ACC-001**: User ID must be unique across all accounts (enforced by primary key)
- **BR-ACC-002**: Email must be unique across all active accounts
- **BR-ACC-003**: Email format must be valid (basic regex validation)
- **BR-ACC-004**: Name must be non-empty and between 1-255 characters
- **BR-ACC-005**: Default `is_active = true` on creation
- **BR-ACC-006**: Default preferences is empty JSONB `{}`
- **BR-ACC-007**: Multiple calls to `/ensure` with same user_id are idempotent

### Profile Update Rules
- **BR-PRO-001**: Only active accounts can update profiles
- **BR-PRO-002**: Email changes must maintain uniqueness constraint
- **BR-PRO-003**: Name changes must meet length requirements (1-255 chars)
- **BR-PRO-004**: Empty string values rejected for required fields
- **BR-PRO-005**: Updated fields list tracked in `user.profile_updated` event
- **BR-PRO-006**: `updated_at` timestamp automatically set on every update

### Preferences Rules
- **BR-PRF-001**: Preferences stored as JSONB dictionary
- **BR-PRF-002**: Preference updates are merge operations (not replace)
- **BR-PRF-003**: Invalid JSON rejected with 400 Bad Request
- **BR-PRF-004**: Preferences can be empty `{}`
- **BR-PRF-005**: No size limit enforced (PostgreSQL JSONB handles large documents)

### Account Status Rules
- **BR-STS-001**: Only admins can change account status (authorization checked by gateway)
- **BR-STS-002**: Deactivation sets `is_active = false` (soft delete)
- **BR-STS-003**: Deactivation reason is optional but recommended
- **BR-STS-004**: Deactivated accounts excluded from default list/search results
- **BR-STS-005**: Deactivated accounts can be reactivated by setting `is_active = true`
- **BR-STS-006**: Status changes always publish `user.status_changed` event

### Search and Query Rules
- **BR-QRY-001**: Default query returns only `is_active = true` accounts
- **BR-QRY-002**: Search uses ILIKE for case-insensitive partial matching
- **BR-QRY-003**: Search applies to both name and email fields
- **BR-QRY-004**: Pagination enforced with max page_size of 100
- **BR-QRY-005**: Results ordered by `created_at DESC` by default
- **BR-QRY-006**: Email lookup is exact match, case-insensitive

### Event Publishing Rules
- **BR-EVT-001**: All account mutations publish corresponding events
- **BR-EVT-002**: Event publishing failures logged but don't block operations
- **BR-EVT-003**: Events include full context needed by subscribers
- **BR-EVT-004**: Events use ISO 8601 timestamps
- **BR-EVT-005**: user.created published exactly once per new account

### Data Consistency Rules
- **BR-CON-001**: Account creation is atomic (PostgreSQL transaction)
- **BR-CON-002**: Profile updates are atomic
- **BR-CON-003**: Concurrent updates handled by optimistic locking (updated_at check)
- **BR-CON-004**: Soft delete preserves data for audit trail
- **BR-CON-005**: No hard deletes allowed (GDPR compliance via anonymization, not deletion)

---

## Account Service in the Ecosystem

### Upstream Dependencies
- **Auth Service**: Provides authenticated user_id for account creation
- **PostgreSQL gRPC Service**: Persistent storage for account data
- **NATS Event Bus**: Event publishing infrastructure
- **Consul**: Service discovery and health checks
- **API Gateway**: Request routing and authorization

### Downstream Consumers
- **Subscription Service**: User subscription management
- **Billing Service**: Invoice generation and payment processing
- **Wallet Service**: User balance and credits
- **Organization Service**: Family/group memberships
- **Device Service**: User device registration
- **Session Service**: Active session management
- **Storage Service**: User file permissions
- **Media Service**: Photo/video ownership
- **Memory Service**: User-specific memory storage
- **Audit Service**: Compliance and change tracking
- **Analytics Service**: User metrics and reporting
- **Notification Service**: User communication

### Integration Patterns
- **Synchronous REST**: CRUD operations via FastAPI endpoints
- **Asynchronous Events**: NATS for real-time updates
- **Service Discovery**: Consul for dynamic service location
- **Protocol Buffers**: PostgreSQL gRPC communication
- **Health Checks**: `/health` and `/health/detailed` endpoints

### Dependency Injection
- **Repository Pattern**: AccountRepository for data access
- **Protocol Interfaces**: AccountRepositoryProtocol, EventBusProtocol
- **Factory Pattern**: create_account_service() for production instances
- **Mock-Friendly**: Protocols enable test doubles and mocks

---

## Success Metrics

### Account Quality Metrics
- **Profile Completeness**: % of accounts with all recommended fields populated
- **Email Verification Rate**: % of accounts with verified email addresses
- **Active Account Ratio**: active_accounts / total_accounts (target: >95%)
- **Duplicate Account Rate**: Accounts with potential duplicate emails (target: <0.1%)

### Performance Metrics
- **Account Creation Latency**: Time from /ensure call to response (target: <200ms)
- **Profile Fetch Latency**: Time to retrieve account by ID (target: <50ms)
- **Search Query Latency**: Time for search results (target: <150ms)
- **Batch List Latency**: Time for paginated list (100 items) (target: <100ms)

### Availability Metrics
- **Service Uptime**: Account Service availability (target: 99.9%)
- **Database Connectivity**: PostgreSQL connection success rate (target: 99.99%)
- **Event Publishing Success**: % of events successfully published (target: >99.5%)

### Business Metrics
- **Daily New Accounts**: New registrations per day
- **Monthly Active Users**: Accounts accessed in last 30 days
- **Account Churn Rate**: Deactivations / total accounts per month
- **Account Growth Rate**: Net new accounts per month

### System Health Metrics
- **PostgreSQL Query Performance**: Average query execution time
- **NATS Event Throughput**: Events published per second
- **Consul Registration Health**: Service registration success rate
- **API Gateway Response Times**: End-to-end request latency

---

## Glossary

**Account**: Core identity record for a user in the system
**User ID**: Unique identifier for an account (typically from auth provider)
**Profile**: Extended identity information (name, email, preferences)
**Preferences**: User-specific settings stored as JSONB
**Active Account**: Account with `is_active = true`, can access system
**Inactive Account**: Account with `is_active = false`, suspended or deleted
**Soft Delete**: Marking account inactive rather than removing data
**Idempotent**: Operation that produces same result when called multiple times
**Account Ensure**: Idempotent operation guaranteeing account exists
**JSONB**: PostgreSQL JSON binary format with indexing and querying capabilities
**GIN Index**: PostgreSQL Generalized Inverted Index for JSONB fields
**ILIKE**: PostgreSQL case-insensitive partial string matching
**Event Bus**: NATS messaging system for asynchronous event publishing
**Identity Anchor**: Single source of truth for user identity across platform
**Repository Pattern**: Data access abstraction layer
**Protocol Interface**: Abstract contract for dependency injection

---

**Document Version**: 1.1
**Last Updated**: 2025-12-15
**Maintained By**: Account Service Team
