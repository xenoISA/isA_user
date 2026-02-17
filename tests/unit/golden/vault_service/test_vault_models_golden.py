"""
Unit Golden Tests: Vault Service Models

Tests model validation and serialization without external dependencies.
"""
import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from microservices.vault_service.models import (
    SecretType,
    SecretProvider,
    EncryptionMethod,
    VaultAction,
    PermissionLevel,
    VaultItem,
    VaultAccessLog,
    VaultShare,
    VaultCreateRequest,
    VaultUpdateRequest,
    VaultShareRequest,
    VaultTestRequest,
    VaultItemResponse,
    VaultSecretResponse,
    VaultListResponse,
    VaultShareResponse,
    VaultAccessLogResponse,
    VaultStatsResponse,
    VaultTestResponse,
    HealthResponse,
    ServiceInfo,
)


class TestSecretTypeEnum:
    """Test SecretType enum"""

    def test_secret_type_values(self):
        """Test all secret type values are defined"""
        assert SecretType.API_KEY == "api_key"
        assert SecretType.DATABASE_CREDENTIAL == "database_credential"
        assert SecretType.SSH_KEY == "ssh_key"
        assert SecretType.SSL_CERTIFICATE == "ssl_certificate"
        assert SecretType.OAUTH_TOKEN == "oauth_token"
        assert SecretType.AWS_CREDENTIAL == "aws_credential"
        assert SecretType.BLOCKCHAIN_KEY == "blockchain_key"
        assert SecretType.ENVIRONMENT_VARIABLE == "environment_variable"
        assert SecretType.CUSTOM == "custom"

    def test_secret_type_comparison(self):
        """Test secret type comparison"""
        assert SecretType.API_KEY != SecretType.DATABASE_CREDENTIAL
        assert SecretType.API_KEY == SecretType.API_KEY
        assert SecretType.API_KEY.value == "api_key"


class TestSecretProviderEnum:
    """Test SecretProvider enum"""

    def test_secret_provider_values(self):
        """Test all secret provider values are defined"""
        assert SecretProvider.OPENAI == "openai"
        assert SecretProvider.ANTHROPIC == "anthropic"
        assert SecretProvider.STRIPE == "stripe"
        assert SecretProvider.AWS == "aws"
        assert SecretProvider.AZURE == "azure"
        assert SecretProvider.GCP == "gcp"
        assert SecretProvider.GITHUB == "github"
        assert SecretProvider.GITLAB == "gitlab"
        assert SecretProvider.ETHEREUM == "ethereum"
        assert SecretProvider.POLYGON == "polygon"
        assert SecretProvider.CUSTOM == "custom"

    def test_secret_provider_blockchain_providers(self):
        """Test blockchain-specific providers"""
        assert SecretProvider.ETHEREUM == "ethereum"
        assert SecretProvider.POLYGON == "polygon"


class TestEncryptionMethodEnum:
    """Test EncryptionMethod enum"""

    def test_encryption_method_values(self):
        """Test all encryption method values are defined"""
        assert EncryptionMethod.AES_256_GCM == "aes_256_gcm"
        assert EncryptionMethod.FERNET == "fernet"
        assert EncryptionMethod.BLOCKCHAIN_ENCRYPTED == "blockchain_encrypted"

    def test_encryption_method_default(self):
        """Test default encryption method"""
        # AES_256_GCM is the default
        assert EncryptionMethod.AES_256_GCM == "aes_256_gcm"


class TestVaultActionEnum:
    """Test VaultAction enum"""

    def test_vault_action_values(self):
        """Test all vault action values are defined"""
        assert VaultAction.CREATE == "create"
        assert VaultAction.READ == "read"
        assert VaultAction.UPDATE == "update"
        assert VaultAction.DELETE == "delete"
        assert VaultAction.ROTATE == "rotate"
        assert VaultAction.SHARE == "share"
        assert VaultAction.REVOKE_SHARE == "revoke_share"
        assert VaultAction.EXPORT == "export"
        assert VaultAction.IMPORT == "import"

    def test_vault_action_comparison(self):
        """Test vault action comparison"""
        assert VaultAction.READ != VaultAction.WRITE if hasattr(VaultAction, 'WRITE') else VaultAction.READ != VaultAction.UPDATE
        assert VaultAction.CREATE == VaultAction.CREATE


class TestPermissionLevelEnum:
    """Test PermissionLevel enum"""

    def test_permission_level_values(self):
        """Test all permission level values are defined"""
        assert PermissionLevel.READ == "read"
        assert PermissionLevel.READ_WRITE == "read_write"

    def test_permission_level_hierarchy(self):
        """Test permission level hierarchy"""
        # READ_WRITE includes READ permissions
        assert PermissionLevel.READ != PermissionLevel.READ_WRITE
        assert PermissionLevel.READ.value == "read"
        assert PermissionLevel.READ_WRITE.value == "read_write"


class TestVaultItemModel:
    """Test VaultItem model validation"""

    def test_vault_item_creation_minimal(self):
        """Test creating vault item with minimal required fields"""
        item = VaultItem(
            user_id="user_123",
            secret_type=SecretType.API_KEY,
            name="My API Key",
        )

        assert item.user_id == "user_123"
        assert item.secret_type == SecretType.API_KEY
        assert item.name == "My API Key"
        assert item.encryption_method == EncryptionMethod.AES_256_GCM
        assert item.version == 1
        assert item.is_active is True
        assert item.rotation_enabled is False
        assert item.access_count == 0
        assert item.metadata == {}
        assert item.tags == []

    def test_vault_item_with_all_fields(self):
        """Test creating vault item with all fields"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=30)

        item = VaultItem(
            vault_id="vault_123",
            user_id="user_456",
            organization_id="org_789",
            secret_type=SecretType.DATABASE_CREDENTIAL,
            provider=SecretProvider.AWS,
            name="Production Database",
            description="Main production database credentials",
            encrypted_value=b"encrypted_bytes_here",
            encryption_method=EncryptionMethod.AES_256_GCM,
            encryption_key_id="key_123",
            metadata={"env": "production", "region": "us-east-1"},
            tags=["production", "database", "aws"],
            version=2,
            expires_at=future,
            last_accessed_at=now,
            access_count=42,
            is_active=True,
            rotation_enabled=True,
            rotation_days=90,
            blockchain_reference="0x1234567890abcdef",
            created_at=now,
            updated_at=now,
        )

        assert item.vault_id == "vault_123"
        assert item.user_id == "user_456"
        assert item.organization_id == "org_789"
        assert item.secret_type == SecretType.DATABASE_CREDENTIAL
        assert item.provider == SecretProvider.AWS
        assert item.name == "Production Database"
        assert item.description == "Main production database credentials"
        assert item.encrypted_value == b"encrypted_bytes_here"
        assert item.encryption_method == EncryptionMethod.AES_256_GCM
        assert item.encryption_key_id == "key_123"
        assert item.metadata["env"] == "production"
        assert len(item.tags) == 3
        assert item.version == 2
        assert item.expires_at == future
        assert item.access_count == 42
        assert item.rotation_enabled is True
        assert item.rotation_days == 90
        assert item.blockchain_reference == "0x1234567890abcdef"

    def test_vault_item_with_blockchain_key(self):
        """Test vault item with blockchain key type"""
        item = VaultItem(
            user_id="user_123",
            secret_type=SecretType.BLOCKCHAIN_KEY,
            provider=SecretProvider.ETHEREUM,
            name="Ethereum Private Key",
            blockchain_reference="0xabcdef1234567890",
        )

        assert item.secret_type == SecretType.BLOCKCHAIN_KEY
        assert item.provider == SecretProvider.ETHEREUM
        assert item.blockchain_reference == "0xabcdef1234567890"

    def test_vault_item_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            VaultItem(user_id="user_123")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "secret_type" in missing_fields
        assert "name" in missing_fields

    def test_vault_item_with_organization(self):
        """Test vault item for organization-wide secret"""
        item = VaultItem(
            user_id="admin_123",
            organization_id="org_456",
            secret_type=SecretType.API_KEY,
            name="Org Stripe Key",
            provider=SecretProvider.STRIPE,
        )

        assert item.organization_id == "org_456"
        assert item.provider == SecretProvider.STRIPE


class TestVaultAccessLogModel:
    """Test VaultAccessLog model validation"""

    def test_access_log_creation_minimal(self):
        """Test creating access log with minimal fields"""
        log = VaultAccessLog(
            vault_id="vault_123",
            user_id="user_456",
            action=VaultAction.READ,
        )

        assert log.vault_id == "vault_123"
        assert log.user_id == "user_456"
        assert log.action == VaultAction.READ
        assert log.success is True
        assert log.metadata == {}

    def test_access_log_with_all_fields(self):
        """Test creating access log with all fields"""
        now = datetime.now(timezone.utc)

        log = VaultAccessLog(
            log_id="log_123",
            vault_id="vault_456",
            user_id="user_789",
            action=VaultAction.UPDATE,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            success=True,
            error_message=None,
            metadata={"source": "api", "version": "v1"},
            created_at=now,
        )

        assert log.log_id == "log_123"
        assert log.vault_id == "vault_456"
        assert log.action == VaultAction.UPDATE
        assert log.ip_address == "192.168.1.100"
        assert log.user_agent == "Mozilla/5.0"
        assert log.success is True
        assert log.metadata["source"] == "api"

    def test_access_log_failed_action(self):
        """Test access log for failed action"""
        log = VaultAccessLog(
            vault_id="vault_123",
            user_id="user_456",
            action=VaultAction.DELETE,
            success=False,
            error_message="Permission denied",
        )

        assert log.success is False
        assert log.error_message == "Permission denied"

    def test_access_log_different_actions(self):
        """Test access log with different vault actions"""
        actions = [
            VaultAction.CREATE,
            VaultAction.READ,
            VaultAction.UPDATE,
            VaultAction.DELETE,
            VaultAction.ROTATE,
            VaultAction.SHARE,
        ]

        for action in actions:
            log = VaultAccessLog(
                vault_id="vault_123",
                user_id="user_456",
                action=action,
            )
            assert log.action == action


class TestVaultShareModel:
    """Test VaultShare model validation"""

    def test_vault_share_creation_to_user(self):
        """Test creating vault share to user"""
        share = VaultShare(
            vault_id="vault_123",
            owner_user_id="user_456",
            shared_with_user_id="user_789",
        )

        assert share.vault_id == "vault_123"
        assert share.owner_user_id == "user_456"
        assert share.shared_with_user_id == "user_789"
        assert share.permission_level == PermissionLevel.READ
        assert share.is_active is True

    def test_vault_share_creation_to_org(self):
        """Test creating vault share to organization"""
        share = VaultShare(
            vault_id="vault_123",
            owner_user_id="user_456",
            shared_with_org_id="org_789",
        )

        assert share.vault_id == "vault_123"
        assert share.shared_with_org_id == "org_789"
        assert share.shared_with_user_id is None

    def test_vault_share_with_all_fields(self):
        """Test creating vault share with all fields"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=30)

        share = VaultShare(
            share_id="share_123",
            vault_id="vault_456",
            owner_user_id="user_789",
            shared_with_user_id="user_012",
            shared_with_org_id=None,
            permission_level=PermissionLevel.READ_WRITE,
            expires_at=future,
            is_active=True,
            created_at=now,
        )

        assert share.share_id == "share_123"
        assert share.permission_level == PermissionLevel.READ_WRITE
        assert share.expires_at == future
        assert share.created_at == now

    def test_vault_share_permission_levels(self):
        """Test vault share with different permission levels"""
        for level in [PermissionLevel.READ, PermissionLevel.READ_WRITE]:
            share = VaultShare(
                vault_id="vault_123",
                owner_user_id="user_456",
                shared_with_user_id="user_789",
                permission_level=level,
            )
            assert share.permission_level == level


class TestVaultCreateRequest:
    """Test VaultCreateRequest model validation"""

    def test_create_request_minimal(self):
        """Test minimal vault create request"""
        request = VaultCreateRequest(
            secret_type=SecretType.API_KEY,
            name="My Secret",
            secret_value="super_secret_value",
        )

        assert request.secret_type == SecretType.API_KEY
        assert request.name == "My Secret"
        assert request.secret_value == "super_secret_value"
        assert request.rotation_enabled is False
        assert request.blockchain_verify is False
        assert request.metadata == {}
        assert request.tags == []

    def test_create_request_with_all_fields(self):
        """Test vault create request with all fields"""
        future = datetime.now(timezone.utc) + timedelta(days=90)

        request = VaultCreateRequest(
            secret_type=SecretType.DATABASE_CREDENTIAL,
            provider=SecretProvider.AWS,
            name="Production DB Credentials",
            description="Main production database access",
            secret_value="postgres://user:pass@host:5432/db",
            organization_id="org_123",
            metadata={"env": "prod", "critical": True},
            tags=["production", "database"],
            expires_at=future,
            rotation_enabled=True,
            rotation_days=90,
            blockchain_verify=True,
        )

        assert request.secret_type == SecretType.DATABASE_CREDENTIAL
        assert request.provider == SecretProvider.AWS
        assert request.name == "Production DB Credentials"
        assert request.description == "Main production database access"
        assert request.secret_value == "postgres://user:pass@host:5432/db"
        assert request.organization_id == "org_123"
        assert request.metadata["critical"] is True
        assert len(request.tags) == 2
        assert request.rotation_enabled is True
        assert request.rotation_days == 90
        assert request.blockchain_verify is True

    def test_create_request_tags_validation(self):
        """Test tags validation (max 10 tags)"""
        with pytest.raises(ValidationError) as exc_info:
            VaultCreateRequest(
                secret_type=SecretType.API_KEY,
                name="Test",
                secret_value="secret",
                tags=["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8", "tag9", "tag10", "tag11"],
            )

        errors = exc_info.value.errors()
        assert any("Maximum 10 tags allowed" in str(err) for err in errors)

    def test_create_request_tags_normalization(self):
        """Test tags are normalized to lowercase and stripped"""
        request = VaultCreateRequest(
            secret_type=SecretType.API_KEY,
            name="Test",
            secret_value="secret",
            tags=["Production", "  Database  ", "AWS"],
        )

        assert request.tags == ["production", "database", "aws"]

    def test_create_request_rotation_days_validation(self):
        """Test rotation_days validation (1-365)"""
        # Valid rotation days
        request = VaultCreateRequest(
            secret_type=SecretType.API_KEY,
            name="Test",
            secret_value="secret",
            rotation_days=90,
        )
        assert request.rotation_days == 90

        # Invalid: too low
        with pytest.raises(ValidationError):
            VaultCreateRequest(
                secret_type=SecretType.API_KEY,
                name="Test",
                secret_value="secret",
                rotation_days=0,
            )

        # Invalid: too high
        with pytest.raises(ValidationError):
            VaultCreateRequest(
                secret_type=SecretType.API_KEY,
                name="Test",
                secret_value="secret",
                rotation_days=366,
            )

    def test_create_request_name_validation(self):
        """Test name validation (min_length=1, max_length=255)"""
        # Valid name
        request = VaultCreateRequest(
            secret_type=SecretType.API_KEY,
            name="Valid Name",
            secret_value="secret",
        )
        assert request.name == "Valid Name"

        # Invalid: empty name
        with pytest.raises(ValidationError):
            VaultCreateRequest(
                secret_type=SecretType.API_KEY,
                name="",
                secret_value="secret",
            )

        # Valid: max length
        long_name = "a" * 255
        request = VaultCreateRequest(
            secret_type=SecretType.API_KEY,
            name=long_name,
            secret_value="secret",
        )
        assert len(request.name) == 255


class TestVaultUpdateRequest:
    """Test VaultUpdateRequest model validation"""

    def test_update_request_partial(self):
        """Test partial update request"""
        request = VaultUpdateRequest(
            name="Updated Name",
            description="Updated description",
        )

        assert request.name == "Updated Name"
        assert request.description == "Updated description"
        assert request.secret_value is None
        assert request.rotation_enabled is None

    def test_update_request_all_fields(self):
        """Test update request with all fields"""
        future = datetime.now(timezone.utc) + timedelta(days=60)

        request = VaultUpdateRequest(
            name="Updated Secret",
            description="New description",
            secret_value="new_secret_value",
            metadata={"updated": True},
            tags=["updated", "v2"],
            expires_at=future,
            rotation_enabled=True,
            rotation_days=60,
            is_active=True,
        )

        assert request.name == "Updated Secret"
        assert request.description == "New description"
        assert request.secret_value == "new_secret_value"
        assert request.metadata["updated"] is True
        assert len(request.tags) == 2
        assert request.rotation_enabled is True
        assert request.rotation_days == 60
        assert request.is_active is True

    def test_update_request_deactivate(self):
        """Test update request to deactivate secret"""
        request = VaultUpdateRequest(
            is_active=False,
        )

        assert request.is_active is False

    def test_update_request_enable_rotation(self):
        """Test update request to enable rotation"""
        request = VaultUpdateRequest(
            rotation_enabled=True,
            rotation_days=30,
        )

        assert request.rotation_enabled is True
        assert request.rotation_days == 30


class TestVaultShareRequest:
    """Test VaultShareRequest model validation"""

    def test_share_request_to_user(self):
        """Test share request to user"""
        request = VaultShareRequest(
            shared_with_user_id="user_789",
        )

        assert request.shared_with_user_id == "user_789"
        assert request.permission_level == PermissionLevel.READ

    def test_share_request_to_org(self):
        """Test share request to organization"""
        request = VaultShareRequest(
            shared_with_org_id="org_789",
        )

        assert request.shared_with_org_id == "org_789"

    def test_share_request_with_all_fields(self):
        """Test share request with all fields"""
        future = datetime.now(timezone.utc) + timedelta(days=7)

        request = VaultShareRequest(
            shared_with_user_id="user_789",
            permission_level=PermissionLevel.READ_WRITE,
            expires_at=future,
        )

        assert request.shared_with_user_id == "user_789"
        assert request.permission_level == PermissionLevel.READ_WRITE
        assert request.expires_at == future

    def test_share_request_validation_requires_target(self):
        """Test that at least one share target is required"""
        # The validator on shared_with_user_id checks that either
        # shared_with_user_id or shared_with_org_id is provided
        # Both being None triggers validation error
        with pytest.raises(ValidationError) as exc_info:
            VaultShareRequest(
                shared_with_user_id=None,
                shared_with_org_id=None,
            )

        errors = exc_info.value.errors()
        # Validator should catch this
        assert len(errors) > 0


class TestVaultTestRequest:
    """Test VaultTestRequest model validation"""

    def test_test_request_minimal(self):
        """Test minimal test request"""
        request = VaultTestRequest()

        assert request.test_endpoint is None

    def test_test_request_with_endpoint(self):
        """Test test request with custom endpoint"""
        request = VaultTestRequest(
            test_endpoint="https://api.example.com/test",
        )

        assert request.test_endpoint == "https://api.example.com/test"


class TestVaultItemResponse:
    """Test VaultItemResponse model"""

    def test_item_response_creation(self):
        """Test creating vault item response"""
        now = datetime.now(timezone.utc)

        response = VaultItemResponse(
            vault_id="vault_123",
            user_id="user_456",
            secret_type=SecretType.API_KEY,
            name="My API Key",
            encryption_method=EncryptionMethod.AES_256_GCM,
            version=1,
            access_count=0,
            is_active=True,
            rotation_enabled=False,
            created_at=now,
            updated_at=now,
        )

        assert response.vault_id == "vault_123"
        assert response.user_id == "user_456"
        assert response.secret_type == SecretType.API_KEY
        assert response.name == "My API Key"
        assert response.version == 1

    def test_item_response_with_all_fields(self):
        """Test vault item response with all fields"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=30)

        response = VaultItemResponse(
            vault_id="vault_123",
            user_id="user_456",
            organization_id="org_789",
            secret_type=SecretType.DATABASE_CREDENTIAL,
            provider=SecretProvider.AWS,
            name="Production Database",
            description="Main prod database",
            encryption_method=EncryptionMethod.AES_256_GCM,
            metadata={"env": "production"},
            tags=["production", "database"],
            version=2,
            expires_at=future,
            last_accessed_at=now,
            access_count=42,
            is_active=True,
            rotation_enabled=True,
            rotation_days=90,
            blockchain_reference="0x1234567890",
            created_at=now,
            updated_at=now,
        )

        assert response.organization_id == "org_789"
        assert response.provider == SecretProvider.AWS
        assert response.description == "Main prod database"
        assert len(response.tags) == 2
        assert response.access_count == 42
        assert response.rotation_days == 90
        assert response.blockchain_reference == "0x1234567890"


class TestVaultSecretResponse:
    """Test VaultSecretResponse model"""

    def test_secret_response_creation(self):
        """Test creating vault secret response with decrypted value"""
        response = VaultSecretResponse(
            vault_id="vault_123",
            name="My API Key",
            secret_type=SecretType.API_KEY,
            secret_value="decrypted_secret_value",
        )

        assert response.vault_id == "vault_123"
        assert response.name == "My API Key"
        assert response.secret_type == SecretType.API_KEY
        assert response.secret_value == "decrypted_secret_value"
        assert response.blockchain_verified is False

    def test_secret_response_with_all_fields(self):
        """Test vault secret response with all fields"""
        future = datetime.now(timezone.utc) + timedelta(days=30)

        response = VaultSecretResponse(
            vault_id="vault_123",
            name="Production Key",
            secret_type=SecretType.BLOCKCHAIN_KEY,
            provider=SecretProvider.ETHEREUM,
            secret_value="0xprivatekey123",
            metadata={"network": "mainnet"},
            expires_at=future,
            blockchain_verified=True,
        )

        assert response.provider == SecretProvider.ETHEREUM
        assert response.secret_value == "0xprivatekey123"
        assert response.metadata["network"] == "mainnet"
        assert response.blockchain_verified is True


class TestVaultListResponse:
    """Test VaultListResponse model"""

    def test_list_response_empty(self):
        """Test empty vault list response"""
        response = VaultListResponse(
            items=[],
            total=0,
            page=1,
            page_size=50,
        )

        assert len(response.items) == 0
        assert response.total == 0
        assert response.page == 1
        assert response.page_size == 50

    def test_list_response_with_items(self):
        """Test vault list response with items"""
        now = datetime.now(timezone.utc)

        items = [
            VaultItemResponse(
                vault_id=f"vault_{i}",
                user_id="user_123",
                secret_type=SecretType.API_KEY,
                name=f"Secret {i}",
                encryption_method=EncryptionMethod.AES_256_GCM,
                version=1,
                access_count=0,
                is_active=True,
                rotation_enabled=False,
                created_at=now,
                updated_at=now,
            )
            for i in range(3)
        ]

        response = VaultListResponse(
            items=items,
            total=3,
            page=1,
            page_size=50,
        )

        assert len(response.items) == 3
        assert response.total == 3
        assert response.items[0].vault_id == "vault_0"
        assert response.items[2].vault_id == "vault_2"


class TestVaultShareResponse:
    """Test VaultShareResponse model"""

    def test_share_response_to_user(self):
        """Test vault share response to user"""
        now = datetime.now(timezone.utc)

        response = VaultShareResponse(
            share_id="share_123",
            vault_id="vault_456",
            owner_user_id="user_789",
            shared_with_user_id="user_012",
            permission_level=PermissionLevel.READ,
            is_active=True,
            created_at=now,
        )

        assert response.share_id == "share_123"
        assert response.vault_id == "vault_456"
        assert response.owner_user_id == "user_789"
        assert response.shared_with_user_id == "user_012"
        assert response.permission_level == PermissionLevel.READ
        assert response.is_active is True

    def test_share_response_to_org(self):
        """Test vault share response to organization"""
        now = datetime.now(timezone.utc)

        response = VaultShareResponse(
            share_id="share_123",
            vault_id="vault_456",
            owner_user_id="user_789",
            shared_with_org_id="org_012",
            permission_level=PermissionLevel.READ_WRITE,
            is_active=True,
            created_at=now,
        )

        assert response.shared_with_org_id == "org_012"
        assert response.shared_with_user_id is None
        assert response.permission_level == PermissionLevel.READ_WRITE

    def test_share_response_with_expiration(self):
        """Test vault share response with expiration"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=7)

        response = VaultShareResponse(
            share_id="share_123",
            vault_id="vault_456",
            owner_user_id="user_789",
            shared_with_user_id="user_012",
            permission_level=PermissionLevel.READ,
            expires_at=future,
            is_active=True,
            created_at=now,
        )

        assert response.expires_at == future


class TestVaultAccessLogResponse:
    """Test VaultAccessLogResponse model"""

    def test_access_log_response_success(self):
        """Test successful access log response"""
        now = datetime.now(timezone.utc)

        response = VaultAccessLogResponse(
            log_id="log_123",
            vault_id="vault_456",
            user_id="user_789",
            action=VaultAction.READ,
            success=True,
            created_at=now,
        )

        assert response.log_id == "log_123"
        assert response.vault_id == "vault_456"
        assert response.user_id == "user_789"
        assert response.action == VaultAction.READ
        assert response.success is True
        assert response.error_message is None

    def test_access_log_response_failure(self):
        """Test failed access log response"""
        now = datetime.now(timezone.utc)

        response = VaultAccessLogResponse(
            log_id="log_123",
            vault_id="vault_456",
            user_id="user_789",
            action=VaultAction.DELETE,
            ip_address="192.168.1.100",
            success=False,
            error_message="Permission denied",
            metadata={"reason": "insufficient_permissions"},
            created_at=now,
        )

        assert response.success is False
        assert response.error_message == "Permission denied"
        assert response.ip_address == "192.168.1.100"
        assert response.metadata["reason"] == "insufficient_permissions"


class TestVaultStatsResponse:
    """Test VaultStatsResponse model"""

    def test_stats_response_defaults(self):
        """Test vault stats response with defaults"""
        response = VaultStatsResponse()

        assert response.total_secrets == 0
        assert response.active_secrets == 0
        assert response.expired_secrets == 0
        assert response.secrets_by_type == {}
        assert response.secrets_by_provider == {}
        assert response.total_access_count == 0
        assert response.shared_secrets == 0
        assert response.blockchain_verified_secrets == 0

    def test_stats_response_with_data(self):
        """Test vault stats response with data"""
        response = VaultStatsResponse(
            total_secrets=100,
            active_secrets=85,
            expired_secrets=15,
            secrets_by_type={
                "api_key": 40,
                "database_credential": 30,
                "blockchain_key": 10,
            },
            secrets_by_provider={
                "aws": 25,
                "stripe": 15,
                "ethereum": 10,
            },
            total_access_count=1500,
            shared_secrets=20,
            blockchain_verified_secrets=10,
        )

        assert response.total_secrets == 100
        assert response.active_secrets == 85
        assert response.expired_secrets == 15
        assert response.secrets_by_type["api_key"] == 40
        assert response.secrets_by_provider["aws"] == 25
        assert response.total_access_count == 1500
        assert response.shared_secrets == 20
        assert response.blockchain_verified_secrets == 10


class TestVaultTestResponse:
    """Test VaultTestResponse model"""

    def test_test_response_success(self):
        """Test successful credential test response"""
        response = VaultTestResponse(
            success=True,
            message="Credential test successful",
        )

        assert response.success is True
        assert response.message == "Credential test successful"
        assert response.details is None

    def test_test_response_failure(self):
        """Test failed credential test response"""
        response = VaultTestResponse(
            success=False,
            message="Authentication failed",
            details={
                "error_code": "AUTH_FAILED",
                "status_code": 401,
            },
        )

        assert response.success is False
        assert response.message == "Authentication failed"
        assert response.details["error_code"] == "AUTH_FAILED"
        assert response.details["status_code"] == 401

    def test_test_response_with_details(self):
        """Test credential test response with details"""
        response = VaultTestResponse(
            success=True,
            message="API key validated successfully",
            details={
                "api_version": "v2",
                "rate_limit": 1000,
                "quota_remaining": 850,
            },
        )

        assert response.success is True
        assert response.details["api_version"] == "v2"
        assert response.details["rate_limit"] == 1000


class TestHealthResponse:
    """Test HealthResponse model"""

    def test_health_response_defaults(self):
        """Test health response with default values"""
        response = HealthResponse()

        assert response.status == "healthy"
        assert response.service == "vault_service"
        assert response.port == 8214
        assert response.version == "1.0.0"

    def test_health_response_custom(self):
        """Test health response with custom values"""
        response = HealthResponse(
            status="degraded",
            service="vault_service",
            port=8214,
            version="1.1.0",
        )

        assert response.status == "degraded"
        assert response.version == "1.1.0"


class TestServiceInfo:
    """Test ServiceInfo model"""

    def test_service_info_defaults(self):
        """Test service info with default values"""
        info = ServiceInfo()

        assert info.service == "vault_service"
        assert info.version == "1.0.0"
        assert "Secure credential and secret management" in info.description
        assert info.capabilities["encryption"] is True
        assert info.capabilities["blockchain_verification"] is True
        assert "api_key" in info.supported_secret_types
        assert "blockchain_key" in info.supported_secret_types
        assert "ethereum" in info.supported_providers
        assert "/health" in info.endpoints.values()

    def test_service_info_capabilities(self):
        """Test service capabilities"""
        info = ServiceInfo()

        expected_capabilities = [
            "encryption",
            "secret_storage",
            "secret_sharing",
            "access_control",
            "audit_logging",
            "secret_rotation",
            "blockchain_verification",
            "multi_provider_support",
        ]

        for capability in expected_capabilities:
            assert capability in info.capabilities
            assert info.capabilities[capability] is True

    def test_service_info_secret_types(self):
        """Test supported secret types"""
        info = ServiceInfo()

        expected_types = [
            "api_key",
            "database_credential",
            "ssh_key",
            "ssl_certificate",
            "oauth_token",
            "aws_credential",
            "blockchain_key",
            "environment_variable",
            "custom",
        ]

        for secret_type in expected_types:
            assert secret_type in info.supported_secret_types

    def test_service_info_providers(self):
        """Test supported providers"""
        info = ServiceInfo()

        expected_providers = [
            "openai",
            "anthropic",
            "stripe",
            "aws",
            "azure",
            "gcp",
            "github",
            "gitlab",
            "ethereum",
            "polygon",
            "custom",
        ]

        for provider in expected_providers:
            assert provider in info.supported_providers

    def test_service_info_endpoints(self):
        """Test service endpoints"""
        info = ServiceInfo()

        expected_endpoints = [
            "health",
            "create_secret",
            "get_secret",
            "list_secrets",
            "share_secret",
            "test_secret",
        ]

        for endpoint in expected_endpoints:
            assert endpoint in info.endpoints
            assert isinstance(info.endpoints[endpoint], str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
