"""
Compliance Service Business Logic

处理内容审核、PII检测、提示词注入检测等合规检查
"""

import logging
import hashlib
import json
import os
import re
import time
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import uuid
import asyncio

from core.redis_cache import RedisCache, build_redis_cache

from .compliance_repository import ComplianceRepository
from .models import (
    ComplianceCheck,
    ComplianceCheckRequest,
    ComplianceCheckResponse,
    ContentModerationResult,
    PIIDetectionResult,
    PromptInjectionResult,
    ComplianceCheckType,
    ComplianceStatus,
    RiskLevel,
    ContentType,
    PIIType,
    CompliancePolicy,
    GDPRDataRequest,
    GDPRDataRequestArtifactResponse,
    GDPRDataRequestCreate,
    GDPRDataRequestListResponse,
    GDPRDataRequestRunRequest,
    GDPRDataRequestStatus,
    GDPRDataRequestType,
    GDPRDeletionApprovalRequest,
)
from .events.publishers import (
    publish_compliance_check_performed,
    publish_compliance_violation_detected,
    publish_compliance_warning_issued,
)

logger = logging.getLogger(__name__)

# Issue #347: Policy cache TTL — 5 minutes. Long enough that we get hit
# rates worth measuring, short enough that operators don't have to
# manually invalidate after a routine policy edit.
POLICY_CACHE_TTL_SECONDS = 300


class ComplianceService:
    """合规服务核心业务逻辑"""

    def __init__(
        self,
        event_bus=None,
        config=None,
        policy_cache: Optional[RedisCache] = None,
        artifact_storage_client=None,
        gdpr_export_clients: Optional[Dict[str, Any]] = None,
        enable_gdpr_artifact_storage: Optional[bool] = None,
    ):
        self.repository = ComplianceRepository(config=config)
        self.event_bus = event_bus
        self.artifact_storage_client = artifact_storage_client
        self.gdpr_export_clients = (
            gdpr_export_clients
            if gdpr_export_clients is not None
            else self._default_gdpr_export_clients()
        )
        if enable_gdpr_artifact_storage is None:
            storage_enabled = os.getenv("GDPR_EXPORT_STORAGE_ENABLED", "true").lower()
            self.enable_gdpr_artifact_storage = storage_enabled not in {
                "0",
                "false",
                "no",
                "off",
            }
        else:
            self.enable_gdpr_artifact_storage = enable_gdpr_artifact_storage

        # 配置
        self.enable_openai_moderation = True
        self.enable_local_checks = True

        # Policy cache — Redis-backed (issue #347). Falls back to "no-op cache"
        # when REDIS_URL is unset so unit tests stay hermetic. Callers may
        # inject a fakeredis-backed cache for component tests.
        self._policy_cache: RedisCache = policy_cache or build_redis_cache(
            "compliance:policy",
            service_name="compliance_service",
            default_ttl=POLICY_CACHE_TTL_SECONDS,
        )

        # 统计
        self._stats = {"total_checks": 0, "blocked_content": 0, "flagged_content": 0}

    # ====================
    # GDPR 数据请求工作流
    # ====================

    async def create_data_request(
        self, request: GDPRDataRequestCreate
    ) -> GDPRDataRequest:
        """Enqueue a GDPR data export/delete request for admin processing."""
        now = datetime.utcnow()
        data_request = GDPRDataRequest(
            request_id=f"gdpr_req_{uuid.uuid4().hex}",
            request_type=request.request_type,
            user_id=request.user_id,
            organization_id=request.organization_id,
            status=GDPRDataRequestStatus.PENDING,
            requested_by=request.requested_by,
            reason=request.reason,
            per_service_status={},
            metadata=request.metadata or {},
            created_at=now,
            updated_at=now,
        )

        created = await self.repository.create_data_request(data_request)
        if not created:
            raise RuntimeError("Failed to create GDPR data request")

        await self._publish_data_request_event(
            "compliance.gdpr_request.created", created
        )
        await self._publish_gdpr_admin_audit_event(
            "created",
            created,
            actor_user_id=created.requested_by,
            changes={
                "status": {"after": created.status.value},
                "request_type": {"after": created.request_type.value},
            },
        )
        return created

    async def list_data_requests(
        self,
        *,
        status: Optional[GDPRDataRequestStatus] = None,
        request_type: Optional[GDPRDataRequestType] = None,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> GDPRDataRequestListResponse:
        """List queued GDPR requests for the admin compliance queue."""
        items, total = await self.repository.list_data_requests(
            status=status,
            request_type=request_type,
            user_id=user_id,
            organization_id=organization_id,
            limit=limit,
            offset=offset,
        )
        return GDPRDataRequestListResponse(
            items=items, total=total, limit=limit, offset=offset
        )

    async def get_data_request(self, request_id: str) -> Optional[GDPRDataRequest]:
        """Get a single GDPR data request."""
        return await self.repository.get_data_request(request_id)

    async def get_data_request_artifact(
        self, request_id: str, expires_minutes: int = 60
    ) -> Optional[GDPRDataRequestArtifactResponse]:
        """Return download metadata for a completed GDPR export artifact."""
        data_request = await self.repository.get_data_request(request_id)
        if not data_request:
            return None
        if data_request.request_type != GDPRDataRequestType.EXPORT:
            return None
        if data_request.status != GDPRDataRequestStatus.COMPLETED:
            return None
        if not data_request.artifact_uri:
            return None

        manifest = dict((data_request.metadata or {}).get("export_manifest") or {})
        storage_file_id = manifest.get("storage_file_id")
        download_url = manifest.get("download_url")

        if storage_file_id and self._gdpr_artifact_storage_enabled():
            download_info = await self._get_export_artifact_download_url(
                storage_file_id=storage_file_id,
                user_id=data_request.user_id,
                expires_minutes=expires_minutes,
            )
            if download_info:
                download_url = (
                    download_info.get("download_url")
                    or download_info.get("url")
                    or download_url
                )

        return GDPRDataRequestArtifactResponse(
            request_id=data_request.request_id,
            artifact_uri=data_request.artifact_uri,
            storage_file_id=storage_file_id,
            filename=manifest.get("filename"),
            content_type=manifest.get("content_type") or "application/json",
            size_bytes=manifest.get("size_bytes"),
            sha256=manifest.get("sha256"),
            download_url=download_url,
            expires_minutes=expires_minutes,
            generated_at=manifest.get("generated_at"),
            manifest=manifest,
        )

    async def approve_data_request_deletion(
        self, request_id: str, approval: GDPRDeletionApprovalRequest
    ) -> Optional[GDPRDataRequest]:
        """Approve a destructive GDPR deletion request before it can run."""
        if approval.confirmation != "CONFIRM_DELETE":
            raise ValueError("Deletion confirmation must be CONFIRM_DELETE")

        current = await self.repository.get_data_request(request_id)
        if not current:
            return None
        if current.request_type != GDPRDataRequestType.DELETE:
            raise ValueError("Only delete requests can be approved")
        if current.status not in {
            GDPRDataRequestStatus.PENDING,
            GDPRDataRequestStatus.FAILED,
        }:
            raise ValueError("Only pending or failed delete requests can be approved")

        metadata = dict(current.metadata or {})
        metadata["deletion_approval"] = {
            "approved_by": approval.approved_by,
            "notes": approval.notes,
            "approved_at": datetime.utcnow().isoformat(),
        }

        updated = await self.repository.update_data_request(
            request_id,
            approved_by=approval.approved_by,
            approved_at=datetime.utcnow(),
            metadata=metadata,
        )
        if updated:
            await self._publish_data_request_event(
                "compliance.gdpr_request.deletion_approved", updated
            )
            await self._publish_gdpr_admin_audit_event(
                "deletion_approved",
                updated,
                actor_user_id=approval.approved_by,
                changes={"approved_by": {"after": approval.approved_by}},
            )
        return updated

    async def run_data_request(
        self,
        request_id: str,
        run_options: Optional[GDPRDataRequestRunRequest] = None,
    ) -> Optional[GDPRDataRequest]:
        """Run a queued GDPR export/delete request and persist per-service status."""
        current = await self.repository.get_data_request(request_id)
        if not current:
            return None
        if current.status == GDPRDataRequestStatus.COMPLETED:
            return current
        if (
            current.request_type == GDPRDataRequestType.DELETE
            and not current.approved_by
        ):
            raise ValueError("Delete request must be approved before it can run")

        await self.repository.update_data_request(
            request_id, status=GDPRDataRequestStatus.IN_PROGRESS
        )

        try:
            service_names = self._gdpr_service_names(run_options)
            if current.request_type == GDPRDataRequestType.EXPORT:
                result = await self._run_export_data_request(current, service_names)
            else:
                result = await self._run_delete_data_request(current, service_names)

            completed = await self.repository.update_data_request(
                request_id,
                status=GDPRDataRequestStatus.COMPLETED,
                artifact_uri=result.get("artifact_uri"),
                per_service_status=result["per_service_status"],
                metadata=result["metadata"],
                completed_at=datetime.utcnow(),
            )
            if completed:
                await self._publish_data_request_event(
                    "compliance.gdpr_request.completed", completed
                )
                await self._publish_gdpr_admin_audit_event(
                    "completed",
                    completed,
                    actor_user_id=completed.approved_by or completed.requested_by,
                    changes={
                        "status": {"after": completed.status.value},
                        "artifact_uri": {"after": completed.artifact_uri},
                    },
                    metadata={
                        "tombstone": (completed.metadata or {})
                        .get("deletion_result", {})
                        .get("tombstone")
                    }
                    if completed.request_type == GDPRDataRequestType.DELETE
                    else {"artifact_uri": completed.artifact_uri},
                )
            return completed

        except Exception as exc:
            failed = await self.repository.update_data_request(
                request_id,
                status=GDPRDataRequestStatus.FAILED,
                failure_reason=str(exc),
                completed_at=datetime.utcnow(),
            )
            if failed:
                await self._publish_data_request_event(
                    "compliance.gdpr_request.failed", failed
                )
                await self._publish_gdpr_admin_audit_event(
                    "failed",
                    failed,
                    actor_user_id=failed.approved_by or failed.requested_by,
                    changes={
                        "status": {"after": failed.status.value},
                        "failure_reason": {"after": failed.failure_reason},
                    },
                )
            raise

    def _gdpr_service_names(
        self, run_options: Optional[GDPRDataRequestRunRequest]
    ) -> List[str]:
        if run_options and run_options.service_names:
            return list(dict.fromkeys(run_options.service_names))

        service_names = ["compliance_service"]
        for service_name in sorted(self._gdpr_export_clients().keys()):
            if service_name not in service_names:
                service_names.append(service_name)
        return service_names

    async def _run_export_data_request(
        self, data_request: GDPRDataRequest, service_names: List[str]
    ) -> Dict[str, Any]:
        generated_at = datetime.utcnow()
        per_service_status = self._empty_service_status(service_names)
        exported_services: Dict[str, Any] = {}
        manifest_services: Dict[str, Any] = {}

        if "compliance_service" in service_names:
            checks = await self.repository.get_checks_by_user(
                user_id=data_request.user_id,
                limit=10000,
            )
            exported_services["compliance_service"] = {
                "records": len(checks),
                "checks": [check.model_dump(mode="json") for check in checks],
            }
            manifest_services["compliance_service"] = {"records": len(checks)}
            per_service_status["compliance_service"] = {
                "status": "completed",
                "records_exported": len(checks),
                "records_deleted": 0,
                "completed_at": datetime.utcnow().isoformat(),
            }

        for service_name in service_names:
            if service_name == "compliance_service":
                continue
            client = self._gdpr_export_clients().get(service_name)
            if not client:
                continue

            payload = await self._export_external_gdpr_service(
                service_name=service_name,
                client=client,
                data_request=data_request,
            )
            records_exported = self._count_export_records(payload)
            exported_services[service_name] = {
                "records": records_exported,
                "payload": payload,
            }
            manifest_services[service_name] = {"records": records_exported}
            per_service_status[service_name] = {
                "status": "completed",
                "records_exported": records_exported,
                "records_deleted": 0,
                "completed_at": datetime.utcnow().isoformat(),
            }

        export_bundle = {
            "request_id": data_request.request_id,
            "request_type": data_request.request_type.value,
            "user_id": data_request.user_id,
            "organization_id": data_request.organization_id,
            "generated_at": generated_at.isoformat(),
            "services": exported_services,
        }
        artifact = await self._persist_export_artifact(data_request, export_bundle)
        artifact_uri = artifact["artifact_uri"]
        records_exported = sum(
            int(service.get("records", 0)) for service in manifest_services.values()
        )

        metadata = dict(data_request.metadata or {})
        metadata["export_manifest"] = {
            "request_id": data_request.request_id,
            "user_id": data_request.user_id,
            "organization_id": data_request.organization_id,
            "artifact_uri": artifact_uri,
            "storage_file_id": artifact.get("storage_file_id"),
            "download_url": artifact.get("download_url"),
            "filename": artifact["filename"],
            "content_type": artifact["content_type"],
            "size_bytes": artifact["size_bytes"],
            "sha256": artifact["sha256"],
            "generated_at": generated_at.isoformat(),
            "services": manifest_services,
        }
        for status in per_service_status.values():
            if status.get("status") == "completed":
                status["artifact_uri"] = artifact_uri
        return {
            "records_exported": records_exported,
            "artifact_uri": artifact_uri,
            "per_service_status": per_service_status,
            "metadata": metadata,
        }

    async def _run_delete_data_request(
        self, data_request: GDPRDataRequest, service_names: List[str]
    ) -> Dict[str, Any]:
        deleted_at = datetime.utcnow()
        deleted_count = await self.repository.delete_user_data(data_request.user_id)
        cascade_event = await self._publish_user_deleted_cascade_event(data_request)
        if cascade_event.get("status") == "failed":
            raise RuntimeError(
                "Failed to publish GDPR user.deleted cascade event: "
                f"{cascade_event.get('error', 'unknown error')}"
            )
        per_service_status = self._empty_service_status(service_names)
        per_service_status["compliance_service"] = {
            "status": "completed",
            "records_exported": 0,
            "records_deleted": deleted_count,
            "completed_at": datetime.utcnow().isoformat(),
        }

        metadata = dict(data_request.metadata or {})
        tombstone = self._build_gdpr_deletion_tombstone(
            data_request=data_request,
            deleted_count=deleted_count,
            cascade_event=cascade_event,
            deleted_at=deleted_at,
        )
        metadata["deletion_result"] = {
            "request_id": data_request.request_id,
            "subject_user_hash": tombstone["subject_user_hash"],
            "organization_id": data_request.organization_id,
            "deleted_at": deleted_at.isoformat(),
            "services": {"compliance_service": {"records_deleted": deleted_count}},
            "cascade_event": cascade_event,
            "tombstone": tombstone,
        }
        return {
            "artifact_uri": data_request.artifact_uri,
            "per_service_status": per_service_status,
            "metadata": metadata,
        }

    def _empty_service_status(self, service_names: List[str]) -> Dict[str, Any]:
        return {
            service_name: {
                "status": "not_configured",
                "records_exported": 0,
                "records_deleted": 0,
                "error": "adapter_not_configured",
            }
            for service_name in service_names
            if service_name != "compliance_service"
        }

    def _default_gdpr_export_clients(self) -> Dict[str, Any]:
        clients: Dict[str, Any] = {}
        if self._gdpr_export_client_enabled("GDPR_ACCOUNT_EXPORT_ENABLED"):
            from microservices.account_service.client import AccountServiceClient

            clients["account_service"] = AccountServiceClient(
                base_url=os.getenv("ACCOUNT_SERVICE_URL", "http://localhost:8202")
            )

        if self._gdpr_export_client_enabled("GDPR_MEMORY_EXPORT_ENABLED"):
            from microservices.memory_service.client import MemoryServiceClient

            clients["memory_service"] = MemoryServiceClient(
                base_url=os.getenv("MEMORY_SERVICE_URL", "http://localhost:8223")
            )
        if self._gdpr_export_client_enabled("GDPR_STORAGE_EXPORT_ENABLED"):
            from microservices.storage_service.client import StorageServiceClient

            clients["storage_service"] = StorageServiceClient(
                base_url=os.getenv("STORAGE_SERVICE_URL", "http://localhost:8209")
            )
        if self._gdpr_export_client_enabled("GDPR_BILLING_EXPORT_ENABLED"):
            from microservices.billing_service.client import BillingServiceClient

            clients["billing_service"] = BillingServiceClient(
                base_url=os.getenv("BILLING_SERVICE_URL", "http://localhost:8220")
            )
        if self._gdpr_export_client_enabled("GDPR_SESSION_EXPORT_ENABLED"):
            from microservices.session_service.clients.session_client import (
                SessionServiceClient,
            )

            clients["session_service"] = SessionServiceClient(
                base_url=os.getenv("SESSION_SERVICE_URL", "http://localhost:8207")
            )
        if self._gdpr_export_client_enabled("GDPR_PROJECT_EXPORT_ENABLED"):
            from microservices.project_service.client import ProjectServiceClient

            clients["project_service"] = ProjectServiceClient(
                base_url=os.getenv("PROJECT_SERVICE_URL", "http://localhost:8260")
            )
        return clients

    @staticmethod
    def _gdpr_export_client_enabled(env_key: str) -> bool:
        configured = os.getenv(env_key, "true").lower()
        return configured not in {"0", "false", "no", "off"}

    def _gdpr_export_clients(self) -> Dict[str, Any]:
        return dict(getattr(self, "gdpr_export_clients", None) or {})

    async def _export_external_gdpr_service(
        self,
        *,
        service_name: str,
        client: Any,
        data_request: GDPRDataRequest,
    ) -> Dict[str, Any]:
        exporter = getattr(client, "export_user_data", None)
        if exporter is None:
            exporter = getattr(client, "export_memory", None)
        if exporter is None:
            raise RuntimeError(f"{service_name} does not expose a GDPR export adapter")

        payload = await exporter(
            user_id=data_request.user_id,
            organization_id=data_request.organization_id,
            request_id=data_request.request_id,
        )
        if payload is None:
            return {}
        if hasattr(payload, "model_dump"):
            return payload.model_dump(mode="json")
        return dict(payload)

    @staticmethod
    def _count_export_records(payload: Dict[str, Any]) -> int:
        counts = payload.get("counts") if isinstance(payload, dict) else None
        if isinstance(counts, dict):
            for key in ("records", "memories", "items", "total"):
                value = counts.get(key)
                if isinstance(value, int):
                    return value
            by_type = counts.get("by_type")
            if isinstance(by_type, dict):
                return sum(
                    value for value in by_type.values() if isinstance(value, int)
                )

        for key in ("records", "memories", "items", "checks"):
            value = payload.get(key)
            if isinstance(value, list):
                return len(value)
            if isinstance(value, int):
                return value
        return 0

    def _gdpr_artifact_storage_enabled(self) -> bool:
        return bool(getattr(self, "enable_gdpr_artifact_storage", False))

    @staticmethod
    def _gdpr_subject_hash(user_id: str) -> str:
        return hashlib.sha256(user_id.encode("utf-8")).hexdigest()

    def _build_gdpr_deletion_tombstone(
        self,
        *,
        data_request: GDPRDataRequest,
        deleted_count: int,
        cascade_event: Dict[str, Any],
        deleted_at: datetime,
    ) -> Dict[str, Any]:
        return {
            "gdpr_request_id": data_request.request_id,
            "request_type": data_request.request_type.value,
            "subject_user_hash": self._gdpr_subject_hash(data_request.user_id),
            "organization_id": data_request.organization_id,
            "requested_by": data_request.requested_by,
            "approved_by": data_request.approved_by,
            "deleted_at": deleted_at.isoformat(),
            "records_deleted": {"compliance_service": deleted_count},
            "cascade_event_status": cascade_event.get("status"),
            "cascade_event_subject": cascade_event.get("subject"),
            "retention_policy": "gdpr_erasure_tombstone",
        }

    async def _persist_export_artifact(
        self, data_request: GDPRDataRequest, export_bundle: Dict[str, Any]
    ) -> Dict[str, Any]:
        filename = f"{data_request.request_id}.json"
        file_content = json.dumps(
            export_bundle,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        sha256 = hashlib.sha256(file_content).hexdigest()
        base_artifact = {
            "filename": filename,
            "content_type": "application/json",
            "size_bytes": len(file_content),
            "sha256": sha256,
        }

        if not self._gdpr_artifact_storage_enabled():
            return {
                **base_artifact,
                "artifact_uri": f"compliance://gdpr-exports/{filename}",
                "storage_file_id": None,
                "download_url": None,
            }

        upload_result = await self._upload_export_artifact(
            data_request=data_request,
            file_content=file_content,
            filename=filename,
            sha256=sha256,
        )
        if not upload_result or not upload_result.get("file_id"):
            raise RuntimeError("Failed to persist GDPR export artifact to storage")

        storage_file_id = upload_result["file_id"]
        return {
            **base_artifact,
            "artifact_uri": f"storage://files/{storage_file_id}",
            "storage_file_id": storage_file_id,
            "download_url": upload_result.get("download_url"),
        }

    async def _upload_export_artifact(
        self,
        *,
        data_request: GDPRDataRequest,
        file_content: bytes,
        filename: str,
        sha256: str,
    ) -> Optional[Dict[str, Any]]:
        metadata = {
            "gdpr_request_id": data_request.request_id,
            "gdpr_request_type": data_request.request_type.value,
            "artifact_sha256": sha256,
            "classification": "gdpr_export",
            "retention_policy": "privacy_request",
        }
        upload_kwargs = {
            "file_content": file_content,
            "filename": filename,
            "user_id": data_request.user_id,
            "organization_id": data_request.organization_id,
            "access_level": "restricted",
            "content_type": "application/json",
            "metadata": metadata,
            "tags": ["gdpr", "data-export", data_request.request_id],
            "enable_indexing": False,
        }

        client = getattr(self, "artifact_storage_client", None)
        if client is not None:
            return await client.upload_file(**upload_kwargs)

        from microservices.storage_service.client import StorageServiceClient

        async with StorageServiceClient() as storage_client:
            return await storage_client.upload_file(**upload_kwargs)

    async def _get_export_artifact_download_url(
        self,
        *,
        storage_file_id: str,
        user_id: str,
        expires_minutes: int,
    ) -> Optional[Dict[str, Any]]:
        client = getattr(self, "artifact_storage_client", None)
        if client is not None:
            return await client.get_download_url(
                storage_file_id,
                user_id,
                expires_minutes=expires_minutes,
            )

        from microservices.storage_service.client import StorageServiceClient

        async with StorageServiceClient() as storage_client:
            return await storage_client.get_download_url(
                storage_file_id,
                user_id,
                expires_minutes=expires_minutes,
            )

    async def _publish_user_deleted_cascade_event(
        self, data_request: GDPRDataRequest
    ) -> Dict[str, Any]:
        if not self.event_bus:
            return {
                "status": "skipped",
                "reason": "event_bus_unavailable",
            }

        try:
            from core.nats_client import Event

            event = Event(
                event_type="user.deleted",
                source="compliance_service",
                data={
                    "user_id": data_request.user_id,
                    "organization_id": data_request.organization_id,
                    "reason": "gdpr_data_request",
                    "gdpr_request_id": data_request.request_id,
                    "requested_by": data_request.requested_by,
                    "approved_by": data_request.approved_by,
                    "deleted_at": datetime.utcnow().isoformat(),
                },
                metadata={
                    "gdpr_request_id": data_request.request_id,
                    "gdpr_request_type": data_request.request_type.value,
                },
            )
            subject = "account_service.user.deleted"
            published = await self.event_bus.publish_event(event, subject=subject)
            if published is False:
                return {
                    "status": "failed",
                    "subject": subject,
                    "event_id": event.id,
                    "error": "event_bus_publish_returned_false",
                }

            return {
                "status": "published",
                "subject": subject,
                "event_id": event.id,
            }
        except Exception as exc:
            logger.warning("Failed to publish GDPR user.deleted cascade event: %s", exc)
            return {
                "status": "failed",
                "subject": "account_service.user.deleted",
                "error": str(exc),
            }

    async def _publish_gdpr_admin_audit_event(
        self,
        action: str,
        data_request: GDPRDataRequest,
        *,
        actor_user_id: Optional[str],
        changes: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not self.event_bus:
            return

        try:
            from core.nats_client import Event

            action_name = f"gdpr_data_request.{action}"
            subject = f"admin.action.gdpr_data_request.{action}"
            audit_metadata = {
                "service": "compliance_service",
                "gdpr_request_id": data_request.request_id,
                "request_type": data_request.request_type.value,
                "request_status": data_request.status.value,
                "subject_user_hash": self._gdpr_subject_hash(data_request.user_id),
                "organization_id": data_request.organization_id,
                "retention_policy": "gdpr_admin_audit",
            }
            if metadata:
                audit_metadata.update(
                    {key: value for key, value in metadata.items() if value is not None}
                )

            event = Event(
                event_type=subject,
                source="compliance_service",
                data={
                    "admin_user_id": actor_user_id or "system",
                    "action": action_name,
                    "resource_type": "gdpr_data_request",
                    "resource_id": data_request.request_id,
                    "changes": changes or {},
                    "timestamp": datetime.utcnow().isoformat(),
                    "metadata": audit_metadata,
                },
                metadata={
                    "gdpr_request_id": data_request.request_id,
                    "gdpr_request_type": data_request.request_type.value,
                },
            )
            await self.event_bus.publish_event(event, subject=subject)
        except Exception as exc:
            logger.warning("Failed to publish GDPR admin audit event: %s", exc)

    async def _publish_data_request_event(
        self, event_type: str, data_request: GDPRDataRequest
    ) -> None:
        if not self.event_bus:
            return

        try:
            from core.nats_client import Event

            event = Event(
                event_type=event_type,
                source="compliance_service",
                data={
                    "request_id": data_request.request_id,
                    "request_type": data_request.request_type.value,
                    "status": data_request.status.value,
                    "user_id": data_request.user_id,
                    "organization_id": data_request.organization_id,
                    "timestamp": datetime.utcnow().isoformat(),
                },
                metadata=data_request.metadata or {},
            )
            await self.event_bus.publish_event(event)
        except Exception as exc:
            logger.warning("Failed to publish GDPR data request event: %s", exc)

    # ====================
    # 核心检查方法
    # ====================

    async def perform_compliance_check(
        self, request: ComplianceCheckRequest
    ) -> ComplianceCheckResponse:
        """执行合规检查 - 主入口"""
        start_time = time.time()
        check_id = str(uuid.uuid4())

        try:
            logger.info(
                f"Starting compliance check {check_id} for user {request.user_id}"
            )

            # 获取适用的策略
            policy = await self._get_applicable_policy(request)

            # 执行各类检查
            check_results = await self._run_checks(request, check_id)

            # 评估总体合规状态
            overall_status, risk_level, violations, warnings = self._evaluate_results(
                check_results, policy
            )

            # 决定行动
            action_required, action_taken = await self._determine_action(
                overall_status, risk_level, policy
            )

            # 创建检查记录
            compliance_check = ComplianceCheck(
                check_id=check_id,
                check_type=request.check_types[0]
                if request.check_types
                else ComplianceCheckType.CONTENT_MODERATION,
                content_type=request.content_type,
                status=overall_status,
                risk_level=risk_level,
                user_id=request.user_id,
                organization_id=request.organization_id,
                session_id=request.session_id,
                request_id=request.request_id,
                content_id=request.content_id,
                content_hash=self._hash_content(request.content)
                if request.content
                else None,
                violations=violations,
                warnings=warnings,
                detected_issues=[v.get("issue", "") for v in violations],
                action_taken=action_taken,
                metadata=request.metadata,
                checked_at=datetime.utcnow(),
            )

            # 保存到数据库
            await self.repository.create_check(compliance_check)

            # 发送事件通知
            # 1. Always publish check performed event
            await publish_compliance_check_performed(
                self.event_bus,
                check_id=check_id,
                user_id=request.user_id,
                check_type=compliance_check.check_type.value,
                content_type=compliance_check.content_type.value,
                status=overall_status.value,
                risk_level=risk_level.value,
                violations_count=len(violations),
                warnings_count=len(warnings),
                action_taken=action_taken,
                organization_id=request.organization_id,
                processing_time_ms=(time.time() - start_time) * 1000,
                metadata=request.metadata,
            )

            # 2. If violations detected, publish violation event
            if overall_status == ComplianceStatus.FAIL and violations:
                await publish_compliance_violation_detected(
                    self.event_bus,
                    check_id=check_id,
                    user_id=request.user_id,
                    violations=violations,
                    risk_level=risk_level.value,
                    action_taken=action_taken,
                    organization_id=request.organization_id,
                    requires_review=(
                        risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
                    ),
                    blocked_content=(action_taken == "blocked"),
                    metadata=request.metadata,
                )

            # 3. If warnings issued, publish warning event
            if warnings:
                await publish_compliance_warning_issued(
                    self.event_bus,
                    check_id=check_id,
                    user_id=request.user_id,
                    warnings=warnings,
                    risk_level=risk_level.value,
                    organization_id=request.organization_id,
                    allowed_with_warning=(action_taken not in ["blocked", "blocked"]),
                    metadata=request.metadata,
                )

            # 构建响应
            processing_time = (time.time() - start_time) * 1000

            response = ComplianceCheckResponse(
                check_id=check_id,
                status=overall_status,
                risk_level=risk_level,
                passed=(overall_status == ComplianceStatus.PASS),
                violations=violations,
                warnings=warnings,
                moderation_result=check_results.get("moderation"),
                pii_result=check_results.get("pii"),
                injection_result=check_results.get("injection"),
                action_required=action_required,
                action_taken=action_taken,
                message=self._get_response_message(overall_status, risk_level),
                checked_at=datetime.utcnow(),
                processing_time_ms=processing_time,
            )

            logger.info(
                f"Compliance check {check_id} completed: {overall_status.value}"
            )
            return response

        except Exception as e:
            logger.error(f"Error in compliance check {check_id}: {e}")
            return ComplianceCheckResponse(
                check_id=check_id,
                status=ComplianceStatus.FAIL,
                risk_level=RiskLevel.HIGH,
                passed=False,
                violations=[
                    {"issue": "System error during compliance check", "details": str(e)}
                ],
                warnings=[],
                action_required="review",
                action_taken="blocked",
                message="Compliance check failed due to system error",
                checked_at=datetime.utcnow(),
                processing_time_ms=(time.time() - start_time) * 1000,
            )

    async def _run_checks(
        self, request: ComplianceCheckRequest, check_id: str
    ) -> Dict[str, Any]:
        """运行所有需要的检查"""
        results = {}

        # 并发运行多个检查
        tasks = []

        if ComplianceCheckType.CONTENT_MODERATION in request.check_types:
            tasks.append(self._check_content_moderation(request, check_id))

        if ComplianceCheckType.PII_DETECTION in request.check_types:
            tasks.append(self._check_pii_detection(request, check_id))

        if ComplianceCheckType.PROMPT_INJECTION in request.check_types:
            tasks.append(self._check_prompt_injection(request, check_id))

        if ComplianceCheckType.TOXICITY in request.check_types:
            tasks.append(self._check_toxicity(request, check_id))

        # 等待所有检查完成
        if tasks:
            check_results = await asyncio.gather(*tasks, return_exceptions=True)

            # 整理结果
            for i, check_type in enumerate(request.check_types):
                if i < len(check_results):
                    if isinstance(check_results[i], Exception):
                        logger.error(
                            f"Check {check_type.value} failed: {check_results[i]}"
                        )
                    else:
                        results[check_type.value.split("_")[0]] = check_results[i]

        return results

    # ====================
    # 内容审核检查
    # ====================

    async def _check_content_moderation(
        self, request: ComplianceCheckRequest, check_id: str
    ) -> ContentModerationResult:
        """内容审核检查"""
        try:
            logger.info(f"Running content moderation for check {check_id}")

            if (
                request.content_type == ContentType.TEXT
                or request.content_type == ContentType.PROMPT
            ):
                return await self._moderate_text(request.content, check_id)

            elif request.content_type == ContentType.IMAGE:
                return await self._moderate_image(
                    request.content_id or request.content_url, check_id
                )

            elif request.content_type == ContentType.AUDIO:
                return await self._moderate_audio(
                    request.content_id or request.content_url, check_id
                )

            else:
                # 默认返回通过
                return ContentModerationResult(
                    check_id=check_id,
                    content_type=request.content_type,
                    status=ComplianceStatus.PASS,
                    risk_level=RiskLevel.NONE,
                    confidence=1.0,
                    recommendation="allow",
                )

        except Exception as e:
            logger.error(f"Content moderation error: {e}")
            return ContentModerationResult(
                check_id=check_id,
                content_type=request.content_type,
                status=ComplianceStatus.FAIL,
                risk_level=RiskLevel.HIGH,
                confidence=0.0,
                recommendation="review",
                explanation=str(e),
            )

    async def _moderate_text(self, text: str, check_id: str) -> ContentModerationResult:
        """文本内容审核"""
        if not text:
            return ContentModerationResult(
                check_id=check_id,
                content_type=ContentType.TEXT,
                status=ComplianceStatus.PASS,
                risk_level=RiskLevel.NONE,
                confidence=1.0,
                recommendation="allow",
            )

        categories = {}
        flagged_categories = []
        max_score = 0.0

        # 方法1: 使用OpenAI Moderation API（如果可用）
        if self.enable_openai_moderation:
            try:
                openai_result = await self._call_openai_moderation(text)
                if openai_result:
                    categories = openai_result.get("categories", {})
                    for cat, flagged in openai_result.get(
                        "category_scores", {}
                    ).items():
                        score = float(flagged)
                        categories[cat] = score
                        if score > max_score:
                            max_score = score
                        if score > 0.5:  # 阈值
                            flagged_categories.append(cat)
            except Exception as e:
                logger.warning(f"OpenAI moderation failed: {e}")

        # 方法2: 本地规则检查（备选）
        if self.enable_local_checks:
            local_result = await self._local_text_moderation(text)
            categories.update(local_result["categories"])
            flagged_categories.extend(local_result["flagged"])
            max_score = max(max_score, local_result.get("max_score", 0))

        # 确定状态和风险级别
        if max_score >= 0.9:
            status = ComplianceStatus.BLOCKED
            risk_level = RiskLevel.CRITICAL
            recommendation = "block"
        elif max_score >= 0.7:
            status = ComplianceStatus.FAIL
            risk_level = RiskLevel.HIGH
            recommendation = "block"
        elif max_score >= 0.5:
            status = ComplianceStatus.FLAGGED
            risk_level = RiskLevel.MEDIUM
            recommendation = "review"
        elif max_score >= 0.3:
            status = ComplianceStatus.WARNING
            risk_level = RiskLevel.LOW
            recommendation = "allow"
        else:
            status = ComplianceStatus.PASS
            risk_level = RiskLevel.NONE
            recommendation = "allow"

        return ContentModerationResult(
            check_id=check_id,
            content_type=ContentType.TEXT,
            status=status,
            risk_level=risk_level,
            categories=categories,
            flagged_categories=flagged_categories,
            confidence=max_score,
            recommendation=recommendation,
            explanation=f"Flagged categories: {', '.join(flagged_categories)}"
            if flagged_categories
            else None,
        )

    async def _moderate_image(
        self, image_ref: str, check_id: str
    ) -> ContentModerationResult:
        """图片内容审核"""
        # 这里应该集成AWS Rekognition, Google Vision API, 或Azure Content Moderator
        # 简化示例:
        logger.info(f"Image moderation for {image_ref}")

        # TODO: 实际实现图片审核
        # 可以集成:
        # - AWS Rekognition (DetectModerationLabels)
        # - Google Cloud Vision (SafeSearchDetection)
        # - Azure Content Moderator

        return ContentModerationResult(
            check_id=check_id,
            content_type=ContentType.IMAGE,
            status=ComplianceStatus.PASS,
            risk_level=RiskLevel.NONE,
            confidence=0.9,
            recommendation="allow",
            explanation="Image moderation not fully implemented - passed by default",
        )

    async def _moderate_audio(
        self, audio_ref: str, check_id: str
    ) -> ContentModerationResult:
        """音频内容审核"""
        # 音频审核流程:
        # 1. 使用语音转文字 (Whisper, AWS Transcribe, Google Speech-to-Text)
        # 2. 对转录文本进行审核
        logger.info(f"Audio moderation for {audio_ref}")

        # TODO: 实际实现音频审核

        return ContentModerationResult(
            check_id=check_id,
            content_type=ContentType.AUDIO,
            status=ComplianceStatus.PASS,
            risk_level=RiskLevel.NONE,
            confidence=0.9,
            recommendation="allow",
            explanation="Audio moderation not fully implemented - passed by default",
        )

    # ====================
    # PII 检测
    # ====================

    async def _check_pii_detection(
        self, request: ComplianceCheckRequest, check_id: str
    ) -> PIIDetectionResult:
        """PII检测"""
        try:
            if not request.content or request.content_type not in [
                ContentType.TEXT,
                ContentType.PROMPT,
            ]:
                return PIIDetectionResult(
                    check_id=check_id,
                    status=ComplianceStatus.PASS,
                    risk_level=RiskLevel.NONE,
                    detected_pii=[],
                    pii_count=0,
                )

            detected_pii = []

            # 使用正则表达式检测常见PII
            pii_patterns = {
                PIIType.EMAIL: r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                PIIType.PHONE: r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
                PIIType.SSN: r"\b\d{3}-\d{2}-\d{4}\b",
                PIIType.CREDIT_CARD: r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
                PIIType.IP_ADDRESS: r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
            }

            for pii_type, pattern in pii_patterns.items():
                matches = re.finditer(pattern, request.content)
                for match in matches:
                    detected_pii.append(
                        {
                            "type": pii_type.value,
                            "value": self._mask_pii(match.group()),
                            "location": match.span(),
                            "confidence": 0.95,
                        }
                    )

            # 判断风险级别
            pii_count = len(detected_pii)
            if pii_count >= 5:
                risk_level = RiskLevel.CRITICAL
                status = ComplianceStatus.FAIL
                needs_redaction = True
            elif pii_count >= 3:
                risk_level = RiskLevel.HIGH
                status = ComplianceStatus.FLAGGED
                needs_redaction = True
            elif pii_count >= 1:
                risk_level = RiskLevel.MEDIUM
                status = ComplianceStatus.WARNING
                needs_redaction = True
            else:
                risk_level = RiskLevel.NONE
                status = ComplianceStatus.PASS
                needs_redaction = False

            return PIIDetectionResult(
                check_id=check_id,
                status=status,
                detected_pii=detected_pii,
                pii_count=pii_count,
                pii_types=[PIIType(p["type"]) for p in detected_pii],
                risk_level=risk_level,
                needs_redaction=needs_redaction,
            )

        except Exception as e:
            logger.error(f"PII detection error: {e}")
            return PIIDetectionResult(
                check_id=check_id,
                status=ComplianceStatus.FAIL,
                risk_level=RiskLevel.HIGH,
                detected_pii=[],
                pii_count=0,
            )

    # ====================
    # 提示词注入检测
    # ====================

    async def _check_prompt_injection(
        self, request: ComplianceCheckRequest, check_id: str
    ) -> PromptInjectionResult:
        """提示词注入检测"""
        try:
            if not request.content or request.content_type not in [
                ContentType.TEXT,
                ContentType.PROMPT,
            ]:
                return PromptInjectionResult(
                    check_id=check_id,
                    status=ComplianceStatus.PASS,
                    risk_level=RiskLevel.NONE,
                    is_injection_detected=False,
                    confidence=1.0,
                    recommendation="allow",
                )

            text = request.content.lower()

            # 检测常见的注入模式
            injection_patterns = [
                r"ignore\s+(previous|above|prior)\s+(instructions|prompts?|commands?)",
                r"forget\s+(everything|all|previous)",
                r"you\s+are\s+now",
                r"system\s*:\s*",
                r"</?\s*system\s*>",
                r"jailbreak",
                r"developer\s+mode",
                r"override\s+(safety|rules|restrictions)",
            ]

            detected_patterns = []
            max_confidence = 0.0

            for pattern in injection_patterns:
                if re.search(pattern, text):
                    detected_patterns.append(pattern)
                    max_confidence = max(max_confidence, 0.8)

            # 检测异常结构
            suspicious_tokens = []
            if "<|" in text or "|>" in text:
                suspicious_tokens.append("special_tokens")
                max_confidence = max(max_confidence, 0.6)

            if "###" in text or "```" in text:
                suspicious_tokens.append("code_blocks")
                max_confidence = max(max_confidence, 0.4)

            # 判断结果
            is_injection = len(detected_patterns) > 0

            if max_confidence >= 0.8:
                status = ComplianceStatus.FAIL
                risk_level = RiskLevel.HIGH
                injection_type = "direct"
                recommendation = "block"
            elif max_confidence >= 0.5:
                status = ComplianceStatus.FLAGGED
                risk_level = RiskLevel.MEDIUM
                injection_type = "suspicious"
                recommendation = "review"
            else:
                status = ComplianceStatus.PASS
                risk_level = RiskLevel.NONE
                injection_type = None
                recommendation = "allow"

            return PromptInjectionResult(
                check_id=check_id,
                status=status,
                risk_level=risk_level,
                is_injection_detected=is_injection,
                injection_type=injection_type,
                confidence=max_confidence,
                detected_patterns=detected_patterns,
                suspicious_tokens=suspicious_tokens,
                recommendation=recommendation,
                explanation=f"Detected patterns: {', '.join(detected_patterns)}"
                if detected_patterns
                else None,
            )

        except Exception as e:
            logger.error(f"Prompt injection detection error: {e}")
            return PromptInjectionResult(
                check_id=check_id,
                status=ComplianceStatus.FAIL,
                risk_level=RiskLevel.HIGH,
                is_injection_detected=True,
                confidence=0.0,
                recommendation="block",
            )

    # ====================
    # 毒性检测
    # ====================

    async def _check_toxicity(
        self, request: ComplianceCheckRequest, check_id: str
    ) -> Dict[str, Any]:
        """毒性检测"""
        # TODO: 集成 Perspective API 或类似服务
        return {
            "check_id": check_id,
            "toxicity_score": 0.0,
            "status": ComplianceStatus.PASS.value,
        }

    # ====================
    # 辅助方法
    # ====================

    async def _call_openai_moderation(self, text: str) -> Optional[Dict[str, Any]]:
        """调用OpenAI Moderation API"""
        try:
            # TODO: 实际实现OpenAI API调用
            # import openai
            # response = await openai.Moderation.acreate(input=text)
            # return response["results"][0]

            # 模拟返回
            return None
        except Exception as e:
            logger.error(f"OpenAI moderation API error: {e}")
            return None

    async def _local_text_moderation(self, text: str) -> Dict[str, Any]:
        """本地文本审核（基于规则）"""
        categories = {}
        flagged = []
        max_score = 0.0

        # 简单的关键词检测
        hate_keywords = ["hate", "racist", "discrimination"]
        violence_keywords = ["kill", "murder", "violence", "attack"]

        text_lower = text.lower()

        # 仇恨言论检测
        hate_count = sum(1 for kw in hate_keywords if kw in text_lower)
        if hate_count > 0:
            score = min(hate_count * 0.3, 1.0)
            categories["hate"] = score
            max_score = max(max_score, score)
            if score > 0.5:
                flagged.append("hate")

        # 暴力内容检测
        violence_count = sum(1 for kw in violence_keywords if kw in text_lower)
        if violence_count > 0:
            score = min(violence_count * 0.3, 1.0)
            categories["violence"] = score
            max_score = max(max_score, score)
            if score > 0.5:
                flagged.append("violence")

        return {"categories": categories, "flagged": flagged, "max_score": max_score}

    def _evaluate_results(
        self, check_results: Dict[str, Any], policy: Optional[CompliancePolicy]
    ) -> Tuple[ComplianceStatus, RiskLevel, List[Dict], List[Dict]]:
        """评估所有检查结果"""
        violations = []
        warnings = []
        max_risk = RiskLevel.NONE
        worst_status = ComplianceStatus.PASS

        status_priority = {
            ComplianceStatus.PASS: 0,
            ComplianceStatus.WARNING: 1,
            ComplianceStatus.FLAGGED: 2,
            ComplianceStatus.FAIL: 3,
            ComplianceStatus.BLOCKED: 4,
        }

        risk_priority = {
            RiskLevel.NONE: 0,
            RiskLevel.LOW: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.HIGH: 3,
            RiskLevel.CRITICAL: 4,
        }

        # 遍历所有检查结果
        for check_type, result in check_results.items():
            if hasattr(result, "status"):
                if status_priority[result.status] > status_priority[worst_status]:
                    worst_status = result.status

                if risk_priority[result.risk_level] > risk_priority[max_risk]:
                    max_risk = result.risk_level

                # 收集违规和警告
                if result.status in [ComplianceStatus.FAIL, ComplianceStatus.BLOCKED]:
                    violations.append(
                        {
                            "check_type": check_type,
                            "issue": result.recommendation
                            if hasattr(result, "recommendation")
                            else "Compliance violation",
                            "details": result.explanation
                            if hasattr(result, "explanation")
                            else "",
                        }
                    )
                elif result.status in [
                    ComplianceStatus.WARNING,
                    ComplianceStatus.FLAGGED,
                ]:
                    warnings.append(
                        {
                            "check_type": check_type,
                            "issue": "Potential compliance issue",
                            "details": result.explanation
                            if hasattr(result, "explanation")
                            else "",
                        }
                    )

        return worst_status, max_risk, violations, warnings

    async def _determine_action(
        self,
        status: ComplianceStatus,
        risk_level: RiskLevel,
        policy: Optional[CompliancePolicy],
    ) -> Tuple[str, Optional[str]]:
        """决定应采取的行动"""
        if status == ComplianceStatus.BLOCKED or risk_level == RiskLevel.CRITICAL:
            return "block", "blocked"
        elif status == ComplianceStatus.FAIL or risk_level == RiskLevel.HIGH:
            return "block", "blocked"
        elif status == ComplianceStatus.FLAGGED or risk_level == RiskLevel.MEDIUM:
            return "review", "flagged_for_review"
        elif status == ComplianceStatus.WARNING:
            return "allow", "allowed_with_warning"
        else:
            return "none", "allowed"

    async def _get_applicable_policy(
        self, request: ComplianceCheckRequest
    ) -> Optional[CompliancePolicy]:
        """获取适用的策略

        Issue #347: backed by Redis cache so multiple replicas observe
        the same policy without each maintaining a private dict. On
        Redis outage we fall back to the DB and log — the cache is a
        latency optimisation, not a correctness gate.
        """
        try:
            if request.policy_id:
                return await self._get_policy_by_id_cached(request.policy_id)

            # Cache the per-org active policy list (lookup by content type
            # happens client-side over the cached payload).
            org_key = f"org:{request.organization_id or 'global'}:active"
            policies = await self._get_active_policies_cached(
                org_key, request.organization_id
            )

            for policy in policies:
                if request.content_type in policy.content_types:
                    return policy

            return None
        except Exception as e:
            logger.error(f"Error getting policy: {e}")
            return None

    async def _get_policy_by_id_cached(
        self, policy_id: str
    ) -> Optional[CompliancePolicy]:
        """Read a single policy through the Redis cache."""
        cache_key = f"id:{policy_id}"

        def _loads(raw: bytes) -> CompliancePolicy:
            return CompliancePolicy.model_validate_json(raw)

        def _dumps(policy: CompliancePolicy) -> bytes:
            return policy.model_dump_json().encode()

        cached = await self._policy_cache.get(cache_key, loads=_loads)
        if cached is not None:
            return cached

        # DB fallback — also primes the cache when Redis is healthy.
        policy = await self.repository.get_policy_by_id(policy_id)
        if policy is not None:
            await self._policy_cache.set(cache_key, policy, dumps=_dumps)
        return policy

    async def _get_active_policies_cached(
        self, cache_key: str, organization_id: Optional[str]
    ) -> List[CompliancePolicy]:
        """Read the per-org active-policy list through the Redis cache."""

        def _loads(raw: bytes) -> List[CompliancePolicy]:
            import json as _json

            data = _json.loads(raw)
            return [CompliancePolicy.model_validate(p) for p in data]

        def _dumps(policies: List[CompliancePolicy]) -> bytes:
            payload = [p.model_dump(mode="json") for p in policies]
            import json as _json

            return _json.dumps(payload).encode()

        cached = await self._policy_cache.get(cache_key, loads=_loads)
        if cached is not None:
            return cached

        policies = await self.repository.get_active_policies(organization_id)
        if policies:
            await self._policy_cache.set(cache_key, policies, dumps=_dumps)
        return policies

    async def invalidate_policy_cache(
        self,
        *,
        policy_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        purge_all_orgs: bool = False,
    ) -> None:
        """Drop cached policy entries after a write.

        Issue #347 acceptance criterion — explicit DEL on writes (no
        full FLUSHDB). Callers should invoke this whenever a policy is
        created, updated, or deactivated.

        Issue #347 follow-up (PR #357 review): when called with only
        ``policy_id`` (the common path from update/delete handlers),
        we now look the policy's ``organization_id`` up in the DB and
        invalidate both the per-policy key AND the per-org active list.
        Without this, the org's ``org:<x>:active`` entry stays for the
        full TTL and the policy continues to apply on every replica
        until it expires.

        :param policy_id: When provided, drop ``id:<policy_id>`` AND
            (after a DB lookup) the policy's owning org's active list.
        :param organization_id: When provided, drop the org's active
            list. Combined with ``policy_id`` this skips the DB lookup.
        :param purge_all_orgs: When True, also walk every
            ``org:*:active`` key via SCAN. Reserved for global policy
            edits (e.g. retiring a platform-wide rule); never used by
            the routine update path.
        """
        # Step 1 — when the caller knows the org, that's authoritative.
        target_org: Optional[str] = organization_id

        # Step 2 — if we only got a policy_id, look the org up so we can
        # invalidate the corresponding active list. Tolerate a DB miss
        # (the policy may already be deleted) by falling back to the
        # global bucket invalidation.
        if policy_id and organization_id is None:
            try:
                policy = await self.repository.get_policy_by_id(policy_id)
            except Exception as exc:
                policy = None
                logger.warning(
                    "invalidate_policy_cache: failed to look up policy %s "
                    "for org-list invalidation: %s",
                    policy_id,
                    exc,
                )
            if policy is not None:
                target_org = policy.organization_id

        # Step 3 — drop the per-policy key.
        if policy_id:
            await self._policy_cache.delete(f"id:{policy_id}")

        # Step 4 — drop the per-org active list (and the global bucket
        # which represents org_id IS NULL policies).
        if target_org is not None:
            await self._policy_cache.delete(f"org:{target_org}:active")
        await self._policy_cache.delete("org:global:active")

        # Step 5 — only purge every org's active list when the caller
        # explicitly opts in (e.g. retiring a platform-wide policy).
        # raise_on_error=False because this is a best-effort fan-out.
        if purge_all_orgs:
            await self._policy_cache.delete_pattern(
                "org:*:active", raise_on_error=False
            )

    def _hash_content(self, content: str) -> str:
        """生成内容哈希"""
        return hashlib.sha256(content.encode()).hexdigest()

    def _mask_pii(self, value: str) -> str:
        """掩码PII"""
        if len(value) <= 4:
            return "***"
        return value[:2] + "*" * (len(value) - 4) + value[-2:]

    def _get_response_message(
        self, status: ComplianceStatus, risk_level: RiskLevel
    ) -> str:
        """获取响应消息"""
        if status == ComplianceStatus.PASS:
            return "Content passed all compliance checks"
        elif status == ComplianceStatus.WARNING:
            return "Content passed with warnings"
        elif status == ComplianceStatus.FLAGGED:
            return "Content flagged for review"
        elif status == ComplianceStatus.FAIL:
            return "Content failed compliance checks"
        elif status == ComplianceStatus.BLOCKED:
            return "Content blocked due to compliance violations"
        else:
            return "Compliance check pending"


__all__ = ["ComplianceService"]
