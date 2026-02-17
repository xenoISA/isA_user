"""
Session Service - Data Contracts

Pydantic schemas, test data factory, and request builders for session_service.
"""

from .data_contract import (
    # Request Contracts
    SessionCreateRequestContract,
    SessionUpdateRequestContract,
    MessageCreateRequestContract,
    # Response Contracts
    SessionResponseContract,
    SessionListResponseContract,
    SessionSummaryResponseContract,
    SessionStatsResponseContract,
    MessageResponseContract,
    MessageListResponseContract,
    # Test Data Factory
    SessionTestDataFactory,
    # Request Builders
    SessionCreateRequestBuilder,
    SessionUpdateRequestBuilder,
    MessageCreateRequestBuilder,
)

__all__ = [
    # Request Contracts
    "SessionCreateRequestContract",
    "SessionUpdateRequestContract",
    "MessageCreateRequestContract",
    # Response Contracts
    "SessionResponseContract",
    "SessionListResponseContract",
    "SessionSummaryResponseContract",
    "SessionStatsResponseContract",
    "MessageResponseContract",
    "MessageListResponseContract",
    # Test Data Factory
    "SessionTestDataFactory",
    # Request Builders
    "SessionCreateRequestBuilder",
    "SessionUpdateRequestBuilder",
    "MessageCreateRequestBuilder",
]
