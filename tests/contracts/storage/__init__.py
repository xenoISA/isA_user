"""
Storage Service Contracts

Data Contract + Logic Contract for storage service testing.

Usage:
    from tests.contracts.storage.data_contract import (
        StorageTestDataFactory,
        FileUploadRequestContract,
        FileUploadResponseContract,
    )
"""

from .data_contract import (
    # Request Contracts
    FileUploadRequestContract,
    FileShareRequestContract,
    FileListRequestContract,

    # Response Contracts
    FileUploadResponseContract,
    FileInfoResponseContract,
    FileShareResponseContract,
    StorageStatsResponseContract,

    # Test Data Factory
    StorageTestDataFactory,

    # Builders
    FileUploadRequestBuilder,
    FileShareRequestBuilder,
)

__all__ = [
    # Request Contracts
    "FileUploadRequestContract",
    "FileShareRequestContract",
    "FileListRequestContract",

    # Response Contracts
    "FileUploadResponseContract",
    "FileInfoResponseContract",
    "FileShareResponseContract",
    "StorageStatsResponseContract",

    # Test Data Factory
    "StorageTestDataFactory",

    # Builders
    "FileUploadRequestBuilder",
    "FileShareRequestBuilder",
]
