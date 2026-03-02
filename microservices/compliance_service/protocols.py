"""
Compliance Service Protocols (Interfaces)

Protocol definitions for dependency injection.
NO import-time I/O dependencies.
"""
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from datetime import datetime

from .models import ComplianceCheck, CompliancePolicy, ComplianceStatus, RiskLevel


class ComplianceServiceError(Exception):
    """Base exception for compliance service errors"""
    pass


class ComplianceNotFoundError(Exception):
    """Compliance check not found"""
    pass


@runtime_checkable
class ComplianceRepositoryProtocol(Protocol):
    """Interface for Compliance Repository"""

    async def initialize(self) -> None: ...

    async def create_check(self, check: ComplianceCheck) -> Optional[ComplianceCheck]: ...

    async def get_check_by_id(self, check_id: str) -> Optional[ComplianceCheck]: ...

    async def get_checks_by_user(
        self, user_id: str, limit: int = 100, offset: int = 0,
        status: Optional[ComplianceStatus] = None,
        risk_level: Optional[RiskLevel] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[ComplianceCheck]: ...

    async def get_checks_by_organization(
        self, organization_id: str, limit: int = 100, offset: int = 0, **filters
    ) -> List[ComplianceCheck]: ...

    async def get_pending_reviews(self, limit: int = 50) -> List[ComplianceCheck]: ...

    async def update_review_status(
        self, check_id: str, reviewed_by: str, status: ComplianceStatus,
        review_notes: Optional[str] = None,
    ) -> bool: ...

    async def get_statistics(
        self, organization_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]: ...

    async def get_violations_summary(
        self, organization_id: Optional[str] = None, days: int = 30,
    ) -> List[Dict[str, Any]]: ...

    async def create_policy(self, policy: CompliancePolicy) -> Optional[CompliancePolicy]: ...

    async def get_policy_by_id(self, policy_id: str) -> Optional[CompliancePolicy]: ...

    async def get_active_policies(self, organization_id: str) -> List[CompliancePolicy]: ...

    async def delete_user_data(self, user_id: str) -> int: ...

    async def update_user_consent(
        self, user_id: str, consent_type: str, granted: bool,
        ip_address: Optional[str] = None, user_agent: Optional[str] = None,
    ) -> bool: ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for Event Bus"""

    async def publish_event(self, event: Any) -> None: ...
