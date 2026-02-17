"""
Order Service Client

Client library for other microservices to interact with order service
"""

import httpx
from core.service_discovery import get_service_discovery
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class OrderServiceClient:
    """Order Service HTTP client"""

    def __init__(self, base_url: str = None):
        """
        Initialize Order Service client

        Args:
            base_url: Order service base URL, defaults to service discovery
        """
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Use service discovery
            try:
                sd = get_service_discovery()
                self.base_url = sd.get_service_url("order_service")
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                self.base_url = "http://localhost:8215"

        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # =============================================================================
    # Order Management
    # =============================================================================

    async def create_order(
        self,
        user_id: str,
        order_type: str,
        items: List[Dict[str, Any]],
        total_amount: float,
        currency: str = "USD",
        payment_intent_id: Optional[str] = None,
        subscription_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create new order

        Args:
            user_id: User ID
            order_type: Type of order (subscription, one_time, etc.)
            items: List of order items
            total_amount: Total order amount
            currency: Currency code (default: USD)
            payment_intent_id: Payment intent ID (optional)
            subscription_id: Subscription ID (optional)
            metadata: Additional metadata (optional)

        Returns:
            Created order data

        Example:
            >>> client = OrderServiceClient()
            >>> order = await client.create_order(
            ...     user_id="user123",
            ...     order_type="subscription",
            ...     items=[
            ...         {
            ...             "product_id": "prod_premium",
            ...             "quantity": 1,
            ...             "price": 29.99,
            ...             "name": "Premium Subscription"
            ...         }
            ...     ],
            ...     total_amount=29.99,
            ...     subscription_id="sub_123"
            ... )
        """
        try:
            payload = {
                "user_id": user_id,
                "order_type": order_type,
                "items": items,
                "total_amount": total_amount,
                "currency": currency
            }

            if payment_intent_id:
                payload["payment_intent_id"] = payment_intent_id
            if subscription_id:
                payload["subscription_id"] = subscription_id
            if metadata:
                payload["metadata"] = metadata

            response = await self.client.post(
                f"{self.base_url}/api/v1/orders",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create order: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return None

    async def get_order(
        self,
        order_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get order by ID

        Args:
            order_id: Order ID

        Returns:
            Order data

        Example:
            >>> order = await client.get_order("order_123")
            >>> print(f"Status: {order['status']}")
            >>> print(f"Total: ${order['total_amount']}")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/orders/{order_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get order: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting order: {e}")
            return None

    async def update_order(
        self,
        order_id: str,
        status: Optional[str] = None,
        items: Optional[List[Dict[str, Any]]] = None,
        total_amount: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update order

        Args:
            order_id: Order ID
            status: New status (optional)
            items: Updated items (optional)
            total_amount: Updated total (optional)
            metadata: Updated metadata (optional)

        Returns:
            Updated order data

        Example:
            >>> order = await client.update_order(
            ...     order_id="order_123",
            ...     status="processing"
            ... )
        """
        try:
            payload = {}

            if status:
                payload["status"] = status
            if items:
                payload["items"] = items
            if total_amount is not None:
                payload["total_amount"] = total_amount
            if metadata:
                payload["metadata"] = metadata

            if not payload:
                logger.warning("No update data provided")
                return None

            response = await self.client.put(
                f"{self.base_url}/api/v1/orders/{order_id}",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to update order: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error updating order: {e}")
            return None

    async def cancel_order(
        self,
        order_id: str,
        reason: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Cancel order

        Args:
            order_id: Order ID
            reason: Cancellation reason (optional)

        Returns:
            Cancelled order data

        Example:
            >>> order = await client.cancel_order(
            ...     order_id="order_123",
            ...     reason="User requested cancellation"
            ... )
        """
        try:
            payload = {}
            if reason:
                payload["reason"] = reason

            response = await self.client.post(
                f"{self.base_url}/api/v1/orders/{order_id}/cancel",
                json=payload if payload else None
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to cancel order: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return None

    async def complete_order(
        self,
        order_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Mark order as completed

        Args:
            order_id: Order ID

        Returns:
            Completed order data

        Example:
            >>> order = await client.complete_order("order_123")
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/orders/{order_id}/complete"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to complete order: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error completing order: {e}")
            return None

    # =============================================================================
    # Order Queries
    # =============================================================================

    async def list_orders(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        order_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        List orders with filters

        Args:
            user_id: Filter by user (optional)
            status: Filter by status (optional)
            order_type: Filter by order type (optional)
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of orders with pagination

        Example:
            >>> result = await client.list_orders(
            ...     user_id="user123",
            ...     status="completed",
            ...     limit=20
            ... )
            >>> for order in result['orders']:
            ...     print(f"{order['order_id']}: ${order['total_amount']}")
        """
        try:
            params = {
                "limit": limit,
                "offset": offset
            }

            if user_id:
                params["user_id"] = user_id
            if status:
                params["status"] = status
            if order_type:
                params["order_type"] = order_type

            response = await self.client.get(
                f"{self.base_url}/api/v1/orders",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list orders: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error listing orders: {e}")
            return None

    async def get_user_orders(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get user's orders

        Args:
            user_id: User ID
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of user's orders

        Example:
            >>> orders = await client.get_user_orders("user123")
            >>> for order in orders:
            ...     print(f"{order['created_at']}: ${order['total_amount']}")
        """
        try:
            params = {
                "limit": limit,
                "offset": offset
            }

            response = await self.client.get(
                f"{self.base_url}/api/v1/users/{user_id}/orders",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get user orders: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting user orders: {e}")
            return None

    async def search_orders(
        self,
        query: str,
        search_field: str = "order_id",
        limit: int = 50
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Search orders

        Args:
            query: Search query
            search_field: Field to search (order_id, user_id, email)
            limit: Maximum results

        Returns:
            List of matching orders

        Example:
            >>> orders = await client.search_orders(
            ...     query="order_123",
            ...     search_field="order_id"
            ... )
        """
        try:
            params = {
                "query": query,
                "search_field": search_field,
                "limit": limit
            }

            response = await self.client.get(
                f"{self.base_url}/api/v1/orders/search",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to search orders: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error searching orders: {e}")
            return None

    async def get_orders_by_payment(
        self,
        payment_intent_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get orders by payment intent ID

        Args:
            payment_intent_id: Payment intent ID

        Returns:
            List of orders

        Example:
            >>> orders = await client.get_orders_by_payment("pi_123")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/payments/{payment_intent_id}/orders"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get orders by payment: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting orders by payment: {e}")
            return None

    async def get_orders_by_subscription(
        self,
        subscription_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get orders by subscription ID

        Args:
            subscription_id: Subscription ID

        Returns:
            List of orders

        Example:
            >>> orders = await client.get_orders_by_subscription("sub_123")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/subscriptions/{subscription_id}/orders"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get orders by subscription: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting orders by subscription: {e}")
            return None

    # =============================================================================
    # Statistics
    # =============================================================================

    async def get_order_statistics(self) -> Optional[Dict[str, Any]]:
        """
        Get order statistics

        Returns:
            Order statistics

        Example:
            >>> stats = await client.get_order_statistics()
            >>> print(f"Total orders: {stats['total_orders']}")
            >>> print(f"Revenue: ${stats['total_revenue']}")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/orders/statistics"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get order statistics: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting order statistics: {e}")
            return None

    # =============================================================================
    # Health Check
    # =============================================================================

    async def health_check(self) -> bool:
        """
        Check service health status

        Returns:
            True if service is healthy
        """
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False


__all__ = ["OrderServiceClient"]
