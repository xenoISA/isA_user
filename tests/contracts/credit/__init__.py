"""
Credit Service Contracts

This module provides the contracts for credit_service testing.
"""

from .data_contract import (
    # Enums
    CreditTypeEnum,
    TransactionTypeEnum,
    AllocationStatusEnum,
    ExpirationPolicyEnum,
    ReferenceTypeEnum,
    # Request Contracts
    CreateAccountRequestContract,
    AllocateCreditsRequestContract,
    ConsumeCreditsRequestContract,
    CheckAvailabilityRequestContract,
    TransferCreditsRequestContract,
    CreateCampaignRequestContract,
    TransactionQueryRequestContract,
    BalanceQueryRequestContract,
    # Response Contracts
    CreditAccountResponseContract,
    CreditBalanceSummaryContract,
    AllocationResponseContract,
    ConsumptionResponseContract,
    ConsumptionTransactionContract,
    AvailabilityResponseContract,
    TransferResponseContract,
    CreditTransactionResponseContract,
    CreditCampaignResponseContract,
    CreditStatisticsResponseContract,
    HealthCheckResponseContract,
    DetailedHealthCheckResponseContract,
    ErrorResponseContract,
    # Factory
    CreditTestDataFactory,
    # Builders
    AllocateCreditsRequestBuilder,
    ConsumeCreditsRequestBuilder,
    CreateCampaignRequestBuilder,
    TransferCreditsRequestBuilder,
)

__all__ = [
    # Enums
    "CreditTypeEnum",
    "TransactionTypeEnum",
    "AllocationStatusEnum",
    "ExpirationPolicyEnum",
    "ReferenceTypeEnum",
    # Request Contracts
    "CreateAccountRequestContract",
    "AllocateCreditsRequestContract",
    "ConsumeCreditsRequestContract",
    "CheckAvailabilityRequestContract",
    "TransferCreditsRequestContract",
    "CreateCampaignRequestContract",
    "TransactionQueryRequestContract",
    "BalanceQueryRequestContract",
    # Response Contracts
    "CreditAccountResponseContract",
    "CreditBalanceSummaryContract",
    "AllocationResponseContract",
    "ConsumptionResponseContract",
    "ConsumptionTransactionContract",
    "AvailabilityResponseContract",
    "TransferResponseContract",
    "CreditTransactionResponseContract",
    "CreditCampaignResponseContract",
    "CreditStatisticsResponseContract",
    "HealthCheckResponseContract",
    "DetailedHealthCheckResponseContract",
    "ErrorResponseContract",
    # Factory
    "CreditTestDataFactory",
    # Builders
    "AllocateCreditsRequestBuilder",
    "ConsumeCreditsRequestBuilder",
    "CreateCampaignRequestBuilder",
    "TransferCreditsRequestBuilder",
]
