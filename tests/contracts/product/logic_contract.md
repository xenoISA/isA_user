# Product Service Logic Contract

## Overview

This document defines the business rules and logic contracts for the Product Service.
All tests MUST validate these rules to ensure correct behavior.

**Service**: product_service
**Port**: 8215
**Version**: 1.0.0
**Last Updated**: 2025-12-16

---

## Business Rules

### BR-PRD-001: Product ID Uniqueness
**Rule**: Product ID must be unique across all products
**Validation**:
- `product_id` is the primary identifier
- Duplicate `product_id` returns error
**Test**: Attempt to create two products with same `product_id`

### BR-PRD-002: Product Type Validation
**Rule**: Product type must be a valid ProductType enum value
**Valid Values**:
- `model`, `model_inference`, `storage`, `storage_minio`
- `agent`, `agent_execution`, `mcp_tool`, `mcp_service`
- `api_service`, `api_gateway`, `notification`, `computation`
- `data_processing`, `integration`, `other`
**Test**: Create product with invalid `product_type` returns 400

### BR-PRD-003: Product Active Status
**Rule**: Only active products can be consumed
**Validation**:
- Products with `is_active=false` return `available=false`
- Product queries default to `is_active=true`
**Test**: Check availability of inactive product returns unavailable

### BR-PRD-004: Product Category Reference
**Rule**: Products should belong to a valid category
**Validation**:
- `category_id` references product category
- Categories derived from products table
**Test**: Products list shows correct category assignment

---

## Subscription Rules

### BR-SUB-001: Subscription Creation Validation
**Rule**: Subscription requires valid user_id and plan_id
**Validation**:
- `user_id` must be non-empty string
- `plan_id` must reference existing service plan
- Invalid plan_id returns error
**Test**: Create subscription with missing fields returns 400

### BR-SUB-002: Subscription Status Enum Validation
**Rule**: Subscription status must be a valid SubscriptionStatus enum
**Valid Values**:
- `active` - Subscription in good standing
- `trialing` - Free trial period
- `past_due` - Payment failed, grace period
- `canceled` - User canceled
- `incomplete` - Setup not finished
- `incomplete_expired` - Setup expired
- `unpaid` - Payment required
- `paused` - Temporarily suspended
**Test**: Update status with invalid value returns 400

### BR-SUB-003: Billing Cycle Enum Validation
**Rule**: Billing cycle must be a valid BillingCycle enum
**Valid Values**:
- `monthly` - 30-day billing cycle
- `quarterly` - 90-day billing cycle
- `yearly` - 365-day billing cycle
- `one_time` - Single payment
**Test**: Create subscription with invalid billing_cycle returns 400

### BR-SUB-004: Subscription Period Calculation
**Rule**: Current period end calculated from billing cycle
**Calculation**:
- `monthly`: current_period_start + 30 days
- `quarterly`: current_period_start + 90 days
- `yearly`: current_period_start + 365 days
- `one_time`: current_period_start + 30 days (default)
**Test**: Verify period_end matches billing cycle

### BR-SUB-005: Subscription User Validation
**Rule**: User validation is fail-open
**Behavior**:
- If AccountClient available, validate user exists
- If validation fails, log warning and proceed
- Enables testing without account_service dependency
**Test**: Create subscription with non-existent user succeeds

### BR-SUB-006: Organization Validation
**Rule**: Organization validation is fail-open
**Behavior**:
- If OrganizationClient available, validate org exists
- If validation fails, log warning and proceed
- `organization_id` is optional
**Test**: Create subscription with organization_id succeeds

### BR-SUB-007: Subscription Status Change Event
**Rule**: Status changes publish events
**Event**: `subscription.status_changed`
**Payload**:
- `subscription_id`, `user_id`, `organization_id`
- `plan_id`, `old_status`, `new_status`
- `changed_at`
**Test**: Update status publishes event with correct payload

### BR-SUB-008: Subscription Not Found
**Rule**: Operations on non-existent subscription return 404
**Validation**:
- `GET /subscriptions/{id}` returns 404 if not found
- `PUT /subscriptions/{id}/status` returns 404 if not found
**Test**: Get non-existent subscription returns 404

---

## Usage Tracking Rules

### BR-USG-001: Usage Recording Validation
**Rule**: Usage requires user_id, product_id, and positive amount
**Validation**:
- `user_id` must be non-empty string
- `product_id` must be non-empty string
- `usage_amount` must be > 0
**Test**: Record usage with missing fields returns error

### BR-USG-002: Usage Amount Positive
**Rule**: Usage amount must be positive
**Validation**:
- `usage_amount` > 0
- Zero or negative values rejected
**Test**: Record usage with amount=0 returns error

### BR-USG-003: Product Validation for Usage
**Rule**: Product must exist to record usage
**Validation**:
- Product fetched by `product_id`
- Non-existent product returns error response
**Test**: Record usage for non-existent product returns error

### BR-USG-004: Subscription Status for Usage
**Rule**: If subscription provided, it must be ACTIVE
**Validation**:
- If `subscription_id` provided, fetch subscription
- Non-existent subscription returns error
- Non-active subscription returns error
**Test**: Record usage with inactive subscription returns error

### BR-USG-005: Usage User Validation
**Rule**: User validation is fail-open for usage
**Behavior**:
- If AccountClient available, validate user
- If validation fails, log warning and proceed
**Test**: Record usage with non-existent user succeeds

### BR-USG-006: Usage Event Publishing
**Rule**: Usage recording publishes event
**Event**: `product.usage.recorded`
**Payload**:
- `usage_record_id`, `user_id`, `organization_id`
- `subscription_id`, `product_id`, `usage_amount`
- `session_id`, `request_id`, `usage_details`
- `timestamp`
**Test**: Record usage publishes event with correct payload

### BR-USG-007: Usage Response Format
**Rule**: Usage response includes confirmation
**Response Fields**:
- `success`: boolean
- `message`: string
- `usage_record_id`: string (if successful)
- `product`: object (if successful)
- `recorded_amount`: float
- `timestamp`: datetime
**Test**: Record usage returns correct response format

---

## Pricing Rules

### BR-PRC-001: Pricing Query by Product
**Rule**: Pricing queried by product_id
**Validation**:
- Active product required
- Non-existent product returns None
**Test**: Get pricing for non-existent product returns 404

### BR-PRC-002: Tiered Pricing Structure
**Rule**: Pricing includes tier structure
**Tier Structure**:
- Base tier: 0-1000 units at base_price
- Standard tier: 1001-10000 units at 90% of base
- Premium tier: 10001+ units at 80% of base
**Test**: Pricing response includes 3 tiers

### BR-PRC-003: Optional User Personalization
**Rule**: Pricing can be personalized for user/subscription
**Parameters**:
- `user_id`: optional user context
- `subscription_id`: optional subscription context
- Future: Apply plan discounts based on subscription
**Test**: Pricing with user_id returns response

---

## Availability Rules

### BR-AVL-001: Availability Check Requires User
**Rule**: Availability check requires user_id
**Validation**:
- `user_id` query parameter required
- Missing user_id may still return result
**Test**: Check availability with user_id succeeds

### BR-AVL-002: Inactive Product Unavailable
**Rule**: Inactive products return unavailable
**Response**:
- `available`: false
- `reason`: "Product is not active"
**Test**: Check availability of inactive product

### BR-AVL-003: Non-Existent Product Unavailable
**Rule**: Non-existent products return unavailable
**Response**:
- `available`: false
- `reason`: "Product not found"
**Test**: Check availability of non-existent product

### BR-AVL-004: Available Product Response
**Rule**: Available products include product info
**Response**:
- `available`: true
- `product`: full product object
**Test**: Check availability of active product

---

## Event Rules

### BR-EVT-001: Subscription Created Event
**Rule**: Subscription creation publishes event
**Event**: `product_service.subscription.created`
**Trigger**: Successful `POST /api/v1/product/subscriptions`
**Payload**:
- `subscription_id`, `user_id`, `organization_id`
- `plan_id`, `plan_tier`, `billing_cycle`
- `status`, `current_period_start`, `current_period_end`
- `metadata`, `created_at`
**Subscribers**: billing_service, wallet_service, notification_service

### BR-EVT-002: Subscription Status Changed Event
**Rule**: Status update publishes event
**Event**: `product_service.subscription.status_changed`
**Trigger**: Successful `PUT /api/v1/product/subscriptions/{id}/status`
**Payload**:
- `subscription_id`, `user_id`, `organization_id`
- `plan_id`, `old_status`, `new_status`
- `changed_at`
**Subscribers**: billing_service, notification_service, session_service

### BR-EVT-003: Product Usage Recorded Event
**Rule**: Usage recording publishes event
**Event**: `product_service.product.usage.recorded`
**Trigger**: Successful `POST /api/v1/product/usage/record`
**Payload**:
- `usage_record_id`, `user_id`, `organization_id`
- `subscription_id`, `product_id`, `usage_amount`
- `session_id`, `request_id`, `usage_details`
- `timestamp`
**Subscribers**: billing_service, wallet_service, analytics_service

### BR-EVT-004: Event Publishing Fail-Safe
**Rule**: Event failures don't block operations
**Behavior**:
- If event_bus is None, skip publishing
- If publishing fails, log error and continue
- Operation success is independent of event publishing
**Test**: Operations succeed without event bus

### BR-EVT-005: Payment Completed Handler
**Rule**: Handle payment.completed events
**Source**: payment_service
**Pattern**: `payment_service.payment.completed`
**Behavior**:
- If payment failed, update subscription to PAST_DUE
- Log event handling for debugging
**Test**: Payment failed event updates subscription status

### BR-EVT-006: User Deleted Handler
**Rule**: Handle user.deleted events
**Source**: account_service
**Pattern**: `account_service.user.deleted`
**Behavior**:
- Cancel all subscriptions for deleted user
- Log cleanup actions
**Test**: User deleted event cancels subscriptions

---

## API Contract Rules

### BR-API-001: Health Check Response
**Endpoint**: `GET /health`
**Response**:
- `status`: "healthy" | "degraded"
- `service`: "product_service"
- `port`: 8215
- `version`: "1.0.0"
- `dependencies`: {"database": "healthy" | "unhealthy"}
**Test**: Health check returns correct structure

### BR-API-002: Service Info Response
**Endpoint**: `GET /api/v1/product/info`
**Response**:
- `service`: "product_service"
- `version`: "1.0.0"
- `description`: service description
- `capabilities`: list of capabilities
- `supported_product_types`: list of product types
- `supported_pricing_types`: list of pricing types
**Test**: Service info returns correct structure

### BR-API-003: Category List Response
**Endpoint**: `GET /api/v1/product/categories`
**Response**: List of ProductCategory objects
**Fields**: category_id, name, description, display_order, is_active
**Test**: Categories list returns array

### BR-API-004: Product List Filter Parameters
**Endpoint**: `GET /api/v1/product/products`
**Parameters**:
- `category_id`: optional category filter
- `product_type`: optional type filter (enum validation)
- `is_active`: default true
**Test**: Products list respects filters

### BR-API-005: Product Type Enum Validation
**Rule**: Invalid product_type returns 400
**Validation**: Enum conversion via ProductType(value)
**Error**: "Invalid product_type: {value}"
**Test**: Products list with invalid type returns 400

### BR-API-006: Product Not Found
**Endpoint**: `GET /api/v1/product/products/{product_id}`
**Response**: 404 if product not found
**Test**: Get non-existent product returns 404

### BR-API-007: Subscription User List
**Endpoint**: `GET /api/v1/product/subscriptions/user/{user_id}`
**Parameters**:
- `status`: optional status filter (enum validation)
**Response**: List of UserSubscription objects
**Test**: User subscriptions list returns array

### BR-API-008: Usage Records Query
**Endpoint**: `GET /api/v1/product/usage/records`
**Parameters**:
- `user_id`, `organization_id`, `subscription_id`, `product_id`: optional filters
- `start_date`, `end_date`: optional date range
- `limit`: default 100
- `offset`: default 0
**Response**: List of ProductUsageRecord objects
**Test**: Usage records list respects filters

### BR-API-009: Statistics Endpoints
**Endpoints**:
- `GET /api/v1/product/statistics/usage`
- `GET /api/v1/product/statistics/service`
**Test**: Statistics endpoints return correct structure

---

## Error Handling Rules

### BR-ERR-001: Validation Error Response
**Status Code**: 400 or 422
**Response**: `{"detail": "error message"}`
**Triggers**:
- Invalid enum values
- Missing required fields
- Invalid data formats

### BR-ERR-002: Not Found Response
**Status Code**: 404
**Response**: `{"detail": "Resource not found"}`
**Triggers**:
- Non-existent product
- Non-existent subscription

### BR-ERR-003: Internal Error Response
**Status Code**: 500
**Response**: `{"detail": "Internal server error: {message}"}`
**Triggers**:
- Database errors
- Unexpected exceptions

### BR-ERR-004: Service Unavailable Response
**Status Code**: 503
**Response**: `{"detail": "Product service not initialized"}`
**Triggers**:
- Service not ready
- Database connection failed

---

## Test Scenarios

### Scenario 1: Complete Subscription Lifecycle
1. Create subscription with valid user_id and plan_id
2. Verify subscription created with ACTIVE status
3. Verify subscription.created event published
4. Update status to CANCELED
5. Verify subscription.status_changed event published
6. Verify subscription status is CANCELED

### Scenario 2: Usage Tracking Flow
1. Create subscription
2. Record usage with subscription_id
3. Verify usage recorded successfully
4. Verify product.usage.recorded event published
5. Query usage records by subscription_id
6. Verify usage appears in results

### Scenario 3: Product Availability Check
1. Get active product by product_id
2. Check availability - expect available=true
3. (If possible) Set product to inactive
4. Check availability - expect available=false

### Scenario 4: Invalid Input Handling
1. Create subscription without user_id - expect 400
2. Create subscription with invalid billing_cycle - expect 400
3. Update status with invalid status - expect 400
4. Record usage with zero amount - expect error
5. Get non-existent product - expect 404

### Scenario 5: Event Publishing Resilience
1. Create subscription without event_bus
2. Verify subscription created successfully
3. Record usage without event_bus
4. Verify usage recorded successfully
5. Operations succeed independently of events

---

## Data Integrity Rules

### BR-INT-001: Timestamps Auto-Update
**Rule**: created_at and updated_at managed automatically
- `created_at`: Set on creation
- `updated_at`: Updated on modification

### BR-INT-002: Soft Delete Pattern
**Rule**: Subscriptions use status-based soft delete
- Set status to CANCELED instead of deleting
- Preserve data for audit and analytics

### BR-INT-003: Decimal Precision
**Rule**: Prices and amounts use appropriate precision
- Prices: Decimal(12, 4) or Decimal(12, 6)
- Usage amounts: Decimal(18, 6)
- Avoid floating-point arithmetic errors

---

**Document Version**: 1.0
**Last Updated**: 2025-12-16
**Maintained By**: Product Service Engineering Team
