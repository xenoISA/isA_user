"""
Organization Service Contracts

Data contracts, test data factory, and request builders for organization_service.
"""

from .data_contract import (
    # Request Contracts
    OrganizationCreateRequestContract,
    OrganizationUpdateRequestContract,
    OrganizationMemberAddRequestContract,
    OrganizationMemberUpdateRequestContract,
    OrganizationContextSwitchRequestContract,
    SharingCreateRequestContract,
    SharingUpdateRequestContract,
    MemberPermissionUpdateRequestContract,
    # Response Contracts
    OrganizationResponseContract,
    OrganizationMemberResponseContract,
    OrganizationListResponseContract,
    OrganizationMemberListResponseContract,
    OrganizationContextResponseContract,
    OrganizationStatsResponseContract,
    SharingResourceResponseContract,
    MemberSharingPermissionResponseContract,
    # Factory
    OrganizationTestDataFactory,
    # Builders
    OrganizationCreateRequestBuilder,
    OrganizationMemberAddRequestBuilder,
    SharingCreateRequestBuilder,
)

__all__ = [
    # Request Contracts
    "OrganizationCreateRequestContract",
    "OrganizationUpdateRequestContract",
    "OrganizationMemberAddRequestContract",
    "OrganizationMemberUpdateRequestContract",
    "OrganizationContextSwitchRequestContract",
    "SharingCreateRequestContract",
    "SharingUpdateRequestContract",
    "MemberPermissionUpdateRequestContract",
    # Response Contracts
    "OrganizationResponseContract",
    "OrganizationMemberResponseContract",
    "OrganizationListResponseContract",
    "OrganizationMemberListResponseContract",
    "OrganizationContextResponseContract",
    "OrganizationStatsResponseContract",
    "SharingResourceResponseContract",
    "MemberSharingPermissionResponseContract",
    # Factory
    "OrganizationTestDataFactory",
    # Builders
    "OrganizationCreateRequestBuilder",
    "OrganizationMemberAddRequestBuilder",
    "SharingCreateRequestBuilder",
]
