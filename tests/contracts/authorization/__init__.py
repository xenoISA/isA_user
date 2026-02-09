# Authorization Service Test Contracts

from .data_contract import (
    # Enums
    ResourceType,
    AccessLevel,
    PermissionSource,
    SubscriptionTier,
    OrganizationPlan,

    # Request Contracts
    ResourceAccessRequestContract,
    GrantPermissionRequestContract,
    RevokePermissionRequestContract,
    BulkPermissionRequestContract,
    UserPermissionsQueryContract,
    ResourcePermissionConfigContract,
    OrganizationPermissionConfigContract,

    # Response Contracts
    ResourceAccessResponseContract,
    PermissionGrantResponseContract,
    PermissionRevokeResponseContract,
    BatchOperationResultContract,
    BulkPermissionResponseContract,
    UserPermissionSummaryResponseContract,
    UserAccessibleResourceContract,
    UserAccessibleResourcesResponseContract,
    ServiceStatsResponseContract,
    HealthResponseContract,
    DetailedHealthResponseContract,
    ErrorResponseContract,
    CleanupResponseContract,

    # Factory
    AuthorizationTestDataFactory,

    # Builders
    AccessCheckRequestBuilder,
    GrantPermissionRequestBuilder,
    RevokePermissionRequestBuilder,
    BulkPermissionRequestBuilder,
)

__all__ = [
    # Enums
    "ResourceType",
    "AccessLevel",
    "PermissionSource",
    "SubscriptionTier",
    "OrganizationPlan",

    # Request Contracts
    "ResourceAccessRequestContract",
    "GrantPermissionRequestContract",
    "RevokePermissionRequestContract",
    "BulkPermissionRequestContract",
    "UserPermissionsQueryContract",
    "ResourcePermissionConfigContract",
    "OrganizationPermissionConfigContract",

    # Response Contracts
    "ResourceAccessResponseContract",
    "PermissionGrantResponseContract",
    "PermissionRevokeResponseContract",
    "BatchOperationResultContract",
    "BulkPermissionResponseContract",
    "UserPermissionSummaryResponseContract",
    "UserAccessibleResourceContract",
    "UserAccessibleResourcesResponseContract",
    "ServiceStatsResponseContract",
    "HealthResponseContract",
    "DetailedHealthResponseContract",
    "ErrorResponseContract",
    "CleanupResponseContract",

    # Factory
    "AuthorizationTestDataFactory",

    # Builders
    "AccessCheckRequestBuilder",
    "GrantPermissionRequestBuilder",
    "RevokePermissionRequestBuilder",
    "BulkPermissionRequestBuilder",
]
