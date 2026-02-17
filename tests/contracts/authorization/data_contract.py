"""
Authorization Service Data Contract

Executable data contracts with Pydantic schemas, test data factory, and request builders.
Following CDD Layer 4 specification with ZERO hardcoded data.

All test data MUST be generated through AuthorizationTestDataFactory methods.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Union
from enum import Enum
import secrets
import uuid
import string
import random

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# ENUMS
# =============================================================================


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


class OrganizationPlan(str, Enum):
    """Organization plans"""
    STARTUP = "startup"
    GROWTH = "growth"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


# =============================================================================
# REQUEST CONTRACTS
# =============================================================================


class ResourceAccessRequestContract(BaseModel):
    """Contract for resource access check requests"""
    user_id: str = Field(..., min_length=1, max_length=100, description="User ID")
    resource_type: ResourceType = Field(..., description="Resource type")
    resource_name: str = Field(..., min_length=1, max_length=255, description="Resource name")
    required_access_level: AccessLevel = Field(
        default=AccessLevel.READ_ONLY,
        description="Required access level"
    )
    organization_id: Optional[str] = Field(None, max_length=100, description="Organization ID")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """User ID must not be empty or whitespace"""
        if not v or not v.strip():
            raise ValueError("user_id cannot be empty or whitespace")
        return v.strip()

    @field_validator('resource_name')
    @classmethod
    def validate_resource_name(cls, v: str) -> str:
        """Resource name must not be empty or whitespace"""
        if not v or not v.strip():
            raise ValueError("resource_name cannot be empty or whitespace")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_12345",
                "resource_type": "api_endpoint",
                "resource_name": "/api/data",
                "required_access_level": "read_only"
            }
        }


class GrantPermissionRequestContract(BaseModel):
    """Contract for permission grant requests"""
    user_id: str = Field(..., min_length=1, max_length=100, description="Target user ID")
    resource_type: ResourceType = Field(..., description="Resource type")
    resource_name: str = Field(..., min_length=1, max_length=255, description="Resource name")
    access_level: AccessLevel = Field(..., description="Access level to grant")
    permission_source: PermissionSource = Field(..., description="Source of permission")
    granted_by_user_id: Optional[str] = Field(None, max_length=100, description="Granting admin ID")
    organization_id: Optional[str] = Field(None, max_length=100, description="Organization context")
    expires_at: Optional[datetime] = Field(None, description="Permission expiration")
    reason: Optional[str] = Field(None, max_length=500, description="Grant reason")

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("user_id cannot be empty or whitespace")
        return v.strip()

    @field_validator('resource_name')
    @classmethod
    def validate_resource_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("resource_name cannot be empty or whitespace")
        return v.strip()

    @field_validator('expires_at')
    @classmethod
    def validate_expires_at(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Expiry must be in the future"""
        if v and v <= datetime.now(timezone.utc):
            raise ValueError("expires_at must be in the future")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_12345",
                "resource_type": "api_endpoint",
                "resource_name": "/api/admin",
                "access_level": "admin",
                "permission_source": "admin_grant",
                "granted_by_user_id": "admin_001"
            }
        }


class RevokePermissionRequestContract(BaseModel):
    """Contract for permission revoke requests"""
    user_id: str = Field(..., min_length=1, max_length=100, description="Target user ID")
    resource_type: ResourceType = Field(..., description="Resource type")
    resource_name: str = Field(..., min_length=1, max_length=255, description="Resource name")
    revoked_by_user_id: Optional[str] = Field(None, max_length=100, description="Revoking admin ID")
    reason: Optional[str] = Field(None, max_length=500, description="Revoke reason")

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("user_id cannot be empty or whitespace")
        return v.strip()

    @field_validator('resource_name')
    @classmethod
    def validate_resource_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("resource_name cannot be empty or whitespace")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_12345",
                "resource_type": "api_endpoint",
                "resource_name": "/api/admin",
                "revoked_by_user_id": "admin_001",
                "reason": "Access review completed"
            }
        }


class BulkPermissionRequestContract(BaseModel):
    """Contract for bulk permission operations"""
    operations: List[Union[GrantPermissionRequestContract, RevokePermissionRequestContract]] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of permission operations"
    )
    executed_by_user_id: Optional[str] = Field(None, max_length=100, description="Executing admin ID")
    batch_reason: Optional[str] = Field(None, max_length=500, description="Batch operation reason")

    @field_validator('operations')
    @classmethod
    def validate_operations(cls, v: List) -> List:
        if not v:
            raise ValueError("operations cannot be empty")
        if len(v) > 100:
            raise ValueError("maximum 100 operations per batch")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "operations": [
                    {
                        "user_id": "user_001",
                        "resource_type": "api_endpoint",
                        "resource_name": "/api/data",
                        "access_level": "read_write",
                        "permission_source": "admin_grant"
                    }
                ],
                "executed_by_user_id": "admin_001",
                "batch_reason": "Team onboarding"
            }
        }


class UserPermissionsQueryContract(BaseModel):
    """Contract for user permission queries"""
    resource_type: Optional[ResourceType] = Field(None, description="Filter by resource type")


class ResourcePermissionConfigContract(BaseModel):
    """Contract for resource permission configuration"""
    resource_type: ResourceType = Field(..., description="Resource type")
    resource_name: str = Field(..., min_length=1, max_length=255, description="Resource name")
    resource_category: Optional[str] = Field(None, max_length=100, description="Resource category")
    subscription_tier_required: SubscriptionTier = Field(
        default=SubscriptionTier.FREE,
        description="Minimum subscription tier"
    )
    access_level: AccessLevel = Field(
        default=AccessLevel.READ_ONLY,
        description="Default access level"
    )
    description: Optional[str] = Field(None, max_length=500, description="Resource description")
    is_enabled: bool = Field(default=True, description="Whether resource is enabled")

    @field_validator('resource_name')
    @classmethod
    def validate_resource_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("resource_name cannot be empty or whitespace")
        return v.strip()


class OrganizationPermissionConfigContract(BaseModel):
    """Contract for organization permission configuration"""
    organization_id: str = Field(..., min_length=1, max_length=100, description="Organization ID")
    resource_type: ResourceType = Field(..., description="Resource type")
    resource_name: str = Field(..., min_length=1, max_length=255, description="Resource name")
    access_level: AccessLevel = Field(..., description="Access level for org members")
    org_plan_required: OrganizationPlan = Field(
        default=OrganizationPlan.STARTUP,
        description="Minimum org plan required"
    )
    is_enabled: bool = Field(default=True, description="Whether permission is enabled")
    created_by_user_id: Optional[str] = Field(None, max_length=100, description="Creator admin ID")


# =============================================================================
# RESPONSE CONTRACTS
# =============================================================================


class ResourceAccessResponseContract(BaseModel):
    """Contract for resource access check response"""
    has_access: bool = Field(..., description="Whether access is granted")
    user_access_level: AccessLevel = Field(..., description="User's effective access level")
    permission_source: PermissionSource = Field(..., description="Source of the permission")
    subscription_tier: Optional[str] = Field(None, description="User's subscription tier")
    organization_plan: Optional[str] = Field(None, description="Organization plan if applicable")
    reason: str = Field(..., description="Human-readable explanation")
    expires_at: Optional[datetime] = Field(None, description="Permission expiration if applicable")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class PermissionGrantResponseContract(BaseModel):
    """Contract for permission grant response"""
    success: bool = True
    message: str = Field(default="Permission granted successfully")


class PermissionRevokeResponseContract(BaseModel):
    """Contract for permission revoke response"""
    success: bool = True
    message: str = Field(default="Permission revoked successfully")


class BatchOperationResultContract(BaseModel):
    """Contract for individual batch operation result"""
    operation_id: str = Field(..., description="Unique operation ID")
    operation_type: str = Field(..., description="Operation type (grant/revoke)")
    target_user_id: str = Field(..., description="Target user ID")
    resource_type: ResourceType = Field(..., description="Resource type")
    resource_name: str = Field(..., description="Resource name")
    success: bool = Field(..., description="Whether operation succeeded")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    processed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BulkPermissionResponseContract(BaseModel):
    """Contract for bulk permission operation response"""
    total_operations: int = Field(..., description="Total operations in batch")
    successful: int = Field(..., description="Number of successful operations")
    failed: int = Field(..., description="Number of failed operations")
    results: List[BatchOperationResultContract] = Field(..., description="Individual results")


class UserPermissionSummaryResponseContract(BaseModel):
    """Contract for user permission summary response"""
    user_id: str = Field(..., description="User ID")
    subscription_tier: str = Field(..., description="User's subscription tier")
    organization_id: Optional[str] = Field(None, description="Organization ID if member")
    organization_plan: Optional[str] = Field(None, description="Organization plan if member")
    total_permissions: int = Field(..., description="Total permission count")
    permissions_by_type: Dict[str, int] = Field(..., description="Permissions grouped by type")
    permissions_by_source: Dict[str, int] = Field(..., description="Permissions grouped by source")
    permissions_by_level: Dict[str, int] = Field(..., description="Permissions grouped by level")
    expires_soon_count: int = Field(..., description="Permissions expiring within 7 days")
    last_access_check: Optional[datetime] = Field(None, description="Last access check timestamp")
    summary_generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserAccessibleResourceContract(BaseModel):
    """Contract for a single accessible resource"""
    resource_type: str = Field(..., description="Resource type")
    resource_name: str = Field(..., description="Resource name")
    access_level: str = Field(..., description="Access level")
    permission_source: str = Field(..., description="Permission source")
    expires_at: Optional[datetime] = Field(None, description="Expiration if applicable")
    subscription_required: Optional[str] = Field(None, description="Required subscription tier")
    resource_category: Optional[str] = Field(None, description="Resource category")
    organization_id: Optional[str] = Field(None, description="Organization context")


class UserAccessibleResourcesResponseContract(BaseModel):
    """Contract for user accessible resources response"""
    user_id: str = Field(..., description="User ID")
    resource_type_filter: Optional[str] = Field(None, description="Applied resource type filter")
    accessible_resources: List[UserAccessibleResourceContract] = Field(..., description="Accessible resources")
    total_count: int = Field(..., description="Total accessible resource count")


class ServiceStatsResponseContract(BaseModel):
    """Contract for service statistics response"""
    service: str = Field(default="authorization_service")
    version: str = Field(default="1.0.0")
    status: str = Field(default="operational")
    uptime: str = Field(default="running")
    endpoints_count: int = Field(default=8)
    statistics: Dict[str, Any] = Field(default_factory=dict)


class HealthResponseContract(BaseModel):
    """Contract for health check response"""
    status: str = Field(..., description="Health status")
    service: str = Field(..., description="Service name")
    port: int = Field(..., description="Service port")
    version: str = Field(..., description="Service version")


class DetailedHealthResponseContract(BaseModel):
    """Contract for detailed health check response"""
    service: str = Field(..., description="Service name")
    status: str = Field(..., description="Operational status")
    port: int = Field(..., description="Service port")
    version: str = Field(..., description="Service version")
    database_connected: bool = Field(..., description="Database connectivity status")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ErrorResponseContract(BaseModel):
    """Contract for error responses"""
    detail: str = Field(..., description="Error detail message")
    error_code: Optional[str] = Field(None, description="Error code")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CleanupResponseContract(BaseModel):
    """Contract for cleanup operation response"""
    message: str = Field(..., description="Operation message")
    cleaned_count: int = Field(..., description="Number of cleaned items")


# =============================================================================
# TEST DATA FACTORY
# =============================================================================


class AuthorizationTestDataFactory:
    """
    Test data factory for authorization_service.

    Zero hardcoded data - all values generated dynamically.
    Methods prefixed with 'make_' generate valid data.
    Methods prefixed with 'make_invalid_' generate invalid data.
    """

    # =========================================================================
    # ID Generators
    # =========================================================================

    @staticmethod
    def make_user_id(prefix: str = "user") -> str:
        """Generate valid user ID"""
        return f"{prefix}_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_admin_id() -> str:
        """Generate valid admin user ID"""
        return f"admin_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def make_organization_id() -> str:
        """Generate valid organization ID"""
        return f"org_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_permission_id() -> str:
        """Generate valid permission ID"""
        return f"perm_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_operation_id() -> str:
        """Generate valid operation ID"""
        return str(uuid.uuid4())

    @staticmethod
    def make_batch_id() -> str:
        """Generate valid batch ID"""
        return f"batch_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def make_correlation_id() -> str:
        """Generate correlation ID for tracing"""
        return f"corr_{uuid.uuid4().hex[:16]}"

    # =========================================================================
    # String Generators
    # =========================================================================

    @staticmethod
    def make_resource_name(prefix: str = "/api") -> str:
        """Generate valid resource name"""
        return f"{prefix}/{secrets.token_hex(4)}"

    @staticmethod
    def make_api_endpoint_name() -> str:
        """Generate valid API endpoint resource name"""
        endpoints = ["data", "admin", "users", "reports", "analytics", "config"]
        return f"/api/v1/{random.choice(endpoints)}/{secrets.token_hex(3)}"

    @staticmethod
    def make_mcp_tool_name() -> str:
        """Generate valid MCP tool resource name"""
        tools = ["weather_api", "image_generator", "code_analyzer", "data_processor"]
        return f"{random.choice(tools)}_{secrets.token_hex(3)}"

    @staticmethod
    def make_ai_model_name() -> str:
        """Generate valid AI model resource name"""
        models = ["gpt4", "claude", "llama", "gemini", "mistral"]
        return f"{random.choice(models)}_{secrets.token_hex(3)}"

    @staticmethod
    def make_database_name() -> str:
        """Generate valid database resource name"""
        dbs = ["analytics_db", "user_db", "metrics_db", "logs_db"]
        return f"{random.choice(dbs)}_{secrets.token_hex(3)}"

    @staticmethod
    def make_resource_category() -> str:
        """Generate valid resource category"""
        categories = ["utilities", "ai_tools", "data", "admin", "reporting", "storage"]
        return random.choice(categories)

    @staticmethod
    def make_reason(prefix: str = "Reason") -> str:
        """Generate valid reason string"""
        reasons = ["Policy change", "Access review", "Security audit", "Team onboarding", "Feature access"]
        return f"{random.choice(reasons)} {secrets.token_hex(4)}"

    @staticmethod
    def make_description(length: int = 50) -> str:
        """Generate random description"""
        words = ["access", "resource", "permission", "control", "management", "authorization"]
        return " ".join(random.choices(words, k=min(length // 8, 10)))

    @staticmethod
    def make_email(domain: str = "example.com") -> str:
        """Generate unique email"""
        return f"user_{secrets.token_hex(4)}@{domain}"

    # =========================================================================
    # Enum Generators
    # =========================================================================

    @staticmethod
    def make_resource_type() -> ResourceType:
        """Generate random valid resource type"""
        return random.choice(list(ResourceType))

    @staticmethod
    def make_access_level() -> AccessLevel:
        """Generate random valid access level"""
        return random.choice(list(AccessLevel))

    @staticmethod
    def make_permission_source() -> PermissionSource:
        """Generate random valid permission source"""
        return random.choice(list(PermissionSource))

    @staticmethod
    def make_subscription_tier() -> SubscriptionTier:
        """Generate random valid subscription tier"""
        return random.choice(list(SubscriptionTier))

    @staticmethod
    def make_organization_plan() -> OrganizationPlan:
        """Generate random valid organization plan"""
        return random.choice(list(OrganizationPlan))

    # =========================================================================
    # Timestamp Generators
    # =========================================================================

    @staticmethod
    def make_timestamp() -> datetime:
        """Generate current UTC timestamp"""
        return datetime.now(timezone.utc)

    @staticmethod
    def make_past_timestamp(days: int = 30) -> datetime:
        """Generate timestamp in the past"""
        return datetime.now(timezone.utc) - timedelta(days=random.randint(1, days))

    @staticmethod
    def make_future_timestamp(days: int = 30) -> datetime:
        """Generate timestamp in the future"""
        return datetime.now(timezone.utc) + timedelta(days=random.randint(1, days))

    @staticmethod
    def make_expires_soon_timestamp() -> datetime:
        """Generate timestamp expiring within 7 days"""
        return datetime.now(timezone.utc) + timedelta(days=random.randint(1, 7))

    @staticmethod
    def make_timestamp_iso() -> str:
        """Generate ISO format timestamp string"""
        return datetime.now(timezone.utc).isoformat()

    # =========================================================================
    # Numeric Generators
    # =========================================================================

    @staticmethod
    def make_positive_int(max_val: int = 1000) -> int:
        """Generate positive integer"""
        return random.randint(1, max_val)

    @staticmethod
    def make_permission_count() -> int:
        """Generate realistic permission count"""
        return random.randint(5, 50)

    @staticmethod
    def make_port() -> int:
        """Generate service port number"""
        return 8203

    # =========================================================================
    # Request Generators (Valid Data)
    # =========================================================================

    @staticmethod
    def make_access_check_request(**overrides) -> ResourceAccessRequestContract:
        """Generate valid access check request"""
        defaults = {
            "user_id": AuthorizationTestDataFactory.make_user_id(),
            "resource_type": AuthorizationTestDataFactory.make_resource_type(),
            "resource_name": AuthorizationTestDataFactory.make_resource_name(),
            "required_access_level": AccessLevel.READ_ONLY,
            "organization_id": None,
            "context": {},
        }
        defaults.update(overrides)
        return ResourceAccessRequestContract(**defaults)

    @staticmethod
    def make_grant_request(**overrides) -> GrantPermissionRequestContract:
        """Generate valid grant permission request"""
        defaults = {
            "user_id": AuthorizationTestDataFactory.make_user_id(),
            "resource_type": AuthorizationTestDataFactory.make_resource_type(),
            "resource_name": AuthorizationTestDataFactory.make_resource_name(),
            "access_level": AccessLevel.READ_WRITE,
            "permission_source": PermissionSource.ADMIN_GRANT,
            "granted_by_user_id": AuthorizationTestDataFactory.make_admin_id(),
            "organization_id": None,
            "expires_at": None,
            "reason": AuthorizationTestDataFactory.make_reason("Grant"),
        }
        defaults.update(overrides)
        return GrantPermissionRequestContract(**defaults)

    @staticmethod
    def make_revoke_request(**overrides) -> RevokePermissionRequestContract:
        """Generate valid revoke permission request"""
        defaults = {
            "user_id": AuthorizationTestDataFactory.make_user_id(),
            "resource_type": AuthorizationTestDataFactory.make_resource_type(),
            "resource_name": AuthorizationTestDataFactory.make_resource_name(),
            "revoked_by_user_id": AuthorizationTestDataFactory.make_admin_id(),
            "reason": AuthorizationTestDataFactory.make_reason("Revoke"),
        }
        defaults.update(overrides)
        return RevokePermissionRequestContract(**defaults)

    @staticmethod
    def make_bulk_grant_request(count: int = 3, **overrides) -> BulkPermissionRequestContract:
        """Generate valid bulk grant request"""
        operations = [
            AuthorizationTestDataFactory.make_grant_request()
            for _ in range(count)
        ]
        defaults = {
            "operations": operations,
            "executed_by_user_id": AuthorizationTestDataFactory.make_admin_id(),
            "batch_reason": AuthorizationTestDataFactory.make_reason("Bulk grant"),
        }
        defaults.update(overrides)
        return BulkPermissionRequestContract(**defaults)

    @staticmethod
    def make_bulk_revoke_request(count: int = 3, **overrides) -> BulkPermissionRequestContract:
        """Generate valid bulk revoke request"""
        operations = [
            AuthorizationTestDataFactory.make_revoke_request()
            for _ in range(count)
        ]
        defaults = {
            "operations": operations,
            "executed_by_user_id": AuthorizationTestDataFactory.make_admin_id(),
            "batch_reason": AuthorizationTestDataFactory.make_reason("Bulk revoke"),
        }
        defaults.update(overrides)
        return BulkPermissionRequestContract(**defaults)

    @staticmethod
    def make_resource_config_request(**overrides) -> ResourcePermissionConfigContract:
        """Generate valid resource permission config"""
        defaults = {
            "resource_type": AuthorizationTestDataFactory.make_resource_type(),
            "resource_name": AuthorizationTestDataFactory.make_resource_name(),
            "resource_category": AuthorizationTestDataFactory.make_resource_category(),
            "subscription_tier_required": SubscriptionTier.FREE,
            "access_level": AccessLevel.READ_ONLY,
            "description": AuthorizationTestDataFactory.make_description(),
            "is_enabled": True,
        }
        defaults.update(overrides)
        return ResourcePermissionConfigContract(**defaults)

    @staticmethod
    def make_org_permission_config_request(**overrides) -> OrganizationPermissionConfigContract:
        """Generate valid organization permission config"""
        defaults = {
            "organization_id": AuthorizationTestDataFactory.make_organization_id(),
            "resource_type": AuthorizationTestDataFactory.make_resource_type(),
            "resource_name": AuthorizationTestDataFactory.make_resource_name(),
            "access_level": AccessLevel.READ_WRITE,
            "org_plan_required": OrganizationPlan.STARTUP,
            "is_enabled": True,
            "created_by_user_id": AuthorizationTestDataFactory.make_admin_id(),
        }
        defaults.update(overrides)
        return OrganizationPermissionConfigContract(**defaults)

    # =========================================================================
    # Response Generators
    # =========================================================================

    @staticmethod
    def make_access_granted_response(**overrides) -> Dict[str, Any]:
        """Generate access granted response"""
        defaults = {
            "has_access": True,
            "user_access_level": "read_write",
            "permission_source": "subscription",
            "subscription_tier": "pro",
            "organization_plan": None,
            "reason": "Subscription access: read_write",
            "expires_at": None,
            "metadata": {"subscription_required": "pro"},
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_access_denied_response(**overrides) -> Dict[str, Any]:
        """Generate access denied response"""
        defaults = {
            "has_access": False,
            "user_access_level": "none",
            "permission_source": "system_default",
            "subscription_tier": "free",
            "organization_plan": None,
            "reason": "Insufficient permissions",
            "expires_at": None,
            "metadata": {"required_level": "admin"},
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_permission_summary_response(**overrides) -> Dict[str, Any]:
        """Generate user permission summary response"""
        defaults = {
            "user_id": AuthorizationTestDataFactory.make_user_id(),
            "subscription_tier": "pro",
            "organization_id": AuthorizationTestDataFactory.make_organization_id(),
            "organization_plan": "growth",
            "total_permissions": AuthorizationTestDataFactory.make_permission_count(),
            "permissions_by_type": {
                "api_endpoint": random.randint(1, 10),
                "mcp_tool": random.randint(1, 5),
                "ai_model": random.randint(1, 5),
            },
            "permissions_by_source": {
                "subscription": random.randint(5, 15),
                "organization": random.randint(1, 5),
                "admin_grant": random.randint(0, 3),
            },
            "permissions_by_level": {
                "read_only": random.randint(5, 15),
                "read_write": random.randint(3, 10),
                "admin": random.randint(0, 3),
            },
            "expires_soon_count": random.randint(0, 3),
            "last_access_check": AuthorizationTestDataFactory.make_timestamp_iso(),
            "summary_generated_at": AuthorizationTestDataFactory.make_timestamp_iso(),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_accessible_resource(**overrides) -> Dict[str, Any]:
        """Generate single accessible resource"""
        defaults = {
            "resource_type": AuthorizationTestDataFactory.make_resource_type().value,
            "resource_name": AuthorizationTestDataFactory.make_resource_name(),
            "access_level": AuthorizationTestDataFactory.make_access_level().value,
            "permission_source": AuthorizationTestDataFactory.make_permission_source().value,
            "expires_at": None,
            "subscription_required": "pro",
            "resource_category": AuthorizationTestDataFactory.make_resource_category(),
            "organization_id": None,
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_accessible_resources_response(count: int = 5, **overrides) -> Dict[str, Any]:
        """Generate accessible resources list response"""
        resources = [
            AuthorizationTestDataFactory.make_accessible_resource()
            for _ in range(count)
        ]
        defaults = {
            "user_id": AuthorizationTestDataFactory.make_user_id(),
            "resource_type_filter": None,
            "accessible_resources": resources,
            "total_count": count,
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_batch_result(**overrides) -> Dict[str, Any]:
        """Generate batch operation result"""
        success = random.choice([True, True, True, False])  # 75% success rate
        defaults = {
            "operation_id": AuthorizationTestDataFactory.make_operation_id(),
            "operation_type": random.choice(["grant", "revoke"]),
            "target_user_id": AuthorizationTestDataFactory.make_user_id(),
            "resource_type": AuthorizationTestDataFactory.make_resource_type().value,
            "resource_name": AuthorizationTestDataFactory.make_resource_name(),
            "success": success,
            "error_message": None if success else "Operation failed",
            "processed_at": AuthorizationTestDataFactory.make_timestamp_iso(),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_bulk_response(total: int = 5, **overrides) -> Dict[str, Any]:
        """Generate bulk operation response"""
        results = [
            AuthorizationTestDataFactory.make_batch_result()
            for _ in range(total)
        ]
        successful = sum(1 for r in results if r["success"])
        defaults = {
            "total_operations": total,
            "successful": successful,
            "failed": total - successful,
            "results": results,
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_service_stats_response(**overrides) -> Dict[str, Any]:
        """Generate service statistics response"""
        defaults = {
            "service": "authorization_service",
            "version": "1.0.0",
            "status": "operational",
            "uptime": "running",
            "endpoints_count": 10,
            "statistics": {
                "total_permissions": AuthorizationTestDataFactory.make_positive_int(5000),
                "active_users": AuthorizationTestDataFactory.make_positive_int(500),
                "resource_types": 8,
            },
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_health_response(**overrides) -> Dict[str, Any]:
        """Generate health check response"""
        defaults = {
            "status": "healthy",
            "service": "authorization_service",
            "port": 8203,
            "version": "1.0.0",
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_detailed_health_response(**overrides) -> Dict[str, Any]:
        """Generate detailed health check response"""
        defaults = {
            "service": "authorization_service",
            "status": "operational",
            "port": 8203,
            "version": "1.0.0",
            "database_connected": True,
            "timestamp": AuthorizationTestDataFactory.make_timestamp_iso(),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_error_response(status_code: int = 400, **overrides) -> Dict[str, Any]:
        """Generate error response"""
        defaults = {
            "detail": f"Error occurred: {secrets.token_hex(4)}",
            "error_code": "ERROR",
            "timestamp": AuthorizationTestDataFactory.make_timestamp_iso(),
        }
        defaults.update(overrides)
        return defaults

    # =========================================================================
    # Invalid Data Generators
    # =========================================================================

    @staticmethod
    def make_invalid_user_id_empty() -> str:
        """Generate empty user ID"""
        return ""

    @staticmethod
    def make_invalid_user_id_whitespace() -> str:
        """Generate whitespace-only user ID"""
        return "   "

    @staticmethod
    def make_invalid_user_id_too_long() -> str:
        """Generate user ID exceeding max length"""
        return "x" * 101

    @staticmethod
    def make_invalid_resource_name_empty() -> str:
        """Generate empty resource name"""
        return ""

    @staticmethod
    def make_invalid_resource_name_whitespace() -> str:
        """Generate whitespace-only resource name"""
        return "   "

    @staticmethod
    def make_invalid_resource_name_too_long() -> str:
        """Generate resource name exceeding max length"""
        return "/" + "x" * 256

    @staticmethod
    def make_invalid_resource_type() -> str:
        """Generate invalid resource type"""
        return "invalid_type"

    @staticmethod
    def make_invalid_access_level() -> str:
        """Generate invalid access level"""
        return "invalid_level"

    @staticmethod
    def make_invalid_permission_source() -> str:
        """Generate invalid permission source"""
        return "invalid_source"

    @staticmethod
    def make_invalid_subscription_tier() -> str:
        """Generate invalid subscription tier"""
        return "invalid_tier"

    @staticmethod
    def make_invalid_expires_at_past() -> datetime:
        """Generate expired timestamp (in the past)"""
        return datetime.now(timezone.utc) - timedelta(days=1)

    @staticmethod
    def make_invalid_bulk_operations_empty() -> List:
        """Generate empty operations list"""
        return []

    @staticmethod
    def make_invalid_bulk_operations_too_many() -> List:
        """Generate operations list exceeding max"""
        return [
            AuthorizationTestDataFactory.make_grant_request()
            for _ in range(101)
        ]

    @staticmethod
    def make_invalid_reason_too_long() -> str:
        """Generate reason exceeding max length"""
        return "x" * 501

    @staticmethod
    def make_nonexistent_user_id() -> str:
        """Generate user ID that doesn't exist"""
        return f"nonexistent_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def make_nonexistent_organization_id() -> str:
        """Generate organization ID that doesn't exist"""
        return f"nonexistent_org_{uuid.uuid4().hex[:8]}"

    # =========================================================================
    # Edge Case Generators
    # =========================================================================

    @staticmethod
    def make_unicode_resource_name() -> str:
        """Generate resource name with unicode characters"""
        return f"/api/\u4e2d\u6587/{secrets.token_hex(3)}"

    @staticmethod
    def make_special_chars_resource_name() -> str:
        """Generate resource name with special characters"""
        return f"/api/test-name_{secrets.token_hex(3)}"

    @staticmethod
    def make_max_length_resource_name() -> str:
        """Generate resource name at max length (255 chars)"""
        return "/" + "x" * 254

    @staticmethod
    def make_min_length_resource_name() -> str:
        """Generate resource name at min length (1 char)"""
        return "x"

    @staticmethod
    def make_max_length_user_id() -> str:
        """Generate user ID at max length (100 chars)"""
        return "x" * 100

    @staticmethod
    def make_min_length_user_id() -> str:
        """Generate user ID at min length (1 char)"""
        return "x"

    # =========================================================================
    # Batch Generators
    # =========================================================================

    @staticmethod
    def make_batch_user_ids(count: int = 5) -> List[str]:
        """Generate multiple user IDs"""
        return [
            AuthorizationTestDataFactory.make_user_id()
            for _ in range(count)
        ]

    @staticmethod
    def make_batch_grant_requests(count: int = 5) -> List[GrantPermissionRequestContract]:
        """Generate multiple grant requests"""
        return [
            AuthorizationTestDataFactory.make_grant_request()
            for _ in range(count)
        ]

    @staticmethod
    def make_batch_revoke_requests(count: int = 5) -> List[RevokePermissionRequestContract]:
        """Generate multiple revoke requests"""
        return [
            AuthorizationTestDataFactory.make_revoke_request()
            for _ in range(count)
        ]

    @staticmethod
    def make_batch_resource_configs(count: int = 5) -> List[ResourcePermissionConfigContract]:
        """Generate multiple resource configs"""
        return [
            AuthorizationTestDataFactory.make_resource_config_request()
            for _ in range(count)
        ]

    # =========================================================================
    # Event Data Generators
    # =========================================================================

    @staticmethod
    def make_permission_granted_event_data(**overrides) -> Dict[str, Any]:
        """Generate permission.granted event data"""
        defaults = {
            "user_id": AuthorizationTestDataFactory.make_user_id(),
            "resource_type": AuthorizationTestDataFactory.make_resource_type().value,
            "resource_name": AuthorizationTestDataFactory.make_resource_name(),
            "access_level": AuthorizationTestDataFactory.make_access_level().value,
            "permission_source": PermissionSource.ADMIN_GRANT.value,
            "granted_by_user_id": AuthorizationTestDataFactory.make_admin_id(),
            "organization_id": None,
            "timestamp": AuthorizationTestDataFactory.make_timestamp_iso(),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_permission_revoked_event_data(**overrides) -> Dict[str, Any]:
        """Generate permission.revoked event data"""
        defaults = {
            "user_id": AuthorizationTestDataFactory.make_user_id(),
            "resource_type": AuthorizationTestDataFactory.make_resource_type().value,
            "resource_name": AuthorizationTestDataFactory.make_resource_name(),
            "previous_access_level": AuthorizationTestDataFactory.make_access_level().value,
            "revoked_by_user_id": AuthorizationTestDataFactory.make_admin_id(),
            "reason": AuthorizationTestDataFactory.make_reason("Revoke"),
            "timestamp": AuthorizationTestDataFactory.make_timestamp_iso(),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_access_denied_event_data(**overrides) -> Dict[str, Any]:
        """Generate access.denied event data"""
        defaults = {
            "user_id": AuthorizationTestDataFactory.make_user_id(),
            "resource_type": AuthorizationTestDataFactory.make_resource_type().value,
            "resource_name": AuthorizationTestDataFactory.make_resource_name(),
            "required_access_level": AuthorizationTestDataFactory.make_access_level().value,
            "reason": "Insufficient permissions",
            "timestamp": AuthorizationTestDataFactory.make_timestamp_iso(),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_user_deleted_event_data(**overrides) -> Dict[str, Any]:
        """Generate user.deleted event data (consumed)"""
        defaults = {
            "user_id": AuthorizationTestDataFactory.make_user_id(),
            "timestamp": AuthorizationTestDataFactory.make_timestamp_iso(),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_org_member_added_event_data(**overrides) -> Dict[str, Any]:
        """Generate organization.member_added event data (consumed)"""
        defaults = {
            "organization_id": AuthorizationTestDataFactory.make_organization_id(),
            "user_id": AuthorizationTestDataFactory.make_user_id(),
            "role": "member",
            "added_by": AuthorizationTestDataFactory.make_admin_id(),
            "timestamp": AuthorizationTestDataFactory.make_timestamp_iso(),
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_org_member_removed_event_data(**overrides) -> Dict[str, Any]:
        """Generate organization.member_removed event data (consumed)"""
        defaults = {
            "organization_id": AuthorizationTestDataFactory.make_organization_id(),
            "user_id": AuthorizationTestDataFactory.make_user_id(),
            "removed_by": AuthorizationTestDataFactory.make_admin_id(),
            "timestamp": AuthorizationTestDataFactory.make_timestamp_iso(),
        }
        defaults.update(overrides)
        return defaults


# =============================================================================
# REQUEST BUILDERS
# =============================================================================


class AccessCheckRequestBuilder:
    """Builder for access check requests with fluent API"""

    def __init__(self):
        """Initialize with factory-generated defaults"""
        self._user_id = AuthorizationTestDataFactory.make_user_id()
        self._resource_type = ResourceType.API_ENDPOINT
        self._resource_name = AuthorizationTestDataFactory.make_api_endpoint_name()
        self._required_access_level = AccessLevel.READ_ONLY
        self._organization_id: Optional[str] = None
        self._context: Dict[str, Any] = {}

    def with_user_id(self, user_id: str) -> 'AccessCheckRequestBuilder':
        """Set custom user ID"""
        self._user_id = user_id
        return self

    def with_resource_type(self, resource_type: ResourceType) -> 'AccessCheckRequestBuilder':
        """Set custom resource type"""
        self._resource_type = resource_type
        return self

    def with_resource_name(self, resource_name: str) -> 'AccessCheckRequestBuilder':
        """Set custom resource name"""
        self._resource_name = resource_name
        return self

    def with_required_level(self, level: AccessLevel) -> 'AccessCheckRequestBuilder':
        """Set required access level"""
        self._required_access_level = level
        return self

    def with_organization(self, org_id: str) -> 'AccessCheckRequestBuilder':
        """Set organization context"""
        self._organization_id = org_id
        return self

    def with_context(self, context: Dict[str, Any]) -> 'AccessCheckRequestBuilder':
        """Set additional context"""
        self._context = context
        return self

    def with_invalid_user_id(self) -> 'AccessCheckRequestBuilder':
        """Set invalid user ID for negative testing"""
        self._user_id = AuthorizationTestDataFactory.make_invalid_user_id_empty()
        return self

    def with_invalid_resource_name(self) -> 'AccessCheckRequestBuilder':
        """Set invalid resource name for negative testing"""
        self._resource_name = AuthorizationTestDataFactory.make_invalid_resource_name_empty()
        return self

    def build(self) -> ResourceAccessRequestContract:
        """Build the request contract"""
        return ResourceAccessRequestContract(
            user_id=self._user_id,
            resource_type=self._resource_type,
            resource_name=self._resource_name,
            required_access_level=self._required_access_level,
            organization_id=self._organization_id,
            context=self._context,
        )

    def build_dict(self) -> Dict[str, Any]:
        """Build as dictionary for API calls"""
        return self.build().model_dump(mode='json')


class GrantPermissionRequestBuilder:
    """Builder for grant permission requests with fluent API"""

    def __init__(self):
        """Initialize with factory-generated defaults"""
        self._user_id = AuthorizationTestDataFactory.make_user_id()
        self._resource_type = ResourceType.API_ENDPOINT
        self._resource_name = AuthorizationTestDataFactory.make_api_endpoint_name()
        self._access_level = AccessLevel.READ_WRITE
        self._permission_source = PermissionSource.ADMIN_GRANT
        self._granted_by_user_id = AuthorizationTestDataFactory.make_admin_id()
        self._organization_id: Optional[str] = None
        self._expires_at: Optional[datetime] = None
        self._reason: Optional[str] = None

    def with_user_id(self, user_id: str) -> 'GrantPermissionRequestBuilder':
        """Set target user ID"""
        self._user_id = user_id
        return self

    def with_resource_type(self, resource_type: ResourceType) -> 'GrantPermissionRequestBuilder':
        """Set resource type"""
        self._resource_type = resource_type
        return self

    def with_resource_name(self, resource_name: str) -> 'GrantPermissionRequestBuilder':
        """Set resource name"""
        self._resource_name = resource_name
        return self

    def with_access_level(self, level: AccessLevel) -> 'GrantPermissionRequestBuilder':
        """Set access level to grant"""
        self._access_level = level
        return self

    def with_permission_source(self, source: PermissionSource) -> 'GrantPermissionRequestBuilder':
        """Set permission source"""
        self._permission_source = source
        return self

    def with_granted_by(self, admin_id: str) -> 'GrantPermissionRequestBuilder':
        """Set granting admin ID"""
        self._granted_by_user_id = admin_id
        return self

    def with_organization(self, org_id: str) -> 'GrantPermissionRequestBuilder':
        """Set organization context"""
        self._organization_id = org_id
        return self

    def with_expiration(self, expires_at: datetime) -> 'GrantPermissionRequestBuilder':
        """Set permission expiration"""
        self._expires_at = expires_at
        return self

    def with_reason(self, reason: str) -> 'GrantPermissionRequestBuilder':
        """Set grant reason"""
        self._reason = reason
        return self

    def with_invalid_user_id(self) -> 'GrantPermissionRequestBuilder':
        """Set invalid user ID for negative testing"""
        self._user_id = AuthorizationTestDataFactory.make_invalid_user_id_empty()
        return self

    def with_invalid_expiration(self) -> 'GrantPermissionRequestBuilder':
        """Set expired timestamp for negative testing"""
        self._expires_at = AuthorizationTestDataFactory.make_invalid_expires_at_past()
        return self

    def build(self) -> GrantPermissionRequestContract:
        """Build the request contract"""
        return GrantPermissionRequestContract(
            user_id=self._user_id,
            resource_type=self._resource_type,
            resource_name=self._resource_name,
            access_level=self._access_level,
            permission_source=self._permission_source,
            granted_by_user_id=self._granted_by_user_id,
            organization_id=self._organization_id,
            expires_at=self._expires_at,
            reason=self._reason,
        )

    def build_dict(self) -> Dict[str, Any]:
        """Build as dictionary for API calls"""
        return self.build().model_dump(mode='json')


class RevokePermissionRequestBuilder:
    """Builder for revoke permission requests with fluent API"""

    def __init__(self):
        """Initialize with factory-generated defaults"""
        self._user_id = AuthorizationTestDataFactory.make_user_id()
        self._resource_type = ResourceType.API_ENDPOINT
        self._resource_name = AuthorizationTestDataFactory.make_api_endpoint_name()
        self._revoked_by_user_id = AuthorizationTestDataFactory.make_admin_id()
        self._reason: Optional[str] = None

    def with_user_id(self, user_id: str) -> 'RevokePermissionRequestBuilder':
        """Set target user ID"""
        self._user_id = user_id
        return self

    def with_resource_type(self, resource_type: ResourceType) -> 'RevokePermissionRequestBuilder':
        """Set resource type"""
        self._resource_type = resource_type
        return self

    def with_resource_name(self, resource_name: str) -> 'RevokePermissionRequestBuilder':
        """Set resource name"""
        self._resource_name = resource_name
        return self

    def with_revoked_by(self, admin_id: str) -> 'RevokePermissionRequestBuilder':
        """Set revoking admin ID"""
        self._revoked_by_user_id = admin_id
        return self

    def with_reason(self, reason: str) -> 'RevokePermissionRequestBuilder':
        """Set revoke reason"""
        self._reason = reason
        return self

    def with_invalid_user_id(self) -> 'RevokePermissionRequestBuilder':
        """Set invalid user ID for negative testing"""
        self._user_id = AuthorizationTestDataFactory.make_invalid_user_id_empty()
        return self

    def build(self) -> RevokePermissionRequestContract:
        """Build the request contract"""
        return RevokePermissionRequestContract(
            user_id=self._user_id,
            resource_type=self._resource_type,
            resource_name=self._resource_name,
            revoked_by_user_id=self._revoked_by_user_id,
            reason=self._reason,
        )

    def build_dict(self) -> Dict[str, Any]:
        """Build as dictionary for API calls"""
        return self.build().model_dump(mode='json')


class BulkPermissionRequestBuilder:
    """Builder for bulk permission requests with fluent API"""

    def __init__(self):
        """Initialize with empty operations list"""
        self._operations: List[Union[GrantPermissionRequestContract, RevokePermissionRequestContract]] = []
        self._executed_by_user_id = AuthorizationTestDataFactory.make_admin_id()
        self._batch_reason: Optional[str] = None

    def add_grant(self, request: GrantPermissionRequestContract) -> 'BulkPermissionRequestBuilder':
        """Add a grant operation"""
        self._operations.append(request)
        return self

    def add_revoke(self, request: RevokePermissionRequestContract) -> 'BulkPermissionRequestBuilder':
        """Add a revoke operation"""
        self._operations.append(request)
        return self

    def add_multiple_grants(self, count: int = 3) -> 'BulkPermissionRequestBuilder':
        """Add multiple grant operations"""
        for _ in range(count):
            self._operations.append(AuthorizationTestDataFactory.make_grant_request())
        return self

    def add_multiple_revokes(self, count: int = 3) -> 'BulkPermissionRequestBuilder':
        """Add multiple revoke operations"""
        for _ in range(count):
            self._operations.append(AuthorizationTestDataFactory.make_revoke_request())
        return self

    def with_executed_by(self, admin_id: str) -> 'BulkPermissionRequestBuilder':
        """Set executing admin ID"""
        self._executed_by_user_id = admin_id
        return self

    def with_reason(self, reason: str) -> 'BulkPermissionRequestBuilder':
        """Set batch reason"""
        self._batch_reason = reason
        return self

    def build(self) -> BulkPermissionRequestContract:
        """Build the request contract"""
        return BulkPermissionRequestContract(
            operations=self._operations,
            executed_by_user_id=self._executed_by_user_id,
            batch_reason=self._batch_reason,
        )

    def build_dict(self) -> Dict[str, Any]:
        """Build as dictionary for API calls"""
        return self.build().model_dump(mode='json')


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Enums
    "ResourceType",
    "AccessLevel",
    "PermissionSource",
    "SubscriptionTier",
    "OrganizationPlan",
    # Request Contracts
    "ResourceAccessRequestContract",
    "GrantPermissionRequestContract",
    "RevokePermissionRequestContract",
    "BulkPermissionRequestContract",
    "UserPermissionsQueryContract",
    "ResourcePermissionConfigContract",
    "OrganizationPermissionConfigContract",
    # Response Contracts
    "ResourceAccessResponseContract",
    "PermissionGrantResponseContract",
    "PermissionRevokeResponseContract",
    "BatchOperationResultContract",
    "BulkPermissionResponseContract",
    "UserPermissionSummaryResponseContract",
    "UserAccessibleResourceContract",
    "UserAccessibleResourcesResponseContract",
    "ServiceStatsResponseContract",
    "HealthResponseContract",
    "DetailedHealthResponseContract",
    "ErrorResponseContract",
    "CleanupResponseContract",
    # Factory
    "AuthorizationTestDataFactory",
    # Builders
    "AccessCheckRequestBuilder",
    "GrantPermissionRequestBuilder",
    "RevokePermissionRequestBuilder",
    "BulkPermissionRequestBuilder",
]
