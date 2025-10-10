"""
Encryption Utilities for Vault Service

Multi-layer encryption with blockchain verification support.
"""

import os
import hashlib
import base64
import logging
from typing import Tuple, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import secrets

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Base exception for encryption errors"""
    pass


class VaultEncryption:
    """
    Multi-layer encryption system for vault secrets

    Architecture:
    1. Master Key (from environment/KMS) - encrypts User KEKs
    2. User KEK (Key Encryption Key) - per user, encrypts DEKs
    3. DEK (Data Encryption Key) - per secret, encrypts actual data
    """

    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize encryption system

        Args:
            master_key: Master encryption key (base64 encoded)
                       If not provided, will try to get from environment
        """
        self.master_key = self._get_master_key(master_key)
        self.master_cipher = Fernet(self.master_key)

    def _get_master_key(self, provided_key: Optional[str] = None) -> bytes:
        """Get or generate master key"""
        if provided_key:
            return provided_key.encode() if isinstance(provided_key, str) else provided_key

        # Try to get from environment
        env_key = os.getenv('VAULT_MASTER_KEY')
        if env_key:
            return env_key.encode()

        # For development, generate a temporary key (NOT for production!)
        logger.warning("No VAULT_MASTER_KEY found, generating temporary key (NOT for production!)")
        return Fernet.generate_key()

    def generate_user_kek(self, user_id: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        """
        Generate User Key Encryption Key (KEK)

        Args:
            user_id: User identifier
            salt: Optional salt, will be generated if not provided

        Returns:
            Tuple of (KEK, salt)
        """
        if salt is None:
            salt = os.urandom(32)

        # Derive KEK from master key and user_id
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000
        )
        kek = kdf.derive(self.master_key + user_id.encode())

        return kek, salt

    def generate_dek(self) -> bytes:
        """Generate Data Encryption Key (DEK) for a secret"""
        return AESGCM.generate_key(bit_length=256)

    def encrypt_secret(
        self,
        plain_text: str,
        user_id: str,
        kek_salt: Optional[bytes] = None
    ) -> Tuple[bytes, bytes, bytes, bytes]:
        """
        Encrypt a secret using multi-layer encryption

        Args:
            plain_text: The secret to encrypt
            user_id: User who owns the secret
            kek_salt: Optional KEK salt, will be generated if not provided

        Returns:
            Tuple of (encrypted_data, dek_encrypted, kek_salt, nonce)
        """
        try:
            # Generate or retrieve User KEK
            kek, kek_salt = self.generate_user_kek(user_id, kek_salt)

            # Generate DEK for this secret
            dek = self.generate_dek()

            # Encrypt the secret with DEK using AES-GCM
            aesgcm = AESGCM(dek)
            nonce = os.urandom(12)  # 96-bit nonce for GCM
            encrypted_data = aesgcm.encrypt(nonce, plain_text.encode(), None)

            # Encrypt DEK with KEK
            kek_cipher = Fernet(base64.urlsafe_b64encode(kek))
            dek_encrypted = kek_cipher.encrypt(dek)

            return encrypted_data, dek_encrypted, kek_salt, nonce

        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise EncryptionError(f"Failed to encrypt secret: {str(e)}")

    def decrypt_secret(
        self,
        encrypted_data: bytes,
        dek_encrypted: bytes,
        kek_salt: bytes,
        nonce: bytes,
        user_id: str
    ) -> str:
        """
        Decrypt a secret using multi-layer decryption

        Args:
            encrypted_data: The encrypted secret
            dek_encrypted: Encrypted DEK
            kek_salt: Salt used for KEK derivation
            nonce: Nonce used for AES-GCM
            user_id: User who owns the secret

        Returns:
            Decrypted plain text secret
        """
        try:
            # Regenerate User KEK using the same salt
            kek, _ = self.generate_user_kek(user_id, kek_salt)

            # Decrypt DEK using KEK
            kek_cipher = Fernet(base64.urlsafe_b64encode(kek))
            dek = kek_cipher.decrypt(dek_encrypted)

            # Decrypt the secret using DEK
            aesgcm = AESGCM(dek)
            plain_text = aesgcm.decrypt(nonce, encrypted_data, None)

            return plain_text.decode()

        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise EncryptionError(f"Failed to decrypt secret: {str(e)}")

    def rotate_dek(
        self,
        encrypted_data: bytes,
        old_dek_encrypted: bytes,
        kek_salt: bytes,
        nonce: bytes,
        user_id: str
    ) -> Tuple[bytes, bytes, bytes]:
        """
        Rotate DEK by re-encrypting with a new key

        Args:
            encrypted_data: Current encrypted data
            old_dek_encrypted: Current encrypted DEK
            kek_salt: KEK salt
            nonce: Current nonce
            user_id: User ID

        Returns:
            Tuple of (new_encrypted_data, new_dek_encrypted, new_nonce)
        """
        try:
            # First decrypt with old key
            plain_text = self.decrypt_secret(
                encrypted_data, old_dek_encrypted, kek_salt, nonce, user_id
            )

            # Re-encrypt with new DEK
            new_encrypted_data, new_dek_encrypted, _, new_nonce = self.encrypt_secret(
                plain_text, user_id, kek_salt
            )

            return new_encrypted_data, new_dek_encrypted, new_nonce

        except Exception as e:
            logger.error(f"DEK rotation failed: {e}")
            raise EncryptionError(f"Failed to rotate DEK: {str(e)}")

    def hash_secret_for_blockchain(self, secret: str) -> str:
        """
        Create a hash of the secret for blockchain verification

        This hash can be stored on blockchain to verify secret integrity
        without exposing the actual secret.

        Args:
            secret: The secret to hash

        Returns:
            SHA-256 hash as hex string
        """
        return hashlib.sha256(secret.encode()).hexdigest()

    def verify_secret_hash(self, secret: str, stored_hash: str) -> bool:
        """
        Verify a secret against a stored hash

        Args:
            secret: The secret to verify
            stored_hash: Previously stored hash

        Returns:
            True if hash matches
        """
        return self.hash_secret_for_blockchain(secret) == stored_hash

    @staticmethod
    def generate_api_key(prefix: str = "sk", length: int = 32) -> str:
        """
        Generate a secure random API key

        Args:
            prefix: Key prefix (e.g., 'sk' for secret key)
            length: Length of the random part

        Returns:
            Generated API key
        """
        random_part = secrets.token_urlsafe(length)
        return f"{prefix}_{random_part}"

    @staticmethod
    def generate_encryption_key() -> str:
        """Generate a new Fernet encryption key"""
        return Fernet.generate_key().decode()


class BlockchainVaultIntegration:
    """
    Integration point for blockchain-based secret verification

    This class provides methods to store secret hashes on blockchain
    for tamper-proof verification. It uses the blockchain_client for
    actual blockchain operations.
    """

    def __init__(self, blockchain_client=None):
        """
        Initialize blockchain integration

        Args:
            blockchain_client: Instance of BlockchainClient from core
        """
        self.blockchain_client = blockchain_client
        self.enabled = blockchain_client is not None

    async def store_secret_hash(
        self,
        vault_id: str,
        secret_hash: str,
        user_address: Optional[str] = None
    ) -> Optional[str]:
        """
        Store secret hash on blockchain for verification

        Args:
            vault_id: Vault item ID
            secret_hash: Hash of the secret
            user_address: User's blockchain address

        Returns:
            Transaction hash if successful, None otherwise
        """
        if not self.enabled:
            logger.warning("Blockchain integration not enabled")
            return None

        try:
            # Prepare data for blockchain storage
            data = f"vault:{vault_id}:hash:{secret_hash}"

            # Store on blockchain (this would be a smart contract call in production)
            # For now, we'll use a simple transaction with data
            result = await self.blockchain_client.send_transaction(
                to=user_address or self.blockchain_client.gateway_url,
                value="0",  # No value transfer, just data storage
                data=data
            )

            tx_hash = result.get('transactionHash') or result.get('hash')
            logger.info(f"Stored secret hash on blockchain: {tx_hash}")
            return tx_hash

        except Exception as e:
            logger.error(f"Failed to store hash on blockchain: {e}")
            return None

    async def verify_secret_from_blockchain(
        self,
        vault_id: str,
        secret_hash: str,
        blockchain_tx_hash: str
    ) -> bool:
        """
        Verify a secret hash against blockchain record

        Args:
            vault_id: Vault item ID
            secret_hash: Current secret hash
            blockchain_tx_hash: Transaction hash where original was stored

        Returns:
            True if verification passes
        """
        if not self.enabled:
            logger.warning("Blockchain integration not enabled")
            return False

        try:
            # Retrieve transaction from blockchain
            tx = await self.blockchain_client.get_transaction(blockchain_tx_hash)

            # Extract and verify data
            stored_data = tx.get('data', '')
            expected_data = f"vault:{vault_id}:hash:{secret_hash}"

            if stored_data == expected_data:
                logger.info(f"Blockchain verification passed for vault {vault_id}")
                return True
            else:
                logger.warning(f"Blockchain verification failed for vault {vault_id}")
                return False

        except Exception as e:
            logger.error(f"Blockchain verification error: {e}")
            return False

    def get_integration_status(self) -> dict:
        """Get blockchain integration status"""
        return {
            "enabled": self.enabled,
            "client_available": self.blockchain_client is not None,
            "features": {
                "hash_storage": self.enabled,
                "verification": self.enabled,
                "tamper_detection": self.enabled
            }
        }


# Helper functions for common encryption tasks

def encrypt_field(value: str, encryption: VaultEncryption, user_id: str) -> dict:
    """
    Encrypt a field and return all necessary components

    Args:
        value: Plain text value
        encryption: VaultEncryption instance
        user_id: User ID

    Returns:
        Dict with encrypted components
    """
    encrypted_data, dek_encrypted, kek_salt, nonce = encryption.encrypt_secret(value, user_id)

    return {
        'encrypted_value': base64.b64encode(encrypted_data).decode(),
        'dek_encrypted': base64.b64encode(dek_encrypted).decode(),
        'kek_salt': base64.b64encode(kek_salt).decode(),
        'nonce': base64.b64encode(nonce).decode()
    }


def decrypt_field(encrypted_components: dict, encryption: VaultEncryption, user_id: str) -> str:
    """
    Decrypt a field from its components

    Args:
        encrypted_components: Dict with encrypted components
        encryption: VaultEncryption instance
        user_id: User ID

    Returns:
        Decrypted plain text
    """
    return encryption.decrypt_secret(
        encrypted_data=base64.b64decode(encrypted_components['encrypted_value']),
        dek_encrypted=base64.b64decode(encrypted_components['dek_encrypted']),
        kek_salt=base64.b64decode(encrypted_components['kek_salt']),
        nonce=base64.b64decode(encrypted_components['nonce']),
        user_id=user_id
    )
