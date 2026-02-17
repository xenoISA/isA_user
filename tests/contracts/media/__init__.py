"""
Media Service Test Contracts

Exports all contracts for easy importing in tests.
"""

from .data_contract import (
    # Request Contracts
    PhotoVersionCreateRequestContract,
    PlaylistCreateRequestContract,
    PlaylistUpdateRequestContract,
    RotationScheduleCreateRequestContract,

    # Response Contracts
    PhotoVersionResponseContract,
    PhotoMetadataResponseContract,
    PlaylistResponseContract,
    RotationScheduleResponseContract,
    PhotoCacheResponseContract,

    # Factory
    MediaTestDataFactory,

    # Builders
    PlaylistRequestBuilder,
)

__all__ = [
    # Request Contracts
    "PhotoVersionCreateRequestContract",
    "PlaylistCreateRequestContract",
    "PlaylistUpdateRequestContract",
    "RotationScheduleCreateRequestContract",

    # Response Contracts
    "PhotoVersionResponseContract",
    "PhotoMetadataResponseContract",
    "PlaylistResponseContract",
    "RotationScheduleResponseContract",
    "PhotoCacheResponseContract",

    # Factory
    "MediaTestDataFactory",

    # Builders
    "PlaylistRequestBuilder",
]
