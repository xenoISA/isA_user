"""
Calendar Service Event Handlers

处理来自其他服务的事件订阅
"""

import logging
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
        self.repository = calendar_service.repository

    def get_event_handler_map(self) -> Dict[str, Callable]:
        """
        获取事件处理器映射

        Returns:
            Dict[event_type, handler_function]
        """
        return {
            "user.deleted": self.handle_user_deleted,
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


__all__ = ["CalendarEventHandlers"]
