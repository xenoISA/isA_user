"""
Authentication Microservice

Responsibilities:
- JWT Token verification (Auth0, isA_user custom JWT)
- API Key verification and management
- Token generation (access & refresh tokens)
- Identity authentication
- Device authentication

Uses custom self-issued JWT tokens (isA_user provider) as primary authentication method.

Note: Authorization/permission control is handled by separate Authorization microservice
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime, timezone, timedelta

# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

# FastAPI imports
from fastapi import FastAPI, HTTPException, Depends, status, Query, Form, Security
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# 导入新实现的服务
# Import isa-common Consul client for service registration and discovery
from isa_common.consul_client import ConsulRegistry

# Database connection now handled by repositories directly
from core.config_manager import ConfigManager
from core.logger import setup_service_logger
from core.nats_client import NATSEventBus, get_event_bus

from .api_key_repository import ApiKeyRepository
from .api_key_service import ApiKeyService
from .auth_repository import AuthRepository
from .auth_service import AuthenticationService
from .device_auth_repository import DeviceAuthRepository
from .device_auth_service import DeviceAuthService
from .oauth_client_repository import OAuthClientRepository

# Import route registry for Consul metadata
from .routes_registry import SERVICE_METADATA, get_routes_for_consul

# 初始化配置
config_manager = ConfigManager("auth_service")
config = config_manager.get_service_config()

# Setup loggers (use actual service name)
app_logger = setup_service_logger("auth_service")
logger = app_logger  # for backward compatibility

# Request/Response Models


class TokenVerificationRequest(BaseModel):
    """Token verification request"""

    token: str = Field(..., description="JWT token")
    provider: Optional[str] = Field(
        None, description="Provider: auth0, isa_user, local"
    )


class TokenVerificationResponse(BaseModel):
    """Token verification response"""

    valid: bool
    provider: Optional[str] = None
    user_id: Optional[str] = None
    email: Optional[str] = None
    subscription_level: Optional[str] = None
    organization_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    error: Optional[str] = None


class ApiKeyVerificationRequest(BaseModel):
    """API key verification request"""

    api_key: str = Field(..., description="API key")


class ApiKeyVerificationResponse(BaseModel):
    """API key verification response"""

    valid: bool
    key_id: Optional[str] = None
    organization_id: Optional[str] = None
    name: Optional[str] = None
    permissions: Optional[List[str]] = []
    error: Optional[str] = None


class DevTokenRequest(BaseModel):
    """Development token generation request"""

    user_id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    expires_in: int = Field(3600, description="Expiration time in seconds")
    subscription_level: Optional[str] = Field(
        "free", description="User subscription level (free, basic, pro, enterprise)"
    )
    organization_id: Optional[str] = Field(None, description="Organization ID")
    permissions: Optional[List[str]] = Field(None, description="Permission list")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class TokenPairRequest(BaseModel):
    """Token pair generation request (access + refresh)"""

    user_id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    permissions: Optional[List[str]] = Field(None, description="Permission list")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""

    refresh_token: str = Field(..., description="Refresh token")


class OAuthClientCreateRequest(BaseModel):
    """OAuth client creation request"""

    client_name: str = Field(..., description="Human-readable client name")
    organization_id: Optional[str] = Field(None, description="Owning organization ID")
    allowed_scopes: List[str] = Field(
        default=["a2a.invoke"],
        description="Allowed OAuth scopes for this client",
    )
    token_ttl_seconds: int = Field(
        3600, ge=300, le=86400, description="Access token TTL in seconds"
    )


class ApiKeyCreateRequest(BaseModel):
    """API key creation request"""

    organization_id: str = Field(..., description="Organization ID")
    name: str = Field(..., description="Key name")
    permissions: List[str] = Field(default=[], description="Permission list")
    expires_days: Optional[int] = Field(None, description="Expiration days")


class DeviceRegistrationRequest(BaseModel):
    """Device registration request"""

    device_id: str = Field(..., description="Device ID")
    organization_id: str = Field(..., description="Organization ID")
    device_name: Optional[str] = Field(None, description="Device name")
    device_type: Optional[str] = Field(None, description="Device type")
    metadata: Optional[Dict[str, Any]] = Field(
        default={}, description="Device metadata"
    )
    expires_days: Optional[int] = Field(None, description="Credential expiration days")


class DeviceAuthRequest(BaseModel):
    """Device authentication request"""

    device_id: str = Field(..., description="Device ID")
    device_secret: str = Field(..., description="Device secret")


class DeviceTokenVerificationRequest(BaseModel):
    """Device token verification request"""

    token: str = Field(..., description="Device JWT token")


# ================================
# Registration Models
# ================================


class RegistrationRequest(BaseModel):
    """User registration request (email + password)"""

    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")
    name: Optional[str] = Field(None, description="Display name")


class RegistrationStartResponse(BaseModel):
    """Registration start response"""

    pending_registration_id: str
    verification_required: bool = True
    expires_at: str


class RegistrationVerifyRequest(BaseModel):
    """Verify registration code"""

    pending_registration_id: str = Field(..., description="Pending registration ID")
    code: str = Field(..., description="Verification code")


class RegistrationVerifyResponse(BaseModel):
    success: bool
    user_id: Optional[str] = None
    email: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: Optional[str] = None
    expires_in: Optional[int] = None
    error: Optional[str] = None


# ================================
# Login Models
# ================================


class LoginRequest(BaseModel):
    """User login request (email + password)"""

    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")
    organization_id: Optional[str] = Field(None, description="Organization context")


class LoginResponse(BaseModel):
    """Login response"""

    success: bool
    user_id: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: Optional[str] = None
    expires_in: Optional[int] = None
    error: Optional[str] = None


# ================================
# 服务核心类
# ================================


class AuthMicroservice:
    """认证微服务核心类"""

    def __init__(self):
        self.auth_service = None
        self.api_key_service = None
        self.api_key_repository = None
        self.oauth_client_repository = None
        self.auth_repository = None
        self.device_auth_service = None
        self.device_auth_repository = None
        self.event_bus: Optional[NATSEventBus] = None
        self.organization_service_client = None
        self.consul_registry: Optional[ConsulRegistry] = None

    async def initialize(self):
        """初始化服务"""
        try:
            logger.info("Initializing authentication microservice...")

            # Initialize Consul service registration and discovery
            if config.consul_enabled:
                try:
                    # Get route metadata from registry
                    route_meta = get_routes_for_consul()

                    # Merge with service metadata
                    consul_meta = {
                        "version": SERVICE_METADATA["version"],
                        "capabilities": ",".join(SERVICE_METADATA["capabilities"]),
                        **route_meta,
                    }

                    self.consul_registry = ConsulRegistry(
                        service_name=SERVICE_METADATA["service_name"],
                        service_port=config.service_port,
                        consul_host=config.consul_host,
                        consul_port=config.consul_port,
                        tags=SERVICE_METADATA["tags"],
                        meta=consul_meta,
                        health_check_type="ttl"  # Use TTL for reliable health checks,
                    )
                    self.consul_registry.register()
                    self.consul_registry.start_maintenance()  # Start TTL heartbeat
            # Start TTL heartbeat - added for consistency with isA_Model
                    logger.info(
                        f"Service registered with Consul: {len(route_meta.get('all_routes', '').split('|'))} routes registered"
                    )
                    logger.info(
                        f"Consul address: {config.consul_host}:{config.consul_port}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to register with Consul: {e}. Continuing without service registration."
                    )
                    self.consul_registry = None
            else:
                logger.info("Consul service registration disabled")

            # Initialize event bus for event-driven communication
            try:
                self.event_bus = await get_event_bus("auth_service")
                logger.info("Event bus initialized successfully")
            except Exception as e:
                logger.warning(
                    f"Failed to initialize event bus: {e}. Continuing without event publishing."
                )
                self.event_bus = None

            # Initialize organization service client for microservice communication
            try:
                from clients import OrganizationServiceClient


                self.organization_service_client = OrganizationServiceClient()
                logger.info("Organization service client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize organization service client: {e}")
                self.organization_service_client = None

            # 初始化repository (they now handle their own connections with service discovery)
            self.api_key_repository = ApiKeyRepository(
                organization_service_client=self.organization_service_client,
                config=config_manager,
            )
            self.oauth_client_repository = OAuthClientRepository(config=config_manager)
            self.auth_repository = AuthRepository(config=config_manager)
            self.device_auth_repository = DeviceAuthRepository(
                organization_service_client=self.organization_service_client,
                config=config_manager,
            )

            # Initialize services using factory pattern
            from .factory import create_auth_service

            self.auth_service = create_auth_service(
                config=config_manager, event_bus=self.event_bus
            )
            self.api_key_service = ApiKeyService(self.api_key_repository)
            self.device_auth_service = DeviceAuthService(
                self.device_auth_repository, event_bus=self.event_bus
            )

            logger.info("Authentication microservice initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize authentication microservice: {e}")
            raise

    async def shutdown(self):
        """关闭服务"""
        # Deregister from Consul
        if self.consul_registry:
            try:
                self.consul_registry.deregister()
                logger.info("Service deregistered from Consul")
            except Exception as e:
                logger.error(f"Failed to deregister from Consul: {e}")

        if self.auth_service:
            await self.auth_service.close()
        if self.event_bus:
            await self.event_bus.close()
        if self.organization_service_client:
            await self.organization_service_client.close()
        logger.info("Authentication microservice shutdown completed")


# 全局服务实例
auth_microservice = AuthMicroservice()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    # Initialize microservice
    await auth_microservice.initialize()

    yield

    # Cleanup
    await auth_microservice.shutdown()


# Create FastAPI application
app = FastAPI(
    title="Authentication Microservice",
    description="Pure authentication microservice - JWT verification, API key management",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS middleware - enabled for local development
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3001",
        "http://localhost:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency Injection


def get_auth_service() -> AuthenticationService:
    return auth_microservice.auth_service


def get_api_key_service() -> ApiKeyService:
    return auth_microservice.api_key_service


def get_auth_repository() -> AuthRepository:
    return auth_microservice.auth_repository


def get_device_auth_service() -> DeviceAuthService:
    return auth_microservice.device_auth_service


def get_oauth_client_repository() -> OAuthClientRepository:
    return auth_microservice.oauth_client_repository


bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_caller(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    auth_service: AuthenticationService = Depends(get_auth_service),
) -> Dict[str, Any]:
    """Authenticate caller using bearer token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    result = await auth_service.verify_access_token_for_resource(credentials.credentials)
    if not result.get("valid"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result.get("error", "Invalid token"),
        )

    return result


def _is_admin_caller(caller: Dict[str, Any]) -> bool:
    scope = (caller.get("scope") or "").lower()
    permissions = set(caller.get("permissions") or [])
    return scope == "admin" or "auth.admin" in permissions


async def require_admin_caller(
    caller: Dict[str, Any] = Depends(get_current_caller),
) -> Dict[str, Any]:
    """Require admin permission for sensitive auth operations."""
    if not _is_admin_caller(caller):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permission required",
        )
    return caller


# Health Check Endpoints


@app.get("/")
async def root():
    """Root health check"""
    return {
        "service": "auth_microservice",
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }


@app.get("/health")
async def health_check():
    """Service health check"""
    return {
        "status": "healthy",
        "service": "auth_microservice",
        "port": config.service_port,
        "version": "2.0.0",
        "capabilities": [
            "jwt_verification",
            "api_key_management",
            "token_generation",
            "oauth2_client_credentials",
            "device_authentication",
        ],
        "providers": ["auth0", "isa_user"],
    }


@app.get("/api/v1/auth/health")
async def health_check_alias():
    """Alias for service health check under API prefix"""
    return await health_check()


@app.get("/api/v1/auth/info")
async def get_auth_info():
    """Authentication service information"""
    return {
        "service": "auth_microservice",
        "version": "2.0.0",
        "description": "Pure authentication microservice with custom JWT",
        "capabilities": {
            "jwt_verification": ["auth0", "isa_user"],
            "api_key_management": True,
            "token_generation": True,
            "device_authentication": True,
            "oauth2_client_credentials": True,
        },
        "endpoints": {
            "verify_token": "/api/v1/auth/verify-token",
            "verify_api_key": "/api/v1/auth/verify-api-key",
            "generate_dev_token": "/api/v1/auth/dev-token",
            "manage_api_keys": "/api/v1/auth/api-keys",
            "oauth_token": "/oauth/token",
            "oauth_clients": "/api/v1/auth/oauth/clients",
        },
    }


# JWT Token Authentication Endpoints


@app.post("/api/v1/auth/verify-token", response_model=TokenVerificationResponse)
async def verify_token(
    request: TokenVerificationRequest,
    auth_service: AuthenticationService = Depends(get_auth_service),
):
    """Verify JWT Token"""
    try:
        result = await auth_service.verify_token(
            token=request.token, provider=request.provider
        )

        # Extract subscription_level from metadata if present
        metadata = result.get("metadata", {})
        subscription_level = (
            metadata.get("subscription_level") if isinstance(metadata, dict) else None
        )

        return TokenVerificationResponse(
            valid=result.get("valid", False),
            provider=result.get("provider"),
            user_id=result.get("user_id"),
            email=result.get("email"),
            subscription_level=subscription_level,
            organization_id=result.get("organization_id"),
            expires_at=result.get("expires_at"),
            error=result.get("error") if not result.get("valid") else None,
        )
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        return TokenVerificationResponse(
            valid=False, error=f"Verification failed: {str(e)}"
        )


# Registration Endpoints


@app.post("/oauth/token")
async def oauth_token(
    grant_type: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...),
    scope: Optional[str] = Form(None),
    auth_service: AuthenticationService = Depends(get_auth_service),
):
    """OAuth2 client credentials token endpoint."""
    if grant_type != "client_credentials":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="unsupported_grant_type",
        )

    result = await auth_service.issue_client_credentials_token(
        client_id=client_id,
        client_secret=client_secret,
        scope=scope,
    )
    if not result.get("success"):
        error_code = result.get("error_code", "invalid_client")
        status_code = (
            status.HTTP_401_UNAUTHORIZED if error_code == "invalid_client" else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=error_code)

    return {
        "access_token": result["access_token"],
        "token_type": result["token_type"],
        "expires_in": result["expires_in"],
        "scope": result.get("scope", ""),
    }


@app.post("/api/v1/auth/oauth/clients")
async def create_oauth_client(
    request: OAuthClientCreateRequest,
    oauth_repo: OAuthClientRepository = Depends(get_oauth_client_repository),
    caller: Dict[str, Any] = Depends(require_admin_caller),
):
    """Create OAuth client credentials for machine-to-machine calls."""
    result = await oauth_repo.create_client(
        client_name=request.client_name,
        organization_id=request.organization_id or caller.get("organization_id"),
        allowed_scopes=request.allowed_scopes,
        token_ttl_seconds=request.token_ttl_seconds,
        created_by=caller.get("user_id"),
    )
    return {
        "success": True,
        "client_id": result["client_id"],
        "client_secret": result["client_secret"],
        "client_name": result["client_name"],
        "organization_id": result["organization_id"],
        "allowed_scopes": result["allowed_scopes"],
        "token_ttl_seconds": result["token_ttl_seconds"],
        "created_at": result["created_at"],
    }


@app.get("/api/v1/auth/oauth/clients")
async def list_oauth_clients(
    organization_id: Optional[str] = Query(None, description="Filter by organization"),
    oauth_repo: OAuthClientRepository = Depends(get_oauth_client_repository),
    caller: Dict[str, Any] = Depends(require_admin_caller),
):
    """List OAuth clients."""
    org_filter = organization_id or caller.get("organization_id")
    clients = await oauth_repo.list_clients(org_filter)
    return {"success": True, "clients": clients, "total": len(clients)}


@app.get("/api/v1/auth/oauth/clients/{client_id}")
async def get_oauth_client(
    client_id: str,
    oauth_repo: OAuthClientRepository = Depends(get_oauth_client_repository),
    _caller: Dict[str, Any] = Depends(require_admin_caller),
):
    """Get OAuth client metadata."""
    client = await oauth_repo.get_client(client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return {"success": True, "client": client}


@app.post("/api/v1/auth/oauth/clients/{client_id}/rotate-secret")
async def rotate_oauth_client_secret(
    client_id: str,
    oauth_repo: OAuthClientRepository = Depends(get_oauth_client_repository),
    _caller: Dict[str, Any] = Depends(require_admin_caller),
):
    """Rotate OAuth client secret."""
    rotated = await oauth_repo.rotate_client_secret(client_id)
    if not rotated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return {
        "success": True,
        "client_id": rotated["client_id"],
        "client_secret": rotated["client_secret"],
        "rotated_at": rotated["rotated_at"],
    }


@app.delete("/api/v1/auth/oauth/clients/{client_id}")
async def deactivate_oauth_client(
    client_id: str,
    oauth_repo: OAuthClientRepository = Depends(get_oauth_client_repository),
    _caller: Dict[str, Any] = Depends(require_admin_caller),
):
    """Deactivate OAuth client."""
    success = await oauth_repo.deactivate_client(client_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return {"success": True, "client_id": client_id}


@app.post("/api/v1/auth/register", response_model=RegistrationStartResponse)
async def register(
    request: RegistrationRequest,
    auth_service: AuthenticationService = Depends(get_auth_service),
):
    """Start user registration (email + password).

    Example:
    {
      "email": "a@b.com",
      "password": "Strong#123",
      "name": "Alice"
    }
    """
    try:
        result = await auth_service.start_registration(
            email=request.email, password=request.password, name=request.name
        )
        return RegistrationStartResponse(**result)
    except Exception as e:
        logger.error(f"Registration start failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        )


@app.post("/api/v1/auth/verify", response_model=RegistrationVerifyResponse)
async def verify_registration(
    request: RegistrationVerifyRequest,
    auth_service: AuthenticationService = Depends(get_auth_service),
):
    """Verify registration code and create account.

    Example:
    {
      "pending_registration_id": "<id>",
      "code": "123456"
    }
    """
    try:
        result = await auth_service.verify_registration(
            pending_registration_id=request.pending_registration_id, code=request.code
        )
        if not result.get("success"):
            return RegistrationVerifyResponse(success=False, error=result.get("error"))
        return RegistrationVerifyResponse(
            success=True,
            user_id=result.get("user_id"),
            email=result.get("email"),
            access_token=result.get("access_token"),
            refresh_token=result.get("refresh_token"),
            token_type=result.get("token_type"),
            expires_in=result.get("expires_in"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Verification failed",
        )


# Login Endpoint


@app.post("/api/v1/auth/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    auth_service: AuthenticationService = Depends(get_auth_service),
):
    """Authenticate user with email and password.

    Example:
    {
      "email": "user@example.com",
      "password": "your_password"
    }

    Returns access and refresh tokens on success.
    """
    try:
        result = await auth_service.login(
            email=request.email,
            password=request.password,
            organization_id=request.organization_id,
        )

        if not result.get("success"):
            # Return 401 for invalid credentials
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=result.get("error", "Authentication failed"),
            )

        return LoginResponse(
            success=True,
            user_id=result.get("user_id"),
            email=result.get("email"),
            name=result.get("name"),
            access_token=result.get("access_token"),
            refresh_token=result.get("refresh_token"),
            token_type=result.get("token_type"),
            expires_in=result.get("expires_in"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed",
        )


@app.post("/api/v1/auth/dev-token")
async def generate_dev_token(
    request: DevTokenRequest,
    auth_service: AuthenticationService = Depends(get_auth_service),
    _caller: Dict[str, Any] = Depends(require_admin_caller),
):
    """Generate development token (access token only)"""
    try:
        # Include subscription_level in metadata
        metadata = request.metadata or {}
        metadata["subscription_level"] = request.subscription_level

        result = await auth_service.generate_dev_token(
            user_id=request.user_id,
            email=request.email,
            expires_in=request.expires_in,
            organization_id=request.organization_id,
            permissions=request.permissions,
            metadata=metadata,
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Token generation failed"),
            )

        return {
            "success": True,
            "token": result["token"],
            "expires_in": result["expires_in"],
            "token_type": result.get("token_type", "Bearer"),
            "user_id": result["user_id"],
            "email": result["email"],
            "provider": result.get("provider", "isa_user"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Dev token generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token generation failed",
        )


@app.post("/api/v1/auth/token-pair")
async def generate_token_pair(
    request: TokenPairRequest,
    auth_service: AuthenticationService = Depends(get_auth_service),
    _caller: Dict[str, Any] = Depends(require_admin_caller),
):
    """Generate token pair (access + refresh tokens)"""
    try:
        result = await auth_service.generate_token_pair(
            user_id=request.user_id,
            email=request.email,
            organization_id=request.organization_id,
            permissions=request.permissions,
            metadata=request.metadata,
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Token pair generation failed"),
            )

        return {
            "success": True,
            "access_token": result["access_token"],
            "refresh_token": result["refresh_token"],
            "token_type": result["token_type"],
            "expires_in": result["expires_in"],
            "user_id": result["user_id"],
            "email": result["email"],
            "provider": result.get("provider", "isa_user"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token pair generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token pair generation failed",
        )


@app.post("/api/v1/auth/refresh")
async def refresh_token(
    request: RefreshTokenRequest,
    auth_service: AuthenticationService = Depends(get_auth_service),
):
    """Refresh access token using refresh token"""
    try:
        result = await auth_service.refresh_access_token(request.refresh_token)

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=result.get("error", "Token refresh failed"),
            )

        return {
            "success": True,
            "access_token": result["access_token"],
            "token_type": result["token_type"],
            "expires_in": result["expires_in"],
            "provider": result.get("provider", "isa_user"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed",
        )


@app.get("/api/v1/auth/user-info")
async def get_user_info_from_token(
    token: str = Query(..., description="JWT token to extract user info from"),
    auth_service: AuthenticationService = Depends(get_auth_service),
):
    """Extract user information from token"""
    try:
        result = await auth_service.get_user_info_from_token(token)

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=result.get("error", "Invalid token"),
            )

        # Convert datetime to ISO format if needed
        expires_at = result.get("expires_at")
        if expires_at and isinstance(expires_at, datetime):
            expires_at = expires_at.isoformat()

        return {
            "user_id": result.get("user_id"),
            "email": result.get("email"),
            "provider": result.get("provider"),
            "expires_at": expires_at,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User info extraction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"User info extraction failed: {str(e)}",
        )


# API Key Management Endpoints


@app.post("/api/v1/auth/verify-api-key", response_model=ApiKeyVerificationResponse)
async def verify_api_key(
    request: ApiKeyVerificationRequest,
    api_key_service: ApiKeyService = Depends(get_api_key_service),
):
    """Verify API key"""
    try:
        result = await api_key_service.verify_api_key(request.api_key)

        return ApiKeyVerificationResponse(
            valid=result.get("valid", False),
            key_id=result.get("key_id"),
            organization_id=result.get("organization_id"),
            name=result.get("name"),
            permissions=result.get("permissions", []),
            error=result.get("error") if not result.get("valid") else None,
        )

    except Exception as e:
        logger.error(f"API key verification failed: {e}")
        return ApiKeyVerificationResponse(
            valid=False, error=f"Verification failed: {str(e)}"
        )


@app.post("/api/v1/auth/api-keys")
async def create_api_key(
    request: ApiKeyCreateRequest,
    api_key_service: ApiKeyService = Depends(get_api_key_service),
    _caller: Dict[str, Any] = Depends(require_admin_caller),
):
    """Create API key"""
    try:
        result = await api_key_service.create_api_key(
            organization_id=request.organization_id,
            name=request.name,
            permissions=request.permissions,
            expires_days=request.expires_days,
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to create API key"),
            )

        return {
            "success": True,
            "api_key": result["api_key"],
            "key_id": result["key_id"],
            "name": result["name"],
            "expires_at": result["expires_at"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API key creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key creation failed",
        )


@app.get("/api/v1/auth/api-keys/{organization_id}")
async def list_api_keys(
    organization_id: str,
    api_key_service: ApiKeyService = Depends(get_api_key_service),
    _caller: Dict[str, Any] = Depends(require_admin_caller),
):
    """List organization API keys"""
    try:
        result = await api_key_service.list_api_keys(organization_id)

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to list API keys"),
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API keys listing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API keys listing failed",
        )


@app.delete("/api/v1/auth/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    organization_id: str,
    api_key_service: ApiKeyService = Depends(get_api_key_service),
    _caller: Dict[str, Any] = Depends(require_admin_caller),
):
    """Revoke API key"""
    try:
        result = await api_key_service.revoke_api_key(key_id, organization_id)

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to revoke API key"),
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API key revocation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key revocation failed",
        )


# Device Authentication Endpoints


@app.post("/api/v1/auth/device/register")
async def register_device(
    request: DeviceRegistrationRequest,
    device_auth_service: DeviceAuthService = Depends(get_device_auth_service),
    _caller: Dict[str, Any] = Depends(require_admin_caller),
):
    """Register a new device and get credentials"""
    try:
        # 准备设备数据
        device_data = request.model_dump()

        # 如果指定了过期天数，计算过期时间
        if device_data.get("expires_days"):
            expires_at = datetime.now(timezone.utc) + timedelta(
                days=device_data["expires_days"]
            )
            device_data["expires_at"] = expires_at.isoformat()  # Convert to ISO string
            del device_data["expires_days"]

        result = await device_auth_service.register_device(device_data)

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to register device"),
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Device registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Device registration failed",
        )


@app.post("/api/v1/auth/device/authenticate")
async def authenticate_device(
    request: DeviceAuthRequest,
    device_auth_service: DeviceAuthService = Depends(get_device_auth_service),
):
    """Authenticate a device and get access token"""
    try:
        result = await device_auth_service.authenticate_device(
            device_id=request.device_id, device_secret=request.device_secret
        )

        if not result.get("authenticated"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=result.get("error", "Authentication failed"),
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Device authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Device authentication failed",
        )


@app.post("/api/v1/auth/device/verify-token")
async def verify_device_token(
    request: DeviceTokenVerificationRequest,
    device_auth_service: DeviceAuthService = Depends(get_device_auth_service),
):
    """Verify a device JWT token"""
    try:
        result = await device_auth_service.verify_device_token(request.token)
        return result

    except Exception as e:
        logger.error(f"Device token verification failed: {e}")
        return {"valid": False, "error": str(e)}


@app.post("/api/v1/auth/device/{device_id}/refresh-secret")
async def refresh_device_secret(
    device_id: str,
    organization_id: str = Query(..., description="Organization ID"),
    device_auth_service: DeviceAuthService = Depends(get_device_auth_service),
    _caller: Dict[str, Any] = Depends(require_admin_caller),
):
    """Refresh device secret"""
    try:
        result = await device_auth_service.refresh_device_secret(
            device_id, organization_id
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to refresh secret"),
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Device secret refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Device secret refresh failed",
        )


@app.delete("/api/v1/auth/device/{device_id}")
async def revoke_device(
    device_id: str,
    organization_id: str = Query(..., description="Organization ID"),
    device_auth_service: DeviceAuthService = Depends(get_device_auth_service),
    _caller: Dict[str, Any] = Depends(require_admin_caller),
):
    """Revoke device credentials"""
    try:
        result = await device_auth_service.revoke_device(device_id, organization_id)

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to revoke device"),
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Device revocation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Device revocation failed",
        )


@app.get("/api/v1/auth/device/list")
async def list_devices(
    organization_id: str = Query(..., description="Organization ID"),
    device_auth_service: DeviceAuthService = Depends(get_device_auth_service),
    _caller: Dict[str, Any] = Depends(require_admin_caller),
):
    """List all devices for an organization"""
    try:
        result = await device_auth_service.list_devices(organization_id)

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to list devices"),
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Device listing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Device listing failed",
        )


# ============================================================================
# Admin Bootstrap Endpoint
# ============================================================================

ADMIN_BOOTSTRAP_SECRET = os.getenv(
    "ADMIN_BOOTSTRAP_SECRET", "dev-bootstrap-secret-change-in-production"
)


class AdminBootstrapRequest(BaseModel):
    """Admin bootstrap request"""
    user_id: str = Field(..., description="User ID to grant admin privileges")
    bootstrap_secret: str = Field(..., description="Bootstrap secret for authorization")


@app.post("/api/v1/auth/admin/bootstrap")
async def admin_bootstrap(
    request: AdminBootstrapRequest,
    auth_service: AuthenticationService = Depends(get_auth_service),
):
    """Bootstrap the first admin user.

    Protected by ADMIN_BOOTSTRAP_SECRET env var. Generates admin-scoped JWT tokens.
    """
    if request.bootstrap_secret != ADMIN_BOOTSTRAP_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid bootstrap secret",
        )

    try:
        result = await auth_service.generate_token_pair(
            user_id=request.user_id,
            email=f"{request.user_id}@admin.local",
            permissions=["auth.admin"],
            metadata={"scope": "admin", "bootstrap": True},
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Token generation failed"),
            )

        return {
            "success": True,
            "access_token": result["access_token"],
            "refresh_token": result["refresh_token"],
            "token_type": result["token_type"],
            "expires_in": result["expires_in"],
            "user_id": request.user_id,
            "scope": "admin",
            "permissions": ["auth.admin"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin bootstrap failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin bootstrap failed",
        )


# Service Statistics


@app.get("/api/v1/auth/stats")
async def get_auth_stats():
    """Get authentication service statistics"""
    return {
        "service": "auth_microservice",
        "version": "2.0.0",
        "status": "operational",
        "capabilities": {
            "jwt_providers": ["auth0", "isa_user"],
            "api_key_management": True,
            "token_generation": True,
            "oauth2_client_credentials": True,
            "device_authentication": True,
        },
        "stats": {"uptime": "running", "endpoints_count": 8},
    }


# Development/Testing Endpoints


@app.get("/api/v1/auth/dev/pending-registration/{pending_id}")
async def get_pending_registration(
    pending_id: str, auth_service: AuthenticationService = Depends(get_auth_service)
):
    """Development endpoint: Get pending registration info (including verification code)

    WARNING: This endpoint should only be enabled in development/test environments.
    It exposes the verification code which should be kept secret in production.
    """
    # Check if we're in development mode
    if not config.debug:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available in debug mode",
        )

    # Access the internal pending registrations (for testing only)
    if hasattr(auth_service, "_pending_registrations"):
        record = auth_service._pending_registrations.get(pending_id)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pending registration not found",
            )

        # Check if expired
        if record["expires_at"] < datetime.now(timezone.utc):
            return {
                "found": True,
                "expired": True,
                "expires_at": record["expires_at"].isoformat(),
            }

        return {
            "found": True,
            "expired": False,
            "email": record["email"],
            "verification_code": record["code"],
            "expires_at": record["expires_at"].isoformat(),
            "verified": record.get("verified", False),
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Pending registrations store not available",
        )


# Startup Configuration

if __name__ == "__main__":
    uvicorn.run(
        "microservices.auth_service.main:app",
        host=config.service_host,
        port=config.service_port,
        reload=config.debug,
        log_level=config.log_level.lower(),
    )

# ============================================================================
# Pairing Token Models (add after RegistrationVerifyResponse)
# ============================================================================


class PairingTokenGenerateResponse(BaseModel):
    success: bool
    pairing_token: Optional[str] = None
    expires_at: Optional[str] = None
    expires_in: Optional[int] = None
    error: Optional[str] = None


class PairingTokenVerifyRequest(BaseModel):
    device_id: str
    pairing_token: str
    user_id: str


class PairingTokenVerifyResponse(BaseModel):
    valid: bool
    device_id: Optional[str] = None
    user_id: Optional[str] = None
    error: Optional[str] = None


# ============================================================================
# Device Pairing Token APIs
# ============================================================================


@app.post(
    "/api/v1/auth/device/{device_id}/pairing-token",
    response_model=PairingTokenGenerateResponse,
)
async def generate_pairing_token(
    device_id: str,
    device_auth_service: DeviceAuthService = Depends(get_device_auth_service),
):
    """
    Generate a temporary pairing token for device-user pairing

    Called by Display device (EmoFrame tablet) to generate QR code
    """
    try:
        result = await device_auth_service.generate_pairing_token(device_id)

        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to generate pairing token"),
            )

        return PairingTokenGenerateResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating pairing token: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/api/v1/auth/device/pairing-token/verify",
    response_model=PairingTokenVerifyResponse,
)
async def verify_pairing_token_endpoint(
    request: PairingTokenVerifyRequest,
    device_auth_service: DeviceAuthService = Depends(get_device_auth_service),
):
    """
    Verify device pairing token

    Called by device_service when mobile user scans QR code
    """
    try:
        result = await device_auth_service.verify_pairing_token(
            device_id=request.device_id,
            pairing_token=request.pairing_token,
            user_id=request.user_id,
        )

        # Publish pairing completed event if successful
        if result.get("valid"):
            try:
                event_bus = (
                    app.state.event_bus if hasattr(app.state, "event_bus") else None
                )
                if event_bus:
                    from events.publishers import publish_device_pairing_completed

                    await publish_device_pairing_completed(
                        event_bus=event_bus,
                        device_id=request.device_id,
                        user_id=request.user_id,
                    )
            except Exception as e:
                logger.error(f"Error publishing pairing completed event: {e}")

        return PairingTokenVerifyResponse(**result)

    except Exception as e:
        logger.error(f"Error verifying pairing token: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
