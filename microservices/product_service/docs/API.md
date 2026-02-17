# Product Service API Documentation

**Version:** 1.0.0
**Base URL:** `http://localhost:8215`
**Port:** 8215 (Staging/Docker)

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Health & Info Endpoints](#health--info-endpoints)
- [Product Catalog Endpoints](#product-catalog-endpoints)
- [Subscription Management](#subscription-management)
- [Usage Tracking](#usage-tracking)
- [Statistics & Analytics](#statistics--analytics)
- [Error Handling](#error-handling)
- [Data Models](#data-models)

---

## Overview

The Product Service manages the platform's product catalog, pricing models, user subscriptions, and usage tracking. It provides a centralized system for:

- **Product Catalog**: Browse and query available products and services
- **Pricing Management**: Dynamic pricing based on product type and user subscription
- **Subscription Management**: Create and manage user subscriptions to service plans
- **Usage Tracking**: Record and analyze product usage for billing and analytics
- **Service-to-Service Communication**: Validates users and organizations via HTTP APIs

### Key Features

✅ **Microservices Architecture**: No database foreign keys to other services
✅ **Service Discovery**: Consul integration with fallback URLs
✅ **User Validation**: Validates users via Account Service HTTP API
✅ **Organization Validation**: Validates organizations via Organization Service HTTP API
✅ **RESTful API**: Standard HTTP methods and JSON responses
✅ **Comprehensive Analytics**: Usage statistics and reporting

---

## Authentication

Currently, the Product Service does **not** require authentication for read operations. However, write operations (create subscription, record usage) validate the `user_id` by communicating with the Account Service.

### User Validation

When creating subscriptions or recording usage, the service validates:

1. **User exists** in Account Service (`GET /api/v1/accounts/profile/{user_id}`)
2. **User is active** (not suspended or deleted)
3. **Organization exists** (if `organization_id` provided)

**Error Responses:**
- `400 Bad Request`: User not found or inactive
- `500 Internal Server Error`: Service communication error

---

## Health & Info Endpoints

### Health Check

**Endpoint:** `GET /health`

Check service health and dependencies.

**Response:**
```json
{
  "status": "healthy",
  "service": "product_service",
  "port": 8215,
  "version": "1.0.0",
  "dependencies": {
    "database": "healthy"
  }
}
```

**Status Codes:**
- `200 OK`: Service is healthy
- `503 Service Unavailable`: Service or dependencies unhealthy

---

### Service Information

**Endpoint:** `GET /api/v1/info`

Get service capabilities and supported features.

**Response:**
```json
{
  "service": "product_service",
  "version": "1.0.0",
  "description": "专注于产品目录、定价和订阅管理的微服务",
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

---

## Product Catalog Endpoints

### Get Product Categories

**Endpoint:** `GET /api/v1/categories`

Retrieve all active product categories.

**Response:**
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

**Status Codes:**
- `200 OK`: Categories retrieved successfully
- `500 Internal Server Error`: Database error

---

### Get Products

**Endpoint:** `GET /api/v1/products`

Retrieve products with optional filtering.

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `category_id` | string | No | - | Filter by category ID |
| `product_type` | string | No | - | Filter by product type |
| `is_active` | boolean | No | true | Filter by active status |

**Example Request:**
```
GET /api/v1/products?category_id=ai_models&is_active=true
```

**Response:**
```json
[
  {
    "id": 1,
    "product_id": "gpt-4",
    "category_id": "ai_models",
    "name": "GPT-4",
    "description": "Advanced language model from OpenAI",
    "product_type": "model",
    "provider": "openai",
    "specifications": {
      "context_length": 8192,
      "capabilities": ["text_generation", "code", "reasoning"]
    },
    "is_active": true,
    "is_public": true,
    "version": "1.0",
    "service_type": "model_inference",
    "created_at": "2025-10-10T13:49:36.349601Z"
  }
]
```

**Product Types:**
- `model` - AI models (GPT-4, Claude, etc.)
- `storage` - Storage services (MinIO, etc.)
- `agent` - AI agents
- `mcp_tool` - MCP tools
- `api_service` - API services
- `notification` - Notification services

---

### Get Product by ID

**Endpoint:** `GET /api/v1/products/{product_id}`

Retrieve detailed information for a specific product.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `product_id` | string | Yes | Product identifier |

**Example Request:**
```
GET /api/v1/products/gpt-4
```

**Response:**
```json
{
  "id": 1,
  "product_id": "gpt-4",
  "category_id": "ai_models",
  "name": "GPT-4",
  "description": "Advanced language model from OpenAI",
  "product_type": "model",
  "provider": "openai",
  "specifications": {
    "context_length": 8192,
    "capabilities": ["text_generation", "code", "reasoning"]
  },
  "capabilities": [],
  "limitations": {},
  "is_active": true,
  "is_public": true,
  "requires_approval": false,
  "version": "1.0",
  "release_date": "2025-10-10",
  "service_endpoint": null,
  "service_type": "model_inference",
  "metadata": {},
  "created_at": "2025-10-10T13:49:36.349601Z",
  "updated_at": "2025-10-10T13:49:36.349601Z"
}
```

**Status Codes:**
- `200 OK`: Product found
- `404 Not Found`: Product doesn't exist
- `500 Internal Server Error`: Database error

---

### Get Product Pricing

**Endpoint:** `GET /api/v1/products/{product_id}/pricing`

Get pricing information for a product, optionally customized for a user or subscription.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `product_id` | string | Yes | Product identifier |

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | No | User ID for personalized pricing |
| `subscription_id` | string | No | Subscription ID for subscription pricing |

**Example Request:**
```
GET /api/v1/products/gpt-4/pricing?user_id=user_123
```

**Response:**
```json
{
  "product": {
    "product_id": "gpt-4",
    "name": "GPT-4",
    "product_type": "model"
  },
  "pricing_model": {
    "pricing_model_id": "gpt-4-pricing",
    "pricing_type": "usage_based",
    "unit_type": "token",
    "input_unit_price": 0.00003,
    "output_unit_price": 0.00006,
    "currency": "CREDIT",
    "free_tier_limit": 1000
  },
  "subscription_info": null,
  "effective_pricing": {
    "base_price": 0,
    "usage_price": 0.00003,
    "is_included": false,
    "discount_rate": 0
  }
}
```

**Status Codes:**
- `200 OK`: Pricing retrieved
- `404 Not Found`: Product or pricing not found
- `500 Internal Server Error`: Database error

---

### Check Product Availability

**Endpoint:** `GET /api/v1/products/{product_id}/availability`

Check if a product is available for a specific user.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `product_id` | string | Yes | Product identifier |

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | Yes | User ID to check |
| `organization_id` | string | No | Organization ID |

**Example Request:**
```
GET /api/v1/products/gpt-4/availability?user_id=user_123
```

**Response:**
```json
{
  "available": true,
  "product": {
    "product_id": "gpt-4",
    "name": "GPT-4",
    "is_active": true
  }
}
```

**Unavailable Response:**
```json
{
  "available": false,
  "reason": "Product is not active"
}
```

---

## Subscription Management

### Create Subscription

**Endpoint:** `POST /api/v1/subscriptions`

Create a new subscription for a user.

**Request Body:**
```json
{
  "user_id": "user_123",
  "plan_id": "pro-plan",
  "billing_cycle": "monthly",
  "organization_id": "org_456",
  "metadata": {
    "source": "web_signup"
  }
}
```

**Request Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_id` | string | Yes | Valid user ID from Account Service |
| `plan_id` | string | Yes | Service plan ID |
| `billing_cycle` | string | No | monthly/quarterly/yearly (default: monthly) |
| `organization_id` | string | No | Organization ID for team subscriptions |
| `metadata` | object | No | Additional metadata |

**Available Plans:**
- `free-plan` - Basic access with limited usage
- `basic-plan` - Perfect for individual developers
- `pro-plan` - For growing teams and businesses
- `enterprise-plan` - For large organizations

**Response:**
```json
{
  "subscription_id": "sub_abc123",
  "user_id": "user_123",
  "organization_id": "org_456",
  "plan_id": "pro-plan",
  "plan_tier": "pro",
  "status": "active",
  "billing_cycle": "monthly",
  "current_period_start": "2025-10-14T00:00:00Z",
  "current_period_end": "2025-11-14T00:00:00Z",
  "metadata": {
    "source": "web_signup"
  },
  "created_at": "2025-10-14T00:00:00Z"
}
```

**Status Codes:**
- `200 OK`: Subscription created successfully
- `400 Bad Request`: Invalid input or user validation failed
- `500 Internal Server Error`: Service error

**Validation:**
- ✅ User must exist in Account Service
- ✅ User must be active
- ✅ Organization must exist (if provided)
- ✅ Service plan must exist

---

### Get User Subscriptions

**Endpoint:** `GET /api/v1/subscriptions/user/{user_id}`

Get all subscriptions for a user.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | Yes | User identifier |

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `status` | string | No | Filter by status (active, canceled, etc.) |

**Example Request:**
```
GET /api/v1/subscriptions/user/user_123?status=active
```

**Response:**
```json
[
  {
    "subscription_id": "sub_abc123",
    "user_id": "user_123",
    "plan_id": "pro-plan",
    "plan_tier": "pro",
    "status": "active",
    "billing_cycle": "monthly",
    "current_period_start": "2025-10-14T00:00:00Z",
    "current_period_end": "2025-11-14T00:00:00Z",
    "created_at": "2025-10-14T00:00:00Z"
  }
]
```

**Subscription Statuses:**
- `active` - Currently active
- `trialing` - In trial period
- `past_due` - Payment overdue
- `canceled` - Canceled
- `paused` - Temporarily paused

---

### Get Subscription by ID

**Endpoint:** `GET /api/v1/subscriptions/{subscription_id}`

Get detailed information for a specific subscription.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `subscription_id` | string | Yes | Subscription identifier |

**Example Request:**
```
GET /api/v1/subscriptions/sub_abc123
```

**Response:**
```json
{
  "subscription_id": "sub_abc123",
  "user_id": "user_123",
  "organization_id": "org_456",
  "plan_id": "pro-plan",
  "plan_tier": "pro",
  "status": "active",
  "billing_cycle": "monthly",
  "current_period_start": "2025-10-14T00:00:00Z",
  "current_period_end": "2025-11-14T00:00:00Z",
  "metadata": {},
  "created_at": "2025-10-14T00:00:00Z",
  "updated_at": "2025-10-14T00:00:00Z"
}
```

**Status Codes:**
- `200 OK`: Subscription found
- `404 Not Found`: Subscription doesn't exist
- `500 Internal Server Error`: Database error

---

## Usage Tracking

### Record Product Usage

**Endpoint:** `POST /api/v1/usage/record`

Record usage of a product by a user.

**Request Body:**
```json
{
  "user_id": "user_123",
  "product_id": "gpt-4",
  "usage_amount": 1500.0,
  "organization_id": "org_456",
  "subscription_id": "sub_abc123",
  "session_id": "sess_xyz",
  "request_id": "req_789",
  "usage_details": {
    "tokens_input": 1000,
    "tokens_output": 500,
    "model": "gpt-4"
  },
  "usage_timestamp": "2025-10-14T10:30:00Z"
}
```

**Request Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_id` | string | Yes | Valid user ID from Account Service |
| `product_id` | string | Yes | Product being used |
| `usage_amount` | float | Yes | Amount of usage |
| `organization_id` | string | No | Organization ID |
| `subscription_id` | string | No | Associated subscription |
| `session_id` | string | No | Session identifier |
| `request_id` | string | No | Request identifier |
| `usage_details` | object | No | Additional usage metadata |
| `usage_timestamp` | datetime | No | Custom timestamp (default: now) |

**Response:**
```json
{
  "success": true,
  "message": "Usage recorded successfully",
  "usage_record_id": "usage_xyz789",
  "product": {
    "product_id": "gpt-4",
    "name": "GPT-4"
  },
  "recorded_amount": 1500.0,
  "timestamp": "2025-10-14T10:30:00Z"
}
```

**Error Response:**
```json
{
  "success": false,
  "message": "User user_123 not found or inactive",
  "usage_record_id": null
}
```

**Validation:**
- ✅ User must exist and be active (Account Service)
- ✅ Organization must exist if provided (Organization Service)
- ✅ Product must exist
- ✅ Subscription must be active if provided

---

### Get Usage Records

**Endpoint:** `GET /api/v1/usage/records`

Retrieve usage records with filtering.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | No | Filter by user |
| `organization_id` | string | No | Filter by organization |
| `subscription_id` | string | No | Filter by subscription |
| `product_id` | string | No | Filter by product |
| `start_date` | datetime | No | Start date (ISO 8601) |
| `end_date` | datetime | No | End date (ISO 8601) |
| `limit` | integer | No | Max records (default: 100) |
| `offset` | integer | No | Pagination offset (default: 0) |

**Example Request:**
```
GET /api/v1/usage/records?user_id=user_123&limit=10
```

**Response:**
```json
[
  {
    "usage_id": "usage_xyz789",
    "user_id": "user_123",
    "product_id": "gpt-4",
    "usage_amount": 1500.0,
    "unit_type": "token",
    "total_cost": 0.09,
    "usage_timestamp": "2025-10-14T10:30:00Z",
    "usage_details": {
      "tokens_input": 1000,
      "tokens_output": 500
    }
  }
]
```

---

### Get Usage Statistics

**Endpoint:** `GET /api/v1/statistics/usage`

Get aggregated usage statistics.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | No | Filter by user |
| `organization_id` | string | No | Filter by organization |
| `product_id` | string | No | Filter by product |
| `start_date` | datetime | No | Start date (ISO 8601) |
| `end_date` | datetime | No | End date (ISO 8601) |

**Example Request:**
```
GET /api/v1/statistics/usage?user_id=user_123
```

**Response:**
```json
{
  "total_statistics": {
    "total_records": 150,
    "total_usage": 225000.0,
    "avg_usage": 1500.0,
    "min_usage": 100.0,
    "max_usage": 5000.0
  },
  "product_statistics": [
    {
      "product_id": "gpt-4",
      "record_count": 100,
      "total_usage": 150000.0
    },
    {
      "product_id": "gpt-3.5-turbo",
      "record_count": 50,
      "total_usage": 75000.0
    }
  ],
  "filter_criteria": {
    "user_id": "user_123",
    "organization_id": null,
    "product_id": null,
    "start_date": null,
    "end_date": null
  }
}
```

---

## Statistics & Analytics

### Get Service Statistics

**Endpoint:** `GET /api/v1/statistics/service`

Get overall service statistics.

**Response:**
```json
{
  "service": "product_service",
  "statistics": {
    "total_products": 12,
    "active_subscriptions": 45,
    "usage_records_24h": 1250,
    "usage_records_7d": 8750,
    "usage_records_30d": 35000
  },
  "timestamp": "2025-10-14T10:30:00Z"
}
```

---

## Error Handling

### Error Response Format

All errors return a consistent format:

```json
{
  "detail": "Error message description"
}
```

### HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| `200 OK` | Success | Request succeeded |
| `400 Bad Request` | Invalid input | Validation failed, invalid parameters |
| `404 Not Found` | Resource not found | Product, subscription, or user not found |
| `422 Unprocessable Entity` | Validation error | Pydantic validation failed |
| `500 Internal Server Error` | Server error | Database error, service communication error |
| `503 Service Unavailable` | Service down | Database or dependent service unavailable |

### Common Error Messages

**User Validation Errors:**
```json
{
  "detail": "Invalid billing_cycle: User user_123 not found or inactive"
}
```

**Product Not Found:**
```json
{
  "detail": "Product not found"
}
```

**Subscription Not Found:**
```json
{
  "detail": "Subscription not found"
}
```

---

## Data Models

### Product

```typescript
{
  id: number;
  product_id: string;
  category_id: string;
  name: string;
  description: string;
  product_type: "model" | "storage" | "agent" | "mcp_tool" | "api_service" | "notification";
  provider: string;
  specifications: object;
  capabilities: string[];
  limitations: object;
  is_active: boolean;
  is_public: boolean;
  requires_approval: boolean;
  version: string;
  release_date: date;
  deprecation_date?: date;
  service_endpoint?: string;
  service_type?: string;
  metadata: object;
  created_at: datetime;
  updated_at: datetime;
}
```

### Subscription

```typescript
{
  subscription_id: string;
  user_id: string;
  organization_id?: string;
  plan_id: string;
  plan_tier: "free" | "basic" | "pro" | "enterprise" | "custom";
  status: "active" | "trialing" | "past_due" | "canceled" | "paused";
  billing_cycle: "monthly" | "quarterly" | "yearly";
  current_period_start: datetime;
  current_period_end: datetime;
  metadata: object;
  created_at: datetime;
  updated_at: datetime;
}
```

### Usage Record

```typescript
{
  usage_id: string;
  user_id: string;
  organization_id?: string;
  subscription_id?: string;
  product_id: string;
  pricing_model_id: string;
  usage_amount: decimal;
  unit_type: string;
  unit_price: decimal;
  total_cost: decimal;
  currency: string;
  usage_timestamp: datetime;
  usage_details: object;
  session_id?: string;
  request_id?: string;
  created_at: datetime;
}
```

---

## Rate Limits

Currently, no rate limits are enforced. Consider implementing rate limiting for production use.

## Support

For issues or questions:
- Review this documentation
- Check service logs
- Contact platform team
