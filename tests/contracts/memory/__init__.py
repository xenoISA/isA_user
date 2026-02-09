"""
Memory Service Contracts

Public API for memory service data contracts.

Usage:
    from tests.contracts.memory import MemoryTestDataFactory, CreateMemoryRequest

Related Documents:
- Data Contract: tests/contracts/memory/data_contract.py
- Logic Contract: tests/contracts/memory/logic_contract.md
"""

from .data_contract import (
    # Request Schemas
    ExtractFactualMemoryRequest,
    ExtractEpisodicMemoryRequest,
    ExtractProceduralMemoryRequest,
    ExtractSemanticMemoryRequest,
    CreateMemoryRequest,
    UpdateMemoryRequest,
    StoreSessionMessageRequest,
    StoreWorkingMemoryRequest,

    # Response Schemas
    MemoryOperationResult,
    MemoryResponse,
    MemoryListResponse,
    MemoryStatisticsResponse,
    SessionContextResponse,
    UniversalSearchResponse,

    # Factory
    MemoryTestDataFactory,

    # Builders
    FactualMemoryRequestBuilder,
    SessionMemoryRequestBuilder,
)

__all__ = [
    # Request Schemas
    "ExtractFactualMemoryRequest",
    "ExtractEpisodicMemoryRequest",
    "ExtractProceduralMemoryRequest",
    "ExtractSemanticMemoryRequest",
    "CreateMemoryRequest",
    "UpdateMemoryRequest",
    "StoreSessionMessageRequest",
    "StoreWorkingMemoryRequest",

    # Response Schemas
    "MemoryOperationResult",
    "MemoryResponse",
    "MemoryListResponse",
    "MemoryStatisticsResponse",
    "SessionContextResponse",
    "UniversalSearchResponse",

    # Factory
    "MemoryTestDataFactory",

    # Builders
    "FactualMemoryRequestBuilder",
    "SessionMemoryRequestBuilder",
]
