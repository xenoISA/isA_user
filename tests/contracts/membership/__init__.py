"""
Membership Service - Contracts Package

This package contains the contract definitions for membership_service:
- data_contract.py: Pydantic schemas, test data factory, request builders
- logic_contract.md: Business rules, state machines, edge cases
- system_contract.md: Implementation patterns and architecture
"""

from .data_contract import (
    # Enums
    MembershipStatusContract,
    MembershipTierContract,
    PointActionContract,
    InitiatedByContract,
    # Request Contracts
    EnrollMembershipRequestContract,
    EarnPointsRequestContract,
    RedeemPointsRequestContract,
    GetMembershipRequestContract,
    CancelMembershipRequestContract,
    SuspendMembershipRequestContract,
    UseBenefitRequestContract,
    GetHistoryRequestContract,
    # Response/Entity Contracts
    MembershipContract,
    MembershipTierInfoContract,
    MembershipHistoryContract,
    TierProgressContract,
    PointsBalanceContract,
    BenefitContract,
    MembershipResponseContract,
    EnrollMembershipResponseContract,
    EarnPointsResponseContract,
    RedeemPointsResponseContract,
    PointsBalanceResponseContract,
    TierStatusResponseContract,
    BenefitListResponseContract,
    HistoryResponseContract,
    ErrorResponseContract,
    # Factory
    MembershipTestDataFactory,
    # Builders
    EnrollMembershipRequestBuilder,
    EarnPointsRequestBuilder,
    RedeemPointsRequestBuilder,
)

__all__ = [
    # Enums
    "MembershipStatusContract",
    "MembershipTierContract",
    "PointActionContract",
    "InitiatedByContract",
    # Request Contracts
    "EnrollMembershipRequestContract",
    "EarnPointsRequestContract",
    "RedeemPointsRequestContract",
    "GetMembershipRequestContract",
    "CancelMembershipRequestContract",
    "SuspendMembershipRequestContract",
    "UseBenefitRequestContract",
    "GetHistoryRequestContract",
    # Response/Entity Contracts
    "MembershipContract",
    "MembershipTierInfoContract",
    "MembershipHistoryContract",
    "TierProgressContract",
    "PointsBalanceContract",
    "BenefitContract",
    "MembershipResponseContract",
    "EnrollMembershipResponseContract",
    "EarnPointsResponseContract",
    "RedeemPointsResponseContract",
    "PointsBalanceResponseContract",
    "TierStatusResponseContract",
    "BenefitListResponseContract",
    "HistoryResponseContract",
    "ErrorResponseContract",
    # Factory
    "MembershipTestDataFactory",
    # Builders
    "EnrollMembershipRequestBuilder",
    "EarnPointsRequestBuilder",
    "RedeemPointsRequestBuilder",
]
