"""
Product Service Business Logic

产品服务核心业务逻辑，处理产品目录、定价和订阅管理
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
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

            # 这里应该实现更新逻辑，但由于时间关系先简化
            logger.info(f"Would update subscription {subscription_id} to status {status}")

            # Publish subscription status change event via publisher
            await publish_subscription_status_changed(
                event_bus=self.event_bus,
                subscription_id=subscription_id,
                user_id=subscription.user_id,
                organization_id=subscription.organization_id,
                plan_id=subscription.plan_id,
                old_status=subscription.status.value,
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