"""
Task Service Event Publishers

Centralized event publishing functions for task service.
All events published by task service should be defined here.
"""

import logging
from typing import Optional

from core.nats_client import Event

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
            event_type="task.created",
            source="task_service",
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
            event_type="task.completed",
            source="task_service",
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


async def publish_task_assigned(
    event_bus,
    user_id: str,
    task_id: str,
    assigned_to: str,
    assigned_by: str,
    name: str,
    due_date: Optional[str] = None,
) -> bool:
    """
    Publish task.assigned event

    Notifies when a task is assigned to a user.

    Args:
        event_bus: NATS event bus instance
        user_id: Owner user ID
        task_id: Task ID
        assigned_to: User ID task is assigned to
        assigned_by: User ID who assigned the task
        name: Task name/title
        due_date: Optional due date

    Returns:
        True if event published successfully, False otherwise

    Subscribers:
        - notification_service: Notify assignee about new task
        - calendar_service: Add to assignee's calendar
    """
    try:
        event_data = {
            "user_id": user_id,
            "task_id": task_id,
            "assigned_to": assigned_to,
            "assigned_by": assigned_by,
            "name": name,
            "due_date": due_date,
        }

        event = Event(
            event_type="task.created",  # Reuse enum, but override type
            source="task_service",
            data=event_data,
        )

        event.type = "task.assigned"

        result = await event_bus.publish_event(event)

        if result:
            logger.info(f"✅ Published task.assigned event for task {task_id} to {assigned_to}")
        else:
            logger.error(f"❌ Failed to publish task.assigned event for task {task_id}")

        return result

    except Exception as e:
        logger.error(f"Error publishing task.assigned event: {e}", exc_info=True)
        return False


async def publish_task_due_soon(
    event_bus,
    user_id: str,
    task_id: str,
    name: str,
    due_date: str,
    hours_until_due: int,
) -> bool:
    """
    Publish task.due_soon event

    Notifies when a task is approaching its due date.

    Args:
        event_bus: NATS event bus instance
        user_id: User ID
        task_id: Task ID
        name: Task name/title
        due_date: Due date ISO string
        hours_until_due: Hours until task is due

    Returns:
        True if event published successfully, False otherwise

    Subscribers:
        - notification_service: Send reminder to user
    """
    try:
        event_data = {
            "user_id": user_id,
            "task_id": task_id,
            "name": name,
            "due_date": due_date,
            "hours_until_due": hours_until_due,
        }

        event = Event(
            event_type="task.created",  # Reuse enum, but override type
            source="task_service",
            data=event_data,
        )

        event.type = "task.due_soon"

        result = await event_bus.publish_event(event)

        if result:
            logger.info(f"✅ Published task.due_soon event for task {task_id} ({hours_until_due}h)")
        else:
            logger.error(f"❌ Failed to publish task.due_soon event for task {task_id}")

        return result

    except Exception as e:
        logger.error(f"Error publishing task.due_soon event: {e}", exc_info=True)
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
            event_type="task.failed",
            source="task_service",
            data=event_data.model_dump(),
        )

        # Override with specific event type
        event.type = "task.failed"

        result = await event_bus.publish_event(event)

        if result:
            logger.warning(
                f"�  Published task.failed event for task {task_id}, execution {execution_id}"
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
    "publish_task_assigned",
    "publish_task_due_soon",
    "publish_task_failed",
]
