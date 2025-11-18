"""
Task Service Event Publishers

Centralized event publishing functions for task service.
All events published by task service should be defined here.
"""

import logging
from typing import Optional

from core.nats_client import Event, EventType, ServiceSource

from .models import (
    create_task_completed_event_data,
    create_task_created_event_data,
    create_task_failed_event_data,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Event Publishers
# =============================================================================


async def publish_task_created(
    event_bus,
    user_id: str,
    task_id: str,
    task_type: str,
    name: str,
    schedule: Optional[str] = None,
) -> bool:
    """
    Publish task.created event

    Notifies other services that a new task has been created.

    Args:
        event_bus: NATS event bus instance
        user_id: User ID who created the task
        task_id: Task ID
        task_type: Task type (todo, reminder, scheduled, etc.)
        name: Task name/title
        schedule: Optional schedule expression

    Returns:
        True if event published successfully, False otherwise

    Subscribers:
        - notification_service: Notify user about task creation
        - calendar_service: Sync task to calendar if scheduled
    """
    try:
        event_data = create_task_created_event_data(
            user_id=user_id,
            task_id=task_id,
            task_type=task_type,
            name=name,
            schedule=schedule,
        )

        event = Event(
            event_type=EventType.TASK_CREATED,
            source=ServiceSource.TASK_SERVICE,
            data=event_data.model_dump(),
        )

        # Override with specific event type
        event.type = "task.created"

        result = await event_bus.publish_event(event)

        if result:
            logger.info(f" Published task.created event for task {task_id}")
        else:
            logger.error(f"L Failed to publish task.created event for task {task_id}")

        return result

    except Exception as e:
        logger.error(f"Error publishing task.created event: {e}", exc_info=True)
        return False


async def publish_task_completed(
    event_bus,
    user_id: str,
    task_id: str,
    execution_id: str,
    task_type: str,
    status: str,
    credits_consumed: Optional[float] = None,
    duration_seconds: Optional[float] = None,
) -> bool:
    """
    Publish task.completed event

    Notifies when a task execution completes.

    Args:
        event_bus: NATS event bus instance
        user_id: User ID
        task_id: Task ID
        execution_id: Execution ID
        task_type: Task type
        status: Execution status (success, failed)
        credits_consumed: Credits consumed by this execution
        duration_seconds: Task duration in seconds

    Returns:
        True if event published successfully, False otherwise

    Subscribers:
        - notification_service: Notify user about completion
        - analytics_service: Track task execution metrics
        - billing_service: Process credit consumption
    """
    try:
        event_data = create_task_completed_event_data(
            user_id=user_id,
            task_id=task_id,
            execution_id=execution_id,
            task_type=task_type,
            status=status,
            credits_consumed=credits_consumed,
            duration_seconds=duration_seconds,
        )

        event = Event(
            event_type=EventType.TASK_COMPLETED,
            source=ServiceSource.TASK_SERVICE,
            data=event_data.model_dump(),
        )

        # Override with specific event type
        event.type = "task.completed"

        result = await event_bus.publish_event(event)

        if result:
            logger.info(
                f" Published task.completed event for task {task_id}, execution {execution_id}"
            )
        else:
            logger.error(
                f"L Failed to publish task.completed event for task {task_id}"
            )

        return result

    except Exception as e:
        logger.error(f"Error publishing task.completed event: {e}", exc_info=True)
        return False


async def publish_task_failed(
    event_bus,
    user_id: str,
    task_id: str,
    execution_id: str,
    task_type: str,
    error_message: str,
    retry_count: Optional[int] = None,
) -> bool:
    """
    Publish task.failed event

    Notifies when a task execution fails.

    Args:
        event_bus: NATS event bus instance
        user_id: User ID
        task_id: Task ID
        execution_id: Execution ID
        task_type: Task type
        error_message: Error message
        retry_count: Number of retries attempted

    Returns:
        True if event published successfully, False otherwise

    Subscribers:
        - notification_service: Alert user about failure
        - monitoring_service: Track failures for alerting
    """
    try:
        event_data = create_task_failed_event_data(
            user_id=user_id,
            task_id=task_id,
            execution_id=execution_id,
            task_type=task_type,
            error_message=error_message,
            retry_count=retry_count,
        )

        event = Event(
            event_type=EventType.TASK_FAILED,
            source=ServiceSource.TASK_SERVICE,
            data=event_data.model_dump(),
        )

        # Override with specific event type
        event.type = "task.failed"

        result = await event_bus.publish_event(event)

        if result:
            logger.warning(
                f"   Published task.failed event for task {task_id}, execution {execution_id}"
            )
        else:
            logger.error(
                f"L Failed to publish task.failed event for task {task_id}"
            )

        return result

    except Exception as e:
        logger.error(f"Error publishing task.failed event: {e}", exc_info=True)
        return False


__all__ = [
    "publish_task_created",
    "publish_task_completed",
    "publish_task_failed",
]
