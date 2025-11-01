"""
Usage Tracking Client Example

Professional client for product usage tracking and analytics operations.
"""

import httpx
import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class UsageRecord:
    """Usage record information"""
    usage_id: str
    user_id: str
    product_id: str
    usage_amount: float
    total_cost: float
    usage_timestamp: str


class UsageTrackingClient:
    """Professional Usage Tracking Service Client"""

    def __init__(
        self,
        base_url: str = "http://localhost:8215",
        timeout: float = 10.0,
        max_retries: int = 3
    ):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.client: Optional[httpx.AsyncClient] = None
        self.request_count = 0
        self.error_count = 0

    async def __aenter__(self):
        limits = httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100,
            keepalive_expiry=60.0
        )
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout),
            limits=limits,
            headers={
                "User-Agent": "usage-tracking-client/1.0",
                "Accept": "application/json"
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with retry logic"""
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                self.request_count += 1
                response = await self.client.request(method, endpoint, **kwargs)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                last_exception = e
                if 400 <= e.response.status_code < 500:
                    self.error_count += 1
                    try:
                        error_detail = e.response.json()
                        raise Exception(error_detail.get("detail", str(e)))
                    except:
                        raise Exception(str(e))
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.2 * (2 ** attempt))
            except Exception as e:
                last_exception = e
                self.error_count += 1
                raise
        self.error_count += 1
        raise Exception(f"Request failed after {self.max_retries} attempts: {last_exception}")

    async def record_usage(
        self,
        user_id: str,
        product_id: str,
        usage_amount: float,
        organization_id: Optional[str] = None,
        subscription_id: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        usage_details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Record product usage"""
        payload = {
            "user_id": user_id,
            "product_id": product_id,
            "usage_amount": usage_amount
        }
        if organization_id:
            payload["organization_id"] = organization_id
        if subscription_id:
            payload["subscription_id"] = subscription_id
        if session_id:
            payload["session_id"] = session_id
        if request_id:
            payload["request_id"] = request_id
        if usage_details:
            payload["usage_details"] = usage_details

        return await self._make_request(
            "POST",
            "/api/v1/usage/record",
            json=payload
        )

    async def get_usage_records(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        subscription_id: Optional[str] = None,
        product_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get usage records with filtering"""
        params = {"limit": limit, "offset": offset}
        if user_id:
            params["user_id"] = user_id
        if organization_id:
            params["organization_id"] = organization_id
        if subscription_id:
            params["subscription_id"] = subscription_id
        if product_id:
            params["product_id"] = product_id

        return await self._make_request(
            "GET",
            "/api/v1/usage/records",
            params=params
        )

    async def get_usage_statistics(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        product_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get usage statistics"""
        params = {}
        if user_id:
            params["user_id"] = user_id
        if organization_id:
            params["organization_id"] = organization_id
        if product_id:
            params["product_id"] = product_id
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()

        return await self._make_request(
            "GET",
            "/api/v1/statistics/usage",
            params=params
        )

    def get_metrics(self) -> Dict[str, Any]:
        """Get client performance metrics"""
        return {
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate": self.error_count / self.request_count if self.request_count > 0 else 0
        }


# Example Usage
async def main():
    print("=" * 70)
    print("Usage Tracking Client Examples")
    print("=" * 70)

    async with UsageTrackingClient() as client:
        test_user_id = "example_user_123"
        test_product_id = "gpt-4"

        # Example 1: Record Simple Usage
        print("\n1. Record Product Usage")
        print("-" * 70)
        print("⚠ This example requires a valid user_id from account service")
        print("Example usage recording:")
        try:
            # Uncomment to test with valid user:
            # result = await client.record_usage(
            #     user_id=test_user_id,
            #     product_id=test_product_id,
            #     usage_amount=1500.0,  # 1500 tokens
            #     usage_details={
            #         "model": "gpt-4",
            #         "tokens_input": 1000,
            #         "tokens_output": 500
            #     }
            # )
            # print(f"✓ Usage recorded: {result['usage_record_id']}")
            # print(f"  Success: {result['success']}")
            # print(f"  Amount: {result['recorded_amount']}")
            print("Example payload structure:")
            print({
                "user_id": "valid_user_id",
                "product_id": "gpt-4",
                "usage_amount": 1500.0,
                "usage_details": {"tokens_input": 1000, "tokens_output": 500}
            })
        except Exception as e:
            print(f"⚠ {e}")

        # Example 2: Record Usage with Organization
        print("\n2. Record Organization Usage")
        print("-" * 70)
        print("For team/enterprise usage tracking:")
        print({
            "user_id": "user_123",
            "product_id": "gpt-4",
            "usage_amount": 5000.0,
            "organization_id": "org_456",
            "subscription_id": "sub_789"
        })

        # Example 3: Get Usage Records
        print("\n3. Get Usage Records")
        print("-" * 70)
        try:
            records = await client.get_usage_records(
                user_id=test_user_id,
                limit=10
            )
            if records:
                print(f"✓ Found {len(records)} usage records:")
                for record in records[:3]:
                    print(f"  - Product: {record.get('product_id', 'N/A')}")
                    print(f"    Amount: {record.get('usage_amount', 0)}")
                    print(f"    Timestamp: {record.get('usage_timestamp', 'N/A')}")
            else:
                print(f"✓ No usage records found for user {test_user_id}")
        except Exception as e:
            print(f"⚠ {e}")

        # Example 4: Get Usage Statistics
        print("\n4. Get Usage Statistics")
        print("-" * 70)
        try:
            stats = await client.get_usage_statistics(user_id=test_user_id)
            print("✓ Usage Statistics:")
            if stats.get('total_statistics'):
                total = stats['total_statistics']
                print(f"  Total records: {total.get('total_records', 0)}")
                print(f"  Total usage: {total.get('total_usage', 0)}")
                print(f"  Average usage: {total.get('avg_usage', 0):.2f}")

            if stats.get('product_statistics'):
                print("  By product:")
                for prod_stat in stats['product_statistics'][:3]:
                    print(f"    - {prod_stat['product_id']}: {prod_stat['total_usage']}")
        except Exception as e:
            print(f"⚠ {e}")

        # Example 5: Batch Usage Recording
        print("\n5. Batch Usage Recording")
        print("-" * 70)
        print("For high-throughput scenarios:")
        print("""
# Record multiple usage events in parallel
usage_events = [
    {"user_id": "user_1", "product_id": "gpt-4", "usage_amount": 1000},
    {"user_id": "user_2", "product_id": "gpt-3.5-turbo", "usage_amount": 2000},
    {"user_id": "user_3", "product_id": "text-embedding", "usage_amount": 500},
]

tasks = [client.record_usage(**event) for event in usage_events]
results = await asyncio.gather(*tasks, return_exceptions=True)
        """)

        # Example 6: Time-based Analytics
        print("\n6. Time-based Usage Analytics")
        print("-" * 70)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)  # Last 30 days

        try:
            stats = await client.get_usage_statistics(
                user_id=test_user_id,
                start_date=start_date,
                end_date=end_date
            )
            print(f"✓ Usage for last 30 days:")
            if stats.get('total_statistics'):
                print(f"  Total usage: {stats['total_statistics'].get('total_usage', 0)}")
        except Exception as e:
            print(f"⚠ {e}")

        # Example 7: Product-specific Analytics
        print("\n7. Product-specific Usage")
        print("-" * 70)
        print("Track usage for specific products:")
        try:
            stats = await client.get_usage_statistics(
                user_id=test_user_id,
                product_id=test_product_id
            )
            print(f"✓ Usage statistics for {test_product_id}")
        except Exception as e:
            print(f"⚠ {e}")

        # Example 8: Best Practices
        print("\n8. Best Practices")
        print("-" * 70)
        print("✓ Record usage as close to actual usage time as possible")
        print("✓ Include detailed usage_details for debugging")
        print("✓ Use session_id and request_id for traceability")
        print("✓ Batch record usage events for better performance")
        print("✓ Monitor usage patterns to detect anomalies")
        print("✓ Implement retry logic for failed recordings")

        # Show Client Metrics
        print("\n9. Client Performance Metrics")
        print("-" * 70)
        metrics = client.get_metrics()
        print(f"Total requests: {metrics['total_requests']}")
        print(f"Total errors: {metrics['total_errors']}")
        print(f"Error rate: {metrics['error_rate']:.2%}")

        # Example 9: Integration Pattern
        print("\n10. Integration Pattern Example")
        print("-" * 70)
        print("""
# In your application:
async def track_api_usage(user_id: str, endpoint: str, tokens_used: int):
    async with UsageTrackingClient() as client:
        result = await client.record_usage(
            user_id=user_id,
            product_id="api_gateway",
            usage_amount=tokens_used,
            usage_details={
                "endpoint": endpoint,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        if result['success']:
            logger.info(f"Usage recorded: {tokens_used} tokens")
        else:
            logger.error(f"Failed to record usage: {result['message']}")
        """)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())
