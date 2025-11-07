"""
Task Service Client

Client library for other microservices to interact with task service
"""

import httpx
from core.service_discovery import get_service_discovery
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class TaskServiceClient:
    """Task Service HTTP client"""

    def __init__(self, base_url: str = None):
        """
        Initialize Task Service client

        Args:
            base_url: Task service base URL, defaults to service discovery
        """
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Use service discovery
            try:
                sd = get_service_discovery()
                self.base_url = sd.get_service_url("task_service")
            except Exception as e:
                logger.warning(f"Service discovery failed, using default: {e}")
                self.base_url = "http://localhost:8217"

        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # =============================================================================
    # Task Management
    # =============================================================================

    async def create_task(
        self,
        task_type: str,
        user_id: str,
        organization_id: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        priority: str = "normal",
        schedule_type: str = "immediate",
        scheduled_at: Optional[datetime] = None,
        cron_expression: Optional[str] = None,
        retry_policy: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[int] = None,
        parameters: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create new task

        Args:
            task_type: Type of task
            user_id: User ID who created the task
            organization_id: Organization ID (optional)
            name: Task name (optional)
            description: Task description (optional)
            priority: Task priority (low, normal, high, critical)
            schedule_type: Schedule type (immediate, scheduled, recurring)
            scheduled_at: Schedule datetime for 'scheduled' type (optional)
            cron_expression: Cron expression for 'recurring' type (optional)
            retry_policy: Retry policy configuration (optional)
            timeout_seconds: Task timeout in seconds (optional)
            parameters: Task parameters (optional)
            metadata: Additional metadata (optional)

        Returns:
            Created task data

        Example:
            >>> client = TaskServiceClient()
            >>> task = await client.create_task(
            ...     task_type="data_export",
            ...     user_id="user123",
            ...     name="Export user data",
            ...     priority="high",
            ...     schedule_type="immediate",
            ...     parameters={"format": "json"}
            ... )
        """
        try:
            payload = {
                "task_type": task_type,
                "user_id": user_id,
                "priority": priority,
                "schedule_type": schedule_type
            }

            if organization_id:
                payload["organization_id"] = organization_id
            if name:
                payload["name"] = name
            if description:
                payload["description"] = description
            if scheduled_at:
                payload["scheduled_at"] = scheduled_at.isoformat()
            if cron_expression:
                payload["cron_expression"] = cron_expression
            if retry_policy:
                payload["retry_policy"] = retry_policy
            if timeout_seconds:
                payload["timeout_seconds"] = timeout_seconds
            if parameters:
                payload["parameters"] = parameters
            if metadata:
                payload["metadata"] = metadata

            response = await self.client.post(
                f"{self.base_url}/api/v1/tasks",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create task: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            return None

    async def get_task(
        self,
        task_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get task by ID

        Args:
            task_id: Task ID

        Returns:
            Task data

        Example:
            >>> task = await client.get_task("task_123")
            >>> print(f"Status: {task['status']}")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/tasks/{task_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get task: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting task: {e}")
            return None

    async def update_task(
        self,
        task_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        scheduled_at: Optional[datetime] = None,
        parameters: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update task

        Args:
            task_id: Task ID
            name: Updated name (optional)
            description: Updated description (optional)
            priority: Updated priority (optional)
            status: Updated status (optional)
            scheduled_at: Updated schedule time (optional)
            parameters: Updated parameters (optional)
            metadata: Updated metadata (optional)

        Returns:
            Updated task data

        Example:
            >>> task = await client.update_task(
            ...     task_id="task_123",
            ...     status="cancelled"
            ... )
        """
        try:
            payload = {}

            if name:
                payload["name"] = name
            if description:
                payload["description"] = description
            if priority:
                payload["priority"] = priority
            if status:
                payload["status"] = status
            if scheduled_at:
                payload["scheduled_at"] = scheduled_at.isoformat()
            if parameters:
                payload["parameters"] = parameters
            if metadata:
                payload["metadata"] = metadata

            if not payload:
                logger.warning("No update data provided")
                return None

            response = await self.client.put(
                f"{self.base_url}/api/v1/tasks/{task_id}",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to update task: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error updating task: {e}")
            return None

    async def delete_task(
        self,
        task_id: str
    ) -> bool:
        """
        Delete task

        Args:
            task_id: Task ID

        Returns:
            True if successful

        Example:
            >>> success = await client.delete_task("task_123")
        """
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/v1/tasks/{task_id}"
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to delete task: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error deleting task: {e}")
            return False

    # =============================================================================
    # Task Execution
    # =============================================================================

    async def execute_task(
        self,
        task_id: str,
        force: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Execute task immediately

        Args:
            task_id: Task ID
            force: Force execution even if already running

        Returns:
            Task execution result

        Example:
            >>> result = await client.execute_task("task_123")
            >>> print(f"Execution status: {result['status']}")
        """
        try:
            params = {}
            if force:
                params["force"] = force

            response = await self.client.post(
                f"{self.base_url}/api/v1/tasks/{task_id}/execute",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to execute task: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error executing task: {e}")
            return None

    async def get_task_executions(
        self,
        task_id: str,
        limit: int = 50
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get task execution history

        Args:
            task_id: Task ID
            limit: Maximum results

        Returns:
            List of task executions

        Example:
            >>> executions = await client.get_task_executions("task_123")
            >>> for execution in executions:
            ...     print(f"{execution['started_at']}: {execution['status']}")
        """
        try:
            params = {"limit": limit}

            response = await self.client.get(
                f"{self.base_url}/api/v1/tasks/{task_id}/executions",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get task executions: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting task executions: {e}")
            return None

    # =============================================================================
    # Task Queries
    # =============================================================================

    async def list_tasks(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        task_type: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        List tasks with filters

        Args:
            user_id: Filter by user (optional)
            organization_id: Filter by organization (optional)
            task_type: Filter by task type (optional)
            status: Filter by status (optional)
            priority: Filter by priority (optional)
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of tasks with pagination

        Example:
            >>> result = await client.list_tasks(
            ...     user_id="user123",
            ...     status="pending",
            ...     limit=20
            ... )
            >>> for task in result['tasks']:
            ...     print(f"{task['name']}: {task['status']}")
        """
        try:
            params = {
                "limit": limit,
                "offset": offset
            }

            if user_id:
                params["user_id"] = user_id
            if organization_id:
                params["organization_id"] = organization_id
            if task_type:
                params["task_type"] = task_type
            if status:
                params["status"] = status
            if priority:
                params["priority"] = priority

            response = await self.client.get(
                f"{self.base_url}/api/v1/tasks",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list tasks: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error listing tasks: {e}")
            return None

    # =============================================================================
    # Task Templates
    # =============================================================================

    async def list_task_templates(self) -> Optional[List[Dict[str, Any]]]:
        """
        List available task templates

        Returns:
            List of task templates

        Example:
            >>> templates = await client.list_task_templates()
            >>> for template in templates:
            ...     print(f"{template['name']}: {template['description']}")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/templates"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list task templates: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error listing task templates: {e}")
            return None

    async def create_task_from_template(
        self,
        template_id: str,
        user_id: str,
        organization_id: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        schedule_type: str = "immediate",
        scheduled_at: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create task from template

        Args:
            template_id: Template ID
            user_id: User ID
            organization_id: Organization ID (optional)
            parameters: Template parameters (optional)
            schedule_type: Schedule type
            scheduled_at: Schedule time (optional)

        Returns:
            Created task

        Example:
            >>> task = await client.create_task_from_template(
            ...     template_id="data_export",
            ...     user_id="user123",
            ...     parameters={"format": "csv", "include_photos": True}
            ... )
        """
        try:
            payload = {
                "template_id": template_id,
                "user_id": user_id,
                "schedule_type": schedule_type
            }

            if organization_id:
                payload["organization_id"] = organization_id
            if parameters:
                payload["parameters"] = parameters
            if scheduled_at:
                payload["scheduled_at"] = scheduled_at.isoformat()

            response = await self.client.post(
                f"{self.base_url}/api/v1/tasks/from-template",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create task from template: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error creating task from template: {e}")
            return None

    # =============================================================================
    # Analytics & Scheduler
    # =============================================================================

    async def get_task_analytics(self) -> Optional[Dict[str, Any]]:
        """
        Get task analytics

        Returns:
            Task analytics data

        Example:
            >>> analytics = await client.get_task_analytics()
            >>> print(f"Total tasks: {analytics['total_tasks']}")
            >>> print(f"Success rate: {analytics['success_rate']}")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/analytics"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get task analytics: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting task analytics: {e}")
            return None

    async def get_pending_tasks(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get pending scheduled tasks

        Returns:
            List of pending tasks

        Example:
            >>> pending = await client.get_pending_tasks()
            >>> for task in pending:
            ...     print(f"{task['name']}: scheduled at {task['scheduled_at']}")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/scheduler/pending"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get pending tasks: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting pending tasks: {e}")
            return None

    # =============================================================================
    # Service Statistics
    # =============================================================================

    async def get_service_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get task service statistics

        Returns:
            Service statistics

        Example:
            >>> stats = await client.get_service_stats()
            >>> print(f"Total tasks: {stats['total_tasks']}")
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/service/stats"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get service stats: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting service stats: {e}")
            return None

    # =============================================================================
    # Health Check
    # =============================================================================

    async def health_check(self) -> bool:
        """
        Check service health status

        Returns:
            True if service is healthy
        """
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False


__all__ = ["TaskServiceClient"]
