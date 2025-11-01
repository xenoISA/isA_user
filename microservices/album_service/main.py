"""
Album Microservice

Album management service for smart frame ecosystem
Handles albums, album photos, and smart frame synchronization

Port: 8219
"""

import os
import sys
import asyncio
import logging
from typing import Optional, List
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from core.consul_registry import ConsulRegistry
from core.config_manager import ConfigManager
from core.logger import setup_service_logger
from core.nats_client import get_event_bus

from .models import (
    AlbumCreateRequest, AlbumUpdateRequest, AlbumResponse,
    AlbumAddPhotosRequest, AlbumRemovePhotosRequest,
    AlbumSyncRequest, AlbumSyncStatusResponse,
    AlbumListParams, AlbumListResponse,
    AlbumServiceStatus
)
from .album_service import (
    AlbumService,
    AlbumServiceError,
    AlbumNotFoundError,
    AlbumValidationError,
    AlbumPermissionError
)
from .album_repository import AlbumRepository
from .events import AlbumEventHandler

# Initialize configuration
config_manager = ConfigManager("album_service")
service_config = config_manager.get_service_config()

# Setup loggers
app_logger = setup_service_logger("album_service")
logger = app_logger

# Global service instance
album_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    global album_service

    logger.info("Starting Album Service...")

    # Initialize event bus
    event_bus = None
    try:
        event_bus = await get_event_bus("album_service")
        logger.info("✅ Event bus initialized successfully")
    except Exception as e:
        logger.warning(f"⚠️  Failed to initialize event bus: {e}. Continuing without event publishing.")
        event_bus = None

    # Initialize service with event bus
    album_service = AlbumService(event_bus=event_bus)

    # Check database connection
    db_connected = await album_service.check_connection()
    if not db_connected:
        logger.error("Failed to connect to database")
        raise RuntimeError("Database connection failed")

    # Set up event subscriptions if event bus is available
    if event_bus:
        try:
            album_repo = AlbumRepository()
            event_handler = AlbumEventHandler(album_repo)

            # Subscribe to file.deleted events
            await event_bus.subscribe(
                subject="events.file.deleted",
                callback=lambda msg: event_handler.handle_event(msg)
            )
            logger.info("✅ Subscribed to file.deleted events")

            # Note: Add device.deleted subscription when DEVICE_DELETED is added to EventType
            # await event_bus.subscribe(
            #     subject="events.device.deleted",
            #     callback=lambda msg: event_handler.handle_event(msg)
            # )

        except Exception as e:
            logger.warning(f"⚠️  Failed to set up event subscriptions: {e}")

    # Register with Consul
    if service_config.consul_enabled:
        consul_registry = ConsulRegistry(
            service_name=service_config.service_name,
            service_port=service_config.service_port,
            consul_host=service_config.consul_host,
            consul_port=service_config.consul_port,
            service_host=service_config.service_host,
            tags=["microservice", "album", "api"]
        )

        if consul_registry.register():
            consul_registry.start_maintenance()
            app.state.consul_registry = consul_registry
            logger.info(f"{service_config.service_name} registered with Consul")
        else:
            logger.warning(f"Failed to register {service_config.service_name} with Consul")
    else:
        logger.info("Consul registration disabled")

    logger.info(f"Album Service started on port {service_config.service_port}")

    yield

    # Cleanup
    if hasattr(app.state, 'consul_registry'):
        app.state.consul_registry.stop_maintenance()
        app.state.consul_registry.deregister()
        logger.info("Deregistered from Consul")

    # Close event bus
    if event_bus:
        try:
            await event_bus.close()
            logger.info("Event bus closed")
        except Exception as e:
            logger.error(f"Error closing event bus: {e}")

    logger.info("Album Service stopped")


# Initialize FastAPI app
app = FastAPI(
    title="Album Service",
    description="Album management for smart frame ecosystem",
    version="1.0.0",
    lifespan=lifespan
)


# ==================== Dependency Injection ====================

def get_album_service() -> AlbumService:
    """Get album service instance"""
    if album_service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return album_service


def get_user_id(user_id: str = Query(..., description="User ID")) -> str:
    """Extract user_id from query parameters"""
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    return user_id


# ==================== Health Check ====================

@app.get("/", response_model=AlbumServiceStatus)
async def root():
    """Root endpoint - service status"""
    db_connected = await album_service.check_connection()
    return AlbumServiceStatus(
        service="album_service",
        status="operational" if db_connected else "degraded",
        port=service_config.service_port,
        version="1.0.0",
        database_connected=db_connected,
        timestamp=datetime.now()
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    db_connected = await album_service.check_connection()
    health = {
        "status": "healthy" if db_connected else "unhealthy",
        "service": "album_service",
        "database": "connected" if db_connected else "disconnected",
        "timestamp": datetime.now().isoformat()
    }
    status_code = 200 if db_connected else 503
    return JSONResponse(content=health, status_code=status_code)


# ==================== Album Management ====================

@app.post("/api/v1/albums", response_model=AlbumResponse, status_code=201)
async def create_album(
    request: AlbumCreateRequest,
    user_id: str = Depends(get_user_id),
    service: AlbumService = Depends(get_album_service)
):
    """
    Create a new album

    Args:
        request: Album creation details
        user_id: User ID from query parameter

    Returns:
        Created album details
    """
    try:
        album = await service.create_album(request, user_id)
        return album
    except AlbumValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AlbumServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/albums/{album_id}", response_model=AlbumResponse)
async def get_album(
    album_id: str,
    user_id: str = Depends(get_user_id),
    service: AlbumService = Depends(get_album_service)
):
    """
    Get album by ID

    Args:
        album_id: Album ID
        user_id: User ID from query parameter

    Returns:
        Album details
    """
    try:
        album = await service.get_album(album_id, user_id)
        return album
    except AlbumNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AlbumPermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except AlbumServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/albums", response_model=AlbumListResponse)
async def list_user_albums(
    user_id: str = Depends(get_user_id),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    organization_id: Optional[str] = Query(None, description="Filter by organization"),
    is_family_shared: Optional[bool] = Query(None, description="Filter by family sharing"),
    service: AlbumService = Depends(get_album_service)
):
    """
    List albums for a user

    Args:
        user_id: User ID from query parameter
        page: Page number (1-indexed)
        page_size: Items per page
        organization_id: Optional organization filter
        is_family_shared: Optional family sharing filter

    Returns:
        Paginated list of albums
    """
    try:
        params = AlbumListParams(
            page=page,
            page_size=page_size,
            organization_id=organization_id,
            is_family_shared=is_family_shared
        )
        albums = await service.list_user_albums(user_id, **params.dict(exclude_none=True))
        return albums
    except AlbumServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/v1/albums/{album_id}", response_model=AlbumResponse)
async def update_album(
    album_id: str,
    request: AlbumUpdateRequest,
    user_id: str = Depends(get_user_id),
    service: AlbumService = Depends(get_album_service)
):
    """
    Update album

    Args:
        album_id: Album ID
        request: Album update details
        user_id: User ID from query parameter

    Returns:
        Updated album details
    """
    try:
        album = await service.update_album(album_id, user_id, request)
        return album
    except AlbumNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AlbumPermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except AlbumValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AlbumServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/albums/{album_id}")
async def delete_album(
    album_id: str,
    user_id: str = Depends(get_user_id),
    service: AlbumService = Depends(get_album_service)
):
    """
    Delete album

    Args:
        album_id: Album ID
        user_id: User ID from query parameter

    Returns:
        Success status
    """
    try:
        success = await service.delete_album(album_id, user_id)
        if success:
            return JSONResponse(
                content={"success": True, "message": f"Album {album_id} deleted"},
                status_code=200
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to delete album")
    except AlbumNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AlbumPermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except AlbumServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Album Photo Management ====================

@app.post("/api/v1/albums/{album_id}/photos")
async def add_photos_to_album(
    album_id: str,
    request: AlbumAddPhotosRequest,
    user_id: str = Depends(get_user_id),
    service: AlbumService = Depends(get_album_service)
):
    """
    Add photos to album

    Args:
        album_id: Album ID
        request: Photo IDs to add
        user_id: User ID from query parameter

    Returns:
        Operation result with counts
    """
    try:
        result = await service.add_photos_to_album(album_id, user_id, request)
        return JSONResponse(content=result, status_code=200)
    except AlbumNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AlbumPermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except AlbumValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AlbumServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/albums/{album_id}/photos")
async def remove_photos_from_album(
    album_id: str,
    request: AlbumRemovePhotosRequest,
    user_id: str = Depends(get_user_id),
    service: AlbumService = Depends(get_album_service)
):
    """
    Remove photos from album

    Args:
        album_id: Album ID
        request: Photo IDs to remove
        user_id: User ID from query parameter

    Returns:
        Operation result with counts
    """
    try:
        result = await service.remove_photos_from_album(album_id, user_id, request)
        return JSONResponse(content=result, status_code=200)
    except AlbumNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AlbumPermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except AlbumValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AlbumServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/albums/{album_id}/photos")
async def get_album_photos(
    album_id: str,
    user_id: str = Depends(get_user_id),
    limit: int = Query(50, ge=1, le=200, description="Maximum photos to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    service: AlbumService = Depends(get_album_service)
):
    """
    Get photos in album

    Args:
        album_id: Album ID
        user_id: User ID from query parameter
        limit: Maximum number of photos to return
        offset: Pagination offset

    Returns:
        List of album photos
    """
    try:
        photos = await service.get_album_photos(album_id, user_id, limit, offset)
        return JSONResponse(content={"photos": [p.dict() for p in photos]}, status_code=200)
    except AlbumNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AlbumPermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except AlbumServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Sync Operations ====================

@app.post("/api/v1/albums/{album_id}/sync", response_model=AlbumSyncStatusResponse)
async def sync_album_to_frame(
    album_id: str,
    request: AlbumSyncRequest,
    user_id: str = Depends(get_user_id),
    service: AlbumService = Depends(get_album_service)
):
    """
    Sync album to smart frame

    Args:
        album_id: Album ID
        request: Sync request with frame_id
        user_id: User ID from query parameter

    Returns:
        Sync status
    """
    try:
        sync_status = await service.sync_album_to_frame(album_id, user_id, request)
        return sync_status
    except AlbumNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AlbumPermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except AlbumValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AlbumServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/albums/{album_id}/sync/{frame_id}", response_model=AlbumSyncStatusResponse)
async def get_album_sync_status(
    album_id: str,
    frame_id: str,
    user_id: str = Depends(get_user_id),
    service: AlbumService = Depends(get_album_service)
):
    """
    Get album sync status for a frame

    Args:
        album_id: Album ID
        frame_id: Smart frame device ID
        user_id: User ID from query parameter

    Returns:
        Sync status details
    """
    try:
        sync_status = await service.get_album_sync_status(album_id, frame_id, user_id)
        return sync_status
    except AlbumNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AlbumPermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except AlbumServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Run Server ====================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("ALBUM_SERVICE_PORT", "8219"))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
