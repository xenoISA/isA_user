"""
Product Service Data Contract

Defines canonical data structures for product service testing.
All tests MUST use these Pydantic models and factories for consistency.

This is the SINGLE SOURCE OF TRUTH for product service test data.
"""

import uuid
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, Field, field_validator

# Import from production models for type consistency
from microservices.product_service.models import (
    ProductType,
    PricingType,
    UnitType,
    PlanTier,
    Currency,
    SubscriptionStatus,
    BillingCycle,
)


# ============================================================================
# Enum Contracts (For test validation)
# ============================================================================

class ProductTypeEnum(str, Enum):
    """Product type enum for testing"""
    MODEL = "model"
    MODEL_INFERENCE = "model_inference"
    STORAGE = "storage"
    STORAGE_MINIO = "storage_minio"
    AGENT = "agent"
    AGENT_EXECUTION = "agent_execution"
    MCP_TOOL = "mcp_tool"
    MCP_SERVICE = "mcp_service"
    API_SERVICE = "api_service"
    API_GATEWAY = "api_gateway"
    NOTIFICATION = "notification"
    COMPUTATION = "computation"
    DATA_PROCESSING = "data_processing"
    INTEGRATION = "integration"
    OTHER = "other"


class PricingTypeEnum(str, Enum):
    """Pricing type enum for testing"""
    USAGE_BASED = "usage_based"
    SUBSCRIPTION = "subscription"
    ONE_TIME = "one_time"
    FREEMIUM = "freemium"
    HYBRID = "hybrid"


class SubscriptionStatusEnum(str, Enum):
    """Subscription status enum for testing"""
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    UNPAID = "unpaid"
    PAUSED = "paused"


class BillingCycleEnum(str, Enum):
    """Billing cycle enum for testing"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    ONE_TIME = "one_time"


class PlanTierEnum(str, Enum):
    """Plan tier enum for testing"""
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


# ============================================================================
# Request Contracts (Input Schemas)
# ============================================================================

class ProductCategoryResponseContract(BaseModel):
    """
    Contract: Product category response schema

    Validates API response structure for product categories.
    """
    category_id: str = Field(..., description="Category ID")
    name: str = Field(..., description="Category name")
    description: Optional[str] = Field(None, description="Category description")
    parent_category_id: Optional[str] = Field(None, description="Parent category ID")
    display_order: int = Field(0, description="Display order")
    is_active: bool = Field(True, description="Category active status")

    class Config:
        json_schema_extra = {
            "example": {
                "category_id": "cat_ai_models",
                "name": "AI Models",
                "description": "Language models and inference APIs",
                "parent_category_id": None,
                "display_order": 1,
                "is_active": True
            }
        }


class ProductResponseContract(BaseModel):
    """
    Contract: Product response schema

    Validates API response structure for products.
    """
    product_id: str = Field(..., description="Product ID")
    category_id: str = Field(..., description="Category ID")
    name: str = Field(..., description="Product name")
    description: Optional[str] = Field(None, description="Product description")
    product_type: str = Field(..., description="Product type")
    provider: Optional[str] = Field(None, description="Provider name")
    specifications: Dict[str, Any] = Field(default_factory=dict, description="Product specs")
    capabilities: List[str] = Field(default_factory=list, description="Product capabilities")
    is_active: bool = Field(True, description="Product active status")
    is_public: bool = Field(True, description="Product public status")
    version: str = Field("1.0", description="Product version")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "prod_claude_sonnet",
                "category_id": "cat_ai_models",
                "name": "Claude Sonnet",
                "description": "Anthropic Claude 3.5 Sonnet model",
                "product_type": "model_inference",
                "provider": "anthropic",
                "specifications": {"context_window": 200000},
                "capabilities": ["text_generation", "code_generation"],
                "is_active": True,
                "is_public": True,
                "version": "3.5"
            }
        }


class ProductPricingResponseContract(BaseModel):
    """
    Contract: Product pricing response schema

    Validates API response structure for product pricing.
    """
    product_id: str = Field(..., description="Product ID")
    product_name: Optional[str] = Field(None, description="Product name")
    base_price: float = Field(..., ge=0, description="Base price")
    currency: str = Field(..., description="Currency code")
    pricing_type: str = Field(..., description="Pricing type")
    billing_interval: Optional[str] = Field(None, description="Billing interval")
    tiers: List[Dict[str, Any]] = Field(default_factory=list, description="Pricing tiers")
    features: List[str] = Field(default_factory=list, description="Included features")
    quota_limits: Dict[str, Any] = Field(default_factory=dict, description="Quota limits")

    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "prod_claude_sonnet",
                "product_name": "Claude Sonnet",
                "base_price": 0.000003,
                "currency": "USD",
                "pricing_type": "usage_based",
                "tiers": [
                    {"tier_name": "Base", "min_units": 0, "max_units": 1000, "price_per_unit": 0.000003}
                ]
            }
        }


class CreateSubscriptionRequestContract(BaseModel):
    """
    Contract: Create subscription request schema

    Used for creating subscriptions in tests.
    """
    user_id: str = Field(..., min_length=1, description="User ID")
    plan_id: str = Field(..., min_length=1, description="Plan ID")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    billing_cycle: str = Field("monthly", description="Billing cycle")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    @field_validator('billing_cycle')
    @classmethod
    def validate_billing_cycle(cls, v):
        valid_cycles = ["monthly", "quarterly", "yearly", "one_time"]
        if v not in valid_cycles:
            raise ValueError(f"Invalid billing_cycle: {v}. Must be one of {valid_cycles}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_abc123",
                "plan_id": "plan_pro_monthly",
                "organization_id": None,
                "billing_cycle": "monthly",
                "metadata": {"source": "web_app"}
            }
        }


class SubscriptionResponseContract(BaseModel):
    """
    Contract: Subscription response schema

    Validates API response structure for subscriptions.
    """
    subscription_id: str = Field(..., description="Subscription ID")
    user_id: str = Field(..., description="User ID")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    plan_id: str = Field(..., description="Plan ID")
    plan_tier: str = Field(..., description="Plan tier")
    status: str = Field(..., description="Subscription status")
    billing_cycle: str = Field(..., description="Billing cycle")
    current_period_start: Optional[datetime] = Field(None, description="Period start")
    current_period_end: Optional[datetime] = Field(None, description="Period end")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "subscription_id": "sub_xyz789",
                "user_id": "user_abc123",
                "organization_id": None,
                "plan_id": "plan_pro_monthly",
                "plan_tier": "pro",
                "status": "active",
                "billing_cycle": "monthly",
                "current_period_start": "2025-12-16T00:00:00Z",
                "current_period_end": "2026-01-15T00:00:00Z"
            }
        }


class UpdateSubscriptionStatusRequestContract(BaseModel):
    """
    Contract: Update subscription status request schema

    Used for updating subscription status in tests.
    """
    status: str = Field(..., description="New subscription status")

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        valid_statuses = ["active", "trialing", "past_due", "canceled", "incomplete",
                         "incomplete_expired", "unpaid", "paused"]
        if v not in valid_statuses:
            raise ValueError(f"Invalid status: {v}. Must be one of {valid_statuses}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "status": "canceled"
            }
        }


class RecordUsageRequestContract(BaseModel):
    """
    Contract: Record usage request schema

    Used for recording product usage in tests.
    """
    user_id: str = Field(..., min_length=1, description="User ID")
    product_id: str = Field(..., min_length=1, description="Product ID")
    usage_amount: float = Field(..., gt=0, description="Usage amount")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    subscription_id: Optional[str] = Field(None, description="Subscription ID")
    session_id: Optional[str] = Field(None, description="Session ID")
    request_id: Optional[str] = Field(None, description="Request ID")
    usage_details: Optional[Dict[str, Any]] = Field(None, description="Usage details")
    usage_timestamp: Optional[datetime] = Field(None, description="Usage timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_abc123",
                "product_id": "prod_claude_sonnet",
                "usage_amount": 1500,
                "session_id": "sess_123",
                "usage_details": {"input_tokens": 1000, "output_tokens": 500}
            }
        }


class UsageRecordResponseContract(BaseModel):
    """
    Contract: Usage record response schema

    Validates API response structure for usage recording.
    """
    success: bool = Field(..., description="Success status")
    message: str = Field(..., description="Response message")
    usage_record_id: Optional[str] = Field(None, description="Usage record ID")
    product: Optional[Dict[str, Any]] = Field(None, description="Product info")
    recorded_amount: Optional[float] = Field(None, description="Recorded amount")
    timestamp: Optional[datetime] = Field(None, description="Record timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Usage recorded successfully",
                "usage_record_id": "usage_789",
                "recorded_amount": 1500,
                "timestamp": "2025-12-16T10:30:00Z"
            }
        }


class ProductAvailabilityResponseContract(BaseModel):
    """
    Contract: Product availability response schema

    Validates API response structure for availability check.
    """
    available: bool = Field(..., description="Availability status")
    product: Optional[Dict[str, Any]] = Field(None, description="Product info if available")
    reason: Optional[str] = Field(None, description="Reason if unavailable")

    class Config:
        json_schema_extra = {
            "example": {
                "available": True,
                "product": {
                    "product_id": "prod_claude_sonnet",
                    "name": "Claude Sonnet",
                    "is_active": True
                }
            }
        }


class UsageStatisticsResponseContract(BaseModel):
    """
    Contract: Usage statistics response schema

    Validates API response structure for usage statistics.
    """
    total_usage: float = Field(0, description="Total usage")
    usage_by_product: Dict[str, Any] = Field(default_factory=dict, description="Usage by product")
    usage_by_date: Dict[str, Any] = Field(default_factory=dict, description="Usage by date")
    period: Dict[str, Any] = Field(default_factory=dict, description="Period info")

    class Config:
        json_schema_extra = {
            "example": {
                "total_usage": 15420,
                "usage_by_product": {"prod_claude_sonnet": 10000, "prod_storage": 5420},
                "usage_by_date": {"2025-12-15": 5000, "2025-12-16": 10420},
                "period": {"start_date": "2025-12-01", "end_date": "2025-12-16"}
            }
        }


class ServiceStatisticsResponseContract(BaseModel):
    """
    Contract: Service statistics response schema

    Validates API response structure for service statistics.
    """
    service: str = Field(..., description="Service name")
    statistics: Dict[str, Any] = Field(default_factory=dict, description="Statistics")
    timestamp: Optional[datetime] = Field(None, description="Statistics timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "service": "product_service",
                "statistics": {
                    "total_products": 45,
                    "active_subscriptions": 1250,
                    "usage_records_24h": 15420
                },
                "timestamp": "2025-12-16T10:00:00Z"
            }
        }


class ProductServiceHealthContract(BaseModel):
    """
    Contract: Product service health response schema

    Validates API response structure for health check.
    """
    status: str = Field(..., description="Service status")
    service: str = Field(default="product_service", description="Service name")
    port: int = Field(..., ge=1024, le=65535, description="Service port")
    version: str = Field(..., description="Service version")
    dependencies: Dict[str, str] = Field(default_factory=dict, description="Dependency status")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "service": "product_service",
                "port": 8215,
                "version": "1.0.0",
                "dependencies": {"database": "healthy"}
            }
        }


# ============================================================================
# Test Data Factory
# ============================================================================

class ProductTestDataFactory:
    """
    Factory for creating test data conforming to contracts.

    Provides methods to generate valid/invalid test data for all scenarios.
    """

    # Product types for random selection
    PRODUCT_TYPES = [
        "model", "model_inference", "storage", "storage_minio", "agent",
        "agent_execution", "mcp_tool", "mcp_service", "api_service",
        "api_gateway", "notification", "computation", "data_processing", "integration"
    ]

    PRICING_TYPES = ["usage_based", "subscription", "one_time", "freemium", "hybrid"]

    SUBSCRIPTION_STATUSES = [
        "active", "trialing", "past_due", "canceled",
        "incomplete", "incomplete_expired", "unpaid", "paused"
    ]

    BILLING_CYCLES = ["monthly", "quarterly", "yearly", "one_time"]

    PLAN_TIERS = ["free", "basic", "pro", "enterprise", "custom"]

    CURRENCIES = ["USD", "EUR", "CNY", "CREDIT"]

    PROVIDERS = ["anthropic", "openai", "google", "internal", "minio", "aws"]

    @staticmethod
    def make_product_id() -> str:
        """Generate unique test product ID"""
        return f"prod_test_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_category_id() -> str:
        """Generate unique test category ID"""
        return f"cat_test_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def make_user_id() -> str:
        """Generate unique test user ID"""
        return f"user_test_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_subscription_id() -> str:
        """Generate unique test subscription ID"""
        return f"sub_test_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_plan_id() -> str:
        """Generate unique test plan ID"""
        tier = random.choice(ProductTestDataFactory.PLAN_TIERS)
        return f"plan_{tier}_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def make_organization_id() -> str:
        """Generate unique test organization ID"""
        return f"org_test_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_session_id() -> str:
        """Generate unique test session ID"""
        return f"sess_test_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_request_id() -> str:
        """Generate unique test request ID"""
        return f"req_test_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_usage_id() -> str:
        """Generate unique test usage record ID"""
        return f"usage_test_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def make_product_name() -> str:
        """Generate random product name"""
        prefixes = ["Claude", "GPT", "Gemini", "Storage", "Agent", "Tool"]
        suffixes = ["Pro", "Plus", "Basic", "Enterprise", "Mini", "Max"]
        return f"{random.choice(prefixes)} {random.choice(suffixes)}"

    @staticmethod
    def make_category_name() -> str:
        """Generate random category name"""
        categories = [
            "AI Models", "Storage Services", "Agent Services",
            "MCP Tools", "API Services", "Compute Resources"
        ]
        return random.choice(categories)

    @staticmethod
    def make_product_type() -> str:
        """Generate random product type"""
        return random.choice(ProductTestDataFactory.PRODUCT_TYPES)

    @staticmethod
    def make_pricing_type() -> str:
        """Generate random pricing type"""
        return random.choice(ProductTestDataFactory.PRICING_TYPES)

    @staticmethod
    def make_subscription_status() -> str:
        """Generate random subscription status"""
        return random.choice(ProductTestDataFactory.SUBSCRIPTION_STATUSES)

    @staticmethod
    def make_billing_cycle() -> str:
        """Generate random billing cycle"""
        return random.choice(ProductTestDataFactory.BILLING_CYCLES)

    @staticmethod
    def make_plan_tier() -> str:
        """Generate random plan tier"""
        return random.choice(ProductTestDataFactory.PLAN_TIERS)

    @staticmethod
    def make_currency() -> str:
        """Generate random currency"""
        return random.choice(ProductTestDataFactory.CURRENCIES)

    @staticmethod
    def make_provider() -> str:
        """Generate random provider"""
        return random.choice(ProductTestDataFactory.PROVIDERS)

    @staticmethod
    def make_base_price() -> float:
        """Generate random base price"""
        return round(random.uniform(0.000001, 0.01), 6)

    @staticmethod
    def make_usage_amount() -> float:
        """Generate random usage amount"""
        return round(random.uniform(100, 10000), 2)

    @staticmethod
    def make_specifications() -> Dict[str, Any]:
        """Generate random product specifications"""
        return {
            "context_window": random.choice([4096, 8192, 32000, 128000, 200000]),
            "max_output_tokens": random.choice([2048, 4096, 8192]),
            "supports_vision": random.choice([True, False]),
            "supports_function_calling": random.choice([True, False]),
        }

    @staticmethod
    def make_capabilities() -> List[str]:
        """Generate random product capabilities"""
        all_capabilities = [
            "text_generation", "code_generation", "analysis",
            "vision", "function_calling", "streaming",
            "embeddings", "fine_tuning"
        ]
        return random.sample(all_capabilities, k=random.randint(2, 5))

    @staticmethod
    def make_usage_details() -> Dict[str, Any]:
        """Generate random usage details"""
        return {
            "input_tokens": random.randint(100, 5000),
            "output_tokens": random.randint(50, 2000),
            "model_version": f"v{random.randint(1, 5)}.{random.randint(0, 9)}",
            "latency_ms": random.randint(100, 5000),
        }

    @staticmethod
    def make_category_response(**overrides) -> ProductCategoryResponseContract:
        """Create valid category response for assertions"""
        defaults = {
            "category_id": ProductTestDataFactory.make_category_id(),
            "name": ProductTestDataFactory.make_category_name(),
            "description": "Test category description",
            "parent_category_id": None,
            "display_order": random.randint(0, 10),
            "is_active": True,
        }
        defaults.update(overrides)
        return ProductCategoryResponseContract(**defaults)

    @staticmethod
    def make_product_response(**overrides) -> ProductResponseContract:
        """Create valid product response for assertions"""
        defaults = {
            "product_id": ProductTestDataFactory.make_product_id(),
            "category_id": ProductTestDataFactory.make_category_id(),
            "name": ProductTestDataFactory.make_product_name(),
            "description": "Test product description",
            "product_type": ProductTestDataFactory.make_product_type(),
            "provider": ProductTestDataFactory.make_provider(),
            "specifications": ProductTestDataFactory.make_specifications(),
            "capabilities": ProductTestDataFactory.make_capabilities(),
            "is_active": True,
            "is_public": True,
            "version": "1.0",
            "created_at": datetime.now(timezone.utc) - timedelta(days=30),
            "updated_at": datetime.now(timezone.utc),
        }
        defaults.update(overrides)
        return ProductResponseContract(**defaults)

    @staticmethod
    def make_pricing_response(**overrides) -> ProductPricingResponseContract:
        """Create valid pricing response for assertions"""
        base_price = ProductTestDataFactory.make_base_price()
        defaults = {
            "product_id": ProductTestDataFactory.make_product_id(),
            "product_name": ProductTestDataFactory.make_product_name(),
            "base_price": base_price,
            "currency": ProductTestDataFactory.make_currency(),
            "pricing_type": ProductTestDataFactory.make_pricing_type(),
            "billing_interval": "per_unit",
            "tiers": [
                {"tier_name": "Base", "min_units": 0, "max_units": 1000, "price_per_unit": base_price},
                {"tier_name": "Standard", "min_units": 1001, "max_units": 10000, "price_per_unit": round(base_price * 0.9, 6)},
                {"tier_name": "Premium", "min_units": 10001, "max_units": None, "price_per_unit": round(base_price * 0.8, 6)},
            ],
            "features": ["basic_access", "api_support"],
            "quota_limits": {"requests_per_day": 10000},
        }
        defaults.update(overrides)
        return ProductPricingResponseContract(**defaults)

    @staticmethod
    def make_create_subscription_request(**overrides) -> CreateSubscriptionRequestContract:
        """Create valid subscription request"""
        defaults = {
            "user_id": ProductTestDataFactory.make_user_id(),
            "plan_id": ProductTestDataFactory.make_plan_id(),
            "organization_id": None,
            "billing_cycle": ProductTestDataFactory.make_billing_cycle(),
            "metadata": {"source": "test"},
        }
        defaults.update(overrides)
        return CreateSubscriptionRequestContract(**defaults)

    @staticmethod
    def make_subscription_response(**overrides) -> SubscriptionResponseContract:
        """Create valid subscription response for assertions"""
        now = datetime.now(timezone.utc)
        defaults = {
            "subscription_id": ProductTestDataFactory.make_subscription_id(),
            "user_id": ProductTestDataFactory.make_user_id(),
            "organization_id": None,
            "plan_id": ProductTestDataFactory.make_plan_id(),
            "plan_tier": ProductTestDataFactory.make_plan_tier(),
            "status": "active",
            "billing_cycle": "monthly",
            "current_period_start": now,
            "current_period_end": now + timedelta(days=30),
            "metadata": {},
            "created_at": now,
            "updated_at": now,
        }
        defaults.update(overrides)
        return SubscriptionResponseContract(**defaults)

    @staticmethod
    def make_update_status_request(**overrides) -> UpdateSubscriptionStatusRequestContract:
        """Create valid status update request"""
        defaults = {
            "status": "canceled",
        }
        defaults.update(overrides)
        return UpdateSubscriptionStatusRequestContract(**defaults)

    @staticmethod
    def make_record_usage_request(**overrides) -> RecordUsageRequestContract:
        """Create valid usage recording request"""
        defaults = {
            "user_id": ProductTestDataFactory.make_user_id(),
            "product_id": ProductTestDataFactory.make_product_id(),
            "usage_amount": ProductTestDataFactory.make_usage_amount(),
            "organization_id": None,
            "subscription_id": None,
            "session_id": ProductTestDataFactory.make_session_id(),
            "request_id": ProductTestDataFactory.make_request_id(),
            "usage_details": ProductTestDataFactory.make_usage_details(),
            "usage_timestamp": datetime.now(timezone.utc),
        }
        defaults.update(overrides)
        return RecordUsageRequestContract(**defaults)

    @staticmethod
    def make_usage_response(**overrides) -> UsageRecordResponseContract:
        """Create valid usage response for assertions"""
        defaults = {
            "success": True,
            "message": "Usage recorded successfully",
            "usage_record_id": ProductTestDataFactory.make_usage_id(),
            "product": {"product_id": ProductTestDataFactory.make_product_id()},
            "recorded_amount": ProductTestDataFactory.make_usage_amount(),
            "timestamp": datetime.now(timezone.utc),
        }
        defaults.update(overrides)
        return UsageRecordResponseContract(**defaults)

    @staticmethod
    def make_availability_response(**overrides) -> ProductAvailabilityResponseContract:
        """Create valid availability response for assertions"""
        defaults = {
            "available": True,
            "product": {
                "product_id": ProductTestDataFactory.make_product_id(),
                "name": ProductTestDataFactory.make_product_name(),
                "is_active": True,
            },
            "reason": None,
        }
        defaults.update(overrides)
        return ProductAvailabilityResponseContract(**defaults)

    @staticmethod
    def make_usage_statistics_response(**overrides) -> UsageStatisticsResponseContract:
        """Create valid usage statistics response for assertions"""
        defaults = {
            "total_usage": random.uniform(10000, 100000),
            "usage_by_product": {
                ProductTestDataFactory.make_product_id(): random.uniform(5000, 50000),
            },
            "usage_by_date": {
                (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d"): random.uniform(1000, 10000),
            },
            "period": {
                "start_date": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
                "end_date": datetime.now(timezone.utc).isoformat(),
            },
        }
        defaults.update(overrides)
        return UsageStatisticsResponseContract(**defaults)

    @staticmethod
    def make_service_statistics_response(**overrides) -> ServiceStatisticsResponseContract:
        """Create valid service statistics response for assertions"""
        defaults = {
            "service": "product_service",
            "statistics": {
                "total_products": random.randint(20, 100),
                "active_subscriptions": random.randint(100, 5000),
                "usage_records_24h": random.randint(1000, 50000),
                "usage_records_7d": random.randint(10000, 200000),
                "usage_records_30d": random.randint(50000, 500000),
            },
            "timestamp": datetime.now(timezone.utc),
        }
        defaults.update(overrides)
        return ServiceStatisticsResponseContract(**defaults)

    @staticmethod
    def make_health_response(**overrides) -> ProductServiceHealthContract:
        """Create valid health response for assertions"""
        defaults = {
            "status": "healthy",
            "service": "product_service",
            "port": 8215,
            "version": "1.0.0",
            "dependencies": {"database": "healthy"},
        }
        defaults.update(overrides)
        return ProductServiceHealthContract(**defaults)

    # ========================================================================
    # Invalid Data Generators (for negative testing)
    # ========================================================================

    @staticmethod
    def make_invalid_subscription_request_missing_user_id() -> dict:
        """Generate subscription request missing required user_id"""
        return {
            "plan_id": ProductTestDataFactory.make_plan_id(),
            "billing_cycle": "monthly",
        }

    @staticmethod
    def make_invalid_subscription_request_missing_plan_id() -> dict:
        """Generate subscription request missing required plan_id"""
        return {
            "user_id": ProductTestDataFactory.make_user_id(),
            "billing_cycle": "monthly",
        }

    @staticmethod
    def make_invalid_subscription_request_invalid_billing_cycle() -> dict:
        """Generate subscription request with invalid billing cycle"""
        return {
            "user_id": ProductTestDataFactory.make_user_id(),
            "plan_id": ProductTestDataFactory.make_plan_id(),
            "billing_cycle": "invalid_cycle",
        }

    @staticmethod
    def make_invalid_status_update_invalid_status() -> dict:
        """Generate status update with invalid status"""
        return {
            "status": "invalid_status",
        }

    @staticmethod
    def make_invalid_usage_request_missing_user_id() -> dict:
        """Generate usage request missing required user_id"""
        return {
            "product_id": ProductTestDataFactory.make_product_id(),
            "usage_amount": 100,
        }

    @staticmethod
    def make_invalid_usage_request_missing_product_id() -> dict:
        """Generate usage request missing required product_id"""
        return {
            "user_id": ProductTestDataFactory.make_user_id(),
            "usage_amount": 100,
        }

    @staticmethod
    def make_invalid_usage_request_negative_amount() -> dict:
        """Generate usage request with negative amount"""
        return {
            "user_id": ProductTestDataFactory.make_user_id(),
            "product_id": ProductTestDataFactory.make_product_id(),
            "usage_amount": -100,
        }

    @staticmethod
    def make_invalid_usage_request_zero_amount() -> dict:
        """Generate usage request with zero amount"""
        return {
            "user_id": ProductTestDataFactory.make_user_id(),
            "product_id": ProductTestDataFactory.make_product_id(),
            "usage_amount": 0,
        }


# ============================================================================
# Request Builders (for complex test scenarios)
# ============================================================================

class CreateSubscriptionRequestBuilder:
    """
    Builder pattern for creating complex subscription requests.

    Example:
        request = (
            CreateSubscriptionRequestBuilder()
            .with_user_id("user_123")
            .with_plan_id("plan_pro_monthly")
            .with_billing_cycle("yearly")
            .build()
        )
    """

    def __init__(self):
        self._data = {
            "user_id": ProductTestDataFactory.make_user_id(),
            "plan_id": ProductTestDataFactory.make_plan_id(),
            "billing_cycle": "monthly",
            "organization_id": None,
            "metadata": None,
        }

    def with_user_id(self, user_id: str) -> "CreateSubscriptionRequestBuilder":
        """Set user ID"""
        self._data["user_id"] = user_id
        return self

    def with_plan_id(self, plan_id: str) -> "CreateSubscriptionRequestBuilder":
        """Set plan ID"""
        self._data["plan_id"] = plan_id
        return self

    def with_organization_id(self, organization_id: str) -> "CreateSubscriptionRequestBuilder":
        """Set organization ID"""
        self._data["organization_id"] = organization_id
        return self

    def with_billing_cycle(self, billing_cycle: str) -> "CreateSubscriptionRequestBuilder":
        """Set billing cycle"""
        self._data["billing_cycle"] = billing_cycle
        return self

    def with_metadata(self, metadata: Dict[str, Any]) -> "CreateSubscriptionRequestBuilder":
        """Set metadata"""
        self._data["metadata"] = metadata
        return self

    def build(self) -> CreateSubscriptionRequestContract:
        """Build the final request"""
        return CreateSubscriptionRequestContract(**self._data)


class RecordUsageRequestBuilder:
    """
    Builder pattern for creating complex usage recording requests.

    Example:
        request = (
            RecordUsageRequestBuilder()
            .with_user_id("user_123")
            .with_product_id("prod_claude_sonnet")
            .with_usage_amount(1500)
            .with_session_id("sess_456")
            .build()
        )
    """

    def __init__(self):
        self._data = {
            "user_id": ProductTestDataFactory.make_user_id(),
            "product_id": ProductTestDataFactory.make_product_id(),
            "usage_amount": 100,
            "organization_id": None,
            "subscription_id": None,
            "session_id": None,
            "request_id": None,
            "usage_details": None,
            "usage_timestamp": None,
        }

    def with_user_id(self, user_id: str) -> "RecordUsageRequestBuilder":
        """Set user ID"""
        self._data["user_id"] = user_id
        return self

    def with_product_id(self, product_id: str) -> "RecordUsageRequestBuilder":
        """Set product ID"""
        self._data["product_id"] = product_id
        return self

    def with_usage_amount(self, amount: float) -> "RecordUsageRequestBuilder":
        """Set usage amount"""
        self._data["usage_amount"] = amount
        return self

    def with_organization_id(self, organization_id: str) -> "RecordUsageRequestBuilder":
        """Set organization ID"""
        self._data["organization_id"] = organization_id
        return self

    def with_subscription_id(self, subscription_id: str) -> "RecordUsageRequestBuilder":
        """Set subscription ID"""
        self._data["subscription_id"] = subscription_id
        return self

    def with_session_id(self, session_id: str) -> "RecordUsageRequestBuilder":
        """Set session ID"""
        self._data["session_id"] = session_id
        return self

    def with_request_id(self, request_id: str) -> "RecordUsageRequestBuilder":
        """Set request ID"""
        self._data["request_id"] = request_id
        return self

    def with_usage_details(self, details: Dict[str, Any]) -> "RecordUsageRequestBuilder":
        """Set usage details"""
        self._data["usage_details"] = details
        return self

    def with_timestamp(self, timestamp: datetime) -> "RecordUsageRequestBuilder":
        """Set usage timestamp"""
        self._data["usage_timestamp"] = timestamp
        return self

    def build(self) -> RecordUsageRequestContract:
        """Build the final request"""
        return RecordUsageRequestContract(**self._data)


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Enum Contracts
    "ProductTypeEnum",
    "PricingTypeEnum",
    "SubscriptionStatusEnum",
    "BillingCycleEnum",
    "PlanTierEnum",

    # Response Contracts
    "ProductCategoryResponseContract",
    "ProductResponseContract",
    "ProductPricingResponseContract",
    "SubscriptionResponseContract",
    "UsageRecordResponseContract",
    "ProductAvailabilityResponseContract",
    "UsageStatisticsResponseContract",
    "ServiceStatisticsResponseContract",
    "ProductServiceHealthContract",

    # Request Contracts
    "CreateSubscriptionRequestContract",
    "UpdateSubscriptionStatusRequestContract",
    "RecordUsageRequestContract",

    # Factory
    "ProductTestDataFactory",

    # Builders
    "CreateSubscriptionRequestBuilder",
    "RecordUsageRequestBuilder",
]
