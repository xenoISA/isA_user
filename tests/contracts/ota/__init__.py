"""
OTA Service Data Contracts

Exports all contracts and test data factories for OTA service testing.
"""

from tests.contracts.ota.data_contract import (
    # Enums
    UpdateType,
    UpdateStatus,
    DeploymentStrategy,
    Priority,
    RollbackTrigger,
    CampaignStatus,

    # Request Contracts
    FirmwareUploadRequestContract,
    FirmwareQueryRequestContract,
    CampaignCreateRequestContract,
    CampaignUpdateRequestContract,
    CampaignQueryRequestContract,
    DeviceUpdateRequestContract,
    BulkDeviceUpdateRequestContract,
    RollbackRequestContract,

    # Response Contracts
    FirmwareResponseContract,
    FirmwareListResponseContract,
    FirmwareDownloadResponseContract,
    CampaignResponseContract,
    CampaignListResponseContract,
    DeviceUpdateResponseContract,
    DeviceUpdateListResponseContract,
    RollbackResponseContract,
    OTAStatsResponseContract,
    ErrorResponseContract,

    # Factories
    OTATestDataFactory,

    # Builders
    FirmwareUploadRequestBuilder,
    CampaignCreateRequestBuilder,
    DeviceUpdateRequestBuilder,

    # Validators
    OTAValidators,
)

__all__ = [
    # Enums
    'UpdateType',
    'UpdateStatus',
    'DeploymentStrategy',
    'Priority',
    'RollbackTrigger',
    'CampaignStatus',

    # Request Contracts
    'FirmwareUploadRequestContract',
    'FirmwareQueryRequestContract',
    'CampaignCreateRequestContract',
    'CampaignUpdateRequestContract',
    'CampaignQueryRequestContract',
    'DeviceUpdateRequestContract',
    'BulkDeviceUpdateRequestContract',
    'RollbackRequestContract',

    # Response Contracts
    'FirmwareResponseContract',
    'FirmwareListResponseContract',
    'FirmwareDownloadResponseContract',
    'CampaignResponseContract',
    'CampaignListResponseContract',
    'DeviceUpdateResponseContract',
    'DeviceUpdateListResponseContract',
    'RollbackResponseContract',
    'OTAStatsResponseContract',
    'ErrorResponseContract',

    # Factories
    'OTATestDataFactory',

    # Builders
    'FirmwareUploadRequestBuilder',
    'CampaignCreateRequestBuilder',
    'DeviceUpdateRequestBuilder',

    # Validators
    'OTAValidators',
]
