"""
Vault Service Component Tests

Tests VaultService business logic with mocked dependencies.
"""
import pytest
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from microservices.vault_service.vault_service import VaultService
from microservices.vault_service.models import (
    SecretType,
    SecretProvider,
    EncryptionMethod,
    VaultAction,
    PermissionLevel,
    VaultCreateRequest,
    VaultUpdateRequest,
    VaultShareRequest,
    VaultItemResponse,
    VaultSecretResponse,
    VaultShareResponse,
    VaultAccessLogResponse,
    VaultStatsResponse,
)

pytestmark = [pytest.mark.component, pytest.mark.asyncio]


# =============================================================================
# Test Data Factory
# =============================================================================

class VaultTestDataFactory:
    """Factory for generating test data"""

    @staticmethod
    def unique_id() -> str:
        return uuid.uuid4().hex[:8]

    @staticmethod
    def user_id() -> str:
        return f"user_{VaultTestDataFactory.unique_id()}"

    @staticmethod
    def vault_id() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def org_id() -> str:
        return f"org_{VaultTestDataFactory.unique_id()}"

    @staticmethod
    def secret_name() -> str:
        return f"secret_{VaultTestDataFactory.unique_id()}"

    @staticmethod
    def secret_value() -> str:
        return f"sk_test_{VaultTestDataFactory.unique_id()}"

    @staticmethod
    def create_request(**kwargs) -> VaultCreateRequest:
        """Generate vault create request"""
        return VaultCreateRequest(
            secret_type=kwargs.get("secret_type", SecretType.API_KEY),
            provider=kwargs.get("provider"),
            name=kwargs.get("name", VaultTestDataFactory.secret_name()),
            description=kwargs.get("description"),
            secret_value=kwargs.get("secret_value", VaultTestDataFactory.secret_value()),
            organization_id=kwargs.get("organization_id"),
            metadata=kwargs.get("metadata", {}),
            tags=kwargs.get("tags", []),
            expires_at=kwargs.get("expires_at"),
            rotation_enabled=kwargs.get("rotation_enabled", False),
            rotation_days=kwargs.get("rotation_days"),
            blockchain_verify=kwargs.get("blockchain_verify", False),
        )

    @staticmethod
    def vault_item_response(**kwargs) -> VaultItemResponse:
        """Generate vault item response"""
        now = datetime.now(timezone.utc)
        return VaultItemResponse(
            vault_id=kwargs.get("vault_id", VaultTestDataFactory.vault_id()),
            user_id=kwargs.get("user_id", VaultTestDataFactory.user_id()),
            organization_id=kwargs.get("organization_id"),
            secret_type=kwargs.get("secret_type", SecretType.API_KEY),
            provider=kwargs.get("provider"),
            name=kwargs.get("name", VaultTestDataFactory.secret_name()),
            description=kwargs.get("description"),
            encryption_method=kwargs.get("encryption_method", EncryptionMethod.AES_256_GCM),
            metadata=kwargs.get("metadata", {}),
            tags=kwargs.get("tags", []),
            version=kwargs.get("version", 1),
            expires_at=kwargs.get("expires_at"),
            last_accessed_at=kwargs.get("last_accessed_at"),
            access_count=kwargs.get("access_count", 0),
            is_active=kwargs.get("is_active", True),
            rotation_enabled=kwargs.get("rotation_enabled", False),
            rotation_days=kwargs.get("rotation_days"),
            blockchain_reference=kwargs.get("blockchain_reference"),
            created_at=kwargs.get("created_at", now),
            updated_at=kwargs.get("updated_at", now),
        )

    @staticmethod
    def vault_item_dict(**kwargs) -> Dict[str, Any]:
        """Generate vault item as dict (for repository mock)"""
        now = datetime.now(timezone.utc)
        return {
            "vault_id": kwargs.get("vault_id", VaultTestDataFactory.vault_id()),
            "user_id": kwargs.get("user_id", VaultTestDataFactory.user_id()),
            "organization_id": kwargs.get("organization_id"),
            "secret_type": kwargs.get("secret_type", SecretType.API_KEY.value),
            "provider": kwargs.get("provider"),
            "name": kwargs.get("name", VaultTestDataFactory.secret_name()),
            "description": kwargs.get("description"),
            "encrypted_value": kwargs.get("encrypted_value", "encrypted_base64_data"),
            "encryption_method": kwargs.get("encryption_method", EncryptionMethod.AES_256_GCM.value),
            "encryption_key_id": kwargs.get("encryption_key_id"),
            "metadata": kwargs.get("metadata", {
                "dek_encrypted": "mock_dek",
                "kek_salt": "mock_salt",
                "nonce": "mock_nonce",
            }),
            "tags": kwargs.get("tags", []),
            "version": kwargs.get("version", 1),
            "expires_at": kwargs.get("expires_at"),
            "last_accessed_at": kwargs.get("last_accessed_at"),
            "access_count": kwargs.get("access_count", 0),
            "is_active": kwargs.get("is_active", True),
            "rotation_enabled": kwargs.get("rotation_enabled", False),
            "rotation_days": kwargs.get("rotation_days"),
            "blockchain_reference": kwargs.get("blockchain_reference"),
            "created_at": kwargs.get("created_at", now.isoformat()),
            "updated_at": kwargs.get("updated_at", now.isoformat()),
        }


# =============================================================================
# Mock Dependencies
# =============================================================================

class MockVaultRepository:
    """Mock repository for testing"""

    def __init__(self):
        self.create_vault_item = AsyncMock()
        self.get_vault_item = AsyncMock()
        self.list_user_vault_items = AsyncMock(return_value=[])
        self.update_vault_item = AsyncMock(return_value=True)
        self.delete_vault_item = AsyncMock(return_value=True)
        self.increment_access_count = AsyncMock(return_value=True)
        self.create_access_log = AsyncMock()
        self.get_access_logs = AsyncMock(return_value=[])
        self.create_share = AsyncMock()
        self.get_shares_for_vault = AsyncMock(return_value=[])
        self.get_shares_for_user = AsyncMock(return_value=[])
        self.revoke_share = AsyncMock(return_value=True)
        self.check_user_access = AsyncMock(return_value="owner")
        self.get_vault_stats = AsyncMock(return_value={})
        self.get_expiring_secrets = AsyncMock(return_value=[])
        self.delete_user_data = AsyncMock(return_value=0)


class MockVaultEncryption:
    """Mock encryption for testing"""

    def __init__(self):
        self.encrypt_secret = MagicMock(return_value=(
            b"encrypted_data",
            b"encrypted_dek",
            b"kek_salt",
            b"nonce",
        ))
        self.decrypt_secret = MagicMock(return_value="decrypted_secret")
        self.hash_secret_for_blockchain = MagicMock(return_value="sha256_hash")
        self.verify_secret_hash = MagicMock(return_value=True)


class MockBlockchainIntegration:
    """Mock blockchain integration for testing"""

    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self.store_secret_hash = AsyncMock(return_value="tx_hash_123")
        self.verify_secret_from_blockchain = AsyncMock(return_value=True)
        self.get_integration_status = MagicMock(return_value={"enabled": enabled})


class MockEventBus:
    """Mock event bus for testing"""

    def __init__(self):
        self.publish_event = AsyncMock()


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_repository():
    """Create mock repository"""
    return MockVaultRepository()


@pytest.fixture
def mock_encryption():
    """Create mock encryption"""
    return MockVaultEncryption()


@pytest.fixture
def mock_blockchain():
    """Create mock blockchain integration"""
    return MockBlockchainIntegration(enabled=False)


@pytest.fixture
def mock_event_bus():
    """Create mock event bus"""
    return MockEventBus()


@pytest.fixture
def vault_service(mock_repository, mock_encryption, mock_blockchain, mock_event_bus):
    """Create VaultService with mocked dependencies"""
    return VaultService(
        repository=mock_repository,
        encryption=mock_encryption,
        blockchain=mock_blockchain,
        event_bus=mock_event_bus,
    )


# =============================================================================
# Create Secret Tests
# =============================================================================

class TestCreateSecret:
    """Tests for create_secret method"""

    async def test_create_secret_success(self, vault_service, mock_repository, mock_encryption):
        """Should create secret successfully"""
        user_id = VaultTestDataFactory.user_id()
        request = VaultTestDataFactory.create_request()
        expected_response = VaultTestDataFactory.vault_item_response(user_id=user_id)
        mock_repository.create_vault_item.return_value = expected_response

        success, result, message = await vault_service.create_secret(user_id, request)

        assert success is True
        assert result is not None
        assert "created successfully" in message
        mock_encryption.encrypt_secret.assert_called_once()
        mock_repository.create_vault_item.assert_called_once()

    async def test_create_secret_with_all_fields(self, vault_service, mock_repository):
        """Should create secret with all optional fields"""
        user_id = VaultTestDataFactory.user_id()
        request = VaultTestDataFactory.create_request(
            secret_type=SecretType.DATABASE_CREDENTIAL,
            provider=SecretProvider.AWS,
            description="Test credential",
            organization_id=VaultTestDataFactory.org_id(),
            metadata={"environment": "production"},
            tags=["prod", "database"],
            expires_at=datetime.now(timezone.utc) + timedelta(days=90),
            rotation_enabled=True,
            rotation_days=30,
        )
        expected_response = VaultTestDataFactory.vault_item_response(user_id=user_id)
        mock_repository.create_vault_item.return_value = expected_response

        success, result, message = await vault_service.create_secret(user_id, request)

        assert success is True

    async def test_create_secret_logs_access(self, vault_service, mock_repository):
        """Should log access on create"""
        user_id = VaultTestDataFactory.user_id()
        request = VaultTestDataFactory.create_request()
        expected_response = VaultTestDataFactory.vault_item_response(user_id=user_id)
        mock_repository.create_vault_item.return_value = expected_response

        await vault_service.create_secret(user_id, request, ip_address="127.0.0.1")

        mock_repository.create_access_log.assert_called()

    async def test_create_secret_publishes_event(self, vault_service, mock_repository, mock_event_bus):
        """Should publish event on create"""
        user_id = VaultTestDataFactory.user_id()
        request = VaultTestDataFactory.create_request()
        expected_response = VaultTestDataFactory.vault_item_response(user_id=user_id)
        mock_repository.create_vault_item.return_value = expected_response

        await vault_service.create_secret(user_id, request)

        mock_event_bus.publish_event.assert_called()

    async def test_create_secret_failure(self, vault_service, mock_repository):
        """Should handle repository failure"""
        user_id = VaultTestDataFactory.user_id()
        request = VaultTestDataFactory.create_request()
        mock_repository.create_vault_item.return_value = None

        success, result, message = await vault_service.create_secret(user_id, request)

        assert success is False
        assert result is None
        assert "Failed" in message


class TestCreateSecretWithBlockchain:
    """Tests for create_secret with blockchain verification"""

    @pytest.fixture
    def vault_service_with_blockchain(self, mock_repository, mock_encryption, mock_event_bus):
        """Create VaultService with blockchain enabled"""
        blockchain = MockBlockchainIntegration(enabled=True)
        return VaultService(
            repository=mock_repository,
            encryption=mock_encryption,
            blockchain=blockchain,
            event_bus=mock_event_bus,
        )

    async def test_create_with_blockchain_verification(
        self, vault_service_with_blockchain, mock_repository
    ):
        """Should store hash on blockchain when requested"""
        user_id = VaultTestDataFactory.user_id()
        request = VaultTestDataFactory.create_request(blockchain_verify=True)
        expected_response = VaultTestDataFactory.vault_item_response(user_id=user_id)
        mock_repository.create_vault_item.return_value = expected_response

        success, result, message = await vault_service_with_blockchain.create_secret(
            user_id, request
        )

        assert success is True


# =============================================================================
# Get Secret Tests
# =============================================================================

class TestGetSecret:
    """Tests for get_secret method"""

    async def test_get_secret_success(self, vault_service, mock_repository, mock_encryption):
        """Should get and decrypt secret"""
        user_id = VaultTestDataFactory.user_id()
        vault_id = VaultTestDataFactory.vault_id()
        item_dict = VaultTestDataFactory.vault_item_dict(vault_id=vault_id, user_id=user_id)
        mock_repository.get_vault_item.return_value = item_dict
        mock_encryption.decrypt_secret.return_value = "decrypted_value"

        success, result, message = await vault_service.get_secret(vault_id, user_id)

        assert success is True
        assert result is not None
        assert result.secret_value == "decrypted_value"
        mock_repository.increment_access_count.assert_called_with(vault_id)

    async def test_get_secret_without_decrypt(self, vault_service, mock_repository, mock_encryption):
        """Should return encrypted marker when decrypt=False"""
        user_id = VaultTestDataFactory.user_id()
        vault_id = VaultTestDataFactory.vault_id()
        item_dict = VaultTestDataFactory.vault_item_dict(vault_id=vault_id, user_id=user_id)
        mock_repository.get_vault_item.return_value = item_dict

        success, result, message = await vault_service.get_secret(vault_id, user_id, decrypt=False)

        assert success is True
        assert result.secret_value == "[ENCRYPTED]"
        mock_encryption.decrypt_secret.assert_not_called()

    async def test_get_secret_access_denied(self, vault_service, mock_repository):
        """Should deny access when user has no permission"""
        user_id = VaultTestDataFactory.user_id()
        vault_id = VaultTestDataFactory.vault_id()
        mock_repository.check_user_access.return_value = None

        success, result, message = await vault_service.get_secret(vault_id, user_id)

        assert success is False
        assert "Access denied" in message

    async def test_get_secret_not_found(self, vault_service, mock_repository):
        """Should handle secret not found"""
        user_id = VaultTestDataFactory.user_id()
        vault_id = VaultTestDataFactory.vault_id()
        mock_repository.check_user_access.return_value = "owner"
        mock_repository.get_vault_item.return_value = None

        success, result, message = await vault_service.get_secret(vault_id, user_id)

        assert success is False
        assert "not found" in message

    async def test_get_secret_inactive(self, vault_service, mock_repository):
        """Should reject inactive secret"""
        user_id = VaultTestDataFactory.user_id()
        vault_id = VaultTestDataFactory.vault_id()
        item_dict = VaultTestDataFactory.vault_item_dict(
            vault_id=vault_id, user_id=user_id, is_active=False
        )
        mock_repository.get_vault_item.return_value = item_dict

        success, result, message = await vault_service.get_secret(vault_id, user_id)

        assert success is False
        assert "inactive" in message

    async def test_get_secret_expired(self, vault_service, mock_repository):
        """Should reject expired secret"""
        user_id = VaultTestDataFactory.user_id()
        vault_id = VaultTestDataFactory.vault_id()
        expired_time = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        item_dict = VaultTestDataFactory.vault_item_dict(
            vault_id=vault_id, user_id=user_id, expires_at=expired_time
        )
        mock_repository.get_vault_item.return_value = item_dict

        success, result, message = await vault_service.get_secret(vault_id, user_id)

        assert success is False
        assert "expired" in message

    async def test_get_secret_logs_access(self, vault_service, mock_repository):
        """Should log access attempt"""
        user_id = VaultTestDataFactory.user_id()
        vault_id = VaultTestDataFactory.vault_id()
        item_dict = VaultTestDataFactory.vault_item_dict(vault_id=vault_id, user_id=user_id)
        mock_repository.get_vault_item.return_value = item_dict

        await vault_service.get_secret(vault_id, user_id)

        mock_repository.create_access_log.assert_called()


# =============================================================================
# Update Secret Tests
# =============================================================================

class TestUpdateSecret:
    """Tests for update_secret method"""

    async def test_update_secret_success(self, vault_service, mock_repository):
        """Should update secret successfully"""
        user_id = VaultTestDataFactory.user_id()
        vault_id = VaultTestDataFactory.vault_id()
        mock_repository.check_user_access.return_value = "owner"
        item_dict = VaultTestDataFactory.vault_item_dict(vault_id=vault_id, user_id=user_id)
        mock_repository.get_vault_item.return_value = item_dict

        request = VaultUpdateRequest(name="new_name")
        success, result, message = await vault_service.update_secret(vault_id, user_id, request)

        assert success is True
        mock_repository.update_vault_item.assert_called()

    async def test_update_secret_with_new_value(self, vault_service, mock_repository, mock_encryption):
        """Should re-encrypt when secret value changes"""
        user_id = VaultTestDataFactory.user_id()
        vault_id = VaultTestDataFactory.vault_id()
        mock_repository.check_user_access.return_value = "owner"
        item_dict = VaultTestDataFactory.vault_item_dict(vault_id=vault_id, user_id=user_id)
        mock_repository.get_vault_item.return_value = item_dict

        request = VaultUpdateRequest(secret_value="new_secret_value")
        await vault_service.update_secret(vault_id, user_id, request)

        mock_encryption.encrypt_secret.assert_called()

    async def test_update_secret_access_denied(self, vault_service, mock_repository):
        """Should deny update without permission"""
        user_id = VaultTestDataFactory.user_id()
        vault_id = VaultTestDataFactory.vault_id()
        mock_repository.check_user_access.return_value = "read"

        request = VaultUpdateRequest(name="new_name")
        success, result, message = await vault_service.update_secret(vault_id, user_id, request)

        assert success is False
        assert "Access denied" in message

    async def test_update_secret_read_write_permission(self, vault_service, mock_repository):
        """Should allow update with read_write permission"""
        user_id = VaultTestDataFactory.user_id()
        vault_id = VaultTestDataFactory.vault_id()
        mock_repository.check_user_access.return_value = "read_write"
        item_dict = VaultTestDataFactory.vault_item_dict(vault_id=vault_id, user_id=user_id)
        mock_repository.get_vault_item.return_value = item_dict

        request = VaultUpdateRequest(name="new_name")
        success, result, message = await vault_service.update_secret(vault_id, user_id, request)

        assert success is True


# =============================================================================
# Delete Secret Tests
# =============================================================================

class TestDeleteSecret:
    """Tests for delete_secret method"""

    async def test_delete_secret_success(self, vault_service, mock_repository):
        """Should delete secret successfully"""
        user_id = VaultTestDataFactory.user_id()
        vault_id = VaultTestDataFactory.vault_id()
        item_dict = VaultTestDataFactory.vault_item_dict(vault_id=vault_id, user_id=user_id)
        mock_repository.get_vault_item.return_value = item_dict

        success, message = await vault_service.delete_secret(vault_id, user_id)

        assert success is True
        assert "deleted successfully" in message
        mock_repository.delete_vault_item.assert_called_with(vault_id)

    async def test_delete_secret_access_denied(self, vault_service, mock_repository):
        """Should deny delete to non-owner"""
        owner_id = VaultTestDataFactory.user_id()
        other_user_id = VaultTestDataFactory.user_id()
        vault_id = VaultTestDataFactory.vault_id()
        item_dict = VaultTestDataFactory.vault_item_dict(vault_id=vault_id, user_id=owner_id)
        mock_repository.get_vault_item.return_value = item_dict

        success, message = await vault_service.delete_secret(vault_id, other_user_id)

        assert success is False
        assert "Access denied" in message

    async def test_delete_secret_publishes_event(self, vault_service, mock_repository, mock_event_bus):
        """Should publish event on delete"""
        user_id = VaultTestDataFactory.user_id()
        vault_id = VaultTestDataFactory.vault_id()
        item_dict = VaultTestDataFactory.vault_item_dict(vault_id=vault_id, user_id=user_id)
        mock_repository.get_vault_item.return_value = item_dict

        await vault_service.delete_secret(vault_id, user_id)

        mock_event_bus.publish_event.assert_called()


# =============================================================================
# List Secrets Tests
# =============================================================================

class TestListSecrets:
    """Tests for list_secrets method"""

    async def test_list_secrets_empty(self, vault_service, mock_repository):
        """Should return empty list when no secrets"""
        user_id = VaultTestDataFactory.user_id()
        mock_repository.list_user_vault_items.return_value = []

        success, result, message = await vault_service.list_secrets(user_id)

        assert success is True
        assert result.items == []
        assert result.total == 0

    async def test_list_secrets_with_items(self, vault_service, mock_repository):
        """Should return list with items"""
        user_id = VaultTestDataFactory.user_id()
        items = [
            VaultTestDataFactory.vault_item_response(user_id=user_id),
            VaultTestDataFactory.vault_item_response(user_id=user_id),
        ]
        mock_repository.list_user_vault_items.return_value = items

        success, result, message = await vault_service.list_secrets(user_id)

        assert success is True
        assert len(result.items) == 2
        assert result.total == 2

    async def test_list_secrets_with_filters(self, vault_service, mock_repository):
        """Should pass filters to repository"""
        user_id = VaultTestDataFactory.user_id()
        mock_repository.list_user_vault_items.return_value = []

        await vault_service.list_secrets(
            user_id,
            secret_type=SecretType.API_KEY,
            tags=["prod"],
            page=2,
            page_size=25,
        )

        mock_repository.list_user_vault_items.assert_called_with(
            user_id=user_id,
            secret_type=SecretType.API_KEY,
            tags=["prod"],
            active_only=True,
            limit=25,
            offset=25,
        )


# =============================================================================
# Share Secret Tests
# =============================================================================

class TestShareSecret:
    """Tests for share_secret method"""

    async def test_share_secret_success(self, vault_service, mock_repository):
        """Should share secret successfully"""
        owner_id = VaultTestDataFactory.user_id()
        recipient_id = VaultTestDataFactory.user_id()
        vault_id = VaultTestDataFactory.vault_id()
        item_dict = VaultTestDataFactory.vault_item_dict(vault_id=vault_id, user_id=owner_id)
        mock_repository.get_vault_item.return_value = item_dict
        share_response = VaultShareResponse(
            share_id=str(uuid.uuid4()),
            vault_id=vault_id,
            owner_user_id=owner_id,
            shared_with_user_id=recipient_id,
            permission_level=PermissionLevel.READ,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        mock_repository.create_share.return_value = share_response

        request = VaultShareRequest(shared_with_user_id=recipient_id)
        success, result, message = await vault_service.share_secret(vault_id, owner_id, request)

        assert success is True
        assert result is not None
        assert "shared successfully" in message

    async def test_share_secret_access_denied(self, vault_service, mock_repository):
        """Should deny share to non-owner"""
        owner_id = VaultTestDataFactory.user_id()
        other_user_id = VaultTestDataFactory.user_id()
        vault_id = VaultTestDataFactory.vault_id()
        item_dict = VaultTestDataFactory.vault_item_dict(vault_id=vault_id, user_id=owner_id)
        mock_repository.get_vault_item.return_value = item_dict

        request = VaultShareRequest(shared_with_user_id=VaultTestDataFactory.user_id())
        success, result, message = await vault_service.share_secret(vault_id, other_user_id, request)

        assert success is False
        assert "Access denied" in message


# =============================================================================
# Get Shared Secrets Tests
# =============================================================================

class TestGetSharedSecrets:
    """Tests for get_shared_secrets method"""

    async def test_get_shared_secrets_empty(self, vault_service, mock_repository):
        """Should return empty list when no shares"""
        user_id = VaultTestDataFactory.user_id()
        mock_repository.get_shares_for_user.return_value = []

        success, result, message = await vault_service.get_shared_secrets(user_id)

        assert success is True
        assert result == []

    async def test_get_shared_secrets_with_items(self, vault_service, mock_repository):
        """Should return shared secrets"""
        user_id = VaultTestDataFactory.user_id()
        shares = [
            VaultShareResponse(
                share_id=str(uuid.uuid4()),
                vault_id=VaultTestDataFactory.vault_id(),
                owner_user_id=VaultTestDataFactory.user_id(),
                shared_with_user_id=user_id,
                permission_level=PermissionLevel.READ,
                is_active=True,
                created_at=datetime.now(timezone.utc),
            ),
        ]
        mock_repository.get_shares_for_user.return_value = shares

        success, result, message = await vault_service.get_shared_secrets(user_id)

        assert success is True
        assert len(result) == 1


# =============================================================================
# Rotate Secret Tests
# =============================================================================

class TestRotateSecret:
    """Tests for rotate_secret method"""

    async def test_rotate_secret_success(self, vault_service, mock_repository, mock_encryption):
        """Should rotate secret successfully"""
        user_id = VaultTestDataFactory.user_id()
        vault_id = VaultTestDataFactory.vault_id()
        mock_repository.check_user_access.return_value = "owner"
        item_dict = VaultTestDataFactory.vault_item_dict(vault_id=vault_id, user_id=user_id)
        mock_repository.get_vault_item.return_value = item_dict

        success, result, message = await vault_service.rotate_secret(
            vault_id, user_id, "new_secret_value"
        )

        assert success is True
        mock_encryption.encrypt_secret.assert_called()


# =============================================================================
# Get Access Logs Tests
# =============================================================================

class TestGetAccessLogs:
    """Tests for get_access_logs method"""

    async def test_get_access_logs_empty(self, vault_service, mock_repository):
        """Should return empty list when no logs"""
        user_id = VaultTestDataFactory.user_id()
        mock_repository.get_access_logs.return_value = []

        success, result, message = await vault_service.get_access_logs(user_id)

        assert success is True
        assert result == []

    async def test_get_access_logs_with_vault_filter(self, vault_service, mock_repository):
        """Should pass vault_id filter to repository"""
        user_id = VaultTestDataFactory.user_id()
        vault_id = VaultTestDataFactory.vault_id()
        mock_repository.get_access_logs.return_value = []

        await vault_service.get_access_logs(user_id, vault_id=vault_id)

        mock_repository.get_access_logs.assert_called_with(vault_id, user_id, 100, 0)


# =============================================================================
# Get Stats Tests
# =============================================================================

class TestGetStats:
    """Tests for get_stats method"""

    async def test_get_stats_success(self, vault_service, mock_repository):
        """Should return statistics"""
        user_id = VaultTestDataFactory.user_id()
        mock_repository.get_vault_stats.return_value = {
            "total_secrets": 10,
            "active_secrets": 8,
            "expired_secrets": 2,
            "secrets_by_type": {"api_key": 5, "database_credential": 5},
            "secrets_by_provider": {"aws": 3},
            "total_access_count": 100,
            "blockchain_verified_secrets": 1,
        }

        success, result, message = await vault_service.get_stats(user_id)

        assert success is True
        assert result.total_secrets == 10
        assert result.active_secrets == 8


# =============================================================================
# Test Credential Tests
# =============================================================================

class TestTestCredential:
    """Tests for test_credential method"""

    async def test_credential_success(self, vault_service, mock_repository, mock_encryption):
        """Should test credential successfully"""
        user_id = VaultTestDataFactory.user_id()
        vault_id = VaultTestDataFactory.vault_id()
        mock_repository.check_user_access.return_value = "owner"
        item_dict = VaultTestDataFactory.vault_item_dict(vault_id=vault_id, user_id=user_id)
        mock_repository.get_vault_item.return_value = item_dict

        success, result, message = await vault_service.test_credential(vault_id, user_id)

        assert success is True
        assert result.success is True


# =============================================================================
# Health Check Tests
# =============================================================================

class TestHealthCheck:
    """Tests for health_check method"""

    async def test_health_check(self, vault_service):
        """Should return health status"""
        result = await vault_service.health_check()

        assert result["status"] == "healthy"
        assert "encryption" in result
        assert "blockchain" in result
        assert "timestamp" in result
