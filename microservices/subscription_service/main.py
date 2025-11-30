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
from fastapi import Depends, FastAPI, HTTPException, Query, status

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

# Import ConfigManager
from core.config_manager import ConfigManager
from core.logger import setup_service_logger
from core.nats_client import get_event_bus

from isa_common.consul_client import ConsulRegistry

from .models import (
    CreateSubscriptionRequest, CreateSubscriptionResponse,
    UpdateSubscriptionRequest, CancelSubscriptionRequest, CancelSubscriptionResponse,
    ConsumeCreditsRequest, ConsumeCreditsResponse, CreditBalanceResponse,
    SubscriptionResponse, SubscriptionListResponse, SubscriptionHistoryResponse,
    SubscriptionStatus, ErrorResponse, HealthResponse
)
from .routes_registry import SERVICE_METADATA, get_routes_for_consul

# Import local components
from .subscription_service import (
    SubscriptionService,
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
            self.subscription_service = SubscriptionService(
                event_bus=event_bus, config=config_manager
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
                health_check_type="http",
            )
            subscription_microservice.consul_registry.register()
            logger.info(
                f"Service registered with Consul: {route_meta.get('route_count')} routes"
            )
        except Exception as e:
            logger.warning(f"Failed to register with Consul: {e}")
            subscription_microservice.consul_registry = None

    yield

    # Cleanup
    await subscription_microservice.shutdown()


# Create FastAPI application
app = FastAPI(
    title="Subscription Service",
    description="Subscription management and credit allocation microservice",
    version="1.0.0",
    lifespan=lifespan,
)


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

@app.get("/health")
async def health_check():
    """Service health check"""
    return {
        "status": "healthy",
        "service": config.service_name,
        "port": config.service_port,
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/health/detailed")
async def detailed_health_check(
    subscription_service: SubscriptionService = Depends(get_subscription_service),
):
    """Detailed health check"""
    try:
        health_data = await subscription_service.health_check()
        return HealthResponse(
            status=health_data["status"],
            service=config.service_name,
            port=config.service_port,
            version="1.0.0",
            timestamp=health_data["timestamp"],
            database_connected=True
        )
    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            service=config.service_name,
            port=config.service_port,
            version="1.0.0",
            timestamp=datetime.utcnow().isoformat(),
            database_connected=False
        )


# ====================
# Subscription Endpoints
# ====================

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
    subscription_service: SubscriptionService = Depends(get_subscription_service),
):
    """Get active subscription for a user"""
    try:
        return await subscription_service.get_user_subscription(user_id, organization_id)
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
    subscription_service: SubscriptionService = Depends(get_subscription_service),
):
    """Get credit balance for a user"""
    try:
        return await subscription_service.get_credit_balance(user_id, organization_id)
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
