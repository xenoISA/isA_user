"""
Compliance Service Clients Package

客户端管理 - 用于调用其他服务
"""

from microservices.audit_service.client import AuditServiceClient
from microservices.account_service.client import AccountServiceClient
from microservices.storage_service.client import StorageServiceClient

from .service_clients import ServiceClients, get_service_clients, close_service_clients

__all__ = [
    # Individual service clients
    "AuditServiceClient",
    "AccountServiceClient",
    "StorageServiceClient",
    # Service Clients Manager
    "ServiceClients",
    "get_service_clients",
    "close_service_clients",
]
