"""
Family Sharing Service

家庭共享业务逻辑层
处理订阅、设备、存储、钱包等资源的共享管理

Uses dependency injection for testability:
- Repository is injected, not created at import time
- Event publishers are lazily loaded
"""

import logging
from typing import TYPE_CHECKING, Dict, Any, List, Optional
from datetime import datetime, timezone
import uuid

# Import protocols (no I/O dependencies) - NOT the concrete repository!
from .protocols import FamilySharingRepositoryProtocol
from .family_sharing_models import (
    CreateSharingRequest, UpdateSharingRequest,
    UpdateMemberSharingPermissionRequest, GetMemberSharedResourcesRequest,
    SharingResourceResponse, MemberSharingPermissionResponse,
    SharedResourceDetailResponse, MemberSharedResourcesResponse,
    SharingUsageStatsResponse,
    SharingResourceType, SharingPermissionLevel, SharingStatus
)
# Import event bus components
from core.nats_client import Event

logger = logging.getLogger(__name__)


class FamilySharingServiceError(Exception):
    """家庭共享服务异常基类"""
    pass


class SharingNotFoundError(FamilySharingServiceError):
    """共享不存在异常"""
    pass


class SharingAccessDeniedError(FamilySharingServiceError):
    """共享访问被拒绝异常"""
    pass


class SharingQuotaExceededError(FamilySharingServiceError):
    """共享配额超出异常"""
    pass


class FamilySharingService:
    """
    家庭共享服务

    Handles all family sharing operations while delegating
    data access to the repository layer via dependency injection.
    """

    def __init__(
        self,
        repository: Optional[FamilySharingRepositoryProtocol] = None,
        event_bus=None,
    ):
        """
        Initialize service with injected dependencies.

        Args:
            repository: Repository (inject mock for testing)
            event_bus: Event bus for publishing events
        """
        self.repository = repository  # Will be set by factory if None
        self.event_bus = event_bus

    # ============ 共享资源管理 ============

    async def create_sharing(
        self,
        organization_id: str,
        request: CreateSharingRequest,
        created_by: str
    ) -> SharingResourceResponse:
        """
        创建共享资源

        Args:
            organization_id: 组织/家庭ID
            request: 创建共享请求
            created_by: 创建者用户ID

        Returns:
            共享资源响应
        """
        try:
            # 验证创建者是否有权限
            has_permission = await self._check_organization_admin_permission(
                organization_id, created_by
            )
            if not has_permission:
                raise SharingAccessDeniedError(
                    f"User {created_by} does not have permission to create sharing"
                )

            # 生成共享ID
            sharing_id = str(uuid.uuid4())

            # 构建共享数据
            now = datetime.now(timezone.utc)
            sharing_data = {
                "sharing_id": sharing_id,
                "organization_id": organization_id,
                "resource_type": request.resource_type.value if hasattr(request.resource_type, 'value') else request.resource_type,
                "resource_id": request.resource_id,
                "resource_name": request.resource_name,
                "created_by": created_by,
                "share_with_all_members": request.share_with_all_members,
                "default_permission": request.default_permission.value if hasattr(request.default_permission, 'value') else request.default_permission,
                "status": SharingStatus.ACTIVE.value,
                "quota_settings": request.quota_settings or {},  # ✅ 确保不是 None
                "restrictions": request.restrictions or {},  # ✅ 确保不是 None
                "expires_at": request.expires_at.isoformat() if request.expires_at else None,
                "metadata": request.metadata or {}  # ✅ 确保不是 None
                # ✅ 不传 created_at 和 updated_at，让数据库使用默认值
            }

            # 保存到数据库
            sharing = await self.repository.create_sharing(sharing_data)

            if not sharing:
                raise FamilySharingServiceError(
                    f"Failed to create sharing resource in database"
                )

            # 如果指定了共享成员，创建成员权限
            if request.shared_with_members:
                for user_id in request.shared_with_members:
                    permission_level = request.custom_permissions.get(
                        user_id, request.default_permission
                    )
                    await self._grant_member_permission(
                        sharing_id, user_id, permission_level, request.quota_settings
                    )

            # 如果共享给所有成员，为当前所有成员创建权限
            if request.share_with_all_members:
                await self._grant_all_members_permission(
                    organization_id, sharing_id, request.default_permission,
                    request.quota_settings
                )

            logger.info(
                f"Sharing created | sharing_id={sharing_id} | "
                f"resource_type={request.resource_type} | resource_id={request.resource_id}"
            )

            # Publish family.resource_shared event
            if self.event_bus:
                try:
                    event = Event(
                        event_type="family.resource_shared",
                        source="organization_service",
                        data={
                            "sharing_id": sharing_id,
                            "organization_id": organization_id,
                            "resource_type": request.resource_type.value if hasattr(request.resource_type, 'value') else request.resource_type,
                            "resource_id": request.resource_id,
                            "resource_name": request.resource_name,
                            "created_by": created_by,
                            "share_with_all_members": request.share_with_all_members,
                            "default_permission": request.default_permission.value if hasattr(request.default_permission, 'value') else request.default_permission,
                            "shared_with_count": len(request.shared_with_members) if request.shared_with_members else 0,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    )
                    await self.event_bus.publish_event(event)
                    logger.info(f"Published family.resource_shared event for sharing {sharing_id}")
                except Exception as e:
                    logger.error(f"Failed to publish family.resource_shared event: {e}")

            return SharingResourceResponse(**sharing)

        except Exception as e:
            logger.error(f"Error creating sharing: {e}")
            if isinstance(e, FamilySharingServiceError):
                raise
            raise FamilySharingServiceError(f"Failed to create sharing: {str(e)}")

    async def get_sharing(
        self,
        sharing_id: str,
        user_id: Optional[str] = None
    ) -> SharedResourceDetailResponse:
        """
        获取共享资源详情

        Args:
            sharing_id: 共享ID
            user_id: 用户ID（用于权限验证）

        Returns:
            共享资源详情响应
        """
        try:
            # 获取共享基本信息
            sharing = await self.repository.get_sharing(sharing_id)
            if not sharing:
                raise SharingNotFoundError(f"Sharing {sharing_id} not found")

            # 如果提供了user_id，验证访问权限
            if user_id:
                has_access = await self._check_sharing_access(sharing_id, user_id)
                if not has_access:
                    raise SharingAccessDeniedError(
                        f"User {user_id} does not have access to sharing {sharing_id}"
                    )

            # 获取成员权限列表
            member_permissions = await self.repository.get_sharing_member_permissions(
                sharing_id
            )

            # 获取使用统计（可选）
            usage_stats = await self._get_sharing_usage_stats(sharing_id)

            return SharedResourceDetailResponse(
                sharing=SharingResourceResponse(**sharing),
                member_permissions=[
                    MemberSharingPermissionResponse(**perm)
                    for perm in member_permissions
                ],
                usage_stats=usage_stats
            )

        except Exception as e:
            logger.error(f"Error getting sharing: {e}")
            if isinstance(e, FamilySharingServiceError):
                raise
            raise FamilySharingServiceError(f"Failed to get sharing: {str(e)}")

    async def update_sharing(
        self,
        sharing_id: str,
        request: UpdateSharingRequest,
        updated_by: str
    ) -> SharingResourceResponse:
        """
        更新共享资源

        Args:
            sharing_id: 共享ID
            request: 更新请求
            updated_by: 更新者用户ID

        Returns:
            更新后的共享资源响应
        """
        try:
            # 验证权限
            sharing = await self.repository.get_sharing(sharing_id)
            if not sharing:
                raise SharingNotFoundError(f"Sharing {sharing_id} not found")

            has_permission = await self._check_organization_admin_permission(
                sharing["organization_id"], updated_by
            )
            if not has_permission and sharing["created_by"] != updated_by:
                raise SharingAccessDeniedError(
                    f"User {updated_by} does not have permission to update sharing"
                )

            # 准备更新数据
            update_data = request.model_dump(exclude_none=True)
            update_data["updated_at"] = datetime.utcnow()

            # 更新数据库
            updated_sharing = await self.repository.update_sharing(sharing_id, update_data)

            # 如果更新了共享成员列表，同步更新成员权限
            if request.shared_with_members is not None:
                await self._sync_member_permissions(
                    sharing_id,
                    request.shared_with_members,
                    request.custom_permissions or {}
                )

            logger.info(f"Sharing updated | sharing_id={sharing_id}")

            return SharingResourceResponse(**updated_sharing)

        except Exception as e:
            logger.error(f"Error updating sharing: {e}")
            if isinstance(e, FamilySharingServiceError):
                raise
            raise FamilySharingServiceError(f"Failed to update sharing: {str(e)}")

    async def delete_sharing(
        self,
        sharing_id: str,
        deleted_by: str
    ) -> bool:
        """
        删除共享资源

        Args:
            sharing_id: 共享ID
            deleted_by: 删除者用户ID

        Returns:
            是否删除成功
        """
        try:
            # 验证权限
            sharing = await self.repository.get_sharing(sharing_id)
            if not sharing:
                raise SharingNotFoundError(f"Sharing {sharing_id} not found")

            has_permission = await self._check_organization_admin_permission(
                sharing["organization_id"], deleted_by
            )
            if not has_permission and sharing["created_by"] != deleted_by:
                raise SharingAccessDeniedError(
                    f"User {deleted_by} does not have permission to delete sharing"
                )

            # 删除所有成员权限
            await self.repository.delete_sharing_member_permissions(sharing_id)

            # 删除共享
            success = await self.repository.delete_sharing(sharing_id)

            logger.info(f"Sharing deleted | sharing_id={sharing_id}")

            return success

        except Exception as e:
            logger.error(f"Error deleting sharing: {e}")
            if isinstance(e, FamilySharingServiceError):
                raise
            raise FamilySharingServiceError(f"Failed to delete sharing: {str(e)}")

    # ============ 成员权限管理 ============

    async def update_member_permission(
        self,
        sharing_id: str,
        request: UpdateMemberSharingPermissionRequest,
        updated_by: str
    ) -> MemberSharingPermissionResponse:
        """
        更新成员共享权限

        Args:
            sharing_id: 共享ID
            request: 更新权限请求
            updated_by: 更新者用户ID

        Returns:
            成员权限响应
        """
        try:
            # 验证权限
            sharing = await self.repository.get_sharing(sharing_id)
            if not sharing:
                raise SharingNotFoundError(f"Sharing {sharing_id} not found")

            has_permission = await self._check_organization_admin_permission(
                sharing["organization_id"], updated_by
            )
            if not has_permission:
                raise SharingAccessDeniedError(
                    f"User {updated_by} does not have permission to update member permissions"
                )

            # 更新权限
            permission = await self.repository.update_member_permission(
                sharing_id,
                request.user_id,
                {
                    "permission_level": request.permission_level,
                    "quota_allocated": request.quota_override,
                    "restrictions": request.restrictions_override
                }
            )

            logger.info(
                f"Member permission updated | sharing_id={sharing_id} | "
                f"user_id={request.user_id} | permission={request.permission_level}"
            )

            return MemberSharingPermissionResponse(**permission)

        except Exception as e:
            logger.error(f"Error updating member permission: {e}")
            if isinstance(e, FamilySharingServiceError):
                raise
            raise FamilySharingServiceError(f"Failed to update member permission: {str(e)}")

    async def revoke_member_access(
        self,
        sharing_id: str,
        user_id: str,
        revoked_by: str
    ) -> bool:
        """
        撤销成员访问权限

        Args:
            sharing_id: 共享ID
            user_id: 用户ID
            revoked_by: 撤销者用户ID

        Returns:
            是否撤销成功
        """
        try:
            # 验证权限
            sharing = await self.repository.get_sharing(sharing_id)
            if not sharing:
                raise SharingNotFoundError(f"Sharing {sharing_id} not found")

            has_permission = await self._check_organization_admin_permission(
                sharing["organization_id"], revoked_by
            )
            if not has_permission:
                raise SharingAccessDeniedError(
                    f"User {revoked_by} does not have permission to revoke access"
                )

            # 撤销权限
            success = await self.repository.delete_member_permission(sharing_id, user_id)

            logger.info(
                f"Member access revoked | sharing_id={sharing_id} | user_id={user_id}"
            )

            return success

        except Exception as e:
            logger.error(f"Error revoking member access: {e}")
            if isinstance(e, FamilySharingServiceError):
                raise
            raise FamilySharingServiceError(f"Failed to revoke member access: {str(e)}")

    async def get_member_shared_resources(
        self,
        organization_id: str,
        request: GetMemberSharedResourcesRequest
    ) -> MemberSharedResourcesResponse:
        """
        获取成员的共享资源列表

        Args:
            organization_id: 组织/家庭ID
            request: 获取请求

        Returns:
            成员共享资源列表
        """
        try:
            # 获取成员权限列表
            permissions = await self.repository.get_member_permissions(
                organization_id,
                request.user_id,
                resource_type=request.resource_type,
                status=request.status,
                limit=request.limit,
                offset=request.offset
            )

            total = await self.repository.count_member_permissions(
                organization_id,
                request.user_id,
                resource_type=request.resource_type,
                status=request.status
            )

            return MemberSharedResourcesResponse(
                user_id=request.user_id,
                organization_id=organization_id,
                shared_resources=[
                    MemberSharingPermissionResponse(**perm)
                    for perm in permissions
                ],
                total=total,
                limit=request.limit,
                offset=request.offset
            )

        except Exception as e:
            logger.error(f"Error getting member shared resources: {e}")
            raise FamilySharingServiceError(
                f"Failed to get member shared resources: {str(e)}"
            )

    # ============ 使用量统计 ============

    async def list_organization_sharings(
        self,
        organization_id: str,
        user_id: str,
        resource_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[SharingResourceResponse]:
        """
        列出组织的所有共享资源

        Args:
            organization_id: 组织/家庭ID
            user_id: 用户ID（用于权限验证）
            resource_type: 资源类型过滤
            status: 状态过滤
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            共享资源列表
        """
        try:
            # 验证用户是否是组织成员
            has_access = await self.repository.check_organization_member(
                organization_id, user_id
            )
            if not has_access:
                raise SharingAccessDeniedError(
                    f"User {user_id} is not a member of organization {organization_id}"
                )

            # 获取共享资源列表
            sharings = await self.repository.list_organization_sharings(
                organization_id,
                resource_type=resource_type,
                status=status,
                limit=limit,
                offset=offset
            )

            return [SharingResourceResponse(**sharing) for sharing in sharings]

        except Exception as e:
            logger.error(f"Error listing organization sharings: {e}")
            if isinstance(e, FamilySharingServiceError):
                raise
            raise FamilySharingServiceError(
                f"Failed to list organization sharings: {str(e)}"
            )

    async def get_sharing_usage_stats(
        self,
        sharing_id: str,
        period_days: int = 30
    ) -> SharingUsageStatsResponse:
        """
        获取共享资源使用统计

        Args:
            sharing_id: 共享ID
            period_days: 统计周期（天）

        Returns:
            使用统计响应
        """
        try:
            sharing = await self.repository.get_sharing(sharing_id)
            if not sharing:
                raise SharingNotFoundError(f"Sharing {sharing_id} not found")

            # 获取使用统计数据
            stats = await self._get_sharing_usage_stats(sharing_id, period_days)

            return stats

        except Exception as e:
            logger.error(f"Error getting sharing usage stats: {e}")
            if isinstance(e, FamilySharingServiceError):
                raise
            raise FamilySharingServiceError(
                f"Failed to get sharing usage stats: {str(e)}"
            )

    # ============ 内部辅助方法 ============

    async def _check_organization_admin_permission(
        self,
        organization_id: str,
        user_id: str
    ) -> bool:
        """检查用户是否是组织管理员"""
        # Use repository to check admin permissions
        return await self.repository.check_organization_admin(organization_id, user_id)

    async def _check_sharing_access(
        self,
        sharing_id: str,
        user_id: str
    ) -> bool:
        """检查用户是否有访问共享资源的权限"""
        # 获取共享资源
        sharing = await self.repository.get_sharing(sharing_id)
        if not sharing:
            return False

        # 创建者总是有访问权限
        if sharing.get("created_by") == user_id:
            return True

        # 检查是否有成员权限
        permission = await self.repository.get_member_permission(sharing_id, user_id)
        if permission is not None:
            return True

        # 检查是否是组织管理员
        has_admin = await self.repository.check_organization_admin(
            sharing.get("organization_id"), user_id
        )
        return has_admin

    async def _grant_member_permission(
        self,
        sharing_id: str,
        user_id: str,
        permission_level: SharingPermissionLevel,
        quota_settings: Optional[Dict[str, Any]] = None
    ) -> None:
        """为成员授予共享权限"""
        permission_data = {
            "permission_id": str(uuid.uuid4()),
            "sharing_id": sharing_id,
            "user_id": user_id,
            "permission_level": permission_level.value if hasattr(permission_level, 'value') else permission_level,
            "quota_allocated": quota_settings or {},
            "quota_used": {},
            "is_active": True,
            "granted_at": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        await self.repository.create_member_permission(permission_data)

    async def _grant_all_members_permission(
        self,
        organization_id: str,
        sharing_id: str,
        permission_level: SharingPermissionLevel,
        quota_settings: Optional[Dict[str, Any]] = None
    ) -> None:
        """为所有组织成员授予共享权限"""
        # 获取组织所有成员
        members = await self.repository.get_organization_members(organization_id)

        for member in members:
            await self._grant_member_permission(
                sharing_id,
                member["user_id"],
                permission_level,
                quota_settings
            )

    async def _sync_member_permissions(
        self,
        sharing_id: str,
        member_ids: List[str],
        custom_permissions: Dict[str, str]
    ) -> None:
        """同步成员权限列表"""
        # 获取当前所有权限
        current_permissions = await self.repository.get_sharing_member_permissions(sharing_id)
        current_member_ids = {perm["user_id"] for perm in current_permissions}

        # 删除不在新列表中的成员权限
        for user_id in current_member_ids - set(member_ids):
            await self.repository.delete_member_permission(sharing_id, user_id)

        # 添加新成员权限
        for user_id in set(member_ids) - current_member_ids:
            permission_level = custom_permissions.get(
                user_id, SharingPermissionLevel.READ_WRITE
            )
            await self._grant_member_permission(sharing_id, user_id, permission_level)

    async def _get_sharing_usage_stats(
        self,
        sharing_id: str,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """获取共享使用统计（内部方法）"""
        # TODO: 根据资源类型，调用相应服务获取使用统计
        # 例如：storage_service, wallet_service, device_service 等
        # 暂时返回空字典
        return {
            "total_usage": {},
            "member_usage": [],
            "quota_utilization": 0.0
        }
