# Product Service - Domain Context

## Overview

The Product Service is the **commercial backbone** of the isA_user platform. It provides centralized product catalog management, pricing models, subscription lifecycle management, and usage tracking. Every billable service and resource in the system flows through the product domain.

**Business Context**: Enable scalable product and service monetization through flexible pricing models, subscription tiers, and usage-based billing. Product Service owns the "what" and "how much" of the system - defining available products, their costs, and tracking consumption.

**Core Value Proposition**: Transform platform services into billable products with tiered subscriptions, usage-based pricing, and intelligent cost tracking that scales from individual users to enterprise organizations.

---

## Business Taxonomy

### Core Entities

#### 1. Product
**Definition**: A sellable service, capability, or resource available on the platform.

**Business Purpose**:
- Define available services (AI models, storage, agents, APIs)
- Track product specifications and capabilities
- Manage product lifecycle (active, deprecated, discontinued)
- Enable product discovery and categorization

**Key Attributes**:
- Product ID (unique identifier)
- Category ID (reference to product category)
- Name, Description (display information)
- Product Type (model, storage, agent, mcp_tool, api_service, etc.)
- Provider (openai, anthropic, minio, internal)
- Specifications (model parameters, storage limits, etc.)
- Capabilities (list of product features)
- Is Active, Is Public (availability flags)
- Version, Release Date (versioning)
- Service Endpoint (integration URL)

**Product Types**:
- **MODEL**: AI language models (Claude, GPT, etc.)
- **MODEL_INFERENCE**: Model inference execution
- **STORAGE**: File storage services
- **STORAGE_MINIO**: MinIO object storage
- **AGENT**: AI agent services
- **AGENT_EXECUTION**: Agent execution runtime
- **MCP_TOOL**: Model Context Protocol tools
- **MCP_SERVICE**: MCP service integrations
- **API_SERVICE**: REST/gRPC API services
- **API_GATEWAY**: API gateway routing
- **NOTIFICATION**: Notification delivery
- **COMPUTATION**: Compute resources
- **DATA_PROCESSING**: Data transformation
- **INTEGRATION**: Third-party integrations

#### 2. Product Category
**Definition**: Hierarchical grouping of related products for organization and discovery.

**Business Purpose**:
- Organize products into logical groups
- Enable category-based filtering and search
- Support hierarchical category trees
- Improve product discoverability

**Key Attributes**:
- Category ID (unique identifier)
- Name, Description
- Parent Category ID (for hierarchy)
- Display Order (sorting)
- Is Active (visibility)
- Metadata (flexible attributes)

#### 3. Pricing Model
**Definition**: Cost structure and pricing rules for a product.

**Business Purpose**:
- Define how products are priced
- Support multiple pricing strategies
- Enable usage-based, subscription, and hybrid pricing
- Track pricing history and effective periods

**Key Attributes**:
- Pricing Model ID (unique identifier)
- Product ID (reference to product)
- Pricing Type (usage_based, subscription, one_time, freemium, hybrid)
- Unit Type (token, request, minute, GB, etc.)
- Base Unit Price, Input/Output Prices
- Monthly/Yearly Subscription Prices
- Free Tier Limit and Period
- Tier Pricing (volume discounts)
- Currency (USD, EUR, CNY, CREDIT)
- Effective From/Until (validity period)

**Pricing Types**:
- **USAGE_BASED**: Pay per unit consumed (tokens, requests, GB)
- **SUBSCRIPTION**: Fixed monthly/yearly fee
- **ONE_TIME**: Single purchase
- **FREEMIUM**: Free tier with paid upgrades
- **HYBRID**: Combination of subscription + usage

#### 4. Service Plan
**Definition**: Bundled subscription offering with included products, credits, and features.

**Business Purpose**:
- Create tiered subscription offerings
- Bundle products at discounted rates
- Define usage limits per plan tier
- Target different customer segments

**Key Attributes**:
- Plan ID (unique identifier)
- Name, Description
- Plan Tier (free, basic, pro, enterprise, custom)
- Monthly/Yearly Price, Setup Fee
- Included Credits, Credit Rollover
- Included Products (bundled products)
- Usage Limits (quotas per product)
- Features (enabled capabilities)
- Overage Pricing (beyond quota costs)
- Target Audience (individual, team, enterprise)
- Max Users (seat limits)

**Plan Tiers**:
- **FREE**: Zero cost, limited features
- **BASIC**: Entry-level paid tier
- **PRO**: Professional tier with expanded limits
- **ENTERPRISE**: Full-featured business tier
- **CUSTOM**: Tailored enterprise agreements

#### 5. User Subscription
**Definition**: Active subscription linking a user/organization to a service plan.

**Business Purpose**:
- Track user subscription status
- Manage billing cycles and renewals
- Handle subscription lifecycle (create, cancel, pause)
- Connect users to their entitlements

**Key Attributes**:
- Subscription ID (unique identifier)
- User ID (account reference)
- Organization ID (optional group reference)
- Plan ID, Plan Tier
- Status (active, trialing, past_due, canceled, paused)
- Billing Cycle (monthly, quarterly, yearly)
- Current Period Start/End
- Trial Start/End
- Cancel At Period End, Canceled At, Cancellation Reason
- Next Billing Date
- Payment Method ID (for billing integration)
- Usage This Period, Quota Limits

**Subscription States**:
- **ACTIVE**: Subscription in good standing
- **TRIALING**: Free trial period
- **PAST_DUE**: Payment failed, grace period
- **CANCELED**: User canceled
- **INCOMPLETE**: Setup not finished
- **INCOMPLETE_EXPIRED**: Setup expired
- **UNPAID**: Payment required
- **PAUSED**: Temporarily suspended

#### 6. Product Usage Record
**Definition**: Individual usage event tracking consumption of a product.

**Business Purpose**:
- Track detailed product consumption
- Enable usage-based billing
- Provide usage analytics and reporting
- Support audit and compliance

**Key Attributes**:
- Usage ID (unique identifier)
- User ID, Organization ID, Subscription ID
- Product ID, Pricing Model ID
- Usage Amount, Unit Type
- Unit Price, Total Cost, Currency
- Usage Timestamp
- Session ID, Request ID (traceability)
- Usage Details (context metadata)
- Is Free Tier, Is Included In Plan
- Billing Status (pending, billed, credited)

#### 7. Subscription Tier
**Definition**: Defines a subscription plan with credits and features (1 Credit = $0.00001 USD).

**Business Purpose**:
- Define subscription packages
- Allocate monthly credits
- Configure feature access
- Set usage limits per tier

**Key Attributes**:
- Tier ID (unique identifier)
- Tier Name, Tier Code
- Monthly/Yearly Price (USD)
- Monthly Credits
- Credit Rollover, Max Rollover Credits
- Target Audience
- Min/Max Seats, Per Seat Price
- Features, Usage Limits
- Support Level (community, email, priority, dedicated)
- Trial Days

#### 8. Cost Definition
**Definition**: Credit cost mapping for specific service operations.

**Business Purpose**:
- Define credit costs per operation
- Map external API costs to credits
- Apply margins and free tiers
- Enable fine-grained pricing control

**Key Attributes**:
- Cost ID (unique identifier)
- Product ID (optional reference)
- Service Type (model_inference, storage_minio, etc.)
- Provider, Model Name, Operation Type
- Cost Per Unit (credits)
- Unit Type, Unit Size
- Original Cost USD, Margin Percentage
- Free Tier Limit, Free Tier Period
- Effective From/Until

---

## Domain Scenarios

### Scenario 1: Product Catalog Browsing
**Actor**: Developer, User
**Trigger**: User wants to explore available products and pricing
**Flow**:
1. User navigates to product catalog
2. App calls `GET /api/v1/product/categories` to get category tree
3. User selects a category (e.g., "AI Models")
4. App calls `GET /api/v1/product/products?category_id=ai_models`
5. Product Service returns filtered product list
6. User selects a product to view details
7. App calls `GET /api/v1/product/products/{product_id}`
8. App calls `GET /api/v1/product/products/{product_id}/pricing`
9. User sees product specifications, capabilities, and pricing

**Outcome**: User discovers available products with full pricing transparency

### Scenario 2: Subscription Creation
**Actor**: User, Payment System
**Trigger**: User decides to subscribe to a plan
**Flow**:
1. User selects a subscription tier (e.g., "Pro")
2. User confirms billing cycle (monthly/yearly)
3. App calls `POST /api/v1/product/subscriptions` with user_id, plan_id
4. Product Service validates user exists via Account Client
5. Product Service fetches plan details from repository
6. Product Service creates UserSubscription with:
   - Status: ACTIVE
   - Current period calculated from billing cycle
   - Plan tier from service plan
7. Product Service saves subscription to database
8. Publishes `subscription.created` event to NATS
9. Billing Service receives event, creates invoice
10. Wallet Service allocates monthly credits
11. Returns created subscription to user

**Outcome**: User subscribed, credits allocated, billing scheduled

### Scenario 3: Usage-Based Product Consumption
**Actor**: User Application, Backend Service
**Trigger**: User consumes a usage-based product (AI model inference)
**Flow**:
1. Session Service calls model inference for user
2. After completion, calls `POST /api/v1/product/usage/record`:
   - user_id, product_id, usage_amount (tokens)
   - subscription_id (if applicable)
   - session_id, request_id (for tracing)
3. Product Service validates product exists and is active
4. If subscription_id provided, validates subscription is ACTIVE
5. Records usage in ProductUsageRecord table
6. Publishes `product.usage.recorded` event
7. Billing Service aggregates usage for invoicing
8. Wallet Service deducts credits if usage-based
9. Returns usage confirmation with cost breakdown

**Outcome**: Usage tracked, credits deducted, ready for billing

### Scenario 4: Subscription Status Change (Payment Failed)
**Actor**: Billing Service, Payment Provider
**Trigger**: Payment provider webhook indicates payment failed
**Flow**:
1. Billing Service receives payment.failed webhook
2. Billing Service publishes `payment_service.payment.completed` with status=failed
3. Product Service event handler receives event
4. Handler calls `update_subscription_status(subscription_id, PAST_DUE)`
5. Product Service updates subscription status in database
6. Publishes `subscription.status_changed` event:
   - old_status: "active", new_status: "past_due"
7. Notification Service sends payment failure email
8. User has grace period to update payment method

**Outcome**: Subscription marked past_due, user notified, grace period started

### Scenario 5: Usage Statistics Query
**Actor**: Admin Dashboard, Analytics Service
**Trigger**: Need to view usage patterns and trends
**Flow**:
1. Admin requests usage report for last 30 days
2. Dashboard calls `GET /api/v1/product/statistics/usage`:
   - user_id (optional), organization_id (optional)
   - product_id (optional)
   - start_date, end_date
3. Product Service queries usage records with filters
4. Aggregates by product, calculates totals
5. Returns statistics:
   - Total usage per product
   - Cost breakdown
   - Usage trends over time
6. Dashboard renders charts and reports

**Outcome**: Comprehensive usage visibility for billing and planning

### Scenario 6: Product Availability Check
**Actor**: API Gateway, Session Service
**Trigger**: Service needs to verify product access before use
**Flow**:
1. Session Service needs to use Claude model
2. Calls `GET /api/v1/product/products/{product_id}/availability`:
   - user_id, organization_id (optional)
3. Product Service fetches product
4. Validates product.is_active == true
5. (Future: Check user subscription, quota, permissions)
6. Returns availability response:
   - available: true/false
   - reason: explanation if unavailable
   - product: full product details if available
7. Session Service proceeds or returns error to user

**Outcome**: Access control enforced at product level

### Scenario 7: Subscription Cancellation Flow
**Actor**: User
**Trigger**: User decides to cancel subscription
**Flow**:
1. User initiates cancellation in app
2. App calls `PUT /api/v1/product/subscriptions/{id}/status`:
   - status: "canceled"
3. Product Service fetches current subscription
4. Validates subscription exists and belongs to user
5. Updates status to CANCELED
6. Sets canceled_at timestamp
7. Publishes `subscription.status_changed` event
8. Billing Service stops future charges
9. Wallet Service notes remaining credits
10. User retains access until current_period_end

**Outcome**: Subscription canceled, access continues until period end

---

## Domain Events

### Published Events

#### 1. subscription.created
**Trigger**: New subscription created via `POST /api/v1/product/subscriptions`
**Payload**:
- subscription_id: Unique subscription identifier
- user_id: User who subscribed
- organization_id: Optional organization
- plan_id: Selected plan
- plan_tier: Tier level (free, basic, pro, enterprise)
- billing_cycle: monthly, quarterly, yearly
- status: Initial status (typically "active")
- current_period_start: Billing period start
- current_period_end: Billing period end
- metadata: Additional context

**Subscribers**:
- **Billing Service**: Create invoice, schedule charges
- **Wallet Service**: Allocate monthly credits
- **Notification Service**: Send welcome email
- **Audit Service**: Log subscription event
- **Analytics Service**: Track conversion metrics

#### 2. subscription.status_changed
**Trigger**: Subscription status updated via `PUT /api/v1/product/subscriptions/{id}/status`
**Payload**:
- subscription_id: Subscription identifier
- user_id: Subscription owner
- organization_id: Optional organization
- plan_id: Current plan
- old_status: Previous status
- new_status: Updated status
- changed_at: Timestamp

**Subscribers**:
- **Billing Service**: Handle billing state changes
- **Notification Service**: Send status notification
- **Session Service**: Update access permissions
- **Audit Service**: Log status change
- **Analytics Service**: Track churn/retention

#### 3. product.usage.recorded
**Trigger**: Product usage recorded via `POST /api/v1/product/usage/record`
**Payload**:
- usage_record_id: Unique record identifier
- user_id: User who consumed
- organization_id: Optional organization
- subscription_id: Optional subscription
- product_id: Product consumed
- usage_amount: Quantity consumed
- session_id: Session context
- request_id: Request trace ID
- usage_details: Detailed breakdown
- timestamp: Usage time

**Subscribers**:
- **Billing Service**: Aggregate for invoicing
- **Wallet Service**: Deduct credits
- **Analytics Service**: Track usage patterns
- **Audit Service**: Log for compliance

### Subscribed Events

#### 1. payment_service.payment.completed
**Source**: payment_service
**Purpose**: Update subscription status based on payment result
**Payload**:
- user_id: User ID
- subscription_id: Related subscription
- payment_status: success/failed
- amount: Payment amount

**Handler Action**: If payment failed, update subscription to PAST_DUE

#### 2. wallet_service.wallet.insufficient_funds
**Source**: wallet_service
**Purpose**: Handle credit exhaustion
**Payload**:
- user_id: User ID
- wallet_id: Wallet ID
- required_credits: Amount needed
- available_credits: Current balance

**Handler Action**: Log warning, potentially notify user

#### 3. account_service.user.deleted
**Source**: account_service
**Purpose**: Clean up user subscriptions when account deleted
**Payload**:
- user_id: Deleted user ID
- deleted_at: Deletion timestamp

**Handler Action**: Cancel all user subscriptions, mark as deleted

---

## Core Concepts

### Product Lifecycle
1. **Definition**: Product created with specifications and pricing
2. **Activation**: Product marked is_active=true, is_public=true
3. **Usage**: Users consume product, usage tracked
4. **Deprecation**: deprecation_date set, users notified
5. **Deactivation**: is_active=false, no new usage allowed
6. **Archival**: Product retained for historical records

### Subscription Lifecycle
1. **Creation**: User subscribes to plan
2. **Trial**: Optional trial period (TRIALING status)
3. **Active**: Normal operational state (ACTIVE)
4. **Payment Issues**: Grace period (PAST_DUE)
5. **Cancellation**: User or system cancels (CANCELED)
6. **Pause**: Temporary suspension (PAUSED)
7. **Expiration**: Access ends at period_end

### Credit System
- **1 Credit = $0.00001 USD** (100,000 credits = $1 USD)
- Credits allocated monthly per subscription tier
- Usage deducts credits in real-time
- Optional credit rollover between periods
- Overage charged at defined rates

### Pricing Strategy
- **Freemium**: Free tier with limited usage, paid tiers for more
- **Usage-Based**: Pay only for what you consume
- **Subscription**: Fixed monthly/yearly fee for quota
- **Hybrid**: Base subscription + usage overage
- **Enterprise**: Custom pricing agreements

### Separation of Concerns
**Product Service owns**:
- Product catalog and metadata
- Pricing models and tiers
- Subscription lifecycle
- Usage tracking and recording
- Product availability checks

**Product Service does NOT own**:
- User identity (account_service)
- Payment processing (payment_service)
- Credit balance (wallet_service)
- Invoice generation (billing_service)
- Organization membership (organization_service)

---

## Business Rules (High-Level)

### Product Rules
- **BR-PRD-001**: Product ID must be unique across all products
- **BR-PRD-002**: Product must have valid category reference
- **BR-PRD-003**: Product type must be from defined ProductType enum
- **BR-PRD-004**: Only active products can be consumed
- **BR-PRD-005**: Deprecated products show warning but remain usable until deprecation_date
- **BR-PRD-006**: Product specifications stored as flexible JSONB

### Pricing Rules
- **BR-PRC-001**: Each product must have at least one pricing model
- **BR-PRC-002**: Free tier limit applies per billing period
- **BR-PRC-003**: Tier pricing applies volume discounts automatically
- **BR-PRC-004**: Currency must be from defined Currency enum
- **BR-PRC-005**: Effective dates prevent overlapping pricing models

### Subscription Rules
- **BR-SUB-001**: User can have only one active subscription per plan
- **BR-SUB-002**: Organization subscription applies to all members
- **BR-SUB-003**: Status transitions follow defined state machine
- **BR-SUB-004**: Canceled subscriptions retain access until period_end
- **BR-SUB-005**: Trial period cannot exceed 30 days
- **BR-SUB-006**: Billing cycle changes take effect at next renewal

### Usage Rules
- **BR-USG-001**: Usage can only be recorded for existing products
- **BR-USG-002**: Subscription usage requires ACTIVE subscription
- **BR-USG-003**: Free tier usage does not deduct credits
- **BR-USG-004**: Usage records are immutable after creation
- **BR-USG-005**: Usage amount must be positive (> 0)

### Event Rules
- **BR-EVT-001**: All subscription changes publish events
- **BR-EVT-002**: Usage records above threshold trigger events
- **BR-EVT-003**: Event publishing failures logged but don't block operations
- **BR-EVT-004**: Events include full context for subscribers

---

## Product Service in the Ecosystem

### Upstream Dependencies
- **Account Service**: User validation and identity
- **Organization Service**: Organization validation
- **PostgreSQL gRPC Service**: Persistent storage
- **NATS Event Bus**: Event publishing
- **Consul**: Service discovery

### Downstream Consumers
- **Billing Service**: Invoice generation, payment scheduling
- **Wallet Service**: Credit allocation and deduction
- **Session Service**: Usage tracking integration
- **Storage Service**: Storage quota enforcement
- **Media Service**: Media processing billing
- **Memory Service**: Memory usage tracking
- **Notification Service**: Subscription notifications
- **Audit Service**: Usage and subscription auditing
- **Analytics Service**: Business metrics

### Integration Patterns
- **Synchronous REST**: CRUD and query operations
- **Asynchronous Events**: NATS for real-time updates
- **Service Discovery**: Consul for dynamic location
- **Health Checks**: `/health` endpoint

### Dependency Injection
- **Repository Pattern**: ProductRepository for data access
- **Protocol Interfaces**: ProductRepositoryProtocol, EventBusProtocol
- **Factory Pattern**: create_product_service() for production instances
- **Client Abstractions**: AccountClient, OrganizationClient protocols

---

## Success Metrics

### Product Metrics
- **Product Catalog Size**: Total active products
- **Product Discovery Rate**: Products viewed / total visits
- **Product Activation Rate**: New products activated per month
- **Deprecation Compliance**: Users migrated before deprecation

### Subscription Metrics
- **Conversion Rate**: Free → paid tier conversions
- **Monthly Recurring Revenue (MRR)**: Total subscription revenue
- **Annual Recurring Revenue (ARR)**: Yearly revenue projection
- **Churn Rate**: Cancellations / total subscriptions
- **Average Revenue Per User (ARPU)**: Revenue / active subscribers

### Usage Metrics
- **Daily Active Usage**: Usage records per day
- **Usage by Product**: Consumption distribution
- **Free Tier Utilization**: Free tier limit usage percentage
- **Overage Revenue**: Usage beyond subscription quotas

### Performance Metrics
- **Subscription Creation Latency**: < 500ms
- **Usage Recording Latency**: < 100ms
- **Catalog Query Latency**: < 150ms
- **Event Publishing Success**: > 99.5%

---

## Glossary

**Product**: Sellable service or resource on the platform
**Product Category**: Hierarchical grouping of products
**Pricing Model**: Cost structure for a product
**Service Plan**: Bundled subscription offering
**Subscription**: User's active plan enrollment
**Usage Record**: Individual consumption event
**Subscription Tier**: Plan level with credits and features
**Cost Definition**: Credit cost mapping for operations
**Credit**: Platform currency unit (1 credit = $0.00001 USD)
**Billing Cycle**: Payment frequency (monthly, yearly)
**Free Tier**: Complimentary usage quota
**Overage**: Usage beyond included quota
**Plan Tier**: Subscription level (free, basic, pro, enterprise)
**Churn**: Customer subscription cancellation
**MRR**: Monthly Recurring Revenue
**ARR**: Annual Recurring Revenue
**ARPU**: Average Revenue Per User

---

**Document Version**: 1.0
**Last Updated**: 2025-12-16
**Maintained By**: Product Service Team
