"""
Organization Microservice

组织管理微服务主应用
Port: 8212
"""

from fastapi import FastAPI, HTTPException, Depends, status, Query, Path, Header
import uvicorn
import logging
from contextlib import asynccontextmanager
import sys
import os
from typing import Optional, List
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

# Import local components
from .organization_service import (
    OrganizationService, OrganizationServiceError,
    OrganizationNotFoundError, OrganizationAccessDeniedError,
    OrganizationValidationError
)
from .family_sharing_service import FamilySharingService
from .family_sharing_repository import FamilySharingRepository
# Note: AccountServiceClient and AuthServiceClient were removed as they were unused
# If user validation is needed in the future, implement via auth_dependencies
from core.config_manager import ConfigManager
from core.logger import setup_service_logger
from core.nats_client import get_event_bus
from core.auth_dependencies import require_auth_or_internal_service, is_internal_service_request
from isa_common.consul_client import ConsulRegistry
from .routes_registry import get_routes_for_consul, SERVICE_METADATA
from .models import (
    OrganizationCreateRequest, OrganizationUpdateRequest,
    OrganizationMemberAddRequest, OrganizationMemberUpdateRequest,
    OrganizationSwitchRequest, OrganizationResponse,
    OrganizationMemberResponse, OrganizationListResponse,
    OrganizationMemberListResponse, OrganizationContextResponse,
    OrganizationStatsResponse, OrganizationUsageResponse,
    OrganizationRole, HealthResponse, ServiceInfo, ServiceStats
)
from .family_sharing_models import (
    CreateSharingRequest, UpdateSharingRequest,
    UpdateMemberSharingPermissionRequest, GetMemberSharedResourcesRequest,
    SharingResourceResponse, MemberSharingPermissionResponse,
    SharedResourceDetailResponse, MemberSharedResourcesResponse,
    SharingUsageStatsResponse, SharingResourceType, SharingStatus
)

# Initialize configuration
config_manager = ConfigManager("organization_service")
config = config_manager.get_service_config()

# Setup loggers (use actual service name)
app_logger = setup_service_logger("organization_service")
logger = app_logger  # for backward compatibility


class OrganizationMicroservice:
    """组织微服务核心类"""

    def __init__(self):
        self.organization_service = None
        self.family_sharing_service = None
        self.event_bus = None
        self.consul_registry: Optional[ConsulRegistry] = None

    async def initialize(self):
        """初始化微服务"""
        try:
            logger.info("Initializing organization microservice...")

            # Consul 服务注册
            if config.consul_enabled:
                try:
                    # 获取路由元数据
                    route_meta = get_routes_for_consul()

                    # 合并服务元数据
                    consul_meta = {
                        'version': SERVICE_METADATA['version'],
                        'capabilities': ','.join(SERVICE_METADATA['capabilities']),
                        **route_meta
                    }

                    self.consul_registry = ConsulRegistry(
                        service_name=SERVICE_METADATA['service_name'],
                        service_port=config.service_port,
                        consul_host=config.consul_host,
                        consul_port=config.consul_port,
                        tags=SERVICE_METADATA['tags'],
                        meta=consul_meta,
                        health_check_type='http'
                    )
                    self.consul_registry.register()
                    logger.info(f"Service registered with Consul: {route_meta.get('route_count', 0)} routes")
                except Exception as e:
                    logger.warning(f"Failed to register with Consul: {e}")
                    self.consul_registry = None

            # Initialize event bus for event-driven communication
            try:
                self.event_bus = await get_event_bus("organization_service")
                logger.info("Event bus initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize event bus: {e}. Continuing without event publishing.")
                self.event_bus = None

            self.organization_service = OrganizationService(event_bus=self.event_bus, config=config_manager)
            sharing_repository = FamilySharingRepository(config=config_manager)
            self.family_sharing_service = FamilySharingService(
                repository=sharing_repository,
                event_bus=self.event_bus
            )
            logger.info("Organization microservice initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize organization microservice: {e}")
            raise

    async def shutdown(self):
        """关闭微服务"""
        try:
            # Consul 注销
            if self.consul_registry:
                try:
                    self.consul_registry.deregister()
                    logger.info("Service deregistered from Consul")
                except Exception as e:
                    logger.error(f"Failed to deregister from Consul: {e}")

            if self.event_bus:
                await self.event_bus.close()
            logger.info("Organization microservice shutdown completed")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Global microservice instance
organization_microservice = OrganizationMicroservice()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Initialize microservice
    await organization_microservice.initialize()

    # Subscribe to events for cleanup and synchronization
    if organization_microservice.event_bus:
        try:
            from .events.handlers import get_event_handlers

            # Get event handlers (function-based, not class-based)
            handler_map = get_event_handlers()

            # Subscribe to events
            for event_pattern, handler_func in handler_map.items():
                # Subscribe to each event pattern (already includes service prefix)
                await organization_microservice.event_bus.subscribe_to_events(
                    pattern=event_pattern, handler=handler_func
                )
                logger.info(f"Subscribed to {event_pattern} events")

            logger.info(f"✅ Event handlers registered successfully - Subscribed to {len(handler_map)} event types")

        except Exception as e:
            logger.error(f"Failed to subscribe to events: {e}")

    # Register with Consul
    logger.info("Service discovery via Consul agent sidecar")
    
    yield
    
    # Cleanup
    if config.consul_enabled and hasattr(app.state, 'consul_registry'):
        app.state.consul_registry.stop_maintenance()
        app.state.consul_registry.deregister()
    
    await organization_microservice.shutdown()


# Create FastAPI application
app = FastAPI(
    title="Organization Service",
    description="Organization management microservice",
    version="1.0.0",
    lifespan=lifespan
)

# CORS handled by Gateway


# Dependency injection
def get_organization_service() -> OrganizationService:
    """获取组织服务实例"""
    if not organization_microservice.organization_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Organization service not initialized"
        )
    return organization_microservice.organization_service


def get_family_sharing_service() -> FamilySharingService:
    """获取家庭共享服务实例"""
    if not organization_microservice.family_sharing_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Family sharing service not initialized"
        )
    return organization_microservice.family_sharing_service


# 使用统一的认证依赖（已导入）
# get_current_user_id = require_auth_or_internal_service


# ============ Health Check Endpoints ============

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    return HealthResponse(
        status="healthy",
        service=config.service_name,
        port=config.service_port,
        version="1.0.0"
    )


@app.get("/info", response_model=ServiceInfo)
async def service_info():
    """服务信息"""
    return ServiceInfo()


@app.get("/api/v1/organizations/stats", response_model=ServiceStats)
async def get_service_stats(
    service: OrganizationService = Depends(get_organization_service)
):
    """获取服务统计"""
    # TODO: 实现实际的统计逻辑
    return ServiceStats()


# ============ Organization Management Endpoints ============

@app.post("/api/v1/organizations", response_model=OrganizationResponse)
async def create_organization(
    request: OrganizationCreateRequest,
    user_id: str = Depends(require_auth_or_internal_service),
    service: OrganizationService = Depends(get_organization_service)
):
    """创建组织"""
    try:
        return await service.create_organization(request, user_id)
    except OrganizationValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except OrganizationServiceError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/v1/organizations/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: str = Path(..., description="组织ID"),
    user_id: str = Depends(require_auth_or_internal_service),
    service: OrganizationService = Depends(get_organization_service)
):
    """获取组织信息"""
    try:
        return await service.get_organization(organization_id, user_id)
    except OrganizationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except OrganizationAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except OrganizationServiceError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.put("/api/v1/organizations/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: str = Path(..., description="组织ID"),
    request: OrganizationUpdateRequest = ...,
    user_id: str = Depends(require_auth_or_internal_service),
    service: OrganizationService = Depends(get_organization_service)
):
    """更新组织信息"""
    try:
        return await service.update_organization(organization_id, request, user_id)
    except OrganizationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except OrganizationAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except OrganizationValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except OrganizationServiceError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.delete("/api/v1/organizations/{organization_id}")
async def delete_organization(
    organization_id: str = Path(..., description="组织ID"),
    user_id: str = Depends(require_auth_or_internal_service),
    service: OrganizationService = Depends(get_organization_service)
):
    """删除组织"""
    try:
        success = await service.delete_organization(organization_id, user_id)
        if success:
            return {"message": "Organization deleted successfully"}
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete organization")
    except OrganizationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except OrganizationAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except OrganizationServiceError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/v1/organizations", response_model=OrganizationListResponse)
async def get_user_organizations(
    user_id: str = Depends(require_auth_or_internal_service),
    service: OrganizationService = Depends(get_organization_service)
):
    """获取用户所属的所有组织 (user_id from auth)"""
    try:
        return await service.get_user_organizations(user_id)
    except OrganizationServiceError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ============ Member Management Endpoints ============

@app.post("/api/v1/organizations/{organization_id}/members", response_model=OrganizationMemberResponse)
async def add_organization_member(
    organization_id: str = Path(..., description="组织ID"),
    request: OrganizationMemberAddRequest = ...,
    user_id: str = Depends(require_auth_or_internal_service),
    service: OrganizationService = Depends(get_organization_service)
):
    """添加组织成员"""
    try:
        return await service.add_organization_member(organization_id, request, user_id)
    except OrganizationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except OrganizationAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except OrganizationValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except OrganizationServiceError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/v1/organizations/{organization_id}/members", response_model=OrganizationMemberListResponse)
async def get_organization_members(
    organization_id: str = Path(..., description="组织ID"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    role: Optional[OrganizationRole] = Query(None, description="角色过滤"),
    user_id: str = Depends(require_auth_or_internal_service),
    service: OrganizationService = Depends(get_organization_service)
):
    """获取组织成员列表"""
    try:
        return await service.get_organization_members(organization_id, user_id, limit, offset, role)
    except OrganizationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except OrganizationAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except OrganizationServiceError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.put("/api/v1/organizations/{organization_id}/members/{member_user_id}", response_model=OrganizationMemberResponse)
async def update_organization_member(
    organization_id: str = Path(..., description="组织ID"),
    member_user_id: str = Path(..., description="成员用户ID"),
    request: OrganizationMemberUpdateRequest = ...,
    user_id: str = Depends(require_auth_or_internal_service),
    service: OrganizationService = Depends(get_organization_service)
):
    """更新组织成员"""
    try:
        return await service.update_organization_member(organization_id, member_user_id, request, user_id)
    except OrganizationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except OrganizationAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except OrganizationValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except OrganizationServiceError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.delete("/api/v1/organizations/{organization_id}/members/{member_user_id}")
async def remove_organization_member(
    organization_id: str = Path(..., description="组织ID"),
    member_user_id: str = Path(..., description="成员用户ID"),
    user_id: str = Depends(require_auth_or_internal_service),
    service: OrganizationService = Depends(get_organization_service)
):
    """移除组织成员"""
    try:
        success = await service.remove_organization_member(organization_id, member_user_id, user_id)
        if success:
            return {"message": "Member removed successfully"}
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to remove member")
    except OrganizationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except OrganizationAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except OrganizationValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except OrganizationServiceError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ============ Context Switching Endpoints ============

@app.post("/api/v1/organizations/context", response_model=OrganizationContextResponse)
async def switch_organization_context(
    request: OrganizationSwitchRequest,
    user_id: str = Depends(require_auth_or_internal_service),
    service: OrganizationService = Depends(get_organization_service)
):
    """切换用户上下文（组织或个人）"""
    try:
        return await service.switch_user_context(user_id, request.organization_id)
    except OrganizationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except OrganizationAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except OrganizationServiceError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ============ Statistics and Analytics Endpoints ============

@app.get("/api/v1/organizations/{organization_id}/stats", response_model=OrganizationStatsResponse)
async def get_organization_stats(
    organization_id: str = Path(..., description="组织ID"),
    user_id: str = Depends(require_auth_or_internal_service),
    service: OrganizationService = Depends(get_organization_service)
):
    """获取组织统计信息"""
    try:
        return await service.get_organization_stats(organization_id, user_id)
    except OrganizationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except OrganizationAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except OrganizationServiceError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/v1/organizations/{organization_id}/usage", response_model=OrganizationUsageResponse)
async def get_organization_usage(
    organization_id: str = Path(..., description="组织ID"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    user_id: str = Depends(require_auth_or_internal_service),
    service: OrganizationService = Depends(get_organization_service)
):
    """获取组织使用量"""
    try:
        return await service.get_organization_usage(organization_id, user_id, start_date, end_date)
    except OrganizationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except OrganizationAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except OrganizationServiceError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ============ Platform Admin Endpoints ============

@app.get("/api/v1/admin/organizations", response_model=OrganizationListResponse)
async def list_all_organizations(
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    plan: Optional[str] = Query(None, description="计划过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    user_id: str = Depends(require_auth_or_internal_service),
    service: OrganizationService = Depends(get_organization_service)
):
    """获取所有组织列表（平台管理员）"""
    try:
        # TODO: 验证用户是否是平台管理员
        return await service.list_all_organizations(limit, offset, search, plan, status)
    except OrganizationServiceError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ============ Family Sharing Endpoints ============

@app.post("/api/v1/organizations/{organization_id}/sharing", response_model=SharingResourceResponse)
async def create_sharing(
    organization_id: str = Path(..., description="组织ID"),
    request: CreateSharingRequest = ...,
    user_id: str = Depends(require_auth_or_internal_service),
    service: FamilySharingService = Depends(get_family_sharing_service)
):
    """创建共享资源"""
    try:
        logger.info(f"[API] Creating sharing | organization_id={organization_id} | resource_type={request.resource_type} | created_by={user_id}")
        return await service.create_sharing(organization_id, request, user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"[API] Failed to create sharing | organization_id={organization_id} | error={e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/v1/organizations/{organization_id}/sharing/{sharing_id}", response_model=SharedResourceDetailResponse)
async def get_sharing(
    organization_id: str = Path(..., description="组织ID"),
    sharing_id: str = Path(..., description="共享ID"),
    user_id: str = Depends(require_auth_or_internal_service),
    service: FamilySharingService = Depends(get_family_sharing_service)
):
    """获取共享资源详情"""
    try:
        return await service.get_sharing(sharing_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"[API] Failed to get sharing | sharing_id={sharing_id} | error={e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.put("/api/v1/organizations/{organization_id}/sharing/{sharing_id}", response_model=SharingResourceResponse)
async def update_sharing(
    organization_id: str = Path(..., description="组织ID"),
    sharing_id: str = Path(..., description="共享ID"),
    request: UpdateSharingRequest = ...,
    user_id: str = Depends(require_auth_or_internal_service),
    service: FamilySharingService = Depends(get_family_sharing_service)
):
    """更新共享资源"""
    try:
        logger.info(f"[API] Updating sharing | sharing_id={sharing_id} | updated_by={user_id}")
        return await service.update_sharing(sharing_id, request, user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"[API] Failed to update sharing | sharing_id={sharing_id} | error={e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.delete("/api/v1/organizations/{organization_id}/sharing/{sharing_id}")
async def delete_sharing(
    organization_id: str = Path(..., description="组织ID"),
    sharing_id: str = Path(..., description="共享ID"),
    user_id: str = Depends(require_auth_or_internal_service),
    service: FamilySharingService = Depends(get_family_sharing_service)
):
    """删除共享资源"""
    try:
        logger.info(f"[API] Deleting sharing | sharing_id={sharing_id} | deleted_by={user_id}")
        success = await service.delete_sharing(sharing_id, user_id)
        if success:
            return {"message": "Sharing deleted successfully"}
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete sharing")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"[API] Failed to delete sharing | sharing_id={sharing_id} | error={e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/v1/organizations/{organization_id}/sharing", response_model=List[SharingResourceResponse])
async def list_organization_sharings(
    organization_id: str = Path(..., description="组织ID"),
    resource_type: Optional[SharingResourceType] = Query(None, description="资源类型过滤"),
    status_filter: Optional[SharingStatus] = Query(None, alias="status", description="状态过滤"),
    limit: int = Query(50, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    user_id: str = Depends(require_auth_or_internal_service),
    service: FamilySharingService = Depends(get_family_sharing_service)
):
    """获取组织所有共享资源列表"""
    try:
        return await service.list_organization_sharings(organization_id, user_id, resource_type, status_filter, limit, offset)
    except Exception as e:
        logger.error(f"[API] Failed to list sharings | organization_id={organization_id} | error={e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.put("/api/v1/organizations/{organization_id}/sharing/{sharing_id}/members", response_model=MemberSharingPermissionResponse)
async def update_member_permission(
    organization_id: str = Path(..., description="组织ID"),
    sharing_id: str = Path(..., description="共享ID"),
    request: UpdateMemberSharingPermissionRequest = ...,
    user_id: str = Depends(require_auth_or_internal_service),
    service: FamilySharingService = Depends(get_family_sharing_service)
):
    """更新成员共享权限"""
    try:
        logger.info(f"[API] Updating member permission | sharing_id={sharing_id} | member_user_id={request.user_id} | updated_by={user_id}")
        return await service.update_member_permission(sharing_id, request, user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"[API] Failed to update member permission | sharing_id={sharing_id} | error={e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.delete("/api/v1/organizations/{organization_id}/sharing/{sharing_id}/members/{member_user_id}")
async def revoke_member_access(
    organization_id: str = Path(..., description="组织ID"),
    sharing_id: str = Path(..., description="共享ID"),
    member_user_id: str = Path(..., description="成员用户ID"),
    user_id: str = Depends(require_auth_or_internal_service),
    service: FamilySharingService = Depends(get_family_sharing_service)
):
    """撤销成员共享权限"""
    try:
        logger.info(f"[API] Revoking member access | sharing_id={sharing_id} | member_user_id={member_user_id} | revoked_by={user_id}")
        success = await service.revoke_member_access(sharing_id, member_user_id, user_id)
        if success:
            return {"message": "Member access revoked successfully"}
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to revoke member access")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"[API] Failed to revoke member access | sharing_id={sharing_id} | error={e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/v1/organizations/{organization_id}/members/{member_user_id}/shared-resources", response_model=MemberSharedResourcesResponse)
async def get_member_shared_resources(
    organization_id: str = Path(..., description="组织ID"),
    member_user_id: str = Path(..., description="成员用户ID"),
    resource_type: Optional[SharingResourceType] = Query(None, description="资源类型过滤"),
    status_filter: Optional[SharingStatus] = Query(None, alias="status", description="状态过滤"),
    limit: int = Query(50, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    user_id: str = Depends(require_auth_or_internal_service),
    service: FamilySharingService = Depends(get_family_sharing_service)
):
    """获取成员所有共享资源"""
    try:
        request = GetMemberSharedResourcesRequest(
            user_id=member_user_id,
            resource_type=resource_type,
            status=status_filter,
            limit=limit,
            offset=offset
        )
        return await service.get_member_shared_resources(organization_id, request)
    except Exception as e:
        logger.error(f"[API] Failed to get member shared resources | member_user_id={member_user_id} | error={e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/v1/organizations/{organization_id}/sharing/{sharing_id}/usage", response_model=SharingUsageStatsResponse)
async def get_sharing_usage_stats(
    organization_id: str = Path(..., description="组织ID"),
    sharing_id: str = Path(..., description="共享ID"),
    period_start: datetime = Query(..., description="统计开始时间"),
    period_end: datetime = Query(..., description="统计结束时间"),
    user_id: str = Depends(require_auth_or_internal_service),
    service: FamilySharingService = Depends(get_family_sharing_service)
):
    """获取共享资源使用统计"""
    try:
        return await service.get_sharing_usage_stats(sharing_id, user_id, period_start, period_end)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"[API] Failed to get sharing usage stats | sharing_id={sharing_id} | error={e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


if __name__ == "__main__":
    # Print configuration summary for debugging
    config_manager.print_config_summary()
    
    uvicorn.run(
        "microservices.organization_service.main:app",
        host=config.service_host,
        port=config.service_port,
        reload=config.debug,
        log_level=config.log_level.lower()
    )