"""
Audit Repository

数据访问层 - PostgreSQL + gRPC
"""

import logging
import os
import sys
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common.postgres_client import PostgresClient
from core.config_manager import ConfigManager
from .models import (
    AuditEvent, UserActivity, SecurityEvent, ComplianceReport,
    EventType, EventSeverity, EventStatus, AuditCategory
)

logger = logging.getLogger(__name__)


class AuditRepository:
    """审计数据访问仓库 - PostgreSQL"""

    def __init__(self, config: Optional[ConfigManager] = None):
        # Use config_manager for service discovery
        if config is None:
            config = ConfigManager("audit_service")

        # Discover PostgreSQL service
        # Priority: environment variables → Consul → localhost fallback
        host, port = config.discover_service(
            service_name='postgres_grpc_service',
            default_host='isa-postgres-grpc',
            default_port=50061,
            env_host_key='POSTGRES_HOST',
            env_port_key='POSTGRES_PORT'
        )

        logger.info(f"Connecting to PostgreSQL at {host}:{port}")
        self.db = PostgresClient(
            host=host,
            port=port,
            user_id="audit_service"
        )
        self.schema = "audit"
        self.audit_events_table = "audit_events"

    async def check_connection(self) -> bool:
        """检查数据库连接"""
        try:
            result = self.db.health_check(detailed=False)
            return result is not None and result.get('healthy', False)
        except Exception as e:
            logger.error(f"数据库连接检查失败: {e}")
            return False

    async def create_audit_event(self, event: AuditEvent) -> Optional[AuditEvent]:
        """创建审计事件"""
        try:
            import json
            query = f'''
                INSERT INTO {self.schema}.{self.audit_events_table} (
                    event_id, event_type, event_category, event_severity, event_status,
                    user_id, organization_id, session_id, ip_address, user_agent,
                    action, resource_type, resource_id, resource_name,
                    status_code, error_message, changes_made,
                    risk_score, threat_indicators, compliance_flags,
                    metadata, tags, event_timestamp, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                          $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24)
                RETURNING *
            '''
            
            params = [
                event.id, event.event_type.value, event.category.value,
                event.severity.value, event.status.value,
                event.user_id, event.organization_id, event.session_id,
                event.ip_address, event.user_agent, event.action,
                event.resource_type, event.resource_id, event.resource_name,
                None,  # status_code - not in model
                event.error_message,
                "{}",  # changes_made - not in model
                0.0,  # risk_score - not in model
                "[]",  # threat_indicators - not in model
                json.dumps(event.compliance_flags) if event.compliance_flags else "[]",
                json.dumps(event.metadata) if event.metadata else "{}",
                event.tags, event.timestamp, datetime.now(timezone.utc)
            ]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            if results and len(results) > 0:
                return AuditEvent(**results[0])
            return None

        except Exception as e:
            logger.error(f"Error creating audit event: {e}", exc_info=True)
            return None

    async def get_audit_events(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditEvent]:
        """获取审计事件列表"""
        try:
            conditions = []
            params = []
            param_count = 0

            if user_id:
                param_count += 1
                conditions.append(f"user_id = ${param_count}")
                params.append(user_id)

            if organization_id:
                param_count += 1
                conditions.append(f"organization_id = ${param_count}")
                params.append(organization_id)

            if event_type:
                param_count += 1
                conditions.append(f"event_type = ${param_count}")
                params.append(event_type.value)

            if start_time:
                param_count += 1
                conditions.append(f"event_timestamp >= ${param_count}")
                params.append(start_time)

            if end_time:
                param_count += 1
                conditions.append(f"event_timestamp <= ${param_count}")
                params.append(end_time)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = f'''
                SELECT * FROM {self.schema}.{self.audit_events_table}
                {where_clause}
                ORDER BY event_timestamp DESC
                LIMIT ${param_count + 1} OFFSET ${param_count + 2}
            '''

            params.extend([limit, offset])

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return [AuditEvent(**event) for event in results] if results else []

        except Exception as e:
            logger.error(f"Error getting audit events: {e}")
            return []

    async def get_security_events(
        self,
        severity: Optional[EventSeverity] = None,
        limit: int = 100
    ) -> List[SecurityEvent]:
        """获取安全事件"""
        # Convert AuditEvent to SecurityEvent
        events = await self.get_audit_events(
            event_type=EventType.SECURITY_EVENT,
            limit=limit
        )
        return [SecurityEvent(**event.dict()) for event in events]

    async def get_statistics(
        self,
        organization_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """获取审计统计"""
        try:
            conditions = []
            params = []
            param_count = 0

            if organization_id:
                param_count += 1
                conditions.append(f"organization_id = ${param_count}")
                params.append(organization_id)

            if start_time:
                param_count += 1
                conditions.append(f"event_timestamp >= ${param_count}")
                params.append(start_time)

            if end_time:
                param_count += 1
                conditions.append(f"event_timestamp <= ${param_count}")
                params.append(end_time)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = f'''
                SELECT
                    COUNT(*) as total_events,
                    COUNT(CASE WHEN event_severity = 'critical' THEN 1 END) as critical_events,
                    COUNT(CASE WHEN event_severity = 'error' THEN 1 END) as error_events,
                    COUNT(CASE WHEN event_status = 'failed' THEN 1 END) as failed_events
                FROM {self.schema}.{self.audit_events_table}
                {where_clause}
            '''

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            if results and len(results) > 0:
                return results[0]

            return {"total_events": 0, "critical_events": 0, "error_events": 0, "failed_events": 0}

        except Exception as e:
            logger.error(f"Error getting audit statistics: {e}")
            return {"total_events": 0, "critical_events": 0, "error_events": 0, "failed_events": 0}


    async def query_audit_events(self, query: Dict[str, Any]) -> List[AuditEvent]:
        """查询审计事件 (别名方法)"""
        return await self.get_audit_events(
            user_id=query.get('user_id'),
            organization_id=query.get('organization_id'),
            event_type=query.get('event_type'),
            start_time=query.get('start_time'),
            end_time=query.get('end_time'),
            limit=query.get('limit', 100),
            offset=query.get('offset', 0)
        )

    async def get_user_activities(
        self,
        user_id: str,
        days: int = 30,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取用户活动"""
        try:
            from datetime import timedelta
            start_time = datetime.now(timezone.utc) - timedelta(days=days)

            query = f'''
                SELECT * FROM {self.schema}.{self.audit_events_table}
                WHERE user_id = $1 AND event_timestamp >= $2
                ORDER BY event_timestamp DESC
                LIMIT $3
            '''

            with self.db:
                results = self.db.query(query, [user_id, start_time, limit], schema=self.schema)

            return results if results else []

        except Exception as e:
            logger.error(f"Error getting user activities: {e}")
            return []

    async def get_user_activity_summary(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """获取用户活动摘要"""
        try:
            from datetime import timedelta
            start_time = datetime.now(timezone.utc) - timedelta(days=days)

            query = f'''
                SELECT
                    COUNT(*) as total_activities,
                    COUNT(CASE WHEN event_status = 'success' THEN 1 END) as success_count,
                    COUNT(CASE WHEN event_status = 'failure' THEN 1 END) as failure_count,
                    MAX(event_timestamp) as last_activity
                FROM {self.schema}.{self.audit_events_table}
                WHERE user_id = $1 AND event_timestamp >= $2
            '''

            with self.db:
                results = self.db.query(query, [user_id, start_time], schema=self.schema)

            if results and len(results) > 0:
                return results[0]
            return {}

        except Exception as e:
            logger.error(f"Error getting user activity summary: {e}")
            return {}

    async def create_security_event(self, security_event: 'SecurityEvent') -> Optional['SecurityEvent']:
        """创建安全事件 (转换为审计事件)"""
        try:
            # 转换为AuditEvent
            audit_event = AuditEvent(
                event_type=EventType.SECURITY_ALERT,
                category=AuditCategory.SECURITY,
                severity=EventSeverity.HIGH,
                action="security_alert",
                description=getattr(security_event, 'description', None),
                metadata=getattr(security_event, 'metadata', None),
                tags=getattr(security_event, 'tags', None)
            )

            created = await self.create_audit_event(audit_event)
            return security_event if created else None

        except Exception as e:
            logger.error(f"Error creating security event: {e}")
            return None

    async def get_security_events(
        self,
        days: int = 7,
        severity: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取安全事件"""
        try:
            from datetime import timedelta
            start_time = datetime.now(timezone.utc) - timedelta(days=days)

            conditions = ["event_type = $1", "event_timestamp >= $2"]
            params = [EventType.SECURITY_ALERT.value, start_time]
            param_count = 2

            if severity:
                param_count += 1
                conditions.append(f"event_severity = ${param_count}")
                params.append(severity)

            where_clause = " AND ".join(conditions)

            query = f'''
                SELECT * FROM {self.schema}.{self.audit_events_table}
                WHERE {where_clause}
                ORDER BY event_timestamp DESC
                LIMIT 100
            '''

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return results if results else []

        except Exception as e:
            logger.error(f"Error getting security events: {e}")
            return []

    async def get_event_statistics(self, days: int = 30) -> Dict[str, Any]:
        """获取事件统计 (别名方法)"""
        from datetime import timedelta
        start_time = datetime.now(timezone.utc) - timedelta(days=days)
        return await self.get_audit_statistics(
            organization_id=None,
            start_time=start_time,
            end_time=None
        )

    async def cleanup_old_events(self, retention_days: int = 365) -> int:
        """清理旧事件"""
        try:
            from datetime import timedelta
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)

            query = f'''
                DELETE FROM {self.schema}.{self.audit_events_table}
                WHERE event_timestamp < $1
            '''

            with self.db:
                count = self.db.execute(query, [cutoff_date], schema=self.schema)

            return count if count else 0

        except Exception as e:
            logger.error(f"Error cleaning up old events: {e}")
            return 0


__all__ = ["AuditRepository"]
