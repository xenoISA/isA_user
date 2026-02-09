"""
Membership Microservice API

Loyalty engine with points management, tier progression, and benefits tracking.
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Query
from fastapi.responses import JSONResponse

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from core.config_manager import ConfigManager
from core.logger import setup_service_logger
from core.nats_client import get_event_bus

from isa_common.consul_client import ConsulRegistry

from .membership_repository import MembershipRepository
from .membership_service import MembershipService
from .factory import create_membership_service
from .models import (
    HealthResponse,
    ServiceInfo,
    MembershipStatus,
    MembershipTier,
    PointAction,
    EnrollMembershipRequest,
    EnrollMembershipResponse,
    EarnPointsRequest,
    EarnPointsResponse,
    RedeemPointsRequest,
    RedeemPointsResponse,
    CancelMembershipRequest,
    SuspendMembershipRequest,
    UseBenefitRequest,
    UseBenefitResponse,
    PointsBalanceResponse,
    TierStatusResponse,
    BenefitListResponse,
    HistoryResponse,
    ListMembershipsResponse,
    MembershipResponse,
    MembershipStats,
)
from .routes_registry import SERVICE_METADATA, get_routes_for_consul

# Initialize config manager
config_manager = ConfigManager("membership_service")
config = config_manager.get_service_config()

# Configure logger
logger = setup_service_logger("membership_service", level=config.log_level.upper())

# Print config info (development)
if config.debug:
    config_manager.print_config_summary(show_secrets=False)

# Global variables
membership_service: Optional[MembershipService] = None
repository: Optional[MembershipRepository] = None
event_bus = None
consul_registry = None
SERVICE_PORT = config.service_port or 8250


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    global membership_service, repository, consul_registry, event_bus

    try:
        # Initialize NATS JetStream event bus
        try:
            event_bus = await get_event_bus("membership_service")
            logger.info("Event bus initialized successfully")
        except Exception as e:
            logger.warning(
                f"Failed to initialize event bus: {e}. Continuing without event subscriptions."
            )
            event_bus = None

        # Create membership service using factory
        membership_service = create_membership_service(
            config=config_manager, event_bus=event_bus
        )

        # Initialize repository connection
        repository = membership_service.repository
        await repository.initialize()

        # Subscribe to events if event bus is available
        if event_bus:
            try:
                from .events import get_event_handlers

                # Get event handlers
                handler_map = get_event_handlers(membership_service, event_bus)

                # Subscribe to events
                for pattern, handler_func in handler_map.items():
                    await event_bus.subscribe_to_events(
                        pattern=pattern,
                        handler=handler_func,
                        durable=f"membership-{pattern.replace('.', '-').replace('*', 'all')}-consumer",
                    )
                    logger.info(f"Subscribed to {pattern}")

                logger.info(
                    f"Membership event subscriber started ({len(handler_map)} event patterns)"
                )
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

                consul_registry = ConsulRegistry(
                    service_name=SERVICE_METADATA["service_name"],
                    service_port=config.service_port,
                    consul_host=config.consul_host,
                    consul_port=config.consul_port,
                    tags=SERVICE_METADATA["tags"],
                    meta=consul_meta,
                    health_check_type="ttl"  # Use TTL for reliable health checks,
                )
                consul_registry.register()
                consul_registry.start_maintenance()  # Start TTL heartbeat
            # Start TTL heartbeat - added for consistency with isA_Model
                logger.info(
                    f"Service registered with Consul: {route_meta.get('route_count')} routes"
                )
            except Exception as e:
                logger.warning(f"Failed to register with Consul: {e}")
                consul_registry = None

        logger.info(f"Membership service started on port {SERVICE_PORT}")
        yield

    except Exception as e:
        logger.error(f"Failed to initialize membership service: {e}")
        raise
    finally:
        # Cleanup
        if consul_registry:
            try:
                consul_registry.deregister()
                logger.info("Membership service deregistered from Consul")
            except Exception as e:
                logger.error(f"Failed to deregister from Consul: {e}")

        if event_bus:
            try:
                await event_bus.close()
                logger.info("Membership event bus closed")
            except Exception as e:
                logger.error(f"Error closing event bus: {e}")

        if repository:
            await repository.close()
            logger.info("Membership service database connections closed")


# Create FastAPI app
app = FastAPI(
    title="Membership Service",
    description="Loyalty engine with points management, tier progression, and benefits tracking",
    version="1.0.0",
    lifespan=lifespan,
)


# ====================
# Dependency Injection
# ====================


async def get_membership_service() -> MembershipService:
    """Get membership service instance"""
    if not membership_service:
        raise HTTPException(status_code=503, detail="Membership service not initialized")
    return membership_service


# ====================
# Health Check and Service Info
# ====================


@app.get("/api/v1/memberships/health")
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check"""
    dependencies = {}

    # Check database connection
    try:
        if repository and repository.db:
            is_healthy = repository.db.health_check()
            dependencies["database"] = "healthy" if is_healthy else "unhealthy"
        else:
            dependencies["database"] = "unhealthy"
    except Exception:
        dependencies["database"] = "unhealthy"

    return HealthResponse(
        status="healthy" if all(v == "healthy" for v in dependencies.values()) else "degraded",
        service="membership_service",
        port=SERVICE_PORT,
        version="1.0.0",
        dependencies=dependencies,
    )


@app.get("/api/v1/memberships/info", response_model=ServiceInfo)
async def get_service_info():
    """Get service information"""
    return ServiceInfo(
        service="membership_service",
        version="1.0.0",
        description="Loyalty engine with points management, tier progression, and benefits tracking",
        capabilities=[
            "enrollment",
            "points_management",
            "tier_progression",
            "benefits_tracking",
            "history"
        ],
    )


# ====================
# Enrollment API
# ====================


@app.post("/api/v1/memberships", response_model=EnrollMembershipResponse)
async def enroll_membership(
    request: EnrollMembershipRequest,
    service: MembershipService = Depends(get_membership_service)
):
    """Enroll a new membership"""
    try:
        result = await service.enroll_membership(
            user_id=request.user_id,
            organization_id=request.organization_id,
            enrollment_source=request.enrollment_source,
            promo_code=request.promo_code,
            metadata=request.metadata
        )

        if not result.success:
            if "already has active" in result.message:
                raise HTTPException(status_code=409, detail=result.message)
            raise HTTPException(status_code=400, detail=result.message)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enrolling membership: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ====================
# Membership Management API
# ====================


@app.get("/api/v1/memberships", response_model=ListMembershipsResponse)
async def list_memberships(
    user_id: Optional[str] = Query(default=None),
    organization_id: Optional[str] = Query(default=None),
    status: Optional[MembershipStatus] = Query(default=None),
    tier_code: Optional[MembershipTier] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    service: MembershipService = Depends(get_membership_service)
):
    """List memberships"""
    try:
        result = await service.list_memberships(
            user_id=user_id,
            organization_id=organization_id,
            status=status,
            tier_code=tier_code,
            page=page,
            page_size=page_size
        )
        return result

    except Exception as e:
        logger.error(f"Error listing memberships: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/v1/memberships/{membership_id}", response_model=MembershipResponse)
async def get_membership(
    membership_id: str,
    service: MembershipService = Depends(get_membership_service)
):
    """Get membership by ID"""
    try:
        result = await service.get_membership(membership_id)

        if not result.success:
            raise HTTPException(status_code=404, detail=result.message)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting membership: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/v1/memberships/user/{user_id}", response_model=MembershipResponse)
async def get_membership_by_user(
    user_id: str,
    organization_id: Optional[str] = Query(default=None),
    service: MembershipService = Depends(get_membership_service)
):
    """Get membership by user ID"""
    try:
        result = await service.get_membership_by_user(
            user_id=user_id,
            organization_id=organization_id
        )

        if not result.success:
            raise HTTPException(status_code=404, detail=result.message)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting membership by user: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/v1/memberships/{membership_id}/cancel", response_model=MembershipResponse)
async def cancel_membership(
    membership_id: str,
    request: CancelMembershipRequest,
    service: MembershipService = Depends(get_membership_service)
):
    """Cancel membership"""
    try:
        result = await service.cancel_membership(
            membership_id=membership_id,
            reason=request.reason,
            forfeit_points=request.forfeit_points,
            feedback=request.feedback
        )

        if not result.success:
            if "not found" in result.message.lower():
                raise HTTPException(status_code=404, detail=result.message)
            raise HTTPException(status_code=400, detail=result.message)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error canceling membership: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.put("/api/v1/memberships/{membership_id}/suspend", response_model=MembershipResponse)
async def suspend_membership(
    membership_id: str,
    request: SuspendMembershipRequest,
    service: MembershipService = Depends(get_membership_service)
):
    """Suspend membership"""
    try:
        result = await service.suspend_membership(
            membership_id=membership_id,
            reason=request.reason,
            duration_days=request.duration_days
        )

        if not result.success:
            if "not found" in result.message.lower():
                raise HTTPException(status_code=404, detail=result.message)
            raise HTTPException(status_code=400, detail=result.message)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error suspending membership: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.put("/api/v1/memberships/{membership_id}/reactivate", response_model=MembershipResponse)
async def reactivate_membership(
    membership_id: str,
    service: MembershipService = Depends(get_membership_service)
):
    """Reactivate suspended membership"""
    try:
        result = await service.reactivate_membership(membership_id)

        if not result.success:
            if "not found" in result.message.lower():
                raise HTTPException(status_code=404, detail=result.message)
            raise HTTPException(status_code=400, detail=result.message)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reactivating membership: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ====================
# Points API
# ====================


@app.post("/api/v1/memberships/points/earn", response_model=EarnPointsResponse)
async def earn_points(
    request: EarnPointsRequest,
    service: MembershipService = Depends(get_membership_service)
):
    """Earn points"""
    try:
        result = await service.earn_points(
            user_id=request.user_id,
            points_amount=request.points_amount,
            source=request.source,
            organization_id=request.organization_id,
            reference_id=request.reference_id,
            description=request.description,
            metadata=request.metadata
        )

        if not result.success:
            if "not found" in result.message.lower():
                raise HTTPException(status_code=404, detail=result.message)
            if "suspended" in result.message.lower():
                raise HTTPException(status_code=403, detail=result.message)
            if "expired" in result.message.lower():
                raise HTTPException(status_code=403, detail=result.message)
            raise HTTPException(status_code=400, detail=result.message)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error earning points: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/v1/memberships/points/redeem", response_model=RedeemPointsResponse)
async def redeem_points(
    request: RedeemPointsRequest,
    service: MembershipService = Depends(get_membership_service)
):
    """Redeem points"""
    try:
        result = await service.redeem_points(
            user_id=request.user_id,
            points_amount=request.points_amount,
            reward_code=request.reward_code,
            organization_id=request.organization_id,
            description=request.description,
            metadata=request.metadata
        )

        if not result.success:
            if "not found" in result.message.lower():
                raise HTTPException(status_code=404, detail=result.message)
            if "insufficient" in result.message.lower():
                raise HTTPException(status_code=402, detail=result.message)
            if "suspended" in result.message.lower():
                raise HTTPException(status_code=403, detail=result.message)
            if "expired" in result.message.lower():
                raise HTTPException(status_code=403, detail=result.message)
            raise HTTPException(status_code=400, detail=result.message)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error redeeming points: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/v1/memberships/points/balance", response_model=PointsBalanceResponse)
async def get_points_balance(
    user_id: str = Query(...),
    organization_id: Optional[str] = Query(default=None),
    service: MembershipService = Depends(get_membership_service)
):
    """Get points balance"""
    try:
        result = await service.get_points_balance(
            user_id=user_id,
            organization_id=organization_id
        )

        if not result.success:
            raise HTTPException(status_code=404, detail=result.message)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting points balance: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ====================
# Tier API
# ====================


@app.get("/api/v1/memberships/{membership_id}/tier", response_model=TierStatusResponse)
async def get_tier_status(
    membership_id: str,
    service: MembershipService = Depends(get_membership_service)
):
    """Get tier status and progress"""
    try:
        result = await service.get_tier_status(membership_id)

        if not result.success:
            raise HTTPException(status_code=404, detail=result.message)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tier status: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ====================
# Benefits API
# ====================


@app.get("/api/v1/memberships/{membership_id}/benefits", response_model=BenefitListResponse)
async def get_benefits(
    membership_id: str,
    service: MembershipService = Depends(get_membership_service)
):
    """Get available benefits"""
    try:
        result = await service.get_benefits(membership_id)

        if not result.success:
            raise HTTPException(status_code=404, detail=result.message)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting benefits: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/v1/memberships/{membership_id}/benefits/use", response_model=UseBenefitResponse)
async def use_benefit(
    membership_id: str,
    request: UseBenefitRequest,
    service: MembershipService = Depends(get_membership_service)
):
    """Use a benefit"""
    try:
        result = await service.use_benefit(
            membership_id=membership_id,
            benefit_code=request.benefit_code,
            metadata=request.metadata
        )

        if not result.success:
            if "not found" in result.message.lower():
                raise HTTPException(status_code=404, detail=result.message)
            if "not available" in result.message.lower():
                raise HTTPException(status_code=403, detail=result.message)
            if "limit exceeded" in result.message.lower():
                raise HTTPException(status_code=403, detail=result.message)
            raise HTTPException(status_code=400, detail=result.message)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error using benefit: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ====================
# History API
# ====================


@app.get("/api/v1/memberships/{membership_id}/history", response_model=HistoryResponse)
async def get_history(
    membership_id: str,
    action: Optional[PointAction] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    service: MembershipService = Depends(get_membership_service)
):
    """Get membership history"""
    try:
        result = await service.get_history(
            membership_id=membership_id,
            action=action,
            page=page,
            page_size=page_size
        )

        return result

    except Exception as e:
        logger.error(f"Error getting history: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ====================
# Statistics API
# ====================


@app.get("/api/v1/memberships/stats", response_model=MembershipStats)
async def get_statistics(
    service: MembershipService = Depends(get_membership_service)
):
    """Get membership statistics"""
    try:
        return await service.get_stats()
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ====================
# Error Handling
# ====================


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception in {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error occurred"}
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "microservices.membership_service.main:app",
        host="0.0.0.0",
        port=SERVICE_PORT,
        reload=config.debug,
        log_level=config.log_level.lower(),
    )
