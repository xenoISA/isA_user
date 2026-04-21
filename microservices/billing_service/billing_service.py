"""
Billing Service Business Logic

专注于使用量跟踪、费用计算和计费处理的核心业务逻辑
"""

import logging
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import httpx
from core.nats_client import Event

from .protocols import (
    AgentClientProtocol,
    BillingRepositoryProtocol,
    EventBusProtocol,
    ProductClientProtocol,
    WalletClientProtocol,
    SubscriptionClientProtocol,
)
from .models import (
    BillingAccountType,
    BillingCalculationRequest,
    BillingCalculationResponse,
    BillingEvent,
    BillingMethod,
    BillingQuota,
    BillingRecord,
    BillingStats,
    BillingStatus,
    Currency,
    EventType,
    ProcessBillingRequest,
    ProcessBillingResponse,
    QuotaCheckRequest,
    QuotaCheckResponse,
    RecordUsageRequest,
    ServiceType,
    UsageAggregation,
    UsageStatsRequest,
    UsageStatsResponse,
)

logger = logging.getLogger(__name__)


def now_start_of_month() -> datetime:
    """Return the first instant of the current UTC month."""
    now = datetime.utcnow()
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


class BillingService:
    """计费服务核心业务逻辑"""

    def __init__(
        self,
        repository: BillingRepositoryProtocol,
        event_bus: Optional[EventBusProtocol] = None,
        product_client: Optional[ProductClientProtocol] = None,
        wallet_client: Optional[WalletClientProtocol] = None,
        subscription_client: Optional[SubscriptionClientProtocol] = None,
        agent_client: Optional[AgentClientProtocol] = None,
    ):
        """
        Initialize billing service with injected dependencies

        Args:
            repository: Repository for data access
            event_bus: Optional event bus for publishing events
            product_client: Optional client for product service communication
            wallet_client: Optional client for wallet service communication
            subscription_client: Optional client for subscription service communication
            agent_client: Optional client for agent service (used by usage overview)
        """
        self.repository = repository
        self.event_bus = event_bus
        self.product_client = product_client
        self.wallet_client = wallet_client
        self.subscription_client = subscription_client
        self.agent_client = agent_client

        logger.info("✅ BillingService initialized with dependency injection")

    @staticmethod
    def _resolve_billing_scope(
        *,
        user_id: Optional[str],
        organization_id: Optional[str] = None,
        actor_user_id: Optional[str] = None,
        billing_account_type: Optional[BillingAccountType] = None,
        billing_account_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Resolve explicit payer identity while keeping legacy user/org inputs compatible."""
        resolved_actor_user_id = actor_user_id or user_id or billing_account_id or ""
        resolved_type = billing_account_type
        resolved_account_id = billing_account_id

        if resolved_type is None:
            if organization_id:
                resolved_type = BillingAccountType.ORGANIZATION
                resolved_account_id = organization_id
            else:
                resolved_type = BillingAccountType.USER
                resolved_account_id = user_id or resolved_actor_user_id
        elif resolved_account_id is None:
            if resolved_type == BillingAccountType.ORGANIZATION:
                resolved_account_id = organization_id
            else:
                resolved_account_id = user_id or resolved_actor_user_id

        resolved_organization_id = organization_id
        if resolved_type == BillingAccountType.ORGANIZATION:
            resolved_organization_id = resolved_organization_id or resolved_account_id

        return {
            "user_id": user_id or resolved_actor_user_id,
            "actor_user_id": resolved_actor_user_id,
            "organization_id": resolved_organization_id,
            "billing_account_type": resolved_type,
            "billing_account_id": resolved_account_id,
        }

    def _get_service_url(self, service_name: str, fallback_port: int) -> str:
        """Get service URL from environment or use fallback"""
        fallback_url = f"http://localhost:{fallback_port}"
        return fallback_url

    # ====================
    # 使用量记录和计费
    # ====================

    async def record_usage_and_bill(
        self, request: RecordUsageRequest
    ) -> ProcessBillingResponse:
        """记录使用量并立即计费（核心功能）"""
        try:
            scope = self._resolve_billing_scope(
                user_id=request.user_id,
                organization_id=request.organization_id,
                actor_user_id=request.actor_user_id,
                billing_account_type=request.billing_account_type,
                billing_account_id=request.billing_account_id,
            )
            # 1. 首先记录使用量到 Product Service (non-blocking, optional)
            usage_record_id = await self._record_usage_to_product_service(request)
            if not usage_record_id:
                logger.warning(
                    "Product service unavailable, continuing with billing without usage record"
                )
                usage_record_id = (
                    f"local_{request.user_id}_{int(datetime.utcnow().timestamp())}"
                )

            # 2. 计算费用
            calc_request = BillingCalculationRequest(
                user_id=scope["user_id"],
                actor_user_id=scope["actor_user_id"],
                billing_account_type=scope["billing_account_type"],
                billing_account_id=scope["billing_account_id"],
                organization_id=scope["organization_id"],
                agent_id=request.agent_id,
                subscription_id=request.subscription_id,
                product_id=request.product_id,
                usage_amount=request.usage_amount,
                unit_type=request.unit_type,
            )
            calculation = await self.calculate_billing_cost(calc_request)

            if not calculation.success:
                return ProcessBillingResponse(
                    success=False,
                    message=f"Failed to calculate billing cost: {calculation.message}",
                )

            # 3. 检查配额
            quota_check = await self.check_quota(
                QuotaCheckRequest(
                    user_id=request.user_id,
                    actor_user_id=scope["actor_user_id"],
                    billing_account_type=scope["billing_account_type"],
                    billing_account_id=scope["billing_account_id"],
                    organization_id=scope["organization_id"],
                    subscription_id=request.subscription_id,
                    service_type=request.service_type,
                    product_id=request.product_id,
                    requested_amount=request.usage_amount,
                )
            )

            if not quota_check.allowed:
                # 记录配额超出事件
                await self._create_billing_event(
                    EventType.QUOTA_EXCEEDED,
                    "billing_service",
                    user_id=scope["user_id"],
                    actor_user_id=scope["actor_user_id"],
                    billing_account_type=scope["billing_account_type"],
                    billing_account_id=scope["billing_account_id"],
                    organization_id=scope["organization_id"],
                    agent_id=request.agent_id,
                    subscription_id=request.subscription_id,
                    service_type=ServiceType(request.service_type)
                    if request.service_type
                    else None,
                    event_data={
                        "requested_amount": float(request.usage_amount),
                        "quota_limit": float(quota_check.quota_limit)
                        if quota_check.quota_limit
                        else None,
                        "quota_used": float(quota_check.quota_used)
                        if quota_check.quota_used
                        else None,
                    },
                )

                # Publish quota.exceeded event to NATS
                if self.event_bus:
                    try:
                        event = Event(
                            event_type="quota.exceeded",
                            source="billing_service",
                            data={
                                "user_id": scope["user_id"],
                                "actor_user_id": scope["actor_user_id"],
                                "billing_account_type": scope["billing_account_type"],
                                "billing_account_id": scope["billing_account_id"],
                                "organization_id": scope["organization_id"],
                                "agent_id": request.agent_id,
                                "subscription_id": request.subscription_id,
                                "product_id": request.product_id,
                                "requested_amount": float(request.usage_amount),
                                "quota_limit": float(quota_check.quota_limit)
                                if quota_check.quota_limit
                                else None,
                                "quota_used": float(quota_check.quota_used)
                                if quota_check.quota_used
                                else None,
                                "timestamp": datetime.utcnow().isoformat(),
                            },
                        )
                        await self.event_bus.publish_event(event)
                    except Exception as e:
                        logger.error(f"Failed to publish quota.exceeded event: {e}")

                return ProcessBillingResponse(
                    success=False, message=f"Quota exceeded: {quota_check.message}"
                )

            # 4. Free, subscription-included, or zero-cost usage completes immediately
            if (
                calculation.is_free_tier
                or calculation.is_included_in_subscription
                or calculation.total_cost == 0
            ):
                billing_record = await self._create_billing_record(
                    usage_record_id=usage_record_id,
                    calculation=calculation,
                    billing_method=BillingMethod.SUBSCRIPTION_INCLUDED,
                    status=BillingStatus.COMPLETED,
                    service_type=request.service_type,
                    actor_user_id=scope["actor_user_id"],
                    billing_account_type=scope["billing_account_type"],
                    billing_account_id=scope["billing_account_id"],
                    organization_id=scope["organization_id"],
                    agent_id=request.agent_id,
                    subscription_id=request.subscription_id,
                    billing_metadata={
                        "charged_upstream": False,
                        "credit_consumption_handled": False,
                        "usage_details": request.usage_details or {},
                    },
                )

                await self._create_billing_event(
                    EventType.BILLING_PROCESSED,
                    "billing_service",
                    user_id=scope["user_id"],
                    actor_user_id=scope["actor_user_id"],
                    billing_account_type=scope["billing_account_type"],
                    billing_account_id=scope["billing_account_id"],
                    organization_id=scope["organization_id"],
                    agent_id=request.agent_id,
                    subscription_id=request.subscription_id,
                    billing_record_id=billing_record.billing_id,
                    amount=calculation.total_cost,
                    service_type=ServiceType(request.service_type)
                    if request.service_type
                    else None,
                    event_data={"billing_method": "subscription_included"},
                )

                return ProcessBillingResponse(
                    success=True,
                    message="Usage billed successfully (included in subscription)",
                    billing_record_id=billing_record.billing_id,
                    amount_charged=calculation.total_cost,
                    billing_method_used=BillingMethod.SUBSCRIPTION_INCLUDED,
                )

            # 5. A payable usage record needs an actual charge
            process_request = ProcessBillingRequest(
                usage_record_id=usage_record_id,
                billing_method=calculation.suggested_billing_method,
                service_type=request.service_type,
                actor_user_id=scope["actor_user_id"],
                billing_account_type=scope["billing_account_type"],
                billing_account_id=scope["billing_account_id"],
                organization_id=scope["organization_id"],
                agent_id=request.agent_id,
                subscription_id=request.subscription_id,
                billing_metadata={
                    "charged_upstream": False,
                    "credit_consumption_handled": False,
                    "usage_details": request.usage_details or {},
                },
            )

            return await self.process_billing(process_request, calculation)

        except Exception as e:
            logger.error(f"Error in record_usage_and_bill: {e}")
            return ProcessBillingResponse(
                success=False, message=f"Internal error: {str(e)}"
            )

    async def record_usage_with_external_billing(
        self,
        request: RecordUsageRequest,
        *,
        credits_used: Optional[int] = None,
        cost_usd: Optional[Decimal] = None,
        idempotency_key: Optional[str] = None,
        source_event_id: Optional[str] = None,
    ) -> ProcessBillingResponse:
        """Persist usage that was already charged by an upstream service."""
        try:
            scope = self._resolve_billing_scope(
                user_id=request.user_id,
                organization_id=request.organization_id,
                actor_user_id=request.actor_user_id,
                billing_account_type=request.billing_account_type,
                billing_account_id=request.billing_account_id,
            )
            usage_record_id = await self._record_usage_to_product_service(request)
            if not usage_record_id:
                logger.warning(
                    "Product service unavailable, recording external billing without usage record"
                )
                usage_record_id = (
                    f"external_{request.user_id}_{int(datetime.utcnow().timestamp())}"
                )

            calc_request = BillingCalculationRequest(
                user_id=scope["user_id"],
                actor_user_id=scope["actor_user_id"],
                billing_account_type=scope["billing_account_type"],
                billing_account_id=scope["billing_account_id"],
                organization_id=scope["organization_id"],
                agent_id=request.agent_id,
                subscription_id=request.subscription_id,
                product_id=request.product_id,
                usage_amount=request.usage_amount,
                unit_type=request.unit_type,
            )
            calculation = await self.calculate_billing_cost(calc_request)

            if not calculation.success:
                calculation_error = calculation.message
                calculation = self._build_external_billing_fallback_calculation(
                    request=request,
                    user_id=scope["user_id"],
                    actor_user_id=scope["actor_user_id"],
                    billing_account_type=scope["billing_account_type"],
                    billing_account_id=scope["billing_account_id"],
                    organization_id=scope["organization_id"],
                    agent_id=request.agent_id,
                    subscription_id=request.subscription_id,
                    cost_usd=cost_usd,
                    credits_used=credits_used,
                )
                if calculation is None:
                    return ProcessBillingResponse(
                        success=False,
                        message=(
                            "Failed to calculate billing cost for externally billed usage: "
                            f"{calc_request.product_id} ({request.product_id}) -> "
                            f"{calculation_error or 'Product pricing not found'}"
                        ),
                    )

            calculation = self._override_with_upstream_external_cost(
                calculation=calculation,
                cost_usd=cost_usd,
            )

            billing_method = (
                BillingMethod.SUBSCRIPTION_INCLUDED
                if (
                    calculation.is_free_tier
                    or calculation.is_included_in_subscription
                    or calculation.total_cost == 0
                )
                else BillingMethod.CREDIT_CONSUMPTION
            )

            billing_record = await self._create_billing_record(
                usage_record_id=usage_record_id,
                calculation=calculation,
                billing_method=billing_method,
                status=BillingStatus.COMPLETED,
                service_type=request.service_type,
                actor_user_id=scope["actor_user_id"],
                billing_account_type=scope["billing_account_type"],
                billing_account_id=scope["billing_account_id"],
                organization_id=scope["organization_id"],
                agent_id=request.agent_id,
                subscription_id=request.subscription_id,
                billing_metadata={
                    "charged_upstream": True,
                    "credit_consumption_handled": True,
                    "source_event_id": source_event_id,
                    "idempotency_key": idempotency_key,
                    "upstream_credits_used": credits_used,
                    "upstream_cost_usd": (
                        str(cost_usd) if cost_usd is not None else None
                    ),
                    "usage_details": request.usage_details or {},
                },
            )

            await self._create_billing_event(
                EventType.BILLING_PROCESSED,
                "billing_service",
                user_id=scope["user_id"],
                actor_user_id=scope["actor_user_id"],
                billing_account_type=scope["billing_account_type"],
                billing_account_id=scope["billing_account_id"],
                organization_id=scope["organization_id"],
                agent_id=request.agent_id,
                subscription_id=request.subscription_id,
                billing_record_id=billing_record.billing_id,
                amount=calculation.total_cost,
                service_type=request.service_type,
                event_data={
                    "billing_method": billing_method.value,
                    "charged_upstream": True,
                    "credit_consumption_handled": True,
                    "source_event_id": source_event_id,
                    "idempotency_key": idempotency_key,
                    "upstream_credits_used": credits_used,
                    "upstream_cost_usd": (
                        str(cost_usd) if cost_usd is not None else None
                    ),
                },
            )

            return ProcessBillingResponse(
                success=True,
                message="Usage recorded successfully (already billed upstream)",
                billing_record_id=billing_record.billing_id,
                amount_charged=calculation.total_cost,
                billing_method_used=billing_method,
            )
        except Exception as e:
            logger.error("Error recording externally billed usage: %s", e)
            return ProcessBillingResponse(
                success=False,
                message=f"Error recording externally billed usage: {str(e)}",
            )

    def _override_with_upstream_external_cost(
        self,
        *,
        calculation: BillingCalculationResponse,
        cost_usd: Optional[Decimal],
    ) -> BillingCalculationResponse:
        """Use upstream-reported cost when available for externally billed usage."""
        if cost_usd is None:
            return calculation

        upstream_total = Decimal(str(cost_usd))
        usage_amount = calculation.usage_amount or Decimal("0")
        unit_price = (
            upstream_total / usage_amount if usage_amount > 0 else Decimal("0")
        )
        return calculation.model_copy(
            update={
                "unit_price": unit_price,
                "total_cost": upstream_total,
                "currency": Currency.USD,
            }
        )

    def _build_external_billing_fallback_calculation(
        self,
        *,
        request: RecordUsageRequest,
        user_id: str,
        actor_user_id: Optional[str],
        billing_account_type: Optional[BillingAccountType],
        billing_account_id: Optional[str],
        organization_id: Optional[str],
        agent_id: Optional[str],
        subscription_id: Optional[str],
        cost_usd: Optional[Decimal],
        credits_used: Optional[int],
    ) -> Optional[BillingCalculationResponse]:
        """Build a synthetic calculation when upstream already charged successfully."""
        if cost_usd is None and credits_used is None:
            return None

        total_cost = (
            Decimal(str(cost_usd))
            if cost_usd is not None
            else Decimal(str(credits_used or 0))
        )
        currency = Currency.USD if cost_usd is not None else Currency.CREDIT
        usage_amount = request.usage_amount or Decimal("0")
        unit_price = total_cost / usage_amount if usage_amount > 0 else Decimal("0")

        return BillingCalculationResponse(
            success=True,
            message="Using upstream external billing amount",
            user_id=user_id,
            actor_user_id=actor_user_id,
            billing_account_type=billing_account_type,
            billing_account_id=billing_account_id,
            organization_id=organization_id,
            agent_id=agent_id,
            subscription_id=subscription_id,
            product_id=request.product_id,
            usage_amount=request.usage_amount,
            unit_price=unit_price,
            total_cost=total_cost,
            currency=currency,
            suggested_billing_method=BillingMethod.CREDIT_CONSUMPTION,
            available_billing_methods=[BillingMethod.CREDIT_CONSUMPTION],
        )

    async def calculate_billing_cost(
        self, request: BillingCalculationRequest
    ) -> BillingCalculationResponse:
        """计算计费费用"""
        try:
            # Use the compatibility price-calculation endpoint so token-based
            # and tiered products resolve to real per-unit prices instead of
            # legacy catalog base_price fields.
            pricing_info = await self._get_product_pricing(
                request.product_id,
                request.user_id,
                request.subscription_id,
                request.usage_amount,
                request.unit_type,
            )
            if not pricing_info:
                return BillingCalculationResponse(
                    success=False,
                    message="Product pricing not found",
                    user_id=request.user_id,
                    actor_user_id=request.actor_user_id,
                    billing_account_type=request.billing_account_type,
                    billing_account_id=request.billing_account_id,
                    organization_id=request.organization_id,
                    agent_id=request.agent_id,
                    subscription_id=request.subscription_id,
                    product_id=request.product_id,
                    usage_amount=request.usage_amount,
                    unit_price=Decimal("0"),
                    total_cost=Decimal("0"),
                    currency=Currency.CREDIT,
                    suggested_billing_method=BillingMethod.WALLET_DEDUCTION,
                    available_billing_methods=[],
                )

            # Parse nested pricing structure from product service
            # The response has: pricing_model.base_unit_price and effective_pricing.base_unit_price
            pricing_model = pricing_info.get("pricing_model") or {}
            effective_pricing = pricing_info.get("effective_pricing") or {}
            tiers = pricing_info.get("tiers") or []
            tier_unit_price = None
            if isinstance(tiers, list) and tiers:
                first_tier = tiers[0] or {}
                if isinstance(first_tier, dict):
                    tier_unit_price = first_tier.get("price_per_unit")

            # Try to get unit price from various locations (priority order).
            # Use `is not None` so that a legitimate price of 0 (free-tier)
            # is not skipped in favour of a downstream fallback field.
            candidates = [
                pricing_info.get("unit_price"),
                pricing_model.get("base_unit_price"),
                effective_pricing.get("base_unit_price"),
                tier_unit_price,
            ]
            raw_price = next((c for c in candidates if c is not None), None)

            if raw_price is None:
                logger.warning(
                    f"Pricing for product {request.product_id} resolved to None — "
                    f"no price field found in response. "
                    f"pricing_info keys: {list(pricing_info.keys())}, "
                    f"pricing_model keys: {list(pricing_model.keys())}, "
                    f"effective_pricing keys: {list(effective_pricing.keys())}, "
                    f"tiers count: {len(tiers)}"
                )

            unit_price = Decimal(str(raw_price or 0))
            raw_total_cost = pricing_info.get("total_price") or pricing_info.get("total_cost")
            total_cost = (
                Decimal(str(raw_total_cost))
                if raw_total_cost is not None
                else request.usage_amount * unit_price
            )

            # Get currency from pricing_model
            currency_str = (
                pricing_model.get("currency")
                or pricing_info.get("currency")
                or "CREDIT"
            )
            currency = Currency(currency_str)

            # 检查免费层
            is_free_tier = False
            free_tier_remaining = None
            free_tier_limit = float(pricing_model.get("free_tier_limit", 0))
            if free_tier_limit > 0:
                # 这里需要检查用户当前周期的免费层使用量
                # 简化处理，假设还有免费层额度
                free_tier_remaining = Decimal(str(free_tier_limit))
                if request.usage_amount <= free_tier_remaining:
                    is_free_tier = True
                    total_cost = Decimal("0")

            # 检查订阅包含
            is_included_in_subscription = False
            if request.subscription_id:
                subscription_info = await self._get_subscription_info(
                    request.subscription_id
                )
                if subscription_info and self._is_usage_included_in_subscription(
                    request.product_id, request.usage_amount, subscription_info
                ):
                    is_included_in_subscription = True
                    total_cost = Decimal("0")

            # 获取用户余额信息 (subscription_credits, purchased_credits, wallet_balance)
            (
                subscription_credits,
                purchased_credits,
                wallet_balance,
                active_subscription_id,
            ) = await self._get_user_balances(
                request.user_id,
                request.organization_id,
                actor_user_id=request.actor_user_id,
                billing_account_type=request.billing_account_type,
                billing_account_id=request.billing_account_id,
            )

            # Calculate total cost in credits (1 Credit = $0.00001 USD)
            # For CREDIT currency, total_cost is already in credits
            # For USD currency, convert to credits
            if currency == Currency.CREDIT:
                total_cost_credits = int(total_cost)
            else:
                # Convert USD to credits: $1 = 100,000 credits
                total_cost_credits = int(total_cost * Decimal("100000"))

            # 确定建议的计费方式 (priority: subscription -> purchased -> wallet -> payment)
            suggested_method = self._determine_billing_method(
                total_cost_credits,
                subscription_credits,
                purchased_credits,
                wallet_balance,
                is_free_tier,
                is_included_in_subscription,
            )

            # 可用的计费方式
            available_methods = []
            if is_free_tier or is_included_in_subscription:
                available_methods.append(BillingMethod.SUBSCRIPTION_INCLUDED)
            if subscription_credits >= total_cost_credits:
                available_methods.append(BillingMethod.SUBSCRIPTION_CREDIT)
            if purchased_credits >= total_cost_credits:
                available_methods.append(BillingMethod.CREDIT_CONSUMPTION)
            if wallet_balance and wallet_balance >= Decimal(str(total_cost_credits * 0.00001)):
                available_methods.append(BillingMethod.WALLET_DEDUCTION)
            available_methods.append(BillingMethod.PAYMENT_CHARGE)

            # De-duplicate available methods
            available_methods = list(dict.fromkeys(available_methods))

            # For credit_balance in response, use sum of subscription + purchased credits
            credit_balance = Decimal(str(subscription_credits + purchased_credits))

            # Publish billing.calculated event
            if self.event_bus:
                try:
                    event = Event(
                        event_type="billing.calculated",
                        source="billing_service",
                        data={
                            "user_id": request.user_id,
                            "actor_user_id": request.actor_user_id,
                            "billing_account_type": request.billing_account_type,
                            "billing_account_id": request.billing_account_id,
                            "organization_id": request.organization_id,
                            "agent_id": request.agent_id,
                            "product_id": request.product_id,
                            "usage_amount": float(request.usage_amount),
                            "unit_price": float(unit_price),
                            "total_cost": float(total_cost),
                            "currency": currency.value,
                            "is_free_tier": is_free_tier,
                            "is_included_in_subscription": is_included_in_subscription,
                            "suggested_billing_method": suggested_method.value,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    )
                    await self.event_bus.publish_event(event)
                except Exception as e:
                    logger.error(f"Failed to publish billing.calculated event: {e}")

            return BillingCalculationResponse(
                success=True,
                message="Billing cost calculated successfully",
                user_id=request.user_id,
                actor_user_id=request.actor_user_id,
                billing_account_type=request.billing_account_type,
                billing_account_id=request.billing_account_id,
                organization_id=request.organization_id,
                agent_id=request.agent_id,
                subscription_id=request.subscription_id or active_subscription_id,
                product_id=request.product_id,
                usage_amount=request.usage_amount,
                unit_price=unit_price,
                total_cost=total_cost,
                currency=currency,
                is_free_tier=is_free_tier,
                is_included_in_subscription=is_included_in_subscription,
                free_tier_remaining=free_tier_remaining,
                suggested_billing_method=suggested_method,
                available_billing_methods=available_methods,
                wallet_balance=wallet_balance,
                credit_balance=credit_balance,
            )

        except Exception as e:
            logger.error(f"Error calculating billing cost: {e}")
            return BillingCalculationResponse(
                success=False,
                message=f"Error calculating cost: {str(e)}",
                user_id=request.user_id,
                actor_user_id=request.actor_user_id,
                billing_account_type=request.billing_account_type,
                billing_account_id=request.billing_account_id,
                organization_id=request.organization_id,
                agent_id=request.agent_id,
                subscription_id=request.subscription_id or active_subscription_id,
                product_id=request.product_id,
                usage_amount=request.usage_amount,
                unit_price=Decimal("0"),
                total_cost=Decimal("0"),
                currency=Currency.CREDIT,
                suggested_billing_method=BillingMethod.WALLET_DEDUCTION,
                available_billing_methods=[],
            )

    async def process_billing(
        self,
        request: ProcessBillingRequest,
        calculation: Optional[BillingCalculationResponse] = None,
    ) -> ProcessBillingResponse:
        """处理计费（实际扣费）"""
        try:
            # 如果没有提供计算结果，先获取使用记录信息
            if not calculation:
                # 这里需要从 Product Service 获取使用记录信息来计算费用
                # 简化处理，返回错误
                return ProcessBillingResponse(
                    success=False, message="Calculation required for billing processing"
                )

            # 创建计费记录
            billing_record = await self._create_billing_record(
                usage_record_id=request.usage_record_id,
                calculation=calculation,
                billing_method=request.billing_method,
                status=BillingStatus.PROCESSING,
                service_type=request.service_type,
                actor_user_id=request.actor_user_id,
                billing_account_type=request.billing_account_type,
                billing_account_id=request.billing_account_id,
                organization_id=request.organization_id,
                agent_id=request.agent_id,
                subscription_id=request.subscription_id,
                billing_metadata=request.billing_metadata,
            )

            # 根据计费方式处理扣费
            if request.billing_method == BillingMethod.WALLET_DEDUCTION:
                success, transaction_id, error = await self._process_wallet_deduction(
                    calculation.user_id if hasattr(calculation, "user_id") else None,
                    calculation.total_cost,
                    billing_record.billing_id,
                )

                if success:
                    # 更新计费记录状态
                    updated_record = await self.repository.update_billing_record_status(
                        billing_record.billing_id,
                        BillingStatus.COMPLETED,
                        wallet_transaction_id=transaction_id,
                    )

                    await self._create_billing_event(
                        EventType.BILLING_PROCESSED,
                        "billing_service",
                        user_id=billing_record.user_id,
                        actor_user_id=billing_record.actor_user_id,
                        billing_account_type=billing_record.billing_account_type,
                        billing_account_id=billing_record.billing_account_id,
                        organization_id=billing_record.organization_id,
                        agent_id=billing_record.agent_id,
                        subscription_id=billing_record.subscription_id,
                        billing_record_id=billing_record.billing_id,
                        amount=calculation.total_cost,
                        service_type=billing_record.service_type,
                        event_data={
                            "billing_method": "wallet_deduction",
                            "transaction_id": transaction_id,
                        },
                    )

                    # Publish billing.processed event to NATS
                    if self.event_bus:
                        try:
                            event = Event(
                                event_type="billing.processed",
                                source="billing_service",
                                data={
                                    "billing_record_id": billing_record.billing_id,
                                    "user_id": calculation.user_id
                                    if hasattr(calculation, "user_id")
                                    else None,
                                    "actor_user_id": billing_record.actor_user_id,
                                    "billing_account_type": (
                                        billing_record.billing_account_type
                                    ),
                                    "billing_account_id": (
                                        billing_record.billing_account_id
                                    ),
                                    "organization_id": calculation.organization_id
                                    if hasattr(calculation, "organization_id")
                                    else None,
                                    "agent_id": calculation.agent_id
                                    if hasattr(calculation, "agent_id")
                                    else None,
                                    "amount_charged": float(calculation.total_cost),
                                    "currency": calculation.currency.value,
                                    "billing_method": "wallet_deduction",
                                    "transaction_id": transaction_id,
                                    "timestamp": datetime.utcnow().isoformat(),
                                },
                            )
                            await self.event_bus.publish_event(event)
                        except Exception as e:
                            logger.error(
                                f"Failed to publish billing.processed event: {e}"
                            )

                    return ProcessBillingResponse(
                        success=True,
                        message="Billing processed successfully via wallet",
                        billing_record_id=billing_record.billing_id,
                        amount_charged=calculation.total_cost,
                        billing_method_used=BillingMethod.WALLET_DEDUCTION,
                        wallet_transaction_id=transaction_id,
                    )
                else:
                    # 扣费失败
                    await self.repository.update_billing_record_status(
                        billing_record.billing_id,
                        BillingStatus.FAILED,
                        failure_reason=error,
                    )

                    await self._create_billing_event(
                        EventType.BILLING_FAILED,
                        "billing_service",
                        user_id=billing_record.user_id,
                        actor_user_id=billing_record.actor_user_id,
                        billing_account_type=billing_record.billing_account_type,
                        billing_account_id=billing_record.billing_account_id,
                        organization_id=billing_record.organization_id,
                        agent_id=billing_record.agent_id,
                        subscription_id=billing_record.subscription_id,
                        billing_record_id=billing_record.billing_id,
                        service_type=billing_record.service_type,
                        event_data={
                            "error": error,
                            "billing_method": "wallet_deduction",
                        },
                    )

                    return ProcessBillingResponse(
                        success=False,
                        message=f"Wallet deduction failed: {error}",
                        billing_record_id=billing_record.billing_id,
                    )

            elif request.billing_method in (
                BillingMethod.SUBSCRIPTION_INCLUDED,
                BillingMethod.SUBSCRIPTION_CREDIT,
            ):
                credits_to_consume = self._convert_to_credits(
                    calculation.total_cost, calculation.currency
                )
                (
                    success,
                    transaction_id,
                    error,
                    consumed_subscription_id,
                ) = await self._process_subscription_credit_consumption(
                    user_id=billing_record.user_id,
                    actor_user_id=billing_record.actor_user_id,
                    billing_account_type=(
                        billing_record.billing_account_type.value
                        if billing_record.billing_account_type
                        else None
                    ),
                    billing_account_id=billing_record.billing_account_id,
                    organization_id=billing_record.organization_id,
                    credits_amount=credits_to_consume,
                    service_type=billing_record.service_type.value,
                    reference_id=billing_record.billing_id,
                )

                if success:
                    await self.repository.update_billing_record_status(
                        billing_record.billing_id,
                        BillingStatus.COMPLETED,
                        payment_transaction_id=transaction_id,
                        subscription_id=(
                            consumed_subscription_id or billing_record.subscription_id
                        ),
                        billing_method=BillingMethod.SUBSCRIPTION_CREDIT,
                    )
                    return ProcessBillingResponse(
                        success=True,
                        message="Billing processed successfully via subscription credits",
                        billing_record_id=billing_record.billing_id,
                        amount_charged=calculation.total_cost,
                        billing_method_used=BillingMethod.SUBSCRIPTION_CREDIT,
                    )

                await self.repository.update_billing_record_status(
                    billing_record.billing_id,
                    BillingStatus.FAILED,
                    failure_reason=error or "Subscription credit consumption failed",
                )
                return ProcessBillingResponse(
                    success=False,
                    message=f"Subscription credit consumption failed: {error}",
                    billing_record_id=billing_record.billing_id,
                )

            elif request.billing_method == BillingMethod.CREDIT_CONSUMPTION:
                credits_to_consume = self._convert_to_credits(
                    calculation.total_cost, calculation.currency
                )
                success, transaction_id, error = await self._process_purchased_credit_consumption(
                    user_id=billing_record.user_id,
                    credits_amount=credits_to_consume,
                    service_type=billing_record.service_type.value,
                    reference_id=billing_record.billing_id,
                )

                if success:
                    await self.repository.update_billing_record_status(
                        billing_record.billing_id,
                        BillingStatus.COMPLETED,
                        payment_transaction_id=transaction_id,
                    )
                    return ProcessBillingResponse(
                        success=True,
                        message="Billing processed successfully via purchased credits",
                        billing_record_id=billing_record.billing_id,
                        amount_charged=calculation.total_cost,
                        billing_method_used=BillingMethod.CREDIT_CONSUMPTION,
                    )

                await self.repository.update_billing_record_status(
                    billing_record.billing_id,
                    BillingStatus.FAILED,
                    failure_reason=error or "Purchased credit consumption failed",
                )
                return ProcessBillingResponse(
                    success=False,
                    message=f"Purchased credit consumption failed: {error}",
                    billing_record_id=billing_record.billing_id,
                )

            elif request.billing_method == BillingMethod.PAYMENT_CHARGE:
                # 这里需要调用 Payment Service 创建支付意图
                # 简化处理，标记为待处理
                await self.repository.update_billing_record_status(
                    billing_record.billing_id,
                    BillingStatus.PENDING,
                    failure_reason="Payment processing not implemented",
                )

                return ProcessBillingResponse(
                    success=False,
                    message="Payment charge processing not implemented",
                    billing_record_id=billing_record.billing_id,
                )

            else:
                return ProcessBillingResponse(
                    success=False,
                    message=f"Unsupported billing method: {request.billing_method}",
                    billing_record_id=billing_record.billing_id,
                )

        except Exception as e:
            logger.error(f"Error processing billing: {e}")
            return ProcessBillingResponse(
                success=False, message=f"Error processing billing: {str(e)}"
            )

    # ====================
    # 配额管理
    # ====================

    async def check_quota(self, request: QuotaCheckRequest) -> QuotaCheckResponse:
        """检查配额"""
        try:
            # 获取配额信息
            quota = await self.repository.get_billing_quota(
                user_id=request.user_id,
                organization_id=request.organization_id,
                subscription_id=request.subscription_id,
                service_type=request.service_type,
                product_id=request.product_id,
            )

            if not quota:
                # 没有配额限制，允许使用
                return QuotaCheckResponse(allowed=True, message="No quota restrictions")

            # 检查是否超出配额
            remaining = quota.quota_limit - quota.quota_used
            if request.requested_amount <= remaining:
                return QuotaCheckResponse(
                    allowed=True,
                    message="Within quota limits",
                    quota_limit=quota.quota_limit,
                    quota_used=quota.quota_used,
                    quota_remaining=remaining,
                    quota_period=quota.quota_period,
                    next_reset_date=quota.reset_date,
                )
            else:
                return QuotaCheckResponse(
                    allowed=False,
                    message=f"Quota exceeded. Requested: {request.requested_amount}, Remaining: {remaining}",
                    quota_limit=quota.quota_limit,
                    quota_used=quota.quota_used,
                    quota_remaining=remaining,
                    quota_period=quota.quota_period,
                    next_reset_date=quota.reset_date,
                    suggested_actions=[
                        "Upgrade subscription plan",
                        "Wait for quota reset",
                        "Contact support for quota increase",
                    ],
                )

        except Exception as e:
            logger.error(f"Error checking quota: {e}")
            return QuotaCheckResponse(
                allowed=False, message=f"Error checking quota: {str(e)}"
            )

    # ====================
    # Unified billing status (Story #238)
    # ====================

    # In-memory cache: {user_id: (timestamp, result)}
    _billing_status_cache: Dict[str, Tuple[datetime, Dict[str, Any]]] = {}
    _BILLING_STATUS_TTL = timedelta(minutes=5)

    async def get_user_billing_status(self, user_id: str) -> Dict[str, Any]:
        """Return a unified billing status view for isA_Console.

        Aggregates subscription tier, credit balance, and current-period
        usage into a single response object.  Results are cached per-user
        with a 5-minute TTL.

        Falls back to a free-tier stub with a warning field when the
        subscription service is unavailable.
        """
        # Check cache
        now = datetime.utcnow()
        cached = self._billing_status_cache.get(user_id)
        if cached:
            cached_at, cached_result = cached
            if now - cached_at < self._BILLING_STATUS_TTL:
                return cached_result

        result = await self._build_billing_status(user_id)

        # Store in cache
        self._billing_status_cache[user_id] = (now, result)
        return result

    async def _build_billing_status(self, user_id: str) -> Dict[str, Any]:
        """Build the unified billing status dict."""
        # Defaults (free tier fallback)
        subscription_tier = "free"
        credits_remaining = 0
        credits_limit = 0
        next_billing_date = None
        payment_status = "none"
        warning = None

        # Try to fetch subscription info
        if self.subscription_client:
            try:
                sub_info = await self.subscription_client.get_user_subscription(user_id)
                if sub_info:
                    subscription_tier = sub_info.get("tier_code", "free")
                    credits_remaining = sub_info.get("credits_remaining", 0)
                    credits_limit = sub_info.get("credits_limit", 0)
                    next_billing_date = sub_info.get("next_billing_date")
                    payment_status = sub_info.get("payment_status", "none")
                else:
                    warning = "subscription_service_unavailable"
            except Exception as e:
                logger.warning(f"Subscription service unavailable for billing status: {e}")
                warning = "subscription_service_unavailable"
        else:
            warning = "subscription_service_unavailable"

        # Aggregate current-period usage from billing records
        period_start = now_start_of_month()
        try:
            aggregations = await self.repository.get_usage_aggregations(
                user_id=user_id,
                period_start=period_start,
                period_type="monthly",
                limit=1,
            )
            if aggregations:
                agg = aggregations[0]
                usage = {
                    "requests": agg.total_usage_count,
                    "tokens": int(agg.total_usage_amount),
                    "cost": float(agg.total_cost),
                }
            else:
                usage = {"requests": 0, "tokens": 0, "cost": 0.0}
        except Exception as e:
            logger.warning(f"Failed to get usage aggregations for billing status: {e}")
            usage = {"requests": 0, "tokens": 0, "cost": 0.0}

        result: Dict[str, Any] = {
            "user_id": user_id,
            "subscription_tier": subscription_tier,
            "credits_remaining": credits_remaining,
            "credits_limit": credits_limit,
            "next_billing_date": next_billing_date,
            "payment_status": payment_status,
            "current_period_usage": usage,
        }
        if warning:
            result["warning"] = warning
        return result

    # ====================
    # Usage Overview Aggregator (Story #458)
    # ====================

    async def get_usage_overview(
        self,
        user_id: str,
        period_days: int = 30,
        organization_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Cross-service usage overview for the console Usage page.

        Combines billing-side aggregations (requests, tokens, cost) with
        agent_service counts. Each upstream is independent — failure of one
        does not fail the whole response; instead the failed source produces a
        ``warnings`` entry and a null/zero value.
        """
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=period_days)
        warnings: List[str] = []

        # --- billing aggregations: daily series + totals ---
        daily: List[Dict[str, Any]] = []
        totals = {"requests": 0, "tokens": 0, "cost": 0.0}
        try:
            aggregations = await self.repository.get_usage_aggregations(
                user_id=user_id,
                organization_id=organization_id,
                period_start=period_start,
                period_end=period_end,
                period_type="daily",
                limit=period_days,
            )
            # repository returns one row per (period_start, service_type, product_id);
            # collapse to a single row per day for the chart.
            by_day: Dict[str, Dict[str, float]] = {}
            for agg in aggregations or []:
                day_key = agg.period_start.strftime("%Y-%m-%d")
                row = by_day.setdefault(day_key, {"requests": 0, "tokens": 0, "cost": 0.0})
                row["requests"] += int(agg.total_usage_count or 0)
                row["tokens"] += int(agg.total_usage_amount or 0)
                row["cost"] += float(agg.total_cost or 0)

            for day_key in sorted(by_day.keys()):
                row = by_day[day_key]
                daily.append({
                    "date": day_key,
                    "requests": int(row["requests"]),
                    "tokens": int(row["tokens"]),
                    "cost": round(float(row["cost"]), 4),
                })
                totals["requests"] += int(row["requests"])
                totals["tokens"] += int(row["tokens"])
                totals["cost"] += float(row["cost"])
        except Exception as e:
            logger.warning(f"get_usage_overview: billing aggregations failed: {e}")
            warnings.append("billing_aggregations_unavailable")

        totals["cost"] = round(float(totals["cost"]), 4)

        # --- agent count ---
        active_agents: Optional[int] = 0
        if self.agent_client:
            try:
                active_agents = await self.agent_client.count_agents(
                    user_id=user_id,
                    organization_id=organization_id,
                    status="active",
                )
                if active_agents is None:
                    warnings.append("agent_service_unavailable")
                    active_agents = 0
            except Exception as e:
                logger.warning(f"get_usage_overview: agent_client failed: {e}")
                warnings.append("agent_service_unavailable")
                active_agents = 0
        else:
            warnings.append("agent_service_unavailable")

        return {
            "user_id": user_id,
            "organization_id": organization_id,
            "period": {
                "start": period_start.isoformat(),
                "end": period_end.isoformat(),
                "days": period_days,
            },
            "totals": {
                "requests": totals["requests"],
                "tokens": totals["tokens"],
                "cost": totals["cost"],
                "currency": "USD",
            },
            "counts": {
                "active_agents": active_agents,
                "model_deployments": None,
                "prompt_versions": None,
            },
            "daily": daily,
            "warnings": warnings,
        }

    # ====================
    # 统计和报告
    # ====================

    async def get_billing_statistics(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> BillingStats:
        """获取计费统计"""
        try:
            stats_data = await self.repository.get_billing_stats(start_date, end_date)

            return BillingStats(
                total_billing_records=stats_data["total_billing_records"],
                pending_billing_records=stats_data["pending_billing_records"],
                completed_billing_records=stats_data["completed_billing_records"],
                failed_billing_records=stats_data["failed_billing_records"],
                total_revenue=Decimal(str(stats_data["total_revenue"])),
                revenue_by_service={
                    ServiceType(k): Decimal(str(v))
                    for k, v in stats_data["revenue_by_service"].items()
                },
                revenue_by_method={
                    BillingMethod(k): Decimal(str(v))
                    for k, v in stats_data["revenue_by_method"].items()
                },
                active_users=stats_data["active_users"],
                active_organizations=0,  # TODO: 实现
                stats_period_start=stats_data["period_start"],
                stats_period_end=stats_data["period_end"],
            )

        except Exception as e:
            logger.error(f"Error getting billing statistics: {e}")
            raise

    # ====================
    # 私有辅助方法
    # ====================

    async def _record_usage_to_product_service(
        self, request: RecordUsageRequest
    ) -> Optional[str]:
        """向 Product Service 记录使用量"""
        try:
            usage_details = dict(request.usage_details or {})
            if request.agent_id and "agent_id" not in usage_details:
                usage_details["agent_id"] = request.agent_id
            scope = self._resolve_billing_scope(
                user_id=request.user_id,
                organization_id=request.organization_id,
                actor_user_id=request.actor_user_id,
                billing_account_type=request.billing_account_type,
                billing_account_id=request.billing_account_id,
            )
            usage_details.setdefault("actor_user_id", scope["actor_user_id"])
            usage_details.setdefault("billing_account_type", scope["billing_account_type"].value)
            usage_details.setdefault("billing_account_id", scope["billing_account_id"])
            if request.unit_type:
                usage_details.setdefault("unit_type", request.unit_type)
            if request.meter_type:
                usage_details.setdefault("meter_type", request.meter_type)
            if request.operation_type:
                usage_details.setdefault("operation_type", request.operation_type)
            if request.source_service:
                usage_details.setdefault("source_service", request.source_service)
            if request.resource_name:
                usage_details.setdefault("resource_name", request.resource_name)
            if request.billing_surface:
                usage_details.setdefault("billing_surface", request.billing_surface)
            if request.cost_components:
                usage_details.setdefault("cost_components", request.cost_components)

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._get_service_url('product_service', 8215)}/api/v1/product/usage/record",
                    json={
                        "user_id": request.user_id,
                        "organization_id": request.organization_id,
                        "subscription_id": request.subscription_id,
                        "product_id": request.product_id,
                        "usage_amount": float(request.usage_amount),
                        "session_id": request.session_id,
                        "request_id": request.request_id,
                        "usage_details": usage_details,
                        "usage_timestamp": request.usage_timestamp.isoformat()
                        if request.usage_timestamp
                        else None,
                    },
                    timeout=10.0,
                )

                if response.status_code == 200:
                    result = response.json()
                    return result.get("usage_record_id")
                else:
                    logger.error(
                        f"Product service returned {response.status_code}: {response.text}"
                    )
                    return None

        except Exception as e:
            logger.error(f"Error recording usage to product service: {e}")
            return None

    async def _get_product_pricing(
        self,
        product_id: str,
        user_id: str,
        subscription_id: Optional[str],
        quantity: Decimal,
        unit_type: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """Get compatibility pricing for a concrete usage quantity."""
        if self.product_client:
            try:
                calculate_price = getattr(self.product_client, "calculate_price", None)
                if calculate_price is not None:
                    pricing = await calculate_price(
                        product_id=product_id,
                        quantity=quantity,
                        unit_type=unit_type,
                    )
                    if pricing:
                        return pricing
                logger.warning(
                    "ProductServiceClient.calculate_price returned None, falling back to HTTP"
                )
            except Exception as e:
                logger.warning(
                    f"ProductServiceClient.calculate_price failed: {e}, falling back to HTTP"
                )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._get_service_url('product_service', 8215)}/api/v1/pricing/calculate",
                    json={
                        "product_id": product_id,
                        "quantity": str(quantity),
                        "unit_type": unit_type,
                    },
                    timeout=10.0,
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(
                        f"Product service price calculation returned {response.status_code}"
                    )

        except Exception as e:
            logger.error(f"Error calculating product pricing: {e}")

        logger.error(
            f"Product pricing unavailable for {product_id} — "
            "compatibility price calculation failed. Returning None to "
            "prevent incorrect billing records."
        )
        return None

    async def _get_subscription_info(
        self, subscription_id: str
    ) -> Optional[Dict[str, Any]]:
        """从 Product Service 获取订阅信息"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._get_service_url('product_service', 8215)}/api/v1/product/subscriptions/{subscription_id}",
                    timeout=10.0,
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    return None

        except Exception as e:
            logger.error(f"Error getting subscription info: {e}")
            return None

    async def _get_user_balances(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        *,
        actor_user_id: Optional[str] = None,
        billing_account_type: Optional[BillingAccountType] = None,
        billing_account_id: Optional[str] = None,
    ) -> Tuple[Optional[int], Optional[int], Optional[Decimal], Optional[str]]:
        """
        获取用户的各类余额

        Returns:
            Tuple of (subscription_credits, purchased_credits, wallet_balance)
            - subscription_credits: Credits from active subscription (int)
            - purchased_credits: Purchased credits from wallet credit_accounts (int)
            - wallet_balance: Traditional wallet balance (Decimal)
        """
        subscription_credits = 0
        purchased_credits = 0
        wallet_balance = None
        subscription_id = None

        try:
            # 1. 获取订阅信用额度 (highest priority)
            if self.subscription_client:
                try:
                    credit_balance = await self.subscription_client.get_credit_balance(
                        user_id=user_id,
                        organization_id=organization_id,
                        billing_account_type=(
                            billing_account_type.value
                            if isinstance(billing_account_type, BillingAccountType)
                            else billing_account_type
                        ),
                        billing_account_id=billing_account_id,
                        actor_user_id=actor_user_id,
                    )
                    if credit_balance and credit_balance.get("success"):
                        subscription_credits = credit_balance.get("subscription_credits_remaining", 0)
                        subscription_id = credit_balance.get("subscription_id")
                        logger.debug(f"User {user_id} subscription credits: {subscription_credits}")
                except Exception as e:
                    logger.warning(f"Failed to get subscription credits: {e}")

            # 2. 获取钱包余额和购买的信用额度
            try:
                async with httpx.AsyncClient() as client:
                    # 获取钱包余额
                    wallet_response = await client.get(
                        f"{self._get_service_url('wallet_service', 8209)}/api/v1/wallets/user/{user_id}/balance",
                        timeout=5.0,
                    )

                    if wallet_response.status_code == 200:
                        wallet_data = wallet_response.json()
                        wallet_balance = Decimal(
                            str(wallet_data.get("available_balance", 0))
                        )

                    # 获取购买的积分 (credit_accounts)
                    credit_response = await client.get(
                        f"{self._get_service_url('wallet_service', 8209)}/api/v1/credits/balance",
                        params={"user_id": user_id},
                        timeout=5.0,
                    )

                    if credit_response.status_code == 200:
                        credit_data = credit_response.json()
                        if credit_data.get("success"):
                            purchased_credits = credit_data.get("total_credits", 0)
                            logger.debug(f"User {user_id} purchased credits: {purchased_credits}")

            except Exception as e:
                logger.warning(f"Failed to get wallet/credit balance: {e}")

            return subscription_credits, purchased_credits, wallet_balance, subscription_id

        except Exception as e:
            logger.error(f"Error getting user balances: {e}")
            return 0, 0, None, None

    def _is_usage_included_in_subscription(
        self, product_id: str, usage_amount: Decimal, subscription_info: Dict[str, Any]
    ) -> bool:
        """检查使用量是否包含在订阅中"""
        # 简化实现，检查订阅的包含产品
        included_products = subscription_info.get("included_products", [])
        for included in included_products:
            if included.get("product_id") == product_id:
                included_amount = Decimal(str(included.get("included_amount", 0)))
                if usage_amount <= included_amount:
                    return True
        return False

    def _determine_billing_method(
        self,
        total_cost_credits: int,
        subscription_credits: int,
        purchased_credits: int,
        wallet_balance: Optional[Decimal],
        is_free_tier: bool,
        is_included_in_subscription: bool,
    ) -> BillingMethod:
        """
        确定建议的计费方式

        Credit deduction priority:
        1. Subscription credits (included in subscription plan)
        2. Purchased credits (from credit_accounts)
        3. Wallet balance (traditional wallet)
        4. Payment charge (external payment)
        """
        if is_free_tier or is_included_in_subscription:
            return BillingMethod.SUBSCRIPTION_INCLUDED

        # Priority 1: Use subscription credits
        if subscription_credits >= total_cost_credits:
            return BillingMethod.SUBSCRIPTION_CREDIT

        # Priority 2: Use purchased credits
        if purchased_credits >= total_cost_credits:
            return BillingMethod.CREDIT_CONSUMPTION

        # Priority 3: Use wallet balance
        if wallet_balance and wallet_balance >= Decimal(str(total_cost_credits * 0.00001)):
            return BillingMethod.WALLET_DEDUCTION

        # Priority 4: External payment required
        return BillingMethod.PAYMENT_CHARGE

    def _convert_to_credits(self, amount: Decimal, currency: Currency) -> int:
        """
        Convert billing amount to platform credits.

        Rules:
        - CREDIT currency is already credits.
        - USD converts with 1 USD = 100,000 credits.
        - Always charge at least 1 credit for non-zero billable usage.
        """
        if currency == Currency.CREDIT:
            credits = int(amount)
        else:
            credits = int(amount * Decimal("100000"))
        return max(1, credits)

    async def _process_wallet_deduction(
        self, user_id: str, amount: Decimal, reference_id: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """处理钱包扣费"""
        # Try to use WalletServiceClient first
        if self.wallet_client:
            try:
                result = await self.wallet_client.consume(
                    user_id=user_id,
                    wallet_type="balance",
                    amount=float(amount),
                    description=f"Billing charge for {reference_id}",
                    reference_id=reference_id,
                )
                if result.get("success"):
                    return True, result.get("transaction_id"), None
                else:
                    return False, None, result.get("message", "Wallet deduction failed")
            except Exception as e:
                logger.warning(f"WalletServiceClient failed: {e}, falling back to HTTP")

        # Fallback to HTTP if client not available
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._get_service_url('wallet_service', 8209)}/api/v1/wallets/consume",
                    json={
                        "user_id": user_id,
                        "amount": float(amount),
                        "description": f"Billing charge for {reference_id}",
                        "usage_record_id": reference_id,
                    },
                    timeout=10.0,
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        return True, result.get("transaction_id"), None
                    else:
                        return (
                            False,
                            None,
                            result.get("message", "Wallet deduction failed"),
                        )
                else:
                    return (
                        False,
                        None,
                        f"Wallet service returned {response.status_code}",
                    )

        except Exception as e:
            logger.error(f"Error processing wallet deduction: {e}")
            return False, None, str(e)

    async def _process_subscription_credit_consumption(
        self,
        user_id: str,
        actor_user_id: Optional[str],
        billing_account_type: Optional[str],
        billing_account_id: Optional[str],
        organization_id: Optional[str],
        credits_amount: int,
        service_type: str,
        reference_id: str
    ) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """
        Process subscription credit consumption

        Args:
            user_id: User ID
            organization_id: Optional organization ID
            credits_amount: Amount of credits to consume
            service_type: Type of service (e.g., model_inference)
            reference_id: Billing record reference

        Returns:
            Tuple of (success, transaction_id, error_message)
        """
        if not self.subscription_client:
            logger.warning("SubscriptionClient not available")
            return False, None, "Subscription client not available", None

        try:
            result = await self.subscription_client.consume_credits(
                user_id=user_id,
                credits_amount=credits_amount,
                service_type=service_type,
                description=f"Billing charge for {reference_id}",
                usage_record_id=reference_id,
                organization_id=organization_id,
                billing_account_type=billing_account_type,
                billing_account_id=billing_account_id,
                actor_user_id=actor_user_id,
            )

            if result and result.get("success"):
                return (
                    True,
                    result.get("transaction_id"),
                    None,
                    result.get("subscription_id"),
                )
            else:
                error_msg = result.get("message", "Subscription credit consumption failed") if result else "No response"
                return (
                    False,
                    None,
                    error_msg,
                    result.get("subscription_id") if result else None,
                )

        except Exception as e:
            logger.error(f"Error consuming subscription credits: {e}")
            return False, None, str(e), None

    async def _process_purchased_credit_consumption(
        self,
        user_id: str,
        credits_amount: int,
        service_type: str,
        reference_id: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Process purchased credit consumption from wallet credit_accounts

        Args:
            user_id: User ID
            credits_amount: Amount of credits to consume
            service_type: Type of service
            reference_id: Billing record reference

        Returns:
            Tuple of (success, transaction_id, error_message)
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._get_service_url('wallet_service', 8209)}/api/v1/credits/consume",
                    json={
                        "user_id": user_id,
                        "credits_amount": credits_amount,
                        "service_type": service_type,
                        "description": f"Billing charge for {reference_id}",
                        "usage_record_id": reference_id
                    },
                    timeout=10.0,
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        return True, result.get("transaction_id"), None
                    else:
                        return False, None, result.get("message", "Credit consumption failed")
                else:
                    return False, None, f"Wallet service returned {response.status_code}"

        except Exception as e:
            logger.error(f"Error consuming purchased credits: {e}")
            return False, None, str(e)

    async def _create_billing_record(
        self,
        usage_record_id: str,
        calculation: BillingCalculationResponse,
        billing_method: BillingMethod,
        status: BillingStatus,
        service_type: Optional[ServiceType] = None,
        actor_user_id: Optional[str] = None,
        billing_account_type: Optional[BillingAccountType] = None,
        billing_account_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        subscription_id: Optional[str] = None,
        billing_metadata: Optional[Dict[str, Any]] = None,
    ) -> BillingRecord:
        """Create a billing record."""
        resolved_service_type = service_type or ServiceType.OTHER
        base_metadata = {
            "is_free_tier": calculation.is_free_tier,
            "is_included_in_subscription": calculation.is_included_in_subscription,
        }
        if billing_metadata:
            base_metadata.update(billing_metadata)

        billing_record = BillingRecord(
            billing_id=f"bill_{uuid.uuid4().hex[:12]}",
            user_id=getattr(calculation, "user_id", ""),
            actor_user_id=getattr(calculation, "actor_user_id", None) or actor_user_id,
            billing_account_type=(
                getattr(calculation, "billing_account_type", None) or billing_account_type
            ),
            billing_account_id=(
                getattr(calculation, "billing_account_id", None) or billing_account_id
            ),
            organization_id=getattr(calculation, "organization_id", None) or organization_id,
            agent_id=getattr(calculation, "agent_id", None) or agent_id,
            subscription_id=(
                getattr(calculation, "subscription_id", None) or subscription_id
            ),
            usage_record_id=usage_record_id,
            product_id=calculation.product_id,
            service_type=resolved_service_type,
            usage_amount=calculation.usage_amount,
            unit_price=calculation.unit_price,
            total_amount=calculation.total_cost,
            currency=calculation.currency,
            billing_method=billing_method,
            billing_status=status,
            billing_metadata=base_metadata,
        )

        created_record = await self.repository.create_billing_record(billing_record)

        # Publish billing.record.created event to NATS
        if self.event_bus and created_record:
            try:
                event = Event(
                    event_type="record.created",
                    source="billing_service",
                    data={
                        "billing_record_id": created_record.billing_id,
                        "user_id": created_record.user_id,
                        "actor_user_id": created_record.actor_user_id,
                        "billing_account_type": created_record.billing_account_type,
                        "billing_account_id": created_record.billing_account_id,
                        "organization_id": created_record.organization_id,
                        "agent_id": created_record.agent_id,
                        "product_id": created_record.product_id,
                        "total_amount": float(created_record.total_amount),
                        "currency": created_record.currency.value,
                        "billing_method": billing_method.value,
                        "billing_status": status.value,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )
                await self.event_bus.publish_event(event)
            except Exception as e:
                logger.error(f"Failed to publish billing.record.created event: {e}")

        return created_record

    async def _create_billing_event(
        self,
        event_type: EventType,
        event_source: str,
        user_id: Optional[str] = None,
        actor_user_id: Optional[str] = None,
        billing_account_type: Optional[BillingAccountType] = None,
        billing_account_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        subscription_id: Optional[str] = None,
        billing_record_id: Optional[str] = None,
        amount: Optional[Decimal] = None,
        service_type: Optional[ServiceType] = None,
        event_data: Optional[Dict[str, Any]] = None,
    ) -> BillingEvent:
        """创建计费事件"""
        billing_event = BillingEvent(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            event_type=event_type,
            event_source=event_source,
            user_id=user_id,
            actor_user_id=actor_user_id,
            billing_account_type=billing_account_type,
            billing_account_id=billing_account_id,
            organization_id=organization_id,
            agent_id=agent_id,
            subscription_id=subscription_id,
            billing_record_id=billing_record_id,
            amount=amount,
            service_type=service_type,
            currency=Currency.CREDIT if amount else None,
            event_data=event_data or {},
        )

        return await self.repository.create_billing_event(billing_event)
