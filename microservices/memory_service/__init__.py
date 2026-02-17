"""
Memory Service Package

AI-powered memory service for intelligent information storage and retrieval.
Supports multiple memory types based on cognitive science.
"""

from .models import (
    # Memory types
    MemoryType,

    # Base models
    MemoryModel,
    FactualMemory,
    ProceduralMemory,
    EpisodicMemory,
    SemanticMemory,
    WorkingMemory,
    SessionMemory,

    # Operation models
    MemoryOperationResult,
    MemoryCreateRequest,
    MemoryUpdateRequest,
    MemoryListParams,
    MemoryServiceStatus,
)

from .memory_service import MemoryService

from .client import (
    MemoryServiceClient,
    MemoryServiceSyncClient,
)

# Version
__version__ = "1.0.0"

# Package metadata
__author__ = "ISA Team"
__description__ = "AI-powered memory service for intelligent information storage and retrieval"

# Public API
__all__ = [
    # Enums
    "MemoryType",

    # Memory models
    "MemoryModel",
    "FactualMemory",
    "ProceduralMemory",
    "EpisodicMemory",
    "SemanticMemory",
    "WorkingMemory",
    "SessionMemory",

    # Operation models
    "MemoryOperationResult",
    "MemoryCreateRequest",
    "MemoryUpdateRequest",
    "MemoryListParams",
    "MemoryServiceStatus",

    # Service
    "MemoryService",

    # Clients
    "MemoryServiceClient",
    "MemoryServiceSyncClient",

    # Metadata
    "__version__",
    "__author__",
    "__description__",
]
