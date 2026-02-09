"""
Authorization Service with Dependency Injection

Business logic layer for the authorization microservice.
Provides comprehensive resource authorization and permission management.

This service uses dependency injection for all external dependencies:
- Repository is injected (not created at import time)
- Event bus is injected (optional)
"""

import logging
import asyncio
from typing import TYPE_CHECKING, Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid

# Import protocols (no I/O dependencies) - NOT the concrete repository!
from .protocols import (
    AuthorizationRepositoryProtocol,
    EventBusProtocol,
    AuthorizationException,
    PermissionNotFoundException,
    UserNotFoundException,
    OrganizationNotFoundException,
    InvalidPermissionError,
)
from .models import (
    ResourcePermission, UserPermissionRecord, OrganizationPermission,
    ResourceType, AccessLevel, PermissionSource, SubscriptionTier,
    ResourceAccessRequest, ResourceAccessResponse,
    GrantPermissionRequest, RevokePermissionRequest,
    UserPermissionSummary, BulkPermissionRequest,
    BatchOperationResult, BatchOperationSummary,
    PermissionAuditLog, AuthorizationError
)

# Type checking imports (not executed at runtime)
if TYPE_CHECKING:
    from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class AuthorizationService:
    """Core authorization service with business logic - using dependency injection"""

    def __init__(
        self,
        repository: Optional[AuthorizationRepositoryProtocol] = None,
        event_bus: Optional[EventBusProtocol] = None,
        config: Optional["ConfigManager"] = None,
    ):
        """
        Initialize authorization service with injected dependencies.

        Args:
            repository: Authorization repository (inject mock for testing)
            event_bus: Event bus for publishing events (optional)
            config: Configuration manager (optional, for backwards compatibility)
        """
        self.repository = repository  # Will be set by factory if None
        self.event_bus = event_bus

        # Subscription tier hierarchy for access control
        self.subscription_hierarchy = {
            SubscriptionTier.FREE: 0,
            SubscriptionTier.PRO: 1,
            SubscriptionTier.ENTERPRISE: 2,
            SubscriptionTier.CUSTOM: 3
        }
        
        # Access level hierarchy
        self.access_level_hierarchy = {
            AccessLevel.NONE: 0,
            AccessLevel.READ_ONLY: 1,
            AccessLevel.READ_WRITE: 2,
            AccessLevel.ADMIN: 3,
            AccessLevel.OWNER: 4
        }
    
    # ====================
    # Core Authorization Logic
    # ====================
    
    async def check_resource_access(self, request: ResourceAccessRequest) -> ResourceAccessResponse:
        """
        Check if user has access to a specific resource
        
        Priority order:
        1. Admin-granted permissions (highest priority)
        2. Organization permissions
        3. Subscription-based permissions
        4. Default/system permissions
        """
        try:
            user_id = request.user_id
            resource_type = request.resource_type
            resource_name = request.resource_name
            required_level = request.required_access_level
            organization_id = request.organization_id
            
            logger.debug(f"Checking access: user={user_id}, resource={resource_type}:{resource_name}, level={required_level}")
            
            # Get user information
            user_info = await self.repository.get_user_info(user_id)
            if not user_info or not user_info.is_active:
                return ResourceAccessResponse(
                    has_access=False,
                    user_access_level=AccessLevel.NONE,
                    permission_source=PermissionSource.SYSTEM_DEFAULT,
                    subscription_tier=None,
                    organization_plan=None,
                    reason="User not found or inactive",
                    metadata={"user_id": user_id}
                )
            
            # 1. Check admin-granted permissions (highest priority)
            admin_permission = await self.repository.get_user_permission(user_id, resource_type, resource_name)
            if admin_permission and admin_permission.permission_source == PermissionSource.ADMIN_GRANT:
                if self._has_sufficient_access(admin_permission.access_level, required_level):
                    await self._log_access_check(user_id, resource_type, resource_name, "grant", True, "Admin permission")
                    return ResourceAccessResponse(
                        has_access=True,
                        user_access_level=admin_permission.access_level,
                        permission_source=PermissionSource.ADMIN_GRANT,
                        subscription_tier=user_info.subscription_status,
                        organization_plan=None,
                        reason=f"Admin-granted permission: {admin_permission.access_level.value}",
                        expires_at=admin_permission.expires_at,
                        metadata={"granted_by": admin_permission.granted_by_user_id}
                    )
            
            # 2. Check organization permissions
            if organization_id or user_info.organization_id:
                org_id = organization_id or user_info.organization_id
                org_access = await self._check_organization_access(
                    user_id, org_id, resource_type, resource_name, required_level
                )
                if org_access.has_access:
                    await self._log_access_check(user_id, resource_type, resource_name, "grant", True, "Organization permission")
                    return org_access
            
            # 3. Check subscription-based permissions
            subscription_access = await self._check_subscription_access(
                user_id, user_info.subscription_status, resource_type, resource_name, required_level
            )
            if subscription_access.has_access:
                await self._log_access_check(user_id, resource_type, resource_name, "grant", True, "Subscription permission")
                return subscription_access
            
            # 4. Check user-specific permissions (non-admin)
            user_permission = await self.repository.get_user_permission(user_id, resource_type, resource_name)
            if user_permission and user_permission.permission_source != PermissionSource.ADMIN_GRANT:
                if self._has_sufficient_access(user_permission.access_level, required_level):
                    await self._log_access_check(user_id, resource_type, resource_name, "grant", True, "User-specific permission")
                    return ResourceAccessResponse(
                        has_access=True,
                        user_access_level=user_permission.access_level,
                        permission_source=user_permission.permission_source,
                        subscription_tier=user_info.subscription_status,
                        organization_plan=None,
                        reason=f"User permission: {user_permission.access_level.value}",
                        expires_at=user_permission.expires_at,
                        metadata={"permission_id": user_permission.id}
                    )
            
            # 5. Access denied
            await self._log_access_check(user_id, resource_type, resource_name, "deny", False, "Insufficient permissions")

            # Publish access denied event
            if self.event_bus:
                try:
                    # Try to import Event classes, fall back to dict if not available
                    try:
                        from core.nats_client import Event

                        event = Event(
                            event_type="authorization.access.denied",
                            source="authorization_service",
                            data={
                                "user_id": user_id,
                                "resource_type": resource_type.value,
                                "resource_name": resource_name,
                                "required_access_level": required_level.value,
                                "reason": "Insufficient permissions",
                                "timestamp": datetime.utcnow().isoformat()
                            }
                        )
                    except ImportError:
                        # Fall back to simple dict-based event for testing
                        event = {
                            "event_type": "access.denied",
                            "source": "authorization_service",
                            "data": {
                                "user_id": user_id,
                                "resource_type": resource_type.value,
                                "resource_name": resource_name,
                                "required_access_level": required_level.value,
                                "reason": "Insufficient permissions",
                                "timestamp": datetime.utcnow().isoformat()
                            }
                        }

                    await self.event_bus.publish_event(event)
                except Exception as e:
                    logger.error(f"Failed to publish access.denied event: {e}")

            return ResourceAccessResponse(
                has_access=False,
                user_access_level=AccessLevel.NONE,
                permission_source=PermissionSource.SYSTEM_DEFAULT,
                subscription_tier=user_info.subscription_status,
                organization_plan=None,
                reason=f"Insufficient permissions for {resource_type.value}:{resource_name}, required: {required_level.value}",
                metadata={"required_level": required_level.value}
            )
            
        except Exception as e:
            logger.error(f"Error checking resource access: {e}")
            await self._log_access_check(user_id, resource_type, resource_name, "error", False, str(e))
            return ResourceAccessResponse(
                has_access=False,
                user_access_level=AccessLevel.NONE,
                permission_source=PermissionSource.SYSTEM_DEFAULT,
                subscription_tier="unknown",
                organization_plan=None,
                reason=f"Access check failed: {str(e)}",
                metadata={"error": str(e)}
            )
    
    async def _check_organization_access(self, user_id: str, organization_id: str,
                                       resource_type: ResourceType, resource_name: str,
                                       required_level: AccessLevel) -> ResourceAccessResponse:
        """Check organization-based access"""
        try:
            # Verify user is organization member
            if not await self.repository.is_user_organization_member(user_id, organization_id):
                return ResourceAccessResponse(
                    has_access=False,
                    user_access_level=AccessLevel.NONE,
                    permission_source=PermissionSource.ORGANIZATION,
                    reason="User is not a member of the organization"
                )
            
            # Get organization info
            org_info = await self.repository.get_organization_info(organization_id)
            if not org_info or not org_info.is_active:
                return ResourceAccessResponse(
                    has_access=False,
                    user_access_level=AccessLevel.NONE,
                    permission_source=PermissionSource.ORGANIZATION,
                    reason="Organization not found or inactive"
                )
            
            # Check organization-specific permission
            org_permission = await self.repository.get_organization_permission(organization_id, resource_type, resource_name)
            if org_permission:
                # Check if organization plan meets requirements
                if self._organization_plan_sufficient(org_info.plan, org_permission.org_plan_required):
                    if self._has_sufficient_access(org_permission.access_level, required_level):
                        return ResourceAccessResponse(
                            has_access=True,
                            user_access_level=org_permission.access_level,
                            permission_source=PermissionSource.ORGANIZATION,
                            organization_plan=org_info.plan,
                            reason=f"Organization permission: {org_permission.access_level.value}",
                            metadata={
                                "organization_id": organization_id,
                                "org_plan": org_info.plan,
                                "plan_required": org_permission.org_plan_required
                            }
                        )
            
            return ResourceAccessResponse(
                has_access=False,
                user_access_level=AccessLevel.NONE,
                permission_source=PermissionSource.ORGANIZATION,
                organization_plan=org_info.plan,
                reason="Organization does not have sufficient permissions for this resource"
            )
            
        except Exception as e:
            logger.error(f"Error checking organization access: {e}")
            return ResourceAccessResponse(
                has_access=False,
                user_access_level=AccessLevel.NONE,
                permission_source=PermissionSource.ORGANIZATION,
                reason=f"Organization access check failed: {str(e)}"
            )
    
    async def _check_subscription_access(self, user_id: str, subscription_status: str,
                                       resource_type: ResourceType, resource_name: str,
                                       required_level: AccessLevel) -> ResourceAccessResponse:
        """Check subscription-based access"""
        try:
            logger.info(f"Checking subscription access for user={user_id}, subscription={subscription_status}, resource={resource_type.value}:{resource_name}")
            
            # Get resource permission configuration
            resource_permission = await self.repository.get_resource_permission(resource_type, resource_name)
            if not resource_permission:
                logger.warning(f"No resource configuration found for {resource_type.value}:{resource_name}")
                return ResourceAccessResponse(
                    has_access=False,
                    user_access_level=AccessLevel.NONE,
                    permission_source=PermissionSource.SUBSCRIPTION,
                    subscription_tier=subscription_status,
                    reason="Resource not configured for subscription access"
                )
            
            logger.info(f"Resource config found: subscription_required={resource_permission.subscription_tier_required.value}, access_level={resource_permission.access_level.value}")
            
            # Check if user's subscription meets requirements
            user_tier = SubscriptionTier(subscription_status) if subscription_status in [t.value for t in SubscriptionTier] else SubscriptionTier.FREE
            logger.info(f"User tier: {user_tier.value}, Required tier: {resource_permission.subscription_tier_required.value}")
            
            tier_sufficient = self._subscription_tier_sufficient(user_tier, resource_permission.subscription_tier_required)
            logger.info(f"Subscription tier sufficient: {tier_sufficient}")
            
            if tier_sufficient:
                access_sufficient = self._has_sufficient_access(resource_permission.access_level, required_level)
                logger.info(f"Access level sufficient: {access_sufficient} (user={resource_permission.access_level.value}, required={required_level.value})")
                
                if access_sufficient:
                    logger.info(f"GRANTING subscription access for {user_id}")
                    return ResourceAccessResponse(
                        has_access=True,
                        user_access_level=resource_permission.access_level,
                        permission_source=PermissionSource.SUBSCRIPTION,
                        subscription_tier=subscription_status,
                        reason=f"Subscription access: {resource_permission.access_level.value}",
                        metadata={
                            "subscription_required": resource_permission.subscription_tier_required.value,
                            "resource_category": resource_permission.resource_category
                        }
                    )
                else:
                    logger.info(f"DENYING access - insufficient access level")
            else:
                logger.info(f"DENYING access - insufficient subscription tier")
            
            return ResourceAccessResponse(
                has_access=False,
                user_access_level=AccessLevel.NONE,
                permission_source=PermissionSource.SUBSCRIPTION,
                subscription_tier=subscription_status,
                reason=f"Subscription tier '{subscription_status}' insufficient, requires '{resource_permission.subscription_tier_required.value}'"
            )
            
        except Exception as e:
            logger.error(f"Error checking subscription access: {e}")
            return ResourceAccessResponse(
                has_access=False,
                user_access_level=AccessLevel.NONE,
                permission_source=PermissionSource.SUBSCRIPTION,
                subscription_tier=subscription_status,
                reason=f"Subscription access check failed: {str(e)}"
            )
    
    # ====================
    # Permission Management
    # ====================
    
    async def grant_resource_permission(self, request: GrantPermissionRequest) -> bool:
        """Grant resource permission to a user"""
        try:
            # Validate user exists
            user_info = await self.repository.get_user_info(request.user_id)
            if not user_info:
                logger.error(f"Cannot grant permission to non-existent user: {request.user_id}")
                return False
            
            # Create permission record
            permission = UserPermissionRecord(
                user_id=request.user_id,
                resource_type=request.resource_type,
                resource_name=request.resource_name,
                access_level=request.access_level,
                permission_source=request.permission_source,
                granted_by_user_id=request.granted_by_user_id,
                organization_id=request.organization_id,
                expires_at=request.expires_at,
                is_active=True
            )
            
            result = await self.repository.grant_user_permission(permission)
            
            if result:
                # Log the action
                await self._log_permission_action(
                    user_id=request.user_id,
                    resource_type=request.resource_type,
                    resource_name=request.resource_name,
                    action="grant",
                    new_access_level=request.access_level,
                    performed_by_user_id=request.granted_by_user_id,
                    reason=request.reason,
                    success=True
                )

                # Publish permission granted event
                if self.event_bus:
                    try:
                        # Try to import Event classes, fall back to dict if not available
                        try:
                            from core.nats_client import Event

                            event = Event(
                                event_type="authorization.permission.granted",
                                source="authorization_service",
                                data={
                                    "user_id": request.user_id,
                                    "resource_type": request.resource_type.value,
                                    "resource_name": request.resource_name,
                                    "access_level": request.access_level.value,
                                    "permission_source": request.permission_source.value,
                                    "granted_by_user_id": request.granted_by_user_id,
                                    "organization_id": request.organization_id,
                                    "timestamp": datetime.utcnow().isoformat()
                                }
                            )
                        except ImportError:
                            # Fall back to simple dict-based event for testing
                            event = {
                                "event_type": "permission.granted",
                                "source": "authorization_service",
                                "data": {
                                    "user_id": request.user_id,
                                    "resource_type": request.resource_type.value,
                                    "resource_name": request.resource_name,
                                    "access_level": request.access_level.value,
                                    "permission_source": request.permission_source.value,
                                    "granted_by_user_id": request.granted_by_user_id,
                                    "organization_id": request.organization_id,
                                    "timestamp": datetime.utcnow().isoformat()
                                }
                            }

                        await self.event_bus.publish_event(event)
                    except Exception as e:
                        logger.error(f"Failed to publish permission.granted event: {e}")

                logger.info(f"Granted permission: user={request.user_id}, resource={request.resource_type}:{request.resource_name}, level={request.access_level}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error granting resource permission: {e}")
            
            # Log the failed action
            await self._log_permission_action(
                user_id=request.user_id,
                resource_type=request.resource_type,
                resource_name=request.resource_name,
                action="grant",
                new_access_level=request.access_level,
                performed_by_user_id=request.granted_by_user_id,
                reason=request.reason,
                success=False,
                error_message=str(e)
            )
            
            return False
    
    async def revoke_resource_permission(self, request: RevokePermissionRequest) -> bool:
        """Revoke resource permission from a user"""
        try:
            # Get current permission for logging
            current_permission = await self.repository.get_user_permission(
                request.user_id, request.resource_type, request.resource_name
            )
            
            result = await self.repository.revoke_user_permission(
                request.user_id, request.resource_type, request.resource_name
            )
            
            if result:
                # Log the action
                await self._log_permission_action(
                    user_id=request.user_id,
                    resource_type=request.resource_type,
                    resource_name=request.resource_name,
                    action="revoke",
                    old_access_level=current_permission.access_level if current_permission else None,
                    performed_by_user_id=request.revoked_by_user_id,
                    reason=request.reason,
                    success=True
                )

                # Publish permission revoked event
                if self.event_bus:
                    try:
                        # Try to import Event classes, fall back to dict if not available
                        try:
                            from core.nats_client import Event

                            event = Event(
                                event_type="authorization.permission.revoked",
                                source="authorization_service",
                                data={
                                    "user_id": request.user_id,
                                    "resource_type": request.resource_type.value,
                                    "resource_name": request.resource_name,
                                    "previous_access_level": current_permission.access_level.value if current_permission else "none",
                                    "revoked_by_user_id": request.revoked_by_user_id,
                                    "reason": request.reason,
                                    "timestamp": datetime.utcnow().isoformat()
                                }
                            )
                        except ImportError:
                            # Fall back to simple dict-based event for testing
                            event = {
                                "event_type": "permission.revoked",
                                "source": "authorization_service",
                                "data": {
                                    "user_id": request.user_id,
                                    "resource_type": request.resource_type.value,
                                    "resource_name": request.resource_name,
                                    "previous_access_level": current_permission.access_level.value if current_permission else "none",
                                    "revoked_by_user_id": request.revoked_by_user_id,
                                    "reason": request.reason,
                                    "timestamp": datetime.utcnow().isoformat()
                                }
                            }

                        await self.event_bus.publish_event(event)
                    except Exception as e:
                        logger.error(f"Failed to publish permission.revoked event: {e}")

                logger.info(f"Revoked permission: user={request.user_id}, resource={request.resource_type}:{request.resource_name}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error revoking resource permission: {e}")
            
            # Log the failed action
            await self._log_permission_action(
                user_id=request.user_id,
                resource_type=request.resource_type,
                resource_name=request.resource_name,
                action="revoke",
                performed_by_user_id=request.revoked_by_user_id,
                reason=request.reason,
                success=False,
                error_message=str(e)
            )
            
            return False
    
    # ====================
    # Bulk Operations
    # ====================
    
    async def bulk_grant_permissions(self, request: BulkPermissionRequest) -> List[BatchOperationResult]:
        """Grant multiple permissions in bulk"""
        results = []
        batch_id = str(uuid.uuid4())
        started_at = datetime.utcnow()
        
        logger.info(f"Starting bulk grant operation: {len(request.operations)} operations")
        
        for operation in request.operations:
            if isinstance(operation, GrantPermissionRequest):
                operation_id = str(uuid.uuid4())
                
                try:
                    success = await self.grant_resource_permission(operation)
                    
                    results.append(BatchOperationResult(
                        operation_id=operation_id,
                        operation_type="grant",
                        target_user_id=operation.user_id,
                        resource_type=operation.resource_type,
                        resource_name=operation.resource_name,
                        success=success,
                        error_message=None if success else "Grant operation failed"
                    ))
                    
                except Exception as e:
                    results.append(BatchOperationResult(
                        operation_id=operation_id,
                        operation_type="grant",
                        target_user_id=operation.user_id,
                        resource_type=operation.resource_type,
                        resource_name=operation.resource_name,
                        success=False,
                        error_message=str(e)
                    ))
        
        completed_at = datetime.utcnow()
        execution_time = (completed_at - started_at).total_seconds()
        
        logger.info(f"Bulk grant completed: {len([r for r in results if r.success])}/{len(results)} successful")
        
        return results
    
    async def bulk_revoke_permissions(self, request: BulkPermissionRequest) -> List[BatchOperationResult]:
        """Revoke multiple permissions in bulk"""
        results = []
        batch_id = str(uuid.uuid4())
        started_at = datetime.utcnow()
        
        logger.info(f"Starting bulk revoke operation: {len(request.operations)} operations")
        
        for operation in request.operations:
            if isinstance(operation, RevokePermissionRequest):
                operation_id = str(uuid.uuid4())
                
                try:
                    success = await self.revoke_resource_permission(operation)
                    
                    results.append(BatchOperationResult(
                        operation_id=operation_id,
                        operation_type="revoke",
                        target_user_id=operation.user_id,
                        resource_type=operation.resource_type,
                        resource_name=operation.resource_name,
                        success=success,
                        error_message=None if success else "Revoke operation failed"
                    ))
                    
                except Exception as e:
                    results.append(BatchOperationResult(
                        operation_id=operation_id,
                        operation_type="revoke",
                        target_user_id=operation.user_id,
                        resource_type=operation.resource_type,
                        resource_name=operation.resource_name,
                        success=False,
                        error_message=str(e)
                    ))
        
        completed_at = datetime.utcnow()
        execution_time = (completed_at - started_at).total_seconds()
        
        logger.info(f"Bulk revoke completed: {len([r for r in results if r.success])}/{len(results)} successful")
        
        return results
    
    # ====================
    # User Information and Summary
    # ====================
    
    async def get_user_permission_summary(self, user_id: str) -> Optional[UserPermissionSummary]:
        """Get comprehensive permission summary for a user"""
        try:
            return await self.repository.get_user_permission_summary(user_id)
        except Exception as e:
            logger.error(f"Error getting user permission summary: {e}")
            return None
    
    async def list_user_accessible_resources(self, user_id: str, resource_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all resources accessible to a user"""
        try:
            # Convert string to enum if provided
            resource_type_enum = None
            if resource_type:
                try:
                    resource_type_enum = ResourceType(resource_type)
                except ValueError:
                    logger.warning(f"Invalid resource type: {resource_type}")
                    return []
            
            # Get user permissions
            permissions = await self.repository.list_user_permissions(user_id, resource_type_enum)
            
            # Get user info for subscription-based resources
            user_info = await self.repository.get_user_info(user_id)
            if not user_info:
                return []
            
            accessible_resources = []
            
            # Add user-specific permissions
            for perm in permissions:
                accessible_resources.append({
                    "resource_type": perm.resource_type.value,
                    "resource_name": perm.resource_name,
                    "access_level": perm.access_level.value,
                    "permission_source": perm.permission_source.value,
                    "expires_at": perm.expires_at.isoformat() if perm.expires_at else None,
                    "organization_id": perm.organization_id
                })
            
            # Add subscription-based resources
            base_permissions = await self.repository.list_resource_permissions(resource_type_enum)
            user_tier = SubscriptionTier(user_info.subscription_status) if user_info.subscription_status in [t.value for t in SubscriptionTier] else SubscriptionTier.FREE
            
            for base_perm in base_permissions:
                # Check if user already has specific permission
                if not any(r["resource_name"] == base_perm.resource_name for r in accessible_resources):
                    if self._subscription_tier_sufficient(user_tier, base_perm.subscription_tier_required):
                        accessible_resources.append({
                            "resource_type": base_perm.resource_type.value,
                            "resource_name": base_perm.resource_name,
                            "access_level": base_perm.access_level.value,
                            "permission_source": "subscription",
                            "expires_at": None,
                            "subscription_required": base_perm.subscription_tier_required.value,
                            "resource_category": base_perm.resource_category
                        })
            
            return accessible_resources
            
        except Exception as e:
            logger.error(f"Error listing user accessible resources: {e}")
            return []
    
    # ====================
    # Service Management
    # ====================
    
    async def initialize_default_permissions(self) -> bool:
        """Initialize default resource permissions"""
        try:
            logger.info("Initializing default resource permissions...")
            
            default_permissions = [
                # Free tier resources
                ResourcePermission(
                    resource_type=ResourceType.MCP_TOOL,
                    resource_name="weather_api",
                    resource_category="utilities",
                    subscription_tier_required=SubscriptionTier.FREE,
                    access_level=AccessLevel.READ_ONLY,
                    description="Basic weather information tool"
                ),
                ResourcePermission(
                    resource_type=ResourceType.PROMPT,
                    resource_name="basic_assistant",
                    resource_category="assistance",
                    subscription_tier_required=SubscriptionTier.FREE,
                    access_level=AccessLevel.READ_ONLY,
                    description="Basic AI assistant prompts"
                ),
                
                # Pro tier resources
                ResourcePermission(
                    resource_type=ResourceType.MCP_TOOL,
                    resource_name="image_generator",
                    resource_category="ai_tools",
                    subscription_tier_required=SubscriptionTier.PRO,
                    access_level=AccessLevel.READ_WRITE,
                    description="AI image generation tool"
                ),
                ResourcePermission(
                    resource_type=ResourceType.AI_MODEL,
                    resource_name="advanced_llm",
                    resource_category="ai_models",
                    subscription_tier_required=SubscriptionTier.PRO,
                    access_level=AccessLevel.READ_WRITE,
                    description="Advanced language model access"
                ),
                
                # Enterprise tier resources
                ResourcePermission(
                    resource_type=ResourceType.DATABASE,
                    resource_name="analytics_db",
                    resource_category="data",
                    subscription_tier_required=SubscriptionTier.ENTERPRISE,
                    access_level=AccessLevel.READ_WRITE,
                    description="Analytics database access"
                ),
                ResourcePermission(
                    resource_type=ResourceType.API_ENDPOINT,
                    resource_name="admin_api",
                    resource_category="admin",
                    subscription_tier_required=SubscriptionTier.ENTERPRISE,
                    access_level=AccessLevel.ADMIN,
                    description="Administrative API endpoints"
                )
            ]
            
            success_count = 0
            for permission in default_permissions:
                existing = await self.repository.get_resource_permission(permission.resource_type, permission.resource_name)
                if not existing:
                    result = await self.repository.create_resource_permission(permission)
                    if result:
                        success_count += 1
                        logger.debug(f"Created default permission: {permission.resource_type}:{permission.resource_name}")
                else:
                    logger.debug(f"Permission already exists: {permission.resource_type}:{permission.resource_name}")
            
            logger.info(f"Initialized {success_count} default permissions")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error initializing default permissions: {e}")
            return False
    
    async def get_service_statistics(self) -> Dict[str, Any]:
        """Get service statistics"""
        try:
            return await self.repository.get_service_statistics()
        except Exception as e:
            logger.error(f"Error getting service statistics: {e}")
            return {}
    
    async def cleanup_expired_permissions(self) -> int:
        """Clean up expired permissions"""
        try:
            return await self.repository.cleanup_expired_permissions()
        except Exception as e:
            logger.error(f"Error cleaning up expired permissions: {e}")
            return 0
    
    async def cleanup(self) -> None:
        """Service cleanup on shutdown"""
        try:
            # Cleanup repository resources (close service clients)
            await self.repository.cleanup()
            logger.info("Authorization service cleanup completed")
        except Exception as e:
            logger.error(f"Error during authorization service cleanup: {e}")
    
    # ====================
    # Helper Methods
    # ====================
    
    def _subscription_tier_sufficient(self, user_tier: SubscriptionTier, required_tier: SubscriptionTier) -> bool:
        """Check if user's subscription tier meets requirements"""
        user_level = self.subscription_hierarchy.get(user_tier, -1)
        required_level = self.subscription_hierarchy.get(required_tier, 999)
        return user_level >= required_level
    
    def _has_sufficient_access(self, user_level: AccessLevel, required_level: AccessLevel) -> bool:
        """Check if user's access level meets requirements"""
        user_priority = self.access_level_hierarchy.get(user_level, -1)
        required_priority = self.access_level_hierarchy.get(required_level, 999)
        return user_priority >= required_priority
    
    def _organization_plan_sufficient(self, org_plan: str, required_plan: str) -> bool:
        """Check if organization plan meets requirements"""
        plan_hierarchy = {
            "startup": 0,
            "growth": 1,
            "enterprise": 2,
            "custom": 3
        }
        org_priority = plan_hierarchy.get(org_plan.lower(), -1)
        required_priority = plan_hierarchy.get(required_plan.lower(), 999)
        return org_priority >= required_priority
    
    async def _log_access_check(self, user_id: str, resource_type: ResourceType, resource_name: str,
                               action: str, success: bool, reason: str) -> None:
        """Log access check for audit trail"""
        try:
            audit_log = PermissionAuditLog(
                user_id=user_id,
                resource_type=resource_type,
                resource_name=resource_name,
                action=f"access_check_{action}",
                success=success,
                reason=reason
            )
            await self.repository.log_permission_action(audit_log)
        except Exception as e:
            logger.error(f"Failed to log access check: {e}")
    
    async def _log_permission_action(self, user_id: str, resource_type: ResourceType, resource_name: str,
                                   action: str, old_access_level: Optional[AccessLevel] = None,
                                   new_access_level: Optional[AccessLevel] = None,
                                   performed_by_user_id: Optional[str] = None,
                                   reason: Optional[str] = None, success: bool = True,
                                   error_message: Optional[str] = None) -> None:
        """Log permission action for audit trail"""
        try:
            audit_log = PermissionAuditLog(
                user_id=user_id,
                resource_type=resource_type,
                resource_name=resource_name,
                action=action,
                old_access_level=old_access_level,
                new_access_level=new_access_level,
                performed_by_user_id=performed_by_user_id,
                reason=reason,
                success=success,
                error_message=error_message
            )
            await self.repository.log_permission_action(audit_log)
        except Exception as e:
            logger.error(f"Failed to log permission action: {e}")