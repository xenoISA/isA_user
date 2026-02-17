"""
Calendar Service Client

Client for task_service to interact with calendar_service.
Used for syncing tasks with calendar events.
"""

import os
import sys
from typing import Optional, Dict, Any, List
from datetime import datetime

# Add parent directories to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from microservices.calendar_service.client import CalendarServiceClient


class CalendarClient:
    """
    Wrapper client for Calendar Service calls from Task Service.

    This wrapper provides task-specific convenience methods
    while delegating to the actual CalendarServiceClient.
    """

    def __init__(self, base_url: str = None):
        """
        Initialize Calendar Service client

        Args:
            base_url: Calendar service base URL (optional, uses service discovery)
        """
        self._client = CalendarServiceClient(base_url=base_url)

    async def close(self):
        """Close HTTP client"""
        await self._client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # =============================================================================
    # Task-specific convenience methods
    # =============================================================================

    async def create_task_event(
        self,
        user_id: str,
        task_id: str,
        task_name: str,
        due_date: datetime,
        duration_minutes: int = 60,
        description: Optional[str] = None,
        reminders: List[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a calendar event for a task.

        Args:
            user_id: User ID
            task_id: Task ID for reference
            task_name: Task name (event title)
            due_date: Task due date (event start time)
            duration_minutes: Event duration in minutes
            description: Task description
            reminders: Reminder times in minutes before event

        Returns:
            Created calendar event or None
        """
        try:
            from datetime import timedelta

            end_time = due_date + timedelta(minutes=duration_minutes)

            event = await self._client.create_event(
                user_id=user_id,
                title=f"Task: {task_name}",
                start_time=due_date,
                end_time=end_time,
                description=description or f"Task due: {task_name}",
                category="task",
                reminders=reminders or [15, 60],  # Default: 15 min and 1 hour before
                metadata={"task_id": task_id, "source": "task_service"}
            )
            return event
        except Exception:
            return None

    async def update_task_event(
        self,
        user_id: str,
        event_id: str,
        task_name: Optional[str] = None,
        due_date: Optional[datetime] = None,
        duration_minutes: Optional[int] = None,
        description: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update a calendar event for a task.

        Args:
            user_id: User ID
            event_id: Calendar event ID
            task_name: Updated task name
            due_date: Updated due date
            duration_minutes: Updated duration
            description: Updated description

        Returns:
            Updated calendar event or None
        """
        try:
            updates = {}

            if task_name:
                updates["title"] = f"Task: {task_name}"
            if due_date:
                from datetime import timedelta
                updates["start_time"] = due_date.isoformat()
                if duration_minutes:
                    updates["end_time"] = (due_date + timedelta(minutes=duration_minutes)).isoformat()
            if description:
                updates["description"] = description

            if not updates:
                return None

            return await self._client.update_event(
                user_id=user_id,
                event_id=event_id,
                **updates
            )
        except Exception:
            return None

    async def delete_task_event(self, user_id: str, event_id: str) -> bool:
        """
        Delete a calendar event for a completed/deleted task.

        Args:
            user_id: User ID
            event_id: Calendar event ID

        Returns:
            True if deleted successfully
        """
        try:
            return await self._client.delete_event(
                user_id=user_id,
                event_id=event_id
            )
        except Exception:
            return False

    async def get_upcoming_tasks_from_calendar(
        self,
        user_id: str,
        hours_ahead: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get upcoming task events from calendar.

        Args:
            user_id: User ID
            hours_ahead: Hours ahead to look

        Returns:
            List of upcoming task events
        """
        try:
            from datetime import timedelta

            start = datetime.utcnow()
            end = start + timedelta(hours=hours_ahead)

            events = await self._client.get_events(
                user_id=user_id,
                start_time=start,
                end_time=end,
                category="task"
            )

            if events:
                return events.get("events", [])
            return []
        except Exception:
            return []

    # =============================================================================
    # Direct delegation to CalendarServiceClient
    # =============================================================================

    async def get_event(self, user_id: str, event_id: str):
        """Get calendar event by ID"""
        return await self._client.get_event(user_id, event_id)

    async def health_check(self) -> bool:
        """Check Calendar Service health"""
        return await self._client.health_check()


__all__ = ["CalendarClient"]
