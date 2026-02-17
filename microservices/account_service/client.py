"""
Account Service Client

Client library for other microservices to interact with account service
"""

import httpx
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class AccountServiceClient:
    """Account Service HTTP client"""

    def __init__(self, base_url: str = None, config=None):
        """
        Initialize Account Service client

        Args:
            base_url: Account service base URL, defaults to service discovery via ConfigManager
            config: Optional ConfigManager instance for service discovery
        """
        if base_url:
            self.base_url = base_url.rstrip('/')
            self.config = None
        else:
            # Use ConfigManager for service discovery
            # Priority: Environment variables → Consul → localhost fallback
            if config is None:
                from core.config_manager import ConfigManager
                config = ConfigManager("account_service_client")

            self.config = config
            # Do service discovery on first use, not at init time
            self.base_url = None

        self.client = httpx.AsyncClient(timeout=30.0)

    def _get_base_url(self) -> str:
        """Get base URL with lazy service discovery"""
        if self.base_url:
            return self.base_url

        if self.config:
            try:
                host, port = self.config.discover_service(
                    service_name='account_service',
                    default_host='localhost',
                    default_port=8202,
                    env_host_key='ACCOUNT_SERVICE_HOST',
                    env_port_key='ACCOUNT_SERVICE_PORT'
                )
                return f"http://{host}:{port}"
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                return "http://localhost:8202"

        return "http://localhost:8202"

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # =============================================================================
    # Account Management
    # =============================================================================

    async def ensure_account(
        self,
        user_id: str,
        email: str,
        name: str,
        subscription_plan: str = "free"
    ) -> Optional[Dict[str, Any]]:
        """
        Ensure account exists, create if needed

        Args:
            user_id: User ID (from auth service)
            email: User email
            name: User name
            subscription_plan: Initial subscription plan (deprecated, use subscription_service)

        Returns:
            Account profile data

        Example:
            >>> client = AccountServiceClient()
            >>> account = await client.ensure_account(
            ...     user_id="usr_abc123",
            ...     email="user@example.com",
            ...     name="John Doe"
            ... )
            >>> print(f"User ID: {account['user_id']}")
        """
        try:
            response = await self.client.post(
                f"{self._get_base_url()}/api/v1/accounts/ensure",
                json={
                    "user_id": user_id,
                    "email": email,
                    "name": name,
                }
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to ensure account: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error ensuring account: {e}")
            return None

    async def get_account_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed account profile

        Args:
            user_id: User ID

        Returns:
            Account profile data

        Example:
            >>> profile = await client.get_account_profile("user123")
            >>> print(f"Email: {profile['email']}")
            >>> print(f"Credits: {profile['credits_remaining']}")
        """
        try:
            response = await self.client.get(
                f"{self._get_base_url()}/api/v1/accounts/profile/{user_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get account profile: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting account profile: {e}")
            return None

    async def get_account_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get account by email address

        Args:
            email: User email

        Returns:
            Account profile data or None if not found

        Example:
            >>> account = await client.get_account_by_email("user@example.com")
            >>> if account:
            ...     print(f"Found user: {account['user_id']}")
        """
        try:
            response = await self.client.get(
                f"{self._get_base_url()}/api/v1/accounts/by-email/{email}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"Failed to get account by email: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting account by email: {e}")
            return None

    async def update_account_profile(
        self,
        user_id: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        preferences: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update account profile

        Args:
            user_id: User ID
            name: Updated name (optional)
            email: Updated email (optional)
            preferences: Updated preferences (optional)

        Returns:
            Updated account profile

        Example:
            >>> updated = await client.update_account_profile(
            ...     user_id="user123",
            ...     name="Jane Doe"
            ... )
        """
        try:
            update_data = {}
            if name is not None:
                update_data["name"] = name
            if email is not None:
                update_data["email"] = email
            if preferences is not None:
                update_data["preferences"] = preferences

            if not update_data:
                logger.warning("No update data provided")
                return None

            response = await self.client.put(
                f"{self._get_base_url()}/api/v1/accounts/profile/{user_id}",
                json=update_data
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to update account profile: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error updating account profile: {e}")
            return None

    async def update_account_preferences(
        self,
        user_id: str,
        timezone: Optional[str] = None,
        language: Optional[str] = None,
        notification_email: Optional[bool] = None,
        notification_push: Optional[bool] = None,
        theme: Optional[str] = None
    ) -> bool:
        """
        Update account preferences

        Args:
            user_id: User ID
            timezone: User timezone (optional)
            language: Preferred language (optional)
            notification_email: Email notifications enabled (optional)
            notification_push: Push notifications enabled (optional)
            theme: UI theme (light/dark/auto) (optional)

        Returns:
            True if successful

        Example:
            >>> success = await client.update_account_preferences(
            ...     user_id="user123",
            ...     timezone="America/New_York",
            ...     theme="dark"
            ... )
        """
        try:
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

            response = await self.client.put(
                f"{self._get_base_url()}/api/v1/accounts/preferences/{user_id}",
                json=prefs
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to update preferences: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error updating preferences: {e}")
            return False

    # =============================================================================
    # Account Queries
    # =============================================================================

    async def list_accounts(
        self,
        page: int = 1,
        page_size: int = 50,
        is_active: Optional[bool] = None,
        subscription_status: Optional[str] = None,
        search: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        List accounts with pagination and filtering

        Args:
            page: Page number
            page_size: Items per page
            is_active: Filter by active status
            subscription_status: Filter by subscription
            search: Search in name/email

        Returns:
            Paginated account list

        Example:
            >>> result = await client.list_accounts(page=1, page_size=20)
            >>> for account in result['accounts']:
            ...     print(account['name'])
        """
        try:
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

            response = await self.client.get(
                f"{self._get_base_url()}/api/v1/accounts",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list accounts: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error listing accounts: {e}")
            return None

    async def search_accounts(
        self,
        query: str,
        limit: int = 50,
        include_inactive: bool = False
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Search accounts by query

        Args:
            query: Search query
            limit: Maximum results
            include_inactive: Include inactive accounts

        Returns:
            List of matching accounts

        Example:
            >>> accounts = await client.search_accounts("john")
            >>> for account in accounts:
            ...     print(f"{account['name']} - {account['email']}")
        """
        try:
            response = await self.client.get(
                f"{self._get_base_url()}/api/v1/accounts/search",
                params={
                    "query": query,
                    "limit": limit,
                    "include_inactive": include_inactive
                }
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to search accounts: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error searching accounts: {e}")
            return None

    # =============================================================================
    # Admin Operations
    # =============================================================================

    async def change_account_status(
        self,
        user_id: str,
        is_active: bool,
        reason: Optional[str] = None
    ) -> bool:
        """
        Change account status (admin operation)

        Args:
            user_id: User ID
            is_active: New active status
            reason: Reason for change

        Returns:
            True if successful

        Example:
            >>> success = await client.change_account_status(
            ...     user_id="user123",
            ...     is_active=False,
            ...     reason="Terms violation"
            ... )
        """
        try:
            payload = {"is_active": is_active}
            if reason:
                payload["reason"] = reason

            response = await self.client.put(
                f"{self._get_base_url()}/api/v1/accounts/status/{user_id}",
                json=payload
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to change account status: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error changing account status: {e}")
            return False

    async def delete_account(
        self,
        user_id: str,
        reason: Optional[str] = None
    ) -> bool:
        """
        Delete account (soft delete)

        Args:
            user_id: User ID
            reason: Deletion reason

        Returns:
            True if successful

        Example:
            >>> success = await client.delete_account("user123", "User request")
        """
        try:
            params = {}
            if reason:
                params["reason"] = reason

            response = await self.client.delete(
                f"{self._get_base_url()}/api/v1/accounts/profile/{user_id}",
                params=params
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to delete account: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error deleting account: {e}")
            return False

    # =============================================================================
    # Service Statistics
    # =============================================================================

    async def get_service_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get account service statistics

        Returns:
            Service statistics

        Example:
            >>> stats = await client.get_service_stats()
            >>> print(f"Total accounts: {stats['total_accounts']}")
            >>> print(f"Active: {stats['active_accounts']}")
        """
        try:
            response = await self.client.get(f"{self._get_base_url()}/api/v1/accounts/stats")
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
            response = await self.client.get(f"{self._get_base_url()}/health")
            return response.status_code == 200
        except:
            return False


__all__ = ["AccountServiceClient"]
