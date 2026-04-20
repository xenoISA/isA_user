"""Project Service — Business logic (#258, #295, #296, #297, #298)"""
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from .protocols import (
    ProjectRepositoryProtocol,
    EventBusProtocol,
    ProjectNotFoundError,
    ProjectPermissionError,
    ProjectLimitExceeded,
    InvalidProjectUpdate,
)

logger = logging.getLogger(__name__)

MAX_PROJECTS_PER_USER = 100


class ProjectService:
    def __init__(
        self,
        repository: ProjectRepositoryProtocol,
        event_bus: Optional[EventBusProtocol] = None,
    ):
        self.repository = repository
        self.event_bus = event_bus

    # ── helpers ──────────────────────────────────────────────────────────

    async def _publish(self, action: str, user_id: str, project_id: str, success: bool, detail: str = None):
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
        self, user_id: str, name: str, description: str = None, custom_instructions: str = None
    ) -> Dict[str, Any]:
        count = await self.repository.count_projects(user_id)
        if count >= MAX_PROJECTS_PER_USER:
            raise ProjectLimitExceeded(f"User has reached the {MAX_PROJECTS_PER_USER}-project limit")
        result = await self.repository.create_project(user_id, name, description, custom_instructions)
        await self._publish("create", user_id, result["id"], success=True)
        return result

    async def get_project(self, project_id: str, user_id: str) -> Dict[str, Any]:
        project = await self._verify_ownership(project_id, user_id)
        await self._publish("read", user_id, project_id, success=True)
        return project

    async def list_projects(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        return await self.repository.list_projects(user_id, limit, offset)

    async def update_project(self, project_id: str, user_id: str, **updates) -> Dict[str, Any]:
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

    async def set_instructions(self, project_id: str, user_id: str, instructions: str) -> bool:
        await self._verify_ownership(project_id, user_id)
        result = await self.repository.set_instructions(project_id, instructions)
        await self._publish("set_instructions", user_id, project_id, success=True)
        return result
