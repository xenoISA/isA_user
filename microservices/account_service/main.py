"""
Account Microservice

Responsibilities:
- User account management (CRUD operations)
- User profile management
- Account status management
- User preferences management
- Account search and listing

Note: Authentication is handled by auth_service, credits by credit_service
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query, Request, status

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

# Import ConfigManager
from core.config_manager import ConfigManager
from core.graceful_shutdown import GracefulShutdown, shutdown_middleware
from core.metrics import setup_metrics
from core.logger import setup_service_logger
from core.nats_client import get_event_bus
from core.health import HealthCheck

from isa_common.consul_client import ConsulRegistry

# Import local components
from .account_service import (
    AccountNotFoundError,
    AccountService,
    AccountServiceError,
    AccountValidationError,
)
from .factory import create_account_service
from .clients import (
    BillingServiceClient,
    OrganizationServiceClient,
    SubscriptionServiceClient,
    WalletServiceClient,
)
from .events import get_event_handlers
from .models import (
    AccountEnsureRequest,
    AccountListParams,
    AccountPreferencesRequest,
    AccountProfileResponse,
    AccountSearchParams,
    AccountSearchResponse,
    AccountServiceStatus,
    AccountStatsResponse,
    AccountStatusChangeRequest,
    AccountSummaryResponse,
    AccountUpdateRequest,
    AdminAccountDetailResponse,
    AdminAccountListResponse,
    AdminAccountResponse,
    AdminNoteRequest,
    AdminNoteResponse,
    AdminRolesUpdateRequest,
    AdminStatusUpdateRequest,
)
from .role_validator import (
    PLATFORM_ADMIN_ROLES,
    can_assign_platform_role,
    is_valid_platform_role,
)
from .routes_registry import SERVICE_METADATA, get_routes_for_consul

# Database connection now handled by repositories directly

# Initialize configuration
config_manager = ConfigManager("account_service")
config = config_manager.get_service_config()

# Setup loggers (use actual service name)
app_logger = setup_service_logger("account_service")
logger = app_logger  # for backward compatibility


class AccountMicroservice:
    """Account microservice core class"""

    def __init__(self):
        self.account_service = None
        self.event_bus = None
        self.consul_registry: Optional[ConsulRegistry] = None
        # Service clients for synchronous communication
        self.organization_client: Optional[OrganizationServiceClient] = None
        self.billing_client: Optional[BillingServiceClient] = None
        self.wallet_client: Optional[WalletServiceClient] = None

    async def initialize(self, event_bus=None):
        """Initialize the microservice"""
        try:
            logger.info("Initializing account microservice...")

            # Consul 服务注册
            if config.consul_enabled:
                try:
                    # 获取路由元数据
                    route_meta = get_routes_for_consul()

                    # 合并服务元数据
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
                        f"Service registered with Consul: {route_meta.get('route_count', 0)} routes"
                    )
                except Exception as e:
                    logger.warning(f"Failed to register with Consul: {e}")
                    self.consul_registry = None

            self.event_bus = event_bus

            # Initialize service clients for synchronous communication
            try:
                self.organization_client = OrganizationServiceClient()
                self.billing_client = BillingServiceClient()
                self.wallet_client = WalletServiceClient()
                self.subscription_client = SubscriptionServiceClient()
                logger.info("Service clients initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize service clients: {e}")
                self.subscription_client = None

            self.account_service = create_account_service(
                config=config_manager,
                event_bus=event_bus,
                subscription_client=self.subscription_client
            )
            logger.info("Account microservice initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize account microservice: {e}")
            raise

    async def shutdown(self):
        """Shutdown the microservice"""
        try:
            # Consul 注销
            if self.consul_registry:
                try:
                    self.consul_registry.deregister()
                    logger.info("Service deregistered from Consul")
                except Exception as e:
                    logger.error(f"Failed to deregister from Consul: {e}")

            # Close service clients
            if self.organization_client:
                await self.organization_client.close()
            if self.billing_client:
                await self.billing_client.close()
            if self.wallet_client:
                await self.wallet_client.close()
            if self.subscription_client:
                await self.subscription_client.close()
            logger.info("Service clients closed")

            if self.event_bus:
                await self.event_bus.close()
                logger.info("Event bus closed")
            logger.info("Account microservice shutdown completed")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Global microservice instance
account_microservice = AccountMicroservice()
shutdown_manager = GracefulShutdown("account_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    shutdown_manager.install_signal_handlers()
    # Initialize event bus
    event_bus = None
    try:
        event_bus = await get_event_bus("account_service")
        logger.info("✅ Event bus initialized successfully")

        # Register event handlers for subscriptions
        event_handlers = get_event_handlers()
        for event_type, handler in event_handlers.items():
            try:
                await event_bus.subscribe_to_events(event_type, handler)
                logger.info(f"✅ Subscribed to event: {event_type}")
            except Exception as e:
                logger.error(f"❌ Failed to subscribe to {event_type}: {e}")

        logger.info(f"Registered {len(event_handlers)} event handlers")

    except Exception as e:
        logger.warning(
            f"⚠️  Failed to initialize event bus: {e}. Continuing without event publishing."
        )
        event_bus = None

    # Initialize microservice with event bus
    await account_microservice.initialize(event_bus=event_bus)

    # Service discovery via Consul agent sidecar (no programmatic registration needed)
    logger.info("Service discovery via Consul agent sidecar")

    yield

    # Cleanup
    shutdown_manager.initiate_shutdown()
    await shutdown_manager.wait_for_drain()
    await account_microservice.shutdown()


# Create FastAPI application
app = FastAPI(
    title="Account Service",
    description="User account management microservice - Identity anchor. Subscription data managed by subscription_service.",
    version="1.1.0",
    lifespan=lifespan,
)
app.add_middleware(shutdown_middleware, shutdown_manager=shutdown_manager)
setup_metrics(app, "account_service")

# CORS middleware is handled by the Gateway
# Remove local CORS to avoid duplicate headers


# Dependency injection
def get_account_service() -> AccountService:
    """Get account service instance"""
    if not account_microservice.account_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Account service not initialized",
        )
    return account_microservice.account_service


# Health check endpoints
health = HealthCheck("account_service", version="1.0.0", shutdown_manager=shutdown_manager)
health.add_postgres(lambda: account_microservice.account_service.account_repo.db if account_microservice.account_service and hasattr(account_microservice.account_service, 'account_repo') and account_microservice.account_service.account_repo else None)


@app.get("/api/v1/accounts/health")
@app.get("/health")
async def health_check():
    """Service health check"""
    return await health.check()

async def get_authenticated_caller(request: Request) -> str:
    """Extract caller ID from verified authentication credentials."""
    from core.auth_dependencies import (
        INTERNAL_SERVICE_SECRET,
        _extract_user_id_from_bearer,
        _extract_user_id_from_api_key,
    )

    x_internal_service = request.headers.get("X-Internal-Service")
    x_internal_service_secret = request.headers.get("X-Internal-Service-Secret")
    if x_internal_service == "true" and x_internal_service_secret == INTERNAL_SERVICE_SECRET:
        return "internal-service"

    authorization = request.headers.get("authorization")
    if authorization:
        uid = await _extract_user_id_from_bearer(authorization)
        if uid:
            return uid

    x_api_key = request.headers.get("X-API-Key")
    if x_api_key:
        uid = await _extract_user_id_from_api_key(x_api_key)
        if uid:
            return uid

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="User authentication required",
    )


# Core account management endpoints


@app.post("/api/v1/accounts/ensure", response_model=AccountProfileResponse)
async def ensure_account(
    request: AccountEnsureRequest,
    account_service: AccountService = Depends(get_account_service),
    caller_id: str = Depends(get_authenticated_caller),
):
    """Ensure user account exists, create if needed"""
    try:
        account_response, was_created = await account_service.ensure_account(request)
        return account_response
    except AccountValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except AccountServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.get("/api/v1/accounts/profile/{user_id}", response_model=AccountProfileResponse)
async def get_account_profile(
    user_id: str, account_service: AccountService = Depends(get_account_service),
    caller_id: str = Depends(get_authenticated_caller),
):
    """
    Get detailed account profile (identity data only).

    Note: For subscription information, query subscription_service directly.
    """
    try:
        return await account_service.get_account_profile(user_id)
    except AccountNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except AccountServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.put("/api/v1/accounts/profile/{user_id}", response_model=AccountProfileResponse)
async def update_account_profile(
    user_id: str,
    request: AccountUpdateRequest,
    account_service: AccountService = Depends(get_account_service),
    caller_id: str = Depends(get_authenticated_caller),
):
    """Update account profile"""
    try:
        return await account_service.update_account_profile(user_id, request)
    except AccountNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except AccountValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except AccountServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.put("/api/v1/accounts/preferences/{user_id}")
async def update_account_preferences(
    user_id: str,
    request: AccountPreferencesRequest,
    account_service: AccountService = Depends(get_account_service),
    caller_id: str = Depends(get_authenticated_caller),
):
    """Update account preferences"""
    try:
        success = await account_service.update_account_preferences(user_id, request)
        if success:
            return {"message": "Preferences updated successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update preferences",
            )
    except AccountServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.get("/api/v1/users/me/instructions")
async def get_custom_instructions(
    account_service: AccountService = Depends(get_account_service),
    caller_id: str = Depends(get_authenticated_caller),
):
    """Get profile-level custom instructions (#260)"""
    try:
        instructions = await account_service.repository.get_custom_instructions(caller_id)
        return {"instructions": instructions}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.put("/api/v1/users/me/instructions")
async def set_custom_instructions(
    request: dict,
    account_service: AccountService = Depends(get_account_service),
    caller_id: str = Depends(get_authenticated_caller),
):
    """Set profile-level custom instructions (max 4000 chars) (#260)"""
    instructions = request.get("instructions", "")
    if len(instructions) > 4000:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Instructions exceed 4000 character limit")
    try:
        success = await account_service.repository.set_custom_instructions(caller_id, instructions)
        if success:
            return {"message": "Custom instructions updated", "instructions": instructions}
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update instructions")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.delete("/api/v1/accounts/profile/{user_id}")
async def delete_account(
    user_id: str,
    reason: Optional[str] = Query(None, description="Deletion reason"),
    account_service: AccountService = Depends(get_account_service),
    caller_id: str = Depends(get_authenticated_caller),
):
    """Delete account (soft delete)"""
    try:
        success = await account_service.delete_account(user_id, reason)
        if success:
            return {"message": "Account deleted successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete account",
            )
    except AccountServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# Account query endpoints


@app.get("/api/v1/accounts", response_model=AccountSearchResponse)
async def list_accounts(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search in name/email"),
    account_service: AccountService = Depends(get_account_service),
    caller_id: str = Depends(get_authenticated_caller),
):
    """
    List accounts with filtering and pagination.

    Note: Subscription filtering is not available here. Use subscription_service
    for subscription-based queries.
    """
    try:
        params = AccountListParams(
            page=page,
            page_size=page_size,
            is_active=is_active,
            search=search,
        )
        return await account_service.list_accounts(params)
    except AccountServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.get("/api/v1/accounts/search", response_model=List[AccountSummaryResponse])
async def search_accounts(
    query: str = Query(..., description="Search query"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    include_inactive: bool = Query(False, description="Include inactive accounts"),
    account_service: AccountService = Depends(get_account_service),
    caller_id: str = Depends(get_authenticated_caller),
):
    """Search accounts by query"""
    try:
        params = AccountSearchParams(
            query=query, limit=limit, include_inactive=include_inactive
        )
        return await account_service.search_accounts(params)
    except AccountServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.get("/api/v1/accounts/by-email/{email}", response_model=AccountProfileResponse)
async def get_account_by_email(
    email: str, account_service: AccountService = Depends(get_account_service),
    caller_id: str = Depends(get_authenticated_caller),
):
    """Get account by email address"""
    try:
        account = await account_service.get_account_by_email(email)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account not found with email: {email}",
            )
        return account
    except AccountServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# Admin operations


@app.put("/api/v1/accounts/status/{user_id}")
async def change_account_status(
    user_id: str,
    request: AccountStatusChangeRequest,
    account_service: AccountService = Depends(get_account_service),
    caller_id: str = Depends(get_authenticated_caller),
):
    """Change account status (admin operation)"""
    try:
        success = await account_service.change_account_status(user_id, request)
        if success:
            status_text = "activated" if request.is_active else "deactivated"
            return {"message": f"Account {status_text} successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to change account status",
            )
    except AccountServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# Service statistics


@app.get("/api/v1/accounts/stats", response_model=AccountStatsResponse)
async def get_account_stats(
    account_service: AccountService = Depends(get_account_service),
):
    """Get account service statistics"""
    try:
        return await account_service.get_service_stats()
    except AccountServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# ==================== Admin Endpoints ====================


async def require_admin_token(request: Request) -> Dict[str, Any]:
    """Verify admin JWT token from Authorization header.

    Returns the verified admin payload including admin_roles.
    Calls auth_service admin verify internally.
    """
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    import httpx

    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing admin bearer token",
        )

    token = auth_header[len("Bearer "):]

    # Decode and validate token locally using JWT
    try:
        import jwt as pyjwt
        payload = pyjwt.decode(token, options={"verify_signature": False})

        # Check scope is admin
        if payload.get("scope") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin token required",
            )

        metadata = payload.get("metadata", {}) or {}
        admin_roles = metadata.get("admin_roles", [])
        if not admin_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No admin roles in token",
            )

        return {
            "user_id": payload.get("sub"),
            "email": payload.get("email"),
            "admin_roles": admin_roles,
            "scope": payload.get("scope"),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid admin token: {str(e)}",
        )


@app.get("/api/v1/account/admin/accounts", response_model=AdminAccountListResponse)
async def admin_list_accounts(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search in name/email"),
    account_service: AccountService = Depends(get_account_service),
    admin: Dict[str, Any] = Depends(require_admin_token),
):
    """List all accounts (admin only, paginated, searchable)."""
    try:
        params = AccountListParams(
            page=page,
            page_size=page_size,
            is_active=is_active,
            search=search,
        )
        result = await account_service.list_accounts(params)

        # Convert to admin response format (includes admin_roles)
        admin_accounts = []
        for acct in result.accounts:
            admin_accounts.append(
                AdminAccountResponse(
                    user_id=acct.user_id,
                    email=acct.email,
                    name=acct.name,
                    is_active=acct.is_active,
                    admin_roles=None,  # Summary view doesn't load admin_roles
                    created_at=acct.created_at,
                )
            )

        return AdminAccountListResponse(
            accounts=admin_accounts,
            total_count=result.total_count,
            page=result.page,
            page_size=result.page_size,
            has_next=result.has_next,
        )
    except AccountServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.put("/api/v1/account/admin/accounts/{user_id}/roles", response_model=AdminAccountResponse)
async def admin_update_roles(
    user_id: str,
    request: AdminRolesUpdateRequest,
    admin: Dict[str, Any] = Depends(require_admin_token),
):
    """Assign admin roles to a user account (admin only).

    Authorization rules (see ``docs/guidance/role-taxonomy.md``):

    - Every element in ``admin_roles`` must be a canonical platform-admin role
      (``role_validator.is_valid_platform_role``). Otherwise → 400.
    - The caller must hold ``super_admin`` to grant any platform-admin role
      (``role_validator.can_assign_platform_role``). Otherwise → 403.

    Denials are logged as structured ``role_validator_denied`` entries carrying
    the rule name, caller id, and target user id.
    """
    caller_admin_roles = admin.get("admin_roles") or []
    caller_id = admin.get("user_id")

    # Rule 1: every requested role must be a canonical platform-admin role.
    invalid_roles = [
        r for r in request.admin_roles if not is_valid_platform_role(r)
    ]
    if invalid_roles:
        logger.warning(
            "role_validator_denied rule=invalid_platform_role "
            "caller_id=%s target_user_id=%s invalid_roles=%s valid_roles=%s",
            caller_id,
            user_id,
            invalid_roles,
            PLATFORM_ADMIN_ROLES,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid admin roles: {invalid_roles}. "
                f"Valid roles: {PLATFORM_ADMIN_ROLES}"
            ),
        )

    # Rule 2: only super_admin can mutate platform-admin roles — for every
    # requested grant, and also for a clearing request (empty list), since
    # revocation is just as privileged as granting.
    if "super_admin" not in caller_admin_roles:
        logger.warning(
            "role_validator_denied rule=only_super_admin_can_assign "
            "caller_id=%s caller_admin_roles=%s target_user_id=%s "
            "requested_roles=%s",
            caller_id,
            caller_admin_roles,
            user_id,
            request.admin_roles,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "only_super_admin_can_assign: only super_admin can assign or "
                "revoke platform admin roles"
            ),
        )

    # Defensive: even when the caller is super_admin, every role must still
    # pass the canonical validator (already enforced above, but re-check keeps
    # the invariant local to the critical path).
    for role in request.admin_roles:
        if not can_assign_platform_role(caller_admin_roles, role):
            logger.warning(
                "role_validator_denied rule=invariant_can_assign "
                "caller_id=%s caller_admin_roles=%s target_user_id=%s "
                "assignee_role=%s",
                caller_id,
                caller_admin_roles,
                user_id,
                role,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "only_super_admin_can_assign: role assignment rejected"
                ),
            )

    try:
        repo = account_microservice.account_service.account_repo
        updated = await repo.update_admin_roles(user_id, request.admin_roles)

        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account not found: {user_id}",
            )

        return AdminAccountResponse(
            user_id=updated.user_id,
            email=updated.email,
            name=updated.name,
            is_active=updated.is_active,
            admin_roles=updated.admin_roles,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update admin roles: {str(e)}",
        )


@app.get("/api/v1/account/admin/accounts/{user_id}", response_model=AdminAccountDetailResponse)
async def admin_get_account_detail(
    user_id: str,
    admin: Dict[str, Any] = Depends(require_admin_token),
):
    """Get full account details including status, notes, and metadata (admin only)."""
    try:
        repo = account_microservice.account_service.account_repo
        detail = await repo.get_account_detail(user_id)

        if not detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account not found: {user_id}",
            )

        return AdminAccountDetailResponse(**detail)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get account detail: {str(e)}",
        )


@app.put("/api/v1/account/admin/accounts/{user_id}/status")
async def admin_update_account_status(
    user_id: str,
    request: AdminStatusUpdateRequest,
    admin: Dict[str, Any] = Depends(require_admin_token),
):
    """Activate, suspend, or ban an account with a reason (admin only)."""
    try:
        repo = account_microservice.account_service.account_repo
        success = await repo.update_account_status(
            user_id=user_id,
            status=request.status,
            reason=request.reason,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update account status",
            )

        return {
            "message": f"Account status updated to '{request.status}'",
            "user_id": user_id,
            "status": request.status,
        }

    except HTTPException:
        raise
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account not found: {user_id}",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update account status: {str(e)}",
        )


@app.post("/api/v1/account/admin/accounts/{user_id}/note", response_model=AdminNoteResponse, status_code=201)
async def admin_add_note(
    user_id: str,
    request: AdminNoteRequest,
    admin: Dict[str, Any] = Depends(require_admin_token),
):
    """Add an internal support/admin note to an account (admin only)."""
    try:
        repo = account_microservice.account_service.account_repo
        author_id = admin.get("user_id", "unknown_admin")

        note = await repo.add_admin_note(
            user_id=user_id,
            author_id=author_id,
            note=request.note,
        )

        if not note:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add note",
            )

        return AdminNoteResponse(
            note_id=note.note_id,
            user_id=note.user_id,
            author_id=note.author_id,
            note=note.note,
            created_at=note.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account not found: {user_id}",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add note: {str(e)}",
        )


# Error handlers
@app.exception_handler(AccountValidationError)
async def validation_error_handler(request, exc):
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@app.exception_handler(AccountNotFoundError)
async def not_found_error_handler(request, exc):
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@app.exception_handler(AccountServiceError)
async def service_error_handler(request, exc):
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
    )


if __name__ == "__main__":
    # Print configuration summary for debugging
    config_manager.print_config_summary()

    uvicorn.run(
        "microservices.account_service.main:app",
        host=config.service_host,
        port=config.service_port,
        reload=config.debug,
        log_level=config.log_level.lower(),
    )
