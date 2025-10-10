"""
Invitation Repository

邀请数据访问层，负责所有数据库操作
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import uuid
import secrets
import json

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.database.supabase_client import get_supabase_client
from .models import (
    InvitationStatus, OrganizationRole,
    InvitationResponse, InvitationDetailResponse
)

logger = logging.getLogger(__name__)


class InvitationRepository:
    """邀请数据仓库"""
    
    def __init__(self):
        self.client = get_supabase_client()
        self.invitations_table = "organization_invitations"
    
    # ============ Invitation CRUD Operations ============
    
    async def create_invitation(
        self, 
        organization_id: str,
        email: str,
        role: OrganizationRole,
        invited_by: str
    ) -> Optional[InvitationResponse]:
        """创建邀请"""
        try:
            # 生成邀请ID和令牌
            invitation_id = str(uuid.uuid4())
            invitation_token = secrets.token_urlsafe(32)
            
            # 设置过期时间（7天）
            expires_at = datetime.utcnow() + timedelta(days=7)
            
            # 准备邀请数据
            invitation_dict = {
                'invitation_id': invitation_id,
                'organization_id': organization_id,
                'email': email,
                'role': role.value,
                'invited_by': invited_by,
                'invitation_token': invitation_token,
                'status': InvitationStatus.PENDING.value,
                'expires_at': expires_at.isoformat(),
            }
            
            # 创建邀请
            result = self.client.table(self.invitations_table).insert(invitation_dict).execute()
            
            if not result.data:
                logger.error("Failed to create invitation")
                return None
            
            invitation_data = result.data[0]
            return InvitationResponse(**invitation_data)
            
        except Exception as e:
            logger.error(f"Error creating invitation: {e}")
            return None
    
    async def get_invitation_by_id(self, invitation_id: str) -> Optional[InvitationResponse]:
        """根据ID获取邀请"""
        try:
            result = self.client.table(self.invitations_table).select('*').eq('invitation_id', invitation_id).execute()
            
            if not result.data or len(result.data) == 0:
                return None
            
            return InvitationResponse(**result.data[0])
            
        except Exception as e:
            logger.error(f"Error getting invitation by id: {e}")
            return None
    
    async def get_invitation_by_token(self, invitation_token: str) -> Optional[InvitationResponse]:
        """根据令牌获取邀请"""
        try:
            result = self.client.table(self.invitations_table).select('*').eq('invitation_token', invitation_token).execute()
            
            if not result.data or len(result.data) == 0:
                return None
            
            return InvitationResponse(**result.data[0])
            
        except Exception as e:
            logger.error(f"Error getting invitation by token: {e}")
            return None
    
    async def get_invitation_with_organization_info(self, invitation_token: str) -> Optional[Dict[str, Any]]:
        """获取邀请及组织信息"""
        try:
            # 由于Supabase客户端的限制，我们需要分步获取数据
            
            # 首先获取邀请信息
            invitation_result = self.client.table(self.invitations_table).select('*').eq('invitation_token', invitation_token).execute()
            
            if not invitation_result.data or len(invitation_result.data) == 0:
                return None
            
            invitation = invitation_result.data[0]
            
            # 获取组织信息
            org_result = self.client.table('organizations').select('name, domain').eq('organization_id', invitation['organization_id']).execute()
            
            # 获取邀请人信息
            user_result = self.client.table('users').select('name, email').eq('user_id', invitation['invited_by']).execute()
            
            # 合并数据
            result = invitation.copy()
            if org_result.data:
                result['organization_name'] = org_result.data[0].get('name')
                result['organization_domain'] = org_result.data[0].get('domain')
            
            if user_result.data:
                result['inviter_name'] = user_result.data[0].get('name')
                result['inviter_email'] = user_result.data[0].get('email')
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting invitation with organization info: {e}")
            return None
    
    async def get_pending_invitation_by_email_and_organization(
        self, 
        email: str, 
        organization_id: str
    ) -> Optional[InvitationResponse]:
        """根据邮箱和组织ID获取待处理邀请"""
        try:
            result = self.client.table(self.invitations_table).select('*').eq('email', email).eq('organization_id', organization_id).eq('status', InvitationStatus.PENDING.value).order('created_at', desc=True).limit(1).execute()
            
            if not result.data or len(result.data) == 0:
                return None
            
            return InvitationResponse(**result.data[0])
            
        except Exception as e:
            logger.error(f"Error getting pending invitation by email and organization: {e}")
            return None
    
    async def get_organization_invitations(
        self, 
        organization_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[InvitationDetailResponse]:
        """获取组织的邀请列表"""
        try:
            # 获取邀请列表
            invitations_result = self.client.table(self.invitations_table).select('*').eq('organization_id', organization_id).order('created_at', desc=True).range(offset, offset + limit - 1).execute()
            
            if not invitations_result.data:
                return []
            
            # 获取所有邀请人的用户ID
            invited_by_ids = list(set([inv['invited_by'] for inv in invitations_result.data]))
            
            # 批量获取用户信息
            users_map = {}
            if invited_by_ids:
                users_result = self.client.table('users').select('user_id, name, email').in_('user_id', invited_by_ids).execute()
                if users_result.data:
                    users_map = {user['user_id']: user for user in users_result.data}
            
            # 获取组织信息
            org_result = self.client.table('organizations').select('name, domain').eq('organization_id', organization_id).execute()
            org_name = org_result.data[0]['name'] if org_result.data else "Unknown"
            org_domain = org_result.data[0].get('domain') if org_result.data else None
            
            # 构建响应
            invitations = []
            for invitation_data in invitations_result.data:
                user_info = users_map.get(invitation_data['invited_by'], {})
                
                invitation_detail = InvitationDetailResponse(
                    invitation_id=invitation_data['invitation_id'],
                    organization_id=invitation_data['organization_id'],
                    organization_name=org_name,
                    organization_domain=org_domain,
                    email=invitation_data['email'],
                    role=OrganizationRole(invitation_data['role']),
                    status=InvitationStatus(invitation_data['status']),
                    inviter_name=user_info.get('name'),
                    inviter_email=user_info.get('email'),
                    expires_at=datetime.fromisoformat(invitation_data['expires_at']) if invitation_data.get('expires_at') else None,
                    created_at=datetime.fromisoformat(invitation_data['created_at']) if invitation_data.get('created_at') else datetime.utcnow()
                )
                invitations.append(invitation_detail)
            
            return invitations
            
        except Exception as e:
            logger.error(f"Error getting organization invitations: {e}")
            return []
    
    async def update_invitation(self, invitation_id: str, update_data: Dict[str, Any]) -> bool:
        """更新邀请"""
        try:
            # 添加updated_at
            update_data['updated_at'] = datetime.utcnow().isoformat()
            
            result = self.client.table(self.invitations_table).update(update_data).eq('invitation_id', invitation_id).execute()
            
            return result.data is not None and len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error updating invitation: {e}")
            return False
    
    async def accept_invitation(self, invitation_token: str) -> bool:
        """接受邀请"""
        try:
            now = datetime.utcnow()
            
            # 更新邀请状态为已接受，同时检查令牌和状态
            result = self.client.table(self.invitations_table).update({
                'status': InvitationStatus.ACCEPTED.value,
                'accepted_at': now.isoformat(),
                'updated_at': now.isoformat()
            }).eq('invitation_token', invitation_token).eq('status', InvitationStatus.PENDING.value).execute()
            
            return result.data is not None and len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error accepting invitation: {e}")
            return False
    
    async def cancel_invitation(self, invitation_id: str) -> bool:
        """取消邀请"""
        try:
            return await self.update_invitation(invitation_id, {
                'status': InvitationStatus.CANCELLED.value
            })
            
        except Exception as e:
            logger.error(f"Error cancelling invitation: {e}")
            return False
    
    async def expire_old_invitations(self) -> int:
        """过期旧邀请"""
        try:
            now = datetime.utcnow()
            
            # 更新过期的待处理邀请
            result = self.client.table(self.invitations_table).update({
                'status': InvitationStatus.EXPIRED.value,
                'updated_at': now.isoformat()
            }).eq('status', InvitationStatus.PENDING.value).lt('expires_at', now.isoformat()).execute()
            
            return len(result.data) if result.data else 0
            
        except Exception as e:
            logger.error(f"Error expiring old invitations: {e}")
            return 0
    
    async def delete_invitation(self, invitation_id: str) -> bool:
        """删除邀请"""
        try:
            result = self.client.table(self.invitations_table).delete().eq('invitation_id', invitation_id).execute()
            
            return result.data is not None and len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error deleting invitation: {e}")
            return False
    
    # ============ Statistics ============
    
    async def get_invitation_stats(self, organization_id: Optional[str] = None) -> Dict[str, int]:
        """获取邀请统计"""
        try:
            query = self.client.table(self.invitations_table).select('status')
            
            if organization_id:
                query = query.eq('organization_id', organization_id)
            
            result = query.execute()
            
            if not result.data:
                return {"total": 0, "pending": 0, "accepted": 0, "expired": 0, "cancelled": 0}
            
            stats = {"total": len(result.data), "pending": 0, "accepted": 0, "expired": 0, "cancelled": 0}
            
            for invitation in result.data:
                status = invitation['status']
                if status in stats:
                    stats[status] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting invitation stats: {e}")
            return {"total": 0, "pending": 0, "accepted": 0, "expired": 0, "cancelled": 0}