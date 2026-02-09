"""
Vault Service Data Contract

Pydantic schemas defining the contract between tests and vault_service.
These schemas validate request/response shapes and field constraints.

Usage:
    from tests.contracts.vault.data_contract import (
        VaultCreateContract,
        VaultSecretResponseContract,
    )
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Enums (Contract Definitions)
# =============================================================================


class SecretTypeContract(str, Enum):
    """Valid secret types"""
    API_KEY = "api_key"
    DATABASE_CREDENTIAL = "database_credential"
    SSH_KEY = "ssh_key"
    SSL_CERTIFICATE = "ssl_certificate"
    OAUTH_TOKEN = "oauth_token"
    AWS_CREDENTIAL = "aws_credential"
    BLOCKCHAIN_KEY = "blockchain_key"
    ENVIRONMENT_VARIABLE = "environment_variable"
    CUSTOM = "custom"


class SecretProviderContract(str, Enum):
    """Valid secret providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    STRIPE = "stripe"
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    GITHUB = "github"
    GITLAB = "gitlab"
    ETHEREUM = "ethereum"
    POLYGON = "polygon"
    CUSTOM = "custom"


class EncryptionMethodContract(str, Enum):
    """Valid encryption methods"""
    AES_256_GCM = "aes_256_gcm"
    FERNET = "fernet"
    BLOCKCHAIN_ENCRYPTED = "blockchain_encrypted"


class VaultActionContract(str, Enum):
    """Valid vault actions"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    ROTATE = "rotate"
    SHARE = "share"
    REVOKE_SHARE = "revoke_share"
    EXPORT = "export"
    IMPORT = "import"


class PermissionLevelContract(str, Enum):
    """Valid permission levels"""
    READ = "read"
    READ_WRITE = "read_write"


# =============================================================================
# Request Contracts
# =============================================================================


class VaultCreateContract(BaseModel):
    """Contract for create secret request"""
    secret_type: SecretTypeContract
    provider: Optional[SecretProviderContract] = None
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    secret_value: str = Field(..., min_length=1, description="Plain text secret")
    organization_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None
    rotation_enabled: bool = False
    rotation_days: Optional[int] = Field(None, ge=1, le=365)
    blockchain_verify: bool = False

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        if len(v) > 10:
            raise ValueError('Maximum 10 tags allowed')
        return [tag.lower().strip() for tag in v]

    model_config = {"extra": "forbid"}


class VaultUpdateContract(BaseModel):
    """Contract for update secret request"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    secret_value: Optional[str] = Field(None, min_length=1)
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    expires_at: Optional[datetime] = None
    rotation_enabled: Optional[bool] = None
    rotation_days: Optional[int] = Field(None, ge=1, le=365)
    is_active: Optional[bool] = None

    model_config = {"extra": "forbid"}


class VaultShareContract(BaseModel):
    """Contract for share secret request"""
    shared_with_user_id: Optional[str] = None
    shared_with_org_id: Optional[str] = None
    permission_level: PermissionLevelContract = PermissionLevelContract.READ
    expires_at: Optional[datetime] = None

    @field_validator('shared_with_user_id')
    @classmethod
    def validate_share_target(cls, v, info):
        values = info.data
        if not v and not values.get('shared_with_org_id'):
            raise ValueError('Must specify either shared_with_user_id or shared_with_org_id')
        return v

    model_config = {"extra": "forbid"}


class VaultTestContract(BaseModel):
    """Contract for test credential request"""
    test_endpoint: Optional[str] = None

    model_config = {"extra": "forbid"}


# =============================================================================
# Response Contracts
# =============================================================================


class VaultItemResponseContract(BaseModel):
    """Contract for vault item response (without secret value)"""
    vault_id: str
    user_id: str
    organization_id: Optional[str] = None
    secret_type: SecretTypeContract
    provider: Optional[SecretProviderContract] = None
    name: str
    description: Optional[str] = None
    encryption_method: EncryptionMethodContract
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    version: int = Field(ge=1)
    expires_at: Optional[datetime] = None
    last_accessed_at: Optional[datetime] = None
    access_count: int = Field(ge=0)
    is_active: bool
    rotation_enabled: bool
    rotation_days: Optional[int] = None
    blockchain_reference: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VaultSecretResponseContract(BaseModel):
    """Contract for decrypted secret response"""
    vault_id: str
    name: str
    secret_type: SecretTypeContract
    provider: Optional[SecretProviderContract] = None
    secret_value: str = Field(..., description="Decrypted secret value")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    expires_at: Optional[datetime] = None
    blockchain_verified: bool = False

    model_config = {"from_attributes": True}


class VaultListResponseContract(BaseModel):
    """Contract for list secrets response"""
    items: List[VaultItemResponseContract]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=200)

    model_config = {"from_attributes": True}


class VaultShareResponseContract(BaseModel):
    """Contract for share response"""
    share_id: str
    vault_id: str
    owner_user_id: str
    shared_with_user_id: Optional[str] = None
    shared_with_org_id: Optional[str] = None
    permission_level: PermissionLevelContract
    expires_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class VaultAccessLogResponseContract(BaseModel):
    """Contract for access log response"""
    log_id: str
    vault_id: str
    user_id: str
    action: VaultActionContract
    ip_address: Optional[str] = None
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = {"from_attributes": True}


class VaultStatsResponseContract(BaseModel):
    """Contract for statistics response"""
    total_secrets: int = Field(ge=0)
    active_secrets: int = Field(ge=0)
    expired_secrets: int = Field(ge=0)
    secrets_by_type: Dict[str, int] = Field(default_factory=dict)
    secrets_by_provider: Dict[str, int] = Field(default_factory=dict)
    total_access_count: int = Field(ge=0)
    shared_secrets: int = Field(ge=0, default=0)
    blockchain_verified_secrets: int = Field(ge=0, default=0)

    model_config = {"from_attributes": True}


class VaultTestResponseContract(BaseModel):
    """Contract for test credential response"""
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}


class HealthResponseContract(BaseModel):
    """Contract for health check response"""
    status: str
    service: str = "vault_service"
    port: int = 8214
    version: str = "1.0.0"

    model_config = {"from_attributes": True}


class DetailedHealthResponseContract(BaseModel):
    """Contract for detailed health check response"""
    service: str
    status: str
    port: int
    version: str
    encryption: Optional[str] = None
    blockchain: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None

    model_config = {"from_attributes": True, "extra": "allow"}


class ServiceInfoContract(BaseModel):
    """Contract for service info response"""
    service: str = "vault_service"
    version: str = "1.0.0"
    description: str
    capabilities: Dict[str, bool]
    supported_secret_types: List[str]
    supported_providers: List[str]
    endpoints: Dict[str, str]

    model_config = {"from_attributes": True}


# =============================================================================
# Error Contracts
# =============================================================================


class ErrorResponseContract(BaseModel):
    """Contract for error responses"""
    detail: str

    model_config = {"extra": "allow"}


class ValidationErrorContract(BaseModel):
    """Contract for validation error responses"""
    detail: List[Dict[str, Any]]

    model_config = {"extra": "allow"}


# =============================================================================
# Event Contracts
# =============================================================================


class VaultSecretCreatedEventContract(BaseModel):
    """Contract for vault.secret.created event"""
    vault_id: str
    user_id: str
    organization_id: Optional[str] = None
    secret_type: str
    provider: Optional[str] = None
    name: str
    blockchain_verified: bool
    timestamp: str

    model_config = {"from_attributes": True}


class VaultSecretAccessedEventContract(BaseModel):
    """Contract for vault.secret.accessed event"""
    vault_id: str
    user_id: str
    secret_type: str
    decrypted: bool
    blockchain_verified: bool
    timestamp: str

    model_config = {"from_attributes": True}


class VaultSecretUpdatedEventContract(BaseModel):
    """Contract for vault.secret.updated event"""
    vault_id: str
    user_id: str
    secret_value_updated: bool
    metadata_updated: bool
    timestamp: str

    model_config = {"from_attributes": True}


class VaultSecretDeletedEventContract(BaseModel):
    """Contract for vault.secret.deleted event"""
    vault_id: str
    user_id: str
    secret_type: Optional[str] = None
    timestamp: str

    model_config = {"from_attributes": True}


class VaultSecretSharedEventContract(BaseModel):
    """Contract for vault.secret.shared event"""
    vault_id: str
    owner_user_id: str
    shared_with_user_id: Optional[str] = None
    shared_with_org_id: Optional[str] = None
    permission_level: str
    timestamp: str

    model_config = {"from_attributes": True}


class VaultSecretRotatedEventContract(BaseModel):
    """Contract for vault.secret.rotated event"""
    vault_id: str
    user_id: str
    new_version: Optional[int] = None
    timestamp: str

    model_config = {"from_attributes": True}


# =============================================================================
# Exports
# =============================================================================


__all__ = [
    # Enums
    "SecretTypeContract",
    "SecretProviderContract",
    "EncryptionMethodContract",
    "VaultActionContract",
    "PermissionLevelContract",
    # Request Contracts
    "VaultCreateContract",
    "VaultUpdateContract",
    "VaultShareContract",
    "VaultTestContract",
    # Response Contracts
    "VaultItemResponseContract",
    "VaultSecretResponseContract",
    "VaultListResponseContract",
    "VaultShareResponseContract",
    "VaultAccessLogResponseContract",
    "VaultStatsResponseContract",
    "VaultTestResponseContract",
    "HealthResponseContract",
    "DetailedHealthResponseContract",
    "ServiceInfoContract",
    # Error Contracts
    "ErrorResponseContract",
    "ValidationErrorContract",
    # Event Contracts
    "VaultSecretCreatedEventContract",
    "VaultSecretAccessedEventContract",
    "VaultSecretUpdatedEventContract",
    "VaultSecretDeletedEventContract",
    "VaultSecretSharedEventContract",
    "VaultSecretRotatedEventContract",
]
