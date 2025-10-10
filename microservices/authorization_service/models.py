"""
Authorization Service Data Models

Independent data models for the authorization microservice.
These models are completely separate from the main application models.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, validator


# ====================
# Enums
# ====================

class ResourceType(str, Enum):
    """Resource types that can be authorized"""
    MCP_TOOL = "mcp_tool"
    PROMPT = "prompt"
    RESOURCE = "resource"
    API_ENDPOINT = "api_endpoint"
    DATABASE = "database"
    FILE_STORAGE = "file_storage"
    COMPUTE = "compute"
    AI_MODEL = "ai_model"


class AccessLevel(str, Enum):
    """Access levels for resources"""
    NONE = "none"
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    ADMIN = "admin"
    OWNER = "owner"


class PermissionSource(str, Enum):
    """Source of permission grant"""
    SUBSCRIPTION = "subscription"
    ORGANIZATION = "organization"
    ADMIN_GRANT = "admin_grant"
    SYSTEM_DEFAULT = "system_default"


class SubscriptionTier(str, Enum):
    """Subscription tiers"""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


# ====================
# Base Models
# ====================

class BaseResponse(BaseModel):
    """Base response model"""
    success: bool = True
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    port: int
    version: str


class ServiceInfo(BaseModel):
    """Service information"""
    service: str
    version: str
    description: str
    capabilities: Dict[str, Any]
    endpoints: Dict[str, str]


class ServiceStats(BaseModel):
    """Service statistics"""
    service: str
    version: str
    status: str
    uptime: str
    endpoints_count: int
    statistics: Dict[str, Any]


# ====================
# Core Authorization Models
# ====================

class ResourcePermission(BaseModel):
    """Base resource permission definition"""
    id: Optional[str] = None
    resource_type: ResourceType
    resource_name: str
    resource_category: Optional[str] = None
    description: Optional[str] = None
    subscription_tier_required: SubscriptionTier = SubscriptionTier.FREE
    access_level: AccessLevel = AccessLevel.READ_ONLY
    is_enabled: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UserPermissionRecord(BaseModel):
    """User-specific permission record"""
    id: Optional[str] = None
    user_id: str
    resource_type: ResourceType
    resource_name: str
    access_level: AccessLevel
    permission_source: PermissionSource
    granted_by_user_id: Optional[str] = None
    organization_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @validator('expires_at')
    def validate_expiry(cls, v):
        if v and v <= datetime.utcnow():
            raise ValueError('Expiry date must be in the future')
        return v


class OrganizationPermission(BaseModel):
    """Organization-level permission configuration"""
    id: Optional[str] = None
    organization_id: str
    resource_type: ResourceType
    resource_name: str
    access_level: AccessLevel
    org_plan_required: str = "startup"
    is_enabled: bool = True
    created_by_user_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ====================
# Request/Response Models
# ====================

class ResourceAccessRequest(BaseModel):
    """Request to check resource access"""
    user_id: str
    resource_type: ResourceType
    resource_name: str
    required_access_level: AccessLevel = AccessLevel.READ_ONLY
    organization_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ResourceAccessResponse(BaseModel):
    """Response for resource access check"""
    has_access: bool
    user_access_level: AccessLevel
    permission_source: PermissionSource
    subscription_tier: Optional[str] = None
    organization_plan: Optional[str] = None
    reason: str
    expires_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class GrantPermissionRequest(BaseModel):
    """Request to grant permission"""
    user_id: str
    resource_type: ResourceType
    resource_name: str
    access_level: AccessLevel
    permission_source: PermissionSource
    granted_by_user_id: Optional[str] = None
    organization_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    reason: Optional[str] = None


class RevokePermissionRequest(BaseModel):
    """Request to revoke permission"""
    user_id: str
    resource_type: ResourceType
    resource_name: str
    revoked_by_user_id: Optional[str] = None
    reason: Optional[str] = None


class BulkPermissionRequest(BaseModel):
    """Request for bulk permission operations"""
    operations: List[Union[GrantPermissionRequest, RevokePermissionRequest]]
    executed_by_user_id: Optional[str] = None
    batch_reason: Optional[str] = None


# ====================
# Summary and Analytics Models
# ====================

class UserPermissionSummary(BaseModel):
    """User permission summary"""
    user_id: str
    subscription_tier: str
    organization_id: Optional[str] = None
    organization_plan: Optional[str] = None
    total_permissions: int
    permissions_by_type: Dict[ResourceType, int]
    permissions_by_source: Dict[PermissionSource, int]
    permissions_by_level: Dict[AccessLevel, int]
    expires_soon_count: int
    last_access_check: Optional[datetime] = None
    summary_generated_at: datetime = Field(default_factory=datetime.utcnow)


class ResourceAccessSummary(BaseModel):
    """Resource access summary"""
    resource_type: ResourceType
    resource_name: str
    total_authorized_users: int
    access_level_distribution: Dict[AccessLevel, int]
    permission_source_distribution: Dict[PermissionSource, int]
    organization_access_count: int
    expires_soon_count: int
    last_accessed: Optional[datetime] = None


class OrganizationPermissionSummary(BaseModel):
    """Organization permission summary"""
    organization_id: str
    organization_plan: str
    total_members: int
    total_permissions: int
    permissions_by_type: Dict[ResourceType, int]
    permissions_by_level: Dict[AccessLevel, int]
    member_access_summary: List[Dict[str, Any]]
    summary_generated_at: datetime = Field(default_factory=datetime.utcnow)


# ====================
# Service Communication Models
# ====================

class ExternalServiceUser(BaseModel):
    """User information from account service"""
    user_id: str
    email: str
    subscription_status: str
    is_active: bool
    organization_id: Optional[str] = None


class ExternalServiceOrganization(BaseModel):
    """Organization information from account service"""
    organization_id: str
    plan: str
    is_active: bool
    member_count: int


class ServiceHealthCheck(BaseModel):
    """Health check for external services"""
    service_name: str
    endpoint: str
    is_healthy: bool
    response_time_ms: Optional[float] = None
    last_check: datetime = Field(default_factory=datetime.utcnow)


# ====================
# Database Operation Models
# ====================

class PermissionAuditLog(BaseModel):
    """Audit log for permission changes"""
    id: Optional[str] = None
    user_id: str
    resource_type: ResourceType
    resource_name: str
    action: str  # grant, revoke, check
    old_access_level: Optional[AccessLevel] = None
    new_access_level: Optional[AccessLevel] = None
    performed_by_user_id: Optional[str] = None
    reason: Optional[str] = None
    success: bool
    error_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PermissionCacheEntry(BaseModel):
    """Cache entry for permission checks"""
    cache_key: str
    user_id: str
    resource_type: ResourceType
    resource_name: str
    has_access: bool
    access_level: AccessLevel
    permission_source: PermissionSource
    cached_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(default_factory=lambda: datetime.utcnow() + timedelta(minutes=15))
    
    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at


# ====================
# Error Models
# ====================

class AuthorizationError(BaseModel):
    """Authorization error details"""
    error_code: str
    error_message: str
    user_id: Optional[str] = None
    resource_type: Optional[ResourceType] = None
    resource_name: Optional[str] = None
    suggested_action: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ValidationError(BaseModel):
    """Validation error details"""
    field: str
    error: str
    provided_value: Any
    expected_format: Optional[str] = None


# ====================
# Batch Operation Models
# ====================

class BatchOperationResult(BaseModel):
    """Result of a batch operation"""
    operation_id: str
    operation_type: str  # grant, revoke
    target_user_id: str
    resource_type: ResourceType
    resource_name: str
    success: bool
    error_message: Optional[str] = None
    processed_at: datetime = Field(default_factory=datetime.utcnow)


class BatchOperationSummary(BaseModel):
    """Summary of batch operations"""
    batch_id: str
    total_operations: int
    successful_operations: int
    failed_operations: int
    execution_time_seconds: float
    executed_by_user_id: Optional[str] = None
    results: List[BatchOperationResult]
    started_at: datetime
    completed_at: datetime = Field(default_factory=datetime.utcnow)