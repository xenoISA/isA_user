"""
Order Repository

Data access layer for order management operations using PostgresClient.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid
import logging
from decimal import Decimal
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common import AsyncPostgresClient
from core.config_manager import ConfigManager
from .models import (
    Order, OrderStatus, OrderType, PaymentStatus,
    OrderFilter, OrderStatistics
)

logger = logging.getLogger(__name__)


class OrderNotFoundException(Exception):
    """Order not found exception"""
    pass


class OrderRepository:
    """
    Repository for order data operations

    Handles all database operations for orders using PostgresClient.
    """

    def __init__(self, config: Optional[ConfigManager] = None):
        """Initialize Order Repository with PostgresClient"""
        # 使用 config_manager 进行服务发现
        if config is None:
            config = ConfigManager("order_service")

        # 发现 PostgreSQL 服务
        # 优先级：环境变量 → Consul → localhost fallback
        host, port = config.discover_service(
            service_name='postgres_grpc_service',
            default_host='isa-postgres-grpc',
            default_port=50061,
            env_host_key='POSTGRES_GRPC_HOST',
            env_port_key='POSTGRES_GRPC_PORT'
        )

        logger.info(f"Connecting to PostgreSQL at {host}:{port}")
        self.db = AsyncPostgresClient(host=host, port=port, user_id="order_service")

        self.schema = "orders"  # Using "orders" instead of "order" (reserved keyword)
        self.orders_table = "orders"

        logger.info("OrderRepository initialized with PostgresClient")

    async def create_order(
        self,
        user_id: str,
        order_type: OrderType,
        total_amount: Decimal,
        currency: str = "USD",
        payment_intent_id: Optional[str] = None,
        subscription_id: Optional[str] = None,
        wallet_id: Optional[str] = None,
        items: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None
    ) -> Order:
        """Create a new order"""
        try:
            order_id = f"order_{uuid.uuid4().hex[:12]}"
            now = datetime.now(timezone.utc)

            order_data = {
                "order_id": order_id,
                "user_id": user_id,
                "organization_id": None,
                "order_type": order_type.value,
                "status": OrderStatus.PENDING.value,
                "total_amount": float(total_amount),
                "currency": currency,
                "discount_amount": 0.0,
                "tax_amount": 0.0,
                "final_amount": float(total_amount),
                "payment_status": PaymentStatus.PENDING.value,
                "payment_intent_id": payment_intent_id,
                "payment_method": None,
                "subscription_id": subscription_id,
                "wallet_id": wallet_id,
                "invoice_id": None,
                "items": items or [],  # Direct list
                "metadata": metadata or {},  # Direct dict
                "fulfillment_status": "pending",
                "tracking_number": None,
                "shipping_address": None,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "completed_at": None,
                "cancelled_at": None,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "cancellation_reason": None,
                "cancelled_by": None
            }

            async with self.db:
                count = await self.db.insert_into(self.orders_table, [order_data], schema=self.schema)

            if count is not None and count > 0:
                return await self.get_order(order_id)

            # If insert returns None/0, try to get the order anyway
            result = await self.get_order(order_id)
            if result:
                return result

            raise Exception("Failed to create order")

        except Exception as e:
            logger.error(f"Failed to create order: {e}")
            raise

    async def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        try:
            query = f'SELECT * FROM "{self.schema}".{self.orders_table} WHERE order_id = $1'

            async with self.db:
                result = await self.db.query_row(query, [order_id], schema=self.schema)

            if result:
                return self._dict_to_order(result)
            return None

        except Exception as e:
            logger.error(f"Failed to get order {order_id}: {e}")
            raise

    async def update_order(
        self,
        order_id: str,
        status: Optional[OrderStatus] = None,
        payment_status: Optional[PaymentStatus] = None,
        payment_intent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        completed_at: Optional[datetime] = None
    ) -> Optional[Order]:
        """Update order"""
        try:
            update_data = {
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            if status:
                update_data["status"] = status.value
            if payment_status:
                update_data["payment_status"] = payment_status.value
            if payment_intent_id:
                update_data["payment_intent_id"] = payment_intent_id
            if metadata:
                update_data["metadata"] = metadata  # Direct dict
            if completed_at:
                update_data["completed_at"] = completed_at.isoformat()

            # Build SET clause
            set_clauses = []
            params = []
            param_count = 0

            for key, value in update_data.items():
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")
                params.append(value)

            param_count += 1
            params.append(order_id)

            set_clause = ", ".join(set_clauses)
            query = f'''
                UPDATE "{self.schema}".{self.orders_table}
                SET {set_clause}
                WHERE order_id = ${param_count}
            '''

            async with self.db:
                count = await self.db.execute(query, params, schema=self.schema)

            if count is not None and count > 0:
                return await self.get_order(order_id)
            return None

        except Exception as e:
            logger.error(f"Failed to update order {order_id}: {e}")
            raise

    async def list_orders(
        self,
        limit: int = 50,
        offset: int = 0,
        user_id: Optional[str] = None,
        order_type: Optional[OrderType] = None,
        status: Optional[OrderStatus] = None,
        payment_status: Optional[PaymentStatus] = None
    ) -> List[Order]:
        """List orders with filtering"""
        try:
            conditions = []
            params = []
            param_count = 0

            if user_id:
                param_count += 1
                conditions.append(f"user_id = ${param_count}")
                params.append(user_id)

            if order_type:
                param_count += 1
                conditions.append(f"order_type = ${param_count}")
                params.append(order_type.value)

            if status:
                param_count += 1
                conditions.append(f"status = ${param_count}")
                params.append(status.value)

            if payment_status:
                param_count += 1
                conditions.append(f"payment_status = ${param_count}")
                params.append(payment_status.value)

            where_clause = " AND ".join(conditions) if conditions else "TRUE"
            query = f'''
                SELECT * FROM "{self.schema}".{self.orders_table}
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT {limit} OFFSET {offset}
            '''

            async with self.db:
                results = await self.db.query(query, params, schema=self.schema)

            if results:
                return [self._dict_to_order(order_data) for order_data in results]
            return []

        except Exception as e:
            logger.error(f"Failed to list orders: {e}")
            raise

    async def get_user_orders(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Order]:
        """Get orders for a specific user"""
        return await self.list_orders(
            limit=limit,
            offset=offset,
            user_id=user_id
        )

    async def search_orders(
        self,
        query: str,
        limit: int = 50,
        user_id: Optional[str] = None
    ) -> List[Order]:
        """Search orders by query"""
        try:
            conditions = []
            params = []
            param_count = 0

            # Add search conditions
            param_count += 1
            params.append(f"%{query}%")
            search_condition = f"(order_id ILIKE ${param_count} OR order_type ILIKE ${param_count} OR status ILIKE ${param_count})"
            conditions.append(search_condition)

            if user_id:
                param_count += 1
                conditions.append(f"user_id = ${param_count}")
                params.append(user_id)

            where_clause = " AND ".join(conditions)
            sql_query = f'''
                SELECT * FROM "{self.schema}".{self.orders_table}
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT {limit}
            '''

            async with self.db:
                results = await self.db.query(sql_query, params, schema=self.schema)

            if results:
                return [self._dict_to_order(order_data) for order_data in results]
            return []

        except Exception as e:
            logger.error(f"Failed to search orders: {e}")
            raise

    async def get_orders_by_payment_intent(self, payment_intent_id: str) -> List[Order]:
        """Get orders by payment intent ID"""
        try:
            query = f'SELECT * FROM "{self.schema}".{self.orders_table} WHERE payment_intent_id = $1'

            async with self.db:
                results = await self.db.query(query, [payment_intent_id], schema=self.schema)

            if results:
                return [self._dict_to_order(order_data) for order_data in results]
            return []

        except Exception as e:
            logger.error(f"Failed to get orders by payment intent {payment_intent_id}: {e}")
            raise

    async def get_order_by_payment_intent(self, payment_intent_id: str) -> Optional[Order]:
        """Get a single order by payment intent ID (returns first match)"""
        try:
            orders = await self.get_orders_by_payment_intent(payment_intent_id)
            return orders[0] if orders else None
        except Exception as e:
            logger.error(f"Failed to get order by payment intent {payment_intent_id}: {e}")
            raise

    async def get_orders_by_subscription(self, subscription_id: str) -> List[Order]:
        """Get orders by subscription ID"""
        try:
            query = f'SELECT * FROM "{self.schema}".{self.orders_table} WHERE subscription_id = $1'

            async with self.db:
                results = await self.db.query(query, [subscription_id], schema=self.schema)

            if results:
                return [self._dict_to_order(order_data) for order_data in results]
            return []

        except Exception as e:
            logger.error(f"Failed to get orders by subscription {subscription_id}: {e}")
            raise

    async def cancel_order(self, order_id: str, reason: Optional[str] = None) -> bool:
        """Cancel an order"""
        try:
            metadata = {"cancellation_reason": reason} if reason else {}

            result = await self.update_order(
                order_id=order_id,
                status=OrderStatus.CANCELLED,
                metadata=metadata
            )

            return result is not None

        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            raise

    async def complete_order(
        self,
        order_id: str,
        payment_intent_id: Optional[str] = None
    ) -> bool:
        """Complete an order"""
        try:
            result = await self.update_order(
                order_id=order_id,
                status=OrderStatus.COMPLETED,
                payment_status=PaymentStatus.COMPLETED,
                payment_intent_id=payment_intent_id,
                completed_at=datetime.now(timezone.utc)
            )

            return result is not None

        except Exception as e:
            logger.error(f"Failed to complete order {order_id}: {e}")
            raise

    async def get_order_statistics(self) -> Dict[str, Any]:
        """Get order statistics"""
        try:
            # Get total orders
            total_query = f'SELECT COUNT(*) as count FROM "{self.schema}".{self.orders_table}'
            async with self.db:
                total_result = await self.db.query_row(total_query, [], schema=self.schema)
            total_orders = int(total_result.get("count", 0)) if total_result else 0

            # Get orders by status
            status_stats = {}
            for status in OrderStatus:
                status_query = f'SELECT COUNT(*) as count FROM "{self.schema}".{self.orders_table} WHERE status = $1'
                async with self.db:
                    status_result = await self.db.query_row(status_query, [status.value], schema=self.schema)
                status_stats[status.value] = int(status_result.get("count", 0)) if status_result else 0

            # Get orders by type
            type_stats = {}
            for order_type in OrderType:
                type_query = f'SELECT COUNT(*) as count FROM "{self.schema}".{self.orders_table} WHERE order_type = $1'
                async with self.db:
                    type_result = await self.db.query_row(type_query, [order_type.value], schema=self.schema)
                type_stats[order_type.value] = int(type_result.get("count", 0)) if type_result else 0

            # Get revenue (completed orders only)
            revenue_query = f'SELECT total_amount, currency FROM "{self.schema}".{self.orders_table} WHERE status = $1'
            async with self.db:
                revenue_results = await self.db.query(revenue_query, [OrderStatus.COMPLETED.value], schema=self.schema)

            total_revenue = Decimal(0)
            revenue_by_currency = {}

            if revenue_results:
                for order in revenue_results:
                    amount = Decimal(str(order["total_amount"]))
                    currency = order["currency"]

                    total_revenue += amount
                    revenue_by_currency[currency] = revenue_by_currency.get(currency, Decimal(0)) + amount

            avg_order_value = total_revenue / max(total_orders, 1)

            # Get recent orders (simplified - would need date filtering in real implementation)
            recent_24h = min(total_orders, 10)  # Placeholder
            recent_7d = min(total_orders, 50)   # Placeholder
            recent_30d = min(total_orders, 200) # Placeholder

            return {
                "total_orders": total_orders,
                "orders_by_status": status_stats,
                "orders_by_type": type_stats,
                "total_revenue": float(total_revenue),
                "revenue_by_currency": {k: float(v) for k, v in revenue_by_currency.items()},
                "avg_order_value": float(avg_order_value),
                "recent_orders_24h": recent_24h,
                "recent_orders_7d": recent_7d,
                "recent_orders_30d": recent_30d
            }

        except Exception as e:
            logger.error(f"Failed to get order statistics: {e}")
            raise

    def _dict_to_order(self, data: Dict[str, Any]) -> Order:
        """Convert dictionary to Order model"""
        # Handle items (list)
        items = data.get("items")
        if isinstance(items, str):
            import json
            items = json.loads(items)
        elif not isinstance(items, list):
            items = []

        # Handle metadata (dict)
        metadata = data.get("metadata")
        if isinstance(metadata, str):
            import json
            metadata = json.loads(metadata)
        elif not isinstance(metadata, dict):
            metadata = {}

        return Order(
            order_id=data["order_id"],
            user_id=data["user_id"],
            order_type=OrderType(data["order_type"]),
            status=OrderStatus(data["status"]),
            total_amount=Decimal(str(data["total_amount"])),
            currency=data["currency"],
            payment_status=PaymentStatus(data["payment_status"]),
            payment_intent_id=data.get("payment_intent_id"),
            subscription_id=data.get("subscription_id"),
            wallet_id=data.get("wallet_id"),
            items=items,
            metadata=metadata,
            created_at=datetime.fromisoformat(data["created_at"].replace('Z', '+00:00')),
            updated_at=datetime.fromisoformat(data["updated_at"].replace('Z', '+00:00')),
            completed_at=datetime.fromisoformat(data["completed_at"].replace('Z', '+00:00')) if data.get("completed_at") else None,
            expires_at=datetime.fromisoformat(data["expires_at"].replace('Z', '+00:00')) if data.get("expires_at") else None
        )
