"""
Audit Service Main Application

审计服务FastAPI应用入口 - 端口8204
提供审计事件记录、查询、分析、安全告警和合规报告功能
"""

import uvicorn
import logging
import os
import sys
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Query, Depends, Request
from fastapi.responses import JSONResponse

# Add parent directory to path for consul_registry
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from core.config_manager import ConfigManager
from core.graceful_shutdown import GracefulShutdown, shutdown_middleware
from core.metrics import setup_metrics
from core.logger import setup_service_logger
from core.nats_client import get_event_bus
from core.health import HealthCheck
from isa_common.consul_client import ConsulRegistry

from .audit_service import AuditService
from .factory import create_audit_service
from .events.handlers import AuditEventHandlers
from .events.admin_audit_handler import AdminAuditEventHandler
from .admin_audit_repository import AdminAuditRepository
from .admin_audit_models import (
    AdminAuditCreateRequest, AdminAuditResponse, AdminAuditQueryResponse,
    AdminAuditLogEntry,
)
from .routes_registry import get_routes_for_consul, SERVICE_METADATA
from .models import (
    AuditEventCreateRequest, AuditEventResponse, AuditQueryRequest, AuditQueryResponse,
    UserActivitySummary, SecurityAlertRequest, ComplianceReportRequest, EventSeverity, AuditCategory,
    EventType, HealthResponse, ServiceInfo, ServiceStats
)

# Initialize configuration
config_manager = ConfigManager("audit_service")
config = config_manager.get_service_config()

# Setup loggers (use actual service name)
app_logger = setup_service_logger("audit_service")
logger = app_logger  # for backward compatibility

# 全局服务实例
audit_service: Optional[AuditService] = None
admin_audit_repo: Optional[AdminAuditRepository] = None
event_bus = None
consul_registry = None
shutdown_manager = GracefulShutdown("audit_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    shutdown_manager.install_signal_handlers()
    global audit_service, admin_audit_repo, event_bus, consul_registry

    logger.info("🚀 Audit Service starting up...")

    try:
        # 初始化服务 (使用工厂方法)
        audit_service = create_audit_service(config=config_manager)

        # Initialize admin audit repository
        admin_audit_repo = AdminAuditRepository(config=config_manager)

        # 检查数据库连接
        if await audit_service.repository.check_connection():
            logger.info("✅ 数据库连接成功")
        else:
            logger.warning("⚠️ 数据库连接失败")

        # Initialize event bus
        try:
            event_bus = await get_event_bus("audit_service")
            logger.info("✅ Event bus initialized successfully")

            # Initialize event handlers
            event_handlers = AuditEventHandlers(audit_service)

            # Subscribe to ALL events using wildcard pattern
            await event_bus.subscribe_to_events(
                pattern="*.*",  # Subscribe to all events from all services
                handler=event_handlers.handle_nats_event
            )
            logger.info("✅ Subscribed to all NATS events (*.*) for audit logging")

            # Subscribe to admin action events for dedicated admin audit log
            admin_audit_handler = AdminAuditEventHandler(admin_audit_repo)
            await event_bus.subscribe_to_events(
                pattern="admin.action.>",
                handler=admin_audit_handler.handle_admin_action_event,
                durable="audit-service-admin-actions-consumer",
            )
            logger.info("✅ Subscribed to admin.action.> for admin audit logging")

        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize event bus: {e}. Continuing without event subscriptions.")
            event_bus = None

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

                consul_registry = ConsulRegistry(
                    service_name=SERVICE_METADATA['service_name'],
                    service_port=config.service_port,
                    consul_host=config.consul_host,
                    consul_port=config.consul_port,
                    tags=SERVICE_METADATA['tags'],
                    meta=consul_meta,
                    health_check_type='ttl'  # Use TTL for reliable health checks
                )
                consul_registry.register()
                consul_registry.start_maintenance()  # Start TTL heartbeat
                logger.info(f"✅ Service registered with Consul: {route_meta.get('route_count')} routes")
            except Exception as e:
                logger.warning(f"⚠️  Failed to register with Consul: {e}")
                consul_registry = None

        logger.info("✅ Audit Service started successfully")

    except Exception as e:
        logger.error(f"❌ Audit Service startup failed: {e}")
        audit_service = None

    yield

    logger.info("🛑 Audit Service shutting down...")
    shutdown_manager.initiate_shutdown()
    await shutdown_manager.wait_for_drain()

    # Consul deregistration
    if consul_registry:
        try:
            consul_registry.deregister()
            logger.info("✅ Service deregistered from Consul")
        except Exception as e:
            logger.error(f"❌ Failed to deregister from Consul: {e}")

    # Close event bus
    if event_bus:
        await event_bus.close()
        logger.info("✅ Event bus closed")
    if audit_service:
        logger.info("✅ Audit Service cleanup completed")


# 创建FastAPI应用
app = FastAPI(
    title="Audit Service",
    description="审计服务 - 提供事件记录、查询、分析和合规报告功能",
    version="1.0.0",
    lifespan=lifespan
)
app.add_middleware(shutdown_middleware, shutdown_manager=shutdown_manager)
setup_metrics(app, "audit_service")

# CORS中间件
# CORS handled by Gateway

# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"未处理的异常: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"内部服务器错误: {str(exc)}"}
    )


# ====================
# 依赖注入
# ====================

def get_audit_service() -> AuditService:
    """获取审计服务实例"""
    if not audit_service:
        raise HTTPException(status_code=503, detail="审计服务不可用")
    return audit_service


# ====================
# 健康检查和服务信息
# ====================

health = HealthCheck("audit_service", version="1.0.0", shutdown_manager=shutdown_manager)
health.add_check("postgres", lambda: audit_service.repository.check_connection() if audit_service and audit_service.repository else False)
health.add_nats(lambda: event_bus)


@app.get("/api/v1/audit/health")
@app.get("/health")
async def health_check():
    """Service health check"""
    return await health.check()

@app.get("/api/v1/audit/info", response_model=ServiceInfo)
async def service_info():
    """服务信息和能力"""
    return ServiceInfo(
        service="audit_service",
        version="1.0.0",
        description="综合审计事件记录、查询、分析和合规报告服务",
        capabilities={
            "event_logging": True,
            "event_querying": True,
            "user_activity_tracking": True,
            "security_alerting": True,
            "compliance_reporting": True,
            "real_time_analysis": True,
            "data_retention": True
        },
        endpoints={
            "log_event": "/api/v1/audit/events",
            "query_events": "/api/v1/audit/events/query", 
            "user_activities": "/api/v1/audit/users/{user_id}/activities",
            "security_alerts": "/api/v1/audit/security/alerts",
            "compliance_reports": "/api/v1/audit/compliance/reports"
        }
    )


@app.get("/api/v1/audit/stats", response_model=ServiceStats)
async def service_stats(svc: AuditService = Depends(get_audit_service)):
    """服务统计和指标"""
    try:
        stats = await svc.get_service_statistics()
        
        return ServiceStats(
            total_events=stats.get("total_events", 0),
            events_today=stats.get("events_today", 0),
            active_users=stats.get("active_users", 0),
            security_alerts=stats.get("security_alerts", 0),
            compliance_score=stats.get("compliance_score", 0.0)
        )
        
    except Exception as e:
        logger.error(f"获取服务统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")


# ====================
# 审计事件管理
# ====================

@app.post("/api/v1/audit/events", response_model=AuditEventResponse)
async def log_audit_event(
    request: AuditEventCreateRequest,
    svc: AuditService = Depends(get_audit_service)
):
    """记录审计事件"""
    try:
        logger.info(f"记录审计事件: {request.event_type.value} - {request.action}")
        
        result = await svc.log_event(request)
        if not result:
            raise HTTPException(status_code=500, detail="事件记录失败")
        
        return result
        
    except Exception as e:
        logger.error(f"审计事件记录失败: {e}")
        raise HTTPException(status_code=500, detail=f"事件记录失败: {str(e)}")


@app.post("/api/v1/audit/events/query", response_model=AuditQueryResponse)
async def query_audit_events(
    query: AuditQueryRequest,
    svc: AuditService = Depends(get_audit_service)
):
    """查询审计事件"""
    try:
        logger.info(f"查询审计事件: 类型={query.event_types}, 用户={query.user_id}")
        
        result = await svc.query_events(query)
        return result
        
    except Exception as e:
        logger.error(f"审计事件查询失败: {e}")
        raise HTTPException(status_code=500, detail=f"事件查询失败: {str(e)}")


@app.get("/api/v1/audit/events")
async def get_audit_events(
    event_type: Optional[str] = Query(None, description="事件类型过滤"),
    category: Optional[str] = Query(None, description="事件分类过滤"),
    user_id: Optional[str] = Query(None, description="用户ID过滤"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    limit: int = Query(100, description="返回条数限制", le=1000),
    offset: int = Query(0, description="偏移量"),
    svc: AuditService = Depends(get_audit_service)
):
    """获取审计事件 (GET方式)"""
    try:
        # 构建查询请求
        query = AuditQueryRequest(
            event_types=[EventType(event_type)] if event_type else None,
            categories=[AuditCategory(category)] if category else None,
            user_id=user_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset
        )
        
        result = await svc.query_events(query)
        return result
        
    except Exception as e:
        logger.error(f"审计事件获取失败: {e}")
        raise HTTPException(status_code=500, detail=f"事件获取失败: {str(e)}")


# ====================
# 用户活动跟踪
# ====================

@app.get("/api/v1/audit/users/{user_id}/activities")
async def get_user_activities(
    user_id: str,
    days: int = Query(30, description="查询天数", le=365),
    limit: int = Query(100, description="返回条数限制", le=1000),
    svc: AuditService = Depends(get_audit_service)
):
    """获取用户活动记录"""
    try:
        logger.info(f"获取用户活动: {user_id}, 天数={days}")
        
        activities = await svc.get_user_activities(user_id, days, limit)
        
        # Convert activities to JSON-serializable format
        serializable_activities = []
        for activity in activities:
            if isinstance(activity, dict):
                # Convert any datetime objects to ISO format
                serialized = {}
                for k, v in activity.items():
                    if isinstance(v, datetime):
                        serialized[k] = v.isoformat()
                    else:
                        serialized[k] = v
                serializable_activities.append(serialized)
            else:
                serializable_activities.append(activity)

        return {
            "user_id": user_id,
            "activities": serializable_activities,
            "total_count": len(activities),
            "period_days": days,
            "query_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取用户活动失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取用户活动失败: {str(e)}")


@app.get("/api/v1/audit/users/{user_id}/summary", response_model=UserActivitySummary)
async def get_user_activity_summary(
    user_id: str,
    days: int = Query(30, description="查询天数", le=365),
    svc: AuditService = Depends(get_audit_service)
):
    """获取用户活动摘要"""
    try:
        logger.info(f"生成用户活动摘要: {user_id}")
        
        summary = await svc.get_user_activity_summary(user_id, days)
        return summary
        
    except Exception as e:
        logger.error(f"生成用户活动摘要失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成摘要失败: {str(e)}")


# ====================
# 安全事件管理
# ====================

@app.post("/api/v1/audit/security/alerts")
async def create_security_alert(
    alert: SecurityAlertRequest,
    svc: AuditService = Depends(get_audit_service)
):
    """创建安全告警"""
    try:
        logger.warning(f"创建安全告警: {alert.threat_type}")
        
        security_event = await svc.create_security_alert(alert)
        if not security_event:
            raise HTTPException(status_code=500, detail="安全告警创建失败")
        
        return {
            "message": "安全告警已创建",
            "alert_id": security_event.id,
            "threat_level": security_event.threat_level,
            "created_at": security_event.detected_at
        }
        
    except Exception as e:
        logger.error(f"创建安全告警失败: {e}")
        raise HTTPException(status_code=500, detail=f"安全告警创建失败: {str(e)}")


@app.get("/api/v1/audit/security/events")
async def get_security_events(
    days: int = Query(7, description="查询天数", le=90),
    severity: Optional[str] = Query(None, description="严重程度过滤"),
    svc: AuditService = Depends(get_audit_service)
):
    """获取安全事件列表"""
    try:
        severity_filter = EventSeverity(severity) if severity else None
        events = await svc.get_security_events(days, severity_filter)
        
        return {
            "security_events": events,
            "total_count": len(events),
            "period_days": days,
            "severity_filter": severity,
            "query_timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"获取安全事件失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取安全事件失败: {str(e)}")


# ====================
# 合规报告
# ====================

@app.post("/api/v1/audit/compliance/reports")
async def generate_compliance_report(
    request: ComplianceReportRequest,
    svc: AuditService = Depends(get_audit_service)
):
    """生成合规报告"""
    try:
        logger.info(f"生成合规报告: {request.compliance_standard}")
        
        report = await svc.generate_compliance_report(request)
        if not report:
            raise HTTPException(status_code=500, detail="合规报告生成失败")
        
        return report
        
    except Exception as e:
        logger.error(f"生成合规报告失败: {e}")
        raise HTTPException(status_code=500, detail=f"合规报告生成失败: {str(e)}")


@app.get("/api/v1/audit/compliance/standards")
async def get_compliance_standards():
    """获取支持的合规标准"""
    return {
        "supported_standards": [
            {
                "name": "GDPR",
                "description": "通用数据保护条例",
                "retention_days": 2555,
                "regions": ["EU"]
            },
            {
                "name": "SOX",
                "description": "萨班斯-奥克斯利法案",
                "retention_days": 2555,
                "regions": ["US"]
            },
            {
                "name": "HIPAA",
                "description": "健康保险便携性和问责法案",
                "retention_days": 2190,
                "regions": ["US"]
            }
        ]
    }


# ====================
# Admin Action Audit Trail
# ====================

def get_admin_audit_repo() -> AdminAuditRepository:
    """Get admin audit repository instance"""
    if not admin_audit_repo:
        raise HTTPException(status_code=503, detail="Admin audit repository not available")
    return admin_audit_repo


@app.get("/api/v1/audit/admin/actions", response_model=AdminAuditQueryResponse)
async def get_admin_actions(
    admin_user_id: Optional[str] = Query(None, description="Filter by admin user ID"),
    action: Optional[str] = Query(None, description="Filter by action (e.g. create_product)"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID"),
    start_time: Optional[datetime] = Query(None, description="Start of date range"),
    end_time: Optional[datetime] = Query(None, description="End of date range"),
    limit: int = Query(100, description="Max results", le=1000),
    offset: int = Query(0, description="Offset for pagination"),
    repo: AdminAuditRepository = Depends(get_admin_audit_repo),
):
    """Query admin action audit log with filters"""
    try:
        entries, total = await repo.query_admin_audit_log(
            admin_user_id=admin_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )

        filters = {
            k: v for k, v in {
                "admin_user_id": admin_user_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "start_time": start_time.isoformat() if start_time else None,
                "end_time": end_time.isoformat() if end_time else None,
            }.items() if v is not None
        }

        return AdminAuditQueryResponse(
            actions=[
                AdminAuditResponse(
                    audit_id=e.audit_id,
                    admin_user_id=e.admin_user_id,
                    admin_email=e.admin_email,
                    action=e.action,
                    resource_type=e.resource_type,
                    resource_id=e.resource_id,
                    changes=e.changes,
                    ip_address=e.ip_address,
                    user_agent=e.user_agent,
                    timestamp=e.timestamp,
                    metadata=e.metadata,
                )
                for e in entries
            ],
            total_count=total,
            limit=limit,
            offset=offset,
            filters_applied=filters,
        )

    except Exception as e:
        logger.error(f"Error querying admin audit log: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to query admin audit log: {str(e)}")


@app.post("/api/v1/audit/admin/actions", response_model=AdminAuditResponse, status_code=201)
async def record_admin_action(
    request_body: AdminAuditCreateRequest,
    repo: AdminAuditRepository = Depends(get_admin_audit_repo),
):
    """
    Record an admin action (internal endpoint, called by other services).

    This endpoint is the synchronous alternative to NATS event publishing.
    Services can POST here directly if NATS is unavailable.
    """
    try:
        import uuid as _uuid
        entry = AdminAuditLogEntry(
            audit_id=f"admin_audit_{_uuid.uuid4().hex[:16]}",
            admin_user_id=request_body.admin_user_id,
            admin_email=request_body.admin_email,
            action=request_body.action,
            resource_type=request_body.resource_type,
            resource_id=request_body.resource_id,
            changes=request_body.changes,
            ip_address=request_body.ip_address,
            user_agent=request_body.user_agent,
            metadata=request_body.metadata,
        )

        result = await repo.create_admin_audit_entry(entry)
        if not result:
            raise HTTPException(status_code=500, detail="Failed to record admin action")

        return AdminAuditResponse(
            audit_id=result.audit_id,
            admin_user_id=result.admin_user_id,
            admin_email=result.admin_email,
            action=result.action,
            resource_type=result.resource_type,
            resource_id=result.resource_id,
            changes=result.changes,
            ip_address=result.ip_address,
            user_agent=result.user_agent,
            timestamp=result.timestamp,
            metadata=result.metadata,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording admin action: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to record admin action: {str(e)}")


# ====================
# 系统管理
# ====================

@app.post("/api/v1/audit/maintenance/cleanup")
async def cleanup_old_data(
    retention_days: int = Query(365, description="数据保留天数"),
    svc: AuditService = Depends(get_audit_service)
):
    """清理过期数据"""
    try:
        logger.info(f"开始数据清理: 保留{retention_days}天")
        
        result = await svc.cleanup_old_data(retention_days)
        
        return {
            "message": "数据清理完成",
            "cleaned_events": result["cleaned_events"],
            "retention_days": result["retention_days"],
            "cleanup_timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"数据清理失败: {e}")
        raise HTTPException(status_code=500, detail=f"数据清理失败: {str(e)}")


# ====================
# 批量操作
# ====================

@app.post("/api/v1/audit/events/batch")
async def log_batch_events(
    events: List[AuditEventCreateRequest],
    svc: AuditService = Depends(get_audit_service)
):
    """批量记录审计事件"""
    try:
        if len(events) > 100:
            raise HTTPException(status_code=400, detail="批量事件数量不能超过100")
        
        logger.info(f"批量记录 {len(events)} 个审计事件")
        
        results = []
        failed_count = 0
        
        for event_request in events:
            try:
                result = await svc.log_event(event_request)
                if result:
                    results.append(result)
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"批量事件记录失败: {e}")
                failed_count += 1
        
        return {
            "message": "批量事件记录完成",
            "successful_count": len(results),
            "failed_count": failed_count,
            "total_count": len(events),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"批量事件记录失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量操作失败: {str(e)}")


if __name__ == "__main__":
    # Print configuration summary for debugging
    config_manager.print_config_summary()
    
    logger.info(f"🚀 Starting Audit Microservice on port {config.service_port}...")
    uvicorn.run(
        app,
        host=config.service_host,
        port=config.service_port,
        log_level=config.log_level.lower()
    )
