"""
Session Microservice

Responsibilities:
- Session management (CRUD operations)
- Session message management
- Session statistics and analytics
Note: Session memory is handled by dedicated memory_service
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
    ErrorResponse,
    MemoryCreateRequest,
    MemoryResponse,
    MemoryUpdateRequest,
    MessageCreateRequest,
    MessageListResponse,
    MessageResponse,
    SessionCreateRequest,
    SessionListResponse,
    SessionResponse,
    SessionServiceStatus,
    SessionStatsResponse,
    SessionSummaryResponse,
    SessionUpdateRequest,
)
from .routes_registry import SERVICE_METADATA, get_routes_for_consul

# Import local components
from .session_service import (
    MemoryNotFoundError,
    MessageNotFoundError,
    SessionNotFoundError,
    SessionService,
    SessionServiceError,
    SessionValidationError,
)

# Initialize configuration
config_manager = ConfigManager("session_service")
config = config_manager.get_service_config()

# Setup loggers (use actual service name)
app_logger = setup_service_logger("session_service")
logger = app_logger  # for backward compatibility


class SessionMicroservice:
    """Session microservice core class"""

    def __init__(self):
        self.session_service = None
        self.event_bus = None
        self.consul_registry = None

    async def initialize(self, event_bus=None):
        """Initialize the microservice"""
        try:
            self.event_bus = event_bus
            self.session_service = SessionService(
                event_bus=event_bus, config=config_manager
            )
            logger.info("Session microservice initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize session microservice: {e}")
            raise

    async def shutdown(self):
        """Shutdown the microservice"""
        try:
            # Consul deregistration
            if self.consul_registry:
                try:
                    self.consul_registry.deregister()
                    logger.info("✅ Session service deregistered from Consul")
                except Exception as e:
                    logger.error(f"❌ Failed to deregister from Consul: {e}")

            if self.event_bus:
                await self.event_bus.close()
                logger.info("Event bus closed")
            logger.info("Session microservice shutdown completed")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Global microservice instance
session_microservice = SessionMicroservice()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Initialize event bus
    event_bus = None
    try:
        event_bus = await get_event_bus("session_service")
        logger.info("✅ Event bus initialized successfully")
    except Exception as e:
        logger.warning(
            f"⚠️  Failed to initialize event bus: {e}. Continuing without event publishing."
        )
        event_bus = None

    # Initialize microservice with event bus
    await session_microservice.initialize(event_bus=event_bus)

    # Subscribe to events if event bus is available
    if event_bus and session_microservice.session_service:
        try:
            from .events import SessionEventHandlers

            event_handlers = SessionEventHandlers(session_microservice.session_service)
            handler_map = event_handlers.get_event_handler_map()

            for event_type, handler_func in handler_map.items():
                # Subscribe to each event type
                await event_bus.subscribe_to_events(
                    pattern=f"*.{event_type}", handler=handler_func
                )
                logger.info(f"✅ Subscribed to {event_type} events")

            logger.info(f"✅ Subscribed to {len(handler_map)} event types")
        except Exception as e:
            logger.warning(f"⚠️  Failed to subscribe to events: {e}")

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

            session_microservice.consul_registry = ConsulRegistry(
                service_name=SERVICE_METADATA["service_name"],
                service_port=config.service_port,
                consul_host=config.consul_host,
                consul_port=config.consul_port,
                tags=SERVICE_METADATA["tags"],
                meta=consul_meta,
                health_check_type="http",
            )
            session_microservice.consul_registry.register()
            logger.info(
                f"✅ Service registered with Consul: {route_meta.get('route_count')} routes"
            )
        except Exception as e:
            logger.warning(f"⚠️  Failed to register with Consul: {e}")
            session_microservice.consul_registry = None

    yield

    # Cleanup
    await session_microservice.shutdown()


# Create FastAPI application
app = FastAPI(
    title="Session Service",
    description="Session management microservice",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS handled by Gateway


# Dependency injection
def get_session_service() -> SessionService:
    """Get session service instance"""
    if not session_microservice.session_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Session service not initialized",
        )
    return session_microservice.session_service


# Health check endpoints
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
    session_service: SessionService = Depends(get_session_service),
):
    """Detailed health check"""
    try:
        health_data = await session_service.health_check()
        return SessionServiceStatus(
            database_connected=health_data["status"] == "healthy",
            timestamp=health_data["timestamp"],
        )
    except Exception as e:
        return SessionServiceStatus(database_connected=False, timestamp=None)


# Session management endpoints


@app.post("/api/v1/sessions", response_model=SessionResponse)
async def create_session(
    request: SessionCreateRequest,
    session_service: SessionService = Depends(get_session_service),
):
    """Create new session"""
    try:
        return await session_service.create_session(request)
    except SessionValidationError as e:
        logger.error(f"Session validation error: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except SessionServiceError as e:
        logger.error(f"Session service error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error creating session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}",
        )


# Service statistics - must be before {session_id} route
@app.get("/api/v1/sessions/stats", response_model=SessionStatsResponse)
async def get_session_stats(
    session_service: SessionService = Depends(get_session_service),
):
    """Get session service statistics"""
    try:
        return await session_service.get_service_stats()
    except SessionServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.get("/api/v1/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    user_id: Optional[str] = Query(None, description="User ID for authorization"),
    session_service: SessionService = Depends(get_session_service),
):
    """Get session by ID"""
    try:
        return await session_service.get_session(session_id, user_id)
    except SessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except SessionServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.put("/api/v1/sessions/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    request: SessionUpdateRequest,
    user_id: Optional[str] = Query(None, description="User ID for authorization"),
    session_service: SessionService = Depends(get_session_service),
):
    """Update session"""
    try:
        return await session_service.update_session(session_id, request, user_id)
    except SessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except SessionValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except SessionServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.delete("/api/v1/sessions/{session_id}")
async def end_session(
    session_id: str,
    user_id: Optional[str] = Query(None, description="User ID for authorization"),
    session_service: SessionService = Depends(get_session_service),
):
    """End session"""
    try:
        success = await session_service.end_session(session_id, user_id)
        if success:
            return {"message": "Session ended successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to end session",
            )
    except SessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except SessionServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.get("/api/v1/sessions", response_model=SessionListResponse)
async def get_user_sessions(
    user_id: str = Query(..., description="User ID to filter sessions"),
    active_only: bool = Query(False, description="Only return active sessions"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    session_service: SessionService = Depends(get_session_service),
):
    """Get user sessions (filtered by user_id query parameter)"""
    try:
        return await session_service.get_user_sessions(
            user_id, active_only, page, page_size
        )
    except SessionServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.get("/api/v1/sessions/{session_id}/summary", response_model=SessionSummaryResponse)
async def get_session_summary(
    session_id: str,
    user_id: Optional[str] = Query(None, description="User ID for authorization"),
    session_service: SessionService = Depends(get_session_service),
):
    """Get session summary"""
    try:
        return await session_service.get_session_summary(session_id, user_id)
    except SessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except SessionServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# Message management endpoints


@app.post("/api/v1/sessions/{session_id}/messages", response_model=MessageResponse)
async def add_message(
    session_id: str,
    request: MessageCreateRequest,
    user_id: Optional[str] = Query(None, description="User ID for authorization"),
    session_service: SessionService = Depends(get_session_service),
):
    """Add message to session"""
    try:
        return await session_service.add_message(session_id, request, user_id)
    except SessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except SessionValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except SessionServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.get("/api/v1/sessions/{session_id}/messages", response_model=MessageListResponse)
async def get_session_messages(
    session_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=200, description="Items per page"),
    user_id: Optional[str] = Query(None, description="User ID for authorization"),
    session_service: SessionService = Depends(get_session_service),
):
    """Get session messages"""
    try:
        return await session_service.get_session_messages(
            session_id, page, page_size, user_id
        )
    except SessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except SessionServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# Note: Memory management is handled by dedicated memory_service
# See microservices/memory_service for session memory functionality


# Moved stats route to before session_id route to avoid conflicts


# Error handlers
@app.exception_handler(SessionValidationError)
async def validation_error_handler(request, exc):
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@app.exception_handler(SessionNotFoundError)
async def not_found_error_handler(request, exc):
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@app.exception_handler(SessionServiceError)
async def service_error_handler(request, exc):
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
    )


if __name__ == "__main__":
    # Print configuration summary for debugging
    config_manager.print_config_summary()

    uvicorn.run(
        "microservices.session_service.main:app",
        host=config.service_host,
        port=config.service_port,
        reload=config.debug,
        log_level=config.log_level.lower(),
    )
