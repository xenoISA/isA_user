"""
Authentication Service - Data Contract

Pydantic schemas, test data factory, and request builders for auth_service.
Zero hardcoded data - all test data generated through factory methods.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr, field_validator
from datetime import datetime, timezone, timedelta
import secrets
import uuid


# ============================================================================
# Request Contracts (12 schemas)
# ============================================================================

class TokenVerificationRequestContract(BaseModel):
    """Contract for token verification requests"""
    token: str = Field(..., description="JWT token to verify")
    provider: Optional[str] = Field(None, description="Provider hint: auth0, isa_user, local")

    class Config:
        json_schema_extra = {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "provider": "isa_user"
            }
        }


class DevTokenRequestContract(BaseModel):
    """Contract for development token generation"""
    user_id: str = Field(..., description="User ID")
    email: EmailStr = Field(..., description="User email")
    expires_in: int = Field(3600, ge=1, le=86400, description="Expiration in seconds")
    subscription_level: Optional[str] = Field("free", description="Subscription level")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    permissions: Optional[List[str]] = Field(None, description="Permissions list")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "usr_abc123",
                "email": "user@example.com",
                "expires_in": 3600,
                "subscription_level": "free",
                "organization_id": "org_xyz789",
                "permissions": ["read:users", "write:users"]
            }
        }


class TokenPairRequestContract(BaseModel):
    """Contract for token pair generation"""
    user_id: str = Field(..., description="User ID")
    email: EmailStr = Field(..., description="User email")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    permissions: Optional[List[str]] = Field(None, description="Permissions")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "usr_abc123",
                "email": "user@example.com",
                "organization_id": "org_xyz789",
                "permissions": ["read:data"]
            }
        }


class RefreshTokenRequestContract(BaseModel):
    """Contract for token refresh"""
    refresh_token: str = Field(..., description="Refresh token")

    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class RegistrationStartRequestContract(BaseModel):
    """Contract for registration start"""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=8, description="Password (min 8 chars)")
    name: Optional[str] = Field(None, description="Display name")

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "email": "newuser@example.com",
                "password": "SecurePass123!",
                "name": "John Doe"
            }
        }


class RegistrationVerifyRequestContract(BaseModel):
    """Contract for registration verification"""
    pending_registration_id: str = Field(..., description="Pending registration ID")
    code: str = Field(..., min_length=6, max_length=6, description="6-digit verification code")

    @field_validator('code')
    @classmethod
    def validate_code(cls, v):
        if not v.isdigit():
            raise ValueError("Code must contain only digits")
        if len(v) != 6:
            raise ValueError("Code must be exactly 6 digits")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "pending_registration_id": "abc123def456",
                "code": "123456"
            }
        }


class ApiKeyCreateRequestContract(BaseModel):
    """Contract for API key creation"""
    organization_id: str = Field(..., description="Organization ID")
    name: str = Field(..., min_length=1, description="Key name")
    permissions: Optional[List[str]] = Field(default=[], description="Permissions")
    expires_days: Optional[int] = Field(None, ge=1, le=365, description="Expiration in days (max 365)")

    class Config:
        json_schema_extra = {
            "example": {
                "organization_id": "org_xyz789",
                "name": "Production API Key",
                "permissions": ["read:data", "write:data"],
                "expires_days": 90
            }
        }


class ApiKeyVerifyRequestContract(BaseModel):
    """Contract for API key verification"""
    api_key: str = Field(..., description="API key to verify")

    class Config:
        json_schema_extra = {
            "example": {
                "api_key": "isa_abc123def456xyz789"
            }
        }


class DeviceRegisterRequestContract(BaseModel):
    """Contract for device registration"""
    device_id: str = Field(..., description="Device ID")
    organization_id: str = Field(..., description="Organization ID")
    device_name: Optional[str] = Field(None, description="Device name")
    device_type: Optional[str] = Field(None, description="Device type")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="Device metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "device_id": "dev_abc123",
                "organization_id": "org_xyz789",
                "device_name": "IoT Sensor #1",
                "device_type": "iot_sensor",
                "metadata": {"location": "office", "firmware": "1.0.0"}
            }
        }


class DeviceAuthenticateRequestContract(BaseModel):
    """Contract for device authentication"""
    device_id: str = Field(..., description="Device ID")
    device_secret: str = Field(..., description="Device secret")

    class Config:
        json_schema_extra = {
            "example": {
                "device_id": "dev_abc123",
                "device_secret": "secret_xyz789abc123"
            }
        }


class DevicePairingGenerateRequestContract(BaseModel):
    """Contract for pairing token generation"""
    device_id: str = Field(..., description="Device ID")

    class Config:
        json_schema_extra = {
            "example": {
                "device_id": "dev_abc123"
            }
        }


class DevicePairingVerifyRequestContract(BaseModel):
    """Contract for pairing token verification"""
    device_id: str = Field(..., description="Device ID")
    pairing_token: str = Field(..., description="Pairing token")
    user_id: str = Field(..., description="User ID")

    class Config:
        json_schema_extra = {
            "example": {
                "device_id": "dev_abc123",
                "pairing_token": "pairing_xyz789",
                "user_id": "usr_abc123"
            }
        }


# ============================================================================
# Response Contracts (10 schemas)
# ============================================================================

class TokenVerificationResponseContract(BaseModel):
    """Contract for token verification response"""
    valid: bool
    provider: Optional[str] = None
    user_id: Optional[str] = None
    email: Optional[str] = None
    organization_id: Optional[str] = None
    subscription_level: Optional[str] = None
    expires_at: Optional[datetime] = None
    error: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "valid": True,
                "provider": "isa_user",
                "user_id": "usr_abc123",
                "email": "user@example.com",
                "organization_id": "org_xyz789",
                "expires_at": "2025-12-13T12:00:00Z"
            }
        }


class TokenResponseContract(BaseModel):
    """Contract for token generation response"""
    success: bool
    token: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: Optional[int] = None
    user_id: Optional[str] = None
    email: Optional[str] = None
    provider: str = "isa_user"
    error: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "Bearer",
                "expires_in": 3600,
                "user_id": "usr_abc123",
                "email": "user@example.com",
                "provider": "isa_user"
            }
        }


class RegistrationStartResponseContract(BaseModel):
    """Contract for registration start response"""
    pending_registration_id: str
    verification_required: bool = True
    expires_at: str

    class Config:
        json_schema_extra = {
            "example": {
                "pending_registration_id": "abc123def456",
                "verification_required": True,
                "expires_at": "2025-12-13T12:10:00Z"
            }
        }


class RegistrationVerifyResponseContract(BaseModel):
    """Contract for registration verification response"""
    success: bool
    user_id: Optional[str] = None
    email: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: Optional[str] = None
    expires_in: Optional[int] = None
    error: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "user_id": "usr_abc123",
                "email": "user@example.com",
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "Bearer",
                "expires_in": 3600
            }
        }


class ApiKeyCreateResponseContract(BaseModel):
    """Contract for API key creation response"""
    success: bool
    api_key: Optional[str] = None
    key_id: Optional[str] = None
    name: Optional[str] = None
    expires_at: Optional[datetime] = None
    error: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "api_key": "isa_abc123def456xyz789",
                "key_id": "key_123",
                "name": "Production API Key",
                "expires_at": "2025-03-13T12:00:00Z"
            }
        }


class ApiKeyVerifyResponseContract(BaseModel):
    """Contract for API key verification response"""
    valid: bool
    key_id: Optional[str] = None
    organization_id: Optional[str] = None
    name: Optional[str] = None
    permissions: Optional[List[str]] = None
    error: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "valid": True,
                "key_id": "key_123",
                "organization_id": "org_xyz789",
                "name": "Production API Key",
                "permissions": ["read:data", "write:data"]
            }
        }


class DeviceRegisterResponseContract(BaseModel):
    """Contract for device registration response"""
    success: bool
    device_id: Optional[str] = None
    device_secret: Optional[str] = None
    organization_id: Optional[str] = None
    error: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "device_id": "dev_abc123",
                "device_secret": "secret_xyz789abc123",
                "organization_id": "org_xyz789"
            }
        }


class DeviceAuthenticateResponseContract(BaseModel):
    """Contract for device authentication response"""
    success: bool
    authenticated: bool
    device_id: Optional[str] = None
    organization_id: Optional[str] = None
    access_token: Optional[str] = None
    token_type: Optional[str] = None
    expires_in: Optional[int] = None
    error: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "authenticated": True,
                "device_id": "dev_abc123",
                "organization_id": "org_xyz789",
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "Bearer",
                "expires_in": 3600
            }
        }


class DevicePairingResponseContract(BaseModel):
    """Contract for device pairing response (both generate and verify)"""
    success: Optional[bool] = None
    valid: Optional[bool] = None
    pairing_token: Optional[str] = None
    device_id: Optional[str] = None
    user_id: Optional[str] = None
    expires_at: Optional[str] = None
    expires_in: Optional[int] = None
    error: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "pairing_token": "pairing_xyz789",
                "device_id": "dev_abc123",
                "expires_at": "2025-12-13T12:10:00Z",
                "expires_in": 300
            }
        }


class UserInfoResponseContract(BaseModel):
    """Contract for user info extraction from token"""
    user_id: str
    email: str
    organization_id: Optional[str] = None
    permissions: Optional[List[str]] = None
    provider: str
    expires_at: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "usr_abc123",
                "email": "user@example.com",
                "organization_id": "org_xyz789",
                "permissions": ["read:data"],
                "provider": "isa_user",
                "expires_at": "2025-12-13T12:00:00Z"
            }
        }


# ============================================================================
# AuthTestDataFactory - 35+ methods (20+ valid + 15+ invalid)
# ============================================================================

class AuthTestDataFactory:
    """Test data factory for auth_service - zero hardcoded data"""

    # ========================================================================
    # Valid data generators (20+ methods)
    # ========================================================================

    @staticmethod
    def make_user_id() -> str:
        """Generate valid user ID"""
        return f"usr_{uuid.uuid4().hex}"

    @staticmethod
    def make_email() -> str:
        """Generate valid email"""
        return f"user_{secrets.token_hex(4)}@example.com"

    @staticmethod
    def make_organization_id() -> str:
        """Generate valid organization ID"""
        return f"org_{uuid.uuid4().hex}"

    @staticmethod
    def make_device_id() -> str:
        """Generate valid device ID"""
        return f"dev_{uuid.uuid4().hex}"

    @staticmethod
    def make_device_secret() -> str:
        """Generate valid device secret"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def make_password() -> str:
        """Generate valid password (min 8 chars with complexity)"""
        return f"SecurePass{secrets.randbelow(10000):04d}!"

    @staticmethod
    def make_verification_code() -> str:
        """Generate 6-digit verification code"""
        return f"{secrets.randbelow(1000000):06d}"

    @staticmethod
    def make_api_key() -> str:
        """Generate valid API key"""
        return f"isa_{secrets.token_urlsafe(32)}"

    @staticmethod
    def make_pairing_token() -> str:
        """Generate pairing token"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def make_jwt_token() -> str:
        """Generate mock JWT token (not real, for testing format)"""
        # Mock JWT structure: header.payload.signature
        header = secrets.token_urlsafe(16)
        payload = secrets.token_urlsafe(64)
        signature = secrets.token_urlsafe(43)
        return f"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.{payload}.{signature}"

    @staticmethod
    def make_refresh_token() -> str:
        """Generate mock refresh token"""
        return AuthTestDataFactory.make_jwt_token()

    @staticmethod
    def make_permissions() -> List[str]:
        """Generate valid permissions list"""
        all_perms = ["read:users", "write:users", "read:data", "write:data", "admin:all", "read:devices"]
        num_perms = secrets.randbelow(len(all_perms)) + 1
        return [all_perms[i] for i in range(num_perms)]

    @staticmethod
    def make_subscription_level() -> str:
        """Generate valid subscription level"""
        levels = ["free", "basic", "pro", "enterprise"]
        return levels[secrets.randbelow(len(levels))]

    @staticmethod
    def make_device_type() -> str:
        """Generate valid device type"""
        types = ["iot_sensor", "smart_display", "mobile_device", "gateway"]
        return types[secrets.randbelow(len(types))]

    @staticmethod
    def make_device_name() -> str:
        """Generate valid device name"""
        return f"Device {secrets.token_hex(4)}"

    @staticmethod
    def make_api_key_name() -> str:
        """Generate valid API key name"""
        return f"API Key {secrets.token_hex(4)}"

    @staticmethod
    def make_pending_registration_id() -> str:
        """Generate pending registration ID"""
        return uuid.uuid4().hex

    @staticmethod
    def make_key_id() -> str:
        """Generate API key ID"""
        return f"key_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def make_metadata() -> Dict[str, Any]:
        """Generate sample metadata"""
        return {
            "source": "test",
            "environment": "development",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    @staticmethod
    def make_token_verification_request(**overrides) -> TokenVerificationRequestContract:
        """Generate valid token verification request"""
        defaults = {
            "token": AuthTestDataFactory.make_jwt_token(),
            "provider": "isa_user"
        }
        defaults.update(overrides)
        return TokenVerificationRequestContract(**defaults)

    @staticmethod
    def make_dev_token_request(**overrides) -> DevTokenRequestContract:
        """Generate valid dev token request"""
        defaults = {
            "user_id": AuthTestDataFactory.make_user_id(),
            "email": AuthTestDataFactory.make_email(),
            "expires_in": 3600,
            "subscription_level": AuthTestDataFactory.make_subscription_level(),
            "organization_id": AuthTestDataFactory.make_organization_id(),
            "permissions": AuthTestDataFactory.make_permissions(),
            "metadata": AuthTestDataFactory.make_metadata()
        }
        defaults.update(overrides)
        return DevTokenRequestContract(**defaults)

    @staticmethod
    def make_token_pair_request(**overrides) -> TokenPairRequestContract:
        """Generate valid token pair request"""
        defaults = {
            "user_id": AuthTestDataFactory.make_user_id(),
            "email": AuthTestDataFactory.make_email(),
            "organization_id": AuthTestDataFactory.make_organization_id(),
            "permissions": AuthTestDataFactory.make_permissions(),
            "metadata": AuthTestDataFactory.make_metadata()
        }
        defaults.update(overrides)
        return TokenPairRequestContract(**defaults)

    @staticmethod
    def make_refresh_token_request(**overrides) -> RefreshTokenRequestContract:
        """Generate valid refresh token request"""
        defaults = {
            "refresh_token": AuthTestDataFactory.make_refresh_token()
        }
        defaults.update(overrides)
        return RefreshTokenRequestContract(**defaults)

    @staticmethod
    def make_registration_start_request(**overrides) -> RegistrationStartRequestContract:
        """Generate valid registration start request"""
        defaults = {
            "email": AuthTestDataFactory.make_email(),
            "password": AuthTestDataFactory.make_password(),
            "name": f"User {secrets.token_hex(4)}"
        }
        defaults.update(overrides)
        return RegistrationStartRequestContract(**defaults)

    @staticmethod
    def make_registration_verify_request(**overrides) -> RegistrationVerifyRequestContract:
        """Generate valid registration verify request"""
        defaults = {
            "pending_registration_id": AuthTestDataFactory.make_pending_registration_id(),
            "code": AuthTestDataFactory.make_verification_code()
        }
        defaults.update(overrides)
        return RegistrationVerifyRequestContract(**defaults)

    @staticmethod
    def make_api_key_create_request(**overrides) -> ApiKeyCreateRequestContract:
        """Generate valid API key create request"""
        defaults = {
            "organization_id": AuthTestDataFactory.make_organization_id(),
            "name": AuthTestDataFactory.make_api_key_name(),
            "permissions": AuthTestDataFactory.make_permissions(),
            "expires_days": 90
        }
        defaults.update(overrides)
        return ApiKeyCreateRequestContract(**defaults)

    @staticmethod
    def make_api_key_verify_request(**overrides) -> ApiKeyVerifyRequestContract:
        """Generate valid API key verify request"""
        defaults = {
            "api_key": AuthTestDataFactory.make_api_key()
        }
        defaults.update(overrides)
        return ApiKeyVerifyRequestContract(**defaults)

    @staticmethod
    def make_device_register_request(**overrides) -> DeviceRegisterRequestContract:
        """Generate valid device register request"""
        defaults = {
            "device_id": AuthTestDataFactory.make_device_id(),
            "organization_id": AuthTestDataFactory.make_organization_id(),
            "device_name": AuthTestDataFactory.make_device_name(),
            "device_type": AuthTestDataFactory.make_device_type(),
            "metadata": {"location": "office", "firmware": "1.0.0"}
        }
        defaults.update(overrides)
        return DeviceRegisterRequestContract(**defaults)

    @staticmethod
    def make_device_authenticate_request(**overrides) -> DeviceAuthenticateRequestContract:
        """Generate valid device authenticate request"""
        defaults = {
            "device_id": AuthTestDataFactory.make_device_id(),
            "device_secret": AuthTestDataFactory.make_device_secret()
        }
        defaults.update(overrides)
        return DeviceAuthenticateRequestContract(**defaults)

    @staticmethod
    def make_device_pairing_generate_request(**overrides) -> DevicePairingGenerateRequestContract:
        """Generate valid pairing generate request"""
        defaults = {
            "device_id": AuthTestDataFactory.make_device_id()
        }
        defaults.update(overrides)
        return DevicePairingGenerateRequestContract(**defaults)

    @staticmethod
    def make_device_pairing_verify_request(**overrides) -> DevicePairingVerifyRequestContract:
        """Generate valid pairing verify request"""
        defaults = {
            "device_id": AuthTestDataFactory.make_device_id(),
            "pairing_token": AuthTestDataFactory.make_pairing_token(),
            "user_id": AuthTestDataFactory.make_user_id()
        }
        defaults.update(overrides)
        return DevicePairingVerifyRequestContract(**defaults)

    @staticmethod
    def make_token_verification_response(**overrides) -> TokenVerificationResponseContract:
        """Generate expected token verification response"""
        defaults = {
            "valid": True,
            "provider": "isa_user",
            "user_id": AuthTestDataFactory.make_user_id(),
            "email": AuthTestDataFactory.make_email(),
            "organization_id": AuthTestDataFactory.make_organization_id(),
            "subscription_level": AuthTestDataFactory.make_subscription_level(),
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
            "error": None
        }
        defaults.update(overrides)
        return TokenVerificationResponseContract(**defaults)

    @staticmethod
    def make_token_response(**overrides) -> TokenResponseContract:
        """Generate expected token response"""
        defaults = {
            "success": True,
            "access_token": AuthTestDataFactory.make_jwt_token(),
            "refresh_token": AuthTestDataFactory.make_refresh_token(),
            "token_type": "Bearer",
            "expires_in": 3600,
            "user_id": AuthTestDataFactory.make_user_id(),
            "email": AuthTestDataFactory.make_email(),
            "provider": "isa_user",
            "error": None
        }
        defaults.update(overrides)
        return TokenResponseContract(**defaults)

    @staticmethod
    def make_registration_start_response(**overrides) -> RegistrationStartResponseContract:
        """Generate expected registration start response"""
        defaults = {
            "pending_registration_id": AuthTestDataFactory.make_pending_registration_id(),
            "verification_required": True,
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
        }
        defaults.update(overrides)
        return RegistrationStartResponseContract(**defaults)

    @staticmethod
    def make_registration_verify_response(**overrides) -> RegistrationVerifyResponseContract:
        """Generate expected registration verify response"""
        defaults = {
            "success": True,
            "user_id": AuthTestDataFactory.make_user_id(),
            "email": AuthTestDataFactory.make_email(),
            "access_token": AuthTestDataFactory.make_jwt_token(),
            "refresh_token": AuthTestDataFactory.make_refresh_token(),
            "token_type": "Bearer",
            "expires_in": 3600,
            "error": None
        }
        defaults.update(overrides)
        return RegistrationVerifyResponseContract(**defaults)

    # ========================================================================
    # Invalid data generators (15+ methods)
    # ========================================================================

    @staticmethod
    def make_invalid_email() -> str:
        """Generate invalid email"""
        return "not-an-email"

    @staticmethod
    def make_invalid_password() -> str:
        """Generate invalid password (too short)"""
        return "short"

    @staticmethod
    def make_invalid_token() -> str:
        """Generate invalid JWT token"""
        return "invalid.token.format"

    @staticmethod
    def make_expired_token() -> str:
        """Generate expired JWT token (mock)"""
        return "expired.token.placeholder"

    @staticmethod
    def make_invalid_verification_code() -> str:
        """Generate invalid verification code (5 digits instead of 6)"""
        return "99999"

    @staticmethod
    def make_invalid_verification_code_alpha() -> str:
        """Generate invalid verification code (contains letters)"""
        return "12345A"

    @staticmethod
    def make_invalid_api_key() -> str:
        """Generate invalid API key"""
        return "invalid_key_format"

    @staticmethod
    def make_invalid_device_secret() -> str:
        """Generate invalid device secret (too short)"""
        return "short"

    @staticmethod
    def make_empty_permissions() -> List[str]:
        """Generate empty permissions list"""
        return []

    @staticmethod
    def make_invalid_expires_in() -> int:
        """Generate invalid expires_in (negative)"""
        return -1

    @staticmethod
    def make_invalid_expires_in_too_large() -> int:
        """Generate invalid expires_in (exceeds max)"""
        return 90000  # > 86400 (24 hours)

    @staticmethod
    def make_invalid_expires_days() -> int:
        """Generate invalid expires_days (too large)"""
        return 400  # > 365

    @staticmethod
    def make_invalid_expires_days_negative() -> int:
        """Generate invalid expires_days (negative)"""
        return -10

    @staticmethod
    def make_empty_user_id() -> str:
        """Generate empty user ID"""
        return ""

    @staticmethod
    def make_empty_organization_id() -> str:
        """Generate empty organization ID"""
        return ""

    @staticmethod
    def make_empty_device_id() -> str:
        """Generate empty device ID"""
        return ""

    @staticmethod
    def make_malformed_token() -> str:
        """Generate malformed token (missing parts)"""
        return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"  # Only header

    @staticmethod
    def make_invalid_subscription_level() -> str:
        """Generate invalid subscription level"""
        return "platinum"  # Not in [free, basic, pro, enterprise]

    @staticmethod
    def make_invalid_provider() -> str:
        """Generate invalid provider"""
        return "unknown_provider"

    @staticmethod
    def make_invalid_device_type() -> str:
        """Generate invalid device type"""
        return "quantum_computer"


# ============================================================================
# Request Builders (3 builders)
# ============================================================================

class TokenPairRequestBuilder:
    """Builder for token pair requests"""

    def __init__(self):
        self._user_id = AuthTestDataFactory.make_user_id()
        self._email = AuthTestDataFactory.make_email()
        self._organization_id = AuthTestDataFactory.make_organization_id()
        self._permissions = AuthTestDataFactory.make_permissions()
        self._metadata = {}

    def with_user_id(self, user_id: str) -> 'TokenPairRequestBuilder':
        """Set user ID"""
        self._user_id = user_id
        return self

    def with_email(self, email: str) -> 'TokenPairRequestBuilder':
        """Set email"""
        self._email = email
        return self

    def with_organization_id(self, org_id: str) -> 'TokenPairRequestBuilder':
        """Set organization ID"""
        self._organization_id = org_id
        return self

    def with_permissions(self, permissions: List[str]) -> 'TokenPairRequestBuilder':
        """Set permissions"""
        self._permissions = permissions
        return self

    def with_metadata(self, metadata: Dict[str, Any]) -> 'TokenPairRequestBuilder':
        """Set metadata"""
        self._metadata = metadata
        return self

    def with_metadata_field(self, key: str, value: Any) -> 'TokenPairRequestBuilder':
        """Add single metadata field"""
        self._metadata[key] = value
        return self

    def build(self) -> TokenPairRequestContract:
        """Build the final request"""
        return TokenPairRequestContract(
            user_id=self._user_id,
            email=self._email,
            organization_id=self._organization_id,
            permissions=self._permissions,
            metadata=self._metadata if self._metadata else None
        )


class DeviceRegisterRequestBuilder:
    """Builder for device register requests"""

    def __init__(self):
        self._device_id = AuthTestDataFactory.make_device_id()
        self._organization_id = AuthTestDataFactory.make_organization_id()
        self._device_name = AuthTestDataFactory.make_device_name()
        self._device_type = AuthTestDataFactory.make_device_type()
        self._metadata = {}

    def with_device_id(self, device_id: str) -> 'DeviceRegisterRequestBuilder':
        """Set device ID"""
        self._device_id = device_id
        return self

    def with_organization_id(self, org_id: str) -> 'DeviceRegisterRequestBuilder':
        """Set organization ID"""
        self._organization_id = org_id
        return self

    def with_device_name(self, name: str) -> 'DeviceRegisterRequestBuilder':
        """Set device name"""
        self._device_name = name
        return self

    def with_device_type(self, device_type: str) -> 'DeviceRegisterRequestBuilder':
        """Set device type"""
        self._device_type = device_type
        return self

    def with_metadata(self, metadata: Dict[str, Any]) -> 'DeviceRegisterRequestBuilder':
        """Set metadata"""
        self._metadata = metadata
        return self

    def with_metadata_field(self, key: str, value: Any) -> 'DeviceRegisterRequestBuilder':
        """Add single metadata field"""
        self._metadata[key] = value
        return self

    def with_location(self, location: str) -> 'DeviceRegisterRequestBuilder':
        """Set location metadata"""
        self._metadata["location"] = location
        return self

    def with_firmware(self, firmware: str) -> 'DeviceRegisterRequestBuilder':
        """Set firmware metadata"""
        self._metadata["firmware"] = firmware
        return self

    def build(self) -> DeviceRegisterRequestContract:
        """Build the final request"""
        return DeviceRegisterRequestContract(
            device_id=self._device_id,
            organization_id=self._organization_id,
            device_name=self._device_name,
            device_type=self._device_type,
            metadata=self._metadata if self._metadata else {}
        )


class ApiKeyCreateRequestBuilder:
    """Builder for API key create requests"""

    def __init__(self):
        self._organization_id = AuthTestDataFactory.make_organization_id()
        self._name = AuthTestDataFactory.make_api_key_name()
        self._permissions = AuthTestDataFactory.make_permissions()
        self._expires_days = 90

    def with_organization_id(self, org_id: str) -> 'ApiKeyCreateRequestBuilder':
        """Set organization ID"""
        self._organization_id = org_id
        return self

    def with_name(self, name: str) -> 'ApiKeyCreateRequestBuilder':
        """Set key name"""
        self._name = name
        return self

    def with_permissions(self, permissions: List[str]) -> 'ApiKeyCreateRequestBuilder':
        """Set permissions"""
        self._permissions = permissions
        return self

    def with_read_permissions(self) -> 'ApiKeyCreateRequestBuilder':
        """Set read-only permissions"""
        self._permissions = ["read:data", "read:users"]
        return self

    def with_write_permissions(self) -> 'ApiKeyCreateRequestBuilder':
        """Set read-write permissions"""
        self._permissions = ["read:data", "write:data", "read:users", "write:users"]
        return self

    def with_admin_permissions(self) -> 'ApiKeyCreateRequestBuilder':
        """Set admin permissions"""
        self._permissions = ["admin:all"]
        return self

    def with_expires_days(self, days: int) -> 'ApiKeyCreateRequestBuilder':
        """Set expiration days"""
        self._expires_days = days
        return self

    def with_no_expiration(self) -> 'ApiKeyCreateRequestBuilder':
        """Set no expiration"""
        self._expires_days = None
        return self

    def build(self) -> ApiKeyCreateRequestContract:
        """Build the final request"""
        return ApiKeyCreateRequestContract(
            organization_id=self._organization_id,
            name=self._name,
            permissions=self._permissions if self._permissions else [],
            expires_days=self._expires_days
        )


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Request Contracts
    "TokenVerificationRequestContract",
    "DevTokenRequestContract",
    "TokenPairRequestContract",
    "RefreshTokenRequestContract",
    "RegistrationStartRequestContract",
    "RegistrationVerifyRequestContract",
    "ApiKeyCreateRequestContract",
    "ApiKeyVerifyRequestContract",
    "DeviceRegisterRequestContract",
    "DeviceAuthenticateRequestContract",
    "DevicePairingGenerateRequestContract",
    "DevicePairingVerifyRequestContract",

    # Response Contracts
    "TokenVerificationResponseContract",
    "TokenResponseContract",
    "RegistrationStartResponseContract",
    "RegistrationVerifyResponseContract",
    "ApiKeyCreateResponseContract",
    "ApiKeyVerifyResponseContract",
    "DeviceRegisterResponseContract",
    "DeviceAuthenticateResponseContract",
    "DevicePairingResponseContract",
    "UserInfoResponseContract",

    # Factory
    "AuthTestDataFactory",

    # Builders
    "TokenPairRequestBuilder",
    "DeviceRegisterRequestBuilder",
    "ApiKeyCreateRequestBuilder",
]
