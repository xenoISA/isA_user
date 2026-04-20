"""
Mock implementations for Project Service component testing.

Implements ProjectRepositoryProtocol — no real I/O.
"""
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


class MockProjectRepository:
    """Mock repository implementing ProjectRepositoryProtocol."""

    def __init__(self):
        self._projects: Dict[str, Dict[str, Any]] = {}
        self._should_fail: Optional[Exception] = None

    def set_failure(self, error: Exception):
        self._should_fail = error

    def clear_failure(self):
        self._should_fail = None

    def seed_project(self, project_id: str, user_id: str, name: str, **kwargs) -> Dict[str, Any]:
        now = datetime.now(tz=timezone.utc)
        project = {
            "id": project_id,
            "user_id": user_id,
            "name": name,
            "description": kwargs.get("description"),
            "custom_instructions": kwargs.get("custom_instructions"),
            "created_at": kwargs.get("created_at", now),
            "updated_at": kwargs.get("updated_at", now),
        }
        self._projects[project_id] = project
        return project

    async def create_project(self, user_id: str, name: str, description: str = None, custom_instructions: str = None) -> Dict[str, Any]:
        if self._should_fail:
            raise self._should_fail
        project_id = str(uuid.uuid4())
        now = datetime.now(tz=timezone.utc)
        project = {"id": project_id, "user_id": user_id, "name": name, "description": description, "custom_instructions": custom_instructions, "created_at": now, "updated_at": now}
        self._projects[project_id] = project
        return project

    async def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        if self._should_fail:
            raise self._should_fail
        return self._projects.get(project_id)

    async def list_projects(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        if self._should_fail:
            raise self._should_fail
        user_projects = [p for p in self._projects.values() if p["user_id"] == user_id]
        user_projects.sort(key=lambda p: p["updated_at"], reverse=True)
        return user_projects[offset:offset + limit]

    async def update_project(self, project_id: str, **updates) -> Optional[Dict[str, Any]]:
        if self._should_fail:
            raise self._should_fail
        project = self._projects.get(project_id)
        if not project:
            return None
        project.update(updates)
        project["updated_at"] = datetime.now(tz=timezone.utc)
        return project

    async def delete_project(self, project_id: str) -> bool:
        if self._should_fail:
            raise self._should_fail
        return self._projects.pop(project_id, None) is not None

    async def set_instructions(self, project_id: str, instructions: str) -> bool:
        if self._should_fail:
            raise self._should_fail
        project = self._projects.get(project_id)
        if not project:
            return False
        project["custom_instructions"] = instructions
        project["updated_at"] = datetime.now(tz=timezone.utc)
        return True

    async def count_projects(self, user_id: str) -> int:
        if self._should_fail:
            raise self._should_fail
        return sum(1 for p in self._projects.values() if p["user_id"] == user_id)

    async def cleanup(self) -> None:
        pass
