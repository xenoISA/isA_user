"""
Vault Service Model Unit Tests

Tests for Pydantic model validation and enum definitions.
"""
import pytest
from datetime import datetime, timedelta
from typing import Any, Dict

from microservices.vault_service.models import (
    # Enums
    SecretType,
    SecretProvider,
    EncryptionMethod,
    VaultAction,
    PermissionLevel,
    # Models
    VaultItem,
    VaultAccessLog,
    VaultShare,
    # Request Models
    VaultCreateRequest,
    VaultUpdateRequest,
    VaultShareRequest,
    VaultTestRequest,
    # Response Models
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

pytestmark = pytest.mark.unit


# =============================================================================
# Test Data Factory
# =============================================================================

class VaultTestDataFactory:
    """Factory for generating test data with zero hardcoded values"""

    @staticmethod
    def create_request(
        secret_type: SecretType = SecretType.API_KEY,
        provider: SecretProvider = None,
        name: str = None,
        secret_value: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate vault create request data"""
        import uuid
        unique_id = uuid.uuid4().hex[:8]
        return {
            "secret_type": secret_type,
            "provider": provider,
            "name": name or f"test_secret_{unique_id}",
            "description": kwargs.get("description"),
            "secret_value": secret_value or f"sk_test_{unique_id}",
            "organization_id": kwargs.get("organization_id"),
            "metadata": kwargs.get("metadata", {}),
            "tags": kwargs.get("tags", []),
            "expires_at": kwargs.get("expires_at"),
            "rotation_enabled": kwargs.get("rotation_enabled", False),
            "rotation_days": kwargs.get("rotation_days"),
            "blockchain_verify": kwargs.get("blockchain_verify", False),
        }

    @staticmethod
    def update_request(**kwargs) -> Dict[str, Any]:
        """Generate vault update request data"""
        return {
            "name": kwargs.get("name"),
            "description": kwargs.get("description"),
            "secret_value": kwargs.get("secret_value"),
            "metadata": kwargs.get("metadata"),
            "tags": kwargs.get("tags"),
            "expires_at": kwargs.get("expires_at"),
            "rotation_enabled": kwargs.get("rotation_enabled"),
            "rotation_days": kwargs.get("rotation_days"),
            "is_active": kwargs.get("is_active"),
        }

    @staticmethod
    def share_request(
        shared_with_user_id: str = None,
        shared_with_org_id: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate share request data"""
        import uuid
        unique_id = uuid.uuid4().hex[:8]
        return {
            "shared_with_user_id": shared_with_user_id or f"user_{unique_id}",
            "shared_with_org_id": shared_with_org_id,
            "permission_level": kwargs.get("permission_level", PermissionLevel.READ),
            "expires_at": kwargs.get("expires_at"),
        }

    @staticmethod
    def vault_item_data(**kwargs) -> Dict[str, Any]:
        """Generate vault item data"""
        import uuid
        unique_id = uuid.uuid4().hex[:8]
        now = datetime.utcnow()
        return {
            "vault_id": kwargs.get("vault_id", str(uuid.uuid4())),
            "user_id": kwargs.get("user_id", f"user_{unique_id}"),
            "organization_id": kwargs.get("organization_id"),
            "secret_type": kwargs.get("secret_type", SecretType.API_KEY),
            "provider": kwargs.get("provider"),
            "name": kwargs.get("name", f"test_secret_{unique_id}"),
            "description": kwargs.get("description"),
            "encrypted_value": kwargs.get("encrypted_value", b"encrypted_data"),
            "encryption_method": kwargs.get("encryption_method", EncryptionMethod.AES_256_GCM),
            "encryption_key_id": kwargs.get("encryption_key_id"),
            "metadata": kwargs.get("metadata", {}),
            "tags": kwargs.get("tags", []),
            "version": kwargs.get("version", 1),
            "expires_at": kwargs.get("expires_at"),
            "last_accessed_at": kwargs.get("last_accessed_at"),
            "access_count": kwargs.get("access_count", 0),
            "is_active": kwargs.get("is_active", True),
            "rotation_enabled": kwargs.get("rotation_enabled", False),
            "rotation_days": kwargs.get("rotation_days"),
            "blockchain_reference": kwargs.get("blockchain_reference"),
            "created_at": kwargs.get("created_at", now),
            "updated_at": kwargs.get("updated_at", now),
        }


# =============================================================================
# Enum Tests
# =============================================================================

class TestSecretTypeEnum:
    """Tests for SecretType enum"""

    def test_all_secret_types_exist(self):
        """All expected secret types should be defined"""
        expected_types = [
            "api_key", "database_credential", "ssh_key", "ssl_certificate",
            "oauth_token", "aws_credential", "blockchain_key",
            "environment_variable", "custom"
        ]
        actual_types = [t.value for t in SecretType]
        for expected in expected_types:
            assert expected in actual_types, f"Missing secret type: {expected}"

    def test_secret_type_values(self):
        """SecretType values should match expected strings"""
        assert SecretType.API_KEY.value == "api_key"
        assert SecretType.DATABASE_CREDENTIAL.value == "database_credential"
        assert SecretType.SSH_KEY.value == "ssh_key"
        assert SecretType.CUSTOM.value == "custom"

    @pytest.mark.parametrize("secret_type", list(SecretType))
    def test_secret_type_is_string_enum(self, secret_type):
        """All secret types should be string enums"""
        assert isinstance(secret_type.value, str)
        assert len(secret_type.value) > 0


class TestSecretProviderEnum:
    """Tests for SecretProvider enum"""

    def test_all_providers_exist(self):
        """All expected providers should be defined"""
        expected_providers = [
            "openai", "anthropic", "stripe", "aws", "azure", "gcp",
            "github", "gitlab", "ethereum", "polygon", "custom"
        ]
        actual_providers = [p.value for p in SecretProvider]
        for expected in expected_providers:
            assert expected in actual_providers, f"Missing provider: {expected}"

    @pytest.mark.parametrize("provider", list(SecretProvider))
    def test_provider_is_string_enum(self, provider):
        """All providers should be string enums"""
        assert isinstance(provider.value, str)


class TestEncryptionMethodEnum:
    """Tests for EncryptionMethod enum"""

    def test_encryption_methods(self):
        """All encryption methods should be defined"""
        assert EncryptionMethod.AES_256_GCM.value == "aes_256_gcm"
        assert EncryptionMethod.FERNET.value == "fernet"
        assert EncryptionMethod.BLOCKCHAIN_ENCRYPTED.value == "blockchain_encrypted"


class TestVaultActionEnum:
    """Tests for VaultAction enum"""

    def test_all_actions_exist(self):
        """All expected actions should be defined"""
        expected_actions = [
            "create", "read", "update", "delete", "rotate",
            "share", "revoke_share", "export", "import"
        ]
        actual_actions = [a.value for a in VaultAction]
        for expected in expected_actions:
            assert expected in actual_actions, f"Missing action: {expected}"


class TestPermissionLevelEnum:
    """Tests for PermissionLevel enum"""

    def test_permission_levels(self):
        """Permission levels should be defined"""
        assert PermissionLevel.READ.value == "read"
        assert PermissionLevel.READ_WRITE.value == "read_write"


# =============================================================================
# VaultCreateRequest Tests
# =============================================================================

class TestVaultCreateRequest:
    """Tests for VaultCreateRequest model"""

    def test_valid_minimal_request(self):
        """Minimal valid request should pass validation"""
        data = VaultTestDataFactory.create_request()
        request = VaultCreateRequest(**data)
        assert request.secret_type == data["secret_type"]
        assert request.name == data["name"]
        assert request.secret_value == data["secret_value"]

    def test_valid_full_request(self):
        """Full request with all fields should pass validation"""
        data = VaultTestDataFactory.create_request(
            secret_type=SecretType.DATABASE_CREDENTIAL,
            provider=SecretProvider.AWS,
            description="Test database credential",
            organization_id="org_123",
            metadata={"environment": "production"},
            tags=["prod", "database"],
            expires_at=datetime.utcnow() + timedelta(days=90),
            rotation_enabled=True,
            rotation_days=30,
            blockchain_verify=True,
        )
        request = VaultCreateRequest(**data)
        assert request.provider == SecretProvider.AWS
        assert request.rotation_enabled is True
        assert request.rotation_days == 30

    def test_name_max_length(self):
        """Name should be limited to 255 characters"""
        data = VaultTestDataFactory.create_request(name="a" * 255)
        request = VaultCreateRequest(**data)
        assert len(request.name) == 255

    def test_name_too_long_raises_error(self):
        """Name over 255 characters should raise validation error"""
        data = VaultTestDataFactory.create_request(name="a" * 256)
        with pytest.raises(Exception):  # Pydantic ValidationError
            VaultCreateRequest(**data)

    def test_empty_name_raises_error(self):
        """Empty name should raise validation error"""
        data = VaultTestDataFactory.create_request(name="")
        with pytest.raises(Exception):
            VaultCreateRequest(**data)

    def test_description_max_length(self):
        """Description should be limited to 500 characters"""
        data = VaultTestDataFactory.create_request(description="a" * 500)
        request = VaultCreateRequest(**data)
        assert len(request.description) == 500

    def test_tags_max_count(self):
        """Tags should be limited to 10 items"""
        data = VaultTestDataFactory.create_request(tags=["tag"] * 11)
        with pytest.raises(Exception):
            VaultCreateRequest(**data)

    def test_tags_normalized_to_lowercase(self):
        """Tags should be normalized to lowercase"""
        data = VaultTestDataFactory.create_request(tags=["TAG1", "Tag2", "TAG3"])
        request = VaultCreateRequest(**data)
        assert all(tag.islower() for tag in request.tags)

    def test_rotation_days_range(self):
        """Rotation days should be between 1 and 365"""
        # Valid values
        for days in [1, 30, 90, 365]:
            data = VaultTestDataFactory.create_request(rotation_days=days)
            request = VaultCreateRequest(**data)
            assert request.rotation_days == days

    def test_rotation_days_too_low(self):
        """Rotation days below 1 should raise error"""
        data = VaultTestDataFactory.create_request(rotation_days=0)
        with pytest.raises(Exception):
            VaultCreateRequest(**data)

    def test_rotation_days_too_high(self):
        """Rotation days above 365 should raise error"""
        data = VaultTestDataFactory.create_request(rotation_days=366)
        with pytest.raises(Exception):
            VaultCreateRequest(**data)

    @pytest.mark.parametrize("secret_type", list(SecretType))
    def test_all_secret_types_accepted(self, secret_type):
        """All secret types should be accepted"""
        data = VaultTestDataFactory.create_request(secret_type=secret_type)
        request = VaultCreateRequest(**data)
        assert request.secret_type == secret_type

    @pytest.mark.parametrize("provider", list(SecretProvider))
    def test_all_providers_accepted(self, provider):
        """All providers should be accepted"""
        data = VaultTestDataFactory.create_request(provider=provider)
        request = VaultCreateRequest(**data)
        assert request.provider == provider


# =============================================================================
# VaultUpdateRequest Tests
# =============================================================================

class TestVaultUpdateRequest:
    """Tests for VaultUpdateRequest model"""

    def test_empty_update_is_valid(self):
        """Empty update request should be valid"""
        request = VaultUpdateRequest()
        assert request.name is None
        assert request.secret_value is None

    def test_partial_update(self):
        """Partial update with some fields should be valid"""
        request = VaultUpdateRequest(name="new_name", is_active=False)
        assert request.name == "new_name"
        assert request.is_active is False
        assert request.secret_value is None

    def test_name_constraints(self):
        """Name should follow same constraints as create"""
        # Valid
        request = VaultUpdateRequest(name="valid_name")
        assert request.name == "valid_name"

        # Too long
        with pytest.raises(Exception):
            VaultUpdateRequest(name="a" * 256)


# =============================================================================
# VaultShareRequest Tests
# =============================================================================

class TestVaultShareRequest:
    """Tests for VaultShareRequest model"""

    def test_share_with_user(self):
        """Share with user_id should be valid"""
        data = VaultTestDataFactory.share_request(shared_with_user_id="user_123")
        request = VaultShareRequest(**data)
        assert request.shared_with_user_id == "user_123"

    def test_share_with_org(self):
        """Share with org_id should be valid"""
        data = VaultTestDataFactory.share_request(
            shared_with_user_id=None,
            shared_with_org_id="org_123"
        )
        request = VaultShareRequest(**data)
        assert request.shared_with_org_id == "org_123"

    def test_share_requires_target(self):
        """Share without user_id or org_id should raise error"""
        with pytest.raises(Exception):
            VaultShareRequest(shared_with_user_id=None, shared_with_org_id=None)

    def test_default_permission_level(self):
        """Default permission level should be READ"""
        data = VaultTestDataFactory.share_request()
        request = VaultShareRequest(**data)
        assert request.permission_level == PermissionLevel.READ

    def test_read_write_permission(self):
        """READ_WRITE permission should be accepted"""
        data = VaultTestDataFactory.share_request(permission_level=PermissionLevel.READ_WRITE)
        request = VaultShareRequest(**data)
        assert request.permission_level == PermissionLevel.READ_WRITE


# =============================================================================
# VaultItem Tests
# =============================================================================

class TestVaultItem:
    """Tests for VaultItem model"""

    def test_valid_vault_item(self):
        """Valid vault item should pass validation"""
        data = VaultTestDataFactory.vault_item_data()
        item = VaultItem(**data)
        assert item.user_id == data["user_id"]
        assert item.is_active is True

    def test_default_values(self):
        """Default values should be set correctly"""
        item = VaultItem(
            user_id="user_123",
            secret_type=SecretType.API_KEY,
            name="test_secret",
        )
        assert item.version == 1
        assert item.access_count == 0
        assert item.is_active is True
        assert item.rotation_enabled is False
        assert item.metadata == {}
        assert item.tags == []

    def test_encrypted_value_accepts_bytes(self):
        """Encrypted value should accept bytes"""
        data = VaultTestDataFactory.vault_item_data(encrypted_value=b"encrypted_bytes")
        item = VaultItem(**data)
        assert item.encrypted_value == b"encrypted_bytes"


# =============================================================================
# Response Model Tests
# =============================================================================

class TestVaultItemResponse:
    """Tests for VaultItemResponse model"""

    def test_from_dict(self):
        """Should create response from dict"""
        import uuid
        now = datetime.utcnow()
        data = {
            "vault_id": str(uuid.uuid4()),
            "user_id": "user_123",
            "secret_type": SecretType.API_KEY,
            "name": "test_secret",
            "encryption_method": EncryptionMethod.AES_256_GCM,
            "metadata": {},
            "tags": [],
            "version": 1,
            "access_count": 0,
            "is_active": True,
            "rotation_enabled": False,
            "created_at": now,
            "updated_at": now,
        }
        response = VaultItemResponse(**data)
        assert response.vault_id == data["vault_id"]
        assert response.is_active is True


class TestVaultSecretResponse:
    """Tests for VaultSecretResponse model"""

    def test_includes_secret_value(self):
        """Response should include decrypted secret value"""
        response = VaultSecretResponse(
            vault_id="vault_123",
            name="test_secret",
            secret_type=SecretType.API_KEY,
            secret_value="decrypted_secret_value",
            metadata={},
            blockchain_verified=False,
        )
        assert response.secret_value == "decrypted_secret_value"


class TestVaultListResponse:
    """Tests for VaultListResponse model"""

    def test_pagination_fields(self):
        """Should include pagination fields"""
        response = VaultListResponse(
            items=[],
            total=0,
            page=1,
            page_size=50,
        )
        assert response.page == 1
        assert response.page_size == 50
        assert response.total == 0


class TestVaultStatsResponse:
    """Tests for VaultStatsResponse model"""

    def test_default_values(self):
        """Default values should be zero"""
        response = VaultStatsResponse()
        assert response.total_secrets == 0
        assert response.active_secrets == 0
        assert response.expired_secrets == 0
        assert response.total_access_count == 0
        assert response.secrets_by_type == {}
        assert response.secrets_by_provider == {}


class TestHealthResponse:
    """Tests for HealthResponse model"""

    def test_default_values(self):
        """Default values should be set"""
        response = HealthResponse()
        assert response.status == "healthy"
        assert response.service == "vault_service"
        assert response.port == 8214
        assert response.version == "1.0.0"


class TestServiceInfo:
    """Tests for ServiceInfo model"""

    def test_capabilities(self):
        """Service info should include capabilities"""
        info = ServiceInfo()
        assert info.capabilities["encryption"] is True
        assert info.capabilities["secret_storage"] is True
        assert info.capabilities["blockchain_verification"] is True

    def test_supported_types(self):
        """Should include supported secret types"""
        info = ServiceInfo()
        assert "api_key" in info.supported_secret_types
        assert "database_credential" in info.supported_secret_types

    def test_endpoints(self):
        """Should include endpoint mappings"""
        info = ServiceInfo()
        assert "/health" in info.endpoints.values()
        assert "/api/v1/vault/secrets" in info.endpoints.values()
