"""
Product Service Client for Billing Service

Handles product/usage-related operations: record usage, pricing info
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ProductClient:
    """Client for communicating with Product Service"""

    def __init__(self):
        """Initialize Product Service client"""
        try:
            import os
            import sys

            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

            from microservices.product_service.client import ProductServiceClient

            self.client = ProductServiceClient()
            logger.info("✅ ProductClient initialized with ProductServiceClient")
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize ProductServiceClient: {e}")
            self.client = None

    async def record_usage(
        self,
        user_id: str,
        service_type: str,
        usage_type: str,
        quantity: Decimal,
        unit: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Record usage to Product Service

        Args:
            user_id: User ID
            service_type: Service type (e.g., 'storage', 'ai_service')
            usage_type: Usage type (e.g., 'api_call', 'storage_gb')
            quantity: Usage quantity
            unit: Usage unit
            metadata: Additional metadata

        Returns:
            Usage record ID or None if failed
        """
        try:
            if not self.client:
                logger.warning("ProductServiceClient not available")
                return None

            result = await self.client.record_usage(
                user_id=user_id,
                service_type=service_type,
                usage_type=usage_type,
                quantity=float(quantity),
                unit=unit,
                metadata=metadata or {},
            )

            if result and result.get("success"):
                return result.get("usage_record_id")

            return None

        except Exception as e:
            logger.error(f"Failed to record usage for user {user_id}: {e}")
            return None

    async def get_pricing(
        self, service_type: str, usage_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get pricing information for a service/usage type

        Args:
            service_type: Service type
            usage_type: Usage type

        Returns:
            Pricing info dict or None if failed
        """
        try:
            if not self.client:
                logger.warning("ProductServiceClient not available")
                return None

            result = await self.client.get_pricing(
                service_type=service_type, usage_type=usage_type
            )

            return result

        except Exception as e:
            logger.error(f"Failed to get pricing for {service_type}/{usage_type}: {e}")
            return None

    async def get_user_quota(
        self, user_id: str, service_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get user's quota/subscription info for a service

        Args:
            user_id: User ID
            service_type: Service type

        Returns:
            Quota info dict or None if failed
        """
        try:
            if not self.client:
                logger.warning("ProductServiceClient not available")
                return None

            result = await self.client.get_user_quota(
                user_id=user_id, service_type=service_type
            )

            return result

        except Exception as e:
            logger.error(f"Failed to get quota for user {user_id}: {e}")
            return None

    async def get_product_pricing(
        self, product_id: str, user_id: str = None, subscription_id: Optional[str] = None, currency: str = "USD"
    ) -> Optional[Dict[str, Any]]:
        """
        Get pricing information for a specific product

        Args:
            product_id: Product ID
            user_id: User ID (kept for API compatibility, not used by ProductServiceClient)
            subscription_id: Optional subscription ID (kept for API compatibility, not used by ProductServiceClient)
            currency: Currency code (default: USD)

        Returns:
            Pricing info dict or None if failed
        """
        try:
            if not self.client:
                logger.warning("ProductServiceClient not available")
                return None

            # ProductServiceClient.get_product_pricing only accepts product_id and currency
            result = await self.client.get_product_pricing(
                product_id=product_id,
                currency=currency
            )

            return result

        except Exception as e:
            logger.error(f"Failed to get product pricing for {product_id}: {e}")
            return None
