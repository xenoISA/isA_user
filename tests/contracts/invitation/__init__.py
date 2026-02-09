"""
Invitation Service Contracts Package

Data contracts, test factories, and request builders for invitation_service testing.
"""

from .data_contract import (
    # Enums
    InvitationStatus,
    OrganizationRole,

    # Request Contracts
    InvitationCreateRequestContract,
    InvitationAcceptRequestContract,
    InvitationResendRequestContract,
    InvitationCancelRequestContract,
    InvitationListParamsContract,
    InvitationBulkExpireRequestContract,

    # Response Contracts
    InvitationResponseContract,
    InvitationDetailResponseContract,
    InvitationListResponseContract,
    AcceptInvitationResponseContract,
    InvitationCreateResponseContract,
    InvitationStatsResponseContract,
    InvitationHealthResponseContract,
    InvitationServiceInfoContract,
    ErrorResponseContract,

    # Factory
    InvitationTestDataFactory,

    # Builders
    InvitationCreateRequestBuilder,
    InvitationAcceptRequestBuilder,
    InvitationListParamsBuilder,
)

__all__ = [
    # Enums
    "InvitationStatus",
    "OrganizationRole",

    # Request Contracts
    "InvitationCreateRequestContract",
    "InvitationAcceptRequestContract",
    "InvitationResendRequestContract",
    "InvitationCancelRequestContract",
    "InvitationListParamsContract",
    "InvitationBulkExpireRequestContract",

    # Response Contracts
    "InvitationResponseContract",
    "InvitationDetailResponseContract",
    "InvitationListResponseContract",
    "AcceptInvitationResponseContract",
    "InvitationCreateResponseContract",
    "InvitationStatsResponseContract",
    "InvitationHealthResponseContract",
    "InvitationServiceInfoContract",
    "ErrorResponseContract",

    # Factory
    "InvitationTestDataFactory",

    # Builders
    "InvitationCreateRequestBuilder",
    "InvitationAcceptRequestBuilder",
    "InvitationListParamsBuilder",
]
