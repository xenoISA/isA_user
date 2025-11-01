"""
Billing Microservice API

专注于使用量跟踪、费用计算和计费处理的REST API服务
"""

from fastapi import FastAPI, HTTPException, Depends, Request
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List
import logging
import os
import sys
import asyncio
from datetime import datetime

# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from core.consul_registry import ConsulRegistry
from core.config_manager import ConfigManager
from core.logger import setup_service_logger
from core.nats_client import get_event_bus

from .billing_repository import BillingRepository
from .billing_service import BillingService
from .models import (
    RecordUsageRequest, BillingCalculationRequest, BillingCalculationResponse,
    ProcessBillingRequest, ProcessBillingResponse, QuotaCheckRequest, QuotaCheckResponse,
    UsageStatsRequest, UsageStatsResponse, BillingStats,
    HealthResponse, ServiceInfo
)

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
consul_registry: Optional[ConsulRegistry] = None
event_bus = None  # NATS event bus
event_handlers = None  # Event handlers
SERVICE_PORT = config.service_port or 8216


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global billing_service, repository, consul_registry, event_bus, event_handlers

    try:
        # 初始化数据库连接
        repository = BillingRepository()
        await repository.initialize()

        # 初始化并启动事件订阅器 (CRITICAL for event-driven billing)
        # Initialize NATS JetStream event bus
        try:
            from .event_handlers import BillingEventHandlers

            event_bus = await get_event_bus("billing_service")
            logger.info("✅ Event bus initialized successfully")

            # 初始化业务服务 with event bus
            billing_service = BillingService(repository, event_bus=event_bus)

            # Initialize event handlers
            event_handlers = BillingEventHandlers(billing_service)

            # Subscribe to events
            handler_map = event_handlers.get_event_handler_map()
            for event_type, handler_func in handler_map.items():
                # Subscribe to each event type
                # Convert event type like "session.tokens_used" to subscription pattern "*.session.tokens_used"
                await event_bus.subscribe_to_events(
                    pattern=f"*.{event_type}",
                    handler=handler_func
                )
                logger.info(f"✅ Subscribed to {event_type} events")

            logger.info(f"✅ Billing event subscriber started ({len(handler_map)} event types)")

        except Exception as e:
            logger.warning(f"⚠️  Failed to initialize event bus: {e}. Continuing without event subscriptions.")
            event_bus = None
            event_handlers = None

            # 初始化业务服务 without event bus
            billing_service = BillingService(repository, event_bus=None)

        # 注册到 Consul（如果启用）
        if config.consul_enabled:
            consul_registry = ConsulRegistry(
                service_name="billing_service",
                service_port=SERVICE_PORT,
                consul_host=config.consul_host,
                consul_port=config.consul_port,
                service_host=config.service_host,
                tags=["microservice", "billing", "api"]
            )
            if consul_registry.register():
                consul_registry.start_maintenance()
                logger.info("Billing service registered with Consul")
            else:
                logger.error("Failed to register billing service with Consul")

        logger.info(f"Billing service started on port {SERVICE_PORT}")
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize billing service: {e}")
        raise
    finally:
        # 清理资源
        if event_bus:
            try:
                await event_bus.close()
                logger.info("Billing event bus closed")
            except Exception as e:
                logger.error(f"Error closing event bus: {e}")

        if consul_registry:
            consul_registry.stop_maintenance()
            consul_registry.deregister()
            logger.info("Billing service deregistered from Consul")

        if repository:
            await repository.close()
            logger.info("Billing service database connections closed")


# 创建 FastAPI 应用
app = FastAPI(
    title="Billing Service",
    description="专注于使用量跟踪、费用计算和计费处理",
    version="1.0.0",
    lifespan=lifespan
)


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

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    dependencies = {}
    
    # 检查数据库连接
    try:
        if repository and repository.client:
            # Simple test query to check database connection
            repository.client.table("billing_records").select("count", count="exact").limit(1).execute()
            dependencies["database"] = "healthy"
        else:
            dependencies["database"] = "unhealthy"
    except Exception:
        dependencies["database"] = "unhealthy"
    
    return HealthResponse(
        status="healthy" if all(v == "healthy" for v in dependencies.values()) else "degraded",
        service="billing_service",
        port=SERVICE_PORT,
        version="1.0.0",
        dependencies=dependencies
    )


@app.get("/api/v1/info", response_model=ServiceInfo)
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
            "billing_analytics"
        ],
        supported_services=[
            "model_inference",
            "mcp_service", 
            "agent_execution",
            "storage_minio",
            "api_gateway",
            "notification"
        ],
        supported_billing_methods=[
            "wallet_deduction",
            "payment_charge",
            "credit_consumption", 
            "subscription_included"
        ]
    )


# ====================
# 核心计费API
# ====================

@app.post("/api/v1/usage/record", response_model=ProcessBillingResponse)
async def record_usage_and_bill(
    request: RecordUsageRequest,
    service: BillingService = Depends(get_billing_service)
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
    service: BillingService = Depends(get_billing_service)
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
    service: BillingService = Depends(get_billing_service)
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

@app.post("/api/v1/quota/check", response_model=QuotaCheckResponse)
async def check_quota(
    request: QuotaCheckRequest,
    service: BillingService = Depends(get_billing_service)
):
    """检查配额"""
    try:
        result = await service.check_quota(request)
        return result
        
    except Exception as e:
        logger.error(f"Error checking quota: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ====================
# 查询和统计API
# ====================

@app.get("/api/v1/billing/records/user/{user_id}")
async def get_user_billing_records(
    user_id: str,
    status: Optional[str] = None,
    service_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
    service: BillingService = Depends(get_billing_service)
):
    """获取用户计费记录"""
    try:
        from .models import BillingStatus, ServiceType
        
        billing_status = BillingStatus(status) if status else None
        billing_service_type = ServiceType(service_type) if service_type else None
        
        records = await service.repository.get_user_billing_records(
            user_id=user_id,
            status=billing_status,
            service_type=billing_service_type,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
        
        return {
            "user_id": user_id,
            "records": [record.model_dump() for record in records],
            "total_count": len(records),
            "limit": limit,
            "offset": offset
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting user billing records: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/v1/billing/record/{billing_id}")
async def get_billing_record(
    billing_id: str,
    service: BillingService = Depends(get_billing_service)
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


@app.get("/api/v1/usage/aggregations")
async def get_usage_aggregations(
    user_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    subscription_id: Optional[str] = None,
    service_type: Optional[str] = None,
    period_start: Optional[datetime] = None,
    period_end: Optional[datetime] = None,
    period_type: Optional[str] = None,
    limit: int = 100,
    service: BillingService = Depends(get_billing_service)
):
    """获取使用量聚合数据"""
    try:
        from .models import ServiceType
        
        billing_service_type = ServiceType(service_type) if service_type else None
        
        aggregations = await service.repository.get_usage_aggregations(
            user_id=user_id,
            organization_id=organization_id,
            subscription_id=subscription_id,
            service_type=billing_service_type,
            period_start=period_start,
            period_end=period_end,
            period_type=period_type,
            limit=limit
        )
        
        return {
            "aggregations": [agg.model_dump() for agg in aggregations],
            "total_count": len(aggregations),
            "filters": {
                "user_id": user_id,
                "organization_id": organization_id,
                "subscription_id": subscription_id,
                "service_type": service_type,
                "period_start": period_start,
                "period_end": period_end,
                "period_type": period_type
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting usage aggregations: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/v1/stats", response_model=BillingStats)
async def get_billing_statistics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    service: BillingService = Depends(get_billing_service)
):
    """获取计费统计"""
    try:
        stats = await service.get_billing_statistics(start_date, end_date)
        return stats
        
    except Exception as e:
        logger.error(f"Error getting billing statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ====================
# 管理API
# ====================

@app.put("/api/v1/billing/record/{billing_id}/status")
async def update_billing_record_status(
    billing_id: str,
    status: str,
    failure_reason: Optional[str] = None,
    wallet_transaction_id: Optional[str] = None,
    payment_transaction_id: Optional[str] = None,
    service: BillingService = Depends(get_billing_service)
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
            payment_transaction_id=payment_transaction_id
        )
        
        if not updated_record:
            raise HTTPException(status_code=404, detail="Billing record not found")
        
        return {
            "success": True,
            "message": "Billing record status updated",
            "billing_record": updated_record.model_dump()
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
    return HTTPException(
        status_code=500,
        detail="Internal server error occurred"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "microservices.billing_service.main:app",
        host="0.0.0.0",
        port=SERVICE_PORT,
        reload=config.debug,
        log_level=config.log_level.lower()
    )