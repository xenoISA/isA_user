"""
Invitation Service Data Contract

Defines canonical data structures for invitation service testing.
All tests MUST use these Pydantic models and factories for consistency.

This is the SINGLE SOURCE OF TRUTH for invitation service test data.

Zero Hardcoded Data Policy:
- ALL test data MUST be generated through factory methods
- NEVER use literal strings, numbers, or dates in tests
- Factory methods generate unique, valid data for each call
"""

import uuid
import secrets
import random
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from enum import Enum


# ============================================================================
# Enums (Imported from production models for type consistency)
# ============================================================================

class InvitationStatus(str, Enum):
    """Invitation status enumeration"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class OrganizationRole(str, Enum):
    """Organization role enumeration"""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"
    GUEST = "guest"


# ============================================================================
# Request Contracts (Input Schemas)
# ============================================================================

class InvitationCreateRequestContract(BaseModel):
    """
    Contract: Invitation creation request schema

    Used for creating organization invitations in tests.
    Maps to POST /api/v1/invitations/organizations/{org_id}
    """
    email: str = Field(..., description="Email address of invited person")
    role: OrganizationRole = Field(
        default=OrganizationRole.MEMBER,
        description="Role to assign upon acceptance"
    )
    message: Optional[str] = Field(
        None,
        max_length=500,
        description="Personal message to include in invitation"
    )

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Email must contain '@' and be normalized to lowercase"""
        if '@' not in v:
            raise ValueError("Invalid email format - must contain '@'")
        return v.lower().strip()

    @field_validator('message')
    @classmethod
    def validate_message(cls, v: Optional[str]) -> Optional[str]:
        """Message must not exceed 500 characters"""
        if v is not None and len(v) > 500:
            raise ValueError("Message must not exceed 500 characters")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "email": "newmember@example.com",
                "role": "member",
                "message": "Welcome to our team!"
            }
        }


class InvitationAcceptRequestContract(BaseModel):
    """
    Contract: Invitation acceptance request schema

    Used for accepting invitations in tests.
    Maps to POST /api/v1/invitations/accept
    """
    invitation_token: str = Field(
        ...,
        min_length=32,
        description="Secure invitation token from email link"
    )
    user_id: Optional[str] = Field(
        None,
        description="User ID of accepting user (from X-User-Id header)"
    )

    @field_validator('invitation_token')
    @classmethod
    def validate_token(cls, v: str) -> str:
        """Token must be non-empty"""
        if not v or not v.strip():
            raise ValueError("Invitation token cannot be empty")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "invitation_token": "xK9mN2pQ7rS3tU6vW8xY0zA1bC4dE5fG",
                "user_id": "usr_abc123"
            }
        }


class InvitationResendRequestContract(BaseModel):
    """
    Contract: Invitation resend request schema

    Used for resending invitations in tests.
    Maps to POST /api/v1/invitations/{invitation_id}/resend
    """
    invitation_id: str = Field(..., description="Invitation ID to resend")

    @field_validator('invitation_id')
    @classmethod
    def validate_invitation_id(cls, v: str) -> str:
        """Invitation ID must be non-empty"""
        if not v or not v.strip():
            raise ValueError("Invitation ID cannot be empty")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "invitation_id": "inv_abc123def456"
            }
        }


class InvitationCancelRequestContract(BaseModel):
    """
    Contract: Invitation cancellation request schema

    Used for cancelling invitations in tests.
    Maps to DELETE /api/v1/invitations/{invitation_id}
    """
    invitation_id: str = Field(..., description="Invitation ID to cancel")
    user_id: str = Field(..., description="User ID of person cancelling")

    class Config:
        json_schema_extra = {
            "example": {
                "invitation_id": "inv_abc123def456",
                "user_id": "usr_admin123"
            }
        }


class InvitationListParamsContract(BaseModel):
    """
    Contract: Invitation list query parameters schema

    Used for listing organization invitations in tests.
    Maps to GET /api/v1/invitations/organizations/{org_id}
    """
    organization_id: str = Field(..., description="Organization ID to list invitations for")
    status: Optional[InvitationStatus] = Field(
        None,
        description="Filter by invitation status"
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum results to return"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of results to skip"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "organization_id": "org_xyz789",
                "status": "pending",
                "limit": 100,
                "offset": 0
            }
        }


class InvitationBulkExpireRequestContract(BaseModel):
    """
    Contract: Bulk invitation expiration request schema

    Used for admin bulk expiration in tests.
    Maps to POST /api/v1/invitations/admin/expire-invitations
    """
    dry_run: bool = Field(
        default=False,
        description="If true, return count without actually expiring"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "dry_run": False
            }
        }


# ============================================================================
# Response Contracts (Output Schemas)
# ============================================================================

class InvitationResponseContract(BaseModel):
    """
    Contract: Invitation response schema

    Validates API response structure for invitation records.
    """
    invitation_id: str = Field(..., description="Unique invitation identifier")
    organization_id: str = Field(..., description="Target organization ID")
    email: str = Field(..., description="Invited person's email")
    role: OrganizationRole = Field(..., description="Assigned role")
    status: InvitationStatus = Field(..., description="Invitation status")
    invited_by: str = Field(..., description="User ID of inviter")
    invitation_token: str = Field(..., description="Secure acceptance token")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    accepted_at: Optional[datetime] = Field(None, description="Acceptance timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "invitation_id": "inv_abc123def456",
                "organization_id": "org_xyz789",
                "email": "newmember@example.com",
                "role": "member",
                "status": "pending",
                "invited_by": "usr_admin123",
                "invitation_token": "xK9mN2pQ7rS3tU6vW8xY0zA1bC4dE5fG",
                "expires_at": "2025-12-26T10:00:00Z",
                "accepted_at": None,
                "created_at": "2025-12-19T10:00:00Z",
                "updated_at": "2025-12-19T10:00:00Z"
            }
        }


class InvitationDetailResponseContract(BaseModel):
    """
    Contract: Invitation detail response schema

    Validates API response structure for invitation details (with org/inviter info).
    Used for GET /api/v1/invitations/{token}
    """
    invitation_id: str = Field(..., description="Unique invitation identifier")
    organization_id: str = Field(..., description="Target organization ID")
    organization_name: str = Field(..., description="Organization display name")
    organization_domain: Optional[str] = Field(None, description="Organization domain")
    email: str = Field(..., description="Invited person's email")
    role: OrganizationRole = Field(..., description="Assigned role")
    status: InvitationStatus = Field(..., description="Invitation status")
    inviter_name: Optional[str] = Field(None, description="Inviter's display name")
    inviter_email: Optional[str] = Field(None, description="Inviter's email")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "invitation_id": "inv_abc123def456",
                "organization_id": "org_xyz789",
                "organization_name": "Acme Corp",
                "organization_domain": "acme.com",
                "email": "newmember@example.com",
                "role": "member",
                "status": "pending",
                "inviter_name": "John Admin",
                "inviter_email": "admin@acme.com",
                "expires_at": "2025-12-26T10:00:00Z",
                "created_at": "2025-12-19T10:00:00Z"
            }
        }


class InvitationListResponseContract(BaseModel):
    """
    Contract: Invitation list response schema

    Validates API response structure for invitation list with pagination.
    """
    invitations: List[InvitationResponseContract] = Field(
        ...,
        description="List of invitations"
    )
    total: int = Field(..., ge=0, description="Total number of invitations")
    limit: int = Field(..., ge=1, description="Results per page")
    offset: int = Field(..., ge=0, description="Offset from start")

    class Config:
        json_schema_extra = {
            "example": {
                "invitations": [],
                "total": 0,
                "limit": 100,
                "offset": 0
            }
        }


class AcceptInvitationResponseContract(BaseModel):
    """
    Contract: Accept invitation response schema

    Validates API response structure for successful invitation acceptance.
    """
    invitation_id: str = Field(..., description="Invitation identifier")
    organization_id: str = Field(..., description="Joined organization ID")
    organization_name: str = Field(..., description="Joined organization name")
    user_id: str = Field(..., description="User who accepted")
    role: OrganizationRole = Field(..., description="Assigned role")
    accepted_at: datetime = Field(..., description="Acceptance timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "invitation_id": "inv_abc123def456",
                "organization_id": "org_xyz789",
                "organization_name": "Acme Corp",
                "user_id": "usr_newmember456",
                "role": "member",
                "accepted_at": "2025-12-20T14:30:00Z"
            }
        }


class InvitationCreateResponseContract(BaseModel):
    """
    Contract: Invitation creation response schema

    Validates API response structure for successful invitation creation.
    """
    invitation_id: str = Field(..., description="Created invitation ID")
    invitation_token: str = Field(..., description="Secure acceptance token")
    email: str = Field(..., description="Invited person's email")
    role: OrganizationRole = Field(..., description="Assigned role")
    status: InvitationStatus = Field(
        default=InvitationStatus.PENDING,
        description="Invitation status"
    )
    expires_at: datetime = Field(..., description="Expiration timestamp")
    message: str = Field(..., description="Success message")

    class Config:
        json_schema_extra = {
            "example": {
                "invitation_id": "inv_abc123def456",
                "invitation_token": "xK9mN2pQ7rS3tU6vW8xY0zA1bC4dE5fG",
                "email": "newmember@example.com",
                "role": "member",
                "status": "pending",
                "expires_at": "2025-12-26T10:00:00Z",
                "message": "Invitation created successfully"
            }
        }


class InvitationStatsResponseContract(BaseModel):
    """
    Contract: Invitation statistics response schema

    Validates API response structure for invitation statistics.
    """
    total_invitations: int = Field(..., ge=0, description="Total invitations")
    pending_invitations: int = Field(..., ge=0, description="Pending invitations")
    accepted_invitations: int = Field(..., ge=0, description="Accepted invitations")
    expired_invitations: int = Field(..., ge=0, description="Expired invitations")
    cancelled_invitations: int = Field(..., ge=0, description="Cancelled invitations")
    conversion_rate: float = Field(
        ...,
        ge=0,
        le=100,
        description="Acceptance rate percentage"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "total_invitations": 150,
                "pending_invitations": 25,
                "accepted_invitations": 100,
                "expired_invitations": 15,
                "cancelled_invitations": 10,
                "conversion_rate": 66.67
            }
        }


class InvitationHealthResponseContract(BaseModel):
    """
    Contract: Invitation service health response schema

    Validates API response structure for health check.
    """
    status: str = Field(
        default="healthy",
        pattern="^(healthy|unhealthy|degraded)$",
        description="Service health status"
    )
    service: str = Field(default="invitation_service", description="Service name")
    port: int = Field(default=8213, ge=1024, le=65535, description="Service port")
    version: str = Field(default="1.0.0", description="Service version")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "service": "invitation_service",
                "port": 8213,
                "version": "1.0.0"
            }
        }


class InvitationServiceInfoContract(BaseModel):
    """
    Contract: Invitation service info response schema

    Validates API response structure for service info.
    """
    service: str = Field(default="invitation_service", description="Service name")
    version: str = Field(default="1.0.0", description="Service version")
    description: str = Field(..., description="Service description")
    capabilities: Dict[str, bool] = Field(
        default_factory=dict,
        description="Service capabilities"
    )
    endpoints: Dict[str, str] = Field(
        default_factory=dict,
        description="Available endpoints"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "service": "invitation_service",
                "version": "1.0.0",
                "description": "Organization invitation management microservice",
                "capabilities": {
                    "invitation_creation": True,
                    "email_sending": True,
                    "invitation_acceptance": True,
                    "invitation_management": True,
                    "organization_integration": True
                },
                "endpoints": {
                    "health": "/health",
                    "create_invitation": "/api/v1/organizations/{org_id}/invitations",
                    "get_invitation": "/api/v1/invitations/{token}",
                    "accept_invitation": "/api/v1/invitations/accept"
                }
            }
        }


class ErrorResponseContract(BaseModel):
    """
    Contract: Standard error response schema

    Validates API error response structure.
    """
    success: bool = Field(default=False, description="Operation success status")
    error: str = Field(..., description="Error type/code")
    message: str = Field(..., description="Human-readable error message")
    detail: Optional[Dict[str, Any]] = Field(None, description="Additional details")
    status_code: int = Field(..., ge=400, le=599, description="HTTP status code")

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "VALIDATION_ERROR",
                "message": "Invalid email format",
                "detail": {"field": "email", "reason": "must contain '@'"},
                "status_code": 400
            }
        }


class BulkExpireResponseContract(BaseModel):
    """
    Contract: Bulk expiration response schema

    Validates API response structure for bulk expire operation.
    """
    expired_count: int = Field(..., ge=0, description="Number of expired invitations")
    message: str = Field(..., description="Result message")

    class Config:
        json_schema_extra = {
            "example": {
                "expired_count": 47,
                "message": "Expired 47 old invitations"
            }
        }


# ============================================================================
# Test Data Factory
# ============================================================================

class InvitationTestDataFactory:
    """
    Factory for creating test data conforming to contracts.

    Provides methods to generate valid/invalid test data for all scenarios.
    ALL test data MUST be generated through these methods - zero hardcoded data.

    Method naming conventions:
    - make_*: Generate valid data
    - make_invalid_*: Generate invalid data for negative testing
    - make_*_dict: Generate as dictionary for direct API calls
    """

    # ==========================================================================
    # ID Generators
    # ==========================================================================

    @staticmethod
    def make_invitation_id() -> str:
        """Generate unique invitation ID"""
        return f"inv_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def make_organization_id() -> str:
        """Generate unique organization ID"""
        return f"org_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def make_user_id() -> str:
        """Generate unique user ID"""
        return f"user_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def make_uuid() -> str:
        """Generate UUID string"""
        return str(uuid.uuid4())

    @staticmethod
    def make_correlation_id() -> str:
        """Generate correlation ID for tracing"""
        return f"corr_{uuid.uuid4().hex[:16]}"

    # ==========================================================================
    # Token Generators
    # ==========================================================================

    @staticmethod
    def make_invitation_token() -> str:
        """Generate secure URL-safe invitation token (32 bytes)"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def make_short_token(length: int = 16) -> str:
        """Generate shorter token for testing"""
        return secrets.token_urlsafe(length)

    # ==========================================================================
    # String Generators
    # ==========================================================================

    @staticmethod
    def make_email(domain: str = "example.com") -> str:
        """Generate unique email address"""
        return f"user_{secrets.token_hex(4)}@{domain}"

    @staticmethod
    def make_email_with_name(name: str, domain: str = "example.com") -> str:
        """Generate email with specific name part"""
        safe_name = name.lower().replace(" ", ".")
        return f"{safe_name}_{secrets.token_hex(2)}@{domain}"

    @staticmethod
    def make_organization_name() -> str:
        """Generate random organization name"""
        prefixes = ["Acme", "Tech", "Global", "Prime", "Alpha", "Beta", "Delta"]
        suffixes = ["Corp", "Inc", "Labs", "Systems", "Solutions", "Group", "Team"]
        return f"{random.choice(prefixes)} {random.choice(suffixes)} {secrets.token_hex(2)}"

    @staticmethod
    def make_organization_domain() -> str:
        """Generate random organization domain"""
        return f"{secrets.token_hex(4)}.com"

    @staticmethod
    def make_user_name() -> str:
        """Generate random user name"""
        first_names = ["John", "Jane", "Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
        last_names = ["Doe", "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia"]
        return f"{random.choice(first_names)} {random.choice(last_names)}"

    @staticmethod
    def make_message(max_length: int = 200) -> str:
        """Generate random invitation message"""
        messages = [
            "Welcome to our team!",
            "We'd love to have you join us.",
            "Looking forward to working with you.",
            "Join our growing organization.",
            "Excited to have you on board!",
        ]
        base = random.choice(messages)
        suffix = f" - {secrets.token_hex(4)}"
        return (base + suffix)[:max_length]

    @staticmethod
    def make_invitation_message(max_length: int = 200) -> str:
        """Generate random invitation message (alias for make_message)"""
        return InvitationTestDataFactory.make_message(max_length)

    @staticmethod
    def make_alphanumeric(length: int = 16) -> str:
        """Generate alphanumeric string"""
        chars = string.ascii_letters + string.digits
        return ''.join(random.choices(chars, k=length))

    # ==========================================================================
    # Role and Status Generators
    # ==========================================================================

    @staticmethod
    def make_role() -> OrganizationRole:
        """Generate random organization role"""
        return random.choice(list(OrganizationRole))

    @staticmethod
    def make_invite_role() -> OrganizationRole:
        """Generate role suitable for invitation (not owner)"""
        roles = [OrganizationRole.ADMIN, OrganizationRole.MEMBER,
                 OrganizationRole.VIEWER, OrganizationRole.GUEST]
        return random.choice(roles)

    @staticmethod
    def make_admin_role() -> OrganizationRole:
        """Generate admin or owner role"""
        return random.choice([OrganizationRole.OWNER, OrganizationRole.ADMIN])

    @staticmethod
    def make_status() -> InvitationStatus:
        """Generate random invitation status"""
        return random.choice(list(InvitationStatus))

    @staticmethod
    def make_pending_status() -> InvitationStatus:
        """Generate pending status"""
        return InvitationStatus.PENDING

    # ==========================================================================
    # Timestamp Generators
    # ==========================================================================

    @staticmethod
    def make_timestamp() -> datetime:
        """Generate current UTC timestamp"""
        return datetime.now(timezone.utc)

    @staticmethod
    def make_past_timestamp(days: int = 30) -> datetime:
        """Generate timestamp in the past"""
        return datetime.now(timezone.utc) - timedelta(days=random.randint(1, days))

    @staticmethod
    def make_future_timestamp(days: int = 7) -> datetime:
        """Generate timestamp in the future"""
        return datetime.now(timezone.utc) + timedelta(days=random.randint(1, days))

    @staticmethod
    def make_expires_at(days: int = 7) -> datetime:
        """Generate expiration timestamp (default 7 days from now)"""
        return datetime.now(timezone.utc) + timedelta(days=days)

    @staticmethod
    def make_expired_timestamp() -> datetime:
        """Generate already expired timestamp"""
        return datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30))

    @staticmethod
    def make_timestamp_iso() -> str:
        """Generate ISO format timestamp string"""
        return datetime.now(timezone.utc).isoformat()

    # ==========================================================================
    # Numeric Generators
    # ==========================================================================

    @staticmethod
    def make_positive_int(max_val: int = 1000) -> int:
        """Generate positive integer"""
        return random.randint(1, max_val)

    @staticmethod
    def make_limit(default: int = 100) -> int:
        """Generate valid limit value"""
        return random.choice([10, 25, 50, 100, default])

    @staticmethod
    def make_offset() -> int:
        """Generate valid offset value"""
        return random.choice([0, 10, 25, 50, 100])

    @staticmethod
    def make_percentage() -> float:
        """Generate percentage (0-100)"""
        return round(random.uniform(0, 100), 2)

    # ==========================================================================
    # Request Generators (Valid Data)
    # ==========================================================================

    @staticmethod
    def make_create_request(**overrides) -> InvitationCreateRequestContract:
        """
        Generate valid invitation creation request.

        Args:
            **overrides: Override any default fields

        Returns:
            InvitationCreateRequestContract with valid data

        Example:
            request = InvitationTestDataFactory.make_create_request(
                email="custom@example.com",
                role=OrganizationRole.ADMIN
            )
        """
        defaults = {
            "email": InvitationTestDataFactory.make_email(),
            "role": InvitationTestDataFactory.make_invite_role(),
            "message": InvitationTestDataFactory.make_message(),
        }
        defaults.update(overrides)
        return InvitationCreateRequestContract(**defaults)

    @staticmethod
    def make_create_request_dict(**overrides) -> Dict[str, Any]:
        """Generate valid creation request as dictionary"""
        request = InvitationTestDataFactory.make_create_request(**overrides)
        return request.model_dump()

    @staticmethod
    def make_accept_request(**overrides) -> InvitationAcceptRequestContract:
        """
        Generate valid invitation acceptance request.

        Args:
            **overrides: Override any default fields

        Returns:
            InvitationAcceptRequestContract with valid data
        """
        defaults = {
            "invitation_token": InvitationTestDataFactory.make_invitation_token(),
            "user_id": InvitationTestDataFactory.make_user_id(),
        }
        defaults.update(overrides)
        return InvitationAcceptRequestContract(**defaults)

    @staticmethod
    def make_accept_request_dict(**overrides) -> Dict[str, Any]:
        """Generate valid acceptance request as dictionary"""
        request = InvitationTestDataFactory.make_accept_request(**overrides)
        return request.model_dump()

    @staticmethod
    def make_resend_request(**overrides) -> InvitationResendRequestContract:
        """Generate valid resend request"""
        defaults = {
            "invitation_id": InvitationTestDataFactory.make_invitation_id(),
        }
        defaults.update(overrides)
        return InvitationResendRequestContract(**defaults)

    @staticmethod
    def make_cancel_request(**overrides) -> InvitationCancelRequestContract:
        """Generate valid cancel request"""
        defaults = {
            "invitation_id": InvitationTestDataFactory.make_invitation_id(),
            "user_id": InvitationTestDataFactory.make_user_id(),
        }
        defaults.update(overrides)
        return InvitationCancelRequestContract(**defaults)

    @staticmethod
    def make_list_params(**overrides) -> InvitationListParamsContract:
        """
        Generate valid list parameters.

        Args:
            **overrides: Override any default fields

        Returns:
            InvitationListParamsContract with valid data
        """
        defaults = {
            "organization_id": InvitationTestDataFactory.make_organization_id(),
            "status": None,
            "limit": 100,
            "offset": 0,
        }
        defaults.update(overrides)
        return InvitationListParamsContract(**defaults)

    @staticmethod
    def make_list_params_dict(**overrides) -> Dict[str, Any]:
        """Generate valid list params as dictionary"""
        params = InvitationTestDataFactory.make_list_params(**overrides)
        return params.model_dump(exclude_none=True)

    @staticmethod
    def make_bulk_expire_request(**overrides) -> InvitationBulkExpireRequestContract:
        """Generate valid bulk expire request"""
        defaults = {
            "dry_run": False,
        }
        defaults.update(overrides)
        return InvitationBulkExpireRequestContract(**defaults)

    # ==========================================================================
    # Response Generators
    # ==========================================================================

    @staticmethod
    def make_invitation_response(**overrides) -> Dict[str, Any]:
        """
        Generate invitation response for assertions.

        Used in tests to validate API responses match contract.
        Returns dict for easier test assertions.
        """
        now = InvitationTestDataFactory.make_timestamp()
        expires = InvitationTestDataFactory.make_expires_at()

        defaults = {
            "invitation_id": InvitationTestDataFactory.make_invitation_id(),
            "organization_id": InvitationTestDataFactory.make_organization_id(),
            "email": InvitationTestDataFactory.make_email(),
            "role": InvitationTestDataFactory.make_invite_role(),
            "status": InvitationStatus.PENDING,
            "invited_by": InvitationTestDataFactory.make_user_id(),
            "invitation_token": InvitationTestDataFactory.make_invitation_token(),
            "expires_at": expires,
            "accepted_at": None,
            "created_at": now,
            "updated_at": now,
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_invitation_response_dict(**overrides) -> Dict[str, Any]:
        """Generate invitation response as dictionary (same as make_invitation_response)"""
        return InvitationTestDataFactory.make_invitation_response(**overrides)

    @staticmethod
    def make_invitation_detail_response(**overrides) -> Dict[str, Any]:
        """Generate invitation detail response for assertions."""
        now = InvitationTestDataFactory.make_timestamp()
        expires = InvitationTestDataFactory.make_expires_at()

        defaults = {
            "invitation_id": InvitationTestDataFactory.make_invitation_id(),
            "organization_id": InvitationTestDataFactory.make_organization_id(),
            "organization_name": InvitationTestDataFactory.make_organization_name(),
            "organization_domain": InvitationTestDataFactory.make_organization_domain(),
            "email": InvitationTestDataFactory.make_email(),
            "role": InvitationTestDataFactory.make_invite_role(),
            "status": InvitationStatus.PENDING,
            "inviter_name": InvitationTestDataFactory.make_user_name(),
            "inviter_email": InvitationTestDataFactory.make_email(),
            "expires_at": expires,
            "created_at": now,
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_list_response(count: int = 3, **overrides) -> Dict[str, Any]:
        """Generate list response with multiple invitations"""
        invitations = [
            InvitationTestDataFactory.make_invitation_response()
            for _ in range(count)
        ]
        defaults = {
            "invitations": invitations,
            "total": count,
            "limit": 100,
            "offset": 0,
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_accept_response(**overrides) -> Dict[str, Any]:
        """Generate accept invitation response for assertions."""
        now = InvitationTestDataFactory.make_timestamp()

        defaults = {
            "invitation_id": InvitationTestDataFactory.make_invitation_id(),
            "organization_id": InvitationTestDataFactory.make_organization_id(),
            "organization_name": InvitationTestDataFactory.make_organization_name(),
            "user_id": InvitationTestDataFactory.make_user_id(),
            "role": InvitationTestDataFactory.make_invite_role(),
            "accepted_at": now,
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_create_response(**overrides) -> Dict[str, Any]:
        """Generate create invitation response for assertions."""
        expires = InvitationTestDataFactory.make_expires_at()

        defaults = {
            "invitation_id": InvitationTestDataFactory.make_invitation_id(),
            "invitation_token": InvitationTestDataFactory.make_invitation_token(),
            "email": InvitationTestDataFactory.make_email(),
            "role": InvitationTestDataFactory.make_invite_role(),
            "status": InvitationStatus.PENDING,
            "expires_at": expires,
            "message": "Invitation created successfully",
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_stats_response(**overrides) -> Dict[str, Any]:
        """Generate stats response for assertions."""
        total = random.randint(100, 500)
        accepted = int(total * random.uniform(0.5, 0.8))
        pending = int(total * random.uniform(0.1, 0.2))
        expired = int(total * random.uniform(0.05, 0.15))
        cancelled = total - accepted - pending - expired

        defaults = {
            "total_invitations": total,
            "pending_invitations": pending,
            "accepted_invitations": accepted,
            "expired_invitations": expired,
            "cancelled_invitations": max(0, cancelled),
            "conversion_rate": round((accepted / total) * 100, 2) if total > 0 else 0,
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_health_response(**overrides) -> Dict[str, Any]:
        """Generate health response for assertions."""
        defaults = {
            "status": "healthy",
            "service": "invitation_service",
            "port": 8213,
            "version": "1.0.0",
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_service_info(**overrides) -> Dict[str, Any]:
        """Generate service info response for assertions."""
        defaults = {
            "service": "invitation_service",
            "version": "1.0.0",
            "description": "Organization invitation management microservice",
            "capabilities": {
                "invitation_creation": True,
                "email_sending": True,
                "invitation_acceptance": True,
                "invitation_management": True,
                "organization_integration": True,
            },
            "endpoints": {
                "health": "/health",
                "create_invitation": "/api/v1/organizations/{org_id}/invitations",
                "get_invitation": "/api/v1/invitations/{token}",
                "accept_invitation": "/api/v1/invitations/accept",
            },
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_error_response(**overrides) -> Dict[str, Any]:
        """Generate error response for assertions."""
        defaults = {
            "success": False,
            "error": "VALIDATION_ERROR",
            "message": "Validation failed",
            "detail": None,
            "status_code": 400,
        }
        defaults.update(overrides)
        return defaults

    @staticmethod
    def make_bulk_expire_response(**overrides) -> Dict[str, Any]:
        """Generate bulk expire response for assertions."""
        count = random.randint(0, 100)
        defaults = {
            "expired_count": count,
            "message": f"Expired {count} old invitations",
        }
        defaults.update(overrides)
        return defaults

    # ==========================================================================
    # Invalid Data Generators (for negative testing)
    # ==========================================================================

    @staticmethod
    def make_invalid_invitation_id() -> str:
        """Generate invalid invitation ID (wrong format)"""
        return "invalid_id_format"

    @staticmethod
    def make_invalid_organization_id() -> str:
        """Generate invalid organization ID"""
        return ""

    @staticmethod
    def make_invalid_user_id() -> str:
        """Generate invalid user ID"""
        return ""

    @staticmethod
    def make_invalid_token_empty() -> str:
        """Generate empty token"""
        return ""

    @staticmethod
    def make_invalid_token_short() -> str:
        """Generate token too short"""
        return "abc123"

    @staticmethod
    def make_invalid_email_no_at() -> str:
        """Generate email without @ symbol"""
        return "invalid-email-no-at.com"

    @staticmethod
    def make_invalid_email() -> str:
        """Generate invalid email (alias for make_invalid_email_no_at)"""
        return InvitationTestDataFactory.make_invalid_email_no_at()

    @staticmethod
    def make_invalid_email_empty() -> str:
        """Generate empty email"""
        return ""

    @staticmethod
    def make_invalid_email_whitespace() -> str:
        """Generate whitespace-only email"""
        return "   "

    @staticmethod
    def make_invalid_role() -> str:
        """Generate invalid role value"""
        return "invalid_role"

    @staticmethod
    def make_invalid_status() -> str:
        """Generate invalid status value"""
        return "invalid_status"

    @staticmethod
    def make_invalid_message_too_long() -> str:
        """Generate message exceeding 500 characters"""
        return "x" * 501

    @staticmethod
    def make_invalid_limit_zero() -> int:
        """Generate invalid limit (zero)"""
        return 0

    @staticmethod
    def make_invalid_limit_negative() -> int:
        """Generate invalid limit (negative)"""
        return -1

    @staticmethod
    def make_invalid_limit_too_large() -> int:
        """Generate invalid limit (exceeds max)"""
        return 10001

    @staticmethod
    def make_invalid_offset_negative() -> int:
        """Generate invalid offset (negative)"""
        return -1

    @staticmethod
    def make_invalid_create_request_missing_email() -> dict:
        """Generate create request missing required email"""
        return {
            "role": "member",
            "message": "Welcome!",
        }

    @staticmethod
    def make_invalid_create_request_invalid_email() -> dict:
        """Generate create request with invalid email format"""
        return {
            "email": InvitationTestDataFactory.make_invalid_email_no_at(),
            "role": "member",
        }

    @staticmethod
    def make_invalid_create_request_invalid_role() -> dict:
        """Generate create request with invalid role"""
        return {
            "email": InvitationTestDataFactory.make_email(),
            "role": "super_admin",  # Invalid role
        }

    @staticmethod
    def make_invalid_create_request_message_too_long() -> dict:
        """Generate create request with message too long"""
        return {
            "email": InvitationTestDataFactory.make_email(),
            "role": "member",
            "message": InvitationTestDataFactory.make_invalid_message_too_long(),
        }

    @staticmethod
    def make_invalid_accept_request_missing_token() -> dict:
        """Generate accept request missing required token"""
        return {
            "user_id": InvitationTestDataFactory.make_user_id(),
        }

    @staticmethod
    def make_invalid_accept_request_empty_token() -> dict:
        """Generate accept request with empty token"""
        return {
            "invitation_token": "",
            "user_id": InvitationTestDataFactory.make_user_id(),
        }

    @staticmethod
    def make_invalid_list_params_negative_limit() -> dict:
        """Generate list params with negative limit"""
        return {
            "organization_id": InvitationTestDataFactory.make_organization_id(),
            "limit": -1,
            "offset": 0,
        }

    @staticmethod
    def make_invalid_list_params_negative_offset() -> dict:
        """Generate list params with negative offset"""
        return {
            "organization_id": InvitationTestDataFactory.make_organization_id(),
            "limit": 100,
            "offset": -1,
        }

    # ==========================================================================
    # Edge Case Generators
    # ==========================================================================

    @staticmethod
    def make_unicode_email() -> str:
        """Generate email with unicode characters in local part"""
        return f"user_{secrets.token_hex(2)}_\u4e2d\u6587@example.com"

    @staticmethod
    def make_unicode_message() -> str:
        """Generate message with unicode characters"""
        return f"Welcome \u4e2d\u6587 \u65e5\u672c\u8a9e - {secrets.token_hex(4)}"

    @staticmethod
    def make_max_length_message() -> str:
        """Generate message at max length (500 chars)"""
        return "x" * 500

    @staticmethod
    def make_min_length_email() -> str:
        """Generate minimal valid email"""
        return "a@b.c"

    @staticmethod
    def make_special_chars_email() -> str:
        """Generate email with special characters"""
        return f"user+tag_{secrets.token_hex(2)}@example.com"

    @staticmethod
    def make_expired_invitation_response(**overrides) -> Dict[str, Any]:
        """Generate invitation response with expired status"""
        expired_at = InvitationTestDataFactory.make_expired_timestamp()
        return InvitationTestDataFactory.make_invitation_response(
            status=InvitationStatus.EXPIRED,
            expires_at=expired_at,
            **overrides
        )

    @staticmethod
    def make_accepted_invitation_response(**overrides) -> Dict[str, Any]:
        """Generate invitation response with accepted status"""
        accepted_at = InvitationTestDataFactory.make_timestamp()
        return InvitationTestDataFactory.make_invitation_response(
            status=InvitationStatus.ACCEPTED,
            accepted_at=accepted_at,
            **overrides
        )

    @staticmethod
    def make_cancelled_invitation_response(**overrides) -> Dict[str, Any]:
        """Generate invitation response with cancelled status"""
        return InvitationTestDataFactory.make_invitation_response(
            status=InvitationStatus.CANCELLED,
            **overrides
        )

    # ==========================================================================
    # Batch Generators
    # ==========================================================================

    @staticmethod
    def make_batch_create_requests(count: int = 5) -> List[InvitationCreateRequestContract]:
        """Generate multiple creation requests"""
        return [
            InvitationTestDataFactory.make_create_request()
            for _ in range(count)
        ]

    @staticmethod
    def make_batch_invitation_ids(count: int = 5) -> List[str]:
        """Generate multiple invitation IDs"""
        return [
            InvitationTestDataFactory.make_invitation_id()
            for _ in range(count)
        ]

    @staticmethod
    def make_batch_emails(count: int = 5, domain: str = "example.com") -> List[str]:
        """Generate multiple unique emails"""
        return [
            InvitationTestDataFactory.make_email(domain)
            for _ in range(count)
        ]

    @staticmethod
    def make_batch_invitation_responses(count: int = 5) -> List[Dict[str, Any]]:
        """Generate multiple invitation responses"""
        return [
            InvitationTestDataFactory.make_invitation_response()
            for _ in range(count)
        ]

    @staticmethod
    def make_invitations_by_status(
        pending: int = 2,
        accepted: int = 2,
        expired: int = 1,
        cancelled: int = 0
    ) -> List[Dict[str, Any]]:
        """Generate invitations with specific status distribution"""
        invitations = []
        for _ in range(pending):
            invitations.append(InvitationTestDataFactory.make_invitation_response(
                status=InvitationStatus.PENDING
            ))
        for _ in range(accepted):
            invitations.append(InvitationTestDataFactory.make_accepted_invitation_response())
        for _ in range(expired):
            invitations.append(InvitationTestDataFactory.make_expired_invitation_response())
        for _ in range(cancelled):
            invitations.append(InvitationTestDataFactory.make_cancelled_invitation_response())
        return invitations


# ============================================================================
# Request Builders (for complex test scenarios)
# ============================================================================

class InvitationCreateRequestBuilder:
    """
    Builder pattern for creating complex invitation creation requests.

    Useful for tests that need to gradually construct requests.

    Example:
        request = (
            InvitationCreateRequestBuilder()
            .with_email("john@example.com")
            .with_role(OrganizationRole.ADMIN)
            .with_message("Welcome!")
            .build()
        )
    """

    def __init__(self):
        """Initialize with factory-generated defaults"""
        self._email = InvitationTestDataFactory.make_email()
        self._role = OrganizationRole.MEMBER
        self._message: Optional[str] = None

    def with_email(self, email: str) -> "InvitationCreateRequestBuilder":
        """Set email address"""
        self._email = email
        return self

    def with_role(self, role: OrganizationRole) -> "InvitationCreateRequestBuilder":
        """Set organization role"""
        self._role = role
        return self

    def with_member_role(self) -> "InvitationCreateRequestBuilder":
        """Set member role"""
        self._role = OrganizationRole.MEMBER
        return self

    def with_admin_role(self) -> "InvitationCreateRequestBuilder":
        """Set admin role"""
        self._role = OrganizationRole.ADMIN
        return self

    def with_viewer_role(self) -> "InvitationCreateRequestBuilder":
        """Set viewer role"""
        self._role = OrganizationRole.VIEWER
        return self

    def with_guest_role(self) -> "InvitationCreateRequestBuilder":
        """Set guest role"""
        self._role = OrganizationRole.GUEST
        return self

    def with_message(self, message: str) -> "InvitationCreateRequestBuilder":
        """Set invitation message"""
        self._message = message
        return self

    def with_generated_message(self) -> "InvitationCreateRequestBuilder":
        """Set factory-generated message"""
        self._message = InvitationTestDataFactory.make_message()
        return self

    def without_message(self) -> "InvitationCreateRequestBuilder":
        """Remove message"""
        self._message = None
        return self

    def with_invalid_email(self) -> "InvitationCreateRequestBuilder":
        """Set invalid email for negative testing"""
        self._email = InvitationTestDataFactory.make_invalid_email_no_at()
        return self

    def with_invalid_message_too_long(self) -> "InvitationCreateRequestBuilder":
        """Set invalid message for negative testing"""
        self._message = InvitationTestDataFactory.make_invalid_message_too_long()
        return self

    def build(self) -> InvitationCreateRequestContract:
        """Build the final request contract"""
        return InvitationCreateRequestContract(
            email=self._email,
            role=self._role,
            message=self._message,
        )

    def build_dict(self) -> Dict[str, Any]:
        """Build as dictionary for API calls"""
        return self.build().model_dump(exclude_none=True)


class InvitationAcceptRequestBuilder:
    """
    Builder pattern for creating invitation acceptance requests.

    Example:
        request = (
            InvitationAcceptRequestBuilder()
            .with_token("abc123...")
            .with_user_id("usr_xyz")
            .build()
        )
    """

    def __init__(self):
        """Initialize with factory-generated defaults"""
        self._token = InvitationTestDataFactory.make_invitation_token()
        self._user_id: Optional[str] = None

    def with_token(self, token: str) -> "InvitationAcceptRequestBuilder":
        """Set invitation token"""
        self._token = token
        return self

    def with_generated_token(self) -> "InvitationAcceptRequestBuilder":
        """Set factory-generated token"""
        self._token = InvitationTestDataFactory.make_invitation_token()
        return self

    def with_user_id(self, user_id: str) -> "InvitationAcceptRequestBuilder":
        """Set user ID"""
        self._user_id = user_id
        return self

    def with_generated_user_id(self) -> "InvitationAcceptRequestBuilder":
        """Set factory-generated user ID"""
        self._user_id = InvitationTestDataFactory.make_user_id()
        return self

    def without_user_id(self) -> "InvitationAcceptRequestBuilder":
        """Remove user ID"""
        self._user_id = None
        return self

    def with_invalid_token_empty(self) -> "InvitationAcceptRequestBuilder":
        """Set empty token for negative testing"""
        self._token = ""
        return self

    def with_invalid_token_short(self) -> "InvitationAcceptRequestBuilder":
        """Set short token for negative testing"""
        self._token = InvitationTestDataFactory.make_invalid_token_short()
        return self

    def build(self) -> InvitationAcceptRequestContract:
        """Build the final request contract"""
        return InvitationAcceptRequestContract(
            invitation_token=self._token,
            user_id=self._user_id,
        )

    def build_dict(self) -> Dict[str, Any]:
        """Build as dictionary for API calls"""
        return self.build().model_dump(exclude_none=True)


class InvitationListParamsBuilder:
    """
    Builder pattern for creating invitation list query parameters.

    Example:
        params = (
            InvitationListParamsBuilder()
            .for_organization("org_xyz")
            .with_status(InvitationStatus.PENDING)
            .with_pagination(limit=50, offset=0)
            .build()
        )
    """

    def __init__(self):
        """Initialize with factory-generated defaults"""
        self._organization_id = InvitationTestDataFactory.make_organization_id()
        self._status: Optional[InvitationStatus] = None
        self._limit = 100
        self._offset = 0

    def for_organization(self, organization_id: str) -> "InvitationListParamsBuilder":
        """Set organization ID"""
        self._organization_id = organization_id
        return self

    def with_status(self, status: InvitationStatus) -> "InvitationListParamsBuilder":
        """Filter by status"""
        self._status = status
        return self

    def pending_only(self) -> "InvitationListParamsBuilder":
        """Filter pending invitations only"""
        self._status = InvitationStatus.PENDING
        return self

    def accepted_only(self) -> "InvitationListParamsBuilder":
        """Filter accepted invitations only"""
        self._status = InvitationStatus.ACCEPTED
        return self

    def expired_only(self) -> "InvitationListParamsBuilder":
        """Filter expired invitations only"""
        self._status = InvitationStatus.EXPIRED
        return self

    def cancelled_only(self) -> "InvitationListParamsBuilder":
        """Filter cancelled invitations only"""
        self._status = InvitationStatus.CANCELLED
        return self

    def all_statuses(self) -> "InvitationListParamsBuilder":
        """Include all statuses"""
        self._status = None
        return self

    def with_pagination(self, limit: int, offset: int) -> "InvitationListParamsBuilder":
        """Set pagination parameters"""
        self._limit = limit
        self._offset = offset
        return self

    def with_limit(self, limit: int) -> "InvitationListParamsBuilder":
        """Set limit only"""
        self._limit = limit
        return self

    def with_offset(self, offset: int) -> "InvitationListParamsBuilder":
        """Set offset only"""
        self._offset = offset
        return self

    def first_page(self, page_size: int = 50) -> "InvitationListParamsBuilder":
        """Set first page with given page size"""
        self._limit = page_size
        self._offset = 0
        return self

    def page(self, page_number: int, page_size: int = 50) -> "InvitationListParamsBuilder":
        """Set specific page (1-indexed)"""
        self._limit = page_size
        self._offset = (page_number - 1) * page_size
        return self

    def with_invalid_limit_negative(self) -> "InvitationListParamsBuilder":
        """Set negative limit for negative testing"""
        self._limit = -1
        return self

    def with_invalid_offset_negative(self) -> "InvitationListParamsBuilder":
        """Set negative offset for negative testing"""
        self._offset = -1
        return self

    def build(self) -> InvitationListParamsContract:
        """Build the final params contract"""
        return InvitationListParamsContract(
            organization_id=self._organization_id,
            status=self._status,
            limit=self._limit,
            offset=self._offset,
        )

    def build_dict(self) -> Dict[str, Any]:
        """Build as dictionary for API calls"""
        return self.build().model_dump(exclude_none=True)


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Enums
    "InvitationStatus",
    "OrganizationRole",

    # Request Contracts
    "InvitationCreateRequestContract",
    "InvitationAcceptRequestContract",
    "InvitationResendRequestContract",
    "InvitationCancelRequestContract",
    "InvitationListParamsContract",
    "InvitationBulkExpireRequestContract",

    # Response Contracts
    "InvitationResponseContract",
    "InvitationDetailResponseContract",
    "InvitationListResponseContract",
    "AcceptInvitationResponseContract",
    "InvitationCreateResponseContract",
    "InvitationStatsResponseContract",
    "InvitationHealthResponseContract",
    "InvitationServiceInfoContract",
    "ErrorResponseContract",
    "BulkExpireResponseContract",

    # Factory
    "InvitationTestDataFactory",

    # Builders
    "InvitationCreateRequestBuilder",
    "InvitationAcceptRequestBuilder",
    "InvitationListParamsBuilder",
]
