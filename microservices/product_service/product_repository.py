"""
Product Repository

数据访问层 - PostgreSQL + gRPC (Async)
"""

import logging
import os
import sys
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from decimal import Decimal
import json
import uuid

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common import AsyncPostgresClient
from core.config_manager import ConfigManager
from .models import (
    Product,
    PricingModel,
    ProductType,
    ProductKind,
    FulfillmentType,
    InventoryPolicy,
    TaxCategory,
    Currency,
    ProductCategory,
)

logger = logging.getLogger(__name__)


class ProductRepository:
    """产品数据访问仓库 - PostgreSQL (Async)"""

    def __init__(self, config: Optional[ConfigManager] = None):
        """
        Initialize product repository with service discovery.

        Args:
            config: ConfigManager instance for service discovery
        """
        # Use config_manager for service discovery
        if config is None:
            config = ConfigManager("product_service")

        # Discover PostgreSQL service
        # Priority: Environment variables → Consul → localhost fallback
        postgres_host, postgres_port = config.discover_service(
            service_name='postgres_service',
            default_host='localhost',
            default_port=5432,
            env_host_key='POSTGRES_HOST',
            env_port_key='POSTGRES_PORT'
        )

        logger.info(f"Connecting to PostgreSQL at {postgres_host}:{postgres_port}")
        self.db = AsyncPostgresClient(
            host=postgres_host,
            port=postgres_port,
            user_id="product_service"
        )
        self.schema = "product"
        self.products_table = "products"
        self.pricing_table = "product_pricing"
        # In-memory storage for subscriptions (until we have a subscriptions table)
        self._subscriptions_cache = {}

    async def initialize(self):
        """Initialize repository (placeholder for consistency with other services)"""
        logger.info("Product repository initialized")

    async def close(self):
        """Close repository connections (placeholder for consistency with other services)"""
        logger.info("Product repository connections closed")

    async def create_product(self, product: Product) -> Optional[Product]:
        """创建产品"""
        try:
            query = f'''
                INSERT INTO {self.schema}.{self.products_table} (
                    product_id, product_name, product_code, description, category,
                    product_type, base_price, currency, billing_interval,
                    product_kind, fulfillment_type, inventory_policy, requires_shipping,
                    tax_category, default_sku_id,
                    features, quota_limits, is_active, is_featured, display_order,
                    metadata, tags, created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9,
                    $10, $11, $12, $13, $14, $15,
                    $16, $17, $18, $19, $20, $21,
                    $22, $23, $24, $25
                )
                RETURNING *
            '''

            now = datetime.now(timezone.utc)
            product_code = product.product_code or f"code_{product.product_id}"
            params = [
                product.product_id, product.name, product_code,
                product.description, product.category_id, product.product_type.value,
                float(product.base_price), product.currency.value, product.billing_interval,
                product.product_kind.value, product.fulfillment_type.value,
                product.inventory_policy.value, product.requires_shipping,
                product.tax_category.value, product.default_sku_id,
                json.dumps(product.features) if product.features else "[]",
                json.dumps(product.quota_limits) if product.quota_limits else "{}",
                product.is_active, product.is_featured, product.display_order,
                json.dumps(product.metadata) if product.metadata else "{}",
                product.tags, now, now
            ]

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                return self._row_to_product(results[0])
            return None

        except Exception as e:
            logger.error(f"Error creating product: {e}", exc_info=True)
            return None

    async def get_product(self, product_id: str) -> Optional[Product]:
        """获取产品详情"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.products_table}
                WHERE product_id = $1
            '''

            async with self.db:
                result = await self.db.query_row(query, params=[product_id])

            if result:
                return self._row_to_product(result)
            return None

        except Exception as e:
            logger.error(f"Error getting product: {e}")
            return None

    async def get_products(
        self,
        category: Optional[str] = None,
        product_type: Optional[ProductType] = None,
        is_active: Optional[bool] = True,
        limit: int = 100,
        offset: int = 0
    ) -> List[Product]:
        """获取产品列表"""
        try:
            conditions = []
            params = []
            param_count = 0

            if category:
                param_count += 1
                conditions.append(f"category = ${param_count}")
                params.append(category)

            if product_type:
                param_count += 1
                conditions.append(f"product_type = ${param_count}")
                params.append(product_type.value)

            if is_active is not None:
                param_count += 1
                conditions.append(f"is_active = ${param_count}")
                params.append(is_active)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = f'''
                SELECT * FROM {self.schema}.{self.products_table}
                {where_clause}
                ORDER BY display_order ASC, created_at DESC
                LIMIT ${param_count + 1} OFFSET ${param_count + 2}
            '''

            params.extend([limit, offset])

            async with self.db:
                results = await self.db.query(query, params=params)

            return [self._row_to_product(row) for row in results] if results else []

        except Exception as e:
            logger.error(f"Error getting products: {e}")
            return []

    async def update_product(self, product_id: str, updates: Dict[str, Any]) -> Optional[Product]:
        """更新产品"""
        try:
            set_clauses = []
            params = []
            param_count = 0

            for key, value in updates.items():
                if key in ["features", "quota_limits", "metadata"]:
                    value = json.dumps(value)
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")
                params.append(value)

            param_count += 1
            set_clauses.append(f"updated_at = ${param_count}")
            params.append(datetime.now(timezone.utc))

            param_count += 1
            params.append(product_id)

            query = f'''
                UPDATE {self.schema}.{self.products_table}
                SET {", ".join(set_clauses)}
                WHERE product_id = ${param_count}
                RETURNING *
            '''

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                return self._row_to_product(results[0])
            return None

        except Exception as e:
            logger.error(f"Error updating product: {e}")
            return None

    async def delete_product(self, product_id: str) -> bool:
        """删除产品"""
        try:
            query = f'''
                DELETE FROM {self.schema}.{self.products_table}
                WHERE product_id = $1
            '''

            async with self.db:
                count = await self.db.execute(query, params=[product_id])

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error deleting product: {e}")
            return False

    def _row_to_product(self, row: Dict[str, Any]) -> Product:
        """Convert database row to Product model"""
        return Product(
            id=int(row.get("id")) if row.get("id") else None,
            product_id=row.get("product_id"),
            category_id=row.get("category", ""),  # Map category to category_id
            name=row.get("product_name", ""),      # Map product_name to name
            description=row.get("description"),
            product_type=ProductType(row.get("product_type")),
            provider=row.get("provider"),
            product_kind=ProductKind(row.get("product_kind") or ProductKind.DIGITAL.value),
            fulfillment_type=FulfillmentType(row.get("fulfillment_type") or FulfillmentType.DIGITAL.value),
            inventory_policy=InventoryPolicy(row.get("inventory_policy") or InventoryPolicy.INFINITE.value),
            requires_shipping=bool(row.get("requires_shipping", False)),
            tax_category=TaxCategory(row.get("tax_category") or TaxCategory.DIGITAL_GOODS.value),
            default_sku_id=row.get("default_sku_id"),
            product_code=row.get("product_code"),
            base_price=Decimal(str(row.get("base_price", 0.0))),
            currency=Currency(row.get("currency", "USD")),
            billing_interval=row.get("billing_interval"),
            features=row.get("features") or [],
            quota_limits=row.get("quota_limits") or {},
            is_featured=bool(row.get("is_featured", False)),
            display_order=int(row.get("display_order", 0) or 0),
            tags=row.get("tags"),
            specifications=row.get("specifications", {}),
            is_active=row.get("is_active", True),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at")
        )

    # ==================== Category Operations ====================

    async def get_categories(self) -> List[ProductCategory]:
        """获取所有产品类别"""
        try:
            query = f'''
                SELECT DISTINCT category
                FROM {self.schema}.{self.products_table}
                WHERE is_active = true
                ORDER BY category
            '''

            async with self.db:
                results = await self.db.query(query, params=[])

            if results:
                categories = []
                for idx, row in enumerate(results):
                    category_name = row.get("category")
                    categories.append(ProductCategory(
                        category_id=category_name,
                        name=category_name.replace("_", " ").title(),
                        description=f"{category_name.replace('_', ' ').title()} products and services",
                        display_order=idx,
                        is_active=True,
                        created_at=datetime.now(timezone.utc)
                    ))
                return categories
            return []

        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            return []

    # ==================== Pricing Operations ====================

    async def get_product_pricing(
        self,
        product_id: str,
        user_id: Optional[str] = None,
        subscription_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """获取产品定价信息"""
        try:
            # Query product with pricing info from database
            query = f'''
                SELECT
                    product_id,
                    product_name as name,
                    product_type,
                    base_price,
                    currency,
                    billing_interval,
                    features,
                    quota_limits
                FROM {self.schema}.{self.products_table}
                WHERE product_id = $1 AND is_active = true
            '''

            async with self.db:
                result = await self.db.query_row(query, params=[product_id])

            if not result:
                return None

            base_price = float(result.get("base_price", 0.0))

            # Build pricing information
            pricing = {
                "product_id": result.get("product_id"),
                "product_name": result.get("name"),
                "base_price": base_price,
                "currency": result.get("currency", "USD"),
                "billing_interval": result.get("billing_interval", "per_unit"),
                "pricing_type": "usage_based",
                "tiers": [],
                "features": result.get("features") or [],
                "quota_limits": result.get("quota_limits") or {}
            }

            # Add tiered pricing structure
            pricing["tiers"] = [
                {
                    "tier_name": "Base",
                    "min_units": 0,
                    "max_units": 1000,
                    "price_per_unit": base_price,
                    "currency": pricing["currency"]
                },
                {
                    "tier_name": "Standard",
                    "min_units": 1001,
                    "max_units": 10000,
                    "price_per_unit": round(base_price * 0.9, 4),
                    "currency": pricing["currency"]
                },
                {
                    "tier_name": "Premium",
                    "min_units": 10001,
                    "max_units": None,
                    "price_per_unit": round(base_price * 0.8, 4),
                    "currency": pricing["currency"]
                }
            ]

            return pricing

        except Exception as e:
            logger.error(f"Error getting product pricing: {e}")
            return None

    # ==================== Service Plan Operations ====================

    async def get_service_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """获取服务计划"""
        try:
            # TODO: Implement actual service plan query when service_plans table exists
            # For now, return a mock plan with plan_tier
            # Determine tier from plan_id
            tier = "pro"
            if "free" in plan_id.lower():
                tier = "free"
            elif "basic" in plan_id.lower():
                tier = "basic"
            elif "enterprise" in plan_id.lower():
                tier = "enterprise"

            return {
                "plan_id": plan_id,
                "plan_name": plan_id.replace("-", " ").title(),
                "plan_tier": tier,
                "features": [],
                "price": 0.0
            }
        except Exception as e:
            logger.error(f"Error getting service plan: {e}")
            return None

    # ==================== Subscription Operations ====================

    async def create_subscription(self, subscription: Any) -> Any:
        """创建订阅"""
        try:
            # TODO: Implement actual subscription creation when subscriptions table exists
            # For now, store in memory cache
            self._subscriptions_cache[subscription.subscription_id] = subscription
            logger.info(f"Mock: Created subscription {subscription.subscription_id} for user {subscription.user_id}")
            return subscription
        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            return None

    async def get_subscription(self, subscription_id: str) -> Optional[Any]:
        """获取单个订阅"""
        try:
            # TODO: Implement actual subscription query when subscriptions table exists
            # For now, return from memory cache
            subscription = self._subscriptions_cache.get(subscription_id)
            if subscription:
                logger.info(f"Mock: Found subscription {subscription_id}")
            else:
                logger.info(f"Mock: Subscription {subscription_id} not found in cache")
            return subscription
        except Exception as e:
            logger.error(f"Error getting subscription: {e}")
            return None

    async def update_subscription_status(self, subscription_id: str, new_status: str) -> bool:
        """更新订阅状态"""
        try:
            # TODO: Implement actual subscription update when subscriptions table exists
            # For now, update in memory cache
            subscription = self._subscriptions_cache.get(subscription_id)
            if not subscription:
                logger.warning(f"Mock: Subscription {subscription_id} not found for update")
                return False

            # Update the status
            from .models import SubscriptionStatus
            subscription.status = SubscriptionStatus(new_status)
            self._subscriptions_cache[subscription_id] = subscription
            logger.info(f"Mock: Updated subscription {subscription_id} status to {new_status}")
            return True
        except Exception as e:
            logger.error(f"Error updating subscription status: {e}")
            return False

    async def get_user_subscriptions(
        self,
        user_id: str,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取用户订阅列表"""
        try:
            # TODO: Implement actual subscription query when subscriptions table exists
            # For now, return empty list
            return []
        except Exception as e:
            logger.error(f"Error getting user subscriptions: {e}")
            return []

    # ==================== Usage Records Operations ====================

    async def record_product_usage(
        self,
        user_id: str,
        organization_id: Optional[str],
        subscription_id: Optional[str],
        product_id: str,
        usage_amount: Any,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        usage_details: Optional[Dict[str, Any]] = None,
        usage_timestamp: Optional[Any] = None
    ) -> str:
        """记录产品使用量"""
        try:
            # TODO: Implement actual usage recording when usage_records table exists
            # For now, generate a mock usage record ID
            usage_record_id = f"usage_{uuid.uuid4().hex[:16]}"
            logger.info(f"Mock: Recorded product usage {usage_record_id} for user {user_id}, product {product_id}, amount {usage_amount}")
            return usage_record_id
        except Exception as e:
            logger.error(f"Error recording product usage: {e}")
            raise

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
    ) -> List[Dict[str, Any]]:
        """获取使用记录"""
        try:
            # TODO: Implement actual usage records query when usage_records table exists
            # For now, return empty list
            return []
        except Exception as e:
            logger.error(f"Error getting usage records: {e}")
            return []

    # ==================== Statistics Operations ====================

    async def get_usage_statistics(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        product_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """获取使用统计"""
        try:
            # TODO: Implement actual statistics when usage_records table exists
            return {
                "total_usage": 0,
                "usage_by_product": {},
                "usage_by_date": {},
                "period": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None
                }
            }
        except Exception as e:
            logger.error(f"Error getting usage statistics: {e}")
            return {}


__all__ = ["ProductRepository"]
