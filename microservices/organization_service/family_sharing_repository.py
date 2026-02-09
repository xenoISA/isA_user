"""
Family Sharing Repository
家庭共享数据访问层
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from isa_common import AsyncPostgresClient
from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class FamilySharingRepository:
    """家庭共享数据访问层"""

    def __init__(self, config: Optional[ConfigManager] = None):
        """初始化 repository"""
        # 使用 config_manager 进行服务发现
        if config is None:
            config = ConfigManager("organization_service")

        # 发现 PostgreSQL 服务
        # 优先级：环境变量 → Consul → localhost fallback
        host, port = config.discover_service(
            service_name='postgres_service',
            default_host='localhost',
            default_port=5432,
            env_host_key='POSTGRES_HOST',
            env_port_key='POSTGRES_PORT'
        )

        logger.info(f"Connecting to PostgreSQL at {host}:{port}")
        self.db = AsyncPostgresClient(
            host=host,
            port=port,
            database=os.getenv("POSTGRES_DB", "isa_platform"),
            username=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            user_id='organization_service'
        )
        self.schema = "organization"
        self.sharing_table = "family_sharing_resources"
        self.permissions_table = "family_sharing_member_permissions"
        self.usage_stats_table = "family_sharing_usage_stats"

    # ============ 共享资源操作 ============

    async def create_sharing(self, sharing_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建共享资源"""
        try:
            logger.info(f"Creating sharing with data: {sharing_data}")

            async with self.db:
                count = await self.db.insert_into(
                    self.sharing_table,
                    [sharing_data],
                    schema=self.schema
                )

            logger.info(f"Insert result count: {count}")

            if count is None or count == 0:
                logger.warning(f"Insert returned {count}, checking if record exists")
                # 尝试查询看是否已存在
                existing = await self.get_sharing(sharing_data['sharing_id'])
                if existing:
                    logger.info(f"Record already exists, returning it")
                    return existing
                logger.error(f"Insert failed and record not found")
                return None

            # 查询创建的记录
            result = await self.get_sharing(sharing_data['sharing_id'])
            logger.info(f"Created sharing result: {result}")
            return result

        except Exception as e:
            logger.error(f"Failed to create sharing: {e}", exc_info=True)
            raise

    async def get_sharing(self, sharing_id: str) -> Optional[Dict[str, Any]]:
        """获取共享资源"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.sharing_table}
                WHERE sharing_id = $1
            """

            async with self.db:
                result = await self.db.query(query, [sharing_id], schema=self.schema)

            return result[0] if result and len(result) > 0 else None

        except Exception as e:
            logger.error(f"Failed to get sharing: {e}")
            raise

    async def update_sharing(self, sharing_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新共享资源"""
        try:
            # ✅ 手动添加 updated_at
            update_data["updated_at"] = datetime.now(timezone.utc)

            # 构建 SET 子句
            set_clauses = []
            params = []
            param_count = 0

            for key, value in update_data.items():
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")
                params.append(value)

            # 添加 WHERE 条件
            param_count += 1
            params.append(sharing_id)

            set_clause = ", ".join(set_clauses)
            query = f"""
                UPDATE {self.schema}.{self.sharing_table}
                SET {set_clause}
                WHERE sharing_id = ${param_count}
            """

            async with self.db:
                count = await self.db.execute(query, params, schema=self.schema)

            if count is None or count == 0:
                return None

            return await self.get_sharing(sharing_id)

        except Exception as e:
            logger.error(f"Failed to update sharing: {e}")
            raise

    async def delete_sharing(self, sharing_id: str) -> bool:
        """删除共享资源"""
        try:
            query = f"""
                DELETE FROM {self.schema}.{self.sharing_table}
                WHERE sharing_id = $1
            """

            async with self.db:
                count = await self.db.execute(query, [sharing_id], schema=self.schema)

            return count is not None and count > 0

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
            # 构建查询条件
            conditions = ["organization_id = $1"]
            params = [organization_id]
            param_count = 1

            if resource_type:
                param_count += 1
                conditions.append(f"resource_type = ${param_count}")
                params.append(resource_type)

            if status:
                param_count += 1
                conditions.append(f"status = ${param_count}")
                params.append(status)

            where_clause = " AND ".join(conditions)
            query = f"""
                SELECT * FROM {self.schema}.{self.sharing_table}
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT {limit} OFFSET {offset}
            """

            async with self.db:
                result = await self.db.query(query, params, schema=self.schema)

            return result if result else []

        except Exception as e:
            logger.error(f"Failed to list sharings: {e}")
            raise

    # ============ 成员权限操作 ============

    async def create_member_permission(self, permission_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建成员权限"""
        try:
            async with self.db:
                count = await self.db.insert_into(
                    self.permissions_table,
                    [permission_data],
                    schema=self.schema
                )

            if count is None or count == 0:
                return None

            return await self.get_member_permission(
                permission_data['sharing_id'],
                permission_data['user_id']
            )

        except Exception as e:
            logger.error(f"Failed to create member permission: {e}")
            raise

    async def get_member_permission(self, sharing_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """获取成员权限"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.permissions_table}
                WHERE sharing_id = $1 AND user_id = $2
            """

            async with self.db:
                result = await self.db.query(query, [sharing_id, user_id], schema=self.schema)

            return result[0] if result and len(result) > 0 else None

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
            update_data["updated_at"] = datetime.now(timezone.utc)

            set_clauses = []
            params = []
            param_count = 0

            for key, value in update_data.items():
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")
                params.append(value)

            param_count += 1
            params.append(sharing_id)
            sharing_id_param = param_count

            param_count += 1
            params.append(user_id)
            user_id_param = param_count

            set_clause = ", ".join(set_clauses)
            query = f"""
                UPDATE {self.schema}.{self.permissions_table}
                SET {set_clause}
                WHERE sharing_id = ${sharing_id_param} AND user_id = ${user_id_param}
            """

            async with self.db:
                count = await self.db.execute(query, params, schema=self.schema)

            if count is None or count == 0:
                return None

            return await self.get_member_permission(sharing_id, user_id)

        except Exception as e:
            logger.error(f"Failed to update member permission: {e}")
            raise

    async def delete_member_permission(self, sharing_id: str, user_id: str) -> bool:
        """删除成员权限"""
        try:
            query = f"""
                DELETE FROM {self.schema}.{self.permissions_table}
                WHERE sharing_id = $1 AND user_id = $2
            """

            async with self.db:
                count = await self.db.execute(query, [sharing_id, user_id], schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Failed to delete member permission: {e}")
            return False

    async def delete_sharing_member_permissions(self, sharing_id: str) -> bool:
        """删除共享的所有成员权限"""
        try:
            query = f"""
                DELETE FROM {self.schema}.{self.permissions_table}
                WHERE sharing_id = $1
            """

            async with self.db:
                count = await self.db.execute(query, [sharing_id], schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Failed to delete sharing member permissions: {e}")
            return False

    async def get_sharing_member_permissions(self, sharing_id: str) -> List[Dict[str, Any]]:
        """获取共享资源的所有成员权限（别名）"""
        return await self.list_sharing_members(sharing_id)

    async def list_sharing_members(self, sharing_id: str) -> List[Dict[str, Any]]:
        """列出共享的所有成员权限"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.permissions_table}
                WHERE sharing_id = $1
            """

            async with self.db:
                result = await self.db.query(query, [sharing_id], schema=self.schema)

            return result if result else []

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
            query = f"""
                SELECT user_id FROM {self.schema}.organization_members
                WHERE organization_id = $1 AND status = $2
            """

            async with self.db:
                result = await self.db.query(query, [organization_id, "active"], schema=self.schema)

            return result if result else []

        except Exception as e:
            logger.error(f"Failed to get organization members: {e}")
            raise

    async def check_organization_member(self, organization_id: str, user_id: str) -> bool:
        """检查用户是否是组织成员"""
        try:
            query = f"""
                SELECT user_id FROM {self.schema}.organization_members
                WHERE organization_id = $1 AND user_id = $2 AND status = $3
            """

            async with self.db:
                result = await self.db.query(query, [organization_id, user_id, "active"], schema=self.schema)

            return bool(result and len(result) > 0)

        except Exception as e:
            logger.error(f"Failed to check organization member: {e}")
            return False

    async def check_organization_admin(self, organization_id: str, user_id: str) -> bool:
        """检查用户是否是组织管理员"""
        try:
            query = f"""
                SELECT role FROM {self.schema}.organization_members
                WHERE organization_id = $1 AND user_id = $2 AND status = $3
            """

            async with self.db:
                result = await self.db.query(query, [organization_id, user_id, "active"], schema=self.schema)

            if not result or len(result) == 0:
                return False

            role = result[0].get("role")
            return role in ["owner", "admin"]

        except Exception as e:
            logger.error(f"Failed to check organization admin: {e}")
            return False

    async def get_member_permissions(
        self,
        organization_id: str,
        user_id: str,
        resource_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取成员在组织内的所有权限"""
        try:
            # 获取成员的所有权限
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

            sharings_result = query.limit(limit).offset(offset).execute()

            # 合并权限和共享信息
            result = []
            for perm in permissions_result.data:
                for sharing in sharings_result.data:
                    if perm["sharing_id"] == sharing["sharing_id"]:
                        result.append({**perm, "resource": sharing})
                        break

            return result
        except Exception as e:
            logger.error(f"Failed to get member permissions: {e}")
            raise

    async def count_member_permissions(
        self,
        organization_id: str,
        user_id: str,
        resource_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> int:
        """统计成员在组织内的权限数量"""
        try:
            permissions = await self.get_member_permissions(
                organization_id,
                user_id,
                resource_type=resource_type,
                status=status,
                limit=1000,  # 用于计数，设置较大值
                offset=0
            )
            return len(permissions)
        except Exception as e:
            logger.error(f"Failed to count member permissions: {e}")
            return 0
