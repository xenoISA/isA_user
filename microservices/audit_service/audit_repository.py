"""
Audit Repository

数据访问层，处理审计事件、安全事件、合规报告的数据库操作
使用统一的审计表结构存储所有审计相关数据
"""

import logging
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json

# Database client setup 
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.database.supabase_client import get_supabase_client
from .models import (
    AuditEvent, UserActivity, SecurityEvent, ComplianceReport,
    EventType, EventSeverity, EventStatus, AuditCategory,
    AuditQueryRequest
)

logger = logging.getLogger(__name__)


class AuditRepository:
    """审计数据访问仓库"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.table_name = "audit_events"  # 使用专门的审计事件表
    
    # ====================
    # 连接管理
    # ====================
    
    async def check_connection(self) -> bool:
        """检查数据库连接"""
        try:
            result = self.supabase.table(self.table_name).select("count").limit(1).execute()
            return True
        except Exception as e:
            logger.error(f"数据库连接检查失败: {e}")
            return False
    
    # ====================
    # 审计事件管理
    # ====================
    
    async def create_audit_event(self, event: AuditEvent) -> Optional[AuditEvent]:
        """创建审计事件"""
        try:
            data = {
                "event_type": event.event_type.value,
                "category": event.category.value,
                "severity": event.severity.value,
                "status": event.status.value,
                "action": event.action,
                "description": event.description,
                
                # 主体信息
                "user_id": event.user_id,
                "session_id": event.session_id,
                "organization_id": event.organization_id,
                
                # 资源信息
                "resource_type": event.resource_type,
                "resource_id": event.resource_id,
                "resource_name": event.resource_name,
                
                # 技术信息
                "ip_address": event.ip_address,
                "user_agent": event.user_agent,
                "api_endpoint": event.api_endpoint,
                "http_method": event.http_method,
                
                # 结果信息
                "success": event.success,
                "error_code": event.error_code,
                "error_message": event.error_message,
                
                # 元数据
                "metadata": json.dumps(event.metadata) if event.metadata else None,
                "tags": event.tags,
                
                # 时间戳
                "timestamp": event.timestamp.isoformat(),
                "created_at": datetime.utcnow().isoformat(),
                
                # 合规相关
                "retention_policy": event.retention_policy,
                "compliance_flags": event.compliance_flags
            }
            
            result = self.supabase.table(self.table_name).insert(data).execute()
            
            if result.data:
                # 将数据库记录转换回模型
                event_data = result.data[0]
                return self._convert_to_audit_event(event_data)
            return None
            
        except Exception as e:
            logger.error(f"创建审计事件失败: {e}")
            return None
    
    async def get_audit_event(self, event_id: str) -> Optional[AuditEvent]:
        """获取特定审计事件"""
        try:
            result = self.supabase.table(self.table_name)\
                .select("*")\
                .eq("id", event_id)\
                .single()\
                .execute()
            
            if result.data:
                return self._convert_to_audit_event(result.data)
            return None
            
        except Exception as e:
            logger.error(f"获取审计事件失败: {e}")
            return None
    
    async def query_audit_events(self, query: AuditQueryRequest) -> List[AuditEvent]:
        """查询审计事件"""
        try:
            # 构建基础查询
            supabase_query = self.supabase.table(self.table_name).select("*")
            
            # 应用过滤条件
            if query.event_types:
                event_types = [et.value for et in query.event_types]
                supabase_query = supabase_query.in_("event_type", event_types)
            
            if query.categories:
                categories = [cat.value for cat in query.categories]
                supabase_query = supabase_query.in_("category", categories)
            
            if query.severities:
                severities = [sev.value for sev in query.severities]
                supabase_query = supabase_query.in_("severity", severities)
            
            if query.user_id:
                supabase_query = supabase_query.eq("user_id", query.user_id)
            
            if query.organization_id:
                supabase_query = supabase_query.eq("organization_id", query.organization_id)
            
            if query.resource_type:
                supabase_query = supabase_query.eq("resource_type", query.resource_type)
            
            if query.start_time:
                supabase_query = supabase_query.gte("timestamp", query.start_time.isoformat())
            
            if query.end_time:
                supabase_query = supabase_query.lte("timestamp", query.end_time.isoformat())
            
            if query.success_only:
                supabase_query = supabase_query.eq("success", True)
            elif query.failure_only:
                supabase_query = supabase_query.eq("success", False)
            
            if query.ip_address:
                supabase_query = supabase_query.eq("ip_address", query.ip_address)
            
            # 排序
            if query.sort_order == "desc":
                supabase_query = supabase_query.order(query.sort_by, desc=True)
            else:
                supabase_query = supabase_query.order(query.sort_by, desc=False)
            
            # 分页
            supabase_query = supabase_query.range(query.offset, query.offset + query.limit - 1)
            
            result = supabase_query.execute()
            
            if result.data:
                return [self._convert_to_audit_event(item) for item in result.data]
            return []
            
        except Exception as e:
            logger.error(f"查询审计事件失败: {e}")
            return []
    
    async def get_user_activities(self, user_id: str, days: int = 30, limit: int = 100) -> List[UserActivity]:
        """获取用户活动记录"""
        try:
            start_time = datetime.utcnow() - timedelta(days=days)
            
            result = self.supabase.table(self.table_name)\
                .select("*")\
                .eq("user_id", user_id)\
                .gte("timestamp", start_time.isoformat())\
                .order("timestamp", desc=True)\
                .limit(limit)\
                .execute()
            
            if result.data:
                activities = []
                for item in result.data:
                    activity = UserActivity(
                        user_id=item["user_id"],
                        session_id=item.get("session_id"),
                        activity_type=EventType(item["event_type"]),
                        activity_description=item["action"],
                        ip_address=item.get("ip_address"),
                        user_agent=item.get("user_agent"),
                        timestamp=datetime.fromisoformat(item["timestamp"].replace('Z', '+00:00')),
                        success=item["success"],
                        metadata=json.loads(item["metadata"]) if item.get("metadata") else None
                    )
                    activities.append(activity)
                return activities
            return []
            
        except Exception as e:
            logger.error(f"获取用户活动失败: {e}")
            return []
    
    # ====================
    # 安全事件管理
    # ====================
    
    async def create_security_event(self, security_event: SecurityEvent) -> Optional[SecurityEvent]:
        """创建安全事件"""
        try:
            # 将安全事件存储为特殊类型的审计事件
            audit_event = AuditEvent(
                event_type=security_event.event_type,
                category=AuditCategory.SECURITY,
                severity=security_event.severity,
                action="security_alert",
                description=f"安全事件: {security_event.threat_level}",
                ip_address=security_event.source_ip,
                metadata={
                    "threat_level": security_event.threat_level,
                    "target_resource": security_event.target_resource,
                    "attack_vector": security_event.attack_vector,
                    "detection_method": security_event.detection_method,
                    "confidence_score": security_event.confidence_score,
                    "response_action": security_event.response_action,
                    "investigation_status": security_event.investigation_status,
                    "detected_at": security_event.detected_at.isoformat(),
                    "resolved_at": security_event.resolved_at.isoformat() if security_event.resolved_at else None,
                    "related_events": security_event.related_events,
                    **(security_event.metadata or {})
                },
                tags=["security", security_event.threat_level],
                timestamp=security_event.detected_at
            )
            
            created_event = await self.create_audit_event(audit_event)
            if created_event:
                # 从审计事件重构安全事件
                return self._convert_to_security_event(created_event)
            return None
            
        except Exception as e:
            logger.error(f"创建安全事件失败: {e}")
            return None
    
    async def get_security_events(self, days: int = 7, severity: Optional[EventSeverity] = None) -> List[SecurityEvent]:
        """获取安全事件列表"""
        try:
            start_time = datetime.utcnow() - timedelta(days=days)
            
            query = self.supabase.table(self.table_name)\
                .select("*")\
                .eq("category", AuditCategory.SECURITY.value)\
                .gte("timestamp", start_time.isoformat())\
                .order("timestamp", desc=True)
            
            if severity:
                query = query.eq("severity", severity.value)
            
            result = query.execute()
            
            if result.data:
                security_events = []
                for item in result.data:
                    audit_event = self._convert_to_audit_event(item)
                    security_event = self._convert_to_security_event(audit_event)
                    security_events.append(security_event)
                return security_events
            return []
            
        except Exception as e:
            logger.error(f"获取安全事件失败: {e}")
            return []
    
    # ====================
    # 统计和分析
    # ====================
    
    async def get_event_statistics(self, days: int = 30) -> Dict[str, Any]:
        """获取事件统计信息"""
        try:
            start_time = datetime.utcnow() - timedelta(days=days)
            
            # 总事件数
            total_result = self.supabase.table(self.table_name)\
                .select("count")\
                .gte("timestamp", start_time.isoformat())\
                .execute()
            
            total_events = len(total_result.data) if total_result.data else 0
            
            # 成功/失败统计
            success_result = self.supabase.table(self.table_name)\
                .select("count")\
                .eq("success", True)\
                .gte("timestamp", start_time.isoformat())\
                .execute()
            
            success_count = len(success_result.data) if success_result.data else 0
            
            # 按类型统计
            category_stats = {}
            for category in AuditCategory:
                cat_result = self.supabase.table(self.table_name)\
                    .select("count")\
                    .eq("category", category.value)\
                    .gte("timestamp", start_time.isoformat())\
                    .execute()
                category_stats[category.value] = len(cat_result.data) if cat_result.data else 0
            
            # 安全告警数
            security_result = self.supabase.table(self.table_name)\
                .select("count")\
                .eq("category", AuditCategory.SECURITY.value)\
                .gte("timestamp", start_time.isoformat())\
                .execute()
            
            security_alerts = len(security_result.data) if security_result.data else 0
            
            # 活跃用户数
            users_result = self.supabase.table(self.table_name)\
                .select("user_id")\
                .gte("timestamp", start_time.isoformat())\
                .execute()
            
            unique_users = len(set(item["user_id"] for item in users_result.data if item.get("user_id"))) if users_result.data else 0
            
            return {
                "total_events": total_events,
                "success_count": success_count,
                "failure_count": total_events - success_count,
                "success_rate": (success_count / total_events * 100) if total_events > 0 else 0,
                "category_breakdown": category_stats,
                "security_alerts": security_alerts,
                "active_users": unique_users,
                "period_days": days,
                "period_start": start_time.isoformat(),
                "period_end": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取事件统计失败: {e}")
            return {}
    
    async def get_user_activity_summary(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """获取用户活动摘要"""
        try:
            start_time = datetime.utcnow() - timedelta(days=days)
            
            result = self.supabase.table(self.table_name)\
                .select("*")\
                .eq("user_id", user_id)\
                .gte("timestamp", start_time.isoformat())\
                .execute()
            
            if not result.data:
                return {
                    "user_id": user_id,
                    "total_activities": 0,
                    "success_count": 0,
                    "failure_count": 0,
                    "last_activity": None,
                    "most_common_activities": [],
                    "risk_score": 0.0
                }
            
            activities = result.data
            total_count = len(activities)
            success_count = sum(1 for a in activities if a["success"])
            failure_count = total_count - success_count
            
            # 最近活动
            latest_activity = max(activities, key=lambda x: x["timestamp"])
            last_activity = datetime.fromisoformat(latest_activity["timestamp"].replace('Z', '+00:00'))
            
            # 最常见的活动
            activity_counts = {}
            for activity in activities:
                event_type = activity["event_type"]
                activity_counts[event_type] = activity_counts.get(event_type, 0) + 1
            
            most_common = sorted(activity_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            most_common_activities = [{"activity_type": k, "count": v} for k, v in most_common]
            
            # 风险评分 (基于失败率和安全事件)
            failure_rate = failure_count / total_count if total_count > 0 else 0
            security_events = sum(1 for a in activities if a.get("category") == "security")
            risk_score = min(100, (failure_rate * 50) + (security_events * 10))
            
            return {
                "user_id": user_id,
                "total_activities": total_count,
                "success_count": success_count,
                "failure_count": failure_count,
                "last_activity": last_activity.isoformat(),
                "most_common_activities": most_common_activities,
                "risk_score": risk_score,
                "period_days": days
            }
            
        except Exception as e:
            logger.error(f"获取用户活动摘要失败: {e}")
            return {}
    
    # ====================
    # 数据转换辅助方法
    # ====================
    
    def _convert_to_audit_event(self, data: Dict[str, Any]) -> AuditEvent:
        """将数据库记录转换为AuditEvent对象"""
        return AuditEvent(
            id=str(data.get("id")),
            event_type=EventType(data["event_type"]),
            category=AuditCategory(data["category"]),
            severity=EventSeverity(data["severity"]),
            status=EventStatus(data.get("status", "success")),
            action=data["action"],
            description=data.get("description"),
            
            user_id=data.get("user_id"),
            session_id=data.get("session_id"),
            organization_id=data.get("organization_id"),
            
            resource_type=data.get("resource_type"),
            resource_id=data.get("resource_id"),
            resource_name=data.get("resource_name"),
            
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            api_endpoint=data.get("api_endpoint"),
            http_method=data.get("http_method"),
            
            success=data.get("success", True),
            error_code=data.get("error_code"),
            error_message=data.get("error_message"),
            
            metadata=json.loads(data["metadata"]) if data.get("metadata") else None,
            tags=data.get("tags"),
            
            timestamp=datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00')),
            created_at=datetime.fromisoformat(data["created_at"].replace('Z', '+00:00')) if data.get("created_at") else None,
            
            retention_policy=data.get("retention_policy"),
            compliance_flags=data.get("compliance_flags")
        )
    
    def _convert_to_security_event(self, audit_event: AuditEvent) -> SecurityEvent:
        """将AuditEvent转换为SecurityEvent"""
        metadata = audit_event.metadata or {}
        
        return SecurityEvent(
            id=audit_event.id,
            event_type=audit_event.event_type,
            severity=audit_event.severity,
            threat_level=metadata.get("threat_level", "low"),
            
            source_ip=audit_event.ip_address,
            target_resource=metadata.get("target_resource"),
            attack_vector=metadata.get("attack_vector"),
            
            detection_method=metadata.get("detection_method"),
            confidence_score=metadata.get("confidence_score"),
            
            response_action=metadata.get("response_action"),
            investigation_status=metadata.get("investigation_status", "open"),
            
            detected_at=datetime.fromisoformat(metadata["detected_at"]) if metadata.get("detected_at") else audit_event.timestamp,
            resolved_at=datetime.fromisoformat(metadata["resolved_at"]) if metadata.get("resolved_at") else None,
            
            related_events=metadata.get("related_events"),
            metadata=metadata
        )
    
    # ====================
    # 数据维护
    # ====================
    
    async def cleanup_old_events(self, retention_days: int = 365) -> int:
        """清理过期的审计事件"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            
            result = self.supabase.table(self.table_name)\
                .delete()\
                .lt("timestamp", cutoff_date.isoformat())\
                .execute()
            
            cleaned_count = len(result.data) if result.data else 0
            logger.info(f"清理了 {cleaned_count} 条过期审计事件")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"清理过期事件失败: {e}")
            return 0