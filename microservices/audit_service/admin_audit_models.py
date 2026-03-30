"""
Admin Audit Log Models

Pydantic models for the admin action audit trail.
Covers requests, responses, and NATS event data for admin operations.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field


class AdminAuditLogEntry(BaseModel):
    """Single admin audit log entry (DB row representation)"""
    id: Optional[int] = None
    audit_id: str
    admin_user_id: str
    admin_email: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    changes: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AdminAuditCreateRequest(BaseModel):
    """Request body for POST /api/v1/audit/admin/actions"""
    admin_user_id: str = Field(..., description="ID of the admin performing the action")
    admin_email: Optional[str] = Field(None, description="Email of the admin")
    action: str = Field(..., description="Action performed (e.g. create_product, update_pricing)")
    resource_type: str = Field(..., description="Type of resource (e.g. product, pricing, cost_definition)")
    resource_id: Optional[str] = Field(None, description="ID of the affected resource")
    changes: Dict[str, Any] = Field(default_factory=dict, description="Before/after diff")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user-agent")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context")


class AdminAuditResponse(BaseModel):
    """Response for a single admin audit entry"""
    audit_id: str
    admin_user_id: str
    admin_email: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    changes: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AdminAuditQueryResponse(BaseModel):
    """Response for GET /api/v1/audit/admin/actions"""
    actions: List[AdminAuditResponse]
    total_count: int
    limit: int
    offset: int
    filters_applied: Dict[str, Any] = Field(default_factory=dict)


class AdminActionEventData(BaseModel):
    """
    NATS event payload for admin.action.{resource_type}.{action}

    Published by any service when an admin operation occurs.
    Consumed by audit_service to persist the log entry.
    """
    admin_user_id: str
    admin_email: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    changes: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
