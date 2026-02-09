"""
Device Management Service - Main Application

设备管理微服务主应用，提供设备注册、认证、生命周期管理等功能
"""

from fastapi import FastAPI, HTTPException, Depends, Query, Path, Body, Header
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import logging
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.config_manager import ConfigManager
from core.logger import setup_service_logger
from core.service_discovery import get_service_discovery
from core.nats_client import get_event_bus
from isa_common.consul_client import ConsulRegistry
from .models import (
    DeviceRegistrationRequest, DeviceUpdateRequest, DeviceAuthRequest,
    DeviceCommandRequest, BulkCommandRequest, DeviceGroupRequest,
    DevicePairingRequest, DevicePairingResponse,
    DeviceResponse, DeviceAuthResponse, DeviceStatsResponse,
    DeviceHealthResponse, DeviceGroupResponse, DeviceListResponse,
    DeviceStatus, DeviceType, ConnectivityType
)
from .factory import create_device_service
from .routes_registry import get_routes_for_consul, SERVICE_METADATA
from microservices.organization_service.clients import OrganizationServiceClient
from microservices.auth_service.client import AuthServiceClient
from microservices.telemetry_service.clients import TelemetryServiceClient

# Initialize configuration
config_manager = ConfigManager("device_service")
config = config_manager.get_service_config()

# Setup loggers (use actual service name)
app_logger = setup_service_logger("device_service")
logger = app_logger  # for backward compatibility

# Service instance
class DeviceMicroservice:
    def __init__(self):
        self.service = None
        self.event_bus = None
        self.consul_registry = None

    async def initialize(self):
        # Initialize event bus for event-driven communication
        try:
            self.event_bus = await get_event_bus("device_service")
            logger.info("Event bus initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize event bus: {e}. Continuing without event publishing.")
            self.event_bus = None

        self.service = create_device_service(config=config_manager, event_bus=self.event_bus)
        logger.info("Device service initialized")

    async def shutdown(self):
        # Consul deregistration
        if self.consul_registry:
            try:
                self.consul_registry.deregister()
                logger.info("✅ Device service deregistered from Consul")
            except Exception as e:
                logger.error(f"❌ Failed to deregister from Consul: {e}")

        if self.event_bus:
            await self.event_bus.close()
        logger.info("Device service shutting down")

# Global instance
microservice = DeviceMicroservice()

# Lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # Startup
    await microservice.initialize()

    # Subscribe to events for firmware updates and telemetry
    if microservice.event_bus:
        try:
            from .events import DeviceEventHandler
            event_handler = DeviceEventHandler(microservice.service)

            # Subscribe to firmware.uploaded events - notify devices of updates
            await microservice.event_bus.subscribe(
                pattern="events.firmware.uploaded",
                handler=lambda msg: event_handler.handle_event(msg)
            )
            logger.info("✅ Subscribed to firmware.uploaded events")

            # Subscribe to update.completed events - update device firmware version
            await microservice.event_bus.subscribe(
                pattern="events.update.completed",
                handler=lambda msg: event_handler.handle_event(msg)
            )
            logger.info("✅ Subscribed to update.completed events")

            # Subscribe to telemetry.data.received events - update device health
            await microservice.event_bus.subscribe(
                pattern="events.telemetry.data.received",
                handler=lambda msg: event_handler.handle_event(msg)
            )
            logger.info("✅ Subscribed to telemetry.data.received events")

        except Exception as e:
            logger.error(f"Failed to subscribe to events: {e}")

    # Consul service registration
    if config.consul_enabled:
        try:
            # Get route metadata
            route_meta = get_routes_for_consul()

            # Merge service metadata
            consul_meta = {
                'version': SERVICE_METADATA['version'],
                'capabilities': ','.join(SERVICE_METADATA['capabilities']),
                **route_meta
            }

            microservice.consul_registry = ConsulRegistry(
                service_name=SERVICE_METADATA['service_name'],
                service_port=config.service_port,
                consul_host=config.consul_host,
                consul_port=config.consul_port,
                tags=SERVICE_METADATA['tags'],
                meta=consul_meta,
                health_check_type='ttl'  # Use TTL for reliable health checks
            )
            microservice.consul_registry.register()
            microservice.consul_registry.start_maintenance()  # Start TTL heartbeat
            logger.info(f"✅ Service registered with Consul: {route_meta.get('route_count')} routes")
        except Exception as e:
            logger.warning(f"⚠️  Failed to register with Consul: {e}")
            microservice.consul_registry = None

    yield

    # Shutdown
    await microservice.shutdown()

# Create FastAPI application
app = FastAPI(
    title="Device Management Service",
    description="IoT设备管理微服务 - 设备注册、认证、生命周期管理",
    version="1.0.0",
    lifespan=lifespan
)

# ======================
# Health Check Endpoints
# ======================

@app.get("/api/v1/devices/health")
@app.get("/health")
async def health_check():
    """基础健康检查"""
    return {
        "status": "healthy",
        "service": config.service_name,
        "port": config.service_port,
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health/detailed")
async def detailed_health_check():
    """详细健康检查"""
    return {
        "status": "healthy",
        "service": "device_service",
        "port": 8220,
        "version": "1.0.0",
        "components": {
            "service": "healthy",
            "mqtt_broker": "healthy",
            "device_registry": "healthy"
        }
    }

# ======================
# Dependencies
# ======================

async def get_user_context(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
    x_internal_call: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Get user context with authentication using AuthServiceClient

    For internal service calls, set header: X-Internal-Call: true
    to bypass auth (use with caution - only for trusted services)
    """
    # Allow internal service-to-service calls without auth
    if x_internal_call == "true":
        return {
            "user_id": "internal_service",
            "organization_id": None,
            "role": "service"
        }

    if not authorization and not x_api_key:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Use AuthServiceClient to verify token/API key
    try:
        async with AuthServiceClient() as auth_client:
            if authorization:
                # Verify JWT token
                token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
                logger.info(f"Verifying token with AuthServiceClient (first 50 chars): {token[:50]}...")

                result = await auth_client.verify_token(token)

                if not result or not result.get("valid"):
                    raise HTTPException(status_code=401, detail="Token verification failed")

                return {
                    "user_id": result.get("user_id", "unknown"),
                    "organization_id": result.get("organization_id"),
                    "role": result.get("role", "user")
                }

            elif x_api_key:
                # Verify API Key
                result = await auth_client.verify_api_key(x_api_key)

                if not result or not result.get("valid"):
                    raise HTTPException(status_code=401, detail="API key verification failed")

                return {
                    "user_id": result.get("user_id", "unknown"),
                    "organization_id": result.get("organization_id"),
                    "role": result.get("role", "user")
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auth service communication error: {e}")
        raise HTTPException(status_code=503, detail="Authentication service unavailable")

    raise HTTPException(status_code=401, detail="Authentication required")

# ======================
# Device CRUD Endpoints
# ======================

@app.post("/api/v1/devices", response_model=DeviceResponse)
async def register_device(
    request: DeviceRegistrationRequest = Body(...),
    user_context: Dict[str, Any] = Depends(get_user_context)
):
    """注册新设备"""
    try:
        device = await microservice.service.register_device(
            user_context["user_id"],
            request.model_dump()
        )
        if device:
            return device
        raise HTTPException(status_code=400, detail="Failed to register device")
    except Exception as e:
        logger.error(f"Error registering device: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/devices/stats", response_model=DeviceStatsResponse)
async def get_device_stats(
    user_context: Dict[str, Any] = Depends(get_user_context)
):
    """获取设备统计信息"""
    try:
        stats = await microservice.service.get_device_stats(user_context["user_id"])
        if stats:
            return stats
        raise HTTPException(status_code=404, detail="No stats available")
    except Exception as e:
        logger.error(f"Error getting device stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/devices/frames")
async def list_smart_frames(
    limit: int = Query(100, ge=1, le=500, description="Max items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    user_context: Dict[str, Any] = Depends(get_user_context)
):
    """获取智能相框列表 - 过滤现有设备API，包含家庭共享权限"""
    try:
        # Use existing device list API, filter for smart frames
        devices_response = await list_devices(
            device_type=DeviceType.SMART_FRAME,
            limit=limit,
            offset=offset,
            user_context=user_context
        )

        # Get organization service client for access checks
        org_client = OrganizationServiceClient()

        # Filter devices based on family sharing permissions
        accessible_frames = []
        for device in devices_response.devices:
            # Check if user has access via ownership or family sharing
            if device.user_id == user_context["user_id"]:
                accessible_frames.append(device)
            else:
                # TODO: Check family sharing permissions via organization service
                # has_access = await org_client.check_smart_frame_access(
                #     device.device_id, user_context["user_id"], "read"
                # )
                # if has_access:
                #     accessible_frames.append(device)
                pass

        await org_client.close()

        return {
            "frames": accessible_frames,
            "count": len(accessible_frames),
            "message": "Smart frames retrieved with family sharing permissions"
        }
    except Exception as e:
        logger.error(f"Error listing smart frames: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/devices/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: str = Path(..., description="Device ID"),
    user_context: Dict[str, Any] = Depends(get_user_context)
):
    """获取设备详情"""
    try:
        device = await microservice.service.get_device(device_id)
        if device:
            return device
        raise HTTPException(status_code=404, detail="Device not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/v1/devices/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: str = Path(..., description="Device ID"),
    request: DeviceUpdateRequest = Body(...),
    user_context: Dict[str, Any] = Depends(get_user_context)
):
    """更新设备信息"""
    try:
        # Build update data from request
        update_data = {}
        if request.device_name:
            update_data["device_name"] = request.device_name
        if request.firmware_version:
            update_data["firmware_version"] = request.firmware_version
        if request.status:
            update_data["status"] = request.status
        if request.location:
            update_data["location"] = request.location
        if request.metadata:
            update_data["metadata"] = request.metadata
        if request.group_id:
            update_data["group_id"] = request.group_id
        if request.tags:
            update_data["tags"] = request.tags

        # Call service layer to update device
        updated_device = await microservice.service.update_device(device_id, update_data)

        if updated_device:
            return updated_device
        raise HTTPException(status_code=404, detail="Device not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating device {device_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.delete("/api/v1/devices/{device_id}")
async def decommission_device(
    device_id: str = Path(..., description="Device ID"),
    user_context: Dict[str, Any] = Depends(get_user_context)
):
    """停用设备"""
    try:
        success = await microservice.service.decommission_device(device_id)
        if success:
            return {"message": "Device decommissioned successfully"}
        raise HTTPException(status_code=400, detail="Failed to decommission device")
    except Exception as e:
        logger.error(f"Error decommissioning device: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/devices", response_model=DeviceListResponse)
async def list_devices(
    status: Optional[DeviceStatus] = Query(None, description="Filter by status"),
    device_type: Optional[DeviceType] = Query(None, description="Filter by type"),
    connectivity: Optional[ConnectivityType] = Query(None, description="Filter by connectivity"),
    group_id: Optional[str] = Query(None, description="Filter by group"),
    limit: int = Query(100, ge=1, le=500, description="Max items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    user_context: Dict[str, Any] = Depends(get_user_context)
):
    """获取设备列表"""
    try:
        # Get devices from service layer
        devices = await microservice.service.list_user_devices(
            user_id=user_context["user_id"],
            device_type=device_type.value if device_type else None,
            status=status.value if status else None,
            limit=limit,
            offset=offset
        )

        # Filter by connectivity and group_id if provided (repository doesn't support these yet)
        filtered_devices = devices
        if connectivity:
            filtered_devices = [d for d in filtered_devices if d.connectivity_type == connectivity]
        if group_id:
            filtered_devices = [d for d in filtered_devices if d.group_id == group_id]

        return DeviceListResponse(
            devices=filtered_devices,
            count=len(filtered_devices),
            limit=limit,
            offset=offset,
            filters={
                "status": status,
                "device_type": device_type,
                "connectivity": connectivity,
                "group_id": group_id
            }
        )
    except Exception as e:
        logger.error(f"Error listing devices: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ======================
# Device Authentication
# ======================

@app.post("/api/v1/devices/auth", response_model=DeviceAuthResponse)
async def authenticate_device(
    request: DeviceAuthRequest = Body(...),
):
    """设备认证 - 使用 AuthServiceClient 进行验证"""
    try:
        logger.info(f"Authenticating device {request.device_id} via AuthServiceClient")

        async with AuthServiceClient() as auth_client:
            auth_result = await auth_client.authenticate_device(
                device_id=request.device_id,
                device_secret=request.device_secret
            )

            if not auth_result or not auth_result.get("authenticated"):
                raise HTTPException(status_code=401, detail="Device authentication failed")

            # 更新设备状态为活跃
            device_update = await microservice.service.update_device_status(
                request.device_id,
                DeviceStatus.ACTIVE
            )

            return DeviceAuthResponse(
                device_id=auth_result["device_id"],
                access_token=auth_result.get("access_token") or auth_result.get("token") or auth_result.get("device_token"),
                token_type=auth_result.get("token_type", "Bearer"),
                expires_in=auth_result.get("expires_in", 86400)
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error authenticating device: {e}")
        raise HTTPException(status_code=503, detail="Authentication service unavailable")

# ======================
# Device Commands
# ======================

@app.post("/api/v1/devices/{device_id}/commands")
async def send_command(
    device_id: str = Path(..., description="Device ID"),
    request: DeviceCommandRequest = Body(...),
    user_context: Dict[str, Any] = Depends(get_user_context)
):
    """向设备发送命令"""
    try:
        # First verify device exists
        device = await microservice.service.get_device(device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")

        # Send command to device
        result = await microservice.service.send_command(
            device_id,
            user_context["user_id"],
            request.model_dump()
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending command: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ======================
# Device Health & Monitoring
# ======================

async def get_device_health(
    device_id: str = Path(..., description="Device ID"),
    user_context: Dict[str, Any] = Depends(get_user_context)
):
    """获取设备健康状态"""
    try:
        health = await microservice.service.get_device_health(device_id)
        if health:
            return health
        raise HTTPException(status_code=404, detail="Device not found")
    except Exception as e:
        logger.error(f"Error getting device health: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ======================
# Device Groups
# ======================

@app.post("/api/v1/groups", response_model=DeviceGroupResponse)
async def create_device_group(
    request: DeviceGroupRequest = Body(...),
    user_context: Dict[str, Any] = Depends(get_user_context)
):
    """创建设备组"""
    try:
        group = await microservice.service.create_device_group(
            user_context["user_id"],
            request.model_dump()
        )
        if group:
            return group
        raise HTTPException(status_code=400, detail="Failed to create device group")
    except Exception as e:
        logger.error(f"Error creating device group: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/groups/{group_id}", response_model=DeviceGroupResponse)
async def get_device_group(
    group_id: str = Path(..., description="Group ID"),
    user_context: Dict[str, Any] = Depends(get_user_context)
):
    """获取设备组详情"""
    # 返回设备组信息
    pass

@app.put("/api/v1/groups/{group_id}/devices/{device_id}")
async def add_device_to_group(
    group_id: str = Path(..., description="Group ID"),
    device_id: str = Path(..., description="Device ID"),
    user_context: Dict[str, Any] = Depends(get_user_context)
):
    """将设备添加到组"""
    return {"message": f"Device {device_id} added to group {group_id}"}

# ======================
# Bulk Operations
# ======================

@app.post("/api/v1/devices/bulk/register")
async def bulk_register_devices(
    devices: List[DeviceRegistrationRequest] = Body(...),
    user_context: Dict[str, Any] = Depends(get_user_context)
):
    """批量注册设备"""
    results = []
    for device_request in devices:
        try:
            device = await microservice.service.register_device(
                user_context["user_id"],
                device_request.model_dump()
            )
            results.append({"success": True, "device_id": device.device_id if device else None})
        except Exception as e:
            results.append({"success": False, "error": str(e)})
    
    return {"results": results, "total": len(devices)}

@app.post("/api/v1/devices/bulk/commands")
async def bulk_send_commands(
    request: BulkCommandRequest = Body(...),
    user_context: Dict[str, Any] = Depends(get_user_context)
):
    """批量发送命令"""
    results = []
    
    # Create DeviceCommandRequest from flattened BulkCommandRequest
    command_obj = DeviceCommandRequest(
        command=request.command_name,
        parameters=request.parameters,
        timeout=request.timeout,
        priority=request.priority,
        require_ack=request.require_ack
    )
    
    for device_id in request.device_ids:
        try:
            result = await microservice.service.send_command(device_id, user_context["user_id"], command_obj.model_dump())
            results.append({"device_id": device_id, **result})
        except Exception as e:
            results.append({"device_id": device_id, "success": False, "error": str(e)})
    
    return {"results": results, "total": len(request.device_ids)}

# ======================
# Smart Frame Convenience Endpoints (using existing device infrastructure)
# ======================

@app.post("/api/v1/devices/frames/{frame_id}/display")
async def control_frame_display(
    frame_id: str = Path(..., description="Frame Device ID"),
    command_data: Dict[str, Any] = Body(...),
    user_context: Dict[str, Any] = Depends(get_user_context)
):
    """控制相框显示 - 使用现有设备命令API，包含权限检查"""
    try:
        # Check if user has write access to this smart frame
        device = await get_device(frame_id, user_context)

        # Check ownership or family sharing permissions
        if device.user_id != user_context["user_id"]:
            # TODO: Check family sharing permissions via organization service
            # org_client = OrganizationServiceClient()
            # has_access = await org_client.check_smart_frame_access(
            #     frame_id, user_context["user_id"], "read_write"
            # )
            # await org_client.close()
            # if not has_access:
            #     raise HTTPException(status_code=403, detail="Insufficient permissions")
            raise HTTPException(status_code=403, detail="Insufficient permissions to control this smart frame")

        # Use existing device command infrastructure
        display_command = DeviceCommandRequest(
            command="display_control",
            parameters=command_data,
            timeout=command_data.get("timeout", 30),
            priority=5  # default medium priority
        )

        result = await send_command(frame_id, display_command, user_context)
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error controlling frame display: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/devices/frames/{frame_id}/sync")
async def sync_frame_content(
    frame_id: str = Path(..., description="Frame Device ID"),
    sync_data: Dict[str, Any] = Body(...),
    user_context: Dict[str, Any] = Depends(get_user_context)
):
    """同步相框内容 - 使用现有设备命令API，包含权限检查"""
    try:
        # Check if user has write access to this smart frame
        device = await get_device(frame_id, user_context)

        # Check ownership or family sharing permissions
        if device.user_id != user_context["user_id"]:
            # TODO: Check family sharing permissions via organization service
            raise HTTPException(status_code=403, detail="Insufficient permissions to sync this smart frame")

        # Use existing device command infrastructure
        sync_command = DeviceCommandRequest(
            command="sync_content",
            parameters={
                "album_ids": sync_data.get("album_ids", []),
                "sync_type": sync_data.get("sync_type", "incremental"),
                "force": sync_data.get("force", False)
            },
            timeout=sync_data.get("timeout", 300),  # Longer timeout for sync
            priority=5  # default medium priority
        )

        result = await send_command(frame_id, sync_command, user_context)
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing frame content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/v1/devices/frames/{frame_id}/config")
async def update_frame_config(
    frame_id: str = Path(..., description="Frame Device ID"),
    config_updates: Dict[str, Any] = Body(...),
    user_context: Dict[str, Any] = Depends(get_user_context)
):
    """更新相框配置 - 使用现有设备更新API，包含权限检查"""
    try:
        # Get current device to preserve existing metadata
        current_device = await get_device(frame_id, user_context)

        # Check if user has write access to this smart frame
        if current_device.user_id != user_context["user_id"]:
            # TODO: Check family sharing permissions via organization service
            raise HTTPException(status_code=403, detail="Insufficient permissions to configure this smart frame")

        current_metadata = current_device.metadata or {}

        # Update frame-specific config in metadata
        frame_config = current_metadata.get("frame_config", {})
        frame_config.update(config_updates)

        # Use existing device update API
        update_request = DeviceUpdateRequest(
            metadata={**current_metadata, "frame_config": frame_config}
        )

        result = await update_device(frame_id, update_request, user_context)
        return {
            "success": True,
            "device_id": frame_id,
            "updated_config": frame_config,
            "message": "Frame config updated using existing device infrastructure"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating frame config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ======================
# Service Statistics
# ======================

@app.get("/api/v1/service/stats")
async def get_service_stats():
    """获取服务统计信息"""
    return {
        "service": "device_service",
        "version": "1.0.0",
        "port": 8220,
        "endpoints": {
            "health": 2,
            "devices": 8,
            "auth": 1,
            "commands": 1,
            "monitoring": 2,
            "groups": 3,
            "bulk": 2
        },
        "features": [
            "device_registration",
            "device_authentication", 
            "lifecycle_management",
            "remote_commands",
            "health_monitoring",
            "device_groups",
            "bulk_operations",
            "smart_frame_support",
            "display_control",
            "content_sync"
        ]
    }

@app.get("/api/v1/debug/consul")
async def debug_consul():
    """Debug consul registry state"""
    consul_available = hasattr(app.state, 'consul_registry') and app.state.consul_registry is not None
    consul_info = {}
    if consul_available:
        consul_info = {
            "service_name": app.state.consul_registry.service_name,
            "service_host": app.state.consul_registry.service_host,
            "service_port": app.state.consul_registry.service_port
        }
    
    return {
        "consul_available": consul_available,
        "consul_info": consul_info,
        "app_state_keys": list(vars(app.state).keys()) if hasattr(app, 'state') else []
    }

# 导入datetime
from datetime import datetime

if __name__ == "__main__":
    import uvicorn
    # Print configuration summary for debugging
    config_manager.print_config_summary()
    
    uvicorn.run(
        app, 
        host=config.service_host, 
        port=config.service_port,
        log_level=config.log_level.lower()
    )

# ============================================================================
# Device Pairing API
# ============================================================================

@app.post("/api/v1/devices/{device_id}/pair", response_model=DevicePairingResponse)
async def pair_device(
    device_id: str = Path(..., description="Device ID to pair"),
    request: DevicePairingRequest = Body(...),
    user_context: Dict[str, Any] = Depends(get_user_context)
):
    """
    Pair a device with a user using pairing token from QR code
    
    This endpoint is called by the mobile app after scanning the QR code
    displayed on the EmoFrame device.
    
    Flow:
    1. Mobile user scans QR code on Display device
    2. QR code contains: EMOFRAME:deviceId:pairingToken
    3. Mobile app calls this endpoint with device_id and pairing_token
    4. This endpoint verifies token with auth_service
    5. If valid, updates device owner and status to 'active'
    6. Publishes device.paired event
    
    Args:
        device_id: Device ID from QR code
        request: Pairing request with token and user_id
        user_context: User context from authentication
        
    Returns:
        DevicePairingResponse with success status and device info
    """
    try:
        # Get device service instance
        device_service = app.state.microservice.service
        
        # Call pairing method
        result = await device_service.pair_device(
            device_id=device_id,
            pairing_token=request.pairing_token,
            user_id=request.user_id
        )
        
        if not result.get("success"):
            return DevicePairingResponse(
                success=False,
                error=result.get("error", "Device pairing failed")
            )
        
        logger.info(f"Device {device_id} successfully paired with user {request.user_id}")
        
        return DevicePairingResponse(
            success=True,
            device=result.get("device"),
            message=f"Device {device_id} successfully paired"
        )
        
    except Exception as e:
        logger.error(f"Error in pair_device endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to pair device: {str(e)}"
        )
