"""
Subscription Service Client Example

Professional client for subscription management operations with performance optimizations.
"""

import httpx
import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ServicePlan:
    """Service plan information"""
    plan_id: str
    name: str
    plan_tier: str
    monthly_price: float
    yearly_price: float
    included_credits: float


@dataclass
class Subscription:
    """Subscription information"""
    subscription_id: str
    user_id: str
    plan_id: str
    plan_tier: str
    status: str
    billing_cycle: str
    current_period_start: str
    current_period_end: str


class SubscriptionClient:
    """Professional Subscription Service Client"""

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
                "User-Agent": "subscription-client/1.0",
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

    async def create_subscription(
        self,
        user_id: str,
        plan_id: str,
        billing_cycle: str = "monthly",
        organization_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new subscription"""
        payload = {
            "user_id": user_id,
            "plan_id": plan_id,
            "billing_cycle": billing_cycle
        }
        if organization_id:
            payload["organization_id"] = organization_id
        if metadata:
            payload["metadata"] = metadata

        return await self._make_request(
            "POST",
            "/api/v1/subscriptions",
            json=payload
        )

    async def get_user_subscriptions(
        self,
        user_id: str,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get user's subscriptions"""
        params = {}
        if status:
            params["status"] = status

        return await self._make_request(
            "GET",
            f"/api/v1/subscriptions/user/{user_id}",
            params=params
        )

    async def get_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Get subscription details"""
        return await self._make_request(
            "GET",
            f"/api/v1/subscriptions/{subscription_id}"
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
    print("Subscription Service Client Examples")
    print("=" * 70)

    async with SubscriptionClient() as client:
        # Note: These examples require a valid user in the account service
        # For testing purposes, we'll demonstrate the API structure

        # Example 1: Create Subscription (requires valid user)
        print("\n1. Create Subscription")
        print("-" * 70)
        print("⚠ This example requires a valid user_id from account service")
        print("Example payload:")
        print({
            "user_id": "valid_user_id_here",
            "plan_id": "pro-plan",
            "billing_cycle": "monthly",
            "metadata": {"source": "web_signup"}
        })

        # Uncomment to test with a valid user:
        # try:
        #     subscription = await client.create_subscription(
        #         user_id="your_user_id",
        #         plan_id="pro-plan",
        #         billing_cycle="monthly",
        #         metadata={"source": "example"}
        #     )
        #     print(f"✓ Subscription created: {subscription['subscription_id']}")
        #     print(f"  Plan: {subscription['plan_id']}")
        #     print(f"  Status: {subscription['status']}")
        # except Exception as e:
        #     print(f"✗ Error: {e}")

        # Example 2: Get User Subscriptions
        print("\n2. Get User Subscriptions")
        print("-" * 70)
        test_user_id = "example_user_123"
        try:
            subscriptions = await client.get_user_subscriptions(test_user_id)
            if subscriptions:
                print(f"✓ Found {len(subscriptions)} subscription(s):")
                for sub in subscriptions:
                    print(f"  - {sub['plan_id']} ({sub['status']})")
            else:
                print(f"✓ No subscriptions found for user {test_user_id}")
        except Exception as e:
            print(f"⚠ {e}")

        # Example 3: Get Subscription by ID
        print("\n3. Get Subscription Details")
        print("-" * 70)
        print("Example: Fetch subscription details by ID")
        print("Usage: await client.get_subscription('subscription_id')")

        # Example 4: Get Active Subscriptions Only
        print("\n4. Filter Subscriptions by Status")
        print("-" * 70)
        try:
            active_subs = await client.get_user_subscriptions(
                test_user_id,
                status="active"
            )
            print(f"✓ Active subscriptions: {len(active_subs)}")
        except Exception as e:
            print(f"⚠ {e}")

        # Example 5: Subscription Lifecycle Management
        print("\n5. Subscription Lifecycle")
        print("-" * 70)
        print("Typical subscription lifecycle:")
        print("  1. Create subscription (active)")
        print("  2. User uses service")
        print("  3. Billing period renews automatically")
        print("  4. User can upgrade/downgrade plans")
        print("  5. User can cancel (ends at period end)")

        # Example 6: Best Practices
        print("\n6. Best Practices")
        print("-" * 70)
        print("✓ Always validate user_id via account service first")
        print("✓ Check subscription status before allowing access")
        print("✓ Handle subscription expiration gracefully")
        print("✓ Provide clear upgrade/downgrade paths")
        print("✓ Send renewal reminders before expiration")

        # Show Client Metrics
        print("\n7. Client Performance Metrics")
        print("-" * 70)
        metrics = client.get_metrics()
        print(f"Total requests: {metrics['total_requests']}")
        print(f"Total errors: {metrics['total_errors']}")
        print(f"Error rate: {metrics['error_rate']:.2%}")

        # Example 7: Integration Pattern
        print("\n8. Integration Pattern Example")
        print("-" * 70)
        print("""
# In your application:
async def ensure_subscription(user_id: str, plan_id: str):
    async with SubscriptionClient() as client:
        # Check existing subscriptions
        subscriptions = await client.get_user_subscriptions(user_id)
        active = [s for s in subscriptions if s['status'] == 'active']

        if not active:
            # Create new subscription
            subscription = await client.create_subscription(
                user_id=user_id,
                plan_id=plan_id
            )
            return subscription
        else:
            return active[0]
        """)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())
