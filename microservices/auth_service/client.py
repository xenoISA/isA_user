"""
Auth Service Client

Client library for other microservices to interact with authentication service
"""

import httpx
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class AuthServiceClient:
    """Auth Service HTTP client"""

    def __init__(self, base_url: str = None):
        """
        Initialize Auth Service client

        Args:
            base_url: Auth service base URL, defaults to service discovery
        """
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Use service discovery
            try:
                from core.service_discovery import get_service_discovery
                sd = get_service_discovery()
                self.base_url = sd.get_service_url("auth_service")
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                self.base_url = "http://localhost:8201"

        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # =============================================================================
    # Token Verification & Management
    # =============================================================================

    async def verify_token(
        self,
        token: str,
        provider: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Verify JWT token

        Args:
            token: JWT token to verify
            provider: Token provider (auth0, isa_user, local) - defaults to auto-detect

        Returns:
            Token verification result with user info

        Example:
            >>> client = AuthServiceClient()
            >>> result = await client.verify_token(token="eyJ...")
            >>> if result['valid']:
            ...     print(f"User: {result['user_id']}")
        """
        try:
            payload = {"token": token}
            if provider:
                payload["provider"] = provider

            response = await self.client.post(
                f"{self.base_url}/api/v1/auth/verify-token",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to verify token: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error verifying token: {e}")
            return None

    async def generate_dev_token(
        self,
        user_id: str,
        email: str,
        expires_in: int = 3600,
        organization_id: Optional[str] = None,
        permissions: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Generate development token

        Args:
            user_id: User ID
            email: User email
            expires_in: Token expiration in seconds (default: 3600)
            organization_id: Organization ID (optional)
            permissions: Permission list (optional)
            metadata: Additional metadata (optional)

        Returns:
            Generated token data

        Example:
            >>> token_data = await client.generate_dev_token(
            ...     user_id="user123",
            ...     email="user@example.com",
            ...     expires_in=7200
            ... )
            >>> print(f"Token: {token_data['access_token']}")
        """
        try:
            payload = {
                "user_id": user_id,
                "email": email,
                "expires_in": expires_in
            }

            if organization_id:
                payload["organization_id"] = organization_id
            if permissions:
                payload["permissions"] = permissions
            if metadata:
                payload["metadata"] = metadata

            response = await self.client.post(
                f"{self.base_url}/api/v1/auth/dev-token",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to generate dev token: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error generating dev token: {e}")
            return None

    async def generate_token_pair(
        self,
        user_id: str,
        email: str,
        organization_id: Optional[str] = None,
        permissions: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Generate access and refresh token pair

        Args:
            user_id: User ID
            email: User email
            organization_id: Organization ID (optional)
            permissions: Permission list (optional)
            metadata: Additional metadata (optional)

        Returns:
            Token pair with access_token and refresh_token

        Example:
            >>> tokens = await client.generate_token_pair(
            ...     user_id="user123",
            ...     email="user@example.com"
            ... )
            >>> print(f"Access: {tokens['access_token']}")
            >>> print(f"Refresh: {tokens['refresh_token']}")
        """
        try:
            payload = {
                "user_id": user_id,
                "email": email
            }

            if organization_id:
                payload["organization_id"] = organization_id
            if permissions:
                payload["permissions"] = permissions
            if metadata:
                payload["metadata"] = metadata

            response = await self.client.post(
                f"{self.base_url}/api/v1/auth/token-pair",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to generate token pair: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error generating token pair: {e}")
            return None

    async def refresh_access_token(
        self,
        refresh_token: str
    ) -> Optional[Dict[str, Any]]:
        """
        Refresh access token using refresh token

        Args:
            refresh_token: Refresh token

        Returns:
            New access token data

        Example:
            >>> new_token = await client.refresh_access_token(refresh_token)
            >>> print(f"New access token: {new_token['access_token']}")
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/auth/refresh",
                json={"refresh_token": refresh_token}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to refresh token: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return None

    async def get_user_info(
        self,
        token: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get user information from token

        Args:
            token: Access token

        Returns:
            User information

        Example:
            >>> user_info = await client.get_user_info(token)
            >>> print(f"User: {user_info['email']}")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/auth/user-info",
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get user info: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None

    # =============================================================================
    # API Key Management
    # =============================================================================

    async def verify_api_key(
        self,
        api_key: str
    ) -> Optional[Dict[str, Any]]:
        """
        Verify API key

        Args:
            api_key: API key to verify

        Returns:
            API key verification result

        Example:
            >>> result = await client.verify_api_key("sk_...")
            >>> if result['valid']:
            ...     print(f"Org: {result['organization_id']}")
            ...     print(f"Permissions: {result['permissions']}")
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/auth/verify-api-key",
                json={"api_key": api_key}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to verify API key: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error verifying API key: {e}")
            return None

    async def create_api_key(
        self,
        organization_id: str,
        name: str,
        permissions: Optional[List[str]] = None,
        expires_in_days: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create new API key

        Args:
            organization_id: Organization ID
            name: Key name/description
            permissions: List of permissions (optional)
            expires_in_days: Expiration in days (optional)

        Returns:
            Created API key data

        Example:
            >>> api_key = await client.create_api_key(
            ...     organization_id="org123",
            ...     name="Production API Key",
            ...     permissions=["read", "write"]
            ... )
            >>> print(f"API Key: {api_key['api_key']}")
        """
        try:
            payload = {
                "organization_id": organization_id,
                "name": name,
                "permissions": permissions or []
            }

            if expires_in_days:
                payload["expires_in_days"] = expires_in_days

            response = await self.client.post(
                f"{self.base_url}/api/v1/auth/api-keys",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create API key: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error creating API key: {e}")
            return None

    async def list_api_keys(
        self,
        organization_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        List organization's API keys

        Args:
            organization_id: Organization ID

        Returns:
            List of API keys

        Example:
            >>> keys = await client.list_api_keys("org123")
            >>> for key in keys:
            ...     print(f"{key['name']}: {key['is_active']}")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/auth/api-keys/{organization_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list API keys: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error listing API keys: {e}")
            return None

    async def revoke_api_key(
        self,
        key_id: str
    ) -> bool:
        """
        Revoke/delete API key

        Args:
            key_id: API key ID

        Returns:
            True if successful

        Example:
            >>> success = await client.revoke_api_key("key_123")
        """
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/v1/auth/api-keys/{key_id}"
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to revoke API key: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error revoking API key: {e}")
            return False

    # =============================================================================
    # Device Authentication
    # =============================================================================

    async def register_device(
        self,
        device_id: str,
        user_id: str,
        device_name: str,
        device_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Register new device

        Args:
            device_id: Unique device identifier
            user_id: Owner user ID
            device_name: Device name
            device_type: Device type
            metadata: Additional metadata (optional)

        Returns:
            Device registration data with secret

        Example:
            >>> device = await client.register_device(
            ...     device_id="device_001",
            ...     user_id="user123",
            ...     device_name="Smart Frame Living Room",
            ...     device_type="smart_frame"
            ... )
            >>> print(f"Device secret: {device['device_secret']}")
        """
        try:
            payload = {
                "device_id": device_id,
                "user_id": user_id,
                "device_name": device_name,
                "device_type": device_type
            }

            if metadata:
                payload["metadata"] = metadata

            response = await self.client.post(
                f"{self.base_url}/api/v1/auth/device/register",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to register device: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error registering device: {e}")
            return None

    async def authenticate_device(
        self,
        device_id: str,
        device_secret: str
    ) -> Optional[Dict[str, Any]]:
        """
        Authenticate device and get token

        Args:
            device_id: Device ID
            device_secret: Device secret

        Returns:
            Device authentication token

        Example:
            >>> auth = await client.authenticate_device(
            ...     device_id="device_001",
            ...     device_secret="secret_xyz"
            ... )
            >>> print(f"Token: {auth['device_token']}")
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/auth/device/authenticate",
                json={
                    "device_id": device_id,
                    "device_secret": device_secret
                }
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to authenticate device: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error authenticating device: {e}")
            return None

    async def verify_device_token(
        self,
        device_token: str
    ) -> Optional[Dict[str, Any]]:
        """
        Verify device token

        Args:
            device_token: Device authentication token

        Returns:
            Device verification result

        Example:
            >>> result = await client.verify_device_token(token)
            >>> if result['valid']:
            ...     print(f"Device: {result['device_id']}")
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/auth/device/verify-token",
                json={"device_token": device_token}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to verify device token: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error verifying device token: {e}")
            return None

    async def refresh_device_secret(
        self,
        device_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Refresh device secret

        Args:
            device_id: Device ID

        Returns:
            New device secret

        Example:
            >>> result = await client.refresh_device_secret("device_001")
            >>> print(f"New secret: {result['new_secret']}")
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/auth/device/{device_id}/refresh-secret"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to refresh device secret: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error refreshing device secret: {e}")
            return None

    async def deregister_device(
        self,
        device_id: str
    ) -> bool:
        """
        Deregister device

        Args:
            device_id: Device ID

        Returns:
            True if successful

        Example:
            >>> success = await client.deregister_device("device_001")
        """
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/v1/auth/device/{device_id}"
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to deregister device: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error deregistering device: {e}")
            return False

    async def list_user_devices(
        self,
        user_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        List user's registered devices

        Args:
            user_id: User ID

        Returns:
            List of devices

        Example:
            >>> devices = await client.list_user_devices("user123")
            >>> for device in devices:
            ...     print(f"{device['device_name']}: {device['is_active']}")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/auth/device/list",
                params={"user_id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list devices: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error listing devices: {e}")
            return None

    # =============================================================================
    # Service Statistics
    # =============================================================================

    async def get_service_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get auth service statistics

        Returns:
            Service statistics

        Example:
            >>> stats = await client.get_service_stats()
            >>> print(f"Active tokens: {stats['active_tokens']}")
        """
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/auth/stats")
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


__all__ = ["AuthServiceClient"]
