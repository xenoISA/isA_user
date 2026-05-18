from __future__ import annotations

from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient

from microservices.compliance_service import main as compliance_main
from microservices.compliance_service.models import (
    GDPRDataRequest,
    GDPRDataRequestListResponse,
    GDPRDataRequestStatus,
    GDPRDataRequestType,
)


pytestmark = [pytest.mark.api, pytest.mark.asyncio]


class FakeGDPRService:
    def __init__(self):
        self.request = GDPRDataRequest(
            request_id="gdpr_req_test",
            request_type=GDPRDataRequestType.EXPORT,
            user_id="user-1",
            organization_id="org-1",
            status=GDPRDataRequestStatus.PENDING,
            requested_by="admin-1",
            per_service_status={},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    async def create_data_request(self, request):
        self.request = GDPRDataRequest(
            request_id="gdpr_req_test",
            request_type=request.request_type,
            user_id=request.user_id,
            organization_id=request.organization_id,
            status=GDPRDataRequestStatus.PENDING,
            requested_by=request.requested_by,
            reason=request.reason,
            metadata=request.metadata,
            per_service_status={},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        return self.request

    async def list_data_requests(self, **_filters):
        return GDPRDataRequestListResponse(
            items=[self.request], total=1, limit=50, offset=0
        )

    async def get_data_request(self, request_id):
        if request_id != self.request.request_id:
            return None
        return self.request

    async def approve_data_request_deletion(self, request_id, approval):
        self.request = self.request.model_copy(
            update={
                "request_type": GDPRDataRequestType.DELETE,
                "approved_by": approval.approved_by,
                "approved_at": datetime.utcnow(),
            }
        )
        return self.request

    async def run_data_request(self, request_id, run_options=None):
        if request_id != self.request.request_id:
            return None
        self.request = self.request.model_copy(
            update={
                "status": GDPRDataRequestStatus.COMPLETED,
                "artifact_uri": f"compliance://gdpr-exports/{request_id}.json",
                "per_service_status": {
                    "compliance_service": {
                        "status": "completed",
                        "records_exported": 0,
                        "records_deleted": 0,
                    }
                },
                "completed_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        )
        return self.request


def _client_for(service: FakeGDPRService):
    compliance_main.app.dependency_overrides[
        compliance_main.get_compliance_service
    ] = lambda: service
    return AsyncClient(
        transport=ASGITransport(app=compliance_main.app),
        base_url="http://test",
    )


async def test_create_and_list_gdpr_data_requests():
    service = FakeGDPRService()
    try:
        async with _client_for(service) as client:
            created = await client.post(
                "/api/v1/compliance/data-requests",
                json={
                    "request_type": "export",
                    "user_id": "user-1",
                    "organization_id": "org-1",
                    "requested_by": "admin-1",
                    "reason": "subject access request",
                },
            )
            listed = await client.get("/api/v1/compliance/data-requests")
    finally:
        compliance_main.app.dependency_overrides.clear()

    assert created.status_code == 201
    assert created.json()["status"] == "pending"
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["request_id"] == "gdpr_req_test"


async def test_run_gdpr_data_request_returns_result_panel_payload():
    service = FakeGDPRService()
    try:
        async with _client_for(service) as client:
            response = await client.post(
                "/api/v1/compliance/data-requests/gdpr_req_test/run"
            )
    finally:
        compliance_main.app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["artifact_uri"] == "compliance://gdpr-exports/gdpr_req_test.json"
    assert body["per_service_status"]["compliance_service"]["status"] == "completed"
