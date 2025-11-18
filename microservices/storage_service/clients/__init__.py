"""
Storage Service - Clients Module

集中管理所有服务间同步调用的 HTTP 客户端
"""

from .organization_client import StorageOrganizationClient

__all__ = [
    "StorageOrganizationClient",
]
