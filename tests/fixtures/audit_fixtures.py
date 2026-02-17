"""
Audit Service Fixtures

Factories for audit service test data.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .common import make_user_id, make_org_id


def make_event_id() -> str:
    """Generate a unique audit event ID"""
    import uuid
    return f"evt_{uuid.uuid4().hex[:12]}"


def make_audit_event(
    event_id: Optional[str] = None,
    event_type: str = "user_login",
    category: str = "authentication",
    severity: str = "low",
    action: str = "login",
    user_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    success: bool = True,
    **kwargs
) -> Dict[str, Any]:
    """Create an audit event dict for testing"""
    return {
        "id": event_id or make_event_id(),
        "event_type": event_type,
        "category": category,
        "severity": severity,
        "action": action,
        "user_id": user_id or make_user_id(),
        "organization_id": organization_id,
        "success": success,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **kwargs
    }


def make_audit_event_request(
    event_type: str = "user_login",
    category: str = "authentication",
    severity: str = "low",
    action: str = "login",
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    success: bool = True,
    **kwargs
) -> Dict[str, Any]:
    """Create an audit event create request"""
    request = {
        "event_type": event_type,
        "category": category,
        "action": action,
        "success": success,
    }
    if severity:
        request["severity"] = severity
    if user_id:
        request["user_id"] = user_id
    if ip_address:
        request["ip_address"] = ip_address
    request.update(kwargs)
    return request


def make_audit_query_request(
    user_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    event_types: Optional[List[str]] = None,
    categories: Optional[List[str]] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    """Create an audit query request"""
    request = {
        "limit": limit,
        "offset": offset,
    }
    if user_id:
        request["user_id"] = user_id
    if organization_id:
        request["organization_id"] = organization_id
    if event_types:
        request["event_types"] = event_types
    if categories:
        request["categories"] = categories
    if start_time:
        request["start_time"] = start_time.isoformat()
    if end_time:
        request["end_time"] = end_time.isoformat()
    return request


def make_security_alert_request(
    threat_type: str = "brute_force",
    severity: str = "high",
    description: str = "Multiple failed login attempts detected",
    source_ip: Optional[str] = None,
    user_id: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """Create a security alert request"""
    request = {
        "threat_type": threat_type,
        "severity": severity,
        "description": description,
    }
    if source_ip:
        request["source_ip"] = source_ip
    if user_id:
        request["user_id"] = user_id
    request.update(kwargs)
    return request


def make_compliance_report_request(
    report_type: str = "monthly",
    compliance_standard: str = "GDPR",
    period_start: Optional[datetime] = None,
    period_end: Optional[datetime] = None,
    organization_id: Optional[str] = None,
    include_details: bool = True,
) -> Dict[str, Any]:
    """Create a compliance report request"""
    from datetime import timedelta

    end = period_end or datetime.now(timezone.utc)
    start = period_start or (end - timedelta(days=30))

    request = {
        "report_type": report_type,
        "compliance_standard": compliance_standard,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "include_details": include_details,
    }
    if organization_id:
        request["organization_id"] = organization_id
    return request
