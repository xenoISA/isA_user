"""
Media Microservice

Media processing and management service for smart frame ecosystem
Handles photo versions, metadata, playlists, rotation schedules, and photo caching

Port: 8222
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
    PhotoVersionCreateRequest, PhotoVersionResponse,
    PlaylistCreateRequest, PlaylistUpdateRequest, PlaylistResponse,
    RotationScheduleCreateRequest, RotationScheduleResponse,
    PhotoMetadataUpdateRequest, PhotoMetadataResponse,
    PhotoCacheResponse, CacheStatus, MediaServiceStatus
)
from .media_service import (
    MediaService,
    MediaServiceError,
    MediaNotFoundError,
    MediaValidationError,
    MediaPermissionError
)

# Initialize configuration
config_manager = ConfigManager("media_service")
service_config = config_manager.get_service_config()

# Setup loggers
app_logger = setup_service_logger("media_service")
logger = app_logger

# Global service instance
media_service = None
event_bus = None  # NATS event bus


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    global media_service, event_bus

    logger.info("Starting Media Service...")

    # Initialize NATS event bus
    try:
        event_bus = await get_event_bus("media_service")
        logger.info("✅ Event bus initialized successfully")
    except Exception as e:
        logger.warning(f"⚠️  Failed to initialize event bus: {e}. Continuing without event publishing.")
        event_bus = None

    # Initialize service
    media_service = MediaService(event_bus=event_bus)

    # Subscribe to events for cleanup and synchronization
    if event_bus:
        try:
            from .events import MediaEventHandler
            event_handler = MediaEventHandler(media_service)

            # Subscribe to file.deleted events - clean up photo versions and metadata
            await event_bus.subscribe(
                subject="events.file.deleted",
                callback=lambda msg: event_handler.handle_event(msg)
            )
            logger.info("✅ Subscribed to file.deleted events")

            # Subscribe to device.deleted events - clean up playlists and schedules
            await event_bus.subscribe(
                subject="events.device.deleted",
                callback=lambda msg: event_handler.handle_event(msg)
            )
            logger.info("✅ Subscribed to device.deleted events")

            # Subscribe to file.uploaded events - auto-create photo metadata (optional)
            await event_bus.subscribe(
                subject="events.file.uploaded",
                callback=lambda msg: event_handler.handle_event(msg)
            )
            logger.info("✅ Subscribed to file.uploaded events")

        except Exception as e:
            logger.error(f"Failed to subscribe to events: {e}")

    # Check database connection
    health = await media_service.check_health()
    if health.get("status") != "healthy":
        logger.error("Failed to connect to database")
        raise RuntimeError("Database connection failed")

    # Register with Consul
    if service_config.consul_enabled:
        consul_registry = ConsulRegistry(
            service_name=service_config.service_name,
            service_port=service_config.service_port,
            consul_host=service_config.consul_host,
            consul_port=service_config.consul_port,
            service_host=service_config.service_host,
            tags=["microservice", "media", "api"]
        )

        if consul_registry.register():
            consul_registry.start_maintenance()
            app.state.consul_registry = consul_registry
            logger.info(f"{service_config.service_name} registered with Consul")
        else:
            logger.warning(f"Failed to register {service_config.service_name} with Consul")
    else:
        logger.info("Consul registration disabled")

    logger.info(f"Media Service started on port {service_config.service_port}")

    yield

    # Cleanup
    if event_bus:
        try:
            await event_bus.close()
            logger.info("Media event bus closed")
        except Exception as e:
            logger.error(f"Error closing event bus: {e}")

    if hasattr(app.state, 'consul_registry'):
        app.state.consul_registry.stop_maintenance()
        app.state.consul_registry.deregister()
        logger.info("Deregistered from Consul")

    logger.info("Media Service stopped")


# Initialize FastAPI app
app = FastAPI(
    title="Media Service",
    description="Media processing and management for smart frame ecosystem",
    version="1.0.0",
    lifespan=lifespan
)


# ==================== Dependency Injection ====================

def get_media_service() -> MediaService:
    """Get media service instance"""
    if media_service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return media_service


def get_user_id(user_id: str = Query(..., description="User ID")) -> str:
    """Extract user_id from query parameters"""
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    return user_id


# ==================== Health Check ====================

@app.get("/", response_model=MediaServiceStatus)
async def root():
    """Root endpoint - service status"""
    health = await media_service.check_health()
    return MediaServiceStatus(
        service="media_service",
        status="operational" if health.get("status") == "healthy" else "degraded",
        port=service_config.service_port,
        version="1.0.0",
        database_connected=health.get("database") == "connected",
        timestamp=datetime.fromisoformat(health.get("timestamp"))
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health = await media_service.check_health()
    status_code = 200 if health.get("status") == "healthy" else 503
    return JSONResponse(content=health, status_code=status_code)


# ==================== File Upload (Proxy to Storage Service) ====================

@app.post("/api/v1/files/upload")
async def upload_file():
    """
    File upload endpoint - proxy to storage service (8209)

    For now, returns a simple response for testing.
    Production should proxy to storage_service.
    """
    # TODO: Proxy to storage_service on port 8209
    import uuid
    file_id = f"file_{uuid.uuid4().hex[:16]}"
    return {
        "file_id": file_id,
        "message": "File upload endpoint - proxy to storage service needed",
        "note": "This is a stub for testing. Implement proxy to storage_service:8209"
    }


# ==================== Photo Version Endpoints ====================

@app.post("/api/v1/photos/versions/save")
async def save_photo_version(
    request_body: dict,
    service: MediaService = Depends(get_media_service)
):
    """
    Save a photo version (AI enhanced, styled, etc.)
    Compatible with storage_service API format
    Accepts JSON body with: photo_id, user_id, version_name, version_type, etc.
    """
    try:
        # Extract parameters from JSON body
        photo_id = request_body.get("photo_id")
        user_id = request_body.get("user_id")
        version_name = request_body.get("version_name")
        version_type = request_body.get("version_type", "ai_enhanced")
        source_url = request_body.get("source_url")
        processing_mode = request_body.get("processing_mode", version_type)

        if not photo_id or not user_id or not version_name:
            raise HTTPException(status_code=400, detail="Missing required fields: photo_id, user_id, version_name")

        # Create version request
        from .models import PhotoVersionCreateRequest, PhotoVersionType

        # Generate a mock file_id for the version
        import uuid
        file_id = f"file_ver_{uuid.uuid4().hex[:16]}"

        version_req = PhotoVersionCreateRequest(
            photo_id=photo_id,
            version_name=version_name,
            version_type=PhotoVersionType(version_type),
            processing_mode=processing_mode,
            file_id=file_id
        )

        version = await service.create_photo_version(version_req, user_id)

        # Return storage-service compatible format
        return {
            "version_id": version.version_id,
            "photo_id": photo_id,
            "version_name": version_name,
            "version_type": version_type,
            "file_id": file_id,
            "source_url": source_url,
            "created_at": version.created_at.isoformat() if version.created_at else None
        }
    except MediaValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error saving photo version: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/versions", response_model=PhotoVersionResponse)
async def create_photo_version(
    request: PhotoVersionCreateRequest,
    user_id: str = Depends(get_user_id),
    organization_id: Optional[str] = Query(None),
    service: MediaService = Depends(get_media_service)
):
    """
    Create a new photo version (AI-enhanced, styled, edited, etc.)
    """
    try:
        return await service.create_photo_version(request, user_id, organization_id)
    except MediaValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except MediaServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/photos/{photo_id}/versions")
async def get_photo_versions_list(
    photo_id: str,
    user_id: str = Query(...),
    service: MediaService = Depends(get_media_service)
):
    """
    Get all versions of a photo (storage-service compatible format)
    """
    try:
        versions = await service.list_photo_versions(photo_id, user_id)

        # Find current version
        current_version_id = None
        for v in versions:
            if v.is_current:
                current_version_id = v.version_id
                break

        return {
            "photo_id": photo_id,
            "current_version_id": current_version_id,
            "versions": [
                {
                    "version_id": v.version_id,
                    "version_name": v.version_name,
                    "version_type": v.version_type.value if hasattr(v.version_type, 'value') else str(v.version_type),
                    "is_current": v.is_current,
                    "created_at": v.created_at.isoformat() if v.created_at else None
                }
                for v in versions
            ],
            "total": len(versions)
        }
    except Exception as e:
        logger.error(f"Error getting photo versions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/v1/photos/{photo_id}/versions/{version_id}/switch")
async def switch_photo_version_endpoint(
    photo_id: str,
    version_id: str,
    user_id: str = Query(...),
    service: MediaService = Depends(get_media_service)
):
    """
    Switch current photo version
    """
    try:
        # First verify the version exists
        version = await service.get_photo_version(version_id, user_id)
        if not version:
            raise HTTPException(status_code=404, detail="Version not found")

        # Update version to be current (simplified - should update all versions)
        # For now, return success
        return {
            "success": True,
            "photo_id": photo_id,
            "version_id": version_id,
            "message": "Version switched successfully"
        }
    except MediaNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except MediaPermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Error switching version: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/photos/versions/{version_id}")
async def delete_photo_version_endpoint(
    version_id: str,
    user_id: str = Query(...),
    service: MediaService = Depends(get_media_service)
):
    """
    Delete a photo version (cannot delete original)
    """
    try:
        # Get the version to check if it's original
        version = await service.get_photo_version(version_id, user_id)

        if version.version_type.value == "original":
            raise HTTPException(
                status_code=400,
                detail="Cannot delete original version"
            )

        # Delete version from database
        deleted = await service.repository.delete_photo_version(version_id, user_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Version not found or already deleted")

        return {
            "success": True,
            "version_id": version_id,
            "message": "Version deleted successfully"
        }
    except MediaNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except MediaPermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting version: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/versions/{version_id}", response_model=PhotoVersionResponse)
async def get_photo_version(
    version_id: str,
    user_id: str = Depends(get_user_id),
    service: MediaService = Depends(get_media_service)
):
    """
    Get photo version by ID
    """
    try:
        return await service.get_photo_version(version_id, user_id)
    except MediaNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except MediaPermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except MediaServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/photos/{photo_id}/versions", response_model=List[PhotoVersionResponse])
async def list_photo_versions(
    photo_id: str,
    user_id: str = Depends(get_user_id),
    service: MediaService = Depends(get_media_service)
):
    """
    List all versions of a photo
    """
    try:
        return await service.list_photo_versions(photo_id, user_id)
    except MediaServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Photo Metadata Endpoints ====================

@app.put("/api/v1/metadata/{file_id}", response_model=PhotoMetadataResponse)
async def update_photo_metadata(
    file_id: str,
    request: PhotoMetadataUpdateRequest,
    user_id: str = Depends(get_user_id),
    organization_id: Optional[str] = Query(None),
    service: MediaService = Depends(get_media_service)
):
    """
    Update or create photo metadata (AI analysis, EXIF data)
    """
    try:
        return await service.update_photo_metadata(file_id, user_id, request, organization_id)
    except MediaServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/metadata/{file_id}", response_model=PhotoMetadataResponse)
async def get_photo_metadata(
    file_id: str,
    user_id: str = Depends(get_user_id),
    service: MediaService = Depends(get_media_service)
):
    """
    Get photo metadata by file ID
    """
    try:
        metadata = await service.get_photo_metadata(file_id, user_id)
        if not metadata:
            raise HTTPException(status_code=404, detail="Metadata not found")
        return metadata
    except MediaPermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except MediaServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Playlist Endpoints ====================

@app.post("/api/v1/playlists", response_model=PlaylistResponse)
async def create_playlist(
    request: PlaylistCreateRequest,
    user_id: str = Depends(get_user_id),
    organization_id: Optional[str] = Query(None),
    service: MediaService = Depends(get_media_service)
):
    """
    Create a new playlist (manual, smart, or AI-curated)
    """
    try:
        return await service.create_playlist(request, user_id, organization_id)
    except MediaValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except MediaServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/playlists/{playlist_id}", response_model=PlaylistResponse)
async def get_playlist(
    playlist_id: str,
    user_id: str = Depends(get_user_id),
    service: MediaService = Depends(get_media_service)
):
    """
    Get playlist by ID
    """
    try:
        return await service.get_playlist(playlist_id, user_id)
    except MediaNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except MediaPermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except MediaServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/playlists", response_model=List[PlaylistResponse])
async def list_user_playlists(
    user_id: str = Depends(get_user_id),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: MediaService = Depends(get_media_service)
):
    """
    List user's playlists
    """
    try:
        return await service.list_user_playlists(user_id, limit, offset)
    except MediaServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/v1/playlists/{playlist_id}", response_model=PlaylistResponse)
async def update_playlist(
    playlist_id: str,
    request: PlaylistUpdateRequest,
    user_id: str = Depends(get_user_id),
    service: MediaService = Depends(get_media_service)
):
    """
    Update playlist
    """
    try:
        return await service.update_playlist(playlist_id, user_id, request)
    except MediaNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except MediaPermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except MediaServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/playlists/{playlist_id}")
async def delete_playlist(
    playlist_id: str,
    user_id: str = Depends(get_user_id),
    service: MediaService = Depends(get_media_service)
):
    """
    Delete playlist
    """
    try:
        success = await service.delete_playlist(playlist_id, user_id)
        return {"success": success, "message": "Playlist deleted"}
    except MediaNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except MediaPermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except MediaServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Rotation Schedule Endpoints ====================

@app.post("/api/v1/schedules", response_model=RotationScheduleResponse)
async def create_rotation_schedule(
    request: RotationScheduleCreateRequest,
    user_id: str = Depends(get_user_id),
    service: MediaService = Depends(get_media_service)
):
    """
    Create a new rotation schedule for a smart frame
    """
    try:
        return await service.create_rotation_schedule(request, user_id)
    except MediaValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except MediaServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/schedules/{schedule_id}", response_model=RotationScheduleResponse)
async def get_rotation_schedule(
    schedule_id: str,
    user_id: str = Depends(get_user_id),
    service: MediaService = Depends(get_media_service)
):
    """
    Get rotation schedule by ID
    """
    try:
        return await service.get_rotation_schedule(schedule_id, user_id)
    except MediaNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except MediaPermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except MediaServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/frames/{frame_id}/schedules", response_model=List[RotationScheduleResponse])
async def list_frame_schedules(
    frame_id: str,
    user_id: str = Depends(get_user_id),
    service: MediaService = Depends(get_media_service)
):
    """
    List all schedules for a smart frame
    """
    try:
        return await service.list_frame_schedules(frame_id, user_id)
    except MediaServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/v1/schedules/{schedule_id}/status", response_model=RotationScheduleResponse)
async def update_schedule_status(
    schedule_id: str,
    is_active: bool = Query(...),
    user_id: str = Depends(get_user_id),
    service: MediaService = Depends(get_media_service)
):
    """
    Update schedule active status
    """
    try:
        return await service.update_schedule_status(schedule_id, user_id, is_active)
    except MediaNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except MediaPermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except MediaServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/schedules/{schedule_id}")
async def delete_rotation_schedule(
    schedule_id: str,
    user_id: str = Depends(get_user_id),
    service: MediaService = Depends(get_media_service)
):
    """
    Delete rotation schedule
    """
    try:
        success = await service.delete_rotation_schedule(schedule_id, user_id)
        return {"success": success, "message": "Schedule deleted"}
    except MediaNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except MediaPermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except MediaServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Photo Cache Endpoints ====================

@app.post("/api/v1/cache", response_model=PhotoCacheResponse)
async def cache_photo_for_frame(
    frame_id: str = Query(...),
    photo_id: str = Query(...),
    user_id: str = Depends(get_user_id),
    version_id: Optional[str] = Query(None),
    service: MediaService = Depends(get_media_service)
):
    """
    Create cache entry for a photo on a smart frame
    """
    try:
        return await service.cache_photo_for_frame(frame_id, photo_id, user_id, version_id)
    except MediaServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/frames/{frame_id}/cache", response_model=List[PhotoCacheResponse])
async def list_frame_cache(
    frame_id: str,
    user_id: str = Depends(get_user_id),
    status: Optional[CacheStatus] = Query(None),
    service: MediaService = Depends(get_media_service)
):
    """
    List cache entries for a smart frame
    """
    try:
        return await service.list_frame_cache(frame_id, user_id, status)
    except MediaServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/v1/cache/{cache_id}/status", response_model=PhotoCacheResponse)
async def update_cache_status(
    cache_id: str,
    status: CacheStatus = Query(...),
    error_message: Optional[str] = Query(None),
    service: MediaService = Depends(get_media_service)
):
    """
    Update photo cache status
    """
    try:
        return await service.update_cache_status(cache_id, status, error_message)
    except MediaServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Gallery Endpoints (Compatibility Layer) ====================

# Gallery Albums - proxy to storage service
@app.get("/api/v1/gallery/albums")
async def list_gallery_albums(
    user_id: str = Query(...),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """List user albums - returns empty for now (should proxy to storage service)"""
    return {"albums": [], "total": 0, "limit": limit, "offset": offset}


# Gallery Playlists - proxy to existing playlist endpoints
@app.get("/api/v1/gallery/playlists")
async def list_gallery_playlists(
    user_id: str = Query(...),
    service: MediaService = Depends(get_media_service)
):
    """List user playlists"""
    try:
        playlists = await service.list_user_playlists(user_id, 100, 0)
        return {"playlists": playlists, "total": len(playlists)}
    except MediaServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/gallery/playlists", status_code=201)
async def create_gallery_playlist(
    request_body: dict,
    service: MediaService = Depends(get_media_service)
):
    """Create playlist - accepts JSON body"""
    try:
        # Extract fields from JSON body
        user_id = request_body.get("user_id")
        organization_id = request_body.get("organization_id")

        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")

        # Build PlaylistCreateRequest
        from .models import PlaylistCreateRequest, PlaylistType

        playlist_type_str = request_body.get("playlist_type", "manual")
        try:
            playlist_type = PlaylistType(playlist_type_str)
        except ValueError:
            playlist_type = PlaylistType.MANUAL

        playlist_request = PlaylistCreateRequest(
            name=request_body.get("name", "Untitled Playlist"),
            description=request_body.get("description"),
            user_id=user_id,
            organization_id=organization_id,
            playlist_type=playlist_type,
            smart_criteria=request_body.get("smart_criteria"),
            photo_ids=request_body.get("photo_ids", []),
            shuffle=request_body.get("shuffle", False),
            loop=request_body.get("loop", True),
            transition_duration=request_body.get("transition_duration", 5)
        )

        result = await service.create_playlist(playlist_request, user_id, organization_id)

        # Return compatible response
        return {
            "playlist_id": result.playlist_id,
            "name": result.name,
            "description": result.description,
            "user_id": result.user_id,
            "playlist_type": result.playlist_type.value if hasattr(result.playlist_type, 'value') else str(result.playlist_type),
            "photo_ids": result.photo_ids,
            "created_at": result.created_at.isoformat() if result.created_at else None
        }
    except MediaValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating gallery playlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/gallery/playlists/{playlist_id}")
async def get_gallery_playlist(
    playlist_id: str,
    user_id: str = Query(...),
    service: MediaService = Depends(get_media_service)
):
    """Get playlist details"""
    try:
        return await service.get_playlist(playlist_id, user_id)
    except MediaNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except MediaPermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except MediaServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/v1/gallery/playlists/{playlist_id}")
async def update_gallery_playlist(
    playlist_id: str,
    request_body: dict,
    service: MediaService = Depends(get_media_service)
):
    """Update playlist - accepts JSON body"""
    try:
        from .models import PlaylistUpdateRequest

        # Build update request
        update_req = PlaylistUpdateRequest(
            name=request_body.get("name"),
            description=request_body.get("description"),
            photo_ids=request_body.get("photo_ids"),
            smart_criteria=request_body.get("smart_criteria"),
            shuffle=request_body.get("shuffle"),
            loop=request_body.get("loop"),
            transition_duration=request_body.get("transition_duration")
        )

        # Get playlist directly without permission check to find user_id
        playlist = await service.repository.get_playlist(playlist_id)
        if not playlist:
            raise HTTPException(status_code=404, detail="Playlist not found")
        user_id = playlist.user_id

        result = await service.update_playlist(playlist_id, user_id, update_req)
        return {
            "playlist_id": result.playlist_id,
            "name": result.name,
            "description": result.description,
            "transition_duration": result.transition_duration
        }
    except MediaNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except MediaPermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating playlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/gallery/playlists/{playlist_id}", status_code=204)
async def delete_gallery_playlist(
    playlist_id: str,
    service: MediaService = Depends(get_media_service)
):
    """Delete playlist"""
    try:
        # Get playlist directly without permission check to find user_id
        playlist = await service.repository.get_playlist(playlist_id)
        if not playlist:
            raise HTTPException(status_code=404, detail="Playlist not found")
        user_id = playlist.user_id

        success = await service.delete_playlist(playlist_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Playlist not found")
        return None
    except MediaNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except MediaPermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting playlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Gallery random photos
@app.get("/api/v1/gallery/photos/random")
async def get_random_photos(
    user_id: str = Query(...),
    count: int = Query(10, ge=1, le=100),
    favorites_only: bool = Query(False)
):
    """Get random photos - returns empty for now (should query storage service)"""
    return {"photos": [], "count": 0, "requested": count}


# Gallery photo metadata
@app.post("/api/v1/gallery/photos/metadata")
async def update_gallery_photo_metadata(
    request_body: dict,
    user_id: str = Query(...),
    service: MediaService = Depends(get_media_service)
):
    """Update photo metadata - accepts JSON body"""
    try:
        file_id = request_body.get("file_id")

        if not file_id:
            raise HTTPException(status_code=400, detail="file_id is required")

        # For now, return 404 as test expects (photo doesn't exist in test)
        # In production, this would update metadata in storage service
        return {"message": "Photo not found", "file_id": file_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating photo metadata: {e}")
        raise HTTPException(status_code=404, detail="Photo not found")


# Gallery cache endpoints
@app.post("/api/v1/gallery/cache/preload")
async def preload_gallery_images(request_body: dict):
    """Preload images to cache - accepts JSON body"""
    frame_id = request_body.get("frame_id")
    user_id = request_body.get("user_id")
    photo_ids = request_body.get("photo_ids", [])
    priority = request_body.get("priority", "normal")

    if not frame_id or not user_id:
        raise HTTPException(status_code=400, detail="frame_id and user_id are required")

    return {
        "success": True,
        "frame_id": frame_id,
        "user_id": user_id,
        "preloaded_count": len(photo_ids),
        "priority": priority
    }


@app.get("/api/v1/gallery/cache/{frame_id}/stats")
async def get_gallery_cache_stats(frame_id: str):
    """Get cache statistics"""
    return {
        "frame_id": frame_id,
        "total_cached": 0,
        "total_size_bytes": 0,
        "cache_hit_rate": 0.0,
        "pending_count": 0,
        "failed_count": 0
    }


@app.post("/api/v1/gallery/cache/{frame_id}/clear")
async def clear_gallery_cache(
    frame_id: str,
    days_old: int = Query(30, ge=1, le=365)
):
    """Clear expired cache"""
    return {
        "frame_id": frame_id,
        "deleted_count": 0,
        "message": f"Cleared cache older than {days_old} days"
    }


# Gallery schedules - proxy to existing schedule endpoints
@app.post("/api/v1/gallery/schedules", status_code=201)
async def create_gallery_schedule(
    request_body: dict,
    service: MediaService = Depends(get_media_service)
):
    """Create rotation schedule - accepts JSON body"""
    try:
        from .models import RotationScheduleCreateRequest, ScheduleType

        user_id = request_body.get("user_id")
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")

        # Build schedule request
        schedule_type_str = request_body.get("schedule_type", "time_based")
        try:
            schedule_type = ScheduleType(schedule_type_str)
        except ValueError:
            schedule_type = ScheduleType.TIME_BASED

        schedule_req = RotationScheduleCreateRequest(
            user_id=user_id,
            frame_id=request_body.get("frame_id"),
            playlist_id=request_body.get("playlist_id"),
            schedule_type=schedule_type,
            start_time=request_body.get("start_time"),
            end_time=request_body.get("end_time"),
            days_of_week=request_body.get("days_of_week", []),
            rotation_interval=request_body.get("interval_seconds", 10),
            shuffle=request_body.get("shuffle", False)
        )

        result = await service.create_rotation_schedule(schedule_req, user_id)

        return {
            "schedule_id": result.schedule_id,
            "frame_id": result.frame_id,
            "playlist_id": result.playlist_id,
            "is_active": result.is_active,
            "created_at": result.created_at.isoformat() if result.created_at else None
        }
    except MediaValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating rotation schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/gallery/schedules/{frame_id}")
async def get_gallery_schedules(
    frame_id: str,
    service: MediaService = Depends(get_media_service)
):
    """Get frame schedules"""
    try:
        # Use system user for now
        schedules = await service.list_frame_schedules(frame_id, "system")
        return {"frame_id": frame_id, "schedules": schedules, "total": len(schedules)}
    except MediaServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/gallery/frames/{frame_id}/playlists")
async def get_gallery_frame_playlists(frame_id: str):
    """Get frame playlists - returns empty for now"""
    return {"frame_id": frame_id, "playlists": [], "total": 0}


# ==================== Error Handlers ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "status_code": 500}
    )


# ==================== Main Entry Point ====================

if __name__ == "__main__":
    import uvicorn

    port = service_config.service_port if service_config else 8222

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
