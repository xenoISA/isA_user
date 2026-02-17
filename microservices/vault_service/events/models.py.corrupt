"""
Vault Service Event Data Models

vault_service ^„‹öpnÓ„šI
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserDeletedEventData(BaseModel):
    """
    (7 d‹öpn (vault_service ÆÒ)

    vault_service Ñ,d‹öv(7pn

    NATS Subject: *.user.deleted
    Publisher: account_service
    """

    user_id: str = Field(..., description="« d„(7ID")
    timestamp: Optional[datetime] = Field(None, description=" döô")
    reason: Optional[str] = Field(None, description=" dŸà")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class VaultSecretCreatedEventData(BaseModel):
    """
    Æ¥úŸ‹öpn

    vault_service úÆ¥Ñd‹ö

    NATS Subject: vault.secret.created
    Subscribers: audit_service, compliance_service
    """

    user_id: str = Field(..., description="(7ID")
    vault_id: str = Field(..., description="Æ¥ID")
    secret_type: str = Field(..., description="Æ¥{‹")
    name: str = Field(..., description="Æ¥ğ")
    timestamp: Optional[datetime] = Field(None, description="úöô")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class VaultSecretAccessedEventData(BaseModel):
    """
    Æ¥¿î‹öpn

    vault_service Æ¥«¿îöÑd‹ö

    NATS Subject: vault.secret.accessed
    Subscribers: audit_service, compliance_service
    """

    user_id: str = Field(..., description="¿î(7ID")
    vault_id: str = Field(..., description="Æ¥ID")
    access_type: str = Field(..., description="¿î{‹: read, decrypt, rotate")
    ip_address: Optional[str] = Field(None, description="¿îIP")
    user_agent: Optional[str] = Field(None, description="(7ã")
    timestamp: Optional[datetime] = Field(None, description="¿îöô")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class VaultSecretDeletedEventData(BaseModel):
    """
    Æ¥ d‹öpn

    vault_service  dÆ¥Ñd‹ö

    NATS Subject: vault.secret.deleted
    Subscribers: audit_service, compliance_service
    """

    user_id: str = Field(..., description="(7ID")
    vault_id: str = Field(..., description="Æ¥ID")
    secret_type: str = Field(..., description="Æ¥{‹")
    timestamp: Optional[datetime] = Field(None, description=" döô")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class VaultSecretSharedEventData(BaseModel):
    """
    Æ¥«‹öpn

    vault_service «Æ¥Ñd‹ö

    NATS Subject: vault.secret.shared
    Subscribers: audit_service, notification_service
    """

    owner_user_id: str = Field(..., description="@	(7ID")
    shared_with_user_id: Optional[str] = Field(None, description="«Ù(7ID")
    shared_with_org_id: Optional[str] = Field(None, description="«ÙÄÇID")
    vault_id: str = Field(..., description="Æ¥ID")
    permission: str = Field(..., description="CP§+: read, write")
    timestamp: Optional[datetime] = Field(None, description="«öô")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# Helper functions
def parse_user_deleted_event(event_data: dict) -> UserDeletedEventData:
    """ã user.deleted ‹öpn"""
    return UserDeletedEventData(**event_data)


def create_secret_created_event_data(
    user_id: str,
    vault_id: str,
    secret_type: str,
    name: str,
) -> VaultSecretCreatedEventData:
    """ú secret.created ‹öpn"""
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
    """ú secret.accessed ‹öpn"""
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
    """ú secret.deleted ‹öpn"""
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
    """ú secret.shared ‹öpn"""
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
