"""
Billing Microservice API

专注于使用量跟踪、费用计算和计费处理的REST API服务
"""

import asyncio
import inspect
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request

# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from core.config_manager import ConfigManager
from core.graceful_shutdown import GracefulShutdown, shutdown_middleware
from core.metrics import setup_metrics
from core.logger import setup_service_logger
from core.nats_client import get_event_bus

from isa_common.consul_client import ConsulRegistry

from core.admin_audit import publish_admin_action
from core.health import HealthCheck

from .billing_repository import BillingRepository
from .billing_service import BillingService
from .factory import create_billing_service
from .models import (
    BillingCalculationRequest,
    BillingCalculationResponse,
    BillingRecordsListResponse,
    BillingStats,
    HealthResponse,
    ProcessBillingRequest,
    ProcessBillingResponse,
    QuotaCheckRequest,
    QuotaCheckResponse,
    RecordUsageRequest,
    ServiceInfo,
    UserQuotaResponse,
    UsageStatsRequest,
    UsageStatsResponse,
)
from .routes_registry import SERVICE_METADATA, get_routes_for_consul

# 初始化配置管理器
config_manager = ConfigManager("billing_service")
config = config_manager.get_service_config()

# 配置日志
logger = setup_service_logger("billing_service", level=config.log_level.upper())

# 打印配置信息（开发环境）
if config.debug:
    config_manager.print_config_summary(show_secrets=False)

# 全局变量
billing_service: Optional[BillingService] = None
repository: Optional[BillingRepository] = None
event_bus = None  # NATS event bus
event_handlers = None  # Event handlers
consul_registry = None  # Consul service registry
SERVICE_PORT = config.service_port or 8216
shutdown_manager = GracefulShutdown("billing_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    shutdown_manager.install_signal_handlers()
    global billing_service, repository, consul_registry, event_bus, event_handlers

    try:
        # Initialize NATS JetStream event bus
        try:
            from .events import get_event_handlers

            event_bus = await get_event_bus("billing_service")
            logger.info("✅ Event bus initialized successfully")

        except Exception as e:
            logger.warning(
                f"⚠️  Failed to initialize event bus: {e}. Continuing without event subscriptions."
            )
            event_bus = None

        # Create billing service using factory (with or without event bus)
        billing_service = create_billing_service(
            config=config_manager, event_bus=event_bus
        )

        # Initialize repository connection
        repository = billing_service.repository
        await repository.initialize()

        # Subscribe to events if event bus is available
        if event_bus:
            try:
                from .events import get_event_handlers

                # Get event handlers
                handler_map = get_event_handlers(billing_service, event_bus)
                consumer_suffix = os.getenv("BILLING_CONSUMER_SUFFIX", "").strip()
                delivery_policy = os.getenv(
                    "BILLING_CONSUMER_DELIVERY_POLICY", "new"
                ).strip().lower() or "all"

                # Subscribe to events
                for pattern, handler_func in handler_map.items():
                    durable_name = (
                        f"billing-{pattern.replace('.', '-').replace('*', 'all')}"
                        f"-consumer"
                    )
                    if consumer_suffix:
                        durable_name = f"{durable_name}-{consumer_suffix}"
                    await event_bus.subscribe_to_events(
                        pattern=pattern,
                        handler=handler_func,
                        durable=durable_name,
                        delivery_policy=delivery_policy,
                    )
                    logger.info(f"✅ Subscribed to {pattern}")

                logger.info(
                    f"✅ Billing event subscriber started ({len(handler_map)} event patterns, "
                    f"delivery_policy={delivery_policy}, suffix={consumer_suffix or 'default'})"
                )

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

        logger.info(f"✅ Billing service started on port {SERVICE_PORT}")
        yield

    except Exception as e:
        logger.error(f"Failed to initialize billing service: {e}")
        raise
    finally:
        # 清理资源
        shutdown_manager.initiate_shutdown()
        await shutdown_manager.wait_for_drain()
        # Consul deregistration
        if consul_registry:
            try:
                consul_registry.deregister()
                logger.info("✅ Billing service deregistered from Consul")
            except Exception as e:
                logger.error(f"❌ Failed to deregister from Consul: {e}")

        if event_bus:
            try:
                await event_bus.close()
                logger.info("Billing event bus closed")
            except Exception as e:
                logger.error(f"Error closing event bus: {e}")

        if repository:
            await repository.close()
            logger.info("Billing service database connections closed")


# 创建 FastAPI 应用
app = FastAPI(
    title="Billing Service",
    description="专注于使用量跟踪、费用计算和计费处理",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(shutdown_middleware, shutdown_manager=shutdown_manager)
setup_metrics(app, "billing_service")


# ====================
# 依赖注入
# ====================


async def get_billing_service() -> BillingService:
    """获取计费服务实例"""
    if not billing_service:
        raise HTTPException(status_code=503, detail="Billing service not initialized")
    return billing_service


# ====================
# 健康检查和服务信息
# ====================


health = HealthCheck("billing_service", version="1.0.0", shutdown_manager=shutdown_manager)
health.add_postgres(lambda: repository.db if repository else None)
health.add_nats(lambda: event_bus)
health.add_minio(lambda: s3_client)


@app.get("/api/v1/billing/health")
@app.get("/health")
async def health_check():
    """Service health check"""
    return await health.check()

@app.get("/api/v1/billing/info", response_model=ServiceInfo)
async def get_service_info():
    """获取服务信息"""
    return ServiceInfo(
        service="billing_service",
        version="1.0.0",
        description="专注于使用量跟踪、费用计算和计费处理的微服务",
        capabilities=[
            "usage_tracking",
            "cost_calculation",
            "billing_processing",
            "quota_management",
            "billing_analytics",
        ],
        supported_services=[
            "model_inference",
            "mcp_service",
            "agent_execution",
            "storage_minio",
            "api_gateway",
            "notification",
        ],
        supported_billing_methods=[
            "wallet_deduction",
            "payment_charge",
            "credit_consumption",
            "subscription_credit",
            "subscription_included",
        ],
    )


# ====================
# 核心计费API
# ====================


@app.post("/api/v1/billing/usage/record", response_model=ProcessBillingResponse)
async def record_usage_and_bill(
    request: RecordUsageRequest, service: BillingService = Depends(get_billing_service)
):
    """记录使用量并立即计费（核心API）"""
    try:
        result = await service.record_usage_and_bill(request)

        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in record_usage_and_bill: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/v1/billing/calculate", response_model=BillingCalculationResponse)
async def calculate_billing_cost(
    request: BillingCalculationRequest,
    service: BillingService = Depends(get_billing_service),
):
    """计算计费费用"""
    try:
        result = await service.calculate_billing_cost(request)
        return result

    except Exception as e:
        logger.error(f"Error calculating billing cost: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/v1/billing/process", response_model=ProcessBillingResponse)
async def process_billing(
    request: ProcessBillingRequest,
    service: BillingService = Depends(get_billing_service),
):
    """处理计费（实际扣费）"""
    try:
        result = await service.process_billing(request)

        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing billing: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ====================
# 配额管理API
# ====================


@app.post("/api/v1/billing/quota/check", response_model=QuotaCheckResponse)
async def check_quota(
    request: QuotaCheckRequest, service: BillingService = Depends(get_billing_service)
):
    """检查配额"""
    try:
        result = await service.check_quota(request)
        return result

    except Exception as e:
        logger.error(f"Error checking quota: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/v1/billing/quota/{user_id}", response_model=UserQuotaResponse)
async def get_user_quota_status(
    user_id: str,
    service_type: Optional[str] = None,
    service: BillingService = Depends(get_billing_service),
):
    """获取用户配额状态"""
    try:
        from .models import ServiceType

        billing_service_type = ServiceType(service_type) if service_type else None

        quotas = await service.repository.get_user_quotas(
            user_id=user_id,
            service_type=billing_service_type,
        )

        return UserQuotaResponse(user_id=user_id, quotas=quotas)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting user quota status: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ====================
# 查询和统计API
# ====================


@app.get("/api/v1/billing/records", response_model=BillingRecordsListResponse)
async def list_billing_records(
    user_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    billing_account_type: Optional[str] = None,
    billing_account_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    product_id: Optional[str] = None,
    status: Optional[str] = None,
    service_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 50,
    service: BillingService = Depends(get_billing_service),
):
    """获取计费记录列表（支持分页和过滤）"""
    try:
        from .models import BillingStatus, ServiceType

        if page_size > 100:
            page_size = 100
        if page < 1:
            page = 1

        billing_status = BillingStatus(status) if status else None
        billing_service_type = ServiceType(service_type) if service_type else None
        offset = (page - 1) * page_size

        records, total = await service.repository.list_billing_records(
            user_id=user_id,
            organization_id=organization_id,
            billing_account_type=billing_account_type,
            billing_account_id=billing_account_id,
            agent_id=agent_id,
            product_id=product_id,
            status=billing_status,
            service_type=billing_service_type,
            start_date=start_date,
            end_date=end_date,
            limit=page_size,
            offset=offset,
        )

        return BillingRecordsListResponse(
            records=records,
            total=total,
            page=page,
            page_size=page_size,
        )

    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Invalid parameter: {str(e)}")
    except Exception as e:
        logger.error(f"Error listing billing records: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/v1/billing/records/user/{user_id}")
async def get_user_billing_records(
    user_id: str,
    organization_id: Optional[str] = None,
    billing_account_type: Optional[str] = None,
    billing_account_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    product_id: Optional[str] = None,
    status: Optional[str] = None,
    service_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
    service: BillingService = Depends(get_billing_service),
):
    """获取用户计费记录"""
    try:
        from .models import BillingStatus, ServiceType

        billing_status = BillingStatus(status) if status else None
        billing_service_type = ServiceType(service_type) if service_type else None

        records = await service.repository.get_user_billing_records(
            user_id=user_id,
            organization_id=organization_id,
            billing_account_type=billing_account_type,
            billing_account_id=billing_account_id,
            agent_id=agent_id,
            product_id=product_id,
            status=billing_status,
            service_type=billing_service_type,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )

        return {
            "user_id": user_id,
            "records": [record.model_dump() for record in records],
            "total_count": len(records),
            "limit": limit,
            "offset": offset,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting user billing records: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/v1/billing/record/{billing_id}")
async def get_billing_record(
    billing_id: str, service: BillingService = Depends(get_billing_service)
):
    """获取单个计费记录"""
    try:
        record = await service.repository.get_billing_record(billing_id)

        if not record:
            raise HTTPException(status_code=404, detail="Billing record not found")

        return record.model_dump()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting billing record: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ====================
# Unified Billing Status (Story #238/#239)
# ====================


@app.get("/api/v1/billing/user/status")
async def get_user_billing_status(
    request: Request,
    user_id: Optional[str] = None,
    service: BillingService = Depends(get_billing_service),
):
    """Return unified billing status for a user (Story #238/#239).

    Requires authentication via X-User-Id header or query param.
    Rate limited: 60 req/min per user (enforced at gateway level).
    """
    resolved_user_id = user_id or request.headers.get("X-User-Id")
    if not resolved_user_id:
        raise HTTPException(status_code=401, detail="Authentication required: X-User-Id header or user_id param")

    try:
        result = await service.get_user_billing_status(resolved_user_id)
        return result
    except Exception as e:
        logger.error(f"Error getting user billing status: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ====================
# Invoices / Billing History (Story #241)
# ====================


@app.get("/api/v1/billing/invoices")
async def get_invoices(
    user_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    service: BillingService = Depends(get_billing_service),
):
    """Return paginated invoice/billing history (Story #241).

    Each invoice covers a billing period with totals for credits used,
    cost in USD, subscription tier, and payment status.
    Supports date and status filters.
    """
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    if page < 1:
        page = 1
    if page_size > 100:
        page_size = 100

    try:
        result = await service.repository.get_invoices(
            user_id=user_id,
            organization_id=organization_id,
            start_date=start_date,
            end_date=end_date,
            status=status,
            page=page,
            page_size=page_size,
        )
        return result
    except Exception as e:
        logger.error(f"Error getting invoices: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/v1/billing/usage/overview")
async def get_usage_overview(
    request: Request,
    user_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    period_days: int = Query(30, ge=1, le=365),
    service: BillingService = Depends(get_billing_service),
):
    """Cross-service usage overview for the console Usage page (Story #458).

    Combines billing aggregations (requests/tokens/cost daily series) with
    counts from agent_service (active agents). Returns ``warnings`` for any
    upstream that was unavailable instead of failing the request.
    """
    resolved_user_id = user_id or request.headers.get("X-User-Id")
    if not resolved_user_id:
        raise HTTPException(
            status_code=401,
            detail="Authentication required: X-User-Id header or user_id param",
        )
    resolved_org_id = organization_id or request.headers.get("X-Organization-Id")

    try:
        return await service.get_usage_overview(
            user_id=resolved_user_id,
            period_days=period_days,
            organization_id=resolved_org_id,
        )
    except Exception as e:
        logger.error(f"Error getting usage overview: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/v1/billing/usage/aggregations")
async def get_usage_aggregations(
    user_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    billing_account_type: Optional[str] = None,
    billing_account_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    subscription_id: Optional[str] = None,
    service_type: Optional[str] = None,
    product_id: Optional[str] = None,
    period_start: Optional[datetime] = None,
    period_end: Optional[datetime] = None,
    period_type: Optional[str] = None,
    group_by: Optional[str] = None,
    limit: int = 100,
    service: BillingService = Depends(get_billing_service),
):
    """Get usage aggregations with optional group_by support.

    group_by options (Story #242, #240):
      - agent_id: per-agent token consumption
      - service_type: per-service consumption breakdown
      - agent_id,day: agent + time grouping (combinable)
      - service_type,day: service + time grouping (combinable)
    """
    try:
        from .models import ServiceType

        billing_service_type = ServiceType(service_type) if service_type else None

        # Handle group_by for agent_id (Story #242) and service_type (Story #240)
        if group_by:
            group_fields = [g.strip() for g in group_by.split(",")]

            if "agent_id" in group_fields:
                time_group = next(
                    (g for g in group_fields if g in ("hour", "day", "week", "month")),
                    None,
                )
                agent_aggs = await service.repository.get_agent_usage_aggregations(
                    user_id=user_id,
                    organization_id=organization_id,
                    agent_id=agent_id,
                    service_type=billing_service_type,
                    period_start=period_start,
                    period_end=period_end,
                    time_group=time_group,
                    limit=limit,
                )
                return {
                    "agent_aggregations": agent_aggs,
                    "total_count": len(agent_aggs),
                    "group_by": group_by,
                    "filters": {
                        "user_id": user_id,
                        "organization_id": organization_id,
                        "agent_id": agent_id,
                        "service_type": service_type,
                        "period_start": period_start,
                        "period_end": period_end,
                    },
                }

            if "service_type" in group_fields:
                time_group = next(
                    (g for g in group_fields if g in ("hour", "day", "week", "month")),
                    None,
                )
                service_aggs = await service.repository.get_service_usage_aggregations(
                    user_id=user_id,
                    organization_id=organization_id,
                    agent_id=agent_id,
                    period_start=period_start,
                    period_end=period_end,
                    time_group=time_group,
                    limit=limit,
                )
                return {
                    "service_aggregations": service_aggs,
                    "total_count": len(service_aggs),
                    "group_by": group_by,
                    "filters": {
                        "user_id": user_id,
                        "organization_id": organization_id,
                        "agent_id": agent_id,
                        "period_start": period_start,
                        "period_end": period_end,
                    },
                }

        # Default: existing aggregation logic
        aggregations = await service.repository.get_usage_aggregations(
            user_id=user_id,
            organization_id=organization_id,
            billing_account_type=billing_account_type,
            billing_account_id=billing_account_id,
            agent_id=agent_id,
            subscription_id=subscription_id,
            service_type=billing_service_type,
            product_id=product_id,
            period_start=period_start,
            period_end=period_end,
            period_type=period_type,
            limit=limit,
        )

        return {
            "aggregations": [agg.model_dump() for agg in aggregations],
            "total_count": len(aggregations),
            "filters": {
                "user_id": user_id,
                "organization_id": organization_id,
                "billing_account_type": billing_account_type,
                "billing_account_id": billing_account_id,
                "agent_id": agent_id,
                "subscription_id": subscription_id,
                "service_type": service_type,
                "product_id": product_id,
                "period_start": period_start,
                "period_end": period_end,
                "period_type": period_type,
            },
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting usage aggregations: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/v1/billing/stats", response_model=BillingStats)
async def get_billing_statistics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    service: BillingService = Depends(get_billing_service),
):
    """获取计费统计"""
    try:
        stats = await service.get_billing_statistics(start_date, end_date)
        return stats

    except Exception as e:
        logger.error(f"Error getting billing statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ====================
# Admin API
# ====================


async def require_admin(request: Request):
    """Check for admin role header"""
    if request.headers.get("X-Admin-Role") != "true":
        raise HTTPException(status_code=403, detail="Admin access required")


def _extract_admin_context(request: Request) -> Dict[str, Any]:
    """Extract admin identity and request context from headers for audit logging."""
    return {
        "admin_user_id": request.headers.get("X-Admin-User-Id", "unknown_admin"),
        "admin_email": request.headers.get("X-Admin-Email"),
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("User-Agent"),
    }


async def _audit_admin_action(
    request: Request,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    changes: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
):
    """Fire-and-forget admin audit event. Never raises."""
    try:
        ctx = _extract_admin_context(request)
        await publish_admin_action(
            event_bus=event_bus,
            admin_user_id=ctx["admin_user_id"],
            admin_email=ctx["admin_email"],
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=changes,
            ip_address=ctx["ip_address"],
            user_agent=ctx["user_agent"],
            metadata=metadata,
        )
    except Exception as e:
        logger.warning(f"Admin audit publish failed (non-blocking): {e}")


@app.get("/api/v1/billing/admin/records", response_model=BillingRecordsListResponse)
async def admin_list_billing_records(
    request: Request,
    user_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    billing_account_type: Optional[str] = None,
    billing_account_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    product_id: Optional[str] = None,
    status: Optional[str] = None,
    service_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    service: BillingService = Depends(get_billing_service),
):
    """[Admin] List all billing records with filters (paginated)"""
    await require_admin(request)
    try:
        from .models import BillingStatus as BillingStatusEnum, ServiceType as ServiceTypeEnum

        billing_status = BillingStatusEnum(status) if status else None
        billing_service_type = ServiceTypeEnum(service_type) if service_type else None
        offset = (page - 1) * page_size

        records, total = await service.repository.list_billing_records(
            user_id=user_id,
            organization_id=organization_id,
            billing_account_type=billing_account_type,
            billing_account_id=billing_account_id,
            agent_id=agent_id,
            product_id=product_id,
            status=billing_status,
            service_type=billing_service_type,
            start_date=start_date,
            end_date=end_date,
            limit=page_size,
            offset=offset,
        )

        return BillingRecordsListResponse(
            records=records,
            total=total,
            page=page,
            page_size=page_size,
        )

    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Invalid parameter: {str(e)}")
    except Exception as e:
        logger.error(f"Error listing billing records (admin): {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/v1/billing/admin/refund")
async def admin_issue_refund(
    request: Request,
    billing_id: str = Query(..., description="Billing record ID to refund"),
    reason: str = Query(..., description="Reason for refund"),
    service: BillingService = Depends(get_billing_service),
):
    """[Admin] Issue a refund for a billing record with reason"""
    await require_admin(request)
    try:
        from .models import BillingStatus as BillingStatusEnum

        # Get the billing record
        record = await service.repository.get_billing_record(billing_id)
        if not record:
            raise HTTPException(status_code=404, detail="Billing record not found")

        if record.billing_status == BillingStatusEnum.REFUNDED:
            raise HTTPException(status_code=400, detail="Billing record already refunded")

        # Update status to refunded
        updated_record = await service.repository.update_billing_record_status(
            billing_id=billing_id,
            status=BillingStatusEnum.REFUNDED,
            failure_reason=f"Admin refund: {reason}",
        )

        if not updated_record:
            raise HTTPException(status_code=500, detail="Failed to update billing record")

        # Audit
        await _audit_admin_action(
            request, action="issue_refund", resource_type="billing_record",
            resource_id=billing_id,
            changes={
                "before": {"status": record.billing_status.value},
                "after": {"status": BillingStatusEnum.REFUNDED.value},
            },
            metadata={"reason": reason, "amount": str(record.total_amount)},
        )

        return {
            "success": True,
            "message": f"Refund issued for billing record {billing_id}",
            "billing_id": billing_id,
            "refunded_amount": str(record.total_amount),
            "reason": reason,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error issuing refund (admin): {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ====================
# 管理API (legacy)
# ====================


@app.put("/api/v1/billing/record/{billing_id}/status")
async def update_billing_record_status(
    billing_id: str,
    status: str,
    failure_reason: Optional[str] = None,
    wallet_transaction_id: Optional[str] = None,
    payment_transaction_id: Optional[str] = None,
    service: BillingService = Depends(get_billing_service),
):
    """更新计费记录状态（管理员功能）"""
    try:
        from .models import BillingStatus

        billing_status = BillingStatus(status)

        updated_record = await service.repository.update_billing_record_status(
            billing_id=billing_id,
            status=billing_status,
            failure_reason=failure_reason,
            wallet_transaction_id=wallet_transaction_id,
            payment_transaction_id=payment_transaction_id,
        )

        if not updated_record:
            raise HTTPException(status_code=404, detail="Billing record not found")

        return {
            "success": True,
            "message": "Billing record status updated",
            "billing_record": updated_record.model_dump(),
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid status: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating billing record status: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ====================
# 错误处理
# ====================


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    logger.error(f"Unhandled exception in {request.url}: {exc}", exc_info=True)
    return HTTPException(status_code=500, detail="Internal server error occurred")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "microservices.billing_service.main:app",
        host="0.0.0.0",
        port=SERVICE_PORT,
        reload=config.debug,
        log_level=config.log_level.lower(),
    )
