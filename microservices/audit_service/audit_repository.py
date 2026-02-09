"""
Audit Repository - Async Version

Data access layer for audit service using AsyncPostgresClient.
"""

import logging
import os
import sys
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common import AsyncPostgresClient
from core.config_manager import ConfigManager
from .models import (
    AuditEvent, UserActivity, SecurityEvent, ComplianceReport, EventSeverity, EventStatus, AuditCategory, EventType
)

logger = logging.getLogger(__name__)


class AuditRepository:
    """Audit data repository - AsyncPostgresClient"""

    def __init__(self, config: Optional[ConfigManager] = None):
        if config is None:
            config = ConfigManager("audit_service")

        host, port = config.discover_service(
            service_name='postgres_service',
            default_host='localhost',
            default_port=5432,
            env_host_key='POSTGRES_HOST',
            env_port_key='POSTGRES_PORT'
        )

        logger.info(f"Connecting to PostgreSQL at {host}:{port}")
        self.db = AsyncPostgresClient(
            host=host,
            port=port,
            user_id="audit_service"
        )
        self.schema = "audit"
        self.audit_events_table = "audit_events"

    async def check_connection(self) -> bool:
        """Check database connection"""
        try:
            async with self.db:
                result = await self.db.query_row("SELECT 1 as connected", params=[])
            return result is not None
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False

    def _parse_json_field(self, value, expected_type='dict'):
        """Parse JSON field from database - handles both string and protobuf types"""
        if value is None:
            return [] if expected_type == 'list' else None

        if isinstance(value, dict):
            if expected_type == 'list' and (not value or value == {}):
                return []
            return value if expected_type == 'dict' else None
        if isinstance(value, list):
            return value if expected_type == 'list' else None

        if isinstance(value, str):
            import json
            try:
                parsed = json.loads(value)
                if expected_type == 'list' and not isinstance(parsed, list):
                    return [] if not parsed else None
                if expected_type == 'dict' and not isinstance(parsed, dict):
                    return None
                return parsed
            except:
                return [] if expected_type == 'list' else None

        try:
            if hasattr(value, 'items'):
                result = dict(value.items())
                if expected_type == 'list' and (not result or result == {}):
                    return []
                return result if expected_type == 'dict' else None
            elif hasattr(value, '__iter__'):
                return list(value) if expected_type == 'list' else None
        except:
            pass

        return [] if expected_type == 'list' else None

    async def create_audit_event(self, event: AuditEvent) -> Optional[AuditEvent]:
        """Create audit event"""
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
                None,  # status_code
                event.error_message,
                "{}",  # changes_made
                0.0,  # risk_score
                "[]",  # threat_indicators
                json.dumps(event.compliance_flags) if event.compliance_flags else "[]",
                json.dumps(event.metadata) if event.metadata else "{}",
                event.tags, event.timestamp, datetime.now(timezone.utc)
            ]

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                row = results[0]
                return AuditEvent(
                    id=row.get('event_id'),
                    event_type=EventType(row.get('event_type')),
                    category=AuditCategory(row.get('event_category')),
                    severity=EventSeverity(row.get('event_severity')),
                    status=EventStatus(row.get('event_status')),
                    action=row.get('action'),
                    description=row.get('description'),
                    user_id=row.get('user_id'),
                    session_id=row.get('session_id'),
                    organization_id=row.get('organization_id'),
                    resource_type=row.get('resource_type'),
                    resource_id=row.get('resource_id'),
                    resource_name=row.get('resource_name'),
                    ip_address=row.get('ip_address'),
                    user_agent=row.get('user_agent'),
                    api_endpoint=row.get('api_endpoint'),
                    http_method=row.get('http_method'),
                    success=row.get('success', True),
                    error_code=row.get('error_code'),
                    error_message=row.get('error_message'),
                    metadata=self._parse_json_field(row.get('metadata'), expected_type='dict'),
                    tags=row.get('tags'),
                    timestamp=row.get('event_timestamp'),
                    retention_policy=row.get('retention_policy'),
                    compliance_flags=self._parse_json_field(row.get('compliance_flags'), expected_type='list')
                )
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
        """Get audit events list"""
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

            async with self.db:
                results = await self.db.query(query, params=params)

            return [AuditEvent(**event) for event in results] if results else []

        except Exception as e:
            logger.error(f"Error getting audit events: {e}")
            return []

    async def get_security_events_by_severity(
        self,
        severity: Optional[EventSeverity] = None,
        limit: int = 100
    ) -> List[SecurityEvent]:
        """Get security events by severity"""
        events = await self.get_audit_events(
            event_type="audit.security.event",
            limit=limit
        )
        return [SecurityEvent(**event.dict()) for event in events]

    async def get_statistics(
        self,
        organization_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get audit statistics"""
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

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                return results[0]

            return {"total_events": 0, "critical_events": 0, "error_events": 0, "failed_events": 0}

        except Exception as e:
            logger.error(f"Error getting audit statistics: {e}")
            return {"total_events": 0, "critical_events": 0, "error_events": 0, "failed_events": 0}

    async def query_audit_events(self, query: Dict[str, Any]) -> List[AuditEvent]:
        """Query audit events (alias method)"""
        if hasattr(query, 'model_dump'):
            query_dict = query.model_dump()
        elif hasattr(query, 'dict'):
            query_dict = query.dict()
        else:
            query_dict = query

        return await self.get_audit_events(
            user_id=query_dict.get('user_id'),
            organization_id=query_dict.get('organization_id'),
            event_type=query_dict.get('event_type'),
            start_time=query_dict.get('start_time'),
            end_time=query_dict.get('end_time'),
            limit=query_dict.get('limit', 100),
            offset=query_dict.get('offset', 0)
        )

    async def get_user_activities(
        self,
        user_id: str,
        days: int = 30,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get user activities"""
        try:
            from datetime import timedelta
            start_time = datetime.now(timezone.utc) - timedelta(days=days)

            query = f'''
                SELECT * FROM {self.schema}.{self.audit_events_table}
                WHERE user_id = $1 AND event_timestamp >= $2
                ORDER BY event_timestamp DESC
                LIMIT $3
            '''

            async with self.db:
                results = await self.db.query(query, params=[user_id, start_time, limit])

            if results:
                return [dict(row) if hasattr(row, 'keys') else row for row in results]
            return []

        except Exception as e:
            logger.error(f"Error getting user activities: {e}")
            return []

    async def get_user_activity_summary(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get user activity summary"""
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

            async with self.db:
                results = await self.db.query(query, params=[user_id, start_time])

            if results and len(results) > 0:
                return results[0]
            return {}

        except Exception as e:
            logger.error(f"Error getting user activity summary: {e}")
            return {}

    async def create_security_event(self, security_event: 'SecurityEvent') -> Optional['SecurityEvent']:
        """Create security event (converted to audit event)"""
        try:
            import uuid
            audit_event = AuditEvent(
                id=str(uuid.uuid4()),
                event_type="audit.security.alert",
                category=AuditCategory.SECURITY,
                severity=EventSeverity.HIGH,
                action="security_alert",
                description=getattr(security_event, 'description', None),
                metadata=getattr(security_event, 'metadata', None),
                tags=getattr(security_event, 'tags', None),
                timestamp=datetime.now(timezone.utc)
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
        """Get security events"""
        try:
            from datetime import timedelta
            start_time = datetime.now(timezone.utc) - timedelta(days=days)

            conditions = ["event_type = $1", "event_timestamp >= $2"]
            params = ["audit.security.alert".value, start_time]
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

            async with self.db:
                results = await self.db.query(query, params=params)

            return results if results else []

        except Exception as e:
            logger.error(f"Error getting security events: {e}")
            return []

    async def get_event_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get event statistics (alias method)"""
        from datetime import timedelta
        start_time = datetime.now(timezone.utc) - timedelta(days=days)
        return await self.get_statistics(
            organization_id=None,
            start_time=start_time,
            end_time=None
        )

    async def cleanup_old_events(self, retention_days: int = 365) -> int:
        """Cleanup old events"""
        try:
            from datetime import timedelta
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)

            query = f'''
                DELETE FROM {self.schema}.{self.audit_events_table}
                WHERE event_timestamp < $1
            '''

            async with self.db:
                count = await self.db.execute(query, params=[cutoff_date])

            return count if count else 0

        except Exception as e:
            logger.error(f"Error cleaning up old events: {e}")
            return 0


__all__ = ["AuditRepository"]
