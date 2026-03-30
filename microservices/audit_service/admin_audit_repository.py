"""
Admin Audit Repository

Data access layer for the admin_audit_log table.
"""

import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from isa_common import AsyncPostgresClient
from core.config_manager import ConfigManager

from .admin_audit_models import AdminAuditLogEntry

logger = logging.getLogger(__name__)


class AdminAuditRepository:
    """Repository for admin_audit_log table"""

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

        self.db = AsyncPostgresClient(
            host=host,
            port=port,
            user_id="audit_service",
            min_pool_size=1,
            max_pool_size=2,
        )
        self.schema = "audit"
        self.table = "admin_audit_log"

    async def create_admin_audit_entry(self, entry: AdminAuditLogEntry) -> Optional[AdminAuditLogEntry]:
        """Insert a new admin audit log entry"""
        try:
            query = f"""
                INSERT INTO {self.schema}.{self.table} (
                    audit_id, admin_user_id, admin_email, action,
                    resource_type, resource_id, changes,
                    ip_address, user_agent, timestamp, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING *
            """

            params = [
                entry.audit_id,
                entry.admin_user_id,
                entry.admin_email,
                entry.action,
                entry.resource_type,
                entry.resource_id,
                json.dumps(entry.changes),
                entry.ip_address,
                entry.user_agent,
                entry.timestamp,
                json.dumps(entry.metadata),
            ]

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                return self._row_to_entry(results[0])
            return None

        except Exception as e:
            logger.error(f"Error creating admin audit entry: {e}", exc_info=True)
            return None

    async def query_admin_audit_log(
        self,
        admin_user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[AdminAuditLogEntry], int]:
        """
        Query admin audit log with filters.

        Returns:
            Tuple of (entries, total_count)
        """
        try:
            conditions = []
            params = []
            param_count = 0

            if admin_user_id:
                param_count += 1
                conditions.append(f"admin_user_id = ${param_count}")
                params.append(admin_user_id)

            if action:
                param_count += 1
                conditions.append(f"action = ${param_count}")
                params.append(action)

            if resource_type:
                param_count += 1
                conditions.append(f"resource_type = ${param_count}")
                params.append(resource_type)

            if resource_id:
                param_count += 1
                conditions.append(f"resource_id = ${param_count}")
                params.append(resource_id)

            if start_time:
                param_count += 1
                conditions.append(f"timestamp >= ${param_count}")
                params.append(start_time)

            if end_time:
                param_count += 1
                conditions.append(f"timestamp <= ${param_count}")
                params.append(end_time)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            # Count query
            count_query = f"SELECT COUNT(*) as total FROM {self.schema}.{self.table} {where_clause}"

            # Data query
            data_query = f"""
                SELECT * FROM {self.schema}.{self.table}
                {where_clause}
                ORDER BY timestamp DESC
                LIMIT ${param_count + 1} OFFSET ${param_count + 2}
            """

            data_params = params + [limit, offset]

            async with self.db:
                count_result = await self.db.query(count_query, params=params)
                results = await self.db.query(data_query, params=data_params)

            total = 0
            if count_result and len(count_result) > 0:
                total = count_result[0].get("total", 0)

            entries = [self._row_to_entry(row) for row in (results or [])]
            return entries, total

        except Exception as e:
            logger.error(f"Error querying admin audit log: {e}", exc_info=True)
            return [], 0

    def _row_to_entry(self, row: Dict[str, Any]) -> AdminAuditLogEntry:
        """Convert a DB row to AdminAuditLogEntry"""
        changes = row.get("changes", {})
        if isinstance(changes, str):
            changes = json.loads(changes)

        metadata = row.get("metadata", {})
        if isinstance(metadata, str):
            metadata = json.loads(metadata)

        return AdminAuditLogEntry(
            id=row.get("id"),
            audit_id=row.get("audit_id"),
            admin_user_id=row.get("admin_user_id"),
            admin_email=row.get("admin_email"),
            action=row.get("action"),
            resource_type=row.get("resource_type"),
            resource_id=row.get("resource_id"),
            changes=changes,
            ip_address=row.get("ip_address"),
            user_agent=row.get("user_agent"),
            timestamp=row.get("timestamp"),
            metadata=metadata,
        )
