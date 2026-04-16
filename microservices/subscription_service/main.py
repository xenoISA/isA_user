"""
Subscription Microservice

Responsibilities:
- Subscription lifecycle management (create, update, cancel, renew)
- Credit allocation and consumption tracking
- Subscription tier management
- Subscription history and audit trail
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

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

from isa_common.consul_client import ConsulRegistry

from core.admin_audit import publish_admin_action
from core.health import HealthCheck

from .models import (
    CreateSubscriptionRequest, CreateSubscriptionResponse,
    UpdateSubscriptionRequest, CancelSubscriptionRequest, CancelSubscriptionResponse,
    ConsumeCreditsRequest, ConsumeCreditsResponse, CreditBalanceResponse,
    ReserveCreditsRequest, ReserveCreditsResponse,
    ReconcileReservationRequest, ReconcileReservationResponse,
    ReleaseReservationRequest, ReleaseReservationResponse,
    BillingAccountType,
    SubscriptionResponse, SubscriptionListResponse, SubscriptionHistoryResponse,
    SubscriptionStatus, SubscriptionAction, SubscriptionHistory, InitiatedBy,
    ErrorResponse, HealthResponse
)
from .routes_registry import SERVICE_METADATA, get_routes_for_consul

# Import local components
from .subscription_service import SubscriptionService
from .factory import create_subscription_service
from .protocols import (
    SubscriptionServiceError,
    SubscriptionNotFoundError,
    SubscriptionValidationError,
    InsufficientCreditsError,
    TierNotFoundError
)

# Initialize configuration
config_manager = ConfigManager("subscription_service")
config = config_manager.get_service_config()

# Setup loggers
app_logger = setup_service_logger("subscription_service")
logger = app_logger

shutdown_manager = GracefulShutdown("subscription_service")


class SubscriptionMicroservice:
    """Subscription microservice core class"""

    def __init__(self):
        self.subscription_service: Optional[SubscriptionService] = None
        self.event_bus = None
        self.consul_registry = None

    async def initialize(self, event_bus=None):
        """Initialize the microservice"""
        try:
            self.event_bus = event_bus
            # Use factory to create service with real dependencies
            self.subscription_service = create_subscription_service(
                config=config_manager, event_bus=event_bus
            )
            await self.subscription_service.initialize()
            logger.info("Subscription microservice initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize subscription microservice: {e}")
            raise

    async def shutdown(self):
        """Shutdown the microservice"""
        try:
            # Consul deregistration
            if self.consul_registry:
                try:
                    self.consul_registry.deregister()
                    logger.info("Subscription service deregistered from Consul")
                except Exception as e:
                    logger.error(f"Failed to deregister from Consul: {e}")

            if self.event_bus:
                await self.event_bus.close()
                logger.info("Event bus closed")
            logger.info("Subscription microservice shutdown completed")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Global microservice instance
subscription_microservice = SubscriptionMicroservice()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    shutdown_manager.install_signal_handlers()
    # Initialize event bus
    event_bus = None
    try:
        event_bus = await get_event_bus("subscription_service")
        logger.info("Event bus initialized successfully")
    except Exception as e:
        logger.warning(
            f"Failed to initialize event bus: {e}. Continuing without event publishing."
        )
        event_bus = None

    # Initialize microservice with event bus
    await subscription_microservice.initialize(event_bus=event_bus)

    # Subscribe to events if event bus is available
    if event_bus and subscription_microservice.subscription_service:
        try:
            from .events import SubscriptionEventHandlers

            event_handlers = SubscriptionEventHandlers(subscription_microservice.subscription_service)
            handler_map = event_handlers.get_event_handler_map()

            for event_pattern, handler_func in handler_map.items():
                await event_bus.subscribe_to_events(
                    pattern=event_pattern, handler=handler_func
                )
                logger.info(f"Subscribed to {event_pattern} events")

            logger.info(f"Event handlers registered - Subscribed to {len(handler_map)} event types")
        except Exception as e:
            logger.warning(f"Failed to subscribe to events: {e}")

    # Consul service registration
    if config.consul_enabled:
        try:
            route_meta = get_routes_for_consul()
            consul_meta = {
                "version": SERVICE_METADATA["version"],
                "capabilities": ",".join(SERVICE_METADATA["capabilities"]),
                **route_meta,
            }

            subscription_microservice.consul_registry = ConsulRegistry(
                service_name=SERVICE_METADATA["service_name"],
                service_port=config.service_port,
                consul_host=config.consul_host,
                consul_port=config.consul_port,
                tags=SERVICE_METADATA["tags"],
                meta=consul_meta,
                health_check_type="ttl"  # Use TTL for reliable health checks,
            )
            subscription_microservice.consul_registry.register()
            subscription_microservice.consul_registry.start_maintenance()  # Start TTL heartbeat
            # Start TTL heartbeat - added for consistency with isA_Model
            logger.info(
                f"Service registered with Consul: {route_meta.get('route_count')} routes"
            )
        except Exception as e:
            logger.warning(f"Failed to register with Consul: {e}")
            subscription_microservice.consul_registry = None

    yield

    # Cleanup
    shutdown_manager.initiate_shutdown()
    await shutdown_manager.wait_for_drain()
    await subscription_microservice.shutdown()


# Create FastAPI application
app = FastAPI(
    title="Subscription Service",
    description="Subscription management and credit allocation microservice",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(shutdown_middleware, shutdown_manager=shutdown_manager)
setup_metrics(app, "subscription_service")


# Dependency injection
def get_subscription_service() -> SubscriptionService:
    """Get subscription service instance"""
    if not subscription_microservice.subscription_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Subscription service not initialized",
        )
    return subscription_microservice.subscription_service


# ====================
# Health Endpoints
# ====================

health = HealthCheck("subscription_service", version="1.0.0", shutdown_manager=shutdown_manager)
health.add_postgres(lambda: subscription_microservice.subscription_service.repository.db if subscription_microservice.subscription_service and hasattr(subscription_microservice.subscription_service, 'repository') and subscription_microservice.subscription_service.repository else None)


@app.get("/api/v1/subscriptions/health")
@app.get("/health")
async def health_check():
    """Service health check"""
    return await health.check()

@app.post("/api/v1/subscriptions", response_model=CreateSubscriptionResponse)
async def create_subscription(
    request: CreateSubscriptionRequest,
    subscription_service: SubscriptionService = Depends(get_subscription_service),
):
    """Create a new subscription"""
    try:
        return await subscription_service.create_subscription(request)
    except SubscriptionValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except TierNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except SubscriptionServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.get("/api/v1/subscriptions", response_model=SubscriptionListResponse)
async def list_subscriptions(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    organization_id: Optional[str] = Query(None, description="Filter by organization ID"),
    status: Optional[SubscriptionStatus] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    subscription_service: SubscriptionService = Depends(get_subscription_service),
):
    """List subscriptions with filters"""
    try:
        return await subscription_service.get_subscriptions(
            user_id=user_id,
            organization_id=organization_id,
            status=status,
            page=page,
            page_size=page_size
        )
    except SubscriptionServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.get("/api/v1/subscriptions/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: str,
    subscription_service: SubscriptionService = Depends(get_subscription_service),
):
    """Get subscription by ID"""
    try:
        response = await subscription_service.get_subscription(subscription_id)
        if not response.success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=response.message)
        return response
    except SubscriptionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except SubscriptionServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.post("/api/v1/subscriptions/{subscription_id}/cancel", response_model=CancelSubscriptionResponse)
async def cancel_subscription(
    subscription_id: str,
    request: CancelSubscriptionRequest,
    user_id: str = Query(..., description="User ID for authorization"),
    subscription_service: SubscriptionService = Depends(get_subscription_service),
):
    """Cancel a subscription"""
    try:
        return await subscription_service.cancel_subscription(subscription_id, request, user_id)
    except SubscriptionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except SubscriptionValidationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except SubscriptionServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# ====================
# User Subscription Endpoint
# ====================

@app.get("/api/v1/subscriptions/user/{user_id}", response_model=SubscriptionResponse)
async def get_user_subscription(
    user_id: str,
    organization_id: Optional[str] = Query(None, description="Organization ID"),
    billing_account_type: Optional[BillingAccountType] = Query(
        None, description="Explicit payer type"
    ),
    billing_account_id: Optional[str] = Query(None, description="Explicit payer ID"),
    actor_user_id: Optional[str] = Query(None, description="Human actor ID"),
    subscription_service: SubscriptionService = Depends(get_subscription_service),
):
    """Get active subscription for a user"""
    try:
        return await subscription_service.get_user_subscription(
            user_id=user_id,
            organization_id=organization_id,
            billing_account_type=billing_account_type,
            billing_account_id=billing_account_id,
            actor_user_id=actor_user_id,
        )
    except SubscriptionServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# ====================
# Credit Endpoints
# ====================

@app.get("/api/v1/subscriptions/credits/balance", response_model=CreditBalanceResponse)
async def get_credit_balance(
    user_id: str = Query(..., description="User ID"),
    organization_id: Optional[str] = Query(None, description="Organization ID"),
    billing_account_type: Optional[BillingAccountType] = Query(
        None, description="Explicit payer type"
    ),
    billing_account_id: Optional[str] = Query(None, description="Explicit payer ID"),
    actor_user_id: Optional[str] = Query(None, description="Human actor ID"),
    subscription_service: SubscriptionService = Depends(get_subscription_service),
):
    """Get credit balance for a user"""
    try:
        return await subscription_service.get_credit_balance(
            user_id=user_id,
            organization_id=organization_id,
            billing_account_type=billing_account_type,
            billing_account_id=billing_account_id,
            actor_user_id=actor_user_id,
        )
    except SubscriptionServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.post("/api/v1/subscriptions/credits/consume", response_model=ConsumeCreditsResponse)
async def consume_credits(
    request: ConsumeCreditsRequest,
    subscription_service: SubscriptionService = Depends(get_subscription_service),
):
    """Consume credits from a user's subscription"""
    try:
        response = await subscription_service.consume_credits(request)
        if not response.success:
            if "Insufficient credits" in response.message:
                raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=response.message)
            elif "No active subscription" in response.message:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=response.message)
        return response
    except InsufficientCreditsError as e:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(e))
    except SubscriptionServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.post("/api/v1/subscriptions/credits/reserve", response_model=ReserveCreditsResponse)
async def reserve_credits(
    request: ReserveCreditsRequest,
    subscription_service: SubscriptionService = Depends(get_subscription_service),
):
    """Reserve credits for an in-flight inference request."""
    try:
        response = await subscription_service.reserve_credits(request)
        if not response.success:
            if "Insufficient credits" in response.message:
                raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=response.message)
            elif "No active subscription" in response.message:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=response.message)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response.message,
            )
        return response
    except SubscriptionServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.post("/api/v1/subscriptions/credits/reconcile", response_model=ReconcileReservationResponse)
async def reconcile_reservation(
    request: ReconcileReservationRequest,
    subscription_service: SubscriptionService = Depends(get_subscription_service),
):
    """Reconcile a reservation with actual credits used."""
    try:
        response = await subscription_service.reconcile_reservation(request)
        if not response.success:
            if "not found" in response.message.lower():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=response.message)
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=response.message)
        return response
    except SubscriptionServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.post("/api/v1/subscriptions/credits/release", response_model=ReleaseReservationResponse)
async def release_reservation(
    request: ReleaseReservationRequest,
    subscription_service: SubscriptionService = Depends(get_subscription_service),
):
    """Release a pending reservation after a failed inference."""
    try:
        response = await subscription_service.release_reservation(request)
        if not response.success:
            if "not found" in response.message.lower():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=response.message)
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=response.message)
        return response
    except SubscriptionServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# ====================
# History Endpoint
# ====================

@app.get("/api/v1/subscriptions/{subscription_id}/history", response_model=SubscriptionHistoryResponse)
async def get_subscription_history(
    subscription_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    subscription_service: SubscriptionService = Depends(get_subscription_service),
):
    """Get subscription history"""
    try:
        return await subscription_service.get_subscription_history(
            subscription_id=subscription_id,
            page=page,
            page_size=page_size
        )
    except SubscriptionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except SubscriptionServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# ====================
# Admin Endpoints
# ====================

async def require_admin(request: Request):
    """Check for admin role header"""
    if request.headers.get("X-Admin-Role") != "true":
        raise HTTPException(status_code=403, detail="Admin access required")


def _extract_admin_context(request: Request) -> dict:
    """Extract admin identity and request context from headers for audit logging."""
    return {
        "admin_user_id": request.headers.get("X-Admin-User-Id", "unknown_admin"),
        "admin_email": request.headers.get("X-Admin-Email"),
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("User-Agent"),
    }


async def _audit_admin_action(
    request: Request,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    changes: Optional[dict] = None,
    metadata: Optional[dict] = None,
):
    """Fire-and-forget admin audit event. Never raises."""
    try:
        ctx = _extract_admin_context(request)
        await publish_admin_action(
            event_bus=subscription_microservice.event_bus,
            admin_user_id=ctx["admin_user_id"],
            admin_email=ctx["admin_email"],
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=changes,
            ip_address=ctx["ip_address"],
            user_agent=ctx["user_agent"],
            metadata=metadata,
        )
    except Exception as e:
        logger.warning(f"Admin audit publish failed (non-blocking): {e}")


@app.get("/api/v1/subscriptions/admin/all", response_model=SubscriptionListResponse)
async def admin_list_all_subscriptions(
    request: Request,
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    tier_code: Optional[str] = Query(None, description="Filter by tier code"),
    subscription_status: Optional[SubscriptionStatus] = Query(None, alias="status", description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    subscription_service: SubscriptionService = Depends(get_subscription_service),
):
    """[Admin] List all subscriptions with filters (paginated)"""
    await require_admin(request)
    try:
        offset = (page - 1) * page_size
        subscriptions = await subscription_service.repository.get_subscriptions(
            user_id=user_id,
            status=subscription_status,
            tier_code=tier_code,
            limit=page_size,
            offset=offset,
        )
        return SubscriptionListResponse(
            success=True,
            message="Subscriptions retrieved",
            subscriptions=subscriptions,
            total=len(subscriptions),
            page=page,
            page_size=page_size,
        )
    except Exception as e:
        logger.error(f"Error listing all subscriptions (admin): {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.put("/api/v1/subscriptions/admin/{subscription_id}/tier")
async def admin_force_tier_change(
    subscription_id: str,
    request: Request,
    new_tier_code: str = Query(..., description="New tier code to assign"),
    reason: Optional[str] = Query(None, description="Reason for tier change"),
    subscription_service: SubscriptionService = Depends(get_subscription_service),
):
    """[Admin] Force a tier change on a subscription"""
    await require_admin(request)
    try:
        # Get current subscription
        sub = await subscription_service.repository.get_subscription(subscription_id)
        if not sub:
            raise HTTPException(status_code=404, detail=f"Subscription {subscription_id} not found")

        previous_tier = sub.tier_code

        # Validate the new tier exists
        tier_info = subscription_service._get_tier_info(new_tier_code)

        # Update subscription tier
        updates = {
            "tier_code": new_tier_code,
            "tier_id": tier_info.get("tier_id", new_tier_code),
        }
        updated = await subscription_service.repository.update_subscription(subscription_id, updates)

        # Record history
        import uuid as _uuid
        await subscription_service.repository.add_history(SubscriptionHistory(
            history_id=f"hist_{_uuid.uuid4().hex[:16]}",
            subscription_id=subscription_id,
            user_id=sub.user_id,
            organization_id=sub.organization_id,
            action=SubscriptionAction.UPGRADED if new_tier_code != previous_tier else SubscriptionAction.UPGRADED,
            previous_tier_code=previous_tier,
            new_tier_code=new_tier_code,
            reason=reason or "Admin forced tier change",
            initiated_by=InitiatedBy.ADMIN,
        ))

        # Audit
        await _audit_admin_action(
            request, action="force_tier_change", resource_type="subscription",
            resource_id=subscription_id,
            changes={"before": {"tier_code": previous_tier}, "after": {"tier_code": new_tier_code}},
            metadata={"reason": reason},
        )

        return {
            "success": True,
            "message": f"Tier changed from {previous_tier} to {new_tier_code}",
            "subscription_id": subscription_id,
            "previous_tier": previous_tier,
            "new_tier": new_tier_code,
        }

    except TierNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error force-changing tier (admin): {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/subscriptions/admin/{subscription_id}/credits")
async def admin_credit_adjustment(
    subscription_id: str,
    request: Request,
    credits: int = Query(..., description="Credit adjustment amount (positive to add, negative to subtract)"),
    reason: str = Query(..., description="Reason for credit adjustment"),
    subscription_service: SubscriptionService = Depends(get_subscription_service),
):
    """[Admin] Adjust credits on a subscription with reason"""
    await require_admin(request)
    try:
        sub = await subscription_service.repository.get_subscription(subscription_id)
        if not sub:
            raise HTTPException(status_code=404, detail=f"Subscription {subscription_id} not found")

        previous_remaining = sub.credits_remaining
        new_remaining = max(0, previous_remaining + credits)

        updates = {"credits_remaining": new_remaining}
        if credits > 0:
            updates["credits_allocated"] = sub.credits_allocated + credits

        await subscription_service.repository.update_subscription(subscription_id, updates)

        # Record history
        import uuid as _uuid
        action = SubscriptionAction.CREDITS_ALLOCATED if credits > 0 else SubscriptionAction.CREDITS_CONSUMED
        await subscription_service.repository.add_history(SubscriptionHistory(
            history_id=f"hist_{_uuid.uuid4().hex[:16]}",
            subscription_id=subscription_id,
            user_id=sub.user_id,
            organization_id=sub.organization_id,
            action=action,
            credits_change=credits,
            credits_balance_after=new_remaining,
            reason=reason,
            initiated_by=InitiatedBy.ADMIN,
        ))

        # Audit
        await _audit_admin_action(
            request, action="credit_adjustment", resource_type="subscription",
            resource_id=subscription_id,
            changes={
                "before": {"credits_remaining": previous_remaining},
                "after": {"credits_remaining": new_remaining},
            },
            metadata={"credits_delta": credits, "reason": reason},
        )

        return {
            "success": True,
            "message": f"Credits adjusted by {credits:+d}",
            "subscription_id": subscription_id,
            "previous_credits": previous_remaining,
            "new_credits": new_remaining,
            "adjustment": credits,
            "reason": reason,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adjusting credits (admin): {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ====================
# Error Handlers
# ====================

@app.exception_handler(SubscriptionValidationError)
async def validation_error_handler(request, exc):
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@app.exception_handler(SubscriptionNotFoundError)
async def not_found_error_handler(request, exc):
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@app.exception_handler(InsufficientCreditsError)
async def insufficient_credits_handler(request, exc):
    return HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(exc))


@app.exception_handler(SubscriptionServiceError)
async def service_error_handler(request, exc):
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
    )


if __name__ == "__main__":
    # Print configuration summary for debugging
    config_manager.print_config_summary()

    uvicorn.run(
        "microservices.subscription_service.main:app",
        host=config.service_host,
        port=config.service_port,
        reload=config.debug,
        log_level=config.log_level.lower(),
    )
