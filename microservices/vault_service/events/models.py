"""
Vault Service Event Data Models

vault_service ^���pnӄ�I
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

# =============================================================================
# Event Type Definitions (Service-Specific)
# =============================================================================

class VaultEventType(str, Enum):
    """
    Events published by vault_service.

    Stream: vault-stream
    Subjects: vault.>
    """
    SECRET_CREATED = "vault.secret.created"
    SECRET_ACCESSED = "vault.secret.accessed"
    SECRET_UPDATED = "vault.secret.updated"
    SECRET_DELETED = "vault.secret.deleted"
    SECRET_SHARED = "vault.secret.shared"
    SECRET_ROTATED = "vault.secret.rotated"


class VaultSubscribedEventType(str, Enum):
    """Events that vault_service subscribes to from other services."""
    USER_DELETED = "user.deleted"


class VaultStreamConfig:
    """Stream configuration for vault_service"""
    STREAM_NAME = "vault-stream"
    SUBJECTS = ["vault.>"]
    MAX_MESSAGES = 100000
    CONSUMER_PREFIX = "vault"



class UserDeletedEventData(BaseModel):
    """
    (7 d��pn (vault_service ��)

    vault_service �,d��v(7pn

    NATS Subject: *.user.deleted
    Publisher: account_service
    """

    user_id: str = Field(..., description="� d�(7ID")
    timestamp: Optional[datetime] = Field(None, description=" d��")
    reason: Optional[str] = Field(None, description=" d��")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class VaultSecretCreatedEventData(BaseModel):
    """
    ƥ����pn

    vault_service �ƥ�d��

    NATS Subject: vault.secret.created
    Subscribers: audit_service, compliance_service
    """

    user_id: str = Field(..., description="User ID")
    vault_id: str = Field(..., description="Vault ID")
    secret_type: str = Field(..., description="Secret type")
    name: str = Field(..., description="Secret name")
    timestamp: Optional[datetime] = Field(None, description="Creation timestamp")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class VaultSecretAccessedEventData(BaseModel):
    """
    ƥ���pn

    vault_service ƥ�����d��

    NATS Subject: vault.secret.accessed
    Subscribers: audit_service, compliance_service
    """

    user_id: str = Field(..., description="��(7ID")
    vault_id: str = Field(..., description="ƥID")
    access_type: str = Field(..., description="��{�: read, decrypt, rotate")
    ip_address: Optional[str] = Field(None, description="��IP")
    user_agent: Optional[str] = Field(None, description="(7�")
    timestamp: Optional[datetime] = Field(None, description="����")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class VaultSecretDeletedEventData(BaseModel):
    """
    ƥ d��pn

    vault_service  dƥ�d��

    NATS Subject: vault.secret.deleted
    Subscribers: audit_service, compliance_service
    """

    user_id: str = Field(..., description="(7ID")
    vault_id: str = Field(..., description="ƥID")
    secret_type: str = Field(..., description="ƥ{�")
    timestamp: Optional[datetime] = Field(None, description=" d��")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class VaultSecretSharedEventData(BaseModel):
    """
    ƥ���pn

    vault_service �ƥ�d��

    NATS Subject: vault.secret.shared
    Subscribers: audit_service, notification_service
    """

    owner_user_id: str = Field(..., description="@	(7ID")
    shared_with_user_id: Optional[str] = Field(None, description="��(7ID")
    shared_with_org_id: Optional[str] = Field(None, description="����ID")
    vault_id: str = Field(..., description="ƥID")
    permission: str = Field(..., description="CP�+: read, write")
    timestamp: Optional[datetime] = Field(None, description="���")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# Helper functions
def parse_user_deleted_event(event_data: dict) -> UserDeletedEventData:
    """� user.deleted ��pn"""
    return UserDeletedEventData(**event_data)


def create_secret_created_event_data(
    user_id: str,
    vault_id: str,
    secret_type: str,
    name: str,
) -> VaultSecretCreatedEventData:
    """� secret.created ��pn"""
    return VaultSecretCreatedEventData(
        user_id=user_id,
        vault_id=vault_id,
        secret_type=secret_type,
        name=name,
        timestamp=datetime.utcnow(),
    )


def create_secret_accessed_event_data(
    user_id: str,
    vault_id: str,
    access_type: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> VaultSecretAccessedEventData:
    """� secret.accessed ��pn"""
    return VaultSecretAccessedEventData(
        user_id=user_id,
        vault_id=vault_id,
        access_type=access_type,
        ip_address=ip_address,
        user_agent=user_agent,
        timestamp=datetime.utcnow(),
    )


def create_secret_deleted_event_data(
    user_id: str,
    vault_id: str,
    secret_type: str,
) -> VaultSecretDeletedEventData:
    """� secret.deleted ��pn"""
    return VaultSecretDeletedEventData(
        user_id=user_id,
        vault_id=vault_id,
        secret_type=secret_type,
        timestamp=datetime.utcnow(),
    )


def create_secret_shared_event_data(
    owner_user_id: str,
    vault_id: str,
    permission: str,
    shared_with_user_id: Optional[str] = None,
    shared_with_org_id: Optional[str] = None,
) -> VaultSecretSharedEventData:
    """� secret.shared ��pn"""
    return VaultSecretSharedEventData(
        owner_user_id=owner_user_id,
        shared_with_user_id=shared_with_user_id,
        shared_with_org_id=shared_with_org_id,
        vault_id=vault_id,
        permission=permission,
        timestamp=datetime.utcnow(),
    )


__all__ = [
    "UserDeletedEventData",
    "VaultSecretCreatedEventData",
    "VaultSecretAccessedEventData",
    "VaultSecretDeletedEventData",
    "VaultSecretSharedEventData",
    "parse_user_deleted_event",
    "create_secret_created_event_data",
    "create_secret_accessed_event_data",
    "create_secret_deleted_event_data",
    "create_secret_shared_event_data",
]
