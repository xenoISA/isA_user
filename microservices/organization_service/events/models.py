"""
Organization Service Event Models

Event data models for organization lifecycle and member management events.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# =============================================================================
# Event Type Definitions (Service-Specific)
# =============================================================================

class OrganizationEventType(str, Enum):
    """
    Events published by organization_service.

    Stream: organization-stream
    Subjects: organization.>
    """
    ORG_CREATED = "organization.created"
    ORG_UPDATED = "organization.updated"
    ORG_DELETED = "organization.deleted"
    ORG_MEMBER_ADDED = "organization.member_added"
    ORG_MEMBER_REMOVED = "organization.member_removed"
    FAMILY_RESOURCE_SHARED = "family.resource_shared"


class OrganizationSubscribedEventType(str, Enum):
    """Events that organization_service subscribes to from other services."""
    USER_DELETED = "user.deleted"


class OrganizationStreamConfig:
    """Stream configuration for organization_service"""
    STREAM_NAME = "organization-stream"
    SUBJECTS = ["organization.>"]
    MAX_MESSAGES = 100000
    CONSUMER_PREFIX = "organization"


# ============================================================================
# Organization Event Models
# ============================================================================


class OrganizationCreatedEventData(BaseModel):
    """
    Event: organization.created
    Triggered when a new organization is created
    """

    organization_id: str = Field(..., description="Organization ID")
    name: str = Field(..., description="Organization name")
    billing_email: str = Field(..., description="Billing email")
    plan: str = Field(..., description="Subscription plan")
    created_by: str = Field(..., description="Creator user ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "organization_id": "org_12345",
                "name": "Acme Corporation",
                "billing_email": "billing@acme.com",
                "plan": "professional",
                "created_by": "user_67890",
                "created_at": "2025-11-14T10:00:00Z",
            }
        }


class OrganizationUpdatedEventData(BaseModel):
    """
    Event: organization.updated
    Triggered when organization details are updated
    """

    organization_id: str = Field(..., description="Organization ID")
    name: str = Field(..., description="Updated organization name")
    updated_fields: List[str] = Field(
        ..., description="List of fields that were updated"
    )
    updated_by: str = Field(..., description="User ID who made the update")
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "organization_id": "org_12345",
                "name": "Acme Inc.",
                "updated_fields": ["name", "settings"],
                "updated_by": "user_67890",
                "updated_at": "2025-11-14T10:05:00Z",
            }
        }


class OrganizationDeletedEventData(BaseModel):
    """
    Event: organization.deleted
    Triggered when an organization is deleted
    """

    organization_id: str = Field(..., description="Organization ID")
    name: str = Field(..., description="Organization name")
    deleted_by: str = Field(..., description="User ID who deleted the organization")
    reason: Optional[str] = Field(None, description="Deletion reason")
    deleted_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "organization_id": "org_12345",
                "name": "Acme Inc.",
                "deleted_by": "user_67890",
                "reason": "Company dissolved",
                "deleted_at": "2025-11-14T10:10:00Z",
            }
        }


class OrganizationMemberAddedEventData(BaseModel):
    """
    Event: organization.member_added
    Triggered when a member is added to an organization
    """

    organization_id: str = Field(..., description="Organization ID")
    user_id: str = Field(..., description="Member user ID")
    role: str = Field(..., description="Member role")
    added_by: str = Field(..., description="User ID who added the member")
    added_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "organization_id": "org_12345",
                "user_id": "user_54321",
                "role": "member",
                "added_by": "user_67890",
                "added_at": "2025-11-14T10:15:00Z",
            }
        }


class OrganizationMemberRemovedEventData(BaseModel):
    """
    Event: organization.member_removed
    Triggered when a member is removed from an organization
    """

    organization_id: str = Field(..., description="Organization ID")
    user_id: str = Field(..., description="Member user ID")
    removed_by: str = Field(..., description="User ID who removed the member")
    reason: Optional[str] = Field(None, description="Removal reason")
    removed_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "organization_id": "org_12345",
                "user_id": "user_54321",
                "removed_by": "user_67890",
                "reason": "Left company",
                "removed_at": "2025-11-14T10:20:00Z",
            }
        }


class OrganizationMemberUpdatedEventData(BaseModel):
    """
    Event: organization.member_updated
    Triggered when a member's role or permissions are updated
    """

    organization_id: str = Field(..., description="Organization ID")
    user_id: str = Field(..., description="Member user ID")
    old_role: str = Field(..., description="Previous role")
    new_role: str = Field(..., description="New role")
    updated_by: str = Field(..., description="User ID who made the update")
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "organization_id": "org_12345",
                "user_id": "user_54321",
                "old_role": "member",
                "new_role": "admin",
                "updated_by": "user_67890",
                "updated_at": "2025-11-14T10:25:00Z",
            }
        }


class SharingResourceCreatedEventData(BaseModel):
    """
    Event: organization.sharing_created
    Triggered when a resource is shared within an organization
    """

    organization_id: str = Field(..., description="Organization ID")
    sharing_id: str = Field(..., description="Sharing resource ID")
    resource_type: str = Field(..., description="Resource type (album, file, etc.)")
    resource_id: str = Field(..., description="Resource identifier")
    resource_name: str = Field(..., description="Resource name")
    created_by: str = Field(..., description="User ID who created the sharing")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "organization_id": "org_12345",
                "sharing_id": "share_98765",
                "resource_type": "album",
                "resource_id": "album_11111",
                "resource_name": "Family Vacation 2024",
                "created_by": "user_67890",
                "created_at": "2025-11-14T10:30:00Z",
            }
        }


class SharingResourceDeletedEventData(BaseModel):
    """
    Event: organization.sharing_deleted
    Triggered when a shared resource is deleted or unshared
    """

    organization_id: str = Field(..., description="Organization ID")
    sharing_id: str = Field(..., description="Sharing resource ID")
    resource_type: str = Field(..., description="Resource type")
    resource_id: str = Field(..., description="Resource identifier")
    deleted_by: str = Field(..., description="User ID who deleted the sharing")
    deleted_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "organization_id": "org_12345",
                "sharing_id": "share_98765",
                "resource_type": "album",
                "resource_id": "album_11111",
                "deleted_by": "user_67890",
                "deleted_at": "2025-11-14T10:35:00Z",
            }
        }


# ============================================================================
# Helper Functions
# ============================================================================


def create_organization_created_event_data(
    organization_id: str,
    name: str,
    billing_email: str,
    plan: str,
    created_by: str,
) -> OrganizationCreatedEventData:
    """Create organization created event data"""
    return OrganizationCreatedEventData(
        organization_id=organization_id,
        name=name,
        billing_email=billing_email,
        plan=plan,
        created_by=created_by,
    )


def create_organization_updated_event_data(
    organization_id: str,
    name: str,
    updated_fields: List[str],
    updated_by: str,
) -> OrganizationUpdatedEventData:
    """Create organization updated event data"""
    return OrganizationUpdatedEventData(
        organization_id=organization_id,
        name=name,
        updated_fields=updated_fields,
        updated_by=updated_by,
    )


def create_organization_deleted_event_data(
    organization_id: str,
    name: str,
    deleted_by: str,
    reason: Optional[str] = None,
) -> OrganizationDeletedEventData:
    """Create organization deleted event data"""
    return OrganizationDeletedEventData(
        organization_id=organization_id,
        name=name,
        deleted_by=deleted_by,
        reason=reason,
    )


def create_organization_member_added_event_data(
    organization_id: str,
    user_id: str,
    role: str,
    added_by: str,
) -> OrganizationMemberAddedEventData:
    """Create organization member added event data"""
    return OrganizationMemberAddedEventData(
        organization_id=organization_id,
        user_id=user_id,
        role=role,
        added_by=added_by,
    )


def create_organization_member_removed_event_data(
    organization_id: str,
    user_id: str,
    removed_by: str,
    reason: Optional[str] = None,
) -> OrganizationMemberRemovedEventData:
    """Create organization member removed event data"""
    return OrganizationMemberRemovedEventData(
        organization_id=organization_id,
        user_id=user_id,
        removed_by=removed_by,
        reason=reason,
    )


def create_organization_member_updated_event_data(
    organization_id: str,
    user_id: str,
    old_role: str,
    new_role: str,
    updated_by: str,
) -> OrganizationMemberUpdatedEventData:
    """Create organization member updated event data"""
    return OrganizationMemberUpdatedEventData(
        organization_id=organization_id,
        user_id=user_id,
        old_role=old_role,
        new_role=new_role,
        updated_by=updated_by,
    )


def create_sharing_resource_created_event_data(
    organization_id: str,
    sharing_id: str,
    resource_type: str,
    resource_id: str,
    resource_name: str,
    created_by: str,
) -> SharingResourceCreatedEventData:
    """Create sharing resource created event data"""
    return SharingResourceCreatedEventData(
        organization_id=organization_id,
        sharing_id=sharing_id,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        created_by=created_by,
    )


def create_sharing_resource_deleted_event_data(
    organization_id: str,
    sharing_id: str,
    resource_type: str,
    resource_id: str,
    deleted_by: str,
) -> SharingResourceDeletedEventData:
    """Create sharing resource deleted event data"""
    return SharingResourceDeletedEventData(
        organization_id=organization_id,
        sharing_id=sharing_id,
        resource_type=resource_type,
        resource_id=resource_id,
        deleted_by=deleted_by,
    )
