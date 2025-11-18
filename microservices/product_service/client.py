"""
Product Service Client

Client library for other microservices to interact with product service
"""

import httpx
from core.service_discovery import get_service_discovery
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class ProductServiceClient:
    """Product Service HTTP client"""

    def __init__(self, base_url: str = None):
        """
        Initialize Product Service client

        Args:
            base_url: Product service base URL, defaults to service discovery
        """
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Use service discovery
            try:
                sd = get_service_discovery()
                self.base_url = sd.get_service_url("product_service")
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                self.base_url = "http://localhost:8210"

        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # =============================================================================
    # Product Catalog
    # =============================================================================

    async def get_categories(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get product categories

        Returns:
            List of categories

        Example:
            >>> categories = await client.get_categories()
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/categories"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get categories: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            return None

    async def list_products(
        self,
        category: Optional[str] = None,
        active_only: bool = True
    ) -> Optional[List[Dict[str, Any]]]:
        """
        List products

        Args:
            category: Filter by category (optional)
            active_only: Show only active products (default: True)

        Returns:
            List of products

        Example:
            >>> products = await client.list_products(category="storage")
        """
        try:
            params = {"active_only": active_only}
            if category:
                params["category"] = category

            response = await self.client.get(
                f"{self.base_url}/api/v1/products",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list products: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error listing products: {e}")
            return None

    async def get_product(
        self,
        product_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get product details

        Args:
            product_id: Product ID

        Returns:
            Product details

        Example:
            >>> product = await client.get_product("prod_storage_1tb")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/products/{product_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get product: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting product: {e}")
            return None

    async def get_product_pricing(
        self,
        product_id: str,
        currency: str = "USD"
    ) -> Optional[Dict[str, Any]]:
        """
        Get product pricing

        Args:
            product_id: Product ID
            currency: Currency code (default: USD)

        Returns:
            Product pricing

        Example:
            >>> pricing = await client.get_product_pricing("prod_storage_1tb")
        """
        try:
            params = {"currency": currency}

            response = await self.client.get(
                f"{self.base_url}/api/v1/product/products/{product_id}/pricing",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get product pricing: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting product pricing: {e}")
            return None

    async def get_product_availability(
        self,
        product_id: str,
        region: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get product availability

        Args:
            product_id: Product ID
            region: Region code (optional)

        Returns:
            Product availability

        Example:
            >>> availability = await client.get_product_availability("prod_storage_1tb")
        """
        try:
            params = {}
            if region:
                params["region"] = region

            response = await self.client.get(
                f"{self.base_url}/api/v1/products/{product_id}/availability",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get product availability: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting product availability: {e}")
            return None

    # =============================================================================
    # User Subscriptions
    # =============================================================================

    async def get_user_subscriptions(
        self,
        user_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get user product subscriptions

        Args:
            user_id: User ID

        Returns:
            List of subscriptions

        Example:
            >>> subscriptions = await client.get_user_subscriptions("user123")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/subscriptions/user/{user_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get user subscriptions: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting user subscriptions: {e}")
            return None

    async def get_subscription(
        self,
        subscription_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get subscription details

        Args:
            subscription_id: Subscription ID

        Returns:
            Subscription details

        Example:
            >>> subscription = await client.get_subscription("sub123")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/subscriptions/{subscription_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get subscription: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting subscription: {e}")
            return None

    async def create_subscription(
        self,
        user_id: str,
        product_id: str,
        quantity: int = 1,
        auto_renew: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Create product subscription

        Args:
            user_id: User ID
            product_id: Product ID
            quantity: Quantity (default: 1)
            auto_renew: Auto renew (default: True)

        Returns:
            Created subscription

        Example:
            >>> subscription = await client.create_subscription(
            ...     user_id="user123",
            ...     product_id="prod_storage_1tb"
            ... )
        """
        try:
            payload = {
                "user_id": user_id,
                "product_id": product_id,
                "quantity": quantity,
                "auto_renew": auto_renew
            }

            response = await self.client.post(
                f"{self.base_url}/api/v1/subscriptions",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create subscription: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            return None

    # =============================================================================
    # Usage Tracking
    # =============================================================================

    async def record_usage(
        self,
        user_id: str,
        product_id: str,
        usage_amount: float,
        usage_unit: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Record product usage

        Args:
            user_id: User ID
            product_id: Product ID
            usage_amount: Usage amount
            usage_unit: Usage unit (e.g., GB, requests, API_calls)
            metadata: Additional metadata (optional)

        Returns:
            True if successful

        Example:
            >>> success = await client.record_usage(
            ...     user_id="user123",
            ...     product_id="prod_storage",
            ...     usage_amount=5.2,
            ...     usage_unit="GB"
            ... )
        """
        try:
            payload = {
                "user_id": user_id,
                "product_id": product_id,
                "usage_amount": usage_amount,
                "usage_unit": usage_unit
            }

            if metadata:
                payload["metadata"] = metadata

            response = await self.client.post(
                f"{self.base_url}/api/v1/usage/record",
                json=payload
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to record usage: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error recording usage: {e}")
            return False

    async def get_usage_records(
        self,
        user_id: Optional[str] = None,
        product_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get usage records

        Args:
            user_id: Filter by user ID (optional)
            product_id: Filter by product ID (optional)
            start_date: Start date filter (optional)
            end_date: End date filter (optional)

        Returns:
            List of usage records

        Example:
            >>> records = await client.get_usage_records(user_id="user123")
        """
        try:
            params = {}
            if user_id:
                params["user_id"] = user_id
            if product_id:
                params["product_id"] = product_id
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date

            response = await self.client.get(
                f"{self.base_url}/api/v1/usage/records",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get usage records: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting usage records: {e}")
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


__all__ = ["ProductServiceClient"]
