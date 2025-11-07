"""
Billing Service Client

Client library for other microservices to interact with billing service
"""

import httpx
from core.service_discovery import get_service_discovery
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class BillingServiceClient:
    """Billing Service HTTP client"""

    def __init__(self, base_url: str = None):
        """
        Initialize Billing Service client

        Args:
            base_url: Billing service base URL, defaults to service discovery
        """
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Use service discovery
            try:
                sd = get_service_discovery()
                self.base_url = sd.get_service_url("billing_service")
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                self.base_url = "http://localhost:8220"

        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # =============================================================================
    # Usage Recording
    # =============================================================================

    async def record_usage(
        self,
        user_id: str,
        organization_id: str,
        service_name: str,
        usage_type: str,
        quantity: float,
        unit: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Record service usage

        Args:
            user_id: User ID
            organization_id: Organization ID
            service_name: Service name
            usage_type: Type of usage (storage, compute, api_call, etc.)
            quantity: Usage quantity
            unit: Unit of measurement (GB, hours, requests, etc.)
            metadata: Additional metadata (optional)

        Returns:
            Recorded usage data

        Example:
            >>> client = BillingServiceClient()
            >>> usage = await client.record_usage(
            ...     user_id="user123",
            ...     organization_id="org456",
            ...     service_name="storage_service",
            ...     usage_type="storage",
            ...     quantity=10.5,
            ...     unit="GB"
            ... )
        """
        try:
            payload = {
                "user_id": user_id,
                "organization_id": organization_id,
                "service_name": service_name,
                "usage_type": usage_type,
                "quantity": quantity,
                "unit": unit
            }

            if metadata:
                payload["metadata"] = metadata

            response = await self.client.post(
                f"{self.base_url}/api/v1/usage/record",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to record usage: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error recording usage: {e}")
            return None

    # =============================================================================
    # Billing Calculation & Processing
    # =============================================================================

    async def calculate_billing(
        self,
        user_id: str,
        organization_id: str,
        start_date: datetime,
        end_date: datetime,
        usage_types: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate billing for period

        Args:
            user_id: User ID
            organization_id: Organization ID
            start_date: Period start date
            end_date: Period end date
            usage_types: Specific usage types to calculate (optional)

        Returns:
            Billing calculation result

        Example:
            >>> result = await client.calculate_billing(
            ...     user_id="user123",
            ...     organization_id="org456",
            ...     start_date=datetime(2024, 1, 1),
            ...     end_date=datetime(2024, 1, 31)
            ... )
            >>> print(f"Total: ${result['total_amount']}")
        """
        try:
            payload = {
                "user_id": user_id,
                "organization_id": organization_id,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }

            if usage_types:
                payload["usage_types"] = usage_types

            response = await self.client.post(
                f"{self.base_url}/api/v1/billing/calculate",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to calculate billing: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error calculating billing: {e}")
            return None

    async def process_billing(
        self,
        user_id: str,
        organization_id: str,
        billing_period: str,
        start_date: datetime,
        end_date: datetime,
        auto_charge: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Process billing and create invoice

        Args:
            user_id: User ID
            organization_id: Organization ID
            billing_period: Billing period (monthly, quarterly, annual)
            start_date: Period start date
            end_date: Period end date
            auto_charge: Automatically charge payment method (optional)

        Returns:
            Billing record with invoice

        Example:
            >>> billing = await client.process_billing(
            ...     user_id="user123",
            ...     organization_id="org456",
            ...     billing_period="monthly",
            ...     start_date=datetime(2024, 1, 1),
            ...     end_date=datetime(2024, 1, 31),
            ...     auto_charge=True
            ... )
        """
        try:
            payload = {
                "user_id": user_id,
                "organization_id": organization_id,
                "billing_period": billing_period,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "auto_charge": auto_charge
            }

            response = await self.client.post(
                f"{self.base_url}/api/v1/billing/process",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to process billing: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error processing billing: {e}")
            return None

    # =============================================================================
    # Quota Management
    # =============================================================================

    async def check_quota(
        self,
        user_id: str,
        organization_id: str,
        resource_type: str,
        requested_quantity: float
    ) -> Optional[Dict[str, Any]]:
        """
        Check if user has quota available

        Args:
            user_id: User ID
            organization_id: Organization ID
            resource_type: Type of resource (storage, compute, api_calls, etc.)
            requested_quantity: Requested amount

        Returns:
            Quota check result with available quota

        Example:
            >>> quota = await client.check_quota(
            ...     user_id="user123",
            ...     organization_id="org456",
            ...     resource_type="storage",
            ...     requested_quantity=5.0
            ... )
            >>> if quota['has_quota']:
            ...     print("Quota available")
        """
        try:
            payload = {
                "user_id": user_id,
                "organization_id": organization_id,
                "resource_type": resource_type,
                "requested_quantity": requested_quantity
            }

            response = await self.client.post(
                f"{self.base_url}/api/v1/quota/check",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to check quota: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error checking quota: {e}")
            return None

    # =============================================================================
    # Billing Records
    # =============================================================================

    async def get_user_billing_records(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Get user's billing records

        Args:
            user_id: User ID
            organization_id: Filter by organization (optional)
            status: Filter by status (optional)
            start_date: Filter start date (optional)
            end_date: Filter end date (optional)
            limit: Maximum records
            offset: Pagination offset

        Returns:
            List of billing records

        Example:
            >>> records = await client.get_user_billing_records(
            ...     user_id="user123",
            ...     limit=10
            ... )
            >>> for record in records['records']:
            ...     print(f"{record['billing_period']}: ${record['total_amount']}")
        """
        try:
            params = {
                "limit": limit,
                "offset": offset
            }

            if organization_id:
                params["organization_id"] = organization_id
            if status:
                params["status"] = status
            if start_date:
                params["start_date"] = start_date.isoformat()
            if end_date:
                params["end_date"] = end_date.isoformat()

            response = await self.client.get(
                f"{self.base_url}/api/v1/billing/records/user/{user_id}",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get billing records: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting billing records: {e}")
            return None

    async def get_billing_record(
        self,
        billing_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get specific billing record

        Args:
            billing_id: Billing record ID

        Returns:
            Billing record details

        Example:
            >>> record = await client.get_billing_record("bill_123")
            >>> print(f"Amount: ${record['total_amount']}")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/billing/record/{billing_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get billing record: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting billing record: {e}")
            return None

    async def update_billing_status(
        self,
        billing_id: str,
        status: str,
        payment_method: Optional[str] = None,
        transaction_id: Optional[str] = None
    ) -> bool:
        """
        Update billing record status

        Args:
            billing_id: Billing record ID
            status: New status (paid, failed, pending, etc.)
            payment_method: Payment method (optional)
            transaction_id: Transaction ID (optional)

        Returns:
            True if successful

        Example:
            >>> success = await client.update_billing_status(
            ...     billing_id="bill_123",
            ...     status="paid",
            ...     transaction_id="txn_456"
            ... )
        """
        try:
            payload = {"status": status}

            if payment_method:
                payload["payment_method"] = payment_method
            if transaction_id:
                payload["transaction_id"] = transaction_id

            response = await self.client.put(
                f"{self.base_url}/api/v1/billing/record/{billing_id}/status",
                json=payload
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to update billing status: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error updating billing status: {e}")
            return False

    # =============================================================================
    # Usage Aggregations
    # =============================================================================

    async def get_usage_aggregations(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        service_name: Optional[str] = None,
        usage_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        group_by: str = "day"
    ) -> Optional[Dict[str, Any]]:
        """
        Get usage aggregations

        Args:
            user_id: Filter by user (optional)
            organization_id: Filter by organization (optional)
            service_name: Filter by service (optional)
            usage_type: Filter by usage type (optional)
            start_date: Start date (optional)
            end_date: End date (optional)
            group_by: Grouping (day, week, month)

        Returns:
            Aggregated usage data

        Example:
            >>> agg = await client.get_usage_aggregations(
            ...     organization_id="org456",
            ...     usage_type="storage",
            ...     group_by="month"
            ... )
        """
        try:
            params = {"group_by": group_by}

            if user_id:
                params["user_id"] = user_id
            if organization_id:
                params["organization_id"] = organization_id
            if service_name:
                params["service_name"] = service_name
            if usage_type:
                params["usage_type"] = usage_type
            if start_date:
                params["start_date"] = start_date.isoformat()
            if end_date:
                params["end_date"] = end_date.isoformat()

            response = await self.client.get(
                f"{self.base_url}/api/v1/usage/aggregations",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get usage aggregations: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting usage aggregations: {e}")
            return None

    # =============================================================================
    # Service Information
    # =============================================================================

    async def get_service_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get billing service statistics

        Returns:
            Service statistics

        Example:
            >>> stats = await client.get_service_stats()
            >>> print(f"Total billing records: {stats['total_billing_records']}")
        """
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/stats")
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get service stats: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting service stats: {e}")
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


__all__ = ["BillingServiceClient"]
