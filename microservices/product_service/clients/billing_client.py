"""
Billing Service Client

Client for product_service to interact with billing_service.
Used for recording usage and querying billing records.
"""

import os
import sys
from typing import Optional, Dict, Any, List
from datetime import datetime

# Add parent directories to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from microservices.billing_service.client import BillingServiceClient

import logging

logger = logging.getLogger(__name__)


class BillingClient:
    """
    Wrapper client for Billing Service calls from Product Service.

    Provides product-specific convenience methods while delegating
    to the actual BillingServiceClient. Fail-open on all errors.
    """

    def __init__(self, base_url: str = None):
        self._client = BillingServiceClient(base_url=base_url)

    async def close(self):
        """Close HTTP client"""
        await self._client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def record_product_usage(
        self,
        user_id: str,
        organization_id: Optional[str],
        product_id: str,
        usage_amount: float,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        usage_details: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Record product usage via billing service.

        Returns:
            Usage record ID if successful, None otherwise.
        """
        try:
            metadata = {}
            if session_id:
                metadata["session_id"] = session_id
            if request_id:
                metadata["request_id"] = request_id
            if usage_details:
                metadata["usage_details"] = usage_details

            result = await self._client.record_usage(
                user_id=user_id,
                organization_id=organization_id or "",
                service_name="product_service",
                usage_type=product_id,
                quantity=usage_amount,
                unit="token",
                metadata=metadata,
            )
            if result:
                return result.get("billing_record_id") or result.get("id") or "recorded"
            return None
        except Exception as e:
            logger.warning(f"Failed to record usage via billing_service: {e}")
            return None

    async def get_usage_records(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        product_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get usage/billing records. Returns empty list on failure."""
        try:
            if user_id:
                result = await self._client.get_user_billing_records(
                    user_id=user_id,
                    organization_id=organization_id,
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit,
                    offset=offset,
                )
                if result:
                    return result.get("records", [])
            return []
        except Exception as e:
            logger.warning(f"Failed to get usage records from billing_service: {e}")
            return []

    async def get_usage_statistics(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        product_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get usage statistics/aggregations. Returns empty dict on failure."""
        try:
            result = await self._client.get_usage_aggregations(
                user_id=user_id,
                organization_id=organization_id,
                usage_type=product_id,
                start_date=start_date,
                end_date=end_date,
            )
            return result or {
                "total_usage": 0,
                "usage_by_product": {},
                "usage_by_date": {},
                "period": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                },
            }
        except Exception as e:
            logger.warning(f"Failed to get usage statistics from billing_service: {e}")
            return {
                "total_usage": 0,
                "usage_by_product": {},
                "usage_by_date": {},
                "period": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                },
            }

    async def health_check(self) -> bool:
        """Check Billing Service health"""
        return await self._client.health_check()


__all__ = ["BillingClient"]
