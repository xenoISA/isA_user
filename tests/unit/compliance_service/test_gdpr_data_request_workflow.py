from __future__ import annotations

from copy import deepcopy

import pytest

from microservices.compliance_service.compliance_service import ComplianceService
from microservices.compliance_service.models import (
    ComplianceCheck,
    ComplianceCheckType,
    ComplianceStatus,
    ContentType,
    GDPRDataRequestCreate,
    GDPRDataRequestStatus,
    GDPRDataRequestType,
    GDPRDeletionApprovalRequest,
    RiskLevel,
)


pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class FakeGDPRRepository:
    def __init__(self):
        self.requests = {}
        self.checks = []
        self.deleted_user_ids = []

    async def create_data_request(self, data_request):
        self.requests[data_request.request_id] = data_request.model_copy(deep=True)
        return self.requests[data_request.request_id]

    async def get_data_request(self, request_id):
        return self.requests.get(request_id)

    async def update_data_request(self, request_id, **updates):
        current = self.requests[request_id]
        data = current.model_dump()
        for key, value in updates.items():
            if value is not None:
                data[key] = deepcopy(value)
        updated = current.__class__(**data)
        self.requests[request_id] = updated
        return updated

    async def get_checks_by_user(self, user_id, limit=10000, offset=0, **_filters):
        return [check for check in self.checks if check.user_id == user_id][
            offset : offset + limit
        ]

    async def delete_user_data(self, user_id):
        self.deleted_user_ids.append(user_id)
        deleted = len([check for check in self.checks if check.user_id == user_id])
        self.checks = [check for check in self.checks if check.user_id != user_id]
        return deleted


def _build_service(repository: FakeGDPRRepository) -> ComplianceService:
    service = ComplianceService.__new__(ComplianceService)
    service.repository = repository
    service.event_bus = None
    service.enable_openai_moderation = False
    service.enable_local_checks = False
    service._stats = {"total_checks": 0, "blocked_content": 0, "flagged_content": 0}
    return service


def _check(user_id: str = "user-1") -> ComplianceCheck:
    return ComplianceCheck(
        check_id="check-1",
        check_type=ComplianceCheckType.PII_DETECTION,
        content_type=ContentType.TEXT,
        status=ComplianceStatus.WARNING,
        risk_level=RiskLevel.MEDIUM,
        user_id=user_id,
        organization_id="org-1",
        violations=[],
        warnings=[{"issue": "Potential PII"}],
        action_taken="allowed_with_warning",
    )


async def test_create_data_request_enqueues_pending_export_request():
    repository = FakeGDPRRepository()
    service = _build_service(repository)

    data_request = await service.create_data_request(
        GDPRDataRequestCreate(
            request_type=GDPRDataRequestType.EXPORT,
            user_id="user-1",
            organization_id="org-1",
            requested_by="admin-1",
            reason="subject access request",
        )
    )

    assert data_request.request_id.startswith("gdpr_req_")
    assert data_request.status == GDPRDataRequestStatus.PENDING
    assert data_request.request_type == GDPRDataRequestType.EXPORT
    assert data_request.per_service_status == {}


async def test_run_export_request_tracks_service_status_and_artifact_uri():
    repository = FakeGDPRRepository()
    repository.checks.append(_check("user-1"))
    service = _build_service(repository)
    data_request = await service.create_data_request(
        GDPRDataRequestCreate(
            request_type=GDPRDataRequestType.EXPORT,
            user_id="user-1",
            organization_id="org-1",
            requested_by="admin-1",
        )
    )

    completed = await service.run_data_request(data_request.request_id)

    assert completed.status == GDPRDataRequestStatus.COMPLETED
    assert (
        completed.artifact_uri
        == f"compliance://gdpr-exports/{data_request.request_id}.json"
    )
    assert completed.per_service_status["compliance_service"]["status"] == "completed"
    assert completed.per_service_status["compliance_service"]["records_exported"] == 1


async def test_delete_request_must_be_approved_before_running():
    repository = FakeGDPRRepository()
    service = _build_service(repository)
    data_request = await service.create_data_request(
        GDPRDataRequestCreate(
            request_type=GDPRDataRequestType.DELETE,
            user_id="user-1",
            requested_by="admin-1",
        )
    )

    with pytest.raises(ValueError, match="approved"):
        await service.run_data_request(data_request.request_id)


async def test_approved_delete_request_deletes_compliance_records_and_tracks_audit_state():
    repository = FakeGDPRRepository()
    repository.checks.append(_check("user-1"))
    service = _build_service(repository)
    data_request = await service.create_data_request(
        GDPRDataRequestCreate(
            request_type=GDPRDataRequestType.DELETE,
            user_id="user-1",
            requested_by="admin-1",
        )
    )

    approved = await service.approve_data_request_deletion(
        data_request.request_id,
        GDPRDeletionApprovalRequest(
            approved_by="privacy-officer-1",
            confirmation="CONFIRM_DELETE",
            notes="verified requestor identity",
        ),
    )
    completed = await service.run_data_request(approved.request_id)

    assert completed.status == GDPRDataRequestStatus.COMPLETED
    assert completed.approved_by == "privacy-officer-1"
    assert repository.deleted_user_ids == ["user-1"]
    assert completed.per_service_status["compliance_service"]["status"] == "completed"
    assert completed.per_service_status["compliance_service"]["records_deleted"] == 1
