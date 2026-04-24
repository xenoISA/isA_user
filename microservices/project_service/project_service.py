"""Project Service — Business logic (#258, #295, #296, #297, #298)"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import UploadFile

from .protocols import (
    ProjectRepositoryProtocol,
    EventBusProtocol,
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
    ):
        self.repository = repository
        self.storage_client = storage_client
        self.event_bus = event_bus

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

    async def _verify_ownership(self, project_id: str, user_id: str) -> Dict[str, Any]:
        project = await self.repository.get_project(project_id)
        if not project:
            raise ProjectNotFoundError(f"Project {project_id} not found")
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
    ) -> Dict[str, Any]:
        count = await self.repository.count_projects(user_id)
        if count >= MAX_PROJECTS_PER_USER:
            raise ProjectLimitExceeded(
                f"User has reached the {MAX_PROJECTS_PER_USER}-project limit"
            )
        result = await self.repository.create_project(
            user_id, name, description, custom_instructions
        )
        await self._publish("create", user_id, result["id"], success=True)
        return result

    async def get_project(self, project_id: str, user_id: str) -> Dict[str, Any]:
        project = await self._verify_ownership(project_id, user_id)
        await self._publish("read", user_id, project_id, success=True)
        return project

    async def list_projects(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        return await self.repository.list_projects(user_id, limit, offset)

    async def update_project(
        self, project_id: str, user_id: str, **updates
    ) -> Dict[str, Any]:
        if not updates:
            raise InvalidProjectUpdate("No fields to update")
        await self._verify_ownership(project_id, user_id)
        result = await self.repository.update_project(project_id, **updates)
        await self._publish("update", user_id, project_id, success=True)
        return result

    async def delete_project(self, project_id: str, user_id: str) -> bool:
        await self._verify_ownership(project_id, user_id)
        deleted = await self.repository.delete_project(project_id)
        await self._publish("delete", user_id, project_id, success=True)
        return deleted

    async def set_instructions(
        self, project_id: str, user_id: str, instructions: str
    ) -> bool:
        await self._verify_ownership(project_id, user_id)
        result = await self.repository.set_instructions(project_id, instructions)
        await self._publish("set_instructions", user_id, project_id, success=True)
        return result

    async def list_project_files(
        self,
        project_id: str,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        await self._verify_ownership(project_id, user_id)
        return await self.repository.list_project_files(project_id, limit, offset)

    async def upload_project_file(
        self,
        project_id: str,
        user_id: str,
        file: UploadFile,
    ) -> Dict[str, Any]:
        if self.storage_client is None:
            raise ProjectStorageError("Storage client is not configured")

        project = await self._verify_ownership(project_id, user_id)
        file_content = await file.read()
        upload_result = await self.storage_client.upload_file(
            file_content=file_content,
            filename=file.filename or "upload.bin",
            user_id=user_id,
            organization_id=project.get("org_id"),
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
    ) -> bool:
        if self.storage_client is None:
            raise ProjectStorageError("Storage client is not configured")

        await self._verify_ownership(project_id, user_id)
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
