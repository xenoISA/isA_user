"""
Credit Microservice API

Promotional credit management service with FIFO expiration and event-driven architecture.
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from core.config_manager import ConfigManager
from core.logger import setup_service_logger
from core.nats_client import get_event_bus

from isa_common.consul_client import ConsulRegistry

from .credit_repository import CreditRepository
from .credit_service import CreditService
from .factory import create_credit_service
from .models import (
    AllocateCreditsRequest,
    AllocationResponse as AllocateCreditsResponse,
    CreateCampaignRequest as CampaignRequest,
    CreditCampaignResponse as CampaignResponse,
    CheckAvailabilityRequest,
    AvailabilityResponse as CheckAvailabilityResponse,
    ConsumeCreditsRequest,
    ConsumptionResponse as ConsumeCreditsResponse,
    CreateAccountRequest,
    CreditAccountResponse,
    CreditBalanceSummary as CreditBalanceResponse,
    CreditStatisticsResponse,
    HealthCheckResponse as HealthResponse,
    TransactionListResponse,
    TransferCreditsRequest,
    TransferResponse as TransferCreditsResponse,
)
from .routes_registry import SERVICE_METADATA, get_routes_for_consul

# Initialize configuration manager
config_manager = ConfigManager("credit_service")
config = config_manager.get_service_config()

# Configure logging
logger = setup_service_logger("credit_service", level=config.log_level.upper())

# Print configuration info (development environment)
if config.debug:
    config_manager.print_config_summary(show_secrets=False)

# Global variables
credit_service: Optional[CreditService] = None
repository: Optional[CreditRepository] = None
event_bus = None  # NATS event bus
event_handlers = None  # Event handlers
consul_registry = None  # Consul service registry
scheduler = None  # APScheduler for expiration job
SERVICE_PORT = config.service_port or 8229


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    global credit_service, repository, consul_registry, event_bus, event_handlers, scheduler

    try:
        # Initialize NATS JetStream event bus
        try:
            from .events import get_event_handlers

            event_bus = await get_event_bus("credit_service")
            logger.info("✅ Event bus initialized successfully")

        except Exception as e:
            logger.warning(
                f"⚠️  Failed to initialize event bus: {e}. Continuing without event subscriptions."
            )
            event_bus = None

        # Create credit service using factory (with or without event bus)
        credit_service = create_credit_service(
            config=config_manager, event_bus=event_bus
        )

        # Initialize repository connection
        repository = credit_service.repository
        await repository.initialize()

        # Subscribe to events if event bus is available
        if event_bus:
            try:
                from .events import get_event_handlers

                # Get event handlers
                handler_map = get_event_handlers(credit_service)

                # Subscribe to events
                for pattern, handler_func in handler_map.items():
                    await event_bus.subscribe_to_events(
                        pattern=pattern,
                        handler=handler_func,
                        durable=f"credit-{pattern.replace('.', '-').replace('*', 'all')}-consumer",
                    )
                    logger.info(f"✅ Subscribed to {pattern}")

                logger.info(
                    f"✅ Credit event subscriber started ({len(handler_map)} event patterns)"
                )

            except Exception as e:
                logger.warning(f"⚠️  Failed to subscribe to events: {e}")

        # Start expiration scheduler (APScheduler)
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler

            scheduler = AsyncIOScheduler()

            # Add expiration job - runs daily at midnight
            scheduler.add_job(
                credit_service.process_expirations,
                'cron',
                hour=0,
                minute=0,
                id='credit_expiration_job',
                replace_existing=True,
            )

            scheduler.start()
            logger.info("✅ Credit expiration scheduler started (daily at midnight)")

        except Exception as e:
            logger.warning(f"⚠️  Failed to start expiration scheduler: {e}")
            scheduler = None

        # Consul service registration
        if config.consul_enabled:
            try:
                # Get route metadata
                route_meta = get_routes_for_consul()

                # Merge service metadata
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
                    f"✅ Service registered with Consul: {route_meta.get('route_count')} routes"
                )
            except Exception as e:
                logger.warning(f"⚠️  Failed to register with Consul: {e}")
                consul_registry = None

        logger.info(f"✅ Credit service started on port {SERVICE_PORT}")
        yield

    except Exception as e:
        logger.error(f"Failed to initialize credit service: {e}")
        raise
    finally:
        # Cleanup resources
        # Stop scheduler
        if scheduler:
            try:
                scheduler.shutdown()
                logger.info("✅ Credit expiration scheduler stopped")
            except Exception as e:
                logger.error(f"❌ Failed to stop scheduler: {e}")

        # Consul deregistration
        if consul_registry:
            try:
                consul_registry.deregister()
                logger.info("✅ Credit service deregistered from Consul")
            except Exception as e:
                logger.error(f"❌ Failed to deregister from Consul: {e}")

        if event_bus:
            try:
                await event_bus.close()
                logger.info("Credit event bus closed")
            except Exception as e:
                logger.error(f"Error closing event bus: {e}")

        if repository:
            await repository.close()
            logger.info("Credit service database connections closed")


# Create FastAPI application
app = FastAPI(
    title="Credit Service",
    description="Promotional credit management service with FIFO expiration",
    version="1.0.0",
    lifespan=lifespan,
)


# ====================
# Dependency Injection
# ====================


async def get_credit_service() -> CreditService:
    """Get credit service instance"""
    if not credit_service:
        raise HTTPException(status_code=503, detail="Credit service not initialized")
    return credit_service


# ====================
# Health Check and Service Info
# ====================


@app.get("/api/v1/credits/health")
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Basic health check"""
    dependencies = {}

    # Check database connection
    try:
        if repository and repository.db:
            # Use PostgresClient health check method (async, returns dict with 'healthy' key)
            result = await repository.db.health_check()
            dependencies["database"] = "healthy" if result and result.get('healthy') else "unhealthy"
        else:
            dependencies["database"] = "unhealthy"
    except Exception:
        dependencies["database"] = "unhealthy"

    # Check event bus
    try:
        if event_bus and hasattr(event_bus, 'is_connected'):
            # is_connected is a property, not a method
            dependencies["event_bus"] = "healthy" if event_bus.is_connected else "unhealthy"
        else:
            dependencies["event_bus"] = "not_configured"
    except Exception:
        dependencies["event_bus"] = "unhealthy"

    # Check scheduler
    dependencies["scheduler"] = "healthy" if scheduler and scheduler.running else "not_configured"

    status = "healthy" if all(v in ["healthy", "not_configured"] for v in dependencies.values()) else "degraded"

    return HealthResponse(
        status=status,
        service="credit_service",
        port=SERVICE_PORT,
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat(),
    )


@app.get("/health/detailed", response_model=HealthResponse)
async def health_check_detailed():
    """Detailed health check with full dependencies"""
    return await health_check()


# ====================
# Credit Account Management
# ====================


@app.post("/api/v1/credits/accounts", response_model=CreditAccountResponse)
async def create_account(
    request: CreateAccountRequest,
    service: CreditService = Depends(get_credit_service)
):
    """Create a new credit account"""
    try:
        result = await service.create_account(
            user_id=request.user_id,
            credit_type=request.credit_type,
            organization_id=request.organization_id,
            expiration_policy=request.expiration_policy,
            expiration_days=request.expiration_days,
            metadata=request.metadata
        )
        return result
    except Exception as e:
        logger.error(f"Error creating credit account: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/v1/credits/accounts", response_model=List[CreditAccountResponse])
async def list_accounts(
    user_id: str,
    credit_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    service: CreditService = Depends(get_credit_service)
):
    """List user's credit accounts"""
    try:
        result = await service.get_user_accounts(
            user_id=user_id,
            credit_type=credit_type,
            is_active=is_active
        )
        return result
    except Exception as e:
        logger.error(f"Error listing credit accounts: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/v1/credits/accounts/{account_id}", response_model=CreditAccountResponse)
async def get_account(
    account_id: str,
    service: CreditService = Depends(get_credit_service)
):
    """Get account by ID"""
    try:
        result = await service.get_account(account_id=account_id)
        if not result:
            raise HTTPException(status_code=404, detail="Credit account not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting credit account: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ====================
# Balance Operations
# ====================


@app.get("/api/v1/credits/balance", response_model=CreditBalanceResponse)
async def get_balance(
    user_id: str,
    service: CreditService = Depends(get_credit_service)
):
    """Get aggregated credit balance summary"""
    try:
        result = await service.get_balance_summary(user_id=user_id)
        return result
    except Exception as e:
        logger.error(f"Error getting credit balance: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/v1/credits/check-availability", response_model=CheckAvailabilityResponse)
async def check_availability(
    request: CheckAvailabilityRequest,
    service: CreditService = Depends(get_credit_service)
):
    """Check credit availability for consumption"""
    try:
        result = await service.check_availability(
            user_id=request.user_id,
            amount=request.amount,
            credit_type=request.credit_type
        )
        return result
    except Exception as e:
        logger.error(f"Error checking credit availability: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ====================
# Credit Operations
# ====================


@app.post("/api/v1/credits/allocate", response_model=AllocateCreditsResponse)
async def allocate_credits(
    request: AllocateCreditsRequest,
    service: CreditService = Depends(get_credit_service)
):
    """Allocate credits to user"""
    try:
        result = await service.allocate_credits(
            user_id=request.user_id,
            amount=request.amount,
            credit_type=request.credit_type,
            campaign_id=request.campaign_id,
            description=request.description,
            expires_at=request.expires_at,
            metadata=request.metadata
        )
        if not result.get("success", True):
            raise HTTPException(status_code=400, detail=result.get("message", "Allocation failed"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error allocating credits: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/v1/credits/consume", response_model=ConsumeCreditsResponse)
async def consume_credits(
    request: ConsumeCreditsRequest,
    service: CreditService = Depends(get_credit_service)
):
    """Consume credits with FIFO expiration"""
    try:
        result = await service.consume_credits(
            user_id=request.user_id,
            amount=request.amount,
            billing_record_id=request.billing_record_id,
            description=request.description,
            metadata=request.metadata
        )
        if not result.get("success", True):
            raise HTTPException(status_code=400, detail=result.get("message", "Consumption failed"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error consuming credits: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/v1/credits/transfer", response_model=TransferCreditsResponse)
async def transfer_credits(
    request: TransferCreditsRequest,
    service: CreditService = Depends(get_credit_service)
):
    """Transfer credits between users"""
    try:
        result = await service.transfer_credits(
            from_user_id=request.from_user_id,
            to_user_id=request.to_user_id,
            amount=request.amount,
            credit_type=request.credit_type,
            description=request.description,
            metadata=request.metadata
        )
        if not result.get("success", True):
            raise HTTPException(status_code=400, detail=result.get("message", "Transfer failed"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error transferring credits: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ====================
# Transaction History
# ====================


@app.get("/api/v1/credits/transactions", response_model=TransactionListResponse)
async def get_transactions(
    user_id: str,
    transaction_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
    service: CreditService = Depends(get_credit_service)
):
    """Get credit transaction history"""
    try:
        filters = {
            "transaction_type": transaction_type,
            "start_date": start_date,
            "end_date": end_date,
            "limit": limit,
            "offset": offset,
        }
        result = await service.get_transactions(user_id=user_id, filters=filters)
        return result
    except Exception as e:
        logger.error(f"Error getting credit transactions: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ====================
# Campaign Management
# ====================


@app.post("/api/v1/credits/campaigns", response_model=CampaignResponse)
async def create_campaign(
    request: CampaignRequest,
    service: CreditService = Depends(get_credit_service)
):
    """Create a new credit campaign"""
    try:
        result = await service.create_campaign(
            name=request.name,
            credit_type=request.credit_type,
            credit_amount=request.credit_amount,
            total_budget=request.total_budget,
            start_date=request.start_date,
            end_date=request.end_date,
            description=request.description,
            eligibility_rules=request.eligibility_rules,
            allocation_rules=request.allocation_rules,
            expiration_days=request.expiration_days,
            max_allocations_per_user=request.max_allocations_per_user,
            metadata=request.metadata
        )
        return result
    except Exception as e:
        logger.error(f"Error creating campaign: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/v1/credits/campaigns", response_model=List[CampaignResponse])
async def list_campaigns(
    credit_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    service: CreditService = Depends(get_credit_service)
):
    """List credit campaigns"""
    try:
        # Use get_active_campaigns method which is available in the service
        result = await service.get_active_campaigns(credit_type=credit_type)
        return result
    except Exception as e:
        logger.error(f"Error listing campaigns: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/v1/credits/campaigns/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: str,
    service: CreditService = Depends(get_credit_service)
):
    """Get campaign by ID"""
    try:
        result = await service.get_campaign(campaign_id=campaign_id)
        if not result:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting campaign: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.put("/api/v1/credits/campaigns/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: str,
    request: CampaignRequest,
    service: CreditService = Depends(get_credit_service)
):
    """Update campaign"""
    try:
        result = await service.update_campaign(campaign_id=campaign_id, updates=request)
        if not result:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating campaign: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ====================
# Statistics and Analytics
# ====================


@app.get("/api/v1/credits/statistics", response_model=CreditStatisticsResponse)
async def get_statistics(
    user_id: Optional[str] = None,
    credit_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    service: CreditService = Depends(get_credit_service)
):
    """Get credit statistics and analytics"""
    try:
        filters = {
            "user_id": user_id,
            "credit_type": credit_type,
            "start_date": start_date,
            "end_date": end_date,
        }
        result = await service.get_statistics(filters=filters)
        return result
    except Exception as e:
        logger.error(f"Error getting credit statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ====================
# Error Handling
# ====================


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception in {request.url}: {exc}", exc_info=True)
    return HTTPException(status_code=500, detail="Internal server error occurred")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "microservices.credit_service.main:app",
        host="0.0.0.0",
        port=SERVICE_PORT,
        reload=config.debug,
        log_level=config.log_level.lower(),
    )
