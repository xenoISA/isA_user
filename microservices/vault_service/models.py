"""
Vault Service Models

Data models for secure credential and secret management.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


# ============ Enums ============

class SecretType(str, Enum):
    """Types of secrets that can be stored"""
    API_KEY = "api_key"
    DATABASE_CREDENTIAL = "database_credential"
    SSH_KEY = "ssh_key"
    SSL_CERTIFICATE = "ssl_certificate"
    OAUTH_TOKEN = "oauth_token"
    AWS_CREDENTIAL = "aws_credential"
    BLOCKCHAIN_KEY = "blockchain_key"  # For blockchain integration
    ENVIRONMENT_VARIABLE = "environment_variable"
    CUSTOM = "custom"


class SecretProvider(str, Enum):
    """Third-party service providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    STRIPE = "stripe"
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    GITHUB = "github"
    GITLAB = "gitlab"
    ETHEREUM = "ethereum"  # Blockchain provider
    POLYGON = "polygon"    # Blockchain provider
    CUSTOM = "custom"


class EncryptionMethod(str, Enum):
    """Encryption methods"""
    AES_256_GCM = "aes_256_gcm"
    FERNET = "fernet"
    BLOCKCHAIN_ENCRYPTED = "blockchain_encrypted"  # Future: encrypted using blockchain keys


class VaultAction(str, Enum):
    """Actions performed on vault items"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    ROTATE = "rotate"
    SHARE = "share"
    REVOKE_SHARE = "revoke_share"
    EXPORT = "export"
    IMPORT = "import"


class PermissionLevel(str, Enum):
    """Permission levels for shared secrets"""
    READ = "read"
    READ_WRITE = "read_write"


# ============ Database Models ============

class VaultItem(BaseModel):
    """Vault item (encrypted secret)"""
    vault_id: Optional[str] = None
    user_id: str = Field(..., description="Owner user ID")
    organization_id: Optional[str] = Field(None, description="Organization ID for org-wide secrets")
    secret_type: SecretType = Field(..., description="Type of secret")
    provider: Optional[SecretProvider] = Field(None, description="Service provider")
    name: str = Field(..., description="User-friendly name", max_length=255)
    description: Optional[str] = Field(None, description="Secret description", max_length=500)
    encrypted_value: Optional[bytes] = Field(None, description="Encrypted secret value")
    encryption_method: EncryptionMethod = Field(default=EncryptionMethod.AES_256_GCM)
    encryption_key_id: Optional[str] = Field(None, description="ID of the encryption key used")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    tags: List[str] = Field(default_factory=list, description="Searchable tags")
    version: int = Field(default=1, description="Secret version number")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    last_accessed_at: Optional[datetime] = None
    access_count: int = Field(default=0, description="Number of times accessed")
    is_active: bool = Field(default=True)
    rotation_enabled: bool = Field(default=False, description="Auto-rotation enabled")
    rotation_days: Optional[int] = Field(None, description="Rotation interval in days")
    blockchain_reference: Optional[str] = Field(None, description="Blockchain transaction hash for verification")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class VaultAccessLog(BaseModel):
    """Audit log for vault access"""
    log_id: Optional[str] = None
    vault_id: str
    user_id: str
    action: VaultAction
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool = Field(default=True)
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class VaultShare(BaseModel):
    """Secret sharing configuration"""
    share_id: Optional[str] = None
    vault_id: str
    owner_user_id: str
    shared_with_user_id: Optional[str] = None
    shared_with_org_id: Optional[str] = None
    permission_level: PermissionLevel = Field(default=PermissionLevel.READ)
    expires_at: Optional[datetime] = None
    is_active: bool = Field(default=True)
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============ Request Models ============

class VaultCreateRequest(BaseModel):
    """Request to create a new secret"""
    secret_type: SecretType
    provider: Optional[SecretProvider] = None
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    secret_value: str = Field(..., description="Plain text secret value to be encrypted")
    organization_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None
    rotation_enabled: bool = Field(default=False)
    rotation_days: Optional[int] = Field(None, ge=1, le=365)
    blockchain_verify: bool = Field(default=False, description="Store hash on blockchain for verification")

    @validator('tags')
    def validate_tags(cls, v):
        if len(v) > 10:
            raise ValueError('Maximum 10 tags allowed')
        return [tag.lower().strip() for tag in v]


class VaultUpdateRequest(BaseModel):
    """Request to update a secret"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    secret_value: Optional[str] = Field(None, description="New secret value")
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    expires_at: Optional[datetime] = None
    rotation_enabled: Optional[bool] = None
    rotation_days: Optional[int] = Field(None, ge=1, le=365)
    is_active: Optional[bool] = None


class VaultShareRequest(BaseModel):
    """Request to share a secret"""
    shared_with_user_id: Optional[str] = None
    shared_with_org_id: Optional[str] = None
    permission_level: PermissionLevel = Field(default=PermissionLevel.READ)
    expires_at: Optional[datetime] = None

    @validator('shared_with_user_id')
    def validate_share_target(cls, v, values):
        if not v and not values.get('shared_with_org_id'):
            raise ValueError('Must specify either shared_with_user_id or shared_with_org_id')
        return v


class VaultTestRequest(BaseModel):
    """Request to test a credential"""
    test_endpoint: Optional[str] = Field(None, description="Optional endpoint to test against")


# ============ Response Models ============

class VaultItemResponse(BaseModel):
    """Response for vault item (without secret value)"""
    vault_id: str
    user_id: str
    organization_id: Optional[str] = None
    secret_type: SecretType
    provider: Optional[SecretProvider] = None
    name: str
    description: Optional[str] = None
    encryption_method: EncryptionMethod
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    version: int
    expires_at: Optional[datetime] = None
    last_accessed_at: Optional[datetime] = None
    access_count: int
    is_active: bool
    rotation_enabled: bool
    rotation_days: Optional[int] = None
    blockchain_reference: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VaultSecretResponse(BaseModel):
    """Response with decrypted secret value"""
    vault_id: str
    name: str
    secret_type: SecretType
    provider: Optional[SecretProvider] = None
    secret_value: str = Field(..., description="Decrypted secret value")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    expires_at: Optional[datetime] = None
    blockchain_verified: bool = Field(default=False, description="Whether blockchain verification passed")


class VaultListResponse(BaseModel):
    """List of vault items"""
    items: List[VaultItemResponse]
    total: int
    page: int
    page_size: int


class VaultShareResponse(BaseModel):
    """Vault share response"""
    share_id: str
    vault_id: str
    owner_user_id: str
    shared_with_user_id: Optional[str] = None
    shared_with_org_id: Optional[str] = None
    permission_level: PermissionLevel
    expires_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class VaultAccessLogResponse(BaseModel):
    """Access log response"""
    log_id: str
    vault_id: str
    user_id: str
    action: VaultAction
    ip_address: Optional[str] = None
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    class Config:
        from_attributes = True


class VaultStatsResponse(BaseModel):
    """Vault service statistics"""
    total_secrets: int = 0
    active_secrets: int = 0
    expired_secrets: int = 0
    secrets_by_type: Dict[str, int] = Field(default_factory=dict)
    secrets_by_provider: Dict[str, int] = Field(default_factory=dict)
    total_access_count: int = 0
    shared_secrets: int = 0
    blockchain_verified_secrets: int = 0


class VaultTestResponse(BaseModel):
    """Response from testing a credential"""
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = "healthy"
    service: str = "vault_service"
    port: int = 8214
    version: str = "1.0.0"


class ServiceInfo(BaseModel):
    """Service information"""
    service: str = "vault_service"
    version: str = "1.0.0"
    description: str = "Secure credential and secret management microservice"
    capabilities: Dict[str, bool] = Field(default_factory=lambda: {
        "encryption": True,
        "secret_storage": True,
        "secret_sharing": True,
        "access_control": True,
        "audit_logging": True,
        "secret_rotation": True,
        "blockchain_verification": True,
        "multi_provider_support": True
    })
    supported_secret_types: List[str] = Field(default_factory=lambda: [
        "api_key", "database_credential", "ssh_key", "ssl_certificate",
        "oauth_token", "aws_credential", "blockchain_key", "environment_variable", "custom"
    ])
    supported_providers: List[str] = Field(default_factory=lambda: [
        "openai", "anthropic", "stripe", "aws", "azure", "gcp",
        "github", "gitlab", "ethereum", "polygon", "custom"
    ])
    endpoints: Dict[str, str] = Field(default_factory=lambda: {
        "health": "/health",
        "create_secret": "/api/v1/vault/secrets",
        "get_secret": "/api/v1/vault/secrets/{vault_id}",
        "list_secrets": "/api/v1/vault/secrets",
        "share_secret": "/api/v1/vault/secrets/{vault_id}/share",
        "test_secret": "/api/v1/vault/secrets/{vault_id}/test"
    })
