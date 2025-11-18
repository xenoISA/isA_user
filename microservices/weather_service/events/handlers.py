"""
Weather Service Event Handlers

Handles events from other services.
Weather service primarily publishes events and doesn't subscribe to many external events.
"""

import logging

logger = logging.getLogger(__name__)


def get_event_handlers(weather_service, event_bus):
    """
    Get event handlers for weather service
    
    Args:
        weather_service: WeatherService instance
        event_bus: NATS event bus instance
        
    Returns:
        Dictionary mapping event patterns to handler functions
    """
    # Weather service primarily publishes events
    # Add handlers here if needed to react to other services' events
    return {}
