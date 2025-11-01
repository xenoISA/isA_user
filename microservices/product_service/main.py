"""
Product Microservice API

专注于产品目录、定价和订阅管理的REST API服务
"""

from fastapi import FastAPI, HTTPException, Depends, Request, Query, Body
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List
import logging
import os
import sys
from datetime import datetime

# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from core.consul_registry import ConsulRegistry
from core.config_manager import ConfigManager
from core.logger import setup_service_logger
from core.nats_client import get_event_bus

from .product_repository import ProductRepository
from .product_service import ProductService
from .models import (
    Product, ProductCategory, PricingModel, ServicePlan, UserSubscription,
    ProductUsageRecord, ProductType, PricingType, SubscriptionStatus, BillingCycle
)

# 初始化配置管理器
config_manager = ConfigManager("product_service")
config = config_manager.get_service_config()

# 配置日志
logger = setup_service_logger("product_service", level=config.log_level.upper())

# 打印配置信息（开发环境）
if config.debug:
    config_manager.print_config_summary(show_secrets=False)

# 全局变量
product_service: Optional[ProductService] = None
repository: Optional[ProductRepository] = None
consul_registry: Optional[ConsulRegistry] = None
event_bus = None  # NATS event bus
SERVICE_PORT = config.service_port or 8215


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global product_service, repository, consul_registry, event_bus

    try:
        # 初始化数据库连接
        repository = ProductRepository()
        await repository.initialize()

        # Initialize NATS JetStream event bus
        try:
            event_bus = await get_event_bus("product_service")
            logger.info("✅ Event bus initialized successfully")

            # 初始化业务服务 with event bus
            product_service = ProductService(repository, event_bus=event_bus)

        except Exception as e:
            logger.warning(f"⚠️  Failed to initialize event bus: {e}. Continuing without event publishing.")
            event_bus = None

            # 初始化业务服务 without event bus
            product_service = ProductService(repository, event_bus=None)
        
        # 注册到 Consul（如果启用）
        if config.consul_enabled:
            consul_registry = ConsulRegistry(
                service_name="product_service",
                service_port=SERVICE_PORT,
                consul_host=config.consul_host,
                consul_port=config.consul_port,
                service_host=config.service_host,
                tags=["microservice", "product", "api"]
            )
            if consul_registry.register():
                consul_registry.start_maintenance()
                logger.info("Product service registered with Consul")
            else:
                logger.error("Failed to register product service with Consul")
        
        logger.info(f"Product service started on port {SERVICE_PORT}")
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize product service: {e}")
        raise
    finally:
        # 清理资源
        if event_bus:
            try:
                await event_bus.close()
                logger.info("Product event bus closed")
            except Exception as e:
                logger.error(f"Error closing event bus: {e}")

        if consul_registry:
            consul_registry.stop_maintenance()
            consul_registry.deregister()
            logger.info("Product service deregistered from Consul")

        if repository:
            await repository.close()
            logger.info("Product service database connections closed")


# 创建 FastAPI 应用
app = FastAPI(
    title="Product Service",
    description="专注于产品目录、定价和订阅管理",
    version="1.0.0",
    lifespan=lifespan
)


# ====================
# 依赖注入
# ====================

async def get_product_service() -> ProductService:
    """获取产品服务实例"""
    if not product_service:
        raise HTTPException(status_code=503, detail="Product service not initialized")
    return product_service


# ====================
# 健康检查和服务信息
# ====================

@app.get("/health")
async def health_check():
    """健康检查"""
    dependencies = {}
    
    # 检查数据库连接
    try:
        if repository and repository.client:
            # Simple test query to check database connection
            repository.client.table("product_categories").select("count", count="exact").limit(1).execute()
            dependencies["database"] = "healthy"
        else:
            dependencies["database"] = "unhealthy"
    except Exception:
        dependencies["database"] = "unhealthy"
    
    return {
        "status": "healthy" if all(v == "healthy" for v in dependencies.values()) else "degraded",
        "service": "product_service",
        "port": SERVICE_PORT,
        "version": "1.0.0",
        "dependencies": dependencies
    }


@app.get("/api/v1/info")
async def get_service_info():
    """获取服务信息"""
    return {
        "service": "product_service",
        "version": "1.0.0",
        "description": "专注于产品目录、定价和订阅管理的微服务",
        "capabilities": [
            "product_catalog",
            "pricing_management", 
            "subscription_management",
            "usage_tracking",
            "product_analytics"
        ],
        "supported_product_types": [
            "model_inference",
            "mcp_service", 
            "agent_execution",
            "storage_minio",
            "api_gateway"
        ],
        "supported_pricing_types": [
            "freemium",
            "usage_based",
            "subscription", 
            "hybrid"
        ]
    }


# ====================
# 产品目录API
# ====================

@app.get("/api/v1/categories", response_model=List[ProductCategory])
async def get_product_categories(
    service: ProductService = Depends(get_product_service)
):
    """获取产品类别列表"""
    try:
        return await service.get_product_categories()
    except Exception as e:
        logger.error(f"Error getting product categories: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/v1/products", response_model=List[Product])
async def get_products(
    category_id: Optional[str] = Query(None, description="产品类别ID"),
    product_type: Optional[str] = Query(None, description="产品类型"),
    is_active: bool = Query(True, description="是否仅获取激活的产品"),
    service: ProductService = Depends(get_product_service)
):
    """获取产品列表"""
    try:
        product_type_enum = ProductType(product_type) if product_type else None
        return await service.get_products(
            category_id=category_id,
            product_type=product_type_enum,
            is_active=is_active
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid product_type: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting products: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/v1/products/{product_id}", response_model=Product)
async def get_product(
    product_id: str,
    service: ProductService = Depends(get_product_service)
):
    """获取单个产品信息"""
    try:
        product = await service.get_product(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting product {product_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/v1/products/{product_id}/pricing")
async def get_product_pricing(
    product_id: str,
    user_id: Optional[str] = Query(None, description="用户ID"),
    subscription_id: Optional[str] = Query(None, description="订阅ID"),
    service: ProductService = Depends(get_product_service)
):
    """获取产品定价信息"""
    try:
        pricing = await service.get_product_pricing(
            product_id=product_id,
            user_id=user_id,
            subscription_id=subscription_id
        )
        if not pricing:
            raise HTTPException(status_code=404, detail="Product pricing not found")
        return pricing
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting product pricing for {product_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/v1/products/{product_id}/availability")
async def check_product_availability(
    product_id: str,
    user_id: str = Query(..., description="用户ID"),
    organization_id: Optional[str] = Query(None, description="组织ID"),
    service: ProductService = Depends(get_product_service)
):
    """检查产品可用性"""
    try:
        result = await service.check_product_availability(
            product_id=product_id,
            user_id=user_id,
            organization_id=organization_id
        )
        return result
    except Exception as e:
        logger.error(f"Error checking product availability: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ====================
# 订阅管理API
# ====================

@app.get("/api/v1/subscriptions/user/{user_id}", response_model=List[UserSubscription])
async def get_user_subscriptions(
    user_id: str,
    status: Optional[str] = Query(None, description="订阅状态过滤"),
    service: ProductService = Depends(get_product_service)
):
    """获取用户订阅列表"""
    try:
        status_enum = SubscriptionStatus(status) if status else None
        return await service.get_user_subscriptions(
            user_id=user_id,
            status=status_enum
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid status: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting user subscriptions for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/v1/subscriptions/{subscription_id}", response_model=UserSubscription)
async def get_subscription(
    subscription_id: str,
    service: ProductService = Depends(get_product_service)
):
    """获取订阅详情"""
    try:
        subscription = await service.get_subscription(subscription_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        return subscription
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting subscription {subscription_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/v1/subscriptions", response_model=UserSubscription)
async def create_subscription(
    user_id: str = Body(...),
    plan_id: str = Body(...),
    organization_id: Optional[str] = Body(None),
    billing_cycle: str = Body("monthly"),
    metadata: Optional[Dict[str, Any]] = Body(None),
    service: ProductService = Depends(get_product_service)
):
    """创建新订阅"""
    try:
        # Validate billing cycle first
        try:
            billing_cycle_enum = BillingCycle(billing_cycle)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid billing_cycle: {billing_cycle}")
        
        return await service.create_subscription(
            user_id=user_id,
            plan_id=plan_id,
            organization_id=organization_id,
            billing_cycle=billing_cycle_enum,
            metadata=metadata
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating subscription: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ====================
# 使用量记录API
# ====================

@app.post("/api/v1/usage/record")
async def record_product_usage(
    user_id: str = Body(...),
    product_id: str = Body(...),
    usage_amount: float = Body(...),
    organization_id: Optional[str] = Body(None),
    subscription_id: Optional[str] = Body(None),
    session_id: Optional[str] = Body(None),
    request_id: Optional[str] = Body(None),
    usage_details: Optional[Dict[str, Any]] = Body(None),
    usage_timestamp: Optional[datetime] = Body(None),
    service: ProductService = Depends(get_product_service)
):
    """记录产品使用量"""
    try:
        from decimal import Decimal
        result = await service.record_product_usage(
            user_id=user_id,
            organization_id=organization_id,
            subscription_id=subscription_id,
            product_id=product_id,
            usage_amount=Decimal(str(usage_amount)),
            session_id=session_id,
            request_id=request_id,
            usage_details=usage_details,
            usage_timestamp=usage_timestamp
        )
        return result
    except Exception as e:
        logger.error(f"Error recording product usage: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/v1/usage/records", response_model=List[ProductUsageRecord])
async def get_usage_records(
    user_id: Optional[str] = Query(None, description="用户ID"),
    organization_id: Optional[str] = Query(None, description="组织ID"),
    subscription_id: Optional[str] = Query(None, description="订阅ID"),
    product_id: Optional[str] = Query(None, description="产品ID"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    limit: int = Query(100, description="返回记录数量限制"),
    offset: int = Query(0, description="偏移量"),
    service: ProductService = Depends(get_product_service)
):
    """获取使用量记录"""
    try:
        return await service.get_usage_records(
            user_id=user_id,
            organization_id=organization_id,
            subscription_id=subscription_id,
            product_id=product_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        logger.error(f"Error getting usage records: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ====================
# 统计和分析API
# ====================

@app.get("/api/v1/statistics/usage")
async def get_usage_statistics(
    user_id: Optional[str] = Query(None, description="用户ID"),
    organization_id: Optional[str] = Query(None, description="组织ID"),
    product_id: Optional[str] = Query(None, description="产品ID"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    service: ProductService = Depends(get_product_service)
):
    """获取使用量统计"""
    try:
        return await service.get_usage_statistics(
            user_id=user_id,
            organization_id=organization_id,
            product_id=product_id,
            start_date=start_date,
            end_date=end_date
        )
    except Exception as e:
        logger.error(f"Error getting usage statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/v1/statistics/service")
async def get_service_statistics(
    service: ProductService = Depends(get_product_service)
):
    """获取服务统计"""
    try:
        return await service.get_service_statistics()
    except Exception as e:
        logger.error(f"Error getting service statistics: {e}")
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
        "microservices.product_service.main:app",
        host="0.0.0.0",
        port=SERVICE_PORT,
        reload=config.debug,
        log_level=config.log_level.lower()
    )