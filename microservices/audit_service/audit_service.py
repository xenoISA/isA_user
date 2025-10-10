"""
Audit Service Business Logic

审计服务业务逻辑层，处理审计事件记录、查询、分析、告警和合规报告
"""

import logging
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from .audit_repository import AuditRepository
from .models import (
    AuditEvent, UserActivity, SecurityEvent, ComplianceReport,
    AuditEventCreateRequest, AuditEventResponse, AuditQueryRequest, AuditQueryResponse,
    UserActivitySummary, SecurityAlertRequest, ComplianceReportRequest,
    EventType, EventSeverity, EventStatus, AuditCategory
)

logger = logging.getLogger(__name__)


class AuditService:
    """审计服务核心业务逻辑"""
    
    def __init__(self):
        self.repository = AuditRepository()
        
        # 风险评分配置
        self.risk_thresholds = {
            "low": 30,
            "medium": 60,
            "high": 80,
            "critical": 95
        }
        
        # 合规标准配置
        self.compliance_standards = {
            "GDPR": {
                "retention_days": 2555,  # 7 years
                "required_fields": ["user_id", "action", "timestamp", "ip_address"],
                "sensitive_events": [EventType.USER_DELETE, EventType.PERMISSION_GRANT]
            },
            "SOX": {
                "retention_days": 2555,  # 7 years
                "required_fields": ["user_id", "action", "timestamp"],
                "sensitive_events": [EventType.RESOURCE_UPDATE, EventType.PERMISSION_UPDATE]
            },
            "HIPAA": {
                "retention_days": 2190,  # 6 years
                "required_fields": ["user_id", "action", "timestamp", "resource_type"],
                "sensitive_events": [EventType.RESOURCE_ACCESS, EventType.USER_UPDATE]
            }
        }
    
    # ====================
    # 核心审计事件管理
    # ====================
    
    async def log_event(self, request: AuditEventCreateRequest) -> Optional[AuditEventResponse]:
        """记录审计事件"""
        try:
            logger.info(f"记录审计事件: {request.event_type.value} - {request.action}")
            
            # 创建审计事件对象
            audit_event = AuditEvent(
                event_type=request.event_type,
                category=request.category,
                severity=request.severity,
                status=EventStatus.SUCCESS if request.success else EventStatus.FAILURE,
                action=request.action,
                description=request.description,
                
                user_id=request.user_id,
                session_id=request.session_id,
                organization_id=request.organization_id,
                
                resource_type=request.resource_type,
                resource_id=request.resource_id,
                resource_name=request.resource_name,
                
                ip_address=request.ip_address,
                user_agent=request.user_agent,
                api_endpoint=request.api_endpoint,
                http_method=request.http_method,
                
                success=request.success,
                error_code=request.error_code,
                error_message=request.error_message,
                
                metadata=request.metadata,
                tags=request.tags,
                
                timestamp=datetime.utcnow()
            )
            
            # 自动设置合规相关字段
            await self._apply_compliance_policies(audit_event)
            
            # 保存到数据库
            created_event = await self.repository.create_audit_event(audit_event)
            if not created_event:
                logger.error("保存审计事件失败")
                return None
            
            # 触发实时分析
            await self._trigger_real_time_analysis(created_event)
            
            # 转换为响应格式
            return AuditEventResponse(
                id=created_event.id,
                event_type=created_event.event_type,
                category=created_event.category,
                severity=created_event.severity,
                status=created_event.status,
                action=created_event.action,
                description=created_event.description,
                user_id=created_event.user_id,
                organization_id=created_event.organization_id,
                resource_type=created_event.resource_type,
                resource_name=created_event.resource_name,
                success=created_event.success,
                timestamp=created_event.timestamp,
                metadata=created_event.metadata
            )
            
        except Exception as e:
            logger.error(f"记录审计事件失败: {e}")
            return None
    
    async def query_events(self, query: AuditQueryRequest) -> AuditQueryResponse:
        """查询审计事件"""
        try:
            logger.info(f"查询审计事件: 类型={query.event_types}, 用户={query.user_id}")
            
            # 验证查询参数
            await self._validate_query_parameters(query)
            
            # 执行查询
            events = await self.repository.query_audit_events(query)
            
            # 计算总数（简化版本）
            total_count = len(events)
            
            # 转换为响应格式
            event_responses = [
                AuditEventResponse(
                    id=event.id,
                    event_type=event.event_type,
                    category=event.category,
                    severity=event.severity,
                    status=event.status,
                    action=event.action,
                    description=event.description,
                    user_id=event.user_id,
                    organization_id=event.organization_id,
                    resource_type=event.resource_type,
                    resource_name=event.resource_name,
                    success=event.success,
                    timestamp=event.timestamp,
                    metadata=event.metadata
                )
                for event in events
            ]
            
            return AuditQueryResponse(
                events=event_responses,
                total_count=total_count,
                page_info={
                    "limit": query.limit,
                    "offset": query.offset,
                    "has_more": total_count >= query.limit
                },
                filters_applied={
                    "event_types": [et.value for et in query.event_types] if query.event_types else None,
                    "categories": [cat.value for cat in query.categories] if query.categories else None,
                    "user_id": query.user_id,
                    "time_range": {
                        "start": query.start_time.isoformat() if query.start_time else None,
                        "end": query.end_time.isoformat() if query.end_time else None
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"查询审计事件失败: {e}")
            return AuditQueryResponse(
                events=[],
                total_count=0,
                page_info={"limit": query.limit, "offset": query.offset, "has_more": False},
                filters_applied={}
            )
    
    # ====================
    # 用户活动分析
    # ====================
    
    async def get_user_activities(self, user_id: str, days: int = 30, limit: int = 100) -> List[UserActivity]:
        """获取用户活动记录"""
        try:
            logger.info(f"获取用户活动: {user_id}, 天数={days}")
            
            activities = await self.repository.get_user_activities(user_id, days, limit)
            return activities
            
        except Exception as e:
            logger.error(f"获取用户活动失败: {e}")
            return []
    
    async def get_user_activity_summary(self, user_id: str, days: int = 30) -> UserActivitySummary:
        """获取用户活动摘要"""
        try:
            logger.info(f"生成用户活动摘要: {user_id}")
            
            summary_data = await self.repository.get_user_activity_summary(user_id, days)
            
            return UserActivitySummary(
                user_id=user_id,
                total_activities=summary_data.get("total_activities", 0),
                success_count=summary_data.get("success_count", 0),
                failure_count=summary_data.get("failure_count", 0),
                last_activity=datetime.fromisoformat(summary_data["last_activity"]) if summary_data.get("last_activity") else None,
                most_common_activities=summary_data.get("most_common_activities", []),
                risk_score=summary_data.get("risk_score", 0.0),
                metadata={
                    "period_days": days,
                    "analysis_timestamp": datetime.utcnow().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"生成用户活动摘要失败: {e}")
            return UserActivitySummary(
                user_id=user_id,
                total_activities=0,
                success_count=0,
                failure_count=0,
                last_activity=None,
                most_common_activities=[],
                risk_score=0.0
            )
    
    # ====================
    # 安全事件管理
    # ====================
    
    async def create_security_alert(self, alert: SecurityAlertRequest) -> Optional[SecurityEvent]:
        """创建安全告警"""
        try:
            logger.warning(f"创建安全告警: {alert.threat_type} - {alert.severity.value}")
            
            security_event = SecurityEvent(
                event_type=EventType.SECURITY_ALERT,
                severity=alert.severity,
                threat_level=self._calculate_threat_level(alert.severity),
                
                source_ip=alert.source_ip,
                target_resource=alert.target_resource,
                
                detection_method="manual_report",
                confidence_score=0.8,
                
                response_action="investigation_required",
                investigation_status="open",
                
                detected_at=datetime.utcnow(),
                metadata=alert.metadata
            )
            
            created_event = await self.repository.create_security_event(security_event)
            if created_event:
                # 触发安全响应流程
                await self._trigger_security_response(created_event)
            
            return created_event
            
        except Exception as e:
            logger.error(f"创建安全告警失败: {e}")
            return None
    
    async def get_security_events(self, days: int = 7, severity: Optional[EventSeverity] = None) -> List[SecurityEvent]:
        """获取安全事件列表"""
        try:
            return await self.repository.get_security_events(days, severity)
        except Exception as e:
            logger.error(f"获取安全事件失败: {e}")
            return []
    
    # ====================
    # 合规报告
    # ====================
    
    async def generate_compliance_report(self, request: ComplianceReportRequest) -> Optional[ComplianceReport]:
        """生成合规报告"""
        try:
            logger.info(f"生成合规报告: {request.compliance_standard}")
            
            # 获取合规标准配置
            standard_config = self.compliance_standards.get(request.compliance_standard)
            if not standard_config:
                logger.error(f"不支持的合规标准: {request.compliance_standard}")
                return None
            
            # 查询相关事件
            query = AuditQueryRequest(
                start_time=request.period_start,
                end_time=request.period_end,
                limit=10000  # 合规报告需要完整数据
            )
            
            if request.filters:
                # 应用自定义过滤器
                if "event_types" in request.filters:
                    query.event_types = [EventType(et) for et in request.filters["event_types"]]
                if "user_id" in request.filters:
                    query.user_id = request.filters["user_id"]
            
            events = await self.repository.query_audit_events(query)
            
            # 分析合规性
            compliance_analysis = await self._analyze_compliance(events, standard_config)
            
            # 生成报告
            report = ComplianceReport(
                report_type=request.report_type,
                compliance_standard=request.compliance_standard,
                period_start=request.period_start,
                period_end=request.period_end,
                
                total_events=len(events),
                compliant_events=compliance_analysis["compliant_count"],
                non_compliant_events=compliance_analysis["non_compliant_count"],
                compliance_score=compliance_analysis["compliance_score"],
                
                findings=compliance_analysis["findings"] if request.include_details else None,
                recommendations=compliance_analysis["recommendations"],
                risk_assessment=compliance_analysis["risk_assessment"],
                
                generated_at=datetime.utcnow(),
                generated_by="audit_service",
                status="final",
                metadata={
                    "standard_config": standard_config,
                    "query_filters": request.filters,
                    "include_details": request.include_details
                }
            )
            
            return report
            
        except Exception as e:
            logger.error(f"生成合规报告失败: {e}")
            return None
    
    # ====================
    # 统计和分析
    # ====================
    
    async def get_service_statistics(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        try:
            # 获取基础统计
            stats = await self.repository.get_event_statistics(30)
            
            # 添加合规评分
            compliance_score = await self._calculate_overall_compliance_score()
            stats["compliance_score"] = compliance_score
            
            return stats
            
        except Exception as e:
            logger.error(f"获取服务统计失败: {e}")
            return {
                "total_events": 0,
                "events_today": 0,
                "active_users": 0,
                "security_alerts": 0,
                "compliance_score": 0.0
            }
    
    # ====================
    # 数据维护
    # ====================
    
    async def cleanup_old_data(self, retention_days: int = 365) -> Dict[str, int]:
        """清理过期数据"""
        try:
            logger.info(f"开始清理超过 {retention_days} 天的数据")
            
            cleaned_events = await self.repository.cleanup_old_events(retention_days)
            
            return {
                "cleaned_events": cleaned_events,
                "retention_days": retention_days
            }
            
        except Exception as e:
            logger.error(f"清理数据失败: {e}")
            return {"cleaned_events": 0, "retention_days": retention_days}
    
    # ====================
    # 私有辅助方法
    # ====================
    
    async def _apply_compliance_policies(self, event: AuditEvent) -> None:
        """应用合规策略"""
        try:
            # 设置数据保留策略
            if event.category == AuditCategory.SECURITY:
                event.retention_policy = "7_years"
            elif event.category == AuditCategory.AUTHENTICATION:
                event.retention_policy = "3_years"
            else:
                event.retention_policy = "1_year"
            
            # 设置合规标志
            compliance_flags = []
            
            # GDPR相关事件
            if event.user_id and event.event_type in [EventType.USER_DELETE, EventType.USER_UPDATE]:
                compliance_flags.append("GDPR")
            
            # SOX相关事件
            if event.resource_type and event.event_type in [EventType.RESOURCE_UPDATE, EventType.PERMISSION_UPDATE]:
                compliance_flags.append("SOX")
            
            # HIPAA相关事件
            if event.resource_type and "health" in (event.resource_type.lower() if event.resource_type else ""):
                compliance_flags.append("HIPAA")
            
            event.compliance_flags = compliance_flags if compliance_flags else None
            
        except Exception as e:
            logger.error(f"应用合规策略失败: {e}")
    
    async def _trigger_real_time_analysis(self, event: AuditEvent) -> None:
        """触发实时分析"""
        try:
            # 检查是否需要安全告警
            if event.severity in [EventSeverity.HIGH, EventSeverity.CRITICAL]:
                logger.warning(f"高严重程度事件: {event.event_type.value} - {event.action}")
            
            # 检查异常模式
            if not event.success and event.category == AuditCategory.AUTHENTICATION:
                logger.warning(f"认证失败事件: 用户={event.user_id}, IP={event.ip_address}")
            
            # 检查权限变更
            if event.event_type in [EventType.PERMISSION_GRANT, EventType.PERMISSION_REVOKE]:
                logger.info(f"权限变更事件: {event.action}")
            
        except Exception as e:
            logger.error(f"实时分析失败: {e}")
    
    async def _trigger_security_response(self, security_event: SecurityEvent) -> None:
        """触发安全响应"""
        try:
            if security_event.severity == EventSeverity.CRITICAL:
                logger.critical(f"关键安全事件: {security_event.threat_level}")
                # 这里可以集成外部安全响应系统
            
        except Exception as e:
            logger.error(f"安全响应失败: {e}")
    
    async def _validate_query_parameters(self, query: AuditQueryRequest) -> None:
        """验证查询参数"""
        if query.limit > 1000:
            raise ValueError("查询限制不能超过1000条")
        
        if query.start_time and query.end_time:
            if query.start_time >= query.end_time:
                raise ValueError("开始时间必须早于结束时间")
            
            # 限制查询时间范围
            max_range = timedelta(days=365)
            if query.end_time - query.start_time > max_range:
                raise ValueError("查询时间范围不能超过365天")
    
    def _calculate_threat_level(self, severity: EventSeverity) -> str:
        """计算威胁级别"""
        if severity == EventSeverity.CRITICAL:
            return "critical"
        elif severity == EventSeverity.HIGH:
            return "high"
        elif severity == EventSeverity.MEDIUM:
            return "medium"
        else:
            return "low"
    
    async def _analyze_compliance(self, events: List[AuditEvent], standard_config: Dict[str, Any]) -> Dict[str, Any]:
        """分析合规性"""
        try:
            required_fields = standard_config["required_fields"]
            sensitive_events = standard_config["sensitive_events"]
            
            compliant_count = 0
            non_compliant_count = 0
            findings = []
            
            for event in events:
                is_compliant = True
                event_findings = []
                
                # 检查必需字段
                for field in required_fields:
                    if not getattr(event, field, None):
                        is_compliant = False
                        event_findings.append(f"缺少必需字段: {field}")
                
                # 检查敏感事件的特殊要求
                if event.event_type in sensitive_events:
                    if not event.metadata or "justification" not in event.metadata:
                        is_compliant = False
                        event_findings.append("敏感操作缺少理由说明")
                
                if is_compliant:
                    compliant_count += 1
                else:
                    non_compliant_count += 1
                    findings.append({
                        "event_id": event.id,
                        "event_type": event.event_type.value,
                        "timestamp": event.timestamp.isoformat(),
                        "issues": event_findings
                    })
            
            total_events = len(events)
            compliance_score = (compliant_count / total_events * 100) if total_events > 0 else 100
            
            # 生成建议
            recommendations = []
            if non_compliant_count > 0:
                recommendations.append("确保所有事件包含必需的字段")
                recommendations.append("为敏感操作添加理由说明")
            
            if compliance_score < 95:
                recommendations.append("提高数据质量以满足合规要求")
            
            # 风险评估
            risk_level = "low"
            if compliance_score < 80:
                risk_level = "high"
            elif compliance_score < 90:
                risk_level = "medium"
            
            return {
                "compliant_count": compliant_count,
                "non_compliant_count": non_compliant_count,
                "compliance_score": compliance_score,
                "findings": findings,
                "recommendations": recommendations,
                "risk_assessment": {
                    "risk_level": risk_level,
                    "compliance_score": compliance_score,
                    "total_events": total_events
                }
            }
            
        except Exception as e:
            logger.error(f"合规性分析失败: {e}")
            return {
                "compliant_count": 0,
                "non_compliant_count": len(events),
                "compliance_score": 0.0,
                "findings": [],
                "recommendations": ["合规性分析失败，需要人工审查"],
                "risk_assessment": {"risk_level": "unknown"}
            }
    
    async def _calculate_overall_compliance_score(self) -> float:
        """计算整体合规评分"""
        try:
            # 简化版本：基于过去30天的数据
            stats = await self.repository.get_event_statistics(30)
            
            total_events = stats.get("total_events", 0)
            success_rate = stats.get("success_rate", 0)
            security_alerts = stats.get("security_alerts", 0)
            
            # 基础评分基于成功率
            base_score = success_rate
            
            # 安全事件影响评分
            if total_events > 0:
                security_impact = (security_alerts / total_events) * 100
                security_penalty = min(security_impact * 2, 30)  # 最多扣30分
                base_score -= security_penalty
            
            return max(0, min(100, base_score))
            
        except Exception as e:
            logger.error(f"计算合规评分失败: {e}")
            return 0.0