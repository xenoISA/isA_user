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
from .models import (
    AuditEvent, UserActivity, SecurityEvent, ComplianceReport,
    EventType, EventSeverity, EventStatus, AuditCategory
)

logger = logging.getLogger(__name__)


class AuditRepository:
    """审计数据访问仓库 - PostgreSQL"""

    def __init__(self):
        self.db = PostgresClient(
            host=os.getenv("POSTGRES_GRPC_HOST", "isa-postgres-grpc"),
            port=int(os.getenv("POSTGRES_GRPC_PORT", "50061")),
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
                event.event_id, event.event_type.value, event.event_category.value,
                event.event_severity.value, event.event_status.value,
                event.user_id, event.organization_id, event.session_id,
                event.ip_address, event.user_agent, event.action,
                event.resource_type, event.resource_id, event.resource_name,
                event.status_code, event.error_message,
                json.dumps(event.changes_made) if event.changes_made else "{}",
                event.risk_score,
                json.dumps(event.threat_indicators) if event.threat_indicators else "[]",
                json.dumps(event.compliance_flags) if event.compliance_flags else "[]",
                json.dumps(event.metadata) if event.metadata else "{}",
                event.tags, event.event_timestamp, datetime.now(timezone.utc)
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


__all__ = ["AuditRepository"]
