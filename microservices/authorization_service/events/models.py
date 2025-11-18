"""
Authorization Service Event Models

Event data models for authorization and permission management events.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# ============================================================================
# Permission Event Models
# ============================================================================


class PermissionGrantedEventData(BaseModel):
    """
    Event: permission.granted
    Triggered when a permission is granted to a user
    """

    user_id: str = Field(..., description="User ID")
    resource_type: str = Field(..., description="Resource type")
    resource_name: str = Field(..., description="Resource name")
    access_level: str = Field(..., description="Access level granted")
    permission_source: str = Field(..., description="Permission source")
    granted_by_user_id: Optional[str] = Field(None, description="ID of user who granted the permission")
    organization_id: Optional[str] = Field(None, description="Organization ID if applicable")
    granted_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_12345",
                "resource_type": "api_endpoint",
                "resource_name": "/api/data",
                "access_level": "read_write",
                "permission_source": "admin_grant",
                "granted_by_user_id": "admin_001",
                "organization_id": "org_001",
                "granted_at": "2025-11-14T10:00:00Z",
            }
        }


class PermissionRevokedEventData(BaseModel):
    """
    Event: permission.revoked
    Triggered when a permission is revoked from a user
    """

    user_id: str = Field(..., description="User ID")
    resource_type: str = Field(..., description="Resource type")
    resource_name: str = Field(..., description="Resource name")
    revoked_by_user_id: Optional[str] = Field(None, description="ID of user who revoked the permission")
    reason: Optional[str] = Field(None, description="Reason for revocation")
    revoked_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_12345",
                "resource_type": "api_endpoint",
                "resource_name": "/api/data",
                "revoked_by_user_id": "admin_001",
                "reason": "Policy change",
                "revoked_at": "2025-11-14T10:05:00Z",
            }
        }


class BulkPermissionsGrantedEventData(BaseModel):
    """
    Event: permissions.bulk_granted
    Triggered when multiple permissions are granted in bulk
    """

    user_ids: List[str] = Field(..., description="List of user IDs")
    permission_count: int = Field(..., description="Number of permissions granted")
    granted_by_user_id: Optional[str] = Field(None, description="ID of user who granted permissions")
    organization_id: Optional[str] = Field(None, description="Organization ID if applicable")
    granted_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "user_ids": ["user_001", "user_002", "user_003"],
                "permission_count": 15,
                "granted_by_user_id": "admin_001",
                "organization_id": "org_001",
                "granted_at": "2025-11-14T10:10:00Z",
            }
        }


class BulkPermissionsRevokedEventData(BaseModel):
    """
    Event: permissions.bulk_revoked
    Triggered when multiple permissions are revoked in bulk
    """

    user_ids: List[str] = Field(..., description="List of user IDs")
    permission_count: int = Field(..., description="Number of permissions revoked")
    revoked_by_user_id: Optional[str] = Field(None, description="ID of user who revoked permissions")
    reason: Optional[str] = Field(None, description="Reason for bulk revocation")
    revoked_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "user_ids": ["user_001", "user_002"],
                "permission_count": 10,
                "revoked_by_user_id": "admin_001",
                "reason": "Security audit",
                "revoked_at": "2025-11-14T10:15:00Z",
            }
        }


# ============================================================================
# Event Data Factory Functions
# ============================================================================


def create_permission_granted_event_data(
    user_id: str,
    resource_type: str,
    resource_name: str,
    access_level: str,
    permission_source: str,
    granted_by_user_id: Optional[str] = None,
    organization_id: Optional[str] = None,
) -> PermissionGrantedEventData:
    """Create PermissionGrantedEventData instance"""
    return PermissionGrantedEventData(
        user_id=user_id,
        resource_type=resource_type,
        resource_name=resource_name,
        access_level=access_level,
        permission_source=permission_source,
        granted_by_user_id=granted_by_user_id,
        organization_id=organization_id,
    )


def create_permission_revoked_event_data(
    user_id: str,
    resource_type: str,
    resource_name: str,
    revoked_by_user_id: Optional[str] = None,
    reason: Optional[str] = None,
) -> PermissionRevokedEventData:
    """Create PermissionRevokedEventData instance"""
    return PermissionRevokedEventData(
        user_id=user_id,
        resource_type=resource_type,
        resource_name=resource_name,
        revoked_by_user_id=revoked_by_user_id,
        reason=reason,
    )


def create_bulk_permissions_granted_event_data(
    user_ids: List[str],
    permission_count: int,
    granted_by_user_id: Optional[str] = None,
    organization_id: Optional[str] = None,
) -> BulkPermissionsGrantedEventData:
    """Create BulkPermissionsGrantedEventData instance"""
    return BulkPermissionsGrantedEventData(
        user_ids=user_ids,
        permission_count=permission_count,
        granted_by_user_id=granted_by_user_id,
        organization_id=organization_id,
    )


def create_bulk_permissions_revoked_event_data(
    user_ids: List[str],
    permission_count: int,
    revoked_by_user_id: Optional[str] = None,
    reason: Optional[str] = None,
) -> BulkPermissionsRevokedEventData:
    """Create BulkPermissionsRevokedEventData instance"""
    return BulkPermissionsRevokedEventData(
        user_ids=user_ids,
        permission_count=permission_count,
        revoked_by_user_id=revoked_by_user_id,
        reason=reason,
    )
