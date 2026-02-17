"""
Document Service Contracts

Data contracts, logic contracts, and test data factories for document_service testing.
"""

from .data_contract import (
    # Request Contracts
    DocumentCreateRequestContract,
    DocumentUpdateRequestContract,
    DocumentPermissionUpdateRequestContract,
    RAGQueryRequestContract,
    SemanticSearchRequestContract,
    DocumentListParamsContract,
    # Response Contracts
    DocumentResponseContract,
    DocumentPermissionResponseContract,
    RAGQueryResponseContract,
    SemanticSearchResponseContract,
    SearchResultItemContract,
    DocumentStatsResponseContract,
    DocumentServiceStatusContract,
    # Factory
    DocumentTestDataFactory,
    # Builders
    DocumentCreateRequestBuilder,
    DocumentUpdateRequestBuilder,
    DocumentPermissionUpdateRequestBuilder,
    RAGQueryRequestBuilder,
)

__all__ = [
    # Request Contracts
    "DocumentCreateRequestContract",
    "DocumentUpdateRequestContract",
    "DocumentPermissionUpdateRequestContract",
    "RAGQueryRequestContract",
    "SemanticSearchRequestContract",
    "DocumentListParamsContract",
    # Response Contracts
    "DocumentResponseContract",
    "DocumentPermissionResponseContract",
    "RAGQueryResponseContract",
    "SemanticSearchResponseContract",
    "SearchResultItemContract",
    "DocumentStatsResponseContract",
    "DocumentServiceStatusContract",
    # Factory
    "DocumentTestDataFactory",
    # Builders
    "DocumentCreateRequestBuilder",
    "DocumentUpdateRequestBuilder",
    "DocumentPermissionUpdateRequestBuilder",
    "RAGQueryRequestBuilder",
]
