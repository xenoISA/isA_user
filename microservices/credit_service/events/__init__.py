"""
Credit Service Event Package

Event-driven architecture for credit service:
- Publishing: Credit lifecycle events (allocated, consumed, expired, etc.)
- Subscription: User and subscription events for automatic credit allocation
"""

from .models import (
    CreditAllocatedEventData,
    CreditConsumedEventData,
    CreditExpiredEventData,
    CreditTransferredEventData,
    CreditExpiringSoonEventData,
    CampaignBudgetExhaustedEventData,
    create_credit_allocated_event_data,
    create_credit_consumed_event_data,
    create_credit_expired_event_data,
    create_credit_transferred_event_data,
    create_credit_expiring_soon_event_data,
    create_campaign_budget_exhausted_event_data,
)

from .publishers import (
    publish_credit_allocated,
    publish_credit_consumed,
    publish_credit_expired,
    publish_credit_transferred,
    publish_credit_expiring_soon,
    publish_campaign_budget_exhausted,
)

from .handlers import get_event_handlers

__all__ = [
    # Event models
    "CreditAllocatedEventData",
    "CreditConsumedEventData",
    "CreditExpiredEventData",
    "CreditTransferredEventData",
    "CreditExpiringSoonEventData",
    "CampaignBudgetExhaustedEventData",
    # Helper functions
    "create_credit_allocated_event_data",
    "create_credit_consumed_event_data",
    "create_credit_expired_event_data",
    "create_credit_transferred_event_data",
    "create_credit_expiring_soon_event_data",
    "create_campaign_budget_exhausted_event_data",
    # Publishers
    "publish_credit_allocated",
    "publish_credit_consumed",
    "publish_credit_expired",
    "publish_credit_transferred",
    "publish_credit_expiring_soon",
    "publish_campaign_budget_exhausted",
    # Handlers
    "get_event_handlers",
]
