"""
Compliance Service - Mock Dependencies (Golden)

Mock implementations for component golden testing.
These mocks simulate external dependencies (repository, event bus, clients)
without requiring real infrastructure.

Usage:
    from tests.component.golden.compliance_service.mocks import (
        MockComplianceRepository,
        MockEventBus,
    )
"""

from unittest.mock import AsyncMock, MagicMock
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import uuid


class MockComplianceRepository:
    """
    Mock compliance repository for golden component testing.
    Simulates database operations without real PostgreSQL.
    """

    def __init__(self):
        self._checks: Dict[str, Dict[str, Any]] = {}
        self._policies: Dict[str, Dict[str, Any]] = {}

        # Async mock methods with side effects
        self.create_check = AsyncMock(side_effect=self._create_check)
        self.get_check = AsyncMock(side_effect=self._get_check)
        self.get_check_by_id = AsyncMock(side_effect=self._get_check)
        self.update_check = AsyncMock(side_effect=self._update_check)
        self.delete_check = AsyncMock(side_effect=self._delete_check)
        self.list_checks = AsyncMock(return_value=[])
        self.get_user_checks = AsyncMock(return_value=[])

        # Policy methods
        self.create_policy = AsyncMock(side_effect=self._create_policy)
        self.get_policy_by_id = AsyncMock(side_effect=self._get_policy)
        self.get_active_policies = AsyncMock(return_value=[])
        self.update_policy = AsyncMock(side_effect=self._update_policy)
        self.delete_policy = AsyncMock(return_value=True)

        # Stats and reporting
        self.get_compliance_stats = AsyncMock(return_value={
            "total_checks_today": 100,
            "total_checks_7d": 700,
            "total_checks_30d": 3000,
            "violations_today": 5,
            "violations_7d": 35,
            "violations_30d": 150,
            "blocked_content_today": 2,
            "pending_reviews": 10,
            "avg_processing_time_ms": 125.5,
            "checks_by_type": {"content_moderation": 2000},
            "violations_by_risk": {"high": 20, "critical": 5},
        })
        self.generate_report = AsyncMock(return_value={
            "report_id": f"rpt_{uuid.uuid4().hex[:12]}",
            "total_checks": 1000,
            "passed_checks": 900,
            "failed_checks": 80,
            "flagged_checks": 20,
        })

    async def _create_check(self, check) -> Dict[str, Any]:
        """Simulate create check operation"""
        check_id = check.check_id if hasattr(check, 'check_id') else f"chk_{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc)
        record = {
            "check_id": check_id,
            "user_id": check.user_id if hasattr(check, 'user_id') else "user_unknown",
            "status": check.status.value if hasattr(check.status, 'value') else str(check.status),
            "risk_level": check.risk_level.value if hasattr(check.risk_level, 'value') else str(check.risk_level),
            "created_at": now,
            "updated_at": now,
        }
        self._checks[check_id] = record
        return record

    async def _get_check(self, check_id: str) -> Optional[Dict[str, Any]]:
        """Simulate get check operation"""
        return self._checks.get(check_id)

    async def _update_check(self, check_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Simulate update check operation"""
        if check_id not in self._checks:
            return None
        self._checks[check_id].update(data)
        self._checks[check_id]["updated_at"] = datetime.now(timezone.utc)
        return self._checks[check_id]

    async def _delete_check(self, check_id: str) -> bool:
        """Simulate delete check operation"""
        if check_id in self._checks:
            del self._checks[check_id]
            return True
        return False

    async def _create_policy(self, policy) -> Dict[str, Any]:
        """Simulate create policy operation"""
        policy_id = policy.get("policy_id") or f"pol_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        record = {
            **policy,
            "policy_id": policy_id,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        self._policies[policy_id] = record
        return record

    async def _get_policy(self, policy_id: str) -> Optional[Dict[str, Any]]:
        """Simulate get policy operation"""
        return self._policies.get(policy_id)

    async def _update_policy(self, policy_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Simulate update policy operation"""
        if policy_id not in self._policies:
            return None
        self._policies[policy_id].update(data)
        self._policies[policy_id]["updated_at"] = datetime.now(timezone.utc)
        return self._policies[policy_id]

    def seed_checks(self, records: List[Dict[str, Any]]) -> None:
        """Seed mock with test check data"""
        for record in records:
            check_id = record.get("check_id", f"chk_{uuid.uuid4().hex[:16]}")
            self._checks[check_id] = {**record, "check_id": check_id}

    def seed_policies(self, records: List[Dict[str, Any]]) -> None:
        """Seed mock with test policy data"""
        for record in records:
            policy_id = record.get("policy_id", f"pol_{uuid.uuid4().hex[:12]}")
            self._policies[policy_id] = {**record, "policy_id": policy_id}


class MockEventBus:
    """Mock NATS event bus for golden component testing."""

    def __init__(self):
        self.published_events: List[Any] = []
        self.publish = AsyncMock(side_effect=self._publish)
        self.publish_event = AsyncMock(side_effect=self._publish)

    async def _publish(self, event: Any) -> None:
        """Track published event"""
        self.published_events.append(event)

    def get_published_events(self, event_type: Optional[str] = None) -> List[Any]:
        """Get published events, optionally filtered by type"""
        if event_type is None:
            return self.published_events
        return [
            e for e in self.published_events
            if hasattr(e, 'event_type') and e.event_type == event_type
            or isinstance(e, dict) and e.get('event_type') == event_type
        ]

    def assert_event_published(self, event_type: str) -> None:
        """Assert that an event of given type was published"""
        events = self.get_published_events(event_type)
        assert len(events) > 0, f"Expected event '{event_type}' to be published"

    def clear_events(self) -> None:
        """Clear all published events"""
        self.published_events.clear()


class MockOpenAIClient:
    """Mock OpenAI client for moderation testing"""

    def __init__(self):
        self.moderation = MagicMock()
        self.moderation.create = AsyncMock(return_value=self._default_moderation_response())

    def _default_moderation_response(self) -> Dict[str, Any]:
        return {
            "results": [{
                "flagged": False,
                "categories": {
                    "hate": False,
                    "hate/threatening": False,
                    "harassment": False,
                    "self-harm": False,
                    "sexual": False,
                    "sexual/minors": False,
                    "violence": False,
                    "violence/graphic": False,
                },
                "category_scores": {
                    "hate": 0.01,
                    "hate/threatening": 0.001,
                    "harassment": 0.02,
                    "self-harm": 0.001,
                    "sexual": 0.01,
                    "sexual/minors": 0.001,
                    "violence": 0.02,
                    "violence/graphic": 0.001,
                }
            }]
        }

    def set_flagged_response(self, category: str, score: float = 0.9) -> None:
        """Configure mock to return flagged response"""
        response = self._default_moderation_response()
        response["results"][0]["flagged"] = True
        response["results"][0]["categories"][category] = True
        response["results"][0]["category_scores"][category] = score
        self.moderation.create = AsyncMock(return_value=response)
