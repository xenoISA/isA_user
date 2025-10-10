"""
Task Repository

任务数据访问层，提供任务相关的数据库操作
"""

import uuid
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

# Database client setup
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.database.supabase_client import get_supabase_client
from .models import (
    TaskStatus, TaskType, TaskPriority,
    TaskResponse, TaskExecutionResponse, TaskTemplateResponse, TaskAnalyticsResponse
)

logger = logging.getLogger(__name__)


class TaskRepository:
    """任务数据访问层"""
    
    def __init__(self):
        self.db = get_supabase_client()
        self.table_name = 'user_tasks'
        self.execution_table = 'task_executions'
        self.template_table = 'task_templates'
    
    async def create_task(self, user_id: str, task_data: Dict[str, Any]) -> Optional[TaskResponse]:
        """创建用户任务"""
        try:
            # Use UUID for task_id to match database type
            task_id = str(uuid.uuid4())

            task_record = {
                "task_id": task_id,
                "user_id": user_id,
                "name": task_data.get("name"),
                "description": task_data.get("description"),
                "task_type": task_data.get("task_type"),
                "status": TaskStatus.PENDING.value,
                "priority": task_data.get("priority", TaskPriority.MEDIUM.value),
                "config": task_data.get("config", {}),
                "schedule": task_data.get("schedule"),
                "credits_per_run": float(task_data.get("credits_per_run", 0)),
                "tags": task_data.get("tags", []),
                "metadata": task_data.get("metadata", {}),
                "due_date": task_data.get("due_date"),
                "reminder_time": task_data.get("reminder_time"),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "run_count": 0,
                "success_count": 0,
                "failure_count": 0,
                "total_credits_consumed": 0.0
            }
            
            result = self.db.table(self.table_name).insert(task_record).execute()
            
            if result.data:
                return TaskResponse(**result.data[0])
            return None
            
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            return None
    
    async def get_task_by_id(self, task_id: str, user_id: str = None) -> Optional[TaskResponse]:
        """根据ID获取任务"""
        try:
            query = self.db.table(self.table_name).select("*").eq("task_id", task_id)
            
            if user_id:
                query = query.eq("user_id", user_id)
                
            result = query.execute()
            
            if result.data:
                return TaskResponse(**result.data[0])
            return None
            
        except Exception as e:
            logger.error(f"Failed to get task {task_id}: {e}")
            return None
    
    async def update_task(self, task_id: str, user_id: str, updates: Dict[str, Any]) -> Optional[TaskResponse]:
        """更新任务"""
        try:
            # 处理特殊字段
            if "credits_per_run" in updates and updates["credits_per_run"] is not None:
                updates["credits_per_run"] = float(updates["credits_per_run"])
            
            updates["updated_at"] = datetime.utcnow().isoformat()
            
            result = self.db.table(self.table_name)\
                .update(updates)\
                .eq("task_id", task_id)\
                .eq("user_id", user_id)\
                .execute()
            
            if result.data:
                return TaskResponse(**result.data[0])
            return None
            
        except Exception as e:
            logger.error(f"Failed to update task {task_id}: {e}")
            return None
    
    async def delete_task(self, task_id: str, user_id: str) -> bool:
        """删除任务（软删除）"""
        try:
            result = self.db.table(self.table_name)\
                .update({
                    "deleted_at": datetime.utcnow().isoformat(),
                    "status": TaskStatus.CANCELLED.value,
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("task_id", task_id)\
                .eq("user_id", user_id)\
                .is_("deleted_at", None)\
                .execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Failed to delete task {task_id}: {e}")
            return False
    
    async def get_user_tasks(
        self, 
        user_id: str, 
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[TaskResponse]:
        """获取用户任务列表"""
        try:
            query = self.db.table(self.table_name)\
                .select("*")\
                .eq("user_id", user_id)\
                .is_("deleted_at", None)
            
            if status:
                query = query.eq("status", status)
            
            if task_type:
                query = query.eq("task_type", task_type)
            
            result = query.order("created_at", desc=True)\
                .limit(limit)\
                .offset(offset)\
                .execute()
            
            if result.data:
                return [TaskResponse(**task) for task in result.data]
            return []
            
        except Exception as e:
            logger.error(f"Failed to get user tasks: {e}")
            return []
    
    async def get_pending_tasks(self, limit: int = 50) -> List[TaskResponse]:
        """获取待执行的任务"""
        try:
            now = datetime.utcnow().isoformat()
            
            result = self.db.table(self.table_name)\
                .select("*")\
                .eq("status", TaskStatus.SCHEDULED.value)\
                .lte("next_run_time", now)\
                .is_("deleted_at", None)\
                .order("priority", desc=True)\
                .order("next_run_time")\
                .limit(limit)\
                .execute()
            
            if result.data:
                return [TaskResponse(**task) for task in result.data]
            return []
            
        except Exception as e:
            logger.error(f"Failed to get pending tasks: {e}")
            return []
    
    async def update_task_execution_info(
        self, 
        task_id: str, 
        execution_result: Dict[str, Any]
    ) -> bool:
        """更新任务执行信息"""
        try:
            success = execution_result.get('success', False)
            credits_consumed = execution_result.get('credits_consumed', 0.0)
            
            # 获取当前任务信息以更新统计
            task_result = self.db.table(self.table_name)\
                .select("run_count, success_count, failure_count, total_credits_consumed")\
                .eq("task_id", task_id)\
                .execute()
            
            if not task_result.data:
                return False
            
            current = task_result.data[0]
            
            # 构建更新数据
            update_data = {
                "last_run_time": datetime.utcnow().isoformat(),
                "run_count": current["run_count"] + 1,
                "total_credits_consumed": current["total_credits_consumed"] + credits_consumed,
                "last_result": execution_result.get('result'),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if success:
                update_data["success_count"] = current["success_count"] + 1
                update_data["last_success_time"] = datetime.utcnow().isoformat()
                update_data["last_error"] = None
            else:
                update_data["failure_count"] = current["failure_count"] + 1
                update_data["last_error"] = execution_result.get('error', 'Unknown error')
            
            # 如果有下次执行时间，更新它
            if execution_result.get('next_run_time'):
                update_data["next_run_time"] = execution_result['next_run_time']
            
            result = self.db.table(self.table_name)\
                .update(update_data)\
                .eq("task_id", task_id)\
                .execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Failed to update task execution info: {e}")
            return False
    
    # 任务执行记录相关方法
    async def create_execution_record(
        self, 
        task_id: str, 
        user_id: str,
        execution_data: Dict[str, Any]
    ) -> Optional[TaskExecutionResponse]:
        """创建任务执行记录"""
        try:
            execution_id = f"exec_{uuid.uuid4().hex[:12]}"
            
            record = {
                "execution_id": execution_id,
                "task_id": task_id,
                "user_id": user_id,
                "status": TaskStatus.RUNNING.value,
                "started_at": datetime.utcnow().isoformat(),
                "trigger_type": execution_data.get("trigger_type", "manual"),
                "trigger_data": execution_data.get("trigger_data", {}),
                "created_at": datetime.utcnow().isoformat(),
                "api_calls_made": 0,
                "credits_consumed": 0.0
            }
            
            result = self.db.table(self.execution_table).insert(record).execute()
            
            if result.data:
                return TaskExecutionResponse(**result.data[0])
            return None
            
        except Exception as e:
            logger.error(f"Failed to create execution record: {e}")
            return None
    
    async def update_execution_record(
        self, 
        execution_id: str, 
        execution_result: Dict[str, Any]
    ) -> bool:
        """更新执行记录"""
        try:
            update_data = {
                "status": TaskStatus.COMPLETED.value if execution_result.get('success') else TaskStatus.FAILED.value,
                "completed_at": datetime.utcnow().isoformat(),
                "result": execution_result.get('result'),
                "credits_consumed": float(execution_result.get('credits_consumed', 0)),
                "tokens_used": execution_result.get('tokens_used'),
                "api_calls_made": execution_result.get('api_calls_made', 0)
            }
            
            if not execution_result.get('success'):
                update_data.update({
                    "error_message": execution_result.get('error', 'Unknown error'),
                    "error_details": execution_result.get('error_details')
                })
            
            # 计算执行时长
            if execution_result.get('started_at'):
                started = datetime.fromisoformat(execution_result['started_at'])
                duration = (datetime.utcnow() - started).total_seconds() * 1000
                update_data["duration_ms"] = int(duration)
            
            result = self.db.table(self.execution_table)\
                .update(update_data)\
                .eq("execution_id", execution_id)\
                .execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Failed to update execution record: {e}")
            return False
    
    async def get_task_executions(
        self, 
        task_id: str, 
        limit: int = 50
    ) -> List[TaskExecutionResponse]:
        """获取任务执行历史"""
        try:
            result = self.db.table(self.execution_table)\
                .select("*")\
                .eq("task_id", task_id)\
                .order("started_at", desc=True)\
                .limit(limit)\
                .execute()
            
            if result.data:
                return [TaskExecutionResponse(**record) for record in result.data]
            return []
            
        except Exception as e:
            logger.error(f"Failed to get task executions: {e}")
            return []
    
    # 任务分析相关方法
    async def get_task_analytics(
        self, 
        user_id: str, 
        days: int = 30
    ) -> Optional[TaskAnalyticsResponse]:
        """获取任务分析数据"""
        try:
            since = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            # 获取任务统计
            tasks_result = self.db.table(self.table_name)\
                .select("status, task_type, run_count, success_count, failure_count, total_credits_consumed")\
                .eq("user_id", user_id)\
                .gte("created_at", since)\
                .is_("deleted_at", None)\
                .execute()
            
            # 获取执行统计
            executions_result = self.db.table(self.execution_table)\
                .select("status, credits_consumed, tokens_used, api_calls_made, duration_ms, started_at")\
                .eq("user_id", user_id)\
                .gte("started_at", since)\
                .execute()
            
            tasks = tasks_result.data or []
            executions = executions_result.data or []
            
            # 初始化分析数据
            analytics = {
                "user_id": user_id,
                "time_period": f"{days}d",
                "total_tasks": 0,
                "active_tasks": 0,
                "completed_tasks": 0,
                "failed_tasks": 0,
                "paused_tasks": 0,
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "success_rate": 0.0,
                "average_execution_time": 0.0,
                "total_credits_consumed": 0.0,
                "total_tokens_used": 0,
                "total_api_calls": 0,
                "task_types_distribution": {},
                "busiest_hours": [],
                "busiest_days": []
            }
            
            # 任务状态统计
            for task in tasks:
                status = task.get('status', '')
                if status == TaskStatus.PENDING.value:
                    analytics["active_tasks"] += 1
                elif status == TaskStatus.COMPLETED.value:
                    analytics["completed_tasks"] += 1
                elif status == TaskStatus.FAILED.value:
                    analytics["failed_tasks"] += 1
                elif status == TaskStatus.PAUSED.value:
                    analytics["paused_tasks"] += 1
                
                # 任务类型分布
                task_type = task.get('task_type', 'unknown')
                analytics["task_types_distribution"][task_type] = \
                    analytics["task_types_distribution"].get(task_type, 0) + 1
                
                # 资源消耗
                analytics["total_credits_consumed"] += task.get('total_credits_consumed', 0)
            
            analytics["total_tasks"] = len(tasks)
            
            # 执行统计
            successful_executions = 0
            total_duration = 0
            duration_count = 0
            hour_distribution = {}
            day_distribution = {}
            
            for execution in executions:
                analytics["total_executions"] += 1
                
                if execution.get('status') == TaskStatus.COMPLETED.value:
                    successful_executions += 1
                elif execution.get('status') == TaskStatus.FAILED.value:
                    analytics["failed_executions"] += 1
                
                analytics["total_credits_consumed"] += execution.get('credits_consumed', 0)
                analytics["total_tokens_used"] += execution.get('tokens_used', 0) or 0
                analytics["total_api_calls"] += execution.get('api_calls_made', 0) or 0
                
                if execution.get('duration_ms'):
                    total_duration += execution['duration_ms']
                    duration_count += 1
                
                # 时间分析
                if execution.get('started_at'):
                    started = datetime.fromisoformat(execution['started_at'])
                    hour = started.hour
                    day = started.strftime('%A')
                    
                    hour_distribution[hour] = hour_distribution.get(hour, 0) + 1
                    day_distribution[day] = day_distribution.get(day, 0) + 1
            
            analytics["successful_executions"] = successful_executions
            
            # 计算成功率
            if analytics["total_executions"] > 0:
                analytics["success_rate"] = round(
                    (successful_executions / analytics["total_executions"]) * 100, 2
                )
            
            # 计算平均执行时长（转换为秒）
            if duration_count > 0:
                analytics["average_execution_time"] = round(total_duration / duration_count / 1000, 2)
            
            # 找出最繁忙的时段和日期
            if hour_distribution:
                sorted_hours = sorted(hour_distribution.items(), key=lambda x: x[1], reverse=True)
                analytics["busiest_hours"] = [h[0] for h in sorted_hours[:3]]
            
            if day_distribution:
                sorted_days = sorted(day_distribution.items(), key=lambda x: x[1], reverse=True)
                analytics["busiest_days"] = [d[0] for d in sorted_days[:3]]
            
            return TaskAnalyticsResponse(**analytics)
            
        except Exception as e:
            logger.error(f"Failed to get task analytics: {e}")
            return None
    
    # 任务模板相关方法
    async def get_task_templates(
        self, 
        subscription_level: str = "free"
    ) -> List[TaskTemplateResponse]:
        """获取可用的任务模板"""
        try:
            # 定义订阅级别的优先级
            level_priority = {"free": 0, "basic": 1, "pro": 2, "enterprise": 3}
            user_priority = level_priority.get(subscription_level, 0)
            
            result = self.db.table(self.template_table)\
                .select("*")\
                .eq("is_active", True)\
                .execute()
            
            if result.data:
                # 过滤出用户可用的模板
                templates = []
                for template in result.data:
                    required_level = template.get("required_subscription_level", "free")
                    if level_priority.get(required_level, 0) <= user_priority:
                        templates.append(TaskTemplateResponse(**template))
                
                # 按类别和名称排序
                templates.sort(key=lambda x: (x.category, x.name))
                return templates
            return []
            
        except Exception as e:
            logger.error(f"Failed to get task templates: {e}")
            return []