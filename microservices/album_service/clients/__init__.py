"""
Clients module for album_service

Centralized HTTP clients for synchronous service-to-service communication
"""

from .storage_client import StorageServiceClient
from .media_client import MediaServiceClient

__all__ = [
    "StorageServiceClient",
    "MediaServiceClient",
]
