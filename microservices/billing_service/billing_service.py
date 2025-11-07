"""
Billing Service Business Logic

专注于使用量跟踪、费用计算和计费处理的核心业务逻辑
"""

import logging
import httpx
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

from .billing_repository import BillingRepository
from .models import (
    BillingRecord, BillingEvent, UsageAggregation, BillingQuota,
    RecordUsageRequest, BillingCalculationRequest, BillingCalculationResponse,
    ProcessBillingRequest, ProcessBillingResponse, QuotaCheckRequest, QuotaCheckResponse,
    UsageStatsRequest, UsageStatsResponse, BillingStats,
    BillingStatus, BillingMethod, EventType, ServiceType, Currency
)
from core.nats_client import Event, EventType as NATSEventType, ServiceSource

logger = logging.getLogger(__name__)


class BillingService:
    """计费服务核心业务逻辑"""

    def __init__(self, repository: BillingRepository, event_bus=None):
        self.repository = repository
        self.event_bus = event_bus
        self.consul = None
        self._init_consul()
        self._init_service_clients()

    def _init_service_clients(self):
        """Initialize service clients for inter-service communication"""
        try:
            import sys
            import os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

            from microservices.product_service.client import ProductServiceClient
            from microservices.wallet_service.client import WalletServiceClient

            self.product_client = ProductServiceClient()
            self.wallet_client = WalletServiceClient()
            logger.info("✅ Service clients initialized for billing service")

        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize service clients: {e}")
            logger.warning("Billing service will fall back to HTTP calls")
            self.product_client = None
            self.wallet_client = None

    def _init_consul(self):
        """Service discovery via Consul agent sidecar"""
        logger.info("Service discovery via Consul agent sidecar")

    def _get_service_url(self, service_name: str, fallback_port: int) -> str:
        """Get service URL from environment or use fallback"""
        fallback_url = f"http://localhost:{fallback_port}"
        return fallback_url

    # ====================
    # 使用量记录和计费
    # ====================

    async def record_usage_and_bill(self, request: RecordUsageRequest) -> ProcessBillingResponse:
        """记录使用量并立即计费（核心功能）"""
        try:
            # 1. 首先记录使用量到 Product Service (non-blocking, optional)
            usage_record_id = await self._record_usage_to_product_service(request)
            if not usage_record_id:
                logger.warning("Product service unavailable, continuing with billing without usage record")
                usage_record_id = f"local_{request.user_id}_{int(datetime.utcnow().timestamp())}"

            # Publish usage.recorded event
            if self.event_bus:
                try:
                    event = Event(
                        event_type=NATSEventType.USAGE_RECORDED,
                        source=ServiceSource.BILLING_SERVICE,
                        data={
                            "user_id": request.user_id,
                            "organization_id": request.organization_id,
                            "product_id": request.product_id,
                            "usage_amount": float(request.usage_amount),
                            "service_type": request.service_type,
                            "usage_record_id": usage_record_id,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
                    await self.event_bus.publish_event(event)
                except Exception as e:
                    logger.error(f"Failed to publish usage.recorded event: {e}")

            # 2. 计算费用
            calc_request = BillingCalculationRequest(
                user_id=request.user_id,
                organization_id=request.organization_id,
                subscription_id=request.subscription_id,
                product_id=request.product_id,
                usage_amount=request.usage_amount
            )
            calculation = await self.calculate_billing_cost(calc_request)
            
            if not calculation.success:
                return ProcessBillingResponse(
                    success=False,
                    message=f"Failed to calculate billing cost: {calculation.message}"
                )

            # 3. 检查配额
            quota_check = await self.check_quota(QuotaCheckRequest(
                user_id=request.user_id,
                organization_id=request.organization_id,
                subscription_id=request.subscription_id,
                service_type=request.service_type,
                product_id=request.product_id,
                requested_amount=request.usage_amount
            ))

            if not quota_check.allowed:
                # 记录配额超出事件
                await self._create_billing_event(
                    EventType.QUOTA_EXCEEDED,
                    "billing_service",
                    user_id=request.user_id,
                    organization_id=request.organization_id,
                    subscription_id=request.subscription_id,
                    service_type=ServiceType(request.service_type) if request.service_type else None,
                    event_data={
                        "requested_amount": float(request.usage_amount),
                        "quota_limit": float(quota_check.quota_limit) if quota_check.quota_limit else None,
                        "quota_used": float(quota_check.quota_used) if quota_check.quota_used else None
                    }
                )

                # Publish quota.exceeded event to NATS
                if self.event_bus:
                    try:
                        event = Event(
                            event_type=NATSEventType.QUOTA_EXCEEDED,
                            source=ServiceSource.BILLING_SERVICE,
                            data={
                                "user_id": request.user_id,
                                "organization_id": request.organization_id,
                                "subscription_id": request.subscription_id,
                                "product_id": request.product_id,
                                "requested_amount": float(request.usage_amount),
                                "quota_limit": float(quota_check.quota_limit) if quota_check.quota_limit else None,
                                "quota_used": float(quota_check.quota_used) if quota_check.quota_used else None,
                                "timestamp": datetime.utcnow().isoformat()
                            }
                        )
                        await self.event_bus.publish_event(event)
                    except Exception as e:
                        logger.error(f"Failed to publish quota.exceeded event: {e}")

                return ProcessBillingResponse(
                    success=False,
                    message=f"Quota exceeded: {quota_check.message}"
                )

            # 4. 如果是免费层、订阅包含或0成本，直接标记为完成
            if calculation.is_free_tier or calculation.is_included_in_subscription or calculation.total_cost == 0:
                billing_record = await self._create_billing_record(
                    usage_record_id=usage_record_id,
                    calculation=calculation,
                    billing_method=BillingMethod.SUBSCRIPTION_INCLUDED,
                    status=BillingStatus.COMPLETED
                )
                
                await self._create_billing_event(
                    EventType.BILLING_PROCESSED,
                    "billing_service",
                    user_id=request.user_id,
                    organization_id=request.organization_id,
                    subscription_id=request.subscription_id,
                    billing_record_id=billing_record.billing_id,
                    amount=calculation.total_cost,
                    service_type=ServiceType(request.service_type) if request.service_type else None,
                    event_data={"billing_method": "subscription_included"}
                )

                return ProcessBillingResponse(
                    success=True,
                    message="Usage billed successfully (included in subscription)",
                    billing_record_id=billing_record.billing_id,
                    amount_charged=calculation.total_cost,
                    billing_method_used=BillingMethod.SUBSCRIPTION_INCLUDED
                )

            # 5. 需要实际扣费，处理计费
            process_request = ProcessBillingRequest(
                usage_record_id=usage_record_id,
                billing_method=calculation.suggested_billing_method
            )
            
            return await self.process_billing(process_request, calculation)

        except Exception as e:
            logger.error(f"Error in record_usage_and_bill: {e}")
            return ProcessBillingResponse(
                success=False,
                message=f"Internal error: {str(e)}"
            )

    async def calculate_billing_cost(self, request: BillingCalculationRequest) -> BillingCalculationResponse:
        """计算计费费用"""
        try:
            # 调用 Product Service 获取定价信息
            pricing_info = await self._get_product_pricing(request.product_id, request.user_id, request.subscription_id)
            if not pricing_info:
                return BillingCalculationResponse(
                    success=False,
                    message="Product pricing not found",
                    product_id=request.product_id,
                    usage_amount=request.usage_amount,
                    unit_price=Decimal("0"),
                    total_cost=Decimal("0"),
                    currency=Currency.CREDIT,
                    suggested_billing_method=BillingMethod.WALLET_DEDUCTION,
                    available_billing_methods=[]
                )

            # Parse nested pricing structure from product service
            # The response has: pricing_model.base_unit_price and effective_pricing.base_unit_price
            pricing_model = pricing_info.get("pricing_model", {})
            effective_pricing = pricing_info.get("effective_pricing", {})

            # Try to get unit price from various locations
            unit_price = Decimal(str(
                pricing_info.get("unit_price") or
                effective_pricing.get("base_unit_price") or
                pricing_model.get("base_unit_price") or
                0
            ))

            total_cost = request.usage_amount * unit_price

            # Get currency from pricing_model
            currency_str = pricing_model.get("currency") or pricing_info.get("currency") or "CREDIT"
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
                subscription_info = await self._get_subscription_info(request.subscription_id)
                if subscription_info and self._is_usage_included_in_subscription(
                    request.product_id, request.usage_amount, subscription_info
                ):
                    is_included_in_subscription = True
                    total_cost = Decimal("0")

            # 获取用户余额信息
            wallet_balance, credit_balance = await self._get_user_balances(request.user_id)

            # 确定建议的计费方式
            suggested_method = self._determine_billing_method(
                total_cost, wallet_balance, credit_balance, is_free_tier, is_included_in_subscription
            )

            # 可用的计费方式
            available_methods = []
            if is_free_tier or is_included_in_subscription:
                available_methods.append(BillingMethod.SUBSCRIPTION_INCLUDED)
            if wallet_balance and wallet_balance >= total_cost:
                available_methods.append(BillingMethod.WALLET_DEDUCTION)
            if credit_balance and credit_balance >= total_cost:
                available_methods.append(BillingMethod.CREDIT_CONSUMPTION)
            available_methods.append(BillingMethod.PAYMENT_CHARGE)

            # Publish billing.calculated event
            if self.event_bus:
                try:
                    event = Event(
                        event_type=NATSEventType.BILLING_CALCULATED,
                        source=ServiceSource.BILLING_SERVICE,
                        data={
                            "user_id": request.user_id,
                            "organization_id": request.organization_id,
                            "product_id": request.product_id,
                            "usage_amount": float(request.usage_amount),
                            "unit_price": float(unit_price),
                            "total_cost": float(total_cost),
                            "currency": currency.value,
                            "is_free_tier": is_free_tier,
                            "is_included_in_subscription": is_included_in_subscription,
                            "suggested_billing_method": suggested_method.value,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
                    await self.event_bus.publish_event(event)
                except Exception as e:
                    logger.error(f"Failed to publish billing.calculated event: {e}")

            return BillingCalculationResponse(
                success=True,
                message="Billing cost calculated successfully",
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
                credit_balance=credit_balance
            )

        except Exception as e:
            logger.error(f"Error calculating billing cost: {e}")
            return BillingCalculationResponse(
                success=False,
                message=f"Error calculating cost: {str(e)}",
                product_id=request.product_id,
                usage_amount=request.usage_amount,
                unit_price=Decimal("0"),
                total_cost=Decimal("0"),
                currency=Currency.CREDIT,
                suggested_billing_method=BillingMethod.WALLET_DEDUCTION,
                available_billing_methods=[]
            )

    async def process_billing(
        self, 
        request: ProcessBillingRequest, 
        calculation: Optional[BillingCalculationResponse] = None
    ) -> ProcessBillingResponse:
        """处理计费（实际扣费）"""
        try:
            # 如果没有提供计算结果，先获取使用记录信息
            if not calculation:
                # 这里需要从 Product Service 获取使用记录信息来计算费用
                # 简化处理，返回错误
                return ProcessBillingResponse(
                    success=False,
                    message="Calculation required for billing processing"
                )

            # 创建计费记录
            billing_record = await self._create_billing_record(
                usage_record_id=request.usage_record_id,
                calculation=calculation,
                billing_method=request.billing_method,
                status=BillingStatus.PROCESSING
            )

            # 根据计费方式处理扣费
            if request.billing_method == BillingMethod.WALLET_DEDUCTION:
                success, transaction_id, error = await self._process_wallet_deduction(
                    calculation.user_id if hasattr(calculation, 'user_id') else None,
                    calculation.total_cost,
                    billing_record.billing_id
                )
                
                if success:
                    # 更新计费记录状态
                    updated_record = await self.repository.update_billing_record_status(
                        billing_record.billing_id,
                        BillingStatus.COMPLETED,
                        wallet_transaction_id=transaction_id
                    )
                    
                    await self._create_billing_event(
                        EventType.BILLING_PROCESSED,
                        "billing_service",
                        user_id=billing_record.user_id,
                        organization_id=billing_record.organization_id,
                        billing_record_id=billing_record.billing_id,
                        amount=calculation.total_cost,
                        service_type=billing_record.service_type,
                        event_data={"billing_method": "wallet_deduction", "transaction_id": transaction_id}
                    )

                    # Publish billing.processed event to NATS
                    if self.event_bus:
                        try:
                            event = Event(
                                event_type=NATSEventType.BILLING_PROCESSED,
                                source=ServiceSource.BILLING_SERVICE,
                                data={
                                    "billing_record_id": billing_record.billing_id,
                                    "user_id": calculation.user_id if hasattr(calculation, 'user_id') else None,
                                    "organization_id": calculation.organization_id if hasattr(calculation, 'organization_id') else None,
                                    "amount_charged": float(calculation.total_cost),
                                    "currency": calculation.currency.value,
                                    "billing_method": "wallet_deduction",
                                    "transaction_id": transaction_id,
                                    "timestamp": datetime.utcnow().isoformat()
                                }
                            )
                            await self.event_bus.publish_event(event)
                        except Exception as e:
                            logger.error(f"Failed to publish billing.processed event: {e}")

                    return ProcessBillingResponse(
                        success=True,
                        message="Billing processed successfully via wallet",
                        billing_record_id=billing_record.billing_id,
                        amount_charged=calculation.total_cost,
                        billing_method_used=BillingMethod.WALLET_DEDUCTION,
                        wallet_transaction_id=transaction_id
                    )
                else:
                    # 扣费失败
                    await self.repository.update_billing_record_status(
                        billing_record.billing_id,
                        BillingStatus.FAILED,
                        failure_reason=error
                    )
                    
                    await self._create_billing_event(
                        EventType.BILLING_FAILED,
                        "billing_service",
                        user_id=billing_record.user_id,
                        organization_id=billing_record.organization_id,
                        billing_record_id=billing_record.billing_id,
                        service_type=billing_record.service_type,
                        event_data={"error": error, "billing_method": "wallet_deduction"}
                    )

                    return ProcessBillingResponse(
                        success=False,
                        message=f"Wallet deduction failed: {error}",
                        billing_record_id=billing_record.billing_id
                    )

            elif request.billing_method == BillingMethod.PAYMENT_CHARGE:
                # 这里需要调用 Payment Service 创建支付意图
                # 简化处理，标记为待处理
                await self.repository.update_billing_record_status(
                    billing_record.billing_id,
                    BillingStatus.PENDING,
                    failure_reason="Payment processing not implemented"
                )
                
                return ProcessBillingResponse(
                    success=False,
                    message="Payment charge processing not implemented",
                    billing_record_id=billing_record.billing_id
                )

            else:
                return ProcessBillingResponse(
                    success=False,
                    message=f"Unsupported billing method: {request.billing_method}",
                    billing_record_id=billing_record.billing_id
                )

        except Exception as e:
            logger.error(f"Error processing billing: {e}")
            return ProcessBillingResponse(
                success=False,
                message=f"Error processing billing: {str(e)}"
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
                product_id=request.product_id
            )

            if not quota:
                # 没有配额限制，允许使用
                return QuotaCheckResponse(
                    allowed=True,
                    message="No quota restrictions"
                )

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
                    next_reset_date=quota.reset_date
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
                        "Contact support for quota increase"
                    ]
                )

        except Exception as e:
            logger.error(f"Error checking quota: {e}")
            return QuotaCheckResponse(
                allowed=False,
                message=f"Error checking quota: {str(e)}"
            )

    # ====================
    # 统计和报告
    # ====================

    async def get_billing_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
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
                    ServiceType(k): Decimal(str(v)) for k, v in stats_data["revenue_by_service"].items()
                },
                revenue_by_method={
                    BillingMethod(k): Decimal(str(v)) for k, v in stats_data["revenue_by_method"].items()
                },
                active_users=stats_data["active_users"],
                active_organizations=0,  # TODO: 实现
                stats_period_start=stats_data["period_start"],
                stats_period_end=stats_data["period_end"]
            )

        except Exception as e:
            logger.error(f"Error getting billing statistics: {e}")
            raise

    # ====================
    # 私有辅助方法
    # ====================

    async def _record_usage_to_product_service(self, request: RecordUsageRequest) -> Optional[str]:
        """向 Product Service 记录使用量"""
        try:
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
                        "usage_details": request.usage_details,
                        "usage_timestamp": request.usage_timestamp.isoformat() if request.usage_timestamp else None
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("usage_record_id")
                else:
                    logger.error(f"Product service returned {response.status_code}: {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error recording usage to product service: {e}")
            return None

    async def _get_product_pricing(self, product_id: str, user_id: str, subscription_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """从 Product Service 获取产品定价"""
        # Try to use ProductServiceClient first
        if self.product_client:
            try:
                pricing = await self.product_client.get_product_pricing(
                    product_id=product_id,
                    user_id=user_id,
                    subscription_id=subscription_id
                )
                return pricing
            except Exception as e:
                logger.warning(f"ProductServiceClient failed: {e}, falling back to HTTP")

        # Fallback to HTTP if client not available
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._get_service_url('product_service', 8215)}/api/v1/product/products/{product_id}/pricing",
                    params={
                        "user_id": user_id,
                        "subscription_id": subscription_id
                    },
                    timeout=10.0
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Product service pricing returned {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"Error getting product pricing: {e}")
            return None

    async def _get_subscription_info(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """从 Product Service 获取订阅信息"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._get_service_url('product_service', 8215)}/api/v1/product/subscriptions/{subscription_id}",
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting subscription info: {e}")
            return None

    async def _get_user_balances(self, user_id: str) -> Tuple[Optional[Decimal], Optional[Decimal]]:
        """获取用户钱包和积分余额"""
        try:
            async with httpx.AsyncClient() as client:
                # 获取钱包余额
                wallet_response = await client.get(
                    f"{self._get_service_url('wallet_service', 8209)}/api/v1/wallets/user/{user_id}/balance",
                    timeout=5.0
                )
                
                wallet_balance = None
                if wallet_response.status_code == 200:
                    wallet_data = wallet_response.json()
                    wallet_balance = Decimal(str(wallet_data.get("available_balance", 0)))

                # 积分余额可以从用户表或其他地方获取
                # 这里简化处理，假设积分就是钱包余额
                credit_balance = wallet_balance

                return wallet_balance, credit_balance
                
        except Exception as e:
            logger.error(f"Error getting user balances: {e}")
            return None, None

    def _is_usage_included_in_subscription(
        self, 
        product_id: str, 
        usage_amount: Decimal, 
        subscription_info: Dict[str, Any]
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
        total_cost: Decimal,
        wallet_balance: Optional[Decimal],
        credit_balance: Optional[Decimal],
        is_free_tier: bool,
        is_included_in_subscription: bool
    ) -> BillingMethod:
        """确定建议的计费方式"""
        if is_free_tier or is_included_in_subscription:
            return BillingMethod.SUBSCRIPTION_INCLUDED
        
        if wallet_balance and wallet_balance >= total_cost:
            return BillingMethod.WALLET_DEDUCTION
        
        if credit_balance and credit_balance >= total_cost:
            return BillingMethod.CREDIT_CONSUMPTION
        
        return BillingMethod.PAYMENT_CHARGE

    async def _process_wallet_deduction(
        self,
        user_id: str,
        amount: Decimal,
        reference_id: str
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
                    reference_id=reference_id
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
                        "usage_record_id": reference_id
                    },
                    timeout=10.0
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        return True, result.get("transaction_id"), None
                    else:
                        return False, None, result.get("message", "Wallet deduction failed")
                else:
                    return False, None, f"Wallet service returned {response.status_code}"

        except Exception as e:
            logger.error(f"Error processing wallet deduction: {e}")
            return False, None, str(e)

    async def _create_billing_record(
        self,
        usage_record_id: str,
        calculation: BillingCalculationResponse,
        billing_method: BillingMethod,
        status: BillingStatus
    ) -> BillingRecord:
        """创建计费记录"""
        billing_record = BillingRecord(
            billing_id=f"bill_{uuid.uuid4().hex[:12]}",
            user_id=getattr(calculation, 'user_id', ''),
            organization_id=getattr(calculation, 'organization_id', None),
            subscription_id=getattr(calculation, 'subscription_id', None),
            usage_record_id=usage_record_id,
            product_id=calculation.product_id,
            service_type=ServiceType.OTHER,  # 需要从 Product Service 获取
            usage_amount=calculation.usage_amount,
            unit_price=calculation.unit_price,
            total_amount=calculation.total_cost,
            currency=calculation.currency,
            billing_method=billing_method,
            billing_status=status,
            billing_metadata={
                "is_free_tier": calculation.is_free_tier,
                "is_included_in_subscription": calculation.is_included_in_subscription
            }
        )

        created_record = await self.repository.create_billing_record(billing_record)

        # Publish billing.record.created event to NATS
        if self.event_bus and created_record:
            try:
                event = Event(
                    event_type=NATSEventType.BILLING_RECORD_CREATED,
                    source=ServiceSource.BILLING_SERVICE,
                    data={
                        "billing_record_id": created_record.billing_id,
                        "user_id": created_record.user_id,
                        "organization_id": created_record.organization_id,
                        "product_id": created_record.product_id,
                        "total_amount": float(created_record.total_amount),
                        "currency": created_record.currency.value,
                        "billing_method": billing_method.value,
                        "billing_status": status.value,
                        "timestamp": datetime.utcnow().isoformat()
                    }
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
        organization_id: Optional[str] = None,
        subscription_id: Optional[str] = None,
        billing_record_id: Optional[str] = None,
        amount: Optional[Decimal] = None,
        service_type: Optional[ServiceType] = None,
        event_data: Optional[Dict[str, Any]] = None
    ) -> BillingEvent:
        """创建计费事件"""
        billing_event = BillingEvent(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            event_type=event_type,
            event_source=event_source,
            user_id=user_id,
            organization_id=organization_id,
            subscription_id=subscription_id,
            billing_record_id=billing_record_id,
            amount=amount,
            service_type=service_type,
            currency=Currency.CREDIT if amount else None,
            event_data=event_data or {}
        )

        return await self.repository.create_billing_event(billing_event)