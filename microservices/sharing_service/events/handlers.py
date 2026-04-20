"""
Sharing Service Event Handlers

Handles events from other services relevant to sharing.
"""

import logging
from typing import Callable, Dict

logger = logging.getLogger(__name__)


class SharingEventHandlers:
    """Event handlers for sharing service"""

    def __init__(self, sharing_service):
        self.sharing_service = sharing_service

    def get_event_handler_map(self) -> Dict[str, Callable]:
        """
        Get mapping of event patterns to handler functions.

        Currently handles:
        - session_service.session.ended: could clean up shares for ended sessions
        """
        return {
            # Future: clean up shares when a session is deleted
            # "session_service.session.ended": lambda event: self.handle_session_ended(event.data),
        }
