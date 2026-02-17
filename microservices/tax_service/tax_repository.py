"""
Tax Repository

Data access layer for tax calculation operations using PostgresClient.
Matches schema: tax.calculations
"""

import logging
import sys
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common import AsyncPostgresClient
from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class TaxCalculationNotFoundException(Exception):
    """Tax calculation not found exception"""
    pass


class TaxRepository:
    """
    Repository for tax calculation operations.

    Tables:
        - tax.calculations: Tax calculation records with line-item breakdown
    """

    def __init__(self, config: Optional[ConfigManager] = None):
        """Initialize Tax Repository with PostgresClient"""
        if config is None:
            config = ConfigManager("tax_service")

        host, port = config.discover_service(
            service_name='postgres_service',
            default_host='localhost',
            default_port=5432,
            env_host_key='POSTGRES_HOST',
            env_port_key='POSTGRES_PORT'
        )

        logger.info(f"Connecting to PostgreSQL at {host}:{port}")
        self.db = AsyncPostgresClient(host=host, port=port, user_id="tax_service")

        self.schema = "tax"
        self.calculations_table = "calculations"

        logger.info("TaxRepository initialized with PostgresClient")

    async def create_calculation(
        self,
        order_id: str,
        user_id: str,
        subtotal: float,
        total_tax: float,
        currency: str = "USD",
        tax_lines: Optional[List[Dict[str, Any]]] = None,
        shipping_address: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new tax calculation record"""
        try:
            calculation_id = f"tax_{uuid.uuid4().hex[:12]}"
            now = datetime.now(timezone.utc)

            calculation_data = {
                "calculation_id": calculation_id,
                "order_id": order_id,
                "user_id": user_id,
                "subtotal": subtotal,
                "total_tax": total_tax,
                "currency": currency,
                "tax_lines": tax_lines or [],
                "shipping_address": shipping_address,
                "created_at": now.isoformat(),
                "metadata": metadata or {}
            }

            async with self.db:
                await self.db.insert_into(
                    self.calculations_table,
                    [calculation_data],
                    schema=self.schema
                )

            return await self.get_calculation(calculation_id)

        except Exception as e:
            logger.error(f"Failed to create tax calculation: {e}")
            raise

    async def get_calculation(self, calculation_id: str) -> Optional[Dict[str, Any]]:
        """Get tax calculation by ID"""
        try:
            query = f'SELECT * FROM "{self.schema}".{self.calculations_table} WHERE calculation_id = $1'

            async with self.db:
                result = await self.db.query_row(query, [calculation_id], schema=self.schema)

            return self._normalize_calculation(result) if result else None

        except Exception as e:
            logger.error(f"Failed to get tax calculation {calculation_id}: {e}")
            raise

    async def get_calculation_by_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get tax calculation by order ID"""
        try:
            query = f'SELECT * FROM "{self.schema}".{self.calculations_table} WHERE order_id = $1 ORDER BY created_at DESC LIMIT 1'

            async with self.db:
                result = await self.db.query_row(query, [order_id], schema=self.schema)

            return self._normalize_calculation(result) if result else None

        except Exception as e:
            logger.error(f"Failed to get tax calculation for order {order_id}: {e}")
            raise

    async def list_calculations(
        self,
        limit: int = 50,
        offset: int = 0,
        order_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List tax calculations with filtering"""
        try:
            conditions = []
            params = []
            param_count = 0

            if order_id:
                param_count += 1
                conditions.append(f"order_id = ${param_count}")
                params.append(order_id)

            if user_id:
                param_count += 1
                conditions.append(f"user_id = ${param_count}")
                params.append(user_id)

            where_clause = " AND ".join(conditions) if conditions else "TRUE"
            query = f'''
                SELECT * FROM "{self.schema}".{self.calculations_table}
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT {limit} OFFSET {offset}
            '''

            async with self.db:
                results = await self.db.query(query, params, schema=self.schema)

            return [self._normalize_calculation(r) for r in (results or [])]

        except Exception as e:
            logger.error(f"Failed to list tax calculations: {e}")
            raise

    def _normalize_calculation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize tax calculation data from database"""
        if not data:
            return None

        # Handle JSONB fields
        tax_lines = data.get("tax_lines", [])
        if isinstance(tax_lines, str):
            import json
            tax_lines = json.loads(tax_lines)

        shipping_address = data.get("shipping_address")
        if isinstance(shipping_address, str):
            import json
            shipping_address = json.loads(shipping_address)

        metadata = data.get("metadata", {})
        if isinstance(metadata, str):
            import json
            metadata = json.loads(metadata)

        return {
            "calculation_id": data["calculation_id"],
            "order_id": data["order_id"],
            "user_id": data.get("user_id"),
            "subtotal": float(data.get("subtotal", 0)),
            "total_tax": float(data.get("total_tax", 0)),
            "currency": data.get("currency", "USD"),
            "tax_lines": tax_lines,
            "shipping_address": shipping_address,
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "metadata": metadata
        }
