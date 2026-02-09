"""
Vault Service Protocols (Interfaces)

These interfaces define contracts for dependency injection.
NO import-time I/O dependencies - safe to import anywhere.
"""
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

# Import only models (no I/O dependencies)
from .models import (
    SecretType,
    VaultAccessLog,
    VaultAccessLogResponse,
    VaultItem,
    VaultItemResponse,
    VaultShare,
    VaultShareResponse,
)


class VaultServiceError(Exception):
    """Base exception for vault service"""
    pass


class VaultAccessDeniedError(VaultServiceError):
    """Raised when user doesn't have permission"""
    pass


class VaultNotFoundError(VaultServiceError):
    """Raised when vault item not found"""
    pass


class EncryptionError(Exception):
    """Base exception for encryption errors"""
    pass


@runtime_checkable
class VaultRepositoryProtocol(Protocol):
    """
    Interface for Vault Repository.

    Implementations must provide these methods.
    Used for dependency injection to enable testing.
    """

    # ============ Vault Item Operations ============

    async def create_vault_item(self, vault_item: VaultItem) -> Optional[VaultItemResponse]:
        """Create a new vault item"""
        ...

    async def get_vault_item(self, vault_id: str) -> Optional[Dict[str, Any]]:
        """Get vault item by ID (includes encrypted data)"""
        ...

    async def list_user_vault_items(
        self,
        user_id: str,
        secret_type: Optional[SecretType] = None,
        tags: Optional[List[str]] = None,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> List[VaultItemResponse]:
        """List vault items for a user"""
        ...

    async def update_vault_item(self, vault_id: str, update_data: Dict[str, Any]) -> bool:
        """Update vault item"""
        ...

    async def delete_vault_item(self, vault_id: str) -> bool:
        """Delete vault item (soft delete)"""
        ...

    async def increment_access_count(self, vault_id: str) -> bool:
        """Increment access count and update last accessed time"""
        ...

    # ============ Access Log Operations ============

    async def create_access_log(self, log: VaultAccessLog) -> Optional[VaultAccessLogResponse]:
        """Create access log entry"""
        ...

    async def get_access_logs(
        self,
        vault_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[VaultAccessLogResponse]:
        """Get access logs"""
        ...

    # ============ Share Operations ============

    async def create_share(self, share: VaultShare) -> Optional[VaultShareResponse]:
        """Create a share"""
        ...

    async def get_shares_for_vault(self, vault_id: str) -> List[VaultShareResponse]:
        """Get all shares for a vault item"""
        ...

    async def get_shares_for_user(self, user_id: str) -> List[VaultShareResponse]:
        """Get all secrets shared with a user"""
        ...

    async def revoke_share(self, share_id: str) -> bool:
        """Revoke a share"""
        ...

    async def check_user_access(self, vault_id: str, user_id: str) -> Optional[str]:
        """
        Check if user has access to a vault item

        Returns:
            Permission level if user has access, None otherwise
        """
        ...

    # ============ Statistics ============

    async def get_vault_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get vault statistics"""
        ...

    async def get_expiring_secrets(
        self, user_id: str, days: int = 7
    ) -> List[VaultItemResponse]:
        """Get secrets expiring in the next N days"""
        ...

    # ============ GDPR ============

    async def delete_user_data(self, user_id: str) -> int:
        """Delete user all vault data (GDPR Article 17: Right to Erasure)"""
        ...


@runtime_checkable
class VaultEncryptionProtocol(Protocol):
    """Interface for Vault Encryption - no I/O imports"""

    def encrypt_secret(
        self,
        plain_text: str,
        user_id: str,
        kek_salt: Optional[bytes] = None,
    ) -> tuple:
        """
        Encrypt a secret using multi-layer encryption

        Returns:
            Tuple of (encrypted_data, dek_encrypted, kek_salt, nonce)
        """
        ...

    def decrypt_secret(
        self,
        encrypted_data: bytes,
        dek_encrypted: bytes,
        kek_salt: bytes,
        nonce: bytes,
        user_id: str,
    ) -> str:
        """
        Decrypt a secret using multi-layer decryption

        Returns:
            Decrypted plain text secret
        """
        ...

    def hash_secret_for_blockchain(self, secret: str) -> str:
        """
        Create a hash of the secret for blockchain verification

        Returns:
            SHA-256 hash as hex string
        """
        ...

    def verify_secret_hash(self, secret: str, stored_hash: str) -> bool:
        """
        Verify a secret against a stored hash

        Returns:
            True if hash matches
        """
        ...


@runtime_checkable
class BlockchainIntegrationProtocol(Protocol):
    """Interface for Blockchain Integration - no I/O imports"""

    enabled: bool

    async def store_secret_hash(
        self,
        vault_id: str,
        secret_hash: str,
        user_address: Optional[str] = None,
    ) -> Optional[str]:
        """
        Store secret hash on blockchain for verification

        Returns:
            Transaction hash if successful, None otherwise
        """
        ...

    async def verify_secret_from_blockchain(
        self,
        vault_id: str,
        secret_hash: str,
        blockchain_tx_hash: str,
    ) -> bool:
        """
        Verify a secret hash against blockchain record

        Returns:
            True if verification passes
        """
        ...

    def get_integration_status(self) -> Dict[str, Any]:
        """Get blockchain integration status"""
        ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for Event Bus - no I/O imports"""

    async def publish_event(self, event: Any) -> None:
        """Publish an event"""
        ...


__all__ = [
    "VaultServiceError",
    "VaultAccessDeniedError",
    "VaultNotFoundError",
    "EncryptionError",
    "VaultRepositoryProtocol",
    "VaultEncryptionProtocol",
    "BlockchainIntegrationProtocol",
    "EventBusProtocol",
]
