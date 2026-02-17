"""
Inventory Repository

Data access layer for inventory operations using PostgresClient.
Matches schema: inventory.reservations, inventory.stock_levels
"""

import logging
import sys
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common import AsyncPostgresClient
from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class ReservationNotFoundException(Exception):
    """Reservation not found exception"""
    pass


class InventoryRepository:
    """
    Repository for inventory data operations.

    Tables:
        - inventory.reservations: Order inventory reservations (multi-item)
        - inventory.stock_levels: SKU stock levels per location
    """

    def __init__(self, config: Optional[ConfigManager] = None):
        """Initialize Inventory Repository with PostgresClient"""
        if config is None:
            config = ConfigManager("inventory_service")

        host, port = config.discover_service(
            service_name='postgres_service',
            default_host='localhost',
            default_port=5432,
            env_host_key='POSTGRES_HOST',
            env_port_key='POSTGRES_PORT'
        )

        logger.info(f"Connecting to PostgreSQL at {host}:{port}")
        self.db = AsyncPostgresClient(host=host, port=port, user_id="inventory_service")

        self.schema = "inventory"
        self.reservations_table = "reservations"
        self.stock_table = "stock_levels"

        logger.info("InventoryRepository initialized with PostgresClient")

    async def create_reservation(
        self,
        order_id: str,
        user_id: str,
        items: List[Dict[str, Any]],
        expires_in_minutes: int = 30,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new inventory reservation"""
        try:
            reservation_id = f"res_{uuid.uuid4().hex[:12]}"
            now = datetime.now(timezone.utc)
            expires_at = now + timedelta(minutes=expires_in_minutes)

            reservation_data = {
                "reservation_id": reservation_id,
                "order_id": order_id,
                "user_id": user_id,
                "items": items,
                "status": "active",
                "expires_at": expires_at.isoformat(),
                "created_at": now.isoformat(),
                "metadata": metadata or {}
            }

            async with self.db:
                await self.db.insert_into(
                    self.reservations_table,
                    [reservation_data],
                    schema=self.schema
                )

            return await self.get_reservation(reservation_id)

        except Exception as e:
            logger.error(f"Failed to create reservation: {e}")
            raise

    async def get_reservation(self, reservation_id: str) -> Optional[Dict[str, Any]]:
        """Get reservation by ID"""
        try:
            query = f'SELECT * FROM "{self.schema}".{self.reservations_table} WHERE reservation_id = $1'

            async with self.db:
                result = await self.db.query_row(query, [reservation_id], schema=self.schema)

            return self._normalize_reservation(result) if result else None

        except Exception as e:
            logger.error(f"Failed to get reservation {reservation_id}: {e}")
            raise

    async def get_reservation_by_order(self, order_id: str, status: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get reservation by order ID"""
        try:
            if status:
                query = f'SELECT * FROM "{self.schema}".{self.reservations_table} WHERE order_id = $1 AND status = $2 ORDER BY created_at DESC LIMIT 1'
                params = [order_id, status]
            else:
                query = f'SELECT * FROM "{self.schema}".{self.reservations_table} WHERE order_id = $1 ORDER BY created_at DESC LIMIT 1'
                params = [order_id]

            async with self.db:
                result = await self.db.query_row(query, params, schema=self.schema)

            return self._normalize_reservation(result) if result else None

        except Exception as e:
            logger.error(f"Failed to get reservation for order {order_id}: {e}")
            raise

    async def get_active_reservation_for_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get active reservation for an order"""
        return await self.get_reservation_by_order(order_id, status="active")

    async def commit_reservation(self, reservation_id: str) -> Optional[Dict[str, Any]]:
        """Commit a reservation (after payment)"""
        try:
            now = datetime.now(timezone.utc)
            query = f'''
                UPDATE "{self.schema}".{self.reservations_table}
                SET status = $1, committed_at = $2
                WHERE reservation_id = $3 AND status = 'active'
            '''

            async with self.db:
                await self.db.execute(query, ["committed", now.isoformat(), reservation_id], schema=self.schema)

            return await self.get_reservation(reservation_id)

        except Exception as e:
            logger.error(f"Failed to commit reservation {reservation_id}: {e}")
            raise

    async def release_reservation(self, reservation_id: str) -> Optional[Dict[str, Any]]:
        """Release a reservation (order canceled)"""
        try:
            now = datetime.now(timezone.utc)
            query = f'''
                UPDATE "{self.schema}".{self.reservations_table}
                SET status = $1, released_at = $2
                WHERE reservation_id = $3 AND status = 'active'
            '''

            async with self.db:
                await self.db.execute(query, ["released", now.isoformat(), reservation_id], schema=self.schema)

            return await self.get_reservation(reservation_id)

        except Exception as e:
            logger.error(f"Failed to release reservation {reservation_id}: {e}")
            raise

    async def list_reservations(
        self,
        limit: int = 50,
        offset: int = 0,
        order_id: Optional[str] = None,
        user_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List reservations with filtering"""
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

            if status:
                param_count += 1
                conditions.append(f"status = ${param_count}")
                params.append(status)

            where_clause = " AND ".join(conditions) if conditions else "TRUE"
            query = f'''
                SELECT * FROM "{self.schema}".{self.reservations_table}
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT {limit} OFFSET {offset}
            '''

            async with self.db:
                results = await self.db.query(query, params, schema=self.schema)

            return [self._normalize_reservation(r) for r in (results or [])]

        except Exception as e:
            logger.error(f"Failed to list reservations: {e}")
            raise

    def _normalize_reservation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize reservation data from database"""
        if not data:
            return None

        # Handle JSONB fields
        items = data.get("items", [])
        if isinstance(items, str):
            import json
            items = json.loads(items)

        metadata = data.get("metadata", {})
        if isinstance(metadata, str):
            import json
            metadata = json.loads(metadata)

        return {
            "reservation_id": data["reservation_id"],
            "order_id": data["order_id"],
            "user_id": data.get("user_id"),
            "items": items,
            "status": data.get("status", "active"),
            "expires_at": data.get("expires_at"),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "committed_at": data.get("committed_at"),
            "released_at": data.get("released_at"),
            "metadata": metadata
        }
