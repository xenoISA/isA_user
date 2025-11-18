# Billing Service Documentation

## Overview
The Billing Service is responsible for centralized billing, usage tracking, cost calculation, and billing processing across all platform resources. It handles model inference, MCP services, agent execution, storage services, and API gateway usage.

## Service Information
- **Port**: 8241 (testing), 8216 (production)
- **Service Name**: `billing_service`
- **Health Check**: `GET /health`
- **Database**: Uses Supabase client with dev schema

## Core Capabilities
- Usage tracking and recording
- Cost calculation and billing processing
- Quota management and enforcement
- Billing analytics and reporting
- Inter-service integration for pricing

## Quick Start

### 1. Start the Service
```bash
# Development
BILLING_SERVICE_PORT=8241 ENV=development uvicorn microservices.billing_service.main:app --host 0.0.0.0 --port 8241 --reload

# Production
ENV=production python -m microservices.billing_service.main
```

### 2. Health Check
```bash
curl http://localhost:8241/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "billing_service",
  "port": 8241,
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

### Core Billing Operations

#### 1. Record Usage and Bill (Main API)
```bash
POST /api/v1/usage/record
Content-Type: application/json

{
  "user_id": "user123",
  "product_id": "gpt-4",
  "service_type": "model_inference",
  "usage_amount": 1000,
  "billing_method": "wallet_deduction",
  "organization_id": "org456",
  "session_id": "session789",
  "usage_details": {
    "tokens": 1000,
    "model": "gpt-4"
  }
}
```

#### 2. Calculate Billing Cost
```bash
POST /api/v1/billing/calculate
Content-Type: application/json

{
  "user_id": "user123",
  "product_id": "gpt-4", 
  "service_type": "model_inference",
  "usage_amount": 1000,
  "pricing_context": {
    "subscription_id": "sub123"
  }
}
```

Response:
```json
{
  "success": true,
  "product_id": "gpt-4",
  "usage_amount": "1000",
  "unit_price": "0.002",
  "total_cost": "2.00",
  "currency": "CREDIT",
  "is_free_tier": false,
  "is_included_in_subscription": false,
  "suggested_billing_method": "wallet_deduction",
  "available_billing_methods": ["wallet_deduction", "payment_charge"]
}
```

#### 3. Process Billing
```bash
POST /api/v1/billing/process
Content-Type: application/json

{
  "billing_id": "bill_abc123",
  "billing_method": "wallet_deduction",
  "force_charge": false
}
```

### Quota Management

#### Check Quota
```bash
POST /api/v1/quota/check
Content-Type: application/json

{
  "user_id": "user123",
  "service_type": "model_inference",
  "requested_amount": 1000,
  "organization_id": "org456"
}
```

### Query and Analytics

#### Get User Billing Records
```bash
GET /api/v1/billing/records/user/user123?status=completed&limit=50&offset=0
```

#### Get Billing Statistics
```bash
GET /api/v1/stats?start_date=2025-10-01&end_date=2025-10-31
```

Response:
```json
{
  "total_billing_records": 0,
  "pending_billing_records": 0,
  "completed_billing_records": 0,
  "failed_billing_records": 0,
  "total_revenue": "0",
  "revenue_by_service": {},
  "revenue_by_method": {},
  "active_users": 0,
  "active_organizations": 0,
  "stats_period_start": "2025-09-11T03:09:58.032764",
  "stats_period_end": "2025-10-11T03:09:58.032777"
}
```

#### Get Usage Aggregations
```bash
GET /api/v1/usage/aggregations?user_id=user123&service_type=model_inference
```

## Service Types
- `model_inference` - AI model usage
- `mcp_service` - MCP tool execution  
- `agent_execution` - AI agent workflows
- `storage_minio` - Object storage
- `api_gateway` - Platform API access
- `notification` - Messaging services

## Billing Methods
- `wallet_deduction` - Deduct from user wallet
- `payment_charge` - Charge payment method
- `credit_consumption` - Use platform credits
- `subscription_included` - Included in subscription

## Billing Status
- `pending` - Awaiting processing
- `processing` - Currently being processed
- `completed` - Successfully billed
- `failed` - Billing failed
- `refunded` - Amount refunded

## Integration with Other Services

### Product Service Integration
The billing service automatically retrieves product pricing from the product service:
```bash
# Billing service calls product service internally
GET http://localhost:8240/api/v1/products/gpt-4/pricing?user_id=user123
```

### Wallet Service Integration
For wallet deductions, the billing service integrates with the wallet service for balance checks and transactions.

### Payment Service Integration  
For payment charges, the billing service coordinates with the payment service for credit card processing.

## Database Schema

### billing_records Table
- `id` (serial) - Primary key
- `billing_id` (varchar) - Unique billing identifier
- `user_id` (varchar) - User identifier
- `organization_id` (varchar) - Organization identifier
- `product_id` (varchar) - Product being billed
- `service_type` (varchar) - Type of service
- `usage_amount` (numeric) - Amount of usage
- `unit_price` (numeric) - Price per unit
- `total_amount` (numeric) - Total billing amount
- `billing_method` (varchar) - How to charge
- `billing_status` (varchar) - Current status
- `created_at`, `updated_at` (timestamp)

### billing_events Table
- Event tracking for billing operations
- Links to billing_records

### billing_quotas Table
- User and organization quotas
- Quota limits and usage tracking

## Error Handling

### Common Error Responses
```json
{
  "detail": "Product pricing not found"
}
```

```json
{
  "detail": "Insufficient wallet balance"
}
```

```json
{
  "detail": "Quota exceeded for service type"
}
```

## Configuration

The service uses environment variables from `.env`:
```bash
BILLING_SERVICE_PORT=8216
BILLING_SERVICE_SERVICE_HOST=localhost
SUPABASE_LOCAL_URL=http://127.0.0.1:54321
CONSUL_ENABLED=true
```

## Monitoring and Logs

### Health Monitoring
```bash
# Check service health
curl http://localhost:8241/health

# Check detailed health with dependencies  
curl http://localhost:8241/health/detailed
```

### Logging
- Centralized logging via Loki
- Structured JSON logs
- Error tracking and alerting

## Testing Examples

### End-to-End Billing Flow
1. **Calculate cost**:
```bash
curl -X POST http://localhost:8241/api/v1/billing/calculate \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user123","product_id":"gpt-4","service_type":"model_inference","usage_amount":1000}'
```

2. **Record usage and bill**:
```bash
curl -X POST http://localhost:8241/api/v1/usage/record \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user123","product_id":"gpt-4","service_type":"model_inference","usage_amount":1000,"billing_method":"wallet_deduction"}'
```

3. **Check billing records**:
```bash
curl http://localhost:8241/api/v1/billing/records/user/user123
```

## Best Practices

1. **Always check quotas** before allowing expensive operations
2. **Use appropriate billing methods** based on user preferences
3. **Track usage accurately** with proper session and request IDs
4. **Handle billing failures gracefully** with retry mechanisms
5. **Monitor billing statistics** for business insights

## Troubleshooting

### Service Won't Start
- Check database connectivity to Supabase
- Verify environment variables are set
- Check port availability

### Billing Calculations Fail
- Verify product exists in product service
- Check pricing models are configured
- Ensure user has valid payment methods

### Database Issues
- Check Supabase connection string
- Verify schema permissions
- Check table existence and structure