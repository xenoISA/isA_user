"""
Organization Repository

组织数据访问层，负责所有数据库操作
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from decimal import Decimal
import uuid
import json

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.database.supabase_client import get_supabase_client
from .models import (
    OrganizationPlan, OrganizationStatus, OrganizationRole, MemberStatus,
    OrganizationResponse, OrganizationMemberResponse
)

logger = logging.getLogger(__name__)


class OrganizationRepository:
    """组织数据仓库"""
    
    def __init__(self):
        self.client = get_supabase_client()
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
                'credits_pool': 0,
                'settings': organization_data.get('settings', {}),
                'api_keys': []
            }
            
            # 创建组织
            result = self.client.table(self.organizations_table).insert(org_dict).execute()
            
            if not result.data:
                logger.error("Failed to create organization")
                return None
            
            org_data = result.data[0]
            
            # 添加所有者为成员
            member_result = await self.add_organization_member(
                org_id, 
                owner_user_id, 
                OrganizationRole.OWNER
            )
            
            if not member_result:
                # 如果添加成员失败，删除组织
                self.client.table(self.organizations_table).delete().eq('organization_id', org_id).execute()
                logger.error(f"Failed to add owner, rolling back organization {org_id}")
                return None
            
            # 获取成员数
            org_data['member_count'] = 1
            
            return OrganizationResponse(**org_data)
            
        except Exception as e:
            logger.error(f"Error creating organization: {e}")
            return None
    
    async def get_organization(self, organization_id: str) -> Optional[OrganizationResponse]:
        """获取组织信息"""
        try:
            result = self.client.table(self.organizations_table).select('*').eq('organization_id', organization_id).execute()
            
            if not result.data or len(result.data) == 0:
                return None
            
            org_data = result.data[0]
            
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
            
            update_dict['updated_at'] = datetime.utcnow().isoformat()
            
            result = self.client.table(self.organizations_table).update(update_dict).eq('organization_id', organization_id).execute()
            
            if not result.data:
                return None
            
            org_data = result.data[0]
            
            # 获取成员数
            member_count = await self.get_organization_member_count(organization_id)
            org_data['member_count'] = member_count
            
            return OrganizationResponse(**org_data)
            
        except Exception as e:
            logger.error(f"Error updating organization {organization_id}: {e}")
            return None
    
    async def delete_organization(self, organization_id: str) -> bool:
        """删除组织（软删除）"""
        try:
            result = self.client.table(self.organizations_table).update({
                'status': OrganizationStatus.DELETED.value,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('organization_id', organization_id).execute()
            
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"Error deleting organization {organization_id}: {e}")
            return False
    
    async def get_user_organizations(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户所属的所有组织"""
        try:
            # 从成员表获取用户的组织
            member_result = self.client.table(self.org_members_table).select('organization_id, role, status').eq('user_id', user_id).eq('status', MemberStatus.ACTIVE.value).execute()
            
            if not member_result.data:
                return []
            
            org_ids = [m['organization_id'] for m in member_result.data]
            role_map = {m['organization_id']: m['role'] for m in member_result.data}
            
            # 获取组织详情
            org_result = self.client.table(self.organizations_table).select('*').in_('organization_id', org_ids).neq('status', OrganizationStatus.DELETED.value).execute()
            
            if not org_result.data:
                return []
            
            # 组合数据
            organizations = []
            for org in org_result.data:
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
            existing = self.client.table(self.org_members_table).select('*').eq('organization_id', organization_id).eq('user_id', user_id).execute()
            
            if existing.data and len(existing.data) > 0:
                # 如果是被删除的成员，重新激活
                if existing.data[0]['status'] in [MemberStatus.INACTIVE.value, 'removed']:
                    result = self.client.table(self.org_members_table).update({
                        'role': role.value,
                        'status': MemberStatus.ACTIVE.value,
                        'permissions': permissions or [],
                        'updated_at': datetime.utcnow().isoformat()
                    }).eq('organization_id', organization_id).eq('user_id', user_id).execute()
                    
                    if result.data:
                        return OrganizationMemberResponse(**result.data[0])
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
            
            result = self.client.table(self.org_members_table).insert(member_dict).execute()
            
            if not result.data:
                return None
                
            # 使用数据库返回的数据
            member_data = result.data[0]
                
            # 获取用户信息以补充响应
            user_result = self.client.table('users').select('email, name').eq('user_id', user_id).execute()
            if user_result.data:
                member_data['email'] = user_result.data[0].get('email')
                member_data['name'] = user_result.data[0].get('name')
            
            return OrganizationMemberResponse(**member_data)
            
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
            
            update_dict['updated_at'] = datetime.utcnow().isoformat()
            
            result = self.client.table(self.org_members_table).update(update_dict).eq('organization_id', organization_id).eq('user_id', user_id).execute()
            
            if not result.data:
                return None
            
            member_data = result.data[0]
            
            # 获取用户信息
            user_result = self.client.table('users').select('email, name').eq('user_id', user_id).execute()
            if user_result.data:
                member_data['email'] = user_result.data[0].get('email')
                member_data['name'] = user_result.data[0].get('name')
            
            return OrganizationMemberResponse(**member_data)
            
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
            result = self.client.table(self.org_members_table).update({
                'status': MemberStatus.INACTIVE.value,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('organization_id', organization_id).eq('user_id', user_id).execute()
            
            return bool(result.data)
            
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
            result = self.client.table(self.org_members_table).select('*').eq('organization_id', organization_id).eq('user_id', user_id).execute()
            
            if not result.data or len(result.data) == 0:
                return None
            
            member_data = result.data[0]
            
            # 获取用户信息
            user_result = self.client.table('users').select('email, name').eq('user_id', user_id).execute()
            if user_result.data:
                member_data['email'] = user_result.data[0].get('email')
                member_data['name'] = user_result.data[0].get('name')
            
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
            query = self.client.table(self.org_members_table).select('*').eq('organization_id', organization_id)
            
            if role_filter:
                query = query.eq('role', role_filter.value)
            
            if status_filter:
                query = query.eq('status', status_filter.value)
            else:
                # 默认只返回活跃成员
                query = query.eq('status', MemberStatus.ACTIVE.value)
            
            query = query.order('joined_at', desc=False).range(offset, offset + limit - 1)
            
            result = query.execute()
            
            if not result.data:
                return []
            
            # 获取所有用户信息
            user_ids = [m['user_id'] for m in result.data]
            user_result = self.client.table('users').select('user_id, email, name').in_('user_id', user_ids).execute()
            
            user_map = {u['user_id']: u for u in (user_result.data or [])}
            
            members = []
            for member_data in result.data:
                user_info = user_map.get(member_data['user_id'], {})
                member_data['email'] = user_info.get('email')
                member_data['name'] = user_info.get('name')
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
            result = self.client.table(self.org_members_table).select('role, permissions, status').eq('organization_id', organization_id).eq('user_id', user_id).execute()
            
            if not result.data or len(result.data) == 0:
                return None
            
            member = result.data[0]
            
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
            result = self.client.table(self.org_members_table).select('user_id', count='exact').eq('organization_id', organization_id).eq('status', MemberStatus.ACTIVE.value).execute()
            
            return result.count if result else 0
            
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
            query = self.client.table(self.organizations_table).select('*')
            
            if search:
                query = query.or_(f"name.ilike.%{search}%,display_name.ilike.%{search}%")
            
            if plan_filter:
                query = query.eq('plan', plan_filter)
            
            if status_filter:
                query = query.eq('status', status_filter)
            else:
                query = query.neq('status', OrganizationStatus.DELETED.value)
            
            query = query.order('created_at', desc=True).range(offset, offset + limit - 1)
            
            result = query.execute()
            
            if not result.data:
                return []
            
            organizations = []
            for org_data in result.data:
                org_data['member_count'] = await self.get_organization_member_count(org_data['organization_id'])
                organizations.append(OrganizationResponse(**org_data))
            
            return organizations
            
        except Exception as e:
            logger.error(f"Error listing all organizations: {e}")
            return []