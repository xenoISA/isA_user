"""
Invitation Service

邀请服务业务逻辑层
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import httpx

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from .invitation_repository import InvitationRepository
from .models import (
    InvitationStatus, OrganizationRole,
    InvitationResponse, InvitationDetailResponse, InvitationListResponse,
    AcceptInvitationResponse
)
from core.consul_registry import ConsulRegistry

logger = logging.getLogger(__name__)


class InvitationServiceError(Exception):
    """邀请服务异常"""
    pass


class InvitationService:
    """邀请服务"""

    def __init__(self):
        self.repository = InvitationRepository()
        self.invitation_base_url = "https://app.iapro.ai/accept-invitation"
        self.consul = None
        self._init_consul()

    def _init_consul(self):
        """Initialize Consul registry for service discovery"""
        try:
            from core.config_manager import ConfigManager
            config_manager = ConfigManager("invitation_service")
            config = config_manager.get_service_config()

            if config.consul_enabled:
                self.consul = ConsulRegistry(
                    service_name=config.service_name,
                    service_port=config.service_port,
                    consul_host=config.consul_host,
                    consul_port=config.consul_port
                )
                logger.info("Consul service discovery initialized for invitation service")
        except Exception as e:
            logger.warning(f"Failed to initialize Consul: {e}, will use fallback URLs")

    def _get_service_url(self, service_name: str, fallback_port: int) -> str:
        """Get service URL via Consul discovery with fallback"""
        fallback_url = f"http://localhost:{fallback_port}"
        if self.consul:
            return self.consul.get_service_address(service_name, fallback_url=fallback_url)
        return fallback_url
    
    # ============ Core Invitation Operations ============
    
    async def create_invitation(
        self, 
        organization_id: str,
        inviter_user_id: str,
        email: str,
        role: OrganizationRole,
        message: Optional[str] = None
    ) -> Tuple[bool, Optional[InvitationResponse], str]:
        """
        创建邀请
        
        Returns:
            Tuple[bool, Optional[InvitationResponse], str]: (成功标识, 邀请对象, 消息)
        """
        try:
            logger.info(f"Creating invitation for {email} to organization {organization_id}")
            
            # 验证组织是否存在
            if not await self._verify_organization_exists(organization_id, inviter_user_id):
                return False, None, "Organization not found"
            
            # 验证邀请人权限
            if not await self._verify_inviter_permissions(organization_id, inviter_user_id):
                return False, None, "You don't have permission to invite users to this organization"
            
            # 检查是否已有待处理邀请
            existing_invitation = await self.repository.get_pending_invitation_by_email_and_organization(
                email, organization_id
            )
            if existing_invitation:
                return False, None, "A pending invitation already exists for this email"
            
            # 检查用户是否已经是组织成员
            if await self._check_user_membership(organization_id, email):
                return False, None, "User is already a member of this organization"
            
            # 创建邀请
            invitation = await self.repository.create_invitation(
                organization_id=organization_id,
                email=email,
                role=role,
                invited_by=inviter_user_id
            )
            
            if not invitation:
                return False, None, "Failed to create invitation"
            
            # 发送邀请邮件（这里简化处理）
            email_sent = await self._send_invitation_email(invitation, message)
            
            logger.info(f"Invitation created: {invitation.invitation_id}, email_sent: {email_sent}")
            return True, invitation, "Invitation created successfully"
            
        except Exception as e:
            logger.error(f"Error creating invitation: {e}")
            return False, None, f"Failed to create invitation: {str(e)}"
    
    async def get_invitation_by_token(self, invitation_token: str) -> Tuple[bool, Optional[InvitationDetailResponse], str]:
        """根据令牌获取邀请信息"""
        try:
            # 获取邀请详细信息
            invitation_info = await self.repository.get_invitation_with_organization_info(invitation_token)
            if not invitation_info:
                return False, None, "Invitation not found"
            
            # 检查邀请状态
            if invitation_info['status'] != InvitationStatus.PENDING.value:
                return False, None, f"Invitation is {invitation_info['status']}"
            
            # 检查是否过期
            expires_at_str = invitation_info.get('expires_at')
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str.replace('Z', ''))
                if expires_at < datetime.utcnow():
                    # 更新状态为过期
                    await self.repository.update_invitation(invitation_info['invitation_id'], {
                        'status': InvitationStatus.EXPIRED.value
                    })
                    return False, None, "Invitation has expired"
            
            # 构建响应
            invitation_detail = InvitationDetailResponse(
                invitation_id=invitation_info['invitation_id'],
                organization_id=invitation_info['organization_id'],
                organization_name=invitation_info.get('organization_name', ''),
                organization_domain=invitation_info.get('organization_domain'),
                email=invitation_info['email'],
                role=OrganizationRole(invitation_info['role']),
                status=InvitationStatus(invitation_info['status']),
                inviter_name=invitation_info.get('inviter_name'),
                inviter_email=invitation_info.get('inviter_email'),
                expires_at=datetime.fromisoformat(expires_at_str) if expires_at_str else None,
                created_at=datetime.fromisoformat(invitation_info['created_at']) if invitation_info.get('created_at') else datetime.utcnow()
            )
            
            return True, invitation_detail, "Invitation found"
            
        except Exception as e:
            logger.error(f"Error getting invitation by token: {e}")
            return False, None, f"Failed to get invitation: {str(e)}"
    
    async def accept_invitation(
        self, 
        invitation_token: str, 
        user_id: str
    ) -> Tuple[bool, Optional[AcceptInvitationResponse], str]:
        """接受邀请"""
        try:
            logger.info(f"User {user_id} accepting invitation with token {invitation_token[:10]}...")
            
            # 获取邀请信息
            success, invitation_detail, message = await self.get_invitation_by_token(invitation_token)
            if not success:
                return False, None, message
            
            # 验证用户邮箱匹配
            if not await self._verify_user_email_match(user_id, invitation_detail.email):
                return False, None, "Email mismatch"
            
            # 接受邀请（更新状态）
            accept_success = await self.repository.accept_invitation(invitation_token)
            if not accept_success:
                return False, None, "Failed to accept invitation"
            
            # 添加用户到组织
            add_member_success = await self._add_user_to_organization(
                invitation_detail.organization_id,
                user_id,
                invitation_detail.role
            )
            
            if not add_member_success:
                # 回滚邀请状态
                await self.repository.update_invitation(invitation_detail.invitation_id, {
                    'status': InvitationStatus.PENDING.value,
                    'accepted_at': None
                })
                return False, None, "Failed to add user to organization"
            
            # 构建响应
            accept_response = AcceptInvitationResponse(
                invitation_id=invitation_detail.invitation_id,
                organization_id=invitation_detail.organization_id,
                organization_name=invitation_detail.organization_name,
                user_id=user_id,
                role=invitation_detail.role,
                accepted_at=datetime.utcnow()
            )
            
            logger.info(f"Invitation accepted: user_id={user_id}, org_id={invitation_detail.organization_id}")
            return True, accept_response, "Invitation accepted successfully"
            
        except Exception as e:
            logger.error(f"Error accepting invitation: {e}")
            return False, None, f"Failed to accept invitation: {str(e)}"
    
    async def get_organization_invitations(
        self, 
        organization_id: str,
        user_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[bool, Optional[InvitationListResponse], str]:
        """获取组织邀请列表"""
        try:
            # 验证用户权限
            if not await self._verify_inviter_permissions(organization_id, user_id):
                return False, None, "You don't have permission to view invitations for this organization"
            
            # 获取邀请列表
            invitations = await self.repository.get_organization_invitations(
                organization_id, limit, offset
            )
            
            # 获取总数（简化处理，使用当前批次大小）
            total = len(invitations)
            
            invitation_list = InvitationListResponse(
                invitations=invitations,
                total=total,
                limit=limit,
                offset=offset
            )
            
            return True, invitation_list, f"Found {len(invitations)} invitations"
            
        except Exception as e:
            logger.error(f"Error getting organization invitations: {e}")
            return False, None, f"Failed to get invitations: {str(e)}"
    
    async def cancel_invitation(
        self, 
        invitation_id: str, 
        user_id: str
    ) -> Tuple[bool, str]:
        """取消邀请"""
        try:
            # 获取邀请信息
            invitation = await self.repository.get_invitation_by_id(invitation_id)
            if not invitation:
                return False, "Invitation not found"
            
            # 检查权限（邀请人或组织管理员）
            if invitation.invited_by != user_id:
                if not await self._verify_inviter_permissions(invitation.organization_id, user_id):
                    return False, "You don't have permission to cancel this invitation"
            
            # 取消邀请
            success = await self.repository.cancel_invitation(invitation_id)
            
            if success:
                return True, "Invitation cancelled successfully"
            else:
                return False, "Failed to cancel invitation"
                
        except Exception as e:
            logger.error(f"Error cancelling invitation: {e}")
            return False, f"Failed to cancel invitation: {str(e)}"
    
    async def resend_invitation(
        self, 
        invitation_id: str, 
        user_id: str
    ) -> Tuple[bool, str]:
        """重发邀请"""
        try:
            # 获取邀请信息
            invitation = await self.repository.get_invitation_by_id(invitation_id)
            if not invitation:
                return False, "Invitation not found"
            
            # 检查权限
            if invitation.invited_by != user_id:
                if not await self._verify_inviter_permissions(invitation.organization_id, user_id):
                    return False, "You don't have permission to resend this invitation"
            
            # 检查邀请状态
            if invitation.status != InvitationStatus.PENDING:
                return False, f"Cannot resend {invitation.status.value} invitation"
            
            # 延长过期时间
            from datetime import timedelta
            new_expires_at = datetime.utcnow() + timedelta(days=7)
            await self.repository.update_invitation(invitation_id, {
                'expires_at': new_expires_at.isoformat()
            })
            
            # 重新发送邮件
            email_sent = await self._send_invitation_email(invitation)
            
            message = "Invitation resent successfully"
            if not email_sent:
                message += " (but email sending failed)"
            
            return True, message
            
        except Exception as e:
            logger.error(f"Error resending invitation: {e}")
            return False, f"Failed to resend invitation: {str(e)}"
    
    async def expire_old_invitations(self) -> Tuple[bool, int, str]:
        """过期旧邀请"""
        try:
            expired_count = await self.repository.expire_old_invitations()
            return True, expired_count, f"Expired {expired_count} old invitations"
            
        except Exception as e:
            logger.error(f"Error expiring old invitations: {e}")
            return False, 0, f"Failed to expire invitations: {str(e)}"
    
    # ============ Helper Methods ============
    
    async def _verify_organization_exists(self, organization_id: str, user_id: str) -> bool:
        """验证组织是否存在"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._get_service_url('organization_service', 8212)}/api/v1/organizations/{organization_id}",
                    headers={"X-User-Id": user_id}
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Error verifying organization exists: {e}")
            return False
    
    async def _verify_inviter_permissions(self, organization_id: str, user_id: str) -> bool:
        """验证邀请人权限"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._get_service_url('organization_service', 8212)}/api/v1/organizations/{organization_id}/members",
                    headers={"X-User-Id": user_id}
                )
                if response.status_code != 200:
                    return False
                
                data = response.json()
                members = data.get('members', [])
                
                # 查找用户的角色
                for member in members:
                    if member['user_id'] == user_id:
                        role = member.get('role', '').lower()
                        return role in ['owner', 'admin']
                
                return False
        except Exception as e:
            logger.error(f"Error verifying inviter permissions: {e}")
            return False
    
    async def _check_user_membership(self, organization_id: str, email: str) -> bool:
        """检查用户是否已经是组织成员"""
        try:
            # 这里简化实现，实际应该通过用户服务查询用户ID，然后检查成员关系
            # 为了demo，暂时返回False
            return False
        except Exception as e:
            logger.error(f"Error checking user membership: {e}")
            return False
    
    async def _verify_user_email_match(self, user_id: str, email: str) -> bool:
        """验证用户邮箱匹配"""
        try:
            # 这里应该调用用户服务来验证
            # 为了demo，暂时返回True
            return True
        except Exception as e:
            logger.error(f"Error verifying user email match: {e}")
            return False
    
    async def _add_user_to_organization(
        self, 
        organization_id: str, 
        user_id: str, 
        role: OrganizationRole
    ) -> bool:
        """添加用户到组织"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._get_service_url('organization_service', 8212)}/api/v1/organizations/{organization_id}/members",
                    headers={
                        "X-User-Id": "system",  # 系统级操作
                        "Content-Type": "application/json"
                    },
                    json={
                        "user_id": user_id,
                        "role": role.value,
                        "permissions": []
                    }
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Error adding user to organization: {e}")
            return False
    
    async def _send_invitation_email(
        self, 
        invitation: InvitationResponse, 
        message: Optional[str] = None
    ) -> bool:
        """发送邀请邮件"""
        try:
            # 这里应该集成邮件服务
            # 为了demo，简化实现
            invitation_link = f"{self.invitation_base_url}?token={invitation.invitation_token}"
            
            logger.info(f"Sending invitation email to {invitation.email}")
            logger.info(f"Invitation link: {invitation_link}")
            
            # 实际实现应该调用邮件服务
            return True
            
        except Exception as e:
            logger.error(f"Error sending invitation email: {e}")
            return False