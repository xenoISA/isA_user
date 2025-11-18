"""
Compliance Service Clients Package

客户端管理 - 用于调用其他服务
"""

from .service_clients import ServiceClients, get_service_clients, close_service_clients

__all__ = [
    # Service Clients (调用其他服务)
    "ServiceClients",
    "get_service_clients",
    "close_service_clients",
]
