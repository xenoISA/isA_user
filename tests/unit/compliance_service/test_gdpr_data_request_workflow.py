from __future__ import annotations

from copy import deepcopy
import hashlib
import json

import pytest

from microservices.compliance_service.compliance_service import ComplianceService
from microservices.compliance_service.models import (
    ComplianceCheck,
    ComplianceCheckType,
    ComplianceStatus,
    ContentType,
    GDPRDataRequestCreate,
    GDPRDataRequestRunRequest,
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


class FakeArtifactStorageClient:
    def __init__(self):
        self.uploads = []
        self.downloads = []

    async def upload_file(self, **kwargs):
        self.uploads.append(kwargs)
        return {
            "file_id": "file-gdpr-export-1",
            "download_url": "https://storage.example/download/file-gdpr-export-1",
        }

    async def get_download_url(self, file_id, user_id, expires_minutes=60):
        self.downloads.append(
            {
                "file_id": file_id,
                "user_id": user_id,
                "expires_minutes": expires_minutes,
            }
        )
        return {
            "download_url": (
                f"https://storage.example/download/{file_id}?expires={expires_minutes}"
            )
        }


class FakeMemoryExportClient:
    def __init__(self, payload=None):
        self.calls = []
        self.payload = payload or {
            "schema_version": "memory-export-v1",
            "user_id": "user-1",
            "scope": "user",
            "memories": [
                {"id": "mem-1", "type": "factual", "content": "likes tea"},
                {"id": "mem-2", "type": "semantic", "content": "Python"},
            ],
            "counts": {"memories": 2, "by_type": {"factual": 1, "semantic": 1}},
        }

    async def export_user_data(self, **kwargs):
        self.calls.append(kwargs)
        return deepcopy(self.payload)


class FakeEventBus:
    def __init__(self):
        self.published = []

    async def publish_event(self, event, subject=None):
        self.published.append({"event": event, "subject": subject})
        return True


def _build_service(
    repository: FakeGDPRRepository,
    artifact_storage_client=None,
    enable_artifact_storage: bool = False,
    gdpr_export_clients=None,
) -> ComplianceService:
    service = ComplianceService.__new__(ComplianceService)
    service.repository = repository
    service.event_bus = None
    service.artifact_storage_client = artifact_storage_client
    service.enable_gdpr_artifact_storage = enable_artifact_storage
    service.gdpr_export_clients = gdpr_export_clients or {}
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


async def test_run_export_request_persists_json_bundle_to_storage():
    repository = FakeGDPRRepository()
    repository.checks.append(_check("user-1"))
    storage = FakeArtifactStorageClient()
    service = _build_service(
        repository,
        artifact_storage_client=storage,
        enable_artifact_storage=True,
    )
    data_request = await service.create_data_request(
        GDPRDataRequestCreate(
            request_type=GDPRDataRequestType.EXPORT,
            user_id="user-1",
            organization_id="org-1",
            requested_by="admin-1",
        )
    )

    completed = await service.run_data_request(data_request.request_id)

    assert completed.artifact_uri == "storage://files/file-gdpr-export-1"
    assert len(storage.uploads) == 1
    upload = storage.uploads[0]
    assert upload["filename"] == f"{data_request.request_id}.json"
    assert upload["user_id"] == "user-1"
    assert upload["organization_id"] == "org-1"
    assert upload["access_level"] == "restricted"
    assert upload["content_type"] == "application/json"
    bundle = json.loads(upload["file_content"].decode("utf-8"))
    assert bundle["request_id"] == data_request.request_id
    assert bundle["services"]["compliance_service"]["records"] == 1
    assert (
        bundle["services"]["compliance_service"]["checks"][0]["check_id"] == "check-1"
    )
    manifest = completed.metadata["export_manifest"]
    assert manifest["storage_file_id"] == "file-gdpr-export-1"
    assert manifest["artifact_uri"] == "storage://files/file-gdpr-export-1"
    assert manifest["services"]["compliance_service"]["records"] == 1
    assert "sha256" in manifest


async def test_run_export_request_aggregates_memory_service_export_adapter():
    repository = FakeGDPRRepository()
    repository.checks.append(_check("user-1"))
    storage = FakeArtifactStorageClient()
    memory_client = FakeMemoryExportClient()
    service = _build_service(
        repository,
        artifact_storage_client=storage,
        enable_artifact_storage=True,
        gdpr_export_clients={"memory_service": memory_client},
    )
    data_request = await service.create_data_request(
        GDPRDataRequestCreate(
            request_type=GDPRDataRequestType.EXPORT,
            user_id="user-1",
            organization_id="org-1",
            requested_by="admin-1",
        )
    )

    completed = await service.run_data_request(data_request.request_id)

    assert memory_client.calls == [
        {
            "user_id": "user-1",
            "organization_id": "org-1",
            "request_id": data_request.request_id,
        }
    ]
    bundle = json.loads(storage.uploads[0]["file_content"].decode("utf-8"))
    assert bundle["services"]["memory_service"]["records"] == 2
    assert (
        bundle["services"]["memory_service"]["payload"]["memories"][0]["id"] == "mem-1"
    )
    assert completed.per_service_status["memory_service"]["status"] == "completed"
    assert completed.per_service_status["memory_service"]["records_exported"] == 2
    manifest = completed.metadata["export_manifest"]
    assert manifest["services"]["memory_service"]["records"] == 2


async def test_run_export_request_marks_requested_service_without_adapter_not_configured():
    repository = FakeGDPRRepository()
    storage = FakeArtifactStorageClient()
    service = _build_service(
        repository,
        artifact_storage_client=storage,
        enable_artifact_storage=True,
        gdpr_export_clients={},
    )
    data_request = await service.create_data_request(
        GDPRDataRequestCreate(
            request_type=GDPRDataRequestType.EXPORT,
            user_id="user-1",
            organization_id="org-1",
            requested_by="admin-1",
        )
    )

    completed = await service.run_data_request(
        data_request.request_id,
        GDPRDataRequestRunRequest(service_names=["memory_service"]),
    )

    assert completed.per_service_status["memory_service"] == {
        "status": "not_configured",
        "records_exported": 0,
        "records_deleted": 0,
        "error": "adapter_not_configured",
    }
    bundle = json.loads(storage.uploads[0]["file_content"].decode("utf-8"))
    assert "memory_service" not in bundle["services"]


async def test_get_data_request_artifact_refreshes_storage_download_url():
    repository = FakeGDPRRepository()
    repository.checks.append(_check("user-1"))
    storage = FakeArtifactStorageClient()
    service = _build_service(
        repository,
        artifact_storage_client=storage,
        enable_artifact_storage=True,
    )
    data_request = await service.create_data_request(
        GDPRDataRequestCreate(
            request_type=GDPRDataRequestType.EXPORT,
            user_id="user-1",
            organization_id="org-1",
            requested_by="admin-1",
        )
    )
    await service.run_data_request(data_request.request_id)

    artifact = await service.get_data_request_artifact(
        data_request.request_id,
        expires_minutes=30,
    )

    assert artifact.request_id == data_request.request_id
    assert artifact.artifact_uri == "storage://files/file-gdpr-export-1"
    assert artifact.storage_file_id == "file-gdpr-export-1"
    assert (
        artifact.download_url
        == "https://storage.example/download/file-gdpr-export-1?expires=30"
    )
    assert storage.downloads == [
        {
            "file_id": "file-gdpr-export-1",
            "user_id": "user-1",
            "expires_minutes": 30,
        }
    ]


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


async def test_approved_delete_request_publishes_user_deleted_cascade_event():
    repository = FakeGDPRRepository()
    repository.checks.append(_check("user-1"))
    event_bus = FakeEventBus()
    service = _build_service(repository)
    service.event_bus = event_bus
    data_request = await service.create_data_request(
        GDPRDataRequestCreate(
            request_type=GDPRDataRequestType.DELETE,
            user_id="user-1",
            organization_id="org-1",
            requested_by="admin-1",
            reason="right to erasure",
        )
    )
    approved = await service.approve_data_request_deletion(
        data_request.request_id,
        GDPRDeletionApprovalRequest(
            approved_by="privacy-officer-1",
            confirmation="CONFIRM_DELETE",
        ),
    )

    completed = await service.run_data_request(approved.request_id)

    cascade_events = [
        item
        for item in event_bus.published
        if getattr(item["event"], "type", None) == "user.deleted"
    ]
    assert len(cascade_events) == 1
    cascade = cascade_events[0]
    assert cascade["subject"] == "account_service.user.deleted"
    assert cascade["event"].source == "compliance_service"
    assert cascade["event"].data["user_id"] == "user-1"
    assert cascade["event"].data["reason"] == "gdpr_data_request"
    assert cascade["event"].data["gdpr_request_id"] == data_request.request_id
    assert cascade["event"].data["approved_by"] == "privacy-officer-1"
    assert (
        completed.metadata["deletion_result"]["cascade_event"]["subject"]
        == "account_service.user.deleted"
    )


async def test_gdpr_workflow_emits_privacy_safe_admin_audit_events_and_tombstone():
    repository = FakeGDPRRepository()
    repository.checks.append(_check("user-1"))
    event_bus = FakeEventBus()
    service = _build_service(repository)
    service.event_bus = event_bus
    data_request = await service.create_data_request(
        GDPRDataRequestCreate(
            request_type=GDPRDataRequestType.DELETE,
            user_id="user-1",
            organization_id="org-1",
            requested_by="admin-1",
            reason="right to erasure",
        )
    )
    approved = await service.approve_data_request_deletion(
        data_request.request_id,
        GDPRDeletionApprovalRequest(
            approved_by="privacy-officer-1",
            confirmation="CONFIRM_DELETE",
        ),
    )

    completed = await service.run_data_request(approved.request_id)

    expected_subject_hash = hashlib.sha256(b"user-1").hexdigest()
    admin_audit_events = [
        item
        for item in event_bus.published
        if item["subject"]
        and item["subject"].startswith("admin.action.gdpr_data_request.")
    ]
    assert [item["subject"] for item in admin_audit_events] == [
        "admin.action.gdpr_data_request.created",
        "admin.action.gdpr_data_request.deletion_approved",
        "admin.action.gdpr_data_request.completed",
    ]

    completed_audit = admin_audit_events[-1]["event"]
    assert completed_audit.source == "compliance_service"
    assert completed_audit.data["admin_user_id"] == "privacy-officer-1"
    assert completed_audit.data["action"] == "gdpr_data_request.completed"
    assert completed_audit.data["resource_type"] == "gdpr_data_request"
    assert completed_audit.data["resource_id"] == data_request.request_id
    assert (
        completed_audit.data["metadata"]["subject_user_hash"] == expected_subject_hash
    )
    assert "user-1" not in json.dumps(completed_audit.data["metadata"])

    tombstone = completed.metadata["deletion_result"]["tombstone"]
    assert tombstone["gdpr_request_id"] == data_request.request_id
    assert tombstone["subject_user_hash"] == expected_subject_hash
    assert tombstone["records_deleted"]["compliance_service"] == 1
    assert tombstone["approved_by"] == "privacy-officer-1"
    assert "user-1" not in json.dumps(tombstone)
