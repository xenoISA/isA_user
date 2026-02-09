"""
Calendar Service - Main Application

日历事件管理微服务主应用
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import Body, FastAPI, HTTPException, Path, Query

# Add parent directory to path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from core.config_manager import ConfigManager
from core.logger import setup_service_logger
from core.nats_client import get_event_bus

from isa_common.consul_client import ConsulRegistry

from .factory import create_calendar_service
from .models import (
    EventCategory,
    EventCreateRequest,
    EventListResponse,
    EventQueryRequest,
    EventResponse,
    EventUpdateRequest,
    SyncProvider,
    SyncStatusResponse,
)
from .routes_registry import SERVICE_METADATA, get_routes_for_consul

# Initialize config
config_manager = ConfigManager("calendar_service")
config = config_manager.get_service_config()

# Setup logger
app_logger = setup_service_logger("calendar_service")
logger = app_logger


# Service instance
class CalendarMicroservice:
    def __init__(self):
        self.service = None
        self.event_bus = None

    async def initialize(self):
        # Initialize event bus
        try:
            self.event_bus = await get_event_bus("calendar_service")
            logger.info("✅ Event bus initialized successfully")
        except Exception as e:
            logger.warning(
                f"⚠️  Failed to initialize event bus: {e}. Continuing without event publishing."
            )
            self.event_bus = None

        # Create service with real dependencies using factory
        self.service = create_calendar_service(
            config=config_manager,
            event_bus=self.event_bus
        )
        logger.info("Calendar service initialized")

        # Subscribe to events
        if self.event_bus and self.service:
            try:
                from .events import CalendarEventHandlers

                event_handlers = CalendarEventHandlers(self.service)
                handler_map = event_handlers.get_event_handler_map()

                for event_type, handler_func in handler_map.items():
                    await self.event_bus.subscribe_to_events(
                        pattern=f"*.{event_type}", handler=handler_func
                    )
                    logger.info(f"✅ Subscribed to {event_type} events")

                logger.info(f"✅ Subscribed to {len(handler_map)} event types")
            except Exception as e:
                logger.error(f"❌ Failed to subscribe to events: {e}", exc_info=True)

    async def shutdown(self):
        if self.event_bus:
            try:
                await self.event_bus.close()
                logger.info("Calendar event bus closed")
            except Exception as e:
                logger.error(f"Error closing event bus: {e}")
        logger.info("Calendar service shutting down")


# Global instance
microservice = CalendarMicroservice()
consul_registry: Optional[ConsulRegistry] = None


# Lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global consul_registry

    # Startup
    await microservice.initialize()

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

    yield

    # Shutdown
    # Consul 注销
    if consul_registry:
        try:
            consul_registry.deregister()
            logger.info("✅ Service deregistered from Consul")
        except Exception as e:
            logger.error(f"❌ Failed to deregister from Consul: {e}")

    await microservice.shutdown()


# Create FastAPI application
app = FastAPI(
    title="Calendar Service",
    description="日历事件管理微服务 - Calendar event management with external sync",
    version="1.0.0",
    lifespan=lifespan,
)


# =============================================================================
# Health Check
# =============================================================================


@app.get("/api/v1/calendar/health")
@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "calendar_service", "version": "1.0.0"}


# =============================================================================
# Calendar Event Endpoints
# =============================================================================


@app.post("/api/v1/calendar/events", response_model=EventResponse, status_code=201)
async def create_event(request: EventCreateRequest = Body(...)):
    """
    创建日历事件

    Create a new calendar event
    """
    try:
        event = await microservice.service.create_event(request)

        if not event:
            raise HTTPException(status_code=500, detail="Failed to create event")

        return event

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating event: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/calendar/events/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: str = Path(..., description="Event ID"),
    user_id: Optional[str] = Query(None, description="User ID for authorization"),
):
    """
    获取事件详情

    Get event details by ID
    """
    try:
        event = await microservice.service.get_event(event_id, user_id)

        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        return event

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting event: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/calendar/events", response_model=EventListResponse)
async def list_events(
    user_id: str = Query(..., description="User ID"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    category: Optional[EventCategory] = Query(None, description="Event category"),
    limit: int = Query(100, ge=1, le=1000, description="Results per page"),
    offset: int = Query(0, ge=0, description="Offset"),
):
    """
    查询事件列表

    List events with optional filters
    """
    try:
        from datetime import datetime

        query = EventQueryRequest(
            user_id=user_id,
            start_date=datetime.fromisoformat(start_date) if start_date else None,
            end_date=datetime.fromisoformat(end_date) if end_date else None,
            category=category,
            limit=limit,
            offset=offset,
        )

        result = await microservice.service.query_events(query)
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        logger.error(f"Error listing events: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.put("/api/v1/calendar/events/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: str = Path(..., description="Event ID"),
    request: EventUpdateRequest = Body(...),
    user_id: Optional[str] = Query(None, description="User ID for authorization"),
):
    """
    更新事件

    Update an existing event
    """
    try:
        event = await microservice.service.update_event(event_id, request, user_id)

        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        return event

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating event: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/api/v1/calendar/events/{event_id}", status_code=204)
async def delete_event(
    event_id: str = Path(..., description="Event ID"),
    user_id: Optional[str] = Query(None, description="User ID for authorization"),
):
    """
    删除事件

    Delete an event
    """
    try:
        success = await microservice.service.delete_event(event_id, user_id)

        if not success:
            raise HTTPException(status_code=404, detail="Event not found")

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting event: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# =============================================================================
# Query Endpoints
# =============================================================================


@app.get("/api/v1/calendar/upcoming", response_model=List[EventResponse])
async def get_upcoming_events(
    user_id: str = Query(..., description="User ID"),
    days: int = Query(7, ge=1, le=365, description="Number of days to look ahead"),
):
    """
    获取即将到来的事件

    Get upcoming events for the next N days
    """
    try:
        events = await microservice.service.get_upcoming_events(user_id, days)
        return events

    except Exception as e:
        logger.error(f"Error getting upcoming events: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/calendar/today", response_model=List[EventResponse])
async def get_today_events(user_id: str = Query(..., description="User ID")):
    """
    获取今天的事件

    Get today's events
    """
    try:
        events = await microservice.service.get_today_events(user_id)
        return events

    except Exception as e:
        logger.error(f"Error getting today's events: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# =============================================================================
# External Calendar Sync Endpoints
# =============================================================================


@app.post("/api/v1/calendar/sync", response_model=SyncStatusResponse)
async def sync_external_calendar(
    user_id: str = Query(..., description="User ID"),
    provider: str = Query(
        ..., description="Calendar provider (google_calendar, apple_calendar, outlook)"
    ),
    credentials: dict = Body(None, description="OAuth credentials (optional)"),
):
    """
    同步外部日历

    Sync with external calendar (Google, Apple, Outlook)
    """
    try:
        result = await microservice.service.sync_with_external_calendar(
            user_id=user_id, provider=provider, credentials=credentials
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error syncing calendar: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/calendar/sync/status", response_model=SyncStatusResponse)
async def get_sync_status(
    user_id: str = Query(..., description="User ID"),
    provider: Optional[str] = Query(None, description="Calendar provider"),
):
    """
    获取同步状态

    Get sync status for external calendars
    """
    try:
        status = await microservice.service.get_sync_status(user_id, provider)

        if not status:
            raise HTTPException(status_code=404, detail="Sync status not found")

        return status

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    port = config.service_port if hasattr(config, "service_port") else 8217

    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
