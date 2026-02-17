"""
Vault Service Integration Tests

Tests with real database operations via PostgreSQL gRPC.
"""
import pytest
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from microservices.vault_service.models import (
    SecretType,
    SecretProvider,
    EncryptionMethod,
    VaultAction,
    PermissionLevel,
    VaultItem,
    VaultAccessLog,
    VaultShare,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# =============================================================================
# Test Data Factory
# =============================================================================

class VaultIntegrationTestDataFactory:
    """Factory for generating integration test data"""

    @staticmethod
    def unique_id() -> str:
        return uuid.uuid4().hex[:8]

    @staticmethod
    def user_id() -> str:
        return f"integ_user_{VaultIntegrationTestDataFactory.unique_id()}"

    @staticmethod
    def vault_id() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def org_id() -> str:
        return f"integ_org_{VaultIntegrationTestDataFactory.unique_id()}"

    @staticmethod
    def secret_name() -> str:
        return f"integ_secret_{VaultIntegrationTestDataFactory.unique_id()}"

    @staticmethod
    def vault_item(
        user_id: Optional[str] = None,
        secret_type: SecretType = SecretType.API_KEY,
        **kwargs
    ) -> VaultItem:
        """Generate VaultItem for testing"""
        return VaultItem(
            user_id=user_id or VaultIntegrationTestDataFactory.user_id(),
            organization_id=kwargs.get("organization_id"),
            secret_type=secret_type,
            provider=kwargs.get("provider"),
            name=kwargs.get("name", VaultIntegrationTestDataFactory.secret_name()),
            description=kwargs.get("description"),
            encrypted_value=kwargs.get("encrypted_value", b"test_encrypted_data"),
            encryption_method=kwargs.get("encryption_method", EncryptionMethod.AES_256_GCM),
            encryption_key_id=kwargs.get("encryption_key_id", f"kek_{VaultIntegrationTestDataFactory.unique_id()}"),
            metadata=kwargs.get("metadata", {
                "dek_encrypted": "mock_dek_base64",
                "kek_salt": "mock_salt_base64",
                "nonce": "mock_nonce_base64",
            }),
            tags=kwargs.get("tags", []),
            version=kwargs.get("version", 1),
            expires_at=kwargs.get("expires_at"),
            rotation_enabled=kwargs.get("rotation_enabled", False),
            rotation_days=kwargs.get("rotation_days"),
            blockchain_reference=kwargs.get("blockchain_reference"),
        )

    @staticmethod
    def access_log(
        vault_id: str,
        user_id: str,
        action: VaultAction = VaultAction.READ,
        **kwargs
    ) -> VaultAccessLog:
        """Generate VaultAccessLog for testing"""
        return VaultAccessLog(
            vault_id=vault_id,
            user_id=user_id,
            action=action,
            ip_address=kwargs.get("ip_address", "127.0.0.1"),
            user_agent=kwargs.get("user_agent", "IntegrationTest/1.0"),
            success=kwargs.get("success", True),
            error_message=kwargs.get("error_message"),
            metadata=kwargs.get("metadata", {}),
        )

    @staticmethod
    def share(
        vault_id: str,
        owner_user_id: str,
        shared_with_user_id: Optional[str] = None,
        **kwargs
    ) -> VaultShare:
        """Generate VaultShare for testing"""
        return VaultShare(
            vault_id=vault_id,
            owner_user_id=owner_user_id,
            shared_with_user_id=shared_with_user_id or VaultIntegrationTestDataFactory.user_id(),
            shared_with_org_id=kwargs.get("shared_with_org_id"),
            permission_level=kwargs.get("permission_level", PermissionLevel.READ),
            expires_at=kwargs.get("expires_at"),
        )


# =============================================================================
# Repository Fixture
# =============================================================================

@pytest.fixture
async def repository():
    """Create VaultRepository with real database connection"""
    from microservices.vault_service.vault_repository import VaultRepository
    repo = VaultRepository()
    yield repo


# =============================================================================
# Vault Item Repository Tests
# =============================================================================

class TestVaultItemRepository:
    """Integration tests for vault item operations"""

    async def test_create_vault_item(self, repository):
        """Should create vault item in database"""
        vault_item = VaultIntegrationTestDataFactory.vault_item()

        result = await repository.create_vault_item(vault_item)

        assert result is not None
        assert result.vault_id is not None
        assert result.user_id == vault_item.user_id
        assert result.name == vault_item.name

    async def test_get_vault_item(self, repository):
        """Should retrieve vault item from database"""
        vault_item = VaultIntegrationTestDataFactory.vault_item()
        created = await repository.create_vault_item(vault_item)

        result = await repository.get_vault_item(created.vault_id)

        assert result is not None
        assert result["vault_id"] == created.vault_id
        assert result["user_id"] == vault_item.user_id

    async def test_get_vault_item_not_found(self, repository):
        """Should return None for non-existent item"""
        result = await repository.get_vault_item(str(uuid.uuid4()))
        assert result is None

    async def test_list_user_vault_items(self, repository):
        """Should list user's vault items"""
        user_id = VaultIntegrationTestDataFactory.user_id()

        # Create multiple items
        for _ in range(3):
            vault_item = VaultIntegrationTestDataFactory.vault_item(user_id=user_id)
            await repository.create_vault_item(vault_item)

        results = await repository.list_user_vault_items(user_id)

        assert len(results) >= 3

    async def test_list_user_vault_items_with_type_filter(self, repository):
        """Should filter by secret type"""
        user_id = VaultIntegrationTestDataFactory.user_id()

        # Create items of different types
        await repository.create_vault_item(
            VaultIntegrationTestDataFactory.vault_item(user_id=user_id, secret_type=SecretType.API_KEY)
        )
        await repository.create_vault_item(
            VaultIntegrationTestDataFactory.vault_item(user_id=user_id, secret_type=SecretType.DATABASE_CREDENTIAL)
        )

        results = await repository.list_user_vault_items(user_id, secret_type=SecretType.API_KEY)

        for item in results:
            assert item.secret_type == SecretType.API_KEY

    async def test_list_user_vault_items_with_tags_filter(self, repository):
        """Should filter by tags"""
        user_id = VaultIntegrationTestDataFactory.user_id()
        unique_tag = f"tag_{VaultIntegrationTestDataFactory.unique_id()}"

        # Create items with specific tags
        await repository.create_vault_item(
            VaultIntegrationTestDataFactory.vault_item(user_id=user_id, tags=[unique_tag, "common"])
        )
        await repository.create_vault_item(
            VaultIntegrationTestDataFactory.vault_item(user_id=user_id, tags=["other"])
        )

        results = await repository.list_user_vault_items(user_id, tags=[unique_tag])

        assert len(results) >= 1
        for item in results:
            assert unique_tag in item.tags

    async def test_list_user_vault_items_pagination(self, repository):
        """Should support pagination"""
        user_id = VaultIntegrationTestDataFactory.user_id()

        # Create 5 items
        for _ in range(5):
            await repository.create_vault_item(
                VaultIntegrationTestDataFactory.vault_item(user_id=user_id)
            )

        # Get first page
        page1 = await repository.list_user_vault_items(user_id, limit=2, offset=0)
        # Get second page
        page2 = await repository.list_user_vault_items(user_id, limit=2, offset=2)

        assert len(page1) <= 2
        assert len(page2) <= 2
        # Verify different results
        if len(page1) > 0 and len(page2) > 0:
            assert page1[0].vault_id != page2[0].vault_id

    async def test_update_vault_item(self, repository):
        """Should update vault item"""
        vault_item = VaultIntegrationTestDataFactory.vault_item()
        created = await repository.create_vault_item(vault_item)

        new_name = f"updated_{VaultIntegrationTestDataFactory.unique_id()}"
        success = await repository.update_vault_item(created.vault_id, {"name": new_name})

        assert success is True

        updated = await repository.get_vault_item(created.vault_id)
        assert updated["name"] == new_name

    async def test_delete_vault_item(self, repository):
        """Should soft delete vault item"""
        vault_item = VaultIntegrationTestDataFactory.vault_item()
        created = await repository.create_vault_item(vault_item)

        success = await repository.delete_vault_item(created.vault_id)

        assert success is True

        deleted = await repository.get_vault_item(created.vault_id)
        assert deleted["is_active"] is False

    async def test_increment_access_count(self, repository):
        """Should increment access count"""
        vault_item = VaultIntegrationTestDataFactory.vault_item()
        created = await repository.create_vault_item(vault_item)

        initial = await repository.get_vault_item(created.vault_id)
        initial_count = initial["access_count"]

        success = await repository.increment_access_count(created.vault_id)

        assert success is True

        updated = await repository.get_vault_item(created.vault_id)
        assert updated["access_count"] == initial_count + 1


# =============================================================================
# Access Log Repository Tests
# =============================================================================

class TestAccessLogRepository:
    """Integration tests for access log operations"""

    async def test_create_access_log(self, repository):
        """Should create access log"""
        vault_item = VaultIntegrationTestDataFactory.vault_item()
        created_item = await repository.create_vault_item(vault_item)

        log = VaultIntegrationTestDataFactory.access_log(
            vault_id=created_item.vault_id,
            user_id=vault_item.user_id,
        )
        result = await repository.create_access_log(log)

        assert result is not None
        assert result.log_id is not None
        assert result.vault_id == created_item.vault_id

    async def test_get_access_logs(self, repository):
        """Should retrieve access logs"""
        vault_item = VaultIntegrationTestDataFactory.vault_item()
        created_item = await repository.create_vault_item(vault_item)

        # Create multiple logs
        for action in [VaultAction.CREATE, VaultAction.READ, VaultAction.UPDATE]:
            log = VaultIntegrationTestDataFactory.access_log(
                vault_id=created_item.vault_id,
                user_id=vault_item.user_id,
                action=action,
            )
            await repository.create_access_log(log)

        results = await repository.get_access_logs(
            vault_id=created_item.vault_id,
            user_id=vault_item.user_id,
        )

        assert len(results) >= 3

    async def test_get_access_logs_pagination(self, repository):
        """Should support pagination for logs"""
        vault_item = VaultIntegrationTestDataFactory.vault_item()
        created_item = await repository.create_vault_item(vault_item)

        # Create logs
        for _ in range(5):
            log = VaultIntegrationTestDataFactory.access_log(
                vault_id=created_item.vault_id,
                user_id=vault_item.user_id,
            )
            await repository.create_access_log(log)

        page1 = await repository.get_access_logs(limit=2, offset=0)
        page2 = await repository.get_access_logs(limit=2, offset=2)

        assert len(page1) <= 2
        assert len(page2) <= 2


# =============================================================================
# Share Repository Tests
# =============================================================================

class TestShareRepository:
    """Integration tests for share operations"""

    async def test_create_share(self, repository):
        """Should create share"""
        vault_item = VaultIntegrationTestDataFactory.vault_item()
        created_item = await repository.create_vault_item(vault_item)

        share = VaultIntegrationTestDataFactory.share(
            vault_id=created_item.vault_id,
            owner_user_id=vault_item.user_id,
        )
        result = await repository.create_share(share)

        assert result is not None
        assert result.share_id is not None
        assert result.vault_id == created_item.vault_id

    async def test_get_shares_for_vault(self, repository):
        """Should get shares for vault"""
        vault_item = VaultIntegrationTestDataFactory.vault_item()
        created_item = await repository.create_vault_item(vault_item)

        # Create shares
        for _ in range(2):
            share = VaultIntegrationTestDataFactory.share(
                vault_id=created_item.vault_id,
                owner_user_id=vault_item.user_id,
            )
            await repository.create_share(share)

        results = await repository.get_shares_for_vault(created_item.vault_id)

        assert len(results) >= 2

    async def test_get_shares_for_user(self, repository):
        """Should get shares for user"""
        owner_id = VaultIntegrationTestDataFactory.user_id()
        recipient_id = VaultIntegrationTestDataFactory.user_id()

        vault_item = VaultIntegrationTestDataFactory.vault_item(user_id=owner_id)
        created_item = await repository.create_vault_item(vault_item)

        share = VaultIntegrationTestDataFactory.share(
            vault_id=created_item.vault_id,
            owner_user_id=owner_id,
            shared_with_user_id=recipient_id,
        )
        await repository.create_share(share)

        results = await repository.get_shares_for_user(recipient_id)

        assert len(results) >= 1
        assert any(s.shared_with_user_id == recipient_id for s in results)

    async def test_revoke_share(self, repository):
        """Should revoke share"""
        vault_item = VaultIntegrationTestDataFactory.vault_item()
        created_item = await repository.create_vault_item(vault_item)

        share = VaultIntegrationTestDataFactory.share(
            vault_id=created_item.vault_id,
            owner_user_id=vault_item.user_id,
        )
        created_share = await repository.create_share(share)

        success = await repository.revoke_share(created_share.share_id)

        assert success is True

        # Verify share is inactive
        shares = await repository.get_shares_for_vault(created_item.vault_id)
        revoked = [s for s in shares if s.share_id == created_share.share_id]
        assert len(revoked) == 0  # Inactive shares not returned

    async def test_check_user_access_owner(self, repository):
        """Should return owner for vault owner"""
        vault_item = VaultIntegrationTestDataFactory.vault_item()
        created_item = await repository.create_vault_item(vault_item)

        permission = await repository.check_user_access(created_item.vault_id, vault_item.user_id)

        assert permission == "owner"

    async def test_check_user_access_shared(self, repository):
        """Should return permission level for shared user"""
        owner_id = VaultIntegrationTestDataFactory.user_id()
        recipient_id = VaultIntegrationTestDataFactory.user_id()

        vault_item = VaultIntegrationTestDataFactory.vault_item(user_id=owner_id)
        created_item = await repository.create_vault_item(vault_item)

        share = VaultIntegrationTestDataFactory.share(
            vault_id=created_item.vault_id,
            owner_user_id=owner_id,
            shared_with_user_id=recipient_id,
            permission_level=PermissionLevel.READ_WRITE,
        )
        await repository.create_share(share)

        permission = await repository.check_user_access(created_item.vault_id, recipient_id)

        assert permission == "read_write"

    async def test_check_user_access_no_permission(self, repository):
        """Should return None for unauthorized user"""
        vault_item = VaultIntegrationTestDataFactory.vault_item()
        created_item = await repository.create_vault_item(vault_item)

        other_user_id = VaultIntegrationTestDataFactory.user_id()
        permission = await repository.check_user_access(created_item.vault_id, other_user_id)

        assert permission is None


# =============================================================================
# Statistics Repository Tests
# =============================================================================

class TestStatisticsRepository:
    """Integration tests for statistics operations"""

    async def test_get_vault_stats(self, repository):
        """Should return vault statistics"""
        user_id = VaultIntegrationTestDataFactory.user_id()

        # Create some items
        await repository.create_vault_item(
            VaultIntegrationTestDataFactory.vault_item(
                user_id=user_id,
                secret_type=SecretType.API_KEY,
            )
        )
        await repository.create_vault_item(
            VaultIntegrationTestDataFactory.vault_item(
                user_id=user_id,
                secret_type=SecretType.DATABASE_CREDENTIAL,
            )
        )

        stats = await repository.get_vault_stats(user_id)

        assert stats["total_secrets"] >= 2
        assert stats["active_secrets"] >= 2

    async def test_get_expiring_secrets(self, repository):
        """Should return secrets expiring soon"""
        user_id = VaultIntegrationTestDataFactory.user_id()

        # Create item expiring in 3 days
        expiring_soon = datetime.now(timezone.utc) + timedelta(days=3)
        await repository.create_vault_item(
            VaultIntegrationTestDataFactory.vault_item(
                user_id=user_id,
                expires_at=expiring_soon,
            )
        )

        results = await repository.get_expiring_secrets(user_id, days=7)

        assert len(results) >= 1


# =============================================================================
# GDPR Repository Tests
# =============================================================================

class TestGDPRRepository:
    """Integration tests for GDPR operations"""

    async def test_delete_user_data(self, repository):
        """Should delete all user data"""
        user_id = VaultIntegrationTestDataFactory.user_id()

        # Create items
        item1 = await repository.create_vault_item(
            VaultIntegrationTestDataFactory.vault_item(user_id=user_id)
        )
        item2 = await repository.create_vault_item(
            VaultIntegrationTestDataFactory.vault_item(user_id=user_id)
        )

        # Create logs
        await repository.create_access_log(
            VaultIntegrationTestDataFactory.access_log(
                vault_id=item1.vault_id, user_id=user_id
            )
        )

        # Delete user data
        deleted_count = await repository.delete_user_data(user_id)

        assert deleted_count >= 2

        # Verify items are deleted
        remaining = await repository.list_user_vault_items(user_id)
        assert len(remaining) == 0
