"""
Product Repository

数据访问层 - PostgreSQL + gRPC
"""

import logging
import os
import sys
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common.postgres_client import PostgresClient
from .models import Product, PricingModel, ProductType, Currency

logger = logging.getLogger(__name__)


class ProductRepository:
    """产品数据访问仓库 - PostgreSQL"""

    def __init__(self):
        self.db = PostgresClient(
            host=os.getenv("POSTGRES_GRPC_HOST", "isa-postgres-grpc"),
            port=int(os.getenv("POSTGRES_GRPC_PORT", "50061")),
            user_id="product_service"
        )
        self.schema = "product"
        self.products_table = "products"
        self.pricing_table = "product_pricing"

    async def initialize(self):
        """Initialize repository (placeholder for consistency with other services)"""
        logger.info("Product repository initialized")

    async def close(self):
        """Close repository connections (placeholder for consistency with other services)"""
        logger.info("Product repository connections closed")

    async def create_product(self, product: Product) -> Optional[Product]:
        """创建产品"""
        try:
            import json
            query = f'''
                INSERT INTO {self.schema}.{self.products_table} (
                    product_id, product_name, product_code, description, category,
                    product_type, base_price, currency, billing_interval,
                    features, quota_limits, is_active, is_featured, display_order,
                    metadata, tags, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
                RETURNING *
            '''

            now = datetime.now(timezone.utc)
            params = [
                product.product_id, product.product_name, product.product_code,
                product.description, product.category, product.product_type.value,
                float(product.base_price), product.currency.value, product.billing_interval,
                json.dumps(product.features) if product.features else "[]",
                json.dumps(product.quota_limits) if product.quota_limits else "{}",
                product.is_active, product.is_featured, product.display_order,
                json.dumps(product.metadata) if product.metadata else "{}",
                product.tags, now, now
            ]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

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

            with self.db:
                results = self.db.query(query, [product_id], schema=self.schema)

            if results and len(results) > 0:
                return self._row_to_product(results[0])
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

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return [self._row_to_product(row) for row in results] if results else []

        except Exception as e:
            logger.error(f"Error getting products: {e}")
            return []

    async def update_product(self, product_id: str, updates: Dict[str, Any]) -> Optional[Product]:
        """更新产品"""
        try:
            import json
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

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

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

            with self.db:
                count = self.db.execute(query, [product_id], schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error deleting product: {e}")
            return False

    def _row_to_product(self, row: Dict[str, Any]) -> Product:
        """Convert database row to Product model"""
        return Product(
            id=row.get("id"),
            product_id=row.get("product_id"),
            product_name=row.get("product_name"),
            product_code=row.get("product_code"),
            description=row.get("description"),
            category=row.get("category"),
            product_type=ProductType(row.get("product_type")),
            base_price=Decimal(str(row.get("base_price", 0))),
            currency=Currency(row.get("currency", "USD")),
            billing_interval=row.get("billing_interval"),
            features=row.get("features", []),
            quota_limits=row.get("quota_limits", {}),
            is_active=row.get("is_active", True),
            is_featured=row.get("is_featured", False),
            display_order=row.get("display_order", 0),
            metadata=row.get("metadata", {}),
            tags=row.get("tags", []),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at")
        )


__all__ = ["ProductRepository"]
