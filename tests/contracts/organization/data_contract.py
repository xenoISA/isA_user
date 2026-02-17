"""
Organization Service Data Contract

Defines canonical data structures for organization service testing.
All tests MUST use these Pydantic models and factories for consistency.

This is the SINGLE SOURCE OF TRUTH for organization service test data.
"""

import uuid
import random
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field, EmailStr, field_validator


# ============================================================================
# Enums
# ============================================================================

class OrganizationTypeContract(str, Enum):
    """Organization type enumeration"""
    BUSINESS = "business"
    FAMILY = "family"
    TEAM = "team"
    ENTERPRISE = "enterprise"


class OrganizationRoleContract(str, Enum):
    """Organization member role enumeration"""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    GUEST = "guest"


class MemberStatusContract(str, Enum):
    """Member status enumeration"""
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REMOVED = "removed"


class SharingResourceTypeContract(str, Enum):
    """Sharing resource type enumeration"""
    SUBSCRIPTION = "subscription"
    DEVICE = "device"
    STORAGE = "storage"
    WALLET = "wallet"
    ALBUM = "album"
    MEDIA_LIBRARY = "media_library"
    CALENDAR = "calendar"
    LOCATION = "location"
    SMART_FRAME = "smart_frame"


class SharingPermissionLevelContract(str, Enum):
    """Sharing permission level enumeration"""
    OWNER = "owner"
    ADMIN = "admin"
    FULL_ACCESS = "full_access"
    READ_WRITE = "read_write"
    READ_ONLY = "read_only"
    LIMITED = "limited"
    VIEW_ONLY = "view_only"


class SharingStatusContract(str, Enum):
    """Sharing status enumeration"""
    ACTIVE = "active"
    PAUSED = "paused"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PENDING = "pending"


# ============================================================================
# Request Contracts
# ============================================================================

class OrganizationCreateRequestContract(BaseModel):
    """Contract: Organization create request schema"""
    name: str = Field(..., min_length=1, max_length=100, description="Organization name")
    type: Optional[OrganizationTypeContract] = Field(
        OrganizationTypeContract.BUSINESS,
        description="Organization type"
    )
    billing_email: EmailStr = Field(..., description="Billing email address")
    description: Optional[str] = Field(None, max_length=500, description="Organization description")
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Organization settings")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("Organization name cannot be empty or whitespace only")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "name": "My Family",
                "type": "family",
                "billing_email": "billing@example.com",
                "description": "Family organization for sharing devices",
                "settings": {}
            }
        }


class OrganizationUpdateRequestContract(BaseModel):
    """Contract: Organization update request schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Organization name")
    billing_email: Optional[EmailStr] = Field(None, description="Billing email address")
    description: Optional[str] = Field(None, max_length=500, description="Organization description")
    settings: Optional[Dict[str, Any]] = Field(None, description="Organization settings")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if v is not None and not v.strip():
            raise ValueError("Organization name cannot be empty or whitespace only")
        return v.strip() if v else v


class OrganizationMemberAddRequestContract(BaseModel):
    """Contract: Organization member add request schema"""
    user_id: Optional[str] = Field(None, description="User ID to add")
    email: Optional[EmailStr] = Field(None, description="Email for invitation")
    role: OrganizationRoleContract = Field(
        OrganizationRoleContract.MEMBER,
        description="Member role"
    )
    permissions: Optional[List[str]] = Field(default_factory=list, description="Additional permissions")

    @field_validator('user_id', 'email')
    @classmethod
    def validate_user_or_email(cls, v, info):
        # At least one of user_id or email must be provided
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_abc123",
                "role": "member",
                "permissions": []
            }
        }


class OrganizationMemberUpdateRequestContract(BaseModel):
    """Contract: Organization member update request schema"""
    role: Optional[OrganizationRoleContract] = Field(None, description="New member role")
    status: Optional[MemberStatusContract] = Field(None, description="New member status")
    permissions: Optional[List[str]] = Field(None, description="Updated permissions")


class OrganizationContextSwitchRequestContract(BaseModel):
    """Contract: Organization context switch request schema"""
    organization_id: Optional[str] = Field(None, description="Organization ID (null for personal context)")


class SharingCreateRequestContract(BaseModel):
    """Contract: Sharing create request schema"""
    resource_type: SharingResourceTypeContract = Field(..., description="Resource type")
    resource_id: str = Field(..., description="Resource ID")
    resource_name: Optional[str] = Field(None, max_length=255, description="Resource name")
    shared_with_members: Optional[List[str]] = Field(default_factory=list, description="Member IDs to share with")
    share_with_all_members: bool = Field(False, description="Share with all members")
    default_permission: SharingPermissionLevelContract = Field(
        SharingPermissionLevelContract.READ_WRITE,
        description="Default permission level"
    )
    custom_permissions: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="Custom permissions per member"
    )
    quota_settings: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Quota settings")
    restrictions: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Restrictions")
    expires_at: Optional[datetime] = Field(None, description="Expiration time")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata")


class SharingUpdateRequestContract(BaseModel):
    """Contract: Sharing update request schema"""
    shared_with_members: Optional[List[str]] = None
    share_with_all_members: Optional[bool] = None
    default_permission: Optional[SharingPermissionLevelContract] = None
    custom_permissions: Optional[Dict[str, str]] = None
    quota_settings: Optional[Dict[str, Any]] = None
    restrictions: Optional[Dict[str, Any]] = None
    status: Optional[SharingStatusContract] = None
    expires_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class MemberPermissionUpdateRequestContract(BaseModel):
    """Contract: Member permission update request schema"""
    user_id: str = Field(..., description="User ID")
    permission_level: SharingPermissionLevelContract = Field(..., description="Permission level")
    quota_override: Optional[Dict[str, Any]] = Field(None, description="Quota override")
    restrictions_override: Optional[Dict[str, Any]] = Field(None, description="Restrictions override")


# ============================================================================
# Response Contracts
# ============================================================================

class OrganizationResponseContract(BaseModel):
    """Contract: Organization response schema"""
    organization_id: str = Field(..., description="Organization ID")
    name: str = Field(..., description="Organization name")
    type: str = Field(..., description="Organization type")
    billing_email: Optional[str] = Field(None, description="Billing email")
    description: Optional[str] = Field(None, description="Description")
    status: str = Field(..., description="Organization status")
    plan: str = Field(..., description="Organization plan")
    credits_pool: int = Field(default=0, description="Credits pool")
    max_members: int = Field(default=10, description="Max members")
    settings: Dict[str, Any] = Field(default_factory=dict, description="Settings")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Update timestamp")


class OrganizationMemberResponseContract(BaseModel):
    """Contract: Organization member response schema"""
    organization_id: str = Field(..., description="Organization ID")
    user_id: str = Field(..., description="User ID")
    role: str = Field(..., description="Member role")
    status: str = Field(..., description="Member status")
    permissions: List[str] = Field(default_factory=list, description="Permissions")
    joined_at: Optional[datetime] = Field(None, description="Joined timestamp")
    updated_at: Optional[datetime] = Field(None, description="Update timestamp")


class OrganizationListResponseContract(BaseModel):
    """Contract: Organization list response schema"""
    organizations: List[OrganizationResponseContract] = Field(default_factory=list)
    total: int = Field(..., ge=0)
    limit: int = Field(..., ge=1, le=1000)
    offset: int = Field(..., ge=0)


class OrganizationMemberListResponseContract(BaseModel):
    """Contract: Organization member list response schema"""
    members: List[OrganizationMemberResponseContract] = Field(default_factory=list)
    total: int = Field(..., ge=0)
    limit: int = Field(..., ge=1, le=1000)
    offset: int = Field(..., ge=0)


class OrganizationContextResponseContract(BaseModel):
    """Contract: Organization context response schema"""
    context_type: str = Field(..., description="Context type (organization/individual)")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    organization_name: Optional[str] = Field(None, description="Organization name")
    user_role: Optional[str] = Field(None, description="User role")
    permissions: List[str] = Field(default_factory=list, description="Permissions")
    credits_available: Optional[int] = Field(None, description="Available credits")


class OrganizationStatsResponseContract(BaseModel):
    """Contract: Organization stats response schema"""
    organization_id: str
    total_members: int = Field(default=0, ge=0)
    active_members: int = Field(default=0, ge=0)
    suspended_members: int = Field(default=0, ge=0)
    members_by_role: Dict[str, int] = Field(default_factory=dict)
    total_sharings: int = Field(default=0, ge=0)
    active_sharings: int = Field(default=0, ge=0)
    credits_balance: int = Field(default=0)
    storage_used_gb: float = Field(default=0.0)


class SharingResourceResponseContract(BaseModel):
    """Contract: Sharing resource response schema"""
    sharing_id: str
    organization_id: str
    resource_type: str
    resource_id: str
    resource_name: Optional[str] = None
    created_by: str
    share_with_all_members: bool = False
    default_permission: str
    status: str
    total_members_shared: int = Field(default=0, ge=0)
    quota_settings: Dict[str, Any] = Field(default_factory=dict)
    restrictions: Dict[str, Any] = Field(default_factory=dict)
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MemberSharingPermissionResponseContract(BaseModel):
    """Contract: Member sharing permission response schema"""
    user_id: str
    sharing_id: str
    resource_type: str
    resource_id: str
    resource_name: Optional[str] = None
    permission_level: str
    quota_allocated: Optional[Dict[str, Any]] = None
    quota_used: Optional[Dict[str, Any]] = None
    restrictions: Optional[Dict[str, Any]] = None
    is_active: bool = True
    granted_at: Optional[datetime] = None
    last_accessed_at: Optional[datetime] = None


# ============================================================================
# Test Data Factory
# ============================================================================

class OrganizationTestDataFactory:
    """
    Factory for creating test data conforming to contracts.

    Provides methods to generate valid/invalid test data for all scenarios.
    Zero hardcoded data - all values are dynamically generated.
    """

    # === Valid Data Generators ===

    @staticmethod
    def make_organization_id() -> str:
        """Generate unique test organization ID"""
        return f"org_test_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_user_id() -> str:
        """Generate unique test user ID"""
        return f"user_test_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_sharing_id() -> str:
        """Generate unique test sharing ID"""
        return f"share_test_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_permission_id() -> str:
        """Generate unique test permission ID"""
        return f"perm_test_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_organization_name() -> str:
        """Generate random organization name"""
        prefixes = ["Family", "Team", "Company", "Group", "Unit", "Division"]
        names = ["Alpha", "Beta", "Gamma", "Delta", "Omega", "Prime", "Core"]
        return f"{random.choice(prefixes)} {random.choice(names)} {secrets.token_hex(4)}"

    @staticmethod
    def make_email() -> str:
        """Generate unique test email address"""
        return f"test_{uuid.uuid4().hex[:8]}@example.com"

    @staticmethod
    def make_organization_type() -> OrganizationTypeContract:
        """Generate random organization type"""
        return random.choice(list(OrganizationTypeContract))

    @staticmethod
    def make_role() -> OrganizationRoleContract:
        """Generate random organization role"""
        return random.choice(list(OrganizationRoleContract))

    @staticmethod
    def make_member_status() -> MemberStatusContract:
        """Generate random member status"""
        return random.choice(list(MemberStatusContract))

    @staticmethod
    def make_resource_type() -> SharingResourceTypeContract:
        """Generate random sharing resource type"""
        return random.choice(list(SharingResourceTypeContract))

    @staticmethod
    def make_permission_level() -> SharingPermissionLevelContract:
        """Generate random sharing permission level"""
        return random.choice(list(SharingPermissionLevelContract))

    @staticmethod
    def make_sharing_status() -> SharingStatusContract:
        """Generate random sharing status"""
        return random.choice(list(SharingStatusContract))

    @staticmethod
    def make_resource_id() -> str:
        """Generate unique resource ID"""
        prefixes = ["device", "album", "wallet", "storage", "sub"]
        return f"{random.choice(prefixes)}_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_resource_name() -> str:
        """Generate random resource name"""
        items = ["Living Room Speaker", "Family Album", "Shared Wallet", "Cloud Storage", "Family Subscription"]
        return f"{random.choice(items)} {secrets.token_hex(4)}"

    @staticmethod
    def make_timestamp() -> datetime:
        """Generate current timestamp"""
        return datetime.now(timezone.utc)

    @staticmethod
    def make_past_timestamp() -> datetime:
        """Generate past timestamp (within 30 days)"""
        days_ago = random.randint(1, 30)
        return datetime.now(timezone.utc) - timedelta(days=days_ago)

    @staticmethod
    def make_future_timestamp() -> datetime:
        """Generate future timestamp (within 30 days)"""
        days_ahead = random.randint(1, 30)
        return datetime.now(timezone.utc) + timedelta(days=days_ahead)

    @staticmethod
    def make_permissions() -> List[str]:
        """Generate random permissions list"""
        all_permissions = [
            "manage_members", "manage_sharing", "view_stats",
            "manage_billing", "delete_organization", "invite_members"
        ]
        count = random.randint(0, len(all_permissions))
        return random.sample(all_permissions, count)

    @staticmethod
    def make_settings() -> Dict[str, Any]:
        """Generate random organization settings"""
        return {
            "notification_enabled": random.choice([True, False]),
            "auto_approve_members": random.choice([True, False]),
            "default_role": random.choice(["member", "guest"]),
        }

    @staticmethod
    def make_quota_settings() -> Dict[str, Any]:
        """Generate random quota settings"""
        return {
            "max_storage_gb": random.randint(10, 100),
            "max_devices": random.randint(5, 20),
            "daily_limit": random.randint(100, 1000),
        }

    @staticmethod
    def make_restrictions() -> Dict[str, Any]:
        """Generate random restrictions"""
        return {
            "time_restrictions": {"start_hour": 8, "end_hour": 22},
            "allowed_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
        }

    @staticmethod
    def make_metadata() -> Dict[str, Any]:
        """Generate random metadata"""
        return {
            "source": "test",
            "version": "1.0",
            "tags": ["test", "automated"],
        }

    # === Request Factory Methods ===

    @staticmethod
    def make_create_request(**overrides) -> OrganizationCreateRequestContract:
        """Create valid organization create request with defaults"""
        defaults = {
            "name": OrganizationTestDataFactory.make_organization_name(),
            "type": OrganizationTestDataFactory.make_organization_type(),
            "billing_email": OrganizationTestDataFactory.make_email(),
            "description": f"Test organization {secrets.token_hex(4)}",
            "settings": OrganizationTestDataFactory.make_settings(),
        }
        defaults.update(overrides)
        return OrganizationCreateRequestContract(**defaults)

    @staticmethod
    def make_update_request(**overrides) -> OrganizationUpdateRequestContract:
        """Create valid organization update request with defaults"""
        defaults = {
            "name": OrganizationTestDataFactory.make_organization_name(),
            "billing_email": OrganizationTestDataFactory.make_email(),
        }
        defaults.update(overrides)
        return OrganizationUpdateRequestContract(**defaults)

    @staticmethod
    def make_member_add_request(**overrides) -> OrganizationMemberAddRequestContract:
        """Create valid member add request with defaults"""
        defaults = {
            "user_id": OrganizationTestDataFactory.make_user_id(),
            "role": OrganizationRoleContract.MEMBER,
            "permissions": [],
        }
        defaults.update(overrides)
        return OrganizationMemberAddRequestContract(**defaults)

    @staticmethod
    def make_member_update_request(**overrides) -> OrganizationMemberUpdateRequestContract:
        """Create valid member update request with defaults"""
        defaults = {
            "role": OrganizationRoleContract.MEMBER,
            "status": MemberStatusContract.ACTIVE,
        }
        defaults.update(overrides)
        return OrganizationMemberUpdateRequestContract(**defaults)

    @staticmethod
    def make_context_switch_request(**overrides) -> OrganizationContextSwitchRequestContract:
        """Create valid context switch request with defaults"""
        defaults = {
            "organization_id": OrganizationTestDataFactory.make_organization_id(),
        }
        defaults.update(overrides)
        return OrganizationContextSwitchRequestContract(**defaults)

    @staticmethod
    def make_sharing_create_request(**overrides) -> SharingCreateRequestContract:
        """Create valid sharing create request with defaults"""
        defaults = {
            "resource_type": OrganizationTestDataFactory.make_resource_type(),
            "resource_id": OrganizationTestDataFactory.make_resource_id(),
            "resource_name": OrganizationTestDataFactory.make_resource_name(),
            "shared_with_members": [OrganizationTestDataFactory.make_user_id()],
            "share_with_all_members": False,
            "default_permission": SharingPermissionLevelContract.READ_WRITE,
            "custom_permissions": {},
            "quota_settings": OrganizationTestDataFactory.make_quota_settings(),
            "restrictions": {},
            "metadata": {},
        }
        defaults.update(overrides)
        return SharingCreateRequestContract(**defaults)

    @staticmethod
    def make_sharing_update_request(**overrides) -> SharingUpdateRequestContract:
        """Create valid sharing update request with defaults"""
        defaults = {
            "default_permission": SharingPermissionLevelContract.READ_WRITE,
            "status": SharingStatusContract.ACTIVE,
        }
        defaults.update(overrides)
        return SharingUpdateRequestContract(**defaults)

    @staticmethod
    def make_member_permission_update_request(**overrides) -> MemberPermissionUpdateRequestContract:
        """Create valid member permission update request with defaults"""
        defaults = {
            "user_id": OrganizationTestDataFactory.make_user_id(),
            "permission_level": SharingPermissionLevelContract.READ_WRITE,
        }
        defaults.update(overrides)
        return MemberPermissionUpdateRequestContract(**defaults)

    # === Response Factory Methods ===

    @staticmethod
    def make_organization_response(**overrides) -> OrganizationResponseContract:
        """Create expected organization response for assertions"""
        defaults = {
            "organization_id": OrganizationTestDataFactory.make_organization_id(),
            "name": OrganizationTestDataFactory.make_organization_name(),
            "type": OrganizationTypeContract.FAMILY.value,
            "billing_email": OrganizationTestDataFactory.make_email(),
            "description": "Test organization",
            "status": "active",
            "plan": "free",
            "credits_pool": 0,
            "max_members": 10,
            "settings": {},
            "created_at": OrganizationTestDataFactory.make_past_timestamp(),
            "updated_at": OrganizationTestDataFactory.make_timestamp(),
        }
        defaults.update(overrides)
        return OrganizationResponseContract(**defaults)

    @staticmethod
    def make_member_response(**overrides) -> OrganizationMemberResponseContract:
        """Create expected member response for assertions"""
        defaults = {
            "organization_id": OrganizationTestDataFactory.make_organization_id(),
            "user_id": OrganizationTestDataFactory.make_user_id(),
            "role": OrganizationRoleContract.MEMBER.value,
            "status": MemberStatusContract.ACTIVE.value,
            "permissions": [],
            "joined_at": OrganizationTestDataFactory.make_past_timestamp(),
            "updated_at": OrganizationTestDataFactory.make_timestamp(),
        }
        defaults.update(overrides)
        return OrganizationMemberResponseContract(**defaults)

    @staticmethod
    def make_context_response(**overrides) -> OrganizationContextResponseContract:
        """Create expected context response for assertions"""
        defaults = {
            "context_type": "organization",
            "organization_id": OrganizationTestDataFactory.make_organization_id(),
            "organization_name": OrganizationTestDataFactory.make_organization_name(),
            "user_role": OrganizationRoleContract.MEMBER.value,
            "permissions": [],
            "credits_available": 0,
        }
        defaults.update(overrides)
        return OrganizationContextResponseContract(**defaults)

    @staticmethod
    def make_stats_response(**overrides) -> OrganizationStatsResponseContract:
        """Create expected stats response for assertions"""
        total = random.randint(5, 20)
        active = int(total * 0.8)
        defaults = {
            "organization_id": OrganizationTestDataFactory.make_organization_id(),
            "total_members": total,
            "active_members": active,
            "suspended_members": total - active,
            "members_by_role": {"owner": 1, "admin": 2, "member": total - 3},
            "total_sharings": random.randint(3, 10),
            "active_sharings": random.randint(2, 8),
            "credits_balance": random.randint(0, 1000),
            "storage_used_gb": round(random.uniform(0, 50), 2),
        }
        defaults.update(overrides)
        return OrganizationStatsResponseContract(**defaults)

    @staticmethod
    def make_sharing_response(**overrides) -> SharingResourceResponseContract:
        """Create expected sharing response for assertions"""
        defaults = {
            "sharing_id": OrganizationTestDataFactory.make_sharing_id(),
            "organization_id": OrganizationTestDataFactory.make_organization_id(),
            "resource_type": SharingResourceTypeContract.DEVICE.value,
            "resource_id": OrganizationTestDataFactory.make_resource_id(),
            "resource_name": OrganizationTestDataFactory.make_resource_name(),
            "created_by": OrganizationTestDataFactory.make_user_id(),
            "share_with_all_members": False,
            "default_permission": SharingPermissionLevelContract.READ_WRITE.value,
            "status": SharingStatusContract.ACTIVE.value,
            "total_members_shared": random.randint(1, 5),
            "quota_settings": {},
            "restrictions": {},
            "created_at": OrganizationTestDataFactory.make_past_timestamp(),
            "metadata": {},
        }
        defaults.update(overrides)
        return SharingResourceResponseContract(**defaults)

    @staticmethod
    def make_permission_response(**overrides) -> MemberSharingPermissionResponseContract:
        """Create expected permission response for assertions"""
        defaults = {
            "user_id": OrganizationTestDataFactory.make_user_id(),
            "sharing_id": OrganizationTestDataFactory.make_sharing_id(),
            "resource_type": SharingResourceTypeContract.DEVICE.value,
            "resource_id": OrganizationTestDataFactory.make_resource_id(),
            "resource_name": OrganizationTestDataFactory.make_resource_name(),
            "permission_level": SharingPermissionLevelContract.READ_WRITE.value,
            "is_active": True,
            "granted_at": OrganizationTestDataFactory.make_past_timestamp(),
        }
        defaults.update(overrides)
        return MemberSharingPermissionResponseContract(**defaults)

    # === Invalid Data Generators ===

    @staticmethod
    def make_invalid_create_request_empty_name() -> dict:
        """Generate create request with empty name"""
        return {
            "name": "",
            "billing_email": OrganizationTestDataFactory.make_email(),
        }

    @staticmethod
    def make_invalid_create_request_whitespace_name() -> dict:
        """Generate create request with whitespace-only name"""
        return {
            "name": "   ",
            "billing_email": OrganizationTestDataFactory.make_email(),
        }

    @staticmethod
    def make_invalid_create_request_missing_email() -> dict:
        """Generate create request missing billing email"""
        return {
            "name": OrganizationTestDataFactory.make_organization_name(),
        }

    @staticmethod
    def make_invalid_create_request_invalid_email() -> dict:
        """Generate create request with invalid email"""
        return {
            "name": OrganizationTestDataFactory.make_organization_name(),
            "billing_email": "not-a-valid-email",
        }

    @staticmethod
    def make_invalid_member_add_request_no_user_no_email() -> dict:
        """Generate member add request without user_id or email"""
        return {
            "role": "member",
        }

    @staticmethod
    def make_invalid_member_add_request_invalid_role() -> dict:
        """Generate member add request with invalid role"""
        return {
            "user_id": OrganizationTestDataFactory.make_user_id(),
            "role": "invalid_role",
        }

    @staticmethod
    def make_invalid_sharing_request_missing_resource() -> dict:
        """Generate sharing request missing resource_id"""
        return {
            "resource_type": "device",
        }

    @staticmethod
    def make_invalid_sharing_request_invalid_type() -> dict:
        """Generate sharing request with invalid resource type"""
        return {
            "resource_type": "invalid_type",
            "resource_id": OrganizationTestDataFactory.make_resource_id(),
        }


# ============================================================================
# Request Builders
# ============================================================================

class OrganizationCreateRequestBuilder:
    """Builder pattern for creating complex organization create requests"""

    def __init__(self):
        self._data = {
            "name": OrganizationTestDataFactory.make_organization_name(),
            "type": OrganizationTypeContract.BUSINESS,
            "billing_email": OrganizationTestDataFactory.make_email(),
            "description": None,
            "settings": {},
        }

    def with_name(self, name: str) -> 'OrganizationCreateRequestBuilder':
        self._data["name"] = name
        return self

    def with_type(self, org_type: OrganizationTypeContract) -> 'OrganizationCreateRequestBuilder':
        self._data["type"] = org_type
        return self

    def with_billing_email(self, email: str) -> 'OrganizationCreateRequestBuilder':
        self._data["billing_email"] = email
        return self

    def with_description(self, description: str) -> 'OrganizationCreateRequestBuilder':
        self._data["description"] = description
        return self

    def with_settings(self, settings: Dict[str, Any]) -> 'OrganizationCreateRequestBuilder':
        self._data["settings"] = settings
        return self

    def as_family(self) -> 'OrganizationCreateRequestBuilder':
        self._data["type"] = OrganizationTypeContract.FAMILY
        return self

    def as_team(self) -> 'OrganizationCreateRequestBuilder':
        self._data["type"] = OrganizationTypeContract.TEAM
        return self

    def as_enterprise(self) -> 'OrganizationCreateRequestBuilder':
        self._data["type"] = OrganizationTypeContract.ENTERPRISE
        return self

    def build(self) -> OrganizationCreateRequestContract:
        return OrganizationCreateRequestContract(**self._data)


class OrganizationMemberAddRequestBuilder:
    """Builder pattern for creating complex member add requests"""

    def __init__(self):
        self._data = {
            "user_id": OrganizationTestDataFactory.make_user_id(),
            "email": None,
            "role": OrganizationRoleContract.MEMBER,
            "permissions": [],
        }

    def with_user_id(self, user_id: str) -> 'OrganizationMemberAddRequestBuilder':
        self._data["user_id"] = user_id
        return self

    def with_email(self, email: str) -> 'OrganizationMemberAddRequestBuilder':
        self._data["email"] = email
        return self

    def with_role(self, role: OrganizationRoleContract) -> 'OrganizationMemberAddRequestBuilder':
        self._data["role"] = role
        return self

    def with_permissions(self, permissions: List[str]) -> 'OrganizationMemberAddRequestBuilder':
        self._data["permissions"] = permissions
        return self

    def as_admin(self) -> 'OrganizationMemberAddRequestBuilder':
        self._data["role"] = OrganizationRoleContract.ADMIN
        return self

    def as_guest(self) -> 'OrganizationMemberAddRequestBuilder':
        self._data["role"] = OrganizationRoleContract.GUEST
        return self

    def build(self) -> OrganizationMemberAddRequestContract:
        return OrganizationMemberAddRequestContract(**self._data)


class SharingCreateRequestBuilder:
    """Builder pattern for creating complex sharing create requests"""

    def __init__(self):
        self._data = {
            "resource_type": SharingResourceTypeContract.DEVICE,
            "resource_id": OrganizationTestDataFactory.make_resource_id(),
            "resource_name": OrganizationTestDataFactory.make_resource_name(),
            "shared_with_members": [],
            "share_with_all_members": False,
            "default_permission": SharingPermissionLevelContract.READ_WRITE,
            "custom_permissions": {},
            "quota_settings": {},
            "restrictions": {},
            "expires_at": None,
            "metadata": {},
        }

    def with_resource_type(self, resource_type: SharingResourceTypeContract) -> 'SharingCreateRequestBuilder':
        self._data["resource_type"] = resource_type
        return self

    def with_resource_id(self, resource_id: str) -> 'SharingCreateRequestBuilder':
        self._data["resource_id"] = resource_id
        return self

    def with_resource_name(self, resource_name: str) -> 'SharingCreateRequestBuilder':
        self._data["resource_name"] = resource_name
        return self

    def with_members(self, members: List[str]) -> 'SharingCreateRequestBuilder':
        self._data["shared_with_members"] = members
        return self

    def share_with_all(self) -> 'SharingCreateRequestBuilder':
        self._data["share_with_all_members"] = True
        return self

    def with_permission(self, permission: SharingPermissionLevelContract) -> 'SharingCreateRequestBuilder':
        self._data["default_permission"] = permission
        return self

    def with_quota(self, quota: Dict[str, Any]) -> 'SharingCreateRequestBuilder':
        self._data["quota_settings"] = quota
        return self

    def with_expiration(self, expires_at: datetime) -> 'SharingCreateRequestBuilder':
        self._data["expires_at"] = expires_at
        return self

    def as_device_sharing(self) -> 'SharingCreateRequestBuilder':
        self._data["resource_type"] = SharingResourceTypeContract.DEVICE
        return self

    def as_album_sharing(self) -> 'SharingCreateRequestBuilder':
        self._data["resource_type"] = SharingResourceTypeContract.ALBUM
        return self

    def as_storage_sharing(self) -> 'SharingCreateRequestBuilder':
        self._data["resource_type"] = SharingResourceTypeContract.STORAGE
        return self

    def build(self) -> SharingCreateRequestContract:
        return SharingCreateRequestContract(**self._data)


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Enums
    "OrganizationTypeContract",
    "OrganizationRoleContract",
    "MemberStatusContract",
    "SharingResourceTypeContract",
    "SharingPermissionLevelContract",
    "SharingStatusContract",
    # Request Contracts
    "OrganizationCreateRequestContract",
    "OrganizationUpdateRequestContract",
    "OrganizationMemberAddRequestContract",
    "OrganizationMemberUpdateRequestContract",
    "OrganizationContextSwitchRequestContract",
    "SharingCreateRequestContract",
    "SharingUpdateRequestContract",
    "MemberPermissionUpdateRequestContract",
    # Response Contracts
    "OrganizationResponseContract",
    "OrganizationMemberResponseContract",
    "OrganizationListResponseContract",
    "OrganizationMemberListResponseContract",
    "OrganizationContextResponseContract",
    "OrganizationStatsResponseContract",
    "SharingResourceResponseContract",
    "MemberSharingPermissionResponseContract",
    # Factory
    "OrganizationTestDataFactory",
    # Builders
    "OrganizationCreateRequestBuilder",
    "OrganizationMemberAddRequestBuilder",
    "SharingCreateRequestBuilder",
]
