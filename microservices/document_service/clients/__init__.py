"""
Document Service Clients

Service clients for cross-service communication
"""

from .storage_client import StorageServiceClient
from .authorization_client import AuthorizationServiceClient
from .digital_analytics_client import DigitalAnalyticsClient

__all__ = [
    'StorageServiceClient',
    'AuthorizationServiceClient',
    'DigitalAnalyticsClient',
]
