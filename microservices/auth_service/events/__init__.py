"""
Auth Service Events Module

Event-driven architecture for authentication and device pairing events.
Follows the standard wallet_service pattern.
"""

from .handlers import get_event_handlers
from .models import (
    DevicePairingTokenGeneratedEventData,
    DevicePairingTokenVerifiedEventData,
    DevicePairingCompletedEventData,
    create_pairing_token_generated_event_data,
    create_pairing_token_verified_event_data,
    create_pairing_completed_event_data,
)
from .publishers import (
    publish_device_pairing_token_generated,
    publish_device_pairing_token_verified,
    publish_device_pairing_completed,
)

__all__ = [
    # Handlers
    'get_event_handlers',
    
    # Models
    'DevicePairingTokenGeneratedEventData',
    'DevicePairingTokenVerifiedEventData',
    'DevicePairingCompletedEventData',
    'create_pairing_token_generated_event_data',
    'create_pairing_token_verified_event_data',
    'create_pairing_completed_event_data',
    
    # Publishers
    'publish_device_pairing_token_generated',
    'publish_device_pairing_token_verified',
    'publish_device_pairing_completed',
]
