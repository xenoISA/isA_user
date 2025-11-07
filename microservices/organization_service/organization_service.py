"""
Organization Service

组织业务逻辑层
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from .organization_repository import OrganizationRepository
# Note: AccountServiceClient was removed as it was unused
# If user validation is needed, implement via microservice communication
from .models import (
    OrganizationCreateRequest, OrganizationUpdateRequest,
    OrganizationMemberAddRequest, OrganizationMemberUpdateRequest,
    OrganizationResponse, OrganizationMemberResponse,
    OrganizationListResponse, OrganizationMemberListResponse,
    OrganizationContextResponse, OrganizationStatsResponse,
    OrganizationUsageResponse, OrganizationRole, MemberStatus
)
# Import event bus components
from core.nats_client import Event, EventType, ServiceSource
from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class OrganizationServiceError(Exception):
    """组织服务异常基类"""
    pass


class OrganizationNotFoundError(OrganizationServiceError):
    """组织不存在异常"""
    pass


class OrganizationAccessDeniedError(OrganizationServiceError):
    """组织访问被拒绝异常"""
    pass


class OrganizationValidationError(OrganizationServiceError):
    """组织数据验证异常"""
    pass


class OrganizationService:
    """组织服务"""

    def __init__(self, event_bus=None, config: Optional[ConfigManager] = None):
        self.repository = OrganizationRepository(config=config)
        self.event_bus = event_bus
    
    # ============ Organization Management ============
    
    async def create_organization(
        self,
        request: OrganizationCreateRequest,
        owner_user_id: str
    ) -> OrganizationResponse:
        """创建组织"""
        try:
            # 验证数据
            if not request.name or not request.billing_email:
                raise OrganizationValidationError("Organization name and billing email are required")
            
            # 创建组织
            organization = await self.repository.create_organization(
                request.model_dump(exclude_none=True),
                owner_user_id
            )
            
            if not organization:
                raise OrganizationServiceError("Failed to create organization")

            logger.info(f"Organization created: {organization.organization_id} by user {owner_user_id}")

            # Publish organization.created event
            if self.event_bus:
                try:
                    event = Event(
                        event_type=EventType.ORG_CREATED,
                        source=ServiceSource.ORG_SERVICE,
                        data={
                            "organization_id": organization.organization_id,
                            "organization_name": organization.name,
                            "owner_user_id": owner_user_id,
                            "billing_email": organization.billing_email,
                            "plan": organization.plan,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    )
                    await self.event_bus.publish_event(event)
                    logger.info(f"Published organization.created event for organization {organization.organization_id}")
                except Exception as e:
                    logger.error(f"Failed to publish organization.created event: {e}")

            return organization
            
        except Exception as e:
            logger.error(f"Error creating organization: {e}")
            if isinstance(e, OrganizationServiceError):
                raise
            raise OrganizationServiceError(f"Failed to create organization: {str(e)}")
    
    async def get_organization(
        self,
        organization_id: str,
        user_id: Optional[str] = None
    ) -> OrganizationResponse:
        """获取组织信息"""
        try:
            # 如果提供了user_id，验证访问权限（内部服务调用跳过检查）
            if user_id and user_id != "internal-service":
                has_access = await self.check_user_access(organization_id, user_id)
                if not has_access:
                    raise OrganizationAccessDeniedError(f"User {user_id} does not have access to organization {organization_id}")
            
            organization = await self.repository.get_organization(organization_id)
            
            if not organization:
                raise OrganizationNotFoundError(f"Organization {organization_id} not found")
            
            return organization
            
        except Exception as e:
            logger.error(f"Error getting organization {organization_id}: {e}")
            if isinstance(e, OrganizationServiceError):
                raise
            raise OrganizationServiceError(f"Failed to get organization: {str(e)}")
    
    async def update_organization(
        self,
        organization_id: str,
        request: OrganizationUpdateRequest,
        user_id: str
    ) -> OrganizationResponse:
        """更新组织信息（需要管理员权限）"""
        try:
            # 检查权限
            is_admin = await self.check_admin_access(organization_id, user_id)
            if not is_admin:
                raise OrganizationAccessDeniedError(f"User {user_id} does not have admin access to organization {organization_id}")
            
            # 更新组织
            organization = await self.repository.update_organization(
                organization_id,
                request.model_dump(exclude_none=True)
            )
            
            if not organization:
                raise OrganizationNotFoundError(f"Organization {organization_id} not found")

            # Publish organization.updated event
            if self.event_bus:
                try:
                    event = Event(
                        event_type=EventType.ORG_UPDATED,
                        source=ServiceSource.ORG_SERVICE,
                        data={
                            "organization_id": organization_id,
                            "organization_name": organization.name,
                            "updated_by": user_id,
                            "updated_fields": list(request.model_dump(exclude_none=True).keys()),
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    )
                    await self.event_bus.publish_event(event)
                    logger.info(f"Published organization.updated event for organization {organization_id}")
                except Exception as e:
                    logger.error(f"Failed to publish organization.updated event: {e}")

            logger.info(f"Organization {organization_id} updated by user {user_id}")
            return organization

        except Exception as e:
            logger.error(f"Error updating organization {organization_id}: {e}")
            if isinstance(e, OrganizationServiceError):
                raise
            raise OrganizationServiceError(f"Failed to update organization: {str(e)}")
    
    async def delete_organization(
        self,
        organization_id: str,
        user_id: str
    ) -> bool:
        """删除组织（需要所有者权限）"""
        try:
            # 检查权限
            is_owner = await self.check_owner_access(organization_id, user_id)
            if not is_owner:
                raise OrganizationAccessDeniedError(f"User {user_id} is not the owner of organization {organization_id}")
            
            # Get organization details before deletion for event
            organization = await self.repository.get_organization(organization_id)
            if not organization:
                raise OrganizationNotFoundError(f"Organization {organization_id} not found")

            # 删除组织
            success = await self.repository.delete_organization(organization_id)

            if success:
                # Publish organization.deleted event
                if self.event_bus:
                    try:
                        event = Event(
                            event_type=EventType.ORG_DELETED,
                            source=ServiceSource.ORG_SERVICE,
                            data={
                                "organization_id": organization_id,
                                "organization_name": organization.name,
                                "deleted_by": user_id,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }
                        )
                        await self.event_bus.publish_event(event)
                        logger.info(f"Published organization.deleted event for organization {organization_id}")
                    except Exception as e:
                        logger.error(f"Failed to publish organization.deleted event: {e}")

                logger.info(f"Organization {organization_id} deleted by user {user_id}")

            return success
            
        except Exception as e:
            logger.error(f"Error deleting organization {organization_id}: {e}")
            if isinstance(e, OrganizationServiceError):
                raise
            raise OrganizationServiceError(f"Failed to delete organization: {str(e)}")
    
    async def get_user_organizations(
        self,
        user_id: str
    ) -> OrganizationListResponse:
        """获取用户所属的所有组织"""
        try:
            organizations_data = await self.repository.get_user_organizations(user_id)
            
            organizations = [OrganizationResponse(**org) for org in organizations_data]
            
            return OrganizationListResponse(
                organizations=organizations,
                total=len(organizations),
                limit=100,
                offset=0
            )
            
        except Exception as e:
            logger.error(f"Error getting organizations for user {user_id}: {e}")
            raise OrganizationServiceError(f"Failed to get user organizations: {str(e)}")
    
    # ============ Member Management ============
    
    async def add_organization_member(
        self,
        organization_id: str,
        request: OrganizationMemberAddRequest,
        requesting_user_id: str
    ) -> OrganizationMemberResponse:
        """添加组织成员（需要管理员权限）"""
        try:
            # 检查权限
            is_admin = await self.check_admin_access(organization_id, requesting_user_id)
            if not is_admin:
                raise OrganizationAccessDeniedError(f"User {requesting_user_id} does not have admin access")

            # 验证请求
            if not request.user_id and not request.email:
                raise OrganizationValidationError("Either user_id or email must be provided")

            # 如果只有邮箱，需要先创建邀请（暂不实现）
            if not request.user_id:
                raise OrganizationServiceError("User invitation not implemented yet. Please provide user_id of existing user.")

            # Validate member user exists in account service (fail-open for eventual consistency)
            # Note: For synchronous validation in async context, we'd need to refactor.
            # For now, we'll allow the operation (eventual consistency)
            logger.info(f"Adding member {request.user_id} to organization {organization_id}")

            # 添加成员
            member = await self.repository.add_organization_member(
                organization_id,
                request.user_id,
                request.role,
                request.permissions
            )

            if not member:
                raise OrganizationServiceError("Failed to add member")

            logger.info(f"Member {request.user_id} added to organization {organization_id} with role {request.role}")

            # Publish organization.member_added event
            if self.event_bus:
                try:
                    event = Event(
                        event_type=EventType.ORG_MEMBER_ADDED,
                        source=ServiceSource.ORG_SERVICE,
                        data={
                            "organization_id": organization_id,
                            "user_id": request.user_id,
                            "role": request.role.value if hasattr(request.role, 'value') else request.role,
                            "added_by": requesting_user_id,
                            "permissions": request.permissions or [],
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    )
                    await self.event_bus.publish_event(event)
                    logger.info(f"Published organization.member_added event for user {request.user_id}")
                except Exception as e:
                    logger.error(f"Failed to publish organization.member_added event: {e}")

            return member

        except Exception as e:
            logger.error(f"Error adding member to organization {organization_id}: {e}")
            if isinstance(e, OrganizationServiceError):
                raise
            raise OrganizationServiceError(f"Failed to add member: {str(e)}")
    
    async def update_organization_member(
        self,
        organization_id: str,
        member_user_id: str,
        request: OrganizationMemberUpdateRequest,
        requesting_user_id: str
    ) -> OrganizationMemberResponse:
        """更新组织成员（需要管理员权限）"""
        try:
            # 检查权限
            is_admin = await self.check_admin_access(organization_id, requesting_user_id)
            if not is_admin:
                raise OrganizationAccessDeniedError(f"User {requesting_user_id} does not have admin access")
            
            # 获取目标用户当前角色
            target_role = await self.repository.get_user_organization_role(organization_id, member_user_id)
            if not target_role:
                raise OrganizationNotFoundError(f"Member {member_user_id} not found in organization")
            
            # 检查权限规则
            requesting_role = await self.repository.get_user_organization_role(organization_id, requesting_user_id)
            if requesting_role['role'] == 'admin' and target_role['role'] in ['owner', 'admin']:
                raise OrganizationAccessDeniedError("Admins cannot modify owners or other admins")
            
            # 更新成员
            member = await self.repository.update_organization_member(
                organization_id,
                member_user_id,
                request.model_dump(exclude_none=True)
            )
            
            if not member:
                raise OrganizationServiceError("Failed to update member")
            
            logger.info(f"Member {member_user_id} updated in organization {organization_id}")
            return member
            
        except Exception as e:
            logger.error(f"Error updating member {member_user_id} in organization {organization_id}: {e}")
            if isinstance(e, OrganizationServiceError):
                raise
            raise OrganizationServiceError(f"Failed to update member: {str(e)}")
    
    async def remove_organization_member(
        self,
        organization_id: str,
        member_user_id: str,
        requesting_user_id: str
    ) -> bool:
        """移除组织成员"""
        try:
            # 获取角色
            requesting_role = await self.repository.get_user_organization_role(organization_id, requesting_user_id)
            if not requesting_role:
                raise OrganizationAccessDeniedError(f"User {requesting_user_id} is not a member of organization")
            
            target_role = await self.repository.get_user_organization_role(organization_id, member_user_id)
            if not target_role:
                raise OrganizationNotFoundError(f"Member {member_user_id} not found in organization")
            
            # 检查权限
            if requesting_role['role'] == 'admin':
                if target_role['role'] in ['owner', 'admin']:
                    raise OrganizationAccessDeniedError("Admins cannot remove owners or other admins")
            elif requesting_role['role'] == 'owner':
                # 所有者可以移除任何人，但不能移除最后一个所有者
                if target_role['role'] == 'owner':
                    members = await self.repository.get_organization_members(
                        organization_id, 
                        role_filter=OrganizationRole.OWNER
                    )
                    if len(members) <= 1:
                        raise OrganizationValidationError("Cannot remove the last owner from organization")
            else:
                # 普通成员只能移除自己
                if requesting_user_id != member_user_id:
                    raise OrganizationAccessDeniedError("Members can only remove themselves")
            
            # 移除成员
            success = await self.repository.remove_organization_member(organization_id, member_user_id)

            if success:
                logger.info(f"Member {member_user_id} removed from organization {organization_id}")

                # Publish organization.member_removed event
                if self.event_bus:
                    try:
                        event = Event(
                            event_type=EventType.ORG_MEMBER_REMOVED,
                            source=ServiceSource.ORG_SERVICE,
                            data={
                                "organization_id": organization_id,
                                "user_id": member_user_id,
                                "removed_by": requesting_user_id,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }
                        )
                        await self.event_bus.publish_event(event)
                        logger.info(f"Published organization.member_removed event for user {member_user_id}")
                    except Exception as e:
                        logger.error(f"Failed to publish organization.member_removed event: {e}")

            return success
            
        except Exception as e:
            logger.error(f"Error removing member {member_user_id} from organization {organization_id}: {e}")
            if isinstance(e, OrganizationServiceError):
                raise
            raise OrganizationServiceError(f"Failed to remove member: {str(e)}")
    
    async def get_organization_members(
        self,
        organization_id: str,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
        role_filter: Optional[OrganizationRole] = None
    ) -> OrganizationMemberListResponse:
        """获取组织成员列表"""
        try:
            # 检查访问权限（内部服务调用跳过检查）

            if user_id != "internal-service":

                has_access = await self.check_user_access(organization_id, user_id)

                if not has_access:

                    raise OrganizationAccessDeniedError(f"User {user_id} does not have access to organization")
            
            members = await self.repository.get_organization_members(
                organization_id,
                limit,
                offset,
                role_filter
            )
            
            return OrganizationMemberListResponse(
                members=members,
                total=len(members),
                limit=limit,
                offset=offset
            )
            
        except Exception as e:
            logger.error(f"Error getting members for organization {organization_id}: {e}")
            if isinstance(e, OrganizationServiceError):
                raise
            raise OrganizationServiceError(f"Failed to get organization members: {str(e)}")
    
    # ============ Context Switching ============
    
    async def switch_user_context(
        self,
        user_id: str,
        organization_id: Optional[str] = None
    ) -> OrganizationContextResponse:
        """切换用户上下文（组织或个人）"""
        try:
            if organization_id:
                # 切换到组织上下文
                role_data = await self.repository.get_user_organization_role(organization_id, user_id)
                if not role_data:
                    raise OrganizationAccessDeniedError(f"User is not a member of organization {organization_id}")
                
                if role_data['status'] != MemberStatus.ACTIVE.value:
                    raise OrganizationAccessDeniedError("User membership is not active")
                
                org = await self.repository.get_organization(organization_id)
                if not org:
                    raise OrganizationNotFoundError(f"Organization {organization_id} not found")
                
                return OrganizationContextResponse(
                    context_type="organization",
                    organization_id=organization_id,
                    organization_name=org.name,
                    user_role=OrganizationRole(role_data['role']),
                    permissions=role_data['permissions'],
                    credits_available=org.credits_pool
                )
            else:
                # 切换到个人上下文
                return OrganizationContextResponse(
                    context_type="individual",
                    organization_id=None,
                    organization_name=None,
                    user_role=None,
                    permissions=[],
                    credits_available=None
                )
                
        except Exception as e:
            logger.error(f"Error switching context for user {user_id}: {e}")
            if isinstance(e, OrganizationServiceError):
                raise
            raise OrganizationServiceError(f"Failed to switch context: {str(e)}")
    
    # ============ Statistics and Analytics ============
    
    async def get_organization_stats(
        self,
        organization_id: str,
        user_id: str
    ) -> OrganizationStatsResponse:
        """获取组织统计信息"""
        try:
            # 检查访问权限（内部服务调用跳过检查）

            if user_id != "internal-service":

                has_access = await self.check_user_access(organization_id, user_id)

                if not has_access:

                    raise OrganizationAccessDeniedError(f"User {user_id} does not have access to organization")
            
            stats_data = await self.repository.get_organization_stats(organization_id)
            
            return OrganizationStatsResponse(**stats_data)
            
        except Exception as e:
            logger.error(f"Error getting stats for organization {organization_id}: {e}")
            if isinstance(e, OrganizationServiceError):
                raise
            raise OrganizationServiceError(f"Failed to get organization stats: {str(e)}")
    
    async def get_organization_usage(
        self,
        organization_id: str,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> OrganizationUsageResponse:
        """获取组织使用量信息"""
        try:
            # 检查管理员权限
            is_admin = await self.check_admin_access(organization_id, user_id)
            if not is_admin:
                raise OrganizationAccessDeniedError(f"User {user_id} does not have admin access")
            
            # TODO: 从其他服务获取实际使用量数据
            # 现在返回模拟数据
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = datetime(end_date.year, end_date.month, 1)
            
            return OrganizationUsageResponse(
                organization_id=organization_id,
                period_start=start_date,
                period_end=end_date,
                credits_consumed=0,
                api_calls=0,
                storage_gb_hours=0.0,
                active_users=0,
                top_users=[],
                usage_by_service={}
            )
            
        except Exception as e:
            logger.error(f"Error getting usage for organization {organization_id}: {e}")
            if isinstance(e, OrganizationServiceError):
                raise
            raise OrganizationServiceError(f"Failed to get organization usage: {str(e)}")
    
    # ============ Access Control Helpers ============
    
    async def check_user_access(self, organization_id: str, user_id: str) -> bool:
        """检查用户是否有组织访问权限"""
        try:
            role_data = await self.repository.get_user_organization_role(organization_id, user_id)
            return role_data is not None and role_data['status'] == MemberStatus.ACTIVE.value
        except Exception:
            return False
    
    async def check_admin_access(self, organization_id: str, user_id: str) -> bool:
        """检查用户是否有管理员权限"""
        try:
            role_data = await self.repository.get_user_organization_role(organization_id, user_id)
            return (
                role_data is not None and 
                role_data['status'] == MemberStatus.ACTIVE.value and
                role_data['role'] in ['owner', 'admin']
            )
        except Exception:
            return False
    
    async def check_owner_access(self, organization_id: str, user_id: str) -> bool:
        """检查用户是否是所有者"""
        try:
            role_data = await self.repository.get_user_organization_role(organization_id, user_id)
            return (
                role_data is not None and 
                role_data['status'] == MemberStatus.ACTIVE.value and
                role_data['role'] == 'owner'
            )
        except Exception:
            return False
    
    # ============ Platform Admin Operations ============
    
    async def list_all_organizations(
        self,
        limit: int = 100,
        offset: int = 0,
        search: Optional[str] = None,
        plan_filter: Optional[str] = None,
        status_filter: Optional[str] = None
    ) -> OrganizationListResponse:
        """获取所有组织列表（平台管理员）"""
        try:
            organizations = await self.repository.list_all_organizations(
                limit, offset, search, plan_filter, status_filter
            )
            
            return OrganizationListResponse(
                organizations=organizations,
                total=len(organizations),
                limit=limit,
                offset=offset
            )
            
        except Exception as e:
            logger.error(f"Error listing all organizations: {e}")
            raise OrganizationServiceError(f"Failed to list organizations: {str(e)}")