"""
Family Sharing Repository
家庭共享数据访问层
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from core.database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class FamilySharingRepository:
    """家庭共享数据访问层"""

    def __init__(self):
        """初始化 repository"""
        self.supabase = get_supabase_client()
        self.sharing_table = "family_sharing_resources"
        self.permissions_table = "family_sharing_member_permissions"
        self.usage_stats_table = "family_sharing_usage_stats"

    # ============ 共享资源操作 ============

    async def create_sharing(self, sharing_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建共享资源"""
        try:
            result = self.supabase.table(self.sharing_table).insert(sharing_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to create sharing: {e}")
            raise

    async def get_sharing(self, sharing_id: str) -> Optional[Dict[str, Any]]:
        """获取共享资源"""
        try:
            result = self.supabase.table(self.sharing_table)\
                .select("*")\
                .eq("sharing_id", sharing_id)\
                .execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to get sharing: {e}")
            raise

    async def update_sharing(self, sharing_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新共享资源"""
        try:
            update_data["updated_at"] = datetime.utcnow()
            result = self.supabase.table(self.sharing_table)\
                .update(update_data)\
                .eq("sharing_id", sharing_id)\
                .execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to update sharing: {e}")
            raise

    async def delete_sharing(self, sharing_id: str) -> bool:
        """删除共享资源"""
        try:
            self.supabase.table(self.sharing_table)\
                .delete()\
                .eq("sharing_id", sharing_id)\
                .execute()
            return True
        except Exception as e:
            logger.error(f"Failed to delete sharing: {e}")
            return False

    async def list_organization_sharings(
        self,
        organization_id: str,
        resource_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """列出组织的共享资源"""
        try:
            query = self.supabase.table(self.sharing_table)\
                .select("*")\
                .eq("organization_id", organization_id)

            if resource_type:
                query = query.eq("resource_type", resource_type)
            if status:
                query = query.eq("status", status)

            result = query.limit(limit).offset(offset).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Failed to list sharings: {e}")
            raise

    # ============ 成员权限操作 ============

    async def create_member_permission(self, permission_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建成员权限"""
        try:
            result = self.supabase.table(self.permissions_table).insert(permission_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to create member permission: {e}")
            raise

    async def get_member_permission(self, sharing_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """获取成员权限"""
        try:
            result = self.supabase.table(self.permissions_table)\
                .select("*")\
                .eq("sharing_id", sharing_id)\
                .eq("user_id", user_id)\
                .execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to get member permission: {e}")
            raise

    async def update_member_permission(
        self,
        sharing_id: str,
        user_id: str,
        update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """更新成员权限"""
        try:
            update_data["updated_at"] = datetime.utcnow()
            result = self.supabase.table(self.permissions_table)\
                .update(update_data)\
                .eq("sharing_id", sharing_id)\
                .eq("user_id", user_id)\
                .execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to update member permission: {e}")
            raise

    async def delete_member_permission(self, sharing_id: str, user_id: str) -> bool:
        """删除成员权限"""
        try:
            self.supabase.table(self.permissions_table)\
                .delete()\
                .eq("sharing_id", sharing_id)\
                .eq("user_id", user_id)\
                .execute()
            return True
        except Exception as e:
            logger.error(f"Failed to delete member permission: {e}")
            return False

    async def list_sharing_members(self, sharing_id: str) -> List[Dict[str, Any]]:
        """列出共享的所有成员权限"""
        try:
            result = self.supabase.table(self.permissions_table)\
                .select("*")\
                .eq("sharing_id", sharing_id)\
                .execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Failed to list sharing members: {e}")
            raise

    async def list_member_shared_resources(
        self,
        user_id: str,
        organization_id: str,
        resource_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """列出成员的共享资源"""
        try:
            # 需要 JOIN 两个表
            # 这里简化处理：先获取成员的所有权限，再获取对应的共享资源
            permissions_result = self.supabase.table(self.permissions_table)\
                .select("*")\
                .eq("user_id", user_id)\
                .execute()

            if not permissions_result.data:
                return []

            # 获取对应的共享资源
            sharing_ids = [p["sharing_id"] for p in permissions_result.data]

            query = self.supabase.table(self.sharing_table)\
                .select("*")\
                .in_("sharing_id", sharing_ids)\
                .eq("organization_id", organization_id)

            if resource_type:
                query = query.eq("resource_type", resource_type)
            if status:
                query = query.eq("status", status)

            result = query.limit(limit).offset(offset).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Failed to list member shared resources: {e}")
            raise

    # ============ 组织成员查询 ============

    async def get_organization_members(self, organization_id: str) -> List[Dict[str, Any]]:
        """获取组织所有成员"""
        try:
            result = self.supabase.table("organization_members")\
                .select("user_id")\
                .eq("organization_id", organization_id)\
                .eq("status", "active")\
                .execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Failed to get organization members: {e}")
            raise

    async def check_organization_member(self, organization_id: str, user_id: str) -> bool:
        """检查用户是否是组织成员"""
        try:
            result = self.supabase.table("organization_members")\
                .select("user_id")\
                .eq("organization_id", organization_id)\
                .eq("user_id", user_id)\
                .eq("status", "active")\
                .execute()
            return bool(result.data)
        except Exception as e:
            logger.error(f"Failed to check organization member: {e}")
            return False

    async def check_organization_admin(self, organization_id: str, user_id: str) -> bool:
        """检查用户是否是组织管理员"""
        try:
            result = self.supabase.table("organization_members")\
                .select("role")\
                .eq("organization_id", organization_id)\
                .eq("user_id", user_id)\
                .eq("status", "active")\
                .execute()

            if not result.data:
                return False

            role = result.data[0].get("role")
            return role in ["owner", "admin"]
        except Exception as e:
            logger.error(f"Failed to check organization admin: {e}")
            return False
