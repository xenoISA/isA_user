"""
Campaign Service Main Application

FastAPI application for campaign management.
Port: 8240
"""

import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query, Depends, Request, status
from fastapi.responses import JSONResponse

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.config_manager import ConfigManager

from .models import (
    Campaign,
    CampaignCreateRequest,
    CampaignUpdateRequest,
    CampaignResponse,
    CampaignListResponse,
    CampaignStatus,
    CampaignType,
    CampaignChannel,
    HealthResponse,
    ReadinessResponse,
    LivenessResponse,
    ScheduleRequest,
    CancelRequest,
    CloneRequest,
    VariantCreateRequest,
    ContentPreviewRequest,
    ErrorResponse,
)
from .factory import CampaignServiceFactory, get_factory, close_factory
from .routes_registry import SERVICE_METADATA, get_routes_for_consul
from .protocols import (
    CampaignNotFoundError,
    InvalidCampaignStateError,
    InvalidCampaignTypeError,
    CampaignValidationError,
    VariantAllocationError,
)
from isa_common.consul_client import ConsulRegistry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Service configuration
SERVICE_NAME = "campaign_service"
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8251"))
SERVICE_VERSION = "1.0.0"

# Track startup time for uptime calculation
startup_time = time.time()

# Global factory instance
factory: Optional[CampaignServiceFactory] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global factory

    logger.info(f"Starting {SERVICE_NAME} on port {SERVICE_PORT}")

    # Initialize factory
    config = ConfigManager(SERVICE_NAME)
    factory = CampaignServiceFactory(config)
    await factory.initialize()

    # Register with Consul if available
    consul_registry = None
    if os.getenv("CONSUL_ENABLED", "false").lower() == "true":
        try:
            route_meta = get_routes_for_consul()
            consul_meta = {
                "version": SERVICE_METADATA["version"],
                "capabilities": ",".join(SERVICE_METADATA["capabilities"]),
                **route_meta,
            }
            consul_registry = ConsulRegistry(
                service_name=SERVICE_METADATA["service_name"],
                service_port=SERVICE_PORT,
                consul_host=os.getenv("CONSUL_HOST", "localhost"),
                consul_port=int(os.getenv("CONSUL_PORT", "8500")),
                tags=SERVICE_METADATA["tags"],
                meta=consul_meta,
                health_check_type="ttl"  # Use TTL for reliable health checks,
            )
            consul_registry.register()
            consul_registry.start_maintenance()  # Start TTL heartbeat
            # Start TTL heartbeat - added for consistency with isA_Model
            logger.info(f"Registered {SERVICE_NAME} with Consul")
        except Exception as e:
            logger.warning(f"Consul registration failed: {e}")

    yield

    # Cleanup
    logger.info(f"Shutting down {SERVICE_NAME}")
    if consul_registry:
        try:
            consul_registry.deregister()
        except Exception:
            pass
    await factory.close()


# Create FastAPI application
app = FastAPI(
    title="Campaign Service",
    description="Marketing campaign management service for creating, scheduling, and executing campaigns",
    version=SERVICE_VERSION,
    lifespan=lifespan,
)


# ====================
# Exception Handlers
# ====================


@app.exception_handler(CampaignNotFoundError)
async def campaign_not_found_handler(request: Request, exc: CampaignNotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )


@app.exception_handler(InvalidCampaignStateError)
async def invalid_state_handler(request: Request, exc: InvalidCampaignStateError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )


@app.exception_handler(InvalidCampaignTypeError)
async def invalid_type_handler(request: Request, exc: InvalidCampaignTypeError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


@app.exception_handler(CampaignValidationError)
async def validation_error_handler(request: Request, exc: CampaignValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": str(exc)},
    )


@app.exception_handler(VariantAllocationError)
async def variant_allocation_handler(request: Request, exc: VariantAllocationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler to help debug issues"""
    import traceback
    error_traceback = traceback.format_exc()
    logger.error(f"Unhandled exception: {exc}\n{error_traceback}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": str(exc),
            "type": type(exc).__name__,
            "traceback": error_traceback.split("\n")[-5:-1]  # Last few lines of traceback
        },
    )


# ====================
# Dependencies
# ====================


def get_service():
    """Get campaign service from factory"""
    if not factory:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized",
        )
    return factory.service


def get_auth_context(request: Request) -> dict:
    """Extract auth context from request headers"""
    return {
        "user_id": request.headers.get("X-User-ID", "system"),
        "organization_id": request.headers.get("X-Organization-ID"),
        "role": request.headers.get("X-User-Role", "user"),
    }


# ====================
# Health Endpoints
# ====================


@app.get("/api/v1/campaigns/health")
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint"""
    dependencies = {}

    if factory:
        try:
            db_healthy = await factory.repository.health_check()
            dependencies["postgres"] = "healthy" if db_healthy else "unhealthy"
        except Exception:
            dependencies["postgres"] = "unhealthy"

        try:
            if factory.nats_client:
                dependencies["nats"] = "healthy" if factory.nats_client.is_connected else "unhealthy"
            else:
                dependencies["nats"] = "not_configured"
        except Exception:
            dependencies["nats"] = "unhealthy"

    return HealthResponse(
        status="healthy",
        service=SERVICE_NAME,
        port=SERVICE_PORT,
        version=SERVICE_VERSION,
        dependencies=dependencies,
    )


@app.get("/health/ready", response_model=ReadinessResponse, tags=["Health"])
async def readiness_check():
    """Readiness check endpoint"""
    checks = {}
    details = {}

    if factory:
        try:
            db_healthy = await factory.repository.health_check()
            checks["database"] = db_healthy
            details["database"] = "Connected" if db_healthy else "Connection failed"
        except Exception as e:
            checks["database"] = False
            details["database"] = str(e)

        try:
            if factory.nats_client:
                checks["nats"] = factory.nats_client.is_connected
                details["nats"] = "Connected" if factory.nats_client.is_connected else "Disconnected"
            else:
                checks["nats"] = True  # Optional
                details["nats"] = "Not configured (optional)"
        except Exception as e:
            checks["nats"] = False
            details["nats"] = str(e)
    else:
        checks["factory"] = False
        details["factory"] = "Factory not initialized"

    ready = all(checks.get(k, False) for k in ["database"])

    return ReadinessResponse(
        ready=ready,
        checks=checks,
        details=details,
    )


@app.get("/health/live", response_model=LivenessResponse, tags=["Health"])
async def liveness_check():
    """Liveness check endpoint"""
    return LivenessResponse(
        alive=True,
        uptime_seconds=time.time() - startup_time,
    )


# ====================
# Campaign CRUD Endpoints
# ====================


@app.post(
    "/api/v1/campaigns",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Campaigns"],
)
async def create_campaign(
    request: CampaignCreateRequest,
    service=Depends(get_service),
    auth: dict = Depends(get_auth_context),
):
    """
    Create a new campaign - BR-CAM-001.1

    Creates a campaign in draft status.
    """
    campaign = await service.create_campaign(
        request=request,
        organization_id=auth["organization_id"] or "default_org",
        created_by=auth["user_id"],
    )

    return CampaignResponse(
        campaign=campaign,
        message="Campaign created successfully",
    )


@app.get(
    "/api/v1/campaigns",
    response_model=CampaignListResponse,
    tags=["Campaigns"],
)
async def list_campaigns(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (comma-separated)"),
    type_filter: Optional[str] = Query(None, alias="type", description="Filter by type"),
    channel: Optional[str] = Query(None, description="Filter by channel"),
    search: Optional[str] = Query(None, description="Search by name"),
    created_after: Optional[datetime] = Query(None, description="Filter by creation date"),
    created_before: Optional[datetime] = Query(None, description="Filter by creation date"),
    scheduled_after: Optional[datetime] = Query(None, description="Filter by scheduled date"),
    scheduled_before: Optional[datetime] = Query(None, description="Filter by scheduled date"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    limit: int = Query(20, ge=1, le=100, description="Page size"),
    offset: int = Query(0, ge=0, description="Page offset"),
    service=Depends(get_service),
    auth: dict = Depends(get_auth_context),
):
    """
    List campaigns with filters

    Supports filtering by status, type, channel, and search.
    """
    # Parse status filter
    statuses = None
    if status_filter:
        statuses = [CampaignStatus(s.strip()) for s in status_filter.split(",")]

    # Parse type filter
    campaign_type = None
    if type_filter:
        campaign_type = CampaignType(type_filter)

    campaigns, total = await service.list_campaigns(
        organization_id=auth["organization_id"],
        status=statuses,
        campaign_type=campaign_type,
        search=search,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    return CampaignListResponse(
        campaigns=campaigns,
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + len(campaigns)) < total,
    )


@app.get(
    "/api/v1/campaigns/{campaign_id}",
    response_model=CampaignResponse,
    tags=["Campaigns"],
)
async def get_campaign(
    campaign_id: str,
    service=Depends(get_service),
    auth: dict = Depends(get_auth_context),
):
    """Get campaign by ID"""
    campaign = await service.get_campaign(
        campaign_id=campaign_id,
        organization_id=auth["organization_id"],
    )

    return CampaignResponse(campaign=campaign)


@app.patch(
    "/api/v1/campaigns/{campaign_id}",
    response_model=CampaignResponse,
    tags=["Campaigns"],
)
async def update_campaign(
    campaign_id: str,
    request: CampaignUpdateRequest,
    service=Depends(get_service),
    auth: dict = Depends(get_auth_context),
):
    """
    Update campaign - BR-CAM-001.8

    Only draft or paused campaigns can be updated.
    """
    campaign = await service.update_campaign(
        campaign_id=campaign_id,
        request=request,
        updated_by=auth["user_id"],
        organization_id=auth["organization_id"],
    )

    return CampaignResponse(
        campaign=campaign,
        message="Campaign updated successfully",
    )


@app.delete(
    "/api/v1/campaigns/{campaign_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Campaigns"],
)
async def delete_campaign(
    campaign_id: str,
    service=Depends(get_service),
    auth: dict = Depends(get_auth_context),
):
    """
    Delete campaign (soft delete)

    Cannot delete running campaigns.
    """
    await service.delete_campaign(
        campaign_id=campaign_id,
        organization_id=auth["organization_id"],
    )


# ====================
# Campaign Lifecycle Endpoints
# ====================


@app.post(
    "/api/v1/campaigns/{campaign_id}/schedule",
    response_model=CampaignResponse,
    tags=["Campaign Lifecycle"],
)
async def schedule_campaign(
    campaign_id: str,
    request: Optional[ScheduleRequest] = None,
    service=Depends(get_service),
    auth: dict = Depends(get_auth_context),
):
    """
    Schedule a campaign - BR-CAM-001.2

    Scheduled campaigns require valid audiences and content.
    Scheduled time must be at least 5 minutes in the future.
    """
    scheduled_at = request.scheduled_at if request else None
    timezone_str = request.timezone if request else "UTC"

    campaign = await service.schedule_campaign(
        campaign_id=campaign_id,
        scheduled_at=scheduled_at,
        tz_name=timezone_str,
        organization_id=auth["organization_id"],
        scheduled_by=auth["user_id"],
    )

    return CampaignResponse(
        campaign=campaign,
        message="Campaign scheduled successfully",
    )


@app.post(
    "/api/v1/campaigns/{campaign_id}/activate",
    response_model=CampaignResponse,
    tags=["Campaign Lifecycle"],
)
async def activate_campaign(
    campaign_id: str,
    service=Depends(get_service),
    auth: dict = Depends(get_auth_context),
):
    """
    Activate a triggered campaign - BR-CAM-001.3

    Triggered campaigns require at least one trigger.
    """
    campaign = await service.activate_campaign(
        campaign_id=campaign_id,
        organization_id=auth["organization_id"],
        activated_by=auth["user_id"],
    )

    return CampaignResponse(
        campaign=campaign,
        message="Campaign activated successfully",
    )


@app.post(
    "/api/v1/campaigns/{campaign_id}/pause",
    response_model=CampaignResponse,
    tags=["Campaign Lifecycle"],
)
async def pause_campaign(
    campaign_id: str,
    service=Depends(get_service),
    auth: dict = Depends(get_auth_context),
):
    """
    Pause a running campaign - BR-CAM-001.4

    Only running campaigns can be paused.
    """
    campaign = await service.pause_campaign(
        campaign_id=campaign_id,
        organization_id=auth["organization_id"],
        paused_by=auth["user_id"],
    )

    return CampaignResponse(
        campaign=campaign,
        message="Campaign paused successfully",
    )


@app.post(
    "/api/v1/campaigns/{campaign_id}/resume",
    response_model=CampaignResponse,
    tags=["Campaign Lifecycle"],
)
async def resume_campaign(
    campaign_id: str,
    service=Depends(get_service),
    auth: dict = Depends(get_auth_context),
):
    """
    Resume a paused campaign - BR-CAM-001.5

    Only paused campaigns can be resumed.
    """
    campaign = await service.resume_campaign(
        campaign_id=campaign_id,
        organization_id=auth["organization_id"],
        resumed_by=auth["user_id"],
    )

    return CampaignResponse(
        campaign=campaign,
        message="Campaign resumed successfully",
    )


@app.post(
    "/api/v1/campaigns/{campaign_id}/cancel",
    response_model=CampaignResponse,
    tags=["Campaign Lifecycle"],
)
async def cancel_campaign(
    campaign_id: str,
    request: Optional[CancelRequest] = None,
    service=Depends(get_service),
    auth: dict = Depends(get_auth_context),
):
    """
    Cancel a campaign - BR-CAM-001.6

    Cannot cancel completed or already cancelled campaigns.
    """
    reason = request.reason if request else None

    campaign = await service.cancel_campaign(
        campaign_id=campaign_id,
        reason=reason,
        organization_id=auth["organization_id"],
        cancelled_by=auth["user_id"],
    )

    return CampaignResponse(
        campaign=campaign,
        message="Campaign cancelled successfully",
    )


@app.post(
    "/api/v1/campaigns/{campaign_id}/clone",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Campaign Lifecycle"],
)
async def clone_campaign(
    campaign_id: str,
    request: Optional[CloneRequest] = None,
    service=Depends(get_service),
    auth: dict = Depends(get_auth_context),
):
    """
    Clone a campaign - BR-CAM-001.7

    Creates a copy of campaign with draft status.
    """
    new_name = request.name if request else None

    campaign = await service.clone_campaign(
        campaign_id=campaign_id,
        new_name=new_name,
        organization_id=auth["organization_id"],
        cloned_by=auth["user_id"],
    )

    return CampaignResponse(
        campaign=campaign,
        message="Campaign cloned successfully",
    )


# ====================
# Metrics Endpoints
# ====================


@app.get(
    "/api/v1/campaigns/{campaign_id}/metrics",
    tags=["Metrics"],
)
async def get_campaign_metrics(
    campaign_id: str,
    breakdown_by: Optional[str] = Query(None, description="Breakdown dimensions (variant,channel,segment)"),
    execution_id: Optional[str] = Query(None, description="Filter to specific execution"),
    service=Depends(get_service),
    auth: dict = Depends(get_auth_context),
):
    """
    Get campaign metrics - BR-CAM-005.2

    Returns delivery and engagement metrics.
    """
    breakdown = breakdown_by.split(",") if breakdown_by else None

    metrics = await service.get_campaign_metrics(
        campaign_id=campaign_id,
        organization_id=auth["organization_id"],
        breakdown_by=breakdown,
    )

    return metrics


# ====================
# Variant Endpoints
# ====================


@app.post(
    "/api/v1/campaigns/{campaign_id}/variants",
    status_code=status.HTTP_201_CREATED,
    tags=["Variants"],
)
async def add_variant(
    campaign_id: str,
    request: VariantCreateRequest,
    service=Depends(get_service),
    auth: dict = Depends(get_auth_context),
):
    """
    Add variant to campaign - BR-CAM-004.1

    Maximum 5 variants per campaign.
    """
    variant = await service.add_variant(
        campaign_id=campaign_id,
        name=request.name,
        description=request.description,
        allocation_percentage=Decimal(str(request.allocation_percentage)),
        is_control=request.is_control,
        channels=request.channels,
        organization_id=auth["organization_id"],
    )

    return {
        "variant": variant.model_dump(),
        "message": "Variant created successfully",
    }


# ====================
# Audience Endpoints
# ====================


@app.post(
    "/api/v1/campaigns/{campaign_id}/audiences/estimate",
    tags=["Audiences"],
)
async def estimate_audience(
    campaign_id: str,
    service=Depends(get_service),
    auth: dict = Depends(get_auth_context),
):
    """
    Estimate audience size - BR-CAM-002.3

    Returns estimated size with segment breakdown.
    """
    estimate = await service.estimate_audience_size(
        campaign_id=campaign_id,
        organization_id=auth["organization_id"],
    )

    return estimate


# ====================
# Preview Endpoints
# ====================


@app.post(
    "/api/v1/campaigns/{campaign_id}/preview",
    tags=["Preview"],
)
async def preview_content(
    campaign_id: str,
    request: ContentPreviewRequest,
    service=Depends(get_service),
    auth: dict = Depends(get_auth_context),
):
    """
    Preview campaign content - BR-CAM-008.2

    Renders content with variable substitution.
    """
    preview = await service.preview_content(
        campaign_id=campaign_id,
        variant_id=request.variant_id,
        channel_type=request.channel_type,
        sample_user_id=request.sample_user_id,
        organization_id=auth["organization_id"],
    )

    return preview


# ====================
# Main Entry Point
# ====================


def main():
    """Run the service"""
    import uvicorn

    uvicorn.run(
        "microservices.campaign_service.main:app",
        host="0.0.0.0",
        port=SERVICE_PORT,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
