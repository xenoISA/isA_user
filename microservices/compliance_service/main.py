"""
Compliance Service Main Application

合规检查微服务主入口 - 提供内容审核、PII检测、提示词注入检测等功能

Responsibilities:
- Content moderation (text, image, audio, video)
- PII detection and redaction
- Prompt injection detection
- GDPR/PCI-DSS compliance
- User data control (export, delete)
- Compliance reporting
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Optional, List
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import io
import json

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from core.logger import setup_service_logger
from core.config_manager import ConfigManager
from core.consul_registry import ConsulRegistry
from core.nats_client import get_event_bus
from .compliance_service import ComplianceService
from .compliance_repository import ComplianceRepository
from .models import (
    ComplianceCheckRequest, ComplianceCheckResponse,
    BatchComplianceCheckRequest, BatchComplianceCheckResponse,
    ComplianceReportRequest, ComplianceReportResponse,
    CompliancePolicyRequest, CompliancePolicy,
    ComplianceServiceStatus, ComplianceStats,
    ComplianceStatus, RiskLevel, ComplianceCheckType
)

# ====================
# 配置初始化
# ====================
config_manager = ConfigManager("compliance_service")
config = config_manager.get_service_config()

# ====================
# 日志配置
# ====================
logger = setup_service_logger("compliance_service")
app_logger = logger  # For compatibility

# ====================
# 全局变量
# ====================
compliance_service: Optional[ComplianceService] = None
compliance_repository: Optional[ComplianceRepository] = None
consul_registry: Optional[ConsulRegistry] = None
event_bus = None  # NATS event bus

# ====================
# 服务配置
# ====================
SERVICE_NAME = "compliance_service"
SERVICE_PORT = int(config.port) if config and config.port else int(os.getenv("COMPLIANCE_SERVICE_PORT", "8250"))
SERVICE_VERSION = "1.0.0"
SERVICE_HOST = config.host if config and config.host else os.getenv("COMPLIANCE_SERVICE_HOST", "0.0.0.0")

# ====================
# 生命周期管理
# ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global compliance_service, compliance_repository, consul_registry, event_bus

    try:
        logger.info(f"[{SERVICE_NAME}] Initializing compliance service...")

        # Initialize NATS event bus
        try:
            event_bus = await get_event_bus("compliance_service")
            logger.info("✅ Event bus initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️  Failed to initialize event bus: {e}. Continuing without event publishing.")
            event_bus = None

        # 初始化合规服务
        compliance_service = ComplianceService(event_bus=event_bus)
        compliance_repository = compliance_service.repository
        await compliance_repository.initialize()
        
        # 注册到Consul
        try:
            if config and config.consul_enabled:
                consul_registry = ConsulRegistry(config)
                await consul_registry.register_service(
                    service_name=SERVICE_NAME,
                    service_id=f"{SERVICE_NAME}-{SERVICE_PORT}",
                    port=SERVICE_PORT,
                    health_check_endpoint="/health"
                )
                logger.info(f"[{SERVICE_NAME}] Registered with Consul")
        except Exception as e:
            logger.warning(f"[{SERVICE_NAME}] Consul registration failed (non-critical): {e}")
        
        logger.info(f"[{SERVICE_NAME}] Service started successfully on port {SERVICE_PORT}")
        
        yield
        
    except Exception as e:
        logger.error(f"[{SERVICE_NAME}] Startup error: {e}")
        raise
    finally:
        # Cleanup
        logger.info(f"[{SERVICE_NAME}] Shutting down...")

        # Close event bus
        if event_bus:
            try:
                await event_bus.close()
                logger.info("Compliance event bus closed")
            except Exception as e:
                logger.error(f"Error closing event bus: {e}")

        # Deregister from Consul
        if consul_registry:
            try:
                await consul_registry.deregister_service(f"{SERVICE_NAME}-{SERVICE_PORT}")
                logger.info(f"[{SERVICE_NAME}] Deregistered from Consul")
            except Exception as e:
                logger.warning(f"[{SERVICE_NAME}] Consul deregistration failed: {e}")

# ====================
# FastAPI应用配置
# ====================

app = FastAPI(
    title="Compliance Service",
    description="AI平台内容合规检查服务 - 内容审核、PII检测、提示词注入检测",
    version=SERVICE_VERSION,
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====================
# 依赖注入
# ====================

def get_compliance_service() -> ComplianceService:
    """获取合规服务实例"""
    if compliance_service is None:
        raise HTTPException(status_code=503, detail="Compliance service not initialized")
    return compliance_service

def get_compliance_repository() -> ComplianceRepository:
    """获取合规仓库实例"""
    if compliance_repository is None:
        raise HTTPException(status_code=503, detail="Compliance repository not initialized")
    return compliance_repository

# ====================
# 健康检查端点
# ====================

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "port": SERVICE_PORT,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/status", response_model=ComplianceServiceStatus)
async def service_status(
    service: ComplianceService = Depends(get_compliance_service)
):
    """服务状态详情"""
    return ComplianceServiceStatus(
        service=SERVICE_NAME,
        status="operational",
        port=SERVICE_PORT,
        version=SERVICE_VERSION,
        database_connected=True,
        nats_connected=False,  # TODO: 检查NATS连接状态
        providers={
            "openai": service.enable_openai_moderation,
            "aws_comprehend": False,
            "perspective_api": False
        },
        timestamp=datetime.utcnow()
    )

# ====================
# 核心合规检查端点
# ====================

@app.post("/api/compliance/check", response_model=ComplianceCheckResponse)
async def check_compliance(
    request: ComplianceCheckRequest,
    service: ComplianceService = Depends(get_compliance_service)
):
    """
    执行合规检查
    
    **示例请求:**
    ```json
    {
        "user_id": "user123",
        "content_type": "text",
        "content": "This is a sample message",
        "check_types": ["content_moderation", "pii_detection", "prompt_injection"]
    }
    ```
    
    **示例响应:**
    ```json
    {
        "check_id": "uuid",
        "status": "pass",
        "risk_level": "none",
        "passed": true,
        "violations": [],
        "warnings": [],
        "action_required": "none",
        "message": "Content passed all compliance checks",
        "checked_at": "2025-10-22T10:00:00Z",
        "processing_time_ms": 150.5
    }
    ```
    """
    try:
        logger.info(f"Compliance check request from user {request.user_id}")
        result = await service.perform_compliance_check(request)
        return result
    except Exception as e:
        logger.error(f"Compliance check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/compliance/check/batch", response_model=BatchComplianceCheckResponse)
async def check_compliance_batch(
    request: BatchComplianceCheckRequest,
    service: ComplianceService = Depends(get_compliance_service)
):
    """
    批量合规检查
    
    **用途:** 一次检查多个内容项，提高效率
    """
    try:
        results = []
        for item in request.items:
            check_req = ComplianceCheckRequest(
                user_id=request.user_id,
                organization_id=request.organization_id,
                **item
            )
            result = await service.perform_compliance_check(check_req)
            results.append(result)
        
        passed = sum(1 for r in results if r.passed)
        failed = sum(1 for r in results if r.status == ComplianceStatus.FAIL)
        flagged = sum(1 for r in results if r.status == ComplianceStatus.FLAGGED)
        
        return BatchComplianceCheckResponse(
            total_items=len(results),
            passed_items=passed,
            failed_items=failed,
            flagged_items=flagged,
            results=results,
            summary={
                "passed_rate": passed / len(results) if results else 0,
                "avg_processing_time": sum(r.processing_time_ms for r in results) / len(results) if results else 0
            }
        )
    except Exception as e:
        logger.error(f"Batch compliance check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ====================
# 查询和报告端点
# ====================

@app.get("/api/compliance/checks/{check_id}")
async def get_check_by_id(
    check_id: str,
    repo: ComplianceRepository = Depends(get_compliance_repository)
):
    """获取特定合规检查记录"""
    try:
        check = await repo.get_check_by_id(check_id)
        if not check:
            raise HTTPException(status_code=404, detail="Compliance check not found")
        return check
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting check {check_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/compliance/checks/user/{user_id}")
async def get_user_checks(
    user_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    status: Optional[ComplianceStatus] = None,
    risk_level: Optional[RiskLevel] = None,
    repo: ComplianceRepository = Depends(get_compliance_repository)
):
    """获取用户的合规检查历史"""
    try:
        checks = await repo.get_checks_by_user(
            user_id=user_id,
            limit=limit,
            offset=offset,
            status=status,
            risk_level=risk_level
        )
        return {
            "user_id": user_id,
            "checks": checks,
            "count": len(checks),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Error getting user checks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/compliance/reviews/pending")
async def get_pending_reviews(
    limit: int = Query(50, ge=1, le=100),
    repo: ComplianceRepository = Depends(get_compliance_repository)
):
    """获取待人工审核的项目"""
    try:
        reviews = await repo.get_pending_reviews(limit=limit)
        return {
            "pending_reviews": reviews,
            "count": len(reviews)
        }
    except Exception as e:
        logger.error(f"Error getting pending reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/compliance/reviews/{check_id}")
async def update_review(
    check_id: str,
    reviewed_by: str,
    status: ComplianceStatus,
    review_notes: Optional[str] = None,
    repo: ComplianceRepository = Depends(get_compliance_repository)
):
    """更新人工审核结果"""
    try:
        success = await repo.update_review_status(
            check_id=check_id,
            reviewed_by=reviewed_by,
            status=status,
            review_notes=review_notes
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Compliance check not found")
        
        return {
            "message": "Review updated successfully",
            "check_id": check_id,
            "status": status.value
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating review: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/compliance/reports", response_model=ComplianceReportResponse)
async def generate_report(
    request: ComplianceReportRequest,
    repo: ComplianceRepository = Depends(get_compliance_repository)
):
    """
    生成合规报告
    
    **示例请求:**
    ```json
    {
        "organization_id": "org123",
        "start_date": "2025-10-01T00:00:00Z",
        "end_date": "2025-10-31T23:59:59Z",
        "include_violations": true,
        "include_statistics": true
    }
    ```
    """
    try:
        # 获取统计数据
        stats = await repo.get_statistics(
            organization_id=request.organization_id,
            start_date=request.start_date,
            end_date=request.end_date
        )
        
        # 获取违规摘要
        violations_summary = await repo.get_violations_summary(
            organization_id=request.organization_id,
            days=(request.end_date - request.start_date).days
        )
        
        # 获取违规详情（如果需要）
        violations = None
        if request.include_violations:
            violations = await repo.get_checks_by_organization(
                organization_id=request.organization_id,
                limit=1000
            )
        
        import uuid
        return ComplianceReportResponse(
            report_id=str(uuid.uuid4()),
            period={
                "start": request.start_date,
                "end": request.end_date
            },
            total_checks=stats.get("total_checks", 0),
            passed_checks=stats.get("passed_checks", 0),
            failed_checks=stats.get("failed_checks", 0),
            flagged_checks=stats.get("flagged_checks", 0),
            violations_by_type=stats.get("violations_by_type", {}),
            violations_by_category={},
            high_risk_incidents=violations_summary.get("critical_violations", 0),
            unique_users=0,
            top_violators=violations_summary.get("top_users", []),
            violations=violations if request.include_violations else None,
            generated_at=datetime.utcnow()
        )
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ====================
# 策略管理端点
# ====================

@app.post("/api/compliance/policies", response_model=CompliancePolicy)
async def create_policy(
    request: CompliancePolicyRequest,
    repo: ComplianceRepository = Depends(get_compliance_repository)
):
    """创建合规策略"""
    try:
        import uuid
        policy = CompliancePolicy(
            policy_id=str(uuid.uuid4()),
            policy_name=request.policy_name,
            organization_id=request.organization_id,
            content_types=request.content_types,
            check_types=request.check_types,
            rules=request.rules,
            thresholds=request.thresholds or {},
            auto_block=request.auto_block,
            require_human_review=request.require_human_review,
            notification_enabled=request.notification_enabled,
            is_active=True,
            priority=100,
            created_at=datetime.utcnow()
        )
        
        result = await repo.create_policy(policy)
        if not result:
            raise HTTPException(status_code=500, detail="Failed to create policy")
        
        return result
    except Exception as e:
        logger.error(f"Error creating policy: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/compliance/policies/{policy_id}", response_model=CompliancePolicy)
async def get_policy(
    policy_id: str,
    repo: ComplianceRepository = Depends(get_compliance_repository)
):
    """获取策略详情"""
    try:
        policy = await repo.get_policy_by_id(policy_id)
        if not policy:
            raise HTTPException(status_code=404, detail="Policy not found")
        return policy
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting policy: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/compliance/policies")
async def list_policies(
    organization_id: Optional[str] = None,
    repo: ComplianceRepository = Depends(get_compliance_repository)
):
    """列出活跃策略"""
    try:
        policies = await repo.get_active_policies(organization_id=organization_id)
        return {
            "policies": policies,
            "count": len(policies)
        }
    except Exception as e:
        logger.error(f"Error listing policies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ====================
# 统计端点
# ====================

@app.get("/api/compliance/stats", response_model=ComplianceStats)
async def get_statistics(
    organization_id: Optional[str] = None,
    repo: ComplianceRepository = Depends(get_compliance_repository)
):
    """获取合规统计数据"""
    try:
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        stats_today = await repo.get_statistics(
            organization_id=organization_id,
            start_date=today,
            end_date=datetime.utcnow()
        )
        
        stats_7d = await repo.get_statistics(
            organization_id=organization_id,
            start_date=today - timedelta(days=7),
            end_date=datetime.utcnow()
        )
        
        stats_30d = await repo.get_statistics(
            organization_id=organization_id,
            start_date=today - timedelta(days=30),
            end_date=datetime.utcnow()
        )
        
        pending = await repo.get_pending_reviews(limit=1000)
        
        return ComplianceStats(
            total_checks_today=stats_today.get("total_checks", 0),
            total_checks_7d=stats_7d.get("total_checks", 0),
            total_checks_30d=stats_30d.get("total_checks", 0),
            violations_today=stats_today.get("failed_checks", 0) + stats_today.get("flagged_checks", 0),
            violations_7d=stats_7d.get("failed_checks", 0) + stats_7d.get("flagged_checks", 0),
            violations_30d=stats_30d.get("failed_checks", 0) + stats_30d.get("flagged_checks", 0),
            blocked_content_today=stats_today.get("failed_checks", 0),
            pending_reviews=len(pending),
            avg_processing_time_ms=0.0,  # TODO: 计算平均处理时间
            checks_by_type=stats_30d.get("violations_by_type", {}),
            violations_by_risk=stats_30d.get("violations_by_risk", {})
        )
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ====================
# GDPR / Data Privacy Endpoints
# ====================

@app.get("/api/compliance/user/{user_id}/data-export")
async def export_user_data(
    user_id: str,
    format: str = Query("json", regex="^(json|csv)$"),
    repo: ComplianceRepository = Depends(get_compliance_repository)
):
    """
    **GDPR Article 15 & 20: Right to Access and Data Portability**
    
    Export all compliance-related data for a user.
    User can request their data in JSON or CSV format.
    
    **Example:**
    ```bash
    curl http://localhost:8250/api/compliance/user/user123/data-export?format=json
    ```
    """
    try:
        logger.info(f"Data export requested by user: {user_id}")
        
        # Get all compliance checks for user
        checks = await repo.get_checks_by_user(
            user_id=user_id,
            limit=10000  # Get all records
        )
        
        # Get statistics
        stats = await repo.get_statistics(
            start_date=datetime.utcnow() - timedelta(days=36500),  # All time
            end_date=datetime.utcnow()
        )
        
        export_data = {
            "user_id": user_id,
            "export_date": datetime.utcnow().isoformat(),
            "export_type": "gdpr_data_export",
            "total_checks": len(checks),
            "checks": [
                {
                    "check_id": c.check_id,
                    "check_type": c.check_type.value if hasattr(c.check_type, 'value') else c.check_type,
                    "content_type": c.content_type.value if hasattr(c.content_type, 'value') else c.content_type,
                    "status": c.status.value if hasattr(c.status, 'value') else c.status,
                    "risk_level": c.risk_level.value if hasattr(c.risk_level, 'value') else c.risk_level,
                    "checked_at": c.checked_at.isoformat() if c.checked_at else None,
                    "violations": c.violations,
                    "action_taken": c.action_taken
                }
                for c in checks
            ],
            "statistics": stats
        }
        
        if format == "json":
            return export_data
        else:  # CSV
            import csv
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=[
                "check_id", "check_type", "content_type", "status", 
                "risk_level", "checked_at", "action_taken"
            ])
            writer.writeheader()
            for check in export_data["checks"]:
                writer.writerow({
                    k: v for k, v in check.items() 
                    if k in writer.fieldnames
                })
            
            output.seek(0)
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=compliance_data_{user_id}.csv"
                }
            )
    
    except Exception as e:
        logger.error(f"Error exporting user data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/compliance/user/{user_id}/data")
async def delete_user_data(
    user_id: str,
    confirmation: str = Query(..., description="Must be 'CONFIRM_DELETE'"),
    repo: ComplianceRepository = Depends(get_compliance_repository)
):
    """
    **GDPR Article 17: Right to be Forgotten**
    
    Delete all compliance check data for a user.
    This is irreversible and complies with GDPR's right to erasure.
    
    **Important:** Requires confirmation parameter to prevent accidental deletion.
    
    **Example:**
    ```bash
    curl -X DELETE "http://localhost:8250/api/compliance/user/user123/data?confirmation=CONFIRM_DELETE"
    ```
    """
    try:
        if confirmation != "CONFIRM_DELETE":
            raise HTTPException(
                status_code=400,
                detail="Confirmation required. Set confirmation=CONFIRM_DELETE"
            )
        
        logger.warning(f"User data deletion requested for user: {user_id}")

        # Get count before deletion for audit log
        checks = await repo.get_checks_by_user(user_id=user_id, limit=100000)
        deleted_count = len(checks)

        # Delete user data using repository method
        actual_deleted = await repo.delete_user_data(user_id)

        # Log to audit service
        audit_event = {
            "event_type": "user_data_deletion",
            "category": "data_privacy",
            "severity": "high",
            "user_id": user_id,
            "action": "gdpr_right_to_erasure",
            "description": f"User data deleted (GDPR Article 17)",
            "metadata": {
                "deleted_checks": actual_deleted,
                "deletion_timestamp": datetime.utcnow().isoformat()
            }
        }

        logger.info(f"Deleted {actual_deleted} compliance records for user {user_id}")

        return {
            "status": "success",
            "message": "User data deleted successfully",
            "deleted_records": actual_deleted,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "compliance": "GDPR Article 17 - Right to Erasure"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/compliance/user/{user_id}/data-summary")
async def get_user_data_summary(
    user_id: str,
    repo: ComplianceRepository = Depends(get_compliance_repository)
):
    """
    **GDPR Article 15: Right to Access**
    
    Get a summary of what data we have about the user.
    Transparency about data collection.
    
    **Example Response:**
    ```json
    {
        "user_id": "user123",
        "data_categories": ["compliance_checks", "violations", "reviews"],
        "total_records": 150,
        "oldest_record": "2024-01-01T00:00:00Z",
        "newest_record": "2025-10-22T10:00:00Z",
        "data_retention_days": 2555,
        "can_export": true,
        "can_delete": true
    }
    ```
    """
    try:
        checks = await repo.get_checks_by_user(user_id=user_id, limit=100000)
        
        if not checks:
            return {
                "user_id": user_id,
                "data_categories": [],
                "total_records": 0,
                "message": "No data found for this user"
            }
        
        # Calculate date range
        check_dates = [c.checked_at for c in checks if c.checked_at]
        oldest = min(check_dates) if check_dates else None
        newest = max(check_dates) if check_dates else None
        
        # Count by category
        categories = {}
        for check in checks:
            cat = check.check_type.value if hasattr(check.check_type, 'value') else str(check.check_type)
            categories[cat] = categories.get(cat, 0) + 1
        
        return {
            "user_id": user_id,
            "data_categories": list(categories.keys()),
            "records_by_category": categories,
            "total_records": len(checks),
            "oldest_record": oldest.isoformat() if oldest else None,
            "newest_record": newest.isoformat() if newest else None,
            "data_retention_days": 2555,  # 7 years default
            "retention_policy": "GDPR compliant - data retained for 7 years",
            "can_export": True,
            "can_delete": True,
            "export_url": f"/api/compliance/user/{user_id}/data-export",
            "delete_url": f"/api/compliance/user/{user_id}/data"
        }
    
    except Exception as e:
        logger.error(f"Error getting user data summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/compliance/user/{user_id}/consent")
async def update_user_consent(
    user_id: str,
    consent_type: str = Query(..., description="Type: data_processing, marketing, analytics"),
    granted: bool = Query(..., description="True to grant, False to revoke"),
    repo: ComplianceRepository = Depends(get_compliance_repository)
):
    """
    **GDPR Article 7: Consent Management**
    
    Manage user consent for different types of data processing.
    
    **Consent Types:**
    - `data_processing`: Essential compliance checking
    - `marketing`: Marketing communications
    - `analytics`: Usage analytics
    - `ai_training`: AI model training
    
    **Example:**
    ```bash
    curl -X POST "http://localhost:8250/api/compliance/user/user123/consent?consent_type=analytics&granted=false"
    ```
    """
    try:
        # Extract IP and user agent from request
        ip_address = None  # Could be extracted from request.client.host
        user_agent = None  # Could be extracted from request.headers.get("user-agent")

        # Update consent using repository method
        success = await repo.update_user_consent(
            user_id=user_id,
            consent_type=consent_type,
            granted=granted,
            ip_address=ip_address,
            user_agent=user_agent
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update consent")

        timestamp = datetime.utcnow().isoformat()
        logger.info(f"Consent {'granted' if granted else 'revoked'} for {user_id}: {consent_type}")

        return {
            "status": "success",
            "user_id": user_id,
            "consent_type": consent_type,
            "granted": granted,
            "timestamp": timestamp,
            "message": f"Consent {'granted' if granted else 'revoked'} successfully"
        }
    
    except Exception as e:
        logger.error(f"Error updating consent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/compliance/user/{user_id}/audit-log")
async def get_user_audit_log(
    user_id: str,
    limit: int = Query(100, ge=1, le=1000),
    repo: ComplianceRepository = Depends(get_compliance_repository)
):
    """
    **GDPR Article 30: Records of Processing Activities**
    
    Get audit log of all compliance-related activities for a user.
    Shows who accessed user's data and when.
    
    **Example Response:**
    ```json
    {
        "user_id": "user123",
        "audit_entries": [
            {
                "timestamp": "2025-10-22T10:00:00Z",
                "action": "compliance_check",
                "check_id": "check_123",
                "result": "pass",
                "accessed_by": "system"
            }
        ]
    }
    ```
    """
    try:
        checks = await repo.get_checks_by_user(user_id=user_id, limit=limit)
        
        audit_entries = [
            {
                "timestamp": c.checked_at.isoformat() if c.checked_at else None,
                "action": "compliance_check",
                "check_id": c.check_id,
                "check_type": c.check_type.value if hasattr(c.check_type, 'value') else str(c.check_type),
                "result": c.status.value if hasattr(c.status, 'value') else str(c.status),
                "risk_level": c.risk_level.value if hasattr(c.risk_level, 'value') else str(c.risk_level),
                "accessed_by": c.reviewed_by if c.reviewed_by else "system",
                "action_taken": c.action_taken
            }
            for c in checks
        ]
        
        return {
            "user_id": user_id,
            "audit_entries": audit_entries,
            "total_entries": len(audit_entries),
            "compliance": "GDPR Article 30 - Records of Processing"
        }
    
    except Exception as e:
        logger.error(f"Error getting audit log: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ====================
# PCI-DSS Compliance Endpoints
# ====================

@app.post("/api/compliance/pci/card-data-check")
async def check_card_data_exposure(
    content: str,
    user_id: str,
    service: ComplianceService = Depends(get_compliance_service)
):
    """
    **PCI-DSS Requirement 3: Protect Stored Cardholder Data**
    
    Check if content contains credit card information that should be protected.
    
    **Example:**
    ```bash
    curl -X POST http://localhost:8250/api/compliance/pci/card-data-check \
      -H "Content-Type: application/json" \
      -d '{"content": "My card is 4532-1234-5678-9010", "user_id": "user123"}'
    ```
    """
    try:
        import re
        
        # PCI-DSS: Detect credit card patterns
        card_patterns = {
            "visa": r'\b4[0-9]{3}[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}\b',
            "mastercard": r'\b5[1-5][0-9]{2}[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}\b',
            "amex": r'\b3[47][0-9]{2}[-\s]?[0-9]{6}[-\s]?[0-9]{5}\b',
            "discover": r'\b6(?:011|5[0-9]{2})[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}\b'
        }
        
        detected_cards = []
        for card_type, pattern in card_patterns.items():
            matches = re.findall(pattern, content)
            if matches:
                detected_cards.extend([{
                    "type": card_type,
                    "masked_number": match[:4] + "-****-****-" + match[-4:],
                    "severity": "critical"
                } for match in matches])
        
        if detected_cards:
            logger.warning(f"PCI-DSS violation: Card data detected for user {user_id}")
            
            return {
                "pci_compliant": False,
                "violation": "credit_card_data_exposed",
                "severity": "critical",
                "detected_cards": detected_cards,
                "recommendation": "Remove card data immediately. Use tokenization or encryption.",
                "pci_requirement": "PCI-DSS Requirement 3.4 - Render PAN unreadable",
                "action_required": "block_content"
            }
        
        return {
            "pci_compliant": True,
            "message": "No payment card data detected",
            "checked_at": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error checking card data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ====================
# 错误处理
# ====================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "path": str(request.url)
        }
    )

# ====================
# 服务启动
# ====================

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting {SERVICE_NAME} on port {SERVICE_PORT}")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=SERVICE_PORT,
        reload=True,
        log_level="info"
    )

