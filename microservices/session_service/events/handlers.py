"""
Session Service Event Handlers

Handles events from other services to maintain session data consistency
"""

import logging
from typing import Dict, Callable

logger = logging.getLogger(__name__)


class SessionEventHandlers:
    """Event handlers for session service"""

    def __init__(self, session_service):
        """
        Initialize event handlers

        Args:
            session_service: Instance of SessionService
        """
        self.session_service = session_service
        self.repository = session_service.session_repo

    def get_event_handler_map(self) -> Dict[str, Callable]:
        """
        Get mapping of event patterns to handler functions

        Uses the new event bus API with service-prefixed event patterns.

        Returns:
            Dictionary mapping event patterns to handler functions
        """
        return {
            "account_service.user.deleted": lambda event: self.handle_user_deleted(event.data),
        }

    async def handle_user_deleted(self, event_data: dict):
        """
        Handle user.deleted event - cleanup all sessions for deleted user

        Event data expected:
        {
            "user_id": "user123",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        """
        try:
            user_id = event_data.get("user_id")
            if not user_id:
                logger.error("user.deleted event missing user_id")
                return

            logger.info(f"Handling user.deleted event for user: {user_id}")

            # Get all user sessions
            sessions = await self.repository.get_user_sessions(
                user_id=user_id,
                active_only=False  # Get all sessions
            )

            if not sessions:
                logger.info(f"No sessions found for deleted user {user_id}")
                return

            # End all active sessions
            ended_count = 0
            for session in sessions:
                try:
                    if session.status == "active":
                        # End the session
                        success = await self.repository.end_session(session.session_id)
                        if success:
                            ended_count += 1
                            logger.debug(f"Ended session: {session.session_id}")
                except Exception as e:
                    logger.error(f"Failed to end session {session.session_id}: {e}")

            # Optionally, mark sessions for deletion or anonymize them
            # For now, we just end active sessions
            logger.info(f"Ended {ended_count} active sessions for deleted user {user_id}")

        except Exception as e:
            logger.error(f"Error handling user.deleted event: {e}")
