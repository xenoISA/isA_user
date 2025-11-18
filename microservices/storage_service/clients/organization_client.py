"""
Storage Service - Organization Service Client

封装对 organization_service 的 HTTP 调用
用于家庭共享功能
"""

import logging
from typing import Any, Dict, List, Optional

from microservices.organization_service.clients import OrganizationServiceClient

logger = logging.getLogger(__name__)


class StorageOrganizationClient:
    """
    Storage Service 使用的 Organization Service 客户端封装

    封装与 organization_service 的交互，提供家庭共享相关功能
    """

    def __init__(self):
        """初始化客户端（使用 context manager 模式）"""
        pass

    async def create_album_sharing(
        self,
        organization_id: str,
        user_id: str,
        album_id: str,
        album_name: str,
        shared_with_members: Optional[List[str]] = None,
        share_with_all_members: bool = True,
        default_permission: str = "read_write",
        custom_permissions: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        创建相册家庭共享

        Args:
            organization_id: 组织ID
            user_id: 创建者用户ID
            album_id: 相册ID
            album_name: 相册名称
            shared_with_members: 共享给特定成员
            share_with_all_members: 是否共享给所有家庭成员
            default_permission: 默认权限
            custom_permissions: 自定义权限

        Returns:
            创建结果，包含 sharing_id
        """
        try:
            async with OrganizationServiceClient() as client:
                result = await client.create_sharing(
                    organization_id=organization_id,
                    user_id=user_id,
                    resource_type="album",
                    resource_id=album_id,
                    resource_name=album_name,
                    shared_with_members=shared_with_members,
                    share_with_all_members=share_with_all_members,
                    default_permission=default_permission,
                    custom_permissions=custom_permissions,
                )
                return result
        except Exception as e:
            logger.error(
                f"Failed to create album sharing for album {album_id}: {e}",
                exc_info=True,
            )
            return None

    async def update_album_sharing(
        self,
        organization_id: str,
        sharing_id: str,
        user_id: str,
        updates: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        更新相册家庭共享

        Args:
            organization_id: 组织ID
            sharing_id: 共享资源ID
            user_id: 用户ID
            updates: 更新内容

        Returns:
            更新结果
        """
        try:
            async with OrganizationServiceClient() as client:
                result = await client.update_sharing(
                    organization_id=organization_id,
                    sharing_id=sharing_id,
                    user_id=user_id,
                    updates=updates,
                )
                return result
        except Exception as e:
            logger.error(f"Failed to update album sharing {sharing_id}: {e}")
            return None

    async def get_sharing_info(
        self, organization_id: str, sharing_id: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取共享信息

        Args:
            organization_id: 组织ID
            sharing_id: 共享资源ID
            user_id: 用户ID

        Returns:
            共享信息
        """
        try:
            async with OrganizationServiceClient() as client:
                result = await client.get_sharing(
                    organization_id=organization_id,
                    sharing_id=sharing_id,
                    user_id=user_id,
                )
                return result
        except Exception as e:
            logger.error(f"Failed to get sharing info {sharing_id}: {e}")
            return None

    async def check_album_access(
        self,
        album_id: str,
        user_id: str,
        required_permission: str = "read",
    ) -> bool:
        """
        检查用户是否有相册访问权限

        Args:
            album_id: 相册ID
            user_id: 用户ID
            required_permission: 需要的权限级别

        Returns:
            是否有权限
        """
        try:
            async with OrganizationServiceClient() as client:
                has_access = await client.check_access(
                    resource_type="album",
                    resource_id=album_id,
                    user_id=user_id,
                    required_permission=required_permission,
                )
                return has_access
        except Exception as e:
            logger.error(
                f"Failed to check album access for user {user_id}, album {album_id}: {e}"
            )
            return False

    async def list_shared_albums(
        self, organization_id: str, user_id: str
    ) -> List[Dict[str, Any]]:
        """
        列出用户可访问的共享相册

        Args:
            organization_id: 组织ID
            user_id: 用户ID

        Returns:
            共享相册列表
        """
        try:
            async with OrganizationServiceClient() as client:
                # 获取用户可访问的所有共享资源
                shared_resources = await client.list_user_shared_resources(
                    organization_id=organization_id,
                    user_id=user_id,
                    resource_type="album",
                )
                return shared_resources if shared_resources else []
        except Exception as e:
            logger.error(
                f"Failed to list shared albums for user {user_id}: {e}", exc_info=True
            )
            return []
