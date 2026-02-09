"""
Vault Service Encryption Unit Tests

Tests for VaultEncryption utilities and pure functions.
"""
import pytest
import base64
import os
from unittest.mock import patch

from microservices.vault_service.encryption import (
    VaultEncryption,
    EncryptionError,
    encrypt_field,
    decrypt_field,
)

pytestmark = pytest.mark.unit


# =============================================================================
# Test Data Factory
# =============================================================================

class EncryptionTestDataFactory:
    """Factory for generating encryption test data"""

    @staticmethod
    def unique_user_id() -> str:
        """Generate unique user ID"""
        import uuid
        return f"user_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def unique_secret() -> str:
        """Generate unique secret value"""
        import uuid
        return f"secret_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def api_key() -> str:
        """Generate mock API key"""
        import uuid
        return f"sk_test_{uuid.uuid4().hex[:32]}"

    @staticmethod
    def database_password() -> str:
        """Generate mock database password"""
        import secrets
        return secrets.token_urlsafe(24)


# =============================================================================
# VaultEncryption Tests
# =============================================================================

class TestVaultEncryptionInit:
    """Tests for VaultEncryption initialization"""

    def test_init_with_master_key_string(self):
        """Should initialize with string master key"""
        from cryptography.fernet import Fernet
        master_key = Fernet.generate_key().decode()
        encryption = VaultEncryption(master_key=master_key)
        assert encryption.master_key is not None

    def test_init_without_master_key(self):
        """Should generate temporary key without master key"""
        with patch.dict(os.environ, {}, clear=True):
            encryption = VaultEncryption()
            assert encryption.master_key is not None

    def test_init_with_env_master_key(self):
        """Should use environment variable master key"""
        from cryptography.fernet import Fernet
        env_key = Fernet.generate_key().decode()
        with patch.dict(os.environ, {"VAULT_MASTER_KEY": env_key}):
            encryption = VaultEncryption()
            assert encryption.master_key == env_key.encode()


class TestUserKEKGeneration:
    """Tests for User Key Encryption Key generation"""

    @pytest.fixture
    def encryption(self):
        """Create VaultEncryption instance"""
        from cryptography.fernet import Fernet
        return VaultEncryption(master_key=Fernet.generate_key().decode())

    def test_generate_kek_returns_key_and_salt(self, encryption):
        """Should return KEK and salt tuple"""
        user_id = EncryptionTestDataFactory.unique_user_id()
        kek, salt = encryption.generate_user_kek(user_id)
        assert isinstance(kek, bytes)
        assert isinstance(salt, bytes)
        assert len(kek) == 32  # 256 bits
        assert len(salt) == 32  # 256 bits

    def test_same_salt_produces_same_kek(self, encryption):
        """Same salt should produce same KEK"""
        user_id = EncryptionTestDataFactory.unique_user_id()
        salt = os.urandom(32)
        kek1, _ = encryption.generate_user_kek(user_id, salt)
        kek2, _ = encryption.generate_user_kek(user_id, salt)
        assert kek1 == kek2

    def test_different_salt_produces_different_kek(self, encryption):
        """Different salt should produce different KEK"""
        user_id = EncryptionTestDataFactory.unique_user_id()
        kek1, salt1 = encryption.generate_user_kek(user_id)
        kek2, salt2 = encryption.generate_user_kek(user_id)
        assert kek1 != kek2
        assert salt1 != salt2

    def test_different_user_produces_different_kek(self, encryption):
        """Different users should have different KEKs"""
        salt = os.urandom(32)
        user1 = EncryptionTestDataFactory.unique_user_id()
        user2 = EncryptionTestDataFactory.unique_user_id()
        kek1, _ = encryption.generate_user_kek(user1, salt)
        kek2, _ = encryption.generate_user_kek(user2, salt)
        assert kek1 != kek2


class TestDEKGeneration:
    """Tests for Data Encryption Key generation"""

    @pytest.fixture
    def encryption(self):
        """Create VaultEncryption instance"""
        from cryptography.fernet import Fernet
        return VaultEncryption(master_key=Fernet.generate_key().decode())

    def test_generate_dek_returns_256_bit_key(self, encryption):
        """Should generate 256-bit DEK"""
        dek = encryption.generate_dek()
        assert isinstance(dek, bytes)
        assert len(dek) == 32  # 256 bits

    def test_deks_are_unique(self, encryption):
        """Each DEK should be unique"""
        deks = [encryption.generate_dek() for _ in range(10)]
        assert len(set(deks)) == 10  # All unique


class TestSecretEncryption:
    """Tests for secret encryption/decryption"""

    @pytest.fixture
    def encryption(self):
        """Create VaultEncryption instance"""
        from cryptography.fernet import Fernet
        return VaultEncryption(master_key=Fernet.generate_key().decode())

    def test_encrypt_returns_four_components(self, encryption):
        """Encryption should return 4 components"""
        user_id = EncryptionTestDataFactory.unique_user_id()
        secret = EncryptionTestDataFactory.api_key()
        result = encryption.encrypt_secret(secret, user_id)
        assert len(result) == 4
        encrypted_data, dek_encrypted, kek_salt, nonce = result
        assert isinstance(encrypted_data, bytes)
        assert isinstance(dek_encrypted, bytes)
        assert isinstance(kek_salt, bytes)
        assert isinstance(nonce, bytes)

    def test_encrypted_data_differs_from_plaintext(self, encryption):
        """Encrypted data should differ from plaintext"""
        user_id = EncryptionTestDataFactory.unique_user_id()
        secret = EncryptionTestDataFactory.api_key()
        encrypted_data, _, _, _ = encryption.encrypt_secret(secret, user_id)
        assert encrypted_data != secret.encode()

    def test_nonce_is_12_bytes(self, encryption):
        """Nonce should be 12 bytes (96 bits) for GCM"""
        user_id = EncryptionTestDataFactory.unique_user_id()
        secret = EncryptionTestDataFactory.unique_secret()
        _, _, _, nonce = encryption.encrypt_secret(secret, user_id)
        assert len(nonce) == 12

    def test_each_encryption_produces_different_result(self, encryption):
        """Same secret encrypted twice should produce different ciphertext"""
        user_id = EncryptionTestDataFactory.unique_user_id()
        secret = EncryptionTestDataFactory.api_key()
        result1 = encryption.encrypt_secret(secret, user_id)
        result2 = encryption.encrypt_secret(secret, user_id)
        # Different nonces mean different ciphertext
        assert result1[0] != result2[0]  # encrypted_data
        assert result1[3] != result2[3]  # nonce

    def test_encrypt_decrypt_roundtrip(self, encryption):
        """Encrypted secret should decrypt to original"""
        user_id = EncryptionTestDataFactory.unique_user_id()
        original_secret = EncryptionTestDataFactory.api_key()

        encrypted_data, dek_encrypted, kek_salt, nonce = encryption.encrypt_secret(
            original_secret, user_id
        )

        decrypted = encryption.decrypt_secret(
            encrypted_data, dek_encrypted, kek_salt, nonce, user_id
        )

        assert decrypted == original_secret

    def test_decrypt_with_wrong_user_fails(self, encryption):
        """Decryption with wrong user should fail"""
        user1 = EncryptionTestDataFactory.unique_user_id()
        user2 = EncryptionTestDataFactory.unique_user_id()
        secret = EncryptionTestDataFactory.api_key()

        encrypted_data, dek_encrypted, kek_salt, nonce = encryption.encrypt_secret(
            secret, user1
        )

        with pytest.raises(Exception):
            encryption.decrypt_secret(
                encrypted_data, dek_encrypted, kek_salt, nonce, user2
            )

    def test_decrypt_with_corrupted_data_fails(self, encryption):
        """Decryption with corrupted data should fail"""
        user_id = EncryptionTestDataFactory.unique_user_id()
        secret = EncryptionTestDataFactory.api_key()

        encrypted_data, dek_encrypted, kek_salt, nonce = encryption.encrypt_secret(
            secret, user_id
        )

        # Corrupt the encrypted data
        corrupted_data = encrypted_data[:-1] + b'\x00'

        with pytest.raises(Exception):
            encryption.decrypt_secret(
                corrupted_data, dek_encrypted, kek_salt, nonce, user_id
            )

    @pytest.mark.parametrize("secret_length", [1, 10, 100, 1000, 10000])
    def test_various_secret_lengths(self, encryption, secret_length):
        """Should handle secrets of various lengths"""
        user_id = EncryptionTestDataFactory.unique_user_id()
        secret = "x" * secret_length

        encrypted_data, dek_encrypted, kek_salt, nonce = encryption.encrypt_secret(
            secret, user_id
        )

        decrypted = encryption.decrypt_secret(
            encrypted_data, dek_encrypted, kek_salt, nonce, user_id
        )

        assert decrypted == secret

    def test_unicode_secrets(self, encryption):
        """Should handle unicode secrets"""
        user_id = EncryptionTestDataFactory.unique_user_id()
        secret = "密码🔐日本語한국어"

        encrypted_data, dek_encrypted, kek_salt, nonce = encryption.encrypt_secret(
            secret, user_id
        )

        decrypted = encryption.decrypt_secret(
            encrypted_data, dek_encrypted, kek_salt, nonce, user_id
        )

        assert decrypted == secret


class TestDEKRotation:
    """Tests for DEK rotation"""

    @pytest.fixture
    def encryption(self):
        """Create VaultEncryption instance"""
        from cryptography.fernet import Fernet
        return VaultEncryption(master_key=Fernet.generate_key().decode())

    def test_rotate_dek_preserves_plaintext(self, encryption):
        """DEK rotation should preserve plaintext"""
        user_id = EncryptionTestDataFactory.unique_user_id()
        original_secret = EncryptionTestDataFactory.api_key()

        # Initial encryption
        encrypted_data, dek_encrypted, kek_salt, nonce = encryption.encrypt_secret(
            original_secret, user_id
        )

        # Rotate DEK
        new_encrypted_data, new_dek_encrypted, new_nonce = encryption.rotate_dek(
            encrypted_data, dek_encrypted, kek_salt, nonce, user_id
        )

        # Decrypt with new components
        decrypted = encryption.decrypt_secret(
            new_encrypted_data, new_dek_encrypted, kek_salt, new_nonce, user_id
        )

        assert decrypted == original_secret

    def test_rotate_dek_changes_encrypted_data(self, encryption):
        """DEK rotation should change encrypted data"""
        user_id = EncryptionTestDataFactory.unique_user_id()
        secret = EncryptionTestDataFactory.api_key()

        encrypted_data, dek_encrypted, kek_salt, nonce = encryption.encrypt_secret(
            secret, user_id
        )

        new_encrypted_data, new_dek_encrypted, new_nonce = encryption.rotate_dek(
            encrypted_data, dek_encrypted, kek_salt, nonce, user_id
        )

        assert new_encrypted_data != encrypted_data
        assert new_dek_encrypted != dek_encrypted
        assert new_nonce != nonce


class TestBlockchainHashing:
    """Tests for blockchain hash functions"""

    @pytest.fixture
    def encryption(self):
        """Create VaultEncryption instance"""
        from cryptography.fernet import Fernet
        return VaultEncryption(master_key=Fernet.generate_key().decode())

    def test_hash_returns_hex_string(self, encryption):
        """Hash should return hex string"""
        secret = EncryptionTestDataFactory.api_key()
        hash_value = encryption.hash_secret_for_blockchain(secret)
        assert isinstance(hash_value, str)
        assert all(c in "0123456789abcdef" for c in hash_value)

    def test_hash_is_sha256_length(self, encryption):
        """Hash should be SHA-256 length (64 hex chars)"""
        secret = EncryptionTestDataFactory.api_key()
        hash_value = encryption.hash_secret_for_blockchain(secret)
        assert len(hash_value) == 64

    def test_same_secret_same_hash(self, encryption):
        """Same secret should produce same hash"""
        secret = EncryptionTestDataFactory.api_key()
        hash1 = encryption.hash_secret_for_blockchain(secret)
        hash2 = encryption.hash_secret_for_blockchain(secret)
        assert hash1 == hash2

    def test_different_secrets_different_hash(self, encryption):
        """Different secrets should produce different hashes"""
        secret1 = EncryptionTestDataFactory.api_key()
        secret2 = EncryptionTestDataFactory.api_key()
        hash1 = encryption.hash_secret_for_blockchain(secret1)
        hash2 = encryption.hash_secret_for_blockchain(secret2)
        assert hash1 != hash2

    def test_verify_hash_with_correct_secret(self, encryption):
        """Verification should pass with correct secret"""
        secret = EncryptionTestDataFactory.api_key()
        hash_value = encryption.hash_secret_for_blockchain(secret)
        assert encryption.verify_secret_hash(secret, hash_value) is True

    def test_verify_hash_with_wrong_secret(self, encryption):
        """Verification should fail with wrong secret"""
        secret = EncryptionTestDataFactory.api_key()
        wrong_secret = EncryptionTestDataFactory.api_key()
        hash_value = encryption.hash_secret_for_blockchain(secret)
        assert encryption.verify_secret_hash(wrong_secret, hash_value) is False


class TestAPIKeyGeneration:
    """Tests for API key generation"""

    def test_generate_api_key_default_prefix(self):
        """Should generate API key with default prefix"""
        key = VaultEncryption.generate_api_key()
        assert key.startswith("sk_")

    def test_generate_api_key_custom_prefix(self):
        """Should generate API key with custom prefix"""
        key = VaultEncryption.generate_api_key(prefix="test")
        assert key.startswith("test_")

    def test_generate_api_key_length(self):
        """Should generate key with specified length"""
        key = VaultEncryption.generate_api_key(length=16)
        # Length is for random part after prefix
        assert len(key) > 16

    def test_api_keys_are_unique(self):
        """Generated keys should be unique"""
        keys = [VaultEncryption.generate_api_key() for _ in range(100)]
        assert len(set(keys)) == 100

    def test_generate_encryption_key(self):
        """Should generate valid Fernet key"""
        key = VaultEncryption.generate_encryption_key()
        assert isinstance(key, str)
        # Should be base64 encoded
        decoded = base64.urlsafe_b64decode(key)
        assert len(decoded) == 32


# =============================================================================
# Helper Function Tests
# =============================================================================

class TestEncryptFieldHelper:
    """Tests for encrypt_field helper function"""

    @pytest.fixture
    def encryption(self):
        """Create VaultEncryption instance"""
        from cryptography.fernet import Fernet
        return VaultEncryption(master_key=Fernet.generate_key().decode())

    def test_encrypt_field_returns_dict(self, encryption):
        """Should return dict with all components"""
        user_id = EncryptionTestDataFactory.unique_user_id()
        value = EncryptionTestDataFactory.api_key()
        result = encrypt_field(value, encryption, user_id)
        assert isinstance(result, dict)
        assert "encrypted_value" in result
        assert "dek_encrypted" in result
        assert "kek_salt" in result
        assert "nonce" in result

    def test_encrypt_field_values_are_base64(self, encryption):
        """All values should be base64 encoded strings"""
        user_id = EncryptionTestDataFactory.unique_user_id()
        value = EncryptionTestDataFactory.api_key()
        result = encrypt_field(value, encryption, user_id)
        for key, val in result.items():
            assert isinstance(val, str)
            # Should be valid base64
            base64.b64decode(val)


class TestDecryptFieldHelper:
    """Tests for decrypt_field helper function"""

    @pytest.fixture
    def encryption(self):
        """Create VaultEncryption instance"""
        from cryptography.fernet import Fernet
        return VaultEncryption(master_key=Fernet.generate_key().decode())

    def test_decrypt_field_roundtrip(self, encryption):
        """encrypt_field -> decrypt_field should preserve value"""
        user_id = EncryptionTestDataFactory.unique_user_id()
        original_value = EncryptionTestDataFactory.api_key()

        encrypted = encrypt_field(original_value, encryption, user_id)
        decrypted = decrypt_field(encrypted, encryption, user_id)

        assert decrypted == original_value
