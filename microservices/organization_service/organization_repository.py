"""
Organization Repository

组织数据访问层，负责所有数据库操作
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import uuid

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common.postgres_client import PostgresClient
from .models import (
    OrganizationPlan, OrganizationStatus, OrganizationRole, MemberStatus,
    OrganizationResponse, OrganizationMemberResponse
)

logger = logging.getLogger(__name__)


class OrganizationRepository:
    """组织数据仓库"""

    def __init__(self):
        self.db = PostgresClient(
            host='isa-postgres-grpc',
            port=50061,
            user_id='organization_service'
        )
        self.schema = "organization"
        self.organizations_table = "organizations"
        self.org_members_table = "organization_members"
    
    # ============ Organization CRUD Operations ============
    
    async def create_organization(
        self,
        organization_data: Dict[str, Any],
        owner_user_id: str
    ) -> Optional[OrganizationResponse]:
        """创建组织并添加所有者"""
        try:
            # 生成组织ID
            org_id = f"org_{uuid.uuid4().hex[:12]}"

            # 准备组织数据 (只包含数据库中存在的字段)
            org_dict = {
                'organization_id': org_id,
                'name': organization_data['name'],
                'domain': organization_data.get('domain'),
                'billing_email': organization_data['billing_email'],
                'plan': organization_data.get('plan', OrganizationPlan.FREE.value),
                'status': OrganizationStatus.ACTIVE.value,
                'credits_pool': 0.0,  # ✅ Float for DOUBLE PRECISION
                'settings': organization_data.get('settings', {}),  # ✅ Direct dict, no json.dumps
                'metadata': {},
                'api_keys': []
            }

            # 创建组织
            with self.db:
                count = self.db.insert_into(
                    self.organizations_table,
                    [org_dict],
                    schema=self.schema
                )

            # ✅ Check count for None
            if count is None or count == 0:
                logger.error("Failed to create organization")
                return None

            # 添加所有者为成员
            member_result = await self.add_organization_member(
                org_id,
                owner_user_id,
                OrganizationRole.OWNER
            )

            if not member_result:
                # 如果添加成员失败，删除组织
                query = f"DELETE FROM {self.schema}.{self.organizations_table} WHERE organization_id = $1"
                with self.db:
                    self.db.execute(query, [org_id], schema=self.schema)
                logger.error(f"Failed to add owner, rolling back organization {org_id}")
                return None

            # 查询创建的组织
            org = await self.get_organization(org_id)
            return org

        except Exception as e:
            logger.error(f"Error creating organization: {e}")
            return None
    
    async def get_organization(self, organization_id: str) -> Optional[OrganizationResponse]:
        """获取组织信息"""
        try:
            query = f"SELECT * FROM {self.schema}.{self.organizations_table} WHERE organization_id = $1"

            with self.db:
                result = self.db.query(query, [organization_id], schema=self.schema)

            if not result or len(result) == 0:
                return None

            org_data = result[0]

            # 获取成员数
            member_count = await self.get_organization_member_count(organization_id)
            org_data['member_count'] = member_count

            return OrganizationResponse(**org_data)

        except Exception as e:
            logger.error(f"Error getting organization {organization_id}: {e}")
            return None
    
    async def update_organization(
        self,
        organization_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[OrganizationResponse]:
        """更新组织信息"""
        try:
            # 过滤None值
            update_dict = {k: v for k, v in update_data.items() if v is not None}

            if not update_dict:
                # 没有需要更新的字段
                return await self.get_organization(organization_id)

            # ✅ 手动添加 updated_at
            update_dict['updated_at'] = datetime.now(timezone.utc)

            # 构建 SET 子句
            set_clauses = []
            params = []
            param_count = 0

            for key, value in update_dict.items():
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")
                params.append(value)

            # 添加 WHERE 条件
            param_count += 1
            params.append(organization_id)
            org_id_param = param_count

            set_clause = ", ".join(set_clauses)
            query = f"""
                UPDATE {self.schema}.{self.organizations_table}
                SET {set_clause}
                WHERE organization_id = ${org_id_param}
            """

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            # ✅ Check count for None
            if count is None or count == 0:
                return None

            # 返回更新后的组织
            return await self.get_organization(organization_id)

        except Exception as e:
            logger.error(f"Error updating organization {organization_id}: {e}")
            return None
    
    async def delete_organization(self, organization_id: str) -> bool:
        """删除组织（软删除）"""
        try:
            query = f"""
                UPDATE {self.schema}.{self.organizations_table}
                SET status = $1, updated_at = $2
                WHERE organization_id = $3
            """
            params = [
                OrganizationStatus.DELETED.value,
                datetime.now(timezone.utc),
                organization_id
            ]

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error deleting organization {organization_id}: {e}")
            return False
    
    async def get_user_organizations(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户所属的所有组织"""
        try:
            # 从成员表获取用户的组织
            member_query = f"""
                SELECT organization_id, role, status
                FROM {self.schema}.{self.org_members_table}
                WHERE user_id = $1 AND status = $2
            """

            with self.db:
                member_result = self.db.query(
                    member_query,
                    [user_id, MemberStatus.ACTIVE.value],
                    schema=self.schema
                )

            if not member_result:
                return []

            org_ids = [m['organization_id'] for m in member_result]
            role_map = {m['organization_id']: m['role'] for m in member_result}

            # 获取组织详情
            if not org_ids:
                return []

            # 构建 IN 子句
            placeholders = ', '.join([f'${i+1}' for i in range(len(org_ids))])
            org_query = f"""
                SELECT * FROM {self.schema}.{self.organizations_table}
                WHERE organization_id IN ({placeholders})
                AND status != $%d
            """ % (len(org_ids) + 1)

            params = org_ids + [OrganizationStatus.DELETED.value]

            with self.db:
                org_result = self.db.query(org_query, params, schema=self.schema)

            if not org_result:
                return []

            # 组合数据
            organizations = []
            for org in org_result:
                org['user_role'] = role_map.get(org['organization_id'])
                org['member_count'] = await self.get_organization_member_count(org['organization_id'])
                organizations.append(org)

            return organizations

        except Exception as e:
            logger.error(f"Error getting user organizations for {user_id}: {e}")
            return []
    
    # ============ Member Management ============
    
    async def add_organization_member(
        self,
        organization_id: str,
        user_id: str,
        role: OrganizationRole,
        permissions: Optional[List[str]] = None
    ) -> Optional[OrganizationMemberResponse]:
        """添加组织成员"""
        try:
            # 检查用户是否已经是成员
            check_query = f"""
                SELECT * FROM {self.schema}.{self.org_members_table}
                WHERE organization_id = $1 AND user_id = $2
            """

            with self.db:
                existing = self.db.query(
                    check_query,
                    [organization_id, user_id],
                    schema=self.schema
                )

            if existing and len(existing) > 0:
                # 如果是被删除的成员，重新激活
                if existing[0]['status'] in [MemberStatus.INACTIVE.value, 'removed']:
                    update_query = f"""
                        UPDATE {self.schema}.{self.org_members_table}
                        SET role = $1, status = $2, permissions = $3, updated_at = $4
                        WHERE organization_id = $5 AND user_id = $6
                    """
                    params = [
                        role.value,
                        MemberStatus.ACTIVE.value,
                        permissions or [],
                        datetime.now(timezone.utc),
                        organization_id,
                        user_id
                    ]

                    with self.db:
                        count = self.db.execute(update_query, params, schema=self.schema)

                    if count is not None and count > 0:
                        return await self.get_organization_member(organization_id, user_id)
                else:
                    logger.warning(f"User {user_id} is already a member of organization {organization_id}")
                    return None

            # 添加新成员
            member_dict = {
                'organization_id': organization_id,
                'user_id': user_id,
                'role': role.value,
                'status': MemberStatus.ACTIVE.value,
                'permissions': permissions or []
            }

            with self.db:
                count = self.db.insert_into(
                    self.org_members_table,
                    [member_dict],
                    schema=self.schema
                )

            if count is None or count == 0:
                return None

            # ✅ 不再跨服务查询 users 表，直接返回成员数据
            return await self.get_organization_member(organization_id, user_id)

        except Exception as e:
            logger.error(f"Error adding member {user_id} to organization {organization_id}: {e}")
            return None
    
    async def update_organization_member(
        self,
        organization_id: str,
        user_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[OrganizationMemberResponse]:
        """更新组织成员信息"""
        try:
            update_dict = {k: v.value if hasattr(v, 'value') else v for k, v in update_data.items() if v is not None}

            if not update_dict:
                return await self.get_organization_member(organization_id, user_id)

            # ✅ 手动添加 updated_at
            update_dict['updated_at'] = datetime.now(timezone.utc)

            # 构建 SET 子句
            set_clauses = []
            params = []
            param_count = 0

            for key, value in update_dict.items():
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")
                params.append(value)

            # 添加 WHERE 条件
            param_count += 1
            params.append(organization_id)
            org_id_param = param_count

            param_count += 1
            params.append(user_id)
            user_id_param = param_count

            set_clause = ", ".join(set_clauses)
            query = f"""
                UPDATE {self.schema}.{self.org_members_table}
                SET {set_clause}
                WHERE organization_id = ${org_id_param} AND user_id = ${user_id_param}
            """

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            if count is None or count == 0:
                return None

            # ✅ 不再跨服务查询 users 表
            return await self.get_organization_member(organization_id, user_id)

        except Exception as e:
            logger.error(f"Error updating member {user_id} in organization {organization_id}: {e}")
            return None
    
    async def remove_organization_member(
        self,
        organization_id: str,
        user_id: str
    ) -> bool:
        """移除组织成员（软删除）"""
        try:
            query = f"""
                UPDATE {self.schema}.{self.org_members_table}
                SET status = $1, updated_at = $2
                WHERE organization_id = $3 AND user_id = $4
            """
            params = [
                MemberStatus.INACTIVE.value,
                datetime.now(timezone.utc),
                organization_id,
                user_id
            ]

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error removing member {user_id} from organization {organization_id}: {e}")
            return False
    
    async def get_organization_member(
        self,
        organization_id: str,
        user_id: str
    ) -> Optional[OrganizationMemberResponse]:
        """获取组织成员信息"""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.org_members_table}
                WHERE organization_id = $1 AND user_id = $2
            """

            with self.db:
                result = self.db.query(query, [organization_id, user_id], schema=self.schema)

            if not result or len(result) == 0:
                return None

            member_data = result[0]

            # ✅ 不再跨服务查询 users 表
            # TODO: 如需 email 和 name，通过 Account Service client 获取

            return OrganizationMemberResponse(**member_data)

        except Exception as e:
            logger.error(f"Error getting member {user_id} from organization {organization_id}: {e}")
            return None
    
    async def get_organization_members(
        self,
        organization_id: str,
        limit: int = 100,
        offset: int = 0,
        role_filter: Optional[OrganizationRole] = None,
        status_filter: Optional[MemberStatus] = None
    ) -> List[OrganizationMemberResponse]:
        """获取组织成员列表"""
        try:
            # 构建查询条件
            conditions = ["organization_id = $1"]
            params = [organization_id]
            param_count = 1

            if role_filter:
                param_count += 1
                conditions.append(f"role = ${param_count}")
                params.append(role_filter.value)

            if status_filter:
                param_count += 1
                conditions.append(f"status = ${param_count}")
                params.append(status_filter.value)
            else:
                # 默认只返回活跃成员
                param_count += 1
                conditions.append(f"status = ${param_count}")
                params.append(MemberStatus.ACTIVE.value)

            where_clause = " AND ".join(conditions)
            query = f"""
                SELECT * FROM {self.schema}.{self.org_members_table}
                WHERE {where_clause}
                ORDER BY joined_at ASC
                LIMIT {limit} OFFSET {offset}
            """

            with self.db:
                result = self.db.query(query, params, schema=self.schema)

            if not result:
                return []

            # ✅ 不再跨服务查询 users 表
            # TODO: 如需批量获取用户信息，通过 Account Service client 获取
            members = []
            for member_data in result:
                members.append(OrganizationMemberResponse(**member_data))

            return members

        except Exception as e:
            logger.error(f"Error getting members for organization {organization_id}: {e}")
            return []
    
    async def get_user_organization_role(
        self,
        organization_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """获取用户在组织中的角色"""
        try:
            query = f"""
                SELECT role, permissions, status
                FROM {self.schema}.{self.org_members_table}
                WHERE organization_id = $1 AND user_id = $2
            """

            with self.db:
                result = self.db.query(query, [organization_id, user_id], schema=self.schema)

            if not result or len(result) == 0:
                return None

            member = result[0]

            return {
                'role': member['role'],
                'permissions': member.get('permissions', []),
                'status': member['status']
            }

        except Exception as e:
            logger.error(f"Error getting user role for {user_id} in organization {organization_id}: {e}")
            return None
    
    async def get_organization_member_count(self, organization_id: str) -> int:
        """获取组织成员数量"""
        try:
            query = f"""
                SELECT COUNT(*) as count
                FROM {self.schema}.{self.org_members_table}
                WHERE organization_id = $1 AND status = $2
            """

            with self.db:
                result = self.db.query(
                    query,
                    [organization_id, MemberStatus.ACTIVE.value],
                    schema=self.schema
                )

            if result and len(result) > 0:
                return int(result[0]['count'])
            return 0

        except Exception as e:
            logger.error(f"Error getting member count for organization {organization_id}: {e}")
            return 0
    
    # ============ Statistics and Analytics ============
    
    async def get_organization_stats(self, organization_id: str) -> Dict[str, Any]:
        """获取组织统计信息"""
        try:
            # 获取组织基本信息
            org = await self.get_organization(organization_id)
            if not org:
                return {}
            
            # 获取成员统计
            total_members = await self.get_organization_member_count(organization_id)
            
            # 获取活跃成员数（最近30天有活动）
            # TODO: 需要从活动日志中获取
            active_members = total_members
            
            return {
                'organization_id': organization_id,
                'name': org.name,
                'plan': org.plan,
                'status': org.status,
                'member_count': total_members,
                'active_members': active_members,
                'credits_pool': float(org.credits_pool),
                'credits_used_this_month': 0,  # TODO: 从使用记录获取
                'storage_used_gb': 0.0,  # TODO: 从存储服务获取
                'api_calls_this_month': 0,  # TODO: 从API日志获取
                'created_at': org.created_at
            }
            
        except Exception as e:
            logger.error(f"Error getting stats for organization {organization_id}: {e}")
            return {}
    
    async def list_all_organizations(
        self,
        limit: int = 100,
        offset: int = 0,
        search: Optional[str] = None,
        plan_filter: Optional[str] = None,
        status_filter: Optional[str] = None
    ) -> List[OrganizationResponse]:
        """获取所有组织列表（平台管理员）"""
        try:
            # 构建查询条件
            conditions = []
            params = []
            param_count = 0

            if search:
                param_count += 1
                conditions.append(f"(name ILIKE ${param_count} OR display_name ILIKE ${param_count})")
                params.append(f"%{search}%")

            if plan_filter:
                param_count += 1
                conditions.append(f"plan = ${param_count}")
                params.append(plan_filter)

            if status_filter:
                param_count += 1
                conditions.append(f"status = ${param_count}")
                params.append(status_filter)
            else:
                param_count += 1
                conditions.append(f"status != ${param_count}")
                params.append(OrganizationStatus.DELETED.value)

            where_clause = " AND ".join(conditions) if conditions else "1=1"
            query = f"""
                SELECT * FROM {self.schema}.{self.organizations_table}
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT {limit} OFFSET {offset}
            """

            with self.db:
                result = self.db.query(query, params, schema=self.schema)

            if not result:
                return []

            organizations = []
            for org_data in result:
                org_data['member_count'] = await self.get_organization_member_count(org_data['organization_id'])
                organizations.append(OrganizationResponse(**org_data))

            return organizations

        except Exception as e:
            logger.error(f"Error listing all organizations: {e}")
            return []