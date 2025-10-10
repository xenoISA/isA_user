"""
Order Repository

Data access layer for order management operations using Supabase.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid
import logging
from decimal import Decimal

from core.database.supabase_client import get_supabase_client
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
    
    Handles all database operations for orders using Supabase client.
    """
    
    def __init__(self):
        self.client = get_supabase_client()
        self.orders_table = "orders"
        
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
                "order_type": order_type.value,
                "status": OrderStatus.PENDING.value,
                "total_amount": float(total_amount),
                "currency": currency,
                "payment_status": PaymentStatus.PENDING.value,
                "payment_intent_id": payment_intent_id,
                "subscription_id": subscription_id,
                "wallet_id": wallet_id,
                "items": items or [],
                "metadata": metadata or {},
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "expires_at": expires_at.isoformat() if expires_at else None
            }
            
            result = self.client.table(self.orders_table).insert(order_data).execute()
            
            if result.data:
                return self._dict_to_order(result.data[0])
            else:
                raise Exception("Failed to create order")
                
        except Exception as e:
            logger.error(f"Failed to create order: {e}")
            raise
            
    async def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        try:
            result = self.client.table(self.orders_table).select("*").eq("order_id", order_id).execute()
            
            if result.data:
                return self._dict_to_order(result.data[0])
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
                update_data["metadata"] = metadata
            if completed_at:
                update_data["completed_at"] = completed_at.isoformat()
                
            result = self.client.table(self.orders_table).update(update_data).eq("order_id", order_id).execute()
            
            if result.data:
                return self._dict_to_order(result.data[0])
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
            query = self.client.table(self.orders_table).select("*")
            
            if user_id:
                query = query.eq("user_id", user_id)
            if order_type:
                query = query.eq("order_type", order_type.value)
            if status:
                query = query.eq("status", status.value)
            if payment_status:
                query = query.eq("payment_status", payment_status.value)
                
            result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
            
            return [self._dict_to_order(order_data) for order_data in result.data]
            
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
            # Simple search by order_id or user_id
            search_query = self.client.table(self.orders_table).select("*")
            
            if user_id:
                search_query = search_query.eq("user_id", user_id)
                
            # Search in order_id or metadata
            result = search_query.or_(f"order_id.ilike.%{query}%,metadata->>description.ilike.%{query}%").limit(limit).execute()
            
            return [self._dict_to_order(order_data) for order_data in result.data]
            
        except Exception as e:
            logger.error(f"Failed to search orders: {e}")
            raise
            
    async def get_orders_by_payment_intent(self, payment_intent_id: str) -> List[Order]:
        """Get orders by payment intent ID"""
        try:
            result = self.client.table(self.orders_table).select("*").eq("payment_intent_id", payment_intent_id).execute()
            
            return [self._dict_to_order(order_data) for order_data in result.data]
            
        except Exception as e:
            logger.error(f"Failed to get orders by payment intent {payment_intent_id}: {e}")
            raise
            
    async def get_orders_by_subscription(self, subscription_id: str) -> List[Order]:
        """Get orders by subscription ID"""
        try:
            result = self.client.table(self.orders_table).select("*").eq("subscription_id", subscription_id).execute()
            
            return [self._dict_to_order(order_data) for order_data in result.data]
            
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
            total_result = self.client.table(self.orders_table).select("*", count="exact").execute()
            total_orders = total_result.count
            
            # Get orders by status
            status_stats = {}
            for status in OrderStatus:
                status_result = self.client.table(self.orders_table).select("*", count="exact").eq("status", status.value).execute()
                status_stats[status.value] = status_result.count
                
            # Get orders by type
            type_stats = {}
            for order_type in OrderType:
                type_result = self.client.table(self.orders_table).select("*", count="exact").eq("order_type", order_type.value).execute()
                type_stats[order_type.value] = type_result.count
                
            # Get revenue (completed orders only)
            revenue_result = self.client.table(self.orders_table).select("total_amount,currency").eq("status", OrderStatus.COMPLETED.value).execute()
            
            total_revenue = Decimal(0)
            revenue_by_currency = {}
            
            for order in revenue_result.data:
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
            items=data.get("items", []),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"].replace('Z', '+00:00')),
            updated_at=datetime.fromisoformat(data["updated_at"].replace('Z', '+00:00')),
            completed_at=datetime.fromisoformat(data["completed_at"].replace('Z', '+00:00')) if data.get("completed_at") else None,
            expires_at=datetime.fromisoformat(data["expires_at"].replace('Z', '+00:00')) if data.get("expires_at") else None
        )