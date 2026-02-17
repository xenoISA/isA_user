"""
Auth Service Event Handlers

Handle incoming events from other services.
Following wallet_service pattern.
"""

import logging
from typing import Dict, Any, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from ..auth_service import AuthenticationService
    from ..device_auth_service import DeviceAuthService

logger = logging.getLogger(__name__)

# Track processed events to prevent duplicate processing
_processed_events: Set[str] = set()


def _is_event_processed(event_id: str) -> bool:
    """Check if event has been processed"""
    return event_id in _processed_events


def _mark_event_processed(event_id: str):
    """Mark event as processed"""
    _processed_events.add(event_id)
    # Keep only last 10000 events to prevent memory leak
    if len(_processed_events) > 10000:
        _processed_events.clear()


# ============================================================================
# Event Handler Registration
# ============================================================================

def get_event_handlers(auth_service, device_auth_service, event_bus):
    """
    Get event handlers for auth service
    
    Args:
        auth_service: AuthenticationService instance
        device_auth_service: DeviceAuthService instance
        event_bus: Event bus instance
        
    Returns:
        Dict of event type to handler function
    """
    
    # Currently auth_service doesn't need to subscribe to other service events
    # for device pairing. All pairing logic is initiated by API calls.
    
    # If needed in the future, add handlers here:
    # handlers = {
    #     "device.registered": handle_device_registered,
    #     "user.deleted": handle_user_deleted,
    # }
    
    handlers = {}
    
    logger.info("Auth service event handlers registered")
    return handlers


# ============================================================================
# Example Event Handlers (for future use)
# ============================================================================

async def handle_device_registered(
    event_data: Dict[str, Any],
    auth_service,
    device_auth_service,
    event_bus
):
    """
    Handle device.registered event
    
    This is an example handler that could be used if auth_service
    needs to react to device registration events.
    """
    try:
        event_id = event_data.get("event_id")
        if _is_event_processed(event_id):
            logger.debug(f"Event {event_id} already processed, skipping")
            return
            
        device_id = event_data.get("device_id")
        logger.info(f"Handling device.registered event for device {device_id}")
        
        # Process the event
        # ...
        
        _mark_event_processed(event_id)
        
    except Exception as e:
        logger.error(f"Error handling device.registered event: {e}", exc_info=True)
