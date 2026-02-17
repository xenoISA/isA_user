"""
Subscription Service Contracts

Data contracts, test factories, and builders for subscription_service.
"""

from .data_contract import (
    # Request Contracts
    CreateSubscriptionRequestContract,
    CancelSubscriptionRequestContract,
    ConsumeCreditsRequestContract,
    # Response Contracts
    SubscriptionResponseContract,
    CreateSubscriptionResponseContract,
    CancelSubscriptionResponseContract,
    ConsumeCreditsResponseContract,
    CreditBalanceResponseContract,
    SubscriptionListResponseContract,
    SubscriptionHistoryResponseContract,
    # Factory
    SubscriptionTestDataFactory,
    # Builders
    CreateSubscriptionRequestBuilder,
    ConsumeCreditsRequestBuilder,
    CancelSubscriptionRequestBuilder,
)

__all__ = [
    # Request Contracts
    "CreateSubscriptionRequestContract",
    "CancelSubscriptionRequestContract",
    "ConsumeCreditsRequestContract",
    # Response Contracts
    "SubscriptionResponseContract",
    "CreateSubscriptionResponseContract",
    "CancelSubscriptionResponseContract",
    "ConsumeCreditsResponseContract",
    "CreditBalanceResponseContract",
    "SubscriptionListResponseContract",
    "SubscriptionHistoryResponseContract",
    # Factory
    "SubscriptionTestDataFactory",
    # Builders
    "CreateSubscriptionRequestBuilder",
    "ConsumeCreditsRequestBuilder",
    "CancelSubscriptionRequestBuilder",
]
