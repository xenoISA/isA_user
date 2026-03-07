"""
Location Microservice

AI-powered location tracking and geofencing service
Supports real-time location tracking, geofences, places, and route management

Port: 8224
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query

from fastapi.responses import JSONResponse

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from core.config_manager import ConfigManager
from core.logger import setup_service_logger
from core.nats_client import get_event_bus
from core.graceful_shutdown import GracefulShutdown, shutdown_middleware
from core.metrics import setup_metrics

from isa_common.consul_client import ConsulRegistry

from .location_service import LocationService
from .models import (
    GeofenceCreateRequest,
    GeofenceUpdateRequest,
    LocationBatchRequest,
    LocationOperationResult,
    LocationReportRequest,
    LocationServiceStatus,
    NearbySearchRequest,
    PlaceCreateRequest,
    PlaceUpdateRequest,
    PolygonSearchRequest,
    RadiusSearchRequest,
    RouteStartRequest,
)
from .routes_registry import SERVICE_METADATA, get_routes_for_consul

# Initialize configuration
config_manager = ConfigManager("location_service")
service_config = config_manager.get_service_config()

# Setup logger
logger = setup_service_logger("location_service")

# Global service instance
location_service = None
consul_registry: Optional[ConsulRegistry] = None
shutdown_manager = GracefulShutdown("location_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    global location_service, consul_registry
    shutdown_manager.install_signal_handlers()

    logger.info("Starting Location Service...")

    # Initialize event bus
    event_bus = None
    try:
        event_bus = await get_event_bus("location_service")
        logger.info("✅ Event bus initialized successfully")
    except Exception as e:
        logger.warning(f"⚠️  Failed to initialize event bus: {e}")

    # Initialize service
    location_service = LocationService(event_bus=event_bus)

    # Check database connection
    if not await location_service.check_connection():
        logger.error("Failed to connect to database")
        raise RuntimeError("Database connection failed")

    # Consul 服务注册
    if service_config.consul_enabled:
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
                service_port=service_config.service_port,
                consul_host=service_config.consul_host,
                consul_port=service_config.consul_port,
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

    logger.info("Location Service initialized successfully")

    yield

    # Cleanup
    shutdown_manager.initiate_shutdown()
    await shutdown_manager.wait_for_drain()

    logger.info("Shutting down Location Service...")
    if event_bus:
        await event_bus.close()
        logger.info("Event bus closed")

    # Consul 注销
    if consul_registry:
        try:
            consul_registry.deregister()
            logger.info("✅ Service deregistered from Consul")
        except Exception as e:
            logger.error(f"❌ Failed to deregister from Consul: {e}")


# Create FastAPI app
app = FastAPI(
    title="Location Service",
    description="Location tracking and geofencing service with PostGIS support",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(shutdown_middleware, shutdown_manager=shutdown_manager)
setup_metrics(app, "location_service")


# ==================== Authentication ====================


async def get_authenticated_user_id(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_internal_service: Optional[str] = Header(None, alias="X-Internal-Service"),
    x_internal_service_secret: Optional[str] = Header(None, alias="X-Internal-Service-Secret"),
) -> str:
    """
    Extract user ID from verified authentication credentials.
    Supports Bearer JWT, API Key, and internal service auth.
    """
    import httpx

    # Internal service auth
    from core.auth_dependencies import INTERNAL_SERVICE_SECRET as internal_secret
    if x_internal_service == "true" and x_internal_service_secret == internal_secret:
        return "internal-service"

    auth_service_url = os.getenv("AUTH_SERVICE_URL", "http://localhost:8201")

    # Bearer JWT auth
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{auth_service_url}/api/v1/auth/verify-token",
                    json={"token": token},
                    timeout=5.0,
                )
                if response.status_code == 200:
                    result = response.json()
                    if result.get("valid") and result.get("user_id"):
                        return result["user_id"]
        except Exception as e:
            logger.warning(f"Failed to verify Bearer token: {e}")

    # API Key auth
    if x_api_key:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{auth_service_url}/api/v1/auth/verify-api-key",
                    json={"api_key": x_api_key},
                    timeout=5.0,
                )
                if response.status_code == 200:
                    result = response.json()
                    if result.get("valid") and result.get("organization_id"):
                        return result["organization_id"]
        except Exception as e:
            logger.warning(f"Failed to verify API key: {e}")

    raise HTTPException(status_code=401, detail="Authentication required")


# ==================== Health Check ====================


@app.get("/api/v1/locations/health")
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        db_connected = await location_service.check_connection()

        status = LocationServiceStatus(
            service="location_service",
            status="operational" if db_connected else "degraded",
            version="1.0.0",
            database_connected=db_connected,
            cache_connected=True,  # Placeholder
            geofencing_enabled=True,
            route_tracking_enabled=True,
            timestamp=datetime.now(),
        )

        return {
            "status": status.status,
            "service": status.service,
            "version": status.version,
            "database_connected": status.database_connected,
            "cache_connected": status.cache_connected,
            "geofencing_enabled": status.geofencing_enabled,
            "route_tracking_enabled": status.route_tracking_enabled,
            "timestamp": status.timestamp.isoformat(),
        }

    except Exception as e:
        logger.error(f"Health check error: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "location_service",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            },
        )


# ==================== Location Management ====================


@app.post("/api/v1/locations")
async def report_location(request: LocationReportRequest, user_id: str = Depends(get_authenticated_user_id)):
    """Report device location"""
    try:
        result = await location_service.report_location(request, user_id)

        if result.success:
            return result.model_dump()
        else:
            raise HTTPException(status_code=400, detail=result.message)

    except Exception as e:
        logger.error(f"Error reporting location: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/v1/locations/batch")
async def batch_report_locations(request: LocationBatchRequest, user_id: str = Depends(get_authenticated_user_id)):
    """Report multiple locations in batch"""
    try:
        result = await location_service.batch_report_locations(request, user_id)
        return result.model_dump()

    except Exception as e:
        logger.error(f"Error in batch location report: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/locations/device/{device_id}")
async def get_device_latest_location(device_id: str, user_id: str = Depends(get_authenticated_user_id)):
    """Get device's latest location"""
    try:
        location = await location_service.get_device_latest_location(device_id, user_id)

        if location:
            return location
        else:
            raise HTTPException(status_code=404, detail="Location not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting device location: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/locations/device/{device_id}/latest")
async def get_device_latest_location_alt(device_id: str, user_id: str = Depends(get_authenticated_user_id)):
    """Get device's latest location (alternative route)"""
    return await get_device_latest_location(device_id, user_id)


@app.get("/api/v1/locations/device/{device_id}/history")
async def get_device_location_history(
    device_id: str,
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_authenticated_user_id),
):
    """Get device location history"""
    try:
        locations = await location_service.get_device_location_history(
            device_id=device_id,
            user_id=user_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )

        return {"locations": locations, "count": len(locations)}

    except Exception as e:
        logger.error(f"Error getting location history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/locations/user/{target_user_id}")
async def get_user_devices_locations(target_user_id: str, user_id: str = Depends(get_authenticated_user_id)):
    """Get latest locations for all user's devices"""
    try:
        # Verify user has permission
        if target_user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        locations = await location_service.get_user_devices_locations(target_user_id)
        return {"locations": locations, "count": len(locations)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user devices locations: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/api/v1/locations/{location_id}")
async def delete_location(location_id: str):
    """Delete a location record"""
    try:
        # Implement location deletion
        raise HTTPException(status_code=501, detail="Not implemented")

    except Exception as e:
        logger.error(f"Error deleting location: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ==================== Geofence Management ====================


@app.post("/api/v1/geofences")
async def create_geofence(request: GeofenceCreateRequest, user_id: str = Depends(get_authenticated_user_id)):
    """Create a new geofence"""
    try:
        result = await location_service.create_geofence(request, user_id)

        if result.success:
            return result.model_dump()
        else:
            raise HTTPException(status_code=400, detail=result.message)

    except Exception as e:
        logger.error(f"Error creating geofence: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/geofences")
async def list_geofences(
    active_only: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_authenticated_user_id),
):
    """List geofences"""
    try:
        geofences = await location_service.list_geofences(
            user_id=user_id, active_only=active_only, limit=limit, offset=offset
        )

        return {"geofences": geofences, "count": len(geofences)}

    except Exception as e:
        logger.error(f"Error listing geofences: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/geofences/{geofence_id}")
async def get_geofence(geofence_id: str, user_id: str = Depends(get_authenticated_user_id)):
    """Get geofence details"""
    try:
        geofence = await location_service.get_geofence(geofence_id, user_id)

        if geofence:
            return geofence
        else:
            raise HTTPException(status_code=404, detail="Geofence not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting geofence: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.put("/api/v1/geofences/{geofence_id}")
async def update_geofence(geofence_id: str, request: GeofenceUpdateRequest, user_id: str = Depends(get_authenticated_user_id)):
    """Update a geofence"""
    try:
        result = await location_service.update_geofence(geofence_id, request, user_id)

        if result.success:
            return result.model_dump()
        else:
            raise HTTPException(status_code=400, detail=result.message)

    except Exception as e:
        logger.error(f"Error updating geofence: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/api/v1/geofences/{geofence_id}")
async def delete_geofence(geofence_id: str, user_id: str = Depends(get_authenticated_user_id)):
    """Delete a geofence"""
    try:
        result = await location_service.delete_geofence(geofence_id, user_id)

        if result.success:
            return result.model_dump()
        else:
            raise HTTPException(status_code=400, detail=result.message)

    except Exception as e:
        logger.error(f"Error deleting geofence: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/v1/geofences/{geofence_id}/activate")
async def activate_geofence(geofence_id: str, user_id: str = Depends(get_authenticated_user_id)):
    """Activate a geofence"""
    try:
        result = await location_service.activate_geofence(geofence_id, user_id)

        if result.success:
            return result.model_dump()
        else:
            raise HTTPException(status_code=400, detail=result.message)

    except Exception as e:
        logger.error(f"Error activating geofence: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/v1/geofences/{geofence_id}/deactivate")
async def deactivate_geofence(geofence_id: str, user_id: str = Depends(get_authenticated_user_id)):
    """Deactivate a geofence"""
    try:
        result = await location_service.deactivate_geofence(geofence_id, user_id)

        if result.success:
            return result.model_dump()
        else:
            raise HTTPException(status_code=400, detail=result.message)

    except Exception as e:
        logger.error(f"Error deactivating geofence: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/geofences/{geofence_id}/events")
async def get_geofence_events(
    geofence_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get geofence event history"""
    try:
        # Implement geofence event retrieval
        return {"events": [], "count": 0}

    except Exception as e:
        logger.error(f"Error getting geofence events: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/geofences/device/{device_id}/check")
async def check_device_in_geofences(device_id: str):
    """Check if device is currently in any geofences"""
    try:
        # Implement geofence check
        return {"geofences": [], "count": 0}

    except Exception as e:
        logger.error(f"Error checking device geofences: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ==================== Place Management ====================


@app.post("/api/v1/places")
async def create_place(request: PlaceCreateRequest, user_id: str = Depends(get_authenticated_user_id)):
    """Create a new place"""
    try:
        result = await location_service.create_place(request, user_id)

        if result.success:
            return result.model_dump()
        else:
            raise HTTPException(status_code=400, detail=result.message)

    except Exception as e:
        logger.error(f"Error creating place: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/places/user/{target_user_id}")
async def list_user_places(target_user_id: str, user_id: str = Depends(get_authenticated_user_id)):
    """List places for a user"""
    try:
        # Verify permission
        if target_user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        places = await location_service.list_user_places(target_user_id)
        return {"success": True, "data": {"places": places, "count": len(places)}}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing user places: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/places/{place_id}")
async def get_place(place_id: str, user_id: str = Depends(get_authenticated_user_id)):
    """Get place by ID"""
    try:
        place = await location_service.get_place(place_id, user_id)

        if place:
            return {"success": True, "data": place}
        else:
            raise HTTPException(status_code=404, detail="Place not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting place: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.put("/api/v1/places/{place_id}")
async def update_place(place_id: str, request: PlaceUpdateRequest, user_id: str = Depends(get_authenticated_user_id)):
    """Update a place"""
    try:
        result = await location_service.update_place(place_id, request, user_id)

        if result.success:
            return result.model_dump()
        else:
            raise HTTPException(status_code=400, detail=result.message)

    except Exception as e:
        logger.error(f"Error updating place: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/api/v1/places/{place_id}")
async def delete_place(place_id: str, user_id: str = Depends(get_authenticated_user_id)):
    """Delete a place"""
    try:
        result = await location_service.delete_place(place_id, user_id)

        if result.success:
            return result.model_dump()
        else:
            raise HTTPException(status_code=400, detail=result.message)

    except Exception as e:
        logger.error(f"Error deleting place: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ==================== Location Search ====================


@app.get("/api/v1/locations/nearby")
async def find_nearby_devices(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_meters: float = Query(..., gt=0, le=50000),
    device_types: Optional[str] = Query(None),
    time_window_minutes: int = Query(30, ge=1, le=1440),
    limit: int = Query(50, ge=1, le=500),
    user_id: str = Depends(get_authenticated_user_id),
):
    """Find devices near a location"""
    try:

        device_types_list = device_types.split(",") if device_types else None

        request = NearbySearchRequest(
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius_meters,
            device_types=device_types_list,
            time_window_minutes=time_window_minutes,
            limit=limit,
        )

        devices = await location_service.find_nearby_devices(request, user_id)
        return {"devices": devices, "count": len(devices)}

    except Exception as e:
        logger.error(f"Error finding nearby devices: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/v1/locations/search/radius")
async def search_radius(request: RadiusSearchRequest, user_id: str = Depends(get_authenticated_user_id)):
    """Search locations within a circular area"""
    try:
        locations = await location_service.search_radius(request, user_id)
        return {"locations": locations, "count": len(locations)}

    except Exception as e:
        logger.error(f"Error searching radius: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/v1/locations/search/polygon")
async def search_polygon(request: PolygonSearchRequest):
    """Search locations within a polygon area"""
    try:
        # Implement polygon search
        return {"locations": [], "count": 0}

    except Exception as e:
        logger.error(f"Error searching polygon: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/locations/distance")
async def calculate_distance(
    from_lat: float = Query(..., ge=-90, le=90),
    from_lon: float = Query(..., ge=-180, le=180),
    to_lat: float = Query(..., ge=-90, le=90),
    to_lon: float = Query(..., ge=-180, le=180),
):
    """Calculate distance between two points"""
    try:
        result = location_service.calculate_distance(from_lat, from_lon, to_lat, to_lon)
        return {
            "success": True,
            "data": {
                "from_lat": from_lat,
                "from_lon": from_lon,
                "to_lat": to_lat,
                "to_lon": to_lon,
                **result,
            },
        }

    except Exception as e:
        logger.error(f"Error calculating distance: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/distance")
async def calculate_distance_alt(
    lat1: float = Query(..., ge=-90, le=90),
    lon1: float = Query(..., ge=-180, le=180),
    lat2: float = Query(..., ge=-90, le=90),
    lon2: float = Query(..., ge=-180, le=180),
):
    """Calculate distance between two points (alternative route)"""
    return await calculate_distance(lat1, lon1, lat2, lon2)


# ==================== Statistics ====================


@app.get("/api/v1/stats/user/{target_user_id}")
async def get_user_stats(target_user_id: str, user_id: str = Depends(get_authenticated_user_id)):
    """Get location statistics for a user"""
    try:
        # Verify permission
        if target_user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        stats = await location_service.get_location_statistics(target_user_id)
        return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ==================== Server Entry Point ====================

if __name__ == "__main__":
    import uvicorn

    port = service_config.service_port
    host = "0.0.0.0"

    logger.info(f"Starting Location Service on {host}:{port}")

    uvicorn.run("main:app", host=host, port=port, reload=False, log_level="info")
