"""
Clients module for media_service

Centralized HTTP clients for synchronous service-to-service communication
"""

from .storage_client import StorageServiceClient

__all__ = [
    "StorageServiceClient",
]
