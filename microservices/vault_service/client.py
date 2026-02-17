"""
Vault Service Client

Client library for other microservices to interact with vault service
"""

import httpx
from core.config_manager import ConfigManager
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class VaultServiceClient:
    """Vault Service HTTP client"""

    def __init__(self, base_url: str = None, config: Optional[ConfigManager] = None):
        """
        Initialize Vault Service client

        Args:
            base_url: Vault service base URL, defaults to service discovery
            config: ConfigManager instance for service discovery
        """
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Use service discovery via ConfigManager
            if config is None:
                config = ConfigManager("vault_service_client")

            try:
                host, port = config.discover_service(
                    service_name='vault_service',
                    default_host='localhost',
                    default_port=8214,
                    env_host_key='VAULT_SERVICE_HOST',
                    env_port_key='VAULT_SERVICE_PORT'
                )
                self.base_url = f"http://{host}:{port}"
                logger.info(f"Vault service discovered at {self.base_url}")
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                self.base_url = "http://localhost:8214"

        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # =============================================================================
    # Secret Management
    # =============================================================================

    async def create_secret(
        self,
        secret_type: str,
        secret_name: str,
        secret_value: str,
        user_id: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create new secret

        Args:
            secret_type: Type of secret (password, api_key, token, etc.)
            secret_name: Secret name
            secret_value: Secret value (will be encrypted)
            user_id: User ID
            description: Secret description (optional)
            tags: Tags for organization (optional)
            metadata: Additional metadata (optional)

        Returns:
            Created secret info (without value)

        Example:
            >>> client = VaultServiceClient()
            >>> secret = await client.create_secret(
            ...     secret_type="api_key",
            ...     secret_name="stripe_api_key",
            ...     secret_value="sk_test_...",
            ...     user_id="user123",
            ...     description="Stripe API key for payments"
            ... )
        """
        try:
            payload = {
                "secret_type": secret_type,
                "secret_name": secret_name,
                "secret_value": secret_value
            }

            if description:
                payload["description"] = description
            if tags:
                payload["tags"] = tags
            if metadata:
                payload["metadata"] = metadata

            response = await self.client.post(
                f"{self.base_url}/api/v1/vault/secrets",
                json=payload,
                headers={"X-User-Id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create secret: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error creating secret: {e}")
            return None

    async def get_secret(
        self,
        vault_id: str,
        user_id: str,
        include_value: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get secret by ID

        Args:
            vault_id: Vault ID
            user_id: User ID
            include_value: Include decrypted secret value (default: True)

        Returns:
            Secret details

        Example:
            >>> secret = await client.get_secret("vault123", "user456")
        """
        try:
            params = {"include_value": include_value}

            response = await self.client.get(
                f"{self.base_url}/api/v1/vault/secrets/{vault_id}",
                params=params,
                headers={"X-User-Id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get secret: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting secret: {e}")
            return None

    async def list_secrets(
        self,
        user_id: str,
        secret_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Optional[Dict[str, Any]]:
        """
        List user secrets

        Args:
            user_id: User ID
            secret_type: Filter by secret type (optional)
            tags: Filter by tags (optional)
            page: Page number (default: 1)
            page_size: Items per page (default: 50)

        Returns:
            List of secrets (without values)

        Example:
            >>> secrets = await client.list_secrets("user123", secret_type="api_key")
        """
        try:
            params = {
                "page": page,
                "page_size": page_size
            }

            if secret_type:
                params["secret_type"] = secret_type
            if tags:
                params["tags"] = ",".join(tags)

            response = await self.client.get(
                f"{self.base_url}/api/v1/vault/secrets",
                params=params,
                headers={"X-User-Id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list secrets: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error listing secrets: {e}")
            return None

    async def update_secret(
        self,
        vault_id: str,
        user_id: str,
        secret_value: Optional[str] = None,
        secret_name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update secret

        Args:
            vault_id: Vault ID
            user_id: User ID
            secret_value: New secret value (optional)
            secret_name: New secret name (optional)
            description: New description (optional)
            tags: New tags (optional)
            metadata: New metadata (optional)

        Returns:
            Updated secret info

        Example:
            >>> updated = await client.update_secret(
            ...     vault_id="vault123",
            ...     user_id="user456",
            ...     secret_value="new_value",
            ...     description="Updated description"
            ... )
        """
        try:
            payload = {}

            if secret_value:
                payload["secret_value"] = secret_value
            if secret_name:
                payload["secret_name"] = secret_name
            if description:
                payload["description"] = description
            if tags:
                payload["tags"] = tags
            if metadata:
                payload["metadata"] = metadata

            response = await self.client.put(
                f"{self.base_url}/api/v1/vault/secrets/{vault_id}",
                json=payload,
                headers={"X-User-Id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to update secret: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error updating secret: {e}")
            return None

    async def delete_secret(
        self,
        vault_id: str,
        user_id: str
    ) -> bool:
        """
        Delete secret

        Args:
            vault_id: Vault ID
            user_id: User ID

        Returns:
            True if successful

        Example:
            >>> success = await client.delete_secret("vault123", "user456")
        """
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/v1/vault/secrets/{vault_id}",
                headers={"X-User-Id": user_id}
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to delete secret: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error deleting secret: {e}")
            return False

    async def rotate_secret(
        self,
        vault_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Rotate secret (generate new version)

        Args:
            vault_id: Vault ID
            user_id: User ID

        Returns:
            Rotated secret info

        Example:
            >>> rotated = await client.rotate_secret("vault123", "user456")
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/vault/secrets/{vault_id}/rotate",
                headers={"X-User-Id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to rotate secret: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error rotating secret: {e}")
            return None

    # =============================================================================
    # Secret Sharing
    # =============================================================================

    async def share_secret(
        self,
        vault_id: str,
        share_with_user_id: str,
        user_id: str,
        permission: str = "read",
        expires_in_days: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Share secret with another user

        Args:
            vault_id: Vault ID
            share_with_user_id: User ID to share with
            user_id: Owner user ID
            permission: Permission level (read, write) (default: read)
            expires_in_days: Expiration in days (optional)

        Returns:
            Share info

        Example:
            >>> share = await client.share_secret(
            ...     vault_id="vault123",
            ...     share_with_user_id="user789",
            ...     user_id="user456",
            ...     permission="read",
            ...     expires_in_days=30
            ... )
        """
        try:
            payload = {
                "share_with_user_id": share_with_user_id,
                "permission": permission
            }

            if expires_in_days:
                payload["expires_in_days"] = expires_in_days

            response = await self.client.post(
                f"{self.base_url}/api/v1/vault/secrets/{vault_id}/share",
                json=payload,
                headers={"X-User-Id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to share secret: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error sharing secret: {e}")
            return None

    async def get_shared_secrets(
        self,
        user_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get secrets shared with user

        Args:
            user_id: User ID

        Returns:
            List of shared secrets

        Example:
            >>> shared = await client.get_shared_secrets("user123")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/vault/shared",
                headers={"X-User-Id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get shared secrets: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting shared secrets: {e}")
            return None

    # =============================================================================
    # Audit & Stats
    # =============================================================================

    async def get_audit_logs(
        self,
        user_id: str,
        vault_id: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get audit logs

        Args:
            user_id: User ID
            vault_id: Filter by vault ID (optional)
            action: Filter by action type (optional)
            limit: Result limit (default: 100)

        Returns:
            List of audit logs

        Example:
            >>> logs = await client.get_audit_logs("user123", vault_id="vault456")
        """
        try:
            params = {"limit": limit}

            if vault_id:
                params["vault_id"] = vault_id
            if action:
                params["action"] = action

            response = await self.client.get(
                f"{self.base_url}/api/v1/vault/audit-logs",
                params=params,
                headers={"X-User-Id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get audit logs: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting audit logs: {e}")
            return None

    async def get_vault_stats(
        self,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get vault statistics

        Args:
            user_id: User ID

        Returns:
            Vault statistics

        Example:
            >>> stats = await client.get_vault_stats("user123")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/vault/stats",
                headers={"X-User-Id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get vault stats: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting vault stats: {e}")
            return None

    # =============================================================================
    # Secret Testing
    # =============================================================================

    async def test_secret(
        self,
        vault_id: str,
        user_id: str,
        test_endpoint: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Test secret (verify it works)

        Args:
            vault_id: Vault ID
            user_id: User ID
            test_endpoint: Endpoint to test against (optional)

        Returns:
            Test result

        Example:
            >>> result = await client.test_secret("vault123", "user456")
        """
        try:
            payload = {}
            if test_endpoint:
                payload["test_endpoint"] = test_endpoint

            response = await self.client.post(
                f"{self.base_url}/api/v1/vault/secrets/{vault_id}/test",
                json=payload,
                headers={"X-User-Id": user_id}
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to test secret: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error testing secret: {e}")
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


__all__ = ["VaultServiceClient"]
