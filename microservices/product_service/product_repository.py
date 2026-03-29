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
            user_id="product_service",
        min_pool_size=1,
        max_pool_size=2,
        )
        self.schema = "product"
        self.products_table = "products"
        self.pricing_table = "product_pricing"
        # Service clients for delegation (set via set_clients)
        self._subscription_client = None
        self._billing_client = None

    def set_clients(self, subscription_client=None, billing_client=None):
        """Inject service clients for subscription/usage delegation"""
        self._subscription_client = subscription_client
        self._billing_client = billing_client

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

    # ==================== Admin Operations ====================

    async def admin_soft_delete_product(self, product_id: str) -> bool:
        """Soft-delete a product by setting is_active = FALSE"""
        try:
            query = f'''
                UPDATE {self.schema}.{self.products_table}
                SET is_active = FALSE, updated_at = $2
                WHERE product_id = $1
                RETURNING product_id
            '''
            async with self.db:
                result = await self.db.query_row(query, params=[product_id, datetime.now(timezone.utc)])
            return result is not None
        except Exception as e:
            logger.error(f"Error soft-deleting product {product_id}: {e}")
            return False

    async def admin_create_pricing(self, product_id: str, pricing_id: str, tier_name: str,
                                    min_quantity: float, max_quantity: Optional[float],
                                    unit_price: float, currency: str,
                                    metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Create a pricing tier for a product"""
        try:
            query = f'''
                INSERT INTO {self.schema}.{self.pricing_table} (
                    pricing_id, product_id, tier_name, min_quantity, max_quantity,
                    unit_price, currency, metadata, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING *
            '''
            now = datetime.now(timezone.utc)
            params = [
                pricing_id, product_id, tier_name, min_quantity, max_quantity,
                unit_price, currency, json.dumps(metadata or {}), now, now
            ]
            async with self.db:
                result = await self.db.query_row(query, params=params)
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error creating pricing: {e}")
            return None

    async def admin_get_pricing(self, pricing_id: str) -> Optional[Dict[str, Any]]:
        """Get a pricing tier by ID"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.pricing_table}
                WHERE pricing_id = $1
            '''
            async with self.db:
                result = await self.db.query_row(query, params=[pricing_id])
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error getting pricing {pricing_id}: {e}")
            return None

    async def admin_update_pricing(self, pricing_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a pricing tier"""
        try:
            set_clauses = []
            params = []
            param_count = 0

            for key, value in updates.items():
                if value is None:
                    continue
                if key == "metadata":
                    value = json.dumps(value)
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")
                params.append(value)

            if not set_clauses:
                return await self.admin_get_pricing(pricing_id)

            param_count += 1
            set_clauses.append(f"updated_at = ${param_count}")
            params.append(datetime.now(timezone.utc))

            param_count += 1
            params.append(pricing_id)

            query = f'''
                UPDATE {self.schema}.{self.pricing_table}
                SET {", ".join(set_clauses)}
                WHERE pricing_id = ${param_count}
                RETURNING *
            '''
            async with self.db:
                result = await self.db.query_row(query, params=params)
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error updating pricing {pricing_id}: {e}")
            return None

    # ==================== Cost Definition Operations ====================

    async def get_cost_definitions(self, is_active=None, provider=None, service_type=None):
        """List cost definitions with optional filters"""
        try:
            conditions, params, pc = [], [], 0
            if is_active is not None:
                pc += 1; conditions.append(f"is_active = ${pc}"); params.append(is_active)
            if provider:
                pc += 1; conditions.append(f"provider = ${pc}"); params.append(provider)
            if service_type:
                pc += 1; conditions.append(f"service_type = ${pc}"); params.append(service_type)
            where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            query = f'SELECT * FROM {self.schema}.cost_definitions {where} ORDER BY service_type, provider, model_name'
            async with self.db:
                results = await self.db.query(query, params=params)
            return [dict(r) for r in results] if results else []
        except Exception as e:
            logger.error(f"Error getting cost definitions: {e}"); return []

    async def get_cost_definition(self, cost_id: str):
        """Get a cost definition by ID"""
        try:
            query = f'SELECT * FROM {self.schema}.cost_definitions WHERE cost_id = $1'
            async with self.db:
                result = await self.db.query_row(query, params=[cost_id])
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error getting cost definition {cost_id}: {e}"); return None

    async def create_cost_definition(self, data: Dict[str, Any]):
        """Create a new cost definition"""
        try:
            query = f'''INSERT INTO {self.schema}.cost_definitions (
                cost_id, product_id, service_type, provider, model_name, operation_type,
                cost_per_unit, unit_type, unit_size, original_cost_usd, margin_percentage,
                effective_from, effective_until, free_tier_limit, free_tier_period,
                is_active, description, metadata, created_at, updated_at
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20) RETURNING *'''
            now = datetime.now(timezone.utc)
            params = [
                data["cost_id"], data.get("product_id"), data["service_type"],
                data.get("provider"), data.get("model_name"), data.get("operation_type"),
                data["cost_per_unit"], data["unit_type"], data.get("unit_size", 1),
                data.get("original_cost_usd"), data.get("margin_percentage", 30.0),
                data.get("effective_from", now), data.get("effective_until"),
                data.get("free_tier_limit", 0), data.get("free_tier_period", "monthly"),
                data.get("is_active", True), data.get("description"),
                json.dumps(data.get("metadata", {})), now, now,
            ]
            async with self.db:
                result = await self.db.query_row(query, params=params)
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error creating cost definition: {e}"); return None

    async def update_cost_definition(self, cost_id: str, updates: Dict[str, Any]):
        """Update a cost definition (metadata/description, not price)"""
        try:
            set_clauses, params, pc = [], [], 0
            for k, v in updates.items():
                if v is None: continue
                if k == "metadata": v = json.dumps(v)
                pc += 1; set_clauses.append(f"{k} = ${pc}"); params.append(v)
            if not set_clauses: return await self.get_cost_definition(cost_id)
            pc += 1; set_clauses.append(f"updated_at = ${pc}"); params.append(datetime.now(timezone.utc))
            pc += 1; params.append(cost_id)
            query = f'UPDATE {self.schema}.cost_definitions SET {", ".join(set_clauses)} WHERE cost_id = ${pc} RETURNING *'
            async with self.db:
                result = await self.db.query_row(query, params=params)
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error updating cost definition {cost_id}: {e}"); return None

    async def expire_cost_definition(self, cost_id: str, effective_until: datetime) -> bool:
        """Set effective_until on a cost definition"""
        try:
            query = f'UPDATE {self.schema}.cost_definitions SET effective_until = $1, updated_at = $2 WHERE cost_id = $3 RETURNING cost_id'
            async with self.db:
                result = await self.db.query_row(query, params=[effective_until, datetime.now(timezone.utc), cost_id])
            return result is not None
        except Exception as e:
            logger.error(f"Error expiring cost definition {cost_id}: {e}"); return False

    async def get_cost_history(self, model_name: str):
        """Get price history for a model"""
        try:
            query = f'SELECT * FROM {self.schema}.cost_definitions WHERE model_name = $1 ORDER BY effective_from DESC'
            async with self.db:
                results = await self.db.query(query, params=[model_name])
            return [dict(r) for r in results] if results else []
        except Exception as e:
            logger.error(f"Error getting cost history for {model_name}: {e}"); return []

    # ==================== Catalog Alignment ====================

    async def get_catalog_alignment(self) -> Dict[str, Any]:
        """Cross-check products vs cost_definitions for drift detection"""
        try:
            pq = f"SELECT product_id, product_name, metadata FROM {self.schema}.{self.products_table} WHERE product_type = 'model_inference' AND is_active = true"
            cq = f"SELECT DISTINCT model_name, provider FROM {self.schema}.cost_definitions WHERE service_type = 'model_inference' AND is_active = true AND (effective_until IS NULL OR effective_until > NOW())"
            async with self.db:
                products = await self.db.query(pq, params=[])
                costs = await self.db.query(cq, params=[])
            product_models = {}
            for p in (products or []):
                meta = p.get("metadata") or {}
                model = meta.get("model") or p.get("product_id")
                product_models[model] = {"product_id": p["product_id"], "product_name": p.get("product_name")}
            cost_models = {c["model_name"] for c in (costs or []) if c.get("model_name")}
            return {
                "aligned": not any(k not in cost_models for k in product_models) and not any(m not in product_models for m in cost_models),
                "total_products": len(product_models), "total_cost_definitions": len(cost_models),
                "products_without_cost_definitions": [{"product_id": v["product_id"], "model": k, "action": "Add cost_definition"} for k, v in product_models.items() if k not in cost_models],
                "cost_definitions_without_products": [{"model_name": m, "action": "Add product entry"} for m in cost_models if m not in product_models],
            }
        except Exception as e:
            logger.error(f"Error checking catalog alignment: {e}"); return {"error": str(e)}

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

    # ==================== Subscription Operations (delegated to subscription_service) ====================

    async def create_subscription(self, subscription: Any) -> Any:
        """Delegate subscription creation to subscription_service"""
        try:
            if self._subscription_client:
                result = await self._subscription_client._client.create_subscription(
                    user_id=subscription.user_id,
                    tier_id=subscription.plan_id,
                    billing_cycle=subscription.billing_cycle.value if hasattr(subscription.billing_cycle, 'value') else subscription.billing_cycle,
                )
                if result:
                    logger.info(f"Created subscription {subscription.subscription_id} via subscription_service")
                    return subscription
            logger.warning("subscription_client not available, returning subscription as-is")
            return subscription
        except Exception as e:
            logger.warning(f"Failed to delegate subscription creation: {e}")
            return subscription

    async def get_subscription(self, subscription_id: str) -> Optional[Any]:
        """Delegate subscription lookup to subscription_service"""
        try:
            if self._subscription_client:
                result = await self._subscription_client.get_subscription(subscription_id)
                if result:
                    return result
            return None
        except Exception as e:
            logger.warning(f"Failed to get subscription {subscription_id} from subscription_service: {e}")
            return None

    async def update_subscription_status(self, subscription_id: str, new_status: str) -> bool:
        """Delegate subscription status update to subscription_service"""
        try:
            if self._subscription_client:
                return await self._subscription_client._client.cancel_subscription(subscription_id)
            logger.warning("subscription_client not available for status update")
            return False
        except Exception as e:
            logger.warning(f"Failed to update subscription {subscription_id} status: {e}")
            return False

    async def get_user_subscriptions(
        self,
        user_id: str,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Delegate user subscription query to subscription_service"""
        try:
            if self._subscription_client:
                return await self._subscription_client.get_user_subscriptions(user_id, status)
            return []
        except Exception as e:
            logger.warning(f"Failed to get subscriptions for user {user_id}: {e}")
            return []

    # ==================== Usage Records Operations (delegated to billing_service) ====================

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
        """Delegate usage recording to billing_service"""
        try:
            if self._billing_client:
                result = await self._billing_client.record_product_usage(
                    user_id=user_id,
                    organization_id=organization_id,
                    product_id=product_id,
                    usage_amount=float(usage_amount),
                    session_id=session_id,
                    request_id=request_id,
                    usage_details=usage_details,
                )
                if result:
                    logger.info(f"Recorded usage via billing_service for user {user_id}, product {product_id}")
                    return result
            # Fallback: generate local ID (billing_service unavailable)
            fallback_id = f"usage_{uuid.uuid4().hex[:16]}"
            logger.warning(f"billing_client unavailable, generated fallback usage ID: {fallback_id}")
            return fallback_id
        except Exception as e:
            logger.warning(f"Failed to record usage via billing_service: {e}")
            fallback_id = f"usage_{uuid.uuid4().hex[:16]}"
            return fallback_id

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
        """Delegate usage records query to billing_service"""
        try:
            if self._billing_client:
                return await self._billing_client.get_usage_records(
                    user_id=user_id,
                    organization_id=organization_id,
                    product_id=product_id,
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit,
                    offset=offset,
                )
            return []
        except Exception as e:
            logger.warning(f"Failed to get usage records from billing_service: {e}")
            return []

    # ==================== Statistics Operations (delegated to billing_service) ====================

    async def get_usage_statistics(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        product_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Delegate usage statistics to billing_service"""
        try:
            if self._billing_client:
                return await self._billing_client.get_usage_statistics(
                    user_id=user_id,
                    organization_id=organization_id,
                    product_id=product_id,
                    start_date=start_date,
                    end_date=end_date,
                )
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
            logger.warning(f"Failed to get usage statistics from billing_service: {e}")
            return {}


__all__ = ["ProductRepository"]
