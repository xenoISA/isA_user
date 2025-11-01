"""
Account Service Client Example

Professional client for account management operations with caching and performance optimizations.
"""

import httpx
import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
import time

logger = logging.getLogger(__name__)


@dataclass
class AccountProfile:
    """Account profile data"""
    user_id: str
    auth0_id: Optional[str]
    email: str
    name: str
    subscription_status: str
    credits_remaining: float
    credits_total: float
    is_active: bool
    preferences: Dict[str, Any]
    created_at: str
    updated_at: str


@dataclass
class AccountSummary:
    """Account summary data (for lists)"""
    user_id: str
    email: str
    name: str
    subscription_status: str
    is_active: bool
    created_at: str


class AccountClient:
    """Professional Account Service Client"""

    def __init__(
        self,
        base_url: str = "http://localhost:8202",
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
                "User-Agent": "account-client/1.0",
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

    async def ensure_account(
        self,
        auth0_id: str,
        email: str,
        name: str,
        subscription_plan: str = "free"
    ) -> AccountProfile:
        """Ensure account exists, create if needed"""
        result = await self._make_request(
            "POST",
            "/api/v1/accounts/ensure",
            json={
                "auth0_id": auth0_id,
                "email": email,
                "name": name,
                "subscription_plan": subscription_plan
            }
        )

        return AccountProfile(**result)

    async def get_account_profile(self, user_id: str) -> AccountProfile:
        """Get detailed account profile"""
        result = await self._make_request(
            "GET",
            f"/api/v1/accounts/profile/{user_id}"
        )

        return AccountProfile(**result)

    async def get_account_by_email(self, email: str) -> Optional[AccountProfile]:
        """Get account by email address"""
        try:
            result = await self._make_request(
                "GET",
                f"/api/v1/accounts/by-email/{email}"
            )
            return AccountProfile(**result)
        except Exception as e:
            if "not found" in str(e).lower():
                return None
            raise

    async def update_account_profile(
        self,
        user_id: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        preferences: Optional[Dict[str, Any]] = None
    ) -> AccountProfile:
        """Update account profile"""
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if email is not None:
            update_data["email"] = email
        if preferences is not None:
            update_data["preferences"] = preferences

        if not update_data:
            raise ValueError("At least one field must be provided for update")

        result = await self._make_request(
            "PUT",
            f"/api/v1/accounts/profile/{user_id}",
            json=update_data
        )

        return AccountProfile(**result)

    async def update_account_preferences(
        self,
        user_id: str,
        timezone: Optional[str] = None,
        language: Optional[str] = None,
        notification_email: Optional[bool] = None,
        notification_push: Optional[bool] = None,
        theme: Optional[str] = None
    ) -> bool:
        """Update account preferences"""
        prefs = {}
        if timezone is not None:
            prefs["timezone"] = timezone
        if language is not None:
            prefs["language"] = language
        if notification_email is not None:
            prefs["notification_email"] = notification_email
        if notification_push is not None:
            prefs["notification_push"] = notification_push
        if theme is not None:
            prefs["theme"] = theme

        if not prefs:
            return True  # No changes

        result = await self._make_request(
            "PUT",
            f"/api/v1/accounts/preferences/{user_id}",
            json=prefs
        )

        return result.get("message") == "Preferences updated successfully"

    async def list_accounts(
        self,
        page: int = 1,
        page_size: int = 50,
        is_active: Optional[bool] = None,
        subscription_status: Optional[str] = None,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """List accounts with pagination and filtering"""
        params = {
            "page": page,
            "page_size": page_size
        }
        if is_active is not None:
            params["is_active"] = is_active
        if subscription_status is not None:
            params["subscription_status"] = subscription_status
        if search is not None:
            params["search"] = search

        result = await self._make_request(
            "GET",
            "/api/v1/accounts",
            params=params
        )

        return result

    async def search_accounts(
        self,
        query: str,
        limit: int = 50,
        include_inactive: bool = False
    ) -> List[AccountSummary]:
        """Search accounts by name or email"""
        result = await self._make_request(
            "GET",
            "/api/v1/accounts/search",
            params={
                "query": query,
                "limit": limit,
                "include_inactive": include_inactive
            }
        )

        return [AccountSummary(**account) for account in result]

    async def change_account_status(
        self,
        user_id: str,
        is_active: bool,
        reason: Optional[str] = None
    ) -> bool:
        """Change account status (admin operation)"""
        payload = {"is_active": is_active}
        if reason:
            payload["reason"] = reason

        result = await self._make_request(
            "PUT",
            f"/api/v1/accounts/status/{user_id}",
            json=payload
        )

        return "successfully" in result.get("message", "")

    async def delete_account(
        self,
        user_id: str,
        reason: Optional[str] = None
    ) -> bool:
        """Delete account (soft delete)"""
        params = {}
        if reason:
            params["reason"] = reason

        result = await self._make_request(
            "DELETE",
            f"/api/v1/accounts/profile/{user_id}",
            params=params
        )

        return result.get("message") == "Account deleted successfully"

    async def get_service_stats(self) -> Dict[str, Any]:
        """Get account service statistics"""
        return await self._make_request("GET", "/api/v1/accounts/stats")

    async def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        return await self._make_request("GET", "/health")

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
    print("Account Service Client Examples")
    print("=" * 70)

    async with AccountClient() as client:
        # Example 1: Health Check
        print("\n1. Health Check")
        print("-" * 70)
        health = await client.health_check()
        print(f"✓ Service: {health['service']}")
        print(f"  Status: {health['status']}")
        print(f"  Port: {health['port']}")

        # Example 2: Ensure Account (Create or Get)
        print("\n2. Ensure Account Exists")
        print("-" * 70)
        account = await client.ensure_account(
            auth0_id=f"example_user_{int(datetime.now().timestamp())}",
            email=f"example_{int(datetime.now().timestamp())}@demo.com",
            name="Example User Account",
            subscription_plan="free"
        )
        print(f"✓ Account ensured: {account.user_id}")
        print(f"  Email: {account.email}")
        print(f"  Credits: {account.credits_remaining}/{account.credits_total}")

        # Example 3: Get Account Profile
        print("\n3. Get Account Profile")
        print("-" * 70)
        profile = await client.get_account_profile(account.user_id)
        print(f"✓ Retrieved profile for: {profile.name}")
        print(f"  Subscription: {profile.subscription_status}")
        print(f"  Active: {profile.is_active}")

        # Example 4: Update Account Profile
        print("\n4. Update Account Profile")
        print("-" * 70)
        updated = await client.update_account_profile(
            user_id=account.user_id,
            name="Updated Example User"
        )
        print(f"✓ Profile updated: {updated.name}")

        # Example 5: Update Preferences
        print("\n5. Update Account Preferences")
        print("-" * 70)
        success = await client.update_account_preferences(
            user_id=account.user_id,
            timezone="America/New_York",
            language="en",
            theme="dark",
            notification_email=True,
            notification_push=False
        )
        print(f"✓ Preferences updated: {success}")

        # Example 6: Verify Preferences Saved
        print("\n6. Verify Preferences Were Saved")
        print("-" * 70)
        profile_with_prefs = await client.get_account_profile(account.user_id)
        print(f"✓ Preferences:")
        for key, value in profile_with_prefs.preferences.items():
            print(f"  {key}: {value}")

        # Example 7: Get Account by Email
        print("\n7. Get Account by Email")
        print("-" * 70)
        by_email = await client.get_account_by_email(updated.email)
        if by_email:
            print(f"✓ Found account: {by_email.user_id}")
            print(f"  Name: {by_email.name}")

        # Example 8: List Accounts
        print("\n8. List Accounts (Paginated)")
        print("-" * 70)
        accounts_list = await client.list_accounts(page=1, page_size=5)
        print(f"✓ Total accounts: {accounts_list['total_count']}")
        print(f"  Page: {accounts_list['page']}/{accounts_list['page_size']}")
        print(f"  Has next: {accounts_list['has_next']}")
        print(f"  Showing {len(accounts_list['accounts'])} accounts:")
        for acc in accounts_list['accounts'][:3]:
            print(f"  - {acc['name']} ({acc['email']})")

        # Example 9: Search Accounts
        print("\n9. Search Accounts")
        print("-" * 70)
        search_results = await client.search_accounts(query="example", limit=5)
        print(f"✓ Found {len(search_results)} matching accounts:")
        for result in search_results[:3]:
            print(f"  - {result.name} ({result.email})")

        # Example 10: Get Service Statistics
        print("\n10. Service Statistics")
        print("-" * 70)
        stats = await client.get_service_stats()
        print(f"✓ Total accounts: {stats['total_accounts']}")
        print(f"  Active: {stats['active_accounts']}")
        print(f"  Inactive: {stats['inactive_accounts']}")
        print(f"  By subscription:")
        for sub_type, count in stats['accounts_by_subscription'].items():
            print(f"    {sub_type}: {count}")

        # Example 11: Change Account Status (Deactivate)
        print("\n11. Change Account Status (Deactivate)")
        print("-" * 70)
        deactivated = await client.change_account_status(
            user_id=account.user_id,
            is_active=False,
            reason="Example deactivation"
        )
        print(f"✓ Account deactivated: {deactivated}")

        # Example 12: Reactivate Account
        print("\n12. Reactivate Account")
        print("-" * 70)
        reactivated = await client.change_account_status(
            user_id=account.user_id,
            is_active=True,
            reason="Example reactivation"
        )
        print(f"✓ Account reactivated: {reactivated}")

        # Example 13: Delete Account
        print("\n13. Delete Account (Soft Delete)")
        print("-" * 70)
        deleted = await client.delete_account(
            user_id=account.user_id,
            reason="Example cleanup"
        )
        print(f"✓ Account deleted: {deleted}")

        # Show Client Metrics
        print("\n14. Client Performance Metrics")
        print("-" * 70)
        metrics = client.get_metrics()
        print(f"Total requests: {metrics['total_requests']}")
        print(f"Total errors: {metrics['total_errors']}")
        print(f"Error rate: {metrics['error_rate']:.2%}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())
