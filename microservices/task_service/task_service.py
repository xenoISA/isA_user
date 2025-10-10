"""
Task Service Business Logic Layer

任务服务业务逻辑层，处理任务创建、执行、调度、权限验证等核心功能
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from decimal import Decimal

# Internal imports
from .task_repository import TaskRepository
from .models import (
    TaskCreateRequest, TaskUpdateRequest, TaskExecutionRequest,
    TaskResponse, TaskExecutionResponse, TaskTemplateResponse, 
    TaskAnalyticsResponse, TaskListResponse,
    TaskStatus, TaskType, TaskPriority
)

# Service communication imports
import httpx
from core.consul_registry import ConsulRegistry

# Temporary ServiceError class until shared module is available
class ServiceError(Exception):
    """服务通信错误"""
    pass

logger = logging.getLogger(__name__)


class TaskExecutionError(Exception):
    """任务执行错误"""
    def __init__(self, message: str, task_id: str = None, error_code: str = None):
        super().__init__(message)
        self.task_id = task_id
        self.error_code = error_code


class TaskService:
    """任务服务业务逻辑层"""

    def __init__(self):
        self.repository = TaskRepository()
        self.consul = None
        self._init_consul()

        # 配置参数
        self.max_tasks_per_user = {
            "free": 5,
            "basic": 20,
            "pro": 100,
            "enterprise": -1  # unlimited
        }

        self.max_executions_per_day = {
            "free": 10,
            "basic": 100,
            "pro": 1000,
            "enterprise": -1  # unlimited
        }

        # 任务执行器注册表
        self.task_executors = {}
        self._register_default_executors()

        # HTTP客户端用于服务间通信
        self.http_client = httpx.AsyncClient(timeout=30.0)

        # 临时创建通信器占位符以避免错误
        self.communicator = self._create_temp_communicator()
        self.orchestrator = self._create_temp_orchestrator()

    def _init_consul(self):
        """Initialize Consul registry for service discovery"""
        try:
            from core.config_manager import ConfigManager
            config_manager = ConfigManager("task_service")
            config = config_manager.get_service_config()

            if config.consul_enabled:
                self.consul = ConsulRegistry(
                    service_name=config.service_name,
                    service_port=config.service_port,
                    consul_host=config.consul_host,
                    consul_port=config.consul_port
                )
                logger.info("Consul service discovery initialized for task service")
        except Exception as e:
            logger.warning(f"Failed to initialize Consul: {e}, will use fallback URLs")

    def _get_service_url(self, service_name: str, fallback_port: int) -> str:
        """Get service URL via Consul discovery with fallback"""
        fallback_url = f"http://localhost:{fallback_port}"
        if self.consul:
            return self.consul.get_service_address(service_name, fallback_url=fallback_url)
        return fallback_url
    
    def _create_temp_communicator(self):
        """创建临时通信器占位符"""
        class TempCommunicator:
            async def check_user_permission(self, **kwargs):
                return {"allowed": True, "has_permission": True}
            
            async def log_audit_event(self, **kwargs):
                logger.debug(f"Audit event (skipped): {kwargs}")
            
            async def call_notification_service(self, *args, **kwargs):
                logger.debug(f"Notification (skipped): {args} {kwargs}")
            
            async def _call_service(self, *args, **kwargs):
                logger.debug(f"Service call (skipped): {args} {kwargs}")
                return {}
        
        return TempCommunicator()
    
    def _create_temp_orchestrator(self):
        """创建临时编排器占位符"""
        class TempOrchestrator:
            async def get_user_context_with_permissions(self, user_id):
                return {
                    "success": True,
                    "user": {
                        "user_id": user_id,
                        "subscription_level": "basic"
                    }
                }
        
        return TempOrchestrator()
    
    def _register_default_executors(self):
        """注册默认任务执行器"""
        self.task_executors[TaskType.DAILY_WEATHER] = self._execute_weather_task
        self.task_executors[TaskType.DAILY_NEWS] = self._execute_news_task
        self.task_executors[TaskType.NEWS_MONITOR] = self._execute_news_monitor_task
        self.task_executors[TaskType.WEATHER_ALERT] = self._execute_weather_alert_task
        self.task_executors[TaskType.PRICE_TRACKER] = self._execute_price_tracker_task
        self.task_executors[TaskType.TODO] = self._execute_todo_task
        self.task_executors[TaskType.REMINDER] = self._execute_reminder_task
        self.task_executors[TaskType.CALENDAR_EVENT] = self._execute_calendar_event_task
        self.task_executors[TaskType.CUSTOM] = self._execute_custom_task
    
    # ====================
    # 任务CRUD操作
    # ====================
    
    async def create_task(self, user_id: str, request: TaskCreateRequest) -> TaskResponse:
        """创建用户任务"""
        try:
            # 1. 获取用户信息和权限检查
            user_context = await self.orchestrator.get_user_context_with_permissions(user_id)
            if not user_context["success"]:
                raise TaskExecutionError("Failed to get user context", error_code="USER_CONTEXT_ERROR")
            
            user = user_context["user"]
            subscription_level = user.get("subscription_level", "free")
            
            # 2. 检查任务创建权限
            perm_result = await self.communicator.check_user_permission(
                user_id=user_id,
                resource_type="task",
                resource_name=request.task_type.value,
                action="create",
                subscription_level=subscription_level
            )
            
            if not perm_result.get("allowed", False):
                raise TaskExecutionError(
                    f"Permission denied for creating {request.task_type.value} task",
                    error_code="PERMISSION_DENIED"
                )
            
            # 3. 检查任务数量限制
            await self._check_task_limits(user_id, subscription_level)
            
            # 4. 验证任务配置
            await self._validate_task_config(request)
            
            # 5. 处理调度信息
            task_data = request.dict()
            if request.schedule:
                next_run_time = self._calculate_next_run_time(request.schedule)
                task_data["next_run_time"] = next_run_time
                task_data["status"] = TaskStatus.SCHEDULED.value
            
            # 6. 创建任务
            task = await self.repository.create_task(user_id, task_data)
            if not task:
                raise TaskExecutionError("Failed to create task", error_code="CREATION_FAILED")
            
            # 7. 设置提醒通知
            if request.reminder_time:
                await self._schedule_reminder_notification(task, request.reminder_time)
            
            # 8. 记录审计事件
            await self.communicator.log_audit_event(
                event_type="task_created",
                user_id=user_id,
                event_data={
                    "task_id": task.task_id,
                    "task_type": request.task_type.value,
                    "priority": request.priority.value,
                    "scheduled": bool(request.schedule)
                }
            )
            
            logger.info(f"Task created successfully: {task.task_id} for user {user_id}")
            return task
            
        except TaskExecutionError:
            raise
        except Exception as e:
            logger.error(f"Failed to create task for user {user_id}: {e}")
            raise TaskExecutionError(f"Task creation failed: {str(e)}", error_code="INTERNAL_ERROR")
    
    async def get_task(self, task_id: str, user_id: str) -> Optional[TaskResponse]:
        """获取任务详情"""
        try:
            # 权限检查
            await self._check_task_access_permission(task_id, user_id, "read")
            
            # 获取任务
            task = await self.repository.get_task_by_id(task_id, user_id)
            
            if task:
                # 记录访问审计
                await self.communicator.log_audit_event(
                    event_type="task_accessed",
                    user_id=user_id,
                    event_data={"task_id": task_id, "action": "read"}
                )
            
            return task
            
        except Exception as e:
            logger.error(f"Failed to get task {task_id} for user {user_id}: {e}")
            raise TaskExecutionError(f"Failed to get task: {str(e)}", task_id=task_id)
    
    async def update_task(self, task_id: str, user_id: str, request: TaskUpdateRequest) -> TaskResponse:
        """更新任务"""
        try:
            # 权限检查
            await self._check_task_access_permission(task_id, user_id, "update")
            
            # 验证任务存在
            existing_task = await self.repository.get_task_by_id(task_id, user_id)
            if not existing_task:
                raise TaskExecutionError("Task not found", task_id=task_id, error_code="NOT_FOUND")
            
            # 构建更新数据
            update_data = {}
            if request.name is not None:
                update_data["name"] = request.name
            if request.description is not None:
                update_data["description"] = request.description
            if request.priority is not None:
                update_data["priority"] = request.priority.value
            if request.status is not None:
                update_data["status"] = request.status.value
            if request.config is not None:
                update_data["config"] = request.config
            if request.schedule is not None:
                update_data["schedule"] = request.schedule
                # 重新计算下次执行时间
                if request.schedule:
                    update_data["next_run_time"] = self._calculate_next_run_time(request.schedule)
            if request.credits_per_run is not None:
                update_data["credits_per_run"] = request.credits_per_run
            if request.tags is not None:
                update_data["tags"] = request.tags
            if request.metadata is not None:
                update_data["metadata"] = request.metadata
            if request.due_date is not None:
                update_data["due_date"] = request.due_date
            if request.reminder_time is not None:
                update_data["reminder_time"] = request.reminder_time
            if request.next_run_time is not None:
                update_data["next_run_time"] = request.next_run_time
            
            # 执行更新
            updated_task = await self.repository.update_task(task_id, user_id, update_data)
            if not updated_task:
                raise TaskExecutionError("Failed to update task", task_id=task_id, error_code="UPDATE_FAILED")
            
            # 记录审计事件
            await self.communicator.log_audit_event(
                event_type="task_updated",
                user_id=user_id,
                event_data={
                    "task_id": task_id,
                    "updated_fields": list(update_data.keys()),
                    "status_changed": "status" in update_data
                }
            )
            
            logger.info(f"Task updated successfully: {task_id}")
            return updated_task
            
        except TaskExecutionError:
            raise
        except Exception as e:
            logger.error(f"Failed to update task {task_id}: {e}")
            raise TaskExecutionError(f"Task update failed: {str(e)}", task_id=task_id)
    
    async def delete_task(self, task_id: str, user_id: str) -> bool:
        """删除任务（软删除）"""
        try:
            # 权限检查
            await self._check_task_access_permission(task_id, user_id, "delete")
            
            # 执行删除
            success = await self.repository.delete_task(task_id, user_id)
            
            if success:
                # 记录审计事件
                await self.communicator.log_audit_event(
                    event_type="task_deleted",
                    user_id=user_id,
                    event_data={"task_id": task_id}
                )
                logger.info(f"Task deleted successfully: {task_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete task {task_id}: {e}")
            raise TaskExecutionError(f"Task deletion failed: {str(e)}", task_id=task_id)
    
    async def get_user_tasks(
        self,
        user_id: str,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> TaskListResponse:
        """获取用户任务列表"""
        try:
            # 权限检查
            await self._check_user_access_permission(user_id, "list")
            
            # 获取任务列表
            tasks = await self.repository.get_user_tasks(
                user_id=user_id,
                status=status,
                task_type=task_type,
                limit=limit,
                offset=offset
            )
            
            # Debug logging
            print(f"DEBUG: tasks type = {type(tasks)}")
            print(f"DEBUG: tasks = {tasks}")
            
            # 记录访问审计
            await self.communicator.log_audit_event(
                event_type="task_list_accessed",
                user_id=user_id,
                event_data={
                    "filters": {"status": status, "task_type": task_type},
                    "result_count": len(tasks) if isinstance(tasks, list) else 0
                }
            )
            
            return TaskListResponse(
                tasks=tasks,
                count=len(tasks) if isinstance(tasks, list) else 0,
                limit=limit,
                offset=offset,
                filters={"status": status, "task_type": task_type}
            )
            
        except Exception as e:
            logger.error(f"Failed to get user tasks for {user_id}: {e}")
            raise TaskExecutionError(f"Failed to get user tasks: {str(e)}")
    
    # ====================
    # 任务执行
    # ====================
    
    async def execute_task(self, task_id: str, user_id: str, request: TaskExecutionRequest) -> TaskExecutionResponse:
        """手动执行任务"""
        try:
            # 权限检查
            await self._check_task_access_permission(task_id, user_id, "execute")
            
            # 获取任务信息
            task = await self.repository.get_task_by_id(task_id, user_id)
            if not task:
                raise TaskExecutionError("Task not found", task_id=task_id, error_code="NOT_FOUND")
            
            # 检查任务状态
            if task.status in [TaskStatus.CANCELLED.value, TaskStatus.RUNNING.value]:
                raise TaskExecutionError(
                    f"Cannot execute task in status: {task.status}",
                    task_id=task_id,
                    error_code="INVALID_STATUS"
                )
            
            # 检查执行限制
            await self._check_execution_limits(user_id, task)
            
            # 创建执行记录
            execution_record = await self.repository.create_execution_record(
                task_id=task_id,
                user_id=user_id,
                execution_data=request.dict()
            )
            
            if not execution_record:
                raise TaskExecutionError("Failed to create execution record", task_id=task_id)
            
            # 异步执行任务
            asyncio.create_task(self._execute_task_async(task, execution_record))
            
            logger.info(f"Task execution started: {task_id} (execution: {execution_record.execution_id})")
            return execution_record
            
        except TaskExecutionError:
            raise
        except Exception as e:
            logger.error(f"Failed to execute task {task_id}: {e}")
            raise TaskExecutionError(f"Task execution failed: {str(e)}", task_id=task_id)
    
    async def _execute_task_async(self, task: TaskResponse, execution_record: TaskExecutionResponse):
        """异步执行任务"""
        try:
            # 更新任务状态为运行中
            await self.repository.update_task(
                task.task_id,
                task.user_id,
                {"status": TaskStatus.RUNNING.value}
            )
            
            # 获取任务执行器
            executor = self.task_executors.get(TaskType(task.task_type))
            if not executor:
                raise TaskExecutionError(
                    f"No executor found for task type: {task.task_type}",
                    task_id=task.task_id,
                    error_code="NO_EXECUTOR"
                )
            
            # 执行任务
            start_time = datetime.utcnow()
            result = await executor(task)
            end_time = datetime.utcnow()
            
            # 计算消耗的积分
            credits_consumed = float(task.credits_per_run or 0)
            
            # 更新执行记录
            execution_result = {
                "success": True,
                "result": result,
                "credits_consumed": credits_consumed,
                "started_at": start_time.isoformat()
            }
            
            await self.repository.update_execution_record(
                execution_record.execution_id,
                execution_result
            )
            
            # 更新任务执行信息
            await self.repository.update_task_execution_info(
                task.task_id,
                execution_result
            )
            
            # 更新任务状态
            new_status = TaskStatus.COMPLETED.value
            if task.schedule:  # 如果有调度，设置为已调度状态
                new_status = TaskStatus.SCHEDULED.value
            
            await self.repository.update_task(
                task.task_id,
                task.user_id,
                {"status": new_status}
            )
            
            # 发送执行完成通知
            await self._send_execution_notification(task, execution_record, success=True, result=result)
            
            # 记录审计事件
            await self.communicator.log_audit_event(
                event_type="task_executed",
                user_id=task.user_id,
                event_data={
                    "task_id": task.task_id,
                    "execution_id": execution_record.execution_id,
                    "success": True,
                    "credits_consumed": credits_consumed,
                    "duration_ms": int((end_time - start_time).total_seconds() * 1000)
                }
            )
            
            logger.info(f"Task executed successfully: {task.task_id}")
            
        except Exception as e:
            logger.error(f"Task execution failed: {task.task_id} - {e}")
            
            # 更新执行记录为失败
            execution_result = {
                "success": False,
                "error": str(e),
                "credits_consumed": 0,
                "started_at": execution_record.started_at.isoformat()
            }
            
            await self.repository.update_execution_record(
                execution_record.execution_id,
                execution_result
            )
            
            # 更新任务执行信息
            await self.repository.update_task_execution_info(
                task.task_id,
                execution_result
            )
            
            # 更新任务状态为失败
            await self.repository.update_task(
                task.task_id,
                task.user_id,
                {"status": TaskStatus.FAILED.value}
            )
            
            # 发送执行失败通知
            await self._send_execution_notification(task, execution_record, success=False, error=str(e))
            
            # 记录审计事件
            await self.communicator.log_audit_event(
                event_type="task_execution_failed",
                user_id=task.user_id,
                event_data={
                    "task_id": task.task_id,
                    "execution_id": execution_record.execution_id,
                    "error": str(e)
                }
            )
    
    async def get_pending_tasks(self, limit: int = 50) -> List[TaskResponse]:
        """获取待执行的任务（供调度器使用）"""
        try:
            return await self.repository.get_pending_tasks(limit)
        except Exception as e:
            logger.error(f"Failed to get pending tasks: {e}")
            return []
    
    # ====================
    # 任务分析和统计
    # ====================
    
    async def get_task_analytics(self, user_id: str, days: int = 30) -> Optional[TaskAnalyticsResponse]:
        """获取任务分析数据"""
        try:
            # 权限检查
            await self._check_user_access_permission(user_id, "analytics")
            
            analytics = await self.repository.get_task_analytics(user_id, days)
            
            if analytics:
                # 记录访问审计
                await self.communicator.log_audit_event(
                    event_type="task_analytics_accessed",
                    user_id=user_id,
                    event_data={"days": days}
                )
            
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to get task analytics for {user_id}: {e}")
            raise TaskExecutionError(f"Failed to get task analytics: {str(e)}")
    
    async def get_task_templates(self, user_id: str) -> List[TaskTemplateResponse]:
        """获取可用的任务模板"""
        try:
            # 获取用户订阅级别
            user_context = await self.orchestrator.get_user_context_with_permissions(user_id)
            subscription_level = "free"
            
            if user_context["success"] and user_context["user"]:
                subscription_level = user_context["user"].get("subscription_level", "free")
            
            templates = await self.repository.get_task_templates(subscription_level)
            
            # 记录访问审计
            await self.communicator.log_audit_event(
                event_type="task_templates_accessed",
                user_id=user_id,
                event_data={"subscription_level": subscription_level, "template_count": len(templates)}
            )
            
            return templates
            
        except Exception as e:
            logger.error(f"Failed to get task templates for {user_id}: {e}")
            raise TaskExecutionError(f"Failed to get task templates: {str(e)}")
    
    # ====================
    # 权限和限制检查
    # ====================
    
    async def _check_task_access_permission(self, task_id: str, user_id: str, action: str):
        """检查任务访问权限"""
        try:
            # 首先验证任务是否属于用户
            task = await self.repository.get_task_by_id(task_id, user_id)
            if not task:
                raise TaskExecutionError("Task not found or access denied", task_id=task_id, error_code="NOT_FOUND")
            
            # 检查具体操作权限
            perm_result = await self.communicator.check_user_permission(
                user_id=user_id,
                resource_type="task",
                resource_name=task.task_type,
                action=action
            )
            
            if not perm_result.get("allowed", False):
                raise TaskExecutionError(
                    f"Permission denied for {action} on task {task_id}",
                    task_id=task_id,
                    error_code="PERMISSION_DENIED"
                )
                
        except TaskExecutionError:
            raise
        except Exception as e:
            logger.error(f"Permission check failed for task {task_id}: {e}")
            raise TaskExecutionError("Permission check failed", task_id=task_id, error_code="PERMISSION_CHECK_ERROR")
    
    async def _check_user_access_permission(self, user_id: str, action: str):
        """检查用户级别的访问权限"""
        try:
            perm_result = await self.communicator.check_user_permission(
                user_id=user_id,
                resource_type="task",
                resource_name="user_tasks",
                action=action
            )
            
            if not perm_result.get("allowed", False):
                raise TaskExecutionError(
                    f"Permission denied for {action} on user tasks",
                    error_code="PERMISSION_DENIED"
                )
                
        except TaskExecutionError:
            raise
        except Exception as e:
            logger.error(f"User permission check failed for {user_id}: {e}")
            raise TaskExecutionError("Permission check failed", error_code="PERMISSION_CHECK_ERROR")
    
    async def _check_task_limits(self, user_id: str, subscription_level: str):
        """检查任务数量限制"""
        try:
            max_tasks = self.max_tasks_per_user.get(subscription_level, 5)
            
            if max_tasks > 0:  # -1 表示无限制
                user_tasks = await self.repository.get_user_tasks(user_id, limit=max_tasks + 1)
                
                if len(user_tasks) >= max_tasks:
                    raise TaskExecutionError(
                        f"Task limit exceeded. Maximum {max_tasks} tasks allowed for {subscription_level} subscription",
                        error_code="TASK_LIMIT_EXCEEDED"
                    )
                    
        except TaskExecutionError:
            raise
        except Exception as e:
            logger.error(f"Task limit check failed for {user_id}: {e}")
            raise TaskExecutionError("Task limit check failed", error_code="LIMIT_CHECK_ERROR")
    
    async def _check_execution_limits(self, user_id: str, task: TaskResponse):
        """检查执行次数限制"""
        try:
            # 获取用户订阅级别
            user_context = await self.orchestrator.get_user_context_with_permissions(user_id)
            subscription_level = "free"
            
            if user_context["success"] and user_context["user"]:
                subscription_level = user_context["user"].get("subscription_level", "free")
            
            max_executions = self.max_executions_per_day.get(subscription_level, 10)
            
            if max_executions > 0:  # -1 表示无限制
                # 计算今天的执行次数
                today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                today_tasks = await self.repository.get_user_tasks(
                    user_id,
                    limit=1000  # 获取足够多的任务来计算今天的执行次数
                )
                
                today_executions = sum(
                    task.run_count for task in today_tasks 
                    if task.last_run_time and task.last_run_time >= today_start
                )
                
                if today_executions >= max_executions:
                    raise TaskExecutionError(
                        f"Daily execution limit exceeded. Maximum {max_executions} executions allowed for {subscription_level} subscription",
                        task_id=task.task_id,
                        error_code="EXECUTION_LIMIT_EXCEEDED"
                    )
                    
        except TaskExecutionError:
            raise
        except Exception as e:
            logger.error(f"Execution limit check failed for {user_id}: {e}")
            raise TaskExecutionError("Execution limit check failed", error_code="LIMIT_CHECK_ERROR")
    
    # ====================
    # 任务配置验证
    # ====================
    
    async def _validate_task_config(self, request: TaskCreateRequest):
        """验证任务配置"""
        try:
            # 基本验证
            if not request.name or len(request.name.strip()) == 0:
                raise TaskExecutionError("Task name cannot be empty", error_code="INVALID_CONFIG")
            
            # 根据任务类型验证配置
            if request.task_type == TaskType.DAILY_WEATHER:
                self._validate_weather_config(request.config)
            elif request.task_type == TaskType.DAILY_NEWS:
                self._validate_news_config(request.config)
            elif request.task_type == TaskType.NEWS_MONITOR:
                self._validate_news_monitor_config(request.config)
            elif request.task_type == TaskType.WEATHER_ALERT:
                self._validate_weather_alert_config(request.config)
            elif request.task_type == TaskType.PRICE_TRACKER:
                self._validate_price_tracker_config(request.config)
            elif request.task_type == TaskType.TODO:
                self._validate_todo_config(request.config)
            elif request.task_type == TaskType.REMINDER:
                self._validate_reminder_config(request.config)
            elif request.task_type == TaskType.CALENDAR_EVENT:
                self._validate_calendar_event_config(request.config)
            elif request.task_type == TaskType.CUSTOM:
                self._validate_custom_config(request.config)
            
            # 验证调度配置
            if request.schedule:
                self._validate_schedule_config(request.schedule)
                
        except TaskExecutionError:
            raise
        except Exception as e:
            logger.error(f"Task config validation failed: {e}")
            raise TaskExecutionError(f"Invalid task configuration: {str(e)}", error_code="INVALID_CONFIG")
    
    def _validate_weather_config(self, config: Dict[str, Any]):
        """验证天气任务配置"""
        required_fields = ["location"]
        for field in required_fields:
            if field not in config:
                raise TaskExecutionError(f"Missing required field for weather task: {field}")
    
    def _validate_news_config(self, config: Dict[str, Any]):
        """验证新闻任务配置"""
        # 新闻任务配置相对简单，可以有可选的类别和来源
        pass
    
    def _validate_news_monitor_config(self, config: Dict[str, Any]):
        """验证新闻监控任务配置"""
        required_fields = ["keywords"]
        for field in required_fields:
            if field not in config:
                raise TaskExecutionError(f"Missing required field for news monitor task: {field}")
    
    def _validate_weather_alert_config(self, config: Dict[str, Any]):
        """验证天气预警任务配置"""
        required_fields = ["location", "alert_conditions"]
        for field in required_fields:
            if field not in config:
                raise TaskExecutionError(f"Missing required field for weather alert task: {field}")
    
    def _validate_price_tracker_config(self, config: Dict[str, Any]):
        """验证价格跟踪任务配置"""
        required_fields = ["product_url", "target_price"]
        for field in required_fields:
            if field not in config:
                raise TaskExecutionError(f"Missing required field for price tracker task: {field}")
    
    def _validate_todo_config(self, config: Dict[str, Any]):
        """验证待办任务配置"""
        # 待办任务配置比较简单
        pass
    
    def _validate_reminder_config(self, config: Dict[str, Any]):
        """验证提醒任务配置"""
        required_fields = ["reminder_message"]
        for field in required_fields:
            if field not in config:
                raise TaskExecutionError(f"Missing required field for reminder task: {field}")
    
    def _validate_calendar_event_config(self, config: Dict[str, Any]):
        """验证日历事件任务配置"""
        required_fields = ["event_title", "event_time"]
        for field in required_fields:
            if field not in config:
                raise TaskExecutionError(f"Missing required field for calendar event task: {field}")
    
    def _validate_custom_config(self, config: Dict[str, Any]):
        """验证自定义任务配置"""
        required_fields = ["script_type"]
        for field in required_fields:
            if field not in config:
                raise TaskExecutionError(f"Missing required field for custom task: {field}")
    
    def _validate_schedule_config(self, schedule: Dict[str, Any]):
        """验证调度配置"""
        schedule_type = schedule.get("type")
        if not schedule_type:
            raise TaskExecutionError("Schedule type is required")
        
        if schedule_type not in ["once", "daily", "weekly", "monthly", "cron"]:
            raise TaskExecutionError(f"Invalid schedule type: {schedule_type}")
        
        if schedule_type == "cron" and "cron_expression" not in schedule:
            raise TaskExecutionError("Cron expression is required for cron schedule")
    
    # ====================
    # 调度相关
    # ====================
    
    def _calculate_next_run_time(self, schedule: Dict[str, Any]) -> datetime:
        """计算下次执行时间"""
        try:
            schedule_type = schedule.get("type")
            now = datetime.utcnow()
            
            if schedule_type == "once":
                run_time = schedule.get("run_time")
                if run_time:
                    if isinstance(run_time, str):
                        return datetime.fromisoformat(run_time)
                    return run_time
                return now + timedelta(minutes=5)  # 默认5分钟后执行
            
            elif schedule_type == "daily":
                run_time = schedule.get("run_time", "09:00")
                hour, minute = map(int, run_time.split(":"))
                next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if next_run <= now:
                    next_run += timedelta(days=1)
                return next_run
            
            elif schedule_type == "weekly":
                weekday = schedule.get("weekday", 1)  # Monday = 1
                run_time = schedule.get("run_time", "09:00")
                hour, minute = map(int, run_time.split(":"))
                
                days_ahead = weekday - now.weekday()
                if days_ahead <= 0:  # Target day already happened this week
                    days_ahead += 7
                
                next_run = now + timedelta(days=days_ahead)
                next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)
                return next_run
            
            elif schedule_type == "monthly":
                day_of_month = schedule.get("day", 1)
                run_time = schedule.get("run_time", "09:00")
                hour, minute = map(int, run_time.split(":"))
                
                # 计算下个月的指定日期
                if now.month == 12:
                    next_month = now.replace(year=now.year + 1, month=1, day=day_of_month)
                else:
                    next_month = now.replace(month=now.month + 1, day=day_of_month)
                
                next_run = next_month.replace(hour=hour, minute=minute, second=0, microsecond=0)
                return next_run
            
            elif schedule_type == "cron":
                # 简化的cron解析，实际应用中可以使用croniter库
                # 这里只提供基本实现
                return now + timedelta(hours=1)  # 默认1小时后执行
            
            else:
                return now + timedelta(minutes=5)  # 默认5分钟后执行
                
        except Exception as e:
            logger.error(f"Failed to calculate next run time: {e}")
            return datetime.utcnow() + timedelta(minutes=5)
    
    # ====================
    # 任务执行器实现
    # ====================
    
    async def _execute_weather_task(self, task: TaskResponse) -> Dict[str, Any]:
        """执行天气任务（模拟实现）"""
        try:
            location = task.config.get("location", "Unknown")
            
            # 模拟天气API调用
            weather_data = {
                "location": location,
                "temperature": "22°C",
                "condition": "Sunny",
                "humidity": "65%",
                "wind": "10 km/h",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # 发送天气通知
            await self._send_weather_notification(task, weather_data)
            
            return {
                "status": "success",
                "weather_data": weather_data,
                "message": f"Weather information retrieved for {location}"
            }
            
        except Exception as e:
            logger.error(f"Weather task execution failed: {e}")
            raise TaskExecutionError(f"Weather task failed: {str(e)}", task_id=task.task_id)
    
    async def _execute_news_task(self, task: TaskResponse) -> Dict[str, Any]:
        """执行新闻任务（模拟实现）"""
        try:
            category = task.config.get("category", "general")
            
            # 模拟新闻API调用
            news_data = {
                "category": category,
                "articles": [
                    {
                        "title": "Sample News Article 1",
                        "summary": "This is a sample news article summary.",
                        "url": "https://example.com/news1",
                        "published_at": datetime.utcnow().isoformat()
                    },
                    {
                        "title": "Sample News Article 2",
                        "summary": "This is another sample news article summary.",
                        "url": "https://example.com/news2",
                        "published_at": datetime.utcnow().isoformat()
                    }
                ],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # 发送新闻通知
            await self._send_news_notification(task, news_data)
            
            return {
                "status": "success",
                "news_data": news_data,
                "message": f"News articles retrieved for category: {category}"
            }
            
        except Exception as e:
            logger.error(f"News task execution failed: {e}")
            raise TaskExecutionError(f"News task failed: {str(e)}", task_id=task.task_id)
    
    async def _execute_news_monitor_task(self, task: TaskResponse) -> Dict[str, Any]:
        """执行新闻监控任务（模拟实现）"""
        try:
            keywords = task.config.get("keywords", [])
            
            # 模拟关键词新闻搜索
            monitored_news = {
                "keywords": keywords,
                "matches": [
                    {
                        "title": f"Article mentioning {keywords[0] if keywords else 'keyword'}",
                        "summary": "This article contains the monitored keyword.",
                        "url": "https://example.com/monitored",
                        "relevance_score": 0.85,
                        "published_at": datetime.utcnow().isoformat()
                    }
                ],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return {
                "status": "success",
                "monitored_data": monitored_news,
                "message": f"News monitoring completed for keywords: {', '.join(keywords)}"
            }
            
        except Exception as e:
            logger.error(f"News monitor task execution failed: {e}")
            raise TaskExecutionError(f"News monitor task failed: {str(e)}", task_id=task.task_id)
    
    async def _execute_weather_alert_task(self, task: TaskResponse) -> Dict[str, Any]:
        """执行天气预警任务（模拟实现）"""
        try:
            location = task.config.get("location", "Unknown")
            alert_conditions = task.config.get("alert_conditions", {})
            
            # 模拟天气检查
            current_weather = {
                "temperature": 25,
                "condition": "Rainy",
                "wind_speed": 15
            }
            
            alerts = []
            
            # 检查预警条件
            if "temperature" in alert_conditions:
                temp_condition = alert_conditions["temperature"]
                if (temp_condition.get("operator") == ">" and 
                    current_weather["temperature"] > temp_condition.get("value", 0)):
                    alerts.append(f"Temperature alert: {current_weather['temperature']}°C")
            
            result = {
                "location": location,
                "current_weather": current_weather,
                "alerts": alerts,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # 如果有预警，发送通知
            if alerts:
                await self._send_weather_alert_notification(task, result)
            
            return {
                "status": "success",
                "alert_data": result,
                "message": f"Weather alert check completed for {location}"
            }
            
        except Exception as e:
            logger.error(f"Weather alert task execution failed: {e}")
            raise TaskExecutionError(f"Weather alert task failed: {str(e)}", task_id=task.task_id)
    
    async def _execute_price_tracker_task(self, task: TaskResponse) -> Dict[str, Any]:
        """执行价格跟踪任务（模拟实现）"""
        try:
            product_url = task.config.get("product_url", "")
            target_price = task.config.get("target_price", 0)
            
            # 模拟价格检查
            current_price = 99.99  # 模拟当前价格
            
            result = {
                "product_url": product_url,
                "current_price": current_price,
                "target_price": target_price,
                "price_met": current_price <= target_price,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # 如果价格达到目标，发送通知
            if result["price_met"]:
                await self._send_price_alert_notification(task, result)
            
            return {
                "status": "success",
                "price_data": result,
                "message": f"Price tracking completed for {product_url}"
            }
            
        except Exception as e:
            logger.error(f"Price tracker task execution failed: {e}")
            raise TaskExecutionError(f"Price tracker task failed: {str(e)}", task_id=task.task_id)
    
    async def _execute_todo_task(self, task: TaskResponse) -> Dict[str, Any]:
        """执行待办任务"""
        try:
            # 待办任务主要是提醒功能
            result = {
                "task_name": task.name,
                "task_description": task.description,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "status": "reminder_sent",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # 发送待办提醒通知
            await self._send_todo_notification(task, result)
            
            return {
                "status": "success",
                "todo_data": result,
                "message": f"Todo reminder sent for: {task.name}"
            }
            
        except Exception as e:
            logger.error(f"Todo task execution failed: {e}")
            raise TaskExecutionError(f"Todo task failed: {str(e)}", task_id=task.task_id)
    
    async def _execute_reminder_task(self, task: TaskResponse) -> Dict[str, Any]:
        """执行提醒任务"""
        try:
            reminder_message = task.config.get("reminder_message", task.name)
            
            result = {
                "reminder_message": reminder_message,
                "task_name": task.name,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # 发送提醒通知
            await self._send_reminder_notification(task, result)
            
            return {
                "status": "success",
                "reminder_data": result,
                "message": f"Reminder sent: {reminder_message}"
            }
            
        except Exception as e:
            logger.error(f"Reminder task execution failed: {e}")
            raise TaskExecutionError(f"Reminder task failed: {str(e)}", task_id=task.task_id)
    
    async def _execute_calendar_event_task(self, task: TaskResponse) -> Dict[str, Any]:
        """执行日历事件任务"""
        try:
            event_title = task.config.get("event_title", task.name)
            event_time = task.config.get("event_time")
            
            result = {
                "event_title": event_title,
                "event_time": event_time,
                "task_name": task.name,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # 发送日历事件通知
            await self._send_calendar_notification(task, result)
            
            return {
                "status": "success",
                "calendar_data": result,
                "message": f"Calendar event reminder sent: {event_title}"
            }
            
        except Exception as e:
            logger.error(f"Calendar event task execution failed: {e}")
            raise TaskExecutionError(f"Calendar event task failed: {str(e)}", task_id=task.task_id)
    
    async def _execute_custom_task(self, task: TaskResponse) -> Dict[str, Any]:
        """执行自定义任务（模拟实现）"""
        try:
            script_type = task.config.get("script_type", "unknown")
            
            # 模拟自定义任务执行
            result = {
                "script_type": script_type,
                "task_name": task.name,
                "execution_time": datetime.utcnow().isoformat(),
                "output": "Custom task executed successfully"
            }
            
            return {
                "status": "success",
                "custom_data": result,
                "message": f"Custom task executed: {script_type}"
            }
            
        except Exception as e:
            logger.error(f"Custom task execution failed: {e}")
            raise TaskExecutionError(f"Custom task failed: {str(e)}", task_id=task.task_id)
    
    # ====================
    # 通知相关
    # ====================
    
    async def _schedule_reminder_notification(self, task: TaskResponse, reminder_time: datetime):
        """安排提醒通知"""
        try:
            # 这里可以集成通知服务来安排定时通知
            logger.info(f"Reminder scheduled for task {task.task_id} at {reminder_time}")
        except Exception as e:
            logger.error(f"Failed to schedule reminder notification: {e}")
    
    async def _send_execution_notification(
        self, 
        task: TaskResponse, 
        execution_record: TaskExecutionResponse, 
        success: bool, 
        result: Dict = None, 
        error: str = None
    ):
        """发送任务执行结果通知"""
        try:
            notification_data = {
                "type": "EMAIL",
                "recipient_id": task.user_id,
                "subject": f"Task Execution {'Completed' if success else 'Failed'}: {task.name}",
                "content": self._format_execution_notification(task, success, result, error),
                "metadata": {
                    "task_id": task.task_id,
                    "execution_id": execution_record.execution_id,
                    "task_type": task.task_type
                }
            }
            
            # 调用通知服务
            await self.communicator.call_notification_service(
                "/api/v1/notifications/send",
                notification_data,
                "POST"
            )
            
        except Exception as e:
            logger.error(f"Failed to send execution notification: {e}")
    
    def _format_execution_notification(
        self, 
        task: TaskResponse, 
        success: bool, 
        result: Dict = None, 
        error: str = None
    ) -> str:
        """格式化执行通知内容"""
        if success:
            content = f"""
            Dear User,
            
            Your task "{task.name}" has been executed successfully.
            
            Task Details:
            - Task ID: {task.task_id}
            - Task Type: {task.task_type}
            - Execution Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
            
            """
            
            if result:
                content += f"Result: {json.dumps(result, indent=2)}\n"
            
            content += """
            Best regards,
            Task Service Team
            """
        else:
            content = f"""
            Dear User,
            
            Your task "{task.name}" execution has failed.
            
            Task Details:
            - Task ID: {task.task_id}
            - Task Type: {task.task_type}
            - Execution Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
            - Error: {error or 'Unknown error'}
            
            Please check your task configuration and try again.
            
            Best regards,
            Task Service Team
            """
        
        return content
    
    async def _send_weather_notification(self, task: TaskResponse, weather_data: Dict):
        """发送天气通知"""
        try:
            content = f"""
            Weather Update for {weather_data['location']}:
            
            Temperature: {weather_data['temperature']}
            Condition: {weather_data['condition']}
            Humidity: {weather_data['humidity']}
            Wind: {weather_data['wind']}
            
            Updated at: {weather_data['timestamp']}
            """
            
            await self._send_notification(task, "Weather Update", content, weather_data)
        except Exception as e:
            logger.error(f"Failed to send weather notification: {e}")
    
    async def _send_news_notification(self, task: TaskResponse, news_data: Dict):
        """发送新闻通知"""
        try:
            articles = news_data.get('articles', [])
            content = f"News Update - {news_data['category'].title()} Category:\n\n"
            
            for i, article in enumerate(articles[:3], 1):  # 最多显示3篇
                content += f"{i}. {article['title']}\n"
                content += f"   {article['summary']}\n"
                content += f"   Read more: {article['url']}\n\n"
            
            await self._send_notification(task, "News Update", content, news_data)
        except Exception as e:
            logger.error(f"Failed to send news notification: {e}")
    
    async def _send_weather_alert_notification(self, task: TaskResponse, alert_data: Dict):
        """发送天气预警通知"""
        try:
            alerts = alert_data.get('alerts', [])
            if alerts:
                content = f"Weather Alert for {alert_data['location']}:\n\n"
                for alert in alerts:
                    content += f"⚠️ {alert}\n"
                
                await self._send_notification(task, "Weather Alert", content, alert_data)
        except Exception as e:
            logger.error(f"Failed to send weather alert notification: {e}")
    
    async def _send_price_alert_notification(self, task: TaskResponse, price_data: Dict):
        """发送价格预警通知"""
        try:
            content = f"""
            🎉 Price Alert!
            
            The price has dropped to ${price_data['current_price']} 
            (Target: ${price_data['target_price']})
            
            Product: {price_data['product_url']}
            
            Time to buy!
            """
            
            await self._send_notification(task, "Price Alert", content, price_data)
        except Exception as e:
            logger.error(f"Failed to send price alert notification: {e}")
    
    async def _send_todo_notification(self, task: TaskResponse, todo_data: Dict):
        """发送待办提醒通知"""
        try:
            content = f"""
            📋 Todo Reminder
            
            Task: {todo_data['task_name']}
            Description: {todo_data['task_description'] or 'No description'}
            """
            
            if todo_data.get('due_date'):
                content += f"Due Date: {todo_data['due_date']}\n"
            
            await self._send_notification(task, "Todo Reminder", content, todo_data)
        except Exception as e:
            logger.error(f"Failed to send todo notification: {e}")
    
    async def _send_reminder_notification(self, task: TaskResponse, reminder_data: Dict):
        """发送提醒通知"""
        try:
            content = f"""
            🔔 Reminder
            
            {reminder_data['reminder_message']}
            
            Task: {reminder_data['task_name']}
            """
            
            await self._send_notification(task, "Reminder", content, reminder_data)
        except Exception as e:
            logger.error(f"Failed to send reminder notification: {e}")
    
    async def _send_calendar_notification(self, task: TaskResponse, calendar_data: Dict):
        """发送日历事件通知"""
        try:
            content = f"""
            📅 Calendar Event Reminder
            
            Event: {calendar_data['event_title']}
            Time: {calendar_data['event_time']}
            
            Don't forget your upcoming event!
            """
            
            await self._send_notification(task, "Calendar Reminder", content, calendar_data)
        except Exception as e:
            logger.error(f"Failed to send calendar notification: {e}")
    
    async def _send_notification(self, task: TaskResponse, subject: str, content: str, data: Dict):
        """通用通知发送方法"""
        try:
            notification_data = {
                "type": "EMAIL",
                "recipient_id": task.user_id,
                "subject": subject,
                "content": content,
                "metadata": {
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "data": data
                }
            }
            
            # 调用通知服务
            await self.communicator.call_notification_service(
                "/api/v1/notifications/send",
                notification_data,
                "POST"
            )
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
    
    # ====================
    # 服务通信扩展
    # ====================
    
    async def call_notification_service(self, endpoint: str, data: Dict = None, method: str = "GET") -> Dict:
        """调用通知服务的便捷方法"""
        return await self.communicator._call_service("notification", endpoint, data, method)
    
    # ====================
    # 清理和关闭
    # ====================
    
    async def cleanup(self):
        """清理资源"""
        try:
            logger.info("Task service cleanup completed")
        except Exception as e:
            logger.error(f"Task service cleanup failed: {e}")


# 便捷函数
def create_task_service() -> TaskService:
    """创建任务服务实例"""
    return TaskService()