"""L1 Unit — Project service client GDPR export adapter."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from core.auth_dependencies import INTERNAL_SERVICE_SECRET
from microservices.project_service.client import ProjectServiceClient

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def _make_response(payload=None):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload if payload is not None else {}
    return response


async def test_export_user_data_calls_internal_export_endpoint():
    payload = {
        "schema_version": "project-export-v1",
        "service": "project_service",
        "user_id": "user-1",
        "organization_id": "org-1",
        "gdpr_request_id": "gdpr_req_1",
        "exported_at": "2026-05-19T00:00:00Z",
        "projects": [{"id": "project-1"}],
        "project_files": {"project-1": [{"id": "file-1"}]},
        "counts": {"records": 2, "sections": {"projects": 1, "project_files": 1}},
    }
    client = ProjectServiceClient(base_url="http://project.local")
    client.client.get = AsyncMock(return_value=_make_response(payload))

    result = await client.export_user_data(
        user_id="user-1",
        organization_id="org-1",
        request_id="gdpr_req_1",
    )

    assert result == payload
    client.client.get.assert_awaited_once_with(
        "http://project.local/api/v1/projects/export",
        params={
            "user_id": "user-1",
            "organization_id": "org-1",
            "request_id": "gdpr_req_1",
        },
        headers={
            "X-Internal-Service": "true",
            "X-Internal-Service-Secret": INTERNAL_SERVICE_SECRET,
        },
    )
    await client.close()
