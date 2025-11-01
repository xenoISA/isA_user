# Product Service Documentation

## Overview
The Product Service manages the product catalog, pricing models, subscription management, and usage tracking for all platform offerings. It serves as the central repository for product information, pricing rules, and subscription lifecycle management.

## Service Information
- **Port**: 8240 (testing), 8215 (production)
- **Service Name**: `product_service`
- **Health Check**: `GET /health`
- **Database**: Uses Supabase client with dev schema

## Core Capabilities
- Product catalog management
- Pricing model configuration
- Subscription lifecycle management
- Usage tracking and analytics
- Product availability and access control

## Quick Start

### 1. Start the Service
```bash
# Development
PRODUCT_SERVICE_PORT=8240 ENV=development uvicorn microservices.product_service.main:app --host 0.0.0.0 --port 8240 --reload

# Production
ENV=production python -m microservices.product_service.main
```

### 2. Health Check
```bash
curl http://localhost:8240/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "product_service",
  "port": 8240,
  "version": "1.0.0",
  "dependencies": {
    "database": "healthy"
  }
}
```

## API Endpoints

### Service Information
```bash
GET /api/v1/info
```

Response:
```json
{
  "service": "product_service",
  "version": "1.0.0",
  "description": "èŽ§ÁîUš÷Œ¢¡„®¡",
  "capabilities": [
    "product_catalog",
    "pricing_management",
    "subscription_management",
    "usage_tracking",
    "product_analytics"
  ],
  "supported_product_types": [
    "model_inference",
    "mcp_service",
    "agent_execution",
    "storage_minio",
    "api_gateway"
  ],
  "supported_pricing_types": [
    "freemium",
    "usage_based",
    "subscription",
    "hybrid"
  ]
}
```

## Product Catalog Management

### 1. Get Product Categories
```bash
GET /api/v1/categories
```

Response:
```json
[
  {
    "id": 1,
    "category_id": "ai_models",
    "name": "AI Models",
    "description": "Language models and AI inference services",
    "parent_category_id": null,
    "display_order": 0,
    "is_active": true,
    "metadata": {},
    "created_at": "2025-10-10T13:49:36.347706Z",
    "updated_at": "2025-10-10T13:49:36.347706Z"
  }
]
```

### 2. Get All Products
```bash
GET /api/v1/products
```

### 3. Get Products by Category
```bash
GET /api/v1/products?category_id=ai_models
```

Response:
```json
[
  {
    "id": 1,
    "product_id": "gpt-4",
    "category_id": "ai_models",
    "name": "GPT-4",
    "description": "Advanced language model from OpenAI",
    "short_description": null,
    "product_type": "model",
    "provider": "openai",
    "specifications": {
      "capabilities": ["text_generation", "code", "reasoning"],
      "context_length": 8192
    },
    "capabilities": [],
    "limitations": {},
    "is_active": true,
    "is_public": true,
    "requires_approval": false,
    "version": "1.0",
    "release_date": "2025-10-10",
    "service_type": "model_inference",
    "metadata": {},
    "created_at": "2025-10-10T13:49:36.348401Z"
  }
]
```

### 4. Get Specific Product
```bash
GET /api/v1/products/gpt-4
```

### 5. Filter Products
```bash
# By product type
GET /api/v1/products?product_type=model&is_active=true

# By category and type
GET /api/v1/products?category_id=ai_models&product_type=model
```

## Pricing Management

### 1. Get Product Pricing
```bash
GET /api/v1/products/gpt-4/pricing?user_id=user123&subscription_id=sub456
```

### 2. Check Product Availability
```bash
GET /api/v1/products/gpt-4/availability?user_id=user123&organization_id=org456
```

Response:
```json
{
  "available": true,
  "requires_subscription": false,
  "requires_approval": false,
  "access_level": "public",
  "restrictions": [],
  "pricing_available": true
}
```

## Subscription Management

### 1. Get User Subscriptions
```bash
GET /api/v1/subscriptions/user/user123?status=active
```

### 2. Get Subscription Details
```bash
GET /api/v1/subscriptions/sub123
```

### 3. Create New Subscription
```bash
POST /api/v1/subscriptions
Content-Type: application/json

{
  "user_id": "user123",
  "plan_id": "premium_plan",
  "organization_id": "org456",
  "billing_cycle": "monthly",
  "metadata": {
    "source": "web_signup"
  }
}
```

## Usage Tracking

### 1. Record Product Usage
```bash
POST /api/v1/usage/record
Content-Type: application/json

{
  "user_id": "user123",
  "product_id": "gpt-4",
  "usage_amount": 1000,
  "organization_id": "org456",
  "subscription_id": "sub123",
  "session_id": "session789",
  "request_id": "req456",
  "usage_details": {
    "tokens": 1000,
    "model": "gpt-4",
    "endpoint": "/chat/completions"
  }
}
```

### 2. Get Usage Records
```bash
GET /api/v1/usage/records?user_id=user123&product_id=gpt-4&limit=50&offset=0
```

### 3. Get Usage Statistics
```bash
GET /api/v1/statistics/usage?user_id=user123&start_date=2025-10-01&end_date=2025-10-31
```

## Analytics and Statistics

### 1. Get Service Statistics
```bash
GET /api/v1/statistics/service
```

### 2. Get Usage Statistics
```bash
GET /api/v1/statistics/usage?organization_id=org123&product_id=gpt-4
```

## Product Types
- `model` - AI language models
- `storage` - File storage services
- `agent` - AI workflow agents
- `mcp_tool` - MCP protocol tools
- `api_service` - Platform APIs
- `notification` - Messaging services

## Pricing Types
- `freemium` - Free tier with paid upgrades
- `usage_based` - Pay per use
- `subscription` - Fixed recurring billing
- `hybrid` - Combination of subscription + usage

## Subscription Status
- `active` - Currently active subscription
- `pending` - Pending activation
- `suspended` - Temporarily suspended
- `cancelled` - Cancelled subscription
- `expired` - Expired subscription

## Billing Cycles
- `monthly` - Monthly billing
- `quarterly` - Every 3 months
- `yearly` - Annual billing
- `usage_based` - Based on usage

## Database Schema

### products Table
- `id` (serial) - Primary key
- `product_id` (varchar) - Unique product identifier
- `category_id` (varchar) - Product category
- `name` (varchar) - Product name
- `description` (text) - Detailed description
- `product_type` (varchar) - Type of product
- `provider` (varchar) - Service provider
- `specifications` (jsonb) - Technical specifications
- `is_active` (boolean) - Whether product is active
- `service_type` (varchar) - Associated service type

### product_categories Table
- `id` (serial) - Primary key
- `category_id` (varchar) - Unique category identifier
- `name` (varchar) - Category name
- `description` (text) - Category description
- `display_order` (integer) - Sort order
- `is_active` (boolean) - Whether category is active

### user_subscriptions Table
- `id` (serial) - Primary key
- `subscription_id` (varchar) - Unique subscription identifier
- `user_id` (varchar) - User identifier
- `plan_id` (varchar) - Subscription plan
- `status` (varchar) - Subscription status
- `billing_cycle` (varchar) - Billing frequency
- `current_period_start` (timestamp) - Current billing period start
- `current_period_end` (timestamp) - Current billing period end

## Integration Examples

### Get Product for Billing
```bash
# Billing service calls this to get pricing info
curl "http://localhost:8240/api/v1/products/gpt-4/pricing?user_id=user123"
```

### Check Product Access
```bash
# Before allowing usage, check if user has access
curl "http://localhost:8240/api/v1/products/gpt-4/availability?user_id=user123&organization_id=org456"
```

### Record Usage After Service Call
```bash
# After using a service, record the usage
curl -X POST "http://localhost:8240/api/v1/usage/record" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user123","product_id":"gpt-4","usage_amount":1000}'
```

## Configuration

Environment variables from `.env`:
```bash
PRODUCT_SERVICE_PORT=8215
PRODUCT_SERVICE_SERVICE_HOST=localhost
SUPABASE_LOCAL_URL=http://127.0.0.1:54321
CONSUL_ENABLED=true
```

## Available Products (Example Catalog)

### AI Models
- `gpt-4` - GPT-4 language model
- `gpt-4-turbo` - Fast GPT-4 variant
- `gpt-3.5-turbo` - Affordable language model
- `text-embedding-3-small` - Text embeddings
- `text-embedding-3-large` - Large text embeddings

### Storage Services
- `minio_storage` - Object storage service

### AI Agents
- `basic_agent` - Simple task automation
- `advanced_agent` - Complex reasoning workflows

### MCP Services
- `mcp_tools` - Model Context Protocol tools

### API Services
- `api_gateway` - Platform API access

### Notifications
- `email_notifications` - Email delivery
- `push_notifications` - Mobile/web push

## Testing Examples

### 1. Browse Product Catalog
```bash
# Get all categories
curl http://localhost:8240/api/v1/categories

# Get AI models
curl "http://localhost:8240/api/v1/products?category_id=ai_models"

# Get specific product details
curl http://localhost:8240/api/v1/products/gpt-4
```

### 2. Check User Access
```bash
# Check if user can access GPT-4
curl "http://localhost:8240/api/v1/products/gpt-4/availability?user_id=user123"
```

### 3. Track Usage
```bash
# Record GPT-4 usage
curl -X POST http://localhost:8240/api/v1/usage/record \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user123","product_id":"gpt-4","usage_amount":1500}'

# Check usage history
curl "http://localhost:8240/api/v1/usage/records?user_id=user123"
```

### 4. Subscription Management
```bash
# Get user subscriptions
curl http://localhost:8240/api/v1/subscriptions/user/user123

# Create new subscription
curl -X POST http://localhost:8240/api/v1/subscriptions \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user123","plan_id":"premium","billing_cycle":"monthly"}'
```

## Error Handling

### Common Error Responses
```json
{
  "detail": "Product not found"
}
```

```json
{
  "detail": "Invalid product_type: invalid_type"
}
```

```json
{
  "detail": "Product service not initialized"
}
```

## Best Practices

1. **Cache product information** for frequently accessed products
2. **Check product availability** before allowing access
3. **Track usage accurately** with proper session correlation
4. **Use appropriate filtering** to reduce API response sizes
5. **Monitor subscription status** before granting access
6. **Validate pricing models** before billing operations

## Troubleshooting

### Service Won't Start
- Check Supabase database connectivity
- Verify environment variables
- Check port conflicts

### Product Queries Fail
- Verify database schema exists
- Check product data seeding
- Validate query parameters

### Subscription Issues
- Check user subscription status
- Verify subscription plan configuration
- Check billing cycle settings

### Usage Tracking Problems
- Verify usage record format
- Check decimal precision for amounts
- Ensure proper session tracking