"""
Calendar Service Event Handlers

处理来自其他服务的事件订阅
"""

import logging
from datetime import datetime
from typing import Dict, Callable

logger = logging.getLogger(__name__)


class CalendarEventHandlers:
    """日历服务事件处理器"""

    def __init__(self, calendar_service):
        """
        初始化事件处理器

        Args:
            calendar_service: CalendarService 实例
        """
        self.service = calendar_service
        self.repository = calendar_service.repo

    def get_event_handler_map(self) -> Dict[str, Callable]:
        """
        获取事件处理器映射

        Returns:
            Dict[event_type, handler_function]
        """
        return {
            "user.deleted": self.handle_user_deleted,
            "task_service.task.created": self.handle_task_created,
            "task_service.task.completed": self.handle_task_completed,
        }

    async def handle_user_deleted(self, event_data: dict):
        """
        处理用户删除事件

        当用户被删除时，自动清理该用户的所有日历数据
        符合 GDPR Article 17: Right to Erasure

        Args:
            event_data: {
                "user_id": str,
                "timestamp": str,
                ...
            }
        """
        try:
            user_id = event_data.get("user_id")
            if not user_id:
                logger.warning("Received user.deleted event without user_id")
                return

            logger.info(f"Handling user.deleted event for user: {user_id}")

            # Delete all user calendar data
            deleted_count = await self.repository.delete_user_data(user_id)

            logger.info(
                f"✅ Successfully deleted {deleted_count} calendar records for user {user_id} "
                f"(GDPR compliance)"
            )

        except Exception as e:
            logger.error(
                f"❌ Error handling user.deleted event for user {event_data.get('user_id')}: {e}",
                exc_info=True
            )
            # Don't raise - we don't want to break the event processing chain

    async def handle_task_created(self, event_data: dict):
        """
        处理任务创建事件

        当有新任务创建且有时间安排时，自动同步到日历

        Args:
            event_data: {
                "user_id": str,
                "task_id": str,
                "task_type": str,
                "name": str,
                "schedule": str (optional),
                "due_date": str (optional),
                ...
            }
        """
        try:
            user_id = event_data.get("user_id")
            task_id = event_data.get("task_id")
            name = event_data.get("name")
            schedule = event_data.get("schedule")
            due_date = event_data.get("due_date")

            if not user_id or not task_id:
                logger.warning("task.created event missing user_id or task_id")
                return

            # Only create calendar event if task has schedule or due date
            if not schedule and not due_date:
                logger.debug(f"Task {task_id} has no schedule, skipping calendar sync")
                return

            logger.info(f"Syncing task {task_id} to calendar for user {user_id}")

            # Create calendar event from task
            from datetime import datetime, timedelta

            event_data_for_calendar = {
                "title": f"Task: {name}",
                "description": f"Task ID: {task_id}",
                "start_time": due_date or datetime.utcnow().isoformat(),
                "end_time": None,  # Tasks typically don't have end time
                "all_day": False,
                "source": "task_service",
                "source_id": task_id,
                "metadata": {
                    "task_id": task_id,
                    "task_type": event_data.get("task_type"),
                    "schedule": schedule,
                }
            }

            # Create calendar event
            await self.repository.create_event_from_task(user_id, event_data_for_calendar)

            logger.info(f"✅ Created calendar event for task {task_id}")

        except Exception as e:
            logger.error(
                f"❌ Error handling task.created event: {e}",
                exc_info=True
            )

    async def handle_task_completed(self, event_data: dict):
        """
        处理任务完成事件

        当任务完成时，更新或删除对应的日历事件

        Args:
            event_data: {
                "user_id": str,
                "task_id": str,
                "status": str,
                ...
            }
        """
        try:
            user_id = event_data.get("user_id")
            task_id = event_data.get("task_id")
            status = event_data.get("status", "completed")

            if not user_id or not task_id:
                logger.warning("task.completed event missing user_id or task_id")
                return

            logger.info(f"Updating calendar for completed task {task_id}")

            # Update calendar event to mark as completed or delete
            result = await self.repository.update_event_from_task(
                user_id=user_id,
                task_id=task_id,
                updates={
                    "status": "completed" if status == "success" else "cancelled",
                    "completed_at": datetime.utcnow().isoformat() if status == "success" else None,
                }
            )

            if result:
                logger.info(f"✅ Updated calendar event for completed task {task_id}")
            else:
                logger.debug(f"No calendar event found for task {task_id}")

        except Exception as e:
            logger.error(
                f"❌ Error handling task.completed event: {e}",
                exc_info=True
            )


__all__ = ["CalendarEventHandlers"]
