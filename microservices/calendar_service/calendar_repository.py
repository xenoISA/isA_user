"""
Calendar Repository

日历事件数据访问层 - PostgreSQL + gRPC
"""

import logging
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from core.config_manager import ConfigManager

from isa_common.postgres_client import PostgresClient

from .models import CalendarEvent, EventCategory, EventResponse, RecurrenceType

logger = logging.getLogger(__name__)


class CalendarRepository:
    """日历事件数据访问层 - PostgreSQL"""

    def __init__(self, config: Optional[ConfigManager] = None):
        # 使用 config_manager 进行服务发现
        if config is None:
            config = ConfigManager("calendar_service")

        # 发现 PostgreSQL 服务
        # 优先级：环境变量 → Consul → localhost fallback
        host, port = config.discover_service(
            service_name="postgres_grpc_service",
            default_host="isa-postgres-grpc",
            default_port=50061,
            env_host_key="POSTGRES_GRPC_HOST",
            env_port_key="POSTGRES_GRPC_PORT",
        )

        logger.info(f"Connecting to PostgreSQL at {host}:{port}")
        self.db = PostgresClient(host=host, port=port, user_id="calendar_service")

        self.schema = "calendar"
        self.table_name = "calendar_events"
        self.sync_table = "calendar_sync_status"

    async def create_event(self, event_data: Dict[str, Any]) -> Optional[EventResponse]:
        """创建日历事件"""
        try:
            event_id = f"evt_{uuid.uuid4().hex[:16]}"
            now = datetime.now(timezone.utc)

            # Handle datetime serialization
            start_time = event_data["start_time"]
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00"))

            end_time = event_data["end_time"]
            if isinstance(end_time, str):
                end_time = datetime.fromisoformat(end_time.replace("Z", "+00:00"))

            recurrence_end_date = event_data.get("recurrence_end_date")
            if recurrence_end_date and isinstance(recurrence_end_date, str):
                recurrence_end_date = datetime.fromisoformat(
                    recurrence_end_date.replace("Z", "+00:00")
                )

            query = f"""
                INSERT INTO {self.schema}.{self.table_name} (
                    event_id, user_id, organization_id, title, description, location,
                    start_time, end_time, all_day, timezone, category, color,
                    recurrence_type, recurrence_end_date, recurrence_rule, reminders,
                    sync_provider, external_event_id, is_shared, shared_with, metadata,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23)
                RETURNING *
            """

            params = [
                event_id,
                event_data["user_id"],
                event_data.get("organization_id"),
                event_data["title"],
                event_data.get("description"),
                event_data.get("location"),
                start_time,
                end_time,
                event_data.get("all_day", False),
                event_data.get("timezone", "UTC"),
                event_data.get("category", EventCategory.OTHER.value),
                event_data.get("color"),
                event_data.get("recurrence_type", RecurrenceType.NONE.value),
                recurrence_end_date,
                event_data.get("recurrence_rule"),
                event_data.get("reminders", []),
                event_data.get("sync_provider", "local"),
                event_data.get("external_event_id"),
                event_data.get("is_shared", False),
                event_data.get("shared_with", []),
                event_data.get("metadata", {}),
                now,
                now,
            ]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            if results and len(results) > 0:
                return EventResponse(**results[0])
            return None

        except Exception as e:
            logger.error(f"Failed to create event: {e}", exc_info=True)
            return None

    async def get_event_by_id(
        self, event_id: str, user_id: str = None
    ) -> Optional[EventResponse]:
        """获取事件详情"""
        try:
            conditions = ["event_id = $1"]
            params = [event_id]
            param_count = 1

            if user_id:
                param_count += 1
                conditions.append(f"user_id = ${param_count}")
                params.append(user_id)

            where_clause = " AND ".join(conditions)
            query = (
                f"SELECT * FROM {self.schema}.{self.table_name} WHERE {where_clause}"
            )

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            if results and len(results) > 0:
                return EventResponse(**results[0])
            return None

        except Exception as e:
            logger.error(f"Failed to get event {event_id}: {e}")
            return None

    async def get_events_by_user(
        self,
        user_id: str,
        start_date: datetime = None,
        end_date: datetime = None,
        category: str = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[EventResponse]:
        """查询用户事件"""
        try:
            conditions = ["user_id = $1"]
            params = [user_id]
            param_count = 1

            if start_date:
                param_count += 1
                conditions.append(f"start_time >= ${param_count}")
                params.append(start_date)

            if end_date:
                param_count += 1
                conditions.append(f"end_time <= ${param_count}")
                params.append(end_date)

            if category:
                param_count += 1
                conditions.append(f"category = ${param_count}")
                params.append(category)

            where_clause = " AND ".join(conditions)

            query = f"""
                SELECT * FROM {self.schema}.{self.table_name}
                WHERE {where_clause}
                ORDER BY start_time ASC
                LIMIT ${param_count + 1} OFFSET ${param_count + 2}
            """

            params.extend([limit, offset])

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            if results:
                return [EventResponse(**event) for event in results]
            return []

        except Exception as e:
            logger.error(f"Failed to get events for user {user_id}: {e}")
            return []

    async def get_upcoming_events(
        self, user_id: str, days: int = 7
    ) -> List[EventResponse]:
        """获取即将到来的事件"""
        try:
            now = datetime.now(timezone.utc)
            end_date = now + timedelta(days=days)

            return await self.get_events_by_user(
                user_id, start_date=now, end_date=end_date
            )

        except Exception as e:
            logger.error(f"Failed to get upcoming events: {e}")
            return []

    async def get_today_events(self, user_id: str) -> List[EventResponse]:
        """获取今天的事件"""
        try:
            now = datetime.now(timezone.utc)
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)

            return await self.get_events_by_user(
                user_id, start_date=start_of_day, end_date=end_of_day
            )

        except Exception as e:
            logger.error(f"Failed to get today's events: {e}")
            return []

    async def update_event(
        self, event_id: str, updates: Dict[str, Any]
    ) -> Optional[EventResponse]:
        """更新事件"""
        try:
            # Build SET clause dynamically
            set_clauses = []
            params = []
            param_count = 0

            # Handle datetime serialization
            for key in ["start_time", "end_time", "recurrence_end_date"]:
                if key in updates and isinstance(updates[key], str):
                    updates[key] = datetime.fromisoformat(
                        updates[key].replace("Z", "+00:00")
                    )

            for key, value in updates.items():
                if key == "updated_at":
                    continue
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")
                params.append(value)

            # Add updated_at
            param_count += 1
            set_clauses.append(f"updated_at = ${param_count}")
            params.append(datetime.now(timezone.utc))

            # Add event_id for WHERE clause
            param_count += 1
            params.append(event_id)

            query = f"""
                UPDATE {self.schema}.{self.table_name}
                SET {", ".join(set_clauses)}
                WHERE event_id = ${param_count}
                RETURNING *
            """

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            if results and len(results) > 0:
                return EventResponse(**results[0])
            return None

        except Exception as e:
            logger.error(f"Failed to update event {event_id}: {e}")
            return None

    async def delete_event(self, event_id: str, user_id: str = None) -> bool:
        """删除事件"""
        try:
            conditions = ["event_id = $1"]
            params = [event_id]
            param_count = 1

            if user_id:
                param_count += 1
                conditions.append(f"user_id = ${param_count}")
                params.append(user_id)

            where_clause = " AND ".join(conditions)
            query = f"DELETE FROM {self.schema}.{self.table_name} WHERE {where_clause}"

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Failed to delete event {event_id}: {e}")
            return False

    async def update_sync_status(
        self,
        user_id: str,
        provider: str,
        status: str,
        synced_count: int = 0,
        error_message: str = None,
    ) -> bool:
        """更新同步状态"""
        try:
            now = datetime.now(timezone.utc)

            query = f"""
                INSERT INTO {self.schema}.{self.sync_table} (
                    user_id, provider, last_sync_time, synced_events_count,
                    status, error_message, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (user_id, provider) DO UPDATE
                SET last_sync_time = EXCLUDED.last_sync_time,
                    synced_events_count = EXCLUDED.synced_events_count,
                    status = EXCLUDED.status,
                    error_message = EXCLUDED.error_message,
                    updated_at = EXCLUDED.updated_at
            """

            params = [
                user_id,
                provider,
                now,
                synced_count,
                status,
                error_message,
                now,
                now,
            ]

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count is not None and count >= 0

        except Exception as e:
            logger.error(f"Failed to update sync status: {e}")
            return False

    async def get_sync_status(
        self, user_id: str, provider: str = None
    ) -> Optional[Dict[str, Any]]:
        """获取同步状态"""
        try:
            conditions = ["user_id = $1"]
            params = [user_id]
            param_count = 1

            if provider:
                param_count += 1
                conditions.append(f"provider = ${param_count}")
                params.append(provider)

            where_clause = " AND ".join(conditions)
            query = (
                f"SELECT * FROM {self.schema}.{self.sync_table} WHERE {where_clause}"
            )

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            if results:
                return results[0] if provider else results
            return None

        except Exception as e:
            logger.error(f"Failed to get sync status: {e}")
            return None

    # ====================
    # GDPR 数据管理
    # ====================

    async def delete_user_data(self, user_id: str) -> int:
        """删除用户所有日历数据（GDPR Article 17: Right to Erasure）"""
        try:
            # Delete calendar events
            events_query = (
                f"DELETE FROM {self.schema}.{self.table_name} WHERE user_id = $1"
            )

            with self.db:
                events_count = self.db.execute(
                    events_query, [user_id], schema=self.schema
                )

            # Delete sync status
            sync_query = (
                f"DELETE FROM {self.schema}.{self.sync_table} WHERE user_id = $1"
            )

            with self.db:
                sync_count = self.db.execute(sync_query, [user_id], schema=self.schema)

            total_deleted = (events_count if events_count is not None else 0) + (
                sync_count if sync_count is not None else 0
            )

            logger.info(
                f"Deleted user {user_id} calendar data: "
                f"{events_count} events, {sync_count} sync records"
            )
            return total_deleted

        except Exception as e:
            logger.error(f"Error deleting user data for {user_id}: {e}")
            raise


__all__ = ["CalendarRepository"]
