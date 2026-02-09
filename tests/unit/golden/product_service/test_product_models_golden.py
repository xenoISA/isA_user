"""
Unit Golden Tests: Product Service Models

Tests model validation and serialization without external dependencies.
"""
import pytest
from datetime import datetime, timezone, date, timedelta
from decimal import Decimal
from pydantic import ValidationError

from microservices.product_service.models import (
    # Enums
    ProductType,
    PricingType,
    UnitType,
    PlanTier,
    TargetAudience,
    DependencyType,
    Currency,
    SubscriptionStatus,
    BillingCycle,
    SupportLevel,
    # Core Models
    ProductCategory,
    Product,
    PricingModel,
    ServicePlan,
    ProductDependency,
    # Request/Response Models
    ProductSearchRequest,
    PricingCalculationRequest,
    PricingCalculationResponse,
    ProductCatalogResponse,
    # Subscription Models
    SubscriptionTier,
    CostDefinition,
    UserSubscription,
    SubscriptionUsage,
)


# ====================
# Enum Tests
# ====================


class TestProductType:
    """Test ProductType enum"""

    def test_product_type_values(self):
        """Test all product type values are defined"""
        assert ProductType.MODEL.value == "model"
        assert ProductType.MODEL_INFERENCE.value == "model_inference"
        assert ProductType.STORAGE.value == "storage"
        assert ProductType.STORAGE_MINIO.value == "storage_minio"
        assert ProductType.AGENT.value == "agent"
        assert ProductType.AGENT_EXECUTION.value == "agent_execution"
        assert ProductType.MCP_TOOL.value == "mcp_tool"
        assert ProductType.MCP_SERVICE.value == "mcp_service"
        assert ProductType.API_SERVICE.value == "api_service"
        assert ProductType.API_GATEWAY.value == "api_gateway"
        assert ProductType.NOTIFICATION.value == "notification"
        assert ProductType.COMPUTATION.value == "computation"
        assert ProductType.DATA_PROCESSING.value == "data_processing"
        assert ProductType.INTEGRATION.value == "integration"
        assert ProductType.OTHER.value == "other"

    def test_product_type_comparison(self):
        """Test product type comparison"""
        assert ProductType.MODEL != ProductType.STORAGE
        assert ProductType.AGENT == ProductType.AGENT
        assert ProductType.MODEL.value == "model"


class TestPricingType:
    """Test PricingType enum"""

    def test_pricing_type_values(self):
        """Test all pricing type values"""
        assert PricingType.USAGE_BASED.value == "usage_based"
        assert PricingType.SUBSCRIPTION.value == "subscription"
        assert PricingType.ONE_TIME.value == "one_time"
        assert PricingType.FREEMIUM.value == "freemium"
        assert PricingType.HYBRID.value == "hybrid"


class TestUnitType:
    """Test UnitType enum"""

    def test_unit_type_values(self):
        """Test all unit type values"""
        assert UnitType.TOKEN.value == "token"
        assert UnitType.REQUEST.value == "request"
        assert UnitType.MINUTE.value == "minute"
        assert UnitType.HOUR.value == "hour"
        assert UnitType.DAY.value == "day"
        assert UnitType.MB.value == "mb"
        assert UnitType.GB.value == "gb"
        assert UnitType.USER.value == "user"
        assert UnitType.NOTIFICATION.value == "notification"
        assert UnitType.EMAIL.value == "email"
        assert UnitType.ITEM.value == "item"


class TestPlanTier:
    """Test PlanTier enum"""

    def test_plan_tier_values(self):
        """Test all plan tier values"""
        assert PlanTier.FREE.value == "free"
        assert PlanTier.BASIC.value == "basic"
        assert PlanTier.PRO.value == "pro"
        assert PlanTier.ENTERPRISE.value == "enterprise"
        assert PlanTier.CUSTOM.value == "custom"


class TestTargetAudience:
    """Test TargetAudience enum"""

    def test_target_audience_values(self):
        """Test all target audience values"""
        assert TargetAudience.INDIVIDUAL.value == "individual"
        assert TargetAudience.TEAM.value == "team"
        assert TargetAudience.ENTERPRISE.value == "enterprise"


class TestDependencyType:
    """Test DependencyType enum"""

    def test_dependency_type_values(self):
        """Test all dependency type values"""
        assert DependencyType.REQUIRED.value == "required"
        assert DependencyType.OPTIONAL.value == "optional"
        assert DependencyType.ALTERNATIVE.value == "alternative"


class TestCurrency:
    """Test Currency enum"""

    def test_currency_values(self):
        """Test all currency values"""
        assert Currency.USD.value == "USD"
        assert Currency.EUR.value == "EUR"
        assert Currency.CNY.value == "CNY"
        assert Currency.CREDIT.value == "CREDIT"


class TestSubscriptionStatus:
    """Test SubscriptionStatus enum"""

    def test_subscription_status_values(self):
        """Test all subscription status values"""
        assert SubscriptionStatus.ACTIVE.value == "active"
        assert SubscriptionStatus.TRIALING.value == "trialing"
        assert SubscriptionStatus.PAST_DUE.value == "past_due"
        assert SubscriptionStatus.CANCELED.value == "canceled"
        assert SubscriptionStatus.INCOMPLETE.value == "incomplete"
        assert SubscriptionStatus.INCOMPLETE_EXPIRED.value == "incomplete_expired"
        assert SubscriptionStatus.UNPAID.value == "unpaid"
        assert SubscriptionStatus.PAUSED.value == "paused"


class TestBillingCycle:
    """Test BillingCycle enum"""

    def test_billing_cycle_values(self):
        """Test all billing cycle values"""
        assert BillingCycle.MONTHLY.value == "monthly"
        assert BillingCycle.QUARTERLY.value == "quarterly"
        assert BillingCycle.YEARLY.value == "yearly"
        assert BillingCycle.ONE_TIME.value == "one_time"


class TestSupportLevel:
    """Test SupportLevel enum"""

    def test_support_level_values(self):
        """Test all support level values"""
        assert SupportLevel.COMMUNITY.value == "community"
        assert SupportLevel.EMAIL.value == "email"
        assert SupportLevel.PRIORITY.value == "priority"
        assert SupportLevel.DEDICATED.value == "dedicated"


# ====================
# Core Model Tests
# ====================


class TestProductCategory:
    """Test ProductCategory model"""

    def test_product_category_creation_minimal(self):
        """Test creating product category with minimal fields"""
        category = ProductCategory(
            category_id="cat_ai_models",
            name="AI Models"
        )

        assert category.category_id == "cat_ai_models"
        assert category.name == "AI Models"
        assert category.description is None
        assert category.parent_category_id is None
        assert category.display_order == 0
        assert category.is_active is True
        assert category.metadata == {}

    def test_product_category_creation_full(self):
        """Test creating product category with all fields"""
        now = datetime.now(timezone.utc)
        metadata = {"icon": "cpu", "color": "#4A90E2"}

        category = ProductCategory(
            id=1,
            category_id="cat_ai_models_llm",
            name="Large Language Models",
            description="Advanced LLM services",
            parent_category_id="cat_ai_models",
            display_order=1,
            is_active=True,
            metadata=metadata,
            created_at=now,
            updated_at=now
        )

        assert category.id == 1
        assert category.category_id == "cat_ai_models_llm"
        assert category.name == "Large Language Models"
        assert category.description == "Advanced LLM services"
        assert category.parent_category_id == "cat_ai_models"
        assert category.display_order == 1
        assert category.metadata == metadata

    def test_product_category_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            ProductCategory(name="Test Category")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "category_id" in missing_fields


class TestProduct:
    """Test Product model"""

    def test_product_creation_minimal(self):
        """Test creating product with minimal fields"""
        product = Product(
            product_id="prod_claude_sonnet",
            category_id="cat_ai_models",
            name="Claude Sonnet 4.5",
            product_type=ProductType.MODEL
        )

        assert product.product_id == "prod_claude_sonnet"
        assert product.category_id == "cat_ai_models"
        assert product.name == "Claude Sonnet 4.5"
        assert product.product_type == ProductType.MODEL
        assert product.is_active is True
        assert product.is_public is True
        assert product.requires_approval is False
        assert product.version == "1.0"
        assert product.specifications == {}
        assert product.capabilities == []

    def test_product_creation_full(self):
        """Test creating product with all fields"""
        now = datetime.now(timezone.utc)
        specs = {"context_window": 200000, "max_tokens": 8192}
        capabilities = ["text_generation", "code_generation", "analysis"]
        limitations = {"rate_limit": "100 req/min"}
        metadata = {"region": "us-east-1"}

        product = Product(
            id=1,
            product_id="prod_claude_opus",
            category_id="cat_ai_models",
            name="Claude Opus 4.5",
            description="Most capable Claude model",
            short_description="Advanced reasoning and analysis",
            product_type=ProductType.MODEL_INFERENCE,
            provider="anthropic",
            specifications=specs,
            capabilities=capabilities,
            limitations=limitations,
            is_active=True,
            is_public=True,
            requires_approval=False,
            version="2.0",
            release_date=date(2025, 1, 1),
            deprecation_date=date(2026, 1, 1),
            service_endpoint="https://api.anthropic.com/v1",
            service_type="rest_api",
            metadata=metadata,
            created_at=now,
            updated_at=now
        )

        assert product.id == 1
        assert product.product_id == "prod_claude_opus"
        assert product.name == "Claude Opus 4.5"
        assert product.product_type == ProductType.MODEL_INFERENCE
        assert product.provider == "anthropic"
        assert product.specifications == specs
        assert product.capabilities == capabilities
        assert product.limitations == limitations
        assert product.version == "2.0"
        assert product.service_endpoint == "https://api.anthropic.com/v1"

    def test_product_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            Product(name="Test Product")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "product_id" in missing_fields
        assert "category_id" in missing_fields
        assert "product_type" in missing_fields


class TestPricingModel:
    """Test PricingModel model"""

    def test_pricing_model_creation_minimal(self):
        """Test creating pricing model with minimal fields"""
        pricing = PricingModel(
            pricing_model_id="price_claude_sonnet_v1",
            product_id="prod_claude_sonnet",
            name="Claude Sonnet Token Pricing",
            pricing_type=PricingType.USAGE_BASED
        )

        assert pricing.pricing_model_id == "price_claude_sonnet_v1"
        assert pricing.product_id == "prod_claude_sonnet"
        assert pricing.name == "Claude Sonnet Token Pricing"
        assert pricing.pricing_type == PricingType.USAGE_BASED
        assert pricing.base_unit_price == Decimal("0")
        assert pricing.currency == Currency.CREDIT
        assert pricing.is_active is True

    def test_pricing_model_usage_based(self):
        """Test usage-based pricing model"""
        pricing = PricingModel(
            pricing_model_id="price_claude_tokens",
            product_id="prod_claude_sonnet",
            name="Token-based Pricing",
            pricing_type=PricingType.USAGE_BASED,
            unit_type=UnitType.TOKEN,
            input_unit_price=Decimal("3.00"),
            output_unit_price=Decimal("15.00"),
            free_tier_limit=Decimal("1000000"),
            free_tier_period="monthly",
            currency=Currency.CREDIT
        )

        assert pricing.unit_type == UnitType.TOKEN
        assert pricing.input_unit_price == Decimal("3.00")
        assert pricing.output_unit_price == Decimal("15.00")
        assert pricing.free_tier_limit == Decimal("1000000")
        assert pricing.free_tier_period == "monthly"

    def test_pricing_model_subscription(self):
        """Test subscription-based pricing model"""
        pricing = PricingModel(
            pricing_model_id="price_pro_plan",
            product_id="prod_pro_subscription",
            name="Pro Plan Pricing",
            pricing_type=PricingType.SUBSCRIPTION,
            monthly_price=Decimal("20.00"),
            yearly_price=Decimal("200.00"),
            currency=Currency.USD
        )

        assert pricing.pricing_type == PricingType.SUBSCRIPTION
        assert pricing.monthly_price == Decimal("20.00")
        assert pricing.yearly_price == Decimal("200.00")
        assert pricing.currency == Currency.USD

    def test_pricing_model_with_tiers(self):
        """Test pricing model with tier pricing"""
        tier_pricing = [
            {"min": 0, "max": 1000000, "price": Decimal("3.00")},
            {"min": 1000001, "max": 10000000, "price": Decimal("2.50")},
            {"min": 10000001, "max": None, "price": Decimal("2.00")}
        ]

        pricing = PricingModel(
            pricing_model_id="price_tiered",
            product_id="prod_storage",
            name="Tiered Storage Pricing",
            pricing_type=PricingType.USAGE_BASED,
            unit_type=UnitType.GB,
            base_unit_price=Decimal("0.023"),
            tier_pricing=tier_pricing,
            currency=Currency.USD
        )

        assert pricing.tier_pricing == tier_pricing
        assert len(pricing.tier_pricing) == 3

    def test_pricing_model_decimal_validation(self):
        """Test that negative prices raise ValidationError"""
        with pytest.raises(ValidationError):
            PricingModel(
                pricing_model_id="price_invalid",
                product_id="prod_test",
                name="Invalid Pricing",
                pricing_type=PricingType.USAGE_BASED,
                base_unit_price=Decimal("-10.00")
            )


class TestServicePlan:
    """Test ServicePlan model"""

    def test_service_plan_creation_minimal(self):
        """Test creating service plan with minimal fields"""
        plan = ServicePlan(
            plan_id="plan_free",
            name="Free Plan",
            plan_tier=PlanTier.FREE
        )

        assert plan.plan_id == "plan_free"
        assert plan.name == "Free Plan"
        assert plan.plan_tier == PlanTier.FREE
        assert plan.monthly_price == Decimal("0")
        assert plan.yearly_price == Decimal("0")
        assert plan.currency == Currency.CREDIT
        assert plan.is_active is True

    def test_service_plan_creation_full(self):
        """Test creating service plan with all fields"""
        now = datetime.now(timezone.utc)
        included_products = [
            {"product_id": "prod_storage", "quota": 100},
            {"product_id": "prod_ai_model", "quota": 1000000}
        ]
        usage_limits = {
            "max_api_calls": 10000,
            "max_storage_gb": 100
        }
        features = [
            "24/7 support",
            "Priority queue",
            "Advanced analytics"
        ]
        overage_pricing = {
            "storage": {"unit": "gb", "price": Decimal("0.10")},
            "api_calls": {"unit": "request", "price": Decimal("0.001")}
        }

        plan = ServicePlan(
            id=1,
            plan_id="plan_enterprise",
            name="Enterprise Plan",
            description="Full-featured enterprise solution",
            plan_tier=PlanTier.ENTERPRISE,
            monthly_price=Decimal("500.00"),
            yearly_price=Decimal("5000.00"),
            setup_fee=Decimal("1000.00"),
            currency=Currency.USD,
            included_credits=Decimal("10000000"),
            credit_rollover=True,
            included_products=included_products,
            usage_limits=usage_limits,
            features=features,
            overage_pricing=overage_pricing,
            is_active=True,
            is_public=True,
            requires_approval=True,
            max_users=100,
            target_audience=TargetAudience.ENTERPRISE,
            metadata={"priority": "high"},
            created_at=now,
            updated_at=now
        )

        assert plan.id == 1
        assert plan.plan_id == "plan_enterprise"
        assert plan.name == "Enterprise Plan"
        assert plan.plan_tier == PlanTier.ENTERPRISE
        assert plan.monthly_price == Decimal("500.00")
        assert plan.yearly_price == Decimal("5000.00")
        assert plan.setup_fee == Decimal("1000.00")
        assert plan.included_credits == Decimal("10000000")
        assert plan.credit_rollover is True
        assert plan.included_products == included_products
        assert plan.usage_limits == usage_limits
        assert len(plan.features) == 3
        assert plan.requires_approval is True
        assert plan.max_users == 100
        assert plan.target_audience == TargetAudience.ENTERPRISE


class TestProductDependency:
    """Test ProductDependency model"""

    def test_product_dependency_creation(self):
        """Test creating product dependency"""
        now = datetime.now(timezone.utc)

        dependency = ProductDependency(
            id=1,
            product_id="prod_ai_agent",
            depends_on_product_id="prod_ai_model",
            dependency_type=DependencyType.REQUIRED,
            created_at=now
        )

        assert dependency.id == 1
        assert dependency.product_id == "prod_ai_agent"
        assert dependency.depends_on_product_id == "prod_ai_model"
        assert dependency.dependency_type == DependencyType.REQUIRED
        assert dependency.created_at == now

    def test_product_dependency_types(self):
        """Test different dependency types"""
        required_dep = ProductDependency(
            product_id="prod_a",
            depends_on_product_id="prod_b",
            dependency_type=DependencyType.REQUIRED
        )

        optional_dep = ProductDependency(
            product_id="prod_a",
            depends_on_product_id="prod_c",
            dependency_type=DependencyType.OPTIONAL
        )

        alternative_dep = ProductDependency(
            product_id="prod_a",
            depends_on_product_id="prod_d",
            dependency_type=DependencyType.ALTERNATIVE
        )

        assert required_dep.dependency_type == DependencyType.REQUIRED
        assert optional_dep.dependency_type == DependencyType.OPTIONAL
        assert alternative_dep.dependency_type == DependencyType.ALTERNATIVE


# ====================
# Request/Response Model Tests
# ====================


class TestProductSearchRequest:
    """Test ProductSearchRequest model"""

    def test_product_search_request_defaults(self):
        """Test default search parameters"""
        request = ProductSearchRequest()

        assert request.category_id is None
        assert request.product_type is None
        assert request.provider is None
        assert request.is_active is True
        assert request.is_public is True
        assert request.search_term is None
        assert request.limit == 50
        assert request.offset == 0

    def test_product_search_request_with_filters(self):
        """Test search request with filters"""
        request = ProductSearchRequest(
            category_id="cat_ai_models",
            product_type=ProductType.MODEL,
            provider="anthropic",
            is_active=True,
            is_public=True,
            search_term="claude",
            limit=20,
            offset=10
        )

        assert request.category_id == "cat_ai_models"
        assert request.product_type == ProductType.MODEL
        assert request.provider == "anthropic"
        assert request.search_term == "claude"
        assert request.limit == 20
        assert request.offset == 10

    def test_product_search_request_limit_validation(self):
        """Test limit validation (max 100)"""
        with pytest.raises(ValidationError):
            ProductSearchRequest(limit=101)

    def test_product_search_request_offset_validation(self):
        """Test offset validation (non-negative)"""
        with pytest.raises(ValidationError):
            ProductSearchRequest(offset=-1)


class TestPricingCalculationRequest:
    """Test PricingCalculationRequest model"""

    def test_pricing_calculation_request_minimal(self):
        """Test minimal pricing calculation request"""
        request = PricingCalculationRequest(
            product_id="prod_claude_sonnet",
            usage_amount=Decimal("1000000")
        )

        assert request.product_id == "prod_claude_sonnet"
        assert request.usage_amount == Decimal("1000000")
        assert request.unit_type is None
        assert request.user_plan_id is None
        assert request.calculation_date is None

    def test_pricing_calculation_request_full(self):
        """Test full pricing calculation request"""
        now = datetime.now(timezone.utc)

        request = PricingCalculationRequest(
            product_id="prod_storage",
            usage_amount=Decimal("50.5"),
            unit_type=UnitType.GB,
            user_plan_id="plan_pro",
            calculation_date=now
        )

        assert request.product_id == "prod_storage"
        assert request.usage_amount == Decimal("50.5")
        assert request.unit_type == UnitType.GB
        assert request.user_plan_id == "plan_pro"
        assert request.calculation_date == now

    def test_pricing_calculation_request_negative_usage(self):
        """Test that negative usage raises ValidationError"""
        with pytest.raises(ValidationError):
            PricingCalculationRequest(
                product_id="prod_test",
                usage_amount=Decimal("-100")
            )


class TestPricingCalculationResponse:
    """Test PricingCalculationResponse model"""

    def test_pricing_calculation_response_basic(self):
        """Test basic pricing calculation response"""
        response = PricingCalculationResponse(
            product_id="prod_claude_sonnet",
            pricing_model_id="price_claude_v1",
            usage_amount=Decimal("1000000"),
            unit_type=UnitType.TOKEN,
            unit_price=Decimal("3.00"),
            total_cost=Decimal("3000.00"),
            currency=Currency.CREDIT
        )

        assert response.product_id == "prod_claude_sonnet"
        assert response.pricing_model_id == "price_claude_v1"
        assert response.usage_amount == Decimal("1000000")
        assert response.unit_type == UnitType.TOKEN
        assert response.unit_price == Decimal("3.00")
        assert response.total_cost == Decimal("3000.00")
        assert response.currency == Currency.CREDIT
        assert response.free_tier_applied is False
        assert response.plan_discount_applied is False

    def test_pricing_calculation_response_with_free_tier(self):
        """Test pricing calculation with free tier applied"""
        response = PricingCalculationResponse(
            product_id="prod_test",
            pricing_model_id="price_test",
            usage_amount=Decimal("2000000"),
            unit_type=UnitType.TOKEN,
            unit_price=Decimal("3.00"),
            total_cost=Decimal("3000.00"),
            currency=Currency.CREDIT,
            free_tier_applied=True,
            free_tier_used=Decimal("1000000"),
            free_tier_remaining=Decimal("0")
        )

        assert response.free_tier_applied is True
        assert response.free_tier_used == Decimal("1000000")
        assert response.free_tier_remaining == Decimal("0")

    def test_pricing_calculation_response_with_plan_discount(self):
        """Test pricing calculation with plan discount"""
        tier_breakdown = [
            {"tier": 1, "amount": 1000000, "rate": Decimal("3.00"), "cost": Decimal("3000.00")},
            {"tier": 2, "amount": 1000000, "rate": Decimal("2.50"), "cost": Decimal("2500.00")}
        ]

        response = PricingCalculationResponse(
            product_id="prod_test",
            pricing_model_id="price_test",
            usage_amount=Decimal("2000000"),
            unit_type=UnitType.TOKEN,
            unit_price=Decimal("2.75"),
            total_cost=Decimal("4950.00"),
            currency=Currency.CREDIT,
            tier_breakdown=tier_breakdown,
            plan_discount_applied=True,
            plan_discount_amount=Decimal("550.00")
        )

        assert response.tier_breakdown == tier_breakdown
        assert response.plan_discount_applied is True
        assert response.plan_discount_amount == Decimal("550.00")


class TestProductCatalogResponse:
    """Test ProductCatalogResponse model"""

    def test_product_catalog_response(self):
        """Test product catalog response"""
        categories = [
            ProductCategory(category_id="cat_1", name="Category 1"),
            ProductCategory(category_id="cat_2", name="Category 2")
        ]

        products = [
            Product(
                product_id="prod_1",
                category_id="cat_1",
                name="Product 1",
                product_type=ProductType.MODEL
            )
        ]

        pricing_models = [
            PricingModel(
                pricing_model_id="price_1",
                product_id="prod_1",
                name="Pricing 1",
                pricing_type=PricingType.USAGE_BASED
            )
        ]

        service_plans = [
            ServicePlan(
                plan_id="plan_1",
                name="Plan 1",
                plan_tier=PlanTier.FREE
            )
        ]

        filters = {"category": "cat_1", "active": True}

        response = ProductCatalogResponse(
            categories=categories,
            products=products,
            pricing_models=pricing_models,
            service_plans=service_plans,
            total_products=1,
            filters_applied=filters
        )

        assert len(response.categories) == 2
        assert len(response.products) == 1
        assert len(response.pricing_models) == 1
        assert len(response.service_plans) == 1
        assert response.total_products == 1
        assert response.filters_applied == filters


# ====================
# Subscription Model Tests
# ====================


class TestSubscriptionTier:
    """Test SubscriptionTier model"""

    def test_subscription_tier_creation_minimal(self):
        """Test creating subscription tier with minimal fields"""
        tier = SubscriptionTier(
            tier_id="tier_free",
            tier_name="Free",
            tier_code="free"
        )

        assert tier.tier_id == "tier_free"
        assert tier.tier_name == "Free"
        assert tier.tier_code == "free"
        assert tier.monthly_price_usd == Decimal("0")
        assert tier.yearly_price_usd is None
        assert tier.monthly_credits == 0
        assert tier.credit_rollover is False
        assert tier.target_audience == TargetAudience.INDIVIDUAL
        assert tier.support_level == SupportLevel.COMMUNITY
        assert tier.is_active is True

    def test_subscription_tier_creation_full(self):
        """Test creating subscription tier with all fields"""
        now = datetime.now(timezone.utc)
        features = ["Unlimited API calls", "Priority support", "Custom integrations"]
        usage_limits = {"max_requests_per_day": 100000}

        tier = SubscriptionTier(
            id=1,
            tier_id="tier_enterprise",
            tier_name="Enterprise",
            tier_code="enterprise",
            description="Enterprise-grade solution",
            monthly_price_usd=Decimal("500.00"),
            yearly_price_usd=Decimal("5000.00"),
            monthly_credits=10000000,
            credit_rollover=True,
            max_rollover_credits=5000000,
            target_audience=TargetAudience.ENTERPRISE,
            min_seats=10,
            max_seats=1000,
            per_seat_price_usd=Decimal("50.00"),
            features=features,
            usage_limits=usage_limits,
            support_level=SupportLevel.DEDICATED,
            priority_queue=True,
            is_active=True,
            is_public=True,
            display_order=3,
            trial_days=30,
            metadata={"recommended": True},
            created_at=now,
            updated_at=now
        )

        assert tier.id == 1
        assert tier.tier_id == "tier_enterprise"
        assert tier.tier_name == "Enterprise"
        assert tier.monthly_price_usd == Decimal("500.00")
        assert tier.yearly_price_usd == Decimal("5000.00")
        assert tier.monthly_credits == 10000000
        assert tier.credit_rollover is True
        assert tier.max_rollover_credits == 5000000
        assert tier.min_seats == 10
        assert tier.max_seats == 1000
        assert tier.per_seat_price_usd == Decimal("50.00")
        assert len(tier.features) == 3
        assert tier.support_level == SupportLevel.DEDICATED
        assert tier.priority_queue is True
        assert tier.trial_days == 30

    def test_subscription_tier_validation_negative_price(self):
        """Test that negative prices raise ValidationError"""
        with pytest.raises(ValidationError):
            SubscriptionTier(
                tier_id="tier_invalid",
                tier_name="Invalid",
                tier_code="invalid",
                monthly_price_usd=Decimal("-10.00")
            )

    def test_subscription_tier_validation_min_seats(self):
        """Test that min_seats must be at least 1"""
        with pytest.raises(ValidationError):
            SubscriptionTier(
                tier_id="tier_invalid",
                tier_name="Invalid",
                tier_code="invalid",
                min_seats=0
            )


class TestCostDefinition:
    """Test CostDefinition model"""

    def test_cost_definition_creation_minimal(self):
        """Test creating cost definition with minimal fields"""
        cost = CostDefinition(
            cost_id="cost_claude_input",
            service_type="model_inference",
            cost_per_unit=300,
            unit_type="token"
        )

        assert cost.cost_id == "cost_claude_input"
        assert cost.service_type == "model_inference"
        assert cost.cost_per_unit == 300
        assert cost.unit_type == "token"
        assert cost.unit_size == 1
        assert cost.margin_percentage == Decimal("30.0")
        assert cost.free_tier_limit == 0
        assert cost.is_active is True

    def test_cost_definition_creation_full(self):
        """Test creating cost definition with all fields"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=365)

        cost = CostDefinition(
            id=1,
            cost_id="cost_claude_sonnet_input",
            product_id="prod_claude_sonnet",
            service_type="model_inference",
            provider="anthropic",
            model_name="claude-sonnet-4-20250514",
            operation_type="input",
            cost_per_unit=300,
            unit_type="token",
            unit_size=1000,
            original_cost_usd=Decimal("0.003"),
            margin_percentage=Decimal("30.0"),
            effective_from=now,
            effective_until=future,
            free_tier_limit=1000000,
            free_tier_period="monthly",
            is_active=True,
            description="Claude Sonnet input token cost",
            metadata={"version": "1.0"},
            created_at=now,
            updated_at=now
        )

        assert cost.id == 1
        assert cost.cost_id == "cost_claude_sonnet_input"
        assert cost.product_id == "prod_claude_sonnet"
        assert cost.service_type == "model_inference"
        assert cost.provider == "anthropic"
        assert cost.model_name == "claude-sonnet-4-20250514"
        assert cost.operation_type == "input"
        assert cost.cost_per_unit == 300
        assert cost.unit_type == "token"
        assert cost.unit_size == 1000
        assert cost.original_cost_usd == Decimal("0.003")
        assert cost.free_tier_limit == 1000000
        assert cost.free_tier_period == "monthly"

    def test_cost_definition_validation_negative_cost(self):
        """Test that negative cost raises ValidationError"""
        with pytest.raises(ValidationError):
            CostDefinition(
                cost_id="cost_invalid",
                service_type="test",
                cost_per_unit=-100,
                unit_type="token"
            )

    def test_cost_definition_validation_unit_size(self):
        """Test that unit_size must be at least 1"""
        with pytest.raises(ValidationError):
            CostDefinition(
                cost_id="cost_invalid",
                service_type="test",
                cost_per_unit=100,
                unit_type="token",
                unit_size=0
            )


class TestUserSubscription:
    """Test UserSubscription model"""

    def test_user_subscription_creation_minimal(self):
        """Test creating user subscription with minimal fields"""
        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=30)

        subscription = UserSubscription(
            subscription_id="sub_test_123",
            user_id="user_456",
            plan_id="plan_pro",
            plan_tier=PlanTier.PRO,
            status=SubscriptionStatus.ACTIVE,
            billing_cycle=BillingCycle.MONTHLY,
            current_period_start=now,
            current_period_end=period_end
        )

        assert subscription.subscription_id == "sub_test_123"
        assert subscription.user_id == "user_456"
        assert subscription.plan_id == "plan_pro"
        assert subscription.plan_tier == PlanTier.PRO
        assert subscription.status == SubscriptionStatus.ACTIVE
        assert subscription.billing_cycle == BillingCycle.MONTHLY
        assert subscription.cancel_at_period_end is False
        assert subscription.usage_this_period == {}

    def test_user_subscription_creation_full(self):
        """Test creating user subscription with all fields"""
        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=30)
        trial_start = now - timedelta(days=14)
        trial_end = now

        usage = {
            "api_calls": 5000,
            "storage_gb": 25.5
        }
        quotas = {
            "max_api_calls": 100000,
            "max_storage_gb": 100
        }

        subscription = UserSubscription(
            id=1,
            subscription_id="sub_enterprise_123",
            user_id="user_789",
            organization_id="org_456",
            plan_id="plan_enterprise",
            plan_tier=PlanTier.ENTERPRISE,
            status=SubscriptionStatus.ACTIVE,
            billing_cycle=BillingCycle.YEARLY,
            current_period_start=now,
            current_period_end=period_end,
            trial_start=trial_start,
            trial_end=trial_end,
            cancel_at_period_end=False,
            canceled_at=None,
            cancellation_reason=None,
            next_billing_date=period_end,
            payment_method_id="pm_123",
            external_subscription_id="stripe_sub_xyz",
            usage_this_period=usage,
            quota_limits=quotas,
            metadata={"source": "web"},
            created_at=now,
            updated_at=now
        )

        assert subscription.id == 1
        assert subscription.subscription_id == "sub_enterprise_123"
        assert subscription.user_id == "user_789"
        assert subscription.organization_id == "org_456"
        assert subscription.plan_tier == PlanTier.ENTERPRISE
        assert subscription.billing_cycle == BillingCycle.YEARLY
        assert subscription.trial_start == trial_start
        assert subscription.trial_end == trial_end
        assert subscription.payment_method_id == "pm_123"
        assert subscription.external_subscription_id == "stripe_sub_xyz"
        assert subscription.usage_this_period == usage
        assert subscription.quota_limits == quotas

    def test_user_subscription_cancellation(self):
        """Test subscription cancellation"""
        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=30)
        canceled_time = now

        subscription = UserSubscription(
            subscription_id="sub_canceled_123",
            user_id="user_999",
            plan_id="plan_pro",
            plan_tier=PlanTier.PRO,
            status=SubscriptionStatus.CANCELED,
            billing_cycle=BillingCycle.MONTHLY,
            current_period_start=now,
            current_period_end=period_end,
            cancel_at_period_end=True,
            canceled_at=canceled_time,
            cancellation_reason="Cost concerns"
        )

        assert subscription.status == SubscriptionStatus.CANCELED
        assert subscription.cancel_at_period_end is True
        assert subscription.canceled_at == canceled_time
        assert subscription.cancellation_reason == "Cost concerns"

    def test_user_subscription_trial(self):
        """Test subscription in trial period"""
        now = datetime.now(timezone.utc)
        trial_start = now
        trial_end = now + timedelta(days=14)
        period_end = now + timedelta(days=30)

        subscription = UserSubscription(
            subscription_id="sub_trial_123",
            user_id="user_111",
            plan_id="plan_pro",
            plan_tier=PlanTier.PRO,
            status=SubscriptionStatus.TRIALING,
            billing_cycle=BillingCycle.MONTHLY,
            current_period_start=now,
            current_period_end=period_end,
            trial_start=trial_start,
            trial_end=trial_end
        )

        assert subscription.status == SubscriptionStatus.TRIALING
        assert subscription.trial_start == trial_start
        assert subscription.trial_end == trial_end


class TestSubscriptionUsage:
    """Test SubscriptionUsage model"""

    def test_subscription_usage_creation_minimal(self):
        """Test creating subscription usage with minimal fields"""
        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=30)

        usage = SubscriptionUsage(
            subscription_id="sub_123",
            user_id="user_456",
            period_start=now,
            period_end=period_end
        )

        assert usage.subscription_id == "sub_123"
        assert usage.user_id == "user_456"
        assert usage.period_start == now
        assert usage.period_end == period_end
        assert usage.product_usage == {}
        assert usage.total_usage_cost == Decimal("0")
        assert usage.credits_consumed == Decimal("0")
        assert usage.is_billed is False

    def test_subscription_usage_creation_full(self):
        """Test creating subscription usage with all fields"""
        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=30)
        billed_time = now + timedelta(days=31)

        product_usage_data = {
            "prod_claude_sonnet": {
                "usage_amount": 5000000,
                "cost": Decimal("15000.00")
            },
            "prod_storage": {
                "usage_amount": 50,
                "cost": Decimal("1.15")
            }
        }

        usage = SubscriptionUsage(
            id=1,
            subscription_id="sub_123",
            user_id="user_456",
            organization_id="org_789",
            period_start=now,
            period_end=period_end,
            product_usage=product_usage_data,
            total_usage_cost=Decimal("15001.15"),
            credits_consumed=Decimal("15001.15"),
            is_billed=True,
            billed_at=billed_time,
            created_at=now,
            updated_at=now
        )

        assert usage.id == 1
        assert usage.subscription_id == "sub_123"
        assert usage.organization_id == "org_789"
        assert usage.product_usage == product_usage_data
        assert usage.total_usage_cost == Decimal("15001.15")
        assert usage.credits_consumed == Decimal("15001.15")
        assert usage.is_billed is True
        assert usage.billed_at == billed_time

    def test_subscription_usage_validation_negative_cost(self):
        """Test that negative cost raises ValidationError"""
        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=30)

        with pytest.raises(ValidationError):
            SubscriptionUsage(
                subscription_id="sub_invalid",
                user_id="user_123",
                period_start=now,
                period_end=period_end,
                total_usage_cost=Decimal("-100.00")
            )

    def test_subscription_usage_validation_negative_credits(self):
        """Test that negative credits raises ValidationError"""
        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=30)

        with pytest.raises(ValidationError):
            SubscriptionUsage(
                subscription_id="sub_invalid",
                user_id="user_123",
                period_start=now,
                period_end=period_end,
                credits_consumed=Decimal("-50.00")
            )


if __name__ == "__main__":
    pytest.main([__file__])
