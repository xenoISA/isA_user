"""
Product Service Business Logic

产品服务核心业务逻辑，处理产品目录、定价和订阅管理
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import uuid

from .product_repository import ProductRepository
from .models import (
    Product, ProductCategory, PricingModel, ServicePlan, UserSubscription,
    SubscriptionUsage, ProductUsageRecord,
    ProductType, PricingType, SubscriptionStatus, BillingCycle, Currency
)
from .events.publishers import (
    publish_subscription_created,
    publish_subscription_status_changed,
    publish_product_usage_recorded
)
from .clients import AccountClient, OrganizationClient

logger = logging.getLogger(__name__)


class ProductService:
    """产品服务核心业务逻辑"""

    _QUANTIZE_PRICE = Decimal("0.00000001")

    def __init__(
        self,
        repository: ProductRepository,
        event_bus=None,
        account_client: Optional[AccountClient] = None,
        organization_client: Optional[OrganizationClient] = None
    ):
        """
        Initialize Product Service

        Args:
            repository: Product repository instance
            event_bus: NATS event bus instance (optional)
            account_client: Account service client (optional)
            organization_client: Organization service client (optional)
        """
        self.repository = repository
        self.event_bus = event_bus
        self.account_client = account_client
        self.organization_client = organization_client

        logger.info("✅ ProductService initialized")

    # ====================
    # 产品目录管理
    # ====================

    async def get_product_categories(self) -> List[ProductCategory]:
        """获取产品类别列表"""
        try:
            return await self.repository.get_categories()
        except Exception as e:
            logger.error(f"Error getting product categories: {e}")
            raise

    async def get_products(
        self,
        category_id: Optional[str] = None,
        product_type: Optional[ProductType] = None,
        is_active: bool = True
    ) -> List[Product]:
        """获取产品列表"""
        try:
            return await self.repository.get_products(
                category=category_id,
                product_type=product_type,
                is_active=is_active
            )
        except Exception as e:
            logger.error(f"Error getting products: {e}")
            raise

    async def get_product(self, product_id: str) -> Optional[Product]:
        """获取单个产品信息"""
        try:
            return await self.repository.get_product(product_id)
        except Exception as e:
            logger.error(f"Error getting product {product_id}: {e}")
            raise

    async def get_product_pricing(
        self,
        product_id: str,
        user_id: Optional[str] = None,
        subscription_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """获取产品定价信息"""
        try:
            return await self.repository.get_product_pricing(
                product_id=product_id,
                user_id=user_id,
                subscription_id=subscription_id
            )
        except Exception as e:
            logger.error(f"Error getting product pricing for {product_id}: {e}")
            raise

    async def lookup_cost(
        self,
        service_type: str,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        operation_type: Optional[str] = None,
        service_surface: Optional[str] = None,
        backend: Optional[str] = None,
        engine_used: Optional[str] = None,
        gpu_type: Optional[str] = None,
        gpu_count: Optional[int] = None,
        prefill_seconds: Optional[float] = None,
        generation_seconds: Optional[float] = None,
        queue_seconds: Optional[float] = None,
        cold_start_seconds: Optional[float] = None,
        warm_path: Optional[bool] = None,
        kv_cache_peak_bytes: Optional[int] = None,
        kv_cache_gib_seconds: Optional[float] = None,
        scheduler_share: Optional[float] = None,
        batch_share: Optional[float] = None,
        tenancy_mode: Optional[str] = None,
        region: Optional[str] = None,
        preemptible: Optional[bool] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Lookup an active cost definition in a shape compatible with isa_model."""
        try:
            lookup_name = tool_name or model_name
            cost_lookup_provider = provider
            if service_type == "model_inference":
                cost_lookup_provider = None

            cost_definitions = await self.repository.get_cost_definitions(
                is_active=True,
                provider=cost_lookup_provider,
                service_type=service_type,
            )

            if service_type == "model_inference":
                return self._build_model_inference_cost_lookup(
                    cost_definitions,
                    lookup_name,
                    provider=provider,
                    backend=backend,
                    engine_used=engine_used,
                )

            cost_definition = self._select_cost_definition(
                cost_definitions,
                lookup_name,
                operation_type,
                service_type,
            )
            if not cost_definition:
                return {"success": False, "message": "Cost definition not found"}

            return self._format_cost_lookup_response(cost_definition)
        except Exception as e:
            logger.error("Error looking up cost definition: %s", e)
            raise

    async def calculate_price(
        self,
        product_id: str,
        quantity: Decimal,
        unit_type: Optional[str] = None,
        tier_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Calculate a compatibility pricing response for isa_model."""
        try:
            product = await self.repository.get_product(product_id)
            if not product or not product.is_active:
                return {"success": False, "message": "Product not found"}

            pricing_rows = await self.repository.get_product_pricing_rows(product_id)
            if not pricing_rows:
                return self._build_fallback_price_response(
                    product=product,
                    quantity=quantity,
                    unit_type=unit_type,
                    tier_code=tier_code,
                )

            selected_row = self._select_pricing_row_for_quantity(pricing_rows, quantity)
            if not selected_row:
                return {"success": False, "message": "Pricing definition not found"}

            resolved_unit_type = self._resolve_unit_type(
                requested_unit_type=unit_type,
                product=product,
                pricing_row=selected_row,
            )
            unit_price = Decimal(str(selected_row.get("unit_price", product.base_price)))
            total_price = (quantity * unit_price).quantize(self._QUANTIZE_PRICE, rounding=ROUND_HALF_UP)

            tier_breakdown = [
                {
                    "tier_name": row.get("tier_name"),
                    "min_quantity": row.get("min_quantity"),
                    "max_quantity": row.get("max_quantity"),
                    "unit_price": float(row.get("unit_price", 0)),
                    "currency": row.get("currency", product.currency.value),
                }
                for row in pricing_rows
            ]

            return {
                "success": True,
                "product_id": product_id,
                "quantity": quantity,
                "unit_type": resolved_unit_type,
                "unit_price": unit_price,
                "total_price": total_price,
                "total_cost": total_price,
                "currency": str(selected_row.get("currency", product.currency.value)),
                "pricing_found": True,
                "pricing_model_id": selected_row.get("pricing_id"),
                "tier_name": selected_row.get("tier_name"),
                "tier_breakdown": tier_breakdown,
                "plan_discount_applied": False,
                "plan_discount_amount": Decimal("0"),
                "metadata": {
                    "tier_code": tier_code,
                    "billing_interval": product.billing_interval,
                    "product_type": product.product_type.value,
                    "billing_profile": product.billing_profile.as_metadata(),
                },
            }
        except Exception as e:
            logger.error("Error calculating price for %s: %s", product_id, e)
            raise

    @staticmethod
    def _format_cost_lookup_response(
        cost_definition: Dict[str, Any],
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        response = {
            "success": True,
            "message": "Cost definition found",
            "cost_definition": cost_definition,
            "cost_per_unit": cost_definition.get("cost_per_unit"),
            "unit_type": cost_definition.get("unit_type"),
            "unit_size": cost_definition.get("unit_size"),
            "free_tier_limit": cost_definition.get("free_tier_limit"),
            "free_tier_period": cost_definition.get("free_tier_period"),
        }
        if extra_fields:
            response.update(extra_fields)
        return response

    @staticmethod
    def _select_cost_definition(
        cost_definitions: List[Dict[str, Any]],
        model_name: Optional[str],
        operation_type: Optional[str],
        service_type: str,
    ) -> Optional[Dict[str, Any]]:
        candidates = cost_definitions
        if model_name:
            candidates = [
                item for item in candidates
                if item.get("model_name") == model_name
            ]

        operation_candidates = ProductService._operation_candidates(
            service_type,
            operation_type,
        )
        if operation_candidates:
            for candidate in candidates:
                if candidate.get("operation_type") in operation_candidates:
                    return candidate

        if model_name and candidates:
            return candidates[0]
        if not model_name and not operation_type and candidates:
            return candidates[0]
        return None

    @staticmethod
    def _operation_candidates(service_type: str, operation_type: Optional[str]) -> List[str]:
        if not operation_type:
            return []
        aliases = {
            ("mcp_service", "tool_call"): ["request", "execution", "minute", "image", "character"],
            ("storage_minio", "download"): ["egress_gb"],
            ("storage_minio", "storage_month"): ["storage_gb_month"],
        }
        return [operation_type, *aliases.get((service_type, operation_type), [])]

    @staticmethod
    def _normalize_runtime_value(value: Optional[str]) -> Optional[str]:
        normalized = (value or "").strip().lower()
        return normalized or None

    def _normalize_model_inference_runtime(
        self,
        provider: Optional[str],
        backend: Optional[str],
        engine_used: Optional[str],
    ):
        local_gpu_engines = {"vllm", "sglang", "triton", "onnx"}
        normalized_provider = self._normalize_runtime_value(provider)
        normalized_backend = self._normalize_runtime_value(backend)
        normalized_engine = self._normalize_runtime_value(engine_used)

        if normalized_engine is None and normalized_provider in local_gpu_engines:
            normalized_engine = normalized_provider
        if normalized_backend is None and normalized_engine in local_gpu_engines:
            normalized_backend = "local_gpu"

        return normalized_backend, normalized_engine

    def _extract_model_inference_runtime(self, cost_definition: Dict[str, Any]):
        metadata = cost_definition.get("metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {}
        backend = self._normalize_runtime_value(
            metadata.get("backend") or metadata.get("runtime_backend")
        )
        engine_used = self._normalize_runtime_value(
            metadata.get("engine_used") or metadata.get("engine")
        )
        return backend, engine_used

    def _score_model_inference_definition(
        self,
        cost_definition: Dict[str, Any],
        model_name: Optional[str],
        provider: Optional[str],
        backend: Optional[str],
        engine_used: Optional[str],
    ) -> Optional[int]:
        normalized_provider = self._normalize_runtime_value(provider)
        requested_backend, requested_engine = self._normalize_model_inference_runtime(
            provider,
            backend,
            engine_used,
        )
        item_provider = self._normalize_runtime_value(cost_definition.get("provider"))
        item_model_name = cost_definition.get("model_name")
        if model_name and item_model_name not in (model_name, None, ""):
            return None

        if normalized_provider:
            allowed_providers = {normalized_provider}
            if requested_engine:
                allowed_providers.add(requested_engine)
            if item_provider not in allowed_providers and item_provider is not None:
                return None

        item_backend, item_engine = self._extract_model_inference_runtime(cost_definition)
        if requested_engine and item_engine not in (None, requested_engine):
            return None
        if requested_backend and item_backend not in (None, requested_backend):
            return None

        score = 0
        if model_name:
            if item_model_name == model_name:
                score += 100
            elif item_model_name in (None, ""):
                score += 10
        elif item_model_name in (None, ""):
            score += 5

        if normalized_provider:
            if item_provider == requested_engine and requested_engine:
                score += 60
            elif item_provider == normalized_provider:
                score += 40
        elif item_provider is None:
            score += 5

        if requested_engine:
            if item_engine == requested_engine:
                score += 200
        elif item_engine is not None:
            score -= 20

        if requested_backend:
            if item_backend == requested_backend:
                score += 100
        elif item_backend is not None:
            score -= 10

        if cost_definition.get("operation_type") in {"input", "output"}:
            score += 1

        return score

    def _select_best_model_inference_definition(
        self,
        cost_definitions: List[Dict[str, Any]],
        operation_type: Optional[str],
        model_name: Optional[str],
        provider: Optional[str],
        backend: Optional[str],
        engine_used: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        best_definition = None
        best_score = None
        for item in cost_definitions:
            if operation_type and item.get("operation_type") != operation_type:
                continue
            score = self._score_model_inference_definition(
                item,
                model_name=model_name,
                provider=provider,
                backend=backend,
                engine_used=engine_used,
            )
            if score is None:
                continue
            if best_score is None or score > best_score:
                best_definition = item
                best_score = score
        return best_definition

    def _build_model_inference_cost_lookup(
        self,
        cost_definitions: List[Dict[str, Any]],
        model_name: Optional[str],
        provider: Optional[str] = None,
        backend: Optional[str] = None,
        engine_used: Optional[str] = None,
    ) -> Dict[str, Any]:
        input_definition = self._select_best_model_inference_definition(
            cost_definitions,
            operation_type="input",
            model_name=model_name,
            provider=provider,
            backend=backend,
            engine_used=engine_used,
        )
        output_definition = self._select_best_model_inference_definition(
            cost_definitions,
            operation_type="output",
            model_name=model_name,
            provider=provider,
            backend=backend,
            engine_used=engine_used,
        )
        primary = (
            input_definition
            or output_definition
            or self._select_best_model_inference_definition(
                cost_definitions,
                operation_type=None,
                model_name=model_name,
                provider=provider,
                backend=backend,
                engine_used=engine_used,
            )
        )
        if not primary:
            return {"success": False, "message": "Cost definition not found"}

        resolved_input = input_definition or primary
        resolved_output = output_definition

        return self._format_cost_lookup_response(
            primary,
            extra_fields={
                "input_cost_per_unit": (
                    resolved_input.get("cost_per_unit") if resolved_input else 0
                ),
                "output_cost_per_unit": (
                    resolved_output.get("cost_per_unit") if resolved_output else 0
                ),
                "input_unit_size": (
                    resolved_input.get("unit_size") if resolved_input else primary.get("unit_size")
                ),
                "output_unit_size": (
                    resolved_output.get("unit_size") if resolved_output else 0
                ),
                "input_unit_type": (
                    resolved_input.get("unit_type") if resolved_input else primary.get("unit_type")
                ),
                "output_unit_type": (
                    resolved_output.get("unit_type") if resolved_output else None
                ),
            },
        )

    def _build_fallback_price_response(
        self,
        *,
        product: Product,
        quantity: Decimal,
        unit_type: Optional[str],
        tier_code: Optional[str],
    ) -> Dict[str, Any]:
        resolved_unit_type = unit_type or self._infer_unit_type_from_billing_interval(product.billing_interval)
        unit_price = Decimal(str(product.base_price))
        total_price = (quantity * unit_price).quantize(self._QUANTIZE_PRICE, rounding=ROUND_HALF_UP)
        return {
            "success": True,
            "product_id": product.product_id,
            "quantity": quantity,
            "unit_type": resolved_unit_type,
            "unit_price": unit_price,
            "total_price": total_price,
            "total_cost": total_price,
            "currency": product.currency.value,
            "pricing_found": False,
            "pricing_model_id": None,
            "tier_name": "base",
            "tier_breakdown": [],
            "plan_discount_applied": False,
            "plan_discount_amount": Decimal("0"),
            "metadata": {
                "tier_code": tier_code,
                "billing_interval": product.billing_interval,
                "product_type": product.product_type.value,
                "billing_profile": product.billing_profile.as_metadata(),
                "fallback": True,
            },
        }

    @staticmethod
    def _select_pricing_row_for_quantity(
        pricing_rows: List[Dict[str, Any]],
        quantity: Decimal,
    ) -> Optional[Dict[str, Any]]:
        for row in pricing_rows:
            min_quantity = Decimal(str(row.get("min_quantity", 0)))
            max_quantity_raw = row.get("max_quantity")
            if quantity < min_quantity:
                continue
            if max_quantity_raw is None:
                return row
            max_quantity = Decimal(str(max_quantity_raw))
            if quantity <= max_quantity:
                return row
        return pricing_rows[-1] if pricing_rows else None

    def _resolve_unit_type(
        self,
        *,
        requested_unit_type: Optional[str],
        product: Product,
        pricing_row: Dict[str, Any],
    ) -> str:
        if requested_unit_type:
            return requested_unit_type

        metadata = pricing_row.get("metadata")
        if isinstance(metadata, str):
            try:
                import json as _json
                metadata = _json.loads(metadata)
            except Exception:
                metadata = {}
        if isinstance(metadata, dict) and metadata.get("unit"):
            return str(metadata["unit"])

        return self._infer_unit_type_from_billing_interval(product.billing_interval)

    @staticmethod
    def _infer_unit_type_from_billing_interval(billing_interval: Optional[str]) -> str:
        mapping = {
            "per_token": "token",
            "per_character": "character",
            "per_request": "request",
            "per_message": "message",
            "per_execution": "execution",
            "per_operation": "operation",
            "per_image": "image",
            "per_minute": "minute",
            "per_second": "second",
            "monthly": "month",
            "yearly": "year",
            "per_unit": "unit",
        }
        return mapping.get(billing_interval or "", "unit")

    # ====================
    # 订阅管理
    # ====================

    async def get_user_subscriptions(
        self,
        user_id: str,
        status: Optional[SubscriptionStatus] = None
    ) -> List[UserSubscription]:
        """获取用户订阅列表"""
        try:
            return await self.repository.get_user_subscriptions(
                user_id=user_id,
                status=status
            )
        except Exception as e:
            logger.error(f"Error getting user subscriptions for {user_id}: {e}")
            raise

    async def get_subscription(self, subscription_id: str) -> Optional[UserSubscription]:
        """获取订阅详情"""
        try:
            return await self.repository.get_subscription(subscription_id)
        except Exception as e:
            logger.error(f"Error getting subscription {subscription_id}: {e}")
            raise

    async def create_subscription(
        self,
        user_id: str,
        plan_id: str,
        organization_id: Optional[str] = None,
        billing_cycle: BillingCycle = BillingCycle.MONTHLY,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UserSubscription:
        """创建新订阅"""
        try:
            # Validate user via account service (skip if service clients not available)
            if self.account_client:
                try:
                    user_exists = await self.account_client.get_user(user_id)
                    if not user_exists:
                        logger.warning(f"User {user_id} not found, but proceeding with subscription creation")
                except Exception as e:
                    logger.warning(f"User validation error: {e}, proceeding anyway")

            # Validate organization if provided
            if organization_id and self.organization_client:
                try:
                    org_exists = await self.organization_client.get_organization(organization_id)
                    if not org_exists:
                        logger.warning(f"Organization {organization_id} not found, but proceeding")
                except Exception as e:
                    logger.warning(f"Organization validation error: {e}, proceeding anyway")

            # Query the service plan to get its tier
            service_plan = await self.repository.get_service_plan(plan_id)
            if not service_plan:
                raise ValueError(f"Service plan {plan_id} not found")

            subscription = UserSubscription(
                subscription_id=str(uuid.uuid4()),
                user_id=user_id,
                organization_id=organization_id,
                plan_id=plan_id,
                plan_tier=service_plan.get("plan_tier", "basic"),
                status=SubscriptionStatus.ACTIVE,
                current_period_start=datetime.utcnow(),
                current_period_end=self._calculate_period_end(billing_cycle),
                billing_cycle=billing_cycle,
                metadata=metadata or {}
            )

            created_subscription = await self.repository.create_subscription(subscription)

            # Publish subscription.created event via publisher
            await publish_subscription_created(
                event_bus=self.event_bus,
                subscription_id=created_subscription.subscription_id,
                user_id=created_subscription.user_id,
                organization_id=created_subscription.organization_id,
                plan_id=created_subscription.plan_id,
                plan_tier=created_subscription.plan_tier,
                billing_cycle=created_subscription.billing_cycle.value,
                status=created_subscription.status.value,
                current_period_start=created_subscription.current_period_start,
                current_period_end=created_subscription.current_period_end,
                metadata=metadata
            )

            return created_subscription
        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            raise

    def _calculate_period_end(self, billing_cycle: BillingCycle) -> datetime:
        """计算计费周期结束时间"""
        now = datetime.utcnow()
        if billing_cycle == BillingCycle.MONTHLY:
            return now + timedelta(days=30)
        elif billing_cycle == BillingCycle.QUARTERLY:
            return now + timedelta(days=90)
        elif billing_cycle == BillingCycle.YEARLY:
            return now + timedelta(days=365)
        else:
            return now + timedelta(days=30)  # 默认月度

    async def update_subscription_status(
        self,
        subscription_id: str,
        status: SubscriptionStatus
    ) -> bool:
        """更新订阅状态"""
        try:
            # Get the subscription first to publish with full details
            subscription = await self.repository.get_subscription(subscription_id)
            if not subscription:
                logger.warning(f"Subscription {subscription_id} not found")
                return False

            # Store old status before update
            old_status = subscription.status.value

            # Update the subscription status in repository
            success = await self.repository.update_subscription_status(
                subscription_id=subscription_id,
                new_status=status.value
            )

            if not success:
                logger.error(f"Failed to update subscription {subscription_id} status")
                return False

            logger.info(f"Updated subscription {subscription_id} from {old_status} to {status.value}")

            # Publish subscription status change event via publisher
            await publish_subscription_status_changed(
                event_bus=self.event_bus,
                subscription_id=subscription_id,
                user_id=subscription.user_id,
                organization_id=subscription.organization_id,
                plan_id=subscription.plan_id,
                old_status=old_status,
                new_status=status.value
            )

            return True
        except Exception as e:
            logger.error(f"Error updating subscription status: {e}")
            raise

    # ====================
    # 使用量记录
    # ====================

    async def record_product_usage(
        self,
        user_id: str,
        organization_id: Optional[str],
        subscription_id: Optional[str],
        product_id: str,
        usage_amount: Decimal,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        usage_details: Optional[Dict[str, Any]] = None,
        usage_timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """记录产品使用量"""
        try:
            # Validate user via account service (fail-open for testing)
            if self.account_client:
                try:
                    user_valid = await self.account_client.validate_user(user_id)
                    if not user_valid:
                        logger.warning(f"User {user_id} validation failed, but proceeding with usage recording")
                except Exception as e:
                    logger.warning(f"User validation error: {e}, proceeding anyway")

            # Validate organization if provided (fail-open for testing)
            if organization_id and self.organization_client:
                try:
                    org_valid = await self.organization_client.validate_organization(organization_id)
                    if not org_valid:
                        logger.warning(f"Organization {organization_id} validation failed, but proceeding")
                except Exception as e:
                    logger.warning(f"Organization validation error: {e}, proceeding anyway")

            # 验证产品是否存在
            product = await self.repository.get_product(product_id)
            if not product:
                return {
                    "success": False,
                    "message": f"Product {product_id} not found",
                    "usage_record_id": None
                }

            # 验证订阅（如果提供）
            if subscription_id:
                subscription = await self.repository.get_subscription(subscription_id)
                if not subscription:
                    return {
                        "success": False,
                        "message": f"Subscription {subscription_id} not found",
                        "usage_record_id": None
                    }
                if subscription.status != SubscriptionStatus.ACTIVE:
                    return {
                        "success": False,
                        "message": f"Subscription {subscription_id} is not active",
                        "usage_record_id": None
                    }

            # 记录使用量
            usage_record_id = await self.repository.record_product_usage(
                user_id=user_id,
                organization_id=organization_id,
                subscription_id=subscription_id,
                product_id=product_id,
                usage_amount=usage_amount,
                session_id=session_id,
                request_id=request_id,
                usage_details=usage_details,
                usage_timestamp=usage_timestamp
            )

            logger.info(f"Recorded usage for user {user_id}, product {product_id}, amount {usage_amount}")

            # Publish product.usage.recorded event via publisher
            await publish_product_usage_recorded(
                event_bus=self.event_bus,
                usage_record_id=usage_record_id,
                user_id=user_id,
                organization_id=organization_id,
                subscription_id=subscription_id,
                product_id=product_id,
                usage_amount=float(usage_amount),
                session_id=session_id,
                request_id=request_id,
                usage_details=usage_details,
                timestamp=usage_timestamp
            )

            return {
                "success": True,
                "message": "Usage recorded successfully",
                "usage_record_id": usage_record_id,
                "product": product.model_dump(),
                "recorded_amount": float(usage_amount),
                "timestamp": usage_timestamp or datetime.utcnow()
            }

        except Exception as e:
            logger.error(f"Error recording product usage: {e}")
            return {
                "success": False,
                "message": f"Failed to record usage: {str(e)}",
                "usage_record_id": None
            }

    async def get_usage_records(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        subscription_id: Optional[str] = None,
        product_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ProductUsageRecord]:
        """获取使用量记录"""
        try:
            return await self.repository.get_usage_records(
                user_id=user_id,
                organization_id=organization_id,
                subscription_id=subscription_id,
                product_id=product_id,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
                offset=offset
            )
        except Exception as e:
            logger.error(f"Error getting usage records: {e}")
            raise

    # ====================
    # 统计和分析
    # ====================

    async def get_usage_statistics(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        product_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """获取使用量统计"""
        try:
            return await self.repository.get_usage_statistics(
                user_id=user_id,
                organization_id=organization_id,
                product_id=product_id,
                start_date=start_date,
                end_date=end_date
            )
        except Exception as e:
            logger.error(f"Error getting usage statistics: {e}")
            raise

    async def get_service_statistics(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        try:
            # 获取基本统计
            current_time = datetime.utcnow()
            last_24h = current_time - timedelta(hours=24)
            last_7d = current_time - timedelta(days=7)
            last_30d = current_time - timedelta(days=30)

            # 这里可以实现更详细的统计逻辑
            return {
                "service": "product_service",
                "statistics": {
                    "total_products": 0,  # 可以从数据库获取
                    "active_subscriptions": 0,  # 可以从数据库获取
                    "usage_records_24h": 0,  # 可以从数据库获取
                    "usage_records_7d": 0,
                    "usage_records_30d": 0
                },
                "timestamp": current_time
            }
        except Exception as e:
            logger.error(f"Error getting service statistics: {e}")
            raise

    # ====================
    # Admin Operations
    # ====================

    async def admin_create_product(self, data: Dict[str, Any]) -> Optional[Product]:
        """Create a product via admin API"""
        try:
            product = Product(
                product_id=data["product_id"],
                category_id=data.get("category", "ai_models"),
                name=data["product_name"],
                product_code=data.get("product_code"),
                description=data.get("description"),
                product_type=ProductType(data["product_type"]) if isinstance(data["product_type"], str) else data["product_type"],
                base_price=Decimal(str(data.get("base_price", 0))),
                currency=Currency(data.get("currency", "USD")),
                billing_interval=data.get("billing_interval"),
                features=data.get("features", []),
                quota_limits=data.get("quota_limits", {}),
                metadata=data.get("metadata", {}),
                tags=data.get("tags"),
                is_active=data.get("is_active", True),
            )
            return await self.repository.create_product(product)
        except Exception as e:
            logger.error(f"Error in admin_create_product: {e}")
            raise

    async def admin_update_product(self, product_id: str, data: Dict[str, Any]) -> Optional[Product]:
        """Update a product via admin API"""
        try:
            existing = await self.repository.get_product(product_id)
            if not existing:
                return None

            updates = {}
            field_map = {
                "product_name": "product_name",
                "description": "description",
                "category": "category",
                "product_type": "product_type",
                "base_price": "base_price",
                "currency": "currency",
                "billing_interval": "billing_interval",
                "features": "features",
                "quota_limits": "quota_limits",
                "metadata": "metadata",
                "tags": "tags",
                "is_active": "is_active",
            }
            for req_field, db_field in field_map.items():
                if req_field in data and data[req_field] is not None:
                    value = data[req_field]
                    if req_field == "product_type" and isinstance(value, ProductType):
                        value = value.value
                    updates[db_field] = value

            if not updates:
                return existing

            return await self.repository.update_product(product_id, updates)
        except Exception as e:
            logger.error(f"Error in admin_update_product: {e}")
            raise

    async def admin_delete_product(self, product_id: str) -> bool:
        """Soft-delete a product via admin API"""
        try:
            existing = await self.repository.get_product(product_id)
            if not existing:
                return False
            return await self.repository.admin_soft_delete_product(product_id)
        except Exception as e:
            logger.error(f"Error in admin_delete_product: {e}")
            raise

    async def admin_create_pricing(self, product_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a pricing tier via admin API"""
        try:
            product = await self.repository.get_product(product_id)
            if not product:
                return None

            return await self.repository.admin_create_pricing(
                product_id=product_id,
                pricing_id=data["pricing_id"],
                tier_name=data.get("tier_name", "base"),
                min_quantity=data.get("min_quantity", 0),
                max_quantity=data.get("max_quantity"),
                unit_price=data["unit_price"],
                currency=data.get("currency", "USD"),
                metadata=data.get("metadata"),
            )
        except Exception as e:
            logger.error(f"Error in admin_create_pricing: {e}")
            raise

    async def admin_update_pricing(self, pricing_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a pricing tier via admin API"""
        try:
            existing = await self.repository.admin_get_pricing(pricing_id)
            if not existing:
                return None

            updates = {k: v for k, v in data.items() if v is not None}
            if not updates:
                return existing

            return await self.repository.admin_update_pricing(pricing_id, updates)
        except Exception as e:
            logger.error(f"Error in admin_update_pricing: {e}")
            raise

    # ====================
    # Cost Definition Admin
    # ====================

    async def admin_get_cost_definitions(self, is_active=None, provider=None, service_type=None):
        return await self.repository.get_cost_definitions(is_active=is_active, provider=provider, service_type=service_type)

    async def admin_create_cost_definition(self, data):
        effective_from = data.get("effective_from")
        if effective_from and isinstance(effective_from, str):
            effective_from = datetime.fromisoformat(effective_from)
        if effective_from and effective_from < datetime.utcnow():
            raise ValueError("effective_from cannot be in the past")
        return await self.repository.create_cost_definition(data)

    async def admin_update_cost_definition(self, cost_id, data):
        existing = await self.repository.get_cost_definition(cost_id)
        if not existing: return None
        return await self.repository.update_cost_definition(cost_id, data)

    async def admin_rotate_cost_definitions(self, rotations):
        results = []
        for r in rotations:
            cost_id = r["cost_id"]
            eff = r.get("effective_from")
            if isinstance(eff, str): eff = datetime.fromisoformat(eff)
            if eff and eff < datetime.utcnow():
                raise ValueError(f"effective_from for {cost_id} cannot be in the past")
            old = await self.repository.get_cost_definition(cost_id)
            if not old: raise ValueError(f"Cost definition {cost_id} not found")
            await self.repository.expire_cost_definition(cost_id, eff)
            new_data = {
                "cost_id": f"{cost_id}_v{int(datetime.utcnow().timestamp())}",
                "product_id": old.get("product_id"), "service_type": old["service_type"],
                "provider": old.get("provider"), "model_name": old.get("model_name"),
                "operation_type": old.get("operation_type"),
                "cost_per_unit": r.get("new_cost_per_unit", old["cost_per_unit"]),
                "unit_type": old["unit_type"], "unit_size": old.get("unit_size", 1),
                "original_cost_usd": r.get("new_original_cost_usd", old.get("original_cost_usd")),
                "margin_percentage": old.get("margin_percentage", 30.0),
                "effective_from": eff,
                "free_tier_limit": old.get("free_tier_limit", 0),
                "free_tier_period": old.get("free_tier_period", "monthly"),
                "description": old.get("description"),
            }
            new_def = await self.repository.create_cost_definition(new_data)
            results.append({"expired": cost_id, "created": new_def})
        return results

    async def admin_get_cost_history(self, model_name):
        return await self.repository.get_cost_history(model_name)

    # ====================
    # Catalog Alignment
    # ====================

    async def get_catalog_alignment(self):
        return await self.repository.get_catalog_alignment()

    # ====================
    # 业务逻辑辅助方法
    # ====================

    async def check_product_availability(
        self,
        product_id: str,
        user_id: str,
        organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """检查产品可用性"""
        try:
            product = await self.repository.get_product(product_id)
            if not product:
                return {
                    "available": False,
                    "reason": "Product not found"
                }

            if not product.is_active:
                return {
                    "available": False,
                    "reason": "Product is not active"
                }

            # 可以添加更多检查逻辑，比如用户权限、地区限制等
            
            return {
                "available": True,
                "product": product.model_dump()
            }

        except Exception as e:
            logger.error(f"Error checking product availability: {e}")
            return {
                "available": False,
                "reason": f"Error checking availability: {str(e)}"
            }
