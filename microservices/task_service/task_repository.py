"""
Task Repository

任务数据访问层，提供任务相关的数据库操作
"""

import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from core.config_manager import ConfigManager
from google.protobuf.json_format import MessageToDict
from google.protobuf.struct_pb2 import ListValue, Struct

from isa_common import AsyncPostgresClient

from .models import (
    TaskAnalyticsResponse,
    TaskExecutionResponse,
    TaskPriority,
    TaskResponse,
    TaskStatus,
    TaskTemplateResponse,
    TaskType,
)

logger = logging.getLogger(__name__)


def _convert_protobuf_to_native(value: Any) -> Any:
    """Convert Protobuf types to Python native types"""
    if isinstance(value, ListValue):
        return list(value)
    elif isinstance(value, Struct):
        return MessageToDict(value)
    elif isinstance(value, (list, tuple)):
        return [_convert_protobuf_to_native(item) for item in value]
    elif isinstance(value, dict):
        return {k: _convert_protobuf_to_native(v) for k, v in value.items()}
    else:
        return value


class TaskRepository:
    """任务数据访问层"""

    def __init__(self, config: Optional[ConfigManager] = None):
        """
        Initialize task repository with service discovery.

        Args:
            config: ConfigManager instance for service discovery
        """
        # Use config_manager for service discovery
        if config is None:
            config = ConfigManager("task_service")

        # Discover PostgreSQL service
        # Priority: Environment variables → Consul → localhost fallback
        postgres_host, postgres_port = config.discover_service(
            service_name="postgres_grpc_service",
            default_host="isa-postgres-grpc",
            default_port=50061,
            env_host_key="POSTGRES_GRPC_HOST",
            env_port_key="POSTGRES_GRPC_PORT",
        )

        logger.info(f"Connecting to PostgreSQL at {postgres_host}:{postgres_port}")
        self.db = AsyncPostgresClient(
            host=postgres_host, port=postgres_port, user_id="task_service"
        )
        self.schema = "task"
        self.table_name = "user_tasks"
        self.task_table = "user_tasks"  # Alias for consistency
        self.execution_table = "task_executions"
        self.template_table = "task_templates"

    async def create_task(
        self, user_id: str, task_data: Dict[str, Any]
    ) -> Optional[TaskResponse]:
        """创建用户任务"""
        try:
            now = datetime.now(timezone.utc)
            task_id = str(uuid.uuid4())

            # Helper function to serialize datetime
            def serialize_datetime(value):
                if value is None:
                    return None
                if isinstance(value, datetime):
                    return value
                if isinstance(value, str):
                    return datetime.fromisoformat(value.replace("Z", "+00:00"))
                return value

            query = f"""
                INSERT INTO {self.schema}.{self.table_name} (
                    task_id, user_id, name, description, task_type, status, priority,
                    config, schedule, credits_per_run, tags, metadata, due_date,
                    reminder_time, next_run_time, created_at, updated_at,
                    run_count, success_count, failure_count, total_credits_consumed
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21)
            """

            params = [
                task_id,
                user_id,
                task_data.get("name"),
                task_data.get("description"),
                task_data.get("task_type"),
                task_data.get("status", TaskStatus.PENDING.value),
                task_data.get("priority", TaskPriority.MEDIUM.value),
                task_data.get("config", {}),
                task_data.get("schedule"),
                float(task_data.get("credits_per_run", 0)),
                task_data.get("tags", []),
                task_data.get("metadata", {}),
                serialize_datetime(task_data.get("due_date")),
                serialize_datetime(task_data.get("reminder_time")),
                serialize_datetime(task_data.get("next_run_time")),
                now,
                now,
                0,
                0,
                0,
                0.0,
            ]

            async with self.db:
                count = await self.db.execute(query, params=params)

            if count is not None and count > 0:
                # Query back to get the created task
                select_query = (
                    f"SELECT * FROM {self.schema}.{self.table_name} WHERE task_id = $1"
                )
                async with self.db:
                    results = await self.db.query(select_query, params=[task_id])

                if results and len(results) > 0:
                    return self._parse_task(results[0])

            return None

        except Exception as e:
            logger.error(f"Failed to create task: {e}", exc_info=True)
            return None

    async def get_task_by_id(
        self, task_id: str, user_id: str = None
    ) -> Optional[TaskResponse]:
        """根据ID获取任务"""
        try:
            conditions = ["task_id = $1", "deleted_at IS NULL"]
            params = [task_id]
            param_count = 1

            if user_id:
                param_count += 1
                conditions.append(f"user_id = ${param_count}")
                params.append(user_id)

            where_clause = " AND ".join(conditions)
            query = f"SELECT * FROM {self.schema}.{self.table_name} WHERE {where_clause} LIMIT 1"

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                return self._parse_task(results[0])

            return None

        except Exception as e:
            logger.error(f"Failed to get task {task_id}: {e}")
            return None

    async def get_user_tasks(
        self,
        user_id: str,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[TaskResponse]:
        """获取用户任务列表"""
        try:
            conditions = ["user_id = $1", "deleted_at IS NULL"]
            params = [user_id]
            param_count = 1

            if status:
                param_count += 1
                conditions.append(f"status = ${param_count}")
                params.append(status)

            if task_type:
                param_count += 1
                conditions.append(f"task_type = ${param_count}")
                params.append(task_type)

            where_clause = " AND ".join(conditions)
            query = f"""
                SELECT * FROM {self.schema}.{self.table_name}
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT {limit} OFFSET {offset}
            """

            async with self.db:
                results = await self.db.query(query, params=params)

            tasks = []
            if results:
                for data in results:
                    task = self._parse_task(data)
                    if task:
                        tasks.append(task)

            return tasks

        except Exception as e:
            logger.error(f"Failed to list user tasks: {e}")
            return []

    async def update_task(
        self, task_id: str, updates: Dict[str, Any], user_id: str = None
    ) -> bool:
        """更新任务"""
        try:
            update_parts = []
            params = []
            param_count = 0

            # Process update fields
            for field in [
                "name",
                "description",
                "status",
                "priority",
                "config",
                "schedule",
                "tags",
                "metadata",
                "due_date",
                "reminder_time",
                "next_run_time",
                "last_error",
                "last_result",
            ]:
                if field in updates:
                    param_count += 1
                    update_parts.append(f"{field} = ${param_count}")

                    value = updates[field]
                    # Handle enum values
                    if hasattr(value, "value"):
                        value = value.value

                    params.append(value)

            if not update_parts:
                return True

            # Add updated_at
            param_count += 1
            update_parts.append(f"updated_at = ${param_count}")
            params.append(datetime.now(timezone.utc))

            # Build WHERE clause
            param_count += 1
            where_conditions = [f"task_id = ${param_count}"]
            params.append(task_id)

            if user_id:
                param_count += 1
                where_conditions.append(f"user_id = ${param_count}")
                params.append(user_id)

            where_clause = " AND ".join(where_conditions)
            set_clause = ", ".join(update_parts)

            query = f"""
                UPDATE {self.schema}.{self.table_name}
                SET {set_clause}
                WHERE {where_clause}
            """

            async with self.db:
                count = await self.db.execute(query, params=params)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Failed to update task {task_id}: {e}")
            return False

    async def delete_task(self, task_id: str, user_id: str = None) -> bool:
        """软删除任务"""
        try:
            now = datetime.now(timezone.utc)
            params = [now, now]  # deleted_at and updated_at
            param_count = 2

            conditions = []
            param_count += 1
            conditions.append(f"task_id = ${param_count}")
            params.append(task_id)

            if user_id:
                param_count += 1
                conditions.append(f"user_id = ${param_count}")
                params.append(user_id)

            where_clause = " AND ".join(conditions)
            query = f"""
                UPDATE {self.schema}.{self.table_name}
                SET deleted_at = $1, updated_at = $2
                WHERE {where_clause} AND deleted_at IS NULL
            """

            async with self.db:
                count = await self.db.execute(query, params=params)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Failed to delete task {task_id}: {e}")
            return False

    async def update_task_execution_info(
        self, task_id: str, success: bool, credits_consumed: float = 0
    ) -> bool:
        """更新任务执行统计 (别名)"""
        return await self.update_task_execution_stats(
            task_id, success, credits_consumed
        )

    async def update_task_execution_stats(
        self, task_id: str, success: bool, credits_consumed: float = 0
    ) -> bool:
        """更新任务执行统计"""
        try:
            now = datetime.now(timezone.utc)

            if success:
                query = f"""
                    UPDATE {self.schema}.{self.table_name}
                    SET run_count = run_count + 1,
                        success_count = success_count + 1,
                        total_credits_consumed = total_credits_consumed + $1,
                        last_run_time = $2,
                        last_success_time = $2,
                        updated_at = $2
                    WHERE task_id = $3
                """
                params = [credits_consumed, now, task_id]
            else:
                query = f"""
                    UPDATE {self.schema}.{self.table_name}
                    SET run_count = run_count + 1,
                        failure_count = failure_count + 1,
                        total_credits_consumed = total_credits_consumed + $1,
                        last_run_time = $2,
                        updated_at = $2
                    WHERE task_id = $3
                """
                params = [credits_consumed, now, task_id]

            async with self.db:
                count = await self.db.execute(query, params=params)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Failed to update task execution stats: {e}")
            return False

    async def get_pending_tasks(self, limit: int = 100) -> List[TaskResponse]:
        """获取待执行的任务"""
        try:
            now = datetime.now(timezone.utc)
            query = f"""
                SELECT * FROM {self.schema}.{self.table_name}
                WHERE status = 'scheduled'
                AND deleted_at IS NULL
                AND (next_run_time IS NULL OR next_run_time <= $1)
                ORDER BY priority DESC, next_run_time
                LIMIT {limit}
            """

            async with self.db:
                results = await self.db.query(query, params=[now])

            tasks = []
            if results:
                for data in results:
                    task = self._parse_task(data)
                    if task:
                        tasks.append(task)

            return tasks

        except Exception as e:
            logger.error(f"Failed to get pending tasks: {e}")
            return []

    # ====================
    # Task Executions
    # ====================

    async def create_execution_record(
        self, task_id: str, user_id: str, execution_data: Dict[str, Any]
    ) -> Optional[TaskExecutionResponse]:
        """创建任务执行记录 (别名)"""
        # Merge all data into one dict for create_execution
        merged_data = {"task_id": task_id, "user_id": user_id, **execution_data}
        return await self.create_execution(merged_data)

    async def create_execution(
        self, execution_data: Dict[str, Any]
    ) -> Optional[TaskExecutionResponse]:
        """创建任务执行记录"""
        try:
            now = datetime.now(timezone.utc)
            execution_id = str(uuid.uuid4())

            query = f"""
                INSERT INTO {self.schema}.{self.execution_table} (
                    execution_id, task_id, user_id, status, trigger_type,
                    trigger_data, started_at, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """

            params = [
                execution_id,
                execution_data.get("task_id"),
                execution_data.get("user_id"),
                execution_data.get("status", "running"),
                execution_data.get("trigger_type", "manual"),
                execution_data.get("trigger_data"),
                now,
                now,
            ]

            async with self.db:
                count = await self.db.execute(query, params=params)

            if count is not None and count > 0:
                select_query = f"SELECT * FROM {self.schema}.{self.execution_table} WHERE execution_id = $1"
                async with self.db:
                    results = await self.db.query(select_query, params=[execution_id])

                if results and len(results) > 0:
                    return self._parse_execution(results[0])

            return None

        except Exception as e:
            logger.error(f"Failed to create execution: {e}")
            return None

    async def update_execution_record(
        self, execution_id: str, updates: Dict[str, Any]
    ) -> bool:
        """更新任务执行记录 (别名)"""
        return await self.update_execution(execution_id, updates)

    async def update_execution(
        self, execution_id: str, updates: Dict[str, Any]
    ) -> bool:
        """更新任务执行记录"""
        try:
            update_parts = []
            params = []
            param_count = 0

            for field in [
                "status",
                "result",
                "error_message",
                "error_details",
                "credits_consumed",
                "tokens_used",
                "api_calls_made",
                "duration_ms",
            ]:
                if field in updates:
                    param_count += 1
                    update_parts.append(f"{field} = ${param_count}")
                    params.append(updates[field])

            if updates.get("status") in ["completed", "failed", "cancelled"]:
                param_count += 1
                update_parts.append(f"completed_at = ${param_count}")
                params.append(datetime.now(timezone.utc))

            if not update_parts:
                return True

            param_count += 1
            params.append(execution_id)

            set_clause = ", ".join(update_parts)
            query = f"""
                UPDATE {self.schema}.{self.execution_table}
                SET {set_clause}
                WHERE execution_id = ${param_count}
            """

            async with self.db:
                count = await self.db.execute(query, params=params)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Failed to update execution {execution_id}: {e}")
            return False

    async def list_task_executions(
        self, task_id: str, limit: int = 50, offset: int = 0
    ) -> List[TaskExecutionResponse]:
        """获取任务执行历史"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.execution_table}
                WHERE task_id = $1
                ORDER BY started_at DESC
                LIMIT {limit} OFFSET {offset}
            """

            async with self.db:
                results = await self.db.query(query, params=[task_id])

            executions = []
            if results:
                for data in results:
                    execution = self._parse_execution(data)
                    if execution:
                        executions.append(execution)

            return executions

        except Exception as e:
            logger.error(f"Failed to list task executions: {e}")
            return []

    async def get_task_executions(
        self, task_id: str, limit: int = 50, offset: int = 0
    ) -> List[TaskExecutionResponse]:
        """获取任务执行历史 (别名)"""
        return await self.list_task_executions(task_id, limit, offset)

    # ====================
    # Task Templates
    # ====================

    async def get_task_templates(
        self,
        subscription_level: Optional[str] = None,
        category: Optional[str] = None,
        task_type: Optional[str] = None,
        is_active: bool = True,
    ) -> List[TaskTemplateResponse]:
        """获取任务模板列表"""
        try:
            conditions = []
            params = []
            param_count = 0

            if is_active is not None:
                param_count += 1
                conditions.append(f"is_active = ${param_count}")
                params.append(is_active)

            if category:
                param_count += 1
                conditions.append(f"category = ${param_count}")
                params.append(category)

            if task_type:
                param_count += 1
                conditions.append(f"task_type = ${param_count}")
                params.append(task_type)

            if subscription_level:
                # Filter templates based on subscription level hierarchy
                # Users can access templates at or below their subscription level
                subscription_hierarchy = {
                    "free": ["free"],
                    "basic": ["free", "basic"],
                    "pro": ["free", "basic", "pro"],
                    "enterprise": ["free", "basic", "pro", "enterprise"],
                }
                allowed_levels = subscription_hierarchy.get(
                    subscription_level, ["free"]
                )

                # Build IN clause for allowed levels
                level_placeholders = []
                for level in allowed_levels:
                    param_count += 1
                    level_placeholders.append(f"${param_count}")
                    params.append(level)

                if level_placeholders:
                    conditions.append(
                        f"required_subscription_level IN ({', '.join(level_placeholders)})"
                    )

            where_clause = " AND ".join(conditions) if conditions else "TRUE"
            query = f"""
                SELECT * FROM {self.schema}.{self.template_table}
                WHERE {where_clause}
                ORDER BY category, name
            """

            async with self.db:
                results = await self.db.query(query, params=params)

            templates = []
            if results:
                for data in results:
                    template = self._parse_template(data)
                    if template:
                        templates.append(template)

            return templates

        except Exception as e:
            logger.error(f"Failed to get task templates: {e}")
            return []

    async def list_templates(
        self,
        category: Optional[str] = None,
        task_type: Optional[str] = None,
        is_active: bool = True,
    ) -> List[TaskTemplateResponse]:
        """获取任务模板列表 (别名)"""
        try:
            conditions = []
            params = []
            param_count = 0

            if is_active is not None:
                param_count += 1
                conditions.append(f"is_active = ${param_count}")
                params.append(is_active)

            if category:
                param_count += 1
                conditions.append(f"category = ${param_count}")
                params.append(category)

            if task_type:
                param_count += 1
                conditions.append(f"task_type = ${param_count}")
                params.append(task_type)

            where_clause = " AND ".join(conditions) if conditions else "TRUE"
            query = f"""
                SELECT * FROM {self.schema}.{self.template_table}
                WHERE {where_clause}
                ORDER BY category, name
            """

            async with self.db:
                results = await self.db.query(query, params=params)

            templates = []
            if results:
                for data in results:
                    template = self._parse_template(data)
                    if template:
                        templates.append(template)

            return templates

        except Exception as e:
            logger.error(f"Failed to list templates: {e}")
            return []

    async def get_template(self, template_id: str) -> Optional[TaskTemplateResponse]:
        """获取任务模板"""
        try:
            query = f"SELECT * FROM {self.schema}.{self.template_table} WHERE template_id = $1 LIMIT 1"

            async with self.db:
                results = await self.db.query(query, params=[template_id])

            if results and len(results) > 0:
                return self._parse_template(results[0])

            return None

        except Exception as e:
            logger.error(f"Failed to get template {template_id}: {e}")
            return None

    # ====================
    # Task Analytics
    # ====================

    async def get_task_analytics(
        self, user_id: str, days: int = 30
    ) -> Optional[TaskAnalyticsResponse]:
        """获取任务分析数据"""
        try:
            time_threshold = datetime.now(timezone.utc) - timedelta(days=days)

            # Query 1: Task statistics
            task_stats_query = f"""
                SELECT
                    COUNT(*) as total_tasks,
                    COUNT(*) FILTER (WHERE status IN ('scheduled', 'running')) as active_tasks,
                    COUNT(*) FILTER (WHERE status = 'completed' OR is_completed = true) as completed_tasks,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed_tasks,
                    COUNT(*) FILTER (WHERE status = 'paused') as paused_tasks
                FROM {self.schema}.{self.task_table}
                WHERE user_id = $1 AND deleted_at IS NULL
            """

            # Query 2: Execution statistics
            exec_stats_query = f"""
                SELECT
                    COUNT(*) as total_executions,
                    COUNT(*) FILTER (WHERE status = 'completed') as successful_executions,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed_executions,
                    CAST(COALESCE(AVG(duration_ms) FILTER (WHERE duration_ms IS NOT NULL), 0) AS DOUBLE PRECISION) as avg_duration_ms,
                    CAST(COALESCE(SUM(credits_consumed), 0) AS DOUBLE PRECISION) as total_credits,
                    COALESCE(SUM(tokens_used), 0) as total_tokens,
                    COALESCE(SUM(api_calls_made), 0) as total_api_calls
                FROM {self.schema}.{self.execution_table}
                WHERE user_id = $1 AND created_at >= $2
            """

            # Query 3: Task type distribution
            type_dist_query = f"""
                SELECT task_type, COUNT(*) as count
                FROM {self.schema}.{self.task_table}
                WHERE user_id = $1 AND deleted_at IS NULL
                GROUP BY task_type
            """

            # Query 4: Busiest hours (based on execution start times)
            busiest_hours_query = f"""
                SELECT EXTRACT(HOUR FROM started_at) as hour, COUNT(*) as count
                FROM {self.schema}.{self.execution_table}
                WHERE user_id = $1 AND created_at >= $2
                GROUP BY hour
                ORDER BY count DESC
                LIMIT 5
            """

            # Query 5: Busiest days (based on execution start times)
            busiest_days_query = f"""
                SELECT TO_CHAR(started_at, 'Day') as day_name, COUNT(*) as count
                FROM {self.schema}.{self.execution_table}
                WHERE user_id = $1 AND created_at >= $2
                GROUP BY day_name
                ORDER BY count DESC
                LIMIT 5
            """

            async with self.db:
                # Execute all queries
                task_stats = await self.db.query(
                    task_stats_query, params=[user_id]
                )
                exec_stats = await self.db.query(
                    exec_stats_query, params=[user_id, time_threshold]
                )
                type_dist = await self.db.query(
                    type_dist_query, params=[user_id]
                )
                busiest_hours = await self.db.query(
                    busiest_hours_query, params=[user_id, time_threshold]
                )
                busiest_days = await self.db.query(
                    busiest_days_query, params=[user_id, time_threshold]
                )

            # Parse results
            if not task_stats or not exec_stats:
                return None

            task_data = task_stats[0]
            exec_data = exec_stats[0]

            # Calculate success rate
            total_execs = exec_data.get("total_executions", 0) or 0
            successful_execs = exec_data.get("successful_executions", 0) or 0
            success_rate = (
                (successful_execs / total_execs * 100) if total_execs > 0 else 0.0
            )

            # Parse task type distribution
            task_types_distribution = {}
            if type_dist:
                for row in type_dist:
                    task_types_distribution[row["task_type"]] = row["count"]

            # Parse busiest hours
            busiest_hours_list = []
            if busiest_hours:
                busiest_hours_list = [
                    int(row["hour"]) for row in busiest_hours if row.get("hour") is not None
                ]

            # Parse busiest days
            busiest_days_list = []
            if busiest_days:
                busiest_days_list = [
                    str(row["day_name"]).strip()
                    for row in busiest_days
                    if row.get("day_name")
                ]

            # Create analytics response
            analytics = TaskAnalyticsResponse(
                user_id=user_id,
                time_period=f"Last {days} days",
                total_tasks=task_data.get("total_tasks", 0) or 0,
                active_tasks=task_data.get("active_tasks", 0) or 0,
                completed_tasks=task_data.get("completed_tasks", 0) or 0,
                failed_tasks=task_data.get("failed_tasks", 0) or 0,
                paused_tasks=task_data.get("paused_tasks", 0) or 0,
                total_executions=total_execs,
                successful_executions=successful_execs,
                failed_executions=exec_data.get("failed_executions", 0) or 0,
                success_rate=round(success_rate, 2),
                average_execution_time=round(
                    float(exec_data.get("avg_duration_ms", 0) or 0) / 1000, 2
                ),  # Convert ms to seconds
                total_credits_consumed=float(exec_data.get("total_credits", 0) or 0),
                total_tokens_used=exec_data.get("total_tokens", 0) or 0,
                total_api_calls=exec_data.get("total_api_calls", 0) or 0,
                task_types_distribution=task_types_distribution,
                busiest_hours=busiest_hours_list,
                busiest_days=busiest_days_list,
            )

            return analytics

        except Exception as e:
            logger.error(f"Failed to get task analytics for {user_id}: {e}")
            return None

    # ====================
    # Helper Methods
    # ====================

    def _parse_task(self, data: Dict[str, Any]) -> Optional[TaskResponse]:
        """解析任务数据"""
        try:
            task_data = {
                "id": data.get("id"),
                "task_id": data["task_id"],
                "user_id": data["user_id"],
                "name": data["name"],
                "description": data.get("description"),
                "task_type": data["task_type"],
                "status": data["status"],
                "priority": data.get("priority", "medium"),
                "config": _convert_protobuf_to_native(data.get("config", {})),
                "schedule": _convert_protobuf_to_native(data.get("schedule")),
                "credits_per_run": data.get("credits_per_run", 0),
                "tags": _convert_protobuf_to_native(data.get("tags", [])),
                "metadata": _convert_protobuf_to_native(data.get("metadata", {})),
                "run_count": data.get("run_count", 0),
                "success_count": data.get("success_count", 0),
                "failure_count": data.get("failure_count", 0),
                "total_credits_consumed": data.get("total_credits_consumed", 0),
                "is_completed": data.get("is_completed", False),
                # Initialize optional fields
                "next_run_time": None,
                "last_run_time": None,
                "last_success_time": None,
                "last_error": None,
                "last_result": None,
                "due_date": None,
                "reminder_time": None,
                "completed_at": None,
                "deleted_at": None,
                "created_at": None,
                "updated_at": None,
            }

            # Parse datetime fields
            for field in [
                "next_run_time",
                "last_run_time",
                "last_success_time",
                "due_date",
                "reminder_time",
                "completed_at",
                "created_at",
                "updated_at",
                "deleted_at",
            ]:
                if data.get(field):
                    task_data[field] = datetime.fromisoformat(
                        str(data[field]).replace("+00:00", "")
                    )

            # Parse last_result if present
            if data.get("last_result"):
                task_data["last_result"] = _convert_protobuf_to_native(
                    data["last_result"]
                )

            if data.get("last_error"):
                task_data["last_error"] = data["last_error"]

            return TaskResponse(**task_data)

        except Exception as e:
            logger.error(f"Failed to parse task: {e}")
            return None

    def _parse_execution(self, data: Dict[str, Any]) -> Optional[TaskExecutionResponse]:
        """解析执行记录数据"""
        try:
            execution_data = {
                "id": data.get("id"),
                "execution_id": data["execution_id"],
                "task_id": data["task_id"],
                "user_id": data["user_id"],
                "status": data["status"],
                "trigger_type": data.get("trigger_type", "manual"),
                "trigger_data": _convert_protobuf_to_native(data.get("trigger_data")),
                "result": _convert_protobuf_to_native(data.get("result")),
                "error_message": data.get("error_message"),
                "error_details": _convert_protobuf_to_native(data.get("error_details")),
                "credits_consumed": data.get("credits_consumed", 0),
                "tokens_used": data.get("tokens_used"),
                "api_calls_made": data.get("api_calls_made", 0),
                "duration_ms": data.get("duration_ms"),
                # Initialize optional datetime fields
                "started_at": None,
                "completed_at": None,
                "created_at": None,
            }

            # Parse datetime fields
            for field in ["started_at", "completed_at", "created_at"]:
                if data.get(field):
                    execution_data[field] = datetime.fromisoformat(
                        str(data[field]).replace("+00:00", "")
                    )

            return TaskExecutionResponse(**execution_data)

        except Exception as e:
            logger.error(f"Failed to parse execution: {e}")
            return None

    def _parse_template(self, data: Dict[str, Any]) -> Optional[TaskTemplateResponse]:
        """解析模板数据"""
        try:
            # Convert credits_per_run to float explicitly
            credits = data.get("credits_per_run", 0)
            if credits is not None:
                credits = float(credits)

            template_data = {
                "id": data.get("id"),
                "template_id": data["template_id"],
                "name": data["name"],
                "description": data.get("description", ""),
                "category": data["category"],
                "task_type": data["task_type"],
                "default_config": _convert_protobuf_to_native(
                    data.get("default_config", {})
                ),
                "required_fields": _convert_protobuf_to_native(
                    data.get("required_fields", [])
                ),
                "optional_fields": _convert_protobuf_to_native(
                    data.get("optional_fields", [])
                ),
                "config_schema": _convert_protobuf_to_native(
                    data.get("config_schema", {})
                ),
                "required_subscription_level": data.get(
                    "required_subscription_level", "free"
                ),
                "credits_per_run": credits,
                "tags": _convert_protobuf_to_native(data.get("tags")),
                "metadata": _convert_protobuf_to_native(data.get("metadata", {})),
                "is_active": data.get("is_active", True),
                # Initialize datetime fields
                "created_at": None,
                "updated_at": None,
            }

            # Parse datetime fields
            for field in ["created_at", "updated_at"]:
                if data.get(field):
                    template_data[field] = datetime.fromisoformat(
                        str(data[field]).replace("+00:00", "")
                    )

            return TaskTemplateResponse(**template_data)

        except Exception as e:
            logger.error(f"Failed to parse template: {e}")
            return None

    # ============ Event Handler Methods ============

    async def cancel_user_tasks(self, user_id: str) -> int:
        """
        Cancel all tasks for a user (for user.deleted event)

        Args:
            user_id: User ID

        Returns:
            int: Number of tasks cancelled
        """
        try:
            query = f"""
                UPDATE {self.schema}.{self.task_table}
                SET status = $1, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = $2
                AND status IN ($3, $4)
            """

            async with self.db:
                count = await self.db.execute(
                    query,
                    params=["cancelled", user_id, "pending", "scheduled"],
                )

            logger.info(f"Cancelled {count} tasks for user {user_id}")
            return count if count else 0

        except Exception as e:
            logger.error(f"Error cancelling user tasks: {e}")
            return 0
