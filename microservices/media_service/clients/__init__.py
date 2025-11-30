"""
Clients module for media_service

Centralized HTTP clients for synchronous service-to-service communication
"""

from .digital_analytics_client import DigitalAnalyticsClient
from .storage_client import StorageServiceClient

__all__ = [
    "StorageServiceClient",
    "DigitalAnalyticsClient",
]
