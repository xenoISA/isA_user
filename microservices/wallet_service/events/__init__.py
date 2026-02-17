"""
Wallet Service Event Handling

This module contains event subscribers and handlers for the wallet service.

Standard Structure:
- models.py: Event data models (Pydantic)
- handlers.py: Event handlers (subscribe to events from other services)
- publishers.py: Event publishers (publish events to other services)
"""

# Event Handlers
from .handlers import (
    # BillingCalculatedEventHandler,  # Legacy handler class - removed (not in handlers.py)
    get_event_handlers,
    handle_billing_calculated,
    handle_payment_completed,
    handle_user_created,
)

# Event Models
from .models import (
    BillingCalculatedEventData,
    TokensDeductedEventData,
    TokensInsufficientEventData,
)

# Event Publishers
from .publishers import (
    publish_balance_low_warning,
    publish_deposit_completed,
    publish_tokens_deducted,
    publish_tokens_insufficient,
    publish_wallet_created,
)

__all__ = [
    # Event Handlers
    # "BillingCalculatedEventHandler",  # Legacy - removed
    "get_event_handlers",
    "handle_billing_calculated",
    "handle_payment_completed",
    "handle_user_created",
    # Event Publishers
    "publish_balance_low_warning",
    "publish_deposit_completed",
    "publish_tokens_deducted",
    "publish_tokens_insufficient",
    "publish_wallet_created",
    # Event Models
    "BillingCalculatedEventData",
    "TokensDeductedEventData",
    "TokensInsufficientEventData",
]
