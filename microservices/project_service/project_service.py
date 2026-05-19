"""Project Service — Business logic (#258, #295, #296, #297, #298)"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import UploadFile

from .protocols import (
    ProjectRepositoryProtocol,
    EventBusProtocol,
    OrganizationAccessProtocol,
    StorageServiceProtocol,
    ProjectNotFoundError,
    ProjectPermissionError,
    ProjectLimitExceeded,
    InvalidProjectUpdate,
    ProjectStorageError,
)

logger = logging.getLogger(__name__)

MAX_PROJECTS_PER_USER = 100


class ProjectService:
    def __init__(
        self,
        repository: ProjectRepositoryProtocol,
        storage_client: Optional[StorageServiceProtocol] = None,
        event_bus: Optional[EventBusProtocol] = None,
        organization_access: Optional[OrganizationAccessProtocol] = None,
        project_sharing_client: Optional[Any] = None,
    ):
        self.repository = repository
        self.storage_client = storage_client
        self.event_bus = event_bus
        self.organization_access = organization_access
        # project_sharing_client is best-effort; if not provided, archive
        # still succeeds and share revocation falls to a reconcile job
        # (see microservices/project_service/clients/project_sharing_client.py).
        self.project_sharing_client = project_sharing_client

    # ── helpers ──────────────────────────────────────────────────────────

    async def _publish(
        self,
        action: str,
        user_id: str,
        project_id: str,
        success: bool,
        detail: str = None,
    ):
        if not self.event_bus:
            return
        try:
            from core.nats_client import Event

            event = Event(
                event_type=f"project.{action}",
                source="project_service",
                data={
                    "user_id": user_id,
                    "project_id": project_id,
                    "action": action,
                    "success": success,
                    "detail": detail,
                    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                },
            )
            await self.event_bus.publish_event(event)
        except Exception as exc:
            logger.warning("Failed to publish audit event: %s", exc)

    @staticmethod
    def _project_org_id(project: Dict[str, Any]) -> Optional[str]:
        return project.get("organization_id") or project.get("org_id")

    async def _has_org_access(
        self, organization_id: str, user_id: str, write: bool = False
    ) -> bool:
        if user_id == "internal-service":
            return True
        if self.organization_access is None:
            return False

        if write:
            return bool(
                await self.organization_access.check_admin_access(
                    organization_id, user_id
                )
            )
        return bool(
            await self.organization_access.check_user_access(organization_id, user_id)
        )

    async def _require_org_access(
        self, organization_id: str, user_id: str, write: bool = False
    ) -> None:
        if not await self._has_org_access(organization_id, user_id, write=write):
            raise ProjectPermissionError("Not authorized to access this organization")

    async def _verify_access(
        self,
        project_id: str,
        user_id: str,
        organization_id: Optional[str] = None,
        write: bool = False,
    ) -> Dict[str, Any]:
        project = await self.repository.get_project(project_id)
        if not project:
            raise ProjectNotFoundError(f"Project {project_id} not found")

        project_org_id = self._project_org_id(project)
        if organization_id and project_org_id != organization_id:
            raise ProjectPermissionError("Project does not belong to organization")

        if project_org_id:
            if project["user_id"] == user_id:
                return project
            if await self._has_org_access(project_org_id, user_id, write=write):
                return project
            raise ProjectPermissionError("Not authorized to access this project")

        if project["user_id"] != user_id:
            raise ProjectPermissionError("Not authorized to access this project")
        return project

    # ── CRUD ─────────────────────────────────────────────────────────────

    async def create_project(
        self,
        user_id: str,
        name: str,
        description: str = None,
        custom_instructions: str = None,
        organization_id: str = None,
    ) -> Dict[str, Any]:
        if organization_id:
            await self._require_org_access(organization_id, user_id)

        count = await self.repository.count_projects(user_id)
        if count >= MAX_PROJECTS_PER_USER:
            raise ProjectLimitExceeded(
                f"User has reached the {MAX_PROJECTS_PER_USER}-project limit"
            )
        result = await self.repository.create_project(
            user_id, name, description, custom_instructions, organization_id
        )
        await self._publish("create", user_id, result["id"], success=True)
        return result

    async def get_project(
        self,
        project_id: str,
        user_id: str,
        organization_id: str = None,
    ) -> Dict[str, Any]:
        project = await self._verify_access(project_id, user_id, organization_id)
        await self._publish("read", user_id, project_id, success=True)
        return project

    async def list_projects(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        organization_id: str = None,
        include_archived: bool = False,
        starred_only: bool = False,
    ) -> List[Dict[str, Any]]:
        if organization_id:
            await self._require_org_access(organization_id, user_id)
        return await self.repository.list_projects(
            user_id,
            limit,
            offset,
            organization_id,
            include_archived=include_archived,
            starred_only=starred_only,
        )

    async def export_user_data(
        self,
        user_id: str,
        organization_id: str = None,
        request_id: str = None,
    ) -> Dict[str, Any]:
        """Export project-owned subject data for GDPR access requests."""
        project_page_size = 100
        file_page_size = 500
        projects: List[Dict[str, Any]] = []
        project_files: Dict[str, List[Dict[str, Any]]] = {}

        project_offset = 0
        while True:
            project_page = await self.repository.list_projects_for_export(
                user_id,
                limit=project_page_size,
                offset=project_offset,
                organization_id=organization_id,
            )
            projects.extend(project_page)
            if len(project_page) < project_page_size:
                break
            project_offset += project_page_size

        file_records = 0
        for project in projects:
            project_id = project.get("id")
            if not project_id:
                continue

            files: List[Dict[str, Any]] = []
            file_offset = 0
            while True:
                file_page = await self.repository.list_project_files(
                    project_id,
                    limit=file_page_size,
                    offset=file_offset,
                )
                files.extend(file_page)
                if len(file_page) < file_page_size:
                    break
                file_offset += file_page_size

            project_files[project_id] = files
            file_records += len(files)

        return {
            "schema_version": "project-export-v1",
            "service": "project_service",
            "user_id": user_id,
            "organization_id": organization_id,
            "gdpr_request_id": request_id,
            "exported_at": datetime.now(tz=timezone.utc).isoformat(),
            "projects": projects,
            "project_files": project_files,
            "counts": {
                "records": len(projects) + file_records,
                "sections": {
                    "projects": len(projects),
                    "project_files": file_records,
                },
            },
        }

    async def update_project(
        self,
        project_id: str,
        user_id: str,
        organization_id: str = None,
        **updates,
    ) -> Dict[str, Any]:
        if not updates:
            raise InvalidProjectUpdate("No fields to update")
        await self._verify_access(project_id, user_id, organization_id, write=True)
        result = await self.repository.update_project(project_id, **updates)
        await self._publish("update", user_id, project_id, success=True)
        return result

    async def delete_project(
        self, project_id: str, user_id: str, organization_id: str = None
    ) -> bool:
        await self._verify_access(project_id, user_id, organization_id, write=True)
        deleted = await self.repository.delete_project(project_id)
        await self._publish("delete", user_id, project_id, success=True)
        return deleted

    async def set_instructions(
        self,
        project_id: str,
        user_id: str,
        instructions: str,
        organization_id: str = None,
    ) -> bool:
        await self._verify_access(project_id, user_id, organization_id, write=True)
        result = await self.repository.set_instructions(project_id, instructions)
        await self._publish("set_instructions", user_id, project_id, success=True)
        return result

    # ── Star / Archive (#442, see xenoISA/isA_#429 §15.3, §15.6) ─────────

    async def star_project(
        self,
        project_id: str,
        user_id: str,
        organization_id: str = None,
    ) -> Dict[str, Any]:
        await self._verify_access(project_id, user_id, organization_id, write=True)
        result = await self.repository.set_starred(project_id, True)
        await self._publish("star", user_id, project_id, success=True)
        return result

    async def unstar_project(
        self,
        project_id: str,
        user_id: str,
        organization_id: str = None,
    ) -> Dict[str, Any]:
        await self._verify_access(project_id, user_id, organization_id, write=True)
        result = await self.repository.set_starred(project_id, False)
        await self._publish("unstar", user_id, project_id, success=True)
        return result

    async def archive_project(
        self,
        project_id: str,
        user_id: str,
        organization_id: str = None,
    ) -> Dict[str, Any]:
        """Archive a project and best-effort revoke all of its shares.

        Per design (xenoISA/isA_#429 §15.6) the archived_at flag is the
        source of truth — if project_sharing_service is unreachable we still
        return success and let a reconcile job clean up shares later.
        """
        await self._verify_access(project_id, user_id, organization_id, write=True)
        result = await self.repository.set_archived(project_id, True)
        # Fire-and-forget share revocation. Never raises.
        if self.project_sharing_client is not None:
            try:
                revoked = await self.project_sharing_client.revoke_all_shares(
                    project_id
                )
                if not revoked:
                    logger.info(
                        "project %s archived; share revocation deferred to reconcile job",
                        project_id,
                    )
            except Exception as exc:  # extra belt-and-suspenders
                logger.warning(
                    "project_sharing_client raised during archive of %s: %s",
                    project_id,
                    exc,
                )
        else:
            logger.debug(
                "project_sharing_client not configured; skipping share revocation for %s",
                project_id,
            )
        await self._publish("archive", user_id, project_id, success=True)
        return result

    async def unarchive_project(
        self,
        project_id: str,
        user_id: str,
        organization_id: str = None,
    ) -> Dict[str, Any]:
        """Unarchive — clears archived_at. Does NOT restore previously revoked
        shares (matches Claude / design §15.6 — must re-invite)."""
        await self._verify_access(project_id, user_id, organization_id, write=True)
        result = await self.repository.set_archived(project_id, False)
        await self._publish("unarchive", user_id, project_id, success=True)
        return result

    async def list_project_files(
        self,
        project_id: str,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
        organization_id: str = None,
    ) -> List[Dict[str, Any]]:
        await self._verify_access(project_id, user_id, organization_id)
        return await self.repository.list_project_files(project_id, limit, offset)

    async def upload_project_file(
        self,
        project_id: str,
        user_id: str,
        file: UploadFile,
        organization_id: str = None,
    ) -> Dict[str, Any]:
        if self.storage_client is None:
            raise ProjectStorageError("Storage client is not configured")

        project = await self._verify_access(
            project_id, user_id, organization_id, write=True
        )
        file_content = await file.read()
        upload_result = await self.storage_client.upload_file(
            file_content=file_content,
            filename=file.filename or "upload.bin",
            user_id=user_id,
            organization_id=self._project_org_id(project),
            access_level="private",
            content_type=file.content_type,
            metadata={"project_id": project_id},
            tags=["project-knowledge", project_id],
            enable_indexing=True,
        )
        if not upload_result:
            raise ProjectStorageError("Failed to upload project file")

        persisted = await self.repository.create_project_file(
            project_id=project_id,
            file_id=upload_result["file_id"],
            filename=file.filename or "upload.bin",
            storage_path=upload_result["file_path"],
            file_type=upload_result.get("content_type") or file.content_type,
            file_size=upload_result.get("file_size") or len(file_content),
        )
        await self._publish(
            "upload_file", user_id, project_id, success=True, detail=persisted["id"]
        )
        return persisted

    async def delete_project_file(
        self,
        project_id: str,
        file_id: str,
        user_id: str,
        organization_id: str = None,
    ) -> bool:
        if self.storage_client is None:
            raise ProjectStorageError("Storage client is not configured")

        await self._verify_access(project_id, user_id, organization_id, write=True)
        project_file = await self.repository.get_project_file(project_id, file_id)
        if not project_file:
            raise ProjectNotFoundError(f"Project file {file_id} not found")

        deleted = await self.storage_client.delete_file(
            file_id, user_id, permanent=True
        )
        if not deleted:
            raise ProjectStorageError(f"Failed to delete storage file {file_id}")

        await self.repository.delete_project_file(project_id, file_id)
        await self._publish(
            "delete_file", user_id, project_id, success=True, detail=file_id
        )
        return True
