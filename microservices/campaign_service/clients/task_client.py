"""
Task Service Client

Client for calling task_service to schedule campaign execution.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class TaskClient:
    """Client for task_service"""

    def __init__(self, config: Optional[ConfigManager] = None):
        if config is None:
            config = ConfigManager("campaign_service")

        host, port = config.discover_service(
            service_name='task_service',
            default_host='localhost',
            default_port=8260,
            env_host_key='TASK_SERVICE_HOST',
            env_port_key='TASK_SERVICE_PORT'
        )
        self.base_url = f"http://{host}:{port}"
        self.timeout = 30.0

    async def create_task(
        self,
        task_type: str,
        payload: Dict[str, Any],
        scheduled_at: datetime,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Create a scheduled task.

        Args:
            task_type: Type of task (e.g., "campaign.execute")
            payload: Task payload data
            scheduled_at: When to execute the task
            **kwargs: Additional task parameters

        Returns:
            Task creation response with task_id
        """
        try:
            request_data = {
                "task_type": task_type,
                "payload": payload,
                "scheduled_at": scheduled_at.isoformat(),
                **kwargs,
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/tasks",
                    json=request_data,
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Error creating task: {e.response.text}")
            raise

        except Exception as e:
            logger.error(f"Error creating task: {e}")
            raise

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a scheduled task.

        Args:
            task_id: ID of task to cancel

        Returns:
            True if cancelled successfully
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(
                    f"{self.base_url}/api/v1/tasks/{task_id}"
                )

                if response.status_code == 404:
                    logger.warning(f"Task not found: {task_id}")
                    return False

                response.raise_for_status()
                return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Error cancelling task: {e.response.text}")
            return False

        except Exception as e:
            logger.error(f"Error cancelling task {task_id}: {e}")
            return False

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task data or None if not found
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/tasks/{task_id}"
                )

                if response.status_code == 404:
                    return None

                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(f"Error getting task {task_id}: {e}")
            return None

    async def reschedule_task(
        self,
        task_id: str,
        scheduled_at: datetime,
    ) -> Optional[Dict[str, Any]]:
        """
        Reschedule a task.

        Args:
            task_id: Task ID
            scheduled_at: New scheduled time

        Returns:
            Updated task data
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.patch(
                    f"{self.base_url}/api/v1/tasks/{task_id}",
                    json={"scheduled_at": scheduled_at.isoformat()},
                )

                if response.status_code == 404:
                    logger.warning(f"Task not found: {task_id}")
                    return None

                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(f"Error rescheduling task {task_id}: {e}")
            return None

    async def health_check(self) -> bool:
        """Check if task_service is healthy"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception:
            return False


__all__ = ["TaskClient"]
