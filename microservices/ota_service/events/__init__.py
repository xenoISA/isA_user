"""
OTA Service Events

Exports event models, publishers, and handlers
"""

from .handlers import OTAEventHandler
from .models import (
    FirmwareUploadedEvent,
    CampaignCreatedEvent,
    CampaignStartedEvent,
    UpdateCancelledEvent,
    RollbackInitiatedEvent
)
from .publishers import (
    publish_firmware_uploaded,
    publish_campaign_created,
    publish_campaign_started,
    publish_update_cancelled,
    publish_rollback_initiated
)

__all__ = [
    # Handler
    'OTAEventHandler',
    # Models
    'FirmwareUploadedEvent',
    'CampaignCreatedEvent',
    'CampaignStartedEvent',
    'UpdateCancelledEvent',
    'RollbackInitiatedEvent',
    # Publishers
    'publish_firmware_uploaded',
    'publish_campaign_created',
    'publish_campaign_started',
    'publish_update_cancelled',
    'publish_rollback_initiated',
]
