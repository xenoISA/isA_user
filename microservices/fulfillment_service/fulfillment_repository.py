"""
Fulfillment Repository

Data access layer for fulfillment/shipment operations using PostgresClient.
Matches schema: fulfillment.shipments
"""

import logging
import sys
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common import AsyncPostgresClient
from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class ShipmentNotFoundException(Exception):
    """Shipment not found exception"""
    pass


class FulfillmentRepository:
    """
    Repository for fulfillment/shipment operations.

    Tables:
        - fulfillment.shipments: Shipment records with full lifecycle tracking
    """

    def __init__(self, config: Optional[ConfigManager] = None):
        """Initialize Fulfillment Repository with PostgresClient"""
        if config is None:
            config = ConfigManager("fulfillment_service")

        host, port = config.discover_service(
            service_name='postgres_service',
            default_host='localhost',
            default_port=5432,
            env_host_key='POSTGRES_HOST',
            env_port_key='POSTGRES_PORT'
        )

        logger.info(f"Connecting to PostgreSQL at {host}:{port}")
        self.db = AsyncPostgresClient(host=host, port=port, user_id="fulfillment_service")

        self.schema = "fulfillment"
        self.shipments_table = "shipments"

        logger.info("FulfillmentRepository initialized with PostgresClient")

    async def create_shipment(
        self,
        order_id: str,
        user_id: str,
        items: List[Dict[str, Any]],
        shipping_address: Dict[str, Any],
        carrier: Optional[str] = None,
        tracking_number: Optional[str] = None,
        status: str = "created",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new shipment record"""
        try:
            shipment_id = f"shp_{uuid.uuid4().hex[:12]}"
            now = datetime.now(timezone.utc)

            shipment_data = {
                "shipment_id": shipment_id,
                "order_id": order_id,
                "user_id": user_id,
                "items": items,
                "shipping_address": shipping_address,
                "carrier": carrier,
                "tracking_number": tracking_number,
                "status": status,
                "created_at": now.isoformat(),
                "metadata": metadata or {}
            }

            async with self.db:
                await self.db.insert_into(
                    self.shipments_table,
                    [shipment_data],
                    schema=self.schema
                )

            return await self.get_shipment(shipment_id)

        except Exception as e:
            logger.error(f"Failed to create shipment: {e}")
            raise

    async def get_shipment(self, shipment_id: str) -> Optional[Dict[str, Any]]:
        """Get shipment by ID"""
        try:
            query = f'SELECT * FROM "{self.schema}".{self.shipments_table} WHERE shipment_id = $1'

            async with self.db:
                result = await self.db.query_row(query, [shipment_id], schema=self.schema)

            return self._normalize_shipment(result) if result else None

        except Exception as e:
            logger.error(f"Failed to get shipment {shipment_id}: {e}")
            raise

    async def get_shipment_by_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get shipment by order ID"""
        try:
            query = f'SELECT * FROM "{self.schema}".{self.shipments_table} WHERE order_id = $1 ORDER BY created_at DESC LIMIT 1'

            async with self.db:
                result = await self.db.query_row(query, [order_id], schema=self.schema)

            return self._normalize_shipment(result) if result else None

        except Exception as e:
            logger.error(f"Failed to get shipment for order {order_id}: {e}")
            raise

    async def get_shipment_by_tracking(self, tracking_number: str) -> Optional[Dict[str, Any]]:
        """Get shipment by tracking number"""
        try:
            query = f'SELECT * FROM "{self.schema}".{self.shipments_table} WHERE tracking_number = $1'

            async with self.db:
                result = await self.db.query_row(query, [tracking_number], schema=self.schema)

            return self._normalize_shipment(result) if result else None

        except Exception as e:
            logger.error(f"Failed to get shipment by tracking {tracking_number}: {e}")
            raise

    async def update_shipment(
        self,
        shipment_id: str,
        status: Optional[str] = None,
        carrier: Optional[str] = None,
        tracking_number: Optional[str] = None,
        label_url: Optional[str] = None,
        estimated_delivery: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Update shipment"""
        try:
            now = datetime.now(timezone.utc)
            updates = []
            params = []
            param_count = 0

            if status:
                param_count += 1
                updates.append(f"status = ${param_count}")
                params.append(status)
                # Set lifecycle timestamps based on status
                if status == "label_purchased":
                    param_count += 1
                    updates.append(f"label_created_at = ${param_count}")
                    params.append(now.isoformat())
                elif status == "in_transit":
                    param_count += 1
                    updates.append(f"shipped_at = ${param_count}")
                    params.append(now.isoformat())
                elif status == "delivered":
                    param_count += 1
                    updates.append(f"delivered_at = ${param_count}")
                    params.append(now.isoformat())

            if carrier:
                param_count += 1
                updates.append(f"carrier = ${param_count}")
                params.append(carrier)

            if tracking_number:
                param_count += 1
                updates.append(f"tracking_number = ${param_count}")
                params.append(tracking_number)

            if label_url:
                param_count += 1
                updates.append(f"label_url = ${param_count}")
                params.append(label_url)

            if estimated_delivery:
                param_count += 1
                updates.append(f"estimated_delivery = ${param_count}")
                params.append(estimated_delivery.isoformat())

            if metadata:
                param_count += 1
                updates.append(f"metadata = ${param_count}")
                params.append(metadata)

            if not updates:
                return await self.get_shipment(shipment_id)

            param_count += 1
            params.append(shipment_id)

            query = f'''
                UPDATE "{self.schema}".{self.shipments_table}
                SET {", ".join(updates)}
                WHERE shipment_id = ${param_count}
            '''

            async with self.db:
                await self.db.execute(query, params, schema=self.schema)

            return await self.get_shipment(shipment_id)

        except Exception as e:
            logger.error(f"Failed to update shipment {shipment_id}: {e}")
            raise

    async def create_label(
        self,
        shipment_id: str,
        carrier: str,
        tracking_number: str,
        label_url: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Create shipping label for a shipment"""
        return await self.update_shipment(
            shipment_id=shipment_id,
            status="label_purchased",
            carrier=carrier,
            tracking_number=tracking_number,
            label_url=label_url
        )

    async def cancel_shipment(
        self,
        shipment_id: str,
        reason: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Cancel a shipment"""
        try:
            now = datetime.now(timezone.utc)
            query = f'''
                UPDATE "{self.schema}".{self.shipments_table}
                SET status = $1, canceled_at = $2, cancellation_reason = $3
                WHERE shipment_id = $4
            '''

            params = ["failed", now.isoformat(), reason or "manual_cancellation", shipment_id]

            async with self.db:
                await self.db.execute(query, params, schema=self.schema)

            return await self.get_shipment(shipment_id)

        except Exception as e:
            logger.error(f"Failed to cancel shipment {shipment_id}: {e}")
            raise

    async def list_shipments(
        self,
        limit: int = 50,
        offset: int = 0,
        order_id: Optional[str] = None,
        user_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List shipments with filtering"""
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
                SELECT * FROM "{self.schema}".{self.shipments_table}
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT {limit} OFFSET {offset}
            '''

            async with self.db:
                results = await self.db.query(query, params, schema=self.schema)

            return [self._normalize_shipment(r) for r in (results or [])]

        except Exception as e:
            logger.error(f"Failed to list shipments: {e}")
            raise

    def _normalize_shipment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize shipment data from database"""
        if not data:
            return None

        # Handle JSONB fields
        items = data.get("items", [])
        if isinstance(items, str):
            import json
            items = json.loads(items)

        shipping_address = data.get("shipping_address")
        if isinstance(shipping_address, str):
            import json
            shipping_address = json.loads(shipping_address)

        metadata = data.get("metadata", {})
        if isinstance(metadata, str):
            import json
            metadata = json.loads(metadata)

        return {
            "shipment_id": data["shipment_id"],
            "order_id": data["order_id"],
            "user_id": data.get("user_id"),
            "items": items,
            "shipping_address": shipping_address,
            "carrier": data.get("carrier"),
            "tracking_number": data.get("tracking_number"),
            "label_url": data.get("label_url"),
            "estimated_delivery": data.get("estimated_delivery"),
            "status": data.get("status", "created"),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "label_created_at": data.get("label_created_at"),
            "shipped_at": data.get("shipped_at"),
            "delivered_at": data.get("delivered_at"),
            "canceled_at": data.get("canceled_at"),
            "cancellation_reason": data.get("cancellation_reason"),
            "metadata": metadata
        }
